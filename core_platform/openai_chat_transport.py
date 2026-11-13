"""OpenAI chat + Realtime adapters for Daedalus, role workers and Grantwriter.

Scope, stated honestly
----------------------
* Chat completions use the OpenAI Responses/Chat API over stdlib
  ``urllib`` — no SDK required at import time.  When the ``openai``
  package is installed, :class:`OpenAIChatTransport` can be constructed
  with ``use_sdk=True`` and delegates to it; otherwise it uses the
  stdlib path.  Either way, no live call is made without
  ``OPENAI_API_KEY`` and a model from the environment
  (``OPENAI_CHAT_MODEL`` or ``DAEDALUS_OPENAI_MODEL``).
* Deprecation handling is a hard reject, not a silent fallback:
  ``whisper-1`` (removed 26 Feb 2027), ``tts-1`` / ``tts-1-hd``
  (shutdown 6 Jan 2027) and ``gpt-4o-transcribe`` (deprecated, removed
  26 Feb 2027) raise ``ValueError`` at construction.  Transcription
  belongs to ``gpt-transcribe`` (see ``daedalus_voice.OpenAITranscriber``);
  speech belongs to Google/ElevenLabs/system TTS — never to ``tts-1``.
* Realtime is config-only here: :func:`realtime_session_config`
  validates the model/key and returns the WebSocket URL, headers and
  model a caller needs to open a Realtime session.  This module opens
  no WebSocket and performs no live Realtime handshake; plain WSGI
  cannot hold one, and no live peer is fabricated.
* No key, secret or credential is stored, hardcoded or logged.
  ``FakeChatTransport`` is the deterministic offline stand-in used by
  tests; it returns canned text and records prompts so tests can assert
  what was asked, without any network.
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

# Models that must never be built on for new work.  whisper-1 /
# gpt-4o-transcribe are transcription models (removed 26 Feb 2027);
# tts-1 / tts-1-hd are speech models (shutdown 6 Jan 2027).  They are
# rejected here even though this is a *chat* transport, so a stale
# model name copied from an old config fails loudly instead of
# silently booking a dead endpoint.
DEPRECATED_MODELS = frozenset(
    {"whisper-1", "gpt-4o-transcribe", "tts-1", "tts-1-hd"}
)

# Chat-capable model families this adapter will accept.  The list is a
# guardrail against typos and against transcription/speech model names
# being passed to a chat endpoint; it is not a claim that every listed
# model exists on the provider — the provider is authoritative.
CHAT_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4")


class OpenAIProviderError(RuntimeError):
    """Provider failure without leaking credentials or response bodies."""


def validate_chat_model(model: str) -> str:
    """Validate a chat model name. Returns it unchanged or raises."""
    if not isinstance(model, str) or not model.strip():
        raise ValueError("OpenAI chat model must be a non-empty string")
    model = model.strip()
    if model in DEPRECATED_MODELS:
        raise ValueError(
            f"model {model!r} is deprecated/removed; do not build new work on it"
        )
    if model.startswith("whisper") or model.startswith("tts-"):
        raise ValueError(
            f"model {model!r} is not a chat model; use the transcription/TTS adapters"
        )
    if not model.startswith(CHAT_MODEL_PREFIXES):
        raise ValueError(
            f"model {model!r} does not look like an OpenAI chat model "
            "(expected a gpt-/o-series model name)"
        )
    return model


@dataclass(frozen=True)
class OpenAIChatConfig:
    """Typed config. Key/model come from env only; nothing is defaulted."""

    model: str
    api_key: str
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> "OpenAIChatConfig":
        missing = [
            n
            for n in ("OPENAI_CHAT_MODEL", "OPENAI_API_KEY")
            if not os.environ.get(n)
        ]
        # DAEDALUS_OPENAI_MODEL is accepted as the model alias.
        if "OPENAI_CHAT_MODEL" in missing and os.environ.get("DAEDALUS_OPENAI_MODEL"):
            missing.remove("OPENAI_CHAT_MODEL")
        if missing:
            raise ValueError(f"Missing OpenAI config: {', '.join(missing)}")
        model = os.environ.get("OPENAI_CHAT_MODEL") or os.environ[
            "DAEDALUS_OPENAI_MODEL"
        ]
        return cls(
            model=validate_chat_model(model),
            api_key=os.environ["OPENAI_API_KEY"],
            timeout_seconds=float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "45.0")),
        )


@dataclass(frozen=True)
class OpenAIChatResponse:
    model: str
    response_id: str | None
    text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


class FakeChatTransport:
    """Deterministic offline chat transport for tests.

    Returns ``text`` for any prompt and records (system, user) pairs.
    """

    name = "fake-openai-chat"

    def __init__(self, text: str = "draft text from fake OpenAI chat") -> None:
        if not text.strip():
            raise ValueError("fake chat text must not be empty")
        self.text = text
        self.calls: list[dict[str, str]] = []

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> OpenAIChatResponse:
        if not system.strip() or not user_message.strip():
            raise ValueError("System and user messages must not be empty")
        self.calls.append({"system": system, "user": user_message})
        return OpenAIChatResponse(
            model="fake-openai-chat",
            response_id="resp_fake",
            text=self.text,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
        )


class OpenAIChatTransport:
    """OpenAI chat adapter (stdlib HTTP by default, SDK when asked).

    ``generate(system, user_message)`` mirrors the Daedalus transport
    call shape so Daedalus, role workers and Grantwriter can share one
    prompt interface across Claude and OpenAI backends.
    """

    ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        use_sdk: bool = False,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        raw_model = (
            model
            or os.environ.get("OPENAI_CHAT_MODEL")
            or os.environ.get("DAEDALUS_OPENAI_MODEL", "")
        )
        self.model = validate_chat_model(raw_model)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for live OpenAI chat")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.audit = audit
        self._sdk_client = None
        if use_sdk:
            try:
                from openai import OpenAI  # type: ignore[import-not-found]
            except ImportError as exc:
                raise ImportError(
                    "openai package is not installed; install openai "
                    "before using OpenAIChatTransport(use_sdk=True)"
                ) from exc
            self._sdk_client = OpenAI(api_key=self._api_key)

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> OpenAIChatResponse:
        if not system.strip() or not user_message.strip():
            raise ValueError("System and user messages must not be empty")
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        if self._sdk_client is not None:
            return self._generate_via_sdk(
                system=system,
                user_message=user_message,
                max_tokens=max_tokens,
                metadata=metadata,
            )
        return self._generate_via_stdlib(
            system=system,
            user_message=user_message,
            max_tokens=max_tokens,
            metadata=metadata,
        )

    def _generate_via_stdlib(
        self, *, system: str, user_message: str, max_tokens: int, metadata: dict | None
    ) -> OpenAIChatResponse:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.ENDPOINT,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(
                req,
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                body = response.read(8 * 1024 * 1024 + 1)
                if len(body) > 8 * 1024 * 1024:
                    raise OpenAIProviderError("Provider response exceeds size limit")
        except urllib.error.HTTPError as exc:
            raise OpenAIProviderError(
                f"OpenAI chat API returned HTTP {exc.code}"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OpenAIProviderError(
                f"OpenAI chat API transport failure: {type(exc).__name__}"
            ) from None
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            result = json.loads(body)
            choice = result["choices"][0]
            text = choice["message"]["content"] or ""
            usage = result.get("usage", {})
            output = OpenAIChatResponse(
                model=result.get("model", self.model),
                response_id=result.get("id"),
                text=text,
                latency_ms=latency_ms,
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
            )
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise OpenAIProviderError("Invalid OpenAI chat API response") from None
        self._audit(output, metadata)
        return output

    def _generate_via_sdk(
        self, *, system: str, user_message: str, max_tokens: int, metadata: dict | None
    ) -> OpenAIChatResponse:
        started = time.monotonic()
        try:
            result = self._sdk_client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as exc:  # SDK raises its own error types; no body leaked.
            raise OpenAIProviderError(
                f"OpenAI SDK chat call failed: {type(exc).__name__}"
            ) from None
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            text = result.choices[0].message.content or ""
            usage = result.usage
            output = OpenAIChatResponse(
                model=result.model,
                response_id=result.id,
                text=text,
                latency_ms=latency_ms,
                input_tokens=int(usage.prompt_tokens or 0),
                output_tokens=int(usage.completion_tokens or 0),
            )
        except (AttributeError, IndexError, TypeError) as exc:
            raise OpenAIProviderError("Invalid OpenAI SDK chat response") from None
        self._audit(output, metadata)
        return output

    def _audit(self, output: OpenAIChatResponse, metadata: dict | None) -> None:
        if self.audit is not None:
            self.audit(
                {
                    "component": "OPENAI_CHAT",
                    "provider": "openai",
                    "model": output.model,
                    "response_id": output.response_id,
                    "latency_ms": output.latency_ms,
                    "input_tokens": output.input_tokens,
                    "output_tokens": output.output_tokens,
                    "metadata": metadata or {},
                }
            )


def realtime_session_config(
    *,
    model: str | None = None,
    api_key: str | None = None,
    voice: str = "alloy",
) -> dict[str, Any]:
    """Build (but do not open) an OpenAI Realtime session config.

    Returns the WebSocket URL, the Authorization header value shape and
    the model, so a real WS client can connect.  Raises ``ValueError``
    without a key or with a deprecated/transcription model — Realtime
    uses ``gpt-realtime`` family models, never ``whisper-1`` or
    ``tts-1``.  No network, no handshake, no fabricated live session.
    """
    raw_model = (
        model
        or os.environ.get("OPENAI_REALTIME_MODEL", "")
        or os.environ.get("OPENAI_CHAT_MODEL", "")
    )
    if not raw_model.strip():
        raise ValueError("OPENAI_REALTIME_MODEL (or OPENAI_CHAT_MODEL) is required")
    if raw_model.strip() in DEPRECATED_MODELS or raw_model.strip().startswith(
        ("whisper", "tts-")
    ):
        raise ValueError(
            f"model {raw_model!r} cannot be used for Realtime; "
            "use a gpt-realtime model"
        )
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI Realtime")
    if not voice.strip():
        raise ValueError("Realtime voice must be a non-empty string")
    return {
        "provider": "openai-realtime",
        "model": raw_model.strip(),
        "websocket_url": (
            "wss://api.openai.com/v1/realtime?model=" + raw_model.strip()
        ),
        "headers": {
            "Authorization": "Bearer <OPENAI_API_KEY>",
            "OpenAI-Beta": "realtime=v1",
        },
        "voice": voice,
        "status": "config_only_no_live_session",
        "note": "Open a WebSocket to websocket_url with a real key; "
        "this function performs no handshake and no audio flows through it.",
    }


__all__ = [
    "DEPRECATED_MODELS",
    "OpenAIProviderError",
    "validate_chat_model",
    "OpenAIChatConfig",
    "OpenAIChatResponse",
    "FakeChatTransport",
    "OpenAIChatTransport",
    "realtime_session_config",
]
