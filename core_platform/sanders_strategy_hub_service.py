"""Sanders Strategy Hub — the strategic
planning and multi-domain operations platform.

The production build-out of the Sanders Strategy
Hub design (canonical catalog row #94, Band 2D),
built whole as its own platform service over the
shared RTSA foundation (RTSA Build Program Q76).

NAME — verified before building, per the name law:
the canonical catalog (row #94), the Set A
registry, and Set C Tier 1 all name this platform
**Sanders Strategy Hub** — the queue-note reading
matched the source name exactly. Set B carries NO
entry under this name (verified by direct read).

DISPLAY NAME — D-N14 HELD: Set C's nickname for
this platform is "Radar". Under the owner's
decisions record (D-N14), "the name is just
Radar" — Radar is a name/display, NOT an
identifier (Set C also gives "Radar" to Sanders
Strategy Intel, catalog #117). No identity is
built under "Radar"; it is recorded here as a
display name only, exactly as ruled.

Set C's purpose text for this name — "Strategic
planning, STRATCOM certification, war gaming,
nuclear strategy, multi-domain operations" — is
recorded verbatim as found and is NOT the built
scope beyond governed strategic planning records:
no STRATCOM certification, no war gaming, no
nuclear strategy work, and no direction of
operations was constructed. The designed hostname
strategy-hub.sandersglobal.com sits under the
unowned parent sandersglobal.com, so it is
recorded and nothing is served there.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — strategic planning and
multi-domain operations (canonical catalog row
#94; Set C Tier 1). No Sanders Strategy Hub module
existed in any examined source; Set B carries no
row for this platform.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Strategy
Hub platform's own identity and store, carrying
strategic planning records:

- **Planning records**: a subject reference (a
  strategic plan, planning matter, or operations
  framework under service, by reference), a
  declared set of plan references, and a scope
  reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **The plan discipline**: outcomes are recorded
  only for APPROVED records and only against a
  presented evidence reference, with a closed
  outcome set (STRATEGY_POSITION_CONFIRMED /
  PLAN_ACTION_REQUIRED / INCONCLUSIVE). A record
  declared with no plans stands NO_PLANS_SUBMITTED
  in every view and in the status tallies, and
  both determinations are refused on it — no plans
  were presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against evidence.
- **Records, never direction**: determinations are
  records placed before human operators. The
  platform executes no strategy, conducts no war
  game, certifies nothing, and directs no
  operations — execute_strategy, conduct_war_game,
  certify_stratcom, direct_operations, and
  external_execution are refused by name under
  STRATEGY_HUB_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  plans are carried by reference only; the
  platform holds no classified material, no war
  plans, no operational orders, and no live-system
  state — references and workflow state only, as
  across the ecosystem. No public or customer
  surface is designed for this platform in any
  examined source, so none was built; no security
  internals are exposed.
- **NAICS**: the Set A registry map attests one
  set (621111, 541611, 561612, 541614, 541512,
  611430). No owner ruling assigns a set, and the
  canonical catalog row carries none — NO NAICS
  set is carried into the platform's built
  identity; the attested set stands recorded as
  found and unruled.
- **Separation**: the Sanders Strategy Hub
  platform is its own platform. It is not Sanders
  Consulting (catalog #77), not Sanders Strategy
  Intel (catalog #117 — which shares the "Radar"
  display name in Set C without sharing any
  identity), and not Sanders Analytics (catalog
  #118) — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same
transaction, through the shared foundation's audit
adapter; the service refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541611,
541618, 541612, 541613, 541614, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
attested sets recorded above stand as found; the
reconciled six govern the built identity from this lock-in
forward.

PURPOSE — GIVEN UNDER THE FOUNDER'S DIRECTIVE OF
2026-11-26 ("Give them purpose"): strategy hub — one place
where a client or company plans its whole course with
counsel at every level; tied to the four companies as
their shared planning room, selling access by
subscription, benefiting humanity by putting Fortune-grade
strategy within everyone's reach. This purpose is given of
record under that directive and stands as the founder's to
amend; the design description above stands as built.
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
    platform_id='sanders_strategy_hub',
    name='Sanders Strategy Hub',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541611', '541618', '541612', '541613', '541614', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Strategic planning, multi-domain operations'
DISCIPLINE = 'STRATEGY_HUB_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_strategy_hub', 'approve_strategy_hub', 'record_outcome',
    'view_strategy_hub', 'view_design')
EXECUTION_OPERATIONS = ('execute_strategy', 'conduct_war_game',
    'certify_stratcom', 'direct_operations',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('STRATEGY_POSITION_CONFIRMED', 'PLAN_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('STRATEGY_POSITION_CONFIRMED', 'PLAN_ACTION_REQUIRED')
MAX_REFS = 100


class SandersStrategyHubDenied(Exception):
    """The requested Sanders Strategy Hub operation is not
    allowed."""


class SandersStrategyHubForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersStrategyHubService:
    """Sanders Strategy Hub: governed strategic planning records under the strategy hub records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersStrategyHubDenied(
                'Sanders Strategy Hub requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_strategy_hub', {
            'OPERATOR': {'SANDERS_STRATEGY_HUB'},
            'AUDITOR': {'SANDERS_STRATEGY_HUB'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_strategy_hub_records (
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
            raise SandersStrategyHubForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersStrategyHubForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersStrategyHubForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_STRATEGY_HUB',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersStrategyHubForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersStrategyHubDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #94', 'Set A platform registry (name, hostname, NAICS map)', 'Set C Tier 1 catalog entry (read directly); Set B carries no entry under this name', 'decisions.md D-N14: "Radar" is a display name only, not an identifier'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Strategy Hub is the strategic planning and multi-domain operations platform: it carries governed strategic planning records over strategic plans, planning matters, and operations frameworks and declared plan sets presented by reference only. Set C’s purpose text for this name — Strategic planning, STRATCOM certification, war gaming, nuclear strategy, multi-domain operations — is recorded verbatim as found and is NOT the built scope: no STRATCOM certification, no war gaming, no nuclear strategy work, and no direction of operations was constructed. The platform executes no strategy, conducts no war game, certifies nothing, and directs no operations: execute_strategy, conduct_war_game, certify_stratcom, direct_operations, and external_execution are refused by name under STRATEGY_HUB_RECORDS_ONLY, and determinations are records for human operators, never direction. A record declared with no plans stands NO_PLANS_SUBMITTED and no determination can be recorded on it. DISPLAY NAME — D-N14 HELD: Set C’s nickname Radar is a name/display only, NOT an identifier (Set C also gives Radar to Sanders Strategy Intel, catalog 117); no identity is built under Radar. Set B carries NO entry under this name (verified by direct read). The designed hostname strategy-hub.sandersglobal.com sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its attested NAICS set (the Set A registry map) is recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no classified material, no war plans, no operational orders. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Strategy Hub is distinct from Sanders Consulting (catalog 77), Sanders Strategy Intel (catalog 117), and Sanders Analytics (catalog 118) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the strategy hub records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersStrategyHubDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Strategy Hub platform carries'
                ' strategy hub records only \u2014 it'
                ' executes no strategy, conducts no war'
                ' game, certifies nothing, and directs'
                ' no operations itself'
                ' (STRATEGY_HUB_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersStrategyHubDenied(
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
        operations = json.loads(row['plan_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'plan_refs': operations,
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
        """Record one strategy hub record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_PLANS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record executes no strategy,
        conducts no war game, and directs
        no operations."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersStrategyHubDenied(
                    f'A {label} is required')
        if not isinstance(plan_refs, (list, tuple)):
            raise SandersStrategyHubDenied(
                'plan_refs must be a list of references')
        if len(plan_refs) > MAX_REFS:
            raise SandersStrategyHubDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in plan_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersStrategyHubDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-strategy-hub-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_STRATEGY_HUB_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    plan_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_strategy_hub_records'
                    ' (record_id, subject_ref, plan_refs,'
                    ' plan_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_strategy_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_strategy_hub_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_strategy_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersStrategyHubDenied(
                'Strategy Hub record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested strategy hub record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersStrategyHubDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_strategy_hub_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersStrategyHubDenied(
                        'Strategy Hub record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersStrategyHubDenied(
                        f"Cannot {action} a strategy hub record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_STRATEGY_HUB_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_strategy_hub_records SET status = ?,'
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
                'SELECT * FROM sanders_strategy_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (STRATEGY_POSITION_CONFIRMED or PLAN_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_PLANS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersStrategyHubDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersStrategyHubDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_strategy_hub_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersStrategyHubDenied(
                        'Strategy Hub record not found')
                if row['status'] != 'APPROVED':
                    raise SandersStrategyHubDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" strategy hub records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['plan_count'] == 0:
                    raise SandersStrategyHubDenied(
                        'NO_PLANS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_STRATEGY_HUB_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_strategy_hub_records SET status = ?,'
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
                'SELECT * FROM sanders_strategy_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_strategy_hub_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_strategy_hub_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_strategy_hub_records'
                ' WHERE plan_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(plan_count), 0) AS n'
                ' FROM sanders_strategy_hub_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_plans_submitted': no_refs,
            'plans_declared_total': refs_total,
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
                    raise SandersStrategyHubDenied(str(exc)) from exc
                self._record('SANDERS_STRATEGY_HUB_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
