"""Application Agent — the application-layer health IT AI
agent platform.

The production build-out of the Application Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "Application Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q37). Canonical catalog row #43: "Application-layer
health and repair."

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
the catalog's designed role (application-layer health and
repair); and the IT AI Manager platform's binding of this
design (Q5: work orders record the design's INTERFACE_ONLY
status; no agent execution is claimed there). A pre-existing
related component — the read-only ApplicationAgent observer
in core_platform/operational_runtime.py (a local readiness
observation function) — is a separate component; this
platform does not read, wrap, or replace it, and claims
none of its operation.

REBUILT (everything executable in this module): the governed
platform below — the Application Agent's own identity and
store, carrying application-health assessment records over
applications presented by reference:

- **Assessment records**: an application reference, a
  declared set of health-check references, and a scope
  reference, carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set (APPLICATION_HEALTHY /
  APPLICATION_DEGRADED / INCONCLUSIVE). A record declared
  with no checks stands NO_CHECKS_SUBMITTED in every view
  and in the status tallies, and both determinations are
  refused on it — no check set was presented to determine
  from; INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. The catalog's word
  "repair" is the design's role, not this platform's act:
  this platform repairs nothing, restarts nothing, deploys
  nothing, and executes nothing — repair enters the
  ecosystem only as records through the IT AI Manager's
  orchestration.
- **Reference-only discipline**: applications and checks are
  carried by reference only; the platform holds no
  application payloads, no credentials, and no live-system
  state.
- **Separation**: the Application Agent is its own
  platform. It is not the IT AI Manager that commands its
  design, not the Uptime Agent, and not any other agent of
  the matrix — the twelve are never merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541511,
541512, 518210, 541519, 541513, 541690 — ADOPTED_EXISTING
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
    platform_id='application_agent',
    name='Application Agent',
    legal_entities=(),
    naics_codes=('541511', '541512', '518210', '541519', '541513', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Application Agent')
DESIGNED_ROLE = 'Application-layer health and repair'
RECORD_OPERATIONS = (
    'record_assessment', 'approve_assessment', 'record_outcome',
    'view_assessment', 'view_design',
)
EXECUTION_OPERATIONS = (
    'repair_application', 'restart_application',
    'deploy_application', 'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('APPLICATION_HEALTHY', 'APPLICATION_DEGRADED',
            'INCONCLUSIVE')
DETERMINATIONS = ('APPLICATION_HEALTHY', 'APPLICATION_DEGRADED')
MAX_CHECK_REFS = 100


class ApplicationAgentDenied(Exception):
    """The requested Application Agent operation is not allowed."""


class ApplicationAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ApplicationAgentService:
    """Application Agent: governed application-health
    assessment records under the agent design's
    INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ApplicationAgentDenied(
                'Application Agent requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'application_agent', {
            'OPERATOR': {'APPLICATION'},
            'AUDITOR': {'APPLICATION'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS application_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    application_ref TEXT NOT NULL,
                    check_refs TEXT NOT NULL,
                    check_count INTEGER NOT NULL,
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
            raise ApplicationAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ApplicationAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ApplicationAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'APPLICATION', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise ApplicationAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ApplicationAgentDenied(str(exc)) from exc

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
            'note': 'The platform carries application-health'
                    ' assessment records over applications'
                    ' presented by reference only: it repairs'
                    ' nothing, restarts nothing, deploys'
                    ' nothing, and executes nothing. The agent'
                    ' design is INTERFACE_ONLY with external'
                    ' execution disabled — execution operations'
                    ' are refused by name with the design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. An'
                    ' assessment declared with no checks stands'
                    ' NO_CHECKS_SUBMITTED and no determination'
                    ' can be recorded on it. Repair enters the'
                    ' ecosystem only as records through the IT'
                    ' AI Manager\u2019s orchestration, never as'
                    ' this platform\u2019s act. The read-only'
                    ' observer in'
                    ' core_platform/operational_runtime.py is a'
                    ' separate pre-existing component — this'
                    ' platform does not read, wrap, or replace'
                    ' it. The Application Agent is distinct'
                    ' from the IT AI Manager and from every'
                    ' other agent of the matrix — the twelve are'
                    ' never merged.',
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
            raise ApplicationAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Application Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise ApplicationAgentDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'commanding_authority': DESIGN.commanding_authority,
        }

    # -- assessments ------------------------------------------------------

    @staticmethod
    def _assessment_view(row):
        checks = json.loads(row['check_refs'])
        return {
            'assessment_id': row['assessment_id'],
            'application_ref': row['application_ref'],
            'check_refs': checks,
            'check_count': row['check_count'],
            'check_state': ('NO_CHECKS_SUBMITTED'
                            if row['check_count'] == 0
                            else 'CHECKS_SUBMITTED'),
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

    def create_assessment(self, actor, application_ref, check_refs,
                          scope_ref, *, region=None):
        """Record one application-health assessment (operator
        only) over an application and a declared set of health
        checks, presented by reference. The check set may be
        empty — the record then stands NO_CHECKS_SUBMITTED,
        exactly as the evidence discipline holds, and no
        determination can be recorded on it. Recording the
        assessment repairs nothing and restarts nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('application_ref', application_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ApplicationAgentDenied(f'A {label} is required')
        if not isinstance(check_refs, (list, tuple)):
            raise ApplicationAgentDenied(
                'check_refs must be a list of references')
        if len(check_refs) > MAX_CHECK_REFS:
            raise ApplicationAgentDenied(
                f'At most {MAX_CHECK_REFS} check references'
                ' per record')
        checks = []
        for ref in check_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ApplicationAgentDenied(
                    'Every check reference must be a non-empty'
                    ' string')
            checks.append(ref.strip())
        now = self._now()
        assessment_id = f'application-assessment-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'APPLICATION_AGENT_ASSESSMENT_RECORDED',
                    actor=actor, assessment_id=assessment_id,
                    application_ref=application_ref.strip(),
                    check_count=len(checks))
                db.execute(
                    'INSERT INTO application_assessments'
                    ' (assessment_id, application_ref, check_refs,'
                    ' check_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (assessment_id, application_ref.strip(),
                     json.dumps(checks), len(checks),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM application_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(row)

    def assessments_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assessments',
                           'assessments view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM application_assessments'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._assessment_view(row) for row in rows]

    def assessment_view(self, actor, role, assessment_id, *,
                        region=None):
        self._geo(region)
        self._guard_access(actor, role, assessment_id,
                           'assessment view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM application_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        if row is None:
            raise ApplicationAgentDenied('Assessment record not found')
        return self._assessment_view(row)

    def assessment_action(self, actor, assessment_id, action, *,
                          region=None):
        """Approve or reject one requested assessment record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it repairs nothing, restarts nothing, and
        deploys nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise ApplicationAgentDenied(
                f'Unknown assessment action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM application_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise ApplicationAgentDenied(
                        'Assessment record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ApplicationAgentDenied(
                        f"Cannot {action} an assessment record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'APPLICATION_AGENT_ASSESSMENT_ACTION',
                    actor=actor, assessment_id=assessment_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE application_assessments SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE assessment_id = ?',
                    (new_status, actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM application_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    def record_outcome(self, actor, assessment_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved assessment's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (APPLICATION_HEALTHY or APPLICATION_DEGRADED) on a
        record declared with no checks is refused —
        NO_CHECKS_SUBMITTED: no check set was presented to
        determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise ApplicationAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ApplicationAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM application_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise ApplicationAgentDenied(
                        'Assessment record not found')
                if row['status'] != 'APPROVED':
                    raise ApplicationAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" assessment records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['check_count'] == 0:
                    raise ApplicationAgentDenied(
                        'NO_CHECKS_SUBMITTED: a record declared'
                        ' with no checks cannot be determined'
                        f' {outcome}')
                receipt_id = self._record(
                    'APPLICATION_AGENT_OUTCOME_RECORDED',
                    actor=actor, assessment_id=assessment_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE application_assessments SET status = ?,'
                    ' outcome = ?, evidence_ref = ?, updated_by'
                    ' = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE assessment_id = ?',
                    ('OUTCOME_RECORDED', outcome,
                     evidence_ref.strip(), actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM application_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM application_assessments'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM application_assessments'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_checks = db.execute(
                'SELECT COUNT(*) AS n FROM application_assessments'
                ' WHERE check_count = 0').fetchone()['n']
            checks_total = db.execute(
                'SELECT COALESCE(SUM(check_count), 0) AS n'
                ' FROM application_assessments').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'assessments_total': sum(by_status.values()),
            'assessments_by_status': by_status,
            'assessments_by_outcome': by_outcome,
            'records_no_checks_submitted': no_checks,
            'checks_declared_total': checks_total,
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
                    raise ApplicationAgentDenied(str(exc)) from exc
                self._record('APPLICATION_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
