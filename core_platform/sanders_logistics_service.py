"""Sanders Logistics — the supply chain
management platform.

The production build-out of the Sanders Logistics
design (canonical catalog row #70, Band 2D), built
whole as its own platform service over the shared RTSA
foundation (RTSA Build Program Q61).

NAME — verified before building, per the name law:
the canonical catalog (row #70), the master grid
(deploy/oracle/sanders_master_grid.json id 16), the
Set B schema seed, the Set C tier catalog, and the
pre-existing registry record all name this platform
**Sanders Logistics** — the queue prose name
matched the source name exactly. Two nicknames
conflict as found — "Flow" (the grid and the Set B
seed agree) and "Transport" (Set C) — and Set C
gives "Flow" to Sanders Supply Chain (catalog row
#120); both nicknames are recorded here exactly as
found and neither is adopted as the platform's name.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Supply chain management" (canonical
catalog row #70; master grid id 16); Set C's purpose
text — "Global logistics, Amazon/UPS replacement,
supply chain operations, disaster coordination" (the
Set C tier catalog); Set C's designed hostname
logistics.sandersglobal.com, under the unowned parent
sandersglobal.com — recorded as the designed
address, and nothing is served there. The grid
endpoint the records carry (a Google Cloud host,
:3016) is a file claim, not a verified live check, and
the grid file is truncated at id 28; no Sanders
Logistics module existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Logistics
platform's own identity and store, carrying logistics
records:

- **Logistics records**: a subject reference (a supply
  chain or lane under coordination, by reference), a
  declared set of shipment references, and a scope
  reference, carried as durable, receipted records with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by
  a human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The shipment discipline**: outcomes are recorded
  only for APPROVED records and only against a
  presented evidence reference, with a closed outcome
  set (CHAIN_CONFIRMED / COORDINATION_REQUIRED /
  INCONCLUSIVE). A record declared with no shipments
  stands NO_SHIPMENTS_SUBMITTED in every view and in
  the status tallies, and both determinations are
  refused on it — no shipments were presented to
  determine from; INCONCLUSIVE, which asserts nothing,
  records against evidence.
- **Records, never movement**: determinations are
  records placed before human operators. The platform
  ships nothing, dispatches no fleet, routes no
  shipment, and procures nothing — ship_goods,
  dispatch_fleet, route_shipment, procure_goods, and
  external_execution are refused by name under
  LOGISTICS_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  shipments are carried by reference only; the platform
  holds no cargo content, no customer data, no live
  carrier state — references and workflow state
  only, as across the ecosystem.
- **NAICS**: two sources attest two different sets
  — the grid (493110, 488510, 488991, 541511,
  541512, 541611, 541614, 541690) and Set B (493110,
  488510). No owner ruling assigns a set, and the
  canonical catalog row carries none — NO NAICS
  set is carried into the platform's built identity;
  both sets stand recorded as attested and unruled.
- **Separation**: the Sanders Logistics platform is
  its own platform. It is not Sanders Supply Chain
  (catalog #120) and not Sanders Transportation
  (catalog #74) — identities are never merged.

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
    platform_id='sanders_logistics',
    name='Sanders Logistics',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Supply chain management'
DISCIPLINE = 'LOGISTICS_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_logistics', 'approve_logistics', 'record_outcome',
    'view_logistics', 'view_design')
EXECUTION_OPERATIONS = ('ship_goods', 'dispatch_fleet',
    'route_shipment', 'procure_goods',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('CHAIN_CONFIRMED', 'COORDINATION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('CHAIN_CONFIRMED', 'COORDINATION_REQUIRED')
MAX_REFS = 100


class SandersLogisticsDenied(Exception):
    """The requested Sanders Logistics operation is not
    allowed."""


class SandersLogisticsForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersLogisticsService:
    """Sanders Logistics: governed supply-chain and logistics records under the logistics records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersLogisticsDenied(
                'Sanders Logistics requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_logistics', {
            'OPERATOR': {'SANDERS_LOGISTICS'},
            'AUDITOR': {'SANDERS_LOGISTICS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_logistics_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    shipment_refs TEXT NOT NULL,
                    shipment_count INTEGER NOT NULL,
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
            raise SandersLogisticsForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersLogisticsForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersLogisticsForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_LOGISTICS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersLogisticsForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersLogisticsDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #70',
                'deploy/oracle/sanders_master_grid.json id 16',
                'Set B schema seed row and Set C Tier 3 section (both read directly)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Logistics is the supply chain management platform: it carries governed logistics records over supply chains and lanes and declared shipment sets presented by reference only. It ships nothing, dispatches no fleet, routes no shipment, and procures nothing: ship_goods, dispatch_fleet, route_shipment, procure_goods, and external_execution are refused by name under LOGISTICS_RECORDS_ONLY, and determinations are records for human operators, never movements. A record declared with no shipments stands NO_SHIPMENTS_SUBMITTED and no determination can be recorded on it. Two nicknames conflict as found — “Flow” (the grid and Set B) and “Transport” (Set C) — and Set C gives “Flow” to Sanders Supply Chain (catalog #120); neither nickname is adopted as the platform’s name. Set C’s designed hostname logistics.sandersglobal.com sits under the unowned parent sandersglobal.com — recorded, and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no cargo content, no customer data, no live carrier state. Sanders Logistics is distinct from Sanders Supply Chain (catalog #120) and Sanders Transportation (catalog #74) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a movement operation or an execution operation
        the logistics records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersLogisticsDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Logistics platform carries'
                ' logistics records only \u2014 it'
                ' ships nothing, dispatches no fleet, and'
                ' procures nothing itself'
                ' (LOGISTICS_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersLogisticsDenied(
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
        shipments = json.loads(row['shipment_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'shipment_refs': shipments,
            'shipment_count': row['shipment_count'],
            'shipment_state': ('NO_SHIPMENTS_SUBMITTED'
                             if row['shipment_count'] == 0
                             else 'SHIPMENTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, shipment_refs,
                      scope_ref, *, region=None):
        """Record one logistics record (operator only) over
        a subject and a declared set of shipment
        references, presented by reference. The shipment set
        may be empty — the record then stands
        NO_SHIPMENTS_SUBMITTED, exactly as the shipment
        discipline holds, and no determination can be
        recorded on it. Recording the record ships nothing,
        dispatches no fleet, and procures nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersLogisticsDenied(
                    f'A {label} is required')
        if not isinstance(shipment_refs, (list, tuple)):
            raise SandersLogisticsDenied(
                'shipment_refs must be a list of references')
        if len(shipment_refs) > MAX_REFS:
            raise SandersLogisticsDenied(
                f'At most {MAX_REFS} shipment'
                ' references per record')
        shipments = []
        for ref in shipment_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersLogisticsDenied(
                    'Every shipment reference must be a'
                    ' non-empty string')
            shipments.append(ref.strip())
        now = self._now()
        record_id = f'sanders-logistics-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_LOGISTICS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    shipment_count=len(shipments))
                db.execute(
                    'INSERT INTO sanders_logistics_records'
                    ' (record_id, subject_ref, shipment_refs,'
                    ' shipment_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(shipments), len(shipments),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_logistics_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_logistics_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_logistics_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersLogisticsDenied(
                'Logistics record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested logistics record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersLogisticsDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_logistics_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLogisticsDenied(
                        'Logistics record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersLogisticsDenied(
                        f"Cannot {action} a logistics record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_LOGISTICS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_logistics_records SET status = ?,'
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
                'SELECT * FROM sanders_logistics_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (CHAIN_CONFIRMED or COORDINATION_REQUIRED) on a
        record declared with no shipments is refused —
        NO_SHIPMENTS_SUBMITTED: no shipments were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersLogisticsDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersLogisticsDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_logistics_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLogisticsDenied(
                        'Logistics record not found')
                if row['status'] != 'APPROVED':
                    raise SandersLogisticsDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" logistics records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['shipment_count'] == 0:
                    raise SandersLogisticsDenied(
                        'NO_SHIPMENTS_SUBMITTED: a record'
                        ' declared with no shipments cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_LOGISTICS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_logistics_records SET status = ?,'
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
                'SELECT * FROM sanders_logistics_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_logistics_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_logistics_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_logistics_records'
                ' WHERE shipment_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(shipment_count), 0) AS n'
                ' FROM sanders_logistics_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_shipments_submitted': no_refs,
            'shipments_declared_total': refs_total,
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
                    raise SandersLogisticsDenied(str(exc)) from exc
                self._record('SANDERS_LOGISTICS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
