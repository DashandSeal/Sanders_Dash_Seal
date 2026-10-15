"""Explicit role boundaries for the Twin-Gate execution lifecycle.

Adapters are trusted host components, not arbitrary uploaded scripts.
No network or shell executor is provided by this development foundation.
"""
from .security import Denied, digest, verify

class QualityAgent:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def verify_result(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes), 'verified': True}
        if attestation.get('body') != expected:
            raise Denied('Quality Agent did not verify this result')
        verify(self.key, attestation.get('signature', ''), 'pbd-quality-v1', expected)

class ITAIManager:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def reconcile(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes), 'reconciled': True}
        if attestation.get('body') != expected:
            raise Denied('IT AI Manager did not reconcile this operation')
        verify(self.key, attestation.get('signature', ''), 'pbd-reconcile-v1', expected)

class Minotaur:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def reseal(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes), 'integrity_confirmed': True}
        if attestation.get('body') != expected:
            raise Denied('MINOTAUR did not confirm integrity')
        verify(self.key, attestation.get('signature', ''), 'pbd-integrity-v1', expected)

class LabyrinthShield:
    """Separate in-process containment state; OS isolation remains an adapter duty."""
    def __init__(self):
        self.quarantined = set()
        self.mode = 'GOVERNED'

    def contain(self, agent_key):
        self.quarantined.add(agent_key)
        self.mode = 'HUMANITARIAN'

    def check(self, agent_key):
        if self.mode != 'GOVERNED' or agent_key in self.quarantined:
            raise Denied('Shelter in place; human clearance required')

class GovernedLifecycle:
    def __init__(self, vault, validator, quality, manager, minotaur, shield):
        if len({quality.key, manager.key, minotaur.key}) != 3:
            raise ValueError('Independent verification requires three distinct keys')
        if (manager.key != vault.gate.keys['IT_AI_Manager_v15.0'] or
                minotaur.key != vault.gate.keys['MINOTAUR']):
            raise ValueError('Authority keys must match the Vault trust configuration')
        self.vault, self.validator = vault, validator
        self.quality, self.manager, self.minotaur, self.shield = quality, manager, minotaur, shield

    def run(self, lease_id, scope, payload, proof, artifact, manifest, adapter,
            quality_check, reconcile_check, integrity_check):
        body = None
        result = None
        status = 'DENIED'
        receipt = None
        try:
            # Consumed authority can never be reused, including after process failure.
            body = self.vault.claim(lease_id, scope, payload, proof)
            self.shield.check(body['agent_key'])
            self.validator.validate(payload, artifact, scope, manifest)
            # Persist intent before any side effect. Audit failure prevents adapter entry.
            self.vault.preserve({'lease_id': lease_id, 'stage': 'EXECUTION_INTENT',
                                 'artifact': artifact, 'payload_hash': digest(payload)})
            result = adapter(scope, payload)
            if not isinstance(result, bytes):
                raise Denied('Adapter result must be bytes')
            quality = quality_check(lease_id, result)
            reconciliation = reconcile_check(lease_id, result)
            integrity = integrity_check(lease_id, result)
            self.quality.verify_result(lease_id, result, quality)
            self.manager.reconcile(lease_id, result, reconciliation)
            self.minotaur.reseal(lease_id, result, integrity)
            receipt = {'quality': quality, 'reconciliation': reconciliation, 'integrity': integrity}
            status = 'VERIFIED'
        except BaseException:
            if body:
                self.shield.contain(body['agent_key'])
            raise
        finally:
            # Authority was already consumed. Revoke even when evidence preservation fails.
            try:
                self.vault.preserve({'lease_id': lease_id, 'stage': 'EXECUTION_RESULT',
                    'status': status, 'attestations': receipt,
                    'result_hash': digest(result) if isinstance(result, bytes) else None})
            finally:
                self.vault.revoke(lease_id)
            self.vault.preserve({'lease_id': lease_id, 'stage': 'AUTHORITY_REVOKED'})
        return {'lease_id': lease_id, 'status': status, 'authority': 'REVOKED'}
