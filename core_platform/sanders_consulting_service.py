"""Sanders Consulting — the business consulting &
strategy platform.

The production build-out of the Sanders Consulting
design (canonical catalog row #77, Band 2D), built
whole as its own platform service over the shared
RTSA foundation (RTSA Build Program Q68).

NAME — verified before building, per the name law:
the canonical catalog (row #77), the master grid
(deploy/oracle/sanders_master_grid.json id 23), the
Set B schema seed, and the pre-existing registry
record all name this platform **Sanders
Consulting** — the queue-note reading matched the
source name exactly. The nickname "Compass" (the
grid and the Set B seed agree) is recorded here
exactly as found and is not adopted as the
platform's name. Set C carries no platform entry
under this name (verified by direct read — the slug
appears only in the Set C repo's directory
scaffolding; no section, purpose, or price).

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — "Business consulting & strategy"
(canonical catalog row #77; master grid id 23; the
Set B schema seed carries the platform at the
professional tier). The grid endpoint the records
carry (a Google Cloud host, :3023) is a file claim,
not a verified live check, and the grid file is
truncated at id 28; no Sanders Consulting module
existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Consulting
platform's own identity and store, carrying
consulting records:

- **Consulting records**: a subject reference (a
  business, organization, or program under
  engagement, by reference), a declared set of
  engagement references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by
  a human operator's recorded decision, then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The engagement discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set (CONSULTING_POSITION_CONFIRMED
  / ENGAGEMENT_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no engagements stands
  NO_ENGAGEMENTS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no engagements were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never advice**: determinations are
  records placed before human operators. The
  platform advises no client, delivers no
  consulting, implements no strategy, and bills no
  client — advise_client, deliver_consulting,
  implement_strategy, bill_client, and
  external_execution are refused by name under
  CONSULTING_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  engagements are carried by reference only; the
  platform holds no client data, no engagement
  content, no billing state, and no live-system
  state — references and workflow state only, as
  across the ecosystem.
- **NAICS**: two sources attest two different sets
  — the grid (541611, 541612, 541613, 541614,
  541618, 541690, 541990) and Set B (541611). No
  owner ruling assigns a set, and the canonical
  catalog row carries none — NO NAICS set is
  carried into the platform's built identity; both
  sets stand recorded as attested and unruled.
- **Separation**: the Sanders Consulting platform
  is its own platform. It is not Sanders Strategy
  Hub (catalog #94), not Sanders Strategy Intel
  (catalog #117), and not Sanders Analytics (catalog
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
541612, 541613, 541614, 541618, 541690 — ADOPTED_EXISTING
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
    platform_id='sanders_consulting',
    name='Sanders Consulting',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541611', '541612', '541613', '541614', '541618', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Business consulting & strategy'
DISCIPLINE = 'CONSULTING_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_consulting', 'approve_consulting', 'record_outcome',
    'view_consulting', 'view_design')
EXECUTION_OPERATIONS = ('advise_client', 'deliver_consulting',
    'implement_strategy', 'bill_client',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('CONSULTING_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('CONSULTING_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersConsultingDenied(Exception):
    """The requested Sanders Consulting operation is not
    allowed."""


class SandersConsultingForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersConsultingService:
    """Sanders Consulting: governed consulting records under the consulting records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersConsultingDenied(
                'Sanders Consulting requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_consulting', {
            'OPERATOR': {'SANDERS_CONSULTING'},
            'AUDITOR': {'SANDERS_CONSULTING'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_consulting_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    engagement_refs TEXT NOT NULL,
                    engagement_count INTEGER NOT NULL,
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
            raise SandersConsultingForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersConsultingForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersConsultingForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_CONSULTING',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersConsultingForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersConsultingDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #77', 'deploy/oracle/sanders_master_grid.json id 23', 'Set B schema seed row (read directly); Set C carries no entry under this name'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Consulting is the business consulting & strategy platform: it carries governed consulting records over businesses, organizations, and programs and declared engagement sets presented by reference only. It advises no client, delivers no consulting, implements no strategy, and bills no client: advise_client, deliver_consulting, implement_strategy, bill_client, and external_execution are refused by name under CONSULTING_RECORDS_ONLY, and determinations are records for human operators, never advice. A record declared with no engagements stands NO_ENGAGEMENTS_SUBMITTED and no determination can be recorded on it. The nickname Compass (the grid and Set B agree) is recorded as found and is not adopted as the platform’s name. Set C carries no platform entry under this name. No designed hostname is recorded for this platform in any examined source. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no client data, no engagement content, no billing state. Sanders Consulting is distinct from Sanders Strategy Hub (catalog #94), Sanders Strategy Intel (catalog #117), and Sanders Analytics (catalog #118) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the consulting records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersConsultingDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Consulting platform carries'
                ' consulting records only \u2014 it'
                ' advises no client, delivers no'
                ' consulting, implements no strategy,'
                ' and bills no client itself'
                ' (CONSULTING_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersConsultingDenied(
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
        operations = json.loads(row['engagement_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'engagement_refs': operations,
            'engagement_count': row['engagement_count'],
            'engagement_state': ('NO_ENGAGEMENTS_SUBMITTED'
                             if row['engagement_count'] == 0
                             else 'ENGAGEMENTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, engagement_refs,
                      scope_ref, *, region=None):
        """Record one consulting record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_ENGAGEMENTS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record advises no client,
        delivers no consulting, and implements
        no strategy."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersConsultingDenied(
                    f'A {label} is required')
        if not isinstance(engagement_refs, (list, tuple)):
            raise SandersConsultingDenied(
                'engagement_refs must be a list of references')
        if len(engagement_refs) > MAX_REFS:
            raise SandersConsultingDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in engagement_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersConsultingDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-consulting-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_CONSULTING_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    engagement_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_consulting_records'
                    ' (record_id, subject_ref, engagement_refs,'
                    ' engagement_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_consulting_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_consulting_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_consulting_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersConsultingDenied(
                'Consulting record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested consulting record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersConsultingDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_consulting_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersConsultingDenied(
                        'Consulting record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersConsultingDenied(
                        f"Cannot {action} a consulting record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_CONSULTING_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_consulting_records SET status = ?,'
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
                'SELECT * FROM sanders_consulting_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (CONSULTING_POSITION_CONFIRMED or ENGAGEMENT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_ENGAGEMENTS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersConsultingDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersConsultingDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_consulting_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersConsultingDenied(
                        'Consulting record not found')
                if row['status'] != 'APPROVED':
                    raise SandersConsultingDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" consulting records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['engagement_count'] == 0:
                    raise SandersConsultingDenied(
                        'NO_ENGAGEMENTS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_CONSULTING_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_consulting_records SET status = ?,'
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
                'SELECT * FROM sanders_consulting_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_consulting_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_consulting_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_consulting_records'
                ' WHERE engagement_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(engagement_count), 0) AS n'
                ' FROM sanders_consulting_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_engagements_submitted': no_refs,
            'engagements_declared_total': refs_total,
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
                    raise SandersConsultingDenied(str(exc)) from exc
                self._record('SANDERS_CONSULTING_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
