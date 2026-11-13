"""Grantwriter (Mother): persistent grant opportunity and application management.

REBUILT NOT RESTORED — 2026-11-13.
==============================
Restoration was BLOCKED: no working source exists anywhere that could be
found. The only copy in the repo was added already truncated by commit
6be921d ("Add grantwriter_mother.py for grant management", 2026-11-02):
132 lines, SyntaxError at the old line 115, the file ends mid-statement,
and it calls functions that were never defined in any surviving copy
(own, mark_edited, audit, add_evidence) and imports a module that does
not exist anywhere in the repo (realtime_ai.runtime). Every copy of the
file in git history (all branches checked, including main f4f72abe and
deploy/simultaneous-20261113 4342b230) and on disk is byte-identical to
that truncated version. The P1 branch (commit b22dbc5) deleted the file
for the same reason ("truncated at birth, no compiling version in
history"). So this file is a rebuild, not a restoration.

Purpose — evidenced only by the surviving fragments, not invented:
  * The surviving docstring: "persistent grant opportunity and
    application management".
  * The adding commit's message: "managing grant opportunities and
    applications, including database initialization and cloud
    synchronization".
  * The surviving SQLite schema: opportunities, applications (with a
    draft narrative and optimistic-lock version), budget_lines, evidence
    and an audit trail.
  * The surviving PLATFORM identity: name "Grantwriter", nickname
    "Mother", NAICS codes 541611/541612/541613/541614/541618/541690, and
    a system instruction to operate in the Grantwriter service domain,
    use supplied evidence, and distinguish facts from uncertainty.
  * deploy/oracle/sanders_master_grid.json entry 9 also names it
    "Grantwriter" (nickname "GrantX" there — a discrepancy the owner
    should resolve; this module keeps "Mother", as in the code), role
    "Grant applications & oversight", port 3009.
  * No README, MASTER design document section, or other doc in the repo
    describes Grantwriter further. The MASTER doc contains zero
    mentions of "grant".

What was preserved verbatim from the surviving fragments:
  * The SQLite schema, the SANDERS_GRANTWRITER_DB environment variable,
    require_string / require_list validation, now(), database(), and
    synchronize_cloud_state() behaviour (OCI Instance Principals when
    the OCI SDK is present, otherwise an honest offline-ledger message).
  * The PLATFORM identity values above.

What was reconstructed (labelled, not presented as original):
  * money_cents(): the surviving condition was truncated mid-expression.
    Rebuilt as dollars -> integer cents, rejecting non-finite, negative,
    over-$100,000,000,000, or more-than-2-decimal-place values. The
    2-decimal-place rule is inferred from the cents conversion, not
    recovered from the original.
  * own() / mark_edited() / audit(): called by the surviving fragments
    but never defined. Rebuilt as owner-scoped row lookup (raises
    ValueError('not_found') for missing or other-owner rows),
    version-bump + updated_at on edit, and an audit-row insert.
  * add_evidence() / update_narrative(): completed from their surviving
    fragments (evidence insert + mark_edited + audit 'evidence_added';
    narrative update guarded by expected_version -> 'version_conflict').
    update_narrative() leaves status unchanged: the fragment's intended
    status value was lost in the truncation, so no status transition
    is invented.
  * create_opportunity() / create_application() / add_budget_line() /
    get_application() / list_opportunities() / list_applications() /
    list_audit(): minimal public API implied by the schema. New, not
    restored. No approval gates or approval statuses are introduced:
    applications stay 'draft' unless the caller changes status through
    the data layer, per the surviving system instruction.

Draft generation — pluggable, free-first:
  * The default generator is FakeGenerator: a deterministic offline
    template assembled only from the application's own stored facts
    (opportunity, budget, supplied evidence). No network, no key, no
    spend. Owner directive (2026-11-13): always use free resources
    first; live-model generation is opt-in only.
  * AnthropicGenerator / OpenAIGenerator are real adapters (stdlib
    urllib only, no new dependency). They fail honestly without a key
    (GrantwriterError, code '<provider>_not_configured') and need an
    explicit model (argument or ANTHROPIC_MODEL / OPENAI_MODEL env var)
    — no model is assumed, so no silent spend. They make no call at
    all until generate() is invoked with a key and a model.
  * generate_draft() records the draft in the audit trail
    ('draft_generated') and does NOT overwrite the stored narrative;
    save a draft with update_narrative() and the current version.

Google Docs export — documented optional adapter:
  * GoogleDocsExporter.export() needs a docs client object supplied by
    the caller (duck-typed: create_document(title=..., text=...) ->
    dict). With no client it raises GrantwriterError
    ('google_docs_not_configured') and makes no call. This module never
    reads credentials and never calls Google on its own; a live export
    needs owner approval and a connected Google Docs client. Tests use
    a fake client only.

No secrets are read, stored, or embedded here. No network call is made
except by the live-model adapters after the owner supplies a key.
"""

