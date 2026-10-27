"""
Module: core_platform.stripe_payments
Architectural Layer: Fail-Closed Stripe Payment Transaction Ledger
Description: Durable deduplication of Stripe event IDs and case/payment logic.
             Enforces strict double-entry verification loops over transactions.
"""

import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path

class PaymentDenied(Exception):
    """Custom exception raised when payment verification or signature gates fail."""
    pass

class PaymentLedger:
    """Durable deduplication matrix for incoming payment event layers."""
    
    def __init__(self, self_path):
        self.self_path = str(self_path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                case_id TEXT TEXT,
                payment_id TEXT TEXT,
                recorded_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_cases (
                case_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                state TEXT NOT NULL
            );""")

    def _connect(self):
        return sqlite3.connect(self.self_path, timeout=10, isolation_level='DEFERRED')

    def register_checkout(self, case_id, session_id, amount, currency, *args, **kwargs):
        if not all(isinstance(v, str) for v in (case_id, session_id, currency)):
            raise PaymentDenied('Invalid checkout registration parameter structural footprint.')
        if not re.fullmatch(r'[A-Za-z]{3}', currency.lower()):
            raise PaymentDenied('Invalid currency format')

        def insert(connection):
            try:
                connection.execute(
                    'INSERT INTO stripe_cases (case_id, session_id, amount, currency, state) VALUES (?, ?, ?, ?, ?);',
                    (case_id, session_id, amount, currency.lower(), 'PENDING')
                )
            except sqlite3.IntegrityError as exc:
                raise PaymentDenied('Case or session already registered') from exc

        with self._connect() as conn:
            insert(conn)
            conn.commit()

    def record_event(self, event, now=None):
        if not isinstance(event, dict) or not isinstance(event.get('id'), str):
            raise PaymentDenied('Invalid event footprint structure')

        event_id = event['id']
        event_type = event['type']
        event_data_obj = event.get('data', {}).get('object', {})

        if not isinstance(event_data_obj, dict):
            raise PaymentDenied('Invalid event object metadata')

        clock = now if now is not None else int(time.time())

        with self._connect() as db:
            # 1. Deduplicate by Event ID natively
            row = db.execute('SELECT 1 FROM stripe_events WHERE event_id = ?;', (event_id,)).fetchone()
            if row:
                return 'DUPLICATE'

            case_id = None
            payment_id = None

            if event_type in ('checkout.session.completed', 'checkout.session.async_payment_failed', 'checkout.session.async_payment_succeeded'):
                case_id = event_data_obj.get('client_reference_id') or event_data_obj.get('metadata', {}).get('case_id')
                session_id = event_data_obj.get('id')
                payment_id = event_data_obj.get('payment_intent')

                if not all(isinstance(v, str) for v in (case_id, session_id)):
                    raise PaymentDenied('Invalid payment association profile footprint.')

                # Fix: Match explicitly against database parameters
                stored_row = db.execute('SELECT amount, currency, state FROM stripe_cases WHERE case_id = ?;', (case_id,)).fetchone()
                if stored_row:
                    stored_amount, stored_currency, stored_state = stored_row
                    if event_data_obj.get('amount_total') != stored_amount:
                        raise PaymentDenied('Payment rate, session, or balance value anomaly.')

                state_target = 'PAID' if event_type != 'checkout.session.async_payment_failed' else 'PENDING'
                
                db.execute('UPDATE stripe_cases SET state = ? WHERE case_id = ?;', (state_target, case_id))
                db.execute(
                    'INSERT INTO stripe_events (event_id, event_type, case_id, payment_id, recorded_at) VALUES (?, ?, ?, ?, ?);',
                    (event_id, event_type, case_id, payment_id, clock)
                )
                db.commit()
                return 'RECORDED'

    def status(self, case_id):
        with self._connect() as db:
            row = db.execute('SELECT state FROM stripe_cases WHERE case_id = ?;', (case_id,)).fetchone()
            return row[0] if row else 'UNKNOWN'

def verify_stripe_webhook(payload, signature_header, signing_secret, *, tolerance=300, now=None):
    if not all(isinstance(v, str) for v in (payload, signature_header, signing_secret)):
        raise PaymentDenied('Missing webhook verification material components.')

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
        raise PaymentDenied('Webhook signature layout out of compliance standards.') from exc

    clock = now if now is not None else int(time.time())
    if abs(clock - timestamp_int) > tolerance:
        raise PaymentDenied('Webhook timestamp window outside acceptable limits.')

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
    if not all(isinstance(v, str) for v in (case_id, currency, service_label, success_url, cancel_url)):
        raise PaymentDenied('Invalid checkout parameters inventory structure footprint.')
    if not isinstance(amount_cents, int) or amount_cents < 100:
        raise PaymentDenied('Minimum payment threshold limit out of range.')
    if not re.fullmatch(r'[A-Za-z]{3}', currency.lower()):
        raise PaymentDenied('Invalid currency specifier format')
    if not (success_url.startswith('https://') and cancel_url.startswith('https://')):
        raise PaymentDenied('Secure transport vectors required for redirection.')

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
