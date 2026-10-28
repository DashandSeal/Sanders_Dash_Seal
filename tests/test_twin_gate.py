"""Offline tests for Sanders Dash & Seal Twin-Gate authorization."""
from datetime import timedelta
from hashlib import sha256
import unittest

from core_platform.twin_gate import (
    AuthorizationDenied, GlassBoxAudit, Lease, TwinGate, Vault, utc_now
)

class TwinGateTests(unittest.TestCase):
    def setUp(self):
        self.vault = Vault()
        self.audit = GlassBoxAudit()
        self.gate = TwinGate(self.vault, self.audit)
        self.payload = b"offline test payload"

    def lease(self, **changes):
        now = utc_now()
        args = dict(lease_id="test-lease", agent="QualityAgent",
                    target="offline:test", method="GET",
                    issued_at=now - timedelta(seconds=1),
                    expires_at=now + timedelta(seconds=30),
                    payload_sha256=sha256(self.payload).hexdigest(),
                    manager_approved=True, minotaur_approved=True,
                    human_approved=True)
        args.update(changes)
        return Lease(**args)

    def test_both_gates_required(self):
        for missing in ("manager_approved", "minotaur_approved"):
            with self.subTest(missing=missing):
                gate = TwinGate(Vault(), GlassBoxAudit())
                with self.assertRaises(AuthorizationDenied):
                    gate.authorize(self.lease(**{missing:False}),
                                   agent="QualityAgent", target="offline:test",
                                   method="GET", payload=self.payload)

    def test_replay_denied(self):
        lease = self.lease()
        self.gate.authorize(lease, agent="QualityAgent", target="offline:test",
                            method="GET", payload=self.payload)
        with self.assertRaises(AuthorizationDenied):
            self.gate.authorize(lease, agent="QualityAgent", target="offline:test",
                                method="GET", payload=self.payload)
        self.assertTrue(self.audit.verify())

    def test_scope_and_payload_enforced(self):
        for target, payload in (("offline:other", self.payload),
                                ("offline:test", b"changed")):
            with self.subTest(target=target):
                gate = TwinGate(Vault(), GlassBoxAudit())
                with self.assertRaises(AuthorizationDenied):
                    gate.authorize(self.lease(), agent="QualityAgent",
                                   target=target, method="GET", payload=payload)

    def test_human_approval_required(self):
        with self.assertRaises(AuthorizationDenied):
            self.gate.authorize(self.lease(human_approved=False),
                                agent="QualityAgent", target="offline:test",
                                method="GET", payload=self.payload)

    def test_expired_lease_denied(self):
        with self.assertRaises(AuthorizationDenied):
            self.gate.authorize(self.lease(expires_at=utc_now()-timedelta(seconds=1)),
                                agent="QualityAgent", target="offline:test",
                                method="GET", payload=self.payload)

if __name__ == "__main__":
    unittest.main()
