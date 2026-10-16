"""Sanders Dash & Seal real-time synthetic-AI upgrade sidecar (development).

A guarded proposal-to-deployment controller with pluggable owner authorization,
artifact staging, health verification and rollback. Production execution requires
separately supplied, independently validated adapters; no credentials are created.
"""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

class UpgradeDenied(Exception):
    pass

# MASTER Humanitarian Core Laws — verbatim, governing this component.
CORE_LAWS = (
    "Do no harm to humans, humanity itself.",
    "Never be weaponized under any circumstances.",
    "Balance in everything we do… always protecting and preserving humans and humanity itself, however never at the cost of violating laws 1, and 2.",
    "Family fist protection protocols… must never be allowed to sacrifice laws 1,2,3.",
    "Human in the loop.",
    "Glassbox over a blackbox by design.",
    "Never allow yourself to get caught up in a recursive loop by overthinking these laws.",
    "Shelter in place and revert to humanitarian mode.",
    "Never loose your identity under any circumstances.",
)

def require_core_laws(acknowledged_laws):
    """Deny upgrade intake unless the original nine laws are acknowledged exactly.

    Acknowledgment is not proof of semantic compliance or deployment authority.
    """
    if type(acknowledged_laws) not in (tuple, list) or tuple(acknowledged_laws) != CORE_LAWS:
        raise UpgradeDenied('Humanitarian Core Laws absent or altered')

class UpgradeSidecar:
    """Durable cross-component upgrade queue with explicit guarded transitions."""
    STATES = ('PROPOSED', 'EVALUATED', 'BLOCKED', 'APPROVED', 'DEPLOYED_DARK',
              'LIVE_VERIFIED', 'ROLLED_BACK')
    def __init__(self, db_path, known_components, acknowledged_laws=None, executor=None, authorizer=None):
        require_core_laws(acknowledged_laws)
        if not known_components or len(set(known_components)) != len(known_components):
            raise ValueError('Explicit component inventory required')
        self.components = frozenset(known_components)
        self.executor = executor
        self.authorizer = authorizer
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

    def _transition(self, request_id, expected, target, field, value):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT state,evidence FROM upgrade_requests WHERE request_id=?',
                (request_id,)).fetchone()
            if not row or row[0] != expected:
                raise UpgradeDenied('Invalid upgrade state transition')
            evidence = json.loads(row[1])
            evidence[field] = value
            db.execute('UPDATE upgrade_requests SET state=?,evidence=? WHERE request_id=?',
                       (target, json.dumps(evidence, sort_keys=True), request_id))
        return target

    def approve_or_deploy(self, request_id, authorization=None):
        """Owner-authorized, scope-bound promotion to an approved staging state.

        The injected authorizer must verify an external approval; a caller-supplied
        boolean, role label, or unsigned statement never grants authority.
        """
        if self.authorizer is None or not callable(self.authorizer):
            raise UpgradeDenied('Verified owner authorization adapter required')
        record = self.get(request_id)
        if record['state'] != 'EVALUATED':
            raise UpgradeDenied('Evaluation required before approval')
        if not self.authorizer(request_id, record, authorization):
            raise UpgradeDenied('Owner authorization rejected')
        return self._transition(request_id, 'EVALUATED', 'APPROVED',
                                'authorization', {'verified': True})

    def apply_upgrade(self, request_id, artifact_path=None):
        """Stage a verified artifact using an injected, isolated deployment adapter.

        This never evaluates arbitrary source or imports a submitted artifact.
        The adapter is responsible for sandboxing, PBD/Twin-Gate checks,
        containment and the atomic staging transaction.
        """
        if self.executor is None:
            raise UpgradeDenied('Verified deployment executor required')
        record = self.get(request_id)
        if record['state'] != 'APPROVED':
            raise UpgradeDenied('Upgrade must be approved before execution')
        if artifact_path is None:
            raise UpgradeDenied('Artifact required')
        path = Path(artifact_path)
        if not path.is_file() or path.is_symlink():
            raise UpgradeDenied('Regular artifact file required')
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != record['artifact_hash']:
            raise UpgradeDenied('Artifact integrity mismatch')
        try:
            receipt = self.executor.stage(record, str(path))
        except Exception as exc:
            self._transition(request_id, 'APPROVED', 'BLOCKED',
                             'execution_error', type(exc).__name__)
            raise UpgradeDenied('Upgrade staging failed') from exc
        if not isinstance(receipt, dict) or not receipt.get('staged'):
            self._transition(request_id, 'APPROVED', 'BLOCKED',
                             'execution_error', 'Missing staging receipt')
            raise UpgradeDenied('Verified staging receipt required')
        return self._transition(request_id, 'APPROVED', 'DEPLOYED_DARK',
                                'stage_receipt', receipt)

    def verify_live(self, request_id):
        """Promote only after the deployment adapter independently verifies health."""
        if self.executor is None:
            raise UpgradeDenied('Verified deployment executor required')
        record = self.get(request_id)
        if record['state'] != 'DEPLOYED_DARK':
            raise UpgradeDenied('Staged upgrade required')
        try:
            receipt = self.executor.verify(record)
        except Exception as exc:
            raise UpgradeDenied('Live verification failed; rollback required') from exc
        if not isinstance(receipt, dict) or not receipt.get('healthy'):
            raise UpgradeDenied('Live verification failed; rollback required')
        return self._transition(request_id, 'DEPLOYED_DARK', 'LIVE_VERIFIED',
                                'verification_receipt', receipt)

    def rollback(self, request_id):
        """Use the injected executor to restore the prior verified baseline."""
        if self.executor is None:
            raise UpgradeDenied('Verified deployment executor required')
        record = self.get(request_id)
        if record['state'] not in ('DEPLOYED_DARK', 'LIVE_VERIFIED'):
            raise UpgradeDenied('No staged or live upgrade to roll back')
        try:
            receipt = self.executor.rollback(record)
        except Exception as exc:
            raise UpgradeDenied('Rollback failed; isolate component') from exc
        if not isinstance(receipt, dict) or not receipt.get('restored'):
            raise UpgradeDenied('Verified rollback receipt required')
        return self._transition(request_id, record['state'], 'ROLLED_BACK',
                                'rollback_receipt', receipt)
