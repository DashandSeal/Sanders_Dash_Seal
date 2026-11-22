"""Sanders Dash & Seal — Zone Watch: daily run entry point.

One run, in order:

1. Stream each approved TLD zone file from CZDS (CZDS_USERNAME and
   CZDS_PASSWORD from the environment) and keep only the names that
   match the Sanders brands and platform hostnames.
2. Record matches in the small SQLite match store and emit one JSON
   event per match to the events file for the watchdog and Sentinel
   platforms.
3. Verify every platform and site hostname resolves through public
   DNS — the "function globally" check.
4. Write a run summary JSON.

A failed download for one TLD does not stop the other TLDs or the
global DNS check; the failure is recorded in the summary and the run
exits non-zero.

Usage (from the repository root on the Oracle Always Free instance,
with CZDS_USERNAME and CZDS_PASSWORD set in the environment):

    python3 -m core_platform.zone_watch.run --data-dir /home/opc/zone-watch

Data written (only matches, never a zone file):

* ``zone-watch-matches.db`` — SQLite match store.
* ``zone-watch-events.jsonl`` — one JSON event per match.
* ``zone-watch-summary.json`` — this run's summary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .downloader import ZoneWatchDownloadError, iter_zone_lines, tlds_from_env
from .feed import publish_event
from .filter import KNOWN_HOSTS, MatchStore, classify, is_candidate, is_known_host, owner_name_from_line
from .global_dns import check_all


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(data_dir: str, tlds) -> dict:
    """Run one Zone Watch pass and return the summary dict."""
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "zone-watch-matches.db")
    events_path = os.path.join(data_dir, "zone-watch-events.jsonl")
    summary_path = os.path.join(data_dir, "zone-watch-summary.json")
    started_at = _now_iso()
    per_tld: dict[str, dict] = {}
    download_errors: dict[str, str] = {}

    with MatchStore(db_path) as store:
        for tld in tlds:
            lines = 0
            matches = 0
            new = 0
            try:
                for line in iter_zone_lines(tld):
                    lines += 1
                    name = owner_name_from_line(line)
                    if not name or not is_candidate(name):
                        continue
                    previously_seen = store.seen_before(name)
                    kind = classify(name, store)
                    if kind is None:
                        continue
                    now = _now_iso()
                    first_seen = store.first_seen(name) or now
                    is_new = store.record(name, tld, kind, now)
                    if is_new:
                        new += 1
                    publish_event(
                        name, tld, kind, first_seen, events_path,
                        is_known_host=is_known_host(name),
                        previously_seen=previously_seen,
                    )
                    matches += 1
            except ZoneWatchDownloadError as exc:
                download_errors[tld] = str(exc)
            per_tld[tld] = {"lines_scanned": lines, "matches": matches,
                            "new_registrations": new}

    dns_results = check_all(KNOWN_HOSTS)
    unresolved = [item["name"] for item in dns_results
                  if not item["resolves"]]
    summary = {
        "service": "zone-watch",
        "platform": "Sanders Dash & Seal",
        "started_at_utc": started_at,
        "finished_at_utc": _now_iso(),
        "tlds": per_tld,
        "download_errors": download_errors,
        "dns": {
            "checked": len(dns_results),
            "resolved": len(dns_results) - len(unresolved),
            "unresolved": unresolved,
        },
        "events_file": events_path,
        "match_store": db_path,
    }
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    summary["summary_file"] = summary_path
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zone-watch",
        description="Stream approved CZDS zone files, keep only Sanders "
                    "brand and platform-hostname matches, and verify every "
                    "platform hostname resolves through public DNS.")
    parser.add_argument(
        "--data-dir", default=None,
        help="Directory for the match store, events file and summary "
             "(default: ZONE_WATCH_DATA_DIR or ./data/zone-watch).")
    parser.add_argument(
        "--tlds", default=None,
        help="Comma-separated TLDs (default: CZDS_TLDS or com,app,global).")
    args = parser.parse_args(argv)
    data_dir = (args.data_dir or os.environ.get("ZONE_WATCH_DATA_DIR")
                or os.path.join("data", "zone-watch"))
    tlds = tuple(part.strip().lower() for part in args.tlds.split(",")
                 if part.strip()) if args.tlds else tlds_from_env()
    summary = run(data_dir, tlds)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not summary["download_errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
