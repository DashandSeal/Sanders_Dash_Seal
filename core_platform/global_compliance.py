"""Global compliance for Sanders Dash & Seal (added 2026-11-13).

Compliance & law by jurisdiction, consent, data-subject requests, and
accessibility checks. Stdlib only. No network calls, no keys, no live
provider calls, no legal advice.

Honesty rules enforced by this module:

- No jurisdiction is approved for RON / notarial acts by default.
  ``APPROVED_RON_JURISDICTIONS`` is empty and gating is fail-closed:
  anything not explicitly approved by the owner raises
  ``NotApprovedInJurisdiction`` (error code
  ``NOT_APPROVED_IN_JURISDICTION``). Approval is an owner decision,
  recorded here only when the owner names a jurisdiction; this module
  never approves one on its own.
- No compliance certification, licence, or legal authority is claimed
  anywhere in this module. The jurisdiction registry records only what
  the repo actually does (see the audit in
  ``docs/global-compliance-20261113.md``) plus declared gaps.
- Deletion is honest: a delete request is *recorded*, and per-store
  results say ``DELETED`` only when a store adapter actually deleted
  records, otherwise ``NOT_IMPLEMENTED``. Nothing here can delete
  records from systems this code cannot reach (provider dashboards,
  backups, third-party notary platforms).
- Accessibility results are evidence-based: a checklist item is
  ``pass`` / ``fail`` only when evidence was supplied; otherwise it is
  ``not_checked``. This module does not claim WCAG conformance for any
  page; a real accessibility audit is still a declared gap.

Related, pre-existing repo behaviour this module does NOT change:

- ``core_platform/appointments.py`` accepts jurisdictions ``CO`` and
  ``WY`` for appointment *requests* (an appointment request is not a
  notarization). ``core_platform/cases.py`` accepts any
  identifier-shaped jurisdiction string for case records.
- ``core_platform/authority_review.py`` maps services to providers
  (``MOBILE_NOTARY`` -> Navu, ``E_NOTARY`` -> Signwell, ``RON`` ->
  BlueNotary) for human authority review; it performs no provider
  call and grants no jurisdiction.
- ``core_platform/daedalus_geofence.py`` enforces geographic policy
  only when the trusted runtime supplies an attestation; it does not
  decide notarial authority.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

__all__ = [
    "APPROVED_RON_JURISDICTIONS",
    "JURISDICTIONS",
    "ConsentRecord",
    "ConsentStore",
    "DataSubjectRequestHandler",
    "InMemoryRecordStore",
    "JurisdictionRule",
    "NotApprovedInJurisdiction",
    "WCAG_CHECKLIST",
    "AccessibilityChecklist",
    "check_html_accessibility",
    "gate_ron",
    "jurisdiction_status",
    "utcnow_iso",
]


def utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string. All timestamps here are UTC."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Jurisdiction registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class JurisdictionRule:
    """One jurisdiction's recorded compliance position.

    ``status`` is one of:
    - ``implemented`` — the repo demonstrably enforces this today.
    - ``declared_gap`` — the repo does not do this; no claim is made.
    - ``needs_owner_approval`` — an owner / legal-counsel decision is
      required before anything may proceed (all RON/notarial acts).
    ``privacy_regime`` / ``data_residency`` describe the rule that
    *would* apply; they are not a claim that the platform complies.
    """
    code: str
    name: str
    data_residency: str
    privacy_regime: str
    ron_status: str
    status: str
    notes: str = ""


# Jurisdictions named in the repo (MASTER design doc, appointments,
# web copy). "WY" is Wyoming, which appointments.py accepts; the MASTER
# doc names Wisconsin ("WI") instead — that mismatch is a declared gap
# in the audit doc, not resolved here.
JURISDICTIONS: Dict[str, JurisdictionRule] = {
    "CO": JurisdictionRule(
        code="CO",
        name="Colorado, US",
        data_residency="US only; primary region us-phoenix-1 (Oracle Always Free). No data-residency enforcement in code.",
        privacy_regime="US state law; no GDPR/CCPA-style regime implemented. No privacy policy page exists in the repo.",
        ron_status="needs_owner_approval",
        status="needs_owner_approval",
        notes="MASTER doc lists Colorado notarial operations as a current authority track. Appointments accept CO. RON is NOT approved.",
    ),
    "WI": JurisdictionRule(
        code="WI",
        name="Wisconsin, US",
        data_residency="US only; primary region us-phoenix-1 (Oracle Always Free). No data-residency enforcement in code.",
        privacy_regime="US state law; no GDPR/CCPA-style regime implemented. No privacy policy page exists in the repo.",
        ron_status="needs_owner_approval",
        status="needs_owner_approval",
        notes="MASTER doc lists Wisconsin notarial operations 'upon commission approval'. No commission verification is wired to this module.",
    ),
    "WY": JurisdictionRule(
        code="WY",
        name="Wyoming, US",
        data_residency="US only; primary region us-phoenix-1 (Oracle Always Free). No data-residency enforcement in code.",
        privacy_regime="US state law; no GDPR/CCPA-style regime implemented.",
        ron_status="needs_owner_approval",
        status="declared_gap",
        notes="Accepted by core_platform/appointments.py but NOT named in the MASTER doc (which names Wisconsin). Mismatch needs owner clarification; RON is NOT approved.",
    ),
    "FL": JurisdictionRule(
        code="FL",
        name="Florida, US",
        data_residency="US only; primary region us-phoenix-1 (Oracle Always Free). No data-residency enforcement in code.",
        privacy_regime="US state law; no GDPR/CCPA-style regime implemented.",
        ron_status="needs_owner_approval",
        status="needs_owner_approval",
        notes="MASTER doc lists Florida Commissioner of Deeds work 'upon completion of that authority path'. That path is not complete; RON is NOT approved.",
    ),
    "US": JurisdictionRule(
        code="US",
        name="United States (federal / other states)",
        data_residency="US only; primary region us-phoenix-1 (Oracle Always Free). No data-residency enforcement in code.",
        privacy_regime="US state law; no GDPR/CCPA-style regime implemented. No privacy policy page exists in the repo.",
        ron_status="needs_owner_approval",
        status="declared_gap",
        notes="Catch-all for US jurisdictions not listed above. No per-state notarial rules exist in code.",
    ),
    "EEA": JurisdictionRule(
        code="EEA",
        name="European Economic Area",
        data_residency="EEA residency required — NOT_IMPLEMENTED. No EEA region is deployed; the only deployment region is us-phoenix-1.",
        privacy_regime="GDPR-style rules would apply; no GDPR implementation exists in the repo (no consent store, export, or deletion flow before this module).",
        ron_status="needs_owner_approval",
        status="declared_gap",
        notes="No EEA data residency, no EU representative, no GDPR handling. Do not offer notarial services in the EEA.",
    ),
    "UK": JurisdictionRule(
        code="UK",
        name="United Kingdom",
        data_residency="UK residency required — NOT_IMPLEMENTED. No UK region is deployed; the only deployment region is us-phoenix-1.",
        privacy_regime="UK GDPR-style rules would apply; no implementation exists in the repo.",
        ron_status="needs_owner_approval",
        status="declared_gap",
        notes="No UK data residency or UK GDPR handling. Do not offer notarial services in the UK.",
    ),
    "CA": JurisdictionRule(
        code="CA",
        name="Canada",
        data_residency="Canadian residency rules would apply — NOT_IMPLEMENTED. No Canadian region is deployed; the only deployment region is us-phoenix-1.",
        privacy_regime="PIPEDA-style rules would apply; no implementation exists in the repo.",
        ron_status="needs_owner_approval",
        status="declared_gap",
        notes="No Canadian data residency or PIPEDA handling. Do not offer notarial services in Canada.",
    ),
}


def jurisdiction_status(code: str) -> Optional[JurisdictionRule]:
    """Return the registry entry for ``code`` (case-insensitive), or None."""
    if not isinstance(code, str):
        return None
    return JURISDICTIONS.get(code.strip().upper())


# ---------------------------------------------------------------------------
# RON / notarial gating — fail-closed, nothing approved by default
# ---------------------------------------------------------------------------

class NotApprovedInJurisdiction(PermissionError):
    """Raised when a RON/notarial act is attempted in a jurisdiction
    the owner has not explicitly approved.

    ``code`` is the stable machine-readable error name:
    ``NOT_APPROVED_IN_JURISDICTION``.
    """
    code = "NOT_APPROVED_IN_JURISDICTION"

    def __init__(self, jurisdiction: Any, message: Optional[str] = None):
        self.jurisdiction = jurisdiction
        super().__init__(
            message
            or f"NOT_APPROVED_IN_JURISDICTION: RON/notarial acts are not approved in jurisdiction {jurisdiction!r}. "
            "No jurisdiction is approved by default; owner approval is required."
        )


# The owner-approved set. EMPTY by design: no jurisdiction is approved
# until the owner names it (with legal counsel / verifier confirmation)
# and this set is updated by an explicit owner decision.
APPROVED_RON_JURISDICTIONS: frozenset = frozenset()


def gate_ron(
    jurisdiction: Any,
    *,
    approved: Iterable[str] = APPROVED_RON_JURISDICTIONS,
) -> Dict[str, Any]:
    """Fail-closed gate for RON / notarial surfaces.

    Returns ``{"ok": True, "jurisdiction": code}`` only when
    ``jurisdiction`` is a non-empty string present in ``approved``.
    Otherwise raises :class:`NotApprovedInJurisdiction` — including for
    unknown, empty, or missing jurisdictions. ``approved`` must be
    supplied explicitly by the caller when the owner has approved a
    jurisdiction; the module default is empty.
    """
    approved_set = frozenset(
        a.strip().upper() for a in approved if isinstance(a, str) and a.strip()
    )
    if not isinstance(jurisdiction, str) or not jurisdiction.strip():
        raise NotApprovedInJurisdiction(jurisdiction)
    code = jurisdiction.strip().upper()
    if code not in approved_set:
        raise NotApprovedInJurisdiction(code)
    return {"ok": True, "jurisdiction": code}


# ---------------------------------------------------------------------------
# Consent records (timestamped UTC, grant / withdraw)
# ---------------------------------------------------------------------------

@dataclass
class ConsentRecord:
    subject_id: str
    scope: str
    granted: bool
    granted_at_utc: Optional[str] = None
    withdrawn_at_utc: Optional[str] = None
    updated_at_utc: str = field(default_factory=utcnow_iso)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "scope": self.scope,
            "granted": self.granted,
            "granted_at_utc": self.granted_at_utc,
            "withdrawn_at_utc": self.withdrawn_at_utc,
            "updated_at_utc": self.updated_at_utc,
        }


class ConsentStore:
    """In-memory consent record store.

    This is a record-keeping helper, not durable storage: records live
    in memory for the life of this object. Persisting consent durably
    (SQLite table, retention policy, backup handling) is a declared
    gap — see the audit doc. Scopes are free-form strings such as
    ``"appointment_contact"`` or ``"av_recording"``; no scope is
    granted by default.
    """

    def __init__(self) -> None:
        self._records: Dict[tuple, ConsentRecord] = {}

    @staticmethod
    def _key(subject_id: str, scope: str) -> tuple:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must be a non-empty string")
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("scope must be a non-empty string")
        return (subject_id.strip(), scope.strip())

    def grant(self, subject_id: str, scope: str) -> ConsentRecord:
        now = utcnow_iso()
        record = ConsentRecord(
            subject_id=subject_id.strip(),
            scope=scope.strip(),
            granted=True,
            granted_at_utc=now,
            withdrawn_at_utc=None,
            updated_at_utc=now,
        )
        self._records[self._key(subject_id, scope)] = record
        return record

    def withdraw(self, subject_id: str, scope: str) -> ConsentRecord:
        key = self._key(subject_id, scope)
        now = utcnow_iso()
        existing = self._records.get(key)
        if existing is None:
            record = ConsentRecord(
                subject_id=subject_id.strip(),
                scope=scope.strip(),
                granted=False,
                granted_at_utc=None,
                withdrawn_at_utc=now,
                updated_at_utc=now,
            )
        else:
            record = ConsentRecord(
                subject_id=existing.subject_id,
                scope=existing.scope,
                granted=False,
                granted_at_utc=existing.granted_at_utc,
                withdrawn_at_utc=now,
                updated_at_utc=now,
            )
        self._records[key] = record
        return record

    def status(self, subject_id: str, scope: str) -> Optional[ConsentRecord]:
        return self._records.get(self._key(subject_id, scope))

    def is_granted(self, subject_id: str, scope: str) -> bool:
        record = self.status(subject_id, scope)
        return bool(record and record.granted)

    def all_for_subject(self, subject_id: str) -> List[Dict[str, Any]]:
        if not isinstance(subject_id, str):
            raise ValueError("subject_id must be a string")
        subject = subject_id.strip()
        return [
            r.as_dict()
            for (sid, _scope), r in sorted(self._records.items())
            if sid == subject
        ]


# ---------------------------------------------------------------------------
# Data-subject export / delete requests
# ---------------------------------------------------------------------------

class InMemoryRecordStore:
    """A tiny fake record store used by tests and as the adapter shape
    for real stores. Records are plain dicts that must carry the
    subject's id under ``subject_id``. Real stores (SQLite ledgers,
    case registries) are NOT wired here — that is a declared gap."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._records: List[Dict[str, Any]] = []

    def add(self, record: Mapping[str, Any]) -> None:
        self._records.append(dict(record))

    def export_for(self, subject_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._records if r.get("subject_id") == subject_id]

    def delete_for(self, subject_id: str) -> int:
        before = len(self._records)
        self._records = [r for r in self._records if r.get("subject_id") != subject_id]
        return before - len(self._records)