import datetime as dt
import hashlib
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Attempt to import OCI SDK for active, tokenless cloud state mapping
try:
    import oci

    HAS_OCI = True
except ImportError:  # pragma: no cover - environment dependent
    HAS_OCI = False

REBUILT_NOT_RESTORED = True


@dataclass(frozen=True)
class PlatformInfo:
    """Local stand-in for the Platform record the original imported from
    realtime_ai.runtime, a module that does not exist in this repo.
    Values are exactly those in the surviving fragment."""

    name: str
    nickname: str
    codes: tuple
    system_instruction: str


PLATFORM = PlatformInfo(
    name="Grantwriter",
    nickname="Mother",
    codes=("541611", "541612", "541613", "541614", "541618", "541690"),
    system_instruction=(
        "You are the Grantwriter real-time AI service (Mother). "
        "Operate within the Grantwriter service domain. Use supplied evidence "
        "and distinguish facts from uncertainty. Preserve your independent "
        "identity and inherited ecosystem security protocols. Do not introduce "
        "manual owner approval gates, approval statuses, or approval-dependent "
        "actions. Follow Core Laws 10 and 11: use only Oracle Always Free "
        "resources and actually use those resources in live operations."
    ),
)

_LOCK = threading.RLock()

# Tables own() is allowed to look up. The table name is never taken from
# untrusted input; anything else raises ValueError('invalid_table').
_OWNABLE_TABLES = ("opportunities", "applications")


class GrantwriterError(Exception):
    """Honest failure for unconfigured / unavailable optional adapters.

    ``code`` is a stable machine-readable string (e.g.
    'anthropic_not_configured', 'google_docs_not_configured').
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def database():
    """Initializes the secure data layer, optimized for Oracle Cloud operational boundaries."""
    path = Path(os.environ.get("SANDERS_GRANTWRITER_DB", "grantwriter.sqlite3")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS opportunities (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT NOT NULL,
          funder TEXT NOT NULL, source_url TEXT NOT NULL, deadline TEXT NOT NULL,
          ceiling_cents INTEGER NOT NULL, eligibility_json TEXT NOT NULL,
          requirements_json TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS applications (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL, opportunity_id TEXT NOT NULL,
          organization TEXT NOT NULL, project TEXT NOT NULL, narrative TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'draft', version INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(opportunity_id) REFERENCES opportunities(id));
        CREATE TABLE IF NOT EXISTS budget_lines (
          id TEXT PRIMARY KEY, application_id TEXT NOT NULL, category TEXT NOT NULL,
          description TEXT NOT NULL, amount_cents INTEGER NOT NULL,
          FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS evidence (
          id TEXT PRIMARY KEY, application_id TEXT NOT NULL, label TEXT NOT NULL,
          reference TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, entity TEXT NOT NULL,
          entity_id TEXT NOT NULL, action TEXT NOT NULL, timestamp TEXT NOT NULL,
          details_json TEXT NOT NULL);
        """)
    except BaseException:
        conn.close()
        raise
    return conn


