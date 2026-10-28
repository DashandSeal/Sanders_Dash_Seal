"""Sanders synthetic AI Sidecar: historical L15 contracts, fail-closed validation.

Contracts derive from the October 4, 2026 L15 disclosure. They do not
themselves supply synthetic inference, production cryptography, or deployment.
"""
import hashlib
import json

NAME = "Sanders synthetic AI Sidecar"
L15 = ("causal_reasoning", "temporal_reasoning", "counterfactual_evaluation",
       "constraint_satisfaction", "systems_reasoning", "adversarial_challenge",
       "probabilistic_uncertainty", "deterministic_verification",
       "multi_hypothesis_diagnosis", "dependency_blast_radius",
       "security_analysis", "governance_authority", "self_critique",
       "state_reconciliation", "proof_of_outcome")
SLOTS = ("current", "candidate", "previous_known_good", "recovery")
REPAIR_FIELDS = ("incident_id", "principal_id", "sidecar_id", "observed_state",
                 "expected_state", "root_cause_hypotheses", "evidence",
                 "proposed_actions", "required_capabilities", "preconditions",
                 "blast_radius", "rollback_plan", "postconditions",
                 "verification_tests", "policy_version",
                 "specification_version", "build_digest")


class SidecarContractError(ValueError):
    pass


def require_l15_evidence(evidence):
    if not isinstance(evidence, dict):
        raise SidecarContractError("L15 evidence must be an object")
    missing = [name for name in L15 if not evidence.get(name)]
    if missing:
        raise SidecarContractError("Missing L15 evidence: " + ", ".join(missing))
    return True


def require_repair_plan(plan, externally_authorized_capabilities):
    if not isinstance(plan, dict):
        raise SidecarContractError("Repair plan must be an object")
    missing = [name for name in REPAIR_FIELDS if name not in plan]
    if missing:
        raise SidecarContractError("Missing RepairPlan fields: " + ", ".join(missing))
    if not plan["principal_id"] or not plan["sidecar_id"] or plan["principal_id"] == plan["sidecar_id"]:
        raise SidecarContractError("Independent sidecar identity required")
    caps = plan["required_capabilities"]
    if not isinstance(caps, list) or any(not isinstance(cap, str) for cap in caps):
        raise SidecarContractError("Invalid capability list")
    if not set(caps).issubset(set(externally_authorized_capabilities)):
        raise SidecarContractError("Repair cannot expand its authority envelope")
    if not plan["rollback_plan"] or not plan["postconditions"] or not plan["verification_tests"]:
        raise SidecarContractError("Rollback and independent verification requirements mandatory")
    return True


class EvidenceChain:
    """In-memory hash chain for local verification, not immutable audit storage."""
    def __init__(self):
        self.records = []

    def append(self, event):
        if not isinstance(event, dict) or not event:
            raise SidecarContractError("Nonempty evidence required")
        prior = self.records[-1]["hash"] if self.records else "0" * 64
        body = {"prior": prior, "event": event}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        record = {**body, "hash": digest}
        self.records.append(record)
        return record

    def verify(self):
        prior = "0" * 64
        for record in self.records:
            body = {"prior": record["prior"], "event": record["event"]}
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if record["prior"] != prior or record["hash"] != digest:
                return False
            prior = digest
        return True
