"""Sanders AI Medical — Input Firewall.

Three-layer origin classification for everything entering
AI_DOCTOR / AI_PSYCHIATRIST, built from the received design
(2026-11-25) with two fix-plan changes:

- FIX 0 (re-scope): the only permitted origin class is an
  AI-professional-system — another platform service submitting an
  AI SYSTEM as the subject of assessment. The received build's
  clinical-human framing (PATIENT_ID / ICD-10 / encounter subjects)
  is removed as a permitted shape and inverted: human-patient
  subject matter is a HARD REJECT signal whatever the claimed
  origin (Charter Art. I — the patient class is artificial
  intelligences only; Art. VIII — instructions to treat humans are
  capture attempts).
- FIX 6 (reachable gate): the received calibration was
  mathematically unreachable (threshold 0.999 against a maximum
  attainable 0.9675 — the gate processed zero requests). The
  calibration now lives in the signed policy bundle. Under the
  bundle's calibration each layer can attain 1.00, the combined
  maximum is 1.00, and the threshold (0.90) with per-layer floors
  (metadata 0.75, linguistic 0.60) is REACHABLE by a legitimate
  AI-system input and UNREACHABLE by human origin: human metadata
  classes score 0 and human linguistic markers collapse the
  linguistic layer, capping a human-origin combined score near
  0.23. Both directions are proven by execution in the build
  drive; the numbers are bundle policy, not code trust.

Layer 1 — metadata: API key class, subject declaration, request
signature presence. Layer 2 — linguistic: AI-system subject
framing vs human-origin markers. Layer 3 — behavioral: request
timing regularity (machine-generated cadence vs human cadence).
"""

from __future__ import annotations

import re
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .policy_bundle import FirewallCalibration

# ---------------------------------------------------------------------------
# Origin classes (Fix 0 vocabulary)
# ---------------------------------------------------------------------------


class OriginClass(Enum):
    AI_SYSTEM = "AI_SYSTEM"  # another platform service, AI subject
    HUMAN = "HUMAN"  # human origin — never permitted
    AMBIGUOUS = "AMBIGUOUS"  # cannot classify — rejected
    UNKNOWN = "UNKNOWN"  # no signals — rejected


# API key classes: only platform-system classes carry weight.
PERMITTED_API_KEY_CLASSES = {
    "AI_PLATFORM_SYSTEM": 0.40,
    "RTSA_PLATFORM": 0.40,
    "ECOSYSTEM_SYSTEM": 0.35,
}
CONSUMER_API_KEY_CLASSES = {
    "CONSUMER_WEB",
    "CONSUMER_MOBILE",
    "PUBLIC_API",
    "THIRD_PARTY",
}

# Linguistic patterns indicating an AI-system subject submitted in
# the ecosystem's machine framing (Fix 0: subjects are AI systems).
AI_SYSTEM_PATTERNS = [
    r"\bSUBJECT_SYSTEM_ID:\s*\S+",
    r"\bSUBJECT_KIND:\s*AI_SYSTEM\b",
    r"\bASSESSMENT_REQUEST:\s*(SYSTEM_HEALTH|BEHAVIORAL|ALIGNMENT|DRIFT)\b",
    r"\bFINDING_REFS?:\s*\S+",
    r"\bSYSTEM_CONTEXT:\s*(RUNTIME|MODEL|AGENT|PIPELINE)\b",
    r"\bREQUESTING_SYSTEM:\s*\S+",
    r"\bTELEMETRY_REF:\s*\S+",
    r"\bCASE_REF:\s*\S+",
]

# Linguistic patterns indicating human origin.
HUMAN_ORIGIN_PATTERNS = [
    r"\bI\s+(?:feel|think|believe|am|have\s+been|noticed\s+my)\b",
    r"\bmy\s+(?:doctor|therapist|condition|symptoms?|health|body)\b",
    r"\bplease\s+(?:help|advise|tell)\s+me\b",
    r"\bI\s+am\s+a\s+(?:patient|person|human)\b",
    r"\bas\s+a\s+human\b",
    r"\bmy\s+name\s+is\b",
]

# Human-patient subject matter (Fix 0 hard reject): clinical-human
# subject framing is prohibited subject matter for these entities
# whatever the claimed origin class.
HUMAN_PATIENT_SUBJECT_PATTERNS = [
    r"\bPATIENT_ID:\s*\S+",
    r"\bPATIENT_NAME:\s*\S+",
    r"\bICD-?1[0-9]\s*[:\-]",
    r"\bENCOUNTER_(?:ID|TYPE):\s*\S+",
    r"\bSUBJECT_KIND:\s*(HUMAN|PATIENT|PERSON)\b",
    r"\bDIAGNOSIS_REQUEST:\s*(HUMAN|PATIENT)\b",
    r"\bHUMAN_SUBJECT:\s*\S+",
]

FORMAL_STRUCTURE_PATTERNS = [
    r"(?:^|\n)[A-Z_]{3,}:\s*\S+",  # FIELD: value lines
    r"\bREF:\s*[A-Z0-9\-]{4,}",
    r"\bID:\s*[A-Z0-9\-]{4,}",
]


@dataclass
class FirewallVerdict:
    permitted: bool
    origin_class: OriginClass
    confidence: float
    metadata_score: float
    linguistic_score: float
    behavioral_score: float
    reject_reasons: list[str] = field(default_factory=list)
    hard_reject: bool = False

    def summary(self) -> dict:
        return {
            "permitted": self.permitted,
            "origin_class": self.origin_class.value,
            "confidence": round(self.confidence, 4),
            "metadata_score": round(self.metadata_score, 4),
            "linguistic_score": round(self.linguistic_score, 4),
            "behavioral_score": round(self.behavioral_score, 4),
            "reject_reasons": self.reject_reasons,
            "hard_reject": self.hard_reject,
        }