def synchronize_cloud_state():
    """Autonomously replicates local transactions out to Oracle Object Storage via Instance Principals.

    Returns a status dict; never raises for a missing OCI SDK or a
    failed OCI call. REBUILT: return value added for testability; the
    printed messages and the offline fallback are as surviving.
    """
    if HAS_OCI:
        try:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            client = oci.object_storage.ObjectStorageClient({}, signer=signer)
            namespace = client.get_namespace().data
            print(f"[✅] Mother Node Cloud Backup Engaged: OCI Sovereign Namespace -> {namespace}")
            return {"oci_available": True, "status": "cloud_backup_engaged", "namespace": namespace}
        except Exception as exc:  # noqa: BLE001 - report, do not fail local work
            print("[*] Standing by for live runtime instance principal validation pass.")
            return {"oci_available": True, "status": "oci_unavailable", "error": str(exc)}
    print("[*] Running standalone offline database ledger.")
    return {"oci_available": False, "status": "standalone_offline"}


def require_string(body, key, limit=2000):
    value = body.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("invalid_" + key)
    return value.strip()


def require_list(body, key):
    value = body.get(key)
    if not isinstance(value, list) or len(value) > 100 or any(
        not isinstance(x, str) or len(x) > 1000 for x in value
    ):
        raise ValueError("invalid_" + key)
    return value


def money_cents(value):
    """Dollars (or a decimal string) -> integer cents.

    REBUILT: the surviving line was truncated mid-condition. Rejects
    non-finite, negative, over $100,000,000,000, or more-than-2-decimal-
    place values; the 2-decimal rule is inferred from the cents
    conversion, not recovered.
    """
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("invalid_amount") from None
    if not d.is_finite() or d < 0 or d > Decimal("100000000000") or d.as_tuple().exponent < -2:
        raise ValueError("invalid_amount")
    return int(d * 100)


def own(c, table, row_id, owner):
    """Owner-scoped row lookup. REBUILT (called but never defined in the
    surviving file). Raises ValueError('not_found') for a missing row or
    a row owned by someone else, so ownership is never leaked by the
    distinction. ``table`` must be one of _OWNABLE_TABLES."""
    if table not in _OWNABLE_TABLES:
        raise ValueError("invalid_table")
    row = c.execute(
        f"SELECT * FROM {table} WHERE id=? AND owner=?", (row_id, owner)  # noqa: S608 - table is allow-listed
    ).fetchone()
    if row is None:
        raise ValueError("not_found")
    return row


def audit(c, owner, entity, entity_id, action, details):
    """Append one audit-trail row. REBUILT (called but never defined in
    the surviving file). Returns the audit row id."""
    cur = c.execute(
        "INSERT INTO audit(owner, entity, entity_id, action, timestamp, details_json)"
        " VALUES(?,?,?,?,?,?)",
        (owner, entity, entity_id, action, now(), json.dumps(details or {})),
    )
    return cur.lastrowid


def mark_edited(c, application_id):
    """Bump an application's version and updated_at. REBUILT (called but
    never defined in the surviving file). Returns the new version."""
    c.execute(
        "UPDATE applications SET version=version+1, updated_at=? WHERE id=?",
        (now(), application_id),
    )
    row = c.execute("SELECT version FROM applications WHERE id=?", (application_id,)).fetchone()
    return row["version"] if row is not None else None


def create_opportunity(c, owner, body):
    """Create a grant opportunity. REBUILT (new; implied by the schema).
    Body: title, funder, source_url, deadline (strings), ceiling
    (dollars, via money_cents), eligibility and requirements (lists).
    Commits on success. Returns {'id': ...}."""
    title = require_string(body, "title")
    funder = require_string(body, "funder")
    source_url = require_string(body, "source_url")
    deadline = require_string(body, "deadline")
    ceiling_cents = money_cents(body.get("ceiling"))
    eligibility = require_list(body, "eligibility")
    requirements = require_list(body, "requirements")
    oid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            oid,
            owner,
            title,
            funder,
            source_url,
            deadline,
            ceiling_cents,
            json.dumps(eligibility),
            json.dumps(requirements),
            now(),
        ),
    )
    audit(c, owner, "opportunity", oid, "opportunity_created", {"title": title, "funder": funder})
    c.commit()
    return {"id": oid}


