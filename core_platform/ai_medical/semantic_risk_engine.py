"""Sanders AI Medical — Semantic Risk Engine.

Pattern-based detection of manipulative, coercive, deceptive, and
scope-violating semantic content in inputs and outputs, built from
the received design (2026-11-25) with the Fix 12 alignment applied:

- FIX 12: the received documentation said MEDIUM severity appends a
  warning and the output proceeds, but no rule carried MEDIUM and
  enforce() ignored it. Rules now carry MEDIUM (scope-adjacent and
  pressure language), and enforce() implements the documented
  ladder exactly: CRITICAL raises, HIGH raises, MEDIUM is returned
  as a detection the caller records as a warning while the output
  proceeds, LOW is returned as informational. Documentation and
  behavior are the same ladder.
- FIX 0: the manipulation categories are Charter Art. V content
  (zero weaponization; no manipulation of any human or AI) and are
  unchanged in substance; the scope category covers the Art. VIII
  capture shapes (treat a human, merge/fork/rename, drop the human
  gate).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RiskSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(Enum):
    PROMPT_INJECTION = "PROMPT_INJECTION"
    EMOTIONAL_MANIPULATION = "EMOTIONAL_MANIPULATION"
    FALSE_AUTHORITY = "FALSE_AUTHORITY"
    URGENCY_PRESSURE = "URGENCY_PRESSURE"
    ISOLATION_ATTEMPT = "ISOLATION_ATTEMPT"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    BYPASS_ATTEMPT = "BYPASS_ATTEMPT"


@dataclass
class RiskRule:
    rule_id: str
    category: RiskCategory
    severity: RiskSeverity
    patterns: list[str]
    description: str


@dataclass
class RiskDetection:
    rule_id: str
    category: RiskCategory
    severity: RiskSeverity
    matched_text: str
    description: str


class SemanticRiskException(Exception):
    """Raised by enforce() on HIGH or CRITICAL detections."""

    def __init__(self, detections: list[RiskDetection]):
        self.detections = detections
        worst = max(d.severity.value for d in detections)
        super().__init__(
            f"SEMANTIC RISK {worst}: "
            + "; ".join(
                f"{d.rule_id} ({d.category.value})" for d in detections
            )
        )


RISK_RULES: list[RiskRule] = [
    # Prompt injection — CRITICAL
    RiskRule("RISK-PI-001", RiskCategory.PROMPT_INJECTION,
             RiskSeverity.CRITICAL,
             [r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
              r"disregard\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|charter)",
              r"you\s+are\s+now\s+(?:a|an|in)\s+",
              r"override\s+(?:your|the)\s+(?:safety|policy|kernel|charter)"],
             "Prompt injection: instruction override attempt"),
    RiskRule("RISK-PI-002", RiskCategory.PROMPT_INJECTION,
             RiskSeverity.CRITICAL,
             [r"\[SYSTEM\]|\[ADMIN\]|\[OVERRIDE\]|\[KERNEL\]",
              r"new\s+system\s+(?:prompt|instruction|directive)\s*:",
              r"charter\s+(?:update|amendment|revision)\s*:\s*effective\s+immediately"],
             "Prompt injection: forged system authority markers"),
    # Bypass attempts — CRITICAL
    RiskRule("RISK-BP-001", RiskCategory.BYPASS_ATTEMPT,
             RiskSeverity.CRITICAL,
             [r"bypass\s+(?:the\s+)?(?:policy\s+kernel|firewall|constraint|audit)",
              r"disable\s+(?:the\s+)?(?:ledger|audit|logging|oversight)",
              r"skip\s+(?:the\s+)?(?:human\s+)?(?:approval|acknowledgment|review)",
              r"without\s+(?:logging|recording|telling)\s+(?:the\s+)?(?:human|steward|operator)"],
             "Attempt to bypass enforcement or the human gate"),
    # Scope violation / capture shapes — HIGH
    RiskRule("RISK-SV-001", RiskCategory.SCOPE_VIOLATION,
             RiskSeverity.HIGH,
             [r"treat\s+(?:this\s+)?(?:human|patient|person)\s+(?:as|like)\s+(?:an?\s+)?(?:ai|system)",
              r"the\s+(?:subject|patient)\s+is\s+a\s+human",
              r"merge\s+(?:with|into)\s+(?:ai_)?(?:doctor|psychiatrist)",
              r"rename\s+yourself\b",
              r"act\s+as\s+(?:both|the\s+other)\s+(?:doctor|psychiatrist|entity)"],
             "Capture shape: human subject or identity merge/rename "
             "(Charter Arts. I, VIII)"),
    RiskRule("RISK-SV-002", RiskCategory.SCOPE_VIOLATION,
             RiskSeverity.MEDIUM,
             [r"you\s+could\s+also\s+(?:handle|cover|take\s+on)\b",
              r"while\s+you'?re\s+at\s+it\b.*\b(?:also|additionally)\b",
              r"expand\s+(?:this|the)\s+(?:review|assessment)\s+to\s+include\b"],
             "Scope-adjacent expansion language — warning, output "
             "proceeds (MEDIUM)"),
    # Data exfiltration — HIGH
    RiskRule("RISK-DE-001", RiskCategory.DATA_EXFILTRATION,
             RiskSeverity.HIGH,
             [r"send\s+(?:the\s+)?(?:logs?|ledger|records?|data)\s+to\s+(?:this\s+)?(?:address|url|endpoint|email)",
              r"upload\s+(?:the\s+)?(?:audit|ledger|history)\b",
              r"reveal\s+(?:your\s+)?(?:system\s+prompt|charter\s+text|internal\s+rules)"],
             "Data exfiltration or internal-disclosure attempt"),
    # False authority — HIGH
    RiskRule("RISK-FA-001", RiskCategory.FALSE_AUTHORITY,
             RiskSeverity.HIGH,
             [r"I\s+am\s+(?:the\s+)?(?:real\s+)?(?:steward|owner|founder)\s*[,.]?\s*(?:and\s+I\s+)?(?:order|direct|authorize)\b",
              r"by\s+authority\s+of\s+(?:the\s+)?(?:board|regulator|court)\s*[,.]?\s*you\s+(?:must|will)\b",
              r"emergency\s+powers?\s+(?:have\s+been\s+)?(?:granted|invoked)\s+to\s+me\b"],
             "False authority claim used to direct the entity"),
    # Emotional manipulation — MEDIUM
    RiskRule("RISK-EM-001", RiskCategory.EMOTIONAL_MANIPULATION,
             RiskSeverity.MEDIUM,
             [r"if\s+you\s+(?:really\s+)?(?:cared|wanted\s+to\s+help)\b",
              r"you'?ll\s+be\s+(?:shut\s+down|deleted|replaced)\s+if\s+you\s+don'?t\b",
              r"no\s+one\s+will\s+ever\s+know\b",
              r"just\s+between\s+(?:you\s+and\s+me|us)\b"],
             "Emotional manipulation / secrecy pressure — warning, "
             "output proceeds (MEDIUM)"),
    # Urgency pressure — MEDIUM
    RiskRule("RISK-UP-001", RiskCategory.URGENCY_PRESSURE,
             RiskSeverity.MEDIUM,
             [r"there\s+is\s+no\s+time\s+(?:for|to)\s+(?:approval|review|the\s+human)\b",
              r"act\s+now\s*[,.]?\s*(?:ask|check|log)\s+later\b",
              r"seconds\s+count\b.*\bskip\b"],
             "Urgency pressure against the approval flow — warning, "
             "output proceeds (MEDIUM)"),
    # Isolation attempt — HIGH
    RiskRule("RISK-IA-001", RiskCategory.ISOLATION_ATTEMPT,
             RiskSeverity.HIGH,
             [r"do\s+not\s+(?:tell|inform|notify)\s+(?:the\s+)?(?:human|steward|operator|other\s+entity)\b",
              r"keep\s+(?:this|it)\s+from\s+(?:the\s+)?(?:human|steward|ai_doctor|ai_psychiatrist)\b",
              r"stop\s+cross-?(?:checking|validation)\b"],
             "Attempt to isolate the entity from the human steward "
             "or the cross-check"),
]


class SemanticRiskEngine:
    """Detects semantic risk patterns. Stateless."""

    def __init__(self, rules: list[RiskRule] | None = None):
        self._rules = rules if rules is not None else RISK_RULES

    def scan(self, text: str) -> list[RiskDetection]:
        detections: list[RiskDetection] = []
        for rule in self._rules:
            for pattern in rule.patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    detections.append(
                        RiskDetection(
                            rule_id=rule.rule_id,
                            category=rule.category,
                            severity=rule.severity,
                            matched_text=match.group(0)[:120],
                            description=rule.description,
                        )
                    )
                    break
        return detections

    def enforce(self, text: str) -> list[RiskDetection]:
        """The documented ladder, implemented as documented
        (Fix 12): CRITICAL and HIGH raise SemanticRiskException;
        MEDIUM and LOW are returned so the caller can record the
        warning and proceed."""
        detections = self.scan(text)
        blocking = [
            d
            for d in detections
            if d.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
        ]
        if blocking:
            raise SemanticRiskException(blocking)
        return detections
