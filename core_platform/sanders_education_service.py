"""Sanders Education — the educational and training
platform.

The production build-out of the Sanders Education
design (canonical catalog row #67, Band 2D), built whole
as its own platform service over the shared RTSA
foundation (RTSA Build Program Q58).

NAME — verified before building, per the name law: the
canonical catalog (row #67), the master grid
(deploy/oracle/sanders_master_grid.json id 13), the Set
B schema seed, the Set C Tier 8 section, and the
pre-existing registry record all name this platform
**Sanders Education**. Two nicknames conflict as
found — "Mentor" (the grid and the Set B seed agree)
and "Learn" (Set C) — both are recorded here exactly
as found and neither is adopted as the platform's
name.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Educational & training platform" (canonical
catalog row #67; master grid id 13); Set C's purpose
text — "Education & training, learning management,
certification programs, global accreditation" (Tier 8);
Set C's designed hostname education.sandersglobal.com,
under the unowned parent sandersglobal.com — recorded
as the designed address, and nothing is served there.
The grid endpoint the records carry (a Google Cloud
host, :3013) is a file claim, not a verified live
check, and the grid file is truncated at id 28; no
Sanders Education module existed in any examined
source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Education
platform's own identity and store, carrying
education-program records:

- **Program records**: a subject reference (a training
  program or cohort under coordination, by reference),
  a declared set of course references, and a scope
  reference, carried as durable, receipted records with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The course discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (PROGRAM_CONFIRMED / PROGRAM_ADJUSTMENT_REQUIRED /
  INCONCLUSIVE). A record declared with no courses
  stands NO_COURSES_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no courses were presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Records, never instruction**: the platform's
  designed purpose is education itself, and this build
  is the governed record platform for that purpose —
  programs, curricula, and certification programs by
  reference. Determinations are records placed before
  human educators. The platform delivers no instruction,
  assesses no learner, issues no certification, and
  grants no accreditation — deliver_instruction,
  assess_learner, issue_certification,
  grant_accreditation, and external_execution are
  refused by name under EDUCATION_RECORDS_ONLY.
- **Reference-only discipline**: subjects and courses
  are carried by reference only; the platform holds no
  learner names, no learner records, no assessment
  content, and no live-system state — references and
  workflow state only, as across the ecosystem.
- **NAICS**: two sources attest two different sets —
  the grid (611430, 611710, 541511, 541512, 541519,
  541690, 519190) and Set B (611430, 611710). No owner
  ruling assigns a set, and the canonical catalog row
  carries none — NO NAICS set is carried into the
  platform's built identity; both sets stand recorded
  as attested and unruled.
- **Separation**: the Sanders Education platform is
  its own platform. It is not Sanders Advanced
  Academics (catalog #91), not Sanders Leadership
  Institute (catalog #89), and not Sanders Knowledge
  Base (catalog #104) — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.
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
    platform_id='sanders_education',
    name='Sanders Education',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Educational & training platform'
DISCIPLINE = 'EDUCATION_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_program', 'approve_program', 'record_outcome',
    'view_program', 'view_design')
EXECUTION_OPERATIONS = ('deliver_instruction', 'assess_learner',
    'issue_certification', 'grant_accreditation',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('PROGRAM_CONFIRMED', 'PROGRAM_ADJUSTMENT_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('PROGRAM_CONFIRMED', 'PROGRAM_ADJUSTMENT_REQUIRED')
MAX_REFS = 100


class SandersEducationDenied(Exception):
    """The requested Sanders Education operation is not
    allowed."""


class SandersEducationForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersEducationService:
    """Sanders Education: governed education and training program records under the education records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersEducationDenied(
                'Sanders Education requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_education', {
            'OPERATOR': {'SANDERS_EDUCATION'},
            'AUDITOR': {'SANDERS_EDUCATION'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_education_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    course_refs TEXT NOT NULL,
                    course_count INTEGER NOT NULL,
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
            raise SandersEducationForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersEducationForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersEducationForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_EDUCATION',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersEducationForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersEducationDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #67',
                'deploy/oracle/sanders_master_grid.json id 13',
                'Set B schema seed row and Set C Tier 8 section (both read directly)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Education is the educational and training platform: it carries governed education-program records over training programs and cohorts and declared course sets presented by reference only. Its designed purpose is education itself — education and training, learning management, certification programs, global accreditation (Set C) — and this build is the governed record platform for that purpose: it delivers no instruction, assesses no learner, issues no certification, and grants no accreditation: deliver_instruction, assess_learner, issue_certification, grant_accreditation, and external_execution are refused by name under EDUCATION_RECORDS_ONLY, and determinations are records for human educators, never acts. A record declared with no courses stands NO_COURSES_SUBMITTED and no determination can be recorded on it. The nicknames Mentor (grid and Set B) and Learn (Set C) conflict as found; neither is adopted as the platform’s name. Set C’s designed hostname education.sandersglobal.com sits under the unowned parent sandersglobal.com — recorded, and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no learner names, no learner records, no assessment content. Sanders Education is distinct from Sanders Advanced Academics (catalog #91), Sanders Leadership Institute (catalog #89), and Sanders Knowledge Base (catalog #104) — identities are never merged.',
        }


    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an instructional operation or an execution
        operation the education records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersEducationDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Education platform carries'
                ' education-program records only \u2014 it'
                ' delivers no instruction, assesses no'
                ' learner, and certifies no one itself'
                ' (EDUCATION_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersEducationDenied(
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
        courses = json.loads(row['course_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'course_refs': courses,
            'course_count': row['course_count'],
            'course_state': ('NO_COURSES_SUBMITTED'
                             if row['course_count'] == 0
                             else 'COURSES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, course_refs,
                      scope_ref, *, region=None):
        """Record one education-program record (operator only) over
        a subject and a declared set of course
        references, presented by reference. The course set may
        be empty — the record then stands NO_COURSES_SUBMITTED,
        exactly as the course discipline holds, and no
        determination can be recorded on it. Recording the
        record delivers no instruction, assesses no one, and
        certifies no one."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersEducationDenied(
                    f'A {label} is required')
        if not isinstance(course_refs, (list, tuple)):
            raise SandersEducationDenied(
                'course_refs must be a list of references')
        if len(course_refs) > MAX_REFS:
            raise SandersEducationDenied(
                f'At most {MAX_REFS} course'
                ' references per record')
        courses = []
        for ref in course_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersEducationDenied(
                    'Every course reference must be a'
                    ' non-empty string')
            courses.append(ref.strip())
        now = self._now()
        record_id = f'sanders-education-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_EDUCATION_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    course_count=len(courses))
                db.execute(
                    'INSERT INTO sanders_education_records'
                    ' (record_id, subject_ref, course_refs,'
                    ' course_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(courses), len(courses),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_education_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_education_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_education_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersEducationDenied(
                'Program record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested program record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersEducationDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_education_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersEducationDenied(
                        'Program record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersEducationDenied(
                        f"Cannot {action} a program record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_EDUCATION_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_education_records SET status = ?,'
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
                'SELECT * FROM sanders_education_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (PROGRAM_CONFIRMED or PROGRAM_ADJUSTMENT_REQUIRED) on a
        record declared with no courses is refused —
        NO_COURSES_SUBMITTED: no courses were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersEducationDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersEducationDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_education_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersEducationDenied(
                        'Program record not found')
                if row['status'] != 'APPROVED':
                    raise SandersEducationDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" program records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['course_count'] == 0:
                    raise SandersEducationDenied(
                        'NO_COURSES_SUBMITTED: a record'
                        ' declared with no courses cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_EDUCATION_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_education_records SET status = ?,'
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
                'SELECT * FROM sanders_education_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_education_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_education_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_education_records'
                ' WHERE course_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(course_count), 0) AS n'
                ' FROM sanders_education_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_courses_submitted': no_refs,
            'courses_declared_total': refs_total,
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
                    raise SandersEducationDenied(str(exc)) from exc
                self._record('SANDERS_EDUCATION_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
