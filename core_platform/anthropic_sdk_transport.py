"""Anthropic Claude transport, SDK-first with stdlib fallback.

Daedalus already has a stdlib transport
(``daedalus_claude_transport.DaedalusClaudeTransport``).  This module
adds the SDK path the task requires without replacing it:

* If the ``anthropic`` package is installed, :class:`ClaudeTransport`
  uses the SDK (``anthropic.Anthropic``) — the supported client.
* If it is not installed, the same class delegates to the existing
  stdlib transport, so behaviour is identical and no extra dependency
  is forced on the Oracle host.
* ``use_sdk=True`` makes a missing SDK an honest ``ImportError``
  instead of a silent fallback.

Model comes from the environment (``DAEDALUS_CLAUDE_MODEL``) or an
explicit argument; the key from ``ANTHROPIC_API_KEY``.  Both are
required — without them construction raises ``ValueError``.  No key
is stored in logs, and the audit callback receives metadata only
(no prompts, completions or credentials).
"""

from __future__ import annotations

import os
from typing import Any, Callable

from .daedalus_claude_transport import (
    DaedalusClaudeTransport,
    DaedalusProviderError,
    DaedalusResponse,
)

__all__ = [
    "ClaudeTransport",
    "DaedalusProviderError",
    "DaedalusResponse",
    "build_claude_transport",
    "sdk_available",
]


def sdk_available() -> bool:
    """True when the ``anthropic`` SDK package is importable."""
    try:
        import anthropic  # noqa: F401  (import check only)

        return True
    except ImportError:
        return False


class ClaudeTransport:
    """Claude Messages API adapter: SDK when present, stdlib otherwise.

    The public call shape is ``generate(system, user_message,
    max_tokens, metadata)`` — identical to
    ``DaedalusClaudeTransport`` — so Daedalus, role workers and
    Grantwriter can swap backends without changing callers.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        use_sdk: bool = False,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model = model or os.environ.get("DAEDALUS_CLAUDE_MODEL", "")
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.model:
            raise ValueError("DAEDALUS_CLAUDE_MODEL must identify a real available model")
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for live reasoning")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.audit = audit
        self.backend = "sdk" if use_sdk else "stdlib"
        if use_sdk and not sdk_available():
            raise ImportError(
                "anthropic package is not installed; install anthropic "
                "before using ClaudeTransport(use_sdk=True), or omit "
                "use_sdk to use the stdlib transport"
            )
        if use_sdk:
            import anthropic  # type: ignore[import-not-found]

            self._sdk_client = anthropic.Anthropic(api_key=self._api_key)
            self._stdlib = None
        else:
            self._sdk_client = None
            self._stdlib = DaedalusClaudeTransport(
                model=self.model,
                api_key=self._api_key,
                timeout_seconds=timeout_seconds,
                audit=audit,
            )

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> DaedalusResponse:
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
        assert self._stdlib is not None
        return self._stdlib.generate(
            system=system,
            user_message=user_message,
            max_tokens=max_tokens,
            metadata=metadata,
        )

    def _generate_via_sdk(
        self, *, system: str, user_message: str, max_tokens: int, metadata: dict | None
    ) -> DaedalusResponse:
        import time

        started = time.monotonic()
        try:
            result = self._sdk_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:  # SDK error types vary; never leak the body.
            raise DaedalusProviderError(
                f"Anthropic SDK call failed: {type(exc).__name__}"
            ) from None
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            text = "".join(
                block.text
                for block in result.content
                if getattr(block, "type", None) == "text"
            )
            output = DaedalusResponse(
                model=result.model,
                request_id=getattr(result, "request_id", None)
                or getattr(getattr(result, "_request_id", None), "request_id", None),
                message_id=result.id,
                text=text,
                latency_ms=latency_ms,
                input_tokens=int(result.usage.input_tokens),
                output_tokens=int(result.usage.output_tokens),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise DaedalusProviderError("Invalid Anthropic SDK response") from None
        if self.audit is not None:
            self.audit(
                {
                    "component": "DAEDALUS",
                    "provider": "anthropic",
                    "backend": "sdk",
                    "model": output.model,
                    "request_id": output.request_id,
                    "message_id": output.message_id,
                    "latency_ms": output.latency_ms,
                    "input_tokens": output.input_tokens,
                    "output_tokens": output.output_tokens,
                    "metadata": metadata or {},
                }
            )
        return output


def build_claude_transport(
    *,
    use_sdk: bool = False,
    audit: Callable[[dict[str, Any]], None] | None = None,
) -> ClaudeTransport:
    """Build a Claude transport from the environment.

    Raises ``ValueError`` when model/key are missing, ``ImportError``
    when ``use_sdk=True`` and the SDK is absent.
    """
    return ClaudeTransport(use_sdk=use_sdk, audit=audit)
