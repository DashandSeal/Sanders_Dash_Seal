"""Regression tests for guarded sidecar staging and rollback."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from core_platform.upgrade_sidecar import CORE_LAWS, UpgradeDenied, UpgradeSidecar


class Adapter:
    def __init__(self):
        self.calls = []

    def stage(self, record, path):
        self.calls.append(("stage", record["component"]))
        return {"staged": True, "deployment_id": "test-dark"}

    def verify(self, record):
        self.calls.append(("verify", record["component"]))
        return {"healthy": True, "check": "test"}

    def rollback(self, record):
        self.calls.append(("rollback", record["component"]))
        return {"restored": True, "baseline": "test"}


class UpgradeExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.artifact = self.path / "upgrade.bin"
        self.artifact.write_bytes(b"verified test artifact")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.adapter = Adapter()
        self.sidecar = UpgradeSidecar(
            self.path / "state.sqlite", ["meetings"], CORE_LAWS,
            executor=self.adapter,
            authorizer=lambda request_id, record, proof: proof == "owner-test-approval")
        self.sidecar.propose("request-1", "meetings", "1.1", self.digest, {})
        self.sidecar.evaluate("request-1", {"reviewed": True})

    def test_approved_stage_verify_and_rollback(self):
        self.assertEqual(self.sidecar.approve_or_deploy("request-1", "owner-test-approval"), "APPROVED")
        self.assertEqual(self.sidecar.apply_upgrade("request-1", self.artifact), "DEPLOYED_DARK")
        self.assertEqual(self.sidecar.verify_live("request-1"), "LIVE_VERIFIED")
        self.assertEqual(self.sidecar.rollback("request-1"), "ROLLED_BACK")
        self.assertEqual([c[0] for c in self.adapter.calls], ["stage", "verify", "rollback"])

    def test_unapproved_and_tampered_artifacts_denied(self):
        with self.assertRaises(UpgradeDenied):
            self.sidecar.apply_upgrade("request-1", self.artifact)
        with self.assertRaises(UpgradeDenied):
            self.sidecar.approve_or_deploy("request-1", "bad-proof")
        self.sidecar.approve_or_deploy("request-1", "owner-test-approval")
        self.artifact.write_bytes(b"tampered")
        with self.assertRaises(UpgradeDenied):
            self.sidecar.apply_upgrade("request-1", self.artifact)
        self.assertEqual(self.adapter.calls, [])

    def test_missing_adapters_deny_execution(self):
        sidecar = UpgradeSidecar(self.path / "state.sqlite", ["meetings"], CORE_LAWS)
        with self.assertRaises(UpgradeDenied):
            sidecar.approve_or_deploy("request-1", "owner-test-approval")
        with self.assertRaises(UpgradeDenied):
            sidecar.apply_upgrade("request-1", self.artifact)


if __name__ == "__main__":
    unittest.main()
