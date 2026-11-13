"""P1 ledger-method tests: PaymentLedger.fulfill_checkout /
record_subscription_renewal / process_reversal are real SQLite-backed
methods (durable, idempotent), not pass stubs.

Fake Stripe events only, temp SQLite files. No live keys, no live Stripe
calls, no network.

Run from the repo root with the venv that has stripe:

    ~/workspace/.venv-simultaneous/bin/python -m unittest discover -s tests -v
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core_platform.stripe_payments import PaymentDenied, PaymentLedger


def checkout(case="case-1", session="cs_1", amount=5000, **over):
    obj = {
        "id": session,
        "client_reference_id": case,
        "amount_total": amount,
        "currency": "usd",
        "payment_intent": "pi_1",
        "payment_status": "paid",
    }
    obj.update(over)
    return obj


def invoice(inv="in_1", sub="sub_1", amount=2000, **over):
    obj = {
        "id": inv,
        "subscription": sub,
        "customer": "cus_1",
        "amount_paid": amount,
        "currency": "usd",
        "status": "paid",
        "period_end": 1893456000,
    }
    obj.update(over)
    return obj


def charge(ch="ch_1", refunded=5000, amount=5000, **over):
    obj = {
        "id": ch,
        "payment_intent": "pi_1",
        "amount": amount,
        "amount_refunded": refunded,
        "currency": "usd",
        "refunded": refunded >= amount,
        "refunds": {"data": [{"id": "re_1"}]},
    }
    obj.update(over)
    return obj


class TestFulfillCheckout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        self.ledger = PaymentLedger(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_registered_case_settles_to_paid(self):
        self.ledger.register_checkout("case-1", "cs_1", 5000, "usd")
        self.assertEqual(self.ledger.status("case-1"), "PENDING")
        result = self.ledger.fulfill_checkout(checkout())
        self.assertEqual(result, "FULFILLED")
        self.assertEqual(self.ledger.status("case-1"), "PAID")

    def test_second_fulfill_is_idempotent(self):
        self.ledger.register_checkout("case-1", "cs_1", 5000, "usd")
        self.assertEqual(self.ledger.fulfill_checkout(checkout()), "FULFILLED")
        self.assertEqual(
            self.ledger.fulfill_checkout(checkout()), "ALREADY_FULFILLED")
        self.assertEqual(self.ledger.status("case-1"), "PAID")

    def test_unregistered_case_is_recorded_paid_from_event(self):
        result = self.ledger.fulfill_checkout(checkout())
        self.assertEqual(result, "FULFILLED")
        self.assertEqual(self.ledger.status("case-1"), "PAID")

    def test_amount_mismatch_raises_and_does_not_settle(self):
        self.ledger.register_checkout("case-1", "cs_1", 5000, "usd")
        with self.assertRaises(PaymentDenied):
            self.ledger.fulfill_checkout(checkout(amount=9999))
        self.assertEqual(self.ledger.status("case-1"), "PENDING")

    def test_unpaid_session_raises(self):
        with self.assertRaises(PaymentDenied):
            self.ledger.fulfill_checkout(checkout(payment_status="unpaid"))

    def test_missing_case_id_raises(self):
        obj = checkout()
        del obj["client_reference_id"]
        with self.assertRaises(PaymentDenied):
            self.ledger.fulfill_checkout(obj)

    def test_works_with_passed_connection_and_without(self):
        # With an explicit connection (the webhook path): no commit by
        # the method; the caller commits.
        with self.ledger.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            result = self.ledger.fulfill_checkout(checkout(), db)
            self.assertEqual(result, "FULFILLED")
            db.commit()
        self.assertEqual(self.ledger.status("case-1"), "PAID")
        # Without one (direct call): the method commits itself.
        self.assertEqual(
            self.ledger.fulfill_checkout(checkout(case="case-2",
                                                 session="cs_2",
                                                 payment_intent="pi_2")),
            "FULFILLED")
        self.assertEqual(self.ledger.status("case-2"), "PAID")


class TestRecordSubscriptionRenewal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        self.ledger = PaymentLedger(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _row(self, sub="sub_1"):
        with sqlite3.connect(self.db_path) as db:
            return db.execute(
                "SELECT status, last_invoice_id, amount_paid, "
                "current_period_end FROM stripe_subscriptions "
                "WHERE subscription_id = ?", (sub,)).fetchone()

    def test_first_renewal_recorded(self):
        self.assertEqual(
            self.ledger.record_subscription_renewal(invoice()), "RECORDED")
        self.assertEqual(self._row(), ("paid", "in_1", 2000, 1893456000))

    def test_same_invoice_is_idempotent(self):
        self.assertEqual(
            self.ledger.record_subscription_renewal(invoice()), "RECORDED")
        self.assertEqual(
            self.ledger.record_subscription_renewal(invoice()),
            "ALREADY_RECORDED")
        self.assertEqual(self._row(), ("paid", "in_1", 2000, 1893456000))

    def test_later_invoice_updates_subscription(self):
        self.ledger.record_subscription_renewal(invoice())
        self.assertEqual(
            self.ledger.record_subscription_renewal(
                invoice(inv="in_2", amount=2500, period_end=1896048000)),
            "RECORDED")
        self.assertEqual(self._row(), ("paid", "in_2", 2500, 1896048000))

    def test_missing_subscription_raises(self):
        obj = invoice()
        del obj["subscription"]
        with self.assertRaises(PaymentDenied):
            self.ledger.record_subscription_renewal(obj)


class TestProcessReversal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        self.ledger = PaymentLedger(self.db_path)
        self.ledger.register_checkout("case-1", "cs_1", 5000, "usd")
        self.ledger.fulfill_checkout(checkout())

    def tearDown(self):
        self.tmp.cleanup()

    def _row(self, ch="ch_1"):
        with sqlite3.connect(self.db_path) as db:
            return db.execute(
                "SELECT amount_refunded, status, refund_ids "
                "FROM stripe_reversals WHERE charge_id = ?",
                (ch,)).fetchone()

    def test_full_refund_marks_case_refunded(self):
        self.assertEqual(self.ledger.process_reversal(charge()), "REVERSED")
        row = self._row()
        self.assertEqual(row[0], 5000)
        self.assertEqual(row[1], "refunded")
        self.assertEqual(json.loads(row[2]), ["re_1"])
        self.assertEqual(self.ledger.status("case-1"), "REFUNDED")

    def test_same_refund_is_idempotent(self):
        self.assertEqual(self.ledger.process_reversal(charge()), "REVERSED")
        self.assertEqual(
            self.ledger.process_reversal(charge()), "ALREADY_PROCESSED")
        self.assertEqual(self.ledger.status("case-1"), "REFUNDED")

    def test_partial_then_full_refund_updates(self):
        self.assertEqual(
            self.ledger.process_reversal(charge(refunded=2000)), "REVERSED")
        self.assertEqual(self.ledger.status("case-1"), "PARTIALLY_REFUNDED")
        self.assertEqual(
            self.ledger.process_reversal(charge(refunded=5000)), "UPDATED")
        self.assertEqual(self._row()[1], "refunded")
        self.assertEqual(self.ledger.status("case-1"), "REFUNDED")

    def test_malformed_charge_raises(self):
        with self.assertRaises(PaymentDenied):
            self.ledger.process_reversal({"id": "ch_1"})
        with self.assertRaises(PaymentDenied):
            self.ledger.process_reversal(charge(amount_refunded=-1))


class TestMockLedgerEngineDelegates(unittest.TestCase):
    """wsgi.MockLedgerEngine (the runtime engine) delegates the three
    methods to PaymentLedger. Runs in a subprocess because importing wsgi
    builds the app at module level (needs STRIPE_WEBHOOK_SECRET)."""

    _SCRIPT = (
        "import json, os, sqlite3, sys, tempfile\n"
        "sys.path.insert(0, os.getcwd())\n"
        "from wsgi import MockLedgerEngine\n"
        "tmp = tempfile.mkdtemp()\n"
        "db = os.path.join(tmp, 'ledger.db')\n"
        "eng = MockLedgerEngine(db)\n"
        "from core_platform.stripe_payments import PaymentLedger\n"
        "PaymentLedger(db).register_checkout('case-1', 'cs_1', 5000, 'usd')\n"
        "with eng.connect() as c:\n"
        "    c.execute('BEGIN IMMEDIATE')\n"
        "    r1 = eng.fulfill_checkout({'id': 'cs_1', 'client_reference_id': 'case-1', 'amount_total': 5000, 'currency': 'usd', 'payment_intent': 'pi_1', 'payment_status': 'paid'}, c)\n"
        "    r2 = eng.record_subscription_renewal({'id': 'in_1', 'subscription': 'sub_1', 'customer': 'cus_1', 'amount_paid': 2000, 'currency': 'usd', 'status': 'paid', 'period_end': 1893456000}, c)\n"
        "    r3 = eng.process_reversal({'id': 'ch_1', 'payment_intent': 'pi_1', 'amount': 5000, 'amount_refunded': 5000, 'currency': 'usd', 'refunded': True, 'refunds': {'data': [{'id': 're_1'}]}}, c)\n"
        "    c.execute('INSERT INTO stripe_processed_events (id, type, processed_at) VALUES (?, ?, ?)', ('evt_1', 'checkout.session.completed', 1))\n"
        "    c.commit()\n"
        "with sqlite3.connect(db) as c:\n"
        "    state = c.execute(\"SELECT state FROM stripe_cases WHERE case_id='case-1'\").fetchone()[0]\n"
        "print(json.dumps({'r1': r1, 'r2': r2, 'r3': r3, 'state': state}))\n"
    )

    def setUp(self):
        self._data_dir = REPO_ROOT / "data"
        self._data_existed = self._data_dir.exists()

    def tearDown(self):
        # Importing wsgi builds the app, which creates repo/data/; remove
        # it only if this test created it, never a pre-existing ledger.
        if not self._data_existed and self._data_dir.exists():
            import shutil
            shutil.rmtree(self._data_dir, ignore_errors=True)

    def test_delegation_settles_all_three(self):
        from test_p1_wsgi import FAKE_SECRET

        env = dict(os.environ)
        env["STRIPE_WEBHOOK_SECRET"] = FAKE_SECRET
        env.pop("STRIPE_LIVEMODE", None)
        env.pop("STRIPE_LIVE_VERIFIED", None)
        proc = subprocess.run(
            [sys.executable, "-c", self._SCRIPT],
            cwd=str(REPO_ROOT), env=env,
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result, {
            "r1": "FULFILLED", "r2": "RECORDED", "r3": "REVERSED",
            "state": "REFUNDED",
        })


if __name__ == "__main__":
    unittest.main()
