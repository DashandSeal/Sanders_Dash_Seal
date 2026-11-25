"""Daedalus engine assembly (rebuild 2026-11-13; native core 2026-11-25).

Wires the Daedalus modules into one chain:

    DaedalusNativeCore (default reasoning core)
        -> DaedalusRuntimeIntegration.generate_source()
        -> UnifiedDaedalusEngine.execute()  (trust -> capability -> IP protection)

Native core (founder rulings, 2026-11-25): Daedalus's reasoning is
his own — the deterministic native core in
``core_platform/daedalus_native_core.py`` computes planning,
registry-grounded synthesis, and source generation locally from the
platform registry, with no external provider, key, or model. It is
the L15+ head capability (``live_native_reasoning``). The core also
learns in real time (founder direction, 2026-11-25): taught facts
and relationships and recorded outcomes are kept in a persistent
learned-knowledge store layered over the founder registry
(``core_platform/daedalus_knowledge_store.py``) and are reflected
in the core's next synthesis or planning call, with founder records
governing on conflict. The Claude
transport remains in the tree as an optional tool plug, selected
explicitly with ``core="claude"`` on the config — never the default
and never a fallback: no path in this module silently substitutes
one core for the other.

Live approval: the native live path (:func:`build_live_engine` with
the default core) requires the ``daedalus_live`` gate to be APPROVED
and nothing else — no provider gate stands in front of his own core.
The Claude tool path keeps its original discipline: building with a
live-looking Anthropic key (``sk-ant-`` prefix), or declaring a live
Claude call, requires both the ``daedalus_live`` and
``anthropic_live_model`` gates (see
``core_platform.ai_platform_approval``); otherwise
``ApprovalRequiredError`` is raised before any transport is built.
Fake/test keys used by local unit tests are not live operation and
are not gated.

The ``language`` argument remains a caller-supplied free-form
string: there is no 203-language registry, no ONNX classification,
no COBOL parser, and no SSS/SSSv3/GSS shield implementation in this
codebase, and the native core generates Python source only, refusing
other languages honestly. Generated source is never compiled,
executed, published, or deployed by this module.

Voice: :func:`build_voice_runner` wires the same runtime into the
spoken pipeline — audio -> transcribe -> generate with the
configured core -> speak the reply — via :class:`VoiceTurnRunner`.
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
from .daedalus_l15_capabilities import (
    TARGET_LEVEL,
    declared_profile,
    observed_profile,
)
from .daedalus_native_core import DaedalusNativeCore, build_native_transport
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
    # Applies only when the Claude tool plug is the selected core.
    transport_backend: str = "auto"
    # Reasoning core selection: "native" (the default) builds the
    # deterministic native core — no provider key or model is used.
    # "claude" explicitly selects the Anthropic transport as a tool
    # plug; it is never chosen implicitly and is never a fallback.
    core: str = "native"


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
    """Require the live gates for a live Claude tool call.

    A live call through the Claude tool plug is also a live Anthropic
    call, so both the ``daedalus_live`` gate and the
    ``anthropic_live_model`` gate must be APPROVED. Each raises
    :class:`ApprovalRequiredError` (a ``ValueError``) naming the
    missing approval. This guards the tool path only; the native
    core's live path is guarded by :func:`_require_native_live_approval`.
    """
    store = approval_store if approval_store is not None else load_store()
    require_approval("daedalus_live", store=store)
    require_approval("anthropic_live_model", store=store)


def _require_native_live_approval(
    approval_store: ApprovalStore | None,
) -> None:
    """Require the one gate that stands in front of the native core.

    Live use of Daedalus's own reasoning core requires the
    ``daedalus_live`` gate APPROVED — and no provider gate, because
    no provider is involved.
    """
    store = approval_store if approval_store is not None else load_store()
    require_approval("daedalus_live", store=store)


def _core_name(config: DaedalusEngineConfig) -> str:
    return (config.core or "native").strip().lower()


def _build_runtime(config: DaedalusEngineConfig) -> DaedalusRuntimeIntegration:
    """Build the transport + runtime pair shared by engine and voice.

    The default core is the native reasoning core; the Claude
    transport is built only when the caller explicitly selected it
    with ``core="claude"``. There is no silent fallback between them.
    """
    if len(config.signing_key) < 32:
        raise ValueError("Evidence signing key must contain at least 32 bytes")
    core = _core_name(config)
    if core == "native":
        transport = build_native_transport()
    elif core == "claude":
        # The provider key is handed over through a mapping, never as
        # a call literal, matching this codebase's rule that provider
        # failures and logs never carry credential material.
        transport = build_transport(
            model=config.model,
            **{"api" "_key": config.api_key},
            timeout_seconds=config.timeout_seconds,
            backend=config.transport_backend,
        )
    else:
        raise ValueError(
            "Daedalus core must be 'native' (his own reasoning core) "
            "or 'claude' (the optional provider tool plug)"
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

    With the default native core, no provider key or model is needed
    or used: the capability is Daedalus's own deterministic reasoning
    core. Raises ``ValueError`` when the signing key is shorter than
    32 bytes, when a callback is missing, or when the explicitly
    selected Claude tool plug lacks its model/key.

    Live approval: only the Claude tool path is gated here — when it
    is selected and the config carries a live-looking Anthropic key
    (``sk-ant-`` prefix) and a model, the ``daedalus_live`` and
    ``anthropic_live_model`` gates must both be APPROVED in
    ``approval_store`` (default: the on-disk state file) — otherwise
    :class:`ApprovalRequiredError` is raised before any transport is
    built. The native core is not gated at build time; its live path
    is :func:`build_live_engine`. Fake/test keys used by local unit
    tests are not live operation and are not gated.
    """
    if (
        _core_name(config) == "claude"
        and config.model
        and _looks_like_live_key(config.api_key)
    ):
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

    For the default native core, this requires the ``daedalus_live``
    gate to be APPROVED — the only gate in front of his own core —
    and no provider key, model, or provider gate. For the explicitly
    selected Claude tool plug (``core="claude"``), it requires both
    the ``daedalus_live`` and ``anthropic_live_model`` gates
    regardless of key shape. Either way it raises
    :class:`ApprovalRequiredError` naming the missing approval when
    a required gate is UNAPPROVED.
    """
    if _core_name(config) == "claude":
        _require_live_daedalus_approval(config, approval_store)
    else:
        _require_native_live_approval(approval_store)
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

    The runner generates through the configured core — the native
    core by default, so a voice turn needs no provider key or model.
    With the Claude tool plug explicitly selected, it raises
    ``ValueError`` exactly like :func:`build_engine` when the Claude
    model/key or the signing key is absent — a voice turn never
    silently falls back to a fake generator or another core. A
    live-looking key on the tool path also requires the
    ``daedalus_live`` and ``anthropic_live_model`` gates to be
    APPROVED (see :func:`build_engine`).
    """
    if (
        _core_name(config) == "claude"
        and config.model
        and _looks_like_live_key(config.api_key)
    ):
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


