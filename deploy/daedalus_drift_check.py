#!/usr/bin/env python3
"""Daedalus baseline drift check — read-only, post-deploy.

Compares every file in Daedalus's Minotaur patrol set against the
SHA-256 baselines pinned in the production protection state
(``data/daedalus_protection_state.json``) and reports each target
MATCH / DIFF / MISSING by name.

Why this exists (2026-11-26/27 incident): baselines were pinned at
2026-11-26T00:23:42Z; a routine deploy later that day changed one
patrolled file (``core_platform/ai_platform_links.json``). From that
moment ``DaedalusProtection.require_intact()`` raised
``DaedalusTamperError`` on every call and the five protection-gated
Daedalus capabilities read "unavailable" — silently, for a day. The
protection layer behaved exactly as designed (fail closed); what
was missing was a loud signal at deploy time. This check is that
signal: the master-deploy workflow runs it after every deploy, and
drift fails the deploy visibly instead of darkening capabilities
without a word.

The check is READ-ONLY. It never constructs DaedalusProtection,
never pins, never writes state. Re-pinning baselines is a separate,
deliberate operator act (the "Daedalus baseline re-pin (operator,
deliberate)" workflow) — whether a deploy may ever re-pin
automatically is a Founder policy question, open as of 2026-11-27;
the interim default is deliberate-only.

Usage:
    python3 deploy/daedalus_drift_check.py [--root DIR] [--state FILE]

Exit codes: 0 = every patrolled target matches its pinned baseline
(or no baselines are pinned yet — the first gated operation pins
them, which is the protection layer's own initialize-on-start
behavior, reported here as a notice, not drift). 1 = drift: at
least one target DIFFs or is MISSING. 2 = the state file exists but
cannot be read or parsed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Daedalus's patrol set, repository-relative. This list mirrors
# PATROL_TARGETS in core_platform/daedalus_protection.py exactly;
# tests/test_daedalus_baseline_drift.py asserts the two never drift
# apart (a patrol set changed in one place only would make this
# check patrol the wrong files).
TARGETS = (
    "core_platform/daedalus_native_core.py",
    "core_platform/daedalus_protection.py",
    "core_platform/daedalus_l15_capabilities.py",
    "core_platform/daedalus_knowledge_store.py",
    "core_platform/daedalus_engine.py",
    "core_platform/ai_platform_links.json",
    "labyrinth_shield.py",
    "minotaur_sentinel.py",
)

STATE_FILE_NAME = "daedalus_protection_state.json"


def hash_target(path: Path) -> str:
    """SHA-256 of a target's exact bytes ("FILE_MISSING" if absent).

    Identical to MinotaurSentinel.compute_target_hash, which is
    what DaedalusProtection._hash_target compares against the
    pinned baselines.
    """
    if not path.exists():
        return "FILE_MISSING"
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def check(root: Path, state_path: Path) -> tuple[int, list[str]]:
    """Run the comparison. Returns (exit_code, output_lines)."""
    lines: list[str] = []
    if not state_path.exists():
        lines.append(
            "DAEDALUS DRIFT CHECK: NOTICE — no protection state file at "
            + str(state_path)
            + "; no baselines are pinned yet. The first protection-gated "
            "operation pins them (initialize-on-start). Nothing to compare."
        )
        return 0, lines
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        lines.append(
            "DAEDALUS DRIFT CHECK: ERROR — protection state file "
            + str(state_path)
            + " could not be read ("
            + type(exc).__name__
            + "). The drift check cannot verify the patrol set."
        )
        return 2, lines
    baselines = state.get("baselines") or {}
    if not baselines:
        lines.append(
            "DAEDALUS DRIFT CHECK: NOTICE — protection state holds no "
            "pinned baselines yet. The first protection-gated operation "
            "pins them (initialize-on-start). Nothing to compare."
        )
        return 0, lines
    lines.append(
        "DAEDALUS DRIFT CHECK: baselines pinned at "
        + str(state.get("baseline_pinned_at"))
        + " — comparing "
        + str(len(TARGETS))
        + " patrolled targets."
    )
    drifted: list[str] = []
    for rel in TARGETS:
        current = hash_target(root / rel)
        pinned = baselines.get(rel)
        if pinned is None:
            verdict = "NOPIN"
            drifted.append(rel + " (no baseline pinned)")
        elif current == "FILE_MISSING":
            verdict = "MISSING"
            drifted.append(rel + " (file missing)")
        elif current != pinned:
            verdict = "DIFF"
            drifted.append(rel + " (differs from pinned baseline)")
        else:
            verdict = "MATCH"
        lines.append("BASELINE " + rel + " " + verdict)
    if drifted:
        lines.append(
            "DAEDALUS BASELINE DRIFT DETECTED: "
            + "; ".join(drifted)
            + ". The protection-gated Daedalus capabilities will read "
            "unavailable until an operator deliberately re-pins the "
            "baselines (Actions: 'Daedalus baseline re-pin (operator, "
            "deliberate)'). Re-pinning is never automatic."
        )
        return 1, lines
    lines.append(
        "DAEDALUS DRIFT CHECK: OK — all "
        + str(len(TARGETS))
        + " patrolled targets match their pinned baselines."
    )
    return 0, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Daedalus baseline drift check."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="repository root the patrolled targets resolve against "
        "(default: the parent of this script's directory)",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="protection state file (default: <root>/data/"
        + STATE_FILE_NAME
        + ")",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    state_path = (
        Path(args.state) if args.state else root / "data" / STATE_FILE_NAME
    )
    code, lines = check(root, state_path)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
