"""
Module: core_platform.it_ai_manager
Architectural Layer: IT AI Manager — the MASTER §6 dedicated
real-time synthetic AI IT manager platform (MASTER §20:
"operational authority and repair coordination"; a separate
platform — never merged with MINOTAUR, the IT AI Agents, the
Quality Agent, Glass-Box Audit, the Vault, PBDScriptValidation-
Engine, PBDManifestGenerator, or the Global PBD Sentinel).

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (records only, stated exactly): the platform's
designed purpose in the MASTER (Sanders_Dash_Seal_Actual_Build_
Design_MASTER_2026-10-11.md): §6 — Sanders Dash & Seal "has its
own dedicated real-time synthetic AI IT Manager from the
beginning", responsible for keeping the platform "operational,
healthy, repairable, and functional on a day-to-day basis",
with core responsibilities: fault detection and root-cause
diagnosis; service repair and recovery; dependency restoration;
rollback of bad deployments; post-repair state reconciliation;
orchestration of IT AI agents; preservation of glass-box
execution records; and ensuring repaired systems actually
return to a verified operational state. §6 also rules: "The IT
AI Manager is not MINOTAUR and does not replace MINOTAUR's
independent security function." §7 names the agent matrix it
commands (the 12 IT AI agents); §8 step 1 gives it the Twin-
Gate's first gate — the IT AI Manager evaluates operational
necessity (MINOTAUR's independent clearance is step 2 and is
not this platform's to give); §9 names its commanding-authority
version, IT_AI_Manager_v15.0; §10 gives it the final
reconciliation step of the MINOTAUR-denied failover sequence.
Also recovered: the agent matrix as designs in
core_platform/agent_registry.py — the 12 named agents as
AgentDescriptor records under commanding authority
IT_AI_Manager_v15.0, every one implementation_status
INTERFACE_ONLY with external_execution_enabled False. No IT AI
Manager platform module existed in any examined source (the
143-identity reconciliation, catalog row 21). Pre-existing
related components — core_platform/incident_diagnosis.py
(deterministic evidence diagnosis) and
core_platform/tech_team_dispatch.py (a development task
dispatcher) — are separate components; this platform does not
read, wrap, or replace them.

REBUILT (everything executable in this module): the Manager
service below, built 2026-11-24 under the owner's RTSA build
program on the shared foundation (core_platform.rtsa_foundation):
its own platform identity; an incident ledger, a work-order
ledger, a necessity-evaluation ledger, and a verification
ledger in its own store; Glass-Box receipts for every recorded
act inside the ledger transaction; receipted record access
through the foundation AccessGuard; operator-only decisions,
dispatch, rollback, failover recording, verification, and
reconciliation; and operator-only recall-pattern check-in.

HOW THE MANAGER BINDS THE AGENT DESIGNS — stated exactly: the
12 agents exist as designs (agent_registry.py). The Manager
binds those designs: a work order may be dispatched only to a
registered agent name, and every work order records the agent
design's status at dispatch (INTERFACE_ONLY, external execution
disabled). The Manager orchestrates and records; it does not
execute repairs itself and does not claim any agent executed
anything — outcomes enter this ledger as reported records
through the operator surface, and an incident can reach
VERIFIED only through a recorded independent verification
bound to the Quality Agent design (MASTER §8 step 4), and
CLOSED only through the Manager's post-repair reconciliation
(§6, §10). Diagnoses record cause as UNPROVEN until a verified
return proves the repair (the honesty discipline of the
recovered diagnosis component: a hypothesis is not a proven
cause). The Manager's §8 step-1 necessity evaluations are
recorded determinations; MINOTAUR clearance (step 2) is never
recorded by this platform as given — a MINOTAUR denial enters
only as a presented reference on a failover record, exactly as
the Vault records presented authorization metadata.

INCIDENT LIFECYCLE — checked transitions, no step skipped:
OPEN → DIAGNOSED → PLANNED → IN_PROGRESS → REPAIR_REPORTED →
VERIFIED → CLOSED, with REPAIR_REPORTED → IN_PROGRESS when a
return verification reports NOT_VERIFIED, and ROLLED_BACK
(terminal) from PLANNED, IN_PROGRESS, or REPAIR_REPORTED.
REPAIR_REPORTED is reached only when every work order on the
incident is terminal, at least one COMPLETED, and none FAILED.
Work orders: ISSUED → ACKNOWLEDGED → COMPLETED | FAILED, or
ISSUED → COMPLETED | FAILED; COMPLETED and FAILED are terminal.

Fail-closed throughout: a Glass-Box audit adapter is required
at construction — no record, no action. Python standard library
only. No secrets, no network, no external calls.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541513,
541512, 541511, 518210, 541519, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
"""

