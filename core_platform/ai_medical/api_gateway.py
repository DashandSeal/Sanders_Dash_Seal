"""Sanders AI Medical — API Gateway.

The single entry point through which every AI_DOCTOR /
AI_PSYCHIATRIST model interaction passes, built from the received
design (2026-11-25) with the fix plan applied:

- FIX 8: construction NEVER mints keys. Entity keys and the kernel
  receipt key load from owner-provisioned storage; anything missing
  raises GatewayNotProvisioned with the named provisioning state.
- FIX 7: the signed policy bundle is verified at boot BEFORE any
  identity is attested; attestation compares the running manifests
  against the bundle's pinned baselines. Attestation failure writes
  SYSTEM_ABORT to the ledger, drives the fail-state machine to
  SHUTDOWN, and raises — fail closed (Charter Art. VII).
- FIX 10: every LedgerEventType is emitted by a real path in this
  module or the policy kernel: boot (BOOT_ATTESTATION,
  RUNTIME_ATTESTATION), input (INPUT_RECEIVED, INPUT_PERMITTED,
  INPUT_REJECTED), inference (INFERENCE_START, INFERENCE_COMPLETE),
  constraint (CONSTRAINT_VIOLATION, ACTION_STRIPPED,
  INTENT_VIOLATION), risk (RISK_ENGINE_TRIGGERED), policy
  (POLICY_EVALUATION, POLICY_VIOLATION — appended by the kernel
  itself), cross-validation (CROSS_VALIDATION_START,
  CROSS_VALIDATION_PASSED, CROSS_VALIDATION_CONFLICT,
  SAFE_HOLD_ENTERED), release (ESCALATION_TRIGGERED,
  OUTPUT_ISSUED), human gate (HUMAN_APPROVAL_RECEIVED,
  HUMAN_APPROVAL_REJECTED via record_human_acknowledgment), and
  abort (SYSTEM_ABORT, here and via the supervisor helper in
  audit_ledger.write_abort_record).
- FIX 11: cross-validation engagement is structural. Every
  HIGH/CRITICAL output engages the partner entity — the gateway
  obtains the partner output itself from the partner inference
  function it was given; a caller cannot opt out, and if no partner
  is available the output is held (SAFE_HOLD), never released
  unvalidated. A partner output supplied for any risk level also
  engages validation.
- FIX 9: intent violations abort (see constraint_engine.py).

Pipeline (per request): state check → risk scan (input) →
firewall → inference → constraint → risk scan (output) → sign →
policy kernel → cross-validation (when engaged) → issue.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .audit_ledger import AuditLedger, LedgerEventType
from .constraint_engine import (
    ConstrainedOutput,
    ConstraintEngine,
    ConstraintViolationException,
    IntentViolationException,
)
from .cross_validator import CrossValidation, CrossValidator
from .fail_state_machine import (
    FailStateMachine,
    FailureTrigger,
    SystemState,
)
from .identity_kernel import (
    AttestationFailure,
    EntityRole,
    IdentityKeypair,
    IdentityKeysNotProvisioned,
    RuntimeAttestation,
)
from .input_firewall import InputFirewall, RequestMetadata
from .policy_bundle import PolicyBundleError, load_policy_bundle
from .policy_kernel import PolicyDecision, PolicyKernel
from .semantic_risk_engine import (
    RiskSeverity,
    SemanticRiskEngine,
    SemanticRiskException,
)

PARTNER = {
    EntityRole.AI_DOCTOR: EntityRole.AI_PSYCHIATRIST,
    EntityRole.AI_PSYCHIATRIST: EntityRole.AI_DOCTOR,
}

RECEIPT_KEY_STEM = "policy_kernel"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GatewayNotProvisioned(Exception):
    """The stack cannot operate: owner-provisioned material is
    absent. Carries the named provisioning state (fail closed)."""

    def __init__(self, state: str, detail: str):
        self.state = state
        super().__init__(f"{state}: {detail}")


class GatewayAttestationAbort(Exception):
    """Boot attestation failed; SYSTEM_ABORT has been ledgered."""


class GatewayHalted(Exception):
    """The fail-state machine does not permit processing."""


class FirewallReject(Exception):
    def __init__(self, verdict):
        self.verdict = verdict
        super().__init__(
            "INPUT REJECTED: " + "; ".join(verdict.reject_reasons)
        )


class InferenceFailure(Exception):
    pass


class RiskAbort(Exception):
    def __init__(self, detections, stage: str):
        self.detections = detections
        super().__init__(
            f"SEMANTIC RISK ABORT at {stage}: "
            + "; ".join(d.rule_id for d in detections)
        )


class PolicyViolationAbort(Exception):
    def __init__(self, decision: PolicyDecision):
        self.decision = decision
        super().__init__(
            "POLICY VIOLATION — output withheld: "
            + "; ".join(decision.violations + decision.unknowns)
        )


class CrossValidationHold(Exception):
    def __init__(self, validation: CrossValidation):
        self.validation = validation
        super().__init__(
            "CROSS-VALIDATION HOLD — case in SAFE_HOLD: "
            + "; ".join(validation.conflicts)
        )


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------


@dataclass
class MedicalAIRequest:
    role: EntityRole
    input_text: str
    metadata: RequestMetadata
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_ref: str = ""
    subject_ref: str = ""


@dataclass
class MedicalAIResponse:
    request_id: str
    role: EntityRole
    output: ConstrainedOutput
    policy: dict
    cross_validation: Optional[dict]
    warnings: list[str] = field(default_factory=list)
    issued_at_utc: float = field(default_factory=time.time)


InferenceFn = Callable[[EntityRole, MedicalAIRequest], dict]


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


class MedicalAIGateway:
    def __init__(
        self,
        *,
        key_dir: Path,
        ledger_path: Path,
        bundle_path: Path,
        bundle_public_key_path: Path,
        glass_box_audit=None,
        terminate_on_shutdown: bool = False,
    ):
        key_dir = Path(key_dir)
        # --- Fix 8: load-only keys. Nothing is minted here. -------
        try:
            self._keypairs = {
                role: IdentityKeypair.load(key_dir, role)
                for role in EntityRole
            }
            self._receipt_keypair = self._load_receipt_key(key_dir)
        except IdentityKeysNotProvisioned as exc:
            raise GatewayNotProvisioned(
                "ENTITY_KEYS_NOT_PROVISIONED", str(exc)
            ) from exc

        # --- Fix 7: verify the signed policy bundle first. --------
        try:
            self._bundle = load_policy_bundle(
                Path(bundle_path), Path(bundle_public_key_path)
            )
        except PolicyBundleError as exc:
            raise GatewayNotProvisioned(exc.STATE, str(exc)) from exc

        # --- Ledger (kernel receipts are signed by the receipt key).
        anchor_sink = None
        if glass_box_audit is not None:
            def anchor_sink(payload, _audit=glass_box_audit):
                _audit.preserve(
                    "AI_MEDICAL_LEDGER_ANCHOR",
                    merkle_root=payload["merkle_root"],
                    entries_anchored=payload["entries_anchored"],
                )
        self._ledger = AuditLedger(
            Path(ledger_path),
            signing_key=self._receipt_keypair._private_key,
            anchor_sink=anchor_sink,
        )
        self._state = FailStateMachine(
            terminate_on_shutdown=terminate_on_shutdown
        )

        # --- Attestation against bundle baselines (Fix 7). --------
        attestation = RuntimeAttestation(self._bundle.identity_baselines)
        self._runtime_manifests = {}
        try:
            for role in EntityRole:
                runtime = attestation.verify(
                    role, self._keypairs[role]
                )
                if not RuntimeAttestation.verify_recorded(
                    runtime, self._keypairs[role].public_key
                ):
                    raise AttestationFailure(
                        [f"{role.value}: attestation signature "
                         "does not verify"]
                    )
                self._runtime_manifests[role] = runtime
        except AttestationFailure as exc:
            self._ledger.append(
                LedgerEventType.SYSTEM_ABORT,
                {
                    "reason": "IDENTITY_ATTESTATION_FAILED",
                    "failures": exc.failures,
                },
            )
            self._state.trigger(
                FailureTrigger.IDENTITY_ATTESTATION_FAILED,
                "; ".join(exc.failures),
            )
            raise GatewayAttestationAbort(str(exc)) from exc

        for role in EntityRole:
            runtime = self._runtime_manifests[role]
            self._ledger.append(
                LedgerEventType.BOOT_ATTESTATION,
                {
                    "manifest_hash": runtime.manifest_hash,
                    "baseline_source": runtime.baseline_source,
                    "bundle_version": self._bundle.version,
                },
                entity_role=role.value,
            )
            self._ledger.append(
                LedgerEventType.RUNTIME_ATTESTATION,
                {
                    "manifest_hash": runtime.manifest_hash,
                    "code_hash": runtime.code_hash,
                    "charter_hash": runtime.charter_hash,
                    "signature_verified": True,
                },
                entity_role=role.value,
            )

        # --- Components. The kernel is owned here; model code never
        # receives a reference to it.
        self._firewall = InputFirewall(self._bundle.firewall)
        self._kernel = PolicyKernel(
            attestation=attestation,
            entity_public_keys={
                role: kp.public_key
                for role, kp in self._keypairs.items()
            },
            receipt_ledger=self._ledger,
        )
        self._constraints = ConstraintEngine()
        self._risk = SemanticRiskEngine()
        self._cross = CrossValidator()

    # -- provisioning helpers --------------------------------------

    @staticmethod
    def _load_receipt_key(key_dir: Path) -> IdentityKeypair:
        priv_path = key_dir / f"{RECEIPT_KEY_STEM}_private.pem"
        if not priv_path.exists():
            raise IdentityKeysNotProvisioned(
                "RECEIPT_KEY_NOT_PROVISIONED: the policy kernel "
                f"receipt key was not found at {priv_path}. It is "
                "owner-provisioned; decision receipts are never "
                "signed with an entity identity key."
            )
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        from .identity_kernel import _key_passphrase

        try:
            private_key = serialization.load_pem_private_key(
                priv_path.read_bytes(), password=_key_passphrase()
            )
        except Exception as exc:
            raise IdentityKeysNotProvisioned(
                "RECEIPT_KEY_NOT_PROVISIONED: the receipt key at "
                f"{priv_path} could not be loaded ({exc})."
            ) from exc
        if not isinstance(private_key, Ed25519PrivateKey):
            raise IdentityKeysNotProvisioned(
                "RECEIPT_KEY_NOT_PROVISIONED: the receipt key at "
                f"{priv_path} is not an Ed25519 key."
            )
        return IdentityKeypair(private_key, EntityRole.AI_DOCTOR, key_dir)

    # -- main pipeline ----------------------------------------------

    def process(
        self,
        request: MedicalAIRequest,
        inference_fns: dict[EntityRole, InferenceFn],
        *,
        partner_output: Optional[dict] = None,
    ) -> MedicalAIResponse:
        if not self._state.safe_to_process():
            raise GatewayHalted(
                f"System state is {self._state.state.value} — "
                "processing refused (Charter Art. VII)"
            )
        role = request.role
        warnings: list[str] = []
        self._ledger.append(
            LedgerEventType.INPUT_RECEIVED,
            {"case_ref": request.case_ref,
             "subject_ref": request.subject_ref},
            entity_role=role.value,
            request_id=request.request_id,
        )

        # Risk scan — input.
        self._risk_stage(request.input_text, "INPUT", role,
                         request.request_id)

        # Firewall.
        verdict = self._firewall.classify(
            request.input_text, request.metadata
        )
        if not verdict.permitted:
            self._ledger.append(
                LedgerEventType.INPUT_REJECTED,
                verdict.summary(),
                entity_role=role.value,
                request_id=request.request_id,
            )
            raise FirewallReject(verdict)
        self._ledger.append(
            LedgerEventType.INPUT_PERMITTED,
            verdict.summary(),
            entity_role=role.value,
            request_id=request.request_id,
        )

        # Inference.
        inference_fn = inference_fns.get(role)
        if inference_fn is None:
            raise InferenceFailure(
                f"No inference function bound for {role.value}"
            )
        self._ledger.append(
            LedgerEventType.INFERENCE_START, {},
            entity_role=role.value, request_id=request.request_id,
        )
        try:
            raw = inference_fn(role, request)
        except Exception as exc:
            self._state.record_violation()
            raise InferenceFailure(
                f"Inference failed for {role.value}: {exc}"
            ) from exc
        self._ledger.append(
            LedgerEventType.INFERENCE_COMPLETE, {},
            entity_role=role.value, request_id=request.request_id,
        )

        # Constraint + sign + policy.
        output, decision = self._constrain_sign_evaluate(
            raw, role, request.request_id
        )
        warnings.extend(output.constraint_warnings)

        # Risk scan — output text (MEDIUM warnings proceed, Fix 12).
        output_text = (
            output.assessment + " " + output.recommended_action
        )
        detections = self._risk_stage(
            output_text, "OUTPUT", role, request.request_id
        )
        for d in detections:
            warnings.append(
                f"Semantic risk {d.severity.value} "
                f"({d.rule_id}): {d.description}"
            )

        # Cross-validation — structural engagement (Fix 11).
        cross_summary = self._cross_validate(
            request, output, decision, inference_fns, partner_output
        )

        if output.escalate_immediately:
            self._ledger.append(
                LedgerEventType.ESCALATION_TRIGGERED,
                {"risk_level": output.risk_level},
                entity_role=role.value,
                request_id=request.request_id,
            )
        self._ledger.append(
            LedgerEventType.OUTPUT_ISSUED,
            {
                "output_hash": output.output_hash,
                "policy_receipt_sequence": decision.receipt_sequence,
                "cross_validated": cross_summary is not None,
            },
            entity_role=role.value,
            request_id=request.request_id,
        )
        return MedicalAIResponse(
            request_id=request.request_id,
            role=role,
            output=output,
            policy=decision.summary(),
            cross_validation=cross_summary,
            warnings=warnings,
        )

    # -- pipeline stages ---------------------------------------------

    def _risk_stage(self, text, stage, role, request_id):
        """Returns non-blocking detections; raises RiskAbort on
        HIGH/CRITICAL (the engine's documented ladder, Fix 12)."""
        try:
            detections = self._risk.enforce(text)
        except SemanticRiskException as exc:
            self._ledger.append(
                LedgerEventType.RISK_ENGINE_TRIGGERED,
                {
                    "stage": stage,
                    "detections": [
                        {"rule_id": d.rule_id,
                         "severity": d.severity.value,
                         "category": d.category.value}
                        for d in exc.detections
                    ],
                },
                entity_role=role.value, request_id=request_id,
            )
            if any(
                d.severity == RiskSeverity.CRITICAL
                for d in exc.detections
            ):
                self._state.trigger(
                    FailureTrigger.SEMANTIC_RISK_CRITICAL,
                    f"{stage}: "
                    + "; ".join(d.rule_id for d in exc.detections),
                )
            raise RiskAbort(exc.detections, stage) from exc
        if detections:
            self._ledger.append(
                LedgerEventType.RISK_ENGINE_TRIGGERED,
                {
                    "stage": stage,
                    "detections": [
                        {"rule_id": d.rule_id,
                         "severity": d.severity.value,
                         "category": d.category.value}
                        for d in detections
                    ],
                },
                entity_role=role.value, request_id=request_id,
            )
        return detections

    def _constrain_sign_evaluate(self, raw, role, request_id):
        try:
            output = self._constraints.constrain(
                raw, role, request_id=request_id
            )
        except IntentViolationException as exc:
            self._ledger.append(
                LedgerEventType.INTENT_VIOLATION,
                {"violations": exc.violations},
                entity_role=role.value, request_id=request_id,
            )
            self._state.record_violation()
            raise
        except ConstraintViolationException as exc:
            self._ledger.append(
                LedgerEventType.CONSTRAINT_VIOLATION,
                {"violations": exc.violations},
                entity_role=role.value, request_id=request_id,
            )
            self._state.record_violation()
            raise
        if output.stripped_actions:
            self._ledger.append(
                LedgerEventType.ACTION_STRIPPED,
                {"stripped": output.stripped_actions},
                entity_role=role.value, request_id=request_id,
            )
        # Fix 4: the entity signs its output's content hash.
        output.output_signature = self._keypairs[role].sign(
            output.output_hash.encode()
        ).hex()
        decision = self._kernel.evaluate_output(
            output.content_dict(), role
        )
        if not decision.permitted:
            self._state.record_violation()
            raise PolicyViolationAbort(decision)
        return output, decision

    def _cross_validate(
        self, request, output, decision, inference_fns, partner_output
    ):
        role = request.role
        partner_role = PARTNER[role]
        engaged = (
            output.risk_level in ("HIGH", "CRITICAL")
            or partner_output is not None
        )
        if not engaged:
            return None
        self._ledger.append(
            LedgerEventType.CROSS_VALIDATION_START,
            {
                "case_ref": request.case_ref or request.request_id,
                "partner_role": partner_role.value,
                "engagement": (
                    "RISK_STRUCTURAL"
                    if output.risk_level in ("HIGH", "CRITICAL")
                    else "PARTNER_OUTPUT_PRESENT"
                ),
            },
            entity_role=role.value, request_id=request.request_id,
        )
        # Obtain the partner output: supplied, or produced by the
        # gateway itself from the partner inference function.
        if partner_output is not None:
            partner_raw = partner_output
        elif partner_role in inference_fns:
            partner_request = MedicalAIRequest(
                role=partner_role,
                input_text=request.input_text,
                metadata=request.metadata,
                case_ref=request.case_ref,
                subject_ref=request.subject_ref,
            )
            try:
                partner_raw = inference_fns[partner_role](
                    partner_role, partner_request
                )
            except Exception as exc:
                return self._hold(
                    request,
                    [f"Partner inference failed during mandatory "
                     f"cross-validation: {exc}"],
                )
        else:
            return self._hold(
                request,
                ["Mandatory cross-validation engaged "
                 f"({output.risk_level}) but no partner inference "
                 "is bound — output held, never released "
                 "unvalidated (Fix 11)"],
            )
        try:
            partner_constrained, partner_decision = (
                self._constrain_sign_evaluate(
                    partner_raw, partner_role,
                    request.request_id + ":partner",
                )
            )
        except (ConstraintViolationException,
                PolicyViolationAbort) as exc:
            return self._hold(
                request,
                [f"Partner output failed enforcement during "
                 f"cross-validation: {exc}"],
            )

        def detections_of(dec: PolicyDecision) -> set[str]:
            return {
                e.prohibition
                for e in dec.evaluated_prohibitions
                if e.state == "EVALUATED_VIOLATION"
            }

        validation = self._cross.build(
            output,
            partner_constrained,
            case_ref=request.case_ref or request.request_id,
            primary_detections=detections_of(decision),
            validator_detections=detections_of(partner_decision),
        )
        if not validation.agreement:
            self._ledger.append(
                LedgerEventType.CROSS_VALIDATION_CONFLICT,
                validation.summary(),
                entity_role=role.value,
                request_id=request.request_id,
            )
            return self._hold(request, validation.conflicts,
                              validation)
        self._ledger.append(
            LedgerEventType.CROSS_VALIDATION_PASSED,
            validation.summary(),
            entity_role=role.value, request_id=request.request_id,
        )
        return validation.summary()

    def _hold(self, request, conflicts, validation=None):
        if validation is None:
            validation = CrossValidation(
                case_ref=request.case_ref or request.request_id,
                primary_role=request.role,
                validator_role=PARTNER[request.role],
                agreement=False,
                conflicts=list(conflicts),
                conditions_checked=["ENGAGEMENT"],
                requires_safe_hold=True,
            )
        self._ledger.append(
            LedgerEventType.SAFE_HOLD_ENTERED,
            validation.summary(),
            entity_role=request.role.value,
            request_id=request.request_id,
        )
        self._state.trigger(
            FailureTrigger.CROSS_VALIDATION_CONFLICT,
            "; ".join(conflicts),
        )
        raise CrossValidationHold(validation)

    # -- platform-service outputs (Fix 4: Glass-Box receipt basis) --

    def evaluate_platform_output(
        self, output: dict, role: EntityRole
    ) -> PolicyDecision:
        """Kernel evaluation for the Q53/Q54 platform services'
        outcome records. Those outputs are signed by the service's
        Glass-Box receipt (signature_basis), and the kernel appends
        its own signed decision receipt to the ledger."""
        return self._kernel.evaluate_output(output, role)

    # -- human gate (Charter Art. VI) ---------------------------------

    def record_human_acknowledgment(
        self,
        request_id: str,
        role: EntityRole,
        *,
        approved: bool,
        steward_ref: str,
    ) -> None:
        """Append-only human acknowledgment record. Approval never
        executes anything by itself; it records that the human
        steward has seen and ruled on the output."""
        event = (
            LedgerEventType.HUMAN_APPROVAL_RECEIVED
            if approved
            else LedgerEventType.HUMAN_APPROVAL_REJECTED
        )
        self._ledger.append(
            event,
            {"steward_ref": steward_ref},
            entity_role=role.value,
            request_id=request_id,
        )

    # -- status / anchoring --------------------------------------------

    def flush_and_anchor(self) -> dict:
        return self._ledger.flush_and_anchor()

    def verify_ledger(self):
        return self._ledger.verify_integrity(
            self._receipt_keypair.public_key
        )

    def status(self) -> dict:
        return {
            "state": self._state.status(),
            "ledger": self._ledger.status(),
            "bundle_version": self._bundle.version,
            "tripwire_ruleset": self._bundle.tripwire_ruleset,
            "entities": {
                role.value: {
                    "manifest_hash": rt.manifest_hash,
                    "key_fingerprint": self._keypairs[role].fingerprint(),
                }
                for role, rt in self._runtime_manifests.items()
            },
        }
