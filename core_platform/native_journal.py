"""
Append-only hash-linked native notarial workflow journal.

Entries document workflow events, not legal completion or human authority.
"""

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$', re.ASCII)
EVENTS = frozenset({'SESSION_CREATED', 'DOCUMENT_RECEIVED', 'IDENTITY_REVIEW', 'COMMISSION_REVIEW', 'CONSENT_RECORDED', 'SIGNING_COMPLETED', 'AV_STARTED', 'AV_COMPLETED', 'SESSION_CANCELLED'})

class JournalDenied(ValueError):
    pass

class NativeJournal:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_journal_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE, event_type TEXT NOT NULL,
                actor TEXT NOT NULL, evidence_digest TEXT NOT NULL,
                recorded_at INTEGER NOT NULL, previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            );""")

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        return db

    @staticmethod
    def _hash(row):
        return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def append(self, session_id, event_id, event_type, actor, evidence_digest):
        if not all(isinstance(v, str) and ID.fullmatch(v) for v in (session_id, event_id, actor)):
            raise JournalDenied("Invalid journal identity")
        if event_type not in EVENTS or not isinstance(evidence_digest, str) or not re.fullmatch(r'^[a-f0-9]{64}$', evidence_digest):
            raise JournalDenied("Invalid event or evidence digest")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE;")
            session = db.execute("SELECT state FROM native_notarial_sessions WHERE session_id = ?;", (session_id,)).fetchone()
            if session is None:
                raise JournalDenied("Unknown session")
            existing = db.execute("SELECT session_id, event_type, actor, evidence_digest, entry_hash FROM native_journal_events WHERE event_id = ?;", (event_id,)).fetchone()
            if existing:
                if existing[:4] != (session_id, event_type, actor, evidence_digest):
                    raise JournalDenied("Conflicting event")
                return {"event_id": event_id, "entry_hash": existing[4]}
            if session[0] == "CANCELLED" and event_type != "SESSION_CANCELLED":
                raise JournalDenied("Cancelled session")
            previous = db.execute("SELECT entry_hash FROM native_journal_events ORDER BY sequence DESC LIMIT 1;").fetchone()
            prior = previous[0] if previous else "0" * 64
            recorded_at = int(time.time())
            row = {"session_id": session_id, "event_id": event_id, "event_type": event_type, "actor": actor, "evidence_digest": evidence_digest, "recorded_at": recorded_at, "previous_hash": prior}
            digest = self._hash(row)
            db.execute("INSERT INTO native_journal_events (session_id, event_id, event_type, actor, evidence_digest, recorded_at, previous_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                       (session_id, event_id, event_type, actor, evidence_digest, recorded_at, prior, digest))
            db.commit()
        return {"event_id": event_id, "entry_hash": digest}

    def verify(self):
        with self._db() as db:
            rows = db.execute("SELECT session_id, event_id, event_type, actor, evidence_digest, recorded_at, previous_hash, entry_hash FROM native_journal_events ORDER BY sequence ASC;").fetchall()
            keys = ("session_id", "event_id", "event_type", "actor", "evidence_digest", "recorded_at", "previous_hash")
            previous = "0" * 64
            for row in rows:
                item = dict(zip(keys, row[:7]))
                if item["previous_hash"] != previous or self._hash(item) != row[7]:
                    raise JournalDenied("Journal integrity failure")
                previous = row[7]
            return len(rows)
