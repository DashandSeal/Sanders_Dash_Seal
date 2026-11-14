"""P0 unified-branch route tests: single WSGI entry serves the site.

Covers the routes the simultaneous-branch Phase 1 verification found
missing (GET / 404, /api/voice/* 404, /api/daedalus/describe 404):
- GET / serves the real web/index.html on loopback and canonical hosts.
- GET /healthz is 200; GET /readyz is 503 fail-closed (no verifier).
- P2 (2026-11-13): voice/Daedalus are WIRED now, so the old honest-503
  expectations changed: GET /api/voice/status is a real 200 (null
  backends, no keys), GET /api/daedalus/describe is a real 200 with
  fully_active false, and GET /voice.html serves the real page.
  Transcribe/speak/turn still answer honest 503s naming the missing
  backend/runtime -- never a fake 200.

Fake providers only: no keys, no network, no live calls. Run from the
repo root with the venv that has stripe:

    ~/workspace/.venv-simultaneous/bin/python -m unittest discover -s tests -v
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


def call(app, method, path, host="127.0.0.1:8000", body=b""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8000",
        "HTTP_HOST": host,
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.errors": io.StringIO(),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    status = {}

    def start_response(code, response_headers):
        status["code"] = code
        status["headers"] = dict(response_headers)

    chunks = app(environ, start_response)
    return status["code"], status["headers"], b"".join(chunks)


class TestUnifiedRoutes(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application

        self.app = create_application()

    def test_home_serves_index_on_loopback(self):
        code, headers, body = call(self.app, "GET", "/")
        self.assertTrue(code.startswith("200"), code)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"Sanders Dash", body)

    def test_home_serves_index_on_canonical_host(self):
        code, _, body = call(
            self.app, "GET", "/", host="sandersdashandseal.com"
        )
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"Sanders Dash", body)


    def test_voice_status_is_real_200_with_no_backends(self):
        # P2: the voice API is wired; with no key/package configured the
        # status endpoint honestly reports null backends (200), while
        # transcribe/speak still 503 (see below).
        code, _, body = call(self.app, "GET", "/api/voice/status")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertIsNone(payload["transcriber"])
        self.assertIsNone(payload["synthesizer"])
        self.assertIs(payload["live_calls"], False)

    def test_voice_transcribe_is_honest_503_without_backend(self):
        code, _, body = call(self.app, "POST", "/api/voice/transcribe")
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"transcriber_not_configured", body)

    def test_voice_turn_is_honest_503_without_runtime(self):
        code, _, body = call(self.app, "POST", "/api/voice/turn")
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"daedalus_runtime_not_configured", body)

    def test_daedalus_describe_is_real_200_not_active(self):
        # P2: the real Daedalus engine reports its capabilities; no key
        # is configured, so fully_active is false (never a fake 200).
        code, _, body = call(self.app, "GET", "/api/daedalus/describe")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertEqual(payload["engine"], "DAEDALUS")
        self.assertIs(payload["fully_active"], False)

    def test_voice_html_serves_real_page(self):
        # P2: web/voice.html exists on this branch now.
        code, headers, body = call(self.app, "GET", "/voice.html")
        self.assertTrue(code.startswith("200"), code)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"Voice", body)

    def test_session_api_reaches_customer_app_not_redirect_or_404(self):
        # /api/session is a customer API path: on the canonical host it
        # must reach customer_app (503 fail-closed with no verifier),
        # never the old 308 self-redirect; on loopback never a 404.
        code, _, body = call(
            self.app, "GET", "/api/session", host="sandersdashandseal.com"
        )
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"appointments_unavailable", body)
        code, _, _ = call(self.app, "GET", "/api/session")
        self.assertTrue(code.startswith("503"), code)


FAKE_SECRET = "whsec_test_p0_fake_secret_0123456789abcdef"


def signed_event(event_id, event_type):
    payload = json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "livemode": True,
            "data": {"object": {"id": "cs_test_1"}},
        }
    ).encode()
    ts = int(time.time())
    sig = hmac.new(
        FAKE_SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={ts},v1={sig}"


class FreshLedger:
    """Ledger like wsgi.py's MockLedgerEngine: bare sqlite3.connect, no DDL."""

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


class TestFreshLedgerWebhook(unittest.TestCase):
    """Regression: a signed webhook against a FRESH ledger.db (no tables)
    must settle 200. Before the fix the SELECT on stripe_processed_events
    raised 'no such table' and every first webhook 500d, because only the
    test helper created the table -- production code never did."""

    def test_signed_event_settles_on_fresh_db(self):
        from core_platform.stream_api import import_make_app

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "ledger.db")
            ledger = FreshLedger(db_path)
            app = import_make_app(
                ledger_engine=ledger,
                webhook_secret=FAKE_SECRET,
                enabled=True,
                expected_livemode=True,
                live_verified=True,  # tests simulate a verified-live config
            )
            payload, header = signed_event(
                "evt_p0_fresh_1", "checkout.session.completed"
            )
            environ = {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/v1/payments/stripe/webhook",
                "SERVER_NAME": "127.0.0.1",
                "SERVER_PORT": "8000",
                "HTTP_HOST": "127.0.0.1:8000",
                "HTTP_STRIPE_SIGNATURE": header,
                "wsgi.input": io.BytesIO(payload),
                "CONTENT_LENGTH": str(len(payload)),
                "CONTENT_TYPE": "application/json",
                "wsgi.errors": io.StringIO(),
                "wsgi.version": (1, 0),
                "wsgi.url_scheme": "http",
                "wsgi.multithread": False,
                "wsgi.multiprocess": False,
                "wsgi.run_once": False,
            }
            status = {}

            def start_response(code, headers):
                status["code"] = code

            chunks = app(environ, start_response)
            body = b"".join(chunks)
            self.assertTrue(
                status["code"].startswith("200"), (status["code"], body)
            )
            self.assertIn(b"LEDGER_SETTLED", body)
            self.assertEqual(ledger.calls, [("fulfill_checkout", "cs_test_1")])
            # The table must now exist in the fresh db.
            with sqlite3.connect(db_path) as db:
                rows = db.execute(
                    "SELECT id FROM stripe_processed_events"
                ).fetchall()
            self.assertEqual(rows, [("evt_p0_fresh_1",)])


if __name__ == "__main__":
    unittest.main()
