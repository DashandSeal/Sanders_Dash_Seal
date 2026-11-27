"""Infrastructure Agent — the infrastructure restoration
IT AI agent platform.

The production build-out of the Infrastructure Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "Infrastructure Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q40). Canonical catalog row #46: "Infrastructure
restoration."

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
the catalog's designed role (infrastructure restoration);
and the IT AI Manager platform's binding of this design
(Q5: work orders record the design's INTERFACE_ONLY status;
no agent execution is claimed there). A pre-existing
related component — the read-only InfrastructureAgent
observer entry in core_platform/operational_runtime.py (a
read-only observation roster; observers are maintenance
functions, not deployed services or authorization
authorities) — is a separate component; this platform does
not read, wrap, or replace it, and claims none of its
operation.

REBUILT (everything executable in this module): the governed
platform below — the Infrastructure Agent's own identity
and store, carrying infrastructure-health assessment
records over infrastructure presented by reference:

- **Assessment records**: an infrastructure reference, a
  declared set of health-check references, and a scope
  reference, carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (INFRASTRUCTURE_HEALTHY / INFRASTRUCTURE_DEGRADED /
  INCONCLUSIVE). An assessment declared with no checks
  stands NO_CHECKS_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no check set was presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Restoration, as designed**: the catalog's word
  "restoration" is the design's role, not this platform's
  act. Restoration enters the ecosystem only as records
  through the IT AI Manager's orchestration; this platform
  restores nothing, repairs nothing, and provisions
  nothing.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by
  name with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED.
- **Reference-only discipline**: infrastructure and checks
  are carried by reference only; the platform holds no
  telemetry payloads, no credentials, and no live-system
  state.
- **Separation**: the Infrastructure Agent is its own
  platform. It is not the IT AI Manager that commands its
  design, not the Deployment Agent whose records it never
  touches, and not any other agent of the matrix — the
  twelve are never merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541513,
518210, 541512, 541519, 541330, 541690 — ADOPTED_EXISTING
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
    platform_id='infrastructure_agent',
    name='Infrastructure Agent',
    legal_entities=(),
    naics_codes=('541513', '518210', '541512', '541519', '541330', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Infrastructure Agent')
DESIGNED_ROLE = 'Infrastructure restoration'
RECORD_OPERATIONS = (
    'record_assessment', 'approve_assessment', 'record_outcome',
    'view_assessment', 'view_design',
)
EXECUTION_OPERATIONS = (
    'restore_infrastructure', 'repair_infrastructure',
    'provision_infrastructure', 'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('INFRASTRUCTURE_HEALTHY', 'INFRASTRUCTURE_DEGRADED',
            'INCONCLUSIVE')
DETERMINATIONS = ('INFRASTRUCTURE_HEALTHY',
                  'INFRASTRUCTURE_DEGRADED')
MAX_CHECK_REFS = 100


class InfrastructureAgentDenied(Exception):
    """The requested Infrastructure Agent operation is not
    allowed."""


class InfrastructureAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class InfrastructureAgentService:
    """Infrastructure Agent: governed infrastructure-health
    assessment records under the agent design's
    INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise InfrastructureAgentDenied(
                'Infrastructure Agent requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'infrastructure_agent', {
            'OPERATOR': {'INFRASTRUCTURE'},
            'AUDITOR': {'INFRASTRUCTURE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS infrastructure_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    infrastructure_ref TEXT NOT NULL,
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
            raise InfrastructureAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise InfrastructureAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise InfrastructureAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'INFRASTRUCTURE',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise InfrastructureAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise InfrastructureAgentDenied(str(exc)) from exc

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
            'note': 'The platform carries infrastructure-health'
                    ' assessment records over infrastructure'
                    ' presented by reference only: it restores'
                    ' nothing, repairs nothing, provisions'
                    ' nothing, and executes nothing. The agent'
                    ' design is INTERFACE_ONLY with external'
                    ' execution disabled — execution operations'
                    ' are refused by name with the design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. An'
                    ' assessment declared with no checks stands'
                    ' NO_CHECKS_SUBMITTED and no determination'
                    ' can be recorded on it. Restoration enters'
                    ' the ecosystem only as records through the'
                    ' IT AI Manager\u2019s orchestration, never'
                    ' as this platform\u2019s act. The read-only'
                    ' InfrastructureAgent observer entry in'
                    ' core_platform/operational_runtime.py is a'
                    ' separate pre-existing component — this'
                    ' platform does not read, wrap, or replace'
                    ' it. The Infrastructure Agent is distinct'
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
            raise InfrastructureAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Infrastructure Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise InfrastructureAgentDenied(
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
            'infrastructure_ref': row['infrastructure_ref'],
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

    def create_assessment(self, actor, infrastructure_ref,
                          check_refs, scope_ref, *, region=None):
        """Record one infrastructure-health assessment
        (operator only) over infrastructure and a declared
        set of health checks, presented by reference. The
        check set may be empty — the record then stands
        NO_CHECKS_SUBMITTED, exactly as the evidence
        discipline holds, and no determination can be
        recorded on it. Recording the assessment restores
        nothing and repairs nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('infrastructure_ref',
                              infrastructure_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise InfrastructureAgentDenied(
                    f'A {label} is required')
        if not isinstance(check_refs, (list, tuple)):
            raise InfrastructureAgentDenied(
                'check_refs must be a list of references')
        if len(check_refs) > MAX_CHECK_REFS:
            raise InfrastructureAgentDenied(
                f'At most {MAX_CHECK_REFS} check references'
                ' per record')
        checks = []
        for ref in check_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise InfrastructureAgentDenied(
                    'Every check reference must be a non-empty'
                    ' string')
            checks.append(ref.strip())
        now = self._now()
        assessment_id = (
            f'infrastructure-assessment-{uuid.uuid4().hex[:16]}')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'INFRASTRUCTURE_AGENT_ASSESSMENT_RECORDED',
                    actor=actor, assessment_id=assessment_id,
                    infrastructure_ref=infrastructure_ref.strip(),
                    check_count=len(checks))
                db.execute(
                    'INSERT INTO infrastructure_assessments'
                    ' (assessment_id, infrastructure_ref,'
                    ' check_refs, check_count, scope_ref, status,'
                    ' outcome, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (assessment_id, infrastructure_ref.strip(),
                     json.dumps(checks), len(checks),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM infrastructure_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(row)

    def assessments_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assessments',
                           'assessments view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM infrastructure_assessments'
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
                'SELECT * FROM infrastructure_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        if row is None:
            raise InfrastructureAgentDenied(
                'Assessment record not found')
        return self._assessment_view(row)

    def assessment_action(self, actor, assessment_id, action, *,
                          region=None):
        """Approve or reject one requested assessment record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it restores nothing and repairs nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise InfrastructureAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM infrastructure_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise InfrastructureAgentDenied(
                        'Assessment record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise InfrastructureAgentDenied(
                        f"Cannot {action} an assessment record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'INFRASTRUCTURE_AGENT_ASSESSMENT_ACTION',
                    actor=actor, assessment_id=assessment_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE infrastructure_assessments'
                    ' SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE assessment_id = ?',
                    (new_status, actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM infrastructure_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    def record_outcome(self, actor, assessment_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved assessment's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (INFRASTRUCTURE_HEALTHY or INFRASTRUCTURE_DEGRADED)
        on an assessment declared with no checks is refused —
        NO_CHECKS_SUBMITTED: no check set was presented to
        determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise InfrastructureAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise InfrastructureAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM infrastructure_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise InfrastructureAgentDenied(
                        'Assessment record not found')
                if row['status'] != 'APPROVED':
                    raise InfrastructureAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" assessment records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['check_count'] == 0:
                    raise InfrastructureAgentDenied(
                        'NO_CHECKS_SUBMITTED: an assessment'
                        ' declared with no checks cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'INFRASTRUCTURE_AGENT_OUTCOME_RECORDED',
                    actor=actor, assessment_id=assessment_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE infrastructure_assessments'
                    ' SET status = ?, outcome = ?,'
                    ' evidence_ref = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
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
                'SELECT * FROM infrastructure_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM infrastructure_assessments'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM infrastructure_assessments'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_checks = db.execute(
                'SELECT COUNT(*) AS n'
                ' FROM infrastructure_assessments'
                ' WHERE check_count = 0').fetchone()['n']
            checks_total = db.execute(
                'SELECT COALESCE(SUM(check_count), 0) AS n'
                ' FROM infrastructure_assessments').fetchone()['n']
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
                    raise InfrastructureAgentDenied(str(exc)) from exc
                self._record('INFRASTRUCTURE_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
