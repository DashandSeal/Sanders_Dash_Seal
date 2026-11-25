"""Uptime Agent — the keep-services-up IT AI agent platform.

The production build-out of the Uptime Agent design (MASTER
§7 IT AI Agent Matrix; ``core_platform/agent_registry.py``:
"Uptime Agent" under commanding authority
IT_AI_Manager_v15.0, implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q36). Canonical catalog row #42: "Keep services up;
first responder in the incident flow."

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as recovered
or original.

RECOVERED (records only, stated exactly): the agent's
designed place in the MASTER §7 matrix — the IT AI Manager
commands the twelve agents, who "keep Sanders Dash & Seal
fully functional on a day-to-day basis under bounded
authority"; the agent descriptor in
core_platform/agent_registry.py (commanding authority
IT_AI_Manager_v15.0, INTERFACE_ONLY, external execution
disabled — the registry's own require_executable_agent
refuses every agent with AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED);
the catalog's designed role (keep services up; first
responder in the incident flow), with the catalog's own note
that the uptime function is covered live by
deploy/sds_watchdog.sh; and the IT AI Manager platform's
binding of this design (Q5: work orders record the design's
INTERFACE_ONLY status; no agent execution is claimed there).
Pre-existing related components — the read-only UptimeAgent
observer in core_platform/operational_runtime.py (a local
HTTP process-health observation function) and the watchdog's
live checks — are separate components; this platform does
not read, wrap, or replace them, and claims none of their
operation.

REBUILT (everything executable in this module): the governed
platform below — the Uptime Agent's own identity and store,
carrying uptime records over services presented by
reference:

- **Uptime records**: a service reference, a declared set of
  observation references, and a scope reference, carried as
  durable, receipted records with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision, then an outcome recorded against presented
  evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set (UPTIME_CONFIRMED /
  OUTAGE_CONFIRMED / INCONCLUSIVE). A record declared with
  no observations stands NO_OBSERVATIONS_SUBMITTED in every
  view and in the status tallies, and both determinations
  are refused on it — no observation set was presented to
  determine from; INCONCLUSIVE, which asserts nothing,
  records against evidence.
- **First responder, as designed**: a recorded
  OUTAGE_CONFIRMED outcome is this platform's first-response
  record in the incident flow — a record other platforms
  consume by reference. It pages no one, dispatches no one,
  and restarts nothing.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. This platform probes
  no service, restarts nothing, and executes nothing.
- **Reference-only discipline**: services and observations
  are carried by reference only; the platform holds no
  telemetry payloads, no credentials, and no live-system
  state.
- **Separation**: the Uptime Agent is its own platform. It
  is not the IT AI Manager that commands its design, not
  the watchdog script that covers the uptime function live,
  and not any other agent of the matrix — the twelve are
  never merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from .agent_registry import require_registered_agent
from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    validate_identity,
)
from .rtsa_foundation import (
    latest_check_in as _foundation_latest_check_in,
)
from .rtsa_foundation import (
    record_check_in as _foundation_record_check_in,
)


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='uptime_agent',
    name='Uptime Agent',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Uptime Agent')
DESIGNED_ROLE = 'Keep services up; first responder in the incident flow'
RECORD_OPERATIONS = (
    'record_observation', 'approve_observation', 'record_outcome',
    'view_observation', 'view_design',
)
EXECUTION_OPERATIONS = (
    'probe_service', 'restart_service', 'dispatch_response',
    'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('UPTIME_CONFIRMED', 'OUTAGE_CONFIRMED', 'INCONCLUSIVE')
DETERMINATIONS = ('UPTIME_CONFIRMED', 'OUTAGE_CONFIRMED')
MAX_OBSERVATION_REFS = 100


class UptimeAgentDenied(Exception):
    """The requested Uptime Agent operation is not allowed."""


class UptimeAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class UptimeAgentService:
    """Uptime Agent: governed uptime records under the agent
    design's INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise UptimeAgentDenied(
                'Uptime Agent requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'uptime_agent', {
            'OPERATOR': {'UPTIME'},
            'AUDITOR': {'UPTIME'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS uptime_records (
                    record_id TEXT PRIMARY KEY,
                    service_ref TEXT NOT NULL,
                    observation_refs TEXT NOT NULL,
                    observation_count INTEGER NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    evidence_ref TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                """
            )

    # -- plumbing ---------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self._path, timeout=10,
                             isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def _now(self) -> float:
        return float(self._clock())

    def _check_actor(self, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise UptimeAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise UptimeAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise UptimeAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'UPTIME', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise UptimeAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise UptimeAgentDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': DESIGN.name,
            'commanding_authority': DESIGN.commanding_authority,
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'designed_role': DESIGNED_ROLE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The platform carries uptime records over'
                    ' services presented by reference only: it'
                    ' probes no service, restarts nothing, and'
                    ' executes nothing. The agent design is'
                    ' INTERFACE_ONLY with external execution'
                    ' disabled — execution operations are'
                    ' refused by name with the design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. A'
                    ' record declared with no observations'
                    ' stands NO_OBSERVATIONS_SUBMITTED and no'
                    ' determination can be recorded on it. A'
                    ' recorded OUTAGE_CONFIRMED outcome is the'
                    ' first-response record in the incident'
                    ' flow, consumed by reference; it dispatches'
                    ' no response. The read-only observer in'
                    ' core_platform/operational_runtime.py and'
                    ' the watchdog checks in'
                    ' deploy/sds_watchdog.sh are separate'
                    ' pre-existing components — this platform'
                    ' does not read, wrap, or replace them. The'
                    ' Uptime Agent is distinct from the IT AI'
                    ' Manager and from every other agent of the'
                    ' matrix — the twelve are never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the INTERFACE_ONLY
        design does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise UptimeAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Uptime Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise UptimeAgentDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'commanding_authority': DESIGN.commanding_authority,
        }

    # -- records ----------------------------------------------------------

    @staticmethod
    def _record_view(row):
        observations = json.loads(row['observation_refs'])
        return {
            'record_id': row['record_id'],
            'service_ref': row['service_ref'],
            'observation_refs': observations,
            'observation_count': row['observation_count'],
            'observation_state': (
                'NO_OBSERVATIONS_SUBMITTED'
                if row['observation_count'] == 0
                else 'OBSERVATIONS_SUBMITTED'),
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_record(self, actor, service_ref, observation_refs,
                      scope_ref, *, region=None):
        """Record one uptime record (operator only) over a
        service and a declared set of observations, presented
        by reference. The observation set may be empty — the
        record then stands NO_OBSERVATIONS_SUBMITTED, exactly
        as the evidence discipline holds, and no determination
        can be recorded on it. Recording the record probes
        nothing and restarts nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('service_ref', service_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise UptimeAgentDenied(f'A {label} is required')
        if not isinstance(observation_refs, (list, tuple)):
            raise UptimeAgentDenied(
                'observation_refs must be a list of references')
        if len(observation_refs) > MAX_OBSERVATION_REFS:
            raise UptimeAgentDenied(
                f'At most {MAX_OBSERVATION_REFS} observation'
                ' references per record')
        observations = []
        for ref in observation_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise UptimeAgentDenied(
                    'Every observation reference must be a'
                    ' non-empty string')
            observations.append(ref.strip())
        now = self._now()
        record_id = f'uptime-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'UPTIME_AGENT_RECORD_RECORDED', actor=actor,
                    record_id=record_id,
                    service_ref=service_ref.strip(),
                    observation_count=len(observations))
                db.execute(
                    'INSERT INTO uptime_records (record_id,'
                    ' service_ref, observation_refs,'
                    ' observation_count, scope_ref, status,'
                    ' outcome, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?)',
                    (record_id, service_ref.strip(),
                     json.dumps(observations), len(observations),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM uptime_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM uptime_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM uptime_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        if row is None:
            raise UptimeAgentDenied('Uptime record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested uptime record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it probes nothing, restarts nothing, and
        dispatches no one."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise UptimeAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM uptime_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise UptimeAgentDenied(
                        'Uptime record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise UptimeAgentDenied(
                        f"Cannot {action} an uptime record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'UPTIME_AGENT_RECORD_ACTION', actor=actor,
                    record_id=record_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE uptime_records SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (new_status, actor, now, receipt_id, record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM uptime_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved uptime record's outcome
        (operator only), against a presented evidence
        reference. An outcome without evidence is refused. A
        determination (UPTIME_CONFIRMED or OUTAGE_CONFIRMED)
        on a record declared with no observations is refused —
        NO_OBSERVATIONS_SUBMITTED: no observation set was
        presented to determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise UptimeAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise UptimeAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM uptime_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise UptimeAgentDenied(
                        'Uptime record not found')
                if row['status'] != 'APPROVED':
                    raise UptimeAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" uptime records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['observation_count'] == 0:
                    raise UptimeAgentDenied(
                        'NO_OBSERVATIONS_SUBMITTED: a record'
                        ' declared with no observations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'UPTIME_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE uptime_records SET status = ?,'
                    ' outcome = ?, evidence_ref = ?, updated_by'
                    ' = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    ('OUTCOME_RECORDED', outcome,
                     evidence_ref.strip(), actor, now, receipt_id,
                     record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM uptime_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM uptime_records GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM uptime_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_observations = db.execute(
                'SELECT COUNT(*) AS n FROM uptime_records'
                ' WHERE observation_count = 0').fetchone()['n']
            observations_total = db.execute(
                'SELECT COALESCE(SUM(observation_count), 0) AS n'
                ' FROM uptime_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_observations_submitted': no_observations,
            'observations_declared_total': observations_total,
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to
        the platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise UptimeAgentDenied(str(exc)) from exc
                self._record('UPTIME_AGENT_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
