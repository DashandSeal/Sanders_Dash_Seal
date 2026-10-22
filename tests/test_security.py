import concurrent.futures
import copy
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.security import (Denied, ROLES, TwinGate, Vault, sign, public_hex,
    PBDManifestGenerator, PBDScriptValidationEngine, GlobalPBDSentinel, digest)

from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.protocol import GATES, signing_material

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.keys = {role: Ed25519PrivateKey.generate() for role in ROLES}
        self.gate = TwinGate({r: public_hex(k.public_key()) for r, k in self.keys.items()})
        self.agent = Ed25519PrivateKey.generate()
        self.now = 1000
        self.audit = GlassBoxAudit(Path(self.tmp.name) / 'audit.db', lambda: self.now)
        self.vault = Vault(Path(self.tmp.name) / 'vault.db', self.gate, {'STANDARD': 300}, lambda: self.now)
        self.scope = {'endpoint': 'https://service.internal/status', 'method': 'GET',
                      'ip': '10.0.0.1', 'operation': 'READ_STATUS'}
        self.payload = b'{}'

    def approvals(self, domain, body):
        return {r: sign(k, domain, body) for r, k in self.keys.items()}

    def prepare(self, ttl=60, source=b'def execute(scope, payload):\n    return b"checked-state"\n'):
        bounds = {'endpoint': self.scope['endpoint'], 'allowed_verbs': ['GET', 'POST'],
                  'network_jail_ips': ['10.0.0.1', '10.0.0.2'], 'operation': self.scope['operation']}
        body = self.vault.request(public_hex(self.agent.public_key()), bounds, self.payload,
                                  ttl, 'STANDARD', 'IntegrationAgent', digest(source))
        material = signing_material(body)
        body['agent_identity']['agent_identity_assertion'] = sign(self.agent, 'pbd-agent-assertion-v2', material)
        body['dual_governance_gates'] = dict(zip(GATES,
            (sign(self.keys[r], 'pbd-lease-v2', material) for r in ROLES)))
        return body

    def issue(self, source=b'def execute(scope, payload):\n    return b"checked-state"\n'):
        body = self.prepare(source=source)
        self.vault.mint(body)
        return body, sign(self.agent, 'pbd-agent-proof-v2', {'lease': body, 'operation': self.scope})

    def test_success_and_replay(self):
        body, proof = self.issue()
        self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)
        self.assertEqual(self.vault.state(body['lease_metadata']['lease_id']), 'CONSUMED')
        with self.assertRaises(Denied):
            self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)

    def test_missing_minotaur(self):
        body = self.prepare()
        body['dual_governance_gates'][GATES[1]] = ''
        with self.assertRaises(Denied): self.vault.mint(body)
        self.assertIsNone(self.vault.state(body['lease_metadata']['lease_id']))

    def test_tampered_approval(self):
        body = self.prepare()
        body['operational_bounds']['allowed_verbs'].append('DELETE')
        with self.assertRaises(Denied): self.vault.mint(body)

    def test_same_authority_key_rejected(self):
        key = public_hex(self.agent.public_key())
        with self.assertRaises(ValueError): TwinGate({r: key for r in ROLES})

    def test_expiry(self):
        body, proof = self.issue()
        self.now += 60
        with self.assertRaises(Denied): self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)
        self.assertEqual(self.vault.state(body['lease_metadata']['lease_id']), 'REVOKED')

    def test_payload_tamper_burns_lease(self):
        body, proof = self.issue()
        with self.assertRaises(Denied): self.vault.claim(body['lease_metadata']['lease_id'], self.scope, b'changed', proof)
        self.assertEqual(self.vault.state(body['lease_metadata']['lease_id']), 'REVOKED')

    def test_wrong_agent(self):
        body, _ = self.issue()
        proof = sign(Ed25519PrivateKey.generate(), 'pbd-agent-proof-v1', body)
        with self.assertRaises(Denied): self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)

    def test_scope_drift(self):
        body, proof = self.issue()
        changed = dict(self.scope, ip='10.0.0.3')
        with self.assertRaises(Denied): self.vault.claim(body['lease_metadata']['lease_id'], changed, self.payload, proof)

    def test_revocation_persists(self):
        body, proof = self.issue()
        self.vault.revoke(body['lease_metadata']['lease_id'])
        reopened = Vault(self.vault.path, self.gate, {'STANDARD': 300}, lambda: self.now)
        with self.assertRaises(Denied): reopened.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)

    def test_parallel_claims_exactly_one_wins(self):
        body, proof = self.issue()
        def claim(_):
            try:
                self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)
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

    def test_standard_five_minute_lease_with_explicit_policy(self):
        body = self.prepare(ttl=300)
        self.vault.mint(body)
        self.now += 299
        proof = sign(self.agent, 'pbd-agent-proof-v2', {'lease': body, 'operation': self.scope})
        self.vault.claim(body['lease_metadata']['lease_id'], self.scope, self.payload, proof)

    def test_allowed_lists_and_operation_proof(self):
        body = self.prepare()
        self.vault.mint(body)
        request = dict(self.scope, method='POST', ip='10.0.0.2')
        proof = sign(self.agent, 'pbd-agent-proof-v2', {'lease': body, 'operation': request})
        self.vault.claim(body['lease_metadata']['lease_id'], request, self.payload, proof)

    def test_assertion_required_before_mint(self):
        body = self.prepare()
        body['agent_identity']['agent_identity_assertion'] = ''
        with self.assertRaises(Denied): self.vault.mint(body)

    def test_unknown_lease_fields_rejected(self):
        body = self.prepare()
        body['scope_override'] = '*'
        with self.assertRaises(Denied): self.vault.mint(body)

    def test_case_variants_cannot_fake_independent_keys(self):
        key = public_hex(self.agent.public_key())
        with self.assertRaises(ValueError): TwinGate({ROLES[0]: key, ROLES[1]: key.upper()})

if __name__ == '__main__': unittest.main()
