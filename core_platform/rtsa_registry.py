"""Sanders Dash & Seal — distinct fail-closed RTSA role contracts.

These are individually addressable interfaces, NOT deployed intelligences.
Roles and names follow the owner's canonical 14-name register.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

PLATFORM = "Sanders Dash & Seal"

class RTSAStatus(str, Enum):
    SPECIFIED = "SPECIFIED"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    APPROVED = "APPROVED"

@dataclass(frozen=True)
class RTSARole:
    canonical_name: str
    slug: str
    mission: str
    status: RTSAStatus = RTSAStatus.SPECIFIED
    enabled: bool = False
    permitted_operations: tuple[str, ...] = ()
    prohibited_operations: tuple[str, ...] = (
        "external_execution", "credential_access", "notarization",
        "legal_filing", "financial_transfer", "production_deployment"
    )
    requires_twin_gate: bool = True
    requires_human_approval: bool = True

_ROLES = (
    ("ARCHITECT", "architect", "architecture/design"),
    ("ARCHIMEDES #43", "archimedes-43", "build engineering, coding, testing, deployment"),
    ("PROMETHEAN", "promethean", "adversarial reasoning and red-team evaluation"),
    ("HYDRA-Q", "hydra-q", "quantum-resistant cryptographic security"),
    ("LABYRINTH", "labyrinth", "zero-trust and attack-path security"),
    ("CERBERUS", "cerberus", "evidence, provenance, audit"),
    ("MINOTAUR", "minotaur", "behavioral intelligence and independent patrol"),
    ("CHORUS", "chorus", "multimodal synthesis and orchestration"),
    ("COBOL Synthetic AI", "cobol-synthetic-ai", "legacy systems and modernization"),
    ("SURN", "surn", "disaster and emergency intelligence"),
    ("JUGGERNAUT", "juggernaut", "execution integrity and verification"),
    ("Sanders Labyrinth Shield 🛡️", "sanders-labyrinth-shield", "independent defensive security environment"),
    ("Fraud RTSA 🚨", "fraud-rtsa", "fraud intelligence"),
    ("Operations RTSA 📊", "operations-rtsa", "operational reasoning and incident response"),
)

RTSA_ROLES = {name: RTSARole(name, slug, mission) for name, slug, mission in _ROLES}

class RTSAAuthorizationError(PermissionError):
    pass

def get_rtsa(name: str) -> RTSARole:
    try:
        return RTSA_ROLES[name]
    except KeyError as exc:
        raise RTSAAuthorizationError("UNKNOWN_RTSA_IDENTITY") from exc

def authorize_rtsa(name: str, operation: str) -> RTSARole:
    role = get_rtsa(name)
    if not role.enabled or role.status is not RTSAStatus.APPROVED:
        raise RTSAAuthorizationError("RTSA_NOT_DEPLOYED_OR_APPROVED")
    if operation in role.prohibited_operations or operation not in role.permitted_operations:
        raise RTSAAuthorizationError("RTSA_OPERATION_NOT_AUTHORIZED")
    # No actual execution here. Runtime still requires signed Twin-Gate,
    # independent identity, human approval, and durable evidence.
    return role
