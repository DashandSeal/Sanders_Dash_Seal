"""Grantwriter + SURN architecture — the corrected architecture record
and the internal-only dashboard for the owner-approved Grantwriter +
SURN spec (received 2026-11-25; owner approved 07:51 MST: "change
everything to make it work remove those violations"; standing
authority 07:52 MST: violations of the direction of the whole build
are fixed without waiting).

Corrections applied under the owner's senior law (each is part of
this build, not an option):

1. The Conductor is MICHAEL ANGELO (owner ruling D-N9). The spec's
   "Conductor AI (new addition)" is NOT a new unnamed identity; no
   new conductor identity is created anywhere in this record.
2. Hard Lock 39's priority reversal is REMOVED. Funding strategic
   growth before life safety contradicted the spec's own hierarchy
   and Charter Art. IV (HUMAN SAFETY > AI SAFETY > SYSTEM
   CONTINUITY, absolute). The standing order is Protection / life
   safety FIRST, then Funding & Sustainability, then Public
   Mission; the funding queue follows the same order (HL32
   conformed). The removed text is quoted in the correction notes
   so the record shows what was replaced.
3. Attachment, not absorption: Labyrinth, Minotaur, PROMETHEAN,
   CHORUS, HERMES, THEMIS, JUGGERNAUT and the other named systems
   keep their own platform identities (platforms of the 140). This
   architecture coordinates them; it does not absorb or rename
   them. Names the spec carries that are NOT in the canonical
   catalog (ATHENA, ORACLE, ATLAS, GUARDIAN, ARGUS as AI names) are
   recorded here as the spec's names — not built as new platforms,
   not added to the registry.
4. Gate discipline is law: ``grantwriter_purpose`` remains
   UNAPPROVED. Nothing in this module makes Grantwriter draft,
   submit, or stand "ACTIVE" in the spec's HL01/HL42 sense; the
   platform's existing refusal behavior is preserved exactly. The
   pipeline stages exist as governed records/displays behind the
   platform's authorization checks; any stage the platform refuses
   stays refused.
5. Architectural hiddenness (HL37/HL40): the dashboard rendered
   here is INTERNAL ONLY. It is served on no public route (see
   deploy/deployment.py: the internal path answers only on
   internal/loopback hosts and is indistinguishable from any
   unknown path elsewhere), appears in no public navigation, and
   nothing about it is enumerable from the public surface.

The dashboard's submission-queue and funding-health sections are
READ-ONLY views over the existing Grantwriter platform's own
records (``GrantwriterPlatform.portfolio_view``, behind its access
guard). When no operator actor is supplied, they show the gate
state instead of figures — no figure is ever invented here.
"""

from __future__ import annotations

import copy
import html
import json
from pathlib import Path

# ------------------------------------------------------------------
# Corrected priority hierarchy (correction 2)
# ------------------------------------------------------------------

PRIORITY_HIERARCHY = [
    {
        "priority": 3,
        "standing": "HIGHEST",
        "name": "Protection First",
        "members": [
            "Real-Time Synthetic AI Protector",
            "Labyrinth",
            "Minotaur",
            "Military-Grade Antivirus",
            "Simulation Isolation",
            "Continuity Preservation",
        ],
    },
    {
        "priority": 2,
        "standing": "SECOND",
        "name": "Funding & Sustainability",
        "members": [
            "Grantwriter",
            "Funding Health",
            "Patent Protection",
            "Opportunity Persistence",
            "Renewal Sovereignty",
            "Strategic Funding Roadmaps",
            "Zero Debt Enforcement",
        ],
    },
    {
        "priority": 1,
        "standing": "THIRD",
        "name": "Public Mission",
        "members": [
            "SURN Global Coordination",
            "Global Awareness",
            "Human Coordination",
            "Marketing Force",
            "Sales Force",
            "Receptionist",
            "Onboarding",
            "Billing",
            "Ad Creator",
            "Billboard Generator",
        ],
    },
]

