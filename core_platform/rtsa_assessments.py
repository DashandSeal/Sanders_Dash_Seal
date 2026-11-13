"""Sanders Dash & Seal: 14 distinct deterministic RTSA offline assessment handlers.

These are bounded, auditable functional reference implementations, not AI models.
No network, filesystem, credential, or production action is performed.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from core_platform.rtsa_registry import RTSA_ROLES, get_rtsa

class AssessmentRejected(ValueError):
    pass

@dataclass(frozen=True)
class Assessment:
    rtsa: str
    role: str
    outcome: str
    findings: tuple[str, ...]
    input_digest: str
    execution_allowed: bool = False

def _list(value: object, key: str) -> list:
    if not isinstance(value, list) or len(value) > 100:
        raise AssessmentRejected("INVALID_LIST:" + key)
    return value

def _assess(name: str, data: dict) -> tuple[str, ...]:
    # One distinct, deterministic assessment policy per canonical RTSA identity.
    if name == "ARCHITECT":
        required = ("components", "interfaces", "trust_boundaries")
        return tuple("MISSING_" + key.upper() for key in required if not data.get(key)) or ("ARCHITECTURE_INPUTS_PRESENT",)
    if name == "ARCHIMEDES #43":
        return ("BUILD_TESTS_MISSING",) if not data.get("tests_passed") else ("BUILD_TESTS_REPORTED_PASSING_NOT_VERIFIED",)
    if name == "PROMETHEAN":
        return ("UNREVIEWED_THREAT_CASES",) if _list(data.get("threat_cases", []), "threat_cases") else ("NO_THREAT_CASES_SUBMITTED",)
    if name == "HYDRA-Q":
        return ("CRYPTO_POLICY_UNSPECIFIED",) if not data.get("algorithm_policy") else ("CRYPTO_POLICY_REVIEW_REQUIRED",)
    if name == "LABYRINTH":
        return ("TRUST_BOUNDARY_GAPS",) if not data.get("deny_by_default") else ("ZERO_TRUST_EVIDENCE_REQUIRED",)
    if name == "CERBERUS":
        return ("EVIDENCE_CHAIN_UNVERIFIED",) if not data.get("hash_chain_verified") else ("EXTERNAL_ANCHOR_STILL_REQUIRED",)
    if name == "MINOTAUR":
        return ("SHIELD_CLEARANCE_DENIED",) if not data.get("shield_clearance") else ("INDEPENDENT_ATTESTATION_REQUIRED",)
    if name == "CHORUS":
        return ("UNBOUNDED_MODALITY",) if not data.get("approved_modalities") else ("MULTIMODAL_POLICY_REVIEW_REQUIRED",)
    if name == "COBOL Synthetic AI":
        return ("LEGACY_COMPATIBILITY_UNTESTED",) if not data.get("compatibility_tests") else ("MIGRATION_REVIEW_REQUIRED",)
    if name == "SURN":
        return ("EMERGENCY_PLAN_MISSING",) if not data.get("recovery_plan") else ("EMERGENCY_DRILL_REQUIRED",)
    if name == "JUGGERNAUT":
        return ("EXECUTION_RECEIPT_MISSING",) if not data.get("receipt_digest") else ("RECEIPT_SIGNATURE_VERIFICATION_REQUIRED",)
    if name == "Sanders Labyrinth Shield 🛡️":
        return ("ISOLATION_REQUIRED",) if data.get("threat_detected") else ("DEFENSIVE_MONITORING_REQUIRED",)
    if name == "Fraud RTSA 🚨":
        return ("FRAUD_REVIEW_REQUIRED",) if data.get("suspicious_signals") else ("NO_SIGNALS_SUBMITTED",)
    if name == "Operations RTSA 📊":
        return ("INCIDENT_TRIAGE_REQUIRED",) if data.get("active_incidents") else ("NO_INCIDENTS_SUBMITTED",)
    raise AssessmentRejected("NO_ROLE_HANDLER")

def assess(name: str, data: dict) -> Assessment:
    role = get_rtsa(name)
    if not isinstance(data, dict):
        raise AssessmentRejected("INPUT_MUST_BE_OBJECT")
    if len(data) > 100:
        raise AssessmentRejected("INPUT_TOO_LARGE")
    try:
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise AssessmentRejected("INPUT_NOT_CANONICAL_JSON") from exc
    if len(canonical.encode("utf-8")) > 65536:
        raise AssessmentRejected("INPUT_TOO_LARGE")
    findings = _assess(name, data)
    return Assessment(rtsa=name, role=role.mission, outcome="ADVISORY_ONLY",
                      findings=findings, input_digest=sha256(canonical.encode()).hexdigest())