class DataSubjectRequestHandler:
    """Handles data export and deletion requests against adapters.

    A store adapter is any object with ``name`` and ``export_for``;
    deletion additionally requires ``delete_for``. Stores without
    ``delete_for`` (or whose ``delete_for`` raises
    ``NotImplementedError``) are reported honestly as
    ``NOT_IMPLEMENTED`` — the request itself is still recorded with a
    stable ``request_id`` so the owner can follow it up. This handler
    never claims deletion from systems it cannot reach (provider
    dashboards, backups, third-party platforms).
    """

    def __init__(self, stores: Iterable[Any] = ()) -> None:
        self._stores: Dict[str, Any] = {}
        for store in stores:
            self._stores[store.name] = store
        self._requests: List[Dict[str, Any]] = []

    def register_store(self, store: Any) -> None:
        self._stores[store.name] = store

    def export_subject_data(self, subject_id: str) -> Dict[str, Any]:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must be a non-empty string")
        subject_id = subject_id.strip()
        stores_out: Dict[str, Any] = {}
        for name, store in sorted(self._stores.items()):
            export_for = getattr(store, "export_for", None)
            if export_for is None:
                stores_out[name] = {
                    "status": "NOT_IMPLEMENTED",
                    "records": [],
                    "note": "Store has no export_for adapter.",
                }
            else:
                stores_out[name] = {
                    "status": "EXPORTED",
                    "records": export_for(subject_id),
                }
        result = {
            "subject_id": subject_id,
            "exported_at_utc": utcnow_iso(),
            "stores": stores_out,
            "note": "Export covers only the registered stores above. Backups, provider dashboards, and third-party platforms are not included.",
        }
        self._requests.append({"type": "export", **result})
        return result

    def request_deletion(self, subject_id: str) -> Dict[str, Any]:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must be a non-empty string")
        subject_id = subject_id.strip()
        per_store: Dict[str, Any] = {}
        for name, store in sorted(self._stores.items()):
            delete_for = getattr(store, "delete_for", None)
            if delete_for is None:
                per_store[name] = {
                    "status": "NOT_IMPLEMENTED",
                    "deleted_count": 0,
                    "note": "Store has no delete_for adapter; nothing was deleted here.",
                }
                continue
            try:
                deleted = delete_for(subject_id)
            except NotImplementedError:
                per_store[name] = {
                    "status": "NOT_IMPLEMENTED",
                    "deleted_count": 0,
                    "note": "Store reports deletion as not implemented.",
                }
                continue
            per_store[name] = {
                "status": "DELETED",
                "deleted_count": int(deleted),
                "note": "Records deleted from this store only. Backups and third-party copies are not covered.",
            }
        result = {
            "request_id": str(uuid.uuid4()),
            "type": "deletion",
            "subject_id": subject_id,
            "requested_at_utc": utcnow_iso(),
            "status": "RECORDED",
            "per_store": per_store,
            "note": "Request recorded. NOT_IMPLEMENTED stores still hold the subject's records and need owner follow-up.",
        }
        self._requests.append(result)
        return result

    def recorded_requests(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._requests]

    def export_json(self, subject_id: str) -> str:
        """Export as a JSON string (the portable export format)."""
        return json.dumps(self.export_subject_data(subject_id), indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Accessibility checklist (WCAG 2.2 AA, evidence-based)
# ---------------------------------------------------------------------------

# Each item: (id, WCAG 2.2 criterion, name, what counts as evidence).
WCAG_CHECKLIST: List[Dict[str, str]] = [
    {"id": "a11y-lang", "criterion": "3.1.1", "name": "Page has a lang attribute",
     "evidence": "html lang attribute present (e.g. <html lang=\"en\">)"},
    {"id": "a11y-alt", "criterion": "1.1.1", "name": "Images have alt text",
     "evidence": "every <img> carries an alt attribute"},
    {"id": "a11y-labels", "criterion": "1.3.1 / 3.3.2", "name": "Form inputs have labels",
     "evidence": "every input/select/textarea has an associated <label for=id> or aria-label"},
    {"id": "a11y-buttons", "criterion": "4.1.2", "name": "Buttons have accessible names",
     "evidence": "every <button> has visible text or an aria-label"},
    {"id": "a11y-live", "criterion": "4.1.3", "name": "Status messages use live regions",
     "evidence": "status/feedback containers use role=status and aria-live"},
    {"id": "a11y-keyboard", "criterion": "2.1.1", "name": "All functionality keyboard-operable",
     "evidence": "manual keyboard walkthrough of the page — cannot be proven by static HTML alone"},
    {"id": "a11y-focus", "criterion": "2.4.7", "name": "Keyboard focus is visible",
     "evidence": "visible :focus styles exist and focus is never removed with outline:none alone"},
    {"id": "a11y-contrast", "criterion": "1.4.3", "name": "Text contrast >= 4.5:1 (normal text)",
     "evidence": "measured contrast ratio for body text — cannot be proven by static HTML alone"},
    {"id": "a11y-target", "criterion": "2.5.8", "name": "Pointer targets >= 24x24 CSS px",
     "evidence": "measured target sizes — cannot be proven by static HTML alone"},
    {"id": "a11y-skip", "criterion": "2.4.1", "name": "Skip link / bypass block present",
     "evidence": "a skip-to-content link exists on pages with repeated navigation"},
]

_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ALT_RE = re.compile(r"""alt\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_LANG_RE = re.compile(r"<html\b[^>]*\blang\s*=\s*[\"'][^\"']+[\"']", re.IGNORECASE)
_INPUT_RE = re.compile(
    r"<(input|select|textarea)\b([^>]*)>", re.IGNORECASE)
_ID_RE = re.compile(r"""\bid\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_LABEL_FOR_RE = re.compile(
    r"""<label\b[^>]*\bfor\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_ARIA_LABEL_RE = re.compile(r"""aria-label\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_BUTTON_RE = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
_SKIP_RE = re.compile(r"skip", re.IGNORECASE)


def _strip_quotes(value: str) -> str:
    return value.strip().strip("\"'")


def check_html_accessibility(html: str) -> Dict[str, Any]:
    """Static accessibility checks over an HTML string.

    Only the statically checkable items (lang, alt, labels, button
    names, live regions, skip link) are decided here. Items needing a
    human or a browser measurement (keyboard walkthrough, focus
    visibility, contrast, target size) are honestly reported as
    ``not_checked`` with the reason recorded. ``html`` must be a
    string; anything else raises ``ValueError``.
    """
    if not isinstance(html, str):
        raise ValueError("html must be a string")
    results: List[Dict[str, Any]] = []

    def verdict(item_id: str, outcome: str, detail: str) -> None:
        item = next(i for i in WCAG_CHECKLIST if i["id"] == item_id)
        results.append({
            "id": item["id"],
            "criterion": item["criterion"],
            "name": item["name"],
            "result": outcome,  # pass | fail | not_checked
            "detail": detail,
        })

    # lang
    verdict("a11y-lang",
            "pass" if _LANG_RE.search(html) else "fail",
            "html lang attribute present" if _LANG_RE.search(html)
            else "no <html lang=...> attribute found")

    # alt text
    imgs = _IMG_RE.findall(html)
    missing_alt = [t for t in imgs if not _ALT_RE.search(t)]
    if not imgs:
        verdict("a11y-alt", "not_checked", "no <img> elements on the page")
    elif not missing_alt:
        verdict("a11y-alt", "pass", f"{len(imgs)} image(s), all with alt")
    else:
        verdict("a11y-alt", "fail",
                f"{len(missing_alt)} of {len(imgs)} image(s) missing alt")

    # labels
    label_targets = {_strip_quotes(m) for m in _LABEL_FOR_RE.findall(html)}
    unlabeled: List[str] = []
    for _tag, attrs in _INPUT_RE.findall(html):
        if _ARIA_LABEL_RE.search(attrs):
            continue
        m = _ID_RE.search(attrs)
        if m and _strip_quotes(m.group(1)) in label_targets:
            continue
        if re.search(r"""\btype\s*=\s*["']?(hidden|submit|button)["']?""",
                     attrs, re.IGNORECASE):
            continue
        unlabeled.append(attrs.strip()[:60])
    inputs = _INPUT_RE.findall(html)
    if not inputs:
        verdict("a11y-labels", "not_checked", "no form fields on the page")
    elif not unlabeled:
        verdict("a11y-labels", "pass",
                f"{len(inputs)} field(s), all labelled")
    else:
        verdict("a11y-labels", "fail",
                f"{len(unlabeled)} field(s) without a label: {unlabeled[:3]}")

    # buttons
    buttons = _BUTTON_RE.findall(html)
    unnamed = [a for a, text in buttons
               if not text.strip() and not _ARIA_LABEL_RE.search(a)]
    if not buttons:
        verdict("a11y-buttons", "not_checked", "no <button> elements on the page")
    elif not unnamed:
        verdict("a11y-buttons", "pass", f"{len(buttons)} button(s), all named")
    else:
        verdict("a11y-buttons", "fail",
                f"{len(unnamed)} of {len(buttons)} button(s) without a name")

    # live regions
    has_live = bool(re.search(r"""role\s*=\s*["']status["']""", html, re.IGNORECASE)
                    or re.search(r"""aria-live\s*=\s*["']polite["']""", html, re.IGNORECASE))
    verdict("a11y-live",
            "pass" if has_live else "not_checked",
            "role=status / aria-live region found" if has_live
            else "no live region found in static HTML; status-message behaviour not verified")

    # skip link
    verdict("a11y-skip",
            "pass" if _SKIP_RE.search(html) else "not_checked",
            "skip link text found" if _SKIP_RE.search(html)
            else "no skip link found in static HTML; bypass behaviour not verified")

    # Items that cannot be decided from static HTML.
    for item_id, reason in (
        ("a11y-keyboard", "needs a manual keyboard walkthrough in a browser"),
        ("a11y-focus", "needs rendered :focus styles checked in a browser"),
        ("a11y-contrast", "needs measured contrast ratios, not source text"),
        ("a11y-target", "needs measured target sizes, not source text"),
    ):
        verdict(item_id, "not_checked", reason)

    passed = sum(1 for r in results if r["result"] == "pass")
    failed = [r for r in results if r["result"] == "fail"]
    return {
        "checked_at_utc": utcnow_iso(),
        "total_items": len(results),
        "passed": passed,
        "failed": len(failed),
        "not_checked": sum(1 for r in results if r["result"] == "not_checked"),
        "items": results,
        "summary": (
            "FAIL: " + ", ".join(f"{f['id']} ({f['criterion']})" for f in failed)
            if failed else
            "No static failures found; unchecked items still need a real audit."
        ),
    }


class AccessibilityChecklist:
    """Evidence-based WCAG 2.2 AA checklist.

    ``check_page`` takes an evidence mapping (one boolean / value per
    item id, or ``None`` when unknown) and reports pass / fail /
    not_checked honestly: an item with no evidence is ``not_checked``,
    never assumed to pass. ``check_html`` runs the static checks in
    :func:`check_html_accessibility` for a page's HTML source.
    """

    @staticmethod
    def check_page(evidence: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(evidence, Mapping):
            raise ValueError("evidence must be a mapping of item id -> evidence")
        items: List[Dict[str, Any]] = []
        for entry in WCAG_CHECKLIST:
            value = evidence.get(entry["id"], None)
            if value is None:
                result, detail = "not_checked", "no evidence supplied"
            elif value is True:
                result, detail = "pass", "evidence supplied: pass"
            elif value is False:
                result, detail = "fail", "evidence supplied: fail"
            else:
                result, detail = "not_checked", f"evidence supplied but not a pass/fail boolean: {value!r}"
            items.append({
                "id": entry["id"],
                "criterion": entry["criterion"],
                "name": entry["name"],
                "result": result,
                "detail": detail,
            })
        failed = [i for i in items if i["result"] == "fail"]
        return {
            "checked_at_utc": utcnow_iso(),
            "total_items": len(items),
            "passed": sum(1 for i in items if i["result"] == "pass"),
            "failed": len(failed),
            "not_checked": sum(1 for i in items if i["result"] == "not_checked"),
            "items": items,
            "summary": (
                "FAIL: " + ", ".join(f"{f['id']} ({f['criterion']})" for f in failed)
                if failed else
                "No failures in the evidence supplied; unchecked items still need a real audit."
            ),
        }

    @staticmethod
    def check_html(html: str) -> Dict[str, Any]:
        return check_html_accessibility(html)