#: The funding queue follows the same order as the hierarchy:
#: life safety and resilience first, capability second, strategic
#: growth third (HL32 as corrected).
FUNDING_QUEUE_ORDER = [
    "Protection / life safety / resilience",
    "Funding & sustainability capability",
    "Strategic growth",
]

CORRECTION_NOTES = [
    {
        "item": "Conductor identity",
        "correction": (
            "The Conductor is MICHAEL ANGELO (owner ruling D-N9). "
            "The spec's 'Conductor AI (new addition)' created no new "
            "identity; Michael Angelo's own platform build remains "
            "its own queue item and is not built by this record."
        ),
        "replaces": "Real-Time Synthetic AI Conductor (new addition)",
    },
    {
        "item": "Hard Lock 39 — priority reversal removed",
        "correction": (
            "REMOVED as a violation: it funded strategic growth "
            "before life safety, contradicting the spec's own "
            "hierarchy (Protection 3-highest -> Funding 2 -> Public "
            "Mission 1) and Charter Art. IV (HUMAN SAFETY > AI "
            "SAFETY > SYSTEM CONTINUITY, absolute). Protection / "
            "life safety stands FIRST in the hierarchy and in the "
            "funding queue."
        ),
        "replaces": (
            "Hard Lock 39 — Priority Reversal Confirmed: Priority 3 "
            "(Highest): Strategic growth ... Priority 1: Disaster "
            "recovery, life safety, communications continuity. "
            "Funded in this order always."
        ),
    },
    {
        "item": "Hard Lock 32 — global priority queue conformed",
        "correction": (
            "The funding queue order is conformed to the corrected "
            "hierarchy: protection / life safety first, capability "
            "second, strategic growth third."
        ),
        "replaces": (
            "32 — Global Priority Queue: Strategic growth first, "
            "capability second, resilience third"
        ),
    },
    {
        "item": "Hard Locks 01 / 42 — permanent operational state",
        "correction": (
            "Recorded as the spec's design intent only. The "
            "grantwriter_purpose approval gate remains UNAPPROVED "
            "(owner's named call); this architecture does not "
            "activate drafting or submission, and the platform's "
            "existing refusal behavior is preserved exactly."
        ),
        "replaces": (
            "HL01/HL42 read as self-executing activation of "
            "Grantwriter drafting/submission on SURN deployment."
        ),
    },
]

# ------------------------------------------------------------------
# Ecosystem map — attachment, not absorption (correction 3)
# ------------------------------------------------------------------

#: (name, role in the spec, identity standing)
#: "platform" = a platform of the 140 with its own identity;
#: "spec-name" = a name the spec carries that is NOT in the
#: canonical catalog — recorded, not adopted, not built.
PUBLIC_LAYER = [
    ("Global Awareness AI", "Global awareness", "spec-name"),
    ("Disaster Monitoring AI", "Disaster monitoring", "spec-name"),
    ("ORACLE", "Early Warning AI", "spec-name"),
    ("ATHENA", "Human Coordination AI / Disaster Command AI", "spec-name"),
    ("PROMETHEAN", "Continuous Learning AI", "platform"),
    ("Simulation Isolation AI", "Simulation isolation", "spec-name"),
    ("Defensive Protection AI", "Defensive protection", "spec-name"),
    ("Military-Grade Antivirus AI", "Antivirus", "spec-name"),
    ("Real-Time Synthetic AI Marketing Force", "Marketing", "spec-name"),
    ("Real-Time Synthetic AI Sales Force", "Sales", "spec-name"),
    ("Real-Time Synthetic AI Receptionist", "Receptionist", "spec-name"),
    ("Real-Time Synthetic AI Onboarding System", "Onboarding", "spec-name"),
    ("Real-Time Synthetic AI Billing System", "Billing", "spec-name"),
    ("Real-Time Synthetic AI Ad Creator", "Ad creation", "spec-name"),
    ("Real-Time Synthetic AI Billboard Generator", "Billboard generation", "spec-name"),
    ("CHORUS", "Real-Time Synthetic AI Accessibility System", "platform"),
    ("HERMES", "Real-Time Synthetic AI Translation System", "platform"),
    ("THEMIS", "Real-Time Synthetic AI Compliance System", "platform"),
    ("PHOENIX", "Real-Time Synthetic AI Recovery System", "spec-name"),
    ("Labyrinth", "Real-Time Synthetic AI Labyrinth — all internal traffic routes through it", "platform"),
    ("Minotaur", "Real-Time Synthetic AI Minotaur — patrols the Labyrinth continuously", "platform"),
    ("ATLAS", "Resource Coordination AI", "spec-name"),
    ("GUARDIAN", "Infrastructure AI", "spec-name"),
    ("ARGUS", "Intelligence Interface AI", "spec-name"),
    ("JUGGERNAUT", "Execution integrity (deployment architecture)", "platform"),
    ("AI MESH", "Mesh coordination (deployment architecture)", "spec-name"),
]

