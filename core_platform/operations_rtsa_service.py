"""Operations RTSA — the operational reasoning and incident
response RTSA.

The production build-out of the Operations RTSA role contract
(``core_platform/rtsa_registry.py``: canonical name
"Operations RTSA 📊", slug ``operations-rtsa``, mission
"operational reasoning and incident response", SPECIFIED,
enabled: False), built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program Q35).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform executes nothing, deploys nothing, dispatches
no one, and reaches into no live system. What it does is the
operational incident record, governed:

- **Incident records**: operational incidents presented by
  reference, carried as durable, receipted records (subject,
  incident, and scope references) with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision — the incident triage the role's designed offline
  assessment requires (INCIDENT_TRIAGE_REQUIRED) — then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The designed incident discipline** (the role's designed
  offline assessment in ``core_platform/rtsa_assessments.py``)
  is enforced in the record model: an assessment declared
  with no active incidents stands NO_INCIDENTS_SUBMITTED in
  every view and in the status tallies, and a RESOLVED
  outcome on such a record is refused — there is nothing to
  resolve.
- **Outcomes** are recorded only for APPROVED incidents and
  only against a presented evidence reference, with a closed
  outcome set (RESOLVED / ESCALATED / INCONCLUSIVE). An
  ESCALATED outcome is a record inside this platform: it
  dispatches no one and pages no system.
- **Reference-only discipline**: subjects and incidents are
  carried by reference only; the platform holds no
  operational payloads, no credentials, and no live-system
  state.
- **Separation**: Operations RTSA is its own platform. It is
  not IT AI Manager (the IT operations role contract, built
  separately in this program) and not Sharpshooter (the
  operational-integrity role contract, also built separately);
  the three are never merged.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed —
  whether a named operation is a record operation this
  platform may carry or a prohibited operation it refuses.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses to
exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541611,
541512, 518210, 561110, 541690, 541614 — ADOPTED_EXISTING
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
from .rtsa_registry import RTSA_ROLES


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='operations_rtsa',
    name='Operations RTSA',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541611', '541512', '518210', '561110', '541690', '541614'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['Operations RTSA 📊']
RECORD_OPERATIONS = (
    'record_incident', 'approve_incident', 'record_outcome',
    'view_incident', 'view_contract',
)
INCIDENT_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                     'OUTCOME_RECORDED')
INCIDENT_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('RESOLVED', 'ESCALATED', 'INCONCLUSIVE')
MAX_INCIDENT_REFS = 100


class OperationsRtsaDenied(Exception):
    """The requested Operations RTSA operation is not allowed."""


class OperationsRtsaForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class OperationsRtsaService:
    """Operations RTSA: governed operational incident records
    under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise OperationsRtsaDenied(
                'Operations RTSA requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'operations_rtsa', {
            'OPERATOR': {'OPERATIONS'},
            'AUDITOR': {'OPERATIONS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS operations_incidents (
                    incident_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    incident_refs TEXT NOT NULL,
                    incident_count INTEGER NOT NULL,
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
            raise OperationsRtsaForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise OperationsRtsaForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise OperationsRtsaForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'OPERATIONS', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise OperationsRtsaForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise OperationsRtsaDenied(str(exc)) from exc

    # -- contract -----------------------------------------------------

    @staticmethod
    def contract_view() -> dict:
        return {
            'canonical_name': CONTRACT.canonical_name,
            'slug': CONTRACT.slug,
            'mission': CONTRACT.mission,
            'contract_status': CONTRACT.status.value,
            'enabled': CONTRACT.enabled,
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'prohibited_operations':
                list(CONTRACT.prohibited_operations),
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The platform carries operational incident'
                    ' records presented by reference only: it'
                    ' executes nothing, deploys nothing,'
                    ' dispatches no one, and reaches into no'
                    ' live system. An assessment declared with'
                    ' no active incidents stands'
                    ' NO_INCIDENTS_SUBMITTED and cannot be'
                    ' recorded RESOLVED; an assessment with'
                    ' incidents stands INCIDENT_TRIAGE_REQUIRED'
                    ' until the recorded human triage decision.'
                    ' An ESCALATED outcome is a record inside'
                    ' this platform, not a dispatch. Operations'
                    ' RTSA is distinct from IT AI Manager and'
                    ' from Sharpshooter — the three are never'
                    ' merged. The contract remains SPECIFIED and'
                    ' enabled: False — deployment of the'
                    " intelligence is the owner's named"
                    " approval, not this build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise OperationsRtsaDenied(
                f'Operation {operation!r} is prohibited by the'
                ' Operations RTSA role contract')
        if operation not in RECORD_OPERATIONS:
            raise OperationsRtsaDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- incidents ----------------------------------------------------------

    @staticmethod
    def _incident_view(row):
        incidents = json.loads(row['incident_refs'])
        return {
            'incident_id': row['incident_id'],
            'subject_ref': row['subject_ref'],
            'incident_refs': incidents,
            'incident_count': row['incident_count'],
            'incident_state': ('NO_INCIDENTS_SUBMITTED'
                               if row['incident_count'] == 0
                               else 'INCIDENT_TRIAGE_REQUIRED'),
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

    def create_incident(self, actor, subject_ref, incident_refs,
                        scope_ref, *, region=None):
        """Record one operational incident assessment (operator
        only) over a subject and a declared set of active
        incidents, presented by reference. The incident set may
        be empty — the record then stands NO_INCIDENTS_SUBMITTED,
        exactly as the designed assessment holds, and no
        RESOLVED outcome can be recorded on it. Recording the
        assessment executes nothing and dispatches no one."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise OperationsRtsaDenied(f'A {label} is required')
        if not isinstance(incident_refs, (list, tuple)):
            raise OperationsRtsaDenied(
                'incident_refs must be a list of references')
        if len(incident_refs) > MAX_INCIDENT_REFS:
            raise OperationsRtsaDenied(
                f'At most {MAX_INCIDENT_REFS} incident references'
                ' per record')
        incidents = []
        for ref in incident_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise OperationsRtsaDenied(
                    'Every incident reference must be a non-empty'
                    ' string')
            incidents.append(ref.strip())
        now = self._now()
        incident_id = f'ops-incident-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'OPERATIONS_RTSA_INCIDENT_RECORDED', actor=actor,
                    incident_id=incident_id,
                    subject_ref=subject_ref.strip(),
                    incident_count=len(incidents))
                db.execute(
                    'INSERT INTO operations_incidents (incident_id,'
                    ' subject_ref, incident_refs, incident_count,'
                    ' scope_ref, status, outcome, evidence_ref,'
                    ' requested_by, requested_at, updated_by,'
                    ' updated_at, receipt_id) VALUES (?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?, ?, ?, ?)',
                    (incident_id, subject_ref.strip(),
                     json.dumps(incidents), len(incidents),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM operations_incidents'
                ' WHERE incident_id = ?', (incident_id,)).fetchone()
        return self._incident_view(row)

    def incidents_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'incidents', 'incidents view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM operations_incidents'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._incident_view(row) for row in rows]

    def incident_view(self, actor, role, incident_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, incident_id, 'incident view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM operations_incidents'
                ' WHERE incident_id = ?', (incident_id,)).fetchone()
        if row is None:
            raise OperationsRtsaDenied('Incident record not found')
        return self._incident_view(row)

    def incident_action(self, actor, incident_id, action, *,
                        region=None):
        """Approve or reject one requested incident record
        (operator only) — the recorded human triage decision the
        contract and the designed assessment require. Approval
        approves the RECORD; it executes nothing, deploys
        nothing, and dispatches no one."""
        self._geo(region)
        self._require_operator(actor)
        transitions = INCIDENT_TRANSITIONS.get(action)
        if transitions is None:
            raise OperationsRtsaDenied(
                f'Unknown incident action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM operations_incidents'
                    ' WHERE incident_id = ?', (incident_id,)).fetchone()
                if row is None:
                    raise OperationsRtsaDenied(
                        'Incident record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise OperationsRtsaDenied(
                        f"Cannot {action} an incident record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'OPERATIONS_RTSA_INCIDENT_ACTION', actor=actor,
                    incident_id=incident_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE operations_incidents SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE incident_id = ?',
                    (new_status, actor, now, receipt_id, incident_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM operations_incidents'
                ' WHERE incident_id = ?', (incident_id,)).fetchone()
        return self._incident_view(updated)

    def record_outcome(self, actor, incident_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved incident record's outcome
        (operator only), against a presented evidence reference.
        An outcome without evidence is refused. A RESOLVED
        outcome on a record declared with no active incidents
        is refused — NO_INCIDENTS_SUBMITTED: there is nothing
        to resolve."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise OperationsRtsaDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise OperationsRtsaDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM operations_incidents'
                    ' WHERE incident_id = ?', (incident_id,)).fetchone()
                if row is None:
                    raise OperationsRtsaDenied(
                        'Incident record not found')
                if row['status'] != 'APPROVED':
                    raise OperationsRtsaDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" incident records (this one is"
                        f" {row['status']})")
                if outcome == 'RESOLVED' \
                        and row['incident_count'] == 0:
                    raise OperationsRtsaDenied(
                        'NO_INCIDENTS_SUBMITTED: a record declared'
                        ' with no active incidents cannot be'
                        ' recorded RESOLVED')
                receipt_id = self._record(
                    'OPERATIONS_RTSA_OUTCOME_RECORDED',
                    actor=actor, incident_id=incident_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE operations_incidents SET status = ?,'
                    ' outcome = ?, evidence_ref = ?, updated_by'
                    ' = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE incident_id = ?',
                    ('OUTCOME_RECORDED', outcome,
                     evidence_ref.strip(), actor, now, receipt_id,
                     incident_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM operations_incidents'
                ' WHERE incident_id = ?', (incident_id,)).fetchone()
        return self._incident_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in INCIDENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM operations_incidents GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM operations_incidents'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_incidents = db.execute(
                'SELECT COUNT(*) AS n FROM operations_incidents'
                ' WHERE incident_count = 0').fetchone()['n']
            incidents_total = db.execute(
                'SELECT COALESCE(SUM(incident_count), 0) AS n'
                ' FROM operations_incidents').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'incidents_total': sum(by_status.values()),
            'incidents_by_status': by_status,
            'incidents_by_outcome': by_outcome,
            'records_no_incidents_submitted': no_incidents,
            'incidents_declared_total': incidents_total,
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
                    raise OperationsRtsaDenied(str(exc)) from exc
                self._record('OPERATIONS_RTSA_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
