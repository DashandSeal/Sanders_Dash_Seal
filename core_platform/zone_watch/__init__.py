"""Sanders Dash & Seal — Zone Watch.

Zone Watch incorporates the owner's ICANN CZDS zone-file access into
Sanders Dash & Seal for brand protection and for the global operation
of the platforms.

It streams approved TLD zone files (com, app, global and any others
the owner approves) line by line, keeps only the names that match the
Sanders brands and platform hostnames, records them in a small SQLite
match store, emits one JSON event per match for the watchdog and
Sentinel platforms to consume, and verifies every platform hostname
resolves through public DNS.

It never loads a whole zone file into memory and never stores a whole
zone file on disk: the .com zone alone is gigabytes, and this platform
runs on Oracle Always Free (1 OCPU, 6 GB RAM, 47 GB disk) by
Humanitarian Core Laws 10 and 11.

Zone Watch is a separate service from the watchdog and Sentinel
platforms. It feeds them events; it does not merge with them and does
not replace their own detection. No watchdog or Sentinel module in
this repository exposes an event intake, so the feed is a plain JSON
events file plus the importable :func:`feed.publish_event` function.

Credentials come only from the environment (CZDS_USERNAME and
CZDS_PASSWORD). They are never hardcoded, never written to a file,
and never logged.
"""

from __future__ import annotations

from .downloader import DEFAULT_TLDS, iter_zone_lines
from .feed import build_event, emit_event, publish_event
from .filter import KNOWN_HOSTS, PLATFORM_HOSTS, SITE_HOSTS, MatchStore, classify, is_candidate
from .global_dns import check_all, resolves

__all__ = [
    "DEFAULT_TLDS",
    "KNOWN_HOSTS",
    "PLATFORM_HOSTS",
    "SITE_HOSTS",
    "MatchStore",
    "build_event",
    "check_all",
    "classify",
    "emit_event",
    "is_candidate",
    "iter_zone_lines",
    "publish_event",
    "resolves",
]
