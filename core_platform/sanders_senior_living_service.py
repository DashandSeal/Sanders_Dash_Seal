"""Sanders Senior Living — the senior living and
assisted care platform.

The production build-out of the Sanders Senior Living
design (canonical catalog row #65, Band 2D), built whole
as its own platform service over the shared RTSA
foundation (RTSA Build Program Q56).

NAME — verified before building, per the name law: the
canonical catalog (row #65), the master grid
(deploy/oracle/sanders_master_grid.json id 11), the Set
B schema seed, and the pre-existing registry record all
name this platform **Sanders Senior Living**. The name
is also the name of the owner's company, Sanders Senior
Living LLC — and the platform is NOT the LLC: this build
is the platform of that name (the grid entry and the Set
B platform seed), a platform with its own identity,
store, and records, distinct from the company itself,
exactly as the owner drew the same distinction for the
Home Healthcare RTSA and its LLC. Nothing here is merged
with any company record, and no company record is
carried into the platform. The nickname "SeniorNest"
(the grid and the Set B seed agree) is recorded here
exactly as found and is not adopted as the platform's
name.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Senior living / assisted care" (canonical
catalog row #65; master grid id 11; the Set B schema
seed carries the platform at the professional tier). Set
C carries no entry under this name (verified by direct
read of the tier catalog). The grid endpoint the records
carry (a Google Cloud host, :3011) is a file claim, not
a verified live check, and the grid file is truncated at
id 28; no Sanders Senior Living module existed in any
examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Senior Living
platform's own identity and store, carrying
care-coordination records:

- **Care records**: a subject reference (a residence or
  care program under coordination, by reference), a
  declared set of care-plan references, and a scope
  reference, carried as durable, receipted records with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The plan discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (CARE_PLAN_CONFIRMED / CARE_ADJUSTMENT_REQUIRED /
  INCONCLUSIVE). A record declared with no care plans
  stands NO_PLANS_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no plans were presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Records, never care operations**: determinations
  are records placed before human operators. The
  platform operates no residence, admits no one,
  discharges no one, and provides no care itself —
  admit_resident, provide_care, administer_medication,
  discharge_resident, and external_execution are refused
  by name under CARE_COORDINATION_RECORDS_ONLY.
- **Reference-only, HIPAA-by-design discipline**:
  subjects and plans are carried by reference only; the
  platform holds no resident names, no health data, no
  care notes, and no live-system state — references and
  workflow state only, as across the ecosystem.
- **NAICS**: two sources attest two different sets —
  the grid (623311, 623312, 623110, 623990, 541511,
  541512, 541690, 541512 — eight entries as found, with
  541512 appearing twice) and Set B (623311, 623312). No
  owner ruling assigns a set, and the canonical catalog
  row carries none — NO NAICS set is carried into the
  platform's built identity; both sets stand recorded as
  attested and unruled.
- **Separation**: the Sanders Senior Living platform is
  its own platform. It is not Sanders Senior Living LLC
  (the company), not Sanders Home Healthcare &
  Caregivers (catalog #64), not Sanders Healthcare
  (catalog #132), and not Sanders Wellness (catalog
  #81) — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 623110,
623311, 623312, 624120, 621610, 541611 — COMPOSED per the
NACI six-code reconciliation of 2026-11-26. The attested
sets recorded above stand as found; the reconciled six
govern the built identity from this lock-in forward.
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


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='sanders_senior_living',
    name='Sanders Senior Living',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('623110', '623311', '623312', '624120', '621610', '541611'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Senior living / assisted care'
DISCIPLINE = 'CARE_COORDINATION_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_care', 'approve_care', 'record_outcome',
    'view_care', 'view_design')
EXECUTION_OPERATIONS = ('admit_resident', 'provide_care',
    'administer_medication', 'discharge_resident',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('CARE_PLAN_CONFIRMED', 'CARE_ADJUSTMENT_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('CARE_PLAN_CONFIRMED', 'CARE_ADJUSTMENT_REQUIRED')
MAX_REFS = 100


class SandersSeniorLivingDenied(Exception):
    """The requested Sanders Senior Living operation is not
    allowed."""


class SandersSeniorLivingForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersSeniorLivingService:
    """Sanders Senior Living: governed senior-living care-coordination
    records under the care-coordination records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersSeniorLivingDenied(
                'Sanders Senior Living requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_senior_living', {
            'OPERATOR': {'SANDERS_SENIOR_LIVING'},
            'AUDITOR': {'SANDERS_SENIOR_LIVING'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_senior_living_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    plan_refs TEXT NOT NULL,
                    plan_count INTEGER NOT NULL,
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
            raise SandersSeniorLivingForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersSeniorLivingForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersSeniorLivingForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_SENIOR_LIVING',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersSeniorLivingForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersSeniorLivingDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #65',
                'deploy/oracle/sanders_master_grid.json id 11',
                'Set B schema seed row (read directly);'
                ' Set C carries no entry under this name',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Senior Living is the senior'
                    ' living and assisted care platform: it'
                    ' carries governed care-coordination'
                    ' records over residences and care'
                    ' programs and care plans presented by'
                    ' reference only. The platform is not'
                    ' Sanders Senior Living LLC \u2014 a'
                    ' platform bearing a company\u2019s name'
                    ' is still a platform, distinct from the'
                    ' LLC itself, and nothing is merged with'
                    ' any company record. It operates no'
                    ' residence, admits no one, and provides'
                    ' no care itself: admit_resident,'
                    ' provide_care, administer_medication,'
                    ' discharge_resident, and'
                    ' external_execution are refused by name'
                    ' under CARE_COORDINATION_RECORDS_ONLY,'
                    ' and determinations are records for'
                    ' human operators, never acts. A record'
                    ' declared with no care plans stands'
                    ' NO_PLANS_SUBMITTED and no determination'
                    ' can be recorded on it. The nickname'
                    ' SeniorNest (grid and Set B) is recorded'
                    ' as found and is not the platform\u2019s'
                    ' name. Its two attested NAICS sets are'
                    ' recorded as found, and no NAICS set is'
                    ' carried into its identity. The platform'
                    ' holds references and workflow state'
                    ' only \u2014 no resident data of any'
                    ' kind. Sanders Senior Living is distinct'
                    ' from Sanders Home Healthcare &'
                    ' Caregivers, Sanders Healthcare, and'
                    ' Sanders Wellness \u2014 identities are'
                    ' never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a care operation or an execution operation
        the care-coordination records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersSeniorLivingDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Senior Living platform carries'
                ' care-coordination records only \u2014 it'
                ' operates no residence, admits no one, and'
                ' provides no care itself'
                ' (CARE_COORDINATION_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersSeniorLivingDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'discipline': DISCIPLINE,
            'designed_role': DESIGNED_ROLE,
        }

    # -- records ------------------------------------------------------

    @staticmethod
    def _record_view(row):
        plans = json.loads(row['plan_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'plan_refs': plans,
            'plan_count': row['plan_count'],
            'plan_state': ('NO_PLANS_SUBMITTED'
                             if row['plan_count'] == 0
                             else 'PLANS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, plan_refs,
                      scope_ref, *, region=None):
        """Record one global-care record (operator only) over
        a subject and a declared set of care-plan
        references, presented by reference. The plan set may
        be empty — the record then stands NO_PLANS_SUBMITTED,
        exactly as the plan discipline holds, and no
        determination can be recorded on it. Recording the
        record operates no residence, admits no one, and provides no care itself."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersSeniorLivingDenied(
                    f'A {label} is required')
        if not isinstance(plan_refs, (list, tuple)):
            raise SandersSeniorLivingDenied(
                'plan_refs must be a list of references')
        if len(plan_refs) > MAX_REFS:
            raise SandersSeniorLivingDenied(
                f'At most {MAX_REFS} plan'
                ' references per record')
        plans = []
        for ref in plan_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersSeniorLivingDenied(
                    'Every plan reference must be a'
                    ' non-empty string')
            plans.append(ref.strip())
        now = self._now()
        record_id = f'sanders-senior-living-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_SENIOR_LIVING_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    plan_count=len(plans))
                db.execute(
                    'INSERT INTO sanders_senior_living_records'
                    ' (record_id, subject_ref, plan_refs,'
                    ' plan_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(plans), len(plans),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_senior_living_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_senior_living_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_senior_living_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersSeniorLivingDenied(
                'Care record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested care record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersSeniorLivingDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_senior_living_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSeniorLivingDenied(
                        'Care record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersSeniorLivingDenied(
                        f"Cannot {action} a care record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_SENIOR_LIVING_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_senior_living_records SET status = ?,'
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
                'SELECT * FROM sanders_senior_living_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (CARE_PLAN_CONFIRMED or CARE_ADJUSTMENT_REQUIRED) on a
        record declared with no plans is refused —
        NO_PLANS_SUBMITTED: no plans were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersSeniorLivingDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersSeniorLivingDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_senior_living_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSeniorLivingDenied(
                        'Care record not found')
                if row['status'] != 'APPROVED':
                    raise SandersSeniorLivingDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" care records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['plan_count'] == 0:
                    raise SandersSeniorLivingDenied(
                        'NO_PLANS_SUBMITTED: a record'
                        ' declared with no plans cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_SENIOR_LIVING_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_senior_living_records SET status = ?,'
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
                'SELECT * FROM sanders_senior_living_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_senior_living_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_senior_living_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_senior_living_records'
                ' WHERE plan_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(plan_count), 0) AS n'
                ' FROM sanders_senior_living_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_plans_submitted': no_signals,
            'plans_declared_total': signals_total,
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
                    raise SandersSeniorLivingDenied(str(exc)) from exc
                self._record('SANDERS_SENIOR_LIVING_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
