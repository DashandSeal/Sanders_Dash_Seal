"""Shared upgrade continuity guard for platform and independently named RTSAs.

Baselines come from trusted owner configuration. The injected verifier must obtain
independent, artifact-bound candidate evidence; proposal claims are insufficient.
This wrapper preserves the underlying executor's PBD, halt and Twin-Gate checks.
"""
from copy import deepcopy


class IdentityContinuityDenied(ValueError):
    pass


def require_continuity(baseline, candidate):
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise IdentityContinuityDenied("Identity records required")
    for field in ("identity_id", "role", "authority_boundary"):
        if not baseline.get(field) or candidate.get(field) != baseline[field]:
            raise IdentityContinuityDenied("Identity or authority boundary changed")
    for field in ("capabilities", "protections"):
        old, new = baseline.get(field), candidate.get(field)
        if any(not isinstance(value, list) or not value or
               any(not isinstance(item, str) or not item.strip() for item in value)
               or len(set(value)) != len(value) for value in (old, new)):
            raise IdentityContinuityDenied("Explicit capability/protection inventories required")
        if not set(old).issubset(new):
            raise IdentityContinuityDenied("Historical capability or protection removed")
    return True


class IdentityPreservingExecutor:
    def __init__(self, executor, baselines, candidate_verifier):
        if not isinstance(baselines, dict) or not baselines or not callable(candidate_verifier):
            raise IdentityContinuityDenied("Trusted inventory and verifier required")
        identities = []
        for baseline in baselines.values():
            require_continuity(baseline, baseline)
            identities.append(baseline["identity_id"])
        if len(set(identities)) != len(identities):
            raise IdentityContinuityDenied("Components must retain distinct identities")
        self._baselines = deepcopy(baselines)
        self._executor = executor
        self._verifier = candidate_verifier

    def stage(self, record, artifact_path):
        trusted_record = deepcopy(record)
        baseline = self._baselines.get(trusted_record.get("component"))
        if baseline is None:
            raise IdentityContinuityDenied("Unregistered component")
        candidate = self._verifier(deepcopy(trusted_record), artifact_path)
        require_continuity(baseline, candidate)
        return self._executor.stage(trusted_record, artifact_path)

    def verify(self, record):
        return self._executor.verify(record)

    def rollback(self, record):
        # Recovery remains available, including while an owner halt is active.
        return self._executor.rollback(record)