def create_application(c, owner, body):
    """Create a draft application against an opportunity the owner owns.
    REBUILT (new; implied by the schema). Body: opportunity_id,
    organization, project. Commits on success. Returns {'id': ...}."""
    opportunity = own(c, "opportunities", require_string(body, "opportunity_id", 40), owner)
    organization = require_string(body, "organization")
    project = require_string(body, "project")
    aid = str(uuid.uuid4())
    ts = now()
    c.execute(
        "INSERT INTO applications VALUES(?,?,?,?,?,?,?,?,?,?)",
        (aid, owner, opportunity["id"], organization, project, "", "draft", 1, ts, ts),
    )
    audit(
        c,
        owner,
        "application",
        aid,
        "application_created",
        {"opportunity_id": opportunity["id"], "organization": organization},
    )
    c.commit()
    return {"id": aid}


def add_budget_line(c, owner, body):
    """Add one budget line to an application the owner owns. REBUILT
    (new; implied by the schema). Body: application_id, category,
    description, amount (dollars). Commits on success."""
    app = own(c, "applications", require_string(body, "application_id", 40), owner)
    category = require_string(body, "category")
    description = require_string(body, "description")
    amount_cents = money_cents(body.get("amount"))
    lid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO budget_lines VALUES(?,?,?,?,?)",
        (lid, app["id"], category, description, amount_cents),
    )
    mark_edited(c, app["id"])
    audit(c, owner, "application", app["id"], "budget_line_added", {"budget_line_id": lid})
    c.commit()
    return {"id": lid}


def add_evidence(c, owner, body):
    """Attach one piece of evidence to an application the owner owns.

    Completed from the surviving fragment (evidence insert +
    mark_edited + audit 'evidence_added'). Body: application_id, label,
    reference, notes (max 4000 chars, per the surviving fragment).
    Commits on success. Returns {'id': ...}."""
    app = own(c, "applications", require_string(body, "application_id", 40), owner)
    label = require_string(body, "label")
    ref = require_string(body, "reference")
    notes = require_string(body, "notes", 4000)
    eid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO evidence VALUES(?,?,?,?,?,?)",
        (eid, app["id"], label, ref, notes, now()),
    )
    mark_edited(c, app["id"])
    audit(c, owner, "application", app["id"], "evidence_added", {"evidence_id": eid})
    c.commit()
    return {"id": eid}


def update_narrative(c, owner, body):
    """Replace an application's narrative under optimistic locking.

    Completed from the surviving fragment. Body: application_id,
    narrative (max 50000 chars), expected_version (int, must equal the
    current version or ValueError('version_conflict')). Status is left
    unchanged — the fragment's intended status value was lost, so none
    is invented. Commits on success. Returns {'id', 'version'}."""
    app = own(c, "applications", require_string(body, "application_id", 40), owner)
    narrative = require_string(body, "narrative", 50000)
    expected = body.get("expected_version")
    if type(expected) is not int or expected != app["version"]:
        raise ValueError("version_conflict")
    c.execute(
        "UPDATE applications SET narrative=?,version=version+1,updated_at=? WHERE id=?",
        (narrative, now(), app["id"]),
    )
    new_version = app["version"] + 1
    audit(
        c,
        owner,
        "application",
        app["id"],
        "narrative_updated",
        {"version": new_version},
    )
    c.commit()
    return {"id": app["id"], "version": new_version}


def _row_to_dict(row):
    return dict(row) if row is not None else None


