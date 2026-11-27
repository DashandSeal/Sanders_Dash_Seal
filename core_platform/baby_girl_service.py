"""Baby Girl — the redundant-monitoring watchdog platform,
and a public-facing business of the house.

The production build-out of the Baby Girl design
(canonical catalog row #56, Band 2D), built whole as her
own platform service over the shared RTSA foundation
(RTSA Build Program Q50).

NAME — verified before building, per the name law: the
canonical catalog (row #56), the master grid
(deploy/oracle/sanders_master_grid.json id 3), and the
Police Men status record (rtsa_police_men/status.json)
name this platform **Baby Girl**, watchdog WD-02. The
owner's recorded rulings (canonical-catalog decisions,
Group 3) hold the watchdog roster as Lil Mama, Baby Girl,
Alph, Bata. PERSONA CONFLICTS, flagged and not adopted:
the grid and Set B give Baby Girl the persona "Gamma",
and Set C gives her the nickname "Twin Guardian" —
decision D-N15 records the persona conflict as unruled;
neither persona is carried anywhere in this build, on
either surface. The CareHiveOS inventory the owner
supplied 2026-11-24 calls her a "Gamma Watchdog" — that
designation sits inside the same unruled persona
conflict; his rulings govern, and nothing here is
harmonized to that document.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Redundant monitoring AI" (canonical catalog
row #56; master grid id 3) — and the Police Men status
record naming Baby Girl (WD-02) as the forensic
chain-of-custody custodian of the security audit log. The
grid endpoint the records carry (a Google Cloud host,
:3003) is a file claim, not a verified live check, and
the grid file is truncated at id 28; no Baby Girl module
existed in any examined source. What the sources do NOT
design: any price that may be wired (Set B carries a
$2,400,000 figure and Set C a $455,000,000/yr figure for
her name — both are blocker figures under the owner's
2026-11-24 ruling, flagged in the SPEC entry and the
registry, none wired), any teaching function, any custody
mechanics beyond the custodian designation itself, and
any business offering beyond the dual-role ruling — her
public face therefore presents her designed
redundant-monitoring role in business terms and invents
no product, price, or promise beyond it.

REBUILT (everything executable in this module): the
governed platform below — Baby Girl's own identity and
store, carrying two record families:

- **Monitoring records**: a subject reference (the work,
  service, or activity under redundant monitoring, by
  reference), a declared set of monitoring references,
  and a scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then
  an outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The monitoring discipline**: outcomes are recorded
  only for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (ESCALATION_RECORDED / NO_ESCALATION_REQUIRED /
  INCONCLUSIVE). A record declared with no monitoring
  references stands NO_MONITORING_SUBMITTED in every view
  and in the status tallies, and both determinations are
  refused on it — nothing was presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Custody records**: her designed custodian role,
  carried as append-only records over an evidence
  reference, a closed custody-event set (INTAKE_RECORDED,
  TRANSFER_RECORDED, ACCESS_RECORDED, RELEASE_RECORDED,
  RETURN_RECORDED, DISPOSITION_RECORDED), and a scope
  reference. A custody record records that an evidence
  reference changed hands or state; it holds NO evidence
  content, and this service offers no operation that
  alters, destroys, or releases evidence — those
  operations are refused by name.
- **The watchdog law, enforced**: a watchdog detects and
  escalates only. She holds no corporate decision
  authority, takes no enforcement action against any
  person, company, or platform, and decides nothing: an
  ESCALATION_RECORDED outcome is a record placed before a
  human decision-maker, never an act. Execution operations
  are refused by name with the watchdog signal,
  WATCHDOG_DETECT_AND_ESCALATE_ONLY. She monitors no live
  system — monitoring enters the ecosystem only as records
  presented to her by reference.
- **Dual role**: her public business face is served at
  /baby-girl in the flagship application — a Royal
  Enterprise surface carrying her business identity only.
  No watchdog internals appear on it: no WD number, no
  persona, and no custody, monitoring-mechanics, or
  security detail of any kind.
- **Reference-only discipline**: subjects, monitoring
  inputs, and evidence are carried by reference only; the
  platform holds no case content, no evidence content, no
  personal data, and no live-system state. (Her own record
  store is her own — it is not a window into any
  operational system.)
- **Separation**: Baby Girl is her own platform. She is
  not Lil Mama, not Sanders Sentinel, not Alph, not Bata,
  not the Police Men layer, and not any other platform —
  the watchdogs are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541715,
541618, 621111, 621999, 541690, 561621 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward. Disclosure of record: the older ruled record
carried the watchdogs with no codes; this six is
reconciled under the founder's 2026-11-26 directive that
every platform carries a group of six, from the attested
watchdog set.
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
    platform_id='baby_girl',
    name='Baby Girl',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541715', '541618', '621111', '621999', '541690', '561621'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Redundant monitoring AI'
WATCHDOG_DISCIPLINE = 'DETECT_AND_ESCALATE_ONLY'
RECORD_OPERATIONS = (
    'record_monitoring', 'approve_monitoring', 'record_outcome',
    'view_monitoring', 'view_design',
)
CUSTODY_OPERATIONS = ('record_custody', 'view_custody')
EXECUTION_OPERATIONS = (
    'alter_evidence', 'destroy_evidence',
    'release_evidence_outside_record',
    'take_enforcement_action', 'suspend_subject',
    'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('ESCALATION_RECORDED', 'NO_ESCALATION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('ESCALATION_RECORDED', 'NO_ESCALATION_REQUIRED')
CUSTODY_EVENTS = ('INTAKE_RECORDED', 'TRANSFER_RECORDED',
                  'ACCESS_RECORDED', 'RELEASE_RECORDED',
                  'RETURN_RECORDED', 'DISPOSITION_RECORDED')
MAX_MONITORING_REFS = 100


class BabyGirlDenied(Exception):
    """The requested Baby Girl operation is not allowed."""


class BabyGirlForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class BabyGirlService:
    """Baby Girl: governed redundant-monitoring records and
    append-only custody records under the watchdog
    detect-and-escalate discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise BabyGirlDenied(
                'Baby Girl requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'baby_girl', {
            'OPERATOR': {'MONITORING'},
            'AUDITOR': {'MONITORING'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS baby_girl_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    monitoring_refs TEXT NOT NULL,
                    monitoring_count INTEGER NOT NULL,
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
                CREATE TABLE IF NOT EXISTS baby_girl_custody (
                    custody_id TEXT PRIMARY KEY,
                    evidence_ref TEXT NOT NULL,
                    custody_event TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
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
            raise BabyGirlForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise BabyGirlForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise BabyGirlForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'MONITORING',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise BabyGirlForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise BabyGirlDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #56',
                'deploy/oracle/sanders_master_grid.json id 3',
                'rtsa_police_men/status.json (watchdog WD-02;'
                ' security audit log custodian record)',
                'owner rulings: Group 3 watchdog roster and'
                ' the dual-role ruling (canonical-catalog'
                ' decisions)',
            ],
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'dual_role': 'Public-facing business (owner-ruled);'
                         ' business face served at /baby-girl',
            'record_operations': list(RECORD_OPERATIONS),
            'custody_operations': list(CUSTODY_OPERATIONS),
            'custody_events': list(CUSTODY_EVENTS),
            'note': 'Baby Girl is the redundant-monitoring'
                    ' watchdog: she carries monitoring records'
                    ' over subjects and monitoring inputs'
                    ' presented by reference only, and append-only'
                    ' custody records over evidence references'
                    ' under her designed custodian role. A'
                    ' watchdog detects and escalates only — she'
                    ' holds no corporate decision authority,'
                    ' takes no enforcement action, and decides'
                    ' nothing; an escalation is a record placed'
                    ' before a human decision-maker. Execution'
                    ' operations — including altering,'
                    ' destroying, or releasing evidence outside'
                    ' the record — are refused by name with the'
                    ' watchdog signal'
                    ' WATCHDOG_DETECT_AND_ESCALATE_ONLY. A record'
                    ' declared with no monitoring references'
                    ' stands NO_MONITORING_SUBMITTED and no'
                    ' determination can be recorded on it. The'
                    ' grid/Set B persona "Gamma" and the Set C'
                    ' nickname "Twin Guardian" are recorded as'
                    ' found and are not adopted: the persona'
                    ' conflict is unruled (D-N15). Baby Girl is'
                    ' distinct from Lil Mama, from Sanders'
                    ' Sentinel, from Alph, from Bata, and from'
                    ' the Police Men layer — identities are'
                    ' never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the watchdog discipline
        does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise BabyGirlDenied(
                f'Operation {operation!r} is an execution'
                ' operation: a watchdog detects and escalates'
                ' only and holds no authority to act'
                ' (WATCHDOG_DETECT_AND_ESCALATE_ONLY)')
        if operation in RECORD_OPERATIONS:
            permitted = 'RECORD_ONLY'
        elif operation in CUSTODY_OPERATIONS:
            permitted = 'CUSTODY_RECORD_ONLY'
        else:
            raise BabyGirlDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': permitted,
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'designed_role': DESIGNED_ROLE,
        }

    # -- monitoring records ---------------------------------------------

    @staticmethod
    def _record_view(row):
        monitoring = json.loads(row['monitoring_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'monitoring_refs': monitoring,
            'monitoring_count': row['monitoring_count'],
            'monitoring_state': ('NO_MONITORING_SUBMITTED'
                                 if row['monitoring_count'] == 0
                                 else 'MONITORING_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, monitoring_refs,
                      scope_ref, *, region=None):
        """Record one redundant-monitoring record (operator
        only) over a subject and a declared set of monitoring
        references, presented by reference. The monitoring set
        may be empty — the record then stands
        NO_MONITORING_SUBMITTED, exactly as the monitoring
        discipline holds, and no determination can be recorded
        on it. Recording the record monitors nothing live and
        acts on nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise BabyGirlDenied(
                    f'A {label} is required')
        if not isinstance(monitoring_refs, (list, tuple)):
            raise BabyGirlDenied(
                'monitoring_refs must be a list of references')
        if len(monitoring_refs) > MAX_MONITORING_REFS:
            raise BabyGirlDenied(
                f'At most {MAX_MONITORING_REFS} monitoring'
                ' references per record')
        monitoring = []
        for ref in monitoring_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise BabyGirlDenied(
                    'Every monitoring reference must be a'
                    ' non-empty string')
            monitoring.append(ref.strip())
        now = self._now()
        record_id = f'baby-girl-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'BABY_GIRL_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    monitoring_count=len(monitoring))
                db.execute(
                    'INSERT INTO baby_girl_records'
                    ' (record_id, subject_ref, monitoring_refs,'
                    ' monitoring_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(monitoring), len(monitoring),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM baby_girl_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM baby_girl_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM baby_girl_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise BabyGirlDenied(
                'Monitoring record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested monitoring record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise BabyGirlDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM baby_girl_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise BabyGirlDenied(
                        'Monitoring record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise BabyGirlDenied(
                        f"Cannot {action} a monitoring record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'BABY_GIRL_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE baby_girl_records SET status = ?,'
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
                'SELECT * FROM baby_girl_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (ESCALATION_RECORDED or NO_ESCALATION_REQUIRED) on a
        record declared with no monitoring references is
        refused — NO_MONITORING_SUBMITTED: nothing was
        presented to determine from. An escalation outcome is
        a record for a human decision; it dispatches and
        enforces nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise BabyGirlDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise BabyGirlDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM baby_girl_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise BabyGirlDenied(
                        'Monitoring record not found')
                if row['status'] != 'APPROVED':
                    raise BabyGirlDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" monitoring records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['monitoring_count'] == 0:
                    raise BabyGirlDenied(
                        'NO_MONITORING_SUBMITTED: a record'
                        ' declared with no monitoring references'
                        f' cannot be determined {outcome}')
                receipt_id = self._record(
                    'BABY_GIRL_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE baby_girl_records SET status = ?,'
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
                'SELECT * FROM baby_girl_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- custody records --------------------------------------------------

    @staticmethod
    def _custody_view(row):
        return {
            'custody_id': row['custody_id'],
            'evidence_ref': row['evidence_ref'],
            'custody_event': row['custody_event'],
            'scope_ref': row['scope_ref'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def record_custody(self, actor, evidence_ref, custody_event,
                       scope_ref, *, region=None):
        """Record one custody event (operator only) over an
        evidence reference, from the closed custody-event set.
        The record states that the referenced evidence changed
        hands or state; it carries no evidence content, and no
        operation in this service alters, destroys, or releases
        evidence. Custody records are append-only."""
        self._geo(region)
        self._require_operator(actor)
        if custody_event not in CUSTODY_EVENTS:
            raise BabyGirlDenied(
                f'Unknown custody event: {custody_event!r}')
        for label, value in (('evidence_ref', evidence_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise BabyGirlDenied(
                    f'An {label} is required')
        now = self._now()
        custody_id = f'baby-girl-custody-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'BABY_GIRL_CUSTODY_RECORDED',
                    actor=actor, custody_id=custody_id,
                    evidence_ref=evidence_ref.strip(),
                    custody_event=custody_event)
                db.execute(
                    'INSERT INTO baby_girl_custody'
                    ' (custody_id, evidence_ref, custody_event,'
                    ' scope_ref, recorded_by, recorded_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (custody_id, evidence_ref.strip(),
                     custody_event, scope_ref.strip(), actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM baby_girl_custody'
                ' WHERE custody_id = ?',
                (custody_id,)).fetchone()
        return self._custody_view(row)

    def custody_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'custody', 'custody view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM baby_girl_custody'
                ' ORDER BY recorded_at',
            ).fetchall()
        return [self._custody_view(row) for row in rows]

    def custody_view(self, actor, role, custody_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, custody_id, 'custody view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM baby_girl_custody'
                ' WHERE custody_id = ?',
                (custody_id,)).fetchone()
        if row is None:
            raise BabyGirlDenied(
                'Custody record not found')
        return self._custody_view(row)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM baby_girl_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM baby_girl_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_monitoring = db.execute(
                'SELECT COUNT(*) AS n FROM baby_girl_records'
                ' WHERE monitoring_count = 0').fetchone()['n']
            monitoring_total = db.execute(
                'SELECT COALESCE(SUM(monitoring_count), 0) AS n'
                ' FROM baby_girl_records').fetchone()['n']
            custody_total = db.execute(
                'SELECT COUNT(*) AS n FROM baby_girl_custody'
            ).fetchone()['n']
            by_event = {e: 0 for e in CUSTODY_EVENTS}
            for row in db.execute(
                    'SELECT custody_event, COUNT(*) AS n'
                    ' FROM baby_girl_custody'
                    ' GROUP BY custody_event'):
                by_event[row['custody_event']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_monitoring_submitted': no_monitoring,
            'monitoring_declared_total': monitoring_total,
            'custody_total': custody_total,
            'custody_by_event': by_event,
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
                    raise BabyGirlDenied(str(exc)) from exc
                self._record('BABY_GIRL_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
