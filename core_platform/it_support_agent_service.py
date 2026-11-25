"""IT Support Agent — the support operations IT AI agent
platform.

The production build-out of the IT Support Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "IT Support Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q47). Canonical catalog row #53: "Support
operations".

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
the catalog's designed role (support operations); and the
IT AI Manager platform's binding of this design (Q5: work
orders record the design's INTERFACE_ONLY status; no agent
execution is claimed there). A pre-existing related
component — the read-only ITSupportAgent observer entry in
core_platform/operational_runtime.py — is a separate
component; this platform does not read, wrap, or replace
it, and claims none of its operation. The IT Support Agent
is an internal IT support platform; it is distinct from
Sanders Customer Support (catalog #128, Band 2D), the
customer-facing support business — the two are never
merged.

REBUILT (everything executable in this module): the governed
platform below — the IT Support Agent's own identity and
store, carrying support records over subjects and declared
support cases presented by reference:

- **Support records**: a subject reference, a declared set
  of support-case references, and a scope reference, carried
  as durable, receipted records with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision, then an outcome recorded against presented
  evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set (SUPPORT_RESOLVED /
  SUPPORT_UNRESOLVED / INCONCLUSIVE). A record declared
  with no support cases stands NO_CASES_SUBMITTED in every
  view and in the status tallies, and both determinations
  are refused on it — no case set was presented to determine
  from; INCONCLUSIVE, which asserts nothing, records
  against evidence.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. The catalog's word
  "support" is the design's role, not this platform's act:
  this platform resolves no case itself, contacts no
  requester, and accesses no remote system — support enters
  the ecosystem only as records through the IT AI Manager's
  orchestration.
- **Reference-only discipline**: subjects and cases are
  carried by reference only; the platform holds no case
  content, no requester data, and no live-system state.
  (Its own record store is its own — it is not a window
  into any operational system.)
- **Separation**: the IT Support Agent is its own platform.
  It is not the IT AI Manager that commands its design, not
  Sanders Customer Support, and not any other agent of the
  matrix — the twelve are never merged.

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
    platform_id='it_support_agent',
    name='IT Support Agent',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('IT Support Agent')
DESIGNED_ROLE = 'Support operations'
RECORD_OPERATIONS = (
    'record_support_case', 'approve_support_case', 'record_outcome',
    'view_support_case', 'view_design',
)
EXECUTION_OPERATIONS = (
    'resolve_support_case', 'contact_requester', 'access_remote_system',
    'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SUPPORT_RESOLVED', 'SUPPORT_UNRESOLVED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SUPPORT_RESOLVED', 'SUPPORT_UNRESOLVED')
MAX_CASE_REFS = 100


class ITSupportAgentDenied(Exception):
    """The requested IT Support Agent operation is not
    allowed."""


class ITSupportAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ITSupportAgentService:
    """IT Support Agent: governed support records under
    the agent design's INTERFACE_ONLY discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ITSupportAgentDenied(
                'IT Support Agent requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'it_support_agent', {
            'OPERATOR': {'IT_SUPPORT'},
            'AUDITOR': {'IT_SUPPORT'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS support_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    case_refs TEXT NOT NULL,
                    case_count INTEGER NOT NULL,
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
            raise ITSupportAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ITSupportAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ITSupportAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'IT_SUPPORT',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise ITSupportAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ITSupportAgentDenied(str(exc)) from exc

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
            'note': 'The platform carries support records over subjects '
                    'and declared support cases presented by reference '
                    'only: it resolves no case itself, contacts no '
                    'requester, and accesses no remote system. The agent '
                    'design is INTERFACE_ONLY with external execution '
                    'disabled — execution operations are refused by name '
                    'with the design signal '
                    'AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. A record '
                    'declared with no support cases stands '
                    'NO_CASES_SUBMITTED and no determination can be '
                    'recorded on it. Support enters the ecosystem only as '
                    'records through the IT AI Manager’s orchestration, '
                    'never as this platform’s act. The read-only '
                    'ITSupportAgent observer entry in '
                    'core_platform/operational_runtime.py is a separate '
                    'pre-existing component — this platform does not '
                    'read, wrap, or replace it. The IT Support Agent is '
                    'distinct from the IT AI Manager, from Sanders '
                    'Customer Support, and from every other agent of the '
                    'matrix — the twelve are never merged.',
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
            raise ITSupportAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the IT Support Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled'
                ' (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise ITSupportAgentDenied(
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
        cases = json.loads(row['case_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'case_refs': cases,
            'case_count': row['case_count'],
            'case_state': ('NO_CASES_SUBMITTED'
                                if row['case_count'] == 0
                                else 'CASES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, case_refs,
                      scope_ref, *, region=None):
        """Record one support record (operator only) over
        a subject and a declared set of support-case references,
        presented by reference. The case set may be
        empty — the record then stands NO_CASES_SUBMITTED,
        exactly as the evidence discipline holds, and no
        determination can be recorded on it. Recording the
        record resolves no case and contacts no
        requester."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ITSupportAgentDenied(
                    f'A {label} is required')
        if not isinstance(case_refs, (list, tuple)):
            raise ITSupportAgentDenied(
                'case_refs must be a list of references')
        if len(case_refs) > MAX_CASE_REFS:
            raise ITSupportAgentDenied(
                f'At most {MAX_CASE_REFS} case'
                ' references per record')
        cases = []
        for ref in case_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ITSupportAgentDenied(
                    'Every case reference must be a'
                    ' non-empty string')
            cases.append(ref.strip())
        now = self._now()
        record_id = f'support-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'IT_SUPPORT_AGENT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    case_count=len(cases))
                db.execute(
                    'INSERT INTO support_records'
                    ' (record_id, subject_ref, case_refs,'
                    ' case_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(cases), len(cases),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM support_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM support_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM support_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise ITSupportAgentDenied(
                'Support record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested support record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it resolves no case, contacts no
        requester, and modifies nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise ITSupportAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM support_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ITSupportAgentDenied(
                        'Support record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ITSupportAgentDenied(
                        f"Cannot {action} a support record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'IT_SUPPORT_AGENT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE support_records SET status = ?,'
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
                'SELECT * FROM support_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SUPPORT_RESOLVED or SUPPORT_UNRESOLVED) on a
        record declared with no cases is refused —
        NO_CASES_SUBMITTED: no case set was presented
        to determine from."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise ITSupportAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ITSupportAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM support_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ITSupportAgentDenied(
                        'Support record not found')
                if row['status'] != 'APPROVED':
                    raise ITSupportAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" support records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['case_count'] == 0:
                    raise ITSupportAgentDenied(
                        'NO_CASES_SUBMITTED: a record'
                        ' declared with no cases cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'IT_SUPPORT_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE support_records SET status = ?,'
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
                'SELECT * FROM support_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM support_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM support_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_cases = db.execute(
                'SELECT COUNT(*) AS n FROM support_records'
                ' WHERE case_count = 0').fetchone()['n']
            cases_total = db.execute(
                'SELECT COALESCE(SUM(case_count), 0) AS n'
                ' FROM support_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_cases_submitted': no_cases,
            'cases_declared_total': cases_total,
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
                    raise ITSupportAgentDenied(str(exc)) from exc
                self._record('IT_SUPPORT_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
