"""Tests for core_platform.livekit_realtime (fakes only; no network, no keys)."""

import base64
import hashlib
import hmac
import json
import unittest

from core_platform.livekit_realtime import (
    DailyClient,
    FakeRoomService,
    LiveKitClient,
    RealtimeConfig,
    RealtimeNotConfigured,
    RealtimeUnavailable,
    _decode_jwt_payload,
    issue_access_token,
    screen_share_requirements,
    validate_identity,
    validate_room_name,
)


def _verify_hs256(token, secret):
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = (header_b64 + "." + payload_b64).encode("ascii")
    expected = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, sig_b64)


class TestValidation(unittest.TestCase):
    def test_room_and_identity_accept_contract_shapes(self):
        self.assertEqual(validate_room_name("session-1"), "session-1")
        self.assertEqual(validate_identity("user_1.2"), "user_1.2")

    def test_room_and_identity_reject_bad_shapes(self):
        for bad in ("", "a" * 129, "room with spaces", "room/slash", None, 42):
            with self.assertRaises(ValueError, msg=repr(bad)):
                validate_room_name(bad)
            with self.assertRaises(ValueError, msg=repr(bad)):
                validate_identity(bad)


class TestAccessToken(unittest.TestCase):
    def test_token_is_signed_jwt_scoped_to_one_room_and_identity(self):
        token = issue_access_token(
            api_key="APtestkey", api_secret="s3cret", room="room-1",
            identity="alice", ttl_seconds=600, now=1700000000,
        )
        self.assertTrue(_verify_hs256(token, "s3cret"))
        payload = _decode_jwt_payload(token)
        self.assertEqual(payload["iss"], "APtestkey")
        self.assertEqual(payload["sub"], "alice")
        self.assertEqual(payload["video"]["room"], "room-1")
        self.assertTrue(payload["video"]["roomJoin"])
        self.assertEqual(payload["exp"], 1700000600)
        self.assertEqual(payload["iat"], 1700000000)

    def test_token_rejects_missing_key_or_secret(self):
        with self.assertRaises(RealtimeNotConfigured):
            issue_access_token(api_key="", api_secret="x", room="r", identity="i")
        with self.assertRaises(RealtimeNotConfigured):
            issue_access_token(api_key="k", api_secret="", room="r", identity="i")

    def test_token_rejects_bad_room_identity_ttl(self):
        with self.assertRaises(ValueError):
            issue_access_token(api_key="k", api_secret="s", room="bad room", identity="i")
        with self.assertRaises(ValueError):
            issue_access_token(api_key="k", api_secret="s", room="r", identity="i", ttl_seconds=0)
        with self.assertRaises(ValueError):
            issue_access_token(api_key="k", api_secret="s", room="r", identity="i", ttl_seconds=90000)


class TestLiveKitClient(unittest.TestCase):
    def test_room_crud_against_fake_transport(self):
        fake = FakeRoomService()
        client = LiveKitClient(url="https://lk.example.invalid", api_key="APk",
                               api_secret="sec", transport=fake)
        room = client.create_room("room-1")
        self.assertEqual(room["name"], "room-1")
        self.assertEqual([r["name"] for r in client.list_rooms()], ["room-1"])
        self.assertTrue(client.delete_room("room-1"))
        self.assertEqual(client.list_rooms(), [])
        self.assertFalse(client.delete_room("room-1"))

    def test_unconfigured_client_refuses_to_fabricate_a_room(self):
        client = LiveKitClient()
        with self.assertRaises(RealtimeNotConfigured):
            client.create_room("room-1")
        with self.assertRaises(RealtimeNotConfigured):
            client.issue_token(room="room-1", identity="alice")

    def test_configured_client_without_transport_reports_unavailable(self):
        client = LiveKitClient(url="https://lk.example.invalid", api_key="APk", api_secret="sec")
        with self.assertRaises(RealtimeUnavailable):
            client.create_room("room-1")

    def test_room_url_requires_url(self):
        client = LiveKitClient(url="https://lk.example.invalid/", api_key="k", api_secret="s")
        self.assertEqual(client.room_url("room-1"), "https://lk.example.invalid/room/room-1")
        with self.assertRaises(RealtimeNotConfigured):
            LiveKitClient().room_url("room-1")


class TestDailyClient(unittest.TestCase):
    def test_fake_room_create_and_url(self):
        fake = FakeRoomService()
        client = DailyClient(api_key="daily-key", domain="sanders", transport=fake)
        room = client.create_room("room-9")
        self.assertEqual(room["provider"], "daily")
        self.assertEqual(room["domain"], "sanders")
        self.assertEqual(client.room_url("room-9"), "https://sanders.daily.co/room-9")

    def test_unconfigured_daily_refuses(self):
        with self.assertRaises(RealtimeNotConfigured):
            DailyClient().create_room("room-9")

    def test_pricing_constants_match_brief(self):
        self.assertEqual(DailyClient.FREE_MINUTES, 10_000)
        self.assertEqual(DailyClient.PRICE_PER_PARTICIPANT_MINUTE_USD, 0.004)


class TestConfig(unittest.TestCase):
    def test_provider_selection_prefers_livekit(self):
        env = {"LIVEKIT_URL": "https://lk.example.invalid", "LIVEKIT_API_KEY": "k",
               "LIVEKIT_API_SECRET": "s", "DAILY_API_KEY": "d", "DAILY_DOMAIN": "x"}
        self.assertEqual(RealtimeConfig.from_env(env).provider, "livekit")
        self.assertEqual(RealtimeConfig.from_env({"DAILY_API_KEY": "d", "DAILY_DOMAIN": "x"}).provider, "daily")
        self.assertEqual(RealtimeConfig.from_env({}).provider, "none")

    def test_status_reports_presence_only_never_values(self):
        env = {"LIVEKIT_URL": "https://lk.example.invalid", "LIVEKIT_API_KEY": "SECRETKEYVALUE",
               "LIVEKIT_API_SECRET": "SECRETSECRETVALUE"}
        status = RealtimeConfig.from_env(env).status()
        blob = json.dumps(status)
        self.assertNotIn("SECRETKEYVALUE", blob)
        self.assertNotIn("SECRETSECRETVALUE", blob)
        self.assertTrue(status["livekit_configured"])
        self.assertTrue(status["signalling_server_required"])

    def test_screen_share_contract(self):
        reqs = screen_share_requirements()
        self.assertEqual(reqs["api"], "navigator.mediaDevices.getDisplayMedia")
        self.assertTrue(reqs["video_only"])
        self.assertIn("web/video.js", reqs["implemented_in"])


if __name__ == "__main__":
    unittest.main()
