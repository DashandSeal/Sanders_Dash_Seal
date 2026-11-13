"""Daedalus engine assembly (rebuild 2026-11-13).

Wires the existing Daedalus modules into one chain:

    DaedalusClaudeTransport
        -> DaedalusRuntimeIntegration.generate_source()
        -> UnifiedDaedalusEngine.execute()  (trust -> capability -> IP protection)

No capability is fabricated here. ``declared_profile()`` still reports all
13 declared capabilities UNAVAILABLE, and live Claude reasoning requires
``ANTHROPIC_API_KEY`` and ``DAEDALUS_CLAUDE_MODEL`` supplied by the caller
(environment or arguments) — without them ``build_engine`` raises
``ValueError`` instead of pretending to work. The ``language`` argument is
a caller-supplied free-form string: there is no 203-language registry,
no ONNX classification, no COBOL parser, and no SSS/SSSv3/GSS shield
implementation in this codebase. Generated source is never compiled,
executed, published, or deployed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, FrozenSet, Mapping

from .daedalus_claude_transport import DaedalusClaudeTransport
from .daedalus_continuity import continuity_manifest
from .daedalus_geofence import LocationAttestation
from .daedalus_global_trust import (
    GlobalTrustContext,
    GlobalTrustEnforcer,
    GlobalTrustPolicy,
)
from .daedalus_ip_protection import InventionRecord
from .daedalus_l15_capabilities import declared_profile
from .daedalus_portfolio_ip_pricing import PortfolioProtection, proposed_rate_card
from .daedalus_runtime_integration import DaedalusRuntimeIntegration
from .daedalus_unified_engine import UnifiedDaedalusEngine, UnifiedEngineContext


@dataclass(frozen=True)
class DaedalusEngineConfig:
    """Caller-supplied wiring for one Daedalus engine instance."""

    signing_key: bytes
    persist_private_evidence: Callable[[InventionRecord, str], None]
    persist_confidential: Callable[..., None]
    audit: Callable[[Mapping[str, str]], None]
    model: str | None = None
    api_key: str | None = None
    language: str = "Python"
    authorized_cloud_regions: FrozenSet[str] = frozenset({"us-phoenix-1"})
    timeout_seconds: float = 60.0


def build_engine(config: DaedalusEngineConfig) -> UnifiedDaedalusEngine:
    """Assemble the full Daedalus chain from caller-supplied adapters.

    Raises ``ValueError`` when the Claude model/key are absent, when the
    signing key is shorter than 32 bytes, or when any callback is missing.
    """
    if len(config.signing_key) < 32:
        raise ValueError("Evidence signing key must contain at least 32 bytes")
    transport = DaedalusClaudeTransport(
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )
    runtime = DaedalusRuntimeIntegration(
        transport=transport,
        signing_key=config.signing_key,
        persist_private_evidence=config.persist_private_evidence,
    )
    protection = PortfolioProtection(
        signing_key=config.signing_key,
        persist_confidential=config.persist_confidential,
    )
    enforcer = GlobalTrustEnforcer(
        policy=GlobalTrustPolicy(
            authorized_cloud_regions=config.authorized_cloud_regions
        ),
        audit=config.audit,
    )

    def capability(context: UnifiedEngineContext, objective: str) -> bytes:
        result = runtime.generate_source(
            invention_id=context.invention_id,
            objective=objective,
            language=config.language,
            inventor_assertions=(),
        )
        return result.response.text.encode("utf-8")

    return UnifiedDaedalusEngine(
        global_trust=enforcer,
        portfolio_protection=protection,
        capability=capability,
        audit=config.audit,
    )


def build_context(
    *,
    operation_id: str,
    platform_id: str,
    subsystem_id: str,
    invention_id: str,
    generation: str = "present",
    subject_id: str,
    location: LocationAttestation,
    data_classification: str = "restricted",
    processing_country: str = "US",
    processing_cloud_region: str = "us-phoenix-1",
) -> UnifiedEngineContext:
    """Build an execution context with a verified-identity trust context.

    The caller must supply a real ``LocationAttestation`` from a trusted
    source; this module performs no geolocation or identity verification.
    """
    trust = GlobalTrustContext(
        subject_id=subject_id,
        identity_verified=True,
        authorization_granted=True,
        location=location,
        data_classification=data_classification,
        processing_country=processing_country,
        processing_cloud_region=processing_cloud_region,
        residency_permitted=True,
    )
    return UnifiedEngineContext(
        operation_id=operation_id,
        platform_id=platform_id,
        subsystem_id=subsystem_id,
        invention_id=invention_id,
        generation=generation,
        trust=trust,
    )


def describe() -> dict:
    """Honest capability report: what the engine is, and what is active."""
    profile = declared_profile()
    return {
        "engine": "DAEDALUS",
        "design": UnifiedDaedalusEngine.DESIGN,
        "continuity": continuity_manifest(),
        "capabilities": profile.report(),
        "fully_active": profile.fully_active,
        "commercial": proposed_rate_card(),
        "status": "rebuild_20261113_integration_contract_not_production_deployment",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(describe(), indent=2, default=str))
