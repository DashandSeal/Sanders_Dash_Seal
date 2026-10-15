"""Sanders Dash & Seal — fail-closed Stripe payment boundary (development).

This adapter does not grant notarial authority or create live charges by itself.
Callers supply an authenticated, authorized case and a Stripe client. No secret
or live customer data is stored in source control.
"""
import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path

class PaymentDenied(Exception):
    pass

class PaymentLedger:
    """Durable deduplication of Stripe event IDs and case/payment associations."""
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_events (
                event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
                case_id TEXT, payment_id TEXT, recorded_at INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_cases (
                case_id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                amount INTEGER NOT NULL, currency TEXT NOT NULL,
                state TEXT NOT NULL)""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def register_checkout(self, case_id, session_id, amount, currency):
        if not case_id or not session_id or type(amount) is not int or amount < 1:
            raise PaymentDenied('Invalid checkout registration')
        with self.connect() as db:
            try:
                db.execute('INSERT INTO stripe_cases VALUES (?, ?, ?, ?, ?)',
                           (case_id, session_id, amount, currency, 'PENDING'))
            except sqlite3.IntegrityError as exc:
                raise PaymentDenied('Case or session already registered') from exc

    def record_event(self, event, now=None):
        if not isinstance(event, dict) or not isinstance(event.get('id'), str):
            raise PaymentDenied('Invalid event')
        event_id, event_type = event['id'], event.get('type')
        obj = event.get('data', {}).get('object', {})
        if not isinstance(obj, dict):
            raise PaymentDenied('Invalid event object')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM stripe_events WHERE event_id=?', (event_id,)).fetchone():
                return 'DUPLICATE'
            case_id = obj.get('client_reference_id')
            payment_id = obj.get('payment_intent')
            if event_type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
                row = db.execute('SELECT session_id, amount, currency, state FROM stripe_cases WHERE case_id=?',
                                 (case_id,)).fetchone()
                if (not row or obj.get('id') != row[0] or
                    obj.get('amount_total') != row[1] or obj.get('currency') != row[2] or
                    obj.get('mode') != 'payment'):
                    raise PaymentDenied('Payment case, session or amount mismatch')
                if obj.get('payment_status') != 'paid':
                    state = 'PENDING'
                else:
                    state = 'PAID'
                if row[3] == 'PAID' and state != 'PAID':
                    raise PaymentDenied('Payment state regression')
                db.execute('UPDATE stripe_cases SET state=? WHERE case_id=?', (state, case_id))
            else:
                case_id = None
                payment_id = None
            db.execute('INSERT INTO stripe_events VALUES (?, ?, ?, ?, ?)',
                       (event_id, event_type or '', case_id, payment_id,
                        int(time.time() if now is None else now)))
            return 'RECORDED'

    def status(self, case_id):
        with self.connect() as db:
            row = db.execute('SELECT state FROM stripe_cases WHERE case_id=?', (case_id,)).fetchone()
        return row[0] if row else None

def verify_stripe_webhook(payload, signature_header, signing_secret, now=None, tolerance=300):
    """Verify Stripe's signed raw webhook body before parsing JSON."""
    if not isinstance(payload, bytes) or not isinstance(signing_secret, str) or not signing_secret:
        raise PaymentDenied('Missing webhook trust material')
    if not isinstance(signature_header, str):
        raise PaymentDenied('Missing webhook signature')
    parts = [p.strip().split('=', 1) for p in signature_header.split(',')]
    values = {}
    for part in parts:
        if len(part) == 2:
            values.setdefault(part[0], []).append(part[1])
    try:
        timestamp = int(values['t'][0])
    except (KeyError, ValueError, IndexError) as exc:
        raise PaymentDenied('Invalid webhook timestamp') from exc
    clock = int(time.time() if now is None else now)
    if abs(clock - timestamp) > tolerance:
        raise PaymentDenied('Webhook timestamp outside replay window')
    expected = hmac.new(signing_secret.encode(), str(timestamp).encode() + b'.' + payload,
                        hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in values.get('v1', [])):
        raise PaymentDenied('Webhook signature invalid')
    try:
        event = json.loads(payload)
    except (UnicodeDecodeError, ValueError) as exc:
        raise PaymentDenied('Invalid webhook JSON') from exc
    if not isinstance(event, dict):
        raise PaymentDenied('Invalid webhook envelope')
    return event

def checkout_parameters(case_id, amount_cents, currency, service_label, success_url, cancel_url):
    """Return server-side Stripe Checkout parameters; never infer price from browser input."""
    if (not all(isinstance(v, str) and v for v in
                (case_id, currency, service_label, success_url, cancel_url))
        or type(amount_cents) is not int or amount_cents < 1
        or currency.lower() != currency or len(currency) != 3
        or not success_url.startswith('https://') or not cancel_url.startswith('https://')):
        raise PaymentDenied('Invalid approved checkout inputs')
    return {
        'mode': 'payment',
        'client_reference_id': case_id,
        'line_items': [{'price_data': {'currency': currency,
                        'product_data': {'name': service_label},
                        'unit_amount': amount_cents}, 'quantity': 1}],
        'success_url': success_url,
        'cancel_url': cancel_url,
        'metadata': {'case_id': case_id},
    }
