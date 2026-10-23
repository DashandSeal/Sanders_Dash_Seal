"""Native Sanders Dash & Seal notarial session state machine.

Records workflow state, not a notarization or a substitute for the commissioned
human notary. External identity/commission and evidence services must supply
verified results before completion can be enabled.
"""
import json
import sqlite3
import time
from pathlib import Path

METHODS = frozenset(("E_NOTARY", "RON"))
STATES = frozenset(("DRAFT", "AWAITING_AUTHORITY", "READY", "COMPLETED", "CANCELLED"))

class NativeNotaryDenied(ValueError):
    pass

class NativeNotarySessions:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_notarial_sessions (
                session_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, method TEXT NOT NULL,
                jurisdiction TEXT NOT NULL, state TEXT NOT NULL, created_at INTEGER NOT NULL,
                completed_at INTEGER, evidence_json TEXT)""")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def create(self, session_id, case_id, method, jurisdiction):
        if any(not isinstance(x, str) or not x or len(x) > 128 for x in (session_id, case_id, jurisdiction)):
            raise NativeNotaryDenied("Valid session, case and jurisdiction identifiers required")
        if method not in METHODS:
            raise NativeNotaryDenied("Unsupported notarial method")
        with self._connect() as db:
            try:
                db.execute("INSERT INTO native_notarial_sessions VALUES (?,?,?,?,?,?,?,?)",
                           (session_id, case_id, method, jurisdiction, "AWAITING_AUTHORITY", int(time.time()), None, None))
            except sqlite3.IntegrityError as exc:
                raise NativeNotaryDenied("Session already exists") from exc
        return self.get(session_id)

    def get(self, session_id):
        with self._connect() as db:
            row = db.execute("SELECT session_id,case_id,method,jurisdiction,state,created_at,completed_at,evidence_json FROM native_notarial_sessions WHERE session_id=?", (session_id,)).fetchone()
        if row is None:
            raise NativeNotaryDenied("Unknown session")
        return dict(zip(("session_id","case_id","method","jurisdiction","state","created_at","completed_at","evidence_json"),row))

    def cancel(self, session_id):
        with self._connect() as db:
            result = db.execute("UPDATE native_notarial_sessions SET state='CANCELLED' WHERE session_id=? AND state IN ('DRAFT','AWAITING_AUTHORITY','READY')", (session_id,))
            if result.rowcount != 1:
                raise NativeNotaryDenied("Session cannot be cancelled")
        return self.get(session_id)

    def complete(self, session_id, *, human_attestation=None, authority_evidence=None, identity_evidence=None, act_evidence=None):
        # Never allow a client-supplied boolean or generic success flag to assert
        # commissioned authority or execution. Completion requires independently
        # integrated and authenticated verification services.
        raise NativeNotaryDenied("Native completion requires independently verified human authority, identity, execution and durable evidence services")
