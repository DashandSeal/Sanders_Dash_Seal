"""P1 WSGI entry tests: the repaired composition root and webhook gateway.

Fake providers only: a fake Stripe webhook secret, a fake ledger, and
stripe.Webhook.construct_event verifying a locally computed HMAC signature.
No live keys, no live Stripe calls, no network.

Run from the repo root with the venv that has stripe:

    ~/workspace/sds-p0-work/venv/bin/python -m unittest discover -s tests -v
"""

import hashlib
import hmac
import io
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAKE_SECRET = "whsec_test_p1_fake_secret_0123456789abcdef"


def signed_event(event_id, event_type, object_id="cs_test_1", livemode=True,
                 obj=None):
    """Build (payload bytes, Stripe-Signature header) for a fake event."""
    payload = json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "livemode": livemode,
            "data": {"object": obj if obj is not None else {"id": object_id}},
        }
    ).encode()
    ts = int(time.time())
    sig = hmac.new(
        FAKE_SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={ts},v1={sig}"


def call(app, method, path, body=b"", headers=None):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "sandersdashandseal.com",
        "SERVER_PORT": "8000",
        "HTTP_HOST": "sandersdashandseal.com",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
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


def make_event_table(db_path):
    with sqlite3.connect(db_path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS stripe_processed_events "
            "(id TEXT PRIMARY KEY, type TEXT, processed_at INTEGER)"
        )


class FakeLedger:
    """Ledger with the three dispatch methods, backed by a temp SQLite file."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.calls = []

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def fulfill_checkout(self, session, db):
        self.calls.append(("fulfill_checkout", session.get("id")))

    def record_subscription_renewal(self, invoice, db):
        self.calls.append(("record_subscription_renewal", invoice.get("id")))

    def process_reversal(self, charge, db):
        self.calls.append(("process_reversal", charge.get("id")))


class TestDiagnosticApp(unittest.TestCase):
    def test_healthz_200_readyz_503_stream_503(self):
        from deploy.deployment import create_application

        app = create_application()
        code, _ = call(app, "GET", "/healthz")
        self.assertTrue(code.startswith("200"), code)
        code, body = call(app, "GET", "/readyz")
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"service_ready", body)
        code, _ = call(app, "POST", "/api/stream/transactions", b"{}")
        self.assertTrue(code.startswith("503"), code)


class TestWebhookGateway(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        make_event_table(self.db_path)
        self.ledger = FakeLedger(self.db_path)
        from core_platform.stream_api import import_make_app

        self.app = import_make_app(
            ledger_engine=self.ledger,
            webhook_secret=FAKE_SECRET,
            enabled=True,
            expected_livemode=True,
            live_verified=True,  # tests simulate a verified-live config
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_is_405(self):
        code, body = call(self.app, "GET", "/v1/payments/stripe/webhook")
        self.assertTrue(code.startswith("405"), code)
        self.assertIn(b"post_required", body)

    def test_post_without_signature_is_401(self):
        payload, _ = signed_event("evt_1", "checkout.session.completed")
        code, body = call(
            self.app, "POST", "/v1/payments/stripe/webhook", payload
        )
        self.assertTrue(code.startswith("401"), code)
        self.assertIn(b"missing_stripe_signature_header", body)

    def test_post_with_bad_signature_is_401(self):
        payload, _ = signed_event("evt_1", "checkout.session.completed")
        code, body = call(
            self.app,
            "POST",
            "/v1/payments/stripe/webhook",
            payload,
            {"HTTP_STRIPE_SIGNATURE": "t=1,v1=deadbeef"},
        )
        self.assertTrue(code.startswith("401"), code)
        self.assertIn(b"invalid_cryptographic_signature", body)

    def test_valid_checkout_settles_and_replay_is_idempotent(self):
        payload, header = signed_event(
            "evt_test_1", "checkout.session.completed"
        )
        code, body = call(
            self.app,
            "POST",
            "/v1/payments/stripe/webhook",
            payload,
            {"HTTP_STRIPE_SIGNATURE": header},
        )
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"LEDGER_SETTLED", body)
        self.assertEqual(self.ledger.calls, [("fulfill_checkout", "cs_test_1")])
        # Replay of the same event id must not run the ledger twice.
        code, body = call(
            self.app,
            "POST",
            "/v1/payments/stripe/webhook",
            payload,
            {"HTTP_STRIPE_SIGNATURE": header},
        )
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"SUCCESS_ALREADY_PROCESSED", body)
        self.assertEqual(len(self.ledger.calls), 1)

    def test_valid_invoice_and_refund_dispatch(self):
        for event_type, method in (
            ("invoice.paid", "record_subscription_renewal"),
            ("charge.refunded", "process_reversal"),
        ):
            payload, header = signed_event(
                f"evt_{event_type}", event_type, object_id="obj_1"
            )
            code, body = call(
                self.app,
                "POST",
                "/v1/payments/stripe/webhook",
                payload,
                {"HTTP_STRIPE_SIGNATURE": header},
            )
            self.assertTrue(code.startswith("200"), code)
            self.assertIn(b"LEDGER_SETTLED", body)
        self.assertEqual(
            [c[0] for c in self.ledger.calls],
            ["record_subscription_renewal", "process_reversal"],
        )


if __name__ == "__main__":
    unittest.main()
