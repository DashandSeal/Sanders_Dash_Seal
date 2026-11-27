"""SURN — the disaster and emergency intelligence RTSA.

The production build-out of the SURN role contract
(``core_platform/rtsa_registry.py``: canonical name "SURN",
slug ``surn``, mission "disaster and emergency intelligence",
SPECIFIED, enabled: False), built whole as its own platform
service over the shared RTSA foundation (RTSA Build Program
Q131, Band 4 — the first of the other platforms, founder order
2026-11-25). SURN is the Synthetic Universal Response Network
(the name as expanded in the corrected Grantwriter + SURN
architecture record, ``core_platform/grantwriter_surn_
architecture.py``).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform dispatches no responders, issues no alerts,
contacts no agency, and monitors no live feed. What it does is
the emergency-preparedness record, governed:

- **Preparedness assessments**: emergency-preparedness
  assessments presented by reference, carried as durable,
  receipted records (subject, recovery-plan, and scope
  references) with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then a
  determination recorded against presented evidence.
- **The designed emergency discipline** (the role's designed
  offline assessment in ``core_platform/rtsa_assessments.py``)
  is enforced in the record model: an assessment presented
  with no recovery plan stands EMERGENCY_PLAN_MISSING in
  every view and in the status tallies, and a DRILL_VERIFIED
  determination on such a record is refused — there is no
  plan to verify a drill against. Where a recovery plan is
  presented, the record stands EMERGENCY_DRILL_REQUIRED: a
  drill stands required before preparedness can be verified.
- **Determinations** are recorded only for APPROVED
  assessments and only against a presented evidence
  reference, with a closed determination set (DRILL_VERIFIED
  / DRILL_DEFICIENT / INCONCLUSIVE). A determination is a
  record inside this platform: it dispatches no one, alerts
  no system, and declares no real-world emergency.
- **Reference-only discipline**: subjects, recovery plans,
  and scopes are carried by reference only; the platform
  holds no plan documents, no contact lists, no credentials,
  and no live-feed state.
- **Separation**: SURN is its own platform. The corrected
  Grantwriter + SURN architecture record coordinates SURN
  with Grantwriter behind an internal event bus as a design
  record — this build activates none of it (the
  grantwriter_purpose approval gate remains UNAPPROVED, and
  Grantwriter's drafting and submission stay refused), and
  SURN's external build on Hercules is a separate build,
  neither claimed nor merged by this one. SURN is not
  Operations RTSA (operational reasoning and incident
  response) and not Emergency Global Communication (a
  domain-named platform with no design record) — the three
  are never merged.
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
identity record carries the reconciled six: 624230,
541512, 518210, 517919, 541690, 922190 — ADOPTED_EXISTING
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
    platform_id='surn',
    name='SURN',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('624230', '541512', '518210', '517919', '541690', '922190'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['SURN']
RECORD_OPERATIONS = (
    'record_assessment', 'approve_assessment',
    'record_determination', 'view_assessment', 'view_contract',
)
ASSESSMENT_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                       'DETERMINATION_RECORDED')
ASSESSMENT_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
DETERMINATIONS = ('DRILL_VERIFIED', 'DRILL_DEFICIENT',
                  'INCONCLUSIVE')


class SurnDenied(Exception):
    """The requested SURN operation is not allowed."""


class SurnForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SurnService:
    """SURN: governed emergency-preparedness assessment records
    under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SurnDenied(
                'SURN requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'surn', {
            'OPERATOR': {'SURN'},
            'AUDITOR': {'SURN'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS surn_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    recovery_plan_ref TEXT,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    determination TEXT,
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
            raise SurnForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SurnForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SurnForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SURN', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise SurnForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SurnDenied(str(exc)) from exc

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
            'note': 'The platform carries emergency-'
                    'preparedness assessment records presented'
                    ' by reference only: it dispatches no'
                    ' responders, issues no alerts, contacts'
                    ' no agency, and monitors no live feed. An'
                    ' assessment presented with no recovery'
                    ' plan stands EMERGENCY_PLAN_MISSING and a'
                    ' DRILL_VERIFIED determination on it is'
                    ' refused; an assessment with a recovery'
                    ' plan stands EMERGENCY_DRILL_REQUIRED'
                    ' until the recorded human decision and a'
                    ' determination against presented'
                    ' evidence. A determination is a record'
                    ' inside this platform, not a dispatch and'
                    ' not a declaration of any real-world'
                    ' emergency. SURN is distinct from'
                    ' Operations RTSA and from Emergency'
                    ' Global Communication — the three are'
                    ' never merged. The Grantwriter + SURN'
                    ' architecture record is a design record'
                    ' only: this build activates no event bus'
                    ' and no Grantwriter drafting or'
                    ' submission, and SURN\'s external build'
                    ' on Hercules is a separate build, neither'
                    ' claimed nor merged. The contract remains'
                    ' SPECIFIED and enabled: False —'
                    ' deployment of the intelligence is the'
                    " owner's named approval, not this"
                    " build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise SurnDenied(
                f'Operation {operation!r} is prohibited by the'
                ' SURN role contract')
        if operation not in RECORD_OPERATIONS:
            raise SurnDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- assessments --------------------------------------------------

    @staticmethod
    def _assessment_view(row):
        return {
            'assessment_id': row['assessment_id'],
            'subject_ref': row['subject_ref'],
            'recovery_plan_ref': row['recovery_plan_ref'],
            'plan_state': ('EMERGENCY_DRILL_REQUIRED'
                           if row['recovery_plan_ref']
                           else 'EMERGENCY_PLAN_MISSING'),
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'determination': row['determination'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_assessment(self, actor, subject_ref,
                          recovery_plan_ref, scope_ref, *,
                          region=None):
        """Record one emergency-preparedness assessment (operator
        only) over a subject, presented by reference. The
        recovery plan reference may be absent — the record then
        stands EMERGENCY_PLAN_MISSING, exactly as the designed
        assessment holds, and no DRILL_VERIFIED determination
        can be recorded on it. Recording the assessment
        dispatches no one and alerts no system."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SurnDenied(f'A {label} is required')
        if recovery_plan_ref is not None:
            if not isinstance(recovery_plan_ref, str):
                raise SurnDenied(
                    'recovery_plan_ref must be a reference'
                    ' string or absent')
            recovery_plan_ref = recovery_plan_ref.strip() or None
        now = self._now()
        assessment_id = f'surn-assessment-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SURN_ASSESSMENT_RECORDED', actor=actor,
                    assessment_id=assessment_id,
                    subject_ref=subject_ref.strip(),
                    recovery_plan_present=bool(recovery_plan_ref))
                db.execute(
                    'INSERT INTO surn_assessments (assessment_id,'
                    ' subject_ref, recovery_plan_ref, scope_ref,'
                    ' status, determination, evidence_ref,'
                    ' requested_by, requested_at, updated_by,'
                    ' updated_at, receipt_id) VALUES (?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?, ?, ?, ?)',
                    (assessment_id, subject_ref.strip(),
                     recovery_plan_ref, scope_ref.strip(),
                     'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM surn_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(row)

    def assessments_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assessments',
                           'assessments view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM surn_assessments'
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
                'SELECT * FROM surn_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        if row is None:
            raise SurnDenied('Assessment record not found')
        return self._assessment_view(row)

    def assessment_action(self, actor, assessment_id, action, *,
                          region=None):
        """Approve or reject one requested assessment record
        (operator only) — the recorded human decision the
        contract and the designed assessment require. Approval
        approves the RECORD; it dispatches nothing, alerts
        nothing, and activates nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ASSESSMENT_TRANSITIONS.get(action)
        if transitions is None:
            raise SurnDenied(
                f'Unknown assessment action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM surn_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise SurnDenied(
                        'Assessment record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SurnDenied(
                        f"Cannot {action} an assessment record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'SURN_ASSESSMENT_ACTION', actor=actor,
                    assessment_id=assessment_id, action=action,
                    from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE surn_assessments SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id'
                    ' = ? WHERE assessment_id = ?',
                    (new_status, actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM surn_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    def record_determination(self, actor, assessment_id,
                             determination, evidence_ref, *,
                             region=None):
        """Record one approved assessment record's determination
        (operator only), against a presented evidence reference.
        A determination without evidence is refused. A
        DRILL_VERIFIED determination on a record presented
        with no recovery plan is refused —
        EMERGENCY_PLAN_MISSING: there is no plan to verify a
        drill against."""
        self._geo(region)
        self._require_operator(actor)
        if determination not in DETERMINATIONS:
            raise SurnDenied(
                f'Unknown determination: {determination!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SurnDenied(
                'An evidence reference is required to record a'
                ' determination')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM surn_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise SurnDenied(
                        'Assessment record not found')
                if row['status'] != 'APPROVED':
                    raise SurnDenied(
                        'Determinations are recorded only for'
                        ' APPROVED assessment records (this one'
                        f" is {row['status']})")
                if determination == 'DRILL_VERIFIED' \
                        and not row['recovery_plan_ref']:
                    raise SurnDenied(
                        'EMERGENCY_PLAN_MISSING: a record'
                        ' presented with no recovery plan cannot'
                        ' be determined DRILL_VERIFIED')
                receipt_id = self._record(
                    'SURN_DETERMINATION_RECORDED',
                    actor=actor, assessment_id=assessment_id,
                    determination=determination,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE surn_assessments SET status = ?,'
                    ' determination = ?, evidence_ref = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id'
                    ' = ? WHERE assessment_id = ?',
                    ('DETERMINATION_RECORDED', determination,
                     evidence_ref.strip(), actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM surn_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ASSESSMENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM surn_assessments GROUP BY status'):
                by_status[row['status']] = row['n']
            by_determination = {d: 0 for d in DETERMINATIONS}
            for row in db.execute(
                    'SELECT determination, COUNT(*) AS n'
                    ' FROM surn_assessments'
                    ' WHERE determination IS NOT NULL'
                    ' GROUP BY determination'):
                by_determination[row['determination']] = row['n']
            plan_missing = db.execute(
                'SELECT COUNT(*) AS n FROM surn_assessments'
                ' WHERE recovery_plan_ref IS NULL'
            ).fetchone()['n']
            drill_required = db.execute(
                'SELECT COUNT(*) AS n FROM surn_assessments'
                ' WHERE recovery_plan_ref IS NOT NULL'
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'assessments_total': sum(by_status.values()),
            'assessments_by_status': by_status,
            'assessments_by_determination': by_determination,
            'records_plan_missing': plan_missing,
            'records_drill_required': drill_required,
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
                    raise SurnDenied(str(exc)) from exc
                self._record('SURN_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
