"""Sanders Real Estate — the real estate management
platform.

The production build-out of the Sanders Real Estate
design (canonical catalog row #72, Band 2D), built
whole as its own platform service over the shared
RTSA foundation (RTSA Build Program Q63).

NAME — verified before building, per the name law:
the canonical catalog (row #72), the master grid
(deploy/oracle/sanders_master_grid.json id 18), the
Set B schema seed, and the pre-existing registry
record all name this platform **Sanders Real
Estate** — the queue-note reading matched the source
name exactly. The nickname "Ground" (the grid and
the Set B seed agree) is recorded here exactly as
found and is not adopted as the platform's name.
Set C carries no platform entry under this name
(verified by direct read of the tier catalog — no
section, purpose, or price).

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — "Real estate management"
(canonical catalog row #72; master grid id 18; the
Set B schema seed carries the platform at the
professional tier). The grid endpoint the records
carry (a Google Cloud host, :3018) is a file claim,
not a verified live check, and the grid file is
truncated at id 28; no Sanders Real Estate module
existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Real Estate
platform's own identity and store, carrying real
estate records:

- **Real estate records**: a subject reference (a
  property or real-estate operation under service,
  by reference), a declared set of property
  references, and a scope reference, carried as
  durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The property discipline**: outcomes are recorded
  only for APPROVED records and only against a
  presented evidence reference, with a closed
  outcome set (REAL_ESTATE_POSITION_CONFIRMED /
  MANAGEMENT_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no properties stands
  NO_PROPERTIES_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no properties were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never transactions**: determinations
  are records placed before human operators. The
  platform sells no property, leases no property,
  closes no transaction, and appraises nothing —
  sell_property, lease_property, close_transaction,
  appraise_property, and external_execution are
  refused by name under REAL_ESTATE_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  properties are carried by reference only; the
  platform holds no title documents, no tenant or
  buyer data, no valuation content, and no
  live-system state — references and workflow state
  only, as across the ecosystem.
- **NAICS**: two sources attest two different sets
  — the grid (531110, 531311, 531312, 531320,
  541110, 541191, 541511, 541512, 541611, 541690)
  and Set B (531110, 531312). No owner ruling
  assigns a set, and the canonical catalog row
  carries none — NO NAICS set is carried into the
  platform's built identity; both sets stand
  recorded as attested and unruled.
- **Separation**: the Sanders Real Estate platform
  is its own platform. It is not Sanders Senior
  Living (catalog #65), not Sanders Hospitality
  (catalog #79), and not Sanders Logistics (catalog
  #70) — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same
transaction, through the shared foundation's audit
adapter; the service refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 531390,
531210, 531311, 531312, 541611, 541618 — ADOPTED_EXISTING
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
    platform_id='sanders_real_estate',
    name='Sanders Real Estate',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('531390', '531210', '531311', '531312', '541611', '541618'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Real estate management'
DISCIPLINE = 'REAL_ESTATE_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_real_estate', 'approve_real_estate', 'record_outcome',
    'view_real_estate', 'view_design')
EXECUTION_OPERATIONS = ('sell_property', 'lease_property',
    'close_transaction', 'appraise_property',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('REAL_ESTATE_POSITION_CONFIRMED', 'MANAGEMENT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('REAL_ESTATE_POSITION_CONFIRMED', 'MANAGEMENT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersRealEstateDenied(Exception):
    """The requested Sanders Real Estate operation is not
    allowed."""


class SandersRealEstateForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersRealEstateService:
    """Sanders Real Estate: governed real-estate records under the real estate records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersRealEstateDenied(
                'Sanders Real Estate requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_real_estate', {
            'OPERATOR': {'SANDERS_REAL_ESTATE'},
            'AUDITOR': {'SANDERS_REAL_ESTATE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_real_estate_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    property_refs TEXT NOT NULL,
                    property_count INTEGER NOT NULL,
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
            raise SandersRealEstateForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersRealEstateForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersRealEstateForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_REAL_ESTATE',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersRealEstateForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersRealEstateDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #72', 'deploy/oracle/sanders_master_grid.json id 18', 'Set B schema seed row (read directly); Set C carries no entry under this name'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Real Estate is the real estate management platform: it carries governed real estate records over properties and real-estate operations and declared property sets presented by reference only. It sells no property, leases no property, closes no transaction, and appraises nothing: sell_property, lease_property, close_transaction, appraise_property, and external_execution are refused by name under REAL_ESTATE_RECORDS_ONLY, and determinations are records for human operators, never transactions. A record declared with no properties stands NO_PROPERTIES_SUBMITTED and no determination can be recorded on it. The nickname Ground (the grid and Set B agree) is recorded as found and is not adopted as the platform’s name. Set C carries no platform entry under this name. No designed hostname is recorded for this platform in any examined source. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no title documents, no tenant or buyer data, no valuation content. Sanders Real Estate is distinct from Sanders Senior Living (catalog #65), Sanders Hospitality (catalog #79), and Sanders Logistics (catalog #70) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the real estate records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersRealEstateDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Real Estate platform carries'
                ' real estate records only \u2014 it'
                ' sells no property, leases no property,'
                ' closes no transaction, and appraises'
                ' nothing itself'
                ' (REAL_ESTATE_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersRealEstateDenied(
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
        operations = json.loads(row['property_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'property_refs': operations,
            'property_count': row['property_count'],
            'property_state': ('NO_PROPERTIES_SUBMITTED'
                             if row['property_count'] == 0
                             else 'PROPERTIES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, property_refs,
                      scope_ref, *, region=None):
        """Record one real estate record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_PROPERTIES_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record sells no property, leases
        no property, closes no transaction, and
        appraises nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersRealEstateDenied(
                    f'A {label} is required')
        if not isinstance(property_refs, (list, tuple)):
            raise SandersRealEstateDenied(
                'property_refs must be a list of references')
        if len(property_refs) > MAX_REFS:
            raise SandersRealEstateDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in property_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersRealEstateDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-real-estate-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_REAL_ESTATE_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    property_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_real_estate_records'
                    ' (record_id, subject_ref, property_refs,'
                    ' property_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_real_estate_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_real_estate_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_real_estate_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersRealEstateDenied(
                'Real Estate record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested real estate record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersRealEstateDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_real_estate_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersRealEstateDenied(
                        'Real Estate record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersRealEstateDenied(
                        f"Cannot {action} a real estate record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_REAL_ESTATE_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_real_estate_records SET status = ?,'
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
                'SELECT * FROM sanders_real_estate_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (REAL_ESTATE_POSITION_CONFIRMED or MANAGEMENT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_PROPERTIES_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersRealEstateDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersRealEstateDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_real_estate_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersRealEstateDenied(
                        'Real Estate record not found')
                if row['status'] != 'APPROVED':
                    raise SandersRealEstateDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" real estate records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['property_count'] == 0:
                    raise SandersRealEstateDenied(
                        'NO_PROPERTIES_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_REAL_ESTATE_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_real_estate_records SET status = ?,'
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
                'SELECT * FROM sanders_real_estate_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_real_estate_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_real_estate_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_real_estate_records'
                ' WHERE property_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(property_count), 0) AS n'
                ' FROM sanders_real_estate_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_properties_submitted': no_refs,
            'properties_declared_total': refs_total,
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
                    raise SandersRealEstateDenied(str(exc)) from exc
                self._record('SANDERS_REAL_ESTATE_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
