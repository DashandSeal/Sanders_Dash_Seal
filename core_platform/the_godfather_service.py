"""The Godfather — the Godfather platform.

The production build-out of The Godfather
design (canonical catalog row #143, Band 2D),
built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q101).

NAME — verified before building, per the name
law: the owner's own correction of 2026-11-23
(decisions.md) establishes **The Godfather** as
a platform in its own right — "the Godfather
gets his own row (catalog count 142 → 143)" —
and the program queue carries it as catalog
#143; the queue-note reading matched the
owner's record exactly. The canonical
catalog's printed table ends at row #142; row
#143 stands on the owner's correction, carried
in decisions.md and the queue. No Set A, Set
B, or Set C entry names this platform in its
own right (verified by direct read of all
three), and the MASTER names it nowhere
(verified).

SEPARATION — the owner's correction of
2026-11-23 governs: **The Godfather and
Sanders Patriot Saint are TWO SEPARATE
PLATFORMS.** Set B's schema row pairs Patriot
Saint with the persona "Godfather", and Set C
gives Sanders Patriot Saint the nickname
"Godfather" (its Tier 1 entry, its summary
table, and its embedded registry record
"Sanders Patriot Saint / Godfather") — all of
those are PATRIOT SAINT'S records, recorded
exactly as found on catalog #85's build
(tranche 20); under the owner's correction the
pairing does NOT merge the two platforms. This
build carries only The Godfather identity
(#143): it claims none of Patriot Saint's
scope, purpose text, price, NAICS set, or
hostname, and merges nothing in either
direction.

DESIGNED PURPOSE — the owner's words
(2026-11-23): the Godfather and Patriot Saint
"are businesses for the public, and protection
for his bloodline" — a dual purpose, like the
watchdogs' dual roles. That owner record is
this platform's entire design record, recorded
exactly as found. The built scope is governed
records only: the platform records matters
presented by reference; it provides no
protection, transacts no business, issues no
directive, and enforces no decision itself.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
owner's design record — a business for the
public, and protection for his bloodline
(decisions.md, owner correction 2026-11-23;
canonical catalog row #143 by that
correction). No Godfather module existed in
any examined source; no Set A/B/C entry, no
price, no NAICS set, no hostname, and no
classification is attested for this platform
in its own right in any examined source.

REBUILT (everything executable in this module):
the governed platform below — The Godfather
platform's own identity and store, carrying
governed matter records:

- **Matter records**: a subject reference (a
  public-business matter or a
  bloodline-protection matter under service, by
  reference), a declared set of matter
  references, and a scope reference, carried
  as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The matter discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (GODFATHER_POSITION_CONFIRMED /
  MATTER_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no matters stands
  NO_MATTERS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no matters were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never action**: determinations
  are records placed before human operators.
  The platform provides no protection,
  transacts no business, issues no directive,
  and enforces no decision — provide_protection,
  transact_business, issue_directive,
  enforce_decision, and external_execution are
  refused by name under GODFATHER_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  matters are carried by reference only; the
  platform holds no business records content,
  no family data, no financial state, and no
  credentials — references and workflow state
  only, as across the ecosystem. No public or
  customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source. The NAICS
  set on Set B's Patriot Saint row (541512,
  561621) belongs to catalog #85's record and
  is NOT carried into this platform's built
  identity; none is invented.
- **Separation**: The Godfather platform is
  its own platform. It is not Sanders Patriot
  Saint (catalog #85 — a separate platform
  under the owner's 2026-11-23 correction),
  not Sanders Steward Sentinel (catalog #84),
  and not Sanders Strategy Hub (catalog #94) —
  identities are never merged.

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
    platform_id='the_godfather',
    name='The Godfather',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'A business for the public, and protection for his bloodline (owner record)'
DISCIPLINE = 'GODFATHER_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_godfather', 'approve_godfather', 'record_outcome',
    'view_godfather', 'view_design')
EXECUTION_OPERATIONS = ('provide_protection', 'transact_business',
    'issue_directive', 'enforce_decision',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('GODFATHER_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('GODFATHER_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED')
MAX_REFS = 100


class TheGodfatherDenied(Exception):
    """The requested The Godfather operation is not
    allowed."""


class TheGodfatherForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class TheGodfatherService:
    """The Godfather: governed records under the Godfather records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise TheGodfatherDenied(
                'The Godfather requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'the_godfather', {
            'OPERATOR': {'THE_GODFATHER'},
            'AUDITOR': {'THE_GODFATHER'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS the_godfather_records (
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
            raise TheGodfatherForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise TheGodfatherForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise TheGodfatherForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'THE_GODFATHER',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise TheGodfatherForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise TheGodfatherDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['decisions.md — owner correction 2026-11-23: The Godfather and Patriot Saint are TWO SEPARATE PLATFORMS; the Godfather gets his own row (catalog #143); dual purpose in the owner’s words', 'canonical catalog row #85 (the paired record as found: Set B persona "Godfather"; Set C nickname "Godfather") — Patriot Saint’s records, expressly NOT claimed for this platform', 'Set B (read directly): no row for The Godfather in its own right — "Godfather" appears only as Patriot Saint’s persona in its schema row; Set A carries no entry (platform registry read directly); the MASTER names it nowhere (verified)', 'Set C (read directly): no entry for The Godfather in its own right — "Godfather" appears only as Sanders Patriot Saint’s nickname in its Tier 1 entry, summary table, and embedded registry record'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The Godfather is its own platform (catalog 143, by the owner’s 2026-11-23 correction): it carries governed matter records over public-business matters and bloodline-protection matters and declared matter sets presented by reference only. Its entire design record is the owner’s words — the Godfather is a business for the public, and protection for his bloodline (a dual purpose, like the watchdogs’ dual roles) — recorded exactly as found. The built scope is records only: the platform provides no protection, transacts no business, issues no directive, and enforces no decision: provide_protection, transact_business, issue_directive, enforce_decision, and external_execution are refused by name under GODFATHER_RECORDS_ONLY, and determinations are records for human operators, never action. A record declared with no matters stands NO_MATTERS_SUBMITTED and no determination can be recorded on it. SEPARATION — TWO SEPARATE PLATFORMS (owner correction 2026-11-23): Set B’s schema row pairs Patriot Saint with the persona Godfather and Set C gives Sanders Patriot Saint the nickname Godfather — those are Patriot Saint’s records (catalog 85), recorded as found on that platform’s build; the pairing does not merge the platforms, and this build claims none of Patriot Saint’s scope, purpose text, price, NAICS set, or hostname, in either direction. No Set A, Set B, or Set C entry names The Godfather in its own right (verified by direct read of all three), and the MASTER names it nowhere. No designed price is attested for The Godfather in any examined source — the figures on the paired records stand on Patriot Saint’s row and are NOT carried. No NAICS set is attested for this platform (Patriot Saint’s Set B set is not carried), no designed hostname is recorded for it, and no classification is attested. The platform holds references and workflow state only — no business records content, no family data, no financial state, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. The Godfather is distinct from Sanders Patriot Saint (catalog 85), Sanders Steward Sentinel (catalog 84), and Sanders Strategy Hub (catalog 94) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the Godfather records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise TheGodfatherDenied(
                f'Operation {operation!r} is refused: the'
                ' Godfather platform carries'
                ' governed records only \u2014 it'
                ' provides no protection, transacts'
                ' no business, issues no directive,'
                ' and enforces no decision itself'
                ' (GODFATHER_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise TheGodfatherDenied(
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
        """Record one Godfather record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_MATTERS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record provides no protection,
        transacts no business, and issues
        no directive."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise TheGodfatherDenied(
                    f'A {label} is required')
        if not isinstance(matter_refs, (list, tuple)):
            raise TheGodfatherDenied(
                'matter_refs must be a list of references')
        if len(matter_refs) > MAX_REFS:
            raise TheGodfatherDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in matter_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise TheGodfatherDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'the-godfather-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'THE_GODFATHER_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    matter_count=len(operations))
                db.execute(
                    'INSERT INTO the_godfather_records'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM the_godfather_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise TheGodfatherDenied(
                'Godfather record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested Godfather record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise TheGodfatherDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM the_godfather_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Godfather record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise TheGodfatherDenied(
                        f"Cannot {action} a Godfather record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'THE_GODFATHER_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE the_godfather_records SET status = ?,'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (GODFATHER_POSITION_CONFIRMED or MATTER_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_MATTERS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise TheGodfatherDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise TheGodfatherDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM the_godfather_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Godfather record not found')
                if row['status'] != 'APPROVED':
                    raise TheGodfatherDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" Godfather records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['matter_count'] == 0:
                    raise TheGodfatherDenied(
                        'NO_MATTERS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'THE_GODFATHER_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE the_godfather_records SET status = ?,'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM the_godfather_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM the_godfather_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM the_godfather_records'
                ' WHERE matter_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(matter_count), 0) AS n'
                ' FROM the_godfather_records').fetchone()['n']
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
                    raise TheGodfatherDenied(str(exc)) from exc
                self._record('THE_GODFATHER_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
