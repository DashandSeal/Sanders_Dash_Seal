import concurrent.futures
import copy
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.security import (Denied, ROLES, TwinGate, Vault, sign, public_hex,
    PBDManifestGenerator, PBDScriptValidationEngine, GlobalPBDSentinel)

from core_platform.glass_box_audit import GlassBoxAudit

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.keys = {role: Ed25519PrivateKey.generate() for role in ROLES}
        self.gate = TwinGate({r: public_hex(k.public_key()) for r, k in self.keys.items()})
        self.agent = Ed25519PrivateKey.generate()
        self.now = 1000
        self.audit = GlassBoxAudit(Path(self.tmp.name) / 'audit.db', lambda: self.now)
        self.vault = Vault(Path(self.tmp.name) / 'vault.db', self.gate, lambda: self.now)
        self.scope = {'endpoint': 'https://service.internal/status', 'method': 'GET',
                      'ip': '10.0.0.1', 'operation': 'READ_STATUS'}
        self.payload = b'{}'

    def approvals(self, domain, body):
        return {r: sign(k, domain, body) for r, k in self.keys.items()}

    def issue(self):
        body = self.vault.request(public_hex(self.agent.public_key()), self.scope, self.payload)
        self.vault.mint(body, self.approvals('pbd-lease-v1', body))
        return body, sign(self.agent, 'pbd-agent-proof-v1', body)

    def test_success_and_replay(self):
        body, proof = self.issue()
        self.vault.claim(body['id'], self.scope, self.payload, proof)
        self.assertEqual(self.vault.state(body['id']), 'CONSUMED')
        with self.assertRaises(Denied):
            self.vault.claim(body['id'], self.scope, self.payload, proof)

    def test_missing_minotaur(self):
        body = self.vault.request(public_hex(self.agent.public_key()), self.scope, self.payload)
        signatures = self.approvals('pbd-lease-v1', body)
        del signatures['MINOTAUR']
        with self.assertRaises(Denied): self.vault.mint(body, signatures)
        self.assertIsNone(self.vault.state(body['id']))

    def test_tampered_approval(self):
        body = self.vault.request(public_hex(self.agent.public_key()), self.scope, self.payload)
        signatures = self.approvals('pbd-lease-v1', body)
        body['scope']['method'] = 'POST'
        with self.assertRaises(Denied): self.vault.mint(body, signatures)

    def test_same_authority_key_rejected(self):
        key = public_hex(self.agent.public_key())
        with self.assertRaises(ValueError): TwinGate({r: key for r in ROLES})

    def test_expiry(self):
        body, proof = self.issue()
        self.now += 60
        with self.assertRaises(Denied): self.vault.claim(body['id'], self.scope, self.payload, proof)
        self.assertEqual(self.vault.state(body['id']), 'REVOKED')

    def test_payload_tamper_burns_lease(self):
        body, proof = self.issue()
        with self.assertRaises(Denied): self.vault.claim(body['id'], self.scope, b'changed', proof)
        self.assertEqual(self.vault.state(body['id']), 'REVOKED')

    def test_wrong_agent(self):
        body, _ = self.issue()
        proof = sign(Ed25519PrivateKey.generate(), 'pbd-agent-proof-v1', body)
        with self.assertRaises(Denied): self.vault.claim(body['id'], self.scope, self.payload, proof)

    def test_scope_drift(self):
        body, proof = self.issue()
        changed = dict(self.scope, ip='10.0.0.2')
        with self.assertRaises(Denied): self.vault.claim(body['id'], changed, self.payload, proof)

    def test_revocation_persists(self):
        body, proof = self.issue()
        self.vault.revoke(body['id'])
        reopened = Vault(self.vault.path, self.gate, lambda: self.now)
        with self.assertRaises(Denied): reopened.claim(body['id'], self.scope, self.payload, proof)

    def test_parallel_claims_exactly_one_wins(self):
        body, proof = self.issue()
        def claim(_):
            try:
                self.vault.claim(body['id'], self.scope, self.payload, proof)
                return 1
            except Denied: return 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(claim, range(8))), 1)

    def test_manifest_and_sentinel(self):
        root = Path(self.tmp.name) / 'artifacts'
        root.mkdir()
        path = root / 'pbd_worker.py'
        path.write_bytes(b'pass\n')
        body = PBDManifestGenerator.prepare(path.read_bytes(), path.name, self.scope)
        manifest = {'body': body, 'signatures': self.approvals('pbd-manifest-v1', body)}
        Path(str(path) + '.pbd.json').write_text(json.dumps(manifest))
        scanner = GlobalPBDSentinel(PBDScriptValidationEngine(self.gate))
        self.assertEqual(scanner.scan(root, self.scope)[0]['status'], 'VALID')
        path.write_bytes(b'changed\n')
        self.assertEqual(scanner.scan(root, self.scope)[0]['status'], 'BLOCKED')
        Path(str(path) + '.pbd.json').unlink()
        self.assertEqual(scanner.scan(root, self.scope)[0]['status'], 'BLOCKED')

    def test_audit_tamper(self):
        self.audit.preserve({'result': 'DENIED'})
        self.audit.preserve({'result': 'REVOKED'})
        self.audit.verify_audit()
        with self.audit.connect() as db:
            db.execute("UPDATE receipts SET body='{}' WHERE seq=1")
        with self.assertRaises((Denied, KeyError)): self.audit.verify_audit()

if __name__ == '__main__': unittest.main()
