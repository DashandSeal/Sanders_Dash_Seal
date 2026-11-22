"""Sanders Dash & Seal — Zone Watch: brand matching and match store.

Matches zone-file owner names against the Sanders brands and the
platform hostnames, and records only the matches in a small SQLite
database. The full zone is never stored.

Kinds of match (the ``kind`` carried on every feed event):

* ``new_registration`` — a matched name not seen in the stored match
  set before this run. This is the brand-protection signal: a platform
  hostname appearing for the first time, or a new name carrying the
  Sanders brand.
* ``known`` — a platform hostname (or one of its subdomains) already
  in the stored match set.
* ``lookalike`` — a name carrying the Sanders brand that is not one of
  the platform hostnames and was already in the stored match set.

Every event also carries ``is_known_host`` so a ``new_registration``
event still says whether the name is one of the platform hostnames or
a brand-carrying name, and ``first_seen`` so a lookalike seen for the
first time is identifiable.
"""

from __future__ import annotations

import os
import sqlite3

BRAND_SUBSTRING = "sanders"

# The 35 platform hostnames shared by the four rooseveltsanders381-ship-it
# repositories (Sanders-Ecosystem-, sanders-global-platforms,
# Sanders-Home-Healthcare-ecosystem-,
# https-business-collaborate-integrate.deploypad.app-).
PLATFORM_HOSTS = (
    "ai-doctor.sandershomehealthcare.com",
    "ai-psychiatrist.sandershomehealthcare.com",
    "ai-recognition.sandersglobal.com",
    "omniconm.sandersglobal.com",
    "steward-sentinel.sanderssecurestack.com",
    "patriot-saint.sandersglobal.com",
    "gia-mind.sandersglobal.com",
    "grantwriter.sanders.global",
    "freedom-rev.sandersglobal.com",
    "tactical-training.sandersglobal.com",
    "martial-academy.sandersglobal.com",
    "leadership-institute.sandersglobal.com",
    "fitness-wellness.sandersglobal.com",
    "advanced-academics.sandersglobal.com",
    "recon-ops.sandersglobal.com",
    "guardian-sentinel.sanderssecurestack.com",
    "big-data-mind.sandersglobal.com",
    "strategy-hub.sandersglobal.com",
    "global-freedom.sandersglobal.com",
    "health-solutions.sandershomehealthcare.com",
    "sanders-coordinator.vercel.app",
    "intel-ops.sandersglobal.com",
    "family-council.sandersglobal.com",
    "elite-leadership.sandersglobal.com",
    "combat-academy.sandersglobal.com",
    "tactical-edge.sandersglobal.com",
    "wellness-center.sandersglobal.com",
    "knowledge-base.sandersglobal.com",
    "ai-strategy.sandersglobal.com",
    "freedom-ops.sandersglobal.com",
    "mind-guardian.sandersglobal.com",
    "watchdog-alpha.sanderssecurestack.com",
    "watchdog-beta.sanderssecurestack.com",
    "twin-lil-mama.sanderssecurestack.com",
    "twin-baby-girl.sanderssecurestack.com",
)

# The ten site names served by Sanders Dash & Seal on Oracle.
SITE_HOSTS = (
    "sandersdashandseal.com",
    "www.sandersdashandseal.com",
    "sanderslegalhelpersllc.com",
    "www.sanderslegalhelpersllc.com",
    "sanderssixshield.com",
    "www.sanderssixshield.com",
    "sanderssecurestack.com",
    "www.sanderssecurestack.com",
    "sandersemergencyglobalcommunication.com",
    "www.sandersemergencyglobalcommunication.com",
)

KNOWN_HOSTS = PLATFORM_HOSTS + SITE_HOSTS

_KNOWN_SET = frozenset(KNOWN_HOSTS)


def normalize_name(name: str) -> str:
    """Lowercase a hostname and strip one trailing dot."""
    return name.strip().lower().rstrip(".")


def owner_name_from_line(line: str) -> str:
    """Return the owner name (first field) of one zone-file line.

    Blank lines, comments and zone directives carry no owner name and
    return an empty string.
    """
    text = line.strip()
    if not text or text.startswith(";") or text.startswith("$"):
        return ""
    return normalize_name(text.split()[0])


def is_candidate(name: str) -> bool:
    """Cheap pre-filter: True when a zone name could possibly match.

    Every known host carries the brand substring, so a single substring
    check covers them all; the exact-set lookup also catches any future
    known host added without the brand in its name. Call this before
    touching the match store — a zone file has hundreds of millions of
    lines and the store must only be queried for candidates.
    """
    name = normalize_name(name)
    if BRAND_SUBSTRING in name:
        return True
    return name in _KNOWN_SET


def is_known_host(name: str) -> bool:
    """True when ``name`` is one of the platform/site hostnames, or a
    subdomain of one."""
    name = normalize_name(name)
    if name in _KNOWN_SET:
        return True
    return any(name.endswith("." + host) for host in _KNOWN_SET)


def classify(name: str, store: "MatchStore") -> str | None:
    """Classify one owner name, or return None when it is not a match.

    ``new_registration`` for a matched name not in the stored match
    set, ``known`` for a platform hostname already stored, and
    ``lookalike`` for a brand-carrying name that is not a platform
    hostname and was already stored.
    """
    name = normalize_name(name)
    known = is_known_host(name)
    if not known and BRAND_SUBSTRING not in name:
        return None
    if store.seen_before(name):
        return "known" if known else "lookalike"
    return "new_registration"


class MatchStore:
    """Small SQLite store holding only matched names — never a zone.

    One row per matched name: the TLD it was found under, the kind it
    was first recorded as, and first/last seen timestamps (UTC ISO).
    """

    _SCHEMA = (
        "CREATE TABLE IF NOT EXISTS matches ("
        "  name TEXT PRIMARY KEY,"
        "  tld TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  first_seen TEXT NOT NULL,"
        "  last_seen TEXT NOT NULL"
        ")"
    )

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(self._SCHEMA)
        self._conn.commit()

    def seen_before(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM matches WHERE name = ?", (normalize_name(name),)
        ).fetchone()
        return row is not None

    def record(self, name: str, tld: str, kind: str, seen_at: str) -> bool:
        """Record a match. Returns True when the name is new to the
        store, False when it was already stored (last_seen updated)."""
        name = normalize_name(name)
        cursor = self._conn.execute(
            "UPDATE matches SET last_seen = ? WHERE name = ?",
            (seen_at, name),
        )
        if cursor.rowcount:
            self._conn.commit()
            return False
        self._conn.execute(
            "INSERT INTO matches (name, tld, kind, first_seen, last_seen)"
            " VALUES (?, ?, ?, ?, ?)",
            (name, tld, kind, seen_at, seen_at),
        )
        self._conn.commit()
        return True

    def first_seen(self, name: str) -> str | None:
        row = self._conn.execute(
            "SELECT first_seen FROM matches WHERE name = ?",
            (normalize_name(name),),
        ).fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MatchStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
