"""Sanders Dash & Seal: deterministic containment and state transitions.

No network calls, file deletions, or actual external service changes.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

class Phase(str, Enum):
    REQUEST = "REQUEST"
    CLEARANCE = "CLEARANCE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    PRESERVE = "PRESERVE"
    REVOKE = "REVOKE"
    CONTAINED = "CONTAINED"
    COMPLETE = "COMPLETE"

@dataclass
class Incident:
    incident_id: str
    reason: str
    frozen: bool = True
    integration_isolated: bool = True
    preserved: bool = False
    quality_verified: bool = False
    shield_recleared: bool = False
    reconciled: bool = False
    events: list[str] = field(default_factory=list)

class SandersLabyrinthShield:
    """Defensive environment state; independent from MINOTAUR patrol."""
    def __init__(self):
        self.isolated: set[str] = set()
        self.shelter_in_place = False

    def isolate(self, target: str) -> None:
        self.isolated.add(target)
        self.shelter_in_place = True

class MinotaurPatrol:
    """Separate patrol interface; approval must come from verified external attestation."""
    def __init__(self, shield: SandersLabyrinthShield):
        self.shield = shield

    def can_operate(self, target: str, *, verified_attestation: bool) -> bool:
        return verified_attestation and not self.shield.shelter_in_place and target not in self.shield.isolated

class ContainmentController:
    def __init__(self, shield: SandersLabyrinthShield):
        self.shield = shield
        self.incidents: dict[str, Incident] = {}

    def deny_and_isolate(self, incident_id: str, target: str, reason: str) -> Incident:
        if incident_id in self.incidents:
            raise ValueError("DUPLICATE_INCIDENT")
        self.shield.isolate(target)
        event = Incident(incident_id=incident_id, reason=reason,
                         events=["FREEZE", "ISOLATE", "PRESERVE_REQUIRED"])
        self.incidents[incident_id] = event
        return event

    def mark_preserved(self, incident_id: str, *, audit_verified: bool) -> None:
        if not audit_verified:
            raise PermissionError("EVIDENCE_NOT_VERIFIED")
        self.incidents[incident_id].preserved = True
        self.incidents[incident_id].events.append("PRESERVED")

    def release(self, incident_id: str, *, quality_verified: bool,
                minotaur_recleared: bool, manager_reconciled: bool,
                human_approved: bool) -> None:
        incident = self.incidents[incident_id]
        if not all((incident.preserved, quality_verified,
                    minotaur_recleared, manager_reconciled, human_approved)):
            raise PermissionError("CONTAINMENT_RELEASE_DENIED")
        incident.quality_verified = True
        incident.shield_recleared = True
        incident.reconciled = True
        incident.events.append("RELEASE_AUTHORIZED")
        # Physical isolation removal is intentionally left to a separately
        # signed, approved operational adapter; never clear shield state here.
