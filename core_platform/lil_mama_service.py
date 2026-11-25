"""Lil Mama — the secondary watchdog platform, and a
public-facing business of the house.

The production build-out of the Lil Mama design
(canonical catalog row #55, Band 2D), built whole as her
own platform service over the shared RTSA foundation
(RTSA Build Program Q49).

NAME — verified before building, per the name law: the
canonical catalog (row #55), the master grid
(deploy/oracle/sanders_master_grid.json id 2), and the
Police Men status record (rtsa_police_men/status.json)
name this platform **Lil Mama**, watchdog WD-01. The
owner's recorded rulings (canonical-catalog decisions,
Group 3) hold the watchdog roster as Lil Mama, Baby Girl,
Alph, Bata. PERSONA CONFLICTS, flagged and not adopted:
the grid and Set B give Lil Mama the persona "Beta", and
Set C gives her the nickname "Twin Guardian" — decision
D-N15 records the persona conflict as unruled, and the
owner's roster rules there is NO "Beta" watchdog; neither
persona is carried anywhere in this build, on either
surface. The CareHiveOS inventory the owner supplied
2026-11-24 calls her a "Beta Watchdog" — that designation
conflicts with his ruled roster; his rulings govern, and
nothing here is harmonized to that document.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Secondary watchdog / human oversight"
(canonical catalog row #55; master grid id 2) — the
Police Men status record naming watchdog Lil Mama
(WD-01) as an enforcer, and the owner's Group 3 ruling
that the watchdogs hold DUAL ROLES: they are
public-facing businesses too, and everything has a
business model. The grid endpoint the records carry (a
Google Cloud host, :3002) is a file claim, not a verified
live check, and the grid file is truncated at id 28; no
Lil Mama module existed in any examined source. What the
sources do NOT design: any price that may be wired (Set B
carries a $2,400,000 figure and Set C a $455,000,000/yr
figure for her name — both are blocker figures under the
owner's 2026-11-24 ruling, flagged in the SPEC entry and
the registry, none wired), any teaching function, and any
business offering beyond the dual-role ruling itself —
her public face therefore presents her designed
human-oversight role in business terms and invents no
product, price, or promise beyond it.

REBUILT (everything executable in this module): the
governed platform below — Lil Mama's own identity and
store, carrying human-oversight records over subjects and
observations presented by reference:

- **Oversight records**: a subject reference (the work,
  service, or activity under human oversight, by
  reference), a declared set of observation references,
  and a scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then
  an outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The observation discipline**: outcomes are recorded
  only for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (ESCALATION_RECORDED / NO_ESCALATION_REQUIRED /
  INCONCLUSIVE). A record declared with no observations
  stands NO_OBSERVATIONS_SUBMITTED in every view and in
  the status tallies, and both determinations are refused
  on it — no observations were presented to determine
  from; INCONCLUSIVE, which asserts nothing, records
  against evidence.
- **The watchdog law, enforced**: a watchdog detects and
  escalates only. She holds no corporate decision
  authority, takes no enforcement action against any
  person, company, or platform, overrides no human
  decision, and decides nothing: an ESCALATION_RECORDED
  outcome is a record placed before a human
  decision-maker, never an act. Execution operations are
  refused by name with the watchdog signal,
  WATCHDOG_DETECT_AND_ESCALATE_ONLY. She watches no live
  system — oversight enters the ecosystem only as records
  presented to her by reference.
- **Dual role**: her public business face is served at
  /lil-mama in the flagship application — a Royal
  Enterprise surface carrying her business identity only.
  No watchdog internals appear on it: no WD number, no
  persona, no containment or escalation mechanics, no
  security detail of any kind.
- **Reference-only discipline**: subjects and observations
  are carried by reference only; the platform holds no
  case content, no personal data, and no live-system
  state. (Her own record store is her own — it is not a
  window into any operational system.)
- **Separation**: Lil Mama is her own platform. She is
  not Baby Girl, not Sanders Sentinel, not Alph, not
  Bata, not the Police Men layer, and not any other
  platform — the watchdogs are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.
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
    platform_id='lil_mama',
    name='Lil Mama',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Secondary watchdog / human oversight'
WATCHDOG_DISCIPLINE = 'DETECT_AND_ESCALATE_ONLY'
RECORD_OPERATIONS = (
    'record_oversight', 'approve_oversight', 'record_outcome',
    'view_oversight', 'view_design',
)
EXECUTION_OPERATIONS = (
    'take_enforcement_action', 'override_operator_decision',
    'suspend_subject', 'discipline_subject', 'external_execution',
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
MAX_OBSERVATION_REFS = 100


class LilMamaDenied(Exception):
    """The requested Lil Mama operation is not allowed."""


class LilMamaForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class LilMamaService:
    """Lil Mama: governed human-oversight records under the
    watchdog detect-and-escalate discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise LilMamaDenied(
                'Lil Mama requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'lil_mama', {
            'OPERATOR': {'OVERSIGHT'},
            'AUDITOR': {'OVERSIGHT'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS lil_mama_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    observation_refs TEXT NOT NULL,
                    observation_count INTEGER NOT NULL,
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
            raise LilMamaForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise LilMamaForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise LilMamaForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'OVERSIGHT',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise LilMamaForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise LilMamaDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #55',
                'deploy/oracle/sanders_master_grid.json id 2',
                'rtsa_police_men/status.json (watchdog WD-01'
                ' enforcer record)',
                'owner rulings: Group 3 watchdog roster and'
                ' the dual-role ruling (canonical-catalog'
                ' decisions)',
            ],
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'dual_role': 'Public-facing business (owner-ruled);'
                         ' business face served at /lil-mama',
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Lil Mama is the secondary watchdog: she'
                    ' carries human-oversight records over'
                    ' subjects and observations presented by'
                    ' reference only. A watchdog detects and'
                    ' escalates only — she holds no corporate'
                    ' decision authority, takes no enforcement'
                    ' action, overrides no human decision, and'
                    ' decides nothing; an escalation is a record'
                    ' placed before a human decision-maker.'
                    ' Execution operations are refused by name'
                    ' with the watchdog signal'
                    ' WATCHDOG_DETECT_AND_ESCALATE_ONLY. A record'
                    ' declared with no observations stands'
                    ' NO_OBSERVATIONS_SUBMITTED and no'
                    ' determination can be recorded on it. The'
                    ' grid/Set B persona "Beta" and the Set C'
                    ' nickname "Twin Guardian" are recorded as'
                    ' found and are not adopted: the persona'
                    ' conflict is unruled (D-N15) and the'
                    ' owner\u2019s roster holds no "Beta"'
                    ' watchdog. Lil Mama is distinct from Baby'
                    ' Girl, from Sanders Sentinel, from Alph,'
                    ' from Bata, and from the Police Men layer'
                    ' — identities are never merged.',
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
            raise LilMamaDenied(
                f'Operation {operation!r} is an execution'
                ' operation: a watchdog detects and escalates'
                ' only and holds no authority to act'
                ' (WATCHDOG_DETECT_AND_ESCALATE_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise LilMamaDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'designed_role': DESIGNED_ROLE,
        }

    # -- records ------------------------------------------------------

    @staticmethod
    def _record_view(row):
        observations = json.loads(row['observation_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'observation_refs': observations,
            'observation_count': row['observation_count'],
            'observation_state': ('NO_OBSERVATIONS_SUBMITTED'
                                  if row['observation_count'] == 0
                                  else 'OBSERVATIONS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, observation_refs,
                      scope_ref, *, region=None):
        """Record one human-oversight record (operator only)
        over a subject and a declared set of observation
        references, presented by reference. The observation
        set may be empty — the record then stands
        NO_OBSERVATIONS_SUBMITTED, exactly as the observation
        discipline holds, and no determination can be recorded
        on it. Recording the record watches nothing live and
        acts on nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise LilMamaDenied(
                    f'A {label} is required')
        if not isinstance(observation_refs, (list, tuple)):
            raise LilMamaDenied(
                'observation_refs must be a list of references')
        if len(observation_refs) > MAX_OBSERVATION_REFS:
            raise LilMamaDenied(
                f'At most {MAX_OBSERVATION_REFS} observation'
                ' references per record')
        observations = []
        for ref in observation_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise LilMamaDenied(
                    'Every observation reference must be a'
                    ' non-empty string')
            observations.append(ref.strip())
        now = self._now()
        record_id = f'lil-mama-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LIL_MAMA_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    observation_count=len(observations))
                db.execute(
                    'INSERT INTO lil_mama_records'
                    ' (record_id, subject_ref, observation_refs,'
                    ' observation_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(observations), len(observations),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lil_mama_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM lil_mama_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM lil_mama_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise LilMamaDenied(
                'Oversight record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested oversight record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise LilMamaDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lil_mama_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise LilMamaDenied(
                        'Oversight record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise LilMamaDenied(
                        f"Cannot {action} an oversight record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'LIL_MAMA_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE lil_mama_records SET status = ?,'
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
                'SELECT * FROM lil_mama_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (ESCALATION_RECORDED or NO_ESCALATION_REQUIRED) on a
        record declared with no observations is refused —
        NO_OBSERVATIONS_SUBMITTED: no observations were
        presented to determine from. An escalation outcome is
        a record for a human decision; it dispatches and
        enforces nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise LilMamaDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise LilMamaDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lil_mama_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise LilMamaDenied(
                        'Oversight record not found')
                if row['status'] != 'APPROVED':
                    raise LilMamaDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" oversight records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['observation_count'] == 0:
                    raise LilMamaDenied(
                        'NO_OBSERVATIONS_SUBMITTED: a record'
                        ' declared with no observations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'LIL_MAMA_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE lil_mama_records SET status = ?,'
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
                'SELECT * FROM lil_mama_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM lil_mama_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM lil_mama_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_observations = db.execute(
                'SELECT COUNT(*) AS n FROM lil_mama_records'
                ' WHERE observation_count = 0').fetchone()['n']
            observations_total = db.execute(
                'SELECT COALESCE(SUM(observation_count), 0) AS n'
                ' FROM lil_mama_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_observations_submitted': no_observations,
            'observations_declared_total': observations_total,
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
                    raise LilMamaDenied(str(exc)) from exc
                self._record('LIL_MAMA_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
