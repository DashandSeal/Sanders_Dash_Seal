"""Grantwriter LLM drafting + optional Google Docs export.

Grantwriter (Mother) stores opportunities and applications in SQLite
(``app/grantwriter_mother.py``).  This module adds the language layer
it was missing:

* :func:`draft_application_section` — drafts one application section
  (e.g. executive summary, needs statement, budget narrative) from an
  opportunity dict + applicant facts, using an injectable chat backend
  (Claude or OpenAI, same ``generate`` shape as Daedalus).  Without a
  backend it is built from the environment and raises honestly when
  the key/model are absent.  A fake backend may be passed explicitly
  for tests.
* :func:`draft_to_google_doc` — optional export of a finished draft
  to Google Docs through an injected docs client (any object with
  ``create_document(title, text)``).  No Google library is imported
  here and no live call is made unless the caller supplies a real,
  connected client (see ``google_workspace_adapters.GoogleDocsAdapter``).
  Without a client it raises ``ValueError`` naming the missing piece.

Rules, stated honestly
----------------------
* The model output is draft text only.  Nothing here submits an
  application, signs anything, or claims a funder accepted it.
* Applicant facts are caller-supplied; the model is instructed to
  mark anything it cannot verify as ``[UNVERIFIED]`` rather than
  inventing figures, deadlines or eligibility.
* No key or credential is stored or logged.  Free-tier-first: drafting
  itself costs whatever the chosen provider bills; run it against a
  fake/local backend for $0 rehearsal.
"""

from __future__ import annotations

from typing import Any

REQUIRED_OPPORTUNITY_FIELDS = ("title", "funder", "deadline")


def _validate_opportunity(opportunity: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(opportunity, dict):
        raise ValueError("opportunity must be a dict")
    missing = [
        f for f in REQUIRED_OPPORTUNITY_FIELDS if not str(opportunity.get(f, "")).strip()
    ]
    if missing:
        raise ValueError(f"opportunity is missing: {', '.join(missing)}")
    return opportunity


def draft_application_section(
    *,
    opportunity: dict[str, Any],
    section: str,
    applicant_facts: str,
    backend=None,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Draft one grant application section with a chat backend.

    Returns ``opportunity_title``, ``funder``, ``section`` and
    ``draft_text``.  Raises ``ValueError`` on missing opportunity
    fields, an empty section/facts, or a missing backend key/model.
    """
    opportunity = _validate_opportunity(opportunity)
    if not section.strip():
        raise ValueError("section name must not be empty")
    if not applicant_facts.strip():
        raise ValueError("applicant facts must not be empty")
    client = backend
    if client is None:
        from .role_worker_llm import build_backend

        client = build_backend()
    system = (
        "You are the Grantwriter (Mother) drafting assistant for Sanders "
        "Dash & Seal. Draft grant prose from the supplied facts only. "
        "Do not invent funder requirements, deadlines, amounts, "
        "eligibility or outcomes. Mark anything you cannot verify from "
        "the supplied facts as [UNVERIFIED]. Return draft text only."
    )
    user_message = (
        f"Opportunity: {opportunity['title']}\n"
        f"Funder: {opportunity['funder']}\n"
        f"Deadline: {opportunity['deadline']}\n"
        f"Section to draft: {section}\n"
        f"Applicant facts:\n{applicant_facts}"
    )
    response = client.generate(
        system=system,
        user_message=user_message,
        max_tokens=max_tokens,
        metadata={"component": "GRANTWRITER", "section": section},
    )
    if not response.text.strip():
        raise ValueError("language backend returned no draft text")
    return {
        "opportunity_title": opportunity["title"],
        "funder": opportunity["funder"],
        "deadline": opportunity["deadline"],
        "section": section,
        "draft_text": response.text,
        "model": getattr(response, "model", ""),
    }


def draft_to_google_doc(
    *,
    draft: dict[str, Any],
    docs_client=None,
) -> dict[str, Any]:
    """Export a finished draft to Google Docs via an injected client.

    ``docs_client`` must expose ``create_document(title, text)`` and
    return a mapping with at least a document id/url.  Without a
    client this raises ``ValueError`` — the export is optional and
    never silently skipped.  No Google API is called by this module
    itself.
    """
    if not isinstance(draft, dict) or not str(draft.get("draft_text", "")).strip():
        raise ValueError("draft must contain non-empty draft_text")
    if docs_client is None:
        raise ValueError(
            "no Google Docs client supplied; connect Google Docs and "
            "pass a docs client (see google_workspace_adapters."
            "GoogleDocsAdapter) to export this draft"
        )
    create = getattr(docs_client, "create_document", None)
    if not callable(create):
        raise TypeError("docs client must expose create_document(title, text)")
    title = (
        f"Grant draft — {draft.get('opportunity_title', 'untitled')} "
        f"— {draft.get('section', '')}"
    ).strip()
    result = create(title, draft["draft_text"])
    if not isinstance(result, dict) or not result.get("id") and not result.get("url"):
        raise ValueError("docs client returned no document id or url")
    return {
        "title": title,
        "document_id": result.get("id"),
        "url": result.get("url"),
        "status": "exported_via_injected_docs_client",
    }


__all__ = [
    "REQUIRED_OPPORTUNITY_FIELDS",
    "draft_application_section",
    "draft_to_google_doc",
]
