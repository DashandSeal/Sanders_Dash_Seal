"""Cross-generational continuity registry for existing Daedalus integrations.

Declares preservation-oriented bridges; does not claim that adapters have
been connected to a production engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "CANONICAL_BRIDGES",
    "CONTINUITY_PRINCIPLE",
    "Bridge",
    "Generation",
    "bridge_by_source",
    "continuity_manifest",
]


CONTINUITY_PRINCIPLE = (
    "Preserve, interpret, integrate, and advance computing technologies "
    "across generations without discarding legacy knowledge."
)


class Generation(str, Enum):
    LEGACY = "legacy"
    CURRENT = "current"
    FUTURE = "future"


@dataclass(frozen=True)
class Bridge:
    source: str
    destination: str
    source_generation: Generation
    destination_generation: Generation
    source_adapter: str
    destination_adapter: str
    preserves_source: bool = True

    def __post_init__(self) -> None:
        if not all((self.source, self.destination, self.source_adapter, self.destination_adapter)):
            raise ValueError("A bridge requires explicit endpoints and adapters")
        if not self.preserves_source:
            raise ValueError("Daedalus continuity requires preservation")


CANONICAL_BRIDGES = (
    Bridge("COBOL", "Polyglot Engine LLVM", Generation.LEGACY, Generation.CURRENT,
           "COBOL BRIDGE", "Polyglot Engine LLVM"),
    Bridge("ANSI X12", "FHIR R4", Generation.LEGACY, Generation.CURRENT,
           "COBOL BRIDGE", "FHIR adapter"),
    Bridge("Polyglot Engine LLVM", "Future Language Adapter",
           Generation.CURRENT, Generation.FUTURE,
           "Polyglot Engine LLVM", "Future Language Adapter"),
)


def bridge_by_source(source: str) -> Bridge | None:
    """Return the canonical continuity bridge for a source technology, if any."""
    for bridge in CANONICAL_BRIDGES:
        if bridge.source == source:
            return bridge
    return None


def continuity_manifest() -> dict:
    return {
        "identity": "DAEDALUS",
        "priority": "P0",
        "level_target": "L15+",
        "principle": CONTINUITY_PRINCIPLE,
        "bridges": [
            {
                "source": bridge.source,
                "destination": bridge.destination,
                "source_generation": bridge.source_generation.value,
                "destination_generation": bridge.destination_generation.value,
                "source_adapter": bridge.source_adapter,
                "destination_adapter": bridge.destination_adapter,
                "preserves_source": bridge.preserves_source,
                "status": "declared_not_connected",
            }
            for bridge in CANONICAL_BRIDGES
        ],
    }
