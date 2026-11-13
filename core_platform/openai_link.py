"""OpenAI linking layer for Daedalus voice (added 2026-11-13, Phase 2).

What this module is
--------------------
The stdlib (zero-dependency) OpenAI adapters that the rest of Daedalus
voice uses:

* :class:`OpenAIGPTTranscribeTranscriber` — batch transcription over
  ``POST /v1/audio/transcriptions`` with model ``gpt-transcribe``.
* :func:`create_realtime_session` / :class:`OpenAIRealtimeSession` —
  ``POST /v1/realtime/sessions``, which mints the short-lived ephemeral
  key a Realtime client speaks with. No audio flows over this call.
* :class:`OpenAIRealtimeTTSSpeaker` — text-to-speech **through the
  Realtime API only** (WebSocket ``wss://api.openai.com/v1/realtime``),
  using the current Realtime model. It never calls ``/v1/audio/speech``.

Deprecation handling (verified 2026-11-13 against OpenAI's deprecations
page; re-check before budgeting or shipping)
------------------------------------------------------------------------
* ``whisper-1`` — deprecated, **shuts down 26 Feb 2027**; replacement
  ``gpt-transcribe`` (batch, $0.0045/min) or ``gpt-live-transcribe``.
  ``gpt-4o-transcribe`` / ``gpt-4o-mini-transcribe`` shut down the same day.
* ``tts-1`` / ``tts-1-hd`` / ``gpt-4o-mini-tts`` — deprecated, **shut
  down 6 Jan 2027**; replacement ``gpt-realtime-2.1-mini``. The
  replacement does **not** run on ``/v1/audio/speech`` — it runs only on
  the Realtime API, so there is no drop-in model swap. This module
  therefore rejects ``tts-1``/``tts-1-hd`` outright (see
  :func:`reject_deprecated_openai_model`) and the old
  ``daedalus_voice_pipeline.OpenAITTSSpeaker`` (``/audio/speech``) now
  refuses to construct and points at :class:`OpenAIRealtimeTTSSpeaker`.
* First-generation Realtime models (``gpt-realtime``,
  ``gpt-4o-realtime``, ``gpt-realtime-mini``, ``gpt-4o-mini-realtime``
  and their dated snapshots) shut down **20 Jan 2027**; replacements
  ``gpt-realtime-2.1`` / ``gpt-realtime-2.1-mini``. The default Realtime
  model here is ``gpt-realtime-2.1-mini``; the owner must confirm the
  current model id at deploy time — model ids are not stable.

Honesty rules
-------------
* No key → ``ValueError`` naming the missing variable. No ``websockets``
  package → ``ImportError`` for the Realtime speaker (the stdlib has no
  WebSocket client). No live call is made in this module's tests: the
  HTTP ``opener`` and the WebSocket factory are injectable, and tests
  use fakes plus a local 127.0.0.1 server.
* Provider failures raise :class:`DaedalusProviderError` with the HTTP
  status only — never the upstream body, never a key.
* The ephemeral Realtime key (``client_secret.value``) is stored on the
  session object only so the speaker can use it; it is never logged and
  ``redacted_summary()``-style output must not include it.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .daedalus_claude_transport import DaedalusProviderError

__all__ = [
    "DEFAULT_REALTIME_MODEL",
    "DEFAULT_REALTIME_TTS_MODEL",
    "DEPRECATED_OPENAI_MODELS",
    "GPT_LIVE_TRANSCRIBE_MODEL",
    "GPT_TRANSCRIBE_MODEL",
    "OpenAIGPTTranscribeTranscriber",
    "OpenAIRealtimeSession",
    "OpenAIRealtimeTTSSpeaker",
    "RealtimeSpeechAudio",
    "build_gpt_transcribe_from_env",
    "build_realtime_speaker_from_env",
    "create_realtime_session",
    "reject_deprecated_openai_model",
]

logger = logging.getLogger("daedalus.openai")

GPT_TRANSCRIBE_MODEL = "gpt-transcribe"
GPT_LIVE_TRANSCRIBE_MODEL = "gpt-live-transcribe"
# Current Realtime models (OpenAI deprecations page, checked 2026-11-13).
# gpt-realtime-2.1-mini is OpenAI's named replacement for the retired
# tts-1/tts-1-hd line. Owner must confirm the id at deploy time.
DEFAULT_REALTIME_MODEL = "gpt-realtime-2.1-mini"
DEFAULT_REALTIME_TTS_MODEL = "gpt-realtime-2.1-mini"

# Exact model ids OpenAI has announced as shutting down, plus the
# prefixes their dated snapshots share. Checked 2026-11-13.
DEPRECATED_OPENAI_MODELS: frozenset[str] = frozenset({
    "whisper-1",
    "tts-1",
    "tts-1-hd",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts",
    "gpt-4o-realtime",
    "gpt-4o-mini-realtime",
    "gpt-realtime",
    "gpt-realtime-2025-08-28",
    "gpt-realtime-mini",
    "gpt-realtime-mini-2025-12-15",
})
_DEPRECATED_PREFIXES: tuple[str, ...] = (
    "whisper-1",
    "tts-1",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts",
    "gpt-4o-realtime",
    "gpt-4o-mini-realtime",
)

_REALTIME_REPLACEMENT = "gpt-realtime-2.1-mini"
_TRANSCRIBE_REPLACEMENT = "gpt-transcribe"

_MAX_PROVIDER_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_TRANSCRIBE_BYTES = 25 * 1024 * 1024


def reject_deprecated_openai_model(model: str) -> None:
    """Raise ``ValueError`` when ``model`` is a retired/retiring OpenAI model.

    ``whisper-1`` (shutdown 2027-02-26) → use ``gpt-transcribe``;
    ``tts-1``/``tts-1-hd`` (shutdown 2027-01-06) and the first-generation
    Realtime models (shutdown 2027-01-20) → use the Realtime API with a
    current ``gpt-realtime-2.1*`` model. Unknown models are not rejected
    here — only models OpenAI has announced — so a future model id is
    not blocked by a stale list.
    """
    if not model or not model.strip():
        raise ValueError("OpenAI model must not be empty")
    candidate = model.strip()
    if candidate in DEPRECATED_OPENAI_MODELS or any(
        candidate.startswith(prefix) for prefix in _DEPRECATED_PREFIXES
    ):
        if candidate.startswith(("whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe")):
            replacement = _TRANSCRIBE_REPLACEMENT
            detail = "shutdown 2027-02-26"
        else:
            replacement = _REALTIME_REPLACEMENT
            detail = "shutdown 2027-01-06 / 2027-01-20"
        raise ValueError(
            f"OpenAI model {candidate!r} is deprecated ({detail}); "
            f"use {replacement} instead — tts-1 has no /v1/audio/speech "
            "replacement, it runs only on the Realtime API"
        )


def _http_post(
    url: str,
    *,
    data: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
    opener: Callable[..., Any] | None = None,
) -> tuple[bytes, Mapping[str, str]]:
    """POST bytes; returns (body, headers). Status only on failure."""
    request = urllib.request.Request(url, data=data, method="POST", headers=dict(headers))
    call = opener or urllib.request.urlopen
    try:
        with call(request, timeout=timeout_seconds) as response:
            body = response.read(_MAX_PROVIDER_RESPONSE_BYTES + 1)
            if len(body) > _MAX_PROVIDER_RESPONSE_BYTES:
                raise DaedalusProviderError("Provider response exceeds size limit")
            return body, dict(response.headers)
    except urllib.error.HTTPError as exc:
        logger.warning("daedalus openai provider HTTP %s at %s", exc.code, url.rsplit("/", 1)[0])
        raise DaedalusProviderError(f"OpenAI API returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("daedalus openai transport failure %s", type(exc).__name__)
        raise DaedalusProviderError(
            f"OpenAI API transport failure: {type(exc).__name__}"
        ) from None


def _encode_multipart(
    fields: Mapping[str, str],
    *,
    file_field: str,
    filename: str,
    file_bytes: bytes,
    file_mime_type: str,
    boundary: str | None = None,
) -> tuple[bytes, str]:
    """Encode a multipart/form-data body. Pure function, unit-tested."""
    chosen = boundary or ("----DaedalusOpenAI" + secrets.token_hex(16))
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{chosen}\r\n".encode("ascii"))
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"))
        lines.append(value.encode("utf-8"))
        lines.append(b"\r\n")
    lines.append(f"--{chosen}\r\n".encode("ascii"))
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("ascii")
    )
    lines.append(f"Content-Type: {file_mime_type}\r\n\r\n".encode("ascii"))
    lines.append(file_bytes)
    lines.append(f"\r\n--{chosen}--\r\n".encode("ascii"))
    return b"".join(lines), f"multipart/form-data; boundary={chosen}"


class OpenAIGPTTranscribeTranscriber:
    """Batch transcription via OpenAI ``gpt-transcribe`` (stdlib HTTP).

    Requires ``OPENAI_API_KEY``. ``whisper-1`` is rejected at
    construction — it shuts down 2027-02-26. Not live-tested here: no
    key was available and no live call was made.
    """

    PROVIDER = "openai-gpt-transcribe"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = GPT_TRANSCRIBE_MODEL,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI transcription")
        reject_deprecated_openai_model(model)
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def transcribe(
        self, audio_bytes: bytes, *, filename: str = "audio.wav", language: str | None = None
    ) -> str:
        if not audio_bytes:
            raise ValueError("Audio bytes are required")
        if len(audio_bytes) > MAX_TRANSCRIBE_BYTES:
            raise ValueError("Audio exceeds the 25 MB transcription file limit")
        fields: dict[str, str] = {"model": self.model, "response_format": "json"}
        if language:
            fields["language"] = language
        body, content_type = _encode_multipart(
            fields,
            file_field="file",
            filename=filename,
            file_bytes=bytes(audio_bytes),
            file_mime_type="audio/wav" if filename.endswith(".wav") else "application/octet-stream",
        )
        raw, _headers = _http_post(
            f"{self.base_url}/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": content_type,
                "Accept": "application/json",
            },
            timeout_seconds=self.timeout_seconds,
            opener=self._opener,
        )
        try:
            result = json.loads(raw)
            text = str(result["text"]).strip()
        except (ValueError, KeyError, TypeError):
            raise DaedalusProviderError("Invalid OpenAI transcription response") from None
        if not text:
            raise DaedalusProviderError("OpenAI returned an empty transcript")
        return text


@dataclass(frozen=True)
class OpenAIRealtimeSession:
    """A minted Realtime session: id, model, voice, ephemeral key, expiry.

    The ephemeral key (``client_secret``) is short-lived by design and
    must never be logged. ``redacted()`` is the only safe description.
    """

    session_id: str
    model: str
    voice: str | None
    ephemeral_key: str
    expires_at: int | None

    def redacted(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "model": self.model,
            "voice": self.voice,
            "ephemeral_key_present": bool(self.ephemeral_key),
            "expires_at": self.expires_at,
        }


def create_realtime_session(
    *,
    api_key: str | None = None,
    model: str | None = None,
    voice: str | None = None,
    base_url: str = "https://api.openai.com/v1",
    timeout_seconds: float = 45.0,
    opener: Callable[..., Any] | None = None,
) -> OpenAIRealtimeSession:
    """Mint a Realtime session (``POST /v1/realtime/sessions``).

    ``model`` defaults to ``gpt-realtime-2.1-mini`` when unset; pass an
    explicit current model id (or ``OPENAI_REALTIME_MODEL`` via
    :class:`DaedalusSettings`) at deploy time. Deprecated Realtime
    models are rejected. Returns the ephemeral key the WebSocket client
    authenticates with — never log it.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY is required for the OpenAI Realtime API")
    chosen_model = (model or os.environ.get("OPENAI_REALTIME_MODEL") or DEFAULT_REALTIME_MODEL).strip()
    reject_deprecated_openai_model(chosen_model)
    payload: dict[str, Any] = {"model": chosen_model}
    if voice:
        payload["voice"] = voice
    raw, _headers = _http_post(
        f"{base_url.rstrip('/')}/realtime/sessions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    try:
        result = json.loads(raw)
        secret = result["client_secret"]["value"]
        session_id = str(result["id"])
        expires_at = result.get("expires_at")
    except (ValueError, KeyError, TypeError):
        raise DaedalusProviderError("Invalid OpenAI Realtime session response") from None
    if not secret:
        raise DaedalusProviderError("OpenAI Realtime session returned no ephemeral key")
    return OpenAIRealtimeSession(
        session_id=session_id,
        model=chosen_model,
        voice=voice,
        ephemeral_key=str(secret),
        expires_at=int(expires_at) if expires_at is not None else None,
    )


@dataclass(frozen=True)
class RealtimeSpeechAudio:
    """Audio produced by the Realtime API: raw PCM16 bytes (base64-decoded)."""

    audio: bytes
    mime_type: str = "audio/pcm"
    provider: str = "openai-realtime"
    voice: str | None = None


def _default_ws_factory(url: str, headers: Mapping[str, str]) -> Any:
    """Build a WebSocket client from the ``websockets`` package.

    Raises ``ImportError`` with an install hint when the package is
    absent — the stdlib has no WebSocket client, so a Realtime voice
    call cannot be faked into existence without it.
    """
    try:
        from websockets.sync.client import connect  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "websockets is not installed; install websockets==17.4 "
            "before using OpenAIRealtimeTTSSpeaker, or pass ws_factory="
            "with a test double"
        ) from exc
    return connect(url, additional_headers=dict(headers))


