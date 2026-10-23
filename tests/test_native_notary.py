import tempfile
import unittest
from pathlib import Path

from core_platform.native_notary import NativeNotarySessions, NativeNotaryDenied


class NativeNotaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "native.db"
        self.sessions = NativeNotarySessions(self.path)

    def test_enotary_persists_and_cancels(self):
        created = self.sessions.create("session-1", "case-1", "E_NOTARY", "CO")
        self.assertEqual(created["state"], "AWAITING_AUTHORITY")
        restored = NativeNotarySessions(self.path).get("session-1")
        self.assertEqual(restored["case_id"], "case-1")
        self.assertEqual(self.sessions.cancel("session-1")["state"], "CANCELLED")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.cancel("session-1")

    def test_ron_is_separate_and_duplicate_denied(self):
        self.sessions.create("session-2", "case-2", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-2", "case-3", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-3", "case-3", "MOBILE_NOTARY", "WI")

    def test_no_unverified_completion(self):
        self.sessions.create("session-4", "case-4", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete("session-4", human_attestation=True,
                                   authority_evidence=True, identity_evidence=True,
                                   act_evidence=True)
        self.assertEqual(self.sessions.get("session-4")["state"], "AWAITING_AUTHORITY")

    def test_case_registry_binding_when_shared_database(self):
        from core_platform.cases import CaseRegistry
        from core_platform.upgrade_sidecar import CORE_LAWS
        cases = CaseRegistry(self.path, CORE_LAWS)
        cases.create("case-6", "CO", "E_NOTARY", "requester-6")
        self.sessions.create("session-6", "case-6", "E_NOTARY", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-7", "case-6", "RON", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-8", "missing-case", "E_NOTARY", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-9", "case-6", "E_NOTARY", "WI")

    def test_unknown_session_and_invalid_identity_denied(self):
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.get("missing")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("", "case-5", "RON", "WI")


if __name__ == "__main__":
    unittest.main()
