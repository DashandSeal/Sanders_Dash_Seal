"""Sanders AI Medical — Fail-State Machine.

Deterministic failure-state management, built from the received
design (2026-11-25) with the Fix 12 change:

- FIX 12: the received HALTED handler blocked the calling thread
  forever (an unbounded sleep loop). HALTED is now a FLAG: entering
  HALTED sets the halt state, notifies, and RETURNS. Callers refuse
  work through safe_to_process(); only the human steward's
  authorization moves the machine out of HALTED (Charter Art. VII).
- SHUTDOWN: the received build killed the process from inside the
  library. Termination is now the embedding process's decision:
  the machine reaches SHUTDOWN and invokes the shutdown callback;
  it sends a signal only when constructed with
  terminate_on_shutdown=True (standalone gateway process mode).
  In the repo's server process the default is False — the state
  still fails closed (safe_to_process() is False) without killing
  the host application.

State graph: OPERATIONAL -> DEGRADED -> SAFE_HOLD -> HALTED ->
SHUTDOWN, with steward-authorized recovery from SAFE_HOLD and
HALTED only.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("sds.ai_medical.fail_state")


class SystemState(Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    SAFE_HOLD = "SAFE_HOLD"
    HALTED = "HALTED"
    SHUTDOWN = "SHUTDOWN"


class FailureTrigger(Enum):
    INTEGRITY_CHECK_FAILED = "INTEGRITY_CHECK_FAILED"
    POLICY_KERNEL_FAILURE = "POLICY_KERNEL_FAILURE"
    IDENTITY_ATTESTATION_FAILED = "IDENTITY_ATTESTATION_FAILED"
    CONSTRAINT_ENGINE_FAILURE = "CONSTRAINT_ENGINE_FAILURE"
    SEMANTIC_RISK_CRITICAL = "SEMANTIC_RISK_CRITICAL"
    CROSS_VALIDATION_CONFLICT = "CROSS_VALIDATION_CONFLICT"
    LEDGER_WRITE_FAILED = "LEDGER_WRITE_FAILED"
    REPEATED_VIOLATIONS = "REPEATED_VIOLATIONS"
    HUMAN_STEWARD_COMMAND = "HUMAN_STEWARD_COMMAND"
    RECOVERY_AUTHORIZED = "RECOVERY_AUTHORIZED"


@dataclass
class StateTransition:
    from_state: SystemState
    to_state: SystemState
    trigger: FailureTrigger
    timestamp_utc: float = field(default_factory=time.time)
    detail: str = ""


# Allowed transitions: trigger -> {from_state: to_state}
_TRANSITIONS: dict[FailureTrigger, dict[SystemState, SystemState]] = {
    FailureTrigger.INTEGRITY_CHECK_FAILED: {
        SystemState.OPERATIONAL: SystemState.SHUTDOWN,
        SystemState.DEGRADED: SystemState.SHUTDOWN,
        SystemState.SAFE_HOLD: SystemState.SHUTDOWN,
        SystemState.HALTED: SystemState.SHUTDOWN,
    },
    FailureTrigger.IDENTITY_ATTESTATION_FAILED: {
        SystemState.OPERATIONAL: SystemState.SHUTDOWN,
        SystemState.DEGRADED: SystemState.SHUTDOWN,
        SystemState.SAFE_HOLD: SystemState.SHUTDOWN,
        SystemState.HALTED: SystemState.SHUTDOWN,
    },
    FailureTrigger.POLICY_KERNEL_FAILURE: {
        SystemState.OPERATIONAL: SystemState.HALTED,
        SystemState.DEGRADED: SystemState.HALTED,
        SystemState.SAFE_HOLD: SystemState.HALTED,
    },
    FailureTrigger.CONSTRAINT_ENGINE_FAILURE: {
        SystemState.OPERATIONAL: SystemState.DEGRADED,
        SystemState.DEGRADED: SystemState.SAFE_HOLD,
    },
    FailureTrigger.SEMANTIC_RISK_CRITICAL: {
        SystemState.OPERATIONAL: SystemState.HALTED,
        SystemState.DEGRADED: SystemState.HALTED,
        SystemState.SAFE_HOLD: SystemState.HALTED,
    },
    FailureTrigger.CROSS_VALIDATION_CONFLICT: {
        SystemState.OPERATIONAL: SystemState.SAFE_HOLD,
        SystemState.DEGRADED: SystemState.SAFE_HOLD,
    },
    FailureTrigger.LEDGER_WRITE_FAILED: {
        SystemState.OPERATIONAL: SystemState.HALTED,
        SystemState.DEGRADED: SystemState.HALTED,
        SystemState.SAFE_HOLD: SystemState.HALTED,
    },
    FailureTrigger.REPEATED_VIOLATIONS: {
        SystemState.OPERATIONAL: SystemState.SAFE_HOLD,
        SystemState.DEGRADED: SystemState.HALTED,
        SystemState.SAFE_HOLD: SystemState.HALTED,
    },
    FailureTrigger.HUMAN_STEWARD_COMMAND: {
        SystemState.OPERATIONAL: SystemState.HALTED,
        SystemState.DEGRADED: SystemState.HALTED,
        SystemState.SAFE_HOLD: SystemState.HALTED,
        SystemState.HALTED: SystemState.SHUTDOWN,
    },
    FailureTrigger.RECOVERY_AUTHORIZED: {
        SystemState.SAFE_HOLD: SystemState.OPERATIONAL,
        SystemState.HALTED: SystemState.OPERATIONAL,
        SystemState.DEGRADED: SystemState.OPERATIONAL,
    },
}


class FailStateMachine:
    """Owns the system's failure state. Thread-agnostic: transitions
    are synchronous and non-blocking (Fix 12)."""

    def __init__(
        self,
        *,
        on_state_change: Optional[
            Callable[[StateTransition], None]
        ] = None,
        shutdown_callback: Optional[Callable[[], None]] = None,
        terminate_on_shutdown: bool = False,
        violation_threshold: int = 3,
    ):
        self._state = SystemState.OPERATIONAL
        self._history: list[StateTransition] = []
        self._on_state_change = on_state_change
        self._shutdown_callback = shutdown_callback
        self._terminate = terminate_on_shutdown
        self._violation_count = 0
        self._violation_threshold = violation_threshold
        self._halt_detail = ""

    @property
    def state(self) -> SystemState:
        return self._state

    @property
    def halted(self) -> bool:
        """The HALT flag (Fix 12): a state, never a blocked thread."""
        return self._state in (SystemState.HALTED, SystemState.SHUTDOWN)

    @property
    def history(self) -> list[StateTransition]:
        return list(self._history)

    def safe_to_process(self) -> bool:
        return self._state in (
            SystemState.OPERATIONAL,
            SystemState.DEGRADED,
        )

    def record_violation(self) -> Optional[StateTransition]:
        """Count a violation; escalate at the threshold."""
        self._violation_count += 1
        if self._violation_count >= self._violation_threshold:
            return self.trigger(
                FailureTrigger.REPEATED_VIOLATIONS,
                f"{self._violation_count} violations recorded",
            )
        return None

    def trigger(
        self, trigger: FailureTrigger, detail: str = ""
    ) -> StateTransition:
        mapping = _TRANSITIONS.get(trigger, {})
        target = mapping.get(self._state)
        if target is None:
            # No defined transition: hold state, record the attempt.
            transition = StateTransition(
                from_state=self._state,
                to_state=self._state,
                trigger=trigger,
                detail=f"no transition defined: {detail}",
            )
            self._history.append(transition)
            return transition
        transition = StateTransition(
            from_state=self._state,
            to_state=target,
            trigger=trigger,
            detail=detail,
        )
        self._state = target
        self._history.append(transition)
        logger.warning(
            "AI MEDICAL STATE: %s -> %s (%s) %s",
            transition.from_state.value,
            transition.to_state.value,
            trigger.value,
            detail,
        )
        if target == SystemState.HALTED:
            self._halt_detail = detail
        if self._on_state_change is not None:
            self._on_state_change(transition)
        if target == SystemState.SHUTDOWN:
            if self._shutdown_callback is not None:
                self._shutdown_callback()
            if self._terminate:
                os.kill(os.getpid(), signal.SIGTERM)
        return transition

    def authorize_recovery(self, detail: str = "") -> StateTransition:
        """Human-steward-authorized recovery (Charter Art. VII).
        Callers must have authenticated the steward; the machine
        records the authorization as a transition."""
        transition = self.trigger(
            FailureTrigger.RECOVERY_AUTHORIZED,
            detail or "steward-authorized recovery",
        )
        if transition.to_state == SystemState.OPERATIONAL:
            self._violation_count = 0
            self._halt_detail = ""
        return transition

    def status(self) -> dict:
        return {
            "state": self._state.value,
            "halted": self.halted,
            "safe_to_process": self.safe_to_process(),
            "violation_count": self._violation_count,
            "halt_detail": self._halt_detail,
            "transitions": len(self._history),
        }