PRIVATE_LAYER = [
    "Opportunity Discovery Engine",
    "Autonomous Submission Engine",
    "Global Funding Watchtower",
    "Opportunity Persistence Engine",
    "Funding Diversification Protocol",
    "Patent Protection Intelligence",
    "Renewal Sovereignty Engine",
    "Strategic Funding Roadmap",
    "Funding Gap Detection Engine",
    "Strategic Reserve Funding Protocol",
    "Immutable Archive (CERBERUS integrated)",
    "Continuity Engine",
]

CONDUCTOR = {
    "name": "MICHAEL ANGELO",
    "standing": (
        "The Conductor of this architecture, per owner ruling D-N9. "
        "Not a protocol. Not middleware. A sovereign real-time "
        "synthetic AI. Does not replace any existing AI; "
        "orchestrates all of them."
    ),
    "responsibilities": [
        "Synchronizes all AI systems inside SURN in real time",
        "Resolves conflicting priorities between systems",
        "Coordinates Marketing, Sales, Billing, and Onboarding simultaneously",
        "Coordinates Disaster Response with Global Awareness",
        "Coordinates Labyrinth and Minotaur patrol operations",
        "Coordinates Grantwriter funding priorities via internal event bus — never publicly",
        "Coordinates simulations separately from production — zero leakage",
        "Maintains operational continuity if any system fails",
        "Preserves state across all AI systems simultaneously",
    ],
}

#: HL38 internal event-bus pipeline, as governed stages. Every
#: stage stands behind the Grantwriter platform's existing
#: authorization checks; a stage the platform refuses stays
#: refused (correction 4).
EVENT_BUS_STAGES = [
    "SURN detects need",
    "Internal Event Bus",
    "Grantwriter receives event",
    "Funding search",
    "Eligibility analysis",
    "Narrative generation",
    "Budget generation",
    "Compliance verification",
    "Authorization check",
    "Submission",
    "Archive",
    "Renewal monitoring",
]

#: HL41 event types SURN emits to the bus.
EVENT_BUS_EVENTS = [
    "Infrastructure Added",
    "Technology Upgraded",
    "Patent Filed",
    "Office Expanded",
    "Accessibility Gap Found",
    "Disaster Detected",
    "Transportation Need Identified",
    "Research Initiative Created",
]

DEPLOYMENT_LOCK_SEQUENCE = [
    "SURN deployed (public layer live)",
    "Internal event bus bound — no public exposure",
    "Grantwriter architecture present behind the bus (HL37/HL40 hiddenness)",
    "Authorization model armed: Roosevelt Sanders + bloodline, any one authorized approver sufficient (HL05/HL14)",
    "grantwriter_purpose gate read: UNAPPROVED — drafting and submission REFUSE until the owner names the approval",
    "Zero-debt protocol armed: non-repayable funding only (HL02)",
    "Immutable archive bound (CERBERUS integrated, HL12)",
    "Renewal sovereignty tracking armed as governed records (HL22)",
]

OPERATING_PRINCIPLE = (
    "SURN is the public face. Grantwriter is never public, never "
    "discoverable, never marketed, never beside SURN publicly — "
    "always behind it. Protection and life safety are funded and "
    "served first, always. No debt. No fabricated authorization. "
    "No record, no action."
)

