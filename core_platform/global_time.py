"""Global time handling for Sanders Dash & Seal.

Rules (real-world / global by design):
- Storage is always UTC. Only timezone-aware datetimes are accepted;
  naive datetimes raise :class:`NaiveDatetimeError` instead of being
  silently assumed to be local time or UTC.
- Display is per-user, by IANA timezone name (``ZoneInfo``). No
  hardcoded America/Denver / MST assumption anywhere in this module.
- DST transitions are handled honestly: an ambiguous local time
  (fall-back) resolves to the FIRST occurrence (fold=0) and is flagged;
  a nonexistent local time (spring-forward gap) is shifted forward to
  the first valid instant and flagged. Callers get the flag, never a
  silently wrong instant.

Stdlib only. No live calls, no keys.
"""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "NaiveDatetimeError",
    "UnknownTimezoneError",
    "AmbiguousTime",
    "NonexistentTime",
    "now_utc",
    "require_aware",
    "to_utc",
    "parse_iso8601",
    "serialize_utc",
    "display_in_timezone",
    "resolve_timezone",
    "next_daily_occurrence",
    "is_ambiguous",
    "is_nonexistent",
]

UTC = timezone.utc


class NaiveDatetimeError(ValueError):
    """Raised when a naive (tzinfo-less) datetime is supplied."""


class UnknownTimezoneError(ValueError):
    """Raised when an IANA timezone name cannot be resolved."""


class AmbiguousTime(ValueError):
    """A local time that occurs twice (fall-back DST transition)."""


class NonexistentTime(ValueError):
    """A local time that never occurs (spring-forward DST gap)."""


def resolve_timezone(name: str) -> ZoneInfo:
    """Resolve an IANA timezone name, raising UnknownTimezoneError."""
    if not isinstance(name, str) or not name.strip():
        raise UnknownTimezoneError("empty timezone name")
    try:
        return ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise UnknownTimezoneError(f"unknown IANA timezone: {name!r}") from exc


def now_utc() -> datetime:
    """Current instant, timezone-aware, in UTC."""
    return datetime.now(UTC)


def require_aware(value: datetime, *, what: str = "datetime") -> datetime:
    """Return *value* if aware, else raise NaiveDatetimeError."""
    if not isinstance(value, datetime):
        raise TypeError(f"{what} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise NaiveDatetimeError(
            f"{what} is naive (no tzinfo); pass a timezone-aware datetime"
        )
    return value


def to_utc(value: datetime) -> datetime:
    """Convert an aware datetime to UTC. Naive input raises."""
    return require_aware(value).astimezone(UTC)


def serialize_utc(value: datetime) -> str:
    """Serialize an aware datetime as ISO-8601 UTC, e.g. 2026-11-13T17:48:36Z."""
    return to_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 string. A timezone offset (or Z) is REQUIRED.

    Naive strings raise NaiveDatetimeError. The result is normalized
    to UTC.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty ISO-8601 string")
    text = value.strip().replace("Z", "+00:00").replace("z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 datetime: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NaiveDatetimeError(
            f"ISO-8601 datetime {value!r} has no timezone offset; "
            "storage requires an explicit offset (use Z for UTC)"
        )
    return parsed.astimezone(UTC)


def display_in_timezone(value: datetime, tz_name: str) -> datetime:
    """Render an aware datetime in the user's IANA timezone."""
    return require_aware(value).astimezone(resolve_timezone(tz_name))


def _roundtrip_offset(local_naive: datetime, tz: ZoneInfo) -> timedelta:
    return local_naive.replace(tzinfo=tz).utcoffset()


def is_ambiguous(local_naive: datetime, tz: ZoneInfo) -> bool:
    """True if the naive local time occurs twice (fall-back).

    Nonexistent (spring-forward gap) times are NOT ambiguous.
    """
    if is_nonexistent(local_naive, tz):
        return False
    first = local_naive.replace(tzinfo=tz, fold=0)
    second = local_naive.replace(tzinfo=tz, fold=1)
    return first.utcoffset() != second.utcoffset()


def is_nonexistent(local_naive: datetime, tz: ZoneInfo) -> bool:
    """True if the naive local time never occurs (spring-forward gap)."""
    candidate = local_naive.replace(tzinfo=tz, fold=0)
    # A nonexistent time round-trips to a different wall-clock time.
    return candidate.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != local_naive


def next_daily_occurrence(
    hour: int,
    minute: int,
    tz_name: str,
    *,
    after: datetime | None = None,
) -> tuple[datetime, str]:
    """Next daily occurrence of a local wall-clock time.

    Returns ``(aware_utc_datetime, status)`` where status is one of:
    - ``"ok"`` — unambiguous, exists;
    - ``"ambiguous_first"`` — fall-back day; the FIRST occurrence is used;
    - ``"nonexistent_shifted"`` — spring-forward gap; shifted forward to
      the first valid instant after the gap (same date, later clock time).

    ``after`` must be aware (defaults to now, UTC). The result is UTC.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"invalid local time {hour:02d}:{minute:02d}")
    tz = resolve_timezone(tz_name)
    after_utc = to_utc(after) if after is not None else now_utc()
    after_local = after_utc.astimezone(tz)

    for day_offset in range(0, 3):
        day = (after_local + timedelta(days=day_offset)).date()
        naive = datetime.combine(day, dtime(hour, minute))
        status = "ok"
        if is_nonexistent(naive, tz):
            # Shift forward minute-by-minute to the first valid instant.
            probe = naive
            for _ in range(0, 180):
                probe += timedelta(minutes=1)
                if not is_nonexistent(probe, tz):
                    naive = probe
                    break
            status = "nonexistent_shifted"
        elif is_ambiguous(naive, tz):
            status = "ambiguous_first"  # fold=0 below
        candidate = naive.replace(tzinfo=tz, fold=0).astimezone(UTC)
        if candidate > after_utc:
            return candidate, status
        # Same-day time already passed; try tomorrow (loop continues).
    raise RuntimeError("could not find a next daily occurrence within 3 days")
