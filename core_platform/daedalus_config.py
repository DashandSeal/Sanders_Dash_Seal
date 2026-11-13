"""Daedalus environment-based configuration (added 2026-11-13).

Single place where Daedalus reads process environment. No secret is ever
logged, returned by ``redacted_summary()``, or written to disk by this
module. A missing key or model is an honest configuration error, never a
silent fallback to a fake provider.

Environment variables (all optional unless a live call is attempted):

- ``ANTHROPIC_API_KEY`` — Claude key (required for live reasoning).
- ``DAEDALUS_CLAUDE_MODEL`` — Claude model id, supplied by the owner.
  No model id is hardcoded anywhere in Daedalus: model ids change and
  older ids are retired (the SDK itself warns when an id is deprecated).
- ``DAEDALUS_TRANSPORT_BACKEND`` — ``auto`` (default), ``sdk`` or
  ``stdlib``. ``auto`` prefers the official Anthropic SDK when it is
  installed and falls back to the zero-dependency stdlib transport.
- ``DAEDALUS_TIMEOUT_SECONDS`` — per-request timeout, default 45.
- ``DAEDALUS_MAX_TOKENS`` — default ``max_tokens`` per generation, 2048.
- ``OPENAI_API_KEY`` — OpenAI key for gpt-transcribe / Realtime.
- ``DAEDALUS_TRANSCRIBE_MODEL`` — default ``gpt-transcribe``.
  ``DAEDALUS_WHISPER_MODEL`` is still read for compatibility but
  ``whisper-1`` is rejected: deprecated, shuts down 26 Feb 2027
  (replacement ``gpt-transcribe``). ``gpt-4o-transcribe`` /
  ``gpt-4o-mini-transcribe`` are rejected the same way.
- ``DAEDALUS_TTS_MODEL`` — default ``gpt-realtime-2.1-mini`` (the
  Realtime-only TTS model; OpenAI's named replacement for the retired
  ``tts-1`` line). ``tts-1`` / ``tts-1-hd`` / ``gpt-4o-mini-tts`` are
  rejected: they shut down 6 Jan 2027 and have no ``/v1/audio/speech``
  replacement — TTS runs only on the Realtime API.
- ``OPENAI_REALTIME_MODEL`` — Realtime model id, default
  ``gpt-realtime-2.1-mini``. First-generation Realtime models
  (``gpt-realtime``, ``gpt-4o-realtime``, …) shut down 20 Jan 2027
  and are rejected. Confirm the current id at deploy time.
- ``ELEVENLABS_API_KEY`` — ElevenLabs key for TTS.
- ``DAEDALUS_ELEVENLABS_VOICE_ID`` — ElevenLabs voice id (no default:
  the owner picks a voice; inventing one would silently bill the
  wrong voice).
- ``DAEDALUS_ELEVENLABS_MODEL_ID`` — optional; omitted when unset so
  ElevenLabs applies its account default instead of a guessed model.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Literal, Mapping

__all__ = [
    "DaedalusSettings",
    "TransportBackend",
]

TransportBackend = Literal["auto", "sdk", "stdlib"]

_TRANSPORT_BACKENDS: frozenset[str] = frozenset({"auto", "sdk", "stdlib"})

DEFAULT_TIMEOUT_SECONDS = 45.0
DEFAULT_MAX_TOKENS = 2048
# gpt-transcribe replaces whisper-1 (shutdown 2027-02-26).
DEFAULT_WHISPER_MODEL = "gpt-transcribe"
# Realtime-only TTS model (OpenAI's replacement for tts-1, shutdown
# 2027-01-06). Confirm the current id at deploy time.
DEFAULT_TTS_MODEL = "gpt-realtime-2.1-mini"
DEFAULT_REALTIME_MODEL = "gpt-realtime-2.1-mini"
DEFAULT_TTS_VOICE = "alloy"

# OpenAI model ids that must never be configured (see openai_link).
_DEPRECATED_OPENAI_MODELS: frozenset[str] = frozenset({
    "whisper-1", "tts-1", "tts-1-hd", "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe", "gpt-4o-mini-tts", "gpt-4o-realtime",
    "gpt-4o-mini-realtime", "gpt-realtime", "gpt-realtime-mini",
})
_DEPRECATED_OPENAI_PREFIXES: tuple[str, ...] = (
    "whisper-1", "tts-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts", "gpt-4o-realtime", "gpt-4o-mini-realtime",
)


def _reject_deprecated_openai_model(model: str, field: str) -> None:
    candidate = (model or "").strip()
    if candidate in _DEPRECATED_OPENAI_MODELS or any(
        candidate.startswith(prefix) for prefix in _DEPRECATED_OPENAI_PREFIXES
    ):
        raise ValueError(
            f"{field}={candidate!r} is a deprecated OpenAI model; "
            "use gpt-transcribe for transcription and the Realtime API "
            "(gpt-realtime-2.1-mini) for TTS instead"
        )


def _float_from(source: Mapping[str, str], name: str, default: float) -> float:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive duration")
    return value


def _int_from(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw, 10)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class DaedalusSettings:
    """Validated Daedalus configuration, built from explicit args or env.

    Secrets are stored on the instance only so a transport can use them;
    ``redacted_summary()`` is the only safe way to describe an instance
    in logs or reports.
    """

    anthropic_api_key: str | None = None
    claude_model: str | None = None
    transport_backend: TransportBackend = "auto"
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_tokens: int = DEFAULT_MAX_TOKENS
    openai_api_key: str | None = None
    whisper_model: str = DEFAULT_WHISPER_MODEL
    tts_model: str = DEFAULT_TTS_MODEL
    realtime_model: str = DEFAULT_REALTIME_MODEL
    tts_voice: str = DEFAULT_TTS_VOICE
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model_id: str | None = None

    def __post_init__(self) -> None:
        if self.transport_backend not in _TRANSPORT_BACKENDS:
            raise ValueError(
                "transport_backend must be one of 'auto', 'sdk', 'stdlib'"
            )
        if (
            not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive duration")
        if type(self.max_tokens) is not int or self.max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        for field_name in ("whisper_model", "tts_model", "realtime_model", "tts_voice"):
            if not getattr(self, field_name) or not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        _reject_deprecated_openai_model(self.whisper_model, "whisper_model")
        _reject_deprecated_openai_model(self.tts_model, "tts_model")
        _reject_deprecated_openai_model(self.realtime_model, "realtime_model")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DaedalusSettings":
        """Build settings from the process environment (or a supplied mapping)."""
        source = os.environ if env is None else env
        backend = (source.get("DAEDALUS_TRANSPORT_BACKEND") or "auto").strip().lower()
        if backend not in _TRANSPORT_BACKENDS:
            raise ValueError(
                "DAEDALUS_TRANSPORT_BACKEND must be one of 'auto', 'sdk', 'stdlib'"
            )
        return cls(
            anthropic_api_key=source.get("ANTHROPIC_API_KEY") or None,
            claude_model=source.get("DAEDALUS_CLAUDE_MODEL") or None,
            transport_backend=backend,  # type: ignore[arg-type]
            timeout_seconds=_float_from(source, "DAEDALUS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
            max_tokens=_int_from(source, "DAEDALUS_MAX_TOKENS", DEFAULT_MAX_TOKENS),
            openai_api_key=source.get("OPENAI_API_KEY") or None,
            whisper_model=(source.get("DAEDALUS_TRANSCRIBE_MODEL")
                           or source.get("DAEDALUS_WHISPER_MODEL")
                           or DEFAULT_WHISPER_MODEL).strip(),
            tts_model=(source.get("DAEDALUS_TTS_MODEL") or DEFAULT_TTS_MODEL).strip(),
            realtime_model=(source.get("OPENAI_REALTIME_MODEL")
                            or source.get("DAEDALUS_TTS_MODEL")
                            or DEFAULT_REALTIME_MODEL).strip(),
            tts_voice=(source.get("DAEDALUS_TTS_VOICE") or DEFAULT_TTS_VOICE).strip(),
            elevenlabs_api_key=source.get("ELEVENLABS_API_KEY") or None,
            elevenlabs_voice_id=source.get("DAEDALUS_ELEVENLABS_VOICE_ID") or None,
            elevenlabs_model_id=source.get("DAEDALUS_ELEVENLABS_MODEL_ID") or None,
        )

    @property
    def is_live_reasoning_configured(self) -> bool:
        """True only when both a key and a model are present.

        Configured is not the same as working: no network call is made
        here, so a wrong key or a retired model still reports configured.
        """
        return bool(self.anthropic_api_key and self.claude_model)

    def require_live_reasoning(self) -> None:
        """Raise an honest error when a live Claude call cannot be made."""
        if not self.claude_model:
            raise ValueError("DAEDALUS_CLAUDE_MODEL must identify a real available model")
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for live reasoning")

    def redacted_summary(self) -> dict[str, object]:
        """Log-safe summary: presence of secrets, never their values."""
        return {
            "transport_backend": self.transport_backend,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "claude_model": self.claude_model or "",
            "anthropic_api_key_present": bool(self.anthropic_api_key),
            "openai_api_key_present": bool(self.openai_api_key),
            "elevenlabs_api_key_present": bool(self.elevenlabs_api_key),
            "whisper_model": self.whisper_model,
            "tts_model": self.tts_model,
            "realtime_model": self.realtime_model,
            "tts_voice": self.tts_voice,
            "elevenlabs_voice_id_present": bool(self.elevenlabs_voice_id),
            "elevenlabs_model_id_present": bool(self.elevenlabs_model_id),
        }
