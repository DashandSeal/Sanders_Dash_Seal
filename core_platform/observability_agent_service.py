"""Observability Agent — the telemetry and observation IT AI
agent platform.

The production build-out of the Observability Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "Observability Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q44). Canonical catalog row #50: "Telemetry and
observation".

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
the catalog's designed role (telemetry and observation); and
the IT AI Manager platform's binding of this design (Q5:
work orders record the design's INTERFACE_ONLY status; no
agent execution is claimed there). A pre-existing related
component — the read-only ObservabilityAgent observer entry
in core_platform/operational_runtime.py — is a separate
component; this platform does not read, wrap, or replace it,
and claims none of its operation.

REBUILT (everything executable in this module): the governed
platform below — the Observability Agent's own identity and
store, carrying observation records over telemetry presented
by reference:

- **Observation records**: a subject reference, a declared
  set of telemetry references, and a scope reference, carried
  as durable, receipted records with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision, then an outcome recorded against presented
  evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set (TELEMETRY_HEALTHY /
  TELEMETRY_GAP_DETECTED / INCONCLUSIVE). A record declared
  with no telemetry stands NO_TELEMETRY_SUBMITTED in every
  view and in the status tallies, and both determinations are
  refused on it — no telemetry was presented to determine
  from; INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. The catalog's word
  "observation" is the design's role, not this platform's
  act: this platform collects no telemetry, queries no live
  system, modifies nothing, and observes nothing live —
  observation enters the ecosystem only as records through
  the IT AI Manager's orchestration.
- **Reference-only discipline**: subjects and telemetry are
  carried by reference only; the platform holds no telemetry
  values, no metric streams, and no live-system state. (Its
  own record store is its own — it is not a window into any
  operational system.)
- **Separation**: the Observability Agent is its own
  platform. It is not the IT AI Manager that commands its
  design, not the Performance Agent, and not any other agent
  of the matrix — the twelve are never merged.

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
    platform_id='observability_agent',
    name='Observability Agent',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Observability Agent')
DESIGNED_ROLE = 'Telemetry and observation'
RECORD_OPERATIONS = (
    'record_observation', 'approve_observation', 'record_outcome',
    'view_observation', 'view_design',
)
EXECUTION_OPERATIONS = (
    'collect_telemetry', 'query_telemetry', 'modify_telemetry',
    'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('TELEMETRY_HEALTHY', 'TELEMETRY_GAP_DETECTED',
            'INCONCLUSIVE')
DETERMINATIONS = ('TELEMETRY_HEALTHY', 'TELEMETRY_GAP_DETECTED')
MAX_TELEMETRY_REFS = 100


class ObservabilityAgentDenied(Exception):
    """The requested Observability Agent operation is not
    allowed."""


class ObservabilityAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ObservabilityAgentService:
    """Observability Agent: governed observation records under
    the agent design's INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ObservabilityAgentDenied(
                'Observability Agent requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'observability_agent', {
            'OPERATOR': {'OBSERVABILITY'},
            'AUDITOR': {'OBSERVABILITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS observability_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    telemetry_refs TEXT NOT NULL,
                    telemetry_count INTEGER NOT NULL,
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
            raise ObservabilityAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ObservabilityAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ObservabilityAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'OBSERVABILITY',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise ObservabilityAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ObservabilityAgentDenied(str(exc)) from exc

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
            'note': 'The platform carries observation records'
                    ' over telemetry presented by reference'
                    ' only: it collects no telemetry, queries'
                    ' no live system, modifies nothing, and'
                    ' observes nothing live. The agent design'
                    ' is INTERFACE_ONLY with external execution'
                    ' disabled — execution operations are'
                    ' refused by name with the design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. A'
                    ' record declared with no telemetry stands'
                    ' NO_TELEMETRY_SUBMITTED and no'
                    ' determination can be recorded on it.'
                    ' Observation enters the ecosystem only as'
                    ' records through the IT AI Manager\u2019s'
                    ' orchestration, never as this'
                    ' platform\u2019s act. The read-only'
                    ' ObservabilityAgent observer entry in'
                    ' core_platform/operational_runtime.py is'
                    ' a separate pre-existing component — this'
                    ' platform does not read, wrap, or replace'
                    ' it. The Observability Agent is distinct'
                    ' from the IT AI Manager and from every'
                    ' other agent of the matrix — the twelve'
                    ' are never merged.',
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
            raise ObservabilityAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Observability Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled'
                ' (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise ObservabilityAgentDenied(
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
        telemetry = json.loads(row['telemetry_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'telemetry_refs': telemetry,
            'telemetry_count': row['telemetry_count'],
            'telemetry_state': ('NO_TELEMETRY_SUBMITTED'
                                if row['telemetry_count'] == 0
                                else 'TELEMETRY_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, telemetry_refs,
                      scope_ref, *, region=None):
        """Record one observation record (operator only) over
        a subject and a declared set of telemetry references,
        presented by reference. The telemetry set may be
        empty — the record then stands NO_TELEMETRY_SUBMITTED,
        exactly as the evidence discipline holds, and no
        determination can be recorded on it. Recording the
        record collects no telemetry and observes nothing
        live."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ObservabilityAgentDenied(
                    f'A {label} is required')
        if not isinstance(telemetry_refs, (list, tuple)):
            raise ObservabilityAgentDenied(
                'telemetry_refs must be a list of references')
        if len(telemetry_refs) > MAX_TELEMETRY_REFS:
            raise ObservabilityAgentDenied(
                f'At most {MAX_TELEMETRY_REFS} telemetry'
                ' references per record')
        telemetry = []
        for ref in telemetry_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ObservabilityAgentDenied(
                    'Every telemetry reference must be a'
                    ' non-empty string')
            telemetry.append(ref.strip())
        now = self._now()
        record_id = f'observability-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'OBSERVABILITY_AGENT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    telemetry_count=len(telemetry))
                db.execute(
                    'INSERT INTO observability_records'
                    ' (record_id, subject_ref, telemetry_refs,'
                    ' telemetry_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(telemetry), len(telemetry),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM observability_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM observability_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM observability_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise ObservabilityAgentDenied(
                'Observation record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested observation record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it collects no telemetry, queries nothing,
        and modifies nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise ObservabilityAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM observability_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ObservabilityAgentDenied(
                        'Observation record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ObservabilityAgentDenied(
                        f"Cannot {action} an observation record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'OBSERVABILITY_AGENT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE observability_records SET status = ?,'
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
                'SELECT * FROM observability_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (TELEMETRY_HEALTHY or TELEMETRY_GAP_DETECTED) on a
        record declared with no telemetry is refused —
        NO_TELEMETRY_SUBMITTED: no telemetry was presented to
        determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise ObservabilityAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ObservabilityAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM observability_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ObservabilityAgentDenied(
                        'Observation record not found')
                if row['status'] != 'APPROVED':
                    raise ObservabilityAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" observation records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['telemetry_count'] == 0:
                    raise ObservabilityAgentDenied(
                        'NO_TELEMETRY_SUBMITTED: a record'
                        ' declared with no telemetry cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'OBSERVABILITY_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE observability_records SET status = ?,'
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
                'SELECT * FROM observability_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM observability_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM observability_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_telemetry = db.execute(
                'SELECT COUNT(*) AS n FROM observability_records'
                ' WHERE telemetry_count = 0').fetchone()['n']
            telemetry_total = db.execute(
                'SELECT COALESCE(SUM(telemetry_count), 0) AS n'
                ' FROM observability_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_telemetry_submitted': no_telemetry,
            'telemetry_declared_total': telemetry_total,
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
                    raise ObservabilityAgentDenied(str(exc)) from exc
                self._record('OBSERVABILITY_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
