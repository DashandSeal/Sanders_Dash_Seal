"""
Append-only notarial journal for the native Sanders Dash & Seal chain.

The journal is the platform's own durable record of completed native
notarial acts. An entry is written only for a session that has reached
COMPLETED inside the native session machine, through that machine's
existing completion path, and records what the session record itself
carries: the session and its case, the act kind, the parties the
session record binds (the case and, where a seal is registered, the
sealing notary), the seal's own digest, and digests of the completion
evidence. Entries are hash-chained in the GlassBoxAudit style, so a
later edit to any entry breaks every link after it, and each entry is
also indexed as JOURNAL evidence in the native evidence index.

A journal entry is a record of a completed act. It is not itself the
act, an identity check, a commission authorization, or a substitute
for any record a jurisdiction requires the notary to keep elsewhere.
"""

import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$', re.ASCII)
GENESIS = '0' * 64
EVIDENCE_KINDS = ('HUMAN_ATTESTATION', 'COMMISSION', 'IDENTITY', 'ACT_EXECUTION')
ACT_KINDS = {'E_NOTARY': 'E_NOTARY_NOTARIAL_ACT', 'RON': 'RON_NOTARIAL_ACT'}
SESSION_COLUMNS = ('session_id', 'case_id', 'method', 'jurisdiction', 'state',
                   'completed_at', 'evidence_json')


class JournalDenied(ValueError):
    pass


def _digest(value):
    """SHA-256 of the canonical JSON encoding of a value (GlassBox style)."""
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


