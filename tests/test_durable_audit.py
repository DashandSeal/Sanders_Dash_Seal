"""Offline restart persistence, tampering, and replay tests."""
import tempfile
import unittest
from pathlib import Path
from core_platform.durable_audit import DurableAuditStore, ReplayRejected

class DurableAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "audit.sqlite"

    def test_persistence_and_replay_after_restart(self):
        first = DurableAuditStore(self.path)
        first.preserve_once("corr-1", "ARCHITECT", {"stage": "PRESERVE"})
        self.assertTrue(first.verify_chain())
        first.close()
        second = DurableAuditStore(self.path)
        self.addCleanup(second.close)
        with self.assertRaises(ReplayRejected):
            second.preserve_once("corr-1", "ARCHITECT", {"stage": "REPLAY"})
        second.preserve_once("corr-2", "MINOTAUR", {"stage": "PRESERVE"})
        self.assertTrue(second.verify_chain())

    def test_tampering_detected(self):
        store = DurableAuditStore(self.path)
        self.addCleanup(store.close)
        store.preserve_once("corr-1", "CERBERUS", {"ok": True})
        store.connection.execute(
            "UPDATE receipts SET event_json=? WHERE correlation_id=?",
            ('{"ok":false}', "corr-1"))
        self.assertFalse(store.verify_chain())

    def test_missing_id_rejected(self):
        store = DurableAuditStore(self.path)
        self.addCleanup(store.close)
        with self.assertRaises(ValueError):
            store.preserve_once("", "ARCHITECT", {})

if __name__ == "__main__":
    unittest.main()