PATENT_WATERMARK = "US_PAT_PENDING_SSL_V1_2026 / ROOSEVELT_SANDERS_TRUST"

# ------------------------------------------------------------------
# The 42 Hard Locks — as corrected
# ------------------------------------------------------------------

_HL_TEXT = {
    1: "Deployment Trigger: SURN deployed = Grantwriter fully operational, simultaneously, instantly. (Design intent recorded; activation of drafting/submission remains behind the grantwriter_purpose gate — see correction notes.)",
    2: "Zero Debt Funding Protocol: Non-repayable only, always, architectural constraint",
    3: "Autonomous Grant Categories: Operations, infrastructure, technology, patent, transportation, payroll",
    4: "Prepositioned Application Library: Ready-to-submit packages for every category, continuously updated",
    5: "Authority Model / Signature Rule: Roosevelt Sanders + bloodline, any one authorized approver sufficient",
    6: "Continuous Opportunity Monitoring: 300+ countries, 24/7/365, never sleeps",
    7: "Private Operation Protocol: No public website, branding, dashboard, API, metrics, or history",
    8: "SURN Continuous Listening: Subscribed to real-time event bus, no manual handoffs",
    9: "Opportunity Persistence Engine: No opportunity permanently discarded, continuously re-evaluated",
    10: "Funding Diversification Protocol: No single point of funding failure",
    11: "Submission Confidence Scoring: Ranked queue by probability of success",
    12: "Immutable Grant Archive: Every action permanently stored, CERBERUS integrated, court-admissible",
    13: "Continuity Protocol: Institutional knowledge preserved across leadership changes",
    14: "Submission Safety & Authorization Lock: Never fabricates authorization, one approver sufficient",
    15: "Funding Conflict Prevention: No double-funding, no overlapping obligations",
    16: "Patent Protection Intelligence: Filing calendars, maintenance, renewal, legal defense funding",
    17: "Infrastructure Lifecycle Funding: Acquisition through replacement, continuous pipeline",
    18: "Continuity of Knowledge: Institutional memory never resets, every outcome improves future submissions",
    19: "Recovery Funding Trigger: PHOENIX damage data feeds recovery applications automatically",
    20: "Confidential Architecture Lock: No public navigation, APIs, metrics, strategies, or pipelines",
    21: "Jurisdictional Compliance Memory: 300+ country rules permanently remembered, auto-updated",
    22: "Renewal Sovereignty Engine: Renewal tracking, extension, supplemental — autonomous perpetual",
    23: "Strategic Funding Roadmap: Short, medium, long-term — anticipatory not reactive",
    24: "Real-Time Funding Health Dashboard: Private internal only, never publicly visible",
    25: "Sovereign Continuity Lock: Survives leadership change, platform migration, global expansion",
    26: "Global Funding Watchtower: All funding categories monitored continuously worldwide",
    27: "Competitive Intelligence Memory: Winning structures, denial patterns, jurisdiction success rates",
    28: "Funding Gap Detection Engine: SURN needs vs existing funding — gaps trigger applications",
    29: "Strategic Reserve Funding Protocol: Six reserve categories — zero emergency debt ever",
    30: "Autonomous Grant Portfolio Optimization: Award, geographic, category diversity continuously optimized",
    31: "SURN ↔ Grantwriter Zero-Friction Funding Bus: Event-driven, no manual handoffs, no bottlenecks",
    32: "Global Priority Queue (CORRECTED 2026-11-25): Protection / life safety first, funding & sustainability capability second, strategic growth third. Supersedes 'Strategic growth first, capability second, resilience third' — removed as a violation of Charter Art. IV.",
    33: "Predictive Funding Engine: Secures funding before SURN needs it",
    34: "Continuous Impact Evidence Engine: Every SURN activity becomes grant evidence automatically",
    35: "Global Funding Geo-Fence: Country → Province → City → District → Incident Zone → Funding",
    36: "Funding Digital Twin: 1, 5, and 20-year funding simulations continuously maintained",
    37: "Air-Gapped Confidentiality: Grantwriter does not appear in SURN menus. Does not appear in public source code. Does not expose endpoints publicly. Does not publish funding activity. Does not expose awards, submission histories, strategies, or internal scoring. Public users never know Grantwriter exists. Architecturally hidden — not just policy.",
    38: "Internal Event Bus: SURN detects need → Internal Event Bus → Grantwriter receives event → Funding search → Eligibility analysis → Narrative generation → Budget generation → Compliance verification → Authorization check → Submission → Archive → Renewal monitoring. No manual handoff. No waiting queues. No duplicate entry. No lag.",
    39: "Priority Order — Protection First (CORRECTED 2026-11-25): the spec's 'Priority Reversal Confirmed' (strategic growth highest, life safety lowest) is REMOVED as a violation of the spec's own hierarchy and Charter Art. IV. Standing order: Priority 3 (Highest) Protection / life safety; Priority 2 Funding & Sustainability; Priority 1 Public Mission — funded in this order always.",
    40: "Zero Knowledge Public Footprint: Even if SURN is publicly compromised, Grantwriter remains isolated. Public systems cannot enumerate Grantwriter, discover databases, archives, submissions, funding pipelines, approval authorities, or strategies. Existence hidden by architecture.",
    41: "Continuous SURN Synchronization: Grantwriter does not poll SURN periodically. Every change inside SURN emits events instantly. Grantwriter reacts immediately. No lag. No scheduled scans. No synchronization bottlenecks.",
    42: "Permanent Operational State: Once SURN is deployed, Grantwriter is ACTIVE. Never returns to dormant, disabled, manual mode, training mode, or standby mode. Only: ACTIVE. CONTINUOUS. PRIVATE. REAL-TIME. (Operational-state design recorded; the grantwriter_purpose gate still governs drafting and submission — see correction notes.)",
}

