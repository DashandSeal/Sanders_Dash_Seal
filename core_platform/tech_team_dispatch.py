"""Sanders Dash & Seal IT AI Manager and AI technical-team task dispatch.

Supports multiple bounded technical work types. This is a durable development
dispatcher, not an unrestricted host-command or production authority service.
"""
import json
import re
import sqlite3
import time
import secrets
import math
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
READ_ONLY_CAPABILITIES = frozenset(('BUG_DIAGNOSIS', 'HEALTH_MONITORING',
    'DEPENDENCY_ANALYSIS', 'SECURITY_ANALYSIS', 'HOT_SWAP_PLAN', 'ROLLBACK_PLAN',
    'PATENT_EVIDENCE', 'AUDIT_RECONCILIATION'))
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')

class TechTeamDispatcher:
    def __init__(self, db_path, core_laws, audit, *, clock=time.time):
        require_core_laws(core_laws)
        self.db_path = str(db_path)
        self.audit = audit
        self.clock = clock
        with sqlite3.connect(self.db_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS technical_tasks
                (task_id TEXT PRIMARY KEY, role TEXT NOT NULL,
                 capability TEXT NOT NULL, component TEXT NOT NULL,
                 specification_ref TEXT NOT NULL, status TEXT NOT NULL,
                 evidence TEXT NOT NULL, created_at INTEGER NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS technical_task_runs
                (task_id TEXT PRIMARY KEY, worker TEXT NOT NULL, claim TEXT NOT NULL,
                 deadline REAL NOT NULL, attempts INTEGER NOT NULL,
                 result TEXT, verification TEXT, error_code TEXT)''')

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
                            'QUEUED',json.dumps(evidence,sort_keys=True,allow_nan=False),int(self.clock())))
            except sqlite3.IntegrityError as exc:
                raise DispatchDenied('Duplicate task') from exc
        return 'QUEUED'

    def inspect(self, task_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute('SELECT role,capability,component,specification_ref,status,evidence FROM technical_tasks WHERE task_id=?',
                             (task_id,)).fetchone()
        if not row:
            raise DispatchDenied('Unknown task')
        result=dict(zip(('role','capability','component','specification_ref','status','evidence'),
                        (*row[:5],json.loads(row[5]))))
        with sqlite3.connect(self.db_path) as db:
            run=db.execute('SELECT worker,attempts,result,verification,error_code FROM technical_task_runs WHERE task_id=?',(task_id,)).fetchone()
        if run:
            result['execution']={'worker':run[0],'attempts':run[1],
                'result':json.loads(run[2]) if run[2] else None,
                'verification':json.loads(run[3]) if run[3] else None,'error_code':run[4]}
        return result

    def list_tasks(self):
        with sqlite3.connect(self.db_path) as db:
            ids=[row[0] for row in db.execute('SELECT task_id FROM technical_tasks ORDER BY created_at DESC,rowid DESC LIMIT 100')]
        return [{'task_id':task_id,**self.inspect(task_id)} for task_id in ids]

    def claim_next(self, worker, capabilities, *, lease_seconds=60):
        """Ownership of read-only analysis work; never a privileged Vault lease."""
        if (not isinstance(worker,str) or not ID.fullmatch(worker)
                or not isinstance(capabilities,(set,frozenset)) or not capabilities
                or not capabilities.issubset(READ_ONLY_CAPABILITIES)
                or type(lease_seconds) not in (int,float)
                or not math.isfinite(lease_seconds) or lease_seconds<=0):
            raise DispatchDenied('Registered read-only worker and lease required')
        with sqlite3.connect(self.db_path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('''SELECT t.task_id,t.capability,r.deadline
                FROM technical_tasks t LEFT JOIN technical_task_runs r USING(task_id)
                WHERE t.status IN ('QUEUED','RUNNING') ORDER BY t.created_at,t.rowid''').fetchall()
            selected=next((task_id for task_id,capability,deadline in rows
                if capability in capabilities and (deadline is None or deadline<=self.clock())),None)
            if selected is None:return None
            token=secrets.token_hex(32)
            db.execute('''INSERT INTO technical_task_runs(task_id,worker,claim,deadline,attempts)
                VALUES (?,?,?,?,1) ON CONFLICT(task_id) DO UPDATE SET
                worker=excluded.worker,claim=excluded.claim,deadline=excluded.deadline,
                attempts=technical_task_runs.attempts+1,result=NULL,verification=NULL,error_code=NULL''',
                (selected,worker,token,self.clock()+lease_seconds))
            db.execute('UPDATE technical_tasks SET status=? WHERE task_id=?',('RUNNING',selected))
        return {'task_id':selected,'claim':token,'task':self.inspect(selected)}

    def finish(self, task_id, claim, result, verification):
        if not isinstance(result,dict) or not result or not isinstance(verification,dict):
            raise DispatchDenied('Structured task result and verification required')
        raw=json.dumps(result,sort_keys=True,allow_nan=False)
        review=json.dumps(verification,sort_keys=True,allow_nan=False)
        if len(raw.encode())>65536 or len(review.encode())>8192:
            raise DispatchDenied('Task evidence exceeds allocation')
        with sqlite3.connect(self.db_path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('''SELECT t.status,r.claim,r.deadline FROM technical_tasks t
                JOIN technical_task_runs r USING(task_id) WHERE t.task_id=?''',(task_id,)).fetchone()
            if not row or row[0]!='RUNNING' or row[1]!=claim or row[2]<=self.clock():
                raise DispatchDenied('Task ownership expired or changed')
            status='REVIEW_READY' if verification.get('passed') is True else 'RESULT_RECORDED'
            self.audit.preserve({'stage':'TECH_TASK_RESULT','task_id':task_id,
                'result':result,'verification':verification,'status':status})
            db.execute('UPDATE technical_task_runs SET result=?,verification=? WHERE task_id=?',(raw,review,task_id))
            db.execute('UPDATE technical_tasks SET status=? WHERE task_id=?',(status,task_id))
        return status

    def fail(self, task_id, claim):
        # Do not persist arbitrary handler exception messages or retry mutations.
        with sqlite3.connect(self.db_path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('''SELECT r.claim,r.deadline,t.status FROM technical_task_runs r
                JOIN technical_tasks t USING(task_id) WHERE task_id=?''',(task_id,)).fetchone()
            if not row or row[0]!=claim or row[1]<=self.clock() or row[2]!='RUNNING':
                raise DispatchDenied('Task ownership expired or changed')
            self.audit.preserve({'stage':'TECH_TASK_FAILED','task_id':task_id,'error_code':'HANDLER_FAILED'})
            db.execute('UPDATE technical_task_runs SET error_code=? WHERE task_id=?',('HANDLER_FAILED',task_id))
            db.execute('UPDATE technical_tasks SET status=? WHERE task_id=? AND status=?',('FAILED',task_id,'RUNNING'))

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
