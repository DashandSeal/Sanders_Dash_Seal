"""Sanders Patriot Saint — the strategic
governance and constitutional authority framework
platform.

The production build-out of the Sanders Patriot
Saint design (canonical catalog row #85, Band
2D), built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q74).

NAME — verified before building, per the name law:
the canonical catalog (row #85), the Set A
registry, and Set C Tier 1 all name this platform
**Sanders Patriot Saint** — the queue-note reading
matched the source name exactly. Set B carries the
shorter form "Patriot Saint" (no "Sanders" prefix)
— recorded exactly as found; the canonical name
governs the build.

IDENTITY — the owner's correction of 2026-11-23
governs: **The Godfather and Patriot Saint are TWO
SEPARATE PLATFORMS** (catalog #143 The Godfather is
its own platform, Q101 — not built in this
tranche). Set B's schema row pairs this platform
with the persona "Godfather" and Set C carries the
nickname "Godfather" — both recorded exactly as
found; under the owner's correction that pairing
does NOT merge the two platforms, and this build
carries only the Sanders Patriot Saint identity
(#85), claims none of The Godfather's scope, and
merges nothing.

Set C's purpose text for this name — "Strategic
governance, Joint Chiefs integration,
constitutional authority framework, presidential
briefings" — is recorded verbatim as found and is
NOT the built scope beyond governed governance
records: no Joint Chiefs integration, no
presidential briefing delivery, and no exercise of
constitutional authority was constructed. The
designed hostname patriot-saint.sandersglobal.com
sits under the unowned parent sandersglobal.com,
so it is recorded and nothing is served there.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — strategic governance and the
constitutional authority framework (canonical
catalog row #85; Set C Tier 1; the Set B schema
seed carries the platform at the ultra_premium
tier). No Sanders Patriot Saint module existed in
any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Patriot
Saint platform's own identity and store, carrying
governance records:

- **Governance records**: a subject reference (a
  governance matter, institution, or framework
  under service, by reference), a declared set of
  briefing references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by
  a human operator's recorded decision, then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The briefing discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set (GOVERNANCE_POSITION_CONFIRMED
  / BRIEFING_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no briefings stands
  NO_BRIEFINGS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no briefings were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never authority**: determinations are
  records placed before human operators. The
  platform issues no directive, exercises no
  authority, integrates no command, and delivers
  no briefing — issue_directive,
  exercise_authority, integrate_command,
  deliver_briefing, and external_execution are
  refused by name under PATRIOT_SAINT_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  briefings are carried by reference only; the
  platform holds no classified material, no
  briefing content, no directive text, and no
  live-system state — references and workflow
  state only, as across the ecosystem.
- **NAICS**: two sources attest two different sets
  — Set B (541512, 561621) and the Set A registry
  map (621399, 922190, 561612, 523991, 541715,
  611430). No owner ruling assigns a set, and the
  canonical catalog row carries none — NO NAICS
  set is carried into the platform's built
  identity; both sets stand recorded as attested
  and unruled.
- **Separation**: the Sanders Patriot Saint
  platform is its own platform. It is not The
  Godfather (catalog #143 — a separate platform
  under the owner's 2026-11-23 correction), not
  Sanders Freedom Revolution (catalog #86), and
  not Sanders Strategy Hub (catalog #94) —
  identities are never merged.

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
    platform_id='sanders_patriot_saint',
    name='Sanders Patriot Saint',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Strategic governance, constitutional authority framework'
DISCIPLINE = 'PATRIOT_SAINT_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_patriot_saint', 'approve_patriot_saint', 'record_outcome',
    'view_patriot_saint', 'view_design')
EXECUTION_OPERATIONS = ('issue_directive', 'exercise_authority',
    'integrate_command', 'deliver_briefing',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('GOVERNANCE_POSITION_CONFIRMED', 'BRIEFING_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('GOVERNANCE_POSITION_CONFIRMED', 'BRIEFING_ACTION_REQUIRED')
MAX_REFS = 100


class SandersPatriotSaintDenied(Exception):
    """The requested Sanders Patriot Saint operation is not
    allowed."""


class SandersPatriotSaintForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersPatriotSaintService:
    """Sanders Patriot Saint: governed governance records under the patriot saint records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersPatriotSaintDenied(
                'Sanders Patriot Saint requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_patriot_saint', {
            'OPERATOR': {'SANDERS_PATRIOT_SAINT'},
            'AUDITOR': {'SANDERS_PATRIOT_SAINT'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_patriot_saint_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    briefing_refs TEXT NOT NULL,
                    briefing_count INTEGER NOT NULL,
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
            raise SandersPatriotSaintForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersPatriotSaintForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersPatriotSaintForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_PATRIOT_SAINT',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersPatriotSaintForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersPatriotSaintDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #85', 'Set A platform registry (name, hostname, NAICS map)', 'Set B schema seed row (read directly)', 'Set C Tier 1 catalog entry (read directly)', 'owner correction 2026-11-23 (decisions.md): Godfather and Patriot Saint are two separate platforms'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Patriot Saint is the strategic governance and constitutional authority framework platform: it carries governed governance records over governance matters, institutions, and frameworks and declared briefing sets presented by reference only. Set C’s purpose text for this name — Strategic governance, Joint Chiefs integration, constitutional authority framework, presidential briefings — is recorded verbatim as found and is NOT the built scope: no Joint Chiefs integration, no presidential briefing delivery, and no exercise of constitutional authority was constructed. The platform issues no directive, exercises no authority, integrates no command, and delivers no briefing: issue_directive, exercise_authority, integrate_command, deliver_briefing, and external_execution are refused by name under PATRIOT_SAINT_RECORDS_ONLY, and determinations are records for human operators, never acts of authority. A record declared with no briefings stands NO_BRIEFINGS_SUBMITTED and no determination can be recorded on it. IDENTITY: under the owner’s 2026-11-23 correction, The Godfather and Patriot Saint are TWO SEPARATE PLATFORMS — Set B’s persona pairing Godfather and Set C’s nickname Godfather are recorded as found, but this build carries only the Sanders Patriot Saint identity (catalog 85), claims none of The Godfather’s scope (catalog 143), and merges nothing. Set B carries the shorter name form Patriot Saint (no Sanders prefix) — recorded as found; the canonical name Sanders Patriot Saint governs. The designed hostname patriot-saint.sandersglobal.com sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no classified material, no briefing content, no directive text. Sanders Patriot Saint is distinct from The Godfather (catalog 143), Sanders Freedom Revolution (catalog 86), and Sanders Strategy Hub (catalog 94) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the patriot saint records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersPatriotSaintDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Patriot Saint platform'
                ' carries patriot saint records only'
                ' \u2014 it issues no directive, exercises'
                ' no authority, integrates no command,'
                ' and delivers no briefing itself'
                ' (PATRIOT_SAINT_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersPatriotSaintDenied(
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
        operations = json.loads(row['briefing_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'briefing_refs': operations,
            'briefing_count': row['briefing_count'],
            'briefing_state': ('NO_BRIEFINGS_SUBMITTED'
                             if row['briefing_count'] == 0
                             else 'BRIEFINGS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, briefing_refs,
                      scope_ref, *, region=None):
        """Record one patriot saint record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_BRIEFINGS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record issues no directive,
        exercises no authority, and delivers
        no briefing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersPatriotSaintDenied(
                    f'A {label} is required')
        if not isinstance(briefing_refs, (list, tuple)):
            raise SandersPatriotSaintDenied(
                'briefing_refs must be a list of references')
        if len(briefing_refs) > MAX_REFS:
            raise SandersPatriotSaintDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in briefing_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersPatriotSaintDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-patriot-saint-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    briefing_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_patriot_saint_records'
                    ' (record_id, subject_ref, briefing_refs,'
                    ' briefing_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_patriot_saint_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersPatriotSaintDenied(
                'Patriot Saint record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested patriot saint record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersPatriotSaintDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_patriot_saint_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Patriot Saint record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersPatriotSaintDenied(
                        f"Cannot {action} a patriot saint record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_patriot_saint_records SET status = ?,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (GOVERNANCE_POSITION_CONFIRMED or BRIEFING_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_BRIEFINGS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersPatriotSaintDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersPatriotSaintDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_patriot_saint_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Patriot Saint record not found')
                if row['status'] != 'APPROVED':
                    raise SandersPatriotSaintDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" patriot saint records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['briefing_count'] == 0:
                    raise SandersPatriotSaintDenied(
                        'NO_BRIEFINGS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_patriot_saint_records SET status = ?,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_patriot_saint_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_patriot_saint_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_patriot_saint_records'
                ' WHERE briefing_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(briefing_count), 0) AS n'
                ' FROM sanders_patriot_saint_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_briefings_submitted': no_refs,
            'briefings_declared_total': refs_total,
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
                    raise SandersPatriotSaintDenied(str(exc)) from exc
                self._record('SANDERS_PATRIOT_SAINT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
