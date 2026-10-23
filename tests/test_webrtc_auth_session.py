import os
import tempfile
import unittest
from unittest.mock import patch
from backend.auth_session import (issue_webrtc_access_token,
    validate_worker_token_request, revoke_webrtc_access_token)

class TestWebRTCAuthorization(unittest.TestCase):
    def test_room_token_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SQLITE_DB_PATH": os.path.join(tmp,"auth.db")}):
            token=issue_webrtc_access_token("notary","room-1",ttl_minutes=5)
            self.assertEqual(len(token),64)
            valid=validate_worker_token_request(token)
            self.assertTrue(valid["isValid"])
            self.assertEqual(valid["session"]["assigned_session_id"],"room-1")
            self.assertEqual(valid["session"]["notary_session_ids"],["room-1"])
            self.assertFalse(validate_worker_token_request("invalid")["isValid"])
            self.assertTrue(revoke_webrtc_access_token(token))
            self.assertFalse(validate_worker_token_request(token)["isValid"])

    def test_reject_invalid_lifetime(self):
        with self.assertRaises(ValueError):
            issue_webrtc_access_token("notary","room-1",ttl_minutes=0)
