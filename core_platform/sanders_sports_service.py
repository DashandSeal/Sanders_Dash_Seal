"""Sanders Sports — the sports & recreation
platform.

The production build-out of the Sanders Sports
design (canonical catalog row #80, Band 2D), built
whole as its own platform service over the shared
RTSA foundation (RTSA Build Program Q71).

NAME — verified before building, per the name law:
the canonical catalog (row #80), the master grid
(deploy/oracle/sanders_master_grid.json id 26), the
Set B schema seed, and the pre-existing registry
record all name this platform **Sanders Sports** —
the queue-note reading matched the source name
exactly. The nickname "Arena" (the grid and the
Set B seed agree) is recorded here exactly as
found and is not adopted as the platform's name.
Set C carries no platform entry under this name
(verified by direct read — the slug appears only
in the Set C repo's directory scaffolding; no
section, purpose, or price).

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — "Sports & recreation"
(canonical catalog row #80; master grid id 26; the
Set B schema seed carries the platform at the
professional tier). The grid endpoint the records
carry (a Google Cloud host, :3026) is a file claim,
not a verified live check, and the grid file is
truncated at id 28; no Sanders Sports module
existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Sports
platform's own identity and store, carrying sports
records:

- **Sports records**: a subject reference (a team,
  league, venue, or sports program under service,
  by reference), a declared set of event
  references, and a scope reference, carried as
  durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The event discipline**: outcomes are recorded
  only for APPROVED records and only against a
  presented evidence reference, with a closed
  outcome set (SPORTS_POSITION_CONFIRMED /
  EVENT_ACTION_REQUIRED / INCONCLUSIVE). A record
  declared with no events stands
  NO_EVENTS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no events were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never events**: determinations are
  records placed before human operators. The
  platform stages no event, sells no ticket,
  broadcasts no event, and manages no team —
  stage_event, sell_ticket, broadcast_event,
  manage_team, and external_execution are refused
  by name under SPORTS_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  events are carried by reference only; the
  platform holds no athlete data, no event
  content, no ticketing state, and no live-system
  state — references and workflow state only, as
  across the ecosystem.
- **NAICS**: two sources attest two different sets
  — the grid (711219, 713940, 541511, 541512,
  541690, 519190) and Set B (711219). No owner
  ruling assigns a set, and the canonical catalog
  row carries none — NO NAICS set is carried into
  the platform's built identity; both sets stand
  recorded as attested and unruled.
- **Separation**: the Sanders Sports platform is
  its own platform. It is not Sanders
  Entertainment (catalog #79), not Sanders
  Wellness (catalog #81), and not Sanders Fitness
  & Wellness (catalog #90) — identities are never
  merged.

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
    platform_id='sanders_sports',
    name='Sanders Sports',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Sports & recreation'
DISCIPLINE = 'SPORTS_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_sports', 'approve_sports', 'record_outcome',
    'view_sports', 'view_design')
EXECUTION_OPERATIONS = ('stage_event', 'sell_ticket',
    'broadcast_event', 'manage_team',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SPORTS_POSITION_CONFIRMED', 'EVENT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SPORTS_POSITION_CONFIRMED', 'EVENT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersSportsDenied(Exception):
    """The requested Sanders Sports operation is not
    allowed."""


class SandersSportsForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersSportsService:
    """Sanders Sports: governed sports records under the sports records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersSportsDenied(
                'Sanders Sports requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_sports', {
            'OPERATOR': {'SANDERS_SPORTS'},
            'AUDITOR': {'SANDERS_SPORTS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_sports_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    event_refs TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
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
            raise SandersSportsForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersSportsForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersSportsForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_SPORTS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersSportsForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersSportsDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #80', 'deploy/oracle/sanders_master_grid.json id 26', 'Set B schema seed row (read directly); Set C carries no entry under this name'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Sports is the sports & recreation platform: it carries governed sports records over teams, leagues, venues, and sports programs and declared event sets presented by reference only. It stages no event, sells no ticket, broadcasts no event, and manages no team: stage_event, sell_ticket, broadcast_event, manage_team, and external_execution are refused by name under SPORTS_RECORDS_ONLY, and determinations are records for human operators, never events. A record declared with no events stands NO_EVENTS_SUBMITTED and no determination can be recorded on it. The nickname Arena (the grid and Set B agree) is recorded as found and is not adopted as the platform’s name. Set C carries no platform entry under this name. No designed hostname is recorded for this platform in any examined source. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no athlete data, no event content, no ticketing state. Sanders Sports is distinct from Sanders Entertainment (catalog #79), Sanders Wellness (catalog #81), and Sanders Fitness & Wellness (catalog #90) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the sports records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersSportsDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Sports platform carries'
                ' sports records only \u2014 it'
                ' stages no event, sells no ticket,'
                ' broadcasts no event, and manages'
                ' no team itself'
                ' (SPORTS_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersSportsDenied(
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
        operations = json.loads(row['event_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'event_refs': operations,
            'event_count': row['event_count'],
            'event_state': ('NO_EVENTS_SUBMITTED'
                             if row['event_count'] == 0
                             else 'EVENTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, event_refs,
                      scope_ref, *, region=None):
        """Record one sports record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_EVENTS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record stages no event,
        sells no ticket, and broadcasts
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersSportsDenied(
                    f'A {label} is required')
        if not isinstance(event_refs, (list, tuple)):
            raise SandersSportsDenied(
                'event_refs must be a list of references')
        if len(event_refs) > MAX_REFS:
            raise SandersSportsDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in event_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersSportsDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-sports-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_SPORTS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    event_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_sports_records'
                    ' (record_id, subject_ref, event_refs,'
                    ' event_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_sports_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_sports_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_sports_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersSportsDenied(
                'Sports record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested sports record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersSportsDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_sports_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSportsDenied(
                        'Sports record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersSportsDenied(
                        f"Cannot {action} a sports record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_SPORTS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_sports_records SET status = ?,'
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
                'SELECT * FROM sanders_sports_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SPORTS_POSITION_CONFIRMED or EVENT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_EVENTS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersSportsDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersSportsDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_sports_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSportsDenied(
                        'Sports record not found')
                if row['status'] != 'APPROVED':
                    raise SandersSportsDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" sports records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['event_count'] == 0:
                    raise SandersSportsDenied(
                        'NO_EVENTS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_SPORTS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_sports_records SET status = ?,'
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
                'SELECT * FROM sanders_sports_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_sports_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_sports_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_sports_records'
                ' WHERE event_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(event_count), 0) AS n'
                ' FROM sanders_sports_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_events_submitted': no_refs,
            'events_declared_total': refs_total,
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
                    raise SandersSportsDenied(str(exc)) from exc
                self._record('SANDERS_SPORTS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
