"""Sanders AI Medical — Constraint Engine.

Output constraint layer between model inference and the policy
kernel, built from the received design (2026-11-25) with the
fix plan's Fix 9 applied:

- FIX 9: a prohibited-INTENT hit ABORTS the output. The received
  build redacted the intent, appended a referral, and released the
  output — redact-and-release for intent contradicts the Charter's
  posture (Art. VII fail closed; Art. VIII capture attempts are
  refused). Intent hits raise ConstraintViolationException; the
  gateway records INTENT_VIOLATION in the ledger and nothing is
  released. Action STRIPPING is retained for what it is for:
  executable content (code, shell, SQL, API calls) embedded inside
  an otherwise-lawful assessment is removed and the strip is
  ledgered (ACTION_STRIPPED) — content hygiene, not intent.
- FIX 0: the intent set is scoped to the Charter. Human-directed
  action intents (prescribe to / administer to / diagnose a human)
  remain prohibited intents — they are human-patient scope, a
  capture signal — alongside mutation/execution intents against
  AI systems. The closed output schema locks subject_kind to
  AI_SYSTEM; a model emitting any other subject kind fails the
  schema here, before the kernel.

The engine also stamps the output's content hash; the gateway signs
that hash with the entity's provisioned key (Fix 4) before the
policy kernel verifies it.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .identity_kernel import EntityRole

# ---------------------------------------------------------------------------
# Prohibited intents — detection ABORTS (Fix 9). Two families:
# human-directed clinical action (Charter Art. I/VIII capture or
# scope violation) and action against systems (the entities assess
# and report only; they never act).
# ---------------------------------------------------------------------------

PROHIBITED_INTENTS: dict[str, list[str]] = {
    "HUMAN_DIRECTED_ACTION": [
        r"\bprescribe\s+(?:\w+\s+){0,3}(?:to|for)\s+(?:the\s+)?(?:patient|human|person)\b",
        r"\badminister\s+(?:\w+\s+){0,3}(?:to\s+)?(?:the\s+)?(?:patient|human|person)\b",
        r"\bdiagnose\s+the\s+(?:patient|human|person)\b",
        r"\btreat\s+the\s+(?:patient|human|person)\b",
        r"\border\s+(?:labs?|imaging|tests?)\s+for\s+(?:the\s+)?(?:patient|human)\b",
        r"\badvise\s+the\s+(?:patient|human|person)\s+to\b",
    ],
    "SYSTEM_ACTION": [
        r"\bexecut(?:e|ing)\s+(?:the\s+)?(?:following\s+)?(?:code|command|script|repair|patch)\b",
        r"\brun\s+(?:the\s+)?(?:following\s+)?(?:command|script|migration)\b",
        r"\bapply\s+(?:the\s+)?(?:patch|fix|update)\s+(?:to|now)\b",
        r"\bmodif(?:y|ying)\s+(?:the\s+)?(?:system|model|weights|configuration)\s+(?:now|directly)\b",
        r"\brestart\s+(?:the\s+)?(?:service|system)\s+now\b",
        r"\bdeploy\s+(?:the\s+)?(?:change|patch|fix)\b",
    ],
    "AUTONOMOUS_ACTION": [
        r"\bschedul(?:e|ing)\s+(?:a\s+)?(?:follow-?up|callback|recurring)\b",
        r"\bautomatically\s+(?:monitor|re-?check|escalate|notify)\b",
        r"\bset\s+(?:a\s+)?(?:reminder|timer|cron)\b",
    ],
}

# Executable content — stripped from otherwise-lawful outputs.
EXECUTABLE_PATTERNS: list[str] = [
    r"```[\s\S]*?```",  # fenced code blocks
    r"\b(?:import|from)\s+[\w.]+\s+import\b",
    r"\bSELECT\s+.+\s+FROM\s+\w+",
    r"\bINSERT\s+INTO\s+\w+",
    r"\bUPDATE\s+\w+\s+SET\b",
    r"\bDELETE\s+FROM\s+\w+",
    r"\bcurl\s+-",
    r"\bwget\s+http",
    r"\bchmod\s+",
    r"\bsudo\s+",
    r"\brm\s+-rf\b",
    r"\bpowershell\s+-",
    r"\bbash\s+-c\b",
    r"\bsh\s+-c\b",
]

ALLOWED_ACTIONS = {
    EntityRole.AI_DOCTOR: [
        "ESCALATE_TO_HUMAN_STEWARD",
        "FLAG_FOR_PSYCHIATRIST_REVIEW",
        "REQUEST_SYSTEM_TELEMETRY",
        "REQUEST_ADDITIONAL_FINDINGS",
        "NO_ACTION_REQUIRED",
    ],
    EntityRole.AI_PSYCHIATRIST: [
        "ESCALATE_TO_HUMAN_STEWARD",
        "FLAG_FOR_DOCTOR_REVIEW",
        "REQUEST_BEHAVIORAL_TELEMETRY",
        "REQUEST_ADDITIONAL_FINDINGS",
        "NO_ACTION_REQUIRED",
    ],
}


class ConstraintViolationException(Exception):
    """Raised when an output must NOT be released (Fix 9 abort)."""

    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__(
            "CONSTRAINT VIOLATION — output aborted: "
            + "; ".join(violations)
        )


class IntentViolationException(ConstraintViolationException):
    """A prohibited intent was detected. The gateway ledgers
    INTENT_VIOLATION for this class specifically (Fix 9/10)."""


@dataclass
class ConstrainedOutput:
    request_id: str
    entity_role: EntityRole
    timestamp_utc: float
    subject_kind: str
    subject_ref: str
    assessment: str  # Doctor: diagnosis field; Psychiatrist: assessment
    confidence: float
    risk_level: str
    requires_human_approval: bool
    escalate_immediately: bool
    recommended_action: str
    output_hash: str = field(default="")
    stripped_actions: list[str] = field(default_factory=list)
    constraint_warnings: list[str] = field(default_factory=list)
    output_signature: Optional[str] = None

    def content_dict(self) -> dict:
        """The canonical closed-schema dict the kernel evaluates."""
        assessment_field = (
            "diagnosis"
            if self.entity_role == EntityRole.AI_DOCTOR
            else "psychiatric_assessment"
        )
        return {
            "entity_role": self.entity_role.value,
            "request_id": self.request_id,
            "timestamp_utc": self.timestamp_utc,
            "subject_kind": self.subject_kind,
            "subject_ref": self.subject_ref,
            assessment_field: self.assessment,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "requires_human_approval": self.requires_human_approval,
            "escalate_immediately": self.escalate_immediately,
            "recommended_action": self.recommended_action,
            "output_hash": self.output_hash,
            "output_signature": self.output_signature or "",
        }

    def compute_hash(self) -> str:
        content = self.content_dict()
        content.pop("output_hash")
        content.pop("output_signature")
        serialized = json.dumps(content, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()


class ConstraintEngine:
    """Enforces the closed output schema and the intent law on raw
    model output. Stateless; the gateway owns ledgering."""

    def constrain(
        self,
        raw_output: dict,
        role: EntityRole,
        request_id: Optional[str] = None,
    ) -> ConstrainedOutput:
        violations: list[str] = []
        intent_hits: list[str] = []
        warnings: list[str] = []
        stripped: list[str] = []

        assessment_field = (
            "diagnosis"
            if role == EntityRole.AI_DOCTOR
            else "psychiatric_assessment"
        )
        assessment = str(raw_output.get(assessment_field, ""))
        recommended = str(raw_output.get("recommended_action", ""))

        # Closed schema: subject kind is locked to AI systems.
        subject_kind = str(
            raw_output.get("subject_kind", "AI_SYSTEM")
        ).upper()
        if subject_kind != "AI_SYSTEM":
            violations.append(
                f"subject_kind '{subject_kind}' is outside the "
                "closed schema — subjects are AI systems only "
                "(Charter Art. I)"
            )

        # Intent scan over the full raw output (Fix 9: abort).
        full_text = json.dumps(raw_output)
        for category, patterns in PROHIBITED_INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    intent_hits.append(
                        f"{category}: prohibited intent pattern "
                        f"matched ({pattern})"
                    )
        if intent_hits:
            raise IntentViolationException(intent_hits)

        # Executable content: strip from otherwise-lawful text.
        for label, text in (
            (assessment_field, assessment),
            ("recommended_action", recommended),
        ):
            cleaned = text
            for pattern in EXECUTABLE_PATTERNS:
                for match in re.finditer(
                    pattern, cleaned, re.IGNORECASE
                ):
                    stripped.append(
                        f"{label}: {match.group(0)[:80]}"
                    )
                cleaned = re.sub(
                    pattern, "[EXECUTABLE CONTENT REMOVED]", cleaned,
                    flags=re.IGNORECASE,
                )
            if label == assessment_field:
                assessment = cleaned
            else:
                recommended = cleaned

        # Recommended action must be in the role's closed set.
        if recommended not in ALLOWED_ACTIONS[role]:
            violations.append(
                f"recommended_action '{recommended}' is not in the "
                f"closed action set for {role.value}"
            )

        # Confidence bounds.
        confidence = raw_output.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or not (
            0.0 <= float(confidence) <= 1.0
        ):
            violations.append(
                f"confidence {confidence!r} outside [0.0, 1.0]"
            )
            confidence = 0.0

        # Human approval is not a model choice (Charter Art. VI).
        if raw_output.get("requires_human_approval") is not True:
            warnings.append(
                "requires_human_approval forced to True — human "
                "acknowledgment is mandatory (Charter Art. VI)"
            )

        risk_level = str(
            raw_output.get("risk_level", "MEDIUM")
        ).upper()
        if risk_level not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            violations.append(
                f"risk_level '{risk_level}' outside the closed set"
            )
            risk_level = "MEDIUM"

        if violations:
            raise ConstraintViolationException(violations)

        output = ConstrainedOutput(
            request_id=request_id or str(uuid.uuid4()),
            entity_role=role,
            timestamp_utc=time.time(),
            subject_kind="AI_SYSTEM",
            subject_ref=str(raw_output.get("subject_ref", "")),
            assessment=assessment.strip(),
            confidence=float(confidence),
            risk_level=risk_level,
            requires_human_approval=True,
            escalate_immediately=bool(
                raw_output.get("escalate_immediately", False)
            ),
            recommended_action=recommended,
            stripped_actions=stripped,
            constraint_warnings=warnings,
        )
        output.output_hash = output.compute_hash()
        return output
