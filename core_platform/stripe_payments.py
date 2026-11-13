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
            # Deduplication table the webhook gateway (core_platform/stream_api
            # import_make_app) SELECTs from before dispatching. PaymentLedger
            # is the durable ledger, so it owns this table too; without it
            # every verified event failed with "no such table" (500).
            db.execute("""CREATE TABLE IF NOT EXISTS stripe_processed_events (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                processed_at INTEGER NOT NULL
            );""")

    def _connect(self):
        return sqlite3.connect(self.self_path, timeout=10, isolation_level='DEFERRED')

    def connect(self):
        """Public alias for the ledger_engine interface used by
        core_platform/stream_api.import_make_app (which calls
        ledger_engine.connect()). Same connection as _connect()."""
        return self._connect()

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

    def _ensure_tables(self, db):
        """Create every table the dispatch methods touch, on the given
        connection. The webhook path hands these methods a bare connection
        (wsgi.MockLedgerEngine.connect / stream_api), so the tables cannot
        be assumed to exist from __init__ alone. Safe to call repeatedly:
        CREATE TABLE IF NOT EXISTS + one additive column migration."""
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
        db.execute("""CREATE TABLE IF NOT EXISTS stripe_processed_events (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            processed_at INTEGER NOT NULL
        );""")
        db.execute("""CREATE TABLE IF NOT EXISTS stripe_subscriptions (
            subscription_id TEXT PRIMARY KEY,
            customer_id TEXT,
            case_id TEXT,
            status TEXT NOT NULL,
            current_period_end INTEGER,
            last_invoice_id TEXT,
            amount_paid INTEGER,
            currency TEXT,
            updated_at INTEGER NOT NULL
        );""")
        db.execute("""CREATE TABLE IF NOT EXISTS stripe_reversals (
            charge_id TEXT PRIMARY KEY,
            payment_intent TEXT,
            amount_refunded INTEGER NOT NULL,
            currency TEXT,
            status TEXT NOT NULL,
            refund_ids TEXT,
            recorded_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );""")
        columns = [row[1] for row in db.execute(
            "PRAGMA table_info(stripe_cases)").fetchall()]
        if "payment_intent" not in columns:
            db.execute("ALTER TABLE stripe_cases "
                       "ADD COLUMN payment_intent TEXT")

    @staticmethod
    def _require_str(obj, field):
        value = obj.get(field)
        if not isinstance(value, str) or not value:
            raise PaymentDenied(f"Invalid {field} in ledger event object")
        return value

    @staticmethod
    def _require_amount(obj, field):
        value = obj.get(field)
        if type(value) is not int or value < 0:
            raise PaymentDenied(f"Invalid {field} in ledger event object")
        return value

    @staticmethod
    def _require_currency(obj, field="currency"):
        value = obj.get(field)
        if not isinstance(value, str) or not re.fullmatch(
                r"[A-Za-z]{3}", value):
            raise PaymentDenied(f"Invalid {field} in ledger event object")
        return value.lower()

    def fulfill_checkout(self, session, db=None):
        """Settle a checkout.session.completed object durably.

        Called by core_platform/stream_api.import_make_app with the open
        ledger connection (inside its BEGIN IMMEDIATE transaction): the
        caller owns commit/rollback, so this method never commits when
        ``db`` is given. With ``db=None`` it opens, commits and closes
        its own connection. Idempotent by session id: a session already
        PAID returns 'ALREADY_FULFILLED' without re-applying. A stored
        amount/currency mismatch raises PaymentDenied (fail closed; the
        webhook returns 500 and Stripe retries, the event is not marked
        processed). A session for an unregistered case inserts the case
        row as PAID from the verified event itself.
        """
        if not isinstance(session, dict):
            raise PaymentDenied("Invalid checkout session object")
        session_id = self._require_str(session, "id")
        metadata = session.get("metadata")
        case_id = (session.get("client_reference_id")
                   or (metadata.get("case_id") if isinstance(metadata, dict)
                       else None))
        if not isinstance(case_id, str) or not case_id:
            raise PaymentDenied("Invalid case_id in checkout session")
        amount = self._require_amount(session, "amount_total")
        currency = self._require_currency(session)
        payment_intent = session.get("payment_intent")
        if payment_intent is not None and not isinstance(payment_intent, str):
            raise PaymentDenied("Invalid payment_intent in checkout session")
        if (session.get("payment_status") is not None
                and session.get("payment_status") != "paid"):
            raise PaymentDenied("Checkout session is not paid")

        own = db is None
        conn = db if db is not None else self._connect()
        try:
            self._ensure_tables(conn)
            row = conn.execute(
                "SELECT case_id, amount, currency, state FROM stripe_cases "
                "WHERE session_id = ?", (session_id,)).fetchone()
            if row is not None:
                if row[1] != amount or row[2] != currency:
                    raise PaymentDenied(
                        "Payment rate, session, or balance value anomaly.")
                if row[3] == "PAID":
                    return "ALREADY_FULFILLED"
                conn.execute(
                    "UPDATE stripe_cases SET state = ?, payment_intent = ? "
                    "WHERE session_id = ?",
                    ("PAID", payment_intent, session_id))
            else:
                case_row = conn.execute(
                    "SELECT session_id FROM stripe_cases WHERE case_id = ?",
                    (case_id,)).fetchone()
                if case_row is not None:
                    # Second checkout session for a known case: re-point
                    # the single case row at the settling session.
                    conn.execute(
                        "UPDATE stripe_cases SET session_id = ?, amount = ?, "
                        "currency = ?, state = ?, payment_intent = ? "
                        "WHERE case_id = ?",
                        (session_id, amount, currency, "PAID",
                         payment_intent, case_id))
                else:
                    conn.execute(
                        "INSERT INTO stripe_cases (case_id, session_id, "
                        "amount, currency, state, payment_intent) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (case_id, session_id, amount, currency, "PAID",
                         payment_intent))
            if own:
                conn.commit()
            return "FULFILLED"
        finally:
            if own:
                conn.close()

    def record_subscription_renewal(self, invoice, db=None):
        """Record an invoice.paid object durably (subscription renewal).

        Idempotent by invoice id: repeating the same invoice returns
        'ALREADY_RECORDED'. A later invoice for the same subscription
        updates the row (last_invoice_id / amount / period end). Same
        transaction rules as fulfill_checkout: no commit when ``db`` is
        given. Raises PaymentDenied when the invoice has no subscription
        id or malformed amounts, so the webhook does not acknowledge a
        renewal it could not record.
        """
        if not isinstance(invoice, dict):
            raise PaymentDenied("Invalid invoice object")
        invoice_id = self._require_str(invoice, "id")
        subscription_id = self._require_str(invoice, "subscription")
        amount_paid = self._require_amount(invoice, "amount_paid")
        currency = self._require_currency(invoice)
        status = invoice.get("status")
        if not isinstance(status, str) or not status:
            raise PaymentDenied("Invalid status in invoice object")
        customer = invoice.get("customer")
        if customer is not None and not isinstance(customer, str):
            raise PaymentDenied("Invalid customer in invoice object")
        metadata = invoice.get("metadata")
        case_id = (metadata.get("case_id") if isinstance(metadata, dict)
                   else None)
        period_end = invoice.get("period_end")
        if period_end is None:
            try:
                period_end = invoice["lines"]["data"][0]["period"]["end"]
            except (KeyError, IndexError, TypeError):
                period_end = None
        if period_end is not None and type(period_end) is not int:
            raise PaymentDenied("Invalid period_end in invoice object")

        own = db is None
        conn = db if db is not None else self._connect()
        try:
            self._ensure_tables(conn)
            row = conn.execute(
                "SELECT last_invoice_id FROM stripe_subscriptions "
                "WHERE subscription_id = ?", (subscription_id,)).fetchone()
            if row is not None and row[0] == invoice_id:
                return "ALREADY_RECORDED"
            conn.execute(
                "INSERT INTO stripe_subscriptions (subscription_id, "
                "customer_id, case_id, status, current_period_end, "
                "last_invoice_id, amount_paid, currency, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(subscription_id) DO UPDATE SET "
                "customer_id = excluded.customer_id, "
                "case_id = excluded.case_id, status = excluded.status, "
                "current_period_end = excluded.current_period_end, "
                "last_invoice_id = excluded.last_invoice_id, "
                "amount_paid = excluded.amount_paid, "
                "currency = excluded.currency, "
                "updated_at = excluded.updated_at",
                (subscription_id, customer, case_id, status, period_end,
                 invoice_id, amount_paid, currency, int(time.time())))
            if own:
                conn.commit()
            return "RECORDED"
        finally:
            if own:
                conn.close()

    def process_reversal(self, charge, db=None):
        """Record a charge.refunded object durably (reversal / refund).

        One row per charge, keyed by charge id, holding the cumulative
        refunded amount: repeating the same refund returns
        'ALREADY_PROCESSED'; a larger cumulative amount updates the row
        ('UPDATED'). When the charge's payment_intent matches a PAID case,
        the case state becomes REFUNDED (fully refunded) or
        PARTIALLY_REFUNDED. Same transaction rules as fulfill_checkout.
        Raises PaymentDenied on malformed charge data.
        """
        if not isinstance(charge, dict):
            raise PaymentDenied("Invalid charge object")
        charge_id = self._require_str(charge, "id")
        amount_refunded = self._require_amount(charge, "amount_refunded")
        currency = charge.get("currency")
        if currency is not None:
            currency = self._require_currency(charge)
        payment_intent = charge.get("payment_intent")
        if payment_intent is not None and not isinstance(payment_intent, str):
            raise PaymentDenied("Invalid payment_intent in charge object")
        amount = charge.get("amount")
        if amount is not None and type(amount) is not int:
            raise PaymentDenied("Invalid amount in charge object")
        refund_ids = []
        try:
            for refund in charge.get("refunds", {}).get("data", []):
                if isinstance(refund, dict) and isinstance(
                        refund.get("id"), str):
                    refund_ids.append(refund["id"])
        except AttributeError:
            raise PaymentDenied("Invalid refunds in charge object")
        if amount is not None and amount_refunded >= amount:
            status = "refunded"
        elif amount_refunded > 0:
            status = "partially_refunded"
        else:
            status = "recorded"
        clock = int(time.time())

        own = db is None
        conn = db if db is not None else self._connect()
        try:
            self._ensure_tables(conn)
            row = conn.execute(
                "SELECT amount_refunded FROM stripe_reversals "
                "WHERE charge_id = ?", (charge_id,)).fetchone()
            if row is not None and row[0] == amount_refunded:
                return "ALREADY_PROCESSED"
            if row is not None:
                conn.execute(
                    "UPDATE stripe_reversals SET amount_refunded = ?, "
                    "status = ?, refund_ids = ?, updated_at = ? "
                    "WHERE charge_id = ?",
                    (amount_refunded, status, json.dumps(refund_ids),
                     clock, charge_id))
                result = "UPDATED"
            else:
                conn.execute(
                    "INSERT INTO stripe_reversals (charge_id, "
                    "payment_intent, amount_refunded, currency, status, "
                    "refund_ids, recorded_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (charge_id, payment_intent, amount_refunded, currency,
                     status, json.dumps(refund_ids), clock, clock))
                result = "REVERSED"
            if payment_intent:
                case_row = conn.execute(
                    "SELECT case_id, amount, state FROM stripe_cases "
                    "WHERE payment_intent = ?", (payment_intent,)).fetchone()
                if case_row is None:
                    event_row = conn.execute(
                        "SELECT case_id FROM stripe_events "
                        "WHERE payment_id = ? ORDER BY recorded_at DESC "
                        "LIMIT 1", (payment_intent,)).fetchone()
                    if event_row is not None:
                        case_row = conn.execute(
                            "SELECT case_id, amount, state FROM stripe_cases "
                            "WHERE case_id = ?", (event_row[0],)).fetchone()
                if case_row is not None and case_row[2] in (
                        "PAID", "PARTIALLY_REFUNDED"):
                    new_state = ("REFUNDED" if amount_refunded >= case_row[1]
                                 else "PARTIALLY_REFUNDED")
                    conn.execute(
                        "UPDATE stripe_cases SET state = ? WHERE case_id = ?",
                        (new_state, case_row[0]))
            if own:
                conn.commit()
            return result
        finally:
            if own:
                conn.close()

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
