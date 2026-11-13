"""Bozly CFO live-wiring tests: verified events reach the CFO ledger.

Fake providers only: a fake Stripe webhook secret, fake Bozly route
config, temp SQLite databases. No live keys, no live Stripe calls,
no network.

- A signature-verified webhook is recorded by Bozly (RECORDED, then
  DUPLICATE on replay) and reconciled.
- An unverified webhook (bad/missing signature) answers 401 and is
  NEVER recorded by Bozly.
- With Bozly unconfigured the webhook still settles 200 and reports
  bozly not_configured honestly.
- /api/bozly/status and /api/platform/status report Bozly honestly
  and never return a secret value, a file path, or traceback detail.
"""

import hashlib
import hmac
import io
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAKE_SECRET = "whsec_test_bozly_live_not_a_real_secret"
FAKE_ROUTES = {
    "main": {
        "entity_id": "sanders_home_healthcare",
        "jurisdiction": "Wisconsin",
        "signing_secret": "whsec_test_route_not_a_real_secret",
    }
}


def signed_event(event_id, event_type, livemode=False, obj=None):
    """Build (payload bytes, Stripe-Signature header) for a fake event."""
    payload = json.dumps({
        "id": event_id,
        "type": event_type,
        "livemode": livemode,
        "created": 1700000000,
        "data": {"object": obj if obj is not None else {"id": "cs_test_1"}},
    }).encode()
    ts = int(time.time())
    sig = hmac.new(
        FAKE_SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={ts},v1={sig}"


def call(app, method, path, body=b"", headers=None, host="sandersdashandseal.com"):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": host,
        "SERVER_PORT": "8000",
        "HTTP_HOST": host,
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "QUERY_STRING": "",
        "wsgi.errors": io.StringIO(),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    for key, value in (headers or {}).items():
        environ[key] = value
    status = {}

    def start_response(code, response_headers):
        status["code"] = code
        status["headers"] = dict(response_headers)

    chunks = app(environ, start_response)
    return status["code"], b"".join(chunks)


def make_webhook_app(tmp, routes=True):
    """Webhook app with a real PaymentLedger and a Bozly recorder."""
    from core_platform.stripe_payments import PaymentLedger
    from core_platform.stream_api import import_make_app
    from core_platform.bozly_wiring import BozlyRecorder

    class Engine:
        def __init__(self, db_path):
            self.db_path = db_path
            self._ledger = PaymentLedger(db_path)

        def connect(self):
            return sqlite3.connect(self.db_path, timeout=15)

        def fulfill_checkout(self, session, db):
            return self._ledger.fulfill_checkout(session, db)

        def record_subscription_renewal(self, invoice, db):
            return self._ledger.record_subscription_renewal(invoice, db)

        def process_reversal(self, charge, db):
            return self._ledger.process_reversal(charge, db)

    env = {}
    if routes:
        env["BOZLY_STRIPE_ROUTES_JSON"] = json.dumps(FAKE_ROUTES)
    with mock.patch.dict(os.environ, env, clear=False):
        recorder = BozlyRecorder(db_path=str(Path(tmp) / "bozly_ledger.db"))
        app = import_make_app(
            ledger_engine=Engine(str(Path(tmp) / "ledger.db")),
            webhook_secret=FAKE_SECRET,
            enabled=True,
            expected_livemode=False,
            live_verified=False,
            bozly_recorder=recorder,
        )
    return app, recorder


def bozly_rows(tmp):
    with sqlite3.connect(str(Path(tmp) / "bozly_ledger.db")) as db:
        inbox = db.execute("SELECT event_id FROM stripe_inbox").fetchall()
        queue = db.execute(
            "SELECT event_id, status FROM reconcile_queue").fetchall()
    return inbox, queue


class TestBozlyLiveWiring(unittest.TestCase):
    def test_verified_event_is_recorded_by_bozly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {
                    "BOZLY_STRIPE_ROUTES_JSON": json.dumps(FAKE_ROUTES)}):
                app, _ = make_webhook_app(tmp, routes=True)
                payload, header = signed_event(
                    "evt_bozly_live_1", "checkout.session.completed",
                    obj={"id": "cs_1", "payment_status": "paid",
                         "amount_total": 1000, "currency": "usd",
                         "payment_intent": "pi_1",
                         "client_reference_id": "case-1"})
                code, body = call(app, "POST", "/v1/payments/stripe/webhook",
                                  payload, {"HTTP_STRIPE_SIGNATURE": header})
                self.assertTrue(code.startswith("200"), body)
                self.assertIn(b"LEDGER_SETTLED", body)
                data = json.loads(body)
                self.assertEqual(data["bozly"]["status"], "RECORDED")
                inbox, queue = bozly_rows(tmp)
                self.assertEqual(len(inbox), 1)
                self.assertEqual(inbox[0][0], "evt_bozly_live_1")
                self.assertEqual(queue[0][1], "RECONCILED_OBSERVATION")

    def test_replay_is_duplicate_in_bozly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {
                    "BOZLY_STRIPE_ROUTES_JSON": json.dumps(FAKE_ROUTES)}):
                app, _ = make_webhook_app(tmp, routes=True)
                payload, header = signed_event(
                    "evt_bozly_live_2", "checkout.session.completed",
                    obj={"id": "cs_2", "payment_status": "paid",
                         "amount_total": 1000, "currency": "usd",
                         "payment_intent": "pi_2",
                         "client_reference_id": "case-1"})
                headers = {"HTTP_STRIPE_SIGNATURE": header}
                code, _ = call(app, "POST", "/v1/payments/stripe/webhook",
                               payload, headers)
                self.assertTrue(code.startswith("200"), code)
                code, body = call(app, "POST", "/v1/payments/stripe/webhook",
                                  payload, headers)
                self.assertTrue(code.startswith("200"), body)
                self.assertIn(b"SUCCESS_ALREADY_PROCESSED", body)
                inbox, _ = bozly_rows(tmp)
                self.assertEqual(len(inbox), 1)

    def test_unverified_event_is_never_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {
                    "BOZLY_STRIPE_ROUTES_JSON": json.dumps(FAKE_ROUTES)}):
                app, _ = make_webhook_app(tmp, routes=True)
                payload, _ = signed_event(
                    "evt_bozly_live_3", "checkout.session.completed",
                    obj={"id": "cs_3", "payment_status": "paid",
                         "amount_total": 1000, "currency": "usd",
                         "payment_intent": "pi_3",
                         "client_reference_id": "case-1"})
                code, body = call(
                    app, "POST", "/v1/payments/stripe/webhook", payload,
                    {"HTTP_STRIPE_SIGNATURE": "t=1,v1=" + "0" * 64})
                self.assertTrue(code.startswith("401"), body)
                code, body = call(app, "POST", "/v1/payments/stripe/webhook",
                                  payload, {})
                self.assertTrue(code.startswith("401"), body)
                self.assertFalse((Path(tmp) / "bozly_ledger.db").exists())

    def test_bozly_unconfigured_webhook_still_settles(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items()
                   if k not in ("BOZLY_STRIPE_ROUTES_JSON", "BOZLY_ROUTE_ID")}
            with mock.patch.dict(os.environ, env, clear=True):
                app, _ = make_webhook_app(tmp, routes=False)
                payload, header = signed_event(
                    "evt_bozly_live_4", "checkout.session.completed",
                    obj={"id": "cs_4", "payment_status": "paid",
                         "amount_total": 1000, "currency": "usd",
                         "payment_intent": "pi_4",
                         "client_reference_id": "case-1"})
                code, body = call(app, "POST", "/v1/payments/stripe/webhook",
                                  payload, {"HTTP_STRIPE_SIGNATURE": header})
                self.assertTrue(code.startswith("200"), body)
                self.assertIn(b"LEDGER_SETTLED", body)
                data = json.loads(body)
                self.assertEqual(data["bozly"]["status"], "not_configured")

    def test_bozly_status_is_honest_and_secret_free(self):
        from core_platform.bozly_wiring import bozly_status
        env = {k: v for k, v in os.environ.items()
               if k not in ("BOZLY_STRIPE_ROUTES_JSON", "BOZLY_ROUTE_ID",
                            "BOZLY_DB_PATH")}
        with mock.patch.dict(os.environ, env, clear=True):
            status = bozly_status()
            self.assertFalse(status["configured"])
            self.assertFalse(status["live"])
            self.assertFalse(status["keys_configured"])
            self.assertNotIn("whsec_test_route_not_a_real_secret",
                             json.dumps(status))
        with mock.patch.dict(os.environ, {
                "BOZLY_STRIPE_ROUTES_JSON": json.dumps(FAKE_ROUTES)}):
            status = bozly_status()
            self.assertTrue(status["configured"])
            self.assertTrue(status["live"])
            self.assertEqual(status["routes_configured"], 1)
            self.assertEqual(status["route_ids"], ["main"])
            dumped = json.dumps(status)
            self.assertNotIn("whsec_test_route_not_a_real_secret", dumped)
            self.assertNotIn("traceback", dumped.lower())

    def test_deployment_bozly_status_routes(self):
        from deploy.deployment import create_application
        env = {k: v for k, v in os.environ.items()
               if k not in ("BOZLY_STRIPE_ROUTES_JSON", "BOZLY_ROUTE_ID",
                            "BOZLY_DB_PATH")}
        with mock.patch.dict(os.environ, env, clear=True):
            app = create_application()
            code, body = call(app, "GET", "/api/bozly/status",
                              host="localhost")
            self.assertTrue(code.startswith("200"), body)
            data = json.loads(body)
            self.assertFalse(data["configured"])
            self.assertFalse(data["live"])
            self.assertNotIn("whsec_test_route_not_a_real_secret",
                             json.dumps(data))
            code, body = call(app, "GET", "/api/platform/status",
                              host="localhost")
            self.assertTrue(code.startswith("200"), body)
            data = json.loads(body)
            self.assertIn("bozly", data)
            self.assertFalse(data["bozly"]["configured"])


if __name__ == "__main__":
    unittest.main()
