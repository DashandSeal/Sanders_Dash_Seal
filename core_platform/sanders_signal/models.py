"""Sanders Signal — post, approval, result and supporting models.

Plain dataclasses only. No network access, no secrets, no region or
language restriction anywhere in the model. Accessibility metadata
(language, sign-language track, Braille-ready text) travels with the
post through queue, approval and fan-out.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Statuses a post moves through.
POST_STATUSES = (
    "draft",
    "queued",
    "awaiting_approval",
    "approved",
    "published",
    "blocked",
    "failed",
)

# Publish-result statuses.
RESULT_STATUSES = ("published", "declined", "failed", "not_configured")

# Attachment kinds.
ATTACHMENT_KINDS = ("text", "photo", "video", "audio")

# Reach values.
REACH_VALUES = ("company", "headquarters")

_MISSING = "NOT_AVAILABLE"


def utcnow() -> datetime:
    """Current UTC time, timezone-aware."""
    return datetime.now(timezone.utc)


def make_braille_ready_text(text: str) -> str:
    """Plain structured text suitable for refreshable Braille displays.

    Strips markdown-style formatting that breaks screen readers and
    Braille conversion, keeps the words and line structure.
    """
    if not text:
        return ""
    cleaned = re.sub(r"[*_`#>|]+", "", text)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line)


@dataclass
class Attachment:
    """One media attachment on a post. ``reference`` is a media-library
    asset id or an http(s) URL — never a file copy."""

    kind: str  # text | photo | video | audio
    reference: str
    orientation: str = "unknown"  # vertical | horizontal | square | unknown
    duration_seconds: float | None = None
    sign_language: str | None = None
    interpretation_media: str | None = None
    alt_text: str | None = None


@dataclass
class ApprovalRecord:
    """One recorded approval of a headquarters broadcast."""

    post_id: str
    officer: str
    approved_at: datetime
    destinations: list[str] = field(default_factory=list)
    receipt: str | None = None
    note: str = ""


@dataclass
class PublishResult:
    """The outcome of one publish attempt to one network for one company."""

    post_id: str
    network: str
    company: str
    status: str  # published | declined | failed | not_configured
    reason: str = ""
    remote_id: str | None = None
    metrics: dict | None = None
    published_at: datetime | None = None


@dataclass
class InboxMessage:
    """One incoming comment or message collected from a network."""

    message_id: str
    network: str
    company: str
    sender: str
    text: str
    received_at: datetime = field(default_factory=utcnow)
    status: str = "unread"


@dataclass
class MediaAsset:
    """One approved asset in the media library (reference, not a copy)."""

    asset_id: str
    company: str
    kind: str
    reference: str
    alt_text: str | None = None
    sign_language: str | None = None


@dataclass
class Notification:
    """One hub notification event (approval waiting / live / failed)."""

    kind: str  # approval_waiting | published | failed
    post_id: str
    message: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Post:
    """One composed post, written once and fanned out by the hub."""

    author_company: str
    author_officer: str
    reach: str  # company | headquarters
    text: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    language: str = "en"
    translations: dict[str, str] = field(default_factory=dict)
    braille_ready_text: str = ""
    scheduled_at: datetime | None = None
    scheduled_timezone: str | None = None
    status: str = "draft"
    approval: ApprovalRecord | None = None
    post_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if self.reach not in REACH_VALUES:
            raise ValueError("reach must be 'company' or 'headquarters'")
        if self.status not in POST_STATUSES:
            raise ValueError("unknown post status: %r" % (self.status,))
        for attachment in self.attachments:
            if attachment.kind not in ATTACHMENT_KINDS:
                raise ValueError("unknown attachment kind: %r" % (attachment.kind,))
        if not self.braille_ready_text and self.text:
            self.braille_ready_text = make_braille_ready_text(self.text)


__all__ = [
    "Attachment",
    "ApprovalRecord",
    "PublishResult",
    "InboxMessage",
    "MediaAsset",
    "Notification",
    "Post",
    "POST_STATUSES",
    "RESULT_STATUSES",
    "ATTACHMENT_KINDS",
    "REACH_VALUES",
    "make_braille_ready_text",
    "utcnow",
]
