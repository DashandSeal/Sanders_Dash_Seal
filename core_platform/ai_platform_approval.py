"""AI-platform approval gates for Sanders Dash & Seal (2026-11-13).

Every live external platform in this project sits behind an explicit
owner approval gate. A gate is ``UNAPPROVED`` until one of exactly two
things happens:

1. the owner explicitly approves that specific platform/gate in a
   recorded approval (``record_approval``), or
2. a real verifier for that gate returns ``True``
   (``record_verifier_result`` with ``passed=True``).

Nothing here defaults to approved, nothing is fabricated, and no gate
is ever flipped by a test, a build step, or an import. Approval state
lives in ``core_platform/ai_platform_approvals.json`` next to this
module; the file is the record, this module is the enforcement.

Scope — what is gated and what is not
--------------------------------------
Only *live* operation against an external platform is gated: a real
Anthropic model call, a live Stripe key, a live voice/video provider,
a live grantwriter generation, a live RON/notarial session, live
Daedalus reasoning, live AI role workers, the release verifier for
PR #2 / Checkout, and the Gateway workflow fix. Local builds,
installation, ordinary startup, and local fake/test transports are
not gated: a fake key never touches the network, so it is not live
operation and the guard lets it through. A key is treated as live
when it looks like a real provider key (``sk-ant-`` prefix for
Anthropic) or when the caller explicitly declares live intent
(:func:`build_live_engine` in ``daedalus_engine``).

Free resources first: wherever a platform offers a free tier or free
resources, those are used first before any paid service. An approval
for a live gate does not authorize paid use where a free option
exists, and no gate here authorizes spending.

Guard behaviour
---------------
:func:`require_approval` raises :class:`ApprovalRequiredError` — a
``ValueError`` — naming the missing approval, and
:func:`http_failure` returns the same fact as an honest HTTP 503
payload (``{"status": 503, "error": "approval_required", ...}``) for
WSGI paths. Unapproved live use therefore fails loudly instead of
pretending to work.

No secrets are stored, logged, or returned by this module. Approval
records name only the approver (the owner, Roosevelt Sanders) and the
gate; they never contain keys, tokens, or credentials.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

__all__ = [
    "APPROVED",
    "UNAPPROVED",
    "ApprovalRequiredError",
    "ApprovalStore",
    "Gate",
    "GATES",
    "GATE_IDS",
    "DEFAULT_STATE_PATH",
    "approval_checklist",
    "check_live",
    "guarded_call",
    "guarded_grantwriter_generation",
    "http_failure",
    "is_approved",
    "load_store",
    "render_checklist",
    "require_approval",
]

APPROVED = "APPROVED"
UNAPPROVED = "UNAPPROVED"

OWNER = "Roosevelt Sanders"
STATE_VERSION = 1

#: The state file lives next to this module and is the approval record.
DEFAULT_STATE_PATH = Path(__file__).resolve().with_name("ai_platform_approvals.json")


@dataclass(frozen=True)
class Gate:
    """One approval gate: a live platform that needs owner approval."""

    gate_id: str
    label: str
    description: str
    unlocks: str
    how_to_approve: str


GATES: tuple[Gate, ...] = (
    Gate(
        gate_id="release_verifier_pr2_checkout",
        label="Release verifier for PR #2 / Checkout",
        description=(
            "The release verifier that must pass before PR #2 (Checkout) "
            "can be released. Covers Stripe, identity, and hosting checks "
            "for the checkout path."
        ),
        unlocks="Releasing PR #2 / Checkout to production.",
        how_to_approve=(
            "Owner reviews the release verifier result for PR #2 and "
            "records an explicit approval for this gate, or the real "
            "release verifier returns True."
        ),
    ),
    Gate(
        gate_id="gateway_workflow_fix",
        label="Gateway workflow fix",
        description=(
            "The fix for the Architectural Integrity Gateway workflow "
            "('Securely Push Verified Manifest Assets', exit 128), which "
            "currently blocks PR #107."
        ),
        unlocks="Merging PR #107 and any PR gated on the Gateway check.",
        how_to_approve=(
            "Owner applies the Gateway workflow fix (see "
            "gateway-workflow-fix-owner-steps.md) and the Gateway check "
            "passes, or the owner records an explicit approval."
        ),
    ),
    Gate(
        gate_id="stripe_live_keys",
        label="Stripe live keys",
        description=(
            "Live Stripe secret/publishable keys and the live webhook "
            "secret. Test-mode keys are not live operation and are not "
            "gated; only live keys are."
        ),
        unlocks="Charging real cards and receiving live Stripe webhooks.",
        how_to_approve=(
            "Owner supplies/confirms the live Stripe keys and records an "
            "explicit approval for this gate."
        ),
    ),
    Gate(
        gate_id="anthropic_live_model",
        label="Anthropic live model",
        description=(
            "A live Anthropic API key and a live Claude model id used for "
            "real reasoning calls (api.anthropic.com)."
        ),
        unlocks="Live Claude calls through Daedalus transports.",
        how_to_approve=(
            "Owner supplies/confirms the live Anthropic key and model and "
            "records an explicit approval for this gate."
        ),
    ),
    Gate(
        gate_id="grantwriter_purpose",
        label="Grantwriter purpose approval",
        description=(
            "Approval of the purpose for live grantwriter generation: "
            "which grants, whose data, and what the generated drafts may "
            "be used for."
        ),
        unlocks="Live AI-assisted grant drafting in app/grantwriter_mother.py.",
        how_to_approve=(
            "Owner states the approved grantwriter purpose and records an "
            "explicit approval for this gate."
        ),
    ),
    Gate(
        gate_id="ron_notarial",
        label="RON / notarial approval",
        description=(
            "Remote Online Notarization / notarial sessions: a real "
            "notarial act with legal effect, which requires a commissioned "
            "notary and a compliant RON provider/session."
        ),
        unlocks="Live RON/notarial sessions (native_notary.py, native_ron_rooms.py).",
        how_to_approve=(
            "Owner confirms the commissioned notary and RON provider and "
            "records an explicit approval for this gate."
        ),
    ),
    Gate(
        gate_id="voice_video_provider",
        label="Voice/video provider approval",
        description=(
            "A live voice/video provider used for real calls: transcription "
            "(Whisper/Deepgram), speech (Google/ElevenLabs), and realtime "
            "video (LiveKit/Daily)."
        ),
        unlocks="Live transcription, TTS, and realtime voice/video sessions.",
        how_to_approve=(
            "Owner confirms the chosen live voice/video provider(s) and "
            "records an explicit approval for this gate."
        ),
    ),
    Gate(
        gate_id="daedalus_live",
        label="Daedalus live approval",
        description=(
            "Live Daedalus reasoning: building a Daedalus engine against "
            "a real Anthropic key/model and generating source through it."
        ),
        unlocks="Live Daedalus engine builds and generations.",
        how_to_approve=(
            "Owner records an explicit approval for this gate (requires "
            "the Anthropic live model gate to be approved as well in "
            "practice, since Daedalus calls Claude)."
        ),
    ),
    Gate(
        gate_id="ai_role_workers",
        label="AI role workers approval",
        description=(
            "Live AI role workers: autonomous agents acting in named "
            "roles (PR #14 / codex/ai-role-workers scope) against real "
            "systems."
        ),
        unlocks="Running AI role workers against live systems.",
        how_to_approve=(
            "Owner reviews the role-worker scope and records an explicit "
            "approval for this gate."
        ),
    ),
)

GATE_IDS: tuple[str, ...] = tuple(g.gate_id for g in GATES)
_GATE_BY_ID: dict[str, Gate] = {g.gate_id: g for g in GATES}


class ApprovalRequiredError(ValueError):
    """Raised when live operation is attempted on an unapproved gate.

    A ``ValueError`` so existing ``except ValueError`` handling treats
    it as a configuration/usage failure, with an HTTP 503 attached for
    WSGI paths via :attr:`http_status`.
    """

    http_status = 503

    def __init__(self, gate_id: str, *, detail: str | None = None) -> None:
        gate = _GATE_BY_ID.get(gate_id)
        label = gate.label if gate is not None else gate_id
        message = (
            f"Live operation blocked: approval required for '{label}' "
            f"(gate '{gate_id}'). Status is UNAPPROVED — the owner has not "
            f"approved this platform and no verifier has returned True. "
            f"Record an explicit owner approval for this gate before "
            f"using it live."
        )
        if detail:
            message += f" {detail}"
        super().__init__(message)
        self.gate_id = gate_id
        self.status = UNAPPROVED


def _require_known_gate(gate_id: str) -> Gate:
    gate = _GATE_BY_ID.get(gate_id)
    if gate is None:
        raise ValueError(
            f"Unknown approval gate '{gate_id}'. Known gates: "
            f"{', '.join(GATE_IDS)}. Refusing to guess — no gate is "
            f"approved by default."
        )
    return gate


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_gate_state() -> dict[str, Any]:
    return {
        "status": UNAPPROVED,
        "approved_by": None,
        "approved_at": None,
        "method": None,
        "verifier": None,
        "note": None,
    }


def _default_state_dict() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "owner": OWNER,
        "created": "2026-11-13",
        "updated_at": None,
        "note": (
            "Initial state: every gate UNAPPROVED. No verifier has "
            "returned True for any gate. A gate flips to APPROVED only "
            "on an explicit owner approval for that specific gate, or a "
            "real verifier returning True."
        ),
        "gates": {gate.gate_id: _default_gate_state() for gate in GATES},
    }


@dataclass
class ApprovalStore:
    """In-memory approval state, backed by the JSON state file.

    Construct with :func:`load_store` (reads the file, or defaults when
    the file does not exist yet) or directly with ``ApprovalStore()``
    for an all-UNAPPROVED store — useful for tests. Direct
    construction never reads or writes disk.
    """

    path: Path | None = None
    _gates: dict[str, dict[str, Any]] = field(default_factory=dict)
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if not self._gates:
            self._gates = {
                gate.gate_id: _default_gate_state() for gate in GATES
            }

    # -- reads ---------------------------------------------------------
    def status(self, gate_id: str) -> str:
        _require_known_gate(gate_id)
        return str(self._gates[gate_id]["status"])

    def is_approved(self, gate_id: str) -> bool:
        return self.status(gate_id) == APPROVED

    def record(self, gate_id: str) -> dict[str, Any]:
        """Full stored record for one gate (a copy)."""
        _require_known_gate(gate_id)
        return dict(self._gates[gate_id])

    def checklist(self) -> list[dict[str, Any]]:
        """One row per gate: id, label, status, approver, method, note."""
        rows = []
        for gate in GATES:
            state = self._gates[gate.gate_id]
            rows.append(
                {
                    "gate": gate.gate_id,
                    "label": gate.label,
                    "status": state["status"],
                    "approved_by": state["approved_by"],
                    "approved_at": state["approved_at"],
                    "method": state["method"],
                    "verifier": state["verifier"],
                    "note": state["note"],
                    "unlocks": gate.unlocks,
                    "how_to_approve": gate.how_to_approve,
                }
            )
        return rows

    # -- writes --------------------------------------------------------
    def record_approval(
        self,
        gate_id: str,
        approver: str,
        *,
        note: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        """Record an explicit owner approval for one specific gate.

        Only the named gate flips; every other gate is untouched.
        ``approver`` must name the approver (the owner) — an empty
        approver is refused. Returns the stored record.
        """
        gate = _require_known_gate(gate_id)
        if not approver or not str(approver).strip():
            raise ValueError(
                f"Cannot approve gate '{gate_id}': an explicit approver "
                f"is required. Anonymous or blank approvals are refused."
            )
        now = at or _utcnow_iso()
        self._gates[gate.gate_id] = {
            "status": APPROVED,
            "approved_by": str(approver).strip(),
            "approved_at": now,
            "method": "owner_approval",
            "verifier": None,
            "note": note,
        }
        self.updated_at = now
        return dict(self._gates[gate.gate_id])

    def record_verifier_result(
        self,
        gate_id: str,
        passed: bool,
        *,
        verifier: str,
        note: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        """Record a real verifier result for one gate.

        The gate flips to APPROVED only when ``passed`` is True. A
        failed (or inconclusive) verifier result never flips a gate and
        never revokes an existing approval — it is recorded as a note
        on the gate's record instead.
        """
        gate = _require_known_gate(gate_id)
        if not verifier or not str(verifier).strip():
            raise ValueError(
                f"Cannot record a verifier result for gate '{gate_id}': "
                f"the verifier must be named."
            )
        now = at or _utcnow_iso()
        if passed is True:
            self._gates[gate.gate_id] = {
                "status": APPROVED,
                "approved_by": None,
                "approved_at": now,
                "method": "verifier",
                "verifier": str(verifier).strip(),
                "note": note,
            }
            self.updated_at = now
        else:
            state = self._gates[gate.gate_id]
            state["verifier"] = str(verifier).strip()
            state["note"] = note
            # Status, approver, and method are left exactly as they were.
        return dict(self._gates[gate.gate_id])

    def revoke(
        self, gate_id: str, *, note: str | None = None
    ) -> dict[str, Any]:
        """Return one gate to UNAPPROVED (owner decision)."""
        gate = _require_known_gate(gate_id)
        self._gates[gate.gate_id] = {
            "status": UNAPPROVED,
            "approved_by": None,
            "approved_at": None,
            "method": None,
            "verifier": None,
            "note": note,
        }
        self.updated_at = _utcnow_iso()
        return dict(self._gates[gate.gate_id])

    # -- persistence ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": STATE_VERSION,
            "owner": OWNER,
            "created": "2026-11-13",
            "updated_at": self.updated_at,
            "note": _default_state_dict()["note"],
            "gates": {
                gate.gate_id: dict(self._gates[gate.gate_id])
                for gate in GATES
            },
        }

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError(
                "No path to save approval state to: pass a path or load "
                "the store from a file first."
            )
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=False)
            handle.write("\n")
        self.path = target
        return target


def load_store(path: Path | str | None = None) -> ApprovalStore:
    """Load the approval store from ``path`` (default state file).

    A missing file yields an all-UNAPPROVED store — never an approved
    one. A corrupt file (bad JSON, wrong shape, unknown gate id, or a
    status other than APPROVED/UNAPPROVED) raises ``ValueError`` rather
    than silently defaulting: failing closed and loud beats guessing.
    """
    target = Path(path) if path is not None else DEFAULT_STATE_PATH
    if not target.exists():
        store = ApprovalStore(path=target)
        return store
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"Approval state file {target} is corrupt ({exc}); refusing "
            f"to guess approval state."
        ) from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("gates"), dict):
        raise ValueError(
            f"Approval state file {target} has the wrong shape; refusing "
            f"to guess approval state."
        )
    gates: dict[str, dict[str, Any]] = {}
    for gate in GATES:
        entry = raw["gates"].get(gate.gate_id)
        if entry is None:
            gates[gate.gate_id] = _default_gate_state()
            continue
        if not isinstance(entry, dict):
            raise ValueError(
                f"Approval state for gate '{gate.gate_id}' in {target} "
                f"has the wrong shape."
            )
        status = entry.get("status")
        if status not in (APPROVED, UNAPPROVED):
            raise ValueError(
                f"Approval state for gate '{gate.gate_id}' in {target} "
                f"has unknown status {status!r}; only APPROVED and "
                f"UNAPPROVED are valid."
            )
        state = _default_gate_state()
        state.update(
            {
                "status": status,
                "approved_by": entry.get("approved_by"),
                "approved_at": entry.get("approved_at"),
                "method": entry.get("method"),
                "verifier": entry.get("verifier"),
                "note": entry.get("note"),
            }
        )
        gates[gate.gate_id] = state
    unknown = sorted(set(raw["gates"]) - set(GATE_IDS))
    if unknown:
        raise ValueError(
            f"Approval state file {target} contains unknown gate(s): "
            f"{', '.join(unknown)}. Refusing to guess."
        )
    return ApprovalStore(
        path=target, _gates=gates, updated_at=raw.get("updated_at")
    )


def is_approved(gate_id: str, store: ApprovalStore | None = None) -> bool:
    """True only when the gate is APPROVED in the store (default file)."""
    return (store or load_store()).is_approved(gate_id)


def require_approval(
    gate_id: str, store: ApprovalStore | None = None
) -> None:
    """Raise :class:`ApprovalRequiredError` unless the gate is APPROVED.

    The single guard every live platform path calls before doing live
    work. ``store`` defaults to the on-disk state file.
    """
    _require_known_gate(gate_id)
    if not (store or load_store()).is_approved(gate_id):
        raise ApprovalRequiredError(gate_id)


def http_failure(
    gate_id: str, store: ApprovalStore | None = None
) -> dict[str, Any]:
    """Honest 503-style failure payload for an unapproved gate.

    For WSGI/HTTP paths that cannot raise: ``{"status": 503, ...}``
    naming the missing approval, instead of a fake success.
    """
    gate = _require_known_gate(gate_id)
    try:
        require_approval(gate_id, store=store)
    except ApprovalRequiredError as exc:
        return {
            "status": 503,
            "error": "approval_required",
            "gate": gate_id,
            "label": gate.label,
            "detail": str(exc),
        }
    return {"status": 200, "error": None, "gate": gate_id, "label": gate.label}


def check_live(
    gate_id: str, store: ApprovalStore | None = None
) -> tuple[bool, int, str]:
    """``(allowed, http_status, message)`` for a live attempt on a gate.

    ``(True, 200, ...)`` when approved, ``(False, 503, ...)`` naming
    the missing approval when not.
    """
    _require_known_gate(gate_id)
    active = store or load_store()
    if active.is_approved(gate_id):
        gate = _GATE_BY_ID[gate_id]
        return True, 200, f"Gate '{gate.label}' is APPROVED; live use allowed."
    try:
        require_approval(gate_id, store=active)
    except ApprovalRequiredError as exc:
        return False, 503, str(exc)
    return False, 503, f"Gate '{gate_id}' is UNAPPROVED."  # pragma: no cover


def guarded_call(
    gate_id: str,
    func: Callable[..., Any],
    *args: Any,
    store: ApprovalStore | None = None,
    **kwargs: Any,
) -> Any:
    """Call ``func`` only when ``gate_id`` is APPROVED; else raise.

    The generic wiring helper for live platform paths: the guard runs
    before ``func`` is even invoked, so no live work happens while
    the gate is UNAPPROVED.
    """
    require_approval(gate_id, store=store)
    return func(*args, **kwargs)


def guarded_grantwriter_generation(
    generator: Callable[..., Any],
    *args: Any,
    store: ApprovalStore | None = None,
    **kwargs: Any,
) -> Any:
    """Live grantwriter generation, gated on ``grantwriter_purpose``.

    ``app/grantwriter_mother.py`` currently has no live AI call of its
    own — it manages opportunities and narratives locally — so there
    is no in-place live path to gate there. This wrapper is the live
    entry point: it requires the grantwriter purpose approval, then
    delegates to the caller-supplied live ``generator``. Unapproved,
    it raises :class:`ApprovalRequiredError` before ``generator`` runs.
    """
    require_approval("grantwriter_purpose", store=store)
    return generator(*args, **kwargs)


def approval_checklist(
    store: ApprovalStore | None = None,
) -> list[dict[str, Any]]:
    """Per-gate approval checklist rows (see :meth:`ApprovalStore.checklist`)."""
    return (store or load_store()).checklist()


def render_checklist(store: ApprovalStore | None = None) -> str:
    """Human-readable per-platform approval checklist for the owner."""
    active = store or load_store()
    lines = [
        "Sanders Dash & Seal — AI platform approval checklist",
        f"Owner: {OWNER}",
        "A gate flips to APPROVED only on an explicit owner approval "
        "for that gate, or a real verifier returning True.",
        "Free resources first: use each platform's free tier / free "
        "resources before any paid service.",
        "",
    ]
    approved = 0
    for row in active.checklist():
        status = row["status"]
        if status == APPROVED:
            approved += 1
            by = row["approved_by"] or row["verifier"] or "?"
            lines.append(
                f"[APPROVED]   {row['label']} ({row['gate']}) — "
                f"via {row['method']} by {by}"
            )
        else:
            lines.append(
                f"[UNAPPROVED] {row['label']} ({row['gate']}) — "
                f"blocks: {row['unlocks']} "
                f"To approve: {row['how_to_approve']}"
            )
    lines.append("")
    lines.append(f"{approved}/{len(GATES)} gates approved.")
    if approved < len(GATES):
        lines.append(
            "Nothing above is approved by default. Live use of any "
            "UNAPPROVED platform fails honestly with HTTP 503 / "
            "ApprovalRequiredError naming the missing approval."
        )
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    """CLI: ``python -m core_platform.ai_platform_approval`` prints the checklist."""
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else None
    print(render_checklist(load_store(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
