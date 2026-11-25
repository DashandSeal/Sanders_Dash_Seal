"""Sanders Banking Hub — the banking
operations platform.

The production build-out of the Sanders Banking
Hub design (canonical catalog row #115, Band
2D), built whole as its own platform service
over the shared RTSA foundation (RTSA Build
Program Q83).

NAME — verified before building, per the name
law: the canonical catalog (row #115) and Set C
Tier 4 name this platform **Sanders Banking
Hub** — the queue-note reading matched the
source name exactly. Set B carries NO entry
under this name (verified by direct read of the
schema and the tier pricing file), and Set A
carries no entry for this platform.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Vault" (its
embedded registry record pairs the platform as
"Sanders Banking Hub / Vault"). It is recorded
exactly as found and is not adopted as the
platform's persona, name, or identifier — and
it is not the Vault platform (catalog #22, the
MASTER Twin-Gate token authority), which is a
separate platform.

Set C's purpose text for this name — "Banking
operations, Federal Reserve capability, global
finance, trust management, grants
distribution" — is recorded verbatim as found
and is NOT the built scope beyond governed
banking-operations records: no account is
opened, no funds are held or moved, no trust is
administered, no grant is disbursed, and no
Federal Reserve capability is exercised by this
build. The designed hostname
banking-hub.sandersglobal.com (Set C registry
record) sits under the unowned parent
sandersglobal.com, so it is recorded and
nothing is served there.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — banking operations, global
finance, trust management, and grants
distribution (canonical catalog row #115; Set C
Tier 4 — the platform's only design record; Set
B carries no row). No Sanders Banking Hub
module existed in any examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Banking Hub platform's own identity and store,
carrying banking-operations records:

- **Banking records**: a subject reference (a
  banking relationship, finance program, or
  grants program under service, by reference), a
  declared set of account references, and a
  scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded
  against presented evidence (OUTCOME_RECORDED).
- **The account discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set (BANKING_POSITION_CONFIRMED
  / ACCOUNT_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no accounts stands
  NO_ACCOUNTS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no accounts were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never banking**: determinations are
  records placed before human operators. The
  platform opens no account, holds and moves no
  funds, administers no trust, and disburses no
  grants — open_account, move_funds,
  administer_trust, disburse_grants, and
  external_execution are refused by name under
  BANKING_RECORDS_ONLY. Bozly (catalog #2)
  remains the headquarters CFO and integrity
  witness; this platform claims none of that
  office, and the flagship's central Stripe
  connection remains the ecosystem's payment
  path — this platform processes no payment.
- **Reference-only discipline**: subjects and
  accounts are carried by reference only; the
  platform holds no funds, no account numbers,
  no balances, no trust instruments, and no
  live-system state — references and workflow
  state only, as across the ecosystem. No public
  or customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B row;
  no Set C registry NAICS map entry) — NO NAICS
  set is carried into the platform's built
  identity and none is invented.
- **Separation**: the Sanders Banking Hub
  platform is its own platform. It is not
  Sanders Finance (catalog #68), not Bozly
  (catalog #2), not Money Factory Legal Aid
  (catalog #7), not Grantwriter (catalog #9),
  and not the Vault (catalog #22) — identities
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
    platform_id='sanders_banking_hub',
    name='Sanders Banking Hub',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Banking operations, global finance, trust management'
DISCIPLINE = 'BANKING_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_banking_hub', 'approve_banking_hub', 'record_outcome',
    'view_banking_hub', 'view_design')
EXECUTION_OPERATIONS = ('open_account', 'move_funds',
    'administer_trust', 'disburse_grants',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('BANKING_POSITION_CONFIRMED', 'ACCOUNT_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('BANKING_POSITION_CONFIRMED', 'ACCOUNT_ACTION_REQUIRED')
MAX_REFS = 100


class SandersBankingHubDenied(Exception):
    """The requested Sanders Banking Hub operation is not
    allowed."""


class SandersBankingHubForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersBankingHubService:
    """Sanders Banking Hub: governed banking-operations records under the banking records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersBankingHubDenied(
                'Sanders Banking Hub requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_banking_hub', {
            'OPERATOR': {'SANDERS_BANKING_HUB'},
            'AUDITOR': {'SANDERS_BANKING_HUB'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_banking_hub_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    account_refs TEXT NOT NULL,
                    account_count INTEGER NOT NULL,
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
            raise SandersBankingHubForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersBankingHubForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersBankingHubForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_BANKING_HUB',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersBankingHubForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersBankingHubDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #115', 'Set C Tier 4 catalog entry (read directly) — the platform’s only design record', 'Set B: no entry under this name (verified by direct read); Set A carries no entry', 'decisions.md: no ruling names this platform; Bozly’s CFO office and the Vault identity stay separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Banking Hub is the banking operations platform: it carries governed banking-operations records over banking relationships, finance programs, and grants programs and declared account sets presented by reference only. Set C’s purpose text for this name — Banking operations, Federal Reserve capability, global finance, trust management, grants distribution — is recorded verbatim as found and is NOT the built scope: no account is opened, no funds are held or moved, no trust is administered, no grant is disbursed, and no Federal Reserve capability is exercised by this build. The platform opens no account, moves no funds, administers no trust, and disburses no grants: open_account, move_funds, administer_trust, disburse_grants, and external_execution are refused by name under BANKING_RECORDS_ONLY, and determinations are records for human operators, never banking. A record declared with no accounts stands NO_ACCOUNTS_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Vault is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier, and it is not the Vault platform (catalog 22). Set B carries NO entry under this name (verified by direct read), and Set A carries no entry for this platform. The designed hostname banking-hub.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no funds, no account numbers, no balances, no trust instruments. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Banking Hub is distinct from Sanders Finance (catalog 68), Bozly (catalog 2), Money Factory Legal Aid (catalog 7), Grantwriter (catalog 9), and the Vault (catalog 22) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the banking records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersBankingHubDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Banking Hub platform'
                ' carries banking records'
                ' only \u2014 it opens no account,'
                ' moves no funds, administers'
                ' no trust, and disburses no'
                ' grants itself'
                ' (BANKING_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersBankingHubDenied(
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
        operations = json.loads(row['account_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'account_refs': operations,
            'account_count': row['account_count'],
            'account_state': ('NO_ACCOUNTS_SUBMITTED'
                             if row['account_count'] == 0
                             else 'ACCOUNTS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, account_refs,
                      scope_ref, *, region=None):
        """Record one banking record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_ACCOUNTS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record opens no
        account, moves no funds, and
        disburses no grants."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersBankingHubDenied(
                    f'A {label} is required')
        if not isinstance(account_refs, (list, tuple)):
            raise SandersBankingHubDenied(
                'account_refs must be a list of references')
        if len(account_refs) > MAX_REFS:
            raise SandersBankingHubDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in account_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersBankingHubDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-banking-hub-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_BANKING_HUB_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    account_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_banking_hub_records'
                    ' (record_id, subject_ref, account_refs,'
                    ' account_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_banking_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_banking_hub_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_banking_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersBankingHubDenied(
                'Banking Hub record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested banking record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersBankingHubDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_banking_hub_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersBankingHubDenied(
                        'Banking Hub record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersBankingHubDenied(
                        f"Cannot {action} a banking record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_BANKING_HUB_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_banking_hub_records SET status = ?,'
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
                'SELECT * FROM sanders_banking_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (BANKING_POSITION_CONFIRMED or ACCOUNT_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_ACCOUNTS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersBankingHubDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersBankingHubDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_banking_hub_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersBankingHubDenied(
                        'Banking Hub record not found')
                if row['status'] != 'APPROVED':
                    raise SandersBankingHubDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" banking records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['account_count'] == 0:
                    raise SandersBankingHubDenied(
                        'NO_ACCOUNTS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_BANKING_HUB_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_banking_hub_records SET status = ?,'
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
                'SELECT * FROM sanders_banking_hub_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_banking_hub_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_banking_hub_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_banking_hub_records'
                ' WHERE account_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(account_count), 0) AS n'
                ' FROM sanders_banking_hub_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_accounts_submitted': no_refs,
            'accounts_declared_total': refs_total,
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
                    raise SandersBankingHubDenied(str(exc)) from exc
                self._record('SANDERS_BANKING_HUB_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
