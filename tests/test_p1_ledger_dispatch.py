"""P1 ledger-dispatch tests: stream_api.py must fail closed (503) when the
injected ledger engine lacks the method for the event type, instead of
raising AttributeError and returning 500.

PaymentLedger (core_platform/stripe_payments.py) now implements the three
methods for real (SQLite-backed, idempotent), so the ledger test below
expects settlement; only an engine without the methods still gets 503.

Fake providers only: fake webhook secret, local HMAC signatures, temp
SQLite files. No live keys, no live Stripe calls.
"""

import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from test_p1_wsgi import FakeLedger, call, make_event_table, signed_event


class ConnectOnlyLedger:
    """A ledger engine with connect() but none of the dispatch methods."""

    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)


def make_app(ledger):
    from core_platform.stream_api import import_make_app
    from test_p1_wsgi import FAKE_SECRET

    return import_make_app(
        ledger_engine=ledger,
        webhook_secret=FAKE_SECRET,
        enabled=True,
        expected_livemode=True,
        live_verified=True,  # tests simulate a verified-live config
    )


def post_event(app, event_id, event_type, obj=None):
    payload, header = signed_event(event_id, event_type, obj=obj)
    return call(
        app,
        "POST",
        "/v1/payments/stripe/webhook",
        payload,
        {"HTTP_STRIPE_SIGNATURE": header},
    )


CHECKOUT_OBJ = {
    "id": "cs_test_1",
    "client_reference_id": "case-1",
    "amount_total": 5000,
    "currency": "usd",
    "payment_intent": "pi_1",
    "payment_status": "paid",
}
INVOICE_OBJ = {
    "id": "in_1",
    "subscription": "sub_1",
    "customer": "cus_1",
    "amount_paid": 2000,
    "currency": "usd",
    "status": "paid",
    "period_end": 1893456000,
}
CHARGE_OBJ = {
    "id": "ch_1",
    "payment_intent": "pi_1",
    "amount": 5000,
    "amount_refunded": 5000,
    "currency": "usd",
    "refunded": True,
    "refunds": {"data": [{"id": "re_1"}]},
}


class TestLedgerDispatchFailsClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        make_event_table(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _processed_ids(self):
        with sqlite3.connect(self.db_path) as db:
            return [
                row[0]
                for row in db.execute(
                    "SELECT id FROM stripe_processed_events"
                ).fetchall()
            ]

    def test_ledger_without_method_returns_503_not_500(self):
        app = make_app(ConnectOnlyLedger(self.db_path))
        code, body = post_event(app, "evt_1", "checkout.session.completed")
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"ledger_method_unavailable", body)
        self.assertIn(b"fulfill_checkout", body)
        # The event must NOT be recorded as settled.
        self.assertEqual(self._processed_ids(), [])

    def test_payment_ledger_settles_all_three_for_real(self):
        """PaymentLedger now implements the methods: verified events settle
        200 and are recorded durably (not 503 ledger_method_unavailable)."""
        from core_platform.stripe_payments import PaymentLedger

        ledger = PaymentLedger(self.db_path)
        self.assertTrue(callable(ledger.fulfill_checkout))
        self.assertTrue(callable(ledger.record_subscription_renewal))
        self.assertTrue(callable(ledger.process_reversal))
        ledger.register_checkout("case-1", "cs_test_1", 5000, "usd")
        app = make_app(ledger)
        for event_type, obj in (
            ("checkout.session.completed", CHECKOUT_OBJ),
            ("invoice.paid", INVOICE_OBJ),
            ("charge.refunded", CHARGE_OBJ),
        ):
            code, body = post_event(app, f"evt_{event_type}", event_type, obj)
            self.assertTrue(code.startswith("200"), (code, body))
            self.assertIn(b"LEDGER_SETTLED", body)
        self.assertEqual(
            sorted(self._processed_ids()),
            ["evt_charge.refunded", "evt_checkout.session.completed",
             "evt_invoice.paid"],
        )
        # Durable effects: checkout settled the case, refund marked it.
        self.assertEqual(ledger.status("case-1"), "REFUNDED")

    def test_ledger_with_method_still_settles(self):
        # Control test: the guard must not break the working path.
        ledger = FakeLedger(self.db_path)
        app = make_app(ledger)
        code, body = post_event(app, "evt_1", "checkout.session.completed")
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"LEDGER_SETTLED", body)
        self.assertEqual(self._processed_ids(), ["evt_1"])


if __name__ == "__main__":
    unittest.main()
