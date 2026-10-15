import test_security
from core_platform.security import PBDManifestGenerator, PBDScriptValidationEngine, digest, sign, public_hex, Denied
from core_platform.lifecycle import (QualityAgent, ITAIManager, Minotaur,
                                     LabyrinthShield, GovernedLifecycle)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import unittest
import json
from dataclasses import replace
from unittest.mock import patch
from core_platform.artifacts import SignedPythonArtifact, DevelopmentArtifactRunner

class LifecycleTests(unittest.TestCase):
    setUp = test_security.SecurityTests.setUp
    approvals = test_security.SecurityTests.approvals
    issue = test_security.SecurityTests.issue
    prepare = test_security.SecurityTests.prepare

    def setup_flow(self, source=b'def execute(scope, payload):\n    return b"checked-state"\n'):
        quality_key = Ed25519PrivateKey.generate()
        shield = LabyrinthShield()
        flow = GovernedLifecycle(self.vault, PBDScriptValidationEngine(self.gate),
            QualityAgent(public_hex(quality_key.public_key())),
            ITAIManager(self.gate.keys['IT_AI_Manager_v15.0']),
            Minotaur(self.gate.keys['MINOTAUR']), shield, self.audit)
        def attester(key, domain, field):
            def attest(lease, result):
                body = {'lease_id': lease, 'result_hash': digest(result), field: True}
                return {'body': body, 'signature': sign(key, domain, body)}
            return attest
        checks = [attester(quality_key, 'pbd-quality-v1', 'verified'),
            attester(self.keys['IT_AI_Manager_v15.0'], 'pbd-reconcile-v1', 'reconciled'),
            attester(self.keys['MINOTAUR'], 'pbd-integrity-v1', 'integrity_confirmed')]
        body, proof = self.issue(source=source)
        manifest_body = PBDManifestGenerator.prepare(source, 'worker.py', self.scope)
        manifest = {'body': manifest_body,
                    'signatures': self.approvals('pbd-manifest-v1', manifest_body)}
        args = [body['lease_metadata']['lease_id'], self.scope, self.payload, proof,
                SignedPythonArtifact('worker.py', source, json.dumps(manifest)),
                DevelopmentArtifactRunner(flow.validator, enable_development_execution=True)]
        return flow, args, checks

    def test_verified_lifecycle(self):
        flow, args, checks = self.setup_flow()
        result = flow.run(*args, *checks)
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.audit.verify_audit()

    def test_adapter_failure_revokes_and_contains(self):
        flow, args, checks = self.setup_flow(b'def execute(scope, payload):\n    raise RuntimeError("offline")\n')
        with self.assertRaises(RuntimeError): flow.run(*args, *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.assertEqual(flow.shield.mode, 'HUMANITARIAN')

    def test_no_assumed_quality_success(self):
        flow, args, checks = self.setup_flow()
        checks[0] = lambda *args: {'body': {}, 'signature': ''}
        with self.assertRaises(Denied): flow.run(*args, *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')

    def test_invalid_manifest_blocks_adapter(self):
        flow, args, checks = self.setup_flow()
        manifest = json.loads(args[4].manifest_json)
        manifest['signatures'] = {}
        args[4] = replace(args[4], manifest_json=json.dumps(manifest))
        with patch('builtins.compile') as compile_mock:
            with self.assertRaises(Denied): flow.run(*args, *checks)
            compile_mock.assert_not_called()
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')

    def test_each_verification_is_a_gate(self):
        flow, args, checks = self.setup_flow()
        calls = []
        checks[0] = lambda *args: {'body': {}, 'signature': ''}
        checks[1] = lambda *args: calls.append('reconciliation')
        checks[2] = lambda *args: calls.append('integrity')
        with self.assertRaises(Denied): flow.run(*args, *checks)
        self.assertEqual(calls, [])

    def test_result_audit_failure_contains_and_revokes(self):
        flow, args, checks = self.setup_flow()
        preserve = self.audit.preserve
        def broken(event):
            if event['stage'] == 'EXECUTION_RESULT': raise OSError('storage unavailable')
            return preserve(event)
        self.audit.preserve = broken
        with self.assertRaises(OSError): flow.run(*args, *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.assertEqual(flow.shield.mode, 'HUMANITARIAN')

    def test_revocation_receipt_failure_contains(self):
        flow, args, checks = self.setup_flow()
        preserve = self.audit.preserve
        def broken(event):
            if event['stage'] == 'AUTHORITY_REVOKED': raise OSError('storage unavailable')
            return preserve(event)
        self.audit.preserve = broken
        with self.assertRaises(OSError): flow.run(*args, *checks)
        self.assertEqual(self.vault.state(args[0]), 'REVOKED')
        self.assertEqual(flow.shield.mode, 'HUMANITARIAN')

    def test_audit_and_vault_are_separate(self):
        self.assertFalse(hasattr(self.vault, 'preserve'))
        self.assertNotEqual(self.vault.path, self.audit.path)
        with self.vault.connect() as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn('receipts', tables)

    def test_source_swap_is_rejected(self):
        flow, args, checks = self.setup_flow()
        args[4] = replace(args[4], source=b'raise RuntimeError("must not run")')
        with self.assertRaises(Denied): flow.run(*args, *checks)

    def test_unrelated_callback_is_rejected(self):
        flow, args, checks = self.setup_flow()
        args[4] = lambda *args: b'forged'
        with self.assertRaises(Denied): flow.run(*args, *checks)

    def test_development_execution_requires_explicit_opt_in(self):
        with self.assertRaises(Denied): DevelopmentArtifactRunner(PBDScriptValidationEngine(self.gate))

    def test_receipt_has_master_groups_without_fake_http(self):
        flow, args, checks = self.setup_flow()
        receipt = flow.run(*args, *checks)['execution_receipt']
        self.assertEqual(set(receipt), {'execution_metadata', 'functional_telemetry',
                                      'post_execution_clearance', 'immutable_audit_trail'})
        self.assertIsNone(receipt['functional_telemetry']['http_status_returned'])
        self.assertIsNone(receipt['functional_telemetry']['payload_bytes_transferred'])
        self.assertEqual(receipt['execution_metadata']['executed_by'], 'IntegrationAgent')

    def test_different_signed_artifact_cannot_use_same_lease(self):
        flow, args, checks = self.setup_flow()
        other_source = b'def execute(scope, payload): return b"different"'
        body = PBDManifestGenerator.prepare(other_source, 'worker.py', self.scope)
        manifest = {'body': body, 'signatures': self.approvals('pbd-manifest-v1', body)}
        args[4] = SignedPythonArtifact('worker.py', other_source, json.dumps(manifest))
        with self.assertRaises(Denied): flow.run(*args, *checks)
