"""Tests for core_platform.realtime_api (WSGI, fakes only; no network)."""

import io
import json
import secrets
import unittest

from core_platform.livekit_realtime import _decode_jwt_payload
from core_platform.realtime_api import create_realtime_app, create_realtime_app_with_fakes


def call(app, method, path, body=None):
    raw = b"" if body is None else json.dumps(body).encode()
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "CONTENT_TYPE": "application/json",
        "wsgi.input": io.BytesIO(raw),
    }
    captured = {}
    def start(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    chunks = app(environ, start)
    payload = b"".join(chunks)
    try:
        data = json.loads(payload.decode())
    except (ValueError, UnicodeDecodeError):
        data = {"_raw": payload.decode("utf-8", "replace")}
    return captured["status"], data


class TestRealtimeApi(unittest.TestCase):
    def setUp(self):
        self.app = create_realtime_app_with_fakes()
        self.empty_app = create_realtime_app(platform_env={})

    def test_status_reports_no_provider_when_empty(self):
        status, data = call(self.empty_app, "GET", "/api/realtime/status")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(data["provider"], "none")
        self.assertFalse(data["livekit_configured"])
        self.assertTrue(data["signalling_server_required"])

    def test_video_status_alias(self):
        status, data = call(self.empty_app, "GET", "/api/video/status")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(data["provider"], "none")

    def test_platform_status_lists_every_platform(self):
        status, data = call(self.empty_app, "GET", "/api/platform/status")
        self.assertTrue(status.startswith("200"))
        for key in ("stripe", "oracle", "dns", "github_gateway", "google", "realtime"):
            self.assertIn(key, data, key)
        # P2 adaptation: the ledger handlers are real SQLite-backed
        # methods since P1 (2026-11-13), not stubs.
        self.assertIn("real since the P1 pass", data["ledger_stub_warning"])

    def test_create_room_with_fake_transport(self):
        status, data = call(self.app, "POST", "/api/realtime/room", {"room": "room-1"})
        self.assertTrue(status.startswith("200"))
        self.assertEqual(data["room"]["name"], "room-1")
        self.assertEqual(data["provider"], "livekit")

    def test_create_room_unconfigured_is_honest_503(self):
        status, data = call(self.empty_app, "POST", "/api/realtime/room", {"room": "room-1"})
        self.assertTrue(status.startswith("503"))
        self.assertEqual(data["error"], "not_configured")

    def test_create_room_rejects_bad_name(self):
        status, data = call(self.app, "POST", "/api/realtime/room", {"room": "bad name!"})
        self.assertTrue(status.startswith("400"))

    def test_create_room_unknown_provider(self):
        status, data = call(self.app, "POST", "/api/realtime/room", {"room": "room-1", "provider": "nope"})
        self.assertTrue(status.startswith("400"))

    def test_issue_token_with_fake_client(self):
        status, data = call(self.app, "POST", "/api/realtime/token", {"room": "room-2", "identity": "bob"})
        self.assertTrue(status.startswith("200"))
        payload = _decode_jwt_payload(data["token"])
        self.assertEqual(payload["sub"], "bob")
        self.assertEqual(payload["video"]["room"], "room-2")

    def test_issue_token_unconfigured_is_honest_503(self):
        status, data = call(self.empty_app, "POST", "/api/realtime/token", {"room": "room-2", "identity": "bob"})
        self.assertTrue(status.startswith("503"))
        self.assertEqual(data["error"], "not_configured")

    def test_signaling_validate_accepts_offer_and_rejects_bad_action(self):
        token = secrets.token_hex(32)
        good = {"session_id": "s1", "token": token, "message": {
            "action": "offer", "targetSessionId": "s1", "sdp": {"type": "offer", "sdp": "v=0"}}}
        status, data = call(self.app, "POST", "/api/realtime/signaling/validate", good)
        self.assertTrue(status.startswith("200"))
        self.assertTrue(data["valid"])
        self.assertEqual(data["frame"]["action"], "offer")
        bad = {"session_id": "s1", "token": token, "message": {"action": "hangup", "targetSessionId": "s1"}}
        status, data = call(self.app, "POST", "/api/realtime/signaling/validate", bad)
        self.assertTrue(status.startswith("400"))

    def test_signaling_validate_rejects_bad_token(self):
        body = {"session_id": "s1", "token": "not-a-token", "message": {
            "action": "offer", "targetSessionId": "s1", "sdp": {"type": "offer", "sdp": "v=0"}}}
        status, _ = call(self.app, "POST", "/api/realtime/signaling/validate", body)
        self.assertTrue(status.startswith("400"))

    def test_unknown_route_is_404(self):
        status, data = call(self.app, "GET", "/api/nope")
        self.assertTrue(status.startswith("404"))


if __name__ == "__main__":
    unittest.main()
