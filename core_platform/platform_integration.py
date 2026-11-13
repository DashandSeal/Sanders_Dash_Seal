"""
Module: core_platform.platform_integration
Architectural Layer: MASTER-Governed System Integration Boundary
Description: Connects existing intake, human authority review, technical dispatch, 
             and upgrade sidecars without merging their independent authority domains.
             Guarantees fail-closed orchestration metrics.
"""

from upgrade_sidecar import require_core_laws

class IntegrationDenied(Exception):
    pass

class SandersDashSealIntegration:
    """Fail-closed composition of independently governed existing components."""
    
    PLATFORM = 'Sanders Dash & Seal'

    def __init__(self, cases, authority, dispatcher, sidecar, audit, core_laws=None):
        # Gracefully handle cold-start bootstrap phases where core_laws is uninitialized
        if core_laws is not None:
            require_core_laws(core_laws)
            
        components = (cases, authority, dispatcher, sidecar, audit)
        if any(component is None for component in components):
            raise IntegrationDenied('All five independent components are required')
            
        # Ensure all registered components are separate instances to preserve domain boundaries
        if len({id(component) for component in components}) != len(components):
            raise IntegrationDenied('Independent roles cannot be merged')
            
        if authority.cases is not cases:
            raise IntegrationDenied('Authority review must use the same case registry')
            
        if dispatcher.audit is not audit or authority.audit is not audit:
            raise IntegrationDenied('Shared glass-box evidence boundary required')
            
        self.cases = cases
        self.authority = authority
        self.dispatcher = dispatcher
        self.sidecar = sidecar
        self.audit = audit

    def intake(self, case_id, jurisdiction, service, requester):
        self.audit.preserve('stage', 'CASE_INTAKE_INTENT', 'case_id', case_id,
                           'platform', self.PLATFORM)
        result = self.cases.create(case_id, jurisdiction, service, requester)
        self.audit.preserve('stage', 'CASE_AWAITING_HUMAN_REVIEW',
                           'case_id', case_id, 'status', result['status'])
        return result

    def human_review(self, case_id, reviewer, notary_identity, evidence):
        result = self.authority.review(case_id, reviewer, notary_identity, evidence)
        if result.get('notarial_act_executed') is not False:
            raise IntegrationDenied('Review cannot imply a notarial act')
        return result

    def request_technical_work(self, task_id, role, capability, component, specification_ref, evidence):
        if not specification_ref.startswith('MASTER '):
            raise IntegrationDenied('Technical work must reference MASTER')
        return self.dispatcher.submit(task_id, role, capability, component, specification_ref, evidence)

    def propose_upgrade(self, sample_id, component, version, artifact_hash, evidence):
        if not isinstance(evidence, dict) or not evidence.get('master_section'):
            raise IntegrationDenied('MASTER section traceability required')
        self.audit.preserve('stage', 'UPGRADE_INTENT', 'request_id', sample_id,
                           'component', component,
                           'master_section', evidence['master_section'])
        return self.sidecar.propose(sample_id, component, version, artifact_hash, evidence)

    def execute_notarial_act(self, *args, **kwargs):
        raise IntegrationDenied('Independent live provider and jurisdiction authority required')

    def deploy(self, *args, **kwargs):
        raise IntegrationDenied('Signed PBD, Twin-Gate, Vault and production runtime required')
