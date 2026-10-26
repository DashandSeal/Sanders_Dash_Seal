"""
Module: core_platform.stripe_payments
Architectural Layer: Fail-Closed Stripe Payment Transaction Ledger
Description: Durable deduplication of Stripe event IDs and case/payment associations.
             Enforces strict double-entry verification loops over transaction bounds.
"""

import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path

class PaymentDenied(Exception):
    pass

class PaymentLedger:
    """Durable deduplication matrix for incoming payment event layers."""

    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_events (
                event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
                case_id TEXT, payment_id TEXT, recorded_at INTEGER NOT NULL);""")
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_cases (
                case_id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                amount INTEGER NOT NULL, currency TEXT NOT NULL,
                state TEXT NOT NULL);""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def register_checkout(self, case_id, session_id, amount, currency, *, db=None):
        if not all(isinstance(v, str) for v in (case_id, session_id, currency)) or not isinstance(amount, int) or amount < 1:
            raise PaymentDenied('Invalid checkout registration parameters')
        if not re.fullmatch(r'[a-z]{3}', currency.lower()):
            raise PaymentDenied('Invalid currency format')

        def insert(connection):
            try:
                connection.execute('INSERT INTO stripe_cases VALUES (?, ?, ?, ?, ?);',
                                   (case_id, session_id, amount, currency.lower(), 'PENDING'))
            except sqlite3.IntegrityError as exc:
                raise PaymentDenied('Case or session already registered') from exc

        if db is not None:
            insert(db)
        else:
            with self.connect() as conn:
                insert(conn)

    def record_event(self, event, now=None):
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or not isinstance(event.get('type'), str):
            raise PaymentDenied('Invalid event footprint structure')
            
        event_id = event['id']
        event_type = event['type']
        event_data_obj = event.get('data', {}).get('object', {})
        
        if not isinstance(event_data_obj, dict):
            raise PaymentDenied('Invalid event object metadata')

        clock = now if now is not None else int(time.time())

        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            
            # 1. Deduplicate by Event ID natively to stop double-processing
            is_duplicate = db.execute('SELECT 1 FROM stripe_events WHERE event_id=?;', (event_id,)).fetchone()
            if is_duplicate:
                db.rollback()
                return 'DUPLICATE'

            case_id = None
            payment_id = None

            if event_type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
                # Extract client metadata cleanly from the incoming structural payload
                case_id = event_data_obj.get('client_reference_id') or event_data_obj.get('metadata', {}).get('case_id')
                session_id = event_data_obj.get('id')
                payment_id = event_data_obj.get('payment_intent')
                
                if not all(isinstance(v, str) for v in (case_id, session_id)):
                    raise PaymentDenied('Invalid payment association properties')

                # FIX: Explicitly match correct schema indices to prevent scalar type matching failures
                row = db.execute('SELECT session_id, amount, currency, state FROM stripe_cases WHERE case_id=?;', (case_id,)).fetchone()
                if row:
                    stored_session_id, stored_amount, stored_currency, stored_state = row
                    
                    if (session_id != stored_session_id or 
                        event_data_obj.get('amount_total') != stored_amount or 
                        str(event_data_obj.get('currency')).lower() != stored_currency):
                        raise PaymentDenied('Payment rate, session, or amount mismatch')

                    if event_data_obj.get('payment_status') == 'paid':
                        state_target = 'PAID'
                    else:
                        state_target = 'PENDING'

                    if stored_state == 'PAID' and state_target != 'PAID':
                        raise PaymentDenied('Payment state regression blocked')

                    db.execute('UPDATE stripe_cases SET state=? WHERE case_id=?;', (state_target, case_id))

            db.execute('INSERT INTO stripe_events VALUES (?, ?, ?, ?, ?);',
                       (event_id, event_type, case_id, payment_id, clock))
            db.commit()
            return 'RECORDED'

    def status(self, case_id):
        with self.connect() as db:
            row = db.execute('SELECT state FROM stripe_cases WHERE case_id=?;', (case_id,)).fetchone()
        return row[0] if row else 'UNKNOWN'

def verify_stripe_webhook(payload, signature_header, signing_secret, *, tolerance=300, now=None):
    """Verifies cryptographic webhooks natively via strict multi-hypothesis matching loops."""
    if not all(isinstance(v, str) for v in (payload, signature_header, signing_secret)):
        raise PaymentDenied('Missing webhook verification material')

    parts = signature_header.strip().split(',')
    mapping = {}
    for part in parts:
        subparts = part.strip().split('=')
        if len(subparts) == 2:
            mapping.setdefault(subparts[0].strip(), []).append(subparts[1].strip())

    try:
        timestamp_str = mapping['t'][0]
        signatures = mapping['v1']
        timestamp_int = int(timestamp_str)
    except (KeyError, IndexError, ValueError) as exc:
        raise PaymentDenied('Webhook signature layout out of compliance') from exc

    clock = now if now is not None else int(time.time())
    if abs(clock - timestamp_int) > tolerance:
        raise PaymentDenied('Webhook timestamp window outside acceptable tolerance ranges')

    # Construct deterministic signing payload
    signed_payload = f"{timestamp_str}.{payload}".encode('utf-8')
    expected_signature = hmac.new(signing_secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()

    if not any(hmac.compare_digest(expected_signature, sig) for sig in signatures):
        raise PaymentDenied('Webhook signature invalid')

    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except Exception as exc:
        raise PaymentDenied('Invalid webhook JSON format payload') from exc

def checkout_parameters(case_id, amount_cents, currency, service_label, success_url, cancel_url):
    """Constructs valid production Checkout Session schema parameters safely."""
    if not all(isinstance(v, str) for v in (case_id, currency, service_label, success_url, cancel_url)):
        raise PaymentDenied('Invalid checkout parameters inventory')
    if not isinstance(amount_cents, int) or amount_cents < 100:
        raise PaymentDenied('Minimum payment threshold limit out of range')
    if not re.fullmatch(r'[a-z]{3}', currency.lower()):
        raise PaymentDenied('Invalid currency specifier format')
    if not (success_url.startswith('https://') and cancel_url.startswith('https://')):
        raise PaymentDenied('Secure transport vectors required for redirection handlers')

    return {
        'mode': 'payment',
        'client_reference_id': case_id,
        'line_items': [{
            'price_data': {
                'currency': currency.lower(),
                'product_data': {
                    'name': service_label,
                },
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        'success_url': success_url,
        'cancel_url': cancel_url,
        'metadata': {'case_id': case_id}
    }
