"""Sanders Ethics & Impact Collective
(SEIC) — the ethics, governance, and social
impact platform.

The production build-out of the Sanders Ethics
& Impact Collective design, built whole as its
own platform service over the shared RTSA
foundation. This platform is an OWNER-DIRECTED
ADDITION beyond the 140 repo-evidenced
platforms: the owner directed its build on
2026-11-25 (code-set directive 09:05 MST;
architecture supplied by the owner 09:06 MST)
— scope expanded by his word.

NAME — as named in the owner's architecture
document: **Sanders Ethics & Impact
Collective (SEIC)**. No nickname or persona
is designed for this platform in any examined
source; none is recorded and none is adopted.

DESIGNED PURPOSE — the owner's architecture
document designs five integrated service
pillars, recorded exactly as designed:
(1) Legal & Compliance Framework — ethics
compliance audits, regulatory guidance
(healthcare, AI, environmental), whistleblower
protection programs, governance policy
development; (2) Strategic Consulting —
corporate governance transformation, ESG
strategy, DEI program implementation, ethics
training and certification; (3) Environmental
& Sustainability — environmental justice
assessments, climate ethics consulting,
sustainability compliance, green healthcare
initiatives; (4) Professional Standards &
Networks — industry ethics standards
development, professional certification
programs, peer accountability systems,
continuing education platforms; (5)
Specialized Services & Impact Funding —
ethics auditing services, institutional
review board (IRB) consulting, grant funding
for ethics initiatives, social impact
measurement. The document's target markets
are recorded as designed: primary —
healthcare organizations (including hospital
ethics committees, health tech companies,
medical device manufacturers, telemedicine
platforms), AI & technology companies,
government agencies, and corporations
(Fortune 1000); secondary — nonprofits,
academic institutions, professional
associations, and startups.

NAICS — the owner's selection, recorded
EXACTLY (directive 2026-11-25 09:05):
541110 (Offices of Lawyers), 541618 (Other
Management Consulting Services), 541620
(Environmental Consulting Services), 813910
(Business Associations), 813920 (Professional
Organizations), 541990 (All Other
Professional, Scientific, and Technical
Services), 541611 (Administrative Management
and General Management Consulting Services),
813219 (Other Grantmaking and Giving
Services). This set is carried into the
platform's built identity as the owner
selected it; the cautions recorded in the
design brief (541110 implies a law practice;
813910/813920 classify membership
organizations; 541620 fit) were delivered to
the owner before the directive and he kept
all three — his ruling stands.

DESIGNED BUSINESS MODEL — recorded from the
architecture document as found, NOT wired as
charges: consulting services at $200–$500 per
hour, project engagements $25K–$500K,
retainers $10K–$50K per month; platform
subscriptions at $299 / $999 / $4,999 per
month; certification programs $2,500–$10,000
per certification and corporate training
packages $15K–$100K; grant administration at
a 5–10% fee on grants administered;
memberships $500–$2,500 per year. These are
the document's designed figures, recorded as
found; this build carries pricing structure
only and charges nothing.

FOUNDATION — the architecture document's
Sanders Healthcare Foundation relationship
(the document's ecosystem diagram and its
"Foundation Backing" moat) is recorded as
design text only. The Foundation is NOT one
of the four verified companies; this platform
is not registered under it, and no Foundation
entity is created by this build. The standard
universal attachment of the ecosystem applies
as across the program.

BRANDING — the owner's direction (2026-11-25):
SEIC is a headquarters-scope platform —
ethics and governance is a
corporate-headquarters function, as with
Bozly and Secretary. Its associated company
for the dual-seal lockup is S & G Security
Inc. (Corporate Headquarters itself), so the
lockup carries the headquarters seal in both
positions, per the watchdog/Grantwriter
precedent (headquarters and the associated
company are the same entity). The platform
sits under Sanders Corporate Headquarters in
the Universal Corporate Integration
structure, attached to all four companies
with S & G Security Inc. as its associated
company. Name presentation: "Sanders Ethics
& Impact Collective". The purple-heart HQ
seal variant was not used (Sanders Home
Healthcare & Caregivers exclusive).

No designed hostname is recorded for this
platform in any examined source — the
document names none — so none is recorded and
nothing is served under a designed name. The
document's Client Portal / Provider Network /
Knowledge Hub concepts are recorded as design
text; no public web surface is specified in
the document, so none was built — the
platform is wired through the standard route
family like every platform in the program,
and no security internals are exposed.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — the five service pillars
above, on the owner's eight NAICS codes, with
the document's target markets and designed
business model (owner's architecture document,
2026-11-25; code-set directive 2026-11-25
09:05). No SEIC module existed in any examined
source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Ethics & Impact Collective platform's own
identity and store, carrying governed
engagement records:

- **Engagement records**: a subject reference
  (an ethics, governance, or social-impact
  engagement or program matter under service,
  by reference), a declared set of engagement
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
  (SEIC_POSITION_CONFIRMED /
  ENGAGEMENT_ACTION_REQUIRED / INCONCLUSIVE).
  A record declared with no engagements stands
  NO_ENGAGEMENTS_SUBMITTED in every view and
  in the status tallies, and both
  determinations are refused on it — no
  engagements were presented to determine
  from; INCONCLUSIVE, which asserts nothing,
  records against evidence.
- **Records, never operations**: determinations
  are records placed before human operators.
  The platform practices no law, gives no
  legal advice, administers no grant,
  disburses no funds, issues no certification,
  and enrolls no member — practice_law,
  provide_legal_advice, administer_grant,
  disburse_funds, issue_certification,
  enroll_member, and external_execution are
  refused by name under SEIC_RECORDS_ONLY.
  The designed services are recorded as the
  platform's offerings; no operational
  capability is claimed.
- **Reference-only discipline**: subjects and
  engagements are carried by reference only;
  the platform holds no legal work product,
  no client files, no grant funds, no member
  records content, and no credentials —
  references and workflow state only, as
  across the ecosystem.
- **Separation**: the Sanders Ethics & Impact
  Collective is its own platform, built under
  its own identity. It is not Sanders Legal
  Helpers, not Sanders Legal Services
  (catalog #116), not Sanders Consulting
  (catalog #77), and not Grantwriter —
  identities are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.
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
    platform_id='sanders_ethics_impact_collective',
    name='Sanders Ethics & Impact Collective',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Ethics, governance, and social impact — legal and compliance framework, strategic consulting, environmental sustainability, professional standards, specialized services and impact funding (owner design record, 2026-11-25)'
DISCIPLINE = 'SEIC_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_seic', 'approve_seic', 'record_outcome',
    'view_seic', 'view_design')
EXECUTION_OPERATIONS = ('practice_law', 'provide_legal_advice',
    'administer_grant', 'disburse_funds', 'issue_certification',
    'enroll_member', 'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SEIC_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SEIC_POSITION_CONFIRMED', 'ENGAGEMENT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersEthicsImpactCollectiveDenied(Exception):
    """The requested Sanders Ethics & Impact Collective operation is not
    allowed."""


class SandersEthicsImpactCollectiveForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersEthicsImpactCollectiveService:
    """Sanders Ethics & Impact Collective: governed ethics and impact engagement records under the SEIC records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersEthicsImpactCollectiveDenied(
                'Sanders Ethics & Impact Collective requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_ethics_impact_collective', {
            'OPERATOR': {'SANDERS_ETHICS_IMPACT_COLLECTIVE'},
            'AUDITOR': {'SANDERS_ETHICS_IMPACT_COLLECTIVE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_ethics_impact_collective_records (
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
            raise SandersEthicsImpactCollectiveForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersEthicsImpactCollectiveForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersEthicsImpactCollectiveForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_ETHICS_IMPACT_COLLECTIVE',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersEthicsImpactCollectiveForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersEthicsImpactCollectiveDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['owner directive 2026-11-25 09:05 MST — the eight NAICS codes, selected by the owner (541110, 541618, 541620, 813910, 813920, 541990, 541611, 813219)', 'owner-supplied architecture document 2026-11-25 09:06 MST (Sanders Ethics & Impact Collective (SEIC) — five pillars, target markets, revenue streams, ecosystem connections) — the platform’s design record', 'design brief assembled from the owner’s supplied documents (ethics-platform-design-brief-2026-11-25): the cautions on 541110, 813910/813920, and 541620 were delivered before the directive; the owner kept all three — his ruling stands', 'no entry for this platform exists in the canonical catalog, Set A, Set B, Set C, or the MASTER — it is an owner-directed addition beyond the 140, recorded as such'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Ethics & Impact Collective (SEIC) is the ethics, governance, and social impact platform — an owner-directed addition beyond the 140 repo-evidenced platforms (code-set directive 2026-11-25 09:05; architecture supplied by the owner 2026-11-25 09:06): it carries governed engagement records over ethics, governance, and social-impact engagements and program matters and declared engagement sets presented by reference only. Its designed purpose is the architecture document’s five pillars — Legal & Compliance Framework (ethics compliance audits, regulatory guidance, whistleblower protection programs, governance policy development); Strategic Consulting (corporate governance transformation, ESG strategy, DEI program implementation, ethics training and certification); Environmental & Sustainability (environmental justice assessments, climate ethics consulting, sustainability compliance, green healthcare initiatives); Professional Standards & Networks (industry ethics standards, professional certification programs, peer accountability, continuing education); Specialized Services & Impact Funding (ethics auditing, IRB consulting, grant funding for ethics initiatives, social impact measurement) — recorded exactly as designed; the designed services are recorded as the platform’s offerings and no operational capability is claimed. The platform practices no law, gives no legal advice, administers no grant, disburses no funds, issues no certification, and enrolls no member: practice_law, provide_legal_advice, administer_grant, disburse_funds, issue_certification, enroll_member, and external_execution are refused by name under SEIC_RECORDS_ONLY, and determinations are records for human operators, never operations. A record declared with no engagements stands NO_ENGAGEMENTS_SUBMITTED and no determination can be recorded on it. NAICS — the owner’s selection, recorded exactly: 541110, 541618, 541620, 813910, 813920, 541990, 541611, 813219. The document’s Sanders Healthcare Foundation relationship is recorded as design text only — the Foundation is NOT one of the four verified companies; the platform is not registered under it and no Foundation entity is created. BRANDING (owner direction 2026-11-25): SEIC is a headquarters-scope platform — ethics and governance is a corporate-headquarters function, like Bozly and Secretary; its associated company for the dual-seal lockup is S & G Security Inc. (Corporate Headquarters itself), so the lockup carries the headquarters seal in both positions per the watchdog/Grantwriter precedent; it sits under Sanders Corporate Headquarters in the Universal Corporate Integration structure, attached to all four companies with S & G Security Inc. as its associated company; name presentation: Sanders Ethics & Impact Collective. No designed hostname is recorded for this platform in any examined source, and no nickname or persona is designed for it. The platform holds references and workflow state only — no legal work product, no client files, no grant funds, no member records content, no credentials. No public web surface is specified in the design document, so none was built and no security internals are exposed. SEIC is distinct from Sanders Legal Helpers, Sanders Legal Services (catalog 116), Sanders Consulting (catalog 77), and Grantwriter — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the SEIC records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersEthicsImpactCollectiveDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Ethics & Impact Collective'
                ' platform carries governed records'
                ' only \u2014 it practices no law,'
                ' gives no legal advice, administers'
                ' no grant, disburses no funds,'
                ' issues no certification, and'
                ' enrolls no member itself'
                ' (SEIC_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersEthicsImpactCollectiveDenied(
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
        """Record one SEIC record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_ENGAGEMENTS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record practices no law,
        administers no grant, and disburses
        no funds."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersEthicsImpactCollectiveDenied(
                    f'A {label} is required')
        if not isinstance(engagement_refs, (list, tuple)):
            raise SandersEthicsImpactCollectiveDenied(
                'engagement_refs must be a list of references')
        if len(engagement_refs) > MAX_REFS:
            raise SandersEthicsImpactCollectiveDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in engagement_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersEthicsImpactCollectiveDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-ethics-impact-collective-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_ETHICS_IMPACT_COLLECTIVE_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    engagement_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_ethics_impact_collective_records'
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
                'SELECT * FROM sanders_ethics_impact_collective_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_ethics_impact_collective_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_ethics_impact_collective_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersEthicsImpactCollectiveDenied(
                'SEIC record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested SEIC record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersEthicsImpactCollectiveDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_ethics_impact_collective_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersEthicsImpactCollectiveDenied(
                        'SEIC record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersEthicsImpactCollectiveDenied(
                        f"Cannot {action} a SEIC record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_ETHICS_IMPACT_COLLECTIVE_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_ethics_impact_collective_records SET status = ?,'
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
                'SELECT * FROM sanders_ethics_impact_collective_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SEIC_POSITION_CONFIRMED or ENGAGEMENT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_ENGAGEMENTS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersEthicsImpactCollectiveDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersEthicsImpactCollectiveDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_ethics_impact_collective_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersEthicsImpactCollectiveDenied(
                        'SEIC record not found')
                if row['status'] != 'APPROVED':
                    raise SandersEthicsImpactCollectiveDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" SEIC records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['engagement_count'] == 0:
                    raise SandersEthicsImpactCollectiveDenied(
                        'NO_ENGAGEMENTS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_ETHICS_IMPACT_COLLECTIVE_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_ethics_impact_collective_records SET status = ?,'
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
                'SELECT * FROM sanders_ethics_impact_collective_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_ethics_impact_collective_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_ethics_impact_collective_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_ethics_impact_collective_records'
                ' WHERE engagement_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(engagement_count), 0) AS n'
                ' FROM sanders_ethics_impact_collective_records').fetchone()['n']
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
                    raise SandersEthicsImpactCollectiveDenied(str(exc)) from exc
                self._record('SANDERS_ETHICS_IMPACT_COLLECTIVE_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
