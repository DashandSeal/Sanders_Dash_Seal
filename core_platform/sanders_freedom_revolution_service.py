"""Sanders Freedom Revolution — the democracy
framework and human rights platform.

The production build-out of the Sanders Freedom
Revolution design (canonical catalog row #86, Band
2D), built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q75).

NAME — verified before building, per the name law:
the canonical catalog (row #86), the Set A
registry, and Set C Tier 1 all name this platform
**Sanders Freedom Revolution** — the queue-note
reading matched the source name exactly. Set B
carries the shorter form "Freedom Revolution" (no
"Sanders" prefix — the D-N17 prefix variant) —
recorded exactly as found; the canonical name
governs the build.

PERSONA — OWNER-RULED, recorded exactly as ruled
and nothing beyond: the platform's persona is
**Uncle Freedom** (the owner's ruling, recorded in
decisions.md with his confirmations of 2026-11-23:
"Freedom Revolution AKA Uncle Freedom" — matching
Set B's persona column and Set C's nickname). The
persona is recorded here as ruled; no further
persona material is adopted or presented.

Set C's purpose text for this name — "Democracy
framework, State Department integration, regime
change support, human rights enforcement" — is
recorded verbatim as found and is NOT the built
scope beyond governed democracy-framework records:
no State Department integration, no regime-change
support operation, and no human-rights enforcement
action was constructed. The designed hostname
freedom-rev.sandersglobal.com sits under the
unowned parent sandersglobal.com, so it is
recorded and nothing is served there.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — the democracy framework and
human rights enforcement (canonical catalog row
#86; Set C Tier 1; the Set B schema seed carries
the platform at the ultra_premium tier). No
Sanders Freedom Revolution module existed in any
examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Freedom
Revolution platform's own identity and store,
carrying democracy-framework records:

- **Framework records**: a subject reference (a
  democracy initiative, human-rights matter, or
  framework program under service, by reference),
  a declared set of initiative references, and a
  scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **The initiative discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set
  (DEMOCRACY_POSITION_CONFIRMED /
  INITIATIVE_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no initiatives stands
  NO_INITIATIVES_SUBMITTED in every view and in
  the status tallies, and both determinations are
  refused on it — no initiatives were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never operations**: determinations
  are records placed before human operators. The
  platform integrates no agency, supports no
  regime change, enforces no rights, and conducts
  no operations — integrate_agency,
  support_regime_change, enforce_rights,
  conduct_operations, and external_execution are
  refused by name under
  FREEDOM_REVOLUTION_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  initiatives are carried by reference only; the
  platform holds no operational plans, no target
  data, no partner data, and no live-system state
  — references and workflow state only, as across
  the ecosystem. No public or customer surface is
  designed for this platform in any examined
  source, so none was built; no security
  internals are exposed.
- **NAICS**: two sources attest two different sets
  — Set B (541512) and the Set A registry map
  (621399, 541618, 561612, 541614, 518210,
  611430). No owner ruling assigns a set, and the
  canonical catalog row carries none — NO NAICS
  set is carried into the platform's built
  identity; both sets stand recorded as attested
  and unruled.
- **Separation**: the Sanders Freedom Revolution
  platform is its own platform. It is not Sanders
  Global Freedom (catalog #95), not Sanders
  Patriot Saint (catalog #85), and not Sanders
  Freedom Ops (catalog #107) — identities are
  never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same
transaction, through the shared foundation's audit
adapter; the service refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 813319,
813410, 813910, 813920, 541611, 541618 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
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
    platform_id='sanders_freedom_revolution',
    name='Sanders Freedom Revolution',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('813319', '813410', '813910', '813920', '541611', '541618'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Democracy framework, human rights enforcement'
DISCIPLINE = 'FREEDOM_REVOLUTION_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_freedom_revolution', 'approve_freedom_revolution', 'record_outcome',
    'view_freedom_revolution', 'view_design')
EXECUTION_OPERATIONS = ('integrate_agency', 'support_regime_change',
    'enforce_rights', 'conduct_operations',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('DEMOCRACY_POSITION_CONFIRMED', 'INITIATIVE_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('DEMOCRACY_POSITION_CONFIRMED', 'INITIATIVE_ACTION_REQUIRED')
MAX_REFS = 100


class SandersFreedomRevolutionDenied(Exception):
    """The requested Sanders Freedom Revolution operation is not
    allowed."""


class SandersFreedomRevolutionForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersFreedomRevolutionService:
    """Sanders Freedom Revolution: governed democracy-framework records under the freedom revolution records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersFreedomRevolutionDenied(
                'Sanders Freedom Revolution requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_freedom_revolution', {
            'OPERATOR': {'SANDERS_FREEDOM_REVOLUTION'},
            'AUDITOR': {'SANDERS_FREEDOM_REVOLUTION'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_freedom_revolution_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    initiative_refs TEXT NOT NULL,
                    initiative_count INTEGER NOT NULL,
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
            raise SandersFreedomRevolutionForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersFreedomRevolutionForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersFreedomRevolutionForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_FREEDOM_REVOLUTION',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersFreedomRevolutionForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersFreedomRevolutionDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #86', 'Set A platform registry (name, hostname, NAICS map)', 'Set B schema seed row (read directly)', 'Set C Tier 1 catalog entry (read directly)', 'owner ruling (decisions.md): persona Uncle Freedom; D-N17 prefix variant'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Freedom Revolution is the democracy framework and human rights platform: it carries governed democracy-framework records over democracy initiatives, human-rights matters, and framework programs and declared initiative sets presented by reference only. Set C’s purpose text for this name — Democracy framework, State Department integration, regime change support, human rights enforcement — is recorded verbatim as found and is NOT the built scope: no State Department integration, no regime-change support operation, and no human-rights enforcement action was constructed. The platform integrates no agency, supports no regime change, enforces no rights, and conducts no operations: integrate_agency, support_regime_change, enforce_rights, conduct_operations, and external_execution are refused by name under FREEDOM_REVOLUTION_RECORDS_ONLY, and determinations are records for human operators, never operations. A record declared with no initiatives stands NO_INITIATIVES_SUBMITTED and no determination can be recorded on it. PERSONA — OWNER-RULED: the platform’s persona is Uncle Freedom (the owner’s ruling, decisions.md, confirmed 2026-11-23: “Freedom Revolution AKA Uncle Freedom”, matching Set B’s persona column and Set C’s nickname) — recorded exactly as ruled, nothing beyond it. Set B carries the shorter name form Freedom Revolution (no Sanders prefix — the D-N17 prefix variant) — recorded as found; the canonical name Sanders Freedom Revolution governs. The designed hostname freedom-rev.sandersglobal.com sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no operational plans, no target data, no partner data. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Freedom Revolution is distinct from Sanders Global Freedom (catalog 95), Sanders Patriot Saint (catalog 85), and Sanders Freedom Ops (catalog 107) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the freedom revolution records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersFreedomRevolutionDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Freedom Revolution platform'
                ' carries freedom revolution records'
                ' only \u2014 it integrates no agency,'
                ' supports no regime change, enforces'
                ' no rights, and conducts no operations'
                ' itself'
                ' (FREEDOM_REVOLUTION_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersFreedomRevolutionDenied(
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
        operations = json.loads(row['initiative_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'initiative_refs': operations,
            'initiative_count': row['initiative_count'],
            'initiative_state': ('NO_INITIATIVES_SUBMITTED'
                             if row['initiative_count'] == 0
                             else 'INITIATIVES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, initiative_refs,
                      scope_ref, *, region=None):
        """Record one freedom revolution record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_INITIATIVES_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record integrates no agency,
        supports no regime change, and enforces
        no rights."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersFreedomRevolutionDenied(
                    f'A {label} is required')
        if not isinstance(initiative_refs, (list, tuple)):
            raise SandersFreedomRevolutionDenied(
                'initiative_refs must be a list of references')
        if len(initiative_refs) > MAX_REFS:
            raise SandersFreedomRevolutionDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in initiative_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersFreedomRevolutionDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-freedom-revolution-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_FREEDOM_REVOLUTION_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    initiative_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_freedom_revolution_records'
                    ' (record_id, subject_ref, initiative_refs,'
                    ' initiative_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_freedom_revolution_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_freedom_revolution_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_freedom_revolution_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersFreedomRevolutionDenied(
                'Freedom Revolution record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested freedom revolution record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersFreedomRevolutionDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_freedom_revolution_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersFreedomRevolutionDenied(
                        'Freedom Revolution record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersFreedomRevolutionDenied(
                        f"Cannot {action} a freedom revolution record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_FREEDOM_REVOLUTION_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_freedom_revolution_records SET status = ?,'
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
                'SELECT * FROM sanders_freedom_revolution_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (DEMOCRACY_POSITION_CONFIRMED or INITIATIVE_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_INITIATIVES_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersFreedomRevolutionDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersFreedomRevolutionDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_freedom_revolution_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersFreedomRevolutionDenied(
                        'Freedom Revolution record not found')
                if row['status'] != 'APPROVED':
                    raise SandersFreedomRevolutionDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" freedom revolution records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['initiative_count'] == 0:
                    raise SandersFreedomRevolutionDenied(
                        'NO_INITIATIVES_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_FREEDOM_REVOLUTION_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_freedom_revolution_records SET status = ?,'
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
                'SELECT * FROM sanders_freedom_revolution_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_freedom_revolution_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_freedom_revolution_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_freedom_revolution_records'
                ' WHERE initiative_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(initiative_count), 0) AS n'
                ' FROM sanders_freedom_revolution_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_initiatives_submitted': no_refs,
            'initiatives_declared_total': refs_total,
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
                    raise SandersFreedomRevolutionDenied(str(exc)) from exc
                self._record('SANDERS_FREEDOM_REVOLUTION_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
