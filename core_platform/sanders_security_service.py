"""Sanders Security — the security services
platform.

The production build-out of the Sanders Security
design (canonical catalog row #71, Band 2D), built
whole as its own platform service over the shared RTSA
foundation (RTSA Build Program Q62).

NAME — verified before building, per the name law:
the canonical catalog (row #71), the master grid
(deploy/oracle/sanders_master_grid.json id 17), the
Set B schema seed, the Set C Tier 2 section, and the
pre-existing registry record all name this platform
**Sanders Security** — the queue prose name
matched the source name exactly. Two nicknames
conflict as found — "Guard" (the grid and the Set
B seed agree) and "Shield" (Set C) — both are
recorded here exactly as found and neither is adopted
as the platform's name.

THE OPEN BOUNDARY — flagged, never drawn: the
catalog and decision D-N13 record that the boundary
between Sanders Security and Sanders Security Ops
(catalog row #130) is not drawn — the owner's
D-N13 ruling addresses the Police Men structure and
records the remaining security-name boundaries
(Sanders Security / Security Ops) as not yet drawn.
This build claims no boundary: it builds only what
the sources design for this identity — governed
security-services records — and claims none of
Security Ops' recorded scope (security operations,
physical security, access control, surveillance). The
two platforms' identities remain entirely separate,
exactly as the registry already records them.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Security services" (canonical catalog
row #71; master grid id 17); Set C's purpose text
— "Zero-trust architecture, quantum encryption,
threat hunting, comprehensive security suite" (Tier
2); Set C's designed hostname
security.sandersglobal.com, under the unowned parent
sandersglobal.com — recorded as the designed
address, and nothing is served there. The grid
endpoint the records carry (a Google Cloud host,
:3017) is a file claim, not a verified live check, and
the grid file is truncated at id 28; no Sanders
Security module existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Security
platform's own identity and store, carrying security
records:

- **Security records**: a subject reference (a system
  or facility under security service, by reference), a
  declared set of assessment references, and a scope
  reference, carried as durable, receipted records with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by
  a human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The assessment discipline**: outcomes are recorded
  only for APPROVED records and only against a
  presented evidence reference, with a closed outcome
  set (POSTURE_CONFIRMED / REMEDIATION_REQUIRED /
  INCONCLUSIVE). A record declared with no assessments
  stands NO_ASSESSMENTS_SUBMITTED in every view and in
  the status tallies, and both determinations are
  refused on it — no assessments were presented to
  determine from; INCONCLUSIVE, which asserts nothing,
  records against evidence.
- **Records, never security actions**: determinations
  are records placed before human operators. The
  platform enforces nothing, hunts no threat, blocks
  nothing, and accesses no system —
  enforce_security, hunt_threat, block_threat,
  access_system, and external_execution are refused by
  name under SECURITY_RECORDS_ONLY. No public surface
  is designed for this platform in any examined source,
  so none was built; Police Men discipline holds
  absolutely — no security internals appear on any
  public surface.
- **Reference-only discipline**: subjects and
  assessments are carried by reference only; the
  platform holds no credentials, no access, no threat
  or vulnerability content, and no live-system state
  — references and workflow state only, as across
  the ecosystem.
- **NAICS**: two sources attest two different sets
  — the grid (561621, 561612, 561622, 541511,
  541512, 541690, 519190) and Set B (561612, 561621).
  No owner ruling assigns a set, and the canonical
  catalog row carries none — NO NAICS set is
  carried into the platform's built identity; both
  sets stand recorded as attested and unruled.
- **Separation**: the Sanders Security platform is
  its own platform. It is not S & G Security Inc. (the
  company and corporate headquarters), not Sanders
  Sentinel (catalog #54), not the Police Men (catalog
  #6), and not Sanders Security Ops (catalog #130)
  — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same
transaction, through the shared foundation's audit
adapter; the service refuses to exist without one.
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
    platform_id='sanders_security',
    name='Sanders Security',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Security services'
DISCIPLINE = 'SECURITY_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_security', 'approve_security', 'record_outcome',
    'view_security', 'view_design')
EXECUTION_OPERATIONS = ('enforce_security', 'hunt_threat',
    'block_threat', 'access_system',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('POSTURE_CONFIRMED', 'REMEDIATION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('POSTURE_CONFIRMED', 'REMEDIATION_REQUIRED')
MAX_REFS = 100


class SandersSecurityDenied(Exception):
    """The requested Sanders Security operation is not
    allowed."""


class SandersSecurityForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersSecurityService:
    """Sanders Security: governed security-services records under the security records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersSecurityDenied(
                'Sanders Security requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_security', {
            'OPERATOR': {'SANDERS_SECURITY'},
            'AUDITOR': {'SANDERS_SECURITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_security_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    assessment_refs TEXT NOT NULL,
                    assessment_count INTEGER NOT NULL,
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
            raise SandersSecurityForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersSecurityForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersSecurityForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_SECURITY',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersSecurityForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersSecurityDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #71',
                'deploy/oracle/sanders_master_grid.json id 17',
                'Set B schema seed row and Set C Tier 2 section (both read directly)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Security is the security services platform: it carries governed security-services records over systems and facilities under service and declared assessment sets presented by reference only. It enforces nothing, hunts no threat, blocks nothing, and accesses no system: enforce_security, hunt_threat, block_threat, access_system, and external_execution are refused by name under SECURITY_RECORDS_ONLY, and determinations are records for human operators, never security actions. A record declared with no assessments stands NO_ASSESSMENTS_SUBMITTED and no determination can be recorded on it. Two nicknames conflict as found — “Guard” (the grid and Set B) and “Shield” (Set C) — neither is adopted as the platform’s name. Set C’s designed hostname security.sandersglobal.com sits under the unowned parent sandersglobal.com — recorded, and nothing is served there. The boundary against Sanders Security Ops (catalog #130) is not drawn in any examined source: decision D-N13 records the security-name boundaries as not yet drawn by the owner — this build draws none, claims none of Security Ops’ scope, and keeps the two platforms’ identities entirely separate. No public surface is designed for this platform in any examined source, so none was built, and no security internals appear on any surface. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no credentials, no access, no threat or vulnerability content. Sanders Security is distinct from S & G Security Inc. (the company and headquarters), Sanders Sentinel (catalog #54), the Police Men (catalog #6), and Sanders Security Ops (catalog #130) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a security-action operation or an execution
        operation the security records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersSecurityDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Security platform carries'
                ' security-services records only \u2014 it'
                ' enforces nothing, hunts no threat, and'
                ' accesses no system itself'
                ' (SECURITY_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersSecurityDenied(
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
        assessments = json.loads(row['assessment_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'assessment_refs': assessments,
            'assessment_count': row['assessment_count'],
            'assessment_state': ('NO_ASSESSMENTS_SUBMITTED'
                             if row['assessment_count'] == 0
                             else 'ASSESSMENTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, assessment_refs,
                      scope_ref, *, region=None):
        """Record one security record (operator only) over
        a subject and a declared set of assessment
        references, presented by reference. The assessment
        set may be empty — the record then stands
        NO_ASSESSMENTS_SUBMITTED, exactly as the assessment
        discipline holds, and no determination can be
        recorded on it. Recording the record enforces
        nothing, hunts no threat, and accesses no
        system."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersSecurityDenied(
                    f'A {label} is required')
        if not isinstance(assessment_refs, (list, tuple)):
            raise SandersSecurityDenied(
                'assessment_refs must be a list of references')
        if len(assessment_refs) > MAX_REFS:
            raise SandersSecurityDenied(
                f'At most {MAX_REFS} assessment'
                ' references per record')
        assessments = []
        for ref in assessment_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersSecurityDenied(
                    'Every assessment reference must be a'
                    ' non-empty string')
            assessments.append(ref.strip())
        now = self._now()
        record_id = f'sanders-security-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_SECURITY_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    assessment_count=len(assessments))
                db.execute(
                    'INSERT INTO sanders_security_records'
                    ' (record_id, subject_ref, assessment_refs,'
                    ' assessment_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(assessments), len(assessments),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_security_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_security_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_security_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersSecurityDenied(
                'Security record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested security record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersSecurityDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_security_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSecurityDenied(
                        'Security record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersSecurityDenied(
                        f"Cannot {action} a security record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_SECURITY_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_security_records SET status = ?,'
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
                'SELECT * FROM sanders_security_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (POSTURE_CONFIRMED or REMEDIATION_REQUIRED) on a
        record declared with no assessments is refused —
        NO_ASSESSMENTS_SUBMITTED: no assessments were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersSecurityDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersSecurityDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_security_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSecurityDenied(
                        'Security record not found')
                if row['status'] != 'APPROVED':
                    raise SandersSecurityDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" security records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['assessment_count'] == 0:
                    raise SandersSecurityDenied(
                        'NO_ASSESSMENTS_SUBMITTED: a record'
                        ' declared with no assessments cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_SECURITY_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_security_records SET status = ?,'
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
                'SELECT * FROM sanders_security_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_security_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_security_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_security_records'
                ' WHERE assessment_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(assessment_count), 0) AS n'
                ' FROM sanders_security_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_assessments_submitted': no_refs,
            'assessments_declared_total': refs_total,
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
                    raise SandersSecurityDenied(str(exc)) from exc
                self._record('SANDERS_SECURITY_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
