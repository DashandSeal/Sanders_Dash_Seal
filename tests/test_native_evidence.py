import tempfile
import unittest
from pathlib import Path

from core_platform.native_notary import NativeNotarySessions
from core_platform.native_evidence import NativeEvidenceIndex, EvidenceDenied


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "notary.db"
        self.sessions = NativeNotarySessions(path)
        self.evidence = NativeEvidenceIndex(path)
        self.sessions.create("s-1", "c-1", "RON", "WI")
        self.sessions.create("s-2", "c-2", "E_NOTARY", "CO")

    def test_persistent_idempotent_digest(self):
        digest = "a" * 64
        first = self.evidence.register("s-1", "doc-1", "DOCUMENT", digest)
        self.assertEqual(first, self.evidence.register("s-1", "doc-1", "DOCUMENT", digest))
        self.assertEqual(self.evidence.list_for_session("s-1")[0]["sha256"], digest)
        with self.assertRaises(EvidenceDenied):
            self.evidence.register("s-1", "doc-1", "DOCUMENT", "b" * 64)

    def test_ron_only_recording(self):
        self.evidence.register("s-1", "recording-1", "AV_RECORDING", "c" * 64)
        with self.assertRaises(EvidenceDenied):
            self.evidence.register("s-2", "recording-2", "AV_RECORDING", "c" * 64)

    def test_cancelled_or_unknown_session_rejected(self):
        self.sessions.cancel("s-1")
        with self.assertRaises(EvidenceDenied):
            self.evidence.register("s-1", "doc-2", "DOCUMENT", "a" * 64)
        with self.assertRaises(EvidenceDenied):
            self.evidence.register("unknown", "doc-2", "DOCUMENT", "a" * 64)

    def test_bad_digest_rejected(self):
        with self.assertRaises(EvidenceDenied):
            self.evidence.register("s-1", "doc-3", "DOCUMENT", "not-a-digest")


if __name__ == "__main__":
    unittest.main()