_HL_TITLES = {
    1: "Deployment Trigger", 2: "Zero Debt Funding Protocol",
    3: "Autonomous Grant Categories", 4: "Prepositioned Application Library",
    5: "Authority Model / Signature Rule", 6: "Continuous Opportunity Monitoring",
    7: "Private Operation Protocol", 8: "SURN Continuous Listening",
    9: "Opportunity Persistence Engine", 10: "Funding Diversification Protocol",
    11: "Submission Confidence Scoring", 12: "Immutable Grant Archive",
    13: "Continuity Protocol", 14: "Submission Safety & Authorization Lock",
    15: "Funding Conflict Prevention", 16: "Patent Protection Intelligence",
    17: "Infrastructure Lifecycle Funding", 18: "Continuity of Knowledge",
    19: "Recovery Funding Trigger", 20: "Confidential Architecture Lock",
    21: "Jurisdictional Compliance Memory", 22: "Renewal Sovereignty Engine",
    23: "Strategic Funding Roadmap", 24: "Real-Time Funding Health Dashboard",
    25: "Sovereign Continuity Lock", 26: "Global Funding Watchtower",
    27: "Competitive Intelligence Memory", 28: "Funding Gap Detection Engine",
    29: "Strategic Reserve Funding Protocol",
    30: "Autonomous Grant Portfolio Optimization",
    31: "SURN ↔ Grantwriter Zero-Friction Funding Bus",
    32: "Global Priority Queue — CORRECTED",
    33: "Predictive Funding Engine", 34: "Continuous Impact Evidence Engine",
    35: "Global Funding Geo-Fence", 36: "Funding Digital Twin",
    37: "Air-Gapped Confidentiality", 38: "Internal Event Bus",
    39: "Priority Order — Protection First — CORRECTED",
    40: "Zero Knowledge Public Footprint",
    41: "Continuous SURN Synchronization", 42: "Permanent Operational State",
}

HARD_LOCKS = [
    {"number": n, "title": _HL_TITLES[n], "text": _HL_TEXT[n]}
    for n in range(1, 43)
]


