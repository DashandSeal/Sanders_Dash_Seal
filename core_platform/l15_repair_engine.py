"""
Module: core_platform.l15_repair_engine
Architectural Layer: Sanders Sidecar L15 Repair Evaluation Matrix
Description: Safe dry-run simulation and structural repair evaluation engine.
             Processes multi-hypothesis temporal and causal counterfactual records.
             Never executes destructive commands or exercises runtime production authority.
"""

from dataclasses import dataclass
import hashlib
import json

DIMENSIONS = (
    "causal", "temporal", "counterfactual", "constraint", "systems",
    "adversarial", "probabilistic", "deterministic_verification",
    "multi_hypothesis", "dependency_blast_radius", "security",
    "governance", "self_critique", "state_reconciliation", "proof_of_outcome"
)

PHASES = (
    "observe", "verify", "diagnose", "simulate", "challenge",
    "authorize", "repair", "reconstruct", "verify_postcondition",
    "commit_or_rollback", "harden", "prove"
)

class RepairDenied(PermissionError):
    pass

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode()).hexdigest()

def validate_evidence(evidence):
    if not isinstance(evidence, dict) or any(
        not isinstance(evidence.get(k), dict) or not evidence[k] for k in DIMENSIONS
    ):
        raise RepairDenied("All fifteen independent reasoning evidence records are required")
    # FIX: Corrected NameError from _digest to your defined digest function
    return digest({k: evidence[k] for k in DIMENSIONS})

@dataclass(frozen=True)
class RepairProposal:
    incident_id: str
    principal_id: str
    sidecar_id: str
    action: str
    capability: str
    preconditions: tuple
    blast_radius: tuple
    rollback_steps: tuple
    postconditions: tuple
    evidence_digest: str

    def __post_init__(self):
        if not all(isinstance(getattr(self, name), str) and getattr(self, name).strip()
            for name in ("incident_id", "principal_id", "sidecar_id",
                         "action", "capability", "evidence_digest")):
            raise RepairDenied("Complete repair identity and action required")

        if self.principal_id == self.sidecar_id:
            raise RepairDenied("Sidecar and principal identities must remain distinct")

        if len(self.evidence_digest) != 64 or any(
            c not in "0123456789abcdef" for c in self.evidence_digest
        ):
            raise RepairDenied("Invalid evidence digest")

        for name in ("preconditions", "blast_radius", "rollback_steps", "postconditions"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or not value or any(
                not isinstance(v, str) or not v.strip() for v in value
            ):
                raise RepairDenied("Preconditions, blast radius, rollback and postconditions required")

class RepairSession:
    """Local hash-chained dry run. Never grants production execution or approval."""

    def __init__(self, proposal, evidence):
        if not isinstance(proposal, RepairProposal):
            raise RepairDenied("RepairProposal required")
        if validate_evidence(evidence) != proposal.evidence_digest:
            raise RepairDenied("Evidence mismatch")

        self.proposal = proposal
        self.phase = "observe"
        self.audit = []
        self._prior = '0' * 64
        self._record("created", {"incident_id": proposal.incident_id})

    def _record(self, kind, details):
        entry = {"prior": self._prior, "kind": kind, "details": details}
        entry["digest"] = digest(entry)
        self.audit.append(entry)
        self._prior = entry["digest"]

    def advance(self, next_phase, *, independent_review=False):
        current = PHASES.index(self.phase)
        if current + 1 >= len(PHASES) or PHASES[current + 1] != next_phase:
            raise RepairDenied("Out-of-order repair lifecycle transition")

        if next_phase in ("authorize", "repair", "commit_or_rollback"):
            raise RepairDenied("Authorization and execution unavailable in dry-run engine")

        if next_phase in ("challenge", "verify_postcondition", "prove") and independent_review is not True:
            raise RepairDenied("Independent review required")

        self.phase = next_phase
        self._record("phase", {"phase": next_phase})
        return self.phase

    def audit_valid(self):
        prior = '0' * 64
        for entry in self.audit:
            if entry.get("prior") != prior or entry.get("digest") != digest(
                {k: v for k, v in entry.items() if k != "digest"}
            ):
                return False
            prior = entry["digest"]
        return True

    def simulation_report(self):
        return {
            "incident_id": self.proposal.incident_id,
            "principal_id": self.proposal.principal_id,
            "sidecar_id": self.proposal.sidecar_id,
            "action": self.proposal.action,
            "blast_radius": list(self.proposal.blast_radius),
            "simulation_audit_trail": self.audit,
            "chain_valid": self.audit_valid()
        }
