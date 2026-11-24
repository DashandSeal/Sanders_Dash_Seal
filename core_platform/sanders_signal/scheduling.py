"""Sanders Signal — timezone-aware scheduling.

All stored times are UTC. The owner sets a post with a timezone (kept
for display); the hub compares in UTC. A due post publishes in
scheduled order; an overdue post publishes at the next run and is
logged as overdue — never silently skipped.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import Post, utcnow


def parse_schedule(value: str, timezone_name: str) -> tuple[datetime, str]:
    """Parse an ISO datetime in the owner's timezone -> (UTC, timezone).

    ``value`` may carry its own offset; when it does not, the named
    timezone applies. Raises ValueError on a bad value or timezone.
    """
    try:
        zone = ZoneInfo(timezone_name)
    except (KeyError, ValueError, TypeError):
        raise ValueError("unknown timezone: %r" % (timezone_name,))
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(timezone.utc), timezone_name


def is_due(post: Post, now: datetime | None = None) -> bool:
    """True when a post is due: unscheduled posts are due immediately."""
    if post.scheduled_at is None:
        return True
    moment = now or utcnow()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment >= post.scheduled_at


def is_overdue(post: Post, now: datetime | None = None) -> bool:
    """True when a scheduled post is past its time."""
    if post.scheduled_at is None:
        return False
    moment = now or utcnow()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment > post.scheduled_at


def next_due(posts: list[Post], now: datetime | None = None) -> Post | None:
    """The earliest due post (scheduled order), or None."""
    moment = now or utcnow()
    due = [post for post in posts if is_due(post, moment)]
    if not due:
        return None
    return min(due, key=lambda p: (p.scheduled_at or p.created_at, p.created_at))


def sort_for_publish(posts: list[Post]) -> list[Post]:
    """Posts in publish order: scheduled time, then creation time."""
    return sorted(posts, key=lambda p: (p.scheduled_at or p.created_at, p.created_at))


__all__ = ["parse_schedule", "is_due", "is_overdue", "next_due", "sort_for_publish"]
