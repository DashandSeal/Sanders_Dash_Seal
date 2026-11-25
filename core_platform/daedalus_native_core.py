"""Daedalus native reasoning core (founder-directed build, 2026-11-25).

Daedalus's own reasoning engine: deterministic, local, and native to
the Sanders Dash & Seal codebase. It makes no external network call,
imports no provider SDK, and reads no provider key or model id. Every
output is computed from its inputs and from the ecosystem's own
platform registry (``core_platform/ai_platform_links.json``) — never
canned, never fetched, never simulated.

Founder rulings carried by this module (2026-11-25):

- Native-only law: everything is native, not relying on other
  products; Daedalus's core may not be an outside model provider.
- Providers may exist only as optional, labeled, gated tools at his
  socket — never his mind and never a dependency. This core is the
  mind; the provider transports elsewhere in the tree are the tools.
- "L15 is reasoning": this core is the L15+ head capability, carried
  under its native identity ``live_native_reasoning`` (see
  ``core_platform/daedalus_l15_capabilities.py``).

Task classes genuinely implemented here (and only these):

1. **Planning / decomposition** — an objective is decomposed into
   components, steps, and dependencies computed from the objective
   text and the registry: platforms named in the objective become
   components whose steps are derived from their registry records
   (primary module, local modules, environment variables, endpoint,
   approval flag), and whose dependency edges are the registry's own
   reference graph, topologically ordered. The reference graph
   honors the records' own semantics: mentions inside the records'
   identity-care declarations (``distinct from`` / ``own platform —
   not …`` / roster enumerations and the like) declare that two
   platforms are *not* each other, so they are not counted as
   references. An objective naming no platform decomposes into its
   own clauses, in sequence.
2. **Registry-grounded synthesis** — questions about the ecosystem
   are answered by computation over the registry: platform records,
   counts under computed filters, term searches across every
   registry field, and reference-graph traversal (what a platform
   references, what references it). A question with no computed
   answer says so and shows the closest computed matches instead of
   inventing one.
3. **Deterministic source generation** — Python source computed
   from registry records and the objective: a service module in the
   codebase's established shape for a named platform, generated from
   that platform's own registry entry; or, for a named artifact with
   no registry entry, a module encoding the objective's computed
   decomposition. Every generated module is parse-checked with the
   standard-library AST parser before it is returned; unparseable
   output is refused, never returned.

Language honesty: the native core generates Python source only. A
request for another language raises ``ValueError`` naming the fact
instead of fabricating output in a language the core does not
implement.

Transport shape: :meth:`DaedalusNativeCore.generate` implements the
same call shape the Daedalus runtime integration already consumes
(``generate(system=..., user_message=..., max_tokens=...,
metadata=...)`` returning a response with ``text`` and
``latency_ms``), so evidence signing and persistence in
``daedalus_runtime_integration`` wrap this core unchanged.
``max_tokens`` is accepted for shape compatibility and otherwise
ignored: native outputs are bounded by construction, and truncating
computed source mid-stream would corrupt it. Token counts reported
on the response are whitespace-token counts of the actual inputs and
output — a deterministic local measure, not a provider meter.
Request and message ids are derived from a hash of the request
itself, so identical requests carry identical correlation ids.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

__all__ = [
    "CORE_ID",
    "HEAD_CAPABILITY",
    "LOGIC_LEVEL",
    "MODEL_ID",
    "DaedalusNativeCore",
    "NativeResponse",
    "build_native_transport",
    "core_declaration",
]

CORE_ID = "daedalus_native_core"
LOGIC_LEVEL = "L15+"
HEAD_CAPABILITY = "live_native_reasoning"
MODEL_ID = "daedalus-native-core"

_REGISTRY_PATH = Path(__file__).with_name("ai_platform_links.json")

_QUESTION_STARTERS = frozenset({
    "what", "which", "list", "describe", "how", "show", "name", "count",
})
_PLANNING_MARKERS = (
    "decompose", "roadmap", "break down", "breakdown", "sequence",
    "rollout", "implementation plan",
)
_STOPWORDS = frozenset({
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "that",
    "this", "is", "are", "was", "were", "be", "by", "and", "or", "it",
    "its", "as", "at", "from", "into", "does", "do", "me", "all",
    "platform", "platforms",
})
_VERB_LEXICON = (
    "audit", "build", "check", "compute", "connect", "create",
    "design", "generate", "implement", "monitor", "notify", "plan",
    "process", "protect", "record", "retrieve", "schedule", "sign",
    "store", "verify",
)
_ARTIFACT_VERBS = ("create", "build", "implement", "generate", "write", "make")
_ARTIFACT_TYPES = (
    "module", "service", "function", "class", "tool", "engine",
    "component", "platform",
)
# Segment markers for the registry records' identity-care language:
# a mention inside such a segment declares that two platforms are
# not each other, so it is not a reference (see _reference_graph).
_DISAMBIGUATION_MARKERS = (
    "distinct from", "separate from", "not merged", "nothing merged",
    "never merged", "own platform", "roster",
)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _first_sentence(text: str) -> str:
    stripped = " ".join(text.split())
    cut = stripped.find(". ")
    return stripped if cut < 0 else stripped[: cut + 1]


def _split_clauses(objective: str) -> list[str]:
    parts = re.split(r";|\band then\b|,\s*and\s+|\bthen\b", objective)
    return [part.strip(" ,") for part in parts if part.strip(" ,")]


@dataclass(frozen=True)
class NativeResponse:
    """The response shape the Daedalus runtime integration consumes.

    Field-for-field the same shape as the provider transports'
    response type, produced locally: ``model`` names this core,
    ``request_id`` / ``message_id`` are correlation ids derived from
    the request hash, ``latency_ms`` is the measured local compute
    time, and the token fields are whitespace-token counts.
    """

    model: str
    request_id: str | None
    message_id: str
    text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


class DaedalusNativeCore:
    """Deterministic native reasoning over the platform registry.

    The core is constructed over one registry snapshot (the ecosystem
    registry file by default, or a caller-supplied mapping / path).
    It holds no credentials, opens no sockets, and spawns nothing:
    its only inputs are the objective it is handed and the registry
    it was built over.
    """

    def __init__(
        self,
        registry: Mapping | None = None,
        *,
        registry_path: str | Path | None = None,
    ) -> None:
        if registry is None:
            path = Path(registry_path) if registry_path is not None else _REGISTRY_PATH
            registry = json.loads(path.read_text(encoding="utf-8"))
        platforms = registry.get("platforms")
        if not isinstance(platforms, list) or not platforms:
            raise ValueError("Registry carries no platform entries")
        self._entries: list[dict] = [dict(entry) for entry in platforms]
        self._by_id: dict[str, dict] = {}
        for entry in self._entries:
            self._by_id.setdefault(entry["id"], entry)
        if len(self._by_id) != len(self._entries):
            raise ValueError("Registry platform ids are not unique")
        self._search_text: dict[str, str] = {}
        for entry in self._entries:
            fields = [
                entry.get("id") or "", entry.get("name") or "",
                entry.get("description") or "", entry.get("provider") or "",
                entry.get("cost_tier") or "", entry.get("primary_module") or "",
                " ".join(entry.get("env_vars") or []),
                " ".join(entry.get("local_modules") or []),
                " ".join(entry.get("external_providers") or []),
            ]
            self._search_text[entry["id"]] = " ".join(fields).lower()
        self._out_edges, self._in_edges = self._reference_graph()

    # ------------------------------------------------------------------
    # Registry facts
    # ------------------------------------------------------------------

    @property
    def platform_count(self) -> int:
        return len(self._entries)

    def platform_ids(self) -> tuple[str, ...]:
        return tuple(entry["id"] for entry in self._entries)

    def entry(self, platform_id: str) -> dict:
        """Return a copy of one registry entry; KeyError if absent."""
        return dict(self._by_id[platform_id])

    def _reference_graph(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Reference edges computed from the registry's own records.

        Platform A references platform B when B's id or name appears
        in A's recorded name or description — excluding mentions
        inside the records' identity-care segments (marked by
        ``_DISAMBIGUATION_MARKERS``), which declare that A is *not*
        B and so state the opposite of a reference. Edge lists follow
        registry order so every traversal is deterministic.
        """
        out_edges: dict[str, list[str]] = {entry["id"]: [] for entry in self._entries}
        in_edges: dict[str, list[str]] = {entry["id"]: [] for entry in self._entries}
        for source in self._entries:
            raw = source.get("description", "") + " " + source.get("name", "")
            segments = re.split(r"(?<=[.;])\s+", raw)
            text = " ".join(
                segment for segment in segments
                if not any(
                    marker in segment.lower()
                    for marker in _DISAMBIGUATION_MARKERS
                )
            ).lower()
            for target in self._entries:
                if target["id"] == source["id"]:
                    continue
                tid = target["id"]
                if (
                    re.search(r"\b" + re.escape(tid) + r"\b", text)
                    or tid.replace("_", " ") in text
                    or target.get("name", "").lower() in text
                ):
                    out_edges[source["id"]].append(tid)
                    in_edges[tid].append(source["id"])
        return out_edges, in_edges

    def references(self, platform_id: str) -> list[str]:
        """Platform ids this platform's registry record references."""
        return list(self._out_edges[platform_id])

    def referenced_by(self, platform_id: str) -> list[str]:
        """Platform ids whose registry records reference this one."""
        return list(self._in_edges[platform_id])

    def match_platforms(self, objective: str) -> list[dict]:
        """Registry entries named by the objective, in registry order.

        A platform is named when its id (in underscore or spaced
        form) or its full recorded name appears in the objective.
        """
        text = objective.lower()
        matched = []
        for entry in self._entries:
            pid = entry["id"]
            if (
                re.search(r"\b" + re.escape(pid) + r"\b", text)
                or pid.replace("_", " ") in text
                or entry.get("name", "").lower() in text
            ):
                matched.append(entry)
        return matched

    # ------------------------------------------------------------------
    # Task classification
    # ------------------------------------------------------------------

    def classify(self, objective: str) -> str:
        """Classify an objective into one of the three task classes.

        Deterministic, in a fixed order: questions are synthesis;
        objectives carrying planning markers are planning; everything
        else is source generation (the shape the runtime's own call
        sites demand).
        """
        text = objective.strip()
        if not text:
            raise ValueError("Objective required")
        tokens = _words(text)
        first = tokens[0] if tokens else ""
        if text.endswith("?") or first in _QUESTION_STARTERS:
            return "synthesis"
        lowered = text.lower()
        if re.search(r"\bplan(ning|ned)?\b", lowered) or any(
            marker in lowered for marker in _PLANNING_MARKERS
        ):
            return "planning"
        return "source_generation"

    # ------------------------------------------------------------------
    # Class 1: planning / decomposition
    # ------------------------------------------------------------------

    def plan(self, objective: str) -> dict:
        """Decompose an objective into components, steps, dependencies.

        Components, steps, and edges are computed from the objective
        and the registry as described in the module docstring; the
        returned ``order`` is a dependency order over the components
        (registry order breaks ties; reference cycles are reported in
        ``cycles_broken`` and ordered by registry order, never hidden).
        """
        matched = self.match_platforms(objective)
        components: list[dict] = []
        cycles: list[str] = []
        if matched:
            matched_ids = [entry["id"] for entry in matched]
            for entry in matched:
                deps = [
                    ref for ref in self._out_edges[entry["id"]]
                    if ref in matched_ids and ref != entry["id"]
                ]
                steps = [
                    "Bind the primary module "
                    + str(entry.get("primary_module"))
                    + " recorded for this platform in the registry."
                ]
                for module in entry.get("local_modules") or []:
                    steps.append(
                        "Verify the local module is present and compiles: "
                        + str(module) + "."
                    )
                for var in entry.get("env_vars") or []:
                    steps.append(
                        "Configure environment variable " + str(var)
                        + " through the secure carrier path."
                    )
                if entry.get("endpoint"):
                    steps.append(
                        "Expose the platform surface at "
                        + str(entry["endpoint"])
                        + " and confirm its health route answers."
                    )
                providers = entry.get("external_providers") or []
                if providers:
                    steps.append(
                        "Account for the external providers recorded for "
                        "this platform (" + ", ".join(providers) + ") as "
                        "optional tools only; the reasoning core does not "
                        "depend on them."
                    )
                if entry.get("requires_owner_approval_for_live"):
                    steps.append(
                        "Confirm the owner approval flag "
                        + str(entry.get("approval_env"))
                        + " is set before live use."
                    )
                for dep in deps:
                    steps.append(
                        "Sequence after " + dep + ": this platform's "
                        "registry record references it."
                    )
                components.append({
                    "platform_id": entry["id"],
                    "name": entry.get("name", entry["id"]),
                    "steps": steps,
                    "depends_on": deps,
                })
            order, cycles = self._dependency_order(components)
        else:
            previous = None
            for index, clause in enumerate(_split_clauses(objective)):
                component_id = "clause_" + str(index + 1)
                components.append({
                    "platform_id": None,
                    "component": component_id,
                    "name": clause,
                    "steps": [
                        "Define the contract for: " + clause + ".",
                        "Implement the component for: " + clause + ".",
                        "Verify the component against the objective "
                        "clause: " + clause + ".",
                    ],
                    "depends_on": [previous] if previous else [],
                })
                previous = component_id
            order = [c["component"] for c in components]
        return {
            "objective": objective,
            "kind": "plan",
            "components": components,
            "order": order,
            "cycles_broken": cycles,
            "registry_platforms": len(self._entries),
        }

    @staticmethod
    def _dependency_order(
        components: list[dict],
    ) -> tuple[list[str], list[str]]:
        """Kahn ordering over component dependencies, registry order
        breaking ties; a reference cycle is broken at the registry-
        first remaining component and reported, never hidden."""
        remaining = {c["platform_id"]: c for c in components}
        emitted: list[str] = []
        cycles: list[str] = []
        while remaining:
            ready = [
                pid for pid, comp in remaining.items()
                if all(dep in emitted for dep in comp["depends_on"])
            ]
            if not ready:
                pid = next(iter(remaining))
                cycles.append(pid)
                ready = [pid]
            chosen = ready[0]
            emitted.append(chosen)
            del remaining[chosen]
        return emitted, cycles

    def render_plan(self, objective: str) -> str:
        """Render :meth:`plan` as an importable Python module."""
        plan = self.plan(objective)
        header = (
            '"""Implementation plan computed by the Daedalus native core.\n\n'
            "Objective: " + objective + "\n\n"
            "Decomposed deterministically from the objective and the "
            "platform\nregistry (" + str(len(self._entries)) + " platforms) "
            "at logic level " + LOGIC_LEVEL + ".\n"
            "No external provider produced this plan.\n"
            '"""\n'
        )
        text = (
            header
            + "from __future__ import annotations\n\n"
            + "PLAN = " + repr(plan) + "\n\n\n"
            + "def describe() -> dict:\n"
            + "    return PLAN\n"
        )
        self._require_parseable(text)
        return text

    # ------------------------------------------------------------------
    # Class 2: registry-grounded synthesis
    # ------------------------------------------------------------------

    def synthesize(self, objective: str) -> str:
        """Answer a question about the ecosystem from the registry.

        The answer is computed — from records, counts, field search,
        or the reference graph — and says exactly what was computed.
        """
        lowered = objective.lower()
        tokens = _words(objective)
        matched = self.match_platforms(objective)

        if matched and (
            "reference" in lowered or "depend" in lowered
        ):
            lines = []
            for entry in matched:
                pid = entry["id"]
                out = self._out_edges[pid]
                inc = self._in_edges[pid]
                lines.append(entry.get("name", pid) + " (" + pid + "):")
                lines.append(
                    "  references " + str(len(out)) + " platforms: "
                    + (", ".join(out) if out else "none recorded")
                )
                lines.append(
                    "  referenced by " + str(len(inc)) + " platforms: "
                    + (", ".join(inc) if inc else "none recorded")
                )
            return "\n".join(lines)

        if "how many" in lowered or (tokens and tokens[0] == "count"):
            return self._count_answer(objective, lowered, tokens, matched)

        if matched and not any(
            marker in lowered
            for marker in ("platform", "platforms", "which", "list")
        ):
            return self._describe_entry(matched[0])

        if tokens and tokens[0] in _QUESTION_STARTERS or "platform" in tokens:
            return self._search_answer(objective, tokens)

        if matched:
            return self._describe_entry(matched[0])
        return self._digest_answer(objective, tokens)

    def _count_answer(
        self,
        objective: str,
        lowered: str,
        tokens: list[str],
        matched: list[dict],
    ) -> str:
        if matched and "reference" in lowered:
            entry = matched[0]
            out = self._out_edges[entry["id"]]
            return (
                entry.get("name", entry["id"]) + " (" + entry["id"]
                + ") references " + str(len(out)) + " platforms: "
                + (", ".join(out) if out else "none recorded") + "."
            )
        for tier in ("free_first", "paid", "free"):
            if tier in tokens or tier in lowered:
                hits = [
                    e for e in self._entries if e.get("cost_tier") == tier
                ]
                return (
                    str(len(hits)) + " of " + str(len(self._entries))
                    + " platforms carry cost tier " + tier + ": "
                    + ", ".join(e["id"] for e in hits) + "."
                )
        providers = sorted({
            str(e.get("provider")) for e in self._entries if e.get("provider")
        })
        for provider in providers:
            if provider.lower() in tokens:
                hits = [
                    e for e in self._entries
                    if str(e.get("provider")).lower() == provider.lower()
                ]
                return (
                    str(len(hits)) + " of " + str(len(self._entries))
                    + " platforms record provider " + provider + ": "
                    + ", ".join(e["id"] for e in hits) + "."
                )
        tiers: dict[str, int] = {}
        for entry in self._entries:
            tier = str(entry.get("cost_tier"))
            tiers[tier] = tiers.get(tier, 0) + 1
        breakdown = ", ".join(
            tier + " " + str(tiers[tier]) for tier in sorted(tiers)
        )
        return (
            "The registry records " + str(len(self._entries))
            + " platforms. Cost tiers: " + breakdown + "."
        )

    def _search_answer(self, objective: str, tokens: list[str]) -> str:
        terms = [t for t in tokens if t not in _STOPWORDS]
        terms = [
            t for t in terms
            if t not in ("what", "which", "list", "show", "name",
                         "describe", "how", "many", "count")
        ]
        if terms:
            hits = [
                entry for entry in self._entries
                if all(term in self._search_text[entry["id"]] for term in terms)
            ]
            if hits:
                lines = [
                    str(len(hits)) + " platforms match "
                    + " + ".join(terms) + ":"
                ]
                for entry in hits:
                    lines.append(
                        "- " + entry["id"] + " (" + entry.get("name", "")
                        + ") — provider " + str(entry.get("provider"))
                        + ", cost tier " + str(entry.get("cost_tier"))
                    )
                return "\n".join(lines)
            scored = []
            for entry in self._entries:
                overlap = sum(
                    1 for term in terms
                    if term in self._search_text[entry["id"]]
                )
                if overlap:
                    scored.append((overlap, entry["id"]))
            scored.sort(key=lambda item: (-item[0], item[1]))
            closest = ", ".join(
                pid + " (" + str(score) + " of " + str(len(terms))
                + " terms)"
                for score, pid in scored[:3]
            )
            return (
                "No platform record matches all of: " + ", ".join(terms)
                + ". Searched " + str(len(self._entries)) + " registry "
                "records across id, name, description, provider, cost "
                "tier, modules, and environment variables. Closest "
                "computed matches: " + (closest if closest else "none") + "."
            )
        lines = ["The registry records " + str(len(self._entries)) + " platforms:"]
        for entry in self._entries:
            lines.append("- " + entry["id"] + " (" + entry.get("name", "") + ")")
        return "\n".join(lines)

    def _describe_entry(self, entry: dict) -> str:
        pid = entry["id"]
        out = self._out_edges[pid]
        inc = self._in_edges[pid]
        lines = [
            entry.get("name", pid) + " (" + pid + ")",
            "Description: " + str(entry.get("description", "")),
            "Provider: " + str(entry.get("provider"))
            + " | Cost tier: " + str(entry.get("cost_tier"))
            + " | Endpoint: " + str(entry.get("endpoint")),
            "Primary module: " + str(entry.get("primary_module")),
            "Local modules: "
            + (", ".join(entry.get("local_modules") or []) or "none recorded"),
            "Environment variables: "
            + (", ".join(entry.get("env_vars") or []) or "none recorded"),
            "External providers: "
            + (", ".join(entry.get("external_providers") or []) or "none recorded"),
            "Owner approval for live use: "
            + (
                "required (" + str(entry.get("approval_env")) + ")"
                if entry.get("requires_owner_approval_for_live")
                else "not required"
            ),
            "References: " + (", ".join(out) if out else "none recorded"),
            "Referenced by: " + (", ".join(inc) if inc else "none recorded"),
        ]
        return "\n".join(lines)

    def _digest_answer(self, objective: str, tokens: list[str]) -> str:
        tiers: dict[str, int] = {}
        providers: dict[str, int] = {}
        for entry in self._entries:
            tier = str(entry.get("cost_tier"))
            tiers[tier] = tiers.get(tier, 0) + 1
            provider = str(entry.get("provider"))
            providers[provider] = providers.get(provider, 0) + 1
        top_providers = sorted(
            providers.items(), key=lambda item: (-item[1], item[0])
        )[:5]
        return (
            "No registry record is named by that question, so no "
            "platform-specific answer is computed. Registry digest: "
            + str(len(self._entries)) + " platforms; cost tiers "
            + ", ".join(
                tier + " " + str(tiers[tier]) for tier in sorted(tiers)
            )
            + "; largest recorded providers "
            + ", ".join(name + " " + str(n) for name, n in top_providers)
            + ". Name a platform or a registry term and the answer is "
            "computed from its record."
        )

    # ------------------------------------------------------------------
    # Class 3: deterministic source generation
    # ------------------------------------------------------------------

    def generate_source(self, objective: str, *, language: str = "Python") -> str:
        """Generate Python source computed from the objective.

        A named platform yields its service module, generated from
        its own registry entry in the codebase's established service
        shape. Any other named artifact yields a module encoding the
        objective's computed decomposition. Non-Python requests are
        refused honestly (see the module docstring).
        """
        if language.strip().lower() != "python":
            raise ValueError(
                "The Daedalus native core generates Python source only "
                "(requested " + repr(language) + "); no external "
                "provider is used to cover other languages."
            )
        matched = self.match_platforms(objective)
        if matched:
            text = self._service_module(matched[0])
        else:
            text = self._artifact_module(objective)
        self._require_parseable(text)
        return text

    def _service_module(self, entry: dict) -> str:
        pid = entry["id"]
        name = str(entry.get("name", pid))
        class_name = "".join(
            part.capitalize() for part in pid.split("_") if part
        ) + "Service"
        doc_name = name.replace('"', "'")
        lines = [
            '"""' + doc_name + " service shell — generated by the "
            "Daedalus native core.",
            "",
            "Generated deterministically from the platform registry "
            "entry `" + pid + "`",
            "(core_platform/ai_platform_links.json) at logic level "
            + LOGIC_LEVEL + ", in the",
            "codebase's established service shape. No external provider "
            "produced",
            "this source.",
            '"""',
            "from __future__ import annotations",
            "",
            "import os",
            "from typing import Mapping",
            "",
            "PLATFORM_ID = " + repr(pid),
            "PLATFORM_NAME = " + repr(name),
            "DESCRIPTION = " + repr(str(entry.get("description", ""))),
            "PROVIDER = " + repr(entry.get("provider")),
            "ENDPOINT = " + repr(entry.get("endpoint")),
            "COST_TIER = " + repr(entry.get("cost_tier")),
            "PRIMARY_MODULE = " + repr(entry.get("primary_module")),
            "REQUIRED_ENV = " + repr(tuple(entry.get("env_vars") or ())),
            "LOCAL_MODULES = " + repr(tuple(entry.get("local_modules") or ())),
            "EXTERNAL_PROVIDERS = "
            + repr(tuple(entry.get("external_providers") or ())),
            "",
            "",
            "class " + class_name + ":",
            '    """Registry-grounded service shell for ' + doc_name + '."""',
            "",
            "    def __init__(self, env: Mapping[str, str] | None = None) -> None:",
            "        self.env = dict(os.environ if env is None else env)",
            "",
            "    def missing_configuration(self) -> tuple[str, ...]:",
            "        return tuple(",
            "            name for name in REQUIRED_ENV if not self.env.get(name)",
            "        )",
            "",
            "    def health(self) -> dict:",
            '        return {"platform": PLATFORM_ID, "status": "ok"}',
            "",
            "    def status(self) -> dict:",
            "        missing = self.missing_configuration()",
            "        return {",
            '            "platform": PLATFORM_ID,',
            '            "name": PLATFORM_NAME,',
            '            "configured": not missing,',
            '            "missing_env": list(missing),',
            '            "endpoint": ENDPOINT,',
            '            "cost_tier": COST_TIER,',
            "        }",
            "",
            "    def describe(self) -> dict:",
            "        return {",
            '            "platform": PLATFORM_ID,',
            '            "name": PLATFORM_NAME,',
            '            "description": DESCRIPTION,',
            '            "provider": PROVIDER,',
            '            "endpoint": ENDPOINT,',
            '            "cost_tier": COST_TIER,',
            '            "primary_module": PRIMARY_MODULE,',
            '            "local_modules": list(LOCAL_MODULES),',
            '            "external_providers": list(EXTERNAL_PROVIDERS),',
            "        }",
            "",
        ]
        return "\n".join(lines)

    def _artifact_module(self, objective: str) -> str:
        tokens = _words(objective)
        content = [
            token for token in tokens
            if token not in _STOPWORDS and token not in _ARTIFACT_VERBS
        ]
        slug_tokens = [
            token for token in content if token not in _ARTIFACT_TYPES
        ][:4]
        slug = "_".join(slug_tokens) if slug_tokens else "daedalus_generated"
        clauses = _split_clauses(objective)
        components = tuple(
            {
                "clause": clause,
                "verbs": [verb for verb in _VERB_LEXICON if verb in _words(clause)],
            }
            for clause in clauses
        )
        lines = [
            '"""Generated module for ' + slug + " — computed by the "
            "Daedalus native core.",
            "",
            "Objective: " + objective.replace('"', "'"),
            "",
            "The objective named no platform in the registry, so this "
            "module",
            "encodes the objective's computed decomposition: its "
            "clauses and the",
            "action verbs found in each. No external provider produced "
            "this source.",
            '"""',
            "from __future__ import annotations",
            "",
            "OBJECTIVE = " + repr(objective),
            "CLAUSES = " + repr(tuple(clauses)),
            "COMPONENTS = " + repr(components),
            "",
            "",
            "def spec() -> dict:",
            "    return {",
            '        "objective": OBJECTIVE,',
            '        "clauses": list(CLAUSES),',
            '        "components": [dict(component) for component in COMPONENTS],',
            "    }",
            "",
            "",
            "def main() -> None:",
            "    import json",
            "",
            "    print(json.dumps(spec(), indent=2))",
            "",
            "",
            'if __name__ == "__main__":',
            "    main()",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _require_parseable(text: str) -> None:
        """Symbolic validation: generated Python must parse.

        The core returns no source its own parser rejects. This is a
        deterministic check on the core's own output — it is not a
        claim about any other capability.
        """
        try:
            ast.parse(text)
        except SyntaxError as exc:
            raise RuntimeError(
                "Native core generated unparseable Python and refuses "
                "to return it: " + str(exc)
            ) from exc

    # ------------------------------------------------------------------
    # Transport face (the shape the runtime integration consumes)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_user_message(user_message: str) -> tuple[str, str]:
        match = re.match(
            r"Language:\s*(?P<language>[^\n]+)\nObjective:\n(?P<objective>.*)\Z",
            user_message,
            re.DOTALL,
        )
        if match:
            return match.group("language").strip(), match.group("objective").strip()
        return "Python", user_message.strip()

    def generate(
        self,
        *,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        metadata: dict[str, str] | None = None,
    ) -> NativeResponse:
        """Compute a response locally, in the runtime's call shape.

        The objective is routed by :meth:`classify` to the planning,
        synthesis, or source-generation class and computed there.
        ``max_tokens`` is accepted for shape compatibility (see the
        module docstring) and ``metadata`` is accepted and unused —
        correlation ids derive from the request itself.
        """
        started = time.perf_counter()
        language, objective = self._parse_user_message(user_message)
        if not objective:
            raise ValueError("Objective required")
        kind = self.classify(objective)
        if kind == "planning":
            text = self.render_plan(objective)
        elif kind == "synthesis":
            text = self.synthesize(objective)
        else:
            text = self.generate_source(objective, language=language)
        latency_ms = int((time.perf_counter() - started) * 1000)
        digest = hashlib.sha256(
            (system + "\x00" + user_message).encode("utf-8")
        ).hexdigest()
        return NativeResponse(
            model=MODEL_ID,
            request_id="native-" + digest[:24],
            message_id="native-" + digest[24:48],
            text=text,
            latency_ms=latency_ms,
            input_tokens=len((system + " " + user_message).split()),
            output_tokens=len(text.split()),
        )

    def declaration(self) -> dict:
        """This core's own declaration, stated factually."""
        return {
            "core": CORE_ID,
            "logic_level": LOGIC_LEVEL,
            "head_capability": HEAD_CAPABILITY,
            "task_classes": ["planning", "synthesis", "source_generation"],
            "registry_platforms": len(self._entries),
            "external_network_calls": "none",
            "provider_sdks_imported": "none",
            "provider_keys_required": "none",
        }


def build_native_transport(
    registry_path: str | Path | None = None,
) -> DaedalusNativeCore:
    """Build the native core in its transport role.

    Mirrors the role ``build_transport`` plays for the provider tool
    plugs: the engine's default builder returns this core, and the
    runtime integration consumes it through the same ``generate``
    call shape.
    """
    return DaedalusNativeCore(registry_path=registry_path)


def core_declaration() -> dict:
    """Declaration of the native core over the live registry."""
    return DaedalusNativeCore().declaration()
