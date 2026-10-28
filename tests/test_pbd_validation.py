"""Offline regression tests for signed PBD manifests and containment."""
import base64
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.pbd_validation import (
    ManifestRejected, PBDScriptValidationEngine, TrustedSigner, canonical_bytes
)
from core_platform.containment import (
    SandersLabyrinthShield, MinotaurPatrol, ContainmentController
)

class PBDValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test_script.py"
        self.path.write_text("print('offline test')\n", encoding="utf-8")
        self.manifest = Path(str(self.path) + ".pbd.json")
        self.keys = {r: Ed25519PrivateKey.generate() for r in ("it_manager", "minotaur")}
        roots = {r: TrustedSigner(r, r + "-test-key", key.public_key())
                 for r, key in self.keys.items()}
        self.engine = PBDScriptValidationEngine(roots)
        self.body = dict(platform="Sanders Dash & Seal", artifact=self.path.name,
                         scope="OFFLINE_TEST", max_execution_limit=1,
                         sha256=sha256(self.path.read_bytes()).hexdigest())
        self.sign()

    def sign(self):
        data = canonical_bytes(self.body)
        signatures = {
            role: {"key_id": role + "-test-key",
                   "signature": base64.b64encode(key.sign(data)).decode("ascii")}
            for role, key in self.keys.items()
        }
        self.manifest.write_text(json.dumps({"signed_body":self.body,
                                              "signatures":signatures}), encoding="utf-8")

    def test_valid_pair(self):
        self.assertTrue(self.engine.verify(self.path, self.manifest,
                                           expected_scope="OFFLINE_TEST")["verified"])

    def test_payload_tamper_rejected(self):
        self.path.write_text("print('tampered')\n")
        with self.assertRaises(ManifestRejected):
            self.engine.verify(self.path, self.manifest, expected_scope="OFFLINE_TEST")

    def test_scope_tamper_rejected(self):
        doc = json.loads(self.manifest.read_text())
        doc["signed_body"]["scope"] = "PRODUCTION"
        self.manifest.write_text(json.dumps(doc))
        with self.assertRaises(ManifestRejected):
            self.engine.verify(self.path, self.manifest, expected_scope="PRODUCTION")

    def test_missing_signature_rejected(self):
        doc = json.loads(self.manifest.read_text())
        del doc["signatures"]["minotaur"]
        self.manifest.write_text(json.dumps(doc))
        with self.assertRaises(ManifestRejected):
            self.engine.verify(self.path, self.manifest, expected_scope="OFFLINE_TEST")

class ContainmentTests(unittest.TestCase):
    def test_denial_isolates_and_requires_full_release(self):
        shield = SandersLabyrinthShield()
        patrol = MinotaurPatrol(shield)
        controller = ContainmentController(shield)
        self.assertTrue(patrol.can_operate("offline:test", verified_attestation=True))
        controller.deny_and_isolate("incident-1", "offline:test", "THREAT")
        self.assertFalse(patrol.can_operate("offline:test", verified_attestation=True))
        with self.assertRaises(PermissionError):
            controller.release("incident-1", quality_verified=True,
                minotaur_recleared=True, manager_reconciled=True, human_approved=True)
        controller.mark_preserved("incident-1", audit_verified=True)
        controller.release("incident-1", quality_verified=True,
            minotaur_recleared=True, manager_reconciled=True, human_approved=True)
        self.assertTrue(shield.shelter_in_place)

if __name__ == "__main__":
    unittest.main()
