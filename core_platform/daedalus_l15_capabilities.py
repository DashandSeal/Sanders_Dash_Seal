"""Daedalus L15+ operational capability declaration.

This is a machine-readable contract for the existing engine, not a claim that
all declared capabilities are active. Runtime integrations must report actual
availability independently of the target specification.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class CapabilityState(str, Enum):
    UNAVAILABLE = "unavailable"
    CONFIGURED = "configured"
    ACTIVE = "active"


DAEDALUS_IDENTITY = "DAEDALUS"
POLYGLOT_IDENTITY = "Polyglot Engine LLVM"
COBOL_BRIDGE_IDENTITY = "COBOL BRIDGE"
TARGET_LEVEL = "L15+"
TARGET_LANGUAGE_COUNT = 203
TARGET_PLATFORM_COUNT = 41
TARGET_CODE_GENERATION_MS = 5000
TARGET_LANGUAGE_DETECTION_MS = 100


CAPABILITIES = (
    "live_claude_reasoning",
    "onnx_language_classification",
    "polyglot_llvm",
    "cobol_priority_one",
    "cobol_bridge",
    "language_registry_203",
    "real_time_events",
    "live_source_provenance",
    "glass_box_audit",
    "shield_sss",
    "shield_sssv3",
    "shield_gss",
    "cross_platform_orchestration",
)


@dataclass(frozen=True)
class DaedalusCapabilityProfile:
    """Declared design target with independent observed state per capability."""

    identity: str
    level_target: str
    language_target: int
    platform_target: int
    capability_states: Mapping[str, CapabilityState]

    def __post_init__(self) -> None:
        if self.identity != DAEDALUS_IDENTITY:
            raise ValueError("Daedalus identity is immutable")
        if self.level_target != TARGET_LEVEL:
            raise ValueError("Daedalus level target must remain L15+")
        if self.language_target != TARGET_LANGUAGE_COUNT:
            raise ValueError("Daedalus language target must remain 203")
        if self.platform_target != TARGET_PLATFORM_COUNT:
            raise ValueError("Daedalus platform target must remain 41")
        if set(self.capability_states) != set(CAPABILITIES):
            raise ValueError("Capability inventory must be complete")
        if any(not isinstance(value, CapabilityState) for value in self.capability_states.values()):
            raise TypeError("Capability states must be explicit")

    @property
    def fully_active(self) -> bool:
        return all(state is CapabilityState.ACTIVE for state in self.capability_states.values())

    def report(self) -> dict:
        return {
            "identity": self.identity,
            "level_target": self.level_target,
            "language_target": self.language_target,
            "platform_target": self.platform_target,
            "polyglot_identity": POLYGLOT_IDENTITY,
            "cobol_bridge_identity": COBOL_BRIDGE_IDENTITY,
            "fully_active": self.fully_active,
            "capabilities": {key: value.value for key, value in sorted(self.capability_states.items())},
        }


def declared_profile() -> DaedalusCapabilityProfile:
    """No capability is marked active until the live engine reports it."""
    return DaedalusCapabilityProfile(
        identity=DAEDALUS_IDENTITY,
        level_target=TARGET_LEVEL,
        language_target=TARGET_LANGUAGE_COUNT,
        platform_target=TARGET_PLATFORM_COUNT,
        capability_states={name: CapabilityState.UNAVAILABLE for name in CAPABILITIES},
    )
