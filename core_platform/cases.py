"""Sanders Dash & Seal case intake foundation: no simulated notarial authority."""
import re
import sqlite3
import time
from .upgrade_sidecar import require_core_laws

class CaseDenied(Exception):
    pass

class CaseRegistry:
    """Persistent, fail-closed case intake; authorization is never inferred from payment."""
    def __init__(self, db_path, core_laws):
        require_core_laws(core_laws)
        self.db_path = str(db_path)
        with sqlite3.connect(self.db_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS cases
                (case_id TEXT PRIMARY KEY, jurisdiction TEXT NOT NULL,
                 service TEXT NOT NULL, requester TEXT NOT NULL,
                 status TEXT NOT NULL, created_at INTEGER NOT NULL)''')

    def create(self, case_id, jurisdiction, service, requester, *, connection=None):
        if (not all(isinstance(x, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', x)
                    for x in (case_id, jurisdiction, requester))
                or service not in ('MOBILE_NOTARY', 'E_NOTARY', 'RON', 'AUTHORIZED_DOCUMENT_SERVICE')):
            raise CaseDenied('Invalid case identity, jurisdiction or service')
        if connection is not None:
            return self._insert(connection, case_id, jurisdiction, service, requester)
        with sqlite3.connect(self.db_path) as db:
            return self._insert(db, case_id, jurisdiction, service, requester)

    @staticmethod
    def _insert(db, case_id, jurisdiction, service, requester):
        try:
            db.execute('INSERT INTO cases VALUES (?,?,?,?,?,?)',
                       (case_id, jurisdiction, service, requester,
                        'AWAITING_HUMAN_AUTHORITY_REVIEW', int(time.time())))
        except sqlite3.IntegrityError as exc:
            raise CaseDenied('Duplicate case') from exc
        return dict(case_id=case_id, jurisdiction=jurisdiction, service=service,
                    requester=requester, status='AWAITING_HUMAN_AUTHORITY_REVIEW')

    def get(self, case_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute('SELECT case_id,jurisdiction,service,requester,status FROM cases WHERE case_id=?',
                             (case_id,)).fetchone()
        if not row:
            raise CaseDenied('Unknown case')
        return dict(zip(('case_id','jurisdiction','service','requester','status'), row))

    def authorize_notarization(self, *args, **kwargs):
        raise CaseDenied('Independent human identity, commission, jurisdiction and provider verification not connected')
