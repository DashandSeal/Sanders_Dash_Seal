"""CHORUS — the multimodal synthesis and orchestration RTSA.

The production build-out of the CHORUS role contract
(``core_platform/rtsa_registry.py``: canonical name "CHORUS",
slug ``chorus``, mission "multimodal synthesis and
orchestration", SPECIFIED, enabled: False), built whole as its
own platform service over the shared RTSA foundation (RTSA
Build Program Q31).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform performs no synthesis and no live orchestration:
it reaches into no media pipeline and drives no other system.
What it does is the composition record, governed:

- **Composition records**: multimodal compositions carried as
  durable, receipted records (subject reference, declared
  modalities, output reference, scope reference) with a
  lifecycle: PROPOSED, then AUTHORIZED or REJECTED by a human
  operator's recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **Modality discipline** is the designed core, exactly as the
  role's offline assessment holds: a composition must declare
  its modalities from the platform's closed modality set; an
  undeclared or out-of-set declaration is refused as unbounded
  (UNBOUNDED_MODALITY), and a bounded declaration still
  requires the recorded human authorization before any outcome
  may be recorded (MULTIMODAL_POLICY_REVIEW_REQUIRED).
- **Outcomes** are recorded only for AUTHORIZED compositions
  and only against a presented evidence reference, with a
  closed outcome set (COMPLETED_AS_DECLARED / DEVIATED /
  INCONCLUSIVE) — a DEVIATED outcome records that what was
  produced departed from the declared modalities or scope.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether
  a named operation is a record operation this platform may
  carry or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the
shared foundation's audit adapter; the service refuses to exist
without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541511,
541512, 518210, 519130, 541519, 541690 — ADOPTED_EXISTING
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
    platform_id='chorus',
    name='CHORUS',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541511', '541512', '518210', '519130', '541519', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['CHORUS']
RECORD_OPERATIONS = (
    'record_composition', 'authorize_composition',
    'record_outcome', 'check_modalities', 'view_composition',
    'view_contract',
)
MODALITIES = ('TEXT', 'AUDIO', 'VIDEO', 'IMAGE', 'SIGN')
COMPOSITION_STATUSES = ('PROPOSED', 'AUTHORIZED', 'REJECTED',
                        'OUTCOME_RECORDED')
COMPOSITION_TRANSITIONS = {
    'authorize': {'PROPOSED': 'AUTHORIZED'},
    'reject': {'PROPOSED': 'REJECTED'},
}
OUTCOMES = ('COMPLETED_AS_DECLARED', 'DEVIATED', 'INCONCLUSIVE')


class ChorusDenied(Exception):
    """The requested CHORUS operation is not allowed."""


class ChorusForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ChorusService:
    """CHORUS: governed multimodal composition records under
    the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ChorusDenied(
                'CHORUS requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'chorus', {
            'OPERATOR': {'SYNTHESIS'},
            'AUDITOR': {'SYNTHESIS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS chorus_compositions (
                    composition_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    modalities TEXT NOT NULL,
                    output_ref TEXT NOT NULL,
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
            raise ChorusForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ChorusForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ChorusForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SYNTHESIS', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise ChorusForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ChorusDenied(str(exc)) from exc

    @staticmethod
    def _bounded_modalities(modalities):
        """Normalize a declared modality set, or refuse it as
        unbounded: the declaration must be a non-empty list of
        distinct members of the closed modality set. An absent
        or out-of-set declaration is UNBOUNDED_MODALITY — the
        designed assessment's refusal, enforced in the service.
        """
        if not isinstance(modalities, (list, tuple)) \
                or not modalities:
            raise ChorusDenied(
                'UNBOUNDED_MODALITY: a composition must declare'
                ' its modalities from the closed set ('
                + ', '.join(MODALITIES) + ')')
        normalized = []
        for item in modalities:
            if not isinstance(item, str) \
                    or item.strip().upper() not in MODALITIES:
                raise ChorusDenied(
                    f'UNBOUNDED_MODALITY: {item!r} is not a member'
                    ' of the closed modality set ('
                    + ', '.join(MODALITIES) + ')')
            value = item.strip().upper()
            if value in normalized:
                raise ChorusDenied(
                    f'Duplicate modality declared: {value!r}')
            normalized.append(value)
        return normalized

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
            'modalities': list(MODALITIES),
            'note': 'The platform carries multimodal composition'
                    ' records only: it performs no synthesis and'
                    ' no live orchestration, and any synthesis'
                    ' itself happens outside this platform under'
                    ' its own authority. A composition must'
                    ' declare its modalities from the closed set'
                    ' — an undeclared or out-of-set declaration'
                    ' is UNBOUNDED_MODALITY and is refused — and'
                    ' a bounded declaration still requires the'
                    ' recorded human authorization'
                    ' (MULTIMODAL_POLICY_REVIEW_REQUIRED). The'
                    ' contract remains SPECIFIED and enabled:'
                    " False — deployment of the intelligence is"
                    " the owner's named approval, not this"
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
            raise ChorusDenied(
                f'Operation {operation!r} is prohibited by the'
                ' CHORUS role contract')
        if operation not in RECORD_OPERATIONS:
            raise ChorusDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    def modality_check(self, actor, role, modalities, *,
                       region=None):
        """Answer whether a declared modality set is bounded.
        Bounded is necessary, never sufficient: the human
        authorization decision remains required, and the answer
        says so."""
        self._geo(region)
        self._guard_access(actor, role, 'modalities',
                           'modality bound check')
        normalized = self._bounded_modalities(modalities)
        return {
            'modalities': normalized,
            'bounded': True,
            'policy_review_required': True,
            'note': 'MULTIMODAL_POLICY_REVIEW_REQUIRED: a bounded'
                    ' declaration still requires the recorded'
                    ' human authorization before any outcome may'
                    ' be recorded.',
        }

    # -- compositions ---------------------------------------------------

    @staticmethod
    def _composition_view(row):
        return {
            'composition_id': row['composition_id'],
            'subject_ref': row['subject_ref'],
            'modalities': json.loads(row['modalities']),
            'output_ref': row['output_ref'],
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

    def create_composition(self, actor, subject_ref, modalities,
                           output_ref, scope_ref, *, region=None):
        """Record one multimodal composition proposal (operator
        only) with its declared modalities. The declaration is
        validated against the closed modality set at record
        time: an unbounded declaration is refused, not stored.
        Recording a composition synthesizes nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('output_ref', output_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ChorusDenied(f'A {label} is required')
        normalized = self._bounded_modalities(modalities)
        now = self._now()
        composition_id = f'chorus-composition-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'CHORUS_COMPOSITION_RECORDED', actor=actor,
                    composition_id=composition_id,
                    subject_ref=subject_ref.strip(),
                    modalities=normalized)
                db.execute(
                    'INSERT INTO chorus_compositions'
                    ' (composition_id, subject_ref, modalities,'
                    ' output_ref, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (composition_id, subject_ref.strip(),
                     json.dumps(normalized), output_ref.strip(),
                     scope_ref.strip(), 'PROPOSED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM chorus_compositions'
                ' WHERE composition_id = ?',
                (composition_id,)).fetchone()
        return self._composition_view(row)

    def compositions_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'compositions',
                           'compositions view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM chorus_compositions'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._composition_view(row) for row in rows]

    def composition_view(self, actor, role, composition_id, *,
                         region=None):
        self._geo(region)
        self._guard_access(actor, role, composition_id,
                           'composition view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM chorus_compositions'
                ' WHERE composition_id = ?',
                (composition_id,)).fetchone()
        if row is None:
            raise ChorusDenied('Composition not found')
        return self._composition_view(row)

    def composition_action(self, actor, composition_id, action, *,
                           region=None):
        """Authorize or reject one proposed composition
        (operator only) — the recorded human decision the
        contract requires. Authorization authorizes the RECORD;
        it synthesizes nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = COMPOSITION_TRANSITIONS.get(action)
        if transitions is None:
            raise ChorusDenied(
                f'Unknown composition action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM chorus_compositions'
                    ' WHERE composition_id = ?',
                    (composition_id,)).fetchone()
                if row is None:
                    raise ChorusDenied('Composition not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ChorusDenied(
                        f"Cannot {action} a composition in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'CHORUS_COMPOSITION_ACTION', actor=actor,
                    composition_id=composition_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE chorus_compositions SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE composition_id = ?',
                    (new_status, actor, now, receipt_id,
                     composition_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM chorus_compositions'
                ' WHERE composition_id = ?',
                (composition_id,)).fetchone()
        return self._composition_view(updated)

    def record_outcome(self, actor, composition_id, outcome,
                       evidence_ref, *, region=None):
        """Record one authorized composition's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused: a synthesis claim
        with nothing behind it is not a record."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise ChorusDenied(f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ChorusDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM chorus_compositions'
                    ' WHERE composition_id = ?',
                    (composition_id,)).fetchone()
                if row is None:
                    raise ChorusDenied('Composition not found')
                if row['status'] != 'AUTHORIZED':
                    raise ChorusDenied(
                        'Outcomes are recorded only for AUTHORIZED'
                        f" compositions (this one is {row['status']})")
                receipt_id = self._record(
                    'CHORUS_OUTCOME_RECORDED', actor=actor,
                    composition_id=composition_id, outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE chorus_compositions SET status = ?,'
                    ' outcome = ?, evidence_ref = ?, updated_by'
                    ' = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE composition_id = ?',
                    ('OUTCOME_RECORDED', outcome,
                     evidence_ref.strip(), actor, now, receipt_id,
                     composition_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM chorus_compositions'
                ' WHERE composition_id = ?',
                (composition_id,)).fetchone()
        return self._composition_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in COMPOSITION_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' chorus_compositions GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n FROM'
                    ' chorus_compositions WHERE outcome IS NOT'
                    ' NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            by_modality = {m: 0 for m in MODALITIES}
            for row in db.execute(
                    'SELECT modalities FROM chorus_compositions'):
                for modality in json.loads(row['modalities']):
                    by_modality[modality] += 1
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'compositions_total': sum(by_status.values()),
            'compositions_by_status': by_status,
            'compositions_by_outcome': by_outcome,
            'compositions_by_modality': by_modality,
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
                    raise ChorusDenied(str(exc)) from exc
                self._record('CHORUS_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
