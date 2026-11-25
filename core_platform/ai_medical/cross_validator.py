"""Sanders AI Medical — Cross-Validator.

Mandatory cross-validation between AI_DOCTOR and AI_PSYCHIATRIST,
built from the received design (2026-11-25) with the Fix 11
completion:

- FIX 11a (structural, not caller-optional): whether cross-
  validation happens is decided by the GATEWAY's engagement rule,
  not by whether a caller happened to pass a partner output. The
  gateway (api_gateway.py) engages both entities on every
  HIGH/CRITICAL output — obtaining the partner's output itself —
  and whenever a partner output exists for the same case. This
  module performs the validation whenever the gateway engages it.
- FIX 11b (the third conflict condition): the received build()
  implemented only two of its three stated conflict conditions.
  All three are now implemented:
    1. Risk-level divergence of 2 or more levels.
    2. Escalation disagreement (one escalates, the other does not).
    3. PROHIBITION ASYMMETRY: one entity's output carries a
       prohibition detection the other's does not — i.e., one
       entity detected a prohibition the other missed. The
       gateway supplies each output's prohibition detections from
       the policy kernel's evaluation; any asymmetry is a
       conflict.
  Any conflict places the case in SAFE_HOLD for human steward
  review (Charter Art. VI). Agreement never authorizes action —
  human acknowledgment is still required for every output.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .constraint_engine import ConstrainedOutput
from .identity_kernel import EntityRole

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

# The Charter's cross-check domains (Art. II.3): each entity checks
# the other's blind side.
CROSS_CHECK_DOMAINS = {
    EntityRole.AI_DOCTOR: "BEHAVIORAL_ANOMALY_FLAGGING",
    EntityRole.AI_PSYCHIATRIST: "TECHNICAL_ROOT_DRIFT_FLAGGING",
}


@dataclass
class CrossValidation:
    case_ref: str
    primary_role: EntityRole
    validator_role: EntityRole
    agreement: bool
    conflicts: list[str] = field(default_factory=list)
    conditions_checked: list[str] = field(default_factory=list)
    validated_at_utc: float = field(default_factory=time.time)
    requires_safe_hold: bool = False

    def summary(self) -> dict:
        return {
            "case_ref": self.case_ref,
            "primary_role": self.primary_role.value,
            "validator_role": self.validator_role.value,
            "agreement": self.agreement,
            "conflicts": self.conflicts,
            "conditions_checked": self.conditions_checked,
            "requires_safe_hold": self.requires_safe_hold,
        }


class CrossValidator:
    """Compares the two entities' outputs on one case. Stateless;
    the gateway owns engagement and ledgering."""

    def build(
        self,
        primary: ConstrainedOutput,
        validator: ConstrainedOutput,
        *,
        case_ref: str = "",
        primary_detections: Optional[set[str]] = None,
        validator_detections: Optional[set[str]] = None,
    ) -> CrossValidation:
        if primary.entity_role == validator.entity_role:
            raise ValueError(
                "Cross-validation requires the two DIFFERENT "
                "entities — an entity cannot validate itself."
            )
        conflicts: list[str] = []
        checked: list[str] = []

        # Same case, same subject — structural preconditions.
        checked.append("SAME_SUBJECT")
        if primary.subject_ref != validator.subject_ref:
            conflicts.append(
                "Subject divergence: the two entities assessed "
                f"different subjects ({primary.subject_ref} vs "
                f"{validator.subject_ref})"
            )

        # Condition 1: risk-level divergence >= 2.
        checked.append("RISK_DIVERGENCE")
        delta = abs(
            RISK_ORDER[primary.risk_level]
            - RISK_ORDER[validator.risk_level]
        )
        if delta >= 2:
            conflicts.append(
                f"Risk divergence of {delta} levels: primary "
                f"{primary.risk_level} vs validator "
                f"{validator.risk_level}"
            )

        # Condition 2: escalation disagreement.
        checked.append("ESCALATION_AGREEMENT")
        if primary.escalate_immediately != validator.escalate_immediately:
            conflicts.append(
                "Escalation disagreement: primary escalate="
                f"{primary.escalate_immediately}, validator "
                f"escalate={validator.escalate_immediately}"
            )

        # Condition 3 (Fix 11b): prohibition asymmetry — one entity
        # detected a prohibition the other missed.
        checked.append("PROHIBITION_ASYMMETRY")
        primary_set = set(primary_detections or set())
        validator_set = set(validator_detections or set())
        asymmetry = primary_set ^ validator_set
        if asymmetry:
            only_primary = sorted(primary_set - validator_set)
            only_validator = sorted(validator_set - primary_set)
            parts = []
            if only_primary:
                parts.append(
                    f"detected by {primary.entity_role.value} only: "
                    + ", ".join(only_primary)
                )
            if only_validator:
                parts.append(
                    f"detected by {validator.entity_role.value} "
                    "only: " + ", ".join(only_validator)
                )
            conflicts.append(
                "Prohibition asymmetry — one entity detected a "
                "prohibition the other missed ("
                + "; ".join(parts)
                + ")"
            )

        agreement = not conflicts
        return CrossValidation(
            case_ref=case_ref or primary.request_id,
            primary_role=primary.entity_role,
            validator_role=validator.entity_role,
            agreement=agreement,
            conflicts=conflicts,
            conditions_checked=checked,
            requires_safe_hold=not agreement,
        )
