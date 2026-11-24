"""Sanders Signal — native social-distribution hub.

One post, written once, fans out to the four companies' Facebook
Pages and Instagram Business accounts (Meta Graph API, token from the
environment only), with a headquarters broadcast reaching all four
companies only after explicit owner approval. The hub also carries
scheduling, analytics, one inbox, brand guardrails, roles, a media
library and notifications, and top-notch audio/video plus real-time
language, sign-language and Braille support, globally.

It is local only and never a boot blocker: unconfigured adapters
report not-configured diagnostically, and no live post is made
without configured tokens. No region, no geo-gating, no language
restriction. No secrets, no addresses and no contact info are stored
here; configuration comes only from ``SANDERS_SIGNAL_*`` environment
variables.
"""

from __future__ import annotations

from .adapters import (
    ADAPTERS,
    BaseAdapter,
    LinkedInAdapter,
    MetaAdapter,
    ThreadsAdapter,
    TikTokAdapter,
    XAdapter,
    YouTubeAdapter,
    adapter_for,
)
from .analytics import collect_metrics
from .config import (
    ALL_COMPANIES,
    COMPANIES,
    HEADQUARTERS_COMPANY,
    NETWORKS,
    AdapterStatus,
)
from .guardrails import check_post
from .hub import SignalHub
from .inbox import collect_all, inbox_adapter_for
from .media import CAPABILITIES, capabilities_for, route_media
from .models import (
    ApprovalRecord,
    Attachment,
    InboxMessage,
    MediaAsset,
    Notification,
    Post,
    PublishResult,
)
from .notifications import (
    on_approval_waiting,
    on_failed,
    on_published,
    register,
    unregister,
)
from .roles import can_approve, can_publish, can_write
from .scheduling import is_due, next_due, parse_schedule

__all__ = [
    "ADAPTERS",
    "ALL_COMPANIES",
    "ApprovalRecord",
    "Attachment",
    "BaseAdapter",
    "CAPABILITIES",
    "COMPANIES",
    "HEADQUARTERS_COMPANY",
    "InboxMessage",
    "LinkedInAdapter",
    "MediaAsset",
    "MetaAdapter",
    "NETWORKS",
    "Notification",
    "Post",
    "PublishResult",
    "SignalHub",
    "ThreadsAdapter",
    "TikTokAdapter",
    "XAdapter",
    "YouTubeAdapter",
    "AdapterStatus",
    "adapter_for",
    "can_approve",
    "can_publish",
    "can_write",
    "capabilities_for",
    "check_post",
    "collect_all",
    "collect_metrics",
    "inbox_adapter_for",
    "is_due",
    "next_due",
    "on_approval_waiting",
    "on_failed",
    "on_published",
    "parse_schedule",
    "register",
    "route_media",
    "unregister",
]
