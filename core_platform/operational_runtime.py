"""
Durable operational observations, incidents and verified recovery history.

Observers are read-only maintenance functions, not independently deployed model
services or authorization authorities. A recovered observation never signs a
lease, changes source, or grants permission to repair a service.
"""

import json
import math
import sqlite3
import time
from pathlib import Path

AGENTS = (
    ("UptimeAgent", "uptime"), ("ApplicationAgent", "application"),
    ("DatabaseAgent", "database"), ("DeploymentAgent", "deployment"),
    ("InfrastructureAgent", "infrastructure"), ("IntegrationAgent", "integration"),
    ("PerformanceAgent", "performance"), ("BackupRecoveryAgent", "backup"),
    ("ObservabilityAgent", "observability"), ("QualityAgent", "quality"),
    ("ConfigurationAgent", "configuration"), ("ITSupportAgent", "support")
)
STATES = frozenset(("HEALTHY", "FAULT", "UNKNOWN"))

class ObservationError(ValueError):
    pass

def validated(value):
    if not isinstance(value, dict) or set(value) != {'state', 'code', 'metrics'}:
        raise ObservationError("Invalid observation")
    if value['state'] not in STATES:
        raise ObservationError("Invalid state")
    if not isinstance(value['code'], str) or not value['code']:
        raise ObservationError("Invalid code")
    if len(value['code']) > 80:
        raise ObservationError("Code too long")
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789" for c in value['code']):
        raise ObservationError("Invalid code characters")
    if not isinstance(value['metrics'], dict):
        raise ObservationError("Invalid metrics")
    # Metric values are counts/durations only. No logs, credentials, identifiers,
    # customer records or model-generated free text enter operational history.
    for key, number in value['metrics'].items():
        if not isinstance(key, str) or not key or len(key) > 64 \
            or not key.replace('_', '').isalnum() \
            or not key.key.replace('_', '').islower() \
            or type(number) not in (int, float) \
            or not math.isfinite(number) or number < 0:
            raise ObservationError("Invalid observation metric")
    raw = json.dumps(value, sort_keys=True, allow_nan=False)
    if len(raw) > 4096:
        raise ObservationError("Oversized observation")
    return json.loads(raw)

def observation(state, code, **metrics):
    return validated({'state': state, 'code': code, 'metrics': metrics})

class OperationalRuntime:
    def __init__(self, path, clock=time.monotonic):
        self.path, self.clock = str(path), clock
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ai_observation_cycles (
                    cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started REAL NOT NULL, finished REAL, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_observer_state (
                    agent TEXT PRIMARY KEY, cycle_id INTEGER NOT NULL,
                    observed REAL NOT NULL, observation TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_operational_incidents (
                    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL, code TEXT NOT NULL, state TEXT NOT NULL,
                    opened_cycle INTEGER NOT NULL, closed_cycle INTEGER
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ai_one_open_incident
                ON ai_operational_incidents(agent) WHERE state='OPEN';
                CREATE TABLE IF NOT EXISTS ai_observation_history (
                    cycle_id INTEGER NOT NULL, agent TEXT NOT NULL,
                    observation TEXT NOT NULL, PRIMARY KEY(cycle_id, agent)
                );
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def cycle(self, observers):
        """Run all twelve observers: one failure does not stop the others.

        A newer committed cycle wins over a slower older cycle. UNKNOWN never
        closes a prior fault. Only a later explicit HEALTHY observation does.
        """
        if not isinstance(observers, dict) or set(observers) != {key for _, key in AGENTS}:
            raise ObservationError("Unknown observer binding")
        with self.connect() as db:
            cycle = db.execute("INSERT INTO ai_observation_cycles (started, state) VALUES (?, 'RUNNING');",
                               (self.clock(),)).lastrowid

        samples = {}
        for agent, key in AGENTS:
            probe = observers.get(key)
            try:
                samples[agent] = (validated(probe()) if callable(probe) else
                                  observation('UNKNOWN', 'OBSERVER_NOT_CONNECTED'))
            except Exception:
                # Exception strings can include URLs, credentials and customer data.
                samples[agent] = observation('UNKNOWN', 'OBSERVER_FAILED')

        now = self.clock()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            newest = db.execute("SELECT MAX(cycle_id) FROM ai_observation_cycles WHERE state='COMPLETED';").fetchone()[0]
            if newest is not None and newest > cycle:
                db.execute("UPDATE ai_observation_cycles SET finished=?,state=? WHERE cycle_id=?;",
                           (now, 'SUPERSEDED', cycle))
                return {'cycle_id': cycle, 'state': 'SUPERSEDED'}
            for agent, sample in samples.items():
                raw = json.dumps(sample, sort_keys=True)
                db.execute("INSERT INTO ai_observation_history VALUES (?,?,?);", (cycle, agent, raw))
                db.execute("INSERT OR REPLACE INTO ai_observer_state VALUES (?,?,?,?);",
                           (agent, cycle, now, raw))
                active = db.execute("SELECT incident_id FROM ai_operational_incidents WHERE agent=? AND state='OPEN';", (agent,)).fetchone()
                if sample['state'] == 'FAULT' and active is None:
                    db.execute("INSERT INTO ai_operational_incidents(agent,code,state,opened_cycle) VALUES (?,?,?,?);",
                               (agent, sample['code'], 'OPEN', cycle))
                elif sample['state'] == 'HEALTHY' and active is not None:
                    db.execute("UPDATE ai_operational_incidents SET state=?,closed_cycle=? WHERE incident_id=?;",
                               ('OBSERVED_RECOVERY', cycle, active[0]))
            db.execute("UPDATE ai_observation_cycles SET finished=?,state=? WHERE cycle_id=?;",
                       (now, 'COMPLETED', cycle))
            return {'cycle_id': cycle, 'state': 'COMPLETED'}

    def status(self):
        now = self.clock()
        with self.connect() as db:
            rows = agent, (cycle, observed, json.loads(raw)) for agent, cycle, observed, raw \
                in db.execute("SELECT agent, cycle_id, observed, observation FROM ai_observer_state;")
            latest = db.execute("SELECT cycle_id, finished FROM ai_observation_cycles WHERE state='COMPLETED' ORDER BY cycle_id DESC;").fetchall()
            incidents = [dict(zip(('incident_id', 'agent', 'code', 'state', 'opened_cycle', 'closed_cycle'), row))
                         for row in db.execute("SELECT incident_id, agent, code, state, opened_cycle, closed_cycle FROM ai_operational_incidents WHERE state!='OBSERVED_RECOVERY';"].fetchall()
            return {
                'platform': 'Sanders Dash & Seal',
                'mode': 'READ_ONLY_OPERATIONAL_OBSERVATION',
                'model_inference': 'NOT_CONNECTED', 'autonomous_repair': 'NOT_CONNECTED',
                'independent_authority_services': 'NOT_CONNECTED',
                'last_completed_cycle': latest[0][0] if latest else None,
                'seconds_since_cycle': max(0, now - latest[0][1]) if latest else None,
                'observed_recoveries': recovered,
                'agents': {agent: {'agent': agent, 'kind': 'READ_ONLY_OBSERVER',
                           'cycle_id': rows.get(agent)[0] if agent in rows else None,
                           'seconds_since_observation': max(0, now - rows[agent][1]) if agent in rows else None,
                           'observation': rows.get(agent)[2] if agent in rows else observation('UNKNOWN', 'NOT_OBSERVED')}
                           for agent, _ in AGENTS},
                'incidents': incidents
            }

def readonly_database(path):
    return sqlite3.connect(Path(path).resolve().as_uri(), uri=True, timeout=2)
