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
20+ design set (26 capabilities: 22 with names sourced only from
his own design records, plus the four founder-directed additions
named below) — the 2026-11-13 contract below and
``docs/DAEDALUS_LIVE_UPGRADE_2026-10-23.md`` /
``docs/DAEDALUS_RECOVERED_INVENTORY_2026-11-03.md`` — recorded per
capability in ``CAPABILITY_SOURCES``. A declared capability is a
design scope statement, never a claim of live operation: each
capability carries its explicit observed state, and a state flips
only on evidence (see ``observed_profile``).

Four capabilities are founder-directed additions of 2026-11-25
rather than names from the records above: ``real_time_learning``,
added on the founder's direction of that day — "He's got to have
the ability to actually learn in real time" — and recorded as such
in ``CAPABILITY_SOURCES``. It is performed by the persistent
learned-knowledge store and the native core's incorporation loop
(``core_platform/daedalus_knowledge_store.py``,
``core_platform/daedalus_native_core.py``). It is a different
capability from ``real_time_events``: learning is the incorporation
of taught knowledge and recorded outcomes into later reasoning,
not real-time event handling, and the two are declared and
observed separately.

The other three additions come from the founder's protection
direction of the same day — "He's got to be tamper proof quantum
encryption protection protocols with the full Sanders labyrinth
shield 🛡️ and the RTSA minotaur patoling the labyrinth shield
itself": ``labyrinth_shield_binding``, ``minotaur_integrity_patrol``,
and ``quantum_protection_protocols``, performed by the protection
layer (``core_platform/daedalus_protection.py``) wired
platform-to-platform with the Sanders Labyrinth Shield RTSA and
the RTSA Minotaur — both full platforms with their own identities,
neither absorbed into Daedalus. They are distinct from the
2026-11-13 contract's ``shield_sss`` / ``shield_sssv3`` /
``shield_gss``: those remain separately named owner-defined
components (per the 2026-10-23 design record), no implementation
under those names exists, and the Labyrinth Shield binding is not
renamed into them — they stay declared and unavailable until an
implementation under their own names exists.
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
    "real_time_learning",
    "labyrinth_shield_binding",
    "minotaur_integrity_patrol",
    "quantum_protection_protocols",
)


# Where each declared capability is named. The first thirteen
# entries are the 2026-11-13 contract this module originally
# carried (the head seat under its native identity per the
# founder's 2026-11-25 specification); the next nine are named in
# the founder's Daedalus design records of 2026-10-23 and
# 2026-11-03; the last four are founder-directed additions of
# 2026-11-25, recorded as such in their entries below. No
# capability is declared here from any other source.
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
    "real_time_learning": (
        "founder-directed addition 2026-11-25 (\"He's got to have "
        "the ability to actually learn in real time\"); no learning "
        "capability is named in the 2026-11-13 contract or the "
        "2026-10-23 / 2026-11-03 design records"
    ),
    "labyrinth_shield_binding": (
        "founder-directed addition 2026-11-25 (\"the full Sanders "
        "labyrinth shield\"; the Shield is a full RTSA in its own "
        "right — founder affirmation, same day — and Daedalus is "
        "sheltered by it platform-to-platform, never absorbing it)"
    ),
    "minotaur_integrity_patrol": (
        "founder-directed addition 2026-11-25 (\"the RTSA minotaur "
        "patoling the labyrinth shield itself\"); the Minotaur is "
        "one RTSA (ruling D-N8) and its patrol of Daedalus and of "
        "the Shield is wired, not absorbed"
    ),
    "quantum_protection_protocols": (
        "founder-directed addition 2026-11-25 (\"tamper proof "
        "quantum encryption protection protocols\"); performed by "
        "the hash-based signature layer in "
        "core_platform/daedalus_protection.py — ML-KEM key exchange "
        "remains declared, not implemented, in that layer"
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
