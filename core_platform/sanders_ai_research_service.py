"""Sanders AI Research — the AI research
and development platform.

The production build-out of the Sanders AI
Research design (canonical catalog row #110,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q80).

NAME — verified before building, per the name
law: the canonical catalog (row #110), Set B,
and Set C Tier 3 all name this platform
**Sanders AI Research** — the queue-note reading
matched the source name exactly. Set A carries
no entry for this platform.

PERSONA FORMS — RECORDED, NEITHER ADOPTED: Set
B's persona column names "Think Tank"; Set C's
nickname is "AI Labs" (its embedded registry
record pairs the platform as "Sanders AI
Research / Labs"). The two forms differ; both
are recorded exactly as found, and neither is
adopted as the platform's persona, name, or
identifier.

Set C's purpose text for this name — "AI
research & development, Nobel-level research,
proprietary algorithms, breakthrough AI" — is
recorded verbatim as found and is NOT the built
scope beyond governed AI-research records: no
research is conducted, no algorithm developed,
no findings published, and no model trained by
this build; the "Nobel-level" wording is
design-record language, not a claim. The
designed hostname ai-research.sandersglobal.com
(Set C registry record) sits under the unowned
parent sandersglobal.com, so it is recorded and
nothing is served there.

TWO PLATFORMS — D-N11 HELD: the owner's
decisions record rules that Sanders Research
and Sanders AI Research are TWO platforms.
This build carries only the catalog #110
identity (AI research & development); Sanders
Research (catalog #111 — medical research,
clinical trials, pharmaceutical R&D; Set B
persona "Insight") is a separate platform, not
built here, and nothing is merged.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — AI research & development
and proprietary algorithms (canonical catalog
row #110; Set C Tier 3; the Set B schema seed
carries the platform at the professional tier).
No Sanders AI Research module existed in any
examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders AI
Research platform's own identity and store,
carrying AI-research records:

- **Research records**: a subject reference (a
  research question, study program, or algorithm
  investigation under service, by reference), a
  declared set of study references, and a scope
  reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **The study discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set (RESEARCH_POSITION_CONFIRMED
  / STUDY_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no studies stands
  NO_STUDIES_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no studies were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never research**: determinations
  are records placed before human operators. The
  platform conducts no research, develops no
  algorithm, publishes no findings, and trains
  no model — conduct_research, develop_algorithm,
  publish_findings, train_model, and
  external_execution are refused by name under
  AI_RESEARCH_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  studies are carried by reference only; the
  platform holds no research data, no model
  weights, no proprietary algorithm content, and
  no live-system state — references and workflow
  state only, as across the ecosystem. No public
  or customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: Set B attests a single code
  (541715). No owner ruling assigns a set, and
  the canonical catalog row carries none — NO
  NAICS set is carried into the platform's built
  identity; the attested code stands recorded as
  found and unruled.
- **Separation**: the Sanders AI Research
  platform is its own platform. It is not
  Sanders Research (catalog #111, D-N11), not
  Sanders Innovation Lab (catalog #119), not
  Sanders Big Data Mind (catalog #93), and not
  Sanders Analytics (catalog #118) — identities
  are never merged.

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
    platform_id='sanders_ai_research',
    name='Sanders AI Research',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'AI research & development, proprietary algorithms'
DISCIPLINE = 'AI_RESEARCH_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_ai_research', 'approve_ai_research', 'record_outcome',
    'view_ai_research', 'view_design')
EXECUTION_OPERATIONS = ('conduct_research', 'develop_algorithm',
    'publish_findings', 'train_model',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('RESEARCH_POSITION_CONFIRMED', 'STUDY_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('RESEARCH_POSITION_CONFIRMED', 'STUDY_ACTION_REQUIRED')
MAX_REFS = 100


class SandersAIResearchDenied(Exception):
    """The requested Sanders AI Research operation is not
    allowed."""


class SandersAIResearchForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersAIResearchService:
    """Sanders AI Research: governed AI research records under the AI research records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersAIResearchDenied(
                'Sanders AI Research requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_ai_research', {
            'OPERATOR': {'SANDERS_AI_RESEARCH'},
            'AUDITOR': {'SANDERS_AI_RESEARCH'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_ai_research_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    study_refs TEXT NOT NULL,
                    study_count INTEGER NOT NULL,
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
            raise SandersAIResearchForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersAIResearchForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersAIResearchForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_AI_RESEARCH',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersAIResearchForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersAIResearchDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #110', 'Set B schema seed row (read directly)', 'Set C Tier 3 catalog entry (read directly); Set A carries no entry', 'decisions.md D-N11: Sanders Research and Sanders AI Research are two platforms'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders AI Research is the AI research and development platform: it carries governed AI-research records over research questions, study programs, and algorithm investigations and declared study sets presented by reference only. Set C’s purpose text for this name — AI research & development, Nobel-level research, proprietary algorithms, breakthrough AI — is recorded verbatim as found and is NOT the built scope: no research is conducted, no algorithm developed, no findings published, and no model trained by this build; the Nobel-level wording is design-record language, not a claim. The platform conducts no research, develops no algorithm, publishes no findings, and trains no model: conduct_research, develop_algorithm, publish_findings, train_model, and external_execution are refused by name under AI_RESEARCH_RECORDS_ONLY, and determinations are records for human operators, never research. A record declared with no studies stands NO_STUDIES_SUBMITTED and no determination can be recorded on it. PERSONA FORMS — RECORDED, NEITHER ADOPTED: Set B’s persona Think Tank and Set C’s nickname AI Labs differ; both are recorded exactly as found and neither is adopted as the platform’s persona, name, or identifier. TWO PLATFORMS — D-N11 HELD: Sanders Research (catalog 111) is a separate platform and nothing is merged. Set A carries no entry for this platform. The designed hostname ai-research.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its attested NAICS code (Set B, 541715) is recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no research data, no model weights, no proprietary algorithm content. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders AI Research is distinct from Sanders Research (catalog 111), Sanders Innovation Lab (catalog 119), Sanders Big Data Mind (catalog 93), and Sanders Analytics (catalog 118) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the AI research records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersAIResearchDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders AI Research platform'
                ' carries AI research records'
                ' only \u2014 it conducts no research,'
                ' develops no algorithm, publishes'
                ' no findings, and trains no model'
                ' itself'
                ' (AI_RESEARCH_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersAIResearchDenied(
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
        operations = json.loads(row['study_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'study_refs': operations,
            'study_count': row['study_count'],
            'study_state': ('NO_STUDIES_SUBMITTED'
                             if row['study_count'] == 0
                             else 'STUDIES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, study_refs,
                      scope_ref, *, region=None):
        """Record one AI research record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_STUDIES_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record conducts no
        research, develops no algorithm, and
        trains no model."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersAIResearchDenied(
                    f'A {label} is required')
        if not isinstance(study_refs, (list, tuple)):
            raise SandersAIResearchDenied(
                'study_refs must be a list of references')
        if len(study_refs) > MAX_REFS:
            raise SandersAIResearchDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in study_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersAIResearchDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-ai-research-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_AI_RESEARCH_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    study_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_ai_research_records'
                    ' (record_id, subject_ref, study_refs,'
                    ' study_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_ai_research_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_ai_research_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_ai_research_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersAIResearchDenied(
                'AI Research record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested AI research record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersAIResearchDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_ai_research_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersAIResearchDenied(
                        'AI Research record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersAIResearchDenied(
                        f"Cannot {action} a AI research record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_AI_RESEARCH_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_ai_research_records SET status = ?,'
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
                'SELECT * FROM sanders_ai_research_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (RESEARCH_POSITION_CONFIRMED or STUDY_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_STUDIES_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersAIResearchDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersAIResearchDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_ai_research_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersAIResearchDenied(
                        'AI Research record not found')
                if row['status'] != 'APPROVED':
                    raise SandersAIResearchDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" AI research records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['study_count'] == 0:
                    raise SandersAIResearchDenied(
                        'NO_STUDIES_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_AI_RESEARCH_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_ai_research_records SET status = ?,'
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
                'SELECT * FROM sanders_ai_research_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_ai_research_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_ai_research_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_ai_research_records'
                ' WHERE study_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(study_count), 0) AS n'
                ' FROM sanders_ai_research_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_studies_submitted': no_refs,
            'studies_declared_total': refs_total,
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
                    raise SandersAIResearchDenied(str(exc)) from exc
                self._record('SANDERS_AI_RESEARCH_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
