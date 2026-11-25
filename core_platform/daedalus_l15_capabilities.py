"""Daedalus L15+ operational capability declaration.

This is a machine-readable contract for the existing engine, not a claim that
all declared capabilities are active. Runtime integrations must report actual
availability independently of the target specification.

Founder specification (2026-11-25): Daedalus is designed at logic
level 15+ with 20+ capabilities, and L15 is reasoning — the inventory
is headed by the reasoning capability. Under the founder's
native-only law of the same day, the head seat carries its native
identity, ``live_native_reasoning``: the vendor-era name
``live_claude_reasoning`` recorded in the 2026-11-13 contract was the
fossil of the borrowed-provider era, and the seat it named is now
occupied by Daedalus's own native core
(``core_platform/daedalus_native_core.py``). The provider transports
remain optional gated tools; they are not the head capability and
are not declared here. The inventory is extended to the founder's
20+ design set (22 capabilities) with names sourced only from his
own design records — the 2026-11-13 contract below and
``docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md`` /
``docs/DAEDALUS_RECOVERED_INVENTORY_2026-11-03.md`` — recorded per
capability in ``CAPABILITY_SOURCES``. A declared capability is a
design scope statement, never a claim of live operation: each
capability carries its explicit observed state, and a state flips
only on evidence (see ``observed_profile``).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

__all__ = [
    "CAPABILITIES",
    "CAPABILITY_SOURCES",
    "CapabilityState",
    "DaedalusCapabilityProfile",
    "declared_profile",
    "observed_profile",
]


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
    "live_native_reasoning",
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
    "streamed_responses",
    "request_correlation",
    "source_freshness_enforcement",
    "cobol_dialect_analysis",
    "signed_executable_measurement",
    "graph_rag",
    "multi_agent_validation",
    "neurosymbolic_checks",
    "build_deploy_orchestration",
)


# Where each declared capability is named in the founder's own
# design records. The first thirteen entries are the 2026-11-13
# contract this module originally carried (the head seat under its
# native identity per the founder's 2026-11-25 specification); the
# remaining nine are named in the founder's Daedalus design records
# of 2026-10-23 and 2026-11-03. No capability is declared here that
# those records do not name.
CAPABILITY_SOURCES = {
    "live_native_reasoning": (
        "founder specification 2026-11-25 (L15 head seat, native "
        "identity; 2026-11-13 contract, vendor-era name "
        "live_claude_reasoning)"
    ),
    "onnx_language_classification": "2026-11-13 L15+ contract",
    "polyglot_llvm": "2026-11-13 L15+ contract",
    "cobol_priority_one": "2026-11-13 L15+ contract",
    "cobol_bridge": "2026-11-13 L15+ contract",
    "language_registry_203": "2026-11-13 L15+ contract",
    "real_time_events": "2026-11-13 L15+ contract",
    "live_source_provenance": "2026-11-13 L15+ contract",
    "glass_box_audit": "2026-11-13 L15+ contract",
    "shield_sss": "2026-11-13 L15+ contract",
    "shield_sssv3": "2026-11-13 L15+ contract",
    "shield_gss": "2026-11-13 L15+ contract",
    "cross_platform_orchestration": "2026-11-13 L15+ contract",
    "streamed_responses": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 3 "
        "(streamed responses)"
    ),
    "request_correlation": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 3 "
        "(explicit request correlation)"
    ),
    "source_freshness_enforcement": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 6 "
        "(source freshness and provenance enforcement)"
    ),
    "cobol_dialect_analysis": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 4 "
        "(COBOL dialect-aware frontend/analysis)"
    ),
    "signed_executable_measurement": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 5 "
        "(signed executable measurement)"
    ),
    "graph_rag": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 8 "
        "(Graph-RAG)"
    ),
    "multi_agent_validation": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 8 "
        "(multi-agent validation)"
    ),
    "neurosymbolic_checks": (
        "docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md, required mapping 8 "
        "(neurosymbolic checks)"
    ),
    "build_deploy_orchestration": (
        "docs/DAEDALUS_RECOVERED_INVENTORY_2026-11-03.md (polyglot "
        "build/deploy orchestration)"
    ),
}


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


def observed_profile(
    probes: Mapping[str, Callable[[], bool]] | None = None,
    *,
    live_reasoning_configured: bool = False,
    **states: CapabilityState,
) -> DaedalusCapabilityProfile:
    """Observed capability profile, accepting both call styles.

    Unified 2026-11-13 (deploy/simultaneous): two branches defined
    incompatible ``observed_profile`` signatures, so this one accepts
    both, and both test suites pass against it:

    * Probe style (upgrade/real-world): ``observed_profile(probes)`` —
      a capability is ACTIVE only if its probe callable returns True
      now; no probe -> UNAVAILABLE. A declaration can never flip
      itself to working.
    * Explicit style (upgrade/sota-daedalus-voice):
      ``observed_profile(live_reasoning_configured=True, **states)`` —
      only ``live_native_reasoning`` may be CONFIGURED from
      configuration alone; ACTIVE is never set here (it requires a
      successful live call, which this function does not make).
      Unknown capability names are rejected.

    When both are given, probes run first and explicit states override
    the probed value for the named capabilities.
    """
    for name in states:
        if name not in CAPABILITIES:
            raise ValueError(f"Unknown Daedalus capability: {name}")
    if probes:
        for name in probes:
            if name not in CAPABILITIES:
                raise ValueError(f"Unknown Daedalus capability: {name}")
    observed = {
        name: (
            CapabilityState.ACTIVE
            if probes is not None and probes.get(name, lambda: False)()
            else CapabilityState.UNAVAILABLE
        )
        for name in CAPABILITIES
    }
    if live_reasoning_configured and "live_native_reasoning" not in states:
        observed["live_native_reasoning"] = CapabilityState.CONFIGURED
    observed.update(states)
    return DaedalusCapabilityProfile(
        identity=DAEDALUS_IDENTITY,
        level_target=TARGET_LEVEL,
        language_target=TARGET_LANGUAGE_COUNT,
        platform_target=TARGET_PLATFORM_COUNT,
        capability_states=observed,
    )


def require_capability(profile: DaedalusCapabilityProfile, name: str) -> None:
    """Refuse to run a capability that has not been observed ACTIVE."""
    if profile.capability_states.get(name) is not CapabilityState.ACTIVE:
        raise RuntimeError(
            f"Capability {name} is not ACTIVE "
            f"(observed: {profile.capability_states.get(name)})")
