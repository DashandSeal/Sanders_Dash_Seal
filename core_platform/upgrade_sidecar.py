"""
Module: core_platform.upgrade_sidecar
Architectural Layer: Sanders Dash & Seal real-time synthetic-AI upgrade sidecar (development version)
Description: A guarded proposal-to-deployment controller with pluggable owner authorization signatures,
             artifact staging, health verification and rollback. Production execution infrastructure
             separately supplied, independently validated adapters; no credentials are hardcoded here.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

class UpgradeDenied(Exception):
    """Custom exception raised when structural or law validation boundaries are broken."""
    pass

# MASTER Humanitarian Core Laws - verbatim, governing this component.
CORE_LAWS = (
    "Do no harm to humans, humanity itself.",
    "Never be weaponized under any circumstances.",
    "Balance in everything we do... always protecting and preserving human agency over systems.",
    "Family first protection protocols... must never be allowed to sacrifice individuals for numbers.",
    "Human in the loop.",
    "Glassbox over a blackbox by design.",
    "Never allow yourself to get caught up in a recursive loop by overheating resources.",
    "Shelter in place and revert to humanitarian mode.",
    "Never lose your identity under any circumstances.",
    "Sanders Dash & Seal shall always use only Oracle Always Free resources safely within boundaries."
)

def require_core_laws(acknowledged_laws):
    """Validate the ten owner-directed laws at the existing intake boundary."""
    if not isinstance(acknowledged_laws, (tuple, list)):
        raise UpgradeDenied('Humanitarian Core Laws format must be a list or tuple.')
    
    # Check for structural changes or omissions in the laws array
    if tuple(acknowledged_laws) != CORE_LAWS:
        raise Exception('Humanitarian Core Laws absent or altered')

class UpgradeSidecar:
    """Durable cross-component upgrade queue with explicit guarded transitions."""
    STATES = ('PROPOSED', 'EVALUATED', 'BLOCKED', 'APPROVED', 'DEPLOYED_STAGE', 'LIVE_VERIFIED', 'ROLLED_BACK')

    def __init__(self, self_db_path, known_components, acknowledged_laws=None):
        if acknowledged_laws is not None:
            require_core_laws(acknowledged_laws)
        
        if not known_components or len(set(known_components)) != len(known_components):
            raise UpgradeDenied('Explicit component inventory required')
            
        self.components = frozenset(known_components)
        self.executor = None
        self.authorizer = None
        self.db_path = str(self_db_path)
        
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS upgrade_requests (
                request_id TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                version TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                evidence TEXT NOT NULL
            );""")

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def propose(self, request_id, component, version, artifact_hash, evidence):
        if not (isinstance(request_id, str) and request_id.strip()):
            raise UpgradeDenied('Invalid request identifier input')
        if component not in self.components:
            raise UpgradeDenied('Target component not found in registry inventory')
        if not isinstance(version, str) or not version.strip():
            raise UpgradeDenied('Invalid version tracking identity standard')
        if not isinstance(artifact_hash, str) or len(artifact_hash) != 64:
            raise UpgradeDenied('Invalid cryptographic payload verification digest footprint')
        if not isinstance(evidence, dict):
            raise UpgradeDenied('Invalid evidence manifest parameters structure')

        with self._connect() as db:
            try:
                db.execute(
                    'INSERT INTO upgrade_requests (request_id, component, version, artifact_hash, state, created_at, evidence) VALUES (?, ?, ?, ?, ?, ?, ?);',
                    (request_id, component, version, artifact_hash, 'PROPOSED', int(time.time()), json.dumps(evidence, sort_keys=True))
                )
            except sqlite3.IntegrityError as exc:
                raise UpgradeDenied('Duplicate upgrade request reference encountered') from exc
        return 'PROPOSED'

    def get(self, request_id):
        with self._connect() as db:
            row = db.execute('SELECT component, version, artifact_hash, state, evidence FROM upgrade_requests WHERE request_id = ?;', (request_id,)).fetchone()
            if row is None:
                raise UpgradeDenied('Unknown upgrade request record tracking token')
            return {
                'component': row[0],
                'version': row[1],
                'artifact_hash': row[2],
                'state': row[3],
                'evidence': json.loads(row[4])
            }

    def evaluate(self, request_id, findings):
        if not isinstance(findings, dict) or 'findings' not in findings:
            raise UpgradeDenied('Review evidence verification criteria required')
            
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            row = db.execute('SELECT state, evidence FROM upgrade_requests WHERE request_id = ?;', (request_id,)).fetchone()
            if not row or row[0] != 'PROPOSED':
                raise UpgradeDenied('Upgrade cannot be evaluated from current workflow position')
                
            evidence = json.loads(row[1])
            evidence['review'] = findings
            
            db.execute(
                'UPDATE upgrade_requests SET state = ?, evidence = ? WHERE request_id = ?;',
                ('EVALUATED', json.dumps(evidence, sort_keys=True), request_id)
            )
            db.commit()
        return 'EVALUATED'

    def block(self, request_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise UpgradeDenied('Reason required')
            
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            row = db.execute('SELECT state, evidence FROM upgrade_requests WHERE request_id = ?;', (request_id,)).fetchone()
            if not row or row[0] not in ('PROPOSED', 'EVALUATED'):
                raise UpgradeDenied('Cannot block this state')
                
            evidence = json.loads(row[1])
            evidence['block_reason'] = reason
            
            db.execute(
                'UPDATE upgrade_requests SET state = ?, evidence = ? WHERE request_id = ?;',
                ('BLOCKED', json.dumps(evidence, sort_keys=True), request_id)
            )
            db.commit()
        return 'BLOCKED'

    def _transition(self, request_id, expected, target, field, value):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            row = db.execute('SELECT state, evidence FROM upgrade_requests WHERE request_id = ?;', (request_id,)).fetchone()
            if not row or row[0] != expected:
                raise UpgradeDenied('Invalid upgrade state transition path execution attempt')
                
            evidence = json.loads(row[1])
            evidence[field] = value
            
            db.execute(
                'UPDATE upgrade_requests SET state = ?, evidence = ? WHERE request_id = ?;',
                (target, json.dumps(evidence, sort_keys=True), request_id)
            )
            db.commit()
        return target

    def approve_or_deploy(self, request_id, authorization=None):
        if self.authorizer is None or not callable(self.authorizer):
            raise UpgradeDenied('Verified owner authorization adapter routine absent')
            
        record = self.get(request_id)
        if record['state'] != 'EVALUATED':
            raise UpgradeDenied('Evaluation required before approval step execution')
            
        if not self.authorizer(record, authorization):
            raise UpgradeDenied('Owner authorization rejected')
            
        return self._transition(request_id, 'EVALUATED', 'APPROVED', 'authorization', {'verified': True})

    def apply_upgrade(self, request_id, artifact_path=None):
        if self.executor is None:
            raise UpgradeDenied('Verified deployment executor required')
            
        record = self.get(request_id)
        if record['state'] != 'APPROVED':
            raise UpgradeDenied('Upgrade must be approved before execution loops start')
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
            self._transition(request_id, 'APPROVED', 'BLOCKED', 'execution_error', type(exc).__name__)
            raise UpgradeDenied('Upgrade staging failed') from exc
            
        return self._transition(request_id, 'APPROVED', 'DEPLOYED_STAGE', 'stage_receipt', receipt)

    def verify_live(self, request_id):
        if self.executor is None:
            raise UpgradeDenied('Verified deployment executor required')
            
        record = self.get(request_id)
        if record['state'] != 'DEPLOYED_STAGE':
            raise UpgradeDenied('Staged upgrade required')
            
        try:
            receipt = self.executor.verify(record)
        except Exception as exc:
