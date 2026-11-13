"""P3 LiveKit tests: canonical choice + cross-module interop (fakes only).

No network, no keys, no live peer. Proves the P3 LiveKit decision in
``docs/LIVEKIT_CANONICAL.md``:

* ``livekit_realtime.py`` is canonical; ``livekit_video.py`` is retained
  and imports its JWT helpers from it (single implementation).
* Tokens issued by either module validate/decode under the other (same
  LiveKit wire format, same secret).
* The differences that make a full merge unsafe are pinned: identity
  charset (``@``), TTL floor, and return shape.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FAKE_KEY = "AP_fake_livekit_key"
FAKE_SECRET = "fake-livekit-secret-for-tests-only"
FAKE_URL = "https://livekit.example.invalid"
NOW = 1_700_000_000


class TestLiveKitCanonicalHelpers(unittest.TestCase):
    def test_jwt_helpers_are_one_implementation(self):
        from core_platform import livekit_realtime, livekit_video

        # livekit_video imports these from livekit_realtime (P3): the
        # crypto is implemented once, not duplicated.
        self.assertIs(livekit_video._b64url, livekit_realtime._b64url)
        self.assertIs(livekit_video._b64url_decode, livekit_realtime._b64url_decode)

    def test_canonical_doc_names_both_modules_and_why_merge_is_unsafe(self):
        doc = (REPO_ROOT / "docs" / "LIVEKIT_CANONICAL.md").read_text()
        self.assertIn("livekit_realtime.py", doc)
        self.assertIn("livekit_video.py", doc)
        self.assertIn("unsafe", doc)
        self.assertIn("canonical", doc.lower())


class TestLiveKitCrossModuleInterop(unittest.TestCase):
    def test_realtime_token_validates_under_video_validator(self):
        from core_platform.livekit_realtime import issue_access_token
        from core_platform.livekit_video import validate_room_token

        token = issue_access_token(
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            room="room-a", identity="alice", ttl_seconds=3600, now=NOW)
        checked = validate_room_token(
            token, api_secret=FAKE_SECRET, now=NOW + 100)
        self.assertTrue(checked["valid"])
        self.assertEqual(checked["room"], "room-a")
        self.assertEqual(checked["identity"], "alice")
        self.assertEqual(checked["expires_at"], NOW + 3600)

    def test_video_token_decodes_under_realtime_decoder(self):
        from core_platform.livekit_realtime import _decode_jwt_payload
        from core_platform.livekit_video import issue_room_token

        issued = issue_room_token(
            room="room-b", identity="bob", url=FAKE_URL,
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            ttl_seconds=3600, now=NOW)
        payload = _decode_jwt_payload(issued["token"])
        self.assertEqual(payload["iss"], FAKE_KEY)
        self.assertEqual(payload["sub"], "bob")
        self.assertEqual(payload["video"]["room"], "room-b")
        self.assertTrue(payload["video"]["roomJoin"])
        self.assertEqual(payload["exp"], NOW + 3600)
        self.assertEqual(issued["expires_at"], NOW + 3600)

    def test_wrong_secret_fails_cross_module_validation(self):
        from core_platform.livekit_realtime import issue_access_token
        from core_platform.livekit_video import validate_room_token

        token = issue_access_token(
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            room="room-a", identity="alice", ttl_seconds=3600, now=NOW)
        with self.assertRaises(ValueError):
            validate_room_token(token, api_secret="different-secret", now=NOW + 10)


class TestLiveKitDifferencesPinned(unittest.TestCase):
    def test_identity_at_allowed_by_video_rejected_by_realtime(self):
        # The concrete incompatibility that blocks a full merge: video
        # allows email-style identities, realtime follows the
        # signalling contract (worker/src/webrtc.js) and does not.
        from core_platform.livekit_realtime import issue_access_token
        from core_platform.livekit_video import issue_room_token

        issued = issue_room_token(
            room="room-c", identity="user@example", url=FAKE_URL,
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            ttl_seconds=3600, now=NOW)
        self.assertEqual(issued["identity"], "user@example")
        with self.assertRaises(ValueError):
            issue_access_token(
                api_key=FAKE_KEY, api_secret=FAKE_SECRET,
                room="room-c", identity="user@example",
                ttl_seconds=3600, now=NOW)

    def test_ttl_floor_differs(self):
        # Realtime accepts 1..86400; video requires 60..86400.
        from core_platform.livekit_realtime import issue_access_token
        from core_platform.livekit_video import issue_room_token

        token = issue_access_token(
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            room="room-d", identity="alice", ttl_seconds=30, now=NOW)
        self.assertIsInstance(token, str)
        with self.assertRaises(ValueError):
            issue_room_token(
                room="room-d", identity="alice", url=FAKE_URL,
                api_key=FAKE_KEY, api_secret=FAKE_SECRET,
                ttl_seconds=30, now=NOW)
        issued = issue_room_token(
            room="room-d", identity="alice", url=FAKE_URL,
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            ttl_seconds=60, now=NOW)
        self.assertEqual(issued["expires_at"], NOW + 60)

    def test_return_shapes_differ(self):
        # Realtime issues a bare JWT str; video issues a dict.
        from core_platform.livekit_realtime import issue_access_token
        from core_platform.livekit_video import issue_room_token

        token = issue_access_token(
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            room="room-e", identity="alice", ttl_seconds=3600, now=NOW)
        self.assertIsInstance(token, str)
        self.assertEqual(token.count("."), 2)
        issued = issue_room_token(
            room="room-e", identity="alice", url=FAKE_URL,
            api_key=FAKE_KEY, api_secret=FAKE_SECRET,
            ttl_seconds=3600, now=NOW)
        self.assertIsInstance(issued, dict)
        self.assertEqual(issued["token"].count("."), 2)
        self.assertEqual(issued["url"], FAKE_URL)


if __name__ == "__main__":
    unittest.main()
