"""
Module: core_platform.lifecycle
Architectural Layer: Explicit Role Boundaries for the Twin-Gate Execution Lifecycle
Description: Coordinates high-level contract validation loops across QualityAgent,
             ITAIManager, and Minotaur cryptographic keys without exposing shell access.
"""

from security import Denied, digest, verify
from protocol import utc
from artifacts import DevelopmentArtifactRunner

class QualityAgent:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def verify_result(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes)}
        if attestation.get('body') != expected:
            raise Denied('Quality Agent did not verify this result')
        verify(self.key, attestation.get('signature', ''), 'pbd-quality')

class ITAIManager:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def reconcile(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes)}
        if attestation.get('body') != expected:
            raise Denied('IT AI Manager did not reconcile this operation')
        verify(self.key, attestation.get('signature', ''), 'pbd-reconcile')

class Minotaur:
    def __init__(self, trusted_public_key):
        self.key = trusted_public_key

    def rewall(self, lease_id, result_bytes, attestation):
        expected = {'lease_id': lease_id, 'result_hash': digest(result_bytes)}
        if attestation.get('body') != expected:
            raise Denied('MINOTAUR did not confirm integrity')
        verify(self.key, attestation.get('signature', ''), 'pbd-integrity')

class LabyrinthShield:
    """Separate in-process containment state: OS isolation remains an absolute guard."""
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
        if manager.key != vault.gate_keys['IT_AI_Manager_v15.0'] or minotaur.key != vault.gate_keys['MINOTAUR']:
            raise ValueError('Authority keys must match the Vault trust roots')
        self.vault = vault
        self.validator = validator
        self.audit = audit
        self.quality = quality
        self.manager = manager
        self.minotaur = minotaur
        self.shield = shield

    def run(self, lease_id, scope, payload, proof, artifact, runner,
            quality_check, reconcile_check, integrity_check):
        body = None
        status = 'DENIED'
        receipt = None
        execution_receipt = None
        started = utc(self.vault.clock())

        try:
            # Consumed authority can never be reused, including after partial failure
            body = self.vault.claim(lease_id, scope, payload, proof)
            self.shield.check(body['execution_binding']['agent_public_key'])

            if type(runner) is not DevelopmentArtifactRunner or runner.validator != self.validator:
                raise Denied('Unapproved execution runner')

            runner.validate(artifact, scope)
            if digest(artifact.source) != body['execution_binding']['artifact_hash']:
                raise Denied('Executable differs from the lease-bound cryptographic contract')

            self.audit.preserve({'event': 'EXECUTION_START', 'lease_id': lease_id, 'artifact': artifact.name})

            result = runner.execute(artifact, scope, payload)
            if not isinstance(result, bytes):
                raise Denied('Adapter result must be bytes')

            # Execute systematic Twin-Gate cryptographic confirmation checks
            self.quality.verify_result(lease_id, result, quality_check)
            self.manager.reconcile(lease_id, result, reconcile_check)
            self.minotaur.rewall(lease_id, result, integrity_check)

            receipt = {
                'quality': quality_check,
                'reconciliation': reconcile_check,
                'integrity': integrity_check
            }
            status = 'VERIFIED'
        except BaseException:
            if body:
                self.shield.contain(body['execution_binding']['agent_public_key'])
            raise
        finally:
            # FIX: Properly aligned exception handler blocks to prevent compile and parse crashes
            try:
                execution_receipt = {
                    'execution_metadata': {
                        'lease_id': lease_id,
                        'executed_by': body['agent_identity'] if body else 'UNKNOWN',
                        'started_at_utc': started,
                        'completed_at_utc': utc(self.vault.clock()),
                        'post_condition_verified': status == 'VERIFIED'
                    },
                    'attestations': receipt
                }
                execution_receipt = self.audit.preserve_execution('LICYCLE_SETTLED', execution_receipt)
            finally:
                self.vault.revoke(lease_id)
                self.audit.preserve({'event': 'AUTHORITY_REVOKED', 'lease_id': lease_id})

        return {'lease_id': lease_id, 'status': status, 'execution_receipt': execution_receipt}