class NativeNotaryJournal:
    """Hash-chained, append-only journal of completed native sessions."""

    def __init__(self, database):
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_notarial_journal (
                entry_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL UNIQUE,
                session_id TEXT NOT NULL UNIQUE,
                body TEXT NOT NULL,
                entry_hash TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")
            # The journal registers each entry as JOURNAL evidence in
            # the native evidence index (NativeEvidenceIndex's table,
            # created here with its identical schema so the journal
            # also works on a database the index has not opened yet).
            db.execute("""CREATE TABLE IF NOT EXISTS native_evidence_index (
                session_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
                kind TEXT NOT NULL, sha256 TEXT NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(session_id, evidence_id)
            );""")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        return db

    @staticmethod
    def _row_dict(row):
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return dict(zip(SESSION_COLUMNS, row))

    def _existing(self, db, session_id):
        row = db.execute(
            "SELECT body, entry_hash FROM native_notarial_journal "
            "WHERE session_id = ?;", (session_id,)).fetchone()
        if row is None:
            return None
        body, entry_hash = (row['body'], row['entry_hash']) if isinstance(
            row, sqlite3.Row) else (row[0], row[1])
        return {'entry': json.loads(body), 'entry_hash': entry_hash}

    def record_completion(self, session_id, *, db=None):
        """Journal a completed native session.

        With ``db`` (a caller-owned connection inside its transaction,
        as ``NativeNotarySessions.complete`` supplies) the entry joins
        that transaction; without one the journal opens and commits its
        own. A session that has not completed is denied: the journal
        records completed acts only. Re-recording a session returns its
        existing entry unchanged.
        """
        if not isinstance(session_id, str) or not ID.fullmatch(session_id):
            raise JournalDenied("Invalid session identity")
        if db is not None:
            return self._record(db, session_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            result = self._record(conn, session_id)
            conn.commit()
            return result

    def _record(self, db, session_id):
        existing = self._existing(db, session_id)
        if existing is not None:
            return existing
        row = db.execute(
            "SELECT session_id, case_id, method, jurisdiction, state, "
            "completed_at, evidence_json FROM native_notarial_sessions "
            "WHERE session_id = ?;", (session_id,)).fetchone()
        session = self._row_dict(row)
        if session is None:
            raise JournalDenied("Unknown session record")
        if session['state'] != 'COMPLETED':
            raise JournalDenied(
                "Session has not completed; the journal records "
                "completed notarial acts only")
        # The sealing notary and the seal's own digest, where a seal is
        # registered for this session. Absence is recorded as absence;
        # a digest is never manufactured for a seal that does not exist.
        seal_digest = None
        notary_id = None
        try:
            seal = db.execute(
                "SELECT notary_id, signature_bytes FROM "
                "native_document_seals WHERE session_id = ? "
                "ORDER BY created_at DESC LIMIT 1;",
                (session_id,)).fetchone()
        except sqlite3.OperationalError:
            seal = None
        if seal is not None:
            seal_values = dict(seal) if isinstance(seal, sqlite3.Row) else {
                'notary_id': seal[0], 'signature_bytes': seal[1]}
            notary_id = seal_values['notary_id']
            seal_digest = hashlib.sha256(
                seal_values['signature_bytes']).hexdigest()
        try:
            evidence = json.loads(session['evidence_json'] or '{}')
        except (TypeError, ValueError):
            evidence = {}
        if not isinstance(evidence, dict):
            evidence = {}
        evidence_digests = {
            kind: _digest(evidence[kind])
            for kind in EVIDENCE_KINDS if evidence.get(kind) is not None}
        previous = db.execute(
            "SELECT entry_hash FROM native_notarial_journal "
            "ORDER BY entry_seq DESC LIMIT 1;").fetchone()
        previous_hash = (previous[0] if previous is not None else GENESIS)
        recorded_at = int(time.time())
        body = {
            'entry_id': 'journal-' + uuid.uuid4().hex,
            'session_id': session_id,
            'case_id': session['case_id'],
            'method': session['method'],
            'jurisdiction': session['jurisdiction'],
            'act_kind': ACT_KINDS[session['method']],
            'parties': {'case_id': session['case_id'],
                        'notary_id': notary_id},
            'seal_digest': seal_digest,
            'evidence_digests': evidence_digests,
            'completed_at': session['completed_at'],
            'recorded_at': recorded_at,
            'previous_hash': previous_hash,
        }
        entry_hash = _digest(body)
        db.execute(
            "INSERT INTO native_notarial_journal "
            "(entry_id, session_id, body, entry_hash, recorded_at) "
            "VALUES (?, ?, ?, ?, ?);",
            (body['entry_id'], session_id,
             json.dumps(body, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False),
             entry_hash, recorded_at))
        db.execute(
            "INSERT INTO native_evidence_index "
            "(session_id, evidence_id, kind, sha256, created_at) "
            "VALUES (?, ?, 'JOURNAL', ?, ?);",
            (session_id, body['entry_id'], entry_hash, recorded_at))
        return {'entry': body, 'entry_hash': entry_hash}

    def entries_for_session(self, session_id):
        if not isinstance(session_id, str) or not ID.fullmatch(session_id):
            raise JournalDenied("Invalid session identity")
        with self._connect() as db:
            rows = db.execute(
                "SELECT body, entry_hash FROM native_notarial_journal "
                "WHERE session_id = ? ORDER BY entry_seq ASC;",
                (session_id,)).fetchall()
        return [{'entry': json.loads(body), 'entry_hash': entry_hash}
                for body, entry_hash in rows]

    def verify_chain(self):
        """Recompute every link; return the last entry hash.

        Raises JournalDenied if any stored body no longer hashes to
        its recorded entry hash or any previous-hash link is broken.
        """
        previous = GENESIS
        with self._connect() as db:
            rows = db.execute(
                "SELECT body, entry_hash FROM native_notarial_journal "
                "ORDER BY entry_seq ASC;").fetchall()
        for body_text, entry_hash in rows:
            body = json.loads(body_text)
            if body.get('previous_hash') != previous:
                raise JournalDenied("Journal chain changed: link mismatch")
            if _digest(body) != entry_hash:
                raise JournalDenied("Journal chain changed: entry mismatch")
            previous = entry_hash
        return previous
