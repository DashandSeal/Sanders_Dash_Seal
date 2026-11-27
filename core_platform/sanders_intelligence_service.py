"""Sanders Intelligence — the intelligence
analysis platform.

The production build-out of the Sanders
Intelligence design (canonical catalog row #98,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q79).

NAME — verified before building, per the name
law, WITH A FLAGGED FORM CONFLICT: the
canonical catalog's row #98 head name is
"Sanders Intelligence Ops" — Set A's form — but
the owner's decisions record rules the
canonical name (D-N5): **Sanders Intelligence**,
Set C's form, not "Sanders Intelligence Ops".
The ruling governs the build; the Ops form is
recorded exactly as found and is never adopted
as the platform's name. Set C's nickname for
this platform is "Intel Ops" — recorded as
found; it echoes the unruled name form and is
not adopted as a name or identifier. Set C's
embedded registry record pairs this platform as
"Sanders Intelligence / Recon" — recorded
exactly as found and NOT adopted: Sanders Recon
(catalog #63) is a separate platform under its
own ruling (D-N4), and no identity is shared or
merged.

Set C's purpose text for this name —
"Intelligence analysis, covert operations,
OSINT/HUMINT, classified operations support" —
is recorded verbatim as found and is NOT the
built scope beyond governed intelligence-
analysis records: no covert operation, no
intelligence collection, no classified-system
access, and no surveillance was constructed.
Set C's "TS" classification label for this
platform is a design-record label; the platform
holds no classified material. The designed
hostname intel-ops.sandersglobal.com sits
under the unowned parent sandersglobal.com, so
it is recorded and nothing is served there; Set
C's registry record carries the hostname
intelligence.sandersglobal.com under the same
unowned parent, likewise recorded.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — intelligence analysis,
OSINT/HUMINT support (canonical catalog row
#98; Set C Tier 2). No Sanders Intelligence
module existed in any examined source; Set B
carries no row for this platform (verified by
direct read of the schema and the tier pricing
file).

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Intelligence platform's own identity and store,
carrying intelligence-analysis records:

- **Analysis records**: a subject reference (an
  intelligence question, analysis matter, or
  assessment program under service, by
  reference), a declared set of analysis
  references, and a scope reference, carried as
  durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The analysis discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set
  (INTELLIGENCE_POSITION_CONFIRMED /
  ANALYSIS_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no analyses stands
  NO_ANALYSES_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no analyses were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never collection**: determinations
  are records placed before human operators. The
  platform runs no covert operation, collects no
  intelligence, accesses no classified system,
  and conducts no surveillance —
  run_covert_operation, collect_intelligence,
  access_classified_system, conduct_surveillance,
  and external_execution are refused by name
  under INTELLIGENCE_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  analyses are carried by reference only; the
  platform holds no classified material, no
  source identities, no intercepted material,
  and no live-system state — references and
  workflow state only, as across the ecosystem.
  No public or customer surface is designed for
  this platform in any examined source, so none
  was built; no security internals are exposed.
- **NAICS**: the Set C registry NAICS map
  attests one set, recorded under the
  "Sanders Intelligence Ops" form (621399,
  541611, 561612, 541110, 541512, 611430). No
  owner ruling assigns a set, and the canonical
  catalog row carries none — NO NAICS set is
  carried into the platform's built identity;
  the attested set stands recorded as found and
  unruled.
- **Separation**: the Sanders Intelligence
  platform is its own platform. It is not
  Sanders Recon (catalog #63, ruled name D-N4),
  not Fraud RTSA (catalog #39), not Sanders
  Strategy Intel (catalog #117), and not Sanders
  Omniconn (catalog #59) — identities are never
  merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541910,
561621, 541618, 541512, 541519, 541611 — COMPOSED per the
NACI six-code reconciliation of 2026-11-26. The attested
sets recorded above stand as found; the reconciled six
govern the built identity from this lock-in forward.
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
    platform_id='sanders_intelligence',
    name='Sanders Intelligence',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541910', '561621', '541618', '541512', '541519', '541611'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Intelligence analysis, OSINT/HUMINT support'
DISCIPLINE = 'INTELLIGENCE_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_intelligence', 'approve_intelligence', 'record_outcome',
    'view_intelligence', 'view_design')
EXECUTION_OPERATIONS = ('run_covert_operation', 'collect_intelligence',
    'access_classified_system', 'conduct_surveillance',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('INTELLIGENCE_POSITION_CONFIRMED', 'ANALYSIS_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('INTELLIGENCE_POSITION_CONFIRMED', 'ANALYSIS_ACTION_REQUIRED')
MAX_REFS = 100


class SandersIntelligenceDenied(Exception):
    """The requested Sanders Intelligence operation is not
    allowed."""


class SandersIntelligenceForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersIntelligenceService:
    """Sanders Intelligence: governed intelligence-analysis records under the intelligence records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersIntelligenceDenied(
                'Sanders Intelligence requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_intelligence', {
            'OPERATOR': {'SANDERS_INTELLIGENCE'},
            'AUDITOR': {'SANDERS_INTELLIGENCE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_intelligence_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    analysis_refs TEXT NOT NULL,
                    analysis_count INTEGER NOT NULL,
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
            raise SandersIntelligenceForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersIntelligenceForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersIntelligenceForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_INTELLIGENCE',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersIntelligenceForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersIntelligenceDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #98', 'decisions.md D-N5: canonical name Sanders Intelligence (Set C form), not Sanders Intelligence Ops', 'Set A platform registry (Ops form, slug intel-ops, hostname)', 'Set C Tier 2 catalog entry (read directly); Set B carries no entry under either name form'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Intelligence is the intelligence analysis platform: it carries governed intelligence-analysis records over intelligence questions, analysis matters, and assessment programs and declared analysis sets presented by reference only. Set C’s purpose text for this name — Intelligence analysis, covert operations, OSINT/HUMINT, classified operations support — is recorded verbatim as found and is NOT the built scope: no covert operation, no intelligence collection, no classified-system access, and no surveillance was constructed; Set C’s TS classification label is a design-record label and the platform holds no classified material. The platform runs no covert operation, collects no intelligence, accesses no classified system, and conducts no surveillance: run_covert_operation, collect_intelligence, access_classified_system, conduct_surveillance, and external_execution are refused by name under INTELLIGENCE_RECORDS_ONLY, and determinations are records for human operators, never collection. A record declared with no analyses stands NO_ANALYSES_SUBMITTED and no determination can be recorded on it. NAME — RULED (D-N5): the canonical name is Sanders Intelligence (Set C’s form); the catalog row’s head name and Set A’s form, Sanders Intelligence Ops, are recorded exactly as found and never adopted as the platform’s name. Set C’s nickname Intel Ops is recorded as found and not adopted as a name or identifier; Set C’s embedded registry pairing “Sanders Intelligence / Recon” is recorded as found and NOT adopted — Sanders Recon (catalog 63) is a separate platform under D-N4. Set B carries NO entry under either name form (verified by direct read). The designed hostnames intel-ops.sandersglobal.com (Set A / catalog) and intelligence.sandersglobal.com (Set C registry record) sit under the unowned parent sandersglobal.com; both are recorded and nothing is served at either. Its attested NAICS set (the Set C registry NAICS map, recorded under the Ops form) is recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no classified material, no source identities, no intercepted material. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Intelligence is distinct from Sanders Recon (catalog 63), Fraud RTSA (catalog 39), Sanders Strategy Intel (catalog 117), and Sanders Omniconn (catalog 59) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the intelligence records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersIntelligenceDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Intelligence platform'
                ' carries intelligence records'
                ' only \u2014 it runs no covert'
                ' operation, collects no intelligence,'
                ' accesses no classified system, and'
                ' conducts no surveillance itself'
                ' (INTELLIGENCE_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersIntelligenceDenied(
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
        operations = json.loads(row['analysis_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'analysis_refs': operations,
            'analysis_count': row['analysis_count'],
            'analysis_state': ('NO_ANALYSES_SUBMITTED'
                             if row['analysis_count'] == 0
                             else 'ANALYSES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, analysis_refs,
                      scope_ref, *, region=None):
        """Record one intelligence record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_ANALYSES_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record collects no
        intelligence, runs no operation, and
        accesses no classified system."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersIntelligenceDenied(
                    f'A {label} is required')
        if not isinstance(analysis_refs, (list, tuple)):
            raise SandersIntelligenceDenied(
                'analysis_refs must be a list of references')
        if len(analysis_refs) > MAX_REFS:
            raise SandersIntelligenceDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in analysis_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersIntelligenceDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-intelligence-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_INTELLIGENCE_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    analysis_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_intelligence_records'
                    ' (record_id, subject_ref, analysis_refs,'
                    ' analysis_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_intelligence_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_intelligence_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_intelligence_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersIntelligenceDenied(
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
            raise SandersIntelligenceDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_intelligence_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersIntelligenceDenied(
                        'Intelligence record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersIntelligenceDenied(
                        f"Cannot {action} a intelligence record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_INTELLIGENCE_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_intelligence_records SET status = ?,'
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
                'SELECT * FROM sanders_intelligence_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (INTELLIGENCE_POSITION_CONFIRMED or ANALYSIS_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_ANALYSES_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersIntelligenceDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersIntelligenceDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_intelligence_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersIntelligenceDenied(
                        'Intelligence record not found')
                if row['status'] != 'APPROVED':
                    raise SandersIntelligenceDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" intelligence records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['analysis_count'] == 0:
                    raise SandersIntelligenceDenied(
                        'NO_ANALYSES_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_INTELLIGENCE_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_intelligence_records SET status = ?,'
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
                'SELECT * FROM sanders_intelligence_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_intelligence_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_intelligence_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_intelligence_records'
                ' WHERE analysis_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(analysis_count), 0) AS n'
                ' FROM sanders_intelligence_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_analyses_submitted': no_refs,
            'analyses_declared_total': refs_total,
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
                    raise SandersIntelligenceDenied(str(exc)) from exc
                self._record('SANDERS_INTELLIGENCE_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
