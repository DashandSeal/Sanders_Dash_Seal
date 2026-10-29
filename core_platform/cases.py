"""
Module: core_platform.cases
Architectural Layer: Hard-Locked Case Intake & Registry Engine
Description: Handles immutable storage, validation, and retrieval for cases.
Enforces strict service constraints and parameter sanitation
to prevent structural database injections.
"""

import re
import sqlite3
import time
from .upgrade_sidecar import require_core_laws

class CaseDenied(Exception):
    """Custom exception raised when structural or security boundaries are violated."""
    pass

# Secure strict alphanumeric identity token validation regex
IDENT_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

VALID_SERVICES = frozenset(('MOBILE_NOTARY', 'E_NOTARY', 'RON', 'AUTHORIZATION'))

class CaseRegistry:
    """Persistent, fail-closed case registry providing sanitized transactions."""

    def __init__(self, db_path, core_laws=None):
        if core_laws is not None:
            require_core_laws(core_laws)
        self.db_path = str(db_path)

        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                jurisdiction TEXT NOT NULL,
                service TEXT NOT NULL,
                requester TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")

    def _connect(self):
        """Initializes a thread-safe connection with an explicit Row Factory."""
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row  # Explicitly force dictionary-like rows
        return db

    def path_or_connection_string(self):
        return self.db_path

    def create(self, case_id, jurisdiction, service, requester, *, db=None):
        """Sanitizes inputs and registers a unique case within the persistent layer."""
        if not all(isinstance(x, str) and IDENT_RE.fullmatch(x) for x in (case_id, jurisdiction, requester)):
            raise CaseDenied('Invalid case identity, jurisdiction, or requester format.')

        if service not in VALID_SERVICES:
            raise CaseDenied('Unsupported or unmapped service profile type.')

        if db is not None:
            return self._execute_insert(db, case_id, jurisdiction, service, requester)
        else:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE;")
                result = self._execute_insert(conn, case_id, jurisdiction, service, requester)
                conn.commit()
                return result

    def _execute_insert(self, db, case_id, jurisdiction, service, requester):
        """Executes the raw database statement safely inside an isolated block."""
        try:
            now = int(time.time())
            db.execute(
                """INSERT INTO cases (case_id, jurisdiction, service, requester, status, created_at)
                   VALUES (?, ?, ?, ?, 'AWAITING_HUMAN_REVIEW', ?);""",
                (case_id, jurisdiction, service, requester, now)
            )
        except sqlite3.IntegrityError as exc:
            raise CaseDenied('Duplicate case: this tracking identifier is already registered.') from exc

        return {
            'case_id': case_id,
            'jurisdiction': jurisdiction,
            'service': service,
            'requester': requester,
            'status': 'AWAITING_HUMAN_REVIEW',
            'created_at': now
        }

    def get(self, case_id):
        """Retrieves an existing case file and parses it cleanly into a dynamic dictionary."""
        if not isinstance(case_id, str) or not IDENT_RE.fullmatch(case_id):
            raise CaseDenied('Invalid case lookup identity token format.')

        with self._connect() as db:
            row = db.execute(
                "SELECT case_id, jurisdiction, service, requester, status, created_at FROM cases WHERE case_id = ?;",
                (case_id,)
            ).fetchone()
            if not row:
                raise CaseDenied('Unknown case: request record not found inside registry index.')

            # Clean, exception-free conversion leveraging sqlite3.Row features
            return dict(row)

    def authorize_notarization(self, case_id, *args, **kwargs):
        """Validates notarization authorization rights for a given case."""
        if not isinstance(case_id, str) or not IDENT_RE.fullmatch(case_id):
            raise CaseDenied('Invalid case identity format for notarization authorization.')
        
        case = self.get(case_id)
        if case['status'] not in ('AWAITING_HUMAN_REVIEW', 'REVIEW_VERIFIED'):
            raise CaseDenied('Case status does not permit notarization authorization.')
        return True
