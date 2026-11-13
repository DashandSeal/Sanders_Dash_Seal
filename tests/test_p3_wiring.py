"""P3 wiring tests: per-event webhook currency, RON route gating,
global_connectivity callers, and the stale-doc fixes.

Fakes only: a fake Stripe webhook secret, a fake ledger, and
stripe.Webhook.construct_event verifying a locally computed HMAC
signature. No live keys, no live Stripe calls, no network.
Run from the repo root with the venv that has stripe:

    ~/workspace/.venv-simultaneous/bin/python -m unittest discover -s tests -v
"""

import hashlib
import hmac
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAKE_SECRET = "whsec_test_p3_wiring_only"


def signed_event(event_id, event_type, livemode=False, obj=None):
    """Build (payload bytes, Stripe-Signature header) for a fake event."""
    payload = json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "livemode": livemode,
            "data": {"object": obj if obj is not None else {"id": "cs_test_1"}},
        }
    ).encode()
    ts = int(time.time())
    sig = hmac.new(
        FAKE_SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={ts},v1={sig}"


def call(app, method, path, body=b"", headers=None, query=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8000",
        "HTTP_HOST": "127.0.0.1:8000",
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


class TestWebhookPerEventCurrency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        make_event_table(self.db_path)
        self.ledger = FakeLedger(self.db_path)
        from core_platform.stream_api import import_make_app

        # Test mode (expected_livemode=False), the default.
        self.app = import_make_app(
            ledger_engine=self.ledger,
            webhook_secret=FAKE_SECRET,
            enabled=True,
            expected_livemode=False,
            live_verified=False,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _post(self, event_id, event_type, obj=None):
        payload, sig = signed_event(event_id, event_type, livemode=False, obj=obj)
        return call(
            self.app, "POST", "/v1/payments/stripe/webhook", payload,
            headers={"HTTP_STRIPE_SIGNATURE": sig})

    def test_checkout_with_valid_currency_settles_and_reports_it(self):
        code, body = self._post(
            "evt_p3_1", "checkout.session.completed",
            {"id": "cs_1", "amount_total": 5000, "currency": "usd"})
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"LEDGER_SETTLED", body)
        self.assertIn(b'"currency":"USD"', body)
        self.assertIn(("fulfill_checkout", "cs_1"), self.ledger.calls)

    def test_checkout_with_unsupported_currency_is_400_and_not_settled(self):
        code, body = self._post(
            "evt_p3_2", "checkout.session.completed",
            {"id": "cs_2", "amount_total": 5000, "currency": "xxx"})
        self.assertTrue(code.startswith("400"), code)
        self.assertIn(b"webhook_currency_or_amount_mismatch", body)
        self.assertNotIn(("fulfill_checkout", "cs_2"), self.ledger.calls)

    def test_checkout_with_string_amount_is_400(self):
        code, body = self._post(
            "evt_p3_3", "checkout.session.completed",
            {"id": "cs_3", "amount_total": "5000", "currency": "usd"})
        self.assertTrue(code.startswith("400"), code)
        self.assertIn(b"webhook_currency_or_amount_mismatch", body)

    def test_checkout_without_money_fields_still_settles_legacy_shape(self):
        # The legacy/test shape {"id": ...} carries no amount or
        # currency, so there is nothing to validate; it proceeds as
        # before (P1 tests depend on this).
        code, body = self._post("evt_p3_4", "checkout.session.completed")
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"LEDGER_SETTLED", body)
        self.assertIn(b'"currency":null', body)

    def test_invoice_paid_with_eur_settles(self):
        code, body = self._post(
            "evt_p3_5", "invoice.paid",
            {"id": "in_1", "amount_paid": 2500, "currency": "eur"})
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b'"currency":"EUR"', body)
        self.assertIn(("record_subscription_renewal", "in_1"), self.ledger.calls)

    def test_charge_refunded_currency_only_check(self):
        code, body = self._post(
            "evt_p3_6", "charge.refunded",
            {"id": "ch_1", "amount_refunded": 1000, "currency": "gbp"})
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b'"currency":"GBP"', body)
        self.assertIn(("process_reversal", "ch_1"), self.ledger.calls)
        code, body = self._post(
            "evt_p3_7", "charge.refunded",
            {"id": "ch_2", "amount_refunded": 1000, "currency": "zzz"})
        self.assertTrue(code.startswith("400"), code)
        self.assertIn(b"webhook_currency_or_amount_mismatch", body)
        self.assertNotIn(("process_reversal", "ch_2"), self.ledger.calls)

    def test_non_money_event_type_is_recorded_not_currency_validated(self):
        code, body = self._post(
            "evt_p3_8", "customer.created",
            {"id": "cus_1", "currency": "not-a-currency"})
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"LEDGER_SETTLED", body)

    def test_replay_of_valid_event_keeps_earlier_verdict(self):
        self._post("evt_p3_9", "checkout.session.completed",
                   {"id": "cs_9", "amount_total": 100, "currency": "usd"})
        code, body = self._post("evt_p3_9", "checkout.session.completed",
                                {"id": "cs_9", "amount_total": 100, "currency": "usd"})
        self.assertTrue(code.startswith("200"), code)
        self.assertIn(b"SUCCESS_ALREADY_PROCESSED", body)


