"""Sanders Marketing — the marketing
operations platform.

The production build-out of the Sanders
Marketing design (canonical catalog row #126,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q94).

NAME — verified before building, per the name
law: the canonical catalog (row #126) and Set
C Tier 8 name this platform **Sanders
Marketing** — the queue-note reading matched
the source name exactly. Set B carries NO
entry under this name (verified by direct read
of the schema and the tier pricing file), and
Set A carries no entry for this platform
(verified by direct read of the platform
registry); the MASTER names it nowhere. Set
C's tier catalog entry is the platform's only
design record.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Campaign". It
is recorded exactly as found and is not
adopted as the platform's persona, name, or
identifier.

Set C's purpose text for this name —
"Marketing operations, branding supremacy,
campaign mastery, digital strategy" — is
recorded verbatim as found and is NOT the
built scope beyond governed marketing
records: no campaign is launched, no campaign
is run, no advertising is purchased, and
nothing is published by this build; the
"supremacy" and "mastery" wording is
design-record language, not a claim. The
designed hostname marketing.sandersglobal.com
(Set C registry record) sits under the
unowned parent sandersglobal.com, so it is
recorded and nothing is served there.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — marketing operations,
branding, campaign management, and digital
strategy (canonical catalog row #126; Set C
Tier 8 — the platform's only design record;
Set B carries no row). No Sanders Marketing
module existed in any examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Marketing platform's own identity and store,
carrying marketing records:

- **Marketing records**: a subject reference
  (a marketing program, brand line, or campaign
  plan under service, by reference), a declared
  set of campaign references, and a scope
  reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded
  against presented evidence
  (OUTCOME_RECORDED).
- **The campaign discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (MARKETING_POSITION_CONFIRMED /
  CAMPAIGN_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no campaigns stands
  NO_CAMPAIGNS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no campaigns were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never marketing**: determinations
  are records placed before human operators.
  The platform launches no campaign, runs no
  campaign, purchases no advertising, and
  publishes nothing — launch_campaign,
  run_campaign, purchase_advertising,
  publish_marketing, and external_execution
  are refused by name under
  MARKETING_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  campaigns are carried by reference only; the
  platform holds no creative content, no
  advertising accounts, no audience data, and
  no credentials — references and workflow
  state only, as across the ecosystem. No
  public or customer surface is designed for
  this platform in any examined source, so
  none was built; no security internals are
  exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B
  row; no Set A entry; no Set C registry NAICS
  map entry) — NO NAICS set is carried into
  the platform's built identity and none is
  invented.
- **Separation**: the Sanders Marketing
  platform is its own platform. It is not
  Sanders Sales (catalog #127), not Sanders
  Communications (catalog #113), not Showtime
  (catalog #112+125), and not Sanders Signal
  (catalog #12 — the social-distribution
  platform, a separate identity) — identities
  are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541810,
541613, 541910, 541820, 541512, 519130 — COMPLETED_NEW per
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
    platform_id='sanders_marketing',
    name='Sanders Marketing',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541810', '541613', '541910', '541820', '541512', '519130'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Marketing operations, campaign management, digital strategy'
DISCIPLINE = 'MARKETING_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_marketing', 'approve_marketing', 'record_outcome',
    'view_marketing', 'view_design')
EXECUTION_OPERATIONS = ('launch_campaign', 'run_campaign',
    'purchase_advertising', 'publish_marketing',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('MARKETING_POSITION_CONFIRMED', 'CAMPAIGN_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('MARKETING_POSITION_CONFIRMED', 'CAMPAIGN_ACTION_REQUIRED')
MAX_REFS = 100


class SandersMarketingDenied(Exception):
    """The requested Sanders Marketing operation is not
    allowed."""


class SandersMarketingForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersMarketingService:
    """Sanders Marketing: governed marketing records under the marketing records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersMarketingDenied(
                'Sanders Marketing requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_marketing', {
            'OPERATOR': {'SANDERS_MARKETING'},
            'AUDITOR': {'SANDERS_MARKETING'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_marketing_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    campaign_refs TEXT NOT NULL,
                    campaign_count INTEGER NOT NULL,
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
            raise SandersMarketingForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersMarketingForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersMarketingForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_MARKETING',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersMarketingForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersMarketingDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #126', 'Set C Tier 8 catalog entry (read directly) — the platform’s only design record', 'Set B: no entry under this name (verified by direct read of the schema and the tier pricing file); Set A carries no entry (platform registry read directly); the MASTER names it nowhere', 'decisions.md: no ruling names this platform; the Sanders Sales (catalog #127) and Sanders Signal (catalog #12) identities stay separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Marketing is the marketing operations platform: it carries governed marketing records over marketing programs, brand lines, and campaign plans and declared campaign sets presented by reference only. Set C’s purpose text for this name — Marketing operations, branding supremacy, campaign mastery, digital strategy — is recorded verbatim as found and is NOT the built scope: no campaign is launched, no campaign is run, no advertising is purchased, and nothing is published by this build; the supremacy and mastery wording is design-record language, not a claim. The platform launches no campaign, runs no campaign, purchases no advertising, and publishes nothing: launch_campaign, run_campaign, purchase_advertising, publish_marketing, and external_execution are refused by name under MARKETING_RECORDS_ONLY, and determinations are records for human operators, never marketing. A record declared with no campaigns stands NO_CAMPAIGNS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Campaign is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set B carries NO entry under this name (verified by direct read), and Set A carries no entry for this platform. The designed hostname marketing.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no creative content, no advertising accounts, no audience data, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Marketing is distinct from Sanders Sales (catalog 127), Sanders Communications (catalog 113), Showtime (catalog 112+125), and Sanders Signal (catalog 12) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the marketing records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersMarketingDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Marketing platform'
                ' carries marketing records'
                ' only \u2014 it launches no'
                ' campaign, runs no campaign,'
                ' purchases no advertising, and'
                ' publishes nothing itself'
                ' (MARKETING_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersMarketingDenied(
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
        operations = json.loads(row['campaign_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'campaign_refs': operations,
            'campaign_count': row['campaign_count'],
            'campaign_state': ('NO_CAMPAIGNS_SUBMITTED'
                             if row['campaign_count'] == 0
                             else 'CAMPAIGNS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, campaign_refs,
                      scope_ref, *, region=None):
        """Record one marketing record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_CAMPAIGNS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record launches no
        campaign, purchases no advertising,
        and publishes nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersMarketingDenied(
                    f'A {label} is required')
        if not isinstance(campaign_refs, (list, tuple)):
            raise SandersMarketingDenied(
                'campaign_refs must be a list of references')
        if len(campaign_refs) > MAX_REFS:
            raise SandersMarketingDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in campaign_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersMarketingDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-marketing-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_MARKETING_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    campaign_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_marketing_records'
                    ' (record_id, subject_ref, campaign_refs,'
                    ' campaign_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_marketing_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_marketing_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_marketing_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersMarketingDenied(
                'Marketing record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested marketing record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersMarketingDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_marketing_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersMarketingDenied(
                        'Marketing record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersMarketingDenied(
                        f"Cannot {action} a marketing record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_MARKETING_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_marketing_records SET status = ?,'
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
                'SELECT * FROM sanders_marketing_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (MARKETING_POSITION_CONFIRMED or CAMPAIGN_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_CAMPAIGNS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersMarketingDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersMarketingDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_marketing_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersMarketingDenied(
                        'Marketing record not found')
                if row['status'] != 'APPROVED':
                    raise SandersMarketingDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" marketing records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['campaign_count'] == 0:
                    raise SandersMarketingDenied(
                        'NO_CAMPAIGNS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_MARKETING_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_marketing_records SET status = ?,'
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
                'SELECT * FROM sanders_marketing_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_marketing_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_marketing_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_marketing_records'
                ' WHERE campaign_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(campaign_count), 0) AS n'
                ' FROM sanders_marketing_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_campaigns_submitted': no_refs,
            'campaigns_declared_total': refs_total,
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
                    raise SandersMarketingDenied(str(exc)) from exc
                self._record('SANDERS_MARKETING_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
