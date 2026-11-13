"""DAEDALUS unified-by-design architecture contract.

All capabilities share one native engine context, policy plane, provenance
ledger and capability registry. External adapters remain implementation
boundaries, not independent product identities. No production claim implied.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping

from .daedalus_continuity import continuity_manifest
from .daedalus_global_trust import GlobalTrustEnforcer, GlobalTrustContext
from .daedalus_portfolio_ip_pricing import PortfolioProtection, proposed_rate_card


@dataclass(frozen=True)
class UnifiedEngineContext:
    operation_id: str
    platform_id: str
    subsystem_id: str
    invention_id: str
    generation: str
    trust: GlobalTrustContext

    def __post_init__(self) -> None:
        if not all((self.operation_id, self.platform_id, self.subsystem_id, self.invention_id)):
            raise ValueError("Unified DAEDALUS context requires full identity")
        if self.generation not in {"past", "present", "future"}:
            raise ValueError("Invalid cross-generational designation")


class UnifiedDaedalusEngine:
    """Single coordination plane for native DAEDALUS capabilities.

    The injected capability is an authorized engine function, not a separate
    product. Geographic policy is applied before execution and to egress;
    confidential invention evidence is persisted before returning source.
    """

    IDENTITY = "DAEDALUS"
    DESIGN = "unified_native_architecture_not_bolted_on"

    def __init__(
        self, *,
        global_trust: GlobalTrustEnforcer,
        portfolio_protection: PortfolioProtection,
        capability: Callable[[UnifiedEngineContext, str], bytes],
        audit: Callable[[Mapping[str, str]], None],
    ) -> None:
        if not callable(capability) or not callable(audit):
            raise TypeError("Native capability and audit interfaces required")
        self.global_trust = global_trust
        self.portfolio_protection = portfolio_protection
        self.capability = capability
        self.audit = audit

    def execute(
        self, context: UnifiedEngineContext, objective: str,
        *, title: str, inventor_assertions: tuple[str, ...],
    ) -> dict[str, str]:
        if not objective.strip():
            raise ValueError("Objective required")
        self.global_trust.enforce(action="ingress", context=context.trust)
        self.global_trust.enforce(action="execution", context=context.trust)
        self.audit({
            "engine": self.IDENTITY, "event": "NATIVE_OPERATION_STARTED",
            "operation_id": context.operation_id, "platform_id": context.platform_id,
        })
        source = self.capability(context, objective)
        if not isinstance(source, bytes) or not source:
            raise ValueError("Native capability returned no source")
        self.global_trust.enforce(action="storage", context=context.trust)
        asset = self.portfolio_protection.protect(
            asset_id=context.operation_id, platform_id=context.platform_id,
            subsystem_id=context.subsystem_id, generation=context.generation,
            invention_id=context.invention_id, title=title,
            inventor_assertions=inventor_assertions, source=source,
        )
        self.global_trust.enforce(action="egress", context=context.trust)
        self.audit({
            "engine": self.IDENTITY, "event": "NATIVE_OPERATION_COMPLETED",
            "operation_id": context.operation_id, "source_sha256": asset.source_sha256,
        })
        return {
            "engine": self.IDENTITY, "operation_id": context.operation_id,
            "invention_id": context.invention_id,
            "source_sha256": asset.source_sha256,
        }

    @classmethod
    def architecture(cls) -> dict:
        return {
            "engine": cls.IDENTITY,
            "design": cls.DESIGN,
            "continuity": continuity_manifest(),
            "commercial": proposed_rate_card(),
            "security": "global trust and protected provenance are native operation phases",
            "status": "integration_contract_not_production_deployment",
        }
