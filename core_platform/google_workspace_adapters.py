"""Optional Google Workspace adapters (Docs / Sheets / Gmail / Calendar).

Google Docs, Sheets, Gmail and Calendar are already connected to
Muse for this owner.  These adapters are the *optional* bridge for
the platform to use them where they actually help:

* Grantwriter drafting -> Google Docs (export a finished draft).
* Scheduling -> Google Calendar (create a deadline/reminder event).
* Notifications -> Gmail (send a status email).

Design, stated honestly
-----------------------
* No Google library is imported at module import time and no live
  call is made by this module.  Each adapter takes an injected
  client object (the connected Google service client, or a fake in
  tests) exposing one small method.  Without a client, every action
  raises ``ValueError("... not configured ...")`` and ``status()``
  reports ``MISSING_CLIENT`` — never a silent no-op, never a
  fabricated document/event/email.
* The injected-client shape is deliberately tiny so the real
  connected client can be wrapped by the caller without this module
  knowing Google's API surface:
  - Docs:    ``create_document(title, text) -> {"id": ..., "url": ...}``
  - Sheets:  ``append_row(spreadsheet_id, range, values) -> {"updated": n}``
  - Gmail:   ``send_message(to, subject, body) -> {"id": ...}``
  - Calendar: ``create_event(summary, start, end, description="") -> {"id": ...}``
* No credentials are handled here at all: authentication lives with
  the already-connected Google account; this module never sees a
  token, key or password.
"""

from __future__ import annotations

from typing import Any


class GoogleWorkspaceNotConfigured(ValueError):
    """Raised when a Workspace action is attempted without a client."""


class _BaseAdapter:
    service: str = "google-workspace"
    client_method: str = ""

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def configured(self) -> bool:
        return self._client is not None

    def status(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "configured": self.configured,
            "live_status": "READY" if self.configured else "MISSING_CLIENT",
            "note": (
                "Client supplied; live calls go through the connected "
                "Google account."
                if self.configured
                else "No client supplied; pass the connected Google "
                "service client to enable this adapter. No live call "
                "has been made."
            ),
        }

    def _require_client(self):
        if self._client is None:
            raise GoogleWorkspaceNotConfigured(
                f"{self.service} client is not configured; pass the "
                "connected Google service client to enable it"
            )
        method = getattr(self._client, self.client_method, None)
        if not callable(method):
            raise TypeError(
                f"Google client must expose {self.client_method}()"
            )
        return method


class GoogleDocsAdapter(_BaseAdapter):
    """Optional export target for Grantwriter drafts."""

    service = "google-docs"
    client_method = "create_document"

    def create_document(self, *, title: str, text: str) -> dict[str, Any]:
        if not title.strip() or not text.strip():
            raise ValueError("title and text must not be empty")
        create = self._require_client()
        result = create(title, text)
        if not isinstance(result, dict):
            raise ValueError("docs client returned an unexpected result")
        return {"service": self.service, **result}


class GoogleSheetsAdapter(_BaseAdapter):
    """Optional ledger/log target (e.g. grant pipeline, payment log)."""

    service = "google-sheets"
    client_method = "append_row"

    def append_row(
        self, *, spreadsheet_id: str, range: str, values: list[Any]
    ) -> dict[str, Any]:
        if not spreadsheet_id.strip() or not range.strip():
            raise ValueError("spreadsheet_id and range must not be empty")
        if not isinstance(values, list) or not values:
            raise ValueError("values must be a non-empty list")
        append = self._require_client()
        result = append(spreadsheet_id, range, values)
        if not isinstance(result, dict):
            raise ValueError("sheets client returned an unexpected result")
        return {"service": self.service, **result}


class GmailAdapter(_BaseAdapter):
    """Optional notification sender (status / deadline reminders)."""

    service = "gmail"
    client_method = "send_message"

    def send_notification(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        if "@" not in to or not subject.strip() or not body.strip():
            raise ValueError("to/subject/body must be valid and non-empty")
        send = self._require_client()
        result = send(to, subject, body)
        if not isinstance(result, dict):
            raise ValueError("gmail client returned an unexpected result")
        return {"service": self.service, **result}


class GoogleCalendarAdapter(_BaseAdapter):
    """Optional scheduler (grant deadlines, review reminders)."""

    service = "google-calendar"
    client_method = "create_event"

    def create_event(
        self,
        *,
        summary: str,
        start: str,
        end: str,
        description: str = "",
    ) -> dict[str, Any]:
        if not summary.strip() or not start.strip() or not end.strip():
            raise ValueError("summary, start and end must not be empty")
        create = self._require_client()
        result = create(summary, start, end, description)
        if not isinstance(result, dict):
            raise ValueError("calendar client returned an unexpected result")
        return {"service": self.service, **result}


def workspace_status(adapters: dict[str, _BaseAdapter] | None = None) -> dict[str, Any]:
    """Status of all four optional adapters. No live calls."""
    supplied = adapters or {}
    names = ("google-docs", "google-sheets", "gmail", "google-calendar")
    out: dict[str, Any] = {}
    for name in names:
        adapter = supplied.get(name)
        out[name] = (
            adapter.status()
            if adapter is not None
            else {
                "service": name,
                "configured": False,
                "live_status": "MISSING_CLIENT",
                "note": "No client supplied. No live call has been made.",
            }
        )
    return out


__all__ = [
    "GoogleWorkspaceNotConfigured",
    "GoogleDocsAdapter",
    "GoogleSheetsAdapter",
    "GmailAdapter",
    "GoogleCalendarAdapter",
    "workspace_status",
]
