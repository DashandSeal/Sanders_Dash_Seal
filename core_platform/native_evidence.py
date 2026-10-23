"""Durable evidence digest index for native Sanders Dash & Seal workflows.

An index is not an identity check, commission authorization, signed document,
notarial journal, recording service or completed notarization.
"""
import re
import sqlite3
import time
from pathlib import Path

ID = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z", re.ASCII)
DIGEST = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
KINDS = frozenset(("DOCUMENT", "IDENTITY", "AUTHORITY", "JOURNAL", "AV_RECORDING", "CONSENT", "HUMAN_ATTESTATION"))

class EvidenceDenied(ValueError):
    pass

class NativeEvidenceIndex:
    def __init__(self, database):
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_evidence_index (
                session_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
                kind TEXT NOT NULL, sha256 TEXT NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(session_id,evidence_id))""")

    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def register(self, session_id, evidence_id, kind, sha256):
        if not all(isinstance(x, str) and ID.fullmatch(x) for x in (session_id, evidence_id)):
            raise EvidenceDenied("Invalid evidence identity")
        if kind not in KINDS or not isinstance(sha256, str) or not DIGEST.fullmatch(sha256):
            raise EvidenceDenied("Invalid evidence category or digest")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            session = db.execute("SELECT state,method FROM native_notarial_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session or session[0] != "AWAITING_AUTHORITY":
                raise EvidenceDenied("Session is unavailable for evidence registration")
            if kind == "AV_RECORDING" and session[1] != "RON":
                raise EvidenceDenied("AV recording requires RON session")
            existing = db.execute("SELECT kind,sha256 FROM native_evidence_index WHERE session_id=? AND evidence_id=?", (session_id,evidence_id)).fetchone()
            if existing and existing != (kind, sha256):
                raise EvidenceDenied("Conflicting evidence identifier")
            if not existing:
                db.execute("INSERT INTO native_evidence_index VALUES (?,?,?,?,?)",
                           (session_id,evidence_id,kind,sha256,int(time.time())))
        return {"session_id":session_id,"evidence_id":evidence_id,"kind":kind,"sha256":sha256}

    def list_for_session(self, session_id):
        if not isinstance(session_id, str) or not ID.fullmatch(session_id):
            raise EvidenceDenied("Invalid session identity")
        with self.connect() as db:
            rows = db.execute("SELECT evidence_id,kind,sha256,created_at FROM native_evidence_index WHERE session_id=? ORDER BY created_at,evidence_id",(session_id,)).fetchall()
        return [dict(zip(("evidence_id","kind","sha256","created_at"), row)) for row in rows]
