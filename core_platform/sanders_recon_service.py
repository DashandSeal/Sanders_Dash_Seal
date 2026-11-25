"""Sanders Recon — the security intelligence and
reconnaissance platform.

The production build-out of the Sanders Recon design
(canonical catalog row #63, Band 2D), built whole as its
own platform service over the shared RTSA foundation
(RTSA Build Program Q55).

NAME — verified before building, per the name law: the
canonical catalog (row #63) and the owner's recorded
ruling D-N4 name this platform **Sanders Recon**. D-N4
rules expressly against both competing forms: "Sanders
AI Recon" (the master grid, Set B, Set C, and the
pre-existing registry record) and "Sanders Recon Ops"
(Set A) are NOT the name. The recon-ops hostname
(recon-ops.sandersglobal.com) stays as the designed
address under D-N4 — name and address differ, the
owner's call; it sits under the unowned parent
sandersglobal.com, so it is recorded as the designed
address and nothing is served there. The grid nickname
"ReconX", the Set C nickname "Recon", and the Set B seed
persona string "RECON" are recorded here exactly as
found and are not adopted as this platform's identity.
The pre-existing registry entry's name is corrected in
place under D-N4; its machine id (sanders_ai_recon) is
retained — machine strings are not names.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Security intelligence / recon" (canonical
catalog row #63; master grid id 8). Set C's purpose text
for this name — "AI reconnaissance, NRO satellite
integration, SIGINT/HUMINT fusion, predictive
analytics" — is recorded here exactly as found, as a
design-record claim of that catalog; it is NOT the built
scope: no source the owner has ruled adopts it, and this
build constructs no satellite integration, no signals
collection, no interception, and no external-agency
integration of any kind. The grid endpoint the records
carry (a Google Cloud host, :3008) is a file claim, not
a verified live check, and the grid file is truncated at
id 28; no Sanders Recon module existed in any examined
source.

REBUILT (everything executable in this module): the
governed platform below — Sanders Recon's own identity
and store, carrying security-intelligence records over
subjects and intelligence reports presented by
reference:

- **Intelligence records**: a subject reference (the
  platform, system, service, or area under intelligence
  review, by reference), a declared set of
  intelligence-report references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The report discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (INTELLIGENCE_CONFIRMED / THREAT_INDICATED /
  INCONCLUSIVE). A record declared with no reports
  stands NO_REPORTS_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no reports were presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Records, never collection**: determinations are
  records placed before human decision-makers. The
  platform collects nothing, intercepts nothing, and
  accesses no external system — conduct_surveillance,
  collect_signals_intelligence, intercept_communications,
  access_external_system, and external_execution are
  refused by name under INTELLIGENCE_RECORDS_ONLY.
- **Reference-only discipline**: subjects and reports
  are carried by reference only; the platform holds no
  collected material, no intercepted content, and no
  live-system state.
- **NAICS**: three sources attest three different sets
  — the grid (541715, 541512, 541511, 541519, 561621,
  541690), Set B (541512, 561621), and the Set A/README
  map under "Sanders Recon Ops" (621399, 541618, 561612,
  523991, 541715, 611430). No owner ruling assigns a set,
  and the canonical catalog row carries none — NO NAICS
  set is carried into his built identity; the three sets
  stand recorded as attested and unruled.
- **Separation**: Sanders Recon is its own platform. He
  is not Sanders Intelligence (catalog #98 — a separate
  platform, D-N5), not Sanders Security (catalog #71),
  and not Sanders Security Ops (catalog #130); the
  security-name boundaries remain undrawn in the sources
  (D-N13 partial) and nothing is merged here.

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
    platform_id='sanders_recon',
    name='Sanders Recon',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Security intelligence / recon'
DISCIPLINE = 'INTELLIGENCE_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_intelligence', 'approve_intelligence', 'record_outcome',
    'view_intelligence', 'view_design')
EXECUTION_OPERATIONS = ('conduct_surveillance', 'collect_signals_intelligence',
    'intercept_communications', 'access_external_system',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('INTELLIGENCE_CONFIRMED', 'THREAT_INDICATED',
            'INCONCLUSIVE')
DETERMINATIONS = ('INTELLIGENCE_CONFIRMED', 'THREAT_INDICATED')
MAX_REFS = 100


class SandersReconDenied(Exception):
    """The requested Sanders Recon operation is not
    allowed."""


class SandersReconForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersReconService:
    """Sanders Recon: governed security-intelligence records
    under the intelligence records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersReconDenied(
                'Sanders Recon requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_recon', {
            'OPERATOR': {'SANDERS_RECON'},
            'AUDITOR': {'SANDERS_RECON'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_recon_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    report_refs TEXT NOT NULL,
                    report_count INTEGER NOT NULL,
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
            raise SandersReconForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersReconForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersReconForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_RECON',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersReconForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersReconDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #63',
                'deploy/oracle/sanders_master_grid.json id 8',
                'owner ruling D-N4 (canonical name Sanders'
                ' Recon)',
                'Set B schema seed row and Set C tier'
                ' catalog entry (read directly)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Recon is the security'
                    ' intelligence platform: he carries'
                    ' governed intelligence records over'
                    ' subjects and intelligence reports'
                    ' presented by reference only. The name'
                    ' is Sanders Recon per owner ruling D-N4'
                    ' \u2014 neither Sanders AI Recon (grid,'
                    ' Set B, Set C, registry record) nor'
                    ' Sanders Recon Ops (Set A); the'
                    ' recon-ops hostname stays as the'
                    ' designed address and nothing is served'
                    ' there. He collects nothing, intercepts'
                    ' nothing, and accesses no external'
                    ' system: conduct_surveillance,'
                    ' collect_signals_intelligence,'
                    ' intercept_communications,'
                    ' access_external_system, and'
                    ' external_execution are refused by name'
                    ' under INTELLIGENCE_RECORDS_ONLY, and'
                    ' determinations are records for human'
                    ' decision-makers, never acts. A record'
                    ' declared with no reports stands'
                    ' NO_REPORTS_SUBMITTED and no'
                    ' determination can be recorded on it.'
                    ' Set C\u2019s purpose text (NRO satellite'
                    ' integration, SIGINT/HUMINT fusion) is'
                    ' recorded as found and is NOT the built'
                    ' scope. His three attested NAICS sets'
                    ' are recorded as found, and no NAICS set'
                    ' is carried into his identity. Sanders'
                    ' Recon is distinct from Sanders'
                    ' Intelligence, Sanders Security, and'
                    ' Sanders Security Ops \u2014 identities'
                    ' are never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a collection or execution operation the
        intelligence-records discipline does not authorize,
        or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersReconDenied(
                f'Operation {operation!r} is refused: Sanders'
                ' Recon carries intelligence records only'
                ' \u2014 he collects nothing, intercepts'
                ' nothing, and accesses no external system'
                ' (INTELLIGENCE_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersReconDenied(
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
        reports = json.loads(row['report_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'report_refs': reports,
            'report_count': row['report_count'],
            'report_state': ('NO_REPORTS_SUBMITTED'
                             if row['report_count'] == 0
                             else 'REPORTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, report_refs,
                      scope_ref, *, region=None):
        """Record one global-intelligence record (operator only) over
        a subject and a declared set of intelligence-report
        references, presented by reference. The report set may
        be empty — the record then stands NO_REPORTS_SUBMITTED,
        exactly as the report discipline holds, and no
        determination can be recorded on it. Recording the
        record collects nothing live and acts on nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersReconDenied(
                    f'A {label} is required')
        if not isinstance(report_refs, (list, tuple)):
            raise SandersReconDenied(
                'report_refs must be a list of references')
        if len(report_refs) > MAX_REFS:
            raise SandersReconDenied(
                f'At most {MAX_REFS} report'
                ' references per record')
        reports = []
        for ref in report_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersReconDenied(
                    'Every report reference must be a'
                    ' non-empty string')
            reports.append(ref.strip())
        now = self._now()
        record_id = f'sanders-recon-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_RECON_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    report_count=len(reports))
                db.execute(
                    'INSERT INTO sanders_recon_records'
                    ' (record_id, subject_ref, report_refs,'
                    ' report_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(reports), len(reports),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_recon_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_recon_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_recon_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersReconDenied(
                'Intelligence record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested intelligence record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersReconDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_recon_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersReconDenied(
                        'Intelligence record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersReconDenied(
                        f"Cannot {action} an intelligence record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_RECON_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_recon_records SET status = ?,'
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
                'SELECT * FROM sanders_recon_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (INTELLIGENCE_CONFIRMED or THREAT_INDICATED) on a
        record declared with no reports is refused —
        NO_REPORTS_SUBMITTED: no reports were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersReconDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersReconDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_recon_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersReconDenied(
                        'Intelligence record not found')
                if row['status'] != 'APPROVED':
                    raise SandersReconDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" intelligence records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['report_count'] == 0:
                    raise SandersReconDenied(
                        'NO_REPORTS_SUBMITTED: a record'
                        ' declared with no reports cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_RECON_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_recon_records SET status = ?,'
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
                'SELECT * FROM sanders_recon_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_recon_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_recon_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_recon_records'
                ' WHERE report_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(report_count), 0) AS n'
                ' FROM sanders_recon_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_reports_submitted': no_signals,
            'reports_declared_total': signals_total,
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
                    raise SandersReconDenied(str(exc)) from exc
                self._record('SANDERS_RECON_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
