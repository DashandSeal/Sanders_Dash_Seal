"""Integration Agent — the bounded external execution
IT AI agent platform.

The production build-out of the Integration Agent design
(MASTER §7 IT AI Agent Matrix;
``core_platform/agent_registry.py``: "Integration Agent"
under commanding authority IT_AI_Manager_v15.0,
implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q41). Canonical catalog row #47: "Bounded external
execution under token leases" — with the catalog's own
interface note: "no lease has ever been issued."

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as recovered
or original.

RECOVERED (records only, stated exactly): the agent's
designed place in the MASTER §7 matrix — the IT AI Manager
commands the twelve agents, who "keep Sanders Dash & Seal
fully functional on a day-to-day basis under bounded
authority"; the agent descriptor in
core_platform/agent_registry.py (commanding authority
IT_AI_Manager_v15.0, INTERFACE_ONLY, external execution
disabled — the registry's own require_executable_agent
refuses every agent with AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED);
the catalog's designed role (bounded external execution
under token leases), with its note that no lease has ever
been issued; the MASTER §8 Twin-Gate step 3 — the executing
agent "uses a short-lived, uniquely signed identity lease" —
and the §9 lease law the Vault (Q3) carries: "The AI system
may execute only within the active lease boundary"; and the
IT AI Manager platform's binding of this design (Q5: work
orders record the design's INTERFACE_ONLY status; no agent
execution is claimed there). A pre-existing related
component — the read-only IntegrationAgent observer entry
in core_platform/operational_runtime.py (a read-only
observation roster; observers are maintenance functions,
not deployed services or authorization authorities) — is a
separate component; this platform does not read, wrap, or
replace it, and claims none of its operation.

REBUILT (everything executable in this module): the governed
platform below — the Integration Agent's own identity and
store, carrying integration records over integrations
presented by reference:

- **Integration records**: an integration reference, a
  declared set of bounded-operation references, an optional
  Vault lease reference, and a scope reference, carried as
  durable, receipted records with a lifecycle: REQUESTED,
  then APPROVED or REJECTED by a human operator's recorded
  decision, then an outcome recorded against presented
  evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (BOUNDED_EXECUTION_RECORDED / EXECUTION_NOT_EXECUTED /
  INCONCLUSIVE).
- **The lease discipline**: a record declared with no
  operations stands NO_OPERATIONS_SUBMITTED in every view
  and in the status tallies, and the bounded determination
  is refused on it. A record carrying no Vault lease
  reference stands NO_LEASE_BOUND, and the
  BOUNDED_EXECUTION_RECORDED determination is refused on
  it — bounded execution is recorded only where a lease
  reference and an operation set were both presented.
  EXECUTION_NOT_EXECUTED and INCONCLUSIVE, which assert no
  execution, record against evidence.
- **The Vault binding, by reference**: the lease reference
  is recorded exactly as presented — a lease identifier
  string naming a lease in the Vault's ledger. This
  platform never issues, verifies, consumes, revokes, or
  burns a lease, and never sees a lease token: the Vault
  (Q3) is the lease lifecycle platform, kept separate per
  MASTER §20. A recorded BOUNDED_EXECUTION_RECORDED
  outcome attests a reported bounded execution evidenced
  by reference; the platform itself executes nothing
  externally, calls no external system, and holds no
  endpoint, credential, or payload.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by
  name with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED — including the
  lease-execution operations (issue_lease, consume_lease),
  which belong to the Vault and to no agent.
- **Separation**: the Integration Agent is its own
  platform. It is not the IT AI Manager that commands its
  design, not the Vault whose leases it references, and
  not any other agent of the matrix — the twelve are never
  merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541511,
541512, 518210, 541519, 541513, 541690 — ADOPTED_EXISTING
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

from .agent_registry import require_registered_agent
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
    platform_id='integration_agent',
    name='Integration Agent',
    legal_entities=(),
    naics_codes=('541511', '541512', '518210', '541519', '541513', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Integration Agent')
DESIGNED_ROLE = 'Bounded external execution under token leases'
RECORD_OPERATIONS = (
    'record_integration', 'approve_integration',
    'record_outcome', 'view_integration', 'view_design',
)
EXECUTION_OPERATIONS = (
    'execute_external', 'call_external_system', 'issue_lease',
    'consume_lease', 'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('BOUNDED_EXECUTION_RECORDED',
            'EXECUTION_NOT_EXECUTED', 'INCONCLUSIVE')
DETERMINATIONS = ('BOUNDED_EXECUTION_RECORDED',)
MAX_OPERATION_REFS = 100


class IntegrationAgentDenied(Exception):
    """The requested Integration Agent operation is not
    allowed."""


class IntegrationAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class IntegrationAgentService:
    """Integration Agent: governed integration records under
    the agent design's INTERFACE_ONLY discipline, with the
    designed Vault lease binding carried by reference."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise IntegrationAgentDenied(
                'Integration Agent requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'integration_agent', {
            'OPERATOR': {'INTEGRATION'},
            'AUDITOR': {'INTEGRATION'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS integration_records (
                    record_id TEXT PRIMARY KEY,
                    integration_ref TEXT NOT NULL,
                    operation_refs TEXT NOT NULL,
                    operation_count INTEGER NOT NULL,
                    vault_lease_ref TEXT,
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
            raise IntegrationAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise IntegrationAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise IntegrationAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'INTEGRATION', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise IntegrationAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise IntegrationAgentDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': DESIGN.name,
            'commanding_authority': DESIGN.commanding_authority,
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'designed_role': DESIGNED_ROLE,
            'record_operations': list(RECORD_OPERATIONS),
            'lease_binding': 'core_platform.vault (Q3 Vault),'
                             ' by reference only',
            'note': 'The platform carries integration records'
                    ' over integrations presented by reference'
                    ' only: it executes nothing externally,'
                    ' calls no external system, and holds no'
                    ' endpoint, credential, or payload. The'
                    ' agent design is INTERFACE_ONLY with'
                    ' external execution disabled — execution'
                    ' operations are refused by name with the'
                    ' design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED,'
                    ' including issue_lease and consume_lease:'
                    ' the Vault is the lease lifecycle platform'
                    ' and no agent issues or consumes leases. A'
                    ' record declared with no operations stands'
                    ' NO_OPERATIONS_SUBMITTED, and a record'
                    ' carrying no Vault lease reference stands'
                    ' NO_LEASE_BOUND; the'
                    ' BOUNDED_EXECUTION_RECORDED determination'
                    ' is refused on both — it records only'
                    ' where a lease reference and an operation'
                    ' set were both presented, and it attests a'
                    ' reported bounded execution evidenced by'
                    ' reference. The lease reference is'
                    ' recorded exactly as presented; this'
                    ' platform never issues, verifies, consumes,'
                    ' revokes, or burns a lease and never sees'
                    ' a lease token. The read-only'
                    ' IntegrationAgent observer entry in'
                    ' core_platform/operational_runtime.py is a'
                    ' separate pre-existing component — this'
                    ' platform does not read, wrap, or replace'
                    ' it. The Integration Agent is distinct'
                    ' from the IT AI Manager, from the Vault,'
                    ' and from every other agent of the matrix'
                    ' — the twelve are never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the INTERFACE_ONLY
        design does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise IntegrationAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Integration Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise IntegrationAgentDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'implementation_status': DESIGN.implementation_status,
            'external_execution_enabled':
                DESIGN.external_execution_enabled,
            'commanding_authority': DESIGN.commanding_authority,
        }

    # -- records ----------------------------------------------------------

    @staticmethod
    def _record_view(row):
        operations = json.loads(row['operation_refs'])
        return {
            'record_id': row['record_id'],
            'integration_ref': row['integration_ref'],
            'operation_refs': operations,
            'operation_count': row['operation_count'],
            'operation_state': (
                'NO_OPERATIONS_SUBMITTED'
                if row['operation_count'] == 0
                else 'OPERATIONS_SUBMITTED'),
            'vault_lease_ref': row['vault_lease_ref'],
            'lease_state': (
                'LEASE_BOUND'
                if row['vault_lease_ref'] is not None
                else 'NO_LEASE_BOUND'),
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

    def create_record(self, actor, integration_ref, operation_refs,
                      scope_ref, *, vault_lease_ref=None,
                      region=None):
        """Record one integration record (operator only) over
        an integration and a declared set of bounded
        operations, presented by reference, with an optional
        Vault lease reference binding the record to a lease
        in the Vault's ledger — by reference only: the lease
        identifier is recorded exactly as presented and is
        never verified or consumed here. The operation set
        may be empty — the record then stands
        NO_OPERATIONS_SUBMITTED — and the lease reference may
        be absent — the record then stands NO_LEASE_BOUND;
        in either case the bounded determination cannot be
        recorded on it, exactly as the lease discipline
        holds. Recording the record executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('integration_ref', integration_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise IntegrationAgentDenied(f'A {label} is required')
        if not isinstance(operation_refs, (list, tuple)):
            raise IntegrationAgentDenied(
                'operation_refs must be a list of references')
        if len(operation_refs) > MAX_OPERATION_REFS:
            raise IntegrationAgentDenied(
                f'At most {MAX_OPERATION_REFS} operation'
                ' references per record')
        operations = []
        for ref in operation_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise IntegrationAgentDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        lease_ref = None
        if vault_lease_ref is not None:
            if not isinstance(vault_lease_ref, str) \
                    or not vault_lease_ref.strip():
                raise IntegrationAgentDenied(
                    'A vault_lease_ref, when presented, must be'
                    ' a non-empty lease reference')
            lease_ref = vault_lease_ref.strip()
        now = self._now()
        record_id = f'integration-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'INTEGRATION_AGENT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    integration_ref=integration_ref.strip(),
                    operation_count=len(operations),
                    lease_bound=lease_ref is not None)
                db.execute(
                    'INSERT INTO integration_records (record_id,'
                    ' integration_ref, operation_refs,'
                    ' operation_count, vault_lease_ref, scope_ref,'
                    ' status, outcome, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?, ?)',
                    (record_id, integration_ref.strip(),
                     json.dumps(operations), len(operations),
                     lease_ref, scope_ref.strip(), 'REQUESTED',
                     None, None, actor, now, actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM integration_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM integration_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM integration_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        if row is None:
            raise IntegrationAgentDenied(
                'Integration record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested integration record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no execution and binds no
        lease."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise IntegrationAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM integration_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise IntegrationAgentDenied(
                        'Integration record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise IntegrationAgentDenied(
                        f"Cannot {action} an integration record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'INTEGRATION_AGENT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE integration_records SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (new_status, actor, now, receipt_id, record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM integration_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved integration record's outcome
        (operator only), against a presented evidence
        reference. An outcome without evidence is refused.
        The bounded determination
        (BOUNDED_EXECUTION_RECORDED) is refused on a record
        declared with no operations (NO_OPERATIONS_SUBMITTED)
        and on a record carrying no Vault lease reference
        (NO_LEASE_BOUND): bounded execution is recorded only
        where a lease reference and an operation set were
        both presented. Recording the outcome executes
        nothing — it attests a reported bounded execution
        evidenced by reference."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise IntegrationAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise IntegrationAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM integration_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise IntegrationAgentDenied(
                        'Integration record not found')
                if row['status'] != 'APPROVED':
                    raise IntegrationAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" integration records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['operation_count'] == 0:
                    raise IntegrationAgentDenied(
                        'NO_OPERATIONS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                if outcome in DETERMINATIONS \
                        and row['vault_lease_ref'] is None:
                    raise IntegrationAgentDenied(
                        'NO_LEASE_BOUND: a record carrying no'
                        ' Vault lease reference cannot be'
                        f' determined {outcome} — bounded'
                        ' execution is recorded only under a'
                        ' presented lease reference')
                receipt_id = self._record(
                    'INTEGRATION_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE integration_records SET status = ?,'
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
                'SELECT * FROM integration_records'
                ' WHERE record_id = ?', (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM integration_records GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM integration_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_operations = db.execute(
                'SELECT COUNT(*) AS n FROM integration_records'
                ' WHERE operation_count = 0').fetchone()['n']
            operations_total = db.execute(
                'SELECT COALESCE(SUM(operation_count), 0) AS n'
                ' FROM integration_records').fetchone()['n']
            lease_bound = db.execute(
                'SELECT COUNT(*) AS n FROM integration_records'
                ' WHERE vault_lease_ref IS NOT NULL'
            ).fetchone()['n']
            no_lease = db.execute(
                'SELECT COUNT(*) AS n FROM integration_records'
                ' WHERE vault_lease_ref IS NULL').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_operations_submitted': no_operations,
            'operations_declared_total': operations_total,
            'records_lease_bound': lease_bound,
            'records_no_lease_bound': no_lease,
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
                    raise IntegrationAgentDenied(str(exc)) from exc
                self._record('INTEGRATION_AGENT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
