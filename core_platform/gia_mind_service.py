"""Gaia Mind — the ethical AI and system-balance platform.

The production build-out of the Gaia Mind design
(canonical catalog row #60, Band 2D), built whole as its
own platform service over the shared RTSA foundation
(RTSA Build Program Q52).

NAME — verified before building, per the name law: the
canonical catalog (row #60) and the owner's recorded
ruling D-N2 named this platform **Gaia Mind** as then
recorded (full form per Set A: Sanders Gaia Mind). The
master grid (deploy/oracle/sanders_master_grid.json
id 5) and Set B (the schema seed row) carry the
spelling "Gai Mind" — recorded here exactly as found
and NOT adopted. NAME CORRECTED — Founder ruling
2026-11-27 13:10 MST ("It’s Gaia mind"): the name of
record is **Gaia Mind** (full form: Sanders Gaia
Mind), and this build carries the corrected name from
that ruling forward. The pre-existing registry
entry’s name was corrected in place under D-N2 (the
entry’s machine id, gai_mind, is retained as a machine
string; machine strings are not names).
PERSONA — D-N2 leaves her persona open: the sources'
persona and nickname attributions conflict and none is
ruled. NO persona is adopted, carried, or presented
anywhere in this build; the conflict is flagged in the
build's conformance and registry records as found, and
her identity here is her name and her designed role
only. Her designed hostname (gia-mind.sandersglobal.com,
Set A) sits under the unowned parent sandersglobal.com;
it is recorded as the designed address and nothing is
served there.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Ethical AI, system balance" (canonical
catalog row #60; master grid id 5) — and Set C's purpose
text for her name — "Knowledge management, AI decision
support, strategic intelligence, global knowledge
graphs" — recorded here exactly as found, as facets of
the same design record: the ethics and balance review
this platform carries is the decision-support facet of
that design, recorded as governed review records. The
grid endpoint the records carry (a Google Cloud host,
:3005) is a file claim, not a verified live check, and
the grid file is truncated at id 28; no Gaia Mind module
existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — Gaia Mind's own identity and
store, carrying ethics and system-balance review records
over subjects and review evidence presented by
reference:

- **Review records**: a subject reference (the AI
  system, decision, or process under review, by
  reference), a declared set of review-evidence
  references, and a scope reference, carried as durable,
  receipted records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's recorded
  decision, then an outcome recorded against presented
  evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded
  only for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (BALANCE_CONFIRMED / BALANCE_FINDING_RECORDED /
  INCONCLUSIVE). A record declared with no review
  evidence stands NO_EVIDENCE_SUBMITTED in every view
  and in the status tallies, and both determinations are
  refused on it — no evidence was presented to determine
  from; INCONCLUSIVE, which asserts nothing, records
  against evidence.
- **The review discipline, enforced**: Gaia Mind reviews
  and records. She overrides no decision, rebalances no
  live system, directs no AI, and modifies no knowledge
  base: a balance finding is a record placed before
  human decision-makers, never an act on any system.
  Execution operations are refused by name with the
  signal ETHICS_REVIEW_RECORDS_ONLY.
- **Reference-only discipline**: subjects and evidence
  are carried by reference only; the platform holds no
  model state, no decision stream, and no live-system
  state. (Its own record store is its own — it is not a
  window into any operational system.)
- **Separation**: Gaia Mind is its own platform. She is
  not Sanders Omniconn (oversight and coordination —
  a different designed purpose), not CHORUS (Q31), not
  Sanders AI Research or Sanders Research (D-N11 keeps
  those two separate from each other and from her), and
  not any watchdog — identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 621330,
621112, 621999, 541618, 541512, 541690 — ADOPTED_EXISTING
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
    platform_id='gia_mind',
    name='Gaia Mind',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('621330', '621112', '621999', '541618', '541512', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Ethical AI, system balance'
DISCIPLINE = 'ETHICS_REVIEW_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_review', 'approve_review', 'record_outcome',
    'view_review', 'view_design')
EXECUTION_OPERATIONS = ('override_decision', 'rebalance_system',
    'direct_ai', 'modify_knowledge_base',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('BALANCE_CONFIRMED', 'BALANCE_FINDING_RECORDED',
            'INCONCLUSIVE')
DETERMINATIONS = ('BALANCE_CONFIRMED', 'BALANCE_FINDING_RECORDED')
MAX_REFS = 100


class GiaMindDenied(Exception):
    """The requested Gaia Mind operation is not
    allowed."""


class GiaMindForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class GiaMindService:
    """Gaia Mind: governed ethics and system-balance
    review records under the ethics-review records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise GiaMindDenied(
                'Gaia Mind requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'gia_mind', {
            'OPERATOR': {'GIA_MIND'},
            'AUDITOR': {'GIA_MIND'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS gia_mind_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    review_refs TEXT NOT NULL,
                    review_count INTEGER NOT NULL,
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
            raise GiaMindForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GiaMindForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise GiaMindForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'GIA_MIND',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise GiaMindForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise GiaMindDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #60',
                'deploy/oracle/sanders_master_grid.json id 5',
                'owner ruling D-N2 (canonical-catalog'
                ' decisions)',
                'Set A baseline registry (full form Sanders'
                ' Gia Mind; designed hostname) and Set C'
                ' tier catalog (purpose facet), recorded as'
                ' found',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Gaia Mind is the ethical AI and'
                    ' system-balance platform: she carries'
                    ' ethics and balance review records over'
                    ' subjects and review evidence presented'
                    ' by reference only. She reviews and'
                    ' records \u2014 she overrides no'
                    ' decision, rebalances no live system,'
                    ' directs no AI, and modifies no'
                    ' knowledge base; a finding is a record'
                    ' placed before human decision-makers.'
                    ' Execution operations are refused by'
                    ' name with the signal'
                    ' ETHICS_REVIEW_RECORDS_ONLY. A record'
                    ' declared with no review evidence'
                    ' stands NO_EVIDENCE_SUBMITTED and no'
                    ' determination can be recorded on it.'
                    ' The name is Gaia Mind, corrected by'
                    ' the Founder’s ruling of 2026-11-27'
                    ' (13:10 MST); it stood recorded as'
                    ' Gaia Mind per owner ruling D-N2 (full'
                    ' form: Sanders Gaia Mind), and the'
                    ' "Gai Mind" spelling carried by the'
                    ' grid and Set B is recorded as found'
                    ' and is not adopted. Her persona'
                    ' is unruled under D-N2 \u2014 no persona'
                    ' is adopted, carried, or presented by'
                    ' this build. Her designed hostname'
                    ' (gia-mind.sandersglobal.com) sits'
                    ' under the unowned parent'
                    ' sandersglobal.com; it is recorded as'
                    ' the designed address and nothing is'
                    ' served there. Gaia Mind is distinct'
                    ' from Sanders Omniconn, from CHORUS,'
                    ' from Sanders AI Research and Sanders'
                    ' Research, and from the watchdogs'
                    ' \u2014 identities are never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the review
        discipline does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise GiaMindDenied(
                f'Operation {operation!r} is an execution'
                ' operation: Gaia Mind reviews and records'
                ' only and holds no authority to override a'
                ' decision, rebalance a system, direct an'
                ' AI, or modify a knowledge base'
                ' (ETHICS_REVIEW_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise GiaMindDenied(
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
        evidence = json.loads(row['review_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'review_refs': evidence,
            'review_count': row['review_count'],
            'evidence_state': ('NO_EVIDENCE_SUBMITTED'
                             if row['review_count'] == 0
                             else 'EVIDENCE_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, review_refs,
                      scope_ref, *, region=None):
        """Record one global-review record (operator only) over
        a subject and a declared set of review-evidence
        references, presented by reference. The evidence set may
        be empty — the record then stands NO_EVIDENCE_SUBMITTED,
        exactly as the evidence discipline holds, and no
        determination can be recorded on it. Recording the
        record reviews nothing live and changes nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise GiaMindDenied(
                    f'A {label} is required')
        if not isinstance(review_refs, (list, tuple)):
            raise GiaMindDenied(
                'review_refs must be a list of references')
        if len(review_refs) > MAX_REFS:
            raise GiaMindDenied(
                f'At most {MAX_REFS} evidence'
                ' references per record')
        evidence = []
        for ref in review_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise GiaMindDenied(
                    'Every evidence reference must be a'
                    ' non-empty string')
            evidence.append(ref.strip())
        now = self._now()
        record_id = f'gia-mind-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'GIA_MIND_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    review_count=len(evidence))
                db.execute(
                    'INSERT INTO gia_mind_records'
                    ' (record_id, subject_ref, review_refs,'
                    ' review_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(evidence), len(evidence),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gia_mind_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gia_mind_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gia_mind_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise GiaMindDenied(
                'Review record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested review record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise GiaMindDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM gia_mind_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise GiaMindDenied(
                        'Review record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise GiaMindDenied(
                        f"Cannot {action} a review record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'GIA_MIND_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE gia_mind_records SET status = ?,'
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
                'SELECT * FROM gia_mind_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (BALANCE_CONFIRMED or BALANCE_FINDING_RECORDED) on a
        record declared with no evidence is refused —
        NO_EVIDENCE_SUBMITTED: no evidence were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise GiaMindDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise GiaMindDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM gia_mind_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise GiaMindDenied(
                        'Review record not found')
                if row['status'] != 'APPROVED':
                    raise GiaMindDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" review records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['review_count'] == 0:
                    raise GiaMindDenied(
                        'NO_EVIDENCE_SUBMITTED: a record'
                        ' declared with no evidence cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'GIA_MIND_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE gia_mind_records SET status = ?,'
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
                'SELECT * FROM gia_mind_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM gia_mind_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM gia_mind_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM gia_mind_records'
                ' WHERE review_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(review_count), 0) AS n'
                ' FROM gia_mind_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_evidence_submitted': no_signals,
            'evidence_declared_total': signals_total,
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
                    raise GiaMindDenied(str(exc)) from exc
                self._record('GIA_MIND_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
