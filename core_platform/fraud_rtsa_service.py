"""Fraud RTSA — the fraud intelligence RTSA.

The production build-out of the Fraud RTSA role contract
(``core_platform/rtsa_registry.py``: canonical name
"Fraud RTSA 🚨", slug ``fraud-rtsa``, mission "fraud
intelligence", SPECIFIED, enabled: False), built whole as its
own platform service over the shared RTSA foundation (RTSA
Build Program Q34).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform freezes, holds, reverses, and transfers nothing,
and it reaches into no account and no external system. What it
does is the fraud-intelligence case record, governed:

- **Case records**: fraud-intelligence cases over subjects
  and declared signal sets presented by reference, carried as
  durable, receipted records (subject reference, signal
  references, scope reference) with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision — the fraud review the role's designed offline
  assessment requires (FRAUD_REVIEW_REQUIRED) — then a
  determination recorded against presented evidence
  (DETERMINATION_RECORDED).
- **The designed signal discipline** (the role's designed
  offline assessment in ``core_platform/rtsa_assessments.py``)
  is enforced in the record model: a case declared with no
  signals stands NO_SIGNALS_SUBMITTED in every view and in
  the status tallies, and a FRAUD_SUBSTANTIATED
  determination on such a case is refused — there is nothing
  to substantiate against.
- **Determinations** are recorded only for APPROVED cases
  and only against a presented evidence reference, with a
  closed verdict set (FRAUD_SUBSTANTIATED /
  FRAUD_NOT_SUBSTANTIATED / INCONCLUSIVE). A determination
  without evidence is refused: a fraud claim with nothing
  behind it is not a record.
- **Reference-only discipline**: subjects and signals are
  carried by reference only. The platform holds no personal
  records, no financial records, and no signal payloads; a
  determination is a governed record inside this platform,
  not an accusation published anywhere, and it moves no
  money and takes no enforcement action.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed —
  whether a named operation is a record operation this
  platform may carry or a prohibited operation it refuses.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses to
exist without one.
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
    platform_id='fraud_rtsa',
    name='Fraud RTSA',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['Fraud RTSA 🚨']
RECORD_OPERATIONS = (
    'record_case', 'approve_case', 'record_determination',
    'view_case', 'view_contract',
)
CASE_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                 'DETERMINATION_RECORDED')
CASE_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
VERDICTS = ('FRAUD_SUBSTANTIATED', 'FRAUD_NOT_SUBSTANTIATED',
            'INCONCLUSIVE')
MAX_SIGNAL_REFS = 100


class FraudRtsaDenied(Exception):
    """The requested Fraud RTSA operation is not allowed."""


class FraudRtsaForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class FraudRtsaService:
    """Fraud RTSA: governed fraud-intelligence case records
    under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise FraudRtsaDenied(
                'Fraud RTSA requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'fraud_rtsa', {
            'OPERATOR': {'FRAUD'},
            'AUDITOR': {'FRAUD'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS fraud_cases (
                    case_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    signal_refs TEXT NOT NULL,
                    signal_count INTEGER NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
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
            raise FraudRtsaForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise FraudRtsaForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise FraudRtsaForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'FRAUD', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise FraudRtsaForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise FraudRtsaDenied(str(exc)) from exc

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
            'note': 'The platform carries fraud-intelligence'
                    ' case records over subjects and declared'
                    ' signal sets presented by reference only:'
                    ' it holds no personal records, no financial'
                    ' records, and no signal payloads, and it'
                    ' freezes, holds, reverses, and transfers'
                    ' nothing. A case declared with no signals'
                    ' stands NO_SIGNALS_SUBMITTED and cannot be'
                    ' determined FRAUD_SUBSTANTIATED; a case'
                    ' with signals stands FRAUD_REVIEW_REQUIRED'
                    ' until the recorded human review decision.'
                    ' A determination is a governed record'
                    ' inside this platform, not an accusation'
                    ' published anywhere. The contract remains'
                    ' SPECIFIED and enabled: False — deployment'
                    " of the intelligence is the owner's named"
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
            raise FraudRtsaDenied(
                f'Operation {operation!r} is prohibited by the'
                ' Fraud RTSA role contract')
        if operation not in RECORD_OPERATIONS:
            raise FraudRtsaDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- cases ------------------------------------------------------------

    @staticmethod
    def _case_view(row):
        signals = json.loads(row['signal_refs'])
        return {
            'case_id': row['case_id'],
            'subject_ref': row['subject_ref'],
            'signal_refs': signals,
            'signal_count': row['signal_count'],
            'signal_state': ('NO_SIGNALS_SUBMITTED'
                             if row['signal_count'] == 0
                             else 'FRAUD_REVIEW_REQUIRED'),
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_case(self, actor, subject_ref, signal_refs,
                    scope_ref, *, region=None):
        """Record one fraud-intelligence case (operator only)
        over a subject and a declared signal set, presented by
        reference. The signal set may be empty — the case then
        stands NO_SIGNALS_SUBMITTED, exactly as the designed
        assessment holds, and no FRAUD_SUBSTANTIATED
        determination can be recorded on it. Recording the
        case accuses no one and moves nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise FraudRtsaDenied(f'A {label} is required')
        if not isinstance(signal_refs, (list, tuple)):
            raise FraudRtsaDenied(
                'signal_refs must be a list of references')
        if len(signal_refs) > MAX_SIGNAL_REFS:
            raise FraudRtsaDenied(
                f'At most {MAX_SIGNAL_REFS} signal references'
                ' per case')
        signals = []
        for ref in signal_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise FraudRtsaDenied(
                    'Every signal reference must be a non-empty'
                    ' string')
            signals.append(ref.strip())
        now = self._now()
        case_id = f'fraud-case-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'FRAUD_RTSA_CASE_RECORDED', actor=actor,
                    case_id=case_id, subject_ref=subject_ref.strip(),
                    signal_count=len(signals))
                db.execute(
                    'INSERT INTO fraud_cases (case_id, subject_ref,'
                    ' signal_refs, signal_count, scope_ref, status,'
                    ' verdict, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?)',
                    (case_id, subject_ref.strip(),
                     json.dumps(signals), len(signals),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM fraud_cases WHERE case_id = ?',
                (case_id,)).fetchone()
        return self._case_view(row)

    def cases_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'cases', 'cases view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM fraud_cases ORDER BY requested_at',
            ).fetchall()
        return [self._case_view(row) for row in rows]

    def case_view(self, actor, role, case_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, case_id, 'case view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM fraud_cases WHERE case_id = ?',
                (case_id,)).fetchone()
        if row is None:
            raise FraudRtsaDenied('Case not found')
        return self._case_view(row)

    def case_action(self, actor, case_id, action, *, region=None):
        """Approve or reject one requested case (operator
        only) — the recorded human fraud-review decision the
        contract and the designed assessment require. Approval
        approves the RECORD; it freezes nothing, accuses no
        one, and executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = CASE_TRANSITIONS.get(action)
        if transitions is None:
            raise FraudRtsaDenied(
                f'Unknown case action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM fraud_cases WHERE case_id = ?',
                    (case_id,)).fetchone()
                if row is None:
                    raise FraudRtsaDenied('Case not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise FraudRtsaDenied(
                        f"Cannot {action} a case in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'FRAUD_RTSA_CASE_ACTION', actor=actor,
                    case_id=case_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE fraud_cases SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE case_id = ?',
                    (new_status, actor, now, receipt_id, case_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM fraud_cases WHERE case_id = ?',
                (case_id,)).fetchone()
        return self._case_view(updated)

    def record_determination(self, actor, case_id, verdict,
                             evidence_ref, *, region=None):
        """Record one approved case's determination (operator
        only), against a presented evidence reference. A
        determination without evidence is refused. A
        FRAUD_SUBSTANTIATED determination on a case declared
        with no signals is refused — NO_SIGNALS_SUBMITTED:
        there is nothing to substantiate against."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise FraudRtsaDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise FraudRtsaDenied(
                'An evidence reference is required to record a'
                ' determination')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM fraud_cases WHERE case_id = ?',
                    (case_id,)).fetchone()
                if row is None:
                    raise FraudRtsaDenied('Case not found')
                if row['status'] != 'APPROVED':
                    raise FraudRtsaDenied(
                        'Determinations are recorded only for'
                        f" APPROVED cases (this one is"
                        f" {row['status']})")
                if verdict == 'FRAUD_SUBSTANTIATED' \
                        and row['signal_count'] == 0:
                    raise FraudRtsaDenied(
                        'NO_SIGNALS_SUBMITTED: a case declared'
                        ' with no signals cannot be determined'
                        ' FRAUD_SUBSTANTIATED')
                receipt_id = self._record(
                    'FRAUD_RTSA_DETERMINATION_RECORDED',
                    actor=actor, case_id=case_id, verdict=verdict,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE fraud_cases SET status = ?, verdict'
                    ' = ?, evidence_ref = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE case_id = ?',
                    ('DETERMINATION_RECORDED', verdict,
                     evidence_ref.strip(), actor, now, receipt_id,
                     case_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM fraud_cases WHERE case_id = ?',
                (case_id,)).fetchone()
        return self._case_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in CASE_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM fraud_cases'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM fraud_cases'
                    ' WHERE verdict IS NOT NULL GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM fraud_cases'
                ' WHERE signal_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(signal_count), 0) AS n'
                ' FROM fraud_cases').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'cases_total': sum(by_status.values()),
            'cases_by_status': by_status,
            'cases_by_verdict': by_verdict,
            'cases_no_signals_submitted': no_signals,
            'signals_declared_total': signals_total,
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
                    raise FraudRtsaDenied(str(exc)) from exc
                self._record('FRAUD_RTSA_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
