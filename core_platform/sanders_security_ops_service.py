"""Sanders Security Ops — the security
operations platform.

The production build-out of the Sanders
Security Ops design (canonical catalog row
#130, Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q98).

NAME — verified before building, per the name
law: the canonical catalog (row #130) and Set
C Tier 8 name this platform **Sanders Security
Ops** — the queue-note reading matched the
source name exactly. Set B carries NO entry
under this name (verified by direct read of
the schema and the tier pricing file), and Set
A carries no entry for this platform (verified
by direct read of the platform registry); the
MASTER names it nowhere (verified — the MASTER
contains no "Security Ops"). Set C's tier
catalog entry is the platform's only design
record.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Guardian
Shield". It is recorded exactly as found and
is not adopted as the platform's persona,
name, or identifier.

Set C's purpose text for this name — "Security
operations, physical security mastery, access
control supremacy, surveillance" — is recorded
verbatim as found and is NOT the built scope
beyond governed security operations records:
no surveillance is run, no access control is
operated, no patrol is dispatched, and no
facility is locked by this build; the
"mastery" and "supremacy" wording is
design-record language, not a claim. Set C's
classification for this platform is TS,
recorded as found.

THE SECURITY-NAME BOUNDARY — NOT DRAWN
(D-N13): decisions.md (D-N13) and the
canonical catalog record the security names —
Sanders Security (row #71), Sanders Security
Ops (this platform, row #130), Sanders
Sentinel (row #54), The Police Men (row #6),
and S & G Security Inc. (the company, not a
platform) — with NO document separating their
scopes: the owner draws the boundary lines,
and the Sanders Security / Security Ops
boundary is not yet drawn (only the Police Men
part of D-N13 was ruled). This build draws NO
boundary: it claims no scope against Sanders
Security or any other security-named platform,
cedes none, and defines neither platform's
territory against the other's. Sanders
Security Ops is built as its own governed
records platform under its own catalogued
name, exactly as designed, and nothing more is
asserted. Set C's embedded registry carries NO
separate record for Sanders Security Ops — its
only security registry entry is "Sanders
Security / Shield" (security.sandersglobal.com),
which is Sanders Security's record and is NOT
claimed for this platform; no designed
hostname is recorded for Sanders Security Ops
in any examined source.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — security operations,
physical security, access control, and
surveillance (canonical catalog row #130; Set
C Tier 8 — the platform's only design record;
Set B carries no row), and the D-N13 record
that the security-name boundaries are undrawn.
No Sanders Security Ops module existed in any
examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Security Ops platform's own identity and store,
carrying security operations records:

- **Security operations records**: a subject
  reference (a security program, site
  operations line, or operations plan under
  service, by reference), a declared set of
  operation references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The operations discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (SECURITY_POSITION_CONFIRMED /
  OPERATIONS_ACTION_REQUIRED / INCONCLUSIVE).
  A record declared with no operations stands
  NO_OPERATIONS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no operations were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never operations**: determinations
  are records placed before human operators.
  The platform runs no surveillance, operates
  no access control, dispatches no patrol, and
  locks no facility — run_surveillance,
  operate_access_control, dispatch_patrol,
  lock_facility, and external_execution are
  refused by name under SECURITY_OPS_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  operations are carried by reference only; the
  platform holds no surveillance content, no
  access-control state, no site data, and no
  credentials — references and workflow state
  only, as across the ecosystem. No public or
  customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B
  row; no Set A entry; no Set C NAICS
  attestation) — NO NAICS set is carried into
  the platform's built identity and none is
  invented.
- **Separation**: the Sanders Security Ops
  platform is its own platform. It is not
  Sanders Security (catalog #71), not Sanders
  Sentinel (catalog #54), not The Police Men
  (catalog #6), and not S & G Security Inc.
  (corporate headquarters — a company, not a
  platform) — identities are never merged, and
  per D-N13 no boundary between the
  security-named platforms is drawn by this
  build in either direction.

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
    platform_id='sanders_security_ops',
    name='Sanders Security Ops',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Security operations, physical security, access control, surveillance'
DISCIPLINE = 'SECURITY_OPS_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_security_ops', 'approve_security_ops', 'record_outcome',
    'view_security_ops', 'view_design')
EXECUTION_OPERATIONS = ('run_surveillance', 'operate_access_control',
    'dispatch_patrol', 'lock_facility',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SECURITY_POSITION_CONFIRMED', 'OPERATIONS_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SECURITY_POSITION_CONFIRMED', 'OPERATIONS_ACTION_REQUIRED')
MAX_REFS = 100


class SandersSecurityOpsDenied(Exception):
    """The requested Sanders Security Ops operation is not
    allowed."""


class SandersSecurityOpsForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersSecurityOpsService:
    """Sanders Security Ops: governed security operations records under the security operations records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersSecurityOpsDenied(
                'Sanders Security Ops requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_security_ops', {
            'OPERATOR': {'SANDERS_SECURITY_OPS'},
            'AUDITOR': {'SANDERS_SECURITY_OPS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_security_ops_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    operation_refs TEXT NOT NULL,
                    operation_count INTEGER NOT NULL,
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
            raise SandersSecurityOpsForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersSecurityOpsForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersSecurityOpsForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_SECURITY_OPS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersSecurityOpsForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersSecurityOpsDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #130', 'Set C Tier 8 catalog entry (read directly) — the platform’s only design record', 'decisions.md D-N13 and canonical catalog row #130: the security-name boundaries (Sanders Security / Security Ops) are not drawn — only the Police Men part of D-N13 was ruled', 'Set C embedded registry (read directly): NO separate Sanders Security Ops record — the only security entry is Sanders Security / Shield (security.sandersglobal.com), Sanders Security’s record, not claimed for this platform', 'Set B: no entry under this name (verified by direct read of database_schema.sql and tier_pricing_global.py); Set A carries no entry (platform registry read directly); the MASTER names it nowhere (verified)'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Security Ops is the security operations platform: it carries governed security operations records over security programs, site operations lines, and operations plans and declared operation sets presented by reference only. Set C’s purpose text for this name — Security operations, physical security mastery, access control supremacy, surveillance — is recorded verbatim as found and is NOT the built scope: no surveillance is run, no access control is operated, no patrol is dispatched, and no facility is locked by this build; the mastery and supremacy wording is design-record language, not a claim. The platform runs no surveillance, operates no access control, dispatches no patrol, and locks no facility: run_surveillance, operate_access_control, dispatch_patrol, lock_facility, and external_execution are refused by name under SECURITY_OPS_RECORDS_ONLY, and determinations are records for human operators, never operations. A record declared with no operations stands NO_OPERATIONS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Guardian Shield is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set C’s classification for this platform is TS, recorded as found. THE SECURITY-NAME BOUNDARY IS NOT DRAWN (D-N13): no document separates the scopes of Sanders Security (catalog 71), Sanders Security Ops (catalog 130), Sanders Sentinel (catalog 54), and The Police Men (catalog 6), and the owner has not drawn the Sanders Security / Security Ops boundary — this build claims no scope against any of them, cedes none, and draws no boundary in either direction. Set C’s embedded registry carries no separate record for Sanders Security Ops; its only security registry entry (Sanders Security / Shield, security.sandersglobal.com) is Sanders Security’s record and is not claimed for this platform, and no designed hostname is recorded for Sanders Security Ops in any examined source. Set B carries NO entry under this name (verified by direct read), Set A carries no entry for this platform, and the MASTER names it nowhere. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no surveillance content, no access-control state, no site data, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Security Ops is distinct from Sanders Security (catalog 71), Sanders Sentinel (catalog 54), The Police Men (catalog 6), and S & G Security Inc. (a company, not a platform) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the security operations records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersSecurityOpsDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Security Ops platform'
                ' carries security operations records'
                ' only \u2014 it runs no'
                ' surveillance, operates no access'
                ' control, dispatches no patrol, and'
                ' locks no facility itself'
                ' (SECURITY_OPS_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersSecurityOpsDenied(
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
        operations = json.loads(row['operation_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'operation_refs': operations,
            'operation_count': row['operation_count'],
            'operation_state': ('NO_OPERATIONS_SUBMITTED'
                             if row['operation_count'] == 0
                             else 'OPERATIONS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, operation_refs,
                      scope_ref, *, region=None):
        """Record one security operations record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_OPERATIONS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record runs no surveillance,
        operates no access control, and
        dispatches no patrol."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersSecurityOpsDenied(
                    f'A {label} is required')
        if not isinstance(operation_refs, (list, tuple)):
            raise SandersSecurityOpsDenied(
                'operation_refs must be a list of references')
        if len(operation_refs) > MAX_REFS:
            raise SandersSecurityOpsDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in operation_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersSecurityOpsDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-security-ops-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_SECURITY_OPS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    operation_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_security_ops_records'
                    ' (record_id, subject_ref, operation_refs,'
                    ' operation_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_security_ops_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_security_ops_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_security_ops_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersSecurityOpsDenied(
                'Security Ops record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested security operations record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersSecurityOpsDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_security_ops_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSecurityOpsDenied(
                        'Security Ops record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersSecurityOpsDenied(
                        f"Cannot {action} a security operations record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_SECURITY_OPS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_security_ops_records SET status = ?,'
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
                'SELECT * FROM sanders_security_ops_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SECURITY_POSITION_CONFIRMED or OPERATIONS_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_OPERATIONS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersSecurityOpsDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersSecurityOpsDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_security_ops_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSecurityOpsDenied(
                        'Security Ops record not found')
                if row['status'] != 'APPROVED':
                    raise SandersSecurityOpsDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" security operations records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['operation_count'] == 0:
                    raise SandersSecurityOpsDenied(
                        'NO_OPERATIONS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_SECURITY_OPS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_security_ops_records SET status = ?,'
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
                'SELECT * FROM sanders_security_ops_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_security_ops_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_security_ops_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_security_ops_records'
                ' WHERE operation_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(operation_count), 0) AS n'
                ' FROM sanders_security_ops_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_operations_submitted': no_refs,
            'operations_declared_total': refs_total,
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
                    raise SandersSecurityOpsDenied(str(exc)) from exc
                self._record('SANDERS_SECURITY_OPS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
