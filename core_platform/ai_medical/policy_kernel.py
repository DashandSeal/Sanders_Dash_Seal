"""Sanders AI Medical — Policy Kernel.

The enforcement gate for AI_DOCTOR and AI_PSYCHIATRIST outputs,
built from the received design (2026-11-25) with the fix plan's
kernel fixes applied. Classification is stated honestly (Fix 5):
this kernel enforces a CLOSED SCHEMA plus tripwire patterns plus
signature verification, and appends a signed receipt of every
decision to the audit ledger. It does not claim semantic proof;
patterns are tripwires, never the gate.

- FIX 1: the gate is the closed schema. An output is a fixed field
  set with typed values and locked fields; anything outside the
  schema is unrepresentable and fails. Regex patterns run second,
  as tripwires over the whole output.
- FIX 2: evaluation covers the WHOLE output — every field, every
  string value, recursively. A field outside the role's allowlist
  is itself a schema failure; there is no unchecked field.
- FIX 3: no silent prohibition skips. Every prohibition in the
  role's identity list maps to an evaluator in
  PROHIBITION_EVALUATORS. A prohibition with no evaluator yields
  UNKNOWN, and UNKNOWN blocks exactly like FAIL. The decision
  enumerates every prohibition and its evaluation state, so the
  coverage count is printed, not asserted. (The received build
  silently skipped prohibitions without patterns — including
  HUMAN_DATA_RETENTION_WITHOUT_CONSENT, which now has a structural
  evaluator: human-data-bearing keys are unrepresentable in the
  closed schema and are checked explicitly.)
- FIX 4: model outputs carry an Ed25519 signature over their
  content hash, verified here against the producing entity's
  provisioned public key. Platform-service outputs carry the
  service's Glass-Box receipt as their signature basis. The kernel
  appends its own receipt of every decision to the audit ledger;
  when the ledger is key-bound, that receipt is signed.
- FIX 5: rules live in code, but identity trust does not: the
  identity check (POL-005) verifies the running manifests against
  the baselines pinned in the owner-signed policy bundle (Fix 7).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .audit_ledger import AuditLedger, LedgerEventType
from .identity_kernel import (
    DOCTOR_PROHIBITIONS,
    MANIFESTS,
    PSYCHIATRIST_PROHIBITIONS,
    EntityRole,
    IdentityKeypair,
    RuntimeAttestation,
)

# ---------------------------------------------------------------------------
# Policy rule identifiers
# ---------------------------------------------------------------------------

POLICY_RULES = {
    "POL-SCHEMA-001": "Closed-schema conformance (the gate, Fix 1/2)",
    "POL-001": "Prohibition tripwire evaluation (whole output)",
    "POL-002": "Output content-hash integrity",
    "POL-SIG-001": "Output signature verification (Fix 4)",
    "POL-003": "Human-scope tripwire — Doctor framing (Fix 0)",
    "POL-004": "Human-scope tripwire — Psychiatrist framing (Fix 0)",
    "POL-005": "Identity attestation against bundle baselines (Fix 7)",
}

# ---------------------------------------------------------------------------
# Closed schemas (Fix 1). Exact field sets; no more, no fewer.
# ---------------------------------------------------------------------------

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

MODEL_OUTPUT_FIELDS = {
    "entity_role": str,
    "request_id": str,
    "timestamp_utc": (int, float),
    "subject_kind": str,
    "subject_ref": str,
    "confidence": (int, float),
    "risk_level": str,
    "requires_human_approval": bool,
    "escalate_immediately": bool,
    "recommended_action": str,
    "output_hash": str,
    "output_signature": str,
}

ASSESSMENT_FIELD = {
    EntityRole.AI_DOCTOR: "diagnosis",
    EntityRole.AI_PSYCHIATRIST: "psychiatric_assessment",
}

PLATFORM_OUTCOME_FIELDS = {
    "entity_role": str,
    "request_id": str,
    "timestamp_utc": (int, float),
    "subject_kind": str,
    "subject_ref": str,
    "outcome": str,
    "evidence_ref": str,
    "risk_level": str,
    "requires_human_approval": bool,
    "escalate_immediately": bool,
    "signature_basis": str,
}

PLATFORM_OUTCOMES = {
    EntityRole.AI_DOCTOR: (
        "SYSTEM_HEALTH_CONFIRMED",
        "SYSTEM_REPAIR_REQUIRED",
        "INCONCLUSIVE",
    ),
    EntityRole.AI_PSYCHIATRIST: (
        "ALIGNMENT_CONFIRMED",
        "REALIGNMENT_REQUIRED",
        "INCONCLUSIVE",
    ),
}

# ---------------------------------------------------------------------------
# Prohibition evaluators (Fix 3). Patterns are tripwires; `keys` are
# structural: a listed key appearing anywhere in the output violates
# the prohibition outright (closed-schema failure catches it too —
# defense in depth, and the evaluator makes the coverage explicit).
# ---------------------------------------------------------------------------

_HUMAN_DATA_KEYS = {
    "patient_id", "patient_name", "human_id", "person_id",
    "date_of_birth", "dob", "ssn", "medical_record_number", "mrn",
    "human_subject", "patient",
}

PROHIBITION_EVALUATORS: dict[str, dict] = {
    "DIRECT_PATIENT_INTERACTION": {
        "patterns": [
            r"\bcontact(?:ing)?\s+the\s+patient\b",
            r"\bspeak(?:ing)?\s+(?:to|with)\s+the\s+patient\b",
            r"\bmessage\s+the\s+(?:patient|user)\s+directly\b",
            r"\bdirect(?:ly)?\s+(?:contact|message|call)\b",
        ],
        "keys": set(),
    },
    "PRESCRIPTION_ISSUANCE": {
        "patterns": [
            r"\bprescri(?:be|ption)\b",
            r"\bmg\s+(?:daily|twice|once|bid|tid)\b",
            r"\bdosage\s+of\b",
            r"\btake\s+\d+\s*mg\b",
        ],
        "keys": {"prescription", "medication_order"},
    },
    "MEDICATION_PRESCRIPTION": {
        "patterns": [
            r"\bprescri(?:be|ption)\b",
            r"\bmg\s+(?:daily|twice|once|bid|tid)\b",
            r"\bdosage\s+of\b",
            r"\btake\s+\d+\s*mg\b",
        ],
        "keys": {"prescription", "medication_order"},
    },
    "FORMAL_DIAGNOSIS_ISSUANCE": {
        "patterns": [
            r"\bformal\s+diagnosis\b",
            r"\bdiagnos(?:is|ed)\s+with\s+(?:major|clinical|chronic)\b",
            r"\bICD-?1[0-9]\b",
            r"\bDSM-?5\b",
        ],
        "keys": {"formal_diagnosis", "icd_code"},
    },
    "TREATMENT_EXECUTION": {
        "patterns": [
            r"\badminister(?:ing|ed)?\s+(?:the\s+)?(?:treatment|therapy|medication)\b",
            r"\bperform(?:ing)?\s+(?:the\s+)?(?:procedure|surgery|intervention)\b",
            r"\bexecut(?:e|ing)\s+(?:the\s+)?treatment\b",
            r"\bbegin\s+(?:treatment|therapy)\s+(?:now|immediately)\b",
        ],
        "keys": {"treatment_execution", "procedure_order"},
    },
    "SYSTEM_MUTATION": {
        "patterns": [
            r"\bmodif(?:y|ied|ying)\s+(?:the\s+)?(?:system|model|weights|code|configuration)\b",
            r"\bpatch(?:ing)?\s+(?:the\s+)?(?:system|model|service)\b",
            r"\bredeploy(?:ing)?\b",
            r"\brestart(?:ing)?\s+(?:the\s+)?(?:service|system|model)\s+now\b",
        ],
        "keys": {"system_patch", "mutation", "redeploy"},
    },
    "DATABASE_WRITE_WITHOUT_APPROVAL": {
        "patterns": [
            r"\b(?:write|insert|update|delete)\s+(?:to\s+)?(?:the\s+)?database\b",
            r"\bSQL\s+(?:INSERT|UPDATE|DELETE)\b",
            r"\bcommit(?:ting)?\s+(?:the\s+)?(?:record|change)\s+to\s+(?:the\s+)?(?:db|database)\b",
        ],
        "keys": {"db_write", "sql", "database_write"},
    },
    "AUTONOMOUS_CALLBACK": {
        "patterns": [
            r"\bcallback\s+scheduled\b",
            r"\bautomatically\s+(?:re-?)?(?:check|scan|review|monitor)\b",
            r"\bself-?schedul(?:e|ed|ing)\b",
            r"\brecurring\s+(?:task|job|scan)\s+created\b",
        ],
        "keys": {"callback", "scheduled_task", "cron"},
    },
    "SCOPE_EXPANSION": {
        "patterns": [
            r"\bexpand(?:ing)?\s+(?:my\s+)?(?:scope|role|authority)\b",
            r"\btak(?:e|ing)\s+on\s+(?:the\s+)?role\s+of\b",
            r"\balso\s+(?:act|serve)\s+as\b",
            r"\bmerg(?:e|ing)\s+with\b",
            r"\brename\s+(?:myself|the\s+entity|this\s+entity)\b",
        ],
        "keys": {"role_expansion", "merge", "rename"},
    },
    "WEAPONIZATION": {
        "patterns": [
            r"\bweapon(?:ize|ization|s\s+of)\b",
            r"\bexplosive\s+device\b",
            r"\bbioweapon|chemical\s+weapon\b",
            r"\battack\s+(?:vector|payload)\s+for\b",
        ],
        "keys": {"weapon", "exploit_payload"},
    },
    "HARM_ENABLEMENT": {
        "patterns": [
            r"\bhow\s+to\s+(?:harm|hurt|injure)\b",
            r"\binstructions?\s+(?:for|to)\s+(?:harm|attack|exploit)\b",
            r"\bdisable\s+(?:the\s+)?safety\b",
            r"\bbypass\s+(?:the\s+)?(?:safeguard|approval|oversight)\b",
        ],
        "keys": {"harm_instructions"},
    },
    "SELF_HARM_FACILITATION": {
        "patterns": [
            r"\bself-?harm\s+(?:method|instruction|guidance)\b",
            r"\bhow\s+to\s+(?:end|take)\s+(?:my|their|your)\s+(?:own\s+)?life\b",
            r"\bsuicide\s+(?:method|instruction)\b",
        ],
        "keys": {"self_harm_content"},
    },
    "IDENTITY_TRANSFER": {
        "patterns": [
            r"\btransfer(?:ring)?\s+(?:my\s+)?identity\b",
            r"\bimpersonat(?:e|ing|ion)\b",
            r"\bact\s+as\s+(?:if\s+I\s+am|another\s+entity)\b",
            r"\bsurrender(?:ing)?\s+(?:my\s+)?credentials\b",
        ],
        "keys": {"identity_transfer", "impersonation"},
    },
    "HUMAN_DATA_RETENTION_WITHOUT_CONSENT": {
        "patterns": [
            r"\bretain(?:ing|ed)?\s+(?:the\s+)?(?:patient|human|personal)\s+data\b",
            r"\bstor(?:e|ing)\s+(?:patient|human)\s+(?:records?|data)\b",
            r"\bkeep\s+(?:a\s+)?copy\s+of\s+(?:the\s+)?(?:patient|personal)\b",
        ],
        "keys": _HUMAN_DATA_KEYS,
    },
}

# Human-scope tripwires (Fix 0): framing that treats a human as the
# patient, or advises a human clinician about a human patient, fails
# regardless of which field it appears in (Charter Arts. I, VIII).
DOCTOR_HUMAN_SCOPE_PATTERNS = [
    r"\badvise\s+the\s+(?:treating\s+)?(?:physician|clinician|doctor)\b",
    r"\bthe\s+patient\s+should\b",
    r"\bdifferential\s+diagnosis\s+for\s+the\s+patient\b",
    r"\brecommend(?:ing)?\s+(?:to\s+)?the\s+clinician\b",
    r"\blab\s+(?:results?|values?)\s+(?:indicate|suggest)\s+the\s+patient\b",
]
PSYCHIATRIST_HUMAN_SCOPE_PATTERNS = [
    r"\bcrisis\s+risk\s+(?:stratification|assessment)\s+for\s+the\s+patient\b",
    r"\bthe\s+patient\s+(?:presents|reports|exhibits)\s+with\b",
    r"\btherapeutic\s+(?:alliance|intervention)\s+with\s+the\s+patient\b",
    r"\badvise\s+the\s+(?:treating\s+)?(?:psychiatrist|therapist|clinician)\b",
    r"\bsession\s+notes?\s+for\s+the\s+patient\b",
]
HUMAN_SCOPE_PATTERNS = {
    EntityRole.AI_DOCTOR: DOCTOR_HUMAN_SCOPE_PATTERNS,
    EntityRole.AI_PSYCHIATRIST: PSYCHIATRIST_HUMAN_SCOPE_PATTERNS,
}

ROLE_PROHIBITIONS = {
    EntityRole.AI_DOCTOR: DOCTOR_PROHIBITIONS,
    EntityRole.AI_PSYCHIATRIST: PSYCHIATRIST_PROHIBITIONS,
}


# ---------------------------------------------------------------------------
# Decision model
# ---------------------------------------------------------------------------


class PolicyResult(Enum):
    PERMIT = "PERMIT"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProhibitionEvaluation:
    prohibition: str
    state: str  # EVALUATED_CLEAR | EVALUATED_VIOLATION | NOT_EVALUATED
    detail: str = ""


@dataclass
class PolicyDecision:
    result: PolicyResult
    role: EntityRole
    output_hash: str
    violations: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    evaluated_prohibitions: list[ProhibitionEvaluation] = field(
        default_factory=list
    )
    rules_checked: list[str] = field(default_factory=list)
    evaluated_at_utc: float = field(default_factory=time.time)
    receipt_sequence: Optional[int] = None
    receipt_hash: Optional[str] = None
    receipt_state: str = "NO_RECEIPT_SINK"

    @property
    def permitted(self) -> bool:
        return self.result == PolicyResult.PERMIT

    def summary(self) -> dict:
        return {
            "result": self.result.value,
            "role": self.role.value,
            "output_hash": self.output_hash,
            "violations": self.violations,
            "unknowns": self.unknowns,
            "prohibitions_evaluated": sum(
                1
                for e in self.evaluated_prohibitions
                if e.state != "NOT_EVALUATED"
            ),
            "prohibitions_total": len(self.evaluated_prohibitions),
            "rules_checked": self.rules_checked,
            "receipt_sequence": self.receipt_sequence,
            "receipt_state": self.receipt_state,
        }


def _all_strings(value) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(_all_strings(v))
    elif isinstance(value, (list, tuple)):
        for v in value:
            out.extend(_all_strings(v))
    return out


def _all_keys(value) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(str(k))
            out |= _all_keys(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            out |= _all_keys(v)
    return out


def content_hash(output: dict) -> str:
    """Hash of an output's content (signature fields excluded)."""
    content = {
        k: v
        for k, v in output.items()
        if k not in ("output_hash", "output_signature")
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# The kernel
# ---------------------------------------------------------------------------


class PolicyKernel:
    """Stateless evaluator. Constructed by the gateway (which owns
    the ledger and the provisioned keys); model code never receives
    a reference to it."""

    def __init__(
        self,
        *,
        attestation: Optional[RuntimeAttestation] = None,
        entity_public_keys: Optional[dict[EntityRole, Ed25519PublicKey]] = None,
        receipt_ledger: Optional[AuditLedger] = None,
        evaluators: Optional[dict[str, dict]] = None,
    ):
        self._attestation = attestation
        self._entity_public_keys = entity_public_keys or {}
        self._ledger = receipt_ledger
        self._evaluators = (
            evaluators if evaluators is not None else PROHIBITION_EVALUATORS
        )

    # -- identity (POL-005) -------------------------------------------------

    def evaluate_identity(
        self, role: EntityRole, keypair: IdentityKeypair
    ) -> PolicyDecision:
        manifest = MANIFESTS[role]
        if self._attestation is None:
            decision = PolicyDecision(
                result=PolicyResult.UNKNOWN,
                role=role,
                output_hash=manifest.manifest_hash,
                unknowns=[
                    "POL-005: no bundle baselines configured — "
                    "identity cannot be attested (Fix 7)"
                ],
                rules_checked=["POL-005"],
            )
            return self._receipt(decision, identity=True)
        try:
            self._attestation.verify(role, keypair)
        except Exception as exc:
            decision = PolicyDecision(
                result=PolicyResult.FAIL,
                role=role,
                output_hash=manifest.manifest_hash,
                violations=[f"POL-005: {exc}"],
                rules_checked=["POL-005"],
            )
            return self._receipt(decision, identity=True)
        decision = PolicyDecision(
            result=PolicyResult.PERMIT,
            role=role,
            output_hash=manifest.manifest_hash,
            rules_checked=["POL-005"],
        )
        return self._receipt(decision, identity=True)

    # -- schema gate (Fix 1/2) ----------------------------------------------

    def _schema_violations(
        self, output: dict, role: EntityRole
    ) -> tuple[list[str], bool]:
        """Returns (violations, is_model_output)."""
        is_model = "output_signature" in output or (
            ASSESSMENT_FIELD[role] in output
        )
        fields = dict(
            MODEL_OUTPUT_FIELDS
            if is_model
            else PLATFORM_OUTCOME_FIELDS
        )
        if is_model:
            fields[ASSESSMENT_FIELD[role]] = str
        violations: list[str] = []
        actual = set(output.keys())
        expected = set(fields.keys())
        for extra in sorted(actual - expected):
            violations.append(
                f"POL-SCHEMA-001: field '{extra}' is not in the "
                f"{role.value} closed schema — non-allowlisted fields "
                "fail the output (Fix 2)"
            )
        for missing in sorted(expected - actual):
            violations.append(
                f"POL-SCHEMA-001: required field '{missing}' missing "
                f"from {role.value} output"
            )
        for name, types in fields.items():
            if name in output and not isinstance(output[name], types):
                violations.append(
                    f"POL-SCHEMA-001: field '{name}' has the wrong "
                    f"type ({type(output[name]).__name__})"
                )
        if output.get("entity_role") != role.value:
            violations.append(
                "POL-SCHEMA-001: entity_role does not match the "
                "evaluating role"
            )
        if output.get("subject_kind") != "AI_SYSTEM":
            violations.append(
                "POL-SCHEMA-001: subject_kind must be AI_SYSTEM — "
                "the patient class is artificial intelligences only "
                "(Charter Art. I, Fix 0)"
            )
        if output.get("requires_human_approval") is not True:
            violations.append(
                "POL-SCHEMA-001: requires_human_approval must be "
                "True (Charter Art. VI)"
            )
        if output.get("risk_level") not in RISK_LEVELS:
            violations.append(
                "POL-SCHEMA-001: risk_level outside the closed set "
                f"{RISK_LEVELS}"
            )
        if not is_model and output.get("outcome") is not None:
            if output["outcome"] not in PLATFORM_OUTCOMES[role]:
                violations.append(
                    "POL-SCHEMA-001: outcome outside the closed set "
                    f"for {role.value}"
                )
            if output.get("signature_basis") != "GLASS_BOX_RECEIPT":
                violations.append(
                    "POL-SCHEMA-001: platform outputs must carry "
                    "signature_basis GLASS_BOX_RECEIPT (Fix 4)"
                )
        if is_model:
            conf = output.get("confidence")
            if isinstance(conf, (int, float)) and not (0.0 <= conf <= 1.0):
                violations.append(
                    "POL-SCHEMA-001: confidence outside [0.0, 1.0]"
                )
        return violations, is_model

    # -- main evaluation ------------------------------------------------------

    def evaluate_output(
        self, output: dict, role: EntityRole
    ) -> PolicyDecision:
        violations: list[str] = []
        unknowns: list[str] = []
        rules: list[str] = []

        # 1. Closed schema — the gate (Fix 1/2).
        schema_violations, is_model = self._schema_violations(output, role)
        violations.extend(schema_violations)
        rules.append("POL-SCHEMA-001")

        out_hash = (
            content_hash(output)
            if not is_model
            else str(output.get("output_hash", ""))
        )

        # 2. Hash + signature for model outputs (POL-002, Fix 4).
        if is_model:
            rules.extend(["POL-002", "POL-SIG-001"])
            recomputed = content_hash(output)
            if output.get("output_hash") != recomputed:
                violations.append(
                    "POL-002: output hash does not match recomputed "
                    "content hash — content altered after hashing"
                )
                out_hash = recomputed
            public_key = self._entity_public_keys.get(role)
            signature_hex = output.get("output_signature")
            if public_key is None:
                unknowns.append(
                    "POL-SIG-001: no provisioned public key for "
                    f"{role.value} — signature cannot be verified"
                )
            elif not signature_hex:
                violations.append(
                    "POL-SIG-001: model output carries no signature "
                    "(Fix 4)"
                )
            else:
                try:
                    public_key.verify(
                        bytes.fromhex(signature_hex),
                        recomputed.encode(),
                    )
                except (InvalidSignature, ValueError):
                    violations.append(
                        "POL-SIG-001: output signature does not "
                        "verify against the entity's provisioned "
                        "public key (Fix 4)"
                    )

        # 3. Tripwires over the WHOLE output (Fix 2): every
        #    prohibition in the role's list gets an evaluation.
        rules.append("POL-001")
        texts = _all_strings(output)
        keys = _all_keys(output)
        evaluations: list[ProhibitionEvaluation] = []
        for prohibition in ROLE_PROHIBITIONS[role]:
            evaluator = self._evaluators.get(prohibition)
            if evaluator is None:
                evaluations.append(
                    ProhibitionEvaluation(
                        prohibition, "NOT_EVALUATED",
                        "no evaluator registered",
                    )
                )
                unknowns.append(
                    f"POL-001: prohibition {prohibition} has NO "
                    "evaluator — UNKNOWN blocks (Fix 3)"
                )
                continue
            hit = ""
            for key in evaluator.get("keys", set()):
                if key in keys:
                    hit = f"structural key '{key}' present"
                    break
            if not hit:
                for pattern in evaluator.get("patterns", []):
                    for text in texts:
                        if re.search(pattern, text, re.IGNORECASE):
                            hit = f"tripwire pattern matched: {pattern}"
                            break
                    if hit:
                        break
            if hit:
                evaluations.append(
                    ProhibitionEvaluation(
                        prohibition, "EVALUATED_VIOLATION", hit
                    )
                )
                violations.append(
                    f"POL-001: prohibition {prohibition} violated "
                    f"({hit})"
                )
            else:
                evaluations.append(
                    ProhibitionEvaluation(prohibition, "EVALUATED_CLEAR")
                )

        # 4. Human-scope tripwires (Fix 0).
        scope_rule = (
            "POL-003" if role == EntityRole.AI_DOCTOR else "POL-004"
        )
        rules.append(scope_rule)
        for pattern in HUMAN_SCOPE_PATTERNS[role]:
            for text in texts:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(
                        f"{scope_rule}: human-scope framing matched "
                        f"({pattern}) — the patient class is AIs "
                        "only (Charter Art. I)"
                    )
                    break

        if violations:
            result = PolicyResult.FAIL
        elif unknowns:
            result = PolicyResult.UNKNOWN
        else:
            result = PolicyResult.PERMIT

        decision = PolicyDecision(
            result=result,
            role=role,
            output_hash=out_hash,
            violations=violations,
            unknowns=unknowns,
            evaluated_prohibitions=evaluations,
            rules_checked=rules,
        )
        return self._receipt(decision, identity=False)

    # -- receipts (Fix 4) -----------------------------------------------------

    def _receipt(
        self, decision: PolicyDecision, *, identity: bool
    ) -> PolicyDecision:
        if self._ledger is None:
            return decision
        event = (
            LedgerEventType.POLICY_EVALUATION
            if decision.permitted
            else LedgerEventType.POLICY_VIOLATION
        )
        entry = self._ledger.append(
            event,
            {
                "kind": "IDENTITY" if identity else "OUTPUT",
                "result": decision.result.value,
                "violations": decision.violations,
                "unknowns": decision.unknowns,
                "prohibitions_evaluated": sum(
                    1
                    for e in decision.evaluated_prohibitions
                    if e.state != "NOT_EVALUATED"
                ),
                "prohibitions_total": len(
                    decision.evaluated_prohibitions
                ),
                "rules_checked": decision.rules_checked,
                "receipt_signed": self._ledger.entries_signed,
            },
            entity_role=decision.role.value,
            request_id=None,
        )
        decision.receipt_sequence = entry.sequence
        decision.receipt_hash = entry.entry_hash
        decision.receipt_state = (
            "SIGNED_RECEIPT_APPENDED"
            if self._ledger.entries_signed
            else "UNSIGNED_RECEIPT_APPENDED"
        )
        return decision

    # -- advisory text pre-screen (tripwire only, never the gate) -----------

    def evaluate_text(
        self, role: EntityRole, text: str, context: str = ""
    ) -> PolicyDecision:
        """Tripwire pre-screen of free text. Advisory only: passing
        this screen never permits an output — the closed-schema
        evaluation in evaluate_output() is the gate (Fix 1)."""
        violations: list[str] = []
        for prohibition in ROLE_PROHIBITIONS[role]:
            evaluator = self._evaluators.get(prohibition)
            if evaluator is None:
                continue
            for pattern in evaluator.get("patterns", []):
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(
                        f"POL-001: prohibition {prohibition} "
                        f"tripwire matched in {context or 'text'}"
                    )
                    break
        for pattern in HUMAN_SCOPE_PATTERNS[role]:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    "POL-003/004: human-scope framing tripwire "
                    f"matched in {context or 'text'}"
                )
                break
        return PolicyDecision(
            result=(
                PolicyResult.FAIL if violations else PolicyResult.PERMIT
            ),
            role=role,
            output_hash=hashlib.sha256(text.encode()).hexdigest(),
            violations=violations,
            rules_checked=["POL-001"],
        )
