"""Sanders Legal Helpers — the legal support and
compliance platform.

The production build-out of the Sanders Legal Helpers
design (canonical catalog row #66, Band 2D), built whole
as its own platform service over the shared RTSA
foundation (RTSA Build Program Q57).

NAME — verified before building, per the name law: the
canonical catalog (row #66), the master grid
(deploy/oracle/sanders_master_grid.json id 12), the Set
B schema seed, the Set C Tier 4 section, and the
pre-existing registry record all name this platform
**Sanders Legal Helpers**. The name is also the name of
the owner's company without "LLC" — Sanders Legal
Helpers LLC — and the platform is NOT the LLC: the LLC
is the flagship's legal entity and operates via the
flagship and TwoStep (catalog rows #1 and #4); this
build is the grid platform of that name, a platform
with its own identity, store, and records, distinct
from the company itself, exactly as the owner drew the
same distinction for the Home Healthcare RTSA, the
Senior Living platform, and their LLCs. Nothing here is
merged with any company record, and no company record
is carried into the platform. Two nicknames conflict as
found — "LawAid" (the grid and the Set B seed agree)
and "Face of LLC" (Set C) — both are recorded here
exactly as found and neither is adopted as the
platform's name.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Legal support / compliance" (canonical
catalog row #66; master grid id 12); Set C's purpose
text — "Entity management, contract enforcement,
compliance monitoring, legal support" (Tier 4); Set C's
designed hostname legal.sandersglobal.com, under the
unowned parent sandersglobal.com — recorded as the
designed address, and nothing is served there. The grid
endpoint the records carry (a Google Cloud host, :3012)
is a file claim, not a verified live check, and the
grid file is truncated at id 28; no Sanders Legal
Helpers module existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Legal Helpers
platform's own identity and store, carrying
legal-support records:

- **Support records**: a subject reference (a legal
  matter or entity under support, by reference), a
  declared set of matter references, and a scope
  reference, carried as durable, receipted records with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence
  (OUTCOME_RECORDED).
- **The matter discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (LEGAL_POSITION_CONFIRMED /
  COMPLIANCE_ACTION_REQUIRED / INCONCLUSIVE). A record
  declared with no matters stands NO_MATTERS_SUBMITTED
  in every view and in the status tallies, and both
  determinations are refused on it — no matters were
  presented to determine from; INCONCLUSIVE, which
  asserts nothing, records against evidence.
- **Records, never legal operations**: determinations
  are records placed before human operators. The
  platform renders no legal advice or opinion,
  represents no client, files nothing, and enforces
  nothing — enforce_contract, file_legal_action,
  represent_client, issue_legal_opinion, and
  external_execution are refused by name under
  LEGAL_SUPPORT_RECORDS_ONLY. The platform practices
  no law.
- **Reference-only discipline**: subjects and matters
  are carried by reference only; the platform holds no
  client names, no privileged communications, no case
  content, and no live-system state — references and
  workflow state only, as across the ecosystem.
- **NAICS**: two sources attest two different sets —
  the grid (541110, 541190, 541199, 541511, 541512,
  541611, 541618, 541990) and Set B (541110, 541199). No
  owner ruling assigns a set, and the canonical catalog
  row carries none — NO NAICS set is carried into the
  platform's built identity; both sets stand recorded
  as attested and unruled.
- **Separation**: the Sanders Legal Helpers platform
  is its own platform. It is not Sanders Legal Helpers
  LLC (the company), not Sanders Legal Services
  (catalog #116), and not Sanders Dash & Seal (catalog
  #1) — identities are never merged.

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
    platform_id='sanders_legal_helpers',
    name='Sanders Legal Helpers',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Legal support / compliance'
DISCIPLINE = 'LEGAL_SUPPORT_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_support', 'approve_support', 'record_outcome',
    'view_support', 'view_design')
EXECUTION_OPERATIONS = ('enforce_contract', 'file_legal_action',
    'represent_client', 'issue_legal_opinion',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('LEGAL_POSITION_CONFIRMED', 'COMPLIANCE_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('LEGAL_POSITION_CONFIRMED', 'COMPLIANCE_ACTION_REQUIRED')
MAX_REFS = 100


class SandersLegalHelpersDenied(Exception):
    """The requested Sanders Legal Helpers operation is not
    allowed."""


class SandersLegalHelpersForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersLegalHelpersService:
    """Sanders Legal Helpers: governed legal-support and compliance records under the legal-support records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersLegalHelpersDenied(
                'Sanders Legal Helpers requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_legal_helpers', {
            'OPERATOR': {'SANDERS_LEGAL_HELPERS'},
            'AUDITOR': {'SANDERS_LEGAL_HELPERS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_legal_helpers_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    matter_refs TEXT NOT NULL,
                    matter_count INTEGER NOT NULL,
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
            raise SandersLegalHelpersForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersLegalHelpersForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersLegalHelpersForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_LEGAL_HELPERS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersLegalHelpersForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersLegalHelpersDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #66',
                'deploy/oracle/sanders_master_grid.json id 12',
                'Set B schema seed row and Set C Tier 4 section (both read directly)',
            ],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Legal Helpers is the legal support and compliance platform: it carries governed legal-support records over legal matters and entities and declared matter sets presented by reference only. The platform is not Sanders Legal Helpers LLC — the LLC is the flagship’s legal entity and operates via the flagship and TwoStep; this platform is the grid platform of that name, a distinct identity, and nothing is merged with any company record. It renders no legal advice or opinion, represents no client, files nothing, and enforces nothing: enforce_contract, file_legal_action, represent_client, issue_legal_opinion, and external_execution are refused by name under LEGAL_SUPPORT_RECORDS_ONLY, and determinations are records for human operators, never acts — the platform practices no law. A record declared with no matters stands NO_MATTERS_SUBMITTED and no determination can be recorded on it. The nicknames LawAid (grid and Set B) and Face of LLC (Set C) conflict as found; neither is adopted as the platform’s name. Set C’s designed hostname legal.sandersglobal.com sits under the unowned parent sandersglobal.com — recorded, and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no client data, no privileged communications, no case content. Sanders Legal Helpers is distinct from Sanders Legal Services (catalog #116) and from Sanders Dash & Seal (catalog #1) — identities are never merged.',
        }


    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a legal operation or an execution operation
        the legal-support records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersLegalHelpersDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Legal Helpers platform carries'
                ' legal-support records only \u2014 it'
                ' represents no client, files nothing, and'
                ' practices no law itself'
                ' (LEGAL_SUPPORT_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersLegalHelpersDenied(
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
        matters = json.loads(row['matter_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'matter_refs': matters,
            'matter_count': row['matter_count'],
            'matter_state': ('NO_MATTERS_SUBMITTED'
                             if row['matter_count'] == 0
                             else 'MATTERS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, matter_refs,
                      scope_ref, *, region=None):
        """Record one legal-support record (operator only) over
        a subject and a declared set of matter
        references, presented by reference. The matter set may
        be empty — the record then stands NO_MATTERS_SUBMITTED,
        exactly as the matter discipline holds, and no
        determination can be recorded on it. Recording the
        record enforces no contract, files nothing, and
        represents no one."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersLegalHelpersDenied(
                    f'A {label} is required')
        if not isinstance(matter_refs, (list, tuple)):
            raise SandersLegalHelpersDenied(
                'matter_refs must be a list of references')
        if len(matter_refs) > MAX_REFS:
            raise SandersLegalHelpersDenied(
                f'At most {MAX_REFS} matter'
                ' references per record')
        matters = []
        for ref in matter_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersLegalHelpersDenied(
                    'Every matter reference must be a'
                    ' non-empty string')
            matters.append(ref.strip())
        now = self._now()
        record_id = f'sanders-legal-helpers-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_LEGAL_HELPERS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    matter_count=len(matters))
                db.execute(
                    'INSERT INTO sanders_legal_helpers_records'
                    ' (record_id, subject_ref, matter_refs,'
                    ' matter_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(matters), len(matters),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_legal_helpers_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_legal_helpers_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_legal_helpers_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersLegalHelpersDenied(
                'Support record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested support record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersLegalHelpersDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_legal_helpers_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLegalHelpersDenied(
                        'Support record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersLegalHelpersDenied(
                        f"Cannot {action} a support record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_LEGAL_HELPERS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_legal_helpers_records SET status = ?,'
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
                'SELECT * FROM sanders_legal_helpers_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (LEGAL_POSITION_CONFIRMED or COMPLIANCE_ACTION_REQUIRED) on a
        record declared with no matters is refused —
        NO_MATTERS_SUBMITTED: no matters were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersLegalHelpersDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersLegalHelpersDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_legal_helpers_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersLegalHelpersDenied(
                        'Support record not found')
                if row['status'] != 'APPROVED':
                    raise SandersLegalHelpersDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" support records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['matter_count'] == 0:
                    raise SandersLegalHelpersDenied(
                        'NO_MATTERS_SUBMITTED: a record'
                        ' declared with no matters cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_LEGAL_HELPERS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_legal_helpers_records SET status = ?,'
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
                'SELECT * FROM sanders_legal_helpers_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_legal_helpers_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_legal_helpers_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_legal_helpers_records'
                ' WHERE matter_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(matter_count), 0) AS n'
                ' FROM sanders_legal_helpers_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_matters_submitted': no_refs,
            'matters_declared_total': refs_total,
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
                    raise SandersLegalHelpersDenied(str(exc)) from exc
                self._record('SANDERS_LEGAL_HELPERS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
