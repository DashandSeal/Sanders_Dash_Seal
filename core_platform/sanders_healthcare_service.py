"""Sanders Healthcare — the healthcare
management platform.

The production build-out of the Sanders
Healthcare design (canonical catalog row #132,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q100).

NAME — verified before building, per the name
law: the canonical catalog (row #132) and Set
C Tier 3 name this platform **Sanders
Healthcare** — the queue-note reading matched
the source name exactly. Set B carries NO
entry under this name (verified by direct read
of the schema and the tier pricing file — Set
B's only healthcare row is 'Sanders Home
Healthcare', catalog #64's record, which is
expressly NOT this platform's), and Set A
carries no entry for this platform (verified
by direct read of the platform registry); the
MASTER names it nowhere (verified). Set C's
tier catalog entry is the platform's only
design record.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Care". It is
recorded exactly as found and is not adopted
as the platform's persona, name, or
identifier.

Set C's purpose text for this name —
"Healthcare management, Epic/Cerner
replacement, hospital operations, global
patient coordination" — is recorded verbatim
as found and is NOT the built scope beyond
governed healthcare management records: no
patient is treated, no patient record is
accessed, no care is coordinated live, and no
hospital is operated by this build; the
"replacement" wording is design-record
language, not a claim. Set C's classification
for this platform is C, recorded as found. The
designed hostname healthcare.sandersglobal.com
(Set C embedded registry record) sits under
the unowned parent sandersglobal.com, so it
is recorded and nothing is served there.

HIPAA BY DESIGN: this platform holds NO
protected health information and no patient
data of any kind — there is no patient
reference field in its record model at all.
Subjects are healthcare programs, facilities,
and operations lines, carried by reference
only; the platform holds references and
workflow state only, as across the ecosystem.

NO-MERGE — IDENTITY CARE: Sanders Healthcare
is its own platform. It is NOT Sanders Home
Healthcare & Caregivers (catalog #64 — the
company's own platform, with its own NAICS
record and its exclusive purple-heart seal
designation, none of which is claimed or
carried here), NOT Sanders Health Solutions
(catalog #96 — a separate platform whose
purpose the owner left open in D-N12; nothing
of it is claimed either), NOT Sanders Senior
Living (catalog #65), NOT the AI Doctor
(catalog #61), and NOT the Sanders AI
Psychiatrist (catalog #62). D-N12 ruled the
identity of catalog #64 and left #96 open; it
assigns nothing to this platform — #132's own
Set C record, stated above, is its entire
design record, recorded exactly as found.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — healthcare management,
hospital operations, and global patient
coordination (canonical catalog row #132; Set
C Tier 3 — the platform's only design record;
Set B carries no row under this name). No
Sanders Healthcare module existed in any
examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Healthcare platform's own identity and store,
carrying healthcare management records:

- **Healthcare management records**: a subject
  reference (a healthcare program, facility, or
  operations line under service, by reference),
  a declared set of program references, and a
  scope reference, carried as durable,
  receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The program discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (HEALTHCARE_POSITION_CONFIRMED /
  PROGRAM_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no programs stands
  NO_PROGRAMS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no programs were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never care**: determinations are
  records placed before human operators. The
  platform treats no patient, accesses no
  patient record, coordinates no care, and
  operates no hospital — treat_patient,
  access_patient_records, coordinate_patient_care,
  operate_hospital, and external_execution are
  refused by name under HEALTHCARE_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  programs are carried by reference only; the
  platform holds no patient data, no medical
  records, no clinical content, and no
  credentials — references and workflow state
  only, as across the ecosystem. No public or
  customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for THIS
  platform in any examined source. The NAICS
  set on Set B's 'Sanders Home Healthcare' row
  (621610, 623110) belongs to catalog #64's
  record and is NOT carried into this
  platform's built identity; none is invented.
- **Separation**: the Sanders Healthcare
  platform is its own platform, distinct from
  every platform named in the NO-MERGE note
  above — identities are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.
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
    platform_id='sanders_healthcare',
    name='Sanders Healthcare',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Healthcare management, hospital operations, global patient coordination'
DISCIPLINE = 'HEALTHCARE_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_healthcare', 'approve_healthcare', 'record_outcome',
    'view_healthcare', 'view_design')
EXECUTION_OPERATIONS = ('treat_patient', 'access_patient_records',
    'coordinate_patient_care', 'operate_hospital',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('HEALTHCARE_POSITION_CONFIRMED', 'PROGRAM_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('HEALTHCARE_POSITION_CONFIRMED', 'PROGRAM_ACTION_REQUIRED')
MAX_REFS = 100


class SandersHealthcareDenied(Exception):
    """The requested Sanders Healthcare operation is not
    allowed."""


class SandersHealthcareForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersHealthcareService:
    """Sanders Healthcare: governed healthcare management records under the healthcare records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersHealthcareDenied(
                'Sanders Healthcare requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_healthcare', {
            'OPERATOR': {'SANDERS_HEALTHCARE'},
            'AUDITOR': {'SANDERS_HEALTHCARE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_healthcare_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    program_refs TEXT NOT NULL,
                    program_count INTEGER NOT NULL,
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
            raise SandersHealthcareForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersHealthcareForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersHealthcareForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_HEALTHCARE',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersHealthcareForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersHealthcareDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #132', 'Set C Tier 3 catalog entry (read directly) — the platform’s only design record', 'Set C embedded registry record (read directly): Sanders Healthcare / Care, healthcare.sandersglobal.com — designed hostname recorded, nothing served', 'Set B: no entry under this name (verified by direct read of database_schema.sql and tier_pricing_global.py — its only healthcare row is Sanders Home Healthcare, catalog #64’s record); Set A carries no entry (platform registry read directly); the MASTER names it nowhere (verified)', 'decisions.md D-N12: rules the identity of catalog #64 (Sanders Home Healthcare & Caregivers) and leaves Sanders Health Solutions (catalog #96) open — it assigns nothing to this platform; #132 stands on its own Set C record'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Healthcare is the healthcare management platform: it carries governed healthcare management records over healthcare programs, facilities, and operations lines and declared program sets presented by reference only. Set C’s purpose text for this name — Healthcare management, Epic/Cerner replacement, hospital operations, global patient coordination — is recorded verbatim as found and is NOT the built scope: no patient is treated, no patient record is accessed, no care is coordinated live, and no hospital is operated by this build; the replacement wording is design-record language, not a claim. HIPAA BY DESIGN: the platform holds NO protected health information and no patient data of any kind — there is no patient reference field in its record model; subjects are programs, facilities, and operations lines by reference only. The platform treats no patient, accesses no patient record, coordinates no care, and operates no hospital: treat_patient, access_patient_records, coordinate_patient_care, operate_hospital, and external_execution are refused by name under HEALTHCARE_RECORDS_ONLY, and determinations are records for human operators, never care. A record declared with no programs stands NO_PROGRAMS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Care is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set C’s classification for this platform is C, recorded as found. Set B carries NO entry under this name (verified by direct read — Set B’s only healthcare row is Sanders Home Healthcare, catalog 64’s record, expressly not this platform’s), and Set A carries no entry for this platform. The designed hostname healthcare.sandersglobal.com (Set C embedded registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. No NAICS set is attested for this platform in any examined source — the NAICS set on Set B’s Sanders Home Healthcare row belongs to catalog 64 and is NOT carried — and none is invented. NO-MERGE: Sanders Healthcare is distinct from Sanders Home Healthcare & Caregivers (catalog 64 — its NAICS record and its exclusive purple-heart seal designation are not claimed or carried), Sanders Health Solutions (catalog 96 — purpose left open by the owner in D-N12; nothing of it claimed), Sanders Senior Living (catalog 65), the AI Doctor (catalog 61), and the Sanders AI Psychiatrist (catalog 62) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the healthcare records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersHealthcareDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Healthcare platform'
                ' carries healthcare management records'
                ' only \u2014 it treats no'
                ' patient, accesses no patient'
                ' record, coordinates no care,'
                ' and operates no hospital itself'
                ' (HEALTHCARE_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersHealthcareDenied(
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
        operations = json.loads(row['program_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'program_refs': operations,
            'program_count': row['program_count'],
            'program_state': ('NO_PROGRAMS_SUBMITTED'
                             if row['program_count'] == 0
                             else 'PROGRAMS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, program_refs,
                      scope_ref, *, region=None):
        """Record one healthcare record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_PROGRAMS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record treats no patient,
        accesses no patient record, and
        coordinates no care."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersHealthcareDenied(
                    f'A {label} is required')
        if not isinstance(program_refs, (list, tuple)):
            raise SandersHealthcareDenied(
                'program_refs must be a list of references')
        if len(program_refs) > MAX_REFS:
            raise SandersHealthcareDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in program_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersHealthcareDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-healthcare-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_HEALTHCARE_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    program_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_healthcare_records'
                    ' (record_id, subject_ref, program_refs,'
                    ' program_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(operations), len(operations),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_healthcare_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_healthcare_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_healthcare_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersHealthcareDenied(
                'Healthcare record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested healthcare record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersHealthcareDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_healthcare_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersHealthcareDenied(
                        'Healthcare record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersHealthcareDenied(
                        f"Cannot {action} a healthcare record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_HEALTHCARE_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_healthcare_records SET status = ?,'
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
                'SELECT * FROM sanders_healthcare_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (HEALTHCARE_POSITION_CONFIRMED or PROGRAM_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_PROGRAMS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersHealthcareDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersHealthcareDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_healthcare_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersHealthcareDenied(
                        'Healthcare record not found')
                if row['status'] != 'APPROVED':
                    raise SandersHealthcareDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" healthcare records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['program_count'] == 0:
                    raise SandersHealthcareDenied(
                        'NO_PROGRAMS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_HEALTHCARE_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_healthcare_records SET status = ?,'
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
                'SELECT * FROM sanders_healthcare_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_healthcare_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_healthcare_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_healthcare_records'
                ' WHERE program_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(program_count), 0) AS n'
                ' FROM sanders_healthcare_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_programs_submitted': no_refs,
            'programs_declared_total': refs_total,
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
                    raise SandersHealthcareDenied(str(exc)) from exc
                self._record('SANDERS_HEALTHCARE_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
