"""Sanders Signal — one inbox: collect comments and messages.

The collection model is real; the per-network inbox adapters are
stubs reporting ``NOT_CONNECTED`` until their live connections are
configured. Nothing is invented: an empty inbox is an empty inbox.
"""
from __future__ import annotations

from .models import InboxMessage


class BaseInboxAdapter:
    """Interface for one network's inbox collection."""

    network = "base"

    def status(self, company: str) -> tuple[str, str]:
        return ("NOT_CONNECTED", "no inbox adapter")

    def collect(self, company: str) -> list[InboxMessage]:
        return []


class _StubInboxAdapter(BaseInboxAdapter):
    """One not-connected network inbox."""

    network = "stub"
    display_name = "Stub"

    def status(self, company: str) -> tuple[str, str]:
        return (
            "NOT_CONNECTED",
            "%s inbox not connected: no app/token configured" % self.display_name,
        )


class FacebookInboxAdapter(_StubInboxAdapter):
    network = "facebook"
    display_name = "Facebook"


class InstagramInboxAdapter(_StubInboxAdapter):
    network = "instagram"
    display_name = "Instagram"


class LinkedInInboxAdapter(_StubInboxAdapter):
    network = "linkedin"
    display_name = "LinkedIn"


class ThreadsInboxAdapter(_StubInboxAdapter):
    network = "threads"
    display_name = "Threads"


class YouTubeInboxAdapter(_StubInboxAdapter):
    network = "youtube"
    display_name = "YouTube"


class TikTokInboxAdapter(_StubInboxAdapter):
    network = "tiktok"
    display_name = "TikTok"


class XInboxAdapter(_StubInboxAdapter):
    network = "x"
    display_name = "X"


INBOX_ADAPTERS: dict[str, type[BaseInboxAdapter]] = {
    "facebook": FacebookInboxAdapter,
    "instagram": InstagramInboxAdapter,
    "linkedin": LinkedInInboxAdapter,
    "threads": ThreadsInboxAdapter,
    "youtube": YouTubeInboxAdapter,
    "tiktok": TikTokInboxAdapter,
    "x": XInboxAdapter,
}


def inbox_adapter_for(network: str) -> BaseInboxAdapter:
    """Build the inbox adapter for one network."""
    cls = INBOX_ADAPTERS.get(network)
    if cls is None:
        return _StubInboxAdapter()
    return cls()


def collect_all(company: str, networks: list[str] | None = None) -> list[InboxMessage]:
    """Collect inbox messages for one company across networks.

    Unconnected networks contribute nothing and are reported through
    their adapter status, not by inventing messages.
    """
    from .config import NETWORKS

    messages: list[InboxMessage] = []
    for network in networks or NETWORKS:
        messages.extend(inbox_adapter_for(network).collect(company))
    messages.sort(key=lambda m: m.received_at)
    return messages


__all__ = [
    "BaseInboxAdapter",
    "FacebookInboxAdapter",
    "InstagramInboxAdapter",
    "LinkedInInboxAdapter",
    "ThreadsInboxAdapter",
    "YouTubeInboxAdapter",
    "TikTokInboxAdapter",
    "XInboxAdapter",
    "INBOX_ADAPTERS",
    "inbox_adapter_for",
    "collect_all",
]