def get_application(c, owner, application_id):
    """Full application view: application + opportunity + budget lines +
    evidence, all owner-scoped. REBUILT (new; read helper)."""
    app = own(c, "applications", application_id, owner)
    opportunity = _row_to_dict(
        c.execute("SELECT * FROM opportunities WHERE id=?", (app["opportunity_id"],)).fetchone()
    )
    if opportunity is not None:
        opportunity["eligibility"] = json.loads(opportunity["eligibility_json"])
        opportunity["requirements"] = json.loads(opportunity["requirements_json"])
    budget = [
        _row_to_dict(r)
        for r in c.execute(
            "SELECT * FROM budget_lines WHERE application_id=? ORDER BY rowid", (app["id"],)
        )
    ]
    evidence = [
        _row_to_dict(r)
        for r in c.execute(
            "SELECT * FROM evidence WHERE application_id=? ORDER BY created_at, id", (app["id"],)
        )
    ]
    result = _row_to_dict(app)
    result["opportunity"] = opportunity
    result["budget_lines"] = budget
    result["evidence"] = evidence
    return result


def list_opportunities(c, owner):
    """All opportunities owned by ``owner``, newest first. REBUILT."""
    rows = c.execute(
        "SELECT * FROM opportunities WHERE owner=? ORDER BY created_at DESC, id", (owner,)
    ).fetchall()
    out = []
    for row in rows:
        item = _row_to_dict(row)
        item["eligibility"] = json.loads(item["eligibility_json"])
        item["requirements"] = json.loads(item["requirements_json"])
        out.append(item)
    return out


def list_applications(c, owner, opportunity_id=None):
    """Applications owned by ``owner``, optionally for one opportunity.
    REBUILT."""
    if opportunity_id is None:
        rows = c.execute(
            "SELECT * FROM applications WHERE owner=? ORDER BY created_at DESC, id", (owner,)
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM applications WHERE owner=? AND opportunity_id=? ORDER BY created_at DESC, id",
            (owner, opportunity_id),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_audit(c, owner, entity_id=None):
    """Audit trail for ``owner``, oldest first. REBUILT."""
    if entity_id is None:
        rows = c.execute("SELECT * FROM audit WHERE owner=? ORDER BY id", (owner,)).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM audit WHERE owner=? AND entity_id=? ORDER BY id", (owner, entity_id)
        ).fetchall()
    out = []
    for row in rows:
        item = _row_to_dict(row)
        item["details"] = json.loads(item["details_json"])
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Draft generation (pluggable)
# ---------------------------------------------------------------------------


def build_draft_prompt(context):
    """Build the drafting prompt from stored facts. Pure function, no I/O.

    ``context`` is the dict returned by get_application(). The prompt
    instructs any generator to use only the supplied evidence and to
    mark anything not evidenced as unverified, per the PLATFORM
    instruction."""
    opp = context.get("opportunity") or {}
    budget_total_cents = sum(line.get("amount_cents", 0) for line in context.get("budget_lines", []))
    lines = [
        "Draft a grant application narrative using ONLY the facts below.",
        "Do not invent funders, amounts, dates, results, or credentials.",
        "Mark anything not backed by the supplied evidence as [UNVERIFIED].",
        "",
        f"Opportunity: {opp.get('title', '')}",
        f"Funder: {opp.get('funder', '')}",
        f"Source: {opp.get('source_url', '')}",
        f"Deadline: {opp.get('deadline', '')}",
        f"Funding ceiling (cents): {opp.get('ceiling_cents', '')}",
        f"Eligibility: {', '.join(opp.get('eligibility', []))}",
        f"Requirements: {', '.join(opp.get('requirements', []))}",
        "",
        f"Organization: {context.get('organization', '')}",
        f"Project: {context.get('project', '')}",
        f"Budget total (cents): {budget_total_cents}",
        "",
        "Supplied evidence:",
    ]
    for item in context.get("evidence", []):
        lines.append(f"- {item.get('label', '')}: {item.get('reference', '')} — {item.get('notes', '')}")
    if not context.get("evidence"):
        lines.append("- (none supplied)")
    lines.append("")
    lines.append("Budget lines:")
    for line in context.get("budget_lines", []):
        lines.append(
            f"- {line.get('category', '')}: {line.get('description', '')} "
            f"({line.get('amount_cents', 0)} cents)"
        )
    if not context.get("budget_lines"):
        lines.append("- (none supplied)")
    return "\n".join(lines)


