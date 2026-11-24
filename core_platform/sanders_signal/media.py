"""Sanders Signal — media kinds, orientation and per-network capabilities.

The capability table is the hub's routing table. Only entries marked
``True`` come from the plan or from a network's well-known post types.
Everything else is marked "needs verification" and must be confirmed
against that network's published requirements before live use — never
stated as fact. A network that cannot take a format declines with a
reason; nothing is ever silently dropped.
"""
from __future__ import annotations

from .config import NETWORKS
from .models import Attachment, Post

# True = confirmed the network accepts the kind.
# "needs verification" = not yet confirmed against the network's
# published requirements; treat as not accepted until verified.
CAPABILITIES: dict[str, dict[str, object]] = {
    "facebook": {
        "text": True,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
    "instagram": {
        "text": True,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
    "linkedin": {
        "text": True,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
    "threads": {
        "text": True,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
    "youtube": {
        "text": False,
        "photo": False,
        "video": True,
        "audio": "needs verification",
    },
    "tiktok": {
        "text": False,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
    "x": {
        "text": True,
        "photo": True,
        "video": True,
        "audio": "needs verification",
    },
}

# Human-readable network names for reasons.
NETWORK_NAMES: dict[str, str] = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "threads": "Threads",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "x": "X",
}


def capabilities_for(network: str) -> dict[str, object]:
    """The capability entry for one network (unknown networks: all False)."""
    return dict(CAPABILITIES.get(network, {}))


def _attachment_accepted(network: str, attachment: Attachment) -> tuple[bool, str]:
    """Whether one network accepts one attachment, and why not."""
    entry = CAPABILITIES.get(network)
    if entry is None:
        return False, "%s is not a known network" % network
    accepted = entry.get(attachment.kind)
    if accepted is True:
        return True, ""
    if accepted == "needs verification":
        return (
            False,
            "%s does not accept %s yet (needs verification)"
            % (NETWORK_NAMES.get(network, network), attachment.kind),
        )
    return (
        False,
        "%s does not accept %s" % (NETWORK_NAMES.get(network, network), attachment.kind),
    )


def route_media(post: Post) -> list[tuple[str, bool, str]]:
    """Per-network accept/decline for one post.

    Returns a list of ``(network, accepted, reason)`` in fan-out order.
    A text-only post is accepted by every network that takes text; a
    post with attachments is accepted only where every attachment kind
    is accepted. Declines always carry a reason.
    """
    results: list[tuple[str, bool, str]] = []
    for network in NETWORKS:
        if not post.attachments and not post.text.strip():
            results.append((network, False, "empty post: no text and no attachments"))
            continue
        if not post.attachments:
            accepted = CAPABILITIES.get(network, {}).get("text")
            if accepted is True:
                results.append((network, True, ""))
            else:
                results.append(
                    (network, False, "%s does not accept text-only posts"
                     % NETWORK_NAMES.get(network, network))
                )
            continue
        reasons: list[str] = []
        for attachment in post.attachments:
            accepted, reason = _attachment_accepted(network, attachment)
            if not accepted:
                reasons.append(reason)
        if reasons:
            results.append((network, False, "; ".join(reasons)))
        else:
            results.append((network, True, ""))
    return results


__all__ = [
    "CAPABILITIES",
    "NETWORK_NAMES",
    "capabilities_for",
    "route_media",
]