import json
import secrets
import sqlite3
import time
from pathlib import Path

from .agent_registry import (
    AGENTS,
    IT_AGENT_NAMES,
    IT_MANAGER as MANAGER_VERSION,
    require_registered_agent,
)
from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    latest_check_in as _foundation_latest_check_in,
    record_check_in as _foundation_record_check_in,
    validate_identity,
)


class ITAIManagerDenied(ValueError):
    """The requested Manager operation is invalid or cannot be
    evidenced, so it does not occur."""


class ITAIManagerForbidden(ValueError):
    """The actor lacks authority for this Manager operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='it_ai_manager',
    name='IT AI Manager',
    legal_entities=(),
    naics_codes=('541513', '541512', '541511', '518210', '541519', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The §8 step-4 independent verifier design: return verification
# binds to the Quality Agent, never to the repairing agent and
# never to the Manager itself.
VERIFIER_AGENT = 'Quality Agent'

# The §10 failover and §6 rollback executor design.
DEPLOYMENT_AGENT = 'Deployment Agent'

INCIDENT_STATUSES = (
    'OPEN', 'DIAGNOSED', 'PLANNED', 'IN_PROGRESS',
    'REPAIR_REPORTED', 'VERIFIED', 'CLOSED', 'ROLLED_BACK',
)

_INCIDENT_TRANSITIONS = {
    'OPEN': frozenset(('DIAGNOSED',)),
    'DIAGNOSED': frozenset(('PLANNED',)),
    'PLANNED': frozenset(('IN_PROGRESS', 'ROLLED_BACK')),
    'IN_PROGRESS': frozenset(('REPAIR_REPORTED', 'ROLLED_BACK')),
    'REPAIR_REPORTED': frozenset(
        ('VERIFIED', 'IN_PROGRESS', 'ROLLED_BACK')),
    'VERIFIED': frozenset(('CLOSED',)),
    'CLOSED': frozenset(),
    'ROLLED_BACK': frozenset(),
}

WORK_ORDER_KINDS = ('REPAIR', 'ROLLBACK', 'FAILOVER')
WORK_ORDER_STATUSES = ('ISSUED', 'ACKNOWLEDGED', 'COMPLETED', 'FAILED')
WORK_ORDER_TERMINAL = frozenset(('COMPLETED', 'FAILED'))

_ORDER_TRANSITIONS = {
    'ISSUED': frozenset(('ACKNOWLEDGED', 'COMPLETED', 'FAILED')),
    'ACKNOWLEDGED': frozenset(('COMPLETED', 'FAILED')),
    'COMPLETED': frozenset(),
    'FAILED': frozenset(),
}

NECESSITY_DECISIONS = ('CONFIRMED', 'DENIED')
VERIFICATION_RESULTS = ('VERIFIED_OPERATIONAL', 'NOT_VERIFIED')


class ITAIManager:
    """The REBUILT IT AI Manager service: incident lifecycle,
    root-cause diagnosis records, §8 step-1 operational-necessity
    evaluations, work-order orchestration bound to the 12
    registered agent designs, rollback and §10 failover records,
    independent return verification bound to the Quality Agent
    design, and post-repair reconciliation — every act recorded
    in its own ledgers and receipted to the Glass-Box chain
    inside the ledger transaction."""

    def __init__(self, database, operator_verifier=None, audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ITAIManagerDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'it_ai_manager', {
            'OPERATOR': {'INCIDENT', 'WORK_ORDER', 'EVALUATION', 'STATUS'},
            'AUDITOR': {'INCIDENT', 'WORK_ORDER', 'EVALUATION', 'STATUS'},
            'COORDINATOR': {'INCIDENT', 'WORK_ORDER', 'EVALUATION', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS manager_incidents (
                incident_id TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                symptom TEXT NOT NULL,
                evidence_ref TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                diagnosis TEXT NOT NULL DEFAULT '',
                cause_status TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                closed_at INTEGER
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS manager_work_orders (
                order_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                agent_design_status TEXT NOT NULL,
                kind TEXT NOT NULL,
                task TEXT NOT NULL,
                target TEXT NOT NULL DEFAULT '',
                reference TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                outcome_detail TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS manager_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                target TEXT NOT NULL,
                requesting_agent TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS manager_verifications (
                verification_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                verifier_agent TEXT NOT NULL,
                result TEXT NOT NULL,
                evidence_ref TEXT NOT NULL DEFAULT '',
                actor TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")

    # -- plumbing ----------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row
        return db

    def _is_operator(self, actor):
        if self.operator_verifier is None:
            return False
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    @staticmethod
    def _check_actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise ITAIManagerDenied('Invalid actor identity')

    def _require_operator(self, actor, what):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ITAIManagerForbidden(f'{what} is an operator authority')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    @staticmethod
    def _require_text(value, what):
        if not isinstance(value, str) or not value.strip():
            raise ITAIManagerDenied(f'A non-empty {what} is required')
        return value.strip()

    @staticmethod
    def _registered_agent(name):
        """Bind an agent design from the recovered matrix. An
        unregistered name is denied — the Manager orchestrates
        only the 12 designed agents."""
        if not isinstance(name, str) or not name.strip():
            raise ITAIManagerDenied('An agent name is required')
        try:
            return require_registered_agent(name.strip())
        except PermissionError as exc:
            raise ITAIManagerDenied(
                f'Unknown agent (not in the §7 matrix): {name!r}') from exc

    @staticmethod
    def _incident_view(row):
        return {
            'incident_id': row['incident_id'],
            'component': row['component'],
            'symptom': row['symptom'],
            'evidence_ref': row['evidence_ref'],
            'status': row['status'],
            'diagnosis': row['diagnosis'],
            'cause_status': row['cause_status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'closed_at': row['closed_at'],
        }

    @staticmethod
    def _order_view(row):
        return {
            'order_id': row['order_id'],
            'incident_id': row['incident_id'],
            'agent_name': row['agent_name'],
            'agent_design_status': row['agent_design_status'],
            'kind': row['kind'],
            'task': row['task'],
            'target': row['target'],
            'reference': row['reference'],
            'status': row['status'],
            'outcome_detail': row['outcome_detail'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    @staticmethod
    def _evaluation_view(row):
        return {
            'evaluation_id': row['evaluation_id'],
            'operation': row['operation'],
            'target': row['target'],
            'requesting_agent': row['requesting_agent'],
            'decision': row['decision'],
            'rationale': row['rationale'],
            'actor': row['actor'],
            'created_at': row['created_at'],
        }

    def _incident_row(self, db, incident_id):
        return db.execute(
            "SELECT * FROM manager_incidents WHERE incident_id = ?;",
            (incident_id,)).fetchone()

    def _order_row(self, db, order_id):
        return db.execute(
            "SELECT * FROM manager_work_orders WHERE order_id = ?;",
            (order_id,)).fetchone()

    def _advance_incident(self, db, row, target, now, **updates):
        """One checked incident transition inside the caller's
        transaction. Raises Denied naming the transition when the
        lifecycle does not permit it."""
        current = row['status']
        if target not in _INCIDENT_TRANSITIONS[current]:
            raise ITAIManagerDenied(
                f'Incident transition {current}->{target} is not '
                'permitted')
        fields = {'status': target, 'updated_at': now}
        fields.update(updates)
        assignments = ', '.join(f'{k} = ?' for k in fields)
        db.execute(
            f"UPDATE manager_incidents SET {assignments} "
            "WHERE incident_id = ?;",
            (*fields.values(), row['incident_id']))

    def _create_order(self, db, incident_id, agent_name, kind, task,
                      target, reference, now):
        descriptor = self._registered_agent(agent_name)
        order_id = 'order-' + secrets.token_urlsafe(12)
        db.execute(
            "INSERT INTO manager_work_orders (order_id, "
            "incident_id, agent_name, agent_design_status, kind, "
            "task, target, reference, status, outcome_detail, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, "
            "?, ?, 'ISSUED', '', ?, ?);",
            (order_id, incident_id, descriptor.name,
             descriptor.implementation_status, kind, task, target,
             reference, now, now))
        return order_id

    # -- agent matrix ---------------------------------------------------

    def agent_matrix(self):
        """The 12 IT AI agent designs this Manager orchestrates,
        read from the recovered matrix (core_platform/
        agent_registry.py): name, commanding authority, design
        status, and whether external execution is enabled. The
        Manager binds designs; it does not upgrade their status."""
        return [{
            'name': descriptor.name,
            'commanding_authority': descriptor.commanding_authority,
            'implementation_status': descriptor.implementation_status,
            'external_execution_enabled':
                descriptor.external_execution_enabled,
        } for descriptor in (AGENTS[name] for name in IT_AGENT_NAMES)]

    # -- incidents -------------------------------------------------------

    def report_incident(self, actor, component, symptom, evidence_ref=''):
        """Open an incident (any identified actor): a fault report
        naming the affected component, the observed symptom, and
        an evidence reference. Detection is recorded; no cause is
        claimed at intake."""
        self._check_actor(actor)
        component = self._require_text(component, 'component')
        symptom = self._require_text(symptom, 'symptom')
        if not isinstance(evidence_ref, str):
            raise ITAIManagerDenied('evidence_ref must be a string')
        incident_id = 'inc-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO manager_incidents (incident_id, "
                    "component, symptom, evidence_ref, status, "
                    "diagnosis, cause_status, created_by, "
                    "created_at, updated_at, closed_at) VALUES "
                    "(?, ?, ?, ?, 'OPEN', '', '', ?, ?, ?, NULL);",
                    (incident_id, component, symptom, evidence_ref,
                     actor, now, now))
                self._record('IT_MANAGER_INCIDENT_REPORTED',
                             actor=actor, incident_id=incident_id,
                             component=component)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._incident_view(
                self._incident_row(db, incident_id))

    def diagnose(self, actor, incident_id, diagnosis):
        """Record the root-cause diagnosis (operator-only):
        OPEN → DIAGNOSED. The cause is recorded UNPROVEN — a
        diagnosis is a working determination, proven only by a
        verified return to operational state."""
        self._require_operator(actor, 'Incident diagnosis')
        diagnosis = self._require_text(diagnosis, 'diagnosis')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                self._advance_incident(
                    db, row, 'DIAGNOSED', now, diagnosis=diagnosis,
                    cause_status='UNPROVEN')
                self._record('IT_MANAGER_INCIDENT_DIAGNOSED',
                             actor=actor, incident_id=incident_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._incident_view(
                self._incident_row(db, incident_id))

    # -- §8 step 1: operational necessity --------------------------------

    def evaluate_necessity(self, actor, operation, target,
                           requesting_agent, decision, rationale):
        """Record the Twin-Gate step-1 determination (operator-
        only): whether an operation is operationally necessary.
        The requesting agent must be one of the 12 registered
        designs. This is the Manager's gate only — MINOTAUR's
        independent clearance (step 2) is a separate platform's
        act and is never recorded here as given."""
        self._require_operator(actor, 'Necessity evaluation')
        operation = self._require_text(operation, 'operation')
        target = self._require_text(target, 'target')
        rationale = self._require_text(rationale, 'rationale')
        descriptor = self._registered_agent(requesting_agent)
        if decision not in NECESSITY_DECISIONS:
            raise ITAIManagerDenied(
                f'decision must be one of {NECESSITY_DECISIONS}')
        evaluation_id = 'eval-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO manager_evaluations (evaluation_id, "
                    "operation, target, requesting_agent, decision, "
                    "rationale, actor, created_at) VALUES (?, ?, "
                    "?, ?, ?, ?, ?, ?);",
                    (evaluation_id, operation, target, descriptor.name,
                     decision, rationale, actor, now))
                self._record('IT_MANAGER_NECESSITY_EVALUATED',
                             actor=actor, evaluation_id=evaluation_id,
                             operation=operation, target=target,
                             requesting_agent=descriptor.name,
                             decision=decision)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM manager_evaluations WHERE "
                "evaluation_id = ?;", (evaluation_id,)).fetchone()
            return self._evaluation_view(row)

    # -- work orders -------------------------------------------------------

    def dispatch_work_order(self, actor, incident_id, agent_name,
                            task, target=''):
        """Dispatch one repair work order (operator-only) bound
        to a registered agent design. The first dispatch advances
        the incident DIAGNOSED → PLANNED. The order records the
        design's status (INTERFACE_ONLY): dispatch is the
        Manager's recorded act of orchestration, not a claim that
        the agent executed anything."""
        self._require_operator(actor, 'Work-order dispatch')
        task = self._require_text(task, 'task')
        if not isinstance(target, str):
            raise ITAIManagerDenied('target must be a string')
        descriptor = self._registered_agent(agent_name)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                if row['status'] not in ('DIAGNOSED', 'PLANNED',
                                         'IN_PROGRESS'):
                    raise ITAIManagerDenied(
                        f"Work orders cannot be dispatched while "
                        f"the incident is {row['status']}")
                order_id = self._create_order(
                    db, incident_id, descriptor.name, 'REPAIR', task,
                    target, '', now)
                if row['status'] == 'DIAGNOSED':
                    self._advance_incident(db, row, 'PLANNED', now)
                self._record('IT_MANAGER_WORK_ORDER_DISPATCHED',
                             actor=actor, incident_id=incident_id,
                             order_id=order_id,
                             agent_name=descriptor.name)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._order_view(self._order_row(db, order_id))

    def record_outcome(self, actor, order_id, outcome, detail=''):
        """Record a work order's reported outcome (operator-only):
        ACKNOWLEDGED, COMPLETED, or FAILED, as a checked
        transition. The first outcome advances the incident
        PLANNED → IN_PROGRESS; when every order on the incident
        is terminal with at least one COMPLETED and none FAILED,
        the incident advances IN_PROGRESS → REPAIR_REPORTED
        inside the same transaction."""
        self._require_operator(actor, 'Work-order outcomes')
        if outcome not in WORK_ORDER_STATUSES or \
                outcome == 'ISSUED':
            raise ITAIManagerDenied(
                'outcome must be ACKNOWLEDGED, COMPLETED, or FAILED')
        if not isinstance(detail, str):
            raise ITAIManagerDenied('detail must be a string')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._order_row(db, order_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown work order')
                if outcome not in _ORDER_TRANSITIONS[row['status']]:
                    raise ITAIManagerDenied(
                        f"Work-order transition {row['status']}->"
                        f'{outcome} is not permitted')
                db.execute(
                    "UPDATE manager_work_orders SET status = ?, "
                    "outcome_detail = ?, updated_at = ? WHERE "
                    "order_id = ?;", (outcome, detail, now, order_id))
                incident = self._incident_row(db, row['incident_id'])
                if incident['status'] == 'PLANNED':
                    self._advance_incident(
                        db, incident, 'IN_PROGRESS', now)
                    incident = self._incident_row(db, row['incident_id'])
                if incident['status'] == 'IN_PROGRESS':
                    orders = db.execute(
                        "SELECT status FROM manager_work_orders "
                        "WHERE incident_id = ?;",
                        (row['incident_id'],)).fetchall()
                    statuses = [o['status'] for o in orders]
                    if statuses and all(
                            s in WORK_ORDER_TERMINAL for s in statuses) \
                            and 'COMPLETED' in statuses \
                            and 'FAILED' not in statuses:
                        self._advance_incident(
                            db, incident, 'REPAIR_REPORTED', now)
                self._record('IT_MANAGER_WORK_ORDER_OUTCOME',
                             actor=actor, order_id=order_id,
                             incident_id=row['incident_id'],
                             outcome=outcome)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._order_view(self._order_row(db, order_id))

    def order_rollback(self, actor, incident_id, reason):
        """Order a rollback of a bad deployment (operator-only,
        §6): creates a ROLLBACK work order bound to the Deployment
        Agent design and closes the incident ROLLED_BACK. The
        rollback order's own outcome remains recordable — the
        incident's terminal state does not erase the order."""
        self._require_operator(actor, 'Rollback orders')
        reason = self._require_text(reason, 'rollback reason')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                if row['status'] not in ('PLANNED', 'IN_PROGRESS',
                                         'REPAIR_REPORTED'):
                    raise ITAIManagerDenied(
                        f"Rollback cannot be ordered while the "
                        f"incident is {row['status']}")
                order_id = self._create_order(
                    db, incident_id, DEPLOYMENT_AGENT, 'ROLLBACK',
                    'ROLLBACK: ' + reason, '', reason, now)
                self._advance_incident(
                    db, row, 'ROLLED_BACK', now, closed_at=now)
                self._record('IT_MANAGER_ROLLBACK_ORDERED',
                             actor=actor, incident_id=incident_id,
                             order_id=order_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._order_view(self._order_row(db, order_id))

    def record_failover(self, actor, incident_id,
                        minotaur_decision_ref, note=''):
        """Record a MINOTAUR-denied failover (operator-only, §10):
        the denial enters as a PRESENTED reference — recorded,
        never verified or fabricated by this platform — and the
        Manager opens the failover work order bound to the
        Deployment Agent design ("activate known-safe failover
        route"). Per §10 the denied path gets no token, no
        bypass, and no retry with broader privileges; this record
        is the Manager's step in the prescribed sequence."""
        self._require_operator(actor, 'Failover recording')
        minotaur_decision_ref = self._require_text(
            minotaur_decision_ref, 'MINOTAUR decision reference')
        if not isinstance(note, str):
            raise ITAIManagerDenied('note must be a string')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                if row['status'] not in ('DIAGNOSED', 'PLANNED',
                                         'IN_PROGRESS'):
                    raise ITAIManagerDenied(
                        f"Failover cannot be recorded while the "
                        f"incident is {row['status']}")
                task = 'FAILOVER: activate known-safe failover route'
                if note.strip():
                    task += ' — ' + note.strip()
                order_id = self._create_order(
                    db, incident_id, DEPLOYMENT_AGENT, 'FAILOVER',
                    task, '', minotaur_decision_ref, now)
                if row['status'] == 'DIAGNOSED':
                    self._advance_incident(db, row, 'PLANNED', now)
                self._record('IT_MANAGER_FAILOVER_RECORDED',
                             actor=actor, incident_id=incident_id,
                             order_id=order_id,
                             minotaur_decision_ref=minotaur_decision_ref)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._order_view(self._order_row(db, order_id))

    # -- verified return and reconciliation ------------------------------

    def verify_return(self, actor, incident_id, result, evidence_ref=''):
        """Record the independent return verification (operator-
        only): bound to the Quality Agent design (§8 step 4) —
        the verifier is never the repairing agent and never the
        Manager itself. VERIFIED_OPERATIONAL advances the
        incident REPAIR_REPORTED → VERIFIED and proves the
        recorded diagnosis (cause_status PROVEN); NOT_VERIFIED
        returns it to IN_PROGRESS for further repair."""
        self._require_operator(actor, 'Return verification')
        if result not in VERIFICATION_RESULTS:
            raise ITAIManagerDenied(
                f'result must be one of {VERIFICATION_RESULTS}')
        if not isinstance(evidence_ref, str):
            raise ITAIManagerDenied('evidence_ref must be a string')
        verification_id = 'ver-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                if row['status'] != 'REPAIR_REPORTED':
                    raise ITAIManagerDenied(
                        f"Return verification requires "
                        f"REPAIR_REPORTED; the incident is "
                        f"{row['status']}")
                db.execute(
                    "INSERT INTO manager_verifications "
                    "(verification_id, incident_id, verifier_agent, "
                    "result, evidence_ref, actor, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (verification_id, incident_id, VERIFIER_AGENT,
                     result, evidence_ref, actor, now))
                if result == 'VERIFIED_OPERATIONAL':
                    self._advance_incident(
                        db, row, 'VERIFIED', now, cause_status='PROVEN')
                else:
                    self._advance_incident(db, row, 'IN_PROGRESS', now)
                self._record('IT_MANAGER_RETURN_VERIFICATION',
                             actor=actor, incident_id=incident_id,
                             verification_id=verification_id,
                             verifier_agent=VERIFIER_AGENT,
                             result=result)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._incident_view(
                self._incident_row(db, incident_id))

    def reconcile(self, actor, incident_id):
        """Post-repair state reconciliation (operator-only, §6
        and §10's final step): VERIFIED → CLOSED. An incident
        closes only after a verified return — never on a repair
        report alone."""
        self._require_operator(actor, 'Incident reconciliation')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._incident_row(db, incident_id)
                if row is None:
                    raise ITAIManagerDenied('Unknown incident')
                self._advance_incident(db, row, 'CLOSED', now,
                                       closed_at=now)
                self._record('IT_MANAGER_INCIDENT_RECONCILED',
                             actor=actor, incident_id=incident_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._incident_view(
                self._incident_row(db, incident_id))

    # -- receipted views ---------------------------------------------------

    def incident_view(self, actor, role, incident_id):
        """Serve one incident under the access guard: access is
        authorized and receipted FIRST, then the record is
        fetched and served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'INCIDENT', incident_id,
                              purpose='incident view')
        except FoundationForbidden as exc:
            raise ITAIManagerForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ITAIManagerDenied(str(exc)) from exc
        with self._connect() as db:
            row = self._incident_row(db, incident_id)
            if row is None:
                raise ITAIManagerDenied('Unknown incident')
            return self._incident_view(row)

    def work_order_view(self, actor, role, order_id):
        """Serve one work order under the access guard (receipt
        first, record second)."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'WORK_ORDER', order_id,
                              purpose='work order view')
        except FoundationForbidden as exc:
            raise ITAIManagerForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ITAIManagerDenied(str(exc)) from exc
        with self._connect() as db:
            row = self._order_row(db, order_id)
            if row is None:
                raise ITAIManagerDenied('Unknown work order')
            return self._order_view(row)

    def evaluation_view(self, actor, role, evaluation_id):
        """Serve one necessity evaluation under the access guard
        (receipt first, record second)."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'EVALUATION', evaluation_id,
                              purpose='evaluation view')
        except FoundationForbidden as exc:
            raise ITAIManagerForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ITAIManagerDenied(str(exc)) from exc
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM manager_evaluations WHERE "
                "evaluation_id = ?;", (evaluation_id,)).fetchone()
            if row is None:
                raise ITAIManagerDenied('Unknown evaluation')
            return self._evaluation_view(row)

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to
        the platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ITAIManagerForbidden(
                'Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise ITAIManagerDenied(str(exc)) from exc
                self._record('IT_MANAGER_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    # -- status --------------------------------------------------------

    def status(self):
        """Platform status: identity, the Manager version, the
        agent matrix size, incident counts by status, work-order
        counts by status, necessity-evaluation counts by
        decision, and the latest check-in."""
        with self._connect() as db:
            incidents = {s: 0 for s in INCIDENT_STATUSES}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM "
                    "manager_incidents GROUP BY status;").fetchall():
                if row['status'] in incidents:
                    incidents[row['status']] = row['n']
            orders = {s: 0 for s in WORK_ORDER_STATUSES}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM "
                    "manager_work_orders GROUP BY status;").fetchall():
                if row['status'] in orders:
                    orders[row['status']] = row['n']
            evaluations = {d: 0 for d in NECESSITY_DECISIONS}
            for row in db.execute(
                    "SELECT decision, COUNT(*) AS n FROM "
                    "manager_evaluations GROUP BY decision;").fetchall():
                if row['decision'] in evaluations:
                    evaluations[row['decision']] = row['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'manager_version': MANAGER_VERSION,
            'agent_count': len(IT_AGENT_NAMES),
            'incident_counts': incidents,
            'work_order_counts': orders,
            'evaluation_counts': evaluations,
            'latest_check_in': latest,
        }
