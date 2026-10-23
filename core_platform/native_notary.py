"""Native Sanders Dash & Seal notarial session state machine.

Records workflow state, not a notarization or a substitute for the commissioned
human notary. External identity/commission and evidence services must supply
verified results before completion can be enabled.
"""
import json
import re
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
        if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', x) for x in (session_id, case_id, jurisdiction)):
            raise NativeNotaryDenied("Valid session, case and jurisdiction identifiers required")
        with self._connect() as db:
            case_table = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cases'").fetchone()
            if case_table:
                case = db.execute("SELECT jurisdiction,service FROM cases WHERE case_id=?", (case_id,)).fetchone()
                if case is None or case != (jurisdiction, method):
                    raise NativeNotaryDenied("Session must match an existing case, method and jurisdiction")
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
        """Record verified native completion against separately registered authority.

        Caller assertions are insufficient: all required authority decisions must
        have been admitted by their independent verifier, still be current, and
        bind to this session. The separate RON evidence index is also checked.
        """
        supplied = {
            'HUMAN_ATTESTATION': human_attestation,
            'COMMISSION': authority_evidence,
            'IDENTITY': identity_evidence,
            'ACT_EXECUTION': act_evidence,
        }
        if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', session_id):
            raise NativeNotaryDenied('Invalid session identity')
        if not all(isinstance(value, dict) and value.get('verified') is True and
                   isinstance(value.get('evidence_id'), str) and
                   re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value['evidence_id'])
                   for value in supplied.values()):
            raise NativeNotaryDenied('Verified completion evidence required')
        evidence = {'human_attestation': human_attestation,
                    'authority_evidence': authority_evidence,
                    'identity_evidence': identity_evidence,
                    'act_evidence': act_evidence}
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT method,state FROM native_notarial_sessions WHERE session_id=?',
                             (session_id,)).fetchone()
            if not row or row[1] not in ('AWAITING_AUTHORITY', 'READY'):
                raise NativeNotaryDenied('Session not available for completion')
            method = row[0]
            now = int(time.time())
            required = {'IDENTITY', 'COMMISSION', 'JURISDICTION', 'METHOD',
                        'HUMAN_ATTESTATION', 'ACT_EXECUTION'}
            if method == 'RON':
                required.add('RON_PROVIDER_AUTHORIZATION')
            try:
                decisions = db.execute(
                    'SELECT kind,evidence_id,verified_at,expires_at FROM native_authority_decisions '
                    'WHERE session_id=?', (session_id,)).fetchall()
                valid = {kind: evidence_id for kind, evidence_id, verified_at, expires_at in decisions
                         if verified_at <= now < expires_at}
                if not required.issubset(valid):
                    raise NativeNotaryDenied('Independent authority evidence incomplete or expired')
                for kind, value in supplied.items():
                    if valid[kind] != value['evidence_id']:
                        raise NativeNotaryDenied('Completion evidence does not match authority registry')
                if method == 'RON':
                    room = db.execute(
                        'SELECT state,consent_digest,recording_digest FROM native_ron_rooms '
                        'WHERE session_id=?', (session_id,)).fetchone()
                    if not room or room[0] != 'RECORDING_INDEXED' or not room[1] or not room[2]:
                        raise NativeNotaryDenied('RON consent and recording evidence incomplete')
                    indexed = db.execute(
                        'SELECT kind,sha256 FROM native_evidence_index WHERE session_id=?',
                        (session_id,)).fetchall()
                    indexed_pairs = set(indexed)
                    if not {('CONSENT', room[1]), ('AV_RECORDING', room[2])}.issubset(indexed_pairs):
                        raise NativeNotaryDenied('RON evidence index does not match consent and recording')
            except sqlite3.OperationalError as exc:
                raise NativeNotaryDenied('Authority or evidence registry unavailable') from exc
            db.execute("UPDATE native_notarial_sessions SET state='COMPLETED',completed_at=?,evidence_json=? "
                       "WHERE session_id=?",
                       (now,json.dumps(evidence,sort_keys=True),session_id))
        return self.get(session_id)
