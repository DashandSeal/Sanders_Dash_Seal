"""Sanders Omniconn — the oversight and AI-coordination
platform.

The production build-out of the Sanders Omniconn design
(canonical catalog row #59, Band 2D), built whole as its
own platform service over the shared RTSA foundation
(RTSA Build Program Q51).

NAME — verified before building, per the name law: the
canonical catalog (row #59), the master grid
(deploy/oracle/sanders_master_grid.json id 4), and the
owner's recorded ruling D-N1 name this platform **Sanders
Omniconn**. D-N1 rules expressly against the catalog's
own Omniconm recommendation: the canonical name is
Sanders Omniconn. Set A (the baseline registry), Set C
(the tier catalog), and the designed hostname
(omniconm.sandersglobal.com) carry the "Omniconm"
spelling — recorded here exactly as found and NOT adopted
as a name. The hostname stays as designed (the owner's
call under D-N1: name and address differ); it sits under
the unowned parent sandersglobal.com, so it is recorded
as the designed address and nothing is served there. The
grid nickname and Set C nickname "Big Brother" are
recorded as found and are not adopted as this platform's
identity.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Oversight, AI coordination" (canonical
catalog row #59; master grid id 4). Set C's purpose text
for this name — "Full-spectrum surveillance, DARPA/NSA
integration, nuclear command capability, Five Eyes
coordination" — is recorded here exactly as found, as a
design-record claim of that catalog; it is NOT the built
scope: no source the owner has ruled adopts it, and this
build constructs no surveillance, no external-agency
integration, and no command capability of any kind. The
grid endpoint the records carry (a Google Cloud host,
:3004) is a file claim, not a verified live check, and
the grid file is truncated at id 28; no Omniconn module
existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — Sanders Omniconn's own identity
and store, carrying oversight records over subjects and
observations presented by reference:

- **Oversight records**: a subject reference (the
  platform, system, or service under oversight, by
  reference), a declared set of observation references,
  and a scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then
  an outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The observation discipline**: outcomes are recorded
  only for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (OVERSIGHT_CONFIRMED / OVERSIGHT_FINDING_RECORDED /
  INCONCLUSIVE). A record declared with no observations
  stands NO_OBSERVATIONS_SUBMITTED in every view and in
  the status tallies, and both determinations are refused
  on it — no observations were presented to determine
  from; INCONCLUSIVE, which asserts nothing, records
  against evidence.
- **The oversight discipline, enforced**: this platform
  oversees and coordinates by record only. It directs
  nothing, commands nothing, overrides nothing, and
  surveils nothing: a coordination or oversight outcome
  is a record placed before the subject platform's human
  operators, never an instruction any system executes.
  Execution operations are refused by name with the
  signal OVERSIGHT_AND_COORDINATION_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  observations are carried by reference only; the
  platform holds no telemetry, no traffic, no live feeds,
  and no live-system state. (Its own record store is its
  own — it is not a window into any operational system.)
- **Separation**: Sanders Omniconn is its own platform.
  It is not Sanders Coordinator (catalog #97 — platform
  coordination, cross-platform integration, and workflow
  automation as a business platform; a different designed
  purpose), not the IT AI Manager (Q5), not the Police
  Men layer, and not any watchdog — identities are never
  merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
518210, 541511, 541513, 541519, 541618 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
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
    platform_id='sanders_omniconn',
    name='Sanders Omniconn',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541512', '518210', '541511', '541513', '541519', '541618'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Oversight, AI coordination'
DISCIPLINE = 'OVERSIGHT_AND_COORDINATION_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_oversight', 'approve_oversight', 'record_outcome',
    'view_oversight', 'view_design')
EXECUTION_OPERATIONS = ('direct_platform', 'command_platform',
    'override_platform', 'surveil_subject',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('OVERSIGHT_CONFIRMED', 'OVERSIGHT_FINDING_RECORDED',
            'INCONCLUSIVE')
DETERMINATIONS = ('OVERSIGHT_CONFIRMED', 'OVERSIGHT_FINDING_RECORDED')
MAX_REFS = 100


class SandersOmniconnDenied(Exception):
    """The requested Sanders Omniconn operation is not
    allowed."""


class SandersOmniconnForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersOmniconnService:
    """Sanders Omniconn: governed oversight records
    under the oversight-and-coordination records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersOmniconnDenied(
                'Sanders Omniconn requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_omniconn', {
            'OPERATOR': {'SANDERS_OMNICONN'},
            'AUDITOR': {'SANDERS_OMNICONN'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_omniconn_records (
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
            raise SandersOmniconnForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersOmniconnForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersOmniconnForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_OMNICONN',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersOmniconnForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersOmniconnDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #59',
                'deploy/oracle/sanders_master_grid.json id 4',
                'owner ruling D-N1 (canonical-catalog'
                ' decisions)',
                'Set A baseline registry and Set C tier'
                ' catalog (the "Omniconm" spelling and the'
                ' designed hostname, recorded as found)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Omniconn is the oversight and'
                    ' AI-coordination platform: it carries'
                    ' oversight records over subjects and'
                    ' observations presented by reference'
                    ' only. Oversight and coordination here'
                    ' are records, never acts \u2014 the'
                    ' platform directs nothing, commands'
                    ' nothing, overrides nothing, and'
                    ' surveils nothing live; an outcome is a'
                    ' record placed before the subject'
                    " platform's human operators, never an"
                    ' instruction any system executes.'
                    ' Execution operations are refused by'
                    ' name with the signal'
                    ' OVERSIGHT_AND_COORDINATION_RECORDS_ONLY.'
                    ' A record declared with no observations'
                    ' stands NO_OBSERVATIONS_SUBMITTED and'
                    ' no determination can be recorded on'
                    ' it. The name is Sanders Omniconn per'
                    ' owner ruling D-N1; the "Omniconm"'
                    ' spelling carried by Set A, Set C, and'
                    ' the designed hostname'
                    ' (omniconm.sandersglobal.com, under the'
                    ' unowned parent sandersglobal.com) is'
                    ' recorded as found and is not adopted'
                    ' as a name \u2014 the hostname stays as'
                    " designed, the owner's call, and"
                    ' nothing is served there. Set C\u2019s'
                    ' purpose text for this name is recorded'
                    ' in the module record as found and is'
                    ' not the built scope. Sanders Omniconn'
                    ' is distinct from Sanders Coordinator,'
                    ' from the IT AI Manager, from the'
                    ' Police Men layer, and from the'
                    ' watchdogs \u2014 identities are never'
                    ' merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the oversight
        discipline does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersOmniconnDenied(
                f'Operation {operation!r} is an execution'
                ' operation: Sanders Omniconn oversees and'
                ' coordinates by record only and holds no'
                ' authority to direct, command, override, or'
                ' surveil any platform'
                ' (OVERSIGHT_AND_COORDINATION_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersOmniconnDenied(
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
        """Record one global-oversight record (operator only) over
        a subject and a declared set of observation
        references, presented by reference. The observation set may
        be empty — the record then stands NO_OBSERVATIONS_SUBMITTED,
        exactly as the observation discipline holds, and no
        determination can be recorded on it. Recording the
        record oversees nothing live and acts on nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersOmniconnDenied(
                    f'A {label} is required')
        if not isinstance(observation_refs, (list, tuple)):
            raise SandersOmniconnDenied(
                'observation_refs must be a list of references')
        if len(observation_refs) > MAX_REFS:
            raise SandersOmniconnDenied(
                f'At most {MAX_REFS} observation'
                ' references per record')
        observations = []
        for ref in observation_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersOmniconnDenied(
                    'Every observation reference must be a'
                    ' non-empty string')
            observations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-omniconn-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_OMNICONN_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    observation_count=len(observations))
                db.execute(
                    'INSERT INTO sanders_omniconn_records'
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
                'SELECT * FROM sanders_omniconn_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_omniconn_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_omniconn_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersOmniconnDenied(
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
            raise SandersOmniconnDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_omniconn_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersOmniconnDenied(
                        'Oversight record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersOmniconnDenied(
                        f"Cannot {action} an oversight record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_OMNICONN_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_omniconn_records SET status = ?,'
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
                'SELECT * FROM sanders_omniconn_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (OVERSIGHT_CONFIRMED or OVERSIGHT_FINDING_RECORDED) on a
        record declared with no observations is refused —
        NO_OBSERVATIONS_SUBMITTED: no observations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersOmniconnDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersOmniconnDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_omniconn_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersOmniconnDenied(
                        'Oversight record not found')
                if row['status'] != 'APPROVED':
                    raise SandersOmniconnDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" oversight records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['observation_count'] == 0:
                    raise SandersOmniconnDenied(
                        'NO_OBSERVATIONS_SUBMITTED: a record'
                        ' declared with no observations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_OMNICONN_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_omniconn_records SET status = ?,'
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
                'SELECT * FROM sanders_omniconn_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_omniconn_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_omniconn_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_omniconn_records'
                ' WHERE observation_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(observation_count), 0) AS n'
                ' FROM sanders_omniconn_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_observations_submitted': no_signals,
            'observations_declared_total': signals_total,
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
                    raise SandersOmniconnDenied(str(exc)) from exc
                self._record('SANDERS_OMNICONN_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
