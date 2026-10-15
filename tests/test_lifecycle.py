import test_security
from core_platform.security import PBDManifestGenerator, PBDScriptValidationEngine, digest, sign, public_hex, Denied
from core_platform.lifecycle import (QualityAgent, ITAIManager, Minotaur,
                                     LabyrinthShield, GovernedLifecycle)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import unittest

class LifecycleTests(unittest.TestCase):
    setUp = test_security.SecurityTests.setUp
    approvals = test_security.SecurityTests.approvals
    issue = test_security.SecurityTests.issue

    def setup_flow(self):
        quality_key = Ed25519PrivateKey.generate()
        shield = LabyrinthShield()
        flow = GovernedLifecycle(self.vault, PBDScriptValidationEngine(self.gate),
            QualityAgent(public_hex(quality_key.public_key())),
            ITAIManager(self.gate.keys['IT_AI_Manager_v15.0']),
            Minotaur(self.gate.keys['MINOTAUR']), shield)
        def attester(key, domain, field):
            def attest(lease, result):
                body = {'lease_id': lease, 'result_hash': digest(result), field: True}
                return {'body': body, 'signature': sign(key, domain, body)}
            return attest
        checks = [attester(quality_key, 'pbd-quality-v1', 'verified'),
            attester(self.keys['IT_AI_Manager_v15.0'], 'pbd-reconcile-v1', 'reconciled'),
            attester(self.keys['MINOTAUR'], 'pbd-integrity-v1', 'integrity_confirmed')]
        body, proof = self.issue()
        manifest_body = PBDManifestGenerator.prepare(self.payload, 'worker.py', self.scope)
        manifest = {'body': manifest_body,
                    'signatures': self.approvals('pbd-manifest-v1', manifest_body)}
        args = [body['id'], self.scope, self.payload, proof, 'worker.py', manifest]
        return flow, args, checks

    def test_verified_lifecycle(self):
        flow, args, checks = self.setup_flow()
        result = flow.run(*args, lambda scope, payload: b'checked-state', *checks)
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.vault.verify_audit()

    def test_adapter_failure_revokes_and_contains(self):
        flow, args, checks = self.setup_flow()
        def fail(scope, payload): raise RuntimeError('adapter offline')
        with self.assertRaises(RuntimeError): flow.run(*args, fail, *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.assertEqual(flow.shield.mode, 'HUMANITARIAN')

    def test_no_assumed_quality_success(self):
        flow, args, checks = self.setup_flow()
        checks[0] = lambda *args: {'body': {}, 'signature': ''}
        with self.assertRaises(Denied): flow.run(*args, lambda *args: b'ok', *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')

    def test_invalid_manifest_blocks_adapter(self):
        flow, args, checks = self.setup_flow()
        args[-1]['signatures'] = {}
        calls = []
        with self.assertRaises(Denied):
            flow.run(*args, lambda *args: calls.append(1), *checks)
        self.assertEqual(calls, [])
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
