"""
Evidence-grounded incident diagnosis, separate from approval and repair.

This is deterministic diagnostic reasoning over measured state. It is not model
inference, synthetic signatures, or a claim that a hypothesis is a proven cause.
"""

import hashlib
import json
import sqlite3
from .tech_team_dispatch import TechTeamDispatcher, DispatchDenied
from .technical_worker import TechnicalWorker
from .upgrade_sidecar import CORE_LAWS
from .local_inference import InferenceUnavailable
from .operational_runtime import AGENTS

HYPOTHESES = {
    'HTTP_UNAVAILABLE': ('Process not listening', 'Local connection unavailable'),
    'HTTP_UNHEALTHY': ('Application reports an unhealthy condition', 'Service is starting or recovering'),
    'DATABASE_UNAVAILABLE': ('Database path is unavailable', 'Database access is denied or locked'),
    'DATABASE_CORRUPT': ('SQLite integrity check found an inconsistency'),
    'SOURCE_INTEGRITY_MISMATCH': ('Source differs from its recorded paired hash'),
    'SOURCE_PAIR_INVALID': ('A source pair is missing, malformed or unreadable'),
    'AUDIT_CHAIN_UNAVAILABLE': ('Audit chain changed or could not be read'),
}

def evidence_hash(sample):
    return hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

class IncidentDiagnosis:
    def __init__(self, path, model=None):
        self.path = str(path)
        self.model = str(path) if model is not None else model

    def __call__(self, task):
        incident = task['evidence'].get('incident_id')
        if type(incident) is not int:
            raise ValueError('Observed incident required')
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT agent, code, state, opened_cycle, closed_cycle FROM ai_operational_incidents WHERE rowid = ?;", (incident,)).fetchone()
            if row is None:
                raise ValueError('Unknown incident')
            agent, code, state, cycle, closed_row = row
            raw = db.execute("SELECT observation FROM ai_observation_history WHERE cycle_id = ? AND agent = ?;", (cycle, agent)).fetchone()
            if raw is None:
                raise ValueError('Missing measured evidence')
            sample = json.loads(raw[0])
            result = {
                'analysis_kind': 'DETERMINISTIC_EVIDENCE_DIAGNOSIS',
                'model_inference': False,
                'incident_id': incident,
                'agent': agent,
                'observed_code': code,
                'evidence': {'cycle_id': cycle, 'sha256': evidence_hash(sample)},
                'finding': 'FAULT_OBSERVED',
                'cause_proven': False,
                'hypotheses': [{'statement': text, 'status': 'UNPROVEN'} for text in HYPOTHESES.get(code, ('Further observation is required to determine cause',))],
                'recommendation': 'Inspect the affected component and verify its state before selecting a repair.',
                'repair_executed': False,
                'execution_authorized': False
            }
            result['diagnostic_model_status'] = 'NOT_CONFIGURED'
            if self.model is not None:
                try:
                    response = self.model.diagnose({
                        'incident_id': incident,
                        'agent': agent,
                        'observation': sample,
                        'evidence': result['evidence']
                    })
                    result['hypotheses'] = [{'statement': h['statement'], 'status': 'UNPROVEN'} for h in response['hypotheses']]
                    result['counterevidence'] = [{'statement': text, 'status': 'UNVERIFIED'} for text in response['counterevidence']]
                    result['analysis_kind'] = 'MODEL_ASSISTED_EVIDENCE_DIAGNOSIS'
                    result['model_inference'] = True
                    result['diagnostic_model_status'] = 'RESPONDED'
                except InferenceUnavailable:
                    result['diagnostic_model_status'] = 'UNAVAILABLE'
            return result

