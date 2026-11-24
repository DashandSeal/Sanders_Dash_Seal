"""
Module: core_platform.native_case_bridge
Architectural Layer: Case-to-Native-Session Bridge
Description: The designed link between a paid customer case and the
platform's own native notarial session chain. For a case whose payment
has settled in the Stripe ledger, an operator opens the corresponding
NativeNotarySessions record; the bridge binds case and session ids
durably, mirrors the session's state, and when the native session
completes it propagates that completion back to the case record
(cases.status becomes NATIVE_SESSION_COMPLETED, a state every other
consumer treats fail-closed: no further quote, checkout, review or
provider submission is permitted against a completed case).

Service-to-method mapping: RON cases open RON sessions. MOBILE_NOTARY
cases open E_NOTARY sessions: the native chain is the platform's
electronic session/evidence layer, and the mobile act's records are
kept in that same layer. AUTHORIZED_DOCUMENT_SERVICE involves no
notarial act and has no native session mapping; the bridge denies it
rather than inventing one.

Fail-closed throughout: an unpaid case opens nothing, a non-operator
opens nothing, an unknown case opens nothing, and an uncertain state
is reported as recorded, never auto-advanced.
"""

import hashlib
import re
import sqlite3
import time
from pathlib import Path

from .cases import CaseDenied
from .native_notary import NativeNotaryDenied

ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$', re.ASCII)
SERVICE_METHODS = {'RON': 'RON', 'MOBILE_NOTARY': 'E_NOTARY'}
COMPLETED_CASE_STATUS = 'NATIVE_SESSION_COMPLETED'


class BridgeDenied(ValueError):
    pass


class CaseNativeBridge:
    """Durable case <-> native session binding with state propagation."""

    def __init__(self, database, cases, ledger, sessions,
                 operator_verifier, audit):
        if not all(callable(v) for v in
                   (operator_verifier, audit.preserve)):
            raise BridgeDenied('Independent operator and audit adapters required')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.cases = cases
        self.ledger = ledger
        self.sessions = sessions
        self.operator_verifier = operator_verifier
        self.audit = audit
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS case_native_sessions (
                case_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                method TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _session_id_for(case_id):
        candidate = 'ns-' + case_id
        if len(candidate) <= 128:
            return candidate
        digest = hashlib.sha256(case_id.encode('utf-8')).hexdigest()
        return 'ns-' + digest[:32]

    def _link(self, case_id):
        with self._connect() as db:
            row = db.execute(
                "SELECT case_id, session_id, method, state, created_at, "
                "updated_at FROM case_native_sessions WHERE case_id = ?;",
                (case_id,)).fetchone()
        return dict(row) if row is not None else None

    def open_session(self, case_id, actor):
        """Open the native session for a settled case (operator only).

        Idempotent: a case that already has a session returns its
        existing binding, refreshed, instead of opening a second one.
        """
        if not isinstance(case_id, str) or not ID.fullmatch(case_id):
            raise BridgeDenied('Invalid case identity')
        try:
            authorized = self.operator_verifier(actor) is True
        except Exception:
            authorized = False
        if not authorized:
            raise BridgeDenied('Operator authority required')
        existing = self._link(case_id)
        if existing is not None:
            return self.refresh(case_id)
        try:
            case = self.cases.get(case_id)
        except CaseDenied as exc:
            raise BridgeDenied('Unknown case') from exc
        if self.ledger.status(case_id) != 'PAID':
            raise BridgeDenied(
                'Case payment has not settled; a native session '
                'requires settled payment')
        method = SERVICE_METHODS.get(str(case.get('service', '')).upper())
        if method is None:
            raise BridgeDenied(
                'Service has no native notarial session mapping')
        session_id = self._session_id_for(case_id)
        try:
            self.sessions.create(session_id, case_id, method,
                                 case['jurisdiction'])
        except NativeNotaryDenied as exc:
            raise BridgeDenied(str(exc)) from exc
        session = self.sessions.get(session_id)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            db.execute(
                "INSERT INTO case_native_sessions "
                "(case_id, session_id, method, state, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (case_id, session_id, method, session['state'], now, now))
            db.commit()
        self.audit.preserve({
            'event': 'CASE_NATIVE_SESSION_OPENED',
            'case_id': case_id,
            'session_id': session_id,
            'method': method,
        })
        return self._link(case_id)

    def refresh(self, case_id):
        """Mirror the bound session's state; propagate completion.

        Returns the binding record, or None when the case has no
        native session. When the session has completed and the case
        does not yet say so, the case record is updated to
        NATIVE_SESSION_COMPLETED in the same step.
        """
        if not isinstance(case_id, str) or not ID.fullmatch(case_id):
            raise BridgeDenied('Invalid case identity')
        link = self._link(case_id)
        if link is None:
            return None
        session = self.sessions.get(link['session_id'])
        state = session['state']
        if state != link['state']:
            now = int(time.time())
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE;")
                db.execute(
                    "UPDATE case_native_sessions SET state = ?, "
                    "updated_at = ? WHERE case_id = ?;",
                    (state, now, case_id))
                db.commit()
            link = dict(link, state=state, updated_at=now)
        if state == 'COMPLETED':
            self._propagate_completion(case_id)
        return link

    def _propagate_completion(self, case_id):
        with sqlite3.connect(self.cases.db_path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE;")
            db.execute(
                "UPDATE cases SET status = ? WHERE case_id = ? "
                "AND status != ?;",
                (COMPLETED_CASE_STATUS, case_id, COMPLETED_CASE_STATUS))
            db.commit()

    def status_for_case(self, case_id):
        """Operator-facing view: the refreshed binding, or None."""
        return self.refresh(case_id)