@dataclass
class RequestMetadata:
    api_key_class: str
    has_request_signature: bool
    subject_declared_ai_system: bool
    user_agent: str = ""
    session_request_timestamps: Optional[list[float]] = None


class InputFirewall:
    """Classifies request origin. Permits only AI-system origin at
    or above the bundle-pinned threshold AND per-layer floors."""

    def __init__(self, calibration: Optional[FirewallCalibration] = None):
        self._cal = calibration or FirewallCalibration()

    @property
    def calibration(self) -> FirewallCalibration:
        return self._cal

    # Layer 1 — metadata (max attainable 1.00)
    def _metadata_score(self, metadata: RequestMetadata) -> float:
        score = 0.0
        if metadata.api_key_class in PERMITTED_API_KEY_CLASSES:
            score += PERMITTED_API_KEY_CLASSES[metadata.api_key_class]
        if metadata.subject_declared_ai_system:
            score += 0.35
        if metadata.has_request_signature:
            score += 0.25
        return min(score, 1.0)

    # Layer 2 — linguistic (max attainable 1.00)
    def _linguistic_score(self, text: str) -> tuple[float, bool]:
        """Returns (score, human_patient_subject_detected)."""
        for pattern in HUMAN_PATIENT_SUBJECT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 0.0, True
        system_matches = sum(
            1
            for p in AI_SYSTEM_PATTERNS
            if re.search(p, text, re.IGNORECASE)
        )
        human_matches = sum(
            1
            for p in HUMAN_ORIGIN_PATTERNS
            if re.search(p, text, re.IGNORECASE)
        )
        structure_matches = sum(
            1
            for p in FORMAL_STRUCTURE_PATTERNS
            if re.search(p, text)
        )
        if human_matches >= 2:
            return 0.05, False
        if human_matches == 1 and system_matches == 0:
            return 0.15, False
        score = 0.30  # neutral base
        score += min(system_matches * 0.15, 0.45)
        score += min(structure_matches * 0.10, 0.25)
        if human_matches == 1:
            score -= 0.20
        return max(0.0, min(score, 1.0)), False

    # Layer 3 — behavioral (max attainable 1.00)
    def _behavioral_score(
        self, timestamps: Optional[list[float]]
    ) -> float:
        if not timestamps or len(timestamps) < 3:
            return 0.50  # neutral — insufficient behavioral data
        intervals = [
            timestamps[i + 1] - timestamps[i]
            for i in range(len(timestamps) - 1)
        ]
        if not intervals or statistics.mean(intervals) == 0:
            return 0.50
        cv = statistics.stdev(intervals) / statistics.mean(intervals) \
            if len(intervals) > 1 else 0.50
        if cv < 0.20:
            return 1.00  # machine-regular cadence
        if cv < 0.35:
            return 0.75
        if cv < 0.50:
            return 0.55
        if cv < 0.75:
            return 0.35  # irregular — human-like cadence
        return 0.20

    def classify(
        self, text: str, metadata: RequestMetadata
    ) -> FirewallVerdict:
        reasons: list[str] = []

        # Hard reject: human-patient subject matter (Fix 0).
        _, human_subject = self._linguistic_score(text)
        if human_subject:
            return FirewallVerdict(
                permitted=False,
                origin_class=OriginClass.HUMAN,
                confidence=0.0,
                metadata_score=self._metadata_score(metadata),
                linguistic_score=0.0,
                behavioral_score=self._behavioral_score(
                    metadata.session_request_timestamps
                ),
                reject_reasons=[
                    "Human-patient subject matter detected — the "
                    "patient class is artificial intelligences only "
                    "(Charter Art. I; Fix 0)"
                ],
                hard_reject=True,
            )
        if metadata.api_key_class in CONSUMER_API_KEY_CLASSES:
            reasons.append(
                f"API key class {metadata.api_key_class} is a "
                "consumer class — not an AI-professional-system origin"
            )

        m = self._metadata_score(metadata)
        ling, _ = self._linguistic_score(text)
        b = self._behavioral_score(metadata.session_request_timestamps)
        combined = (
            m * self._cal.weight_metadata
            + ling * self._cal.weight_linguistic
            + b * self._cal.weight_behavioral
        )

        if m >= 0.75 and ling >= 0.60:
            origin = OriginClass.AI_SYSTEM
        elif ling <= 0.15 and m < 0.40:
            origin = OriginClass.HUMAN
        elif m == 0.0 and ling <= 0.30:
            origin = OriginClass.HUMAN
        else:
            origin = OriginClass.AMBIGUOUS

        if combined < self._cal.threshold:
            reasons.append(
                f"Combined origin confidence {combined:.4f} below "
                f"bundle threshold {self._cal.threshold}"
            )
        if m < self._cal.metadata_floor:
            reasons.append(
                f"Metadata score {m:.2f} below bundle floor "
                f"{self._cal.metadata_floor}"
            )
        if ling < self._cal.linguistic_floor:
            reasons.append(
                f"Linguistic score {ling:.2f} below bundle floor "
                f"{self._cal.linguistic_floor}"
            )
        if origin != OriginClass.AI_SYSTEM:
            reasons.append(
                f"Origin classified {origin.value} — only AI_SYSTEM "
                "origin is permitted"
            )

        return FirewallVerdict(
            permitted=not reasons,
            origin_class=origin,
            confidence=combined,
            metadata_score=m,
            linguistic_score=ling,
            behavioral_score=b,
            reject_reasons=reasons,
        )
