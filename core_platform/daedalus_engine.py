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

Voice (added 2026-11-13): :func:`build_voice_runner` wires the same
runtime into the spoken pipeline — audio -> transcribe -> generate
source with the live runtime -> speak the reply — via
:class:`VoiceTurnRunner`. The transport backend is chosen by
``DaedalusEngineConfig.transport_backend`` (``auto`` prefers the
official Anthropic SDK when installed, else the stdlib client).

Live approval (added 2026-11-13): building an engine with a
live-looking Anthropic key (``sk-ant-`` prefix) requires the
``daedalus_live`` and ``anthropic_live_model`` approval gates to be
APPROVED (see ``core_platform.ai_platform_approval``); otherwise
``build_engine``/``build_voice_runner`` raise ``ApprovalRequiredError``
before any transport is built. :func:`build_live_engine` requires
those gates regardless of key shape. Fake/test keys used by local
unit tests are not live operation and are not gated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, FrozenSet, Mapping

from .ai_platform_approval import (
    ApprovalStore,
    load_store,
    require_approval,
)
from .daedalus_claude_transport import build_transport
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
from .daedalus_voice_pipeline import (
    Speaker,
    Transcriber,
    VoiceTurn,
    run_voice_turn,
)

__all__ = [
    "DaedalusEngineConfig",
    "VoiceTurnRunner",
    "build_context",
    "build_engine",
    "build_live_engine",
    "build_voice_runner",
    "describe",
]

logger = logging.getLogger("daedalus.engine")


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
    # "auto" prefers the official Anthropic SDK when installed, else the
    # stdlib client; "sdk" requires the SDK; "stdlib" forces stdlib.
    transport_backend: str = "auto"


def _looks_like_live_key(api_key: str | None) -> bool:
    """True when the key looks like a real Anthropic live key.

    Live Anthropic keys start with ``sk-ant-``. Fake/test keys used by
    local unit tests (e.g. ``"test-key-not-real"``) never touch the
    network, so they are not live operation and are not gated here.
    """
    return isinstance(api_key, str) and api_key.startswith("sk-ant-")


def _require_live_daedalus_approval(
    config: DaedalusEngineConfig,
    approval_store: ApprovalStore | None,
) -> None:
    """Require the live gates for a real Daedalus call.

    A live Daedalus call is also a live Anthropic call, so both the
    ``daedalus_live`` gate and the ``anthropic_live_model`` gate must
    be APPROVED. Each raises :class:`ApprovalRequiredError` (a
    ``ValueError``) naming the missing approval.
    """
    store = approval_store if approval_store is not None else load_store()
    require_approval("daedalus_live", store=store)
    require_approval("anthropic_live_model", store=store)


def _build_runtime(config: DaedalusEngineConfig) -> DaedalusRuntimeIntegration:
    """Build the transport + runtime pair shared by engine and voice."""
    if len(config.signing_key) < 32:
        raise ValueError("Evidence signing key must contain at least 32 bytes")
    transport = build_transport(
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
        backend=config.transport_backend,
    )
    return DaedalusRuntimeIntegration(
        transport=transport,
        signing_key=config.signing_key,
        persist_private_evidence=config.persist_private_evidence,
    )


def build_engine(
    config: DaedalusEngineConfig,
    *,
    approval_store: ApprovalStore | None = None,
) -> UnifiedDaedalusEngine:
    """Assemble the full Daedalus chain from caller-supplied adapters.

    Raises ``ValueError`` when the Claude model/key are absent, when the
    signing key is shorter than 32 bytes, or when any callback is missing.

    Live approval: when the config carries a live-looking Anthropic key
    (``sk-ant-`` prefix) and a model, the ``daedalus_live`` and
    ``anthropic_live_model`` gates must both be APPROVED in
    ``approval_store`` (default: the on-disk state file) — otherwise
    :class:`ApprovalRequiredError` is raised before any transport is
    built. Fake/test keys used by local unit tests are not live
    operation and are not gated.
    """
    if config.model and _looks_like_live_key(config.api_key):
        _require_live_daedalus_approval(config, approval_store)
    runtime = _build_runtime(config)
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


def build_live_engine(
    config: DaedalusEngineConfig,
    *,
    approval_store: ApprovalStore | None = None,
) -> UnifiedDaedalusEngine:
    """Build a Daedalus engine explicitly declared as a live call.

    Unlike :func:`build_engine` — which gates only when the key looks
    live — this entry point requires the ``daedalus_live`` and
    ``anthropic_live_model`` gates to be APPROVED regardless of key
    shape. Callers that intend a real provider call use this; it
    raises :class:`ApprovalRequiredError` naming the missing approval
    when either gate is UNAPPROVED.
    """
    _require_live_daedalus_approval(config, approval_store)
    return build_engine(config, approval_store=approval_store)


class VoiceTurnRunner:
    """Spoken Daedalus turn driven by the live runtime.

    Wires :func:`daedalus_voice_pipeline.run_voice_turn` to a
    :class:`DaedalusRuntimeIntegration`: the transcript becomes the
    generation objective, and the generated source text is spoken back.
    This uses the runtime (which returns the full response text) rather
    than :meth:`UnifiedDaedalusEngine.execute`, which returns only a
    source hash and therefore has no reply text to speak.
    """

    def __init__(
        self,
        *,
        runtime: DaedalusRuntimeIntegration,
        transcriber: Transcriber,
        speaker: Speaker,
        language: str = "Python",
    ) -> None:
        if not language.strip():
            raise ValueError("Voice turn language must not be empty")
        self.runtime = runtime
        self.transcriber = transcriber
        self.speaker = speaker
        self.language = language

    def run(
        self,
        audio: bytes,
        *,
        invention_id: str,
        inventor_assertions: tuple[str, ...] = (),
        language: str | None = None,
        filename: str = "audio.webm",
        mime_type: str | None = None,
    ) -> VoiceTurn:
        """Run one spoken turn and return transcript, reply, and audio."""
        if not invention_id:
            raise ValueError("Invention identity is required")
        chosen_language = language or self.language

        def generate_text(prompt: str) -> str:
            result = self.runtime.generate_source(
                invention_id=invention_id,
                objective=prompt,
                language=chosen_language,
                inventor_assertions=inventor_assertions,
            )
            return result.response.text

        turn = run_voice_turn(
            audio=audio,
            transcriber=self.transcriber,
            generator=generate_text,
            speaker=self.speaker,
            filename=filename,
            mime_type=mime_type,
        )
        logger.debug(
            "daedalus voice turn invention_id=%s latency_ms=%d",
            invention_id, turn.latency_ms,
        )
        return turn


def build_voice_runner(
    config: DaedalusEngineConfig,
    *,
    transcriber: Transcriber,
    speaker: Speaker,
    approval_store: ApprovalStore | None = None,
) -> VoiceTurnRunner:
    """Build a :class:`VoiceTurnRunner` from engine config + voice adapters.

    Raises ``ValueError`` exactly like :func:`build_engine` when the
    Claude model/key or the signing key is absent — a voice turn never
    silently falls back to a fake generator. A live-looking key also
    requires the ``daedalus_live`` and ``anthropic_live_model`` gates
    to be APPROVED (see :func:`build_engine`).
    """
    if config.model and _looks_like_live_key(config.api_key):
        _require_live_daedalus_approval(config, approval_store)
    return VoiceTurnRunner(
        runtime=_build_runtime(config),
        transcriber=transcriber,
        speaker=speaker,
        language=config.language,
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