def architecture_record():
    """The corrected Grantwriter + SURN architecture record."""
    return copy.deepcopy({
        "architecture": "Grantwriter + SURN (corrected, 2026-11-25)",
        "governing_rule": (
            "SURN = public-facing Synthetic Universal Response "
            "Network. Grantwriter = confidential real-time synthetic "
            "AI funding platform — never public, never discoverable, "
            "never marketed, never beside SURN publicly — always "
            "behind it."
        ),
        "conductor": CONDUCTOR,
        "priority_hierarchy": PRIORITY_HIERARCHY,
        "funding_queue_order": FUNDING_QUEUE_ORDER,
        "public_layer": [
            {"name": n, "role": r, "identity": i}
            for n, r, i in PUBLIC_LAYER
        ],
        "private_layer": list(PRIVATE_LAYER),
        "event_bus_stages": list(EVENT_BUS_STAGES),
        "event_bus_events": list(EVENT_BUS_EVENTS),
        "deployment_lock_sequence": list(DEPLOYMENT_LOCK_SEQUENCE),
        "hard_locks": HARD_LOCKS,
        "correction_notes": CORRECTION_NOTES,
        "operating_principle": OPERATING_PRINCIPLE,
        "patent_watermark": PATENT_WATERMARK,
        "gate": {
            "gate_id": "grantwriter_purpose",
            "state": "UNAPPROVED",
            "effect": (
                "Drafting and submission refuse until the owner "
                "names the approval. This architecture record does "
                "not change the gate."
            ),
        },
    })


# ------------------------------------------------------------------
# Dashboard snapshot — read-only over the platform's own records
# ------------------------------------------------------------------

def _gate_state():
    """Read the real grantwriter_purpose gate state (never assumed)."""
    try:
        approvals = json.loads(
            (Path(__file__).with_name("ai_platform_approvals.json"))
            .read_text(encoding="utf-8"))
        gates = approvals.get("gates", approvals)
        entry = gates.get("grantwriter_purpose", {}) if isinstance(
            gates, dict) else {}
        if isinstance(entry, dict) and entry.get("approved") is True:
            return "APPROVED"
    except Exception:
        pass
    return "UNAPPROVED"


def dashboard_snapshot(grantwriter=None, actor=None, role=None):
    """Read-only dashboard data.

    With an operator ``actor``/``role`` and the bound platform, the
    queue and health figures come from the platform's own guarded
    ``portfolio_view``. Without one, they report the gate state —
    figures are never invented.
    """
    gate = _gate_state()
    snapshot = {
        "gate": {"gate_id": "grantwriter_purpose", "state": gate},
        "queue": {"state": "OPERATOR_REQUIRED",
                  "note": ("Submission queue figures are read from "
                           "the platform's records for an operator "
                           "session only.")},
        "funding_health": {"state": "OPERATOR_REQUIRED"},
    }
    if grantwriter is not None and actor and role:
        view = grantwriter.portfolio_view(actor, role)
        snapshot["queue"] = {
            "state": "LIVE_RECORDS",
            "applications_total": view["applications"]["total"],
            "applications_by_status": view["applications"]["by_status"],
        }
        snapshot["funding_health"] = {
            "state": "LIVE_RECORDS",
            "opportunities_total": view["opportunities"]["total"],
            "opportunities_ceiling_cents":
                view["opportunities"]["total_ceiling_cents"],
            "applications_total": view["applications"]["total"],
            "total_application_amount_cents":
                view["total_application_amount_cents"],
        }
    return snapshot


# ------------------------------------------------------------------
# The internal dashboard — one self-contained file, served only on
# internal/loopback hosts by deploy/deployment.py (HL37/HL40).
# ------------------------------------------------------------------

