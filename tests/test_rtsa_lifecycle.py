"""Offline lifecycle tests for all fourteen RTSA identities."""
import unittest
from core_platform.rtsa_registry import RTSA_ROLES
from core_platform.rtsa_lifecycle import OfflineRTSAConductor, LifecycleDenied
from core_platform.twin_gate import GlassBoxAudit

class RTSALifecycleTests(unittest.TestCase):
    def setUp(self):
        self.audit = GlassBoxAudit()
        self.conductor = OfflineRTSAConductor(self.audit)

    def test_all_fourteen_advisory_lifecycles(self):
        for index, name in enumerate(RTSA_ROLES):
            receipt = self.conductor.run(
                rtsa=name, data={}, correlation_id=f"offline-{index}",
                manager_clearance=True, minotaur_clearance=True,
                human_clearance=True)
            self.assertFalse(receipt.execution_allowed)
            self.assertEqual(receipt.rtsa, name)
            self.assertTrue(receipt.findings)
        self.assertTrue(self.audit.verify())

    def test_missing_gate_denies(self):
        for gate in ("manager_clearance", "minotaur_clearance", "human_clearance"):
            kwargs = dict(manager_clearance=True, minotaur_clearance=True, human_clearance=True)
            kwargs[gate] = False
            with self.subTest(gate=gate):
                with self.assertRaises(LifecycleDenied):
                    self.conductor.run(rtsa="MINOTAUR", data={},
                                       correlation_id="denied-" + gate, **kwargs)
        self.assertTrue(self.audit.verify())

    def test_replay_denied(self):
        kwargs = dict(rtsa="ARCHITECT", data={}, correlation_id="unique-id",
                      manager_clearance=True, minotaur_clearance=True,
                      human_clearance=True)
        self.conductor.run(**kwargs)
        with self.assertRaises(LifecycleDenied):
            self.conductor.run(**kwargs)

if __name__ == "__main__":
    unittest.main()
