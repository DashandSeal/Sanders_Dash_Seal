"""Sanders Global Relations — the global
relations platform.

The production build-out of the Sanders Global
Relations design (canonical catalog row #131,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q99).

NAME — verified before building, per the name
law: the canonical catalog (row #131) and Set
C Tier 9 name this platform **Sanders Global
Relations** — the queue-note reading matched
the source name exactly. Set B carries NO
entry under this name (verified by direct read
of the schema and the tier pricing file), and
Set A carries no entry for this platform
(verified by direct read of the platform
registry); the MASTER names it nowhere
(verified). Set C's tier catalog entry is the
platform's only design record.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Diplomat". It
is recorded exactly as found and is not
adopted as the platform's persona, name, or
identifier.

Set C's purpose text for this name —
"Global diplomacy, UN/NATO replacement
capability, international relations, alliance
management" — is recorded verbatim as found
and is NOT the built scope beyond governed
global relations records: no diplomacy is
conducted, no treaty is negotiated, no
alliance is formed, and no communique is
issued by this build; the "replacement
capability" wording is design-record language,
not a claim. Set C's classification for this
platform is Secret, recorded as found. Set C's
embedded registry carries NO entry for this
platform (verified by direct read), so no
designed hostname is recorded for it in any
examined source.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — global diplomacy,
international relations, and alliance
management (canonical catalog row #131; Set C
Tier 9 — the platform's only design record;
Set B carries no row). No Sanders Global
Relations module existed in any examined
source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Global Relations platform's own identity and
store, carrying global relations records:

- **Global relations records**: a subject
  reference (a diplomatic engagement, relations
  program, or alliance matter under service, by
  reference), a declared set of engagement
  references, and a scope reference, carried
  as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The engagement discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (RELATIONS_POSITION_CONFIRMED /
  ENGAGEMENT_ACTION_REQUIRED / INCONCLUSIVE).
  A record declared with no engagements stands
  NO_ENGAGEMENTS_SUBMITTED in every view and
  in the status tallies, and both
  determinations are refused on it — no
  engagements were presented to determine
  from; INCONCLUSIVE, which asserts nothing,
  records against evidence.
- **Records, never diplomacy**: determinations
  are records placed before human operators.
  The platform conducts no diplomacy,
  negotiates no treaty, forms no alliance, and
  issues no communique — conduct_diplomacy,
  negotiate_treaty, form_alliance,
  issue_communique, and external_execution are
  refused by name under
  GLOBAL_RELATIONS_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  engagements are carried by reference only;
  the platform holds no diplomatic
  correspondence, no treaty text, no state
  data, and no credentials — references and
  workflow state only, as across the
  ecosystem. No public or customer surface is
  designed for this platform in any examined
  source, so none was built; no security
  internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B
  row; no Set A entry; no Set C NAICS
  attestation) — NO NAICS set is carried into
  the platform's built identity and none is
  invented.
- **Separation**: the Sanders Global Relations
  platform is its own platform. It is not
  Sanders Global Freedom (catalog #95), not
  Sanders Strategy Hub (catalog #94), and not
  Sanders Freedom Revolution (catalog #86) —
  identities are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 928120,
541820, 541611, 541618, 519190, 541690 — COMPLETED_NEW per
the NACI six-code reconciliation of 2026-11-26. The
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
    platform_id='sanders_global_relations',
    name='Sanders Global Relations',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('928120', '541820', '541611', '541618', '519190', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Global diplomacy, international relations, alliance management'
DISCIPLINE = 'GLOBAL_RELATIONS_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_global_relations', 'approve_global_relations', 'record_outcome',
    'view_global_relations', 'view_design')
EXECUTION_OPERATIONS = ('conduct_diplomacy', 'negotiate_treaty',
    'form_alliance', 'issue_communique',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('RELATIONS_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('RELATIONS_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersGlobalRelationsDenied(Exception):
    """The requested Sanders Global Relations operation is not
    allowed."""


class SandersGlobalRelationsForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersGlobalRelationsService:
    """Sanders Global Relations: governed global relations records under the global relations records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersGlobalRelationsDenied(
                'Sanders Global Relations requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_global_relations', {
            'OPERATOR': {'SANDERS_GLOBAL_RELATIONS'},
            'AUDITOR': {'SANDERS_GLOBAL_RELATIONS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_global_relations_records (
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
            raise SandersGlobalRelationsForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersGlobalRelationsForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersGlobalRelationsForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_GLOBAL_RELATIONS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersGlobalRelationsForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersGlobalRelationsDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #131', 'Set C Tier 9 catalog entry (read directly) — the platform’s only design record', 'Set C embedded registry (read directly): NO entry for this platform — no designed hostname recorded', 'Set B: no entry under this name (verified by direct read of database_schema.sql and tier_pricing_global.py); Set A carries no entry (platform registry read directly); the MASTER names it nowhere (verified)', 'decisions.md: no ruling names this platform; the Sanders Global Freedom (catalog #95) identity stays separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Global Relations is the global relations platform: it carries governed global relations records over diplomatic engagements, relations programs, and alliance matters and declared engagement sets presented by reference only. Set C’s purpose text for this name — Global diplomacy, UN/NATO replacement capability, international relations, alliance management — is recorded verbatim as found and is NOT the built scope: no diplomacy is conducted, no treaty is negotiated, no alliance is formed, and no communique is issued by this build; the replacement-capability wording is design-record language, not a claim. The platform conducts no diplomacy, negotiates no treaty, forms no alliance, and issues no communique: conduct_diplomacy, negotiate_treaty, form_alliance, issue_communique, and external_execution are refused by name under GLOBAL_RELATIONS_RECORDS_ONLY, and determinations are records for human operators, never diplomacy. A record declared with no engagements stands NO_ENGAGEMENTS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Diplomat is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set C’s classification for this platform is Secret, recorded as found. Set B carries NO entry under this name (verified by direct read), and Set A carries no entry for this platform. Set C’s embedded registry carries no entry for this platform, so no designed hostname is recorded for it in any examined source. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no diplomatic correspondence, no treaty text, no state data, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Global Relations is distinct from Sanders Global Freedom (catalog 95), Sanders Strategy Hub (catalog 94), and Sanders Freedom Revolution (catalog 86) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the global relations records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersGlobalRelationsDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Global Relations platform'
                ' carries global relations records'
                ' only \u2014 it conducts no'
                ' diplomacy, negotiates no treaty,'
                ' forms no alliance, and issues'
                ' no communique itself'
                ' (GLOBAL_RELATIONS_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersGlobalRelationsDenied(
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
        """Record one global relations record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_ENGAGEMENTS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record conducts no diplomacy,
        negotiates no treaty, and forms
        no alliance."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersGlobalRelationsDenied(
                    f'A {label} is required')
        if not isinstance(engagement_refs, (list, tuple)):
            raise SandersGlobalRelationsDenied(
                'engagement_refs must be a list of references')
        if len(engagement_refs) > MAX_REFS:
            raise SandersGlobalRelationsDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in engagement_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersGlobalRelationsDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-global-relations-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_GLOBAL_RELATIONS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    engagement_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_global_relations_records'
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
                'SELECT * FROM sanders_global_relations_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_global_relations_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_global_relations_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersGlobalRelationsDenied(
                'Global Relations record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested global relations record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersGlobalRelationsDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_global_relations_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersGlobalRelationsDenied(
                        'Global Relations record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersGlobalRelationsDenied(
                        f"Cannot {action} a global relations record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_GLOBAL_RELATIONS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_global_relations_records SET status = ?,'
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
                'SELECT * FROM sanders_global_relations_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (RELATIONS_POSITION_CONFIRMED or ENGAGEMENT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_ENGAGEMENTS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersGlobalRelationsDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersGlobalRelationsDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_global_relations_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersGlobalRelationsDenied(
                        'Global Relations record not found')
                if row['status'] != 'APPROVED':
                    raise SandersGlobalRelationsDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" global relations records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['engagement_count'] == 0:
                    raise SandersGlobalRelationsDenied(
                        'NO_ENGAGEMENTS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_GLOBAL_RELATIONS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_global_relations_records SET status = ?,'
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
                'SELECT * FROM sanders_global_relations_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_global_relations_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_global_relations_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_global_relations_records'
                ' WHERE engagement_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(engagement_count), 0) AS n'
                ' FROM sanders_global_relations_records').fetchone()['n']
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
                    raise SandersGlobalRelationsDenied(str(exc)) from exc
                self._record('SANDERS_GLOBAL_RELATIONS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
