"""Explicit role boundaries for the Twin-Gate execution lifecycle.

Adapters are trusted host components, not arbitrary uploaded scripts.
No network or shell executor is provided by this development foundation.
"""
from .security import Denied, digest, verify
from .protocol import utc
from .artifacts import DevelopmentArtifactRunner

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
    def __init__(self, vault, validator, quality, manager, minotaur, shield, audit):
        if len({quality.key, manager.key, minotaur.key}) != 3:
            raise ValueError('Independent verification requires three distinct keys')
        if (manager.key != vault.gate.keys['IT_AI_Manager_v15.0'] or
                minotaur.key != vault.gate.keys['MINOTAUR']):
            raise ValueError('Authority keys must match the Vault trust configuration')
        self.vault, self.validator, self.audit = vault, validator, audit
        self.quality, self.manager, self.minotaur, self.shield = quality, manager, minotaur, shield

    def run(self, lease_id, scope, payload, proof, artifact, runner,
            quality_check, reconcile_check, integrity_check):
        body = None
        result = None
        status = 'DENIED'
        receipt = None
        execution_receipt = None
        started = utc(self.vault.clock())
        try:
            # Consumed authority can never be reused, including after process failure.
            body = self.vault.claim(lease_id, scope, payload, proof)
            self.shield.check(body['execution_binding']['agent_public_key'])
            if type(runner) is not DevelopmentArtifactRunner or runner.validator is not self.validator:
                raise Denied('Unapproved execution runner')
            runner.validate(artifact, scope)
            if digest(artifact.source) != body['execution_binding']['artifact_hash']:
                raise Denied('Executable differs from the lease-bound artifact')
            # Persist intent before any side effect. Audit failure prevents adapter entry.
            self.audit.preserve({'lease_id': lease_id, 'stage': 'EXECUTION_INTENT',
                                 'artifact': artifact.name, 'artifact_hash': digest(artifact.source), 'payload_hash': digest(payload)})
            result = runner.execute(artifact, scope, payload)
            if not isinstance(result, bytes):
                raise Denied('Adapter result must be bytes')
            quality = quality_check(lease_id, result)
            self.quality.verify_result(lease_id, result, quality)
            reconciliation = reconcile_check(lease_id, result)
            self.manager.reconcile(lease_id, result, reconciliation)
            integrity = integrity_check(lease_id, result)
            self.minotaur.reseal(lease_id, result, integrity)
            receipt = {'quality': quality, 'reconciliation': reconciliation, 'integrity': integrity}
            status = 'VERIFIED'
        except BaseException:
            if body:
                self.shield.contain(body['execution_binding']['agent_public_key'])
            raise
        finally:
            # Authority was already consumed. Revoke even when evidence preservation fails.
            try:
                try:
                    execution_receipt = {
                        'execution_metadata': {'lease_id': lease_id,
                            'executed_by': body['agent_identity']['requesting_agent'] if body else None,
                            'started_at_utc': started, 'completed_at_utc': utc(self.vault.clock())},
                        'functional_telemetry': {'http_status_returned': None,
                            'payload_bytes_transferred': None, 'execution_result': status,
                            'post_condition_verified': status == 'VERIFIED'},
                        'post_execution_clearance': {
                            'quality_agent_synthetic_validation': receipt['quality'] if receipt else None,
                            'it_manager_state_reconciliation': receipt['reconciliation'] if receipt else None,
                            'minotaur_integrity_seal': receipt['integrity'] if receipt else None}}
                    execution_receipt = self.audit.preserve_execution(execution_receipt)
                finally:
                    self.vault.revoke(lease_id)
                self.audit.preserve({'lease_id': lease_id, 'stage': 'AUTHORITY_REVOKED'})
            except BaseException:
                # Evidence and authority cleanup are required parts of completion.
                if body:
                    self.shield.contain(body['execution_binding']['agent_public_key'])
                raise
        return {'lease_id': lease_id, 'status': status, 'authority': 'REVOKED',
                'execution_receipt': execution_receipt}
