"""Daedalus live Claude transport. Additive adapter; no deployment side effects.

Two backends share one response type and one error type:

- :class:`DaedalusClaudeTransport` — zero-dependency stdlib ``urllib``
  client. Works anywhere Python runs, with no third-party install. This
  is the fallback backend and its request/response behaviour is
  unchanged from the 2026-11-13 rebuild, except the
  ``anthropic-version`` header, which now matches the current official
  SDK default (``2026-10-21``, observed from ``anthropic`` 2.8.0)
  instead of the retired ``2023-06-01`` value.
- :class:`DaedalusClaudeSDKTransport` / :class:`AsyncDaedalusClaudeTransport`
  — the official ``anthropic`` Python SDK (tested here against 2.8.0,
  which moved its HTTP layer from ``httpx`` to ``httpx2`` and removed
  the legacy ``completions`` API in 1.0.0). ``Anthropic`` /
  ``AsyncAnthropic`` with ``messages.create(model=..., max_tokens=...,
  system=..., messages=[...])``. The SDK is optional: when it is not
  installed, :func:`build_transport` falls back to the stdlib backend
  and ``backend="sdk"`` raises an honest error instead of pretending.

Use :func:`build_transport` (``backend="auto"`` by default) or build a
backend directly. No model id is hardcoded: the caller supplies a real
available model (env ``DAEDALUS_CLAUDE_MODEL``). No simulated model
output, fallback text, or implicit tool execution. Provider failures
never leak API credentials or upstream response bodies.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import math
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .daedalus_config import DaedalusSettings

__all__ = [
    "ANTHROPIC_VERSION",
    "AsyncDaedalusClaudeTransport",
    "DaedalusClaudeSDKTransport",
    "DaedalusClaudeTransport",
    "DaedalusProviderError",
    "DaedalusResponse",
    "build_transport",
]

logger = logging.getLogger("daedalus.transport")

# Current Messages API version header, matching the official SDK 2.8.0
# default observed in local testing (2026-11-13).
ANTHROPIC_VERSION = "2026-10-21"

_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class DaedalusProviderError(RuntimeError):
    """Provider failure without leaking API credentials or response bodies."""


@dataclass(frozen=True)
class DaedalusTransportConfig:
    """Typed transport config. Key/model come from the secure flow / env only.

    No default model is chosen here; a missing field names itself in the
    ValueError instead of failing later inside a provider call.
    """

    model: str
    api_key: str
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> "DaedalusTransportConfig":
        missing = [n for n in ("DAEDALUS_CLAUDE_MODEL", "ANTHROPIC_API_KEY")
                   if not os.environ.get(n)]
        if missing:
            raise ValueError(
                f"Missing Daedalus config: {', '.join(missing)}")
        return cls(model=os.environ["DAEDALUS_CLAUDE_MODEL"],
                   api_key=os.environ["ANTHROPIC_API_KEY"],
                   timeout_seconds=float(
                       os.environ.get("DAEDALUS_TIMEOUT_SECONDS", "45.0")))


@dataclass(frozen=True)
class DaedalusResponse:
    model: str
    request_id: str | None
    message_id: str
    text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


def _validate_common(
    *, model: str, api_key: str, timeout_seconds: float
) -> tuple[str, str, float]:
    if not model:
        raise ValueError("DAEDALUS_CLAUDE_MODEL must identify a real available model")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required for live reasoning")
    if (
        not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a finite positive duration")
    return model, api_key, float(timeout_seconds)


def _validate_generate_args(*, system: str, user_message: str, max_tokens: int) -> None:
    if not system.strip() or not user_message.strip():
        raise ValueError("System and user messages must not be empty")
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer; provider model limits apply")


def _audit(audit: Callable[[dict[str, Any]], None] | None, output: DaedalusResponse,
           metadata: dict[str, str] | None) -> None:
    if audit is not None:
        # No prompts, completions, or credentials are sent to the audit callback.
        audit({
            "component": "DAEDALUS",
            "provider": "anthropic",
            "model": output.model,
            "request_id": output.request_id,
            "message_id": output.message_id,
            "latency_ms": output.latency_ms,
            "input_tokens": output.input_tokens,
            "output_tokens": output.output_tokens,
            "metadata": metadata or {},
        })


def _log_success(backend: str, output: DaedalusResponse) -> None:
    logger.debug(
        "daedalus transport=%s model=%s latency_ms=%d input_tokens=%d output_tokens=%d",
        backend, output.model, output.latency_ms, output.input_tokens, output.output_tokens,
    )


class DaedalusClaudeTransport:
    """Stdlib Claude Messages API adapter (zero third-party dependencies).

    The caller controls prompts, model selection, and audit persistence.
    This adapter cannot compile, deploy, or execute generated code.
    """

    ENDPOINT = "https://api.anthropic.com/v1/messages"
    BACKEND = "stdlib"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model, self._api_key, self.timeout_seconds = _validate_common(
            model=model or os.environ.get("DAEDALUS_CLAUDE_MODEL", ""),
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            timeout_seconds=timeout_seconds,
        )
        self.audit = audit

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
        _validate_generate_args(system=system, user_message=user_message, max_tokens=max_tokens)
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.ENDPOINT,
            data=data,
            method="POST",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
                "accept": "application/json",
            },
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(
                req,
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                request_id = response.headers.get("request-id")
                body = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(body) > _MAX_RESPONSE_BYTES:
                    raise DaedalusProviderError("Provider response exceeds size limit")
        except urllib.error.HTTPError as exc:
            # Never include upstream response body or secret-bearing request headers.
            logger.warning("daedalus transport=stdlib provider HTTP %s", exc.code)
            raise DaedalusProviderError(
                f"Anthropic Messages API returned HTTP {exc.code}"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("daedalus transport=stdlib failure %s", type(exc).__name__)
            raise DaedalusProviderError(
                f"Anthropic Messages API transport failure: {type(exc).__name__}"
            ) from None
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            result = json.loads(body)
            if result.get("type") != "message":
                raise ValueError("Unexpected provider response type")
            text = "".join(
                block.get("text", "")
                for block in result["content"]
                if block.get("type") == "text"
            )
            usage = result["usage"]
            output = DaedalusResponse(
                model=result["model"],
                request_id=request_id,
                message_id=result["id"],
                text=text,
                latency_ms=latency_ms,
                input_tokens=int(usage["input_tokens"]),
                output_tokens=int(usage["output_tokens"]),
            )
        except (ValueError, KeyError, TypeError, IndexError):
            raise DaedalusProviderError("Invalid Anthropic Messages API response") from None
        _audit(self.audit, output, metadata)
        _log_success(self.BACKEND, output)
        return output

    async def agenerate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
        """Async form of :meth:`generate`, run off the event loop thread.

        The stdlib ``urllib`` call is blocking I/O, so it runs via
        ``asyncio.to_thread`` instead of stalling the loop. Prefer the
        SDK async transport when the ``anthropic`` package is installed.
        """
        return await asyncio.to_thread(
            self.generate,
            system=system,
            user_message=user_message,
            max_tokens=max_tokens,
            metadata=metadata,
        )

    def close(self) -> None:
        """No persistent connection to close for the stdlib backend."""


def _sdk_available() -> bool:
    return importlib.util.find_spec("anthropic") is not None


def _extract_sdk_text(message: Any) -> str:
    return "".join(
        getattr(block, "text", "")
        for block in getattr(message, "content", [])
        if getattr(block, "type", None) == "text"
    )


def _sdk_response(message: Any, latency_ms: int) -> DaedalusResponse:
    usage = message.usage
    return DaedalusResponse(
        model=message.model,
        # The SDK's public Message type does not expose the HTTP
        # request-id; report None rather than inventing one.
        request_id=None,
        message_id=message.id,
        text=_extract_sdk_text(message),
        latency_ms=latency_ms,
        input_tokens=int(usage.input_tokens),
        output_tokens=int(usage.output_tokens),
    )


class DaedalusClaudeSDKTransport:
    """Official Anthropic SDK adapter (sync).

    Requires the ``anthropic`` package (tested against 2.8.0; SDK 1.x
    moved the HTTP layer from ``httpx`` to ``httpx2`` and removed the
    legacy completions API, so a pinned ``httpx.Client`` must not be
    passed in). ``max_retries`` is the SDK default (2) unless the
    caller overrides it; retries apply to the SDK's own retryable
    statuses and honour ``Retry-After``.
    """

    BACKEND = "sdk"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model, self._api_key, self.timeout_seconds = _validate_common(
            model=model or os.environ.get("DAEDALUS_CLAUDE_MODEL", ""),
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            timeout_seconds=timeout_seconds,
        )
        if type(max_retries) is not int or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self.max_retries = max_retries
        self.audit = audit
        try:
            import anthropic
        except ImportError:
            raise DaedalusProviderError(
                "Anthropic SDK is not installed; install 'anthropic>=2' "
                "or use backend='stdlib'"
            ) from None
        self._anthropic = anthropic
        try:
            self._client = anthropic.Anthropic(
                api_key=self._api_key,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
        except Exception as exc:
            # E.g. an unparseable proxy URL in the process environment:
            # the SDK builds its HTTP client from proxy env vars.
            raise DaedalusProviderError(
                "Anthropic SDK client could not be created: "
                f"{type(exc).__name__}"
            ) from None

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
        _validate_generate_args(system=system, user_message=user_message, max_tokens=max_tokens)
        started = time.monotonic()
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except self._anthropic.APIStatusError as exc:
            # Status only: never include the upstream error body.
            logger.warning("daedalus transport=sdk provider HTTP %s", exc.status_code)
            raise DaedalusProviderError(
                f"Anthropic Messages API returned HTTP {exc.status_code}"
            ) from None
        except self._anthropic.APIConnectionError as exc:
            logger.warning("daedalus transport=sdk failure %s", type(exc).__name__)
            raise DaedalusProviderError(
                f"Anthropic Messages API transport failure: {type(exc).__name__}"
            ) from None
        output = _sdk_response(message, round((time.monotonic() - started) * 1000))
        _audit(self.audit, output, metadata)
        _log_success(self.BACKEND, output)
        return output

    async def agenerate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
        """Sync SDK client called off the event loop thread.

        For a natively async call use :class:`AsyncDaedalusClaudeTransport`.
        """
        return await asyncio.to_thread(
            self.generate,
            system=system,
            user_message=user_message,
            max_tokens=max_tokens,
            metadata=metadata,
        )

    def close(self) -> None:
        self._client.close()


class AsyncDaedalusClaudeTransport:
    """Official Anthropic SDK adapter (async, ``AsyncAnthropic``).

    Use inside ``asyncio`` code so the request path stays non-blocking.
    Never call the sync SDK client from inside an event loop.
    """

    BACKEND = "sdk-async"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model, self._api_key, self.timeout_seconds = _validate_common(
            model=model or os.environ.get("DAEDALUS_CLAUDE_MODEL", ""),
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            timeout_seconds=timeout_seconds,
        )
        if type(max_retries) is not int or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self.max_retries = max_retries
        self.audit = audit
        try:
            import anthropic
        except ImportError:
            raise DaedalusProviderError(
                "Anthropic SDK is not installed; install 'anthropic>=2' "
                "or use backend='stdlib'"
            ) from None
        self._anthropic = anthropic
        try:
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
        except Exception as exc:
            raise DaedalusProviderError(
                "Anthropic SDK client could not be created: "
                f"{type(exc).__name__}"
            ) from None

    async def agenerate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
        _validate_generate_args(system=system, user_message=user_message, max_tokens=max_tokens)
        started = time.monotonic()
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except self._anthropic.APIStatusError as exc:
            logger.warning("daedalus transport=sdk-async provider HTTP %s", exc.status_code)
            raise DaedalusProviderError(
                f"Anthropic Messages API returned HTTP {exc.status_code}"
            ) from None
        except self._anthropic.APIConnectionError as exc:
            logger.warning("daedalus transport=sdk-async failure %s", type(exc).__name__)
            raise DaedalusProviderError(
                f"Anthropic Messages API transport failure: {type(exc).__name__}"
            ) from None
        output = _sdk_response(message, round((time.monotonic() - started) * 1000))
        _audit(self.audit, output, metadata)
        _log_success(self.BACKEND, output)
        return output

    def generate(self, **kwargs: Any) -> Any:
        """Not available: this transport is async-only by design.

        Call :meth:`agenerate` from ``asyncio`` code, or use
        :class:`DaedalusClaudeSDKTransport` for sync callers.
        """
        raise TypeError(
            "AsyncDaedalusClaudeTransport has no sync generate(); "
            "await agenerate() or use DaedalusClaudeSDKTransport"
        )

    async def aclose(self) -> None:
        await self._client.close()


def build_transport(
    *,
    settings: DaedalusSettings | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float | None = None,
    backend: str = "auto",
    max_retries: int = 2,
    audit: Callable[[dict[str, Any]], None] | None = None,
) -> DaedalusClaudeTransport | DaedalusClaudeSDKTransport:
    """Build a Claude transport from settings or explicit arguments.

    ``backend``: ``"auto"`` prefers the SDK when installed and falls
    back to stdlib; ``"sdk"`` requires the SDK; ``"stdlib"`` always
    uses the zero-dependency client. Explicit arguments override
    ``settings``; when ``settings`` is None it is read from the
    environment. Raises ``ValueError`` when the model or key is absent,
    and ``DaedalusProviderError`` when ``backend="sdk"`` but the SDK
    is not installed.
    """
    resolved = settings or DaedalusSettings.from_env()
    chosen = (backend or "auto").strip().lower()
    if chosen not in {"auto", "sdk", "stdlib"}:
        raise ValueError("backend must be one of 'auto', 'sdk', 'stdlib'")
    final_model = model if model is not None else resolved.claude_model
    final_key = api_key if api_key is not None else resolved.anthropic_api_key
    final_timeout = timeout_seconds if timeout_seconds is not None else resolved.timeout_seconds
    if chosen == "stdlib":
        return DaedalusClaudeTransport(
            model=final_model, api_key=final_key,
            timeout_seconds=final_timeout, audit=audit,
        )
    if chosen == "sdk":
        if not _sdk_available():
            raise DaedalusProviderError(
                "Anthropic SDK is not installed; install 'anthropic>=2' "
                "or use backend='stdlib'"
            )
        return DaedalusClaudeSDKTransport(
            model=final_model, api_key=final_key,
            timeout_seconds=final_timeout, max_retries=max_retries, audit=audit,
        )
    # auto: SDK when present, stdlib otherwise — logged, never silent.
    if _sdk_available():
        logger.info("daedalus transport=auto selected sdk backend")
        return DaedalusClaudeSDKTransport(
            model=final_model, api_key=final_key,
            timeout_seconds=final_timeout, max_retries=max_retries, audit=audit,
        )
    logger.info("daedalus transport=auto selected stdlib backend (anthropic SDK not installed)")
    return DaedalusClaudeTransport(
        model=final_model, api_key=final_key,
        timeout_seconds=final_timeout, audit=audit,
    )
