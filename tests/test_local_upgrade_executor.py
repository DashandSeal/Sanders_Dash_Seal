import hashlib
import tempfile
import unittest
from pathlib import Path

from core_platform.local_upgrade_executor import LocalUpgradeExecutor
from core_platform.upgrade_sidecar import CORE_LAWS, UpgradeSidecar, UpgradeDenied


class LocalExecutorTests(unittest.TestCase):
    def test_staging_integrity_and_baseline_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "upgrade.bin"
            artifact.write_bytes(b"version one")
            executor = LocalUpgradeExecutor(root / "deploy")
            sidecar = UpgradeSidecar(root / "requests.sqlite", ["meetings"], CORE_LAWS,
                executor=executor, authorizer=lambda rid, record, proof: proof == "test-owner")
            def upgrade(rid, payload):
                artifact.write_bytes(payload)
                digest = hashlib.sha256(payload).hexdigest()
                sidecar.propose(rid, "meetings", rid, digest, {})
                sidecar.evaluate(rid, {"tests": "local"})
                sidecar.approve_or_deploy(rid, "test-owner")
                sidecar.apply_upgrade(rid, artifact)
                self.assertEqual(sidecar.verify_live(rid), "LIVE_VERIFIED")
            upgrade("v1", b"version one")
            upgrade("v2", b"version two")
            self.assertEqual((root / "deploy/meetings/current.bin").read_bytes(), b"version two")
            self.assertEqual(sidecar.rollback("v2"), "ROLLED_BACK")
            self.assertEqual((root / "deploy/meetings/current.bin").read_bytes(), b"version one")

    def test_no_previous_baseline_cannot_claim_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executor = LocalUpgradeExecutor(root)
            record = {"component": "meetings", "version": "v1",
                      "artifact_hash": hashlib.sha256(b"v1").hexdigest()}
            artifact = root / "artifact.bin"
            artifact.write_bytes(b"v1")
            executor.stage(record, artifact)
            self.assertFalse(executor.rollback(record)["restored"])


if __name__ == "__main__":
    unittest.main()