class OpenAIRealtimeTTSSpeaker:
    """Text-to-speech through the OpenAI Realtime API (WebSocket only).

    Flow: mint a session (or accept one), open
    ``wss://api.openai.com/v1/realtime?model=<model>`` with the ephemeral
    key, send ``session.update`` (audio-only, ``pcm16``), then
    ``conversation.item.create`` with the text as a user message and
    ``response.create``; collect ``response.audio.delta`` events
    (base64 PCM16) until ``response.done``. No ``/v1/audio/speech``
    call is made anywhere in this class — that endpoint's models shut
    down 2027-01-06.

    ``ws_factory`` is injectable for tests: ``ws_factory(url, headers)``
    must return a context manager with ``send(str)`` / ``recv() -> str``.
    When omitted, the ``websockets`` package is required.
    """

    PROVIDER = "openai-realtime"
    REALTIME_WS_URL = "wss://api.openai.com/v1/realtime"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        voice: str = "alloy",
        session: OpenAIRealtimeSession | None = None,
        timeout_seconds: float = 120.0,
        ws_factory: Callable[[str, Mapping[str, str]], Any] | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key and session is None:
            raise ValueError("OPENAI_API_KEY is required for Realtime TTS (or pass a session)")
        chosen_model = (model or session.model if session is not None else model) or (
            os.environ.get("OPENAI_REALTIME_MODEL") or DEFAULT_REALTIME_TTS_MODEL
        )
        reject_deprecated_openai_model(chosen_model)
        self.model = chosen_model.strip()
        self.voice = voice.strip()
        if not self.voice:
            raise ValueError("Realtime voice must not be empty")
        self.session = session
        self.timeout_seconds = timeout_seconds
        self._ws_factory = ws_factory

    def _connect(self) -> Any:
        if self.session is not None:
            token = self.session.ephemeral_key
            model = self.session.model
        else:
            token = self._api_key
            model = self.model
        url = f"{self.REALTIME_WS_URL}?model={model}"
        headers = {"Authorization": f"Bearer {token}"}
        factory = self._ws_factory or _default_ws_factory
        return factory(url, headers)

    def speak(self, text: str, **kwargs: Any) -> RealtimeSpeechAudio:
        if not text.strip():
            raise ValueError("Text to speak must not be empty")
        if len(text) > 4096:
            raise ValueError("Text exceeds the Realtime TTS 4096 character input limit")
        voice = str(kwargs.get("voice") or self.voice)
        started = time.monotonic()
        chunks: list[bytes] = []
        with self._connect() as ws:
            ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["audio"],
                    "voice": voice,
                    "output_audio_format": "pcm16",
                },
            }))
            ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }))
            ws.send(json.dumps({"type": "response.create", "response": {"modalities": ["audio"]}}))
            while True:
                if time.monotonic() - started > self.timeout_seconds:
                    raise DaedalusProviderError("Realtime TTS timed out waiting for audio")
                event = json.loads(ws.recv())
                event_type = event.get("type")
                if event_type == "response.audio.delta":
                    delta = event.get("delta", "")
                    if delta:
                        chunks.append(base64.b64decode(delta))
                elif event_type == "response.done":
                    break
                elif event_type == "error":
                    raise DaedalusProviderError("OpenAI Realtime returned an error event")
                # All other events (audio_transcript, etc.) are ignored.
        audio = b"".join(chunks)
        if not audio:
            raise DaedalusProviderError("Realtime TTS returned no audio")
        logger.debug(
            "daedalus openai realtime tts model=%s voice=%s audio_bytes=%d latency_ms=%d",
            self.model, voice, len(audio), round((time.monotonic() - started) * 1000),
        )
        return RealtimeSpeechAudio(audio=audio, voice=voice)


def build_gpt_transcribe_from_env(
    *, opener: Callable[..., Any] | None = None
) -> OpenAIGPTTranscribeTranscriber:
    """Build the gpt-transcribe transcriber from env (key required)."""
    return OpenAIGPTTranscribeTranscriber(opener=opener)


def build_realtime_speaker_from_env(
    *, ws_factory: Callable[[str, Mapping[str, str]], Any] | None = None
) -> OpenAIRealtimeTTSSpeaker:
    """Build the Realtime TTS speaker from env (key + model required)."""
    return OpenAIRealtimeTTSSpeaker(ws_factory=ws_factory)
