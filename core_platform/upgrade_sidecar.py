"""Sanders Dash & Seal real-time synthetic-AI upgrade sidecar (development).

An always-on *proposal intake*, not autonomous production modification.
The MASTER Twin-Gate/PBD, human release, Glass-Box, and rollback controls remain
authoritative. The sidecar cannot deploy, execute code, or create credentials.
"""
import hashlib
import json
import sqlite3
import time

class UpgradeDenied(Exception):
    pass

class UpgradeSidecar:
    """Durable cross-component upgrade queue with explicit guarded transitions."""
    STATES = ('PROPOSED', 'EVALUATED', 'BLOCKED', 'APPROVED', 'DEPLOYED_DARK',
              'LIVE_VERIFIED', 'ROLLED_BACK')
    def __init__(self, db_path, known_components):
        if not known_components or len(set(known_components)) != len(known_components):
            raise ValueError('Explicit component inventory required')
        self.components = frozenset(known_components)
        self.db_path = str(db_path)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS upgrade_requests
              (request_id TEXT PRIMARY KEY, component TEXT NOT NULL,
               version TEXT NOT NULL, artifact_hash TEXT NOT NULL,
               state TEXT NOT NULL, created_at INTEGER NOT NULL,
               evidence TEXT NOT NULL)''')

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def propose(self, request_id, component, version, artifact_hash, evidence):
        if (not isinstance(request_id, str) or not request_id.strip()
                or component not in self.components
                or not isinstance(version, str) or not version.strip()
                or not isinstance(artifact_hash, str) or len(artifact_hash) != 64
                or any(c not in '0123456789abcdef' for c in artifact_hash)
                or not isinstance(evidence, dict)):
            raise UpgradeDenied('Invalid or unregistered upgrade proposal')
        with self._connect() as db:
            try:
                db.execute('INSERT INTO upgrade_requests VALUES (?,?,?,?,?,?,?)',
                           (request_id, component, version, artifact_hash,
                            'PROPOSED', int(time.time()),
                            json.dumps(evidence, sort_keys=True)))
            except sqlite3.IntegrityError as exc:
                raise UpgradeDenied('Duplicate upgrade request') from exc
        return 'PROPOSED'

    def get(self, request_id):
        with self._connect() as db:
            row = db.execute('SELECT component,version,artifact_hash,state,evidence FROM upgrade_requests WHERE request_id=?',
                             (request_id,)).fetchone()
        if row is None:
            raise UpgradeDenied('Unknown upgrade request')
        return {'component':row[0], 'version':row[1],
                'artifact_hash':row[2], 'state':row[3],
                'evidence':json.loads(row[4])}

    def evaluate(self, request_id, findings):
        """Store a review; AI-generated findings never count as authority."""
        if not isinstance(findings, dict) or not findings:
            raise UpgradeDenied('Review evidence required')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state,evidence FROM upgrade_requests WHERE request_id=?',
                             (request_id,)).fetchone()
            if not row or row[0] != 'PROPOSED':
                raise UpgradeDenied('Upgrade cannot be evaluated from this state')
            evidence = json.loads(row[1])
            evidence['review'] = findings
            db.execute('UPDATE upgrade_requests SET state=?,evidence=? WHERE request_id=?',
                       ('EVALUATED', json.dumps(evidence, sort_keys=True), request_id))
        return 'EVALUATED'

    def block(self, request_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise UpgradeDenied('Reason required')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state,evidence FROM upgrade_requests WHERE request_id=?',
                             (request_id,)).fetchone()
            if not row or row[0] not in ('PROPOSED', 'EVALUATED'):
                raise UpgradeDenied('Cannot block this state')
            evidence = json.loads(row[1])
            evidence['block_reason'] = reason
            db.execute('UPDATE upgrade_requests SET state=?,evidence=? WHERE request_id=?',
                       ('BLOCKED', json.dumps(evidence, sort_keys=True), request_id))
        return 'BLOCKED'

    def approve_or_deploy(self, *args, **kwargs):
        """Production promotion is deliberately unavailable without real authority."""
        raise UpgradeDenied('Twin-Gate PBD and human production release required')

    def apply_upgrade(self, *args, **kwargs):
        raise UpgradeDenied('Sidecar cannot execute or deploy an upgrade')
