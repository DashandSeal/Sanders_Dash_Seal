"""P2 wiring tests: AI-platform links + approvals + services, voice,
realtime/video, free-first and global modules wired into the real WSGI
entry (deploy/deployment.py).

Fakes only: no keys, no network, no live calls. All 9 approval gates
are UNAPPROVED, so every live provider path must fail honestly.
Run from the repo root with the venv that has stripe:

    ~/workspace/.venv-simultaneous/bin/python -m unittest discover -s tests -v
"""

import io
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def call(app, method, path, host="127.0.0.1:8000", body=b"",
         headers=None, query=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
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
    if headers:
        environ.update(headers)
    status = {}

    def start_response(code, response_headers):
        status["code"] = code
        status["headers"] = dict(response_headers)

    chunks = app(environ, start_response)
    return status["code"], status["headers"], b"".join(chunks)


class TestPlatformStatusEndpoint(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_status_reports_links_approvals_services_global(self):
        code, _, body = call(
            self.app, "GET", "/api/platform/status",
            headers={"HTTP_ACCEPT_LANGUAGE": "es-ES, es;q=0.9, en;q=0.8"})
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        # Global wiring: UTC timestamp, negotiated locale, translated title.
        self.assertIn("generated_at_utc", payload)
        self.assertTrue(payload["generated_at_utc"].endswith("Z"))
        self.assertEqual(payload["locale"], "es")
        self.assertEqual(payload["title"], "Sanders Dash & Seal")
        # Link registry: 6 LINKED / 2 MISSING_KEY / 1 NOT_IMPLEMENTED / 0 BROKEN.
        links = payload["platform_links"]
        self.assertEqual(
            sorted(pid for pid, s in links.items() if s["status"] == "LINKED"),
            ["ai_role_workers", "bozly", "grantwriter",
             "minotaur_sentinel", "sharpshooter", "twingate"])
        self.assertEqual(
            sorted(pid for pid, s in links.items() if s["status"] == "MISSING_KEY"),
            ["daedalus", "stream_api"])
        self.assertEqual(
            payload["platform_link_summary"]["counts"]["NOT_IMPLEMENTED"], 1)
        self.assertEqual(
            payload["platform_link_summary"]["counts"]["BROKEN"], 0)
        # Approvals: all 9 gates UNAPPROVED.
        self.assertEqual(len(payload["approvals"]), 9)
        self.assertTrue(all(
            row["status"] == "UNAPPROVED" for row in payload["approvals"]))
        # Services: 19 linking rows, all MISSING_KEY with no env.
        self.assertEqual(payload["service_links"]["rows"], 19)
        self.assertEqual(
            payload["service_links"]["by_live_status"], {"MISSING_KEY": 19})
        # Global regions from env: us-phoenix-1 primary.
        self.assertEqual(
            payload["regions"]["primary_region"], "us-phoenix-1")
        # Payments: currency resolved from Accept-Language (es-ES -> EUR).
        self.assertEqual(payload["payments"]["currency"], "EUR")
        self.assertEqual(payload["payments"]["currency_source"], "accept_language")
        self.assertEqual(payload["payments"]["live_gate"], "TEST_MODE")
        # Voice backends: none available without keys/packages.
        self.assertFalse(
            payload["voice_backends"]["faster-whisper"]["available"])
        # Free-first ordering present: local/offline defaults first.
        self.assertEqual(
            payload["free_first"]["stt"]["default_free_provider"],
            "faster-whisper-local")
        self.assertEqual(
            payload["free_first"]["tts"]["default_free_provider"],
            "system-tts-pyttsx3")
        self.assertIs(payload["free_first"]["stt"]["paid_opt_in"], False)
        # No section failed to load.
        self.assertEqual(
            [k for k in payload if k.endswith("_error")], [])

    def test_status_defaults_to_en_and_unresolvable_currency(self):
        code, _, body = call(self.app, "GET", "/api/platform/status")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertEqual(payload["locale"], "en")
        self.assertIsNone(payload["payments"]["currency"])
        self.assertIn("currency_note", payload["payments"])

    def test_status_is_read_only(self):
        code, _, _ = call(self.app, "POST", "/api/platform/status")
        self.assertTrue(code.startswith("405"), code)


class TestPaymentsCurrencyRoute(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_explicit_currency_wins(self):
        code, _, body = call(self.app, "GET", "/api/payments/currency",
                             query="currency=EUR")
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertEqual(payload["currency"], "EUR")
        self.assertEqual(payload["source"], "explicit_choice")

    def test_accept_language_resolves_currency(self):
        code, _, body = call(
            self.app, "GET", "/api/payments/currency",
            headers={"HTTP_ACCEPT_LANGUAGE": "es-MX"})
        self.assertTrue(code.startswith("200"), code)
        self.assertEqual(json.loads(body)["currency"], "MXN")

    def test_unresolvable_currency_is_honest_400(self):
        code, _, body = call(self.app, "GET", "/api/payments/currency")
        self.assertTrue(code.startswith("400"), code)
        self.assertIn(b"currency_unresolvable", body)


class TestRealtimeRoutes(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_realtime_status_reports_no_provider(self):
        for path in ("/api/realtime/status", "/api/video/status"):
            code, _, body = call(self.app, "GET", path)
            self.assertTrue(code.startswith("200"), code)
            payload = json.loads(body)
            self.assertEqual(payload["provider"], "none")
            self.assertIs(payload["livekit_configured"], False)

    def test_room_without_provider_is_honest_503(self):
        code, _, body = call(
            self.app, "POST", "/api/realtime/room",
            body=json.dumps({"room": "test-room"}).encode())
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"not_configured", body)

    def test_token_without_provider_is_honest_503(self):
        code, _, body = call(
            self.app, "POST", "/api/realtime/token",
            body=json.dumps(
                {"room": "test-room", "identity": "alice"}).encode())
        self.assertTrue(code.startswith("503"), code)
        self.assertIn(b"not_configured", body)

    def test_signaling_validation_rejects_bad_token(self):
        code, _, body = call(
            self.app, "POST", "/api/realtime/signaling/validate",
            body=json.dumps({
                "session_id": "s1", "token": "bad",
                "message": {"type": "offer", "sdp": "x"}}).encode())
        self.assertTrue(code.startswith("400"), code)

    def test_video_page_and_scripts_serve(self):
        for path, needle in (
                ("/video.html", b"Video"),
                ("/daedalus_voice.js", b"voice"),
                ("/video.js", b"video")):
            code, headers, body = call(self.app, "GET", path)
            self.assertTrue(code.startswith("200"), code)
            self.assertIn(needle, body)


class TestGlobalResponseWiring(unittest.TestCase):
    def setUp(self):
        from deploy.deployment import create_application
        self.app = create_application()

    def test_healthz_and_free_resources_carry_utc_timestamps(self):
        for path in ("/healthz", "/api/platform/free-resources"):
            code, _, body = call(self.app, "GET", path)
            self.assertTrue(code.startswith("200"), code)
            payload = json.loads(body)
            self.assertTrue(
                payload["generated_at_utc"].endswith("Z"), path)

    def test_free_resources_catalog_has_six_resources(self):
        _, _, body = call(self.app, "GET", "/api/platform/free-resources")
        payload = json.loads(body)
        self.assertEqual(len(payload["resources"]), 6)
        self.assertEqual(
            payload["resources"][2]["id"], "oracle-object-storage")
        self.assertEqual(
            payload["resources"][2]["allowances"]["total_gb"], 10)

    def test_home_advertises_negotiated_content_language(self):
        _, headers, _ = call(
            self.app, "GET", "/",
            headers={"HTTP_ACCEPT_LANGUAGE": "es-MX, es;q=0.9"})
        self.assertEqual(headers.get("Content-Language"), "es")


class TestApprovalGating(unittest.TestCase):
    def test_voice_video_provider_gate_is_unapproved(self):
        from deploy.deployment import _is_approved
        self.assertIs(_is_approved("voice_video_provider"), False)
        self.assertIs(_is_approved("daedalus_live"), False)
        self.assertIs(_is_approved("no_such_gate"), False)

    def test_unknown_gate_never_approves(self):
        from core_platform.ai_platform_approval import is_approved
        with self.assertRaises(ValueError):
            is_approved("no_such_gate")


class TestComposeConvergence(unittest.TestCase):
    def test_compose_yaml_uses_shared_ledger_volume(self):
        # P2 convergence: compose.yaml (canonical for installer) now uses
        # the same sds-ledger-volume as docker-compose.yml, so the two
        # stacks no longer keep separate ledger data.
        text = (REPO_ROOT / "compose.yaml").read_text()
        self.assertIn("sds-ledger-volume:/app/data", text)
        self.assertIn("name: sds_production_ledger_data", text)
        self.assertNotIn("sqlite_storage", text)
        legacy = (REPO_ROOT / "docker-compose.yml").read_text()
        self.assertIn("sds-ledger-volume:/app/data", legacy)
        # Neither load-bearing compose file was deleted.
        self.assertTrue((REPO_ROOT / "docker-compose.yml").exists())


if __name__ == "__main__":
    unittest.main()