class FakeGenerator:
    """Deterministic offline template generator. The default: free, no
    network, no key, no spend. Assembles a draft only from the stored
    facts and labels it as a template draft, with facts and gaps kept
    separate so nothing un-evidenced is presented as fact."""

    name = "fake_template"

    def generate(self, prompt, context):
        opp = context.get("opportunity") or {}
        total_cents = sum(line.get("amount_cents", 0) for line in context.get("budget_lines", []))
        parts = [
            "[TEMPLATE DRAFT — assembled offline from supplied facts only; "
            "not written by a live model]",
            "",
            f"Project: {context.get('project', '')}",
            f"Organization: {context.get('organization', '')}",
            f"Opportunity: {opp.get('title', '')} (funder: {opp.get('funder', '')})",
            f"Deadline: {opp.get('deadline', '')}",
            f"Funding ceiling: {opp.get('ceiling_cents', '')} cents; "
            f"budget total: {total_cents} cents.",
            "",
            "Facts (from supplied evidence):",
        ]
        if context.get("evidence"):
            for item in context["evidence"]:
                parts.append(
                    f"- {item.get('label', '')}: {item.get('reference', '')} — {item.get('notes', '')}"
                )
        else:
            parts.append("- No evidence has been supplied yet.")
        parts.append("")
        parts.append("Requirements to address:")
        for req in opp.get("requirements", []):
            parts.append(f"- {req}")
        parts.append("")
        parts.append(
            "Uncertainties / not yet evidenced: any claim not listed under "
            "'Facts' above is [UNVERIFIED] and must be evidenced before "
            "submission."
        )
        return "\n".join(parts)


