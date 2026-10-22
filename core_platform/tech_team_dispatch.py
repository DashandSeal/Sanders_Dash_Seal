"""Sanders Dash & Seal IT AI Manager and AI technical-team task dispatch.

Supports multiple bounded technical work types. This is a durable development
dispatcher, not an unrestricted host-command or production authority service.
"""
import json
import re
import sqlite3
import time
from .upgrade_sidecar import require_core_laws

class DispatchDenied(Exception):
    pass

CAPABILITIES = frozenset((
    'FEATURE_DEVELOPMENT', 'BUG_DIAGNOSIS', 'SECURITY_ANALYSIS',
    'DEPENDENCY_ANALYSIS', 'DOCKER_BUILD', 'HOT_SWAP_PLAN',
    'ROLLBACK_PLAN', 'HEALTH_MONITORING', 'INTEGRATION_TEST',
    'INCIDENT_RECOVERY', 'PATENT_EVIDENCE', 'AUDIT_RECONCILIATION',
    'NOTARIAL_WORKFLOW', 'PAYMENT_INTEGRATION', 'FRONTEND_BUILD',
    'BACKEND_BUILD', 'INFRASTRUCTURE_REPAIR'
))
ROLES = frozenset(('IT_AI_Manager_v15.0', 'AI_Tech_Team'))
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')

class TechTeamDispatcher:
    def __init__(self, db_path, core_laws, audit):
        require_core_laws(core_laws)
        self.db_path = str(db_path)
        self.audit = audit
        with sqlite3.connect(self.db_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS technical_tasks
                (task_id TEXT PRIMARY KEY, role TEXT NOT NULL,
                 capability TEXT NOT NULL, component TEXT NOT NULL,
                 specification_ref TEXT NOT NULL, status TEXT NOT NULL,
                 evidence TEXT NOT NULL, created_at INTEGER NOT NULL)''')

    def submit(self, task_id, role, capability, component, specification_ref, evidence):
        if (not all(isinstance(v, str) and ID.fullmatch(v)
                    for v in (task_id, component))
                or role not in ROLES or capability not in CAPABILITIES
                or not isinstance(specification_ref, str) or not specification_ref.strip()
                or not isinstance(evidence, dict)):
            raise DispatchDenied('Invalid technical assignment')
        self.audit.preserve({'stage':'TECH_TASK_INTAKE','task_id':task_id,
                             'role':role,'capability':capability,
                             'component':component,'specification_ref':specification_ref})
        with sqlite3.connect(self.db_path) as db:
            try:
                db.execute('INSERT INTO technical_tasks VALUES (?,?,?,?,?,?,?,?)',
                           (task_id,role,capability,component,specification_ref,
                            'QUEUED',json.dumps(evidence,sort_keys=True),int(time.time())))
            except sqlite3.IntegrityError as exc:
                raise DispatchDenied('Duplicate task') from exc
        return 'QUEUED'

    def inspect(self, task_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute('SELECT role,capability,component,specification_ref,status,evidence FROM technical_tasks WHERE task_id=?',
                             (task_id,)).fetchone()
        if not row:
            raise DispatchDenied('Unknown task')
        return dict(zip(('role','capability','component','specification_ref','status','evidence'),
                        (*row[:5],json.loads(row[5]))))

    def complete_review(self, task_id, result, independent_verification):
        if not isinstance(result, dict) or not isinstance(independent_verification, dict):
            raise DispatchDenied('Structured evidence required')
        if independent_verification.get('passed') is not True:
            raise DispatchDenied('Independent verification required')
        with sqlite3.connect(self.db_path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM technical_tasks WHERE task_id=?',(task_id,)).fetchone()
            if not row or row[0] != 'QUEUED':
                raise DispatchDenied('Invalid task state')
            self.audit.preserve({'stage':'TECH_TASK_VERIFIED','task_id':task_id,
                                 'result':result,'verification':independent_verification})
            db.execute('UPDATE technical_tasks SET status=? WHERE task_id=?',
                       ('REVIEW_READY',task_id))
        return 'REVIEW_READY'