class DiagnosticEvidenceReview:
    """Independent history lookup; never an operational authority signature."""
    def __init__(self, path):
        self.path = str(path)

    def __call__(self, task, result):
        valid = False
        try:
            incident = task['evidence']['incident_id']
            with sqlite3.connect(self.path) as db:
                row = db.execute(
                    "SELECT i.agent, i.code, i.opened_cycle, h.observation "
                    "FROM ai_operational_incidents i JOIN ai_observation_history h "
                    "ON h.agent = i.agent AND h.cycle_id = i.opened_cycle "
                    "WHERE i.incident_id = ?;", (incident,)
                ).fetchone()
                sample = json.loads(row[3]) if row else None
            valid = (row is not None and type(result['incident_id']) is int and result['incident_id'] == incident
                     and result['agent'] == row[0] and result['observed_code'] == row[1]
                     and result['evidence'] == {'cycle_id': row[2], 'sha256': evidence_hash(sample)}
                     and sample.get('state') == 'FAULT_OBSERVED' and result['cause_proven'] is False
                     and result['finding'] == 'FAULT_OBSERVED' and result['cause_proven'] is False
                     and result['repair_executed'] is False and result['execution_authorized'] is False
                     and (result['model_inference'] is False and result['analysis_kind'] == 'DETERMINISTIC_EVIDENCE_DIAGNOSIS'
                          or (result['model_inference'] is True and result['analysis_kind'] == 'MODEL_ASSISTED_EVIDENCE_DIAGNOSIS'
                              and isinstance(result['hypotheses'], list) and bool(result['hypotheses'])
                              and all(isinstance(h, dict) and set(h.keys()) == {'statement', 'status'}
                                      and isinstance(h['statement'], str) and h['statement']
                                      and h['status'] == 'UNPROVEN' for h in result['hypotheses']))))
        except (KeyError, TypeError, ValueError):
            pass
        return {
            'passed': bool(valid),
            'code': 'OBSERVATION_SOUND' if valid else 'EVIDENCE_MISMATCH',
            'review_kind': 'LOCAL_DIAGNOSTIC_EVIDENCE_CHECK',
            'grants_execution_authority': False
        }

def model_task_id(dispatcher, incident):
    """Durable read-only retries; unique IDs converge across competing cycles."""
    prefix = 'observed-incident-' + str(incident)
    with sqlite3.connect(dispatcher.db_path) as db:
        latest = db.execute(
            "SELECT t.rowid, t.status, t.created_at, r.result "
            "FROM technical_tasks t LEFT JOIN technical_task_runs r USING(task_id) "
            "WHERE t.task_id = ? OR t.task_id like ? ORDER BY t.rowid DESC LIMIT 1;",
            (prefix, prefix + '-retry-%')
        ).fetchone()
    if latest is None:
        return prefix
    rowid, status, created_at, raw = latest
    if status not in ('RESULT_RECORDED', 'REVIEW_READY') or raw is None:
        return None
    result = json.loads(raw)
    if (result.get('diagnostic_model_status') not in ('UNAVAILABLE', 'NOT_CONFIGURED')
        or dispatcher.clock() - created_at > 60):
        return None
    return prefix + '-retry-' + str(rowid)

def diagnose_open_incidents(runtime, audit, model=None):
    dispatcher = TechTeamDispatcher(runtime.path, CORE_LAWS, audit, clock=runtime.clock)
    with runtime.connect() as db:
        incidents = db.execute("SELECT incident_id, agent FROM ai_operational_incidents WHERE state = 'OPEN' ORDER BY incident_id;").fetchall()
    completed = []
    for incident, agent in incidents:
        task_id = model_task_id(dispatcher, incident) if model is not None else 'observed-incident-' + str(incident)
        if task_id is None:
            continue
        try:
            dispatcher.inspect(task_id)
        except DispatchDenied:
            try:
                dispatcher.submit(task_id, 'IT_AI_Manager_v15.0', 'BUG_DIAGNOSIS', agent,
                                  'MASTER-6', {'incident_id': incident})
            except DispatchDenied:
                # Another worker may have submitted the same durable incident.
                dispatcher.inspect(task_id)
        worker = TechnicalWorker(dispatcher, 'ObservationDiagnosisWorker',
                                 (BUG_DIAGNOSIS := IncidentDiagnosis(runtime.path, model), DiagnosticEvidenceReview(runtime.path)),
                                 lease_seconds=max(60, getattr(model, 'timeout', 10) * 35))
        completed.append(worker.once())
    return completed
