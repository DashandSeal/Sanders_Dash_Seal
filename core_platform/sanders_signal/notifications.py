"""Sanders Signal — notifications: in-process hooks only.

The hub fires a notification when an approval is waiting, when a post
goes live, and when a post fails (with the reason). Hooks run in
process; there is no delivery channel yet — that is a named next
increment. Registering a hook never blocks publishing.
"""
from __future__ import annotations

from .models import Notification

KINDS = ("approval_waiting", "published", "failed")

_hooks: dict[str, list] = {kind: [] for kind in KINDS}


def register(kind: str, hook) -> None:
    """Register a callable taking one :class:`Notification`."""
    if kind not in KINDS:
        raise ValueError("unknown notification kind: %r" % (kind,))
    _hooks[kind].append(hook)


def unregister(kind: str, hook) -> None:
    """Remove a previously registered hook (no-op when absent)."""
    if kind in _hooks and hook in _hooks[kind]:
        _hooks[kind].remove(hook)


def fire(kind: str, post_id: str, message: str) -> Notification:
    """Build the notification and run every hook for its kind.

    A failing hook is swallowed: notifications never block publishing.
    """
    notification = Notification(kind=kind, post_id=post_id, message=message)
    for hook in list(_hooks.get(kind, [])):
        try:
            hook(notification)
        except Exception:
            continue
    return notification


def on_approval_waiting(post_id: str, message: str) -> Notification:
    """An HQ broadcast is waiting for the owner's approval."""
    return fire("approval_waiting", post_id, message)


def on_published(post_id: str, message: str) -> Notification:
    """A post went live (at least one destination published)."""
    return fire("published", post_id, message)


def on_failed(post_id: str, message: str) -> Notification:
    """A post failed, with the reason in the message."""
    return fire("failed", post_id, message)


__all__ = [
    "KINDS",
    "register",
    "unregister",
    "fire",
    "on_approval_waiting",
    "on_published",
    "on_failed",
]
