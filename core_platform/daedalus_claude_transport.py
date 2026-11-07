"""Daedalus live Claude transport. Additive adapter; no deployment side effects.

This module makes real authenticated HTTPS requests to Anthropic's Messages API.
No simulated model output, fallback text, or implicit tool execution.
"""
from __future__ import annotations

import json
import math
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class DaedalusProviderError(RuntimeError):
    """Provider failure without leaking API credentials or response bodies."""


@dataclass(frozen=True)
class DaedalusResponse:
    model: str
    request_id: str | None
    message_id: str
    text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


class DaedalusClaudeTransport:
    """Actual Claude Messages API adapter for the existing Daedalus runtime.

    The caller controls prompts, model selection, and audit persistence.
    This adapter cannot compile, deploy, or execute generated code.
    """

    ENDPOINT = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
        audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model = model or os.environ.get("DAEDALUS_CLAUDE_MODEL", "")
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.model:
            raise ValueError("DAEDALUS_CLAUDE_MODEL must identify a real available model")
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for live reasoning")
        if (not isinstance(timeout_seconds, (int, float))
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise ValueError("timeout_seconds must be a finite positive duration")
        self.timeout_seconds = timeout_seconds
        self.audit = audit

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
            raise ValueError("max_tokens must be a positive integer; provider model limits apply")
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
                "anthropic-version": "2023-06-01",
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
                body = response.read(8 * 1024 * 1024 + 1)
                if len(body) > 8 * 1024 * 1024:
                    raise DaedalusProviderError("Provider response exceeds size limit")
        except urllib.error.HTTPError as exc:
            # Never include upstream response body or secret-bearing request headers.
            raise DaedalusProviderError(
                f"Anthropic Messages API returned HTTP {exc.code}"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
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
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise DaedalusProviderError("Invalid Anthropic Messages API response") from None
        if self.audit is not None:
            # No prompts, completions, or credentials are sent to the audit callback.
            self.audit({
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
        return output