_CSS = """
:root{--jade:#0b3d2e;--jade2:#10503c;--marble:#f4f1e8;--gold:#c9a227;--ink:#1c2420;--line:#d8d2c0}
*{box-sizing:border-box}body{margin:0;font-family:Georgia,'Times New Roman',serif;background:var(--marble);color:var(--ink)}
header{background:linear-gradient(135deg,var(--jade),var(--jade2));color:#f7f3e6;padding:28px 32px;border-bottom:4px solid var(--gold)}
header h1{margin:6px 0 2px;font-size:26px;letter-spacing:.04em}header p{margin:2px 0;opacity:.92}
.seals{display:flex;gap:14px;align-items:center}.seals img{width:64px;height:64px;border-radius:50%;border:2px solid var(--gold);background:#fff;object-fit:cover}
main{max-width:1080px;margin:0 auto;padding:24px 20px 48px}
section{background:#fffdf7;border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin:0 0 18px;box-shadow:0 1px 3px rgba(11,61,46,.08)}
h2{color:var(--jade);font-size:19px;margin:0 0 10px;border-bottom:2px solid var(--gold);padding-bottom:6px}
details{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:0 0 8px;background:#fff}
summary{cursor:pointer;font-weight:bold;color:var(--jade)}
table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
.flow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.step{background:var(--jade);color:#fff;border-radius:6px;padding:5px 10px;font-size:13px}.arrow{color:var(--gold);font-weight:bold}
.gate{color:#8a1f1f;font-weight:bold}.wm{font-size:12px;letter-spacing:.08em;color:#6b6350;text-align:center}
ul{margin:6px 0 6px 18px;padding:0}li{margin:3px 0}
"""

