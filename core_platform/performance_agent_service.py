"""Performance Agent — the performance monitoring and
remediation IT AI agent platform.

The production build-out of the Performance Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "Performance Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q42). Canonical catalog row #48: "Performance
monitoring/remediation."

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
the catalog's designed role (performance
monitoring/remediation); and the IT AI Manager platform's
binding of this design (Q5: work orders record the design's
INTERFACE_ONLY status; no agent execution is claimed there).
A pre-existing related component — the read-only
PerformanceAgent observer entry in
core_platform/operational_runtime.py (a read-only
observation function over operational history) — is a
separate component; this platform does not read, wrap, or
replace it, and claims none of its operation.

REBUILT (everything executable in this module): the governed
platform below — the Performance Agent's own identity and
store, carrying performance records over subjects presented
by reference:

- **Performance records**: a subject reference, a declared
  set of measurement references, and a scope reference,
  carried as durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set
  (PERFORMANCE_WITHIN_TARGET / PERFORMANCE_DEGRADED /
  INCONCLUSIVE). A record declared with no measurements
  stands NO_MEASUREMENTS_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no measurement set was presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. The catalog's word
  "remediation" is the design's role, not this platform's
  act: this platform remediates nothing, tunes nothing,
  scales nothing, takes no live measurement, and executes
  nothing — remediation enters the ecosystem only as records
  through the IT AI Manager's orchestration.
- **Reference-only discipline**: subjects and measurements
  are carried by reference only; the platform holds no
  metric values, no telemetry, and no live-system state.
  (Its own record store is its own — it is not a window into
  any operational system.)
- **Separation**: the Performance Agent is its own platform.
  It is not the IT AI Manager that commands its design, not
  the Observability Agent, and not any other agent of the
  matrix — the twelve are never merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
541519, 518210, 541513, 541511, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
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
    platform_id='performance_agent',
    name='Performance Agent',
    legal_entities=(),
    naics_codes=('541512', '541519', '518210', '541513', '541511', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Performance Agent')
DESIGNED_ROLE = 'Performance monitoring/remediation'
RECORD_OPERATIONS = (
    'record_performance', 'approve_performance',
    'record_outcome', 'view_performance', 'view_design',
)
EXECUTION_OPERATIONS = (
    'remediate_performance', 'tune_performance',
    'scale_resources', 'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('PERFORMANCE_WITHIN_TARGET', 'PERFORMANCE_DEGRADED',
            'INCONCLUSIVE')
DETERMINATIONS = ('PERFORMANCE_WITHIN_TARGET',
                  'PERFORMANCE_DEGRADED')
MAX_MEASUREMENT_REFS = 100


class PerformanceAgentDenied(Exception):
    """The requested Performance Agent operation is not allowed."""


class PerformanceAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class PerformanceAgentService:
    """Performance Agent: governed performance records under
    the agent design's INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise PerformanceAgentDenied(
                'Performance Agent requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'performance_agent', {
            'OPERATOR': {'PERFORMANCE'},
            'AUDITOR': {'PERFORMANCE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS performance_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    measurement_refs TEXT NOT NULL,
                    measurement_count INTEGER NOT NULL,
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
            raise PerformanceAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PerformanceAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise PerformanceAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'PERFORMANCE', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise PerformanceAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise PerformanceAgentDenied(str(exc)) from exc

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
            'note': 'The platform carries performance records'
                    ' over subjects presented by reference'
                    ' only: it remediates nothing, tunes'
                    ' nothing, scales nothing, takes no live'
                    ' measurement, and executes nothing. The'
                    ' agent design is INTERFACE_ONLY with'
                    ' external execution disabled — execution'
                    ' operations are refused by name with the'
                    ' design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. A'
                    ' record declared with no measurements'
                    ' stands NO_MEASUREMENTS_SUBMITTED and no'
                    ' determination can be recorded on it.'
                    ' Remediation enters the ecosystem only'
                    ' as records through the IT AI Manager\u2019s'
                    ' orchestration, never as this'
                    ' platform\u2019s act. The read-only'
                    ' PerformanceAgent observer entry in'
                    ' core_platform/operational_runtime.py is'
                    ' a separate pre-existing component —'
                    ' this platform does not read, wrap, or'
                    ' replace it. The Performance Agent is'
                    ' distinct from the IT AI Manager and'
                    ' from every other agent of the matrix —'
                    ' the twelve are never merged.',
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
            raise PerformanceAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Performance Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise PerformanceAgentDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'commanding_authority': DESIGN.commanding_authority,
        }

    # -- records ------------------------------------------------------

    @staticmethod
    def _record_view(row):
        measurements = json.loads(row['measurement_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'measurement_refs': measurements,
            'measurement_count': row['measurement_count'],
            'measurement_state': ('NO_MEASUREMENTS_SUBMITTED'
                                  if row['measurement_count'] == 0
                                  else 'MEASUREMENTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, measurement_refs,
                      scope_ref, *, region=None):
        """Record one performance record (operator only) over
        a subject and a declared set of measurements,
        presented by reference. The measurement set may be
        empty — the record then stands
        NO_MEASUREMENTS_SUBMITTED, exactly as the evidence
        discipline holds, and no determination can be
        recorded on it. Recording the record remediates
        nothing and measures nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise PerformanceAgentDenied(f'A {label} is required')
        if not isinstance(measurement_refs, (list, tuple)):
            raise PerformanceAgentDenied(
                'measurement_refs must be a list of references')
        if len(measurement_refs) > MAX_MEASUREMENT_REFS:
            raise PerformanceAgentDenied(
                f'At most {MAX_MEASUREMENT_REFS} measurement'
                ' references per record')
        measurements = []
        for ref in measurement_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise PerformanceAgentDenied(
                    'Every measurement reference must be a'
                    ' non-empty string')
            measurements.append(ref.strip())
        now = self._now()
        record_id = f'performance-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'PERFORMANCE_AGENT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    measurement_count=len(measurements))
                db.execute(
                    'INSERT INTO performance_records'
                    ' (record_id, subject_ref, measurement_refs,'
                    ' measurement_count, scope_ref, status,'
                    ' outcome, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(measurements), len(measurements),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM performance_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM performance_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM performance_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise PerformanceAgentDenied('Performance record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested performance record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it remediates nothing, tunes nothing, and
        scales nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise PerformanceAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM performance_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise PerformanceAgentDenied(
                        'Performance record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise PerformanceAgentDenied(
                        f"Cannot {action} a performance record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'PERFORMANCE_AGENT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE performance_records SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (new_status, actor, now, receipt_id,
                     record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM performance_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (PERFORMANCE_WITHIN_TARGET or PERFORMANCE_DEGRADED)
        on a record declared with no measurements is refused
        — NO_MEASUREMENTS_SUBMITTED: no measurement set was
        presented to determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise PerformanceAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise PerformanceAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM performance_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise PerformanceAgentDenied(
                        'Performance record not found')
                if row['status'] != 'APPROVED':
                    raise PerformanceAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" performance records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['measurement_count'] == 0:
                    raise PerformanceAgentDenied(
                        'NO_MEASUREMENTS_SUBMITTED: a record'
                        ' declared with no measurements cannot'
                        f' be determined {outcome}')
                receipt_id = self._record(
                    'PERFORMANCE_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE performance_records SET status = ?,'
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
                'SELECT * FROM performance_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM performance_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM performance_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_measurements = db.execute(
                'SELECT COUNT(*) AS n FROM performance_records'
                ' WHERE measurement_count = 0').fetchone()['n']
            measurements_total = db.execute(
                'SELECT COALESCE(SUM(measurement_count), 0) AS n'
                ' FROM performance_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_measurements_submitted': no_measurements,
            'measurements_declared_total': measurements_total,
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
                    raise PerformanceAgentDenied(str(exc)) from exc
                self._record('PERFORMANCE_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