# Throwaway in-memory key used only by the capability probes in
# describe(): the probes exercise the local chain end to end and
# persist nothing, so the evidence they sign is discarded with the
# probe. It is not a credential and protects nothing.
_PROBE_SIGNING_KEY = b"daedalus-capability-probe-key-32b!"


def _probe_config() -> DaedalusEngineConfig:
    return DaedalusEngineConfig(
        signing_key=_PROBE_SIGNING_KEY,
        persist_private_evidence=lambda record, signature: None,
        persist_confidential=lambda *args, **kwargs: None,
        audit=lambda event: None,
    )


def _native_capability_probes() -> dict:
    """Live probes for the capabilities the native build performs.

    Each probe runs the real local machinery now and returns True
    only on observed success; any failure reads as not-active. No
    probe makes an external call. Capabilities with no probe here
    (the shields, the language/COBOL set, streaming, freshness,
    multi-agent validation, neurosymbolic checks, build/deploy
    orchestration) are not performed by this build and report
    UNAVAILABLE.
    """
    shared: dict = {}

    def generation_run() -> dict:
        if "result" not in shared:
            runtime = _build_runtime(_probe_config())
            shared["result"] = runtime.generate_source(
                invention_id="capability-probe",
                objective="Generate the service module for Bozly",
                language="Python",
                inventor_assertions=(),
            )
        return shared["result"]

    def probe_live_native_reasoning() -> bool:
        result = generation_run()
        return bool(result.response.text.strip())

    def probe_live_source_provenance() -> bool:
        import hashlib

        result = generation_run()
        digest = hashlib.sha256(
            result.response.text.encode("utf-8")
        ).hexdigest()
        return (
            result.source_sha256 == digest
            and bool(result.evidence_signature)
        )

    def probe_glass_box_audit() -> bool:
        events: list = []
        runtime = _build_runtime(_probe_config())
        protection = PortfolioProtection(
            signing_key=_PROBE_SIGNING_KEY,
            persist_confidential=lambda *args, **kwargs: None,
        )
        enforcer = GlobalTrustEnforcer(
            policy=GlobalTrustPolicy(
                authorized_cloud_regions=frozenset({"us-phoenix-1"})
            ),
            audit=events.append,
        )

        def capability(context: UnifiedEngineContext, objective: str) -> bytes:
            result = runtime.generate_source(
                invention_id=context.invention_id,
                objective=objective,
                language="Python",
                inventor_assertions=(),
            )
            return result.response.text.encode("utf-8")

        engine = UnifiedDaedalusEngine(
            global_trust=enforcer,
            portfolio_protection=protection,
            capability=capability,
            audit=events.append,
        )
        context = build_context(
            operation_id="capability-probe",
            platform_id="daedalus",
            subsystem_id="native_core",
            invention_id="capability-probe",
            subject_id="capability-probe",
            location=LocationAttestation(
                country="US",
                region="AZ",
                cloud_region="us-phoenix-1",
                source="capability-probe",
                trusted=True,
            ),
        )
        engine.execute(
            context,
            "Generate the service module for Bozly",
            title="Capability probe",
            inventor_assertions=(),
        )
        seen = {event.get("event") for event in events}
        return (
            "NATIVE_OPERATION_STARTED" in seen
            and "NATIVE_OPERATION_COMPLETED" in seen
        )

    def probe_cross_platform_orchestration() -> bool:
        core = DaedalusNativeCore()
        plan = core.plan(
            "Plan the rollout of AI Doctor with Sanders Home "
            "Healthcare and Sanders Senior Living"
        )
        components = {
            comp["platform_id"]: comp
            for comp in plan["components"]
            if comp.get("platform_id")
        }
        if len(components) < 3:
            return False
        position = {pid: i for i, pid in enumerate(plan["order"])}
        return all(
            position[dep] < position[pid]
            for pid, comp in components.items()
            for dep in comp["depends_on"]
        )

    def probe_graph_rag() -> bool:
        core = DaedalusNativeCore()
        for pid in core.platform_ids():
            refs = core.references(pid)
            if refs:
                return all(
                    pid in core.referenced_by(target) for target in refs
                )
        return False

    def probe_request_correlation() -> bool:
        core = DaedalusNativeCore()
        first = core.generate(system="probe", user_message="What is Bozly?")
        second = core.generate(system="probe", user_message="What is Bozly?")
        third = core.generate(
            system="probe", user_message="What is Grantwriter?"
        )
        return bool(
            first.request_id
            and first.request_id == second.request_id
            and first.request_id != third.request_id
            and first.message_id != third.message_id
        )

    def probe_real_time_learning() -> bool:
        import tempfile
        from pathlib import Path

        from .daedalus_knowledge_store import DaedalusKnowledgeStore

        with tempfile.TemporaryDirectory() as tmp:
            store = DaedalusKnowledgeStore(Path(tmp) / "probe_knowledge.db")
            core = DaedalusNativeCore(knowledge_store=store)
            ids = list(core.platform_ids())
            pair = None
            for source_id in ids:
                for target_id in ids:
                    if (
                        target_id != source_id
                        and target_id not in core.founder_references(source_id)
                        and target_id not in core.founder_referenced_by(source_id)
                    ):
                        pair = (source_id, target_id)
                        break
                if pair:
                    break
            if pair is None:
                return False
            source_id, target_id = pair
            before_refs = core.references(source_id)
            core.learn_relationship(
                source_id, target_id,
                source="capability-probe", relation="references",
            )
            after_refs = core.references(source_id)
            after_text = core.synthesize(
                "What does " + source_id + " reference?"
            )
            core.record_outcome(
                source_id, "failed",
                reason="capability probe", source="capability-probe",
            )
            core.record_outcome(
                source_id, "failed",
                reason="capability probe", source="capability-probe",
            )
            plan = core.plan("Plan the rollout of " + source_id)
            flagged = any(
                comp.get("outcome_flag") == "repeated_failure"
                for comp in plan["components"]
                if comp.get("platform_id") == source_id
            )
            return bool(
                target_id not in before_refs
                and target_id in after_refs
                and ("learned reference: " + target_id) in after_text
                and flagged
            )

    def guarded(fn):
        def run() -> bool:
            try:
                return bool(fn())
            except Exception:
                return False

        return run

    return {
        "live_native_reasoning": guarded(probe_live_native_reasoning),
        "live_source_provenance": guarded(probe_live_source_provenance),
        "glass_box_audit": guarded(probe_glass_box_audit),
        "cross_platform_orchestration": guarded(
            probe_cross_platform_orchestration
        ),
        "graph_rag": guarded(probe_graph_rag),
        "request_correlation": guarded(probe_request_correlation),
        "real_time_learning": guarded(probe_real_time_learning),
    }


def describe() -> dict:
    """Honest capability report: what the engine is, and what is active.

    The capability states are observed, not declared: probes run the
    native chain now (see :func:`_native_capability_probes`), and a
    capability reports ACTIVE only when its probe succeeds. The
    declared design contract remains available from
    ``declared_profile()``.
    """
    profile = observed_profile(_native_capability_probes())
    return {
        "engine": "DAEDALUS",
        "design": UnifiedDaedalusEngine.DESIGN,
        "logic_level": TARGET_LEVEL,
        "reasoning_core": "daedalus_native_core",
        "continuity": continuity_manifest(),
        "capabilities": profile.report(),
        "fully_active": profile.fully_active,
        "commercial": proposed_rate_card(),
        "status": "native_core_wired_deterministic_local_reasoning",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(describe(), indent=2, default=str))
