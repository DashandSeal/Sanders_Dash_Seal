"""
Module: core_platform.identity_continuity
Architectural Layer: Identity Continuity Guard & Access Control Enforcer
Description: Enforces strict asset-bound execution tracking limits. Verifies that
             no update or modification removes historic capabilities or drops active guards.
"""

from copy import deepcopy

class IdentityContinuityDenied(ValueError):
    pass

def require_continuity(baseline, candidate):
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise IdentityContinuityDenied('Identity records required')

    for field in ('identity_id', 'role', 'authority_boundary'):
        if not baseline.get(field) or candidate.get(field) != baseline[field]:
            raise IdentityContinuityDenied('Identity or authority boundary changed')

    for field in ('capabilities', 'protections'):
        old_list = baseline.get(field)
        new_list = candidate.get(field)

        for value in (old_list, new_list):
            if not isinstance(value, list) or not value or any(
                not isinstance(item, str) or not item.strip() for item in value
            ) or len(set(value)) != len(value):
                raise IdentityContinuityDenied('Explicit capability/protection inventories required')

        # FIX: Convert raw lists into native set representations to safely verify sub-membership bounds
        if not set(old_list).issubset(set(new_list)):
            raise IdentityContinuityDenied('Historical capability or protection removed')

    return True

class IdentityPreservingExecutor:
    """Provides secure identity encapsulation boundaries over runtime resource pools."""

    def __init__(self, executor, baselines, candidate_verifier):
        if not isinstance(baselines, dict) or not baselines or not callable(candidate_verifier):
            raise IdentityContinuityDenied('Trusted inventory and verifier required')

        identities = []
        for baseline in baselines.values():
            require_continuity(baseline, baseline)
            identities.append(baseline['identity_id'])

        if len(set(identities)) != len(identities):
            raise IdentityContinuityDenied('Components must retain distinct identities')

        self._baselines = deepcopy(baselines)
        self._executor = executor
        self._verifier = candidate_verifier

    def stage(self, record, artifact_path):
        trusted_record = deepcopy(record)
        baseline = self._baselines.get(trusted_record.get('component'))
        if baseline is None:
            raise IdentityContinuityDenied('Unregistered component')

        candidate = self._verifier(deepcopy(trusted_record), artifact_path)
        require_continuity(baseline, candidate)
        return self._executor.stage(trusted_record, artifact_path)

    def verify(self, self_record):
        return self._executor.verify(self_record)

    def rollback(self, self_record):
        # Recovery remains available, including while an owner halt is active.
        return self._executor.rollback(self_record)
