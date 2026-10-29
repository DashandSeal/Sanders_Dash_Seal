"""
Module: core_platform.containment
Description: Sanders Dash & Seal: deterministic containment and state transitions.
No network calls, file deletions, or actual external service changes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Dict

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
    events: List[str] = field(default_factory=list)

class SandersLabyrinthShield:
    """Defensive environment state: Independent from Minotaur patrol."""
    
    def __init__(self):
        self.isolated = set()
        self.shelter_in_place = False

    def isolate(self, target: str) -> None:
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Invalid containment isolation target")
        self.isolated.add(target.strip())
        self.shelter_in_place = True

class MinotaurPatrol:
    """Separate patrol interface; approval must come from verified external attestation."""
    
    def __init__(self, shield: SandersLabyrinthShield):
        self.shield = shield

    def can_operate(self, target: str, verified_attestation: bool) -> bool:
        if not isinstance(target, str):
            return False
        return bool(verified_attestation and not self.shield.shelter_in_place and target.strip() not in self.shield.isolated)

class ContainmentController:
    """Manages secure incident isolation, evidence preservation, and multi-factor release workflows."""
    
    def __init__(self, shield: SandersLabyrinthShield):
        self.shield = shield
        self.incidents: Dict[str, Incident] = {}

    def deny_and_isolate(self, incident_id: str, target: str, reason: str) -> Incident:
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValueError("Invalid incident identifier format")
        if incident_id in self.incidents:
            raise ValueError("DUPLICATE_INCIDENT")
            
        self.shield.isolate(target)
        incident = Incident(
            incident_id=incident_id.strip(),
            reason=reason if isinstance(reason, str) else "Unspecified security containment trigger",
            events=["FREEZE", "ISOLATE", "PRESERVE_REQUIRED"]
        )
        self.incidents[incident_id.strip()] = incident
        return incident

    def mark_preserved(self, incident_id: str, *, audit_verified: bool) -> None:
        if not audit_verified:
            raise PermissionError("EVIDENCE_NOT_VERIFIED")
        if incident_id not in self.incidents:
            raise KeyError("Unknown incident identifier")
            
        incident = self.incidents[incident_id]
        incident.preserved = True
        incident.events.append("PRESERVED")

    def release(
        self,
        incident_id: str,
        *,
        quality_verified: bool,
        minotaur_recleared: bool,
        manager_reconciled: bool,
        human_approved: bool
    ) -> Incident:
        if incident_id not in self.incidents:
            raise KeyError("Unknown incident identifier")
            
        incident = self.incidents[incident_id]
        if not all((incident.preserved, quality_verified, minotaur_recleared, manager_reconciled, human_approved)):
            raise PermissionError("CONTAINMENT_RELEASE_DENIED")
            
        incident.quality_verified = True
        incident.shield_recleared = True
        incident.reconciled = True
        incident.events.append("RELEASE_AUTHORIZED")
        
        # Physical isolation removal is intentionally left to a separately
        # signed, approved operational adapter; never clear shield state here.
        return incident
