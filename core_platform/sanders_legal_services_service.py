"""Sanders Legal Services — the legal
advisory platform.

The production build-out of the Sanders Legal
Services design (canonical catalog row #116,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q84).

NAME — verified before building, per the name
law: the canonical catalog (row #116) and Set C
Tier 4 name this platform **Sanders Legal
Services** — the queue-note reading matched the
source name exactly. Set B carries NO entry
under this name (verified by direct read of the
schema and the tier pricing file), and Set A
carries no entry for this platform; Set C's
tier catalog entry is the platform's only
design record.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Counsel" (its
embedded registry record pairs the platform as
"Sanders Legal Services / Counsel"). It is
recorded exactly as found and is not adopted as
the platform's persona, name, or identifier.

Set C's purpose text for this name — "Legal
advisory, International Court capability,
constitutional law, global compliance" — is
recorded verbatim as found and is NOT the built
scope beyond governed legal-services records:
no legal advice is provided, no client is
represented, no court action is filed, and no
appearance is made before any court by this
build. The designed hostname
legal-services.sandersglobal.com (Set C
registry record) sits under the unowned parent
sandersglobal.com, so it is recorded and
nothing is served there.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — legal advisory,
constitutional law, and global compliance
(canonical catalog row #116; Set C Tier 4 — the
platform's only design record; Set B carries no
row). No Sanders Legal Services module existed
in any examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders Legal
Services platform's own identity and store,
carrying legal-services records:

- **Legal-services records**: a subject
  reference (a legal matter, advisory engagement,
  or compliance program under service, by
  reference), a declared set of matter
  references, and a scope reference, carried as
  durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The matter discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set
  (LEGAL_SERVICES_POSITION_CONFIRMED /
  MATTER_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no matters stands
  NO_MATTERS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no matters were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never practice**: determinations
  are records placed before human operators. The
  platform provides no legal advice, represents
  no client, files no court action, and appears
  before no court — provide_legal_advice,
  represent_client, file_court_action,
  appear_before_court, and external_execution
  are refused by name under
  LEGAL_SERVICES_RECORDS_ONLY. The platform
  practices no law and holds itself out as no
  one's counsel.
- **Reference-only discipline**: subjects and
  matters are carried by reference only; the
  platform holds no client confidences, no case
  files, no privileged material, and no
  live-system state — references and workflow
  state only, as across the ecosystem. No public
  or customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B row;
  no Set A entry; no Set C registry NAICS map
  entry) — NO NAICS set is carried into the
  platform's built identity and none is invented.
- **Separation**: the Sanders Legal Services
  platform is its own platform. It is not
  Sanders Legal Helpers (catalog #66 — the
  legal support and compliance platform, built
  whole as Q57), not Sanders Dash & Seal
  (catalog #1), not Money Factory Legal Aid
  (catalog #7), and not Sanders Legal Helpers
  LLC (the company) — identities are never
  merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541110,
541199, 541512, 541611, 518210, 519190 — COMPLETED_NEW per
the NACI six-code reconciliation of 2026-11-26. The
attested sets recorded above stand as found; the
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


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='sanders_legal_services',
    name='Sanders Legal Services',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541110', '541199', '541512', '541611', '518210', '519190'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Legal advisory, constitutional law, global compliance'
DISCIPLINE = 'LEGAL_SERVICES_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_legal_services', 'approve_legal_services', 'record_outcome',
    'view_legal_services', 'view_design')
EXECUTION_OPERATIONS = ('provide_legal_advice', 'represent_client',
    'file_court_action', 'appear_before_court',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('LEGAL_SERVICES_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('LEGAL_SERVICES_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED')
MAX_REFS = 100


class SandersLegalServicesDenied(Exception):
    """The requested Sanders Legal Services operation is not
    allowed."""


class SandersLegalServicesForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersLegalServicesService:
    """Sanders Legal Services: governed legal-services records under the legal services records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersLegalServicesDenied(
                'Sanders Legal Services requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_legal_services', {
            'OPERATOR': {'SANDERS_LEGAL_SERVICES'},
            'AUDITOR': {'SANDERS_LEGAL_SERVICES'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_legal_services_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    matter_refs TEXT NOT NULL,
                    matter_count INTEGER NOT NULL,
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
            raise SandersLegalServicesForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersLegalServicesForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersLegalServicesForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_LEGAL_SERVICES',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersLegalServicesForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersLegalServicesDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #116', 'Set C Tier 4 catalog entry (read directly) — the platform’s only design record', 'Set B: no entry under this name (verified by direct read); Set A carries no entry', 'decisions.md: no ruling names this platform; the Sanders Legal Helpers identity (catalog #66) stays separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Legal Services is the legal advisory platform: it carries governed legal-services records over legal matters, advisory engagements, and compliance programs and declared matter sets presented by reference only. Set C’s purpose text for this name — Legal advisory, International Court capability, constitutional law, global compliance — is recorded verbatim as found and is NOT the built scope: no legal advice is provided, no client is represented, no court action is filed, and no appearance is made before any court by this build. The platform provides no legal advice, represents no client, files no court action, and appears before no court: provide_legal_advice, represent_client, file_court_action, appear_before_court, and external_execution are refused by name under LEGAL_SERVICES_RECORDS_ONLY, and determinations are records for human operators, never the practice of law. A record declared with no matters stands NO_MATTERS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Counsel is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set B carries NO entry under this name (verified by direct read), and Set A carries no entry for this platform. The designed hostname legal-services.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no client confidences, no case files, no privileged material. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Legal Services is distinct from Sanders Legal Helpers (catalog 66), Sanders Dash & Seal (catalog 1), Money Factory Legal Aid (catalog 7), and Sanders Legal Helpers LLC (the company) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the legal records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersLegalServicesDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Legal Services platform'
                ' carries legal services records'
                ' only \u2014 it provides no legal'
                ' advice, represents no client,'
                ' files no court action, and'
                ' appears before no court itself'
                ' (LEGAL_SERVICES_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersLegalServicesDenied(
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
        operations = json.loads(row['matter_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'matter_refs': operations,
            'matter_count': row['matter_count'],
            'matter_state': ('NO_MATTERS_SUBMITTED'
                             if row['matter_count'] == 0
                             else 'MATTERS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, matter_refs,
                      scope_ref, *, region=None):
        """Record one legal record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_MATTERS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record provides no
        advice, represents no client, and
        files no court action."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersLegalServicesDenied(
                    f'A {label} is required')
        if not isinstance(matter_refs, (list, tuple)):
            raise SandersLegalServicesDenied(
                'matter_refs must be a list of references')
        if len(matter_refs) > MAX_REFS:
            raise SandersLegalServicesDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in matter_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersLegalServicesDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-legal-services-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_LEGAL_SERVICES_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    matter_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_legal_services_records'
                    ' (record_id, subject_ref, matter_refs,'
                    ' matter_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_legal_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_legal_services_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_legal_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersLegalServicesDenied(
                'Legal Services record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested legal record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersLegalServicesDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_legal_services_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLegalServicesDenied(
                        'Legal Services record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersLegalServicesDenied(
                        f"Cannot {action} a legal record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_LEGAL_SERVICES_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_legal_services_records SET status = ?,'
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
                'SELECT * FROM sanders_legal_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (LEGAL_SERVICES_POSITION_CONFIRMED or MATTER_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_MATTERS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersLegalServicesDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersLegalServicesDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_legal_services_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLegalServicesDenied(
                        'Legal Services record not found')
                if row['status'] != 'APPROVED':
                    raise SandersLegalServicesDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" legal records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['matter_count'] == 0:
                    raise SandersLegalServicesDenied(
                        'NO_MATTERS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_LEGAL_SERVICES_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_legal_services_records SET status = ?,'
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
                'SELECT * FROM sanders_legal_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_legal_services_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_legal_services_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_legal_services_records'
                ' WHERE matter_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(matter_count), 0) AS n'
                ' FROM sanders_legal_services_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_matters_submitted': no_refs,
            'matters_declared_total': refs_total,
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
                    raise SandersLegalServicesDenied(str(exc)) from exc
                self._record('SANDERS_LEGAL_SERVICES_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
