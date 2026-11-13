"""Role-worker LLM wiring for Sanders Dash & Seal.

The IT AI Manager registry (``agent_registry``) is interface-only:
twelve named agents, no execution.  This module wires a registered
agent to a real chat backend (Claude or OpenAI) through an injectable
client — the same ``generate(system, user_message)`` shape used by
``DaedalusClaudeTransport`` / ``OpenAIChatTransport`` — so a role
worker can do real language work without inventing a new interface.

Rules, stated honestly
----------------------
* ``run_role_task`` raises ``ValueError`` for an unregistered agent
  name and for a missing backend.  No agent runs on a fake by
  accident: fakes must be passed explicitly (tests do this).
* The backend is chosen by ``LLM_BACKEND`` (``claude`` or ``openai``,
  default ``claude``) and built from the environment; without the
  backend's key/model it raises instead of pretending to work.
* Free-tier-first: nothing here spends money on its own.  The only
  no-cost execution path is a caller-supplied local/fake backend;
  provider calls are billed by the provider under the owner's key.
  See ``docs/AI_PLATFORM_SERVICES_LINKING.md``.
* Results are plain text plus the agent name, backend and model.
  This module does not execute, deploy or persist anything the model
  returns.
"""

from __future__ import annotations

import os
from typing import Any

from .agent_registry import AGENTS, require_registered_agent


class RoleWorkerError(RuntimeError):
    """Role-worker failure (bad agent, missing backend, provider error)."""


def available_backends() -> tuple[str, str]:
    return ("claude", "openai")


def build_backend(backend: str | None = None):
    """Build the chat backend named by ``backend`` / ``LLM_BACKEND``.

    Returns a transport with ``generate(system, user_message,
    max_tokens, metadata)``.  Raises ``ValueError`` for an unknown
    backend name or missing key/model.
    """
    name = (backend or os.environ.get("LLM_BACKEND", "claude")).strip().lower()
    if name == "claude":
        from .anthropic_sdk_transport import ClaudeTransport

        return ClaudeTransport()
    if name == "openai":
        from .openai_chat_transport import OpenAIChatTransport

        return OpenAIChatTransport()
    raise ValueError(f"unknown LLM backend {name!r}; expected 'claude' or 'openai'")


def run_role_task(
    *,
    agent_name: str,
    task: str,
    system: str | None = None,
    backend=None,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Run one language task as a registered IT agent.

    ``backend`` is a transport (or a fake with the same ``generate``
    shape).  When omitted it is built from the environment, which
    requires the backend's key/model.  Returns ``agent``, ``backend``,
    ``model``, ``text`` and ``task``.  The model output is returned
    verbatim; this function does not execute it.
    """
    descriptor = require_registered_agent(agent_name)
    if not task.strip():
        raise ValueError("role task must not be empty")
    client = backend if backend is not None else build_backend()
    prompt_system = system or (
        f"You are the {descriptor.name} of Sanders Dash & Seal, "
        "an IT AI Manager agent. Answer with concrete, checkable "
        "steps. Do not claim an action was performed; describe what "
        "should be done and what evidence would confirm it."
    )
    try:
        response = client.generate(
            system=prompt_system,
            user_message=task,
            max_tokens=max_tokens,
            metadata={"component": "ROLE_WORKER", "agent": descriptor.name},
        )
    except (ValueError, RuntimeError) as exc:
        raise RoleWorkerError(
            f"role task failed for {descriptor.name}: {type(exc).__name__}"
        ) from exc
    return {
        "agent": descriptor.name,
        "backend": getattr(client, "backend", None)
        or type(client).__name__,
        "model": getattr(response, "model", ""),
        "text": response.text,
        "task": task,
    }


def role_task_status() -> dict[str, Any]:
    """Honest wiring status: which agents exist, which backend is configured.

    No provider call is made.  ``backend_configured`` is True only
    when the selected backend's key AND model env vars are present.
    """
    backend = (os.environ.get("LLM_BACKEND", "claude")).strip().lower()
    if backend == "openai":
        configured = bool(
            os.environ.get("OPENAI_API_KEY")
            and (
                os.environ.get("OPENAI_CHAT_MODEL")
                or os.environ.get("DAEDALUS_OPENAI_MODEL")
            )
        )
    else:
        backend = "claude"
        configured = bool(
            os.environ.get("ANTHROPIC_API_KEY")
            and os.environ.get("DAEDALUS_CLAUDE_MODEL")
        )
    return {
        "agents": sorted(AGENTS),
        "agent_count": len(AGENTS),
        "backend": backend,
        "backend_configured": configured,
        "live_status": "READY" if configured else "MISSING_KEY",
    }


__all__ = [
    "RoleWorkerError",
    "available_backends",
    "build_backend",
    "run_role_task",
    "role_task_status",
]