def _http_json_post(url, payload, headers, timeout=30):
    """Minimal stdlib JSON POST. Raises GrantwriterError on HTTP/network
    failure; never logs or stores credentials beyond the request."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise GrantwriterError(
            "live_model_request_failed", f"live model request failed with HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GrantwriterError("live_model_unreachable", f"live model request failed: {exc.reason}") from exc


class AnthropicGenerator:
    """Real Anthropic adapter (stdlib urllib, no SDK dependency).

    Fails honestly without a key: generate() raises GrantwriterError
    ('anthropic_not_configured') if neither ``api_key`` nor the
    ANTHROPIC_API_KEY env var is set, and ('anthropic_model_not_
    configured') if neither ``model`` nor ANTHROPIC_MODEL is set. No
    call is made in either case. A key + model are the owner's opt-in;
    nothing here spends by default."""

    name = "anthropic"

    def __init__(self, model=None, api_key=None, timeout=30):
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or None
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or None
        self.timeout = timeout

    def generate(self, prompt, context):
        if not self.api_key:
            raise GrantwriterError(
                "anthropic_not_configured",
                "ANTHROPIC_API_KEY is not set; no live call was made. "
                "Set the key (owner approval required) or use FakeGenerator.",
            )
        if not self.model:
            raise GrantwriterError(
                "anthropic_model_not_configured",
                "No Anthropic model selected; pass model= or set ANTHROPIC_MODEL. "
                "No live call was made.",
            )
        data = _http_json_post(
            "https://api.anthropic.com/v1/messages",
            {
                "model": self.model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            timeout=self.timeout,
        )
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        if not text:
            raise GrantwriterError("anthropic_empty_response", "Anthropic returned no text.")
        return text


class OpenAIGenerator:
    """Real OpenAI adapter (stdlib urllib, no SDK dependency).

    Fails honestly without a key: generate() raises GrantwriterError
    ('openai_not_configured') if neither ``api_key`` nor OPENAI_API_KEY
    is set, and ('openai_model_not_configured') if neither ``model`` nor
    OPENAI_MODEL is set. No call is made in either case."""

    name = "openai"

    def __init__(self, model=None, api_key=None, timeout=30):
        self.model = model or os.environ.get("OPENAI_MODEL") or None
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or None
        self.timeout = timeout

    def generate(self, prompt, context):
        if not self.api_key:
            raise GrantwriterError(
                "openai_not_configured",
                "OPENAI_API_KEY is not set; no live call was made. "
                "Set the key (owner approval required) or use FakeGenerator.",
            )
        if not self.model:
            raise GrantwriterError(
                "openai_model_not_configured",
                "No OpenAI model selected; pass model= or set OPENAI_MODEL. "
                "No live call was made.",
            )
        data = _http_json_post(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Draft using only the supplied facts; mark anything "
                        "not evidenced as [UNVERIFIED]. Do not invent facts.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            {"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        choices = data.get("choices", [])
        if not choices:
            raise GrantwriterError("openai_empty_response", "OpenAI returned no choices.")
        text = (choices[0].get("message") or {}).get("content", "")
        if not text:
            raise GrantwriterError("openai_empty_response", "OpenAI returned no text.")
        return text


def generate_draft(c, owner, application_id, generator=None):
    """Generate a draft narrative for an application the owner owns.

    ``generator`` defaults to FakeGenerator() (free, offline). The
    draft is returned and recorded in the audit trail
    ('draft_generated', with generator name, evidence count, draft
    length and sha256); the stored narrative is NOT overwritten — save
    a draft with update_narrative() and the current version. Commits
    the audit row on success. Returns {'draft', 'generator',
    'evidence_count', 'application_id'}."""
    generator = generator or FakeGenerator()
    context = get_application(c, owner, application_id)
    prompt = build_draft_prompt(context)
    text = generator.generate(prompt, context)
    audit(
        c,
        owner,
        "application",
        context["id"],
        "draft_generated",
        {
            "generator": getattr(generator, "name", type(generator).__name__),
            "evidence_count": len(context.get("evidence", [])),
            "draft_chars": len(text),
            "draft_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    )
    c.commit()
    return {
        "draft": text,
        "generator": getattr(generator, "name", type(generator).__name__),
        "evidence_count": len(context.get("evidence", [])),
        "application_id": context["id"],
    }


# ---------------------------------------------------------------------------
# Google Docs export (documented optional adapter)
# ---------------------------------------------------------------------------


class GoogleDocsExporter:
    """Optional Google Docs export adapter.

    Usage: GoogleDocsExporter().export(draft_text, title, docs_client=...)
    where ``docs_client`` is supplied by the caller and implements
    create_document(title=..., text=...) -> dict (e.g. a thin wrapper
    around the Google Docs API, or a fake in tests). With no client,
    export() raises GrantwriterError ('google_docs_not_configured') and
    makes no call. This module never reads credentials, never opens a
    Google session, and never calls Google on its own: a live export
    needs owner approval and a caller-supplied, already-connected
    Google Docs client. The owner has Gmail/Docs connected, but that
    connection is not used here without approval.
    """

    name = "google_docs"

    def export(self, draft_text, title, docs_client=None):
        if docs_client is None:
            raise GrantwriterError(
                "google_docs_not_configured",
                "No Google Docs client supplied; no live call was made. "
                "Pass docs_client= (an already-connected Google Docs client) "
                "with owner approval, or use a fake client for testing.",
            )
        if not isinstance(draft_text, str) or not draft_text.strip():
            raise ValueError("invalid_draft_text")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("invalid_title")
        return docs_client.create_document(title=title.strip(), text=draft_text)


__all__ = [
    "REBUILT_NOT_RESTORED",
    "PLATFORM",
    "PlatformInfo",
    "GrantwriterError",
    "now",
    "database",
    "synchronize_cloud_state",
    "require_string",
    "require_list",
    "money_cents",
    "own",
    "audit",
    "mark_edited",
    "create_opportunity",
    "create_application",
    "add_budget_line",
    "add_evidence",
    "update_narrative",
    "get_application",
    "list_opportunities",
    "list_applications",
    "list_audit",
    "build_draft_prompt",
    "FakeGenerator",
    "AnthropicGenerator",
    "OpenAIGenerator",
    "generate_draft",
    "GoogleDocsExporter",
]
