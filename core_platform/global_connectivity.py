"""Real-world connectivity policy for Sanders Dash & Seal (added 2026-11-13).

Per-region latency / timeout / retry / backoff policy for the real-time
platforms, with the offline / free-first fallback declared for each one.
Stdlib only. Fakes only: this module makes no network calls, holds no
keys, and performs no live call. It is a *policy table* plus a pure
backoff computation — the numbers below are policy, not measured
latency. No measured latency is claimed anywhere here.

Free-first / Always Free order (owner direction, Core Law 10/11):
Oracle Always Free (us-phoenix-1) is the deployment home first; local
free options (faster-whisper, system TTS, self-hosted LiveKit) are
tried before any paid provider call; a paid provider is only used when
its key is configured by the owner and the free path cannot serve the
request. This module declares the order — it does not perform the
fallback, because no live transport exists in this worktree snapshot
(``core_platform/openai_link.py`` and ``core_platform/realtime_api.py``
live on the link branches, not in snapshot 4342b230).

Timeouts below are per-attempt ceilings, not guarantees. Retries use
exponential backoff with a cap; the backoff function is pure and
deterministic (no jitter randomness) so tests can assert on it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

__all__ = [
    "PLATFORMS",
    "REGIONS",
    "RegionPolicy",
    "backoff_seconds",
    "fallback_for",
    "policy_for",
]

REGIONS: frozenset = frozenset({"us", "eu", "apac"})

# Primary deployment region is us-phoenix-1 (Oracle Always Free).
# "eu" / "apac" policies exist so a future region can be configured;
# no EU/APAC deployment exists today, so those policies are declared
# but unproven — see the compliance audit doc.
REGION_NOTES: Dict[str, str] = {
    "us": "Primary. Oracle Always Free us-phoenix-1. Only region with a deployed instance.",
    "eu": "Declared only. No EU region deployed; EEA data residency is NOT_IMPLEMENTED.",
    "apac": "Declared only. No APAC region deployed.",
}


@dataclass(frozen=True)
class RegionPolicy:
    platform: str
    region: str
    timeout_seconds: float
    max_retries: int
    backoff_base_seconds: float
    backoff_max_seconds: float
    offline_fallback: str
    notes: str = ""


def _policy(platform: str, region: str, timeout: float, retries: int,
            base: float, cap: float, fallback: str, notes: str = "") -> RegionPolicy:
    return RegionPolicy(
        platform=platform, region=region, timeout_seconds=timeout,
        max_retries=retries, backoff_base_seconds=base,
        backoff_max_seconds=cap, offline_fallback=fallback, notes=notes,
    )


# Per-platform defaults. Timeouts mirror the only in-repo precedent:
# Daedalus Claude transport defaults to 45 s per request
# (core_platform/daedalus_claude_transport.py). STT/TTS are shorter
# because a voice turn that takes minutes is unusable; realtime
# signalling uses a short ceiling with more retries.
PLATFORMS: Dict[str, Dict[str, RegionPolicy]] = {
    "daedalus": {
        "us": _policy("daedalus", "us", 45.0, 2, 1.0, 8.0,
                      "No offline fallback for reasoning. Fail honestly with a configuration error; do not fake an answer.",
                      "Anthropic Claude reasoning. Model id comes from env only; no model id is hardcoded."),
        "eu": _policy("daedalus", "eu", 45.0, 2, 1.0, 8.0,
                      "No offline fallback for reasoning. Fail honestly with a configuration error; do not fake an answer.",
                      "Declared only; no EU deployment."),
        "apac": _policy("daedalus", "apac", 60.0, 2, 1.0, 8.0,
                        "No offline fallback for reasoning. Fail honestly with a configuration error; do not fake an answer.",
                        "Declared only; no APAC deployment. Longer ceiling for expected cross-region latency."),
    },
    "openai": {
        "us": _policy("openai", "us", 30.0, 2, 1.0, 8.0,
                      "faster-whisper (local STT) first; system TTS first. OpenAI only when the owner configured a key.",
                      "Whisper transcription / TTS. whisper-1 and tts-1 are deprecated upstream — do not hardcode them as the future default."),
        "eu": _policy("openai", "eu", 30.0, 2, 1.0, 8.0,
                      "faster-whisper (local STT) first; system TTS first.",
                      "Declared only; no EU deployment."),
        "apac": _policy("openai", "apac", 45.0, 2, 1.0, 8.0,
                        "faster-whisper (local STT) first; system TTS first.",
                        "Declared only; no APAC deployment."),
    },
    "livekit": {
        "us": _policy("livekit", "us", 10.0, 3, 0.5, 4.0,
                      "Self-hosted LiveKit on Oracle Always Free first; cloud LiveKit only when the owner configured it.",
                      "Realtime audio/video rooms. Short ceiling, more retries: signalling must fail fast, not hang a room."),
        "eu": _policy("livekit", "eu", 10.0, 3, 0.5, 4.0,
                      "Self-hosted LiveKit on Oracle Always Free first.",
                      "Declared only; no EU deployment."),
        "apac": _policy("livekit", "apac", 15.0, 3, 0.5, 4.0,
                        "Self-hosted LiveKit on Oracle Always Free first.",
                        "Declared only; no APAC deployment."),
    },
    "deepgram": {
        "us": _policy("deepgram", "us", 30.0, 2, 1.0, 8.0,
                      "faster-whisper (local STT) first. Deepgram Nova-3 only when the owner configured a key.",
                      "Realtime/ batch STT alternative to Whisper."),
        "eu": _policy("deepgram", "eu", 30.0, 2, 1.0, 8.0,
                      "faster-whisper (local STT) first.",
                      "Declared only; no EU deployment."),
        "apac": _policy("deepgram", "apac", 45.0, 2, 1.0, 8.0,
                        "faster-whisper (local STT) first.",
                        "Declared only; no APAC deployment."),
    },
    "elevenlabs": {
        "us": _policy("elevenlabs", "us", 30.0, 2, 1.0, 8.0,
                      "System TTS first. ElevenLabs only when the owner configured a key and picked a voice id.",
                      "TTS. No voice id is hardcoded anywhere: the owner picks the voice."),
        "eu": _policy("elevenlabs", "eu", 30.0, 2, 1.0, 8.0,
                      "System TTS first.",
                      "Declared only; no EU deployment."),
        "apac": _policy("elevenlabs", "apac", 45.0, 2, 1.0, 8.0,
                        "System TTS first.",
                        "Declared only; no APAC deployment."),
    },
    "google": {
        "us": _policy("google", "us", 30.0, 2, 1.0, 8.0,
                      "System TTS / local STT first. Google TTS only when the owner configured it.",
                      "Google TTS (WaveNet). Only the legitimate Google uses named in the platform link branch."),
        "eu": _policy("google", "eu", 30.0, 2, 1.0, 8.0,
                      "System TTS / local STT first.",
                      "Declared only; no EU deployment."),
        "apac": _policy("google", "apac", 45.0, 2, 1.0, 8.0,
                        "System TTS / local STT first.",
                        "Declared only; no APAC deployment."),
    },
}


def policy_for(platform: str, region: str = "us") -> RegionPolicy:
    """Return the connectivity policy for ``platform`` in ``region``.

    Raises ``ValueError`` for an unknown platform or region — an
    unlisted platform has no timeout/retry policy and must not be
    called on an invented one.
    """
    if not isinstance(platform, str) or platform.strip().lower() not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform!r}. Known: {sorted(PLATFORMS)}")
    if not isinstance(region, str) or region.strip().lower() not in REGIONS:
        raise ValueError(f"Unknown region: {region!r}. Known: {sorted(REGIONS)}")
    return PLATFORMS[platform.strip().lower()][region.strip().lower()]


def fallback_for(platform: str, region: str = "us") -> str:
    """The declared offline / free-first fallback for a platform."""
    return policy_for(platform, region).offline_fallback


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 8.0) -> float:
    """Exponential backoff delay before retry number ``attempt``.

    ``attempt`` is 1-based (first retry waits ``base``). Pure and
    deterministic: ``min(base * 2 ** (attempt - 1), cap)``. Raises
    ``ValueError`` for ``attempt < 1`` or non-positive ``base``/``cap``.
    """
    if not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt must be a positive integer (1-based retry number)")
    if base <= 0 or cap <= 0:
        raise ValueError("base and cap must be positive")
    return min(base * (2 ** (attempt - 1)), cap)


def all_policies() -> List[RegionPolicy]:
    """Every declared policy, sorted by platform then region."""
    return [PLATFORMS[p][r] for p in sorted(PLATFORMS) for r in sorted(PLATFORMS[p])]