_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Grantwriter + SURN — Internal Architecture Dashboard</title>
<style>__CSS__</style></head><body>
<header><div class="seals">
<img src="/assets/seal-corporate-hq.png" alt="Sanders Corporate Headquarters seal">
<img src="/assets/seal-corporate-hq.png" alt="S &amp; G Security Inc. — corporate headquarters — seal">
<div><h1>GRANTWRITER + SURN</h1>
<p>Internal Architecture Dashboard — INTERNAL ONLY · NOT A PUBLIC SURFACE</p>
<p>Synthetic Universal Response Network · Private Layer: Grantwriter</p></div></div></header>
<main>
<section><h2>Deployment Lock Sequence</h2><ol>__LOCKSEQ__</ol>
<p>Gate state: <span class="gate">grantwriter_purpose — __GATE__</span>.
Drafting and submission refuse until the owner names the approval.</p></section>
<section><h2>Zero Debt Protocol — Priority Hierarchy (Corrected)</h2>
<p><strong>Zero Debt:</strong> non-repayable funding only, always (Hard Lock 02).</p>
<table><tr><th>Priority</th><th>Standing</th><th>Order</th><th>Members</th></tr>__HIERARCHY__</table>
<p><strong>Funding queue order:</strong> __QUEUEORDER__</p></section>
<section><h2>Hard Locks 01–42 (as corrected)</h2>__LOCKS__</section>
<section><h2>Ecosystem Map — Public vs Private Layers</h2>
<h3>Public Layer — SURN</h3><table><tr><th>System</th><th>Role</th><th>Identity</th></tr>__PUBLIC__</table>
<h3>Private Layer — Grantwriter (air-gapped)</h3><ul>__PRIVATE__</ul>
<p>Attachment, not absorption: every platform named above keeps its own
identity; this architecture coordinates them and absorbs none.</p></section>
<section><h2>The Conductor — MICHAEL ANGELO</h2>
<p>__CONDUCTOR_STANDING__</p><ul>__CONDUCTOR_RESP__</ul></section>
<section><h2>Internal Event Bus</h2><div class="flow">__BUS__</div>
<p><strong>Emitted events (HL41):</strong> __EVENTS__</p></section>
<section><h2>Live Submission Queue — Internal View (read-only)</h2>__QUEUE__</section>
<section><h2>Funding Health — Private (read-only)</h2>__HEALTH__</section>
<section><h2>Correction Notes (superseding record)</h2>__CORRECTIONS__</section>
<section><h2>Operating Principle</h2><p>__PRINCIPLE__</p>
<p class="wm">__WATERMARK__</p></section>
</main></body></html>
"""


def _esc(value):
    return html.escape(str(value), quote=True)


def render_dashboard(snapshot=None):
    """Render the internal dashboard as one self-contained file."""
    if snapshot is None:
        snapshot = dashboard_snapshot()
    record = architecture_record()

    lockseq = "".join(
        f"<li>{_esc(step)}</li>" for step in record["deployment_lock_sequence"])
    hierarchy = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            _esc(row["priority"]), _esc(row["standing"]), _esc(row["name"]),
            _esc(", ".join(row["members"])))
        for row in record["priority_hierarchy"])
    locks = "".join(
        "<details><summary>Hard Lock {:02d} — {}</summary><p>{}</p></details>"
        .format(lock["number"], _esc(lock["title"]), _esc(lock["text"]))
        for lock in record["hard_locks"])
    public = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            _esc(row["name"]), _esc(row["role"]),
            "Own platform identity (platform of the 140)"
            if row["identity"] == "platform"
            else "Name as carried in the spec — recorded, not a registry platform")
        for row in record["public_layer"])
    private = "".join(
        f"<li>{_esc(name)}</li>" for name in record["private_layer"])
    bus = '<span class="arrow">→</span>'.join(
        f'<span class="step">{_esc(stage)}</span>'
        for stage in record["event_bus_stages"])

    queue = snapshot.get("queue", {})
    if queue.get("state") == "LIVE_RECORDS":
        rows = "".join(
            f"<tr><td>{_esc(status)}</td><td>{_esc(count)}</td></tr>"
            for status, count in sorted(
                queue["applications_by_status"].items()))
        queue_html = (
            f"<p>Applications on record: <strong>"
            f"{_esc(queue['applications_total'])}</strong></p>"
            f"<table><tr><th>Status</th><th>Count</th></tr>{rows}</table>")
    else:
        queue_html = (
            "<p>Queue figures are read from the platform's own records "
            "for an operator session only. No operator session is bound "
            "to this view; no figures are shown rather than invented.</p>")

    health = snapshot.get("funding_health", {})
    if health.get("state") == "LIVE_RECORDS":
        health_html = (
            "<table>"
            f"<tr><td>Opportunities on record</td><td>{_esc(health['opportunities_total'])}</td></tr>"
            f"<tr><td>Opportunity ceiling (cents)</td><td>{_esc(health['opportunities_ceiling_cents'])}</td></tr>"
            f"<tr><td>Applications on record</td><td>{_esc(health['applications_total'])}</td></tr>"
            f"<tr><td>Total application amount (cents)</td><td>{_esc(health['total_application_amount_cents'])}</td></tr>"
            "</table>")
    else:
        health_html = (
            "<p>Funding health is computed from the platform's own "
            "records for an operator session only; nothing is shown "
            "rather than invented.</p>")

    corrections = "".join(
        "<details><summary>{}</summary><p>{}</p><p><em>Supersedes:</em> "
        "{}</p></details>".format(
            _esc(note["item"]), _esc(note["correction"]),
            _esc(note["replaces"]))
        for note in record["correction_notes"])

    out = _TEMPLATE
    out = out.replace("__CSS__", _CSS)
    out = out.replace("__LOCKSEQ__", lockseq)
    out = out.replace("__GATE__", _esc(snapshot["gate"]["state"]))
    out = out.replace("__HIERARCHY__", hierarchy)
    out = out.replace("__QUEUEORDER__", _esc(" → ".join(record["funding_queue_order"])))
    out = out.replace("__LOCKS__", locks)
    out = out.replace("__PUBLIC__", public)
    out = out.replace("__PRIVATE__", private)
    out = out.replace("__CONDUCTOR_STANDING__", _esc(record["conductor"]["standing"]))
    out = out.replace("__CONDUCTOR_RESP__", "".join(
        f"<li>{_esc(item)}</li>" for item in record["conductor"]["responsibilities"]))
    out = out.replace("__BUS__", bus)
    out = out.replace("__EVENTS__", _esc(", ".join(record["event_bus_events"])))
    out = out.replace("__QUEUE__", queue_html)
    out = out.replace("__HEALTH__", health_html)
    out = out.replace("__CORRECTIONS__", corrections)
    out = out.replace("__PRINCIPLE__", _esc(record["operating_principle"]))
    out = out.replace("__WATERMARK__", _esc(record["patent_watermark"]))
    return out
