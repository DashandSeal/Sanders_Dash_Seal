"""Daedalus learned-knowledge store (founder-directed build, 2026-11-25).

The persistent store behind Daedalus's real-time learning capability
(``real_time_learning`` in ``core_platform/daedalus_l15_capabilities.py``;
founder direction, 2026-11-25: "He's got to have the ability to
actually learn in real time").

What this store is: an append-only SQLite ledger of what Daedalus
has been taught and what outcomes his executed work produced, kept
in the codebase's own persistence pattern — a store class over a
SQLite file under ``data/`` (compare ``core_platform/accounts.py``
and the Bozly ledger wiring), created on first use, never required
to exist beforehand.

Layering law: this store is layered *over* the founder's registry
(``core_platform/ai_platform_links.json``) and never touches it.
Learned records live only here; the native core reads them as an
overlay on the founder records, founder records govern on conflict,
and conflicts are surfaced by the core — never resolved by editing
either side. Nothing in this module opens, writes, or merges into
the registry file.

Provenance (Glass-Box style): every record carries its source, the
timestamp it was learned or recorded, and an evidence hash — the
SHA-256 of the record's canonical content — from which its record
id derives. A record without a named source is refused: knowledge
Daedalus cannot attribute is knowledge he does not keep.

The store holds no credentials, opens no sockets, and imports no
provider SDK. It is local durable memory, nothing else.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Mapping

__all__ = [
    "DEFAULT_DB_PATH",
    "OUTCOMES",
    "DaedalusKnowledgeStore",
    "default_store_path",
    "evidence_hash",
]

# The codebase's data-directory convention (compare the Bozly ledger
# at data/bozly_ledger.db): runtime state lives under data/ at the
# repository root and is created on first use, never committed.
DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "daedalus_knowledge.db"
)
_PATH_ENV = "DAEDALUS_KNOWLEDGE_DB_PATH"

# The closed outcome vocabulary for executed work. Anything outside
# this set is refused, so outcome accounting in the planner stays a
# deterministic count over named outcomes.
OUTCOMES = ("succeeded", "failed", "accepted", "rejected")


def default_store_path() -> Path:
    """The learned-knowledge store path for this deployment.

    The ``DAEDALUS_KNOWLEDGE_DB_PATH`` environment variable wins
    when set (the codebase's env-override pattern for SQLite paths);
    otherwise the store lives at the conventional data path above.
    """
    override = os.environ.get(_PATH_ENV)
    return Path(override) if override else DEFAULT_DB_PATH


def evidence_hash(content: Mapping) -> str:
    """SHA-256 of a record's canonical content (Glass-Box evidence).

    Canonical form: JSON with sorted keys and tight separators, so
    the hash is a pure function of the record's content.
    """
    canonical = json.dumps(
        dict(content), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class DaedalusKnowledgeStore:
    """Append-only ledger of learned records and outcome records.

    Two tables, one discipline: rows are inserted, never updated or
    deleted by this class, so the ledger is the full history of what
    was taught and what happened — the overlay the native core reads
    is derived from it (latest record wins per taught triple), never
    the other way round.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS learned_records (
                record_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('fact', 'relationship')),
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                source TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                learned_at REAL NOT NULL,
                learned_at_iso TEXT NOT NULL,
                evidence_hash TEXT NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS outcome_records (
                record_id TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                outcome TEXT NOT NULL
                    CHECK(outcome IN ('succeeded', 'failed', 'accepted', 'rejected')),
                reason TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL,
                recorded_at REAL NOT NULL,
                recorded_at_iso TEXT NOT NULL,
                evidence_hash TEXT NOT NULL
            );""")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Writing: teaching and outcome recording
    # ------------------------------------------------------------------

    def _learn(
        self,
        kind: str,
        subject: str,
        predicate: str,
        object_value: str,
        *,
        source: str,
        note: str = "",
    ) -> dict:
        for field, value in (
            ("subject", subject),
            ("predicate", predicate),
            ("object", object_value),
            ("source", source),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Learned record requires a non-empty " + field
                    + " (provenance is mandatory: unattributed "
                    "knowledge is not kept)"
                )
        now = time.time()
        content = {
            "kind": kind,
            "subject": subject,
            "predicate": predicate,
            "object": object_value,
            "source": source,
            "note": note,
            "learned_at_epoch": now,
            "learned_at_iso": _iso(now),
        }
        digest = evidence_hash(content)
        record = {
            "record_id": "learned-" + digest[:24],
            **content,
            "learned_at_epoch": now,
            "evidence_hash": digest,
        }
        with self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO learned_records(
                    record_id, kind, subject, predicate, object, source,
                    note, learned_at, learned_at_iso, evidence_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    record["record_id"], kind, subject, predicate,
                    object_value, source, note, now,
                    record["learned_at_iso"], digest,
                ),
            )
        return record

    def learn_fact(
        self,
        subject: str,
        predicate: str,
        object_value: str,
        *,
        source: str,
        note: str = "",
    ) -> dict:
        """Teach one fact: ``subject predicate object_value``.

        Returns the stored record, with provenance and evidence hash.
        """
        return self._learn(
            "fact", subject, predicate, object_value, source=source, note=note
        )

    def learn_relationship(
        self,
        subject: str,
        predicate: str,
        target: str,
        *,
        source: str,
        note: str = "",
    ) -> dict:
        """Teach one relationship: ``subject predicate target``.

        A ``references`` relationship between two registry platform
        ids becomes a learned edge in the core's reference graph; any
        relationship is kept as a recallable record regardless.
        """
        return self._learn(
            "relationship", subject, predicate, target, source=source, note=note
        )

    def record_outcome(
        self,
        component: str,
        outcome: str,
        *,
        reason: str = "",
        source: str,
    ) -> dict:
        """Record the outcome of executed work for one component.

        ``component`` names whatever the outcome is about — a
        platform id, or an edge key of the form ``edge:A->B`` for a
        reference path. ``outcome`` must be one of :data:`OUTCOMES`.
        Returns the stored record, with provenance and evidence hash.
        """
        if outcome not in OUTCOMES:
            raise ValueError(
                "Outcome must be one of " + ", ".join(OUTCOMES)
                + " (got " + repr(outcome) + ")"
            )
        for field, value in (("component", component), ("source", source)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Outcome record requires a non-empty " + field
                    + " (provenance is mandatory: unattributed "
                    "knowledge is not kept)"
                )
        now = time.time()
        content = {
            "component": component,
            "outcome": outcome,
            "reason": reason,
            "source": source,
            "recorded_at_epoch": now,
            "recorded_at_iso": _iso(now),
        }
        digest = evidence_hash(content)
        record = {
            "record_id": "outcome-" + digest[:24],
            **content,
            "recorded_at_epoch": now,
            "evidence_hash": digest,
        }
        with self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO outcome_records(
                    record_id, component, outcome, reason, source,
                    recorded_at, recorded_at_iso, evidence_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    record["record_id"], component, outcome, reason,
                    source, now, record["recorded_at_iso"], digest,
                ),
            )
        return record

    # ------------------------------------------------------------------
    # Reading: the overlay the native core consumes
    # ------------------------------------------------------------------

    @staticmethod
    def _learned_row(row: sqlite3.Row) -> dict:
        return {
            "record_id": row["record_id"],
            "kind": row["kind"],
            "subject": row["subject"],
            "predicate": row["predicate"],
            "object": row["object"],
            "source": row["source"],
            "note": row["note"],
            "learned_at_epoch": row["learned_at"],
            "learned_at_iso": row["learned_at_iso"],
            "evidence_hash": row["evidence_hash"],
        }

    def learned_records(self, kind: str | None = None) -> list[dict]:
        """All learned records in insertion order (the full history)."""
        query = "SELECT * FROM learned_records"
        params: tuple = ()
        if kind is not None:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY rowid"
        with self._connect() as db:
            return [self._learned_row(row) for row in db.execute(query, params)]

    def facts(self) -> list[dict]:
        return self.learned_records("fact")

    def relationships(self) -> list[dict]:
        return self.learned_records("relationship")

    def outcome_records(self, component: str | None = None) -> list[dict]:
        """All outcome records in insertion order, or one component's."""
        query = "SELECT * FROM outcome_records"
        params: tuple = ()
        if component is not None:
            query += " WHERE component = ?"
            params = (component,)
        query += " ORDER BY rowid"
        with self._connect() as db:
            return [
                {
                    "record_id": row["record_id"],
                    "component": row["component"],
                    "outcome": row["outcome"],
                    "reason": row["reason"],
                    "source": row["source"],
                    "recorded_at_epoch": row["recorded_at"],
                    "recorded_at_iso": row["recorded_at_iso"],
                    "evidence_hash": row["evidence_hash"],
                }
                for row in db.execute(query, params)
            ]

    def counts(self) -> dict:
        """Ledger sizes, for declarations and status surfaces."""
        with self._connect() as db:
            learned = db.execute(
                "SELECT COUNT(*) FROM learned_records"
            ).fetchone()[0]
            outcomes = db.execute(
                "SELECT COUNT(*) FROM outcome_records"
            ).fetchone()[0]
        return {"learned_records": learned, "outcome_records": outcomes}
