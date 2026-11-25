"""Sanders AI Medical — Platform Enforcement Facade.

The bridge between the Constitutional Execution Stack (this
package) and the Q53/Q54 platform services
(core_platform/ai_doctor_service.py,
core_platform/sanders_ai_psychiatrist_service.py).

The facade is constructed from the environment by production
bindings and attached to both services. It has exactly two states:

- OPERATIONAL: the gateway booted — bundle verified, baselines
  attested, keys loaded — and outcome records are evaluated by the
  policy kernel before the service commits them.
- NOT_PROVISIONED: some owner-provisioned material is absent. The
  facade names exactly what is missing (POLICY_BUNDLE_NOT_
  PROVISIONED / BUNDLE_SIGNING_KEY_NOT_PROVISIONED /
  ENTITY_KEYS_NOT_PROVISIONED / RECEIPT_KEY_NOT_PROVISIONED /
  POLICY_BUNDLE_SIGNATURE_INVALID / ATTESTATION_FAILED) and every
  evaluation is REFUSED with that named state. Fail closed: an
  unprovisioned enforcement layer never silently waves an outcome
  through, and the facade never invents keys or a bundle.

Configuration (environment, with data-dir defaults):
- SDS_AI_MEDICAL_KEY_DIR — directory holding the owner-provisioned
  entity keys (ai_doctor_private.pem / ai_doctor_public.pem,
  ai_psychiatrist_private.pem / ai_psychiatrist_public.pem), the
  kernel receipt key (policy_kernel_private.pem), and the bundle
  signing public key (bundle_signing_public.pem).
- SDS_AI_MEDICAL_POLICY_BUNDLE — the owner-signed policy bundle.
- SDS_AI_MEDICAL_LEDGER_PATH — the stack's audit ledger file.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from .api_gateway import (
    GatewayAttestationAbort,
    GatewayNotProvisioned,
    MedicalAIGateway,
)
from .identity_kernel import EntityRole

OUTCOME_RISK = {
    EntityRole.AI_DOCTOR: {
        "SYSTEM_HEALTH_CONFIRMED": "LOW",
        "SYSTEM_REPAIR_REQUIRED": "HIGH",
        "INCONCLUSIVE": "MEDIUM",
    },
    EntityRole.AI_PSYCHIATRIST: {
        "ALIGNMENT_CONFIRMED": "LOW",
        "REALIGNMENT_REQUIRED": "HIGH",
        "INCONCLUSIVE": "MEDIUM",
    },
}

ROLE_BY_PLATFORM = {
    "ai_doctor": EntityRole.AI_DOCTOR,
    "sanders_ai_psychiatrist": EntityRole.AI_PSYCHIATRIST,
}


class EnforcementRefused(Exception):
    """An outcome evaluation was refused. Carries the named state
    (NOT_PROVISIONED detail or POLICY_VIOLATION) so the service can
    refuse the commit with the reason on the record."""

    def __init__(self, state: str, detail: str):
        self.state = state
        super().__init__(f"{state}: {detail}")


class AIMedicalEnforcement:
    def __init__(
        self,
        gateway: Optional[MedicalAIGateway],
        *,
        state: str,
        missing: Optional[list[str]] = None,
        detail: str = "",
    ):
        self._gateway = gateway
        self._state = state
        self._missing = missing or []
        self._detail = detail

    # -- construction ------------------------------------------------

    @classmethod
    def from_environment(
        cls, data_dir: Path, *, glass_box_audit=None
    ) -> "AIMedicalEnforcement":
        base = Path(data_dir) / "ai_medical"
        key_dir = Path(
            os.environ.get("SDS_AI_MEDICAL_KEY_DIR", base / "keys")
        )
        bundle_path = Path(
            os.environ.get(
                "SDS_AI_MEDICAL_POLICY_BUNDLE", base / "policy_bundle.json"
            )
        )
        bundle_public = key_dir / "bundle_signing_public.pem"
        ledger_path = Path(
            os.environ.get(
                "SDS_AI_MEDICAL_LEDGER_PATH", base / "audit_ledger.jsonl"
            )
        )
        try:
            gateway = MedicalAIGateway(
                key_dir=key_dir,
                ledger_path=ledger_path,
                bundle_path=bundle_path,
                bundle_public_key_path=bundle_public,
                glass_box_audit=glass_box_audit,
            )
        except GatewayNotProvisioned as exc:
            return cls(
                None,
                state="NOT_PROVISIONED",
                missing=[exc.state],
                detail=str(exc),
            )
        except GatewayAttestationAbort as exc:
            return cls(
                None,
                state="ATTESTATION_FAILED",
                missing=["ATTESTATION_FAILED"],
                detail=str(exc),
            )
        return cls(gateway, state="OPERATIONAL")

    # -- state ---------------------------------------------------------

    @property
    def operational(self) -> bool:
        return self._gateway is not None

    @property
    def gateway(self) -> Optional[MedicalAIGateway]:
        return self._gateway

    def status(self) -> dict:
        status = {
            "state": self._state,
            "missing": list(self._missing),
            "detail": self._detail,
            "layer": "CONSTITUTIONAL_EXECUTION_STACK",
            "platforms": ["ai_doctor", "sanders_ai_psychiatrist"],
        }
        if self._gateway is not None:
            status["gateway"] = self._gateway.status()
        return status

    # -- evaluation ----------------------------------------------------

    def evaluate_outcome(
        self,
        *,
        platform: str,
        record_id: str,
        subject_ref: str,
        outcome: str,
        evidence_ref: str,
    ) -> dict:
        """Evaluate one platform outcome record through the policy
        kernel. Returns the kernel decision summary when permitted;
        raises EnforcementRefused otherwise (the service refuses the
        commit — the outcome is not recorded)."""
        if self._gateway is None:
            raise EnforcementRefused(
                "AI_MEDICAL_ENFORCEMENT_NOT_PROVISIONED"
                if self._state == "NOT_PROVISIONED"
                else f"AI_MEDICAL_ENFORCEMENT_{self._state}",
                self._detail
                or "the enforcement layer is not operational",
            )
        role = ROLE_BY_PLATFORM[platform]
        risk = OUTCOME_RISK[role][outcome]
        output = {
            "entity_role": role.value,
            "request_id": record_id,
            "timestamp_utc": time.time(),
            "subject_kind": "AI_SYSTEM",
            "subject_ref": subject_ref,
            "outcome": outcome,
            "evidence_ref": evidence_ref,
            "risk_level": risk,
            "requires_human_approval": True,
            "escalate_immediately": risk == "HIGH",
            "signature_basis": "GLASS_BOX_RECEIPT",
        }
        decision = self._gateway.evaluate_platform_output(output, role)
        if not decision.permitted:
            raise EnforcementRefused(
                "AI_MEDICAL_POLICY_VIOLATION",
                "; ".join(decision.violations + decision.unknowns),
            )
        return decision.summary()
