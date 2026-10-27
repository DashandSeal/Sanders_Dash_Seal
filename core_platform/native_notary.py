"""
Module: core_platform.native_notary
Architectural Layer: Hard-Locked Remote Online Notarization (RON) Session State Machine
Description: Manages and validates local, secure notarial session transitions.
             Enforces strict programmatic gates to prevent state regressions
             or unverified session completions.
"""

import json
import re
import sqlite3
import time
from pathlib import Path

METHODS = frozenset({'E_NOTARY', 'RON'})
STATES = frozenset({'DRAFT', 'AWAITING_AUTHORITY', 'READY', 'COMPLETED'})
IDENT_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

class NativeNotaryDenied(ValueError):
    pass

class NativeNotarySessions:
    """State machine tracker governing local legal notary session data records."""

    def __init__(self, path):
        self.path = str(path)
        parent_dir = Path(self.path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_notarial_sessions (
                session_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                method TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                completed_at INTEGER,
                evidence_json TEXT
            );""")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row  # Enforce explicit Row Factory maps
        return db

    def create(self, session_id, case_id, method, jurisdiction, *, db=None):
        if not all(isinstance(x, str) and IDENT_RE.fullmatch(x) for x in (session_id, case_id, jurisdiction)):
            raise NativeNotaryDenied('Invalid session tracking identity strings')
        if method not in METHODS:
            raise NativeNotaryDenied('Unsupported notarial execution method')

        def insert(conn):
            # Verify parental case row context layout natively inside your database index
            case = conn.execute('SELECT jurisdiction, service FROM cases WHERE case_id=?;', (case_id,)).fetchone()
            if not case or case['service'] != method or case['jurisdiction'] != jurisdiction:
                raise NativeNotaryDenied('Session parameters mismatch with registered case baseline profile')
                
            try:
                conn.execute('INSERT INTO native_notarial_sessions VALUES (?, ?, ?, ?, ?, ?, NULL, NULL);',
                             (session_id, case_id, method, jurisdiction, 'AWAITING_AUTHORITY', int(time.time())))
            except sqlite3.IntegrityError as exc:
                raise NativeNotaryDenied('Session identifier already active') from exc

        if db is not None:
            insert(db)
        else:
            with self._connect() as conn:
                conn.execute('BEGIN IMMEDIATE;')
                insert(conn)
                conn.commit()
        return session_id

    def get(self, session_id):
        if not isinstance(session_id, str) or not IDENT_RE.fullmatch(session_id):
            raise NativeNotaryDenied('Invalid session lookup token format')
            
        with self._connect() as db:
            row = db.execute('SELECT session_id, case_id, method, jurisdiction, state FROM native_notarial_sessions WHERE session_id=?;',
                             (session_id,)).fetchone()
        if row is None:
            raise NativeNotaryDenied('Unknown session record')
        return {key: row[key] for key in row.keys()}

    def cancel(self, session_id):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            result = db.execute("UPDATE native_notarial_sessions SET state='DRAFT' WHERE session_id=? AND state != 'COMPLETED';", (session_id,))
            if result.rowcount != 1:
                raise NativeNotaryDenied('Session state cannot be canceled or modified')
            db.commit()
        return session_id

    def complete(self, session_id, *, human_attestation=None, authority_evidence=None, identity_evidence=None, act_evidence=None):
        """Validates all independent evidence layers natively before sealing the session."""
        if not isinstance(session_id, str) or not IDENT_RE.fullmatch(session_id):
            raise NativeNotaryDenied('Invalid completion target identity handle')

        evidence = {
            'HUMAN_ATTESTATION': human_attestation,
            'COMMISSION': authority_evidence,
            'IDENTITY': identity_evidence,
            'ACT_EXECUTION': act_evidence
        }

        for key, value in evidence.items():
            if not isinstance(value, dict) or not value.get('evidence_id') or not value.get('verified'):
                raise NativeNotaryDenied(f"Structured completion evidence required for layer: {key}")

        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            
            row = db.execute('SELECT method, state FROM native_notarial_sessions WHERE session_id=?;', (session_id,)).fetchone()
            if not row or row['state'] not in ('AWAITING_AUTHORITY', 'READY'):
                raise NativeNotaryDenied('Session state configuration does not permit completion changes')

            method = row['method']
            now = int(time.time())
            
            # Require explicit verification tokens matching your master list constraints
            required = {'IDENTITY', 'COMMISSION', 'JURISDICTION', 'METHOD', 'HUMAN_ATTESTATION', 'ACT_EXECUTION'}
            if method == 'RON':
                # Dynamically append remote online verification checks
                required_list = list(required)
                required_list.append('RON_PROVIDER_AUTHORIZATION')
                required = set(required_list)

            try:
                # FIX: Clean, exception-free lookup utilizing named parameters over the isolated db context
                decisions = db.execute(
                    'SELECT kind, evidence_id, verified_at, expires_at FROM human_authority_reviews WHERE case_id=(SELECT case_id FROM native_notarial_sessions WHERE session_id=?);',
                    (session_id,)).fetchall()
                
                valid_kinds = {d['kind'] for d in decisions if d['verified_at'] <= now <= d['expires_at']}
                if not required.issubset(valid_kinds):
                    raise NativeNotaryDenied('Independent authority evidence registry validation failure')

                for key, value in evidence.items():
                    matching_decisions = [d for d in decisions if d['kind'] == key and d['evidence_id'] == value['evidence_id']]
                    if not matching_decisions:
                        raise NativeNotaryDenied('Completion evidence mismatch against historic audit reviews')

                if method == 'RON':
                    room = db.execute('SELECT state, consent_digest, recording_digest FROM native_ron_rooms WHERE session_id=?;', (session_id,)).fetchone()
                    if not room or room['state'] != 'RECORDING_INDEXED':
                        raise NativeNotaryDenied('RON consent and video recording indexes missing from network rooms')
                        
                    indexed_pairs = db.execute('SELECT kind, sha256 FROM native_evidence_index WHERE session_id=?;', (session_id,)).fetchall()
                    pairs_set = {f"{p['kind']}:{p['sha256']}" for p in indexed_pairs}
                    
                    if f"CONSENT:{room['consent_digest']}" not in pairs_set or f"AV_RECORDING:{room['recording_digest']}" not in pairs_set:
                        raise NativeNotaryDenied('RON evidence ledger mismatch on persistent block volume index')

                db.execute("UPDATE native_notarial_sessions SET state='COMPLETED', completed_at=?, evidence_json=? WHERE session_id=?;",
                           (now, json.dumps(evidence, sort_keys=True), session_id))
                db.commit()
                return {'session_id': session_id, 'status': 'COMPLETED', 'sealed_at': now}
                
            except sqlite3.Error as err:
                db.rollback()
                raise NativeNotaryDenied(f"Database execution layer failure during state transition: {str(err)}") from err
