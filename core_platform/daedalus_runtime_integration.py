"""Daedalus integration facade for the existing Sanders runtime.

Imports existing Daedalus modules; does not replace production entrypoints.
The caller supplies actual runtime adapters and secure evidence storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .daedalus_claude_transport import DaedalusClaudeTransport, DaedalusResponse
from .daedalus_continuity import continuity_manifest
from .daedalus_l15_capabilities import declared_profile
from .daedalus_ip_protection import InventionRecord, sign_evidence


@dataclass(frozen=True)
class DaedalusBuildResult:
    response: DaedalusResponse
    source_sha256: str
    invention_id: str
    evidence_signature: str


class DaedalusRuntimeIntegration:
    """Connect live reasoning, continuity, and private provenance capture.

    This facade generates source text but never compiles, executes, publishes,
    or deploys generated content. Its storage callback must be configured
    with a confidential, durable backend by the owning runtime.
    """

    def __init__(
        self,
        *,
        transport: DaedalusClaudeTransport,
        signing_key: bytes,
        persist_private_evidence: Callable[[InventionRecord, str], None],
        allowed_languages: frozenset[str] = frozenset({"Python"}),
    ) -> None:
        if not isinstance(transport, DaedalusClaudeTransport):
            raise TypeError("A live Daedalus Claude transport is required")
        if not callable(persist_private_evidence):
            raise TypeError("Private evidence persistence callback required")
        if len(signing_key) < 32:
            raise ValueError("Evidence signing key must contain at least 32 bytes")
        self.transport = transport
        self.signing_key = signing_key
        self.persist_private_evidence = persist_private_evidence
        self.allowed_languages = allowed_languages

    @staticmethod
    def architecture() -> dict:
        return {
            "identity": "DAEDALUS",
            "priority": "P0",
            "capabilities": declared_profile().report(),
            "continuity": continuity_manifest(),
        }

    def generate_source(
        self,
        *,
        invention_id: str,
        objective: str,
        language: str,
        inventor_assertions: tuple[str, ...],
    ) -> DaedalusBuildResult:
        if not invention_id or not objective.strip() or not language.strip():
            raise ValueError("Invention identity, objective and language are required")
        if language not in self.allowed_languages:
            raise ValueError(
                f"Language {language!r} is not in the configured allowlist "
                "(no 203-language registry exists)")
        system = (
            "You are DAEDALUS, the existing Sanders real-time synthetic AI. "
            "Produce source code in the requested language. Preserve "
            "cross-generational compatibility and existing intellectual property. "
            "Do not invent compiler execution, deployment, connectivity, or "
            "validation outcomes. Return source text only."
        )
        response = self.transport.generate(
            system=system,
            user_message=f"Language: {language}\nObjective:\n{objective}",
            metadata={"component": "DAEDALUS", "invention_id": invention_id},
        )
        if not response.text.strip():
            raise ValueError("The live provider returned no source")
        record = InventionRecord.from_source(
            invention_id=invention_id,
            title=f"Daedalus {language} source generation",
            inventor_assertions=inventor_assertions,
            source=response.text.encode("utf-8"),
        )
        signature = sign_evidence(record, self.signing_key)
        # Persist confidential evidence before returning source to the caller.
        self.persist_private_evidence(record, signature)
        return DaedalusBuildResult(
            response=response,
            source_sha256=record.source_sha256,
            invention_id=invention_id,
            evidence_signature=signature,
        )
