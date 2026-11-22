"""Sanders Dash & Seal — Zone Watch: event feed for watchdog/Sentinel.

Emits one JSON event per match so the watchdog and Sentinel platforms
can consume Zone Watch findings. The feed is deliberately plain: one
JSON object per line in a JSONL events file, plus the importable
:func:`publish_event` function for any watchdog module that wants to
receive events directly.

No new wire protocol is invented. No watchdog or Sentinel module in
this repository exposes an event intake, so nothing is wired into one
here; the file and the function are the feed, and a future intake can
read either.

Event fields:

* ``name`` — the matched hostname.
* ``tld`` — the TLD whose zone file the name came from.
* ``first_seen`` — UTC ISO timestamp the name was first recorded.
* ``kind`` — ``new_registration`` | ``known`` | ``lookalike``.
* ``is_known_host`` — True when the name is one of the platform or
  site hostnames (or a subdomain of one).
* ``previously_seen`` — True when the name was already in the match
  store before this run.
* ``source`` — always ``zone-watch``.
"""

from __future__ import annotations

import json
import os

SOURCE = "zone-watch"


def build_event(name: str, tld: str, kind: str, first_seen: str, *,
                is_known_host: bool = False,
                previously_seen: bool = False) -> dict:
    """Build one Zone Watch event dict."""
    return {
        "name": name,
        "tld": tld,
        "first_seen": first_seen,
        "kind": kind,
        "is_known_host": is_known_host,
        "previously_seen": previously_seen,
        "source": SOURCE,
    }


def emit_event(event: dict, events_path: str | os.PathLike) -> dict:
    """Append one event dict as a single JSON line to the events file
    and return the event."""
    with open(events_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def publish_event(name: str, tld: str, kind: str, first_seen: str,
                  events_path: str | os.PathLike, *,
                  is_known_host: bool = False,
                  previously_seen: bool = False) -> dict:
    """Build and append one Zone Watch event. This is the importable
    function watchdog and Sentinel modules can call to receive events
    directly instead of reading the events file."""
    return emit_event(
        build_event(name, tld, kind, first_seen,
                    is_known_host=is_known_host,
                    previously_seen=previously_seen),
        events_path,
    )


def read_events(events_path: str | os.PathLike) -> list[dict]:
    """Read back every event in an events file, in file order."""
    if not os.path.exists(events_path):
        return []
    events = []
    with open(events_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events