class TestRonRoute(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_ron_denied_for_every_jurisdiction_by_default(self):
        for query in ("jurisdiction=CO", "jurisdiction=WI", "jurisdiction=FL",
                      "jurisdiction=XX", ""):
            code, body = call(
                self.app, "GET", "/api/compliance/ron", query=query)
            self.assertTrue(code.startswith("403"), (query, code))
            self.assertIn(b"NOT_APPROVED_IN_JURISDICTION", body)
            payload = json.loads(body)
            self.assertEqual(payload["approved_jurisdictions"], [])

    def test_ron_route_is_read_only(self):
        code, _ = call(self.app, "POST", "/api/compliance/ron",
                       query="jurisdiction=CO")
        self.assertTrue(code.startswith("405"), code)

    def test_platform_status_reports_ron_fail_closed(self):
        code, body = call(self.app, "GET", "/api/platform/status")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertEqual(payload["ron"]["gate"], "fail_closed")
        self.assertEqual(payload["ron"]["approved_jurisdictions"], [])


class TestConnectivityCaller(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_platform_status_reports_connectivity_policies(self):
        code, body = call(self.app, "GET", "/api/platform/status")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        conn = payload["connectivity"]
        self.assertEqual(conn["region"], "us")
        # Policy values come from the real policy table, not the route.
        self.assertEqual(conn["policies"]["daedalus"]["timeout_seconds"], 45.0)
        self.assertEqual(conn["policies"]["livekit"]["timeout_seconds"], 10.0)
        self.assertEqual(conn["policies"]["livekit"]["max_retries"], 3)
        self.assertIn("offline_fallback", conn["policies"]["openai"])
        self.assertIn("declared only", conn["note"])

    def test_connectivity_backoff_is_pure_and_deterministic(self):
        from core_platform.global_connectivity import backoff_seconds
        self.assertEqual(backoff_seconds(1, base=1.0, cap=8.0), 1.0)
        self.assertEqual(backoff_seconds(4, base=1.0, cap=8.0), 8.0)


class TestP3DocFixes(unittest.TestCase):
    def test_ledger_docs_name_converged_volume(self):
        for name in ("docs/LEDGER_BACKUPS.md", "docs/LIVE_VERIFICATION.md"):
            text = (REPO_ROOT / name).read_text()
            # The stale volume reference must be gone; the old name may
            # still appear once inside the dated correction note that
            # records what it used to say.
            self.assertNotIn("sqlite_storage:/app/data", text, name)
            self.assertIn("sds-ledger-volume:/app/data", text, name)
            self.assertIn("sds_production_ledger_data", text, name)

    def test_catalog_doc_states_six_resources(self):
        text = (REPO_ROOT / "docs" / "OCI_FREE_RESOURCE_MAPPING.md").read_text()
        self.assertIn("holds **6 resources**", text)
        self.assertIn("NoSQL; catalog date\n> 2026-11-13", text)

    def test_gitignore_ignores_data_dir_and_env_and_db(self):
        def check(path):
            proc = subprocess.run(
                ["git", "check-ignore", "-v", path],
                cwd=str(REPO_ROOT), capture_output=True, text=True)
            return proc.returncode == 0

        self.assertTrue(check("data/foo.txt"))
        self.assertTrue(check("data/ledger.db"))
        self.assertTrue(check(".env"))
        self.assertTrue(check("foo.db"))
        self.assertFalse(check("wsgi.py"))
        self.assertFalse(check("x.pbd.json"))

    def test_platform_link_checklist_exists_and_gateway_ref_resolves(self):
        from core_platform.platform_services import gateway_status

        doc = REPO_ROOT / "docs" / "platform-link-checklist-20261113.md"
        self.assertTrue(doc.exists(), "checklist doc must exist")
        text = doc.read_text()
        self.assertIn("GitHub", text)
        self.assertIn("exit 128", text)
        self.assertIn("docs/platform-link-checklist-20261113.md",
                      gateway_status()["fix"])


if __name__ == "__main__":
    unittest.main()
