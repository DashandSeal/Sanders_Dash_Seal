"""Deployment Agent — the deployment IT AI agent platform.

The production build-out of the Deployment Agent design
(MASTER §7 IT AI Agent Matrix; ``core_platform/agent_registry.py``:
"Deployment Agent" under commanding authority
IT_AI_Manager_v15.0, implementation_status INTERFACE_ONLY,
external_execution_enabled False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q39). Canonical catalog row #45: "Executes
deployments; on MINOTAUR denial must move to a known-safe
failover path" — with the catalog's own interface note that
deployments run via GitHub Actions + owner-gated workflows.

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
the catalog's designed role (executes deployments; on
MINOTAUR denial must move to a known-safe failover path);
the MASTER §10 MINOTAUR-Denied Failover Rule — "MINOTAUR
denial = no token, no bypass, no retry with broader
privileges. The Deployment Agent must move to a known-safe
failover/containment path rather than attempt to work around
MINOTAUR," with its required failover sequence (freeze
requested action → preserve current state → isolate
threat-affected integration → activate known-safe failover
route → Quality Agent validates functionality → MINOTAUR
rechecks shield integrity → Glass-Box Audit preserves full
record → IT AI Manager reconciles system state); and the IT
AI Manager platform's binding of this design (Q5: work orders
record the design's INTERFACE_ONLY status; no agent execution
is claimed there). A pre-existing related component — the
read-only DeploymentAgent observer entry in
core_platform/operational_runtime.py (a read-only observation
roster; observers are maintenance functions, not deployed
services or authorization authorities) — is a separate
component; this platform does not read, wrap, or replace it,
and claims none of its operation. Actual deployments in this
ecosystem run through GitHub Actions and the owner's gated
workflows; this platform performs none of them.

REBUILT (everything executable in this module): the governed
platform below — the Deployment Agent's own identity and
store, carrying deployment records over deployments
presented by reference:

- **Deployment records**: a deployment-target reference, a
  declared set of change references, and a scope reference,
  carried as durable, receipted records with a lifecycle:
  REQUESTED, then APPROVED or REJECTED by a human operator's
  recorded decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The evidence discipline**: outcomes are recorded only
  for APPROVED records and only against a presented evidence
  reference, with a closed outcome set
  (DEPLOYMENT_PATH_CLEARED / FAILOVER_PATH_RECORDED /
  INCONCLUSIVE). A record declared with no changes stands
  NO_CHANGES_SUBMITTED in every view and in the status
  tallies, and both determinations are refused on it — no
  change set was presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against evidence.
- **The §10 failover rule, as a governed record flow**: a
  MINOTAUR denial is recorded against an APPROVED record as
  a presented denial reference (this platform does not
  consult MINOTAUR — RTSA Minotaur, Q9, is a separate
  platform; the denial enters here by reference, exactly as
  evidence does). Once a denial stands on a record, the
  DEPLOYMENT_PATH_CLEARED determination is refused on it —
  denial means no proceed and no bypass — and the record's
  only determination path is the failover sequence: the
  eight designed steps, recorded in the designed order, each
  against a presented evidence reference. The
  FAILOVER_PATH_RECORDED outcome is refused until a denial
  stands and all eight steps are recorded
  (FAILOVER_INCOMPLETE). Recording the sequence performs
  none of it: no action is frozen, no route is activated,
  and no deployment is executed, moved, or rolled back —
  the failover exists here as the governed record the
  design requires, consumed by reference.
- **The design boundary, enforced**: the design is
  INTERFACE_ONLY with external execution disabled. An
  operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry
  (RECORD_ONLY) or an execution operation it refuses by name
  with the design's own signal,
  AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. This platform
  deploys nothing, rolls back nothing, bypasses nothing,
  and executes nothing.
- **Reference-only discipline**: deployments, changes,
  denials, and failover steps are carried by reference only;
  the platform holds no artifacts, no credentials, and no
  live-system state.
- **Separation**: the Deployment Agent is its own platform.
  It is not the IT AI Manager that commands its design, not
  RTSA Minotaur whose denials it records by reference, not
  the Quality Agent whose validation is one recorded step
  of the sequence, and not any other agent of the matrix —
  the twelve are never merged.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.
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
    platform_id='deployment_agent',
    name='Deployment Agent',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGN = require_registered_agent('Deployment Agent')
DESIGNED_ROLE = ('Executes deployments; on MINOTAUR denial must'
                 ' move to a known-safe failover path')
RECORD_OPERATIONS = (
    'record_deployment', 'approve_deployment', 'record_denial',
    'record_failover_step', 'record_outcome', 'view_deployment',
    'view_design',
)
EXECUTION_OPERATIONS = (
    'execute_deployment', 'perform_deployment',
    'rollback_deployment', 'bypass_minotaur',
    'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('DEPLOYMENT_PATH_CLEARED', 'FAILOVER_PATH_RECORDED',
            'INCONCLUSIVE')
DETERMINATIONS = ('DEPLOYMENT_PATH_CLEARED',
                  'FAILOVER_PATH_RECORDED')
FAILOVER_STEPS = (
    'FREEZE_REQUESTED_ACTION',
    'PRESERVE_CURRENT_STATE',
    'ISOLATE_THREAT_AFFECTED_INTEGRATION',
    'ACTIVATE_KNOWN_SAFE_FAILOVER_ROUTE',
    'QUALITY_AGENT_VALIDATION',
    'MINOTAUR_RECHECK',
    'GLASS_BOX_RECORD_PRESERVED',
    'IT_MANAGER_RECONCILIATION',
)
MAX_CHANGE_REFS = 100


class DeploymentAgentDenied(Exception):
    """The requested Deployment Agent operation is not allowed."""


class DeploymentAgentForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class DeploymentAgentService:
    """Deployment Agent: governed deployment records under the
    agent design's INTERFACE_ONLY discipline, with the MASTER
    §10 MINOTAUR-denial failover sequence carried as a
    governed record flow."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise DeploymentAgentDenied(
                'Deployment Agent requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'deployment_agent', {
            'OPERATOR': {'DEPLOYMENT'},
            'AUDITOR': {'DEPLOYMENT'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS deployment_records (
                    record_id TEXT PRIMARY KEY,
                    target_ref TEXT NOT NULL,
                    change_refs TEXT NOT NULL,
                    change_count INTEGER NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    evidence_ref TEXT,
                    denial_ref TEXT,
                    denial_recorded_by TEXT,
                    denial_recorded_at REAL,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deployment_failover_steps (
                    record_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL,
                    PRIMARY KEY (record_id, step_index)
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
            raise DeploymentAgentForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise DeploymentAgentForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise DeploymentAgentForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'DEPLOYMENT', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise DeploymentAgentForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise DeploymentAgentDenied(str(exc)) from exc

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
            'failover_steps': list(FAILOVER_STEPS),
            'note': 'The platform carries deployment records over'
                    ' deployments presented by reference only: it'
                    ' deploys nothing, rolls back nothing, and'
                    ' executes nothing. The agent design is'
                    ' INTERFACE_ONLY with external execution'
                    ' disabled — execution operations are'
                    ' refused by name with the design signal'
                    ' AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED. A'
                    ' record declared with no changes stands'
                    ' NO_CHANGES_SUBMITTED and no determination'
                    ' can be recorded on it. The MASTER §10'
                    ' failover rule is carried as a governed'
                    ' record flow: a MINOTAUR denial enters by'
                    ' reference (RTSA Minotaur is a separate'
                    ' platform; this platform does not consult'
                    ' it), a denial standing on a record refuses'
                    ' the DEPLOYMENT_PATH_CLEARED determination'
                    ' — no proceed, no bypass — and the'
                    ' FAILOVER_PATH_RECORDED outcome requires'
                    ' the denial and all eight designed failover'
                    ' steps recorded in order, each against a'
                    ' presented evidence reference. Recording'
                    ' the sequence performs none of it. Actual'
                    ' deployments run through GitHub Actions and'
                    ' the owner-gated workflows; the read-only'
                    ' DeploymentAgent observer entry in'
                    ' core_platform/operational_runtime.py is a'
                    ' separate pre-existing component — this'
                    ' platform does not read, wrap, or replace'
                    ' it. The Deployment Agent is distinct from'
                    ' the IT AI Manager and from every other'
                    ' agent of the matrix — the twelve are never'
                    ' merged.',
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
            raise DeploymentAgentDenied(
                f'Operation {operation!r} is an execution'
                ' operation: the Deployment Agent design is'
                ' INTERFACE_ONLY with external execution'
                ' disabled (AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED)')
        if operation not in RECORD_OPERATIONS:
            raise DeploymentAgentDenied(
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

    def _failover_steps(self, db, record_id):
        rows = db.execute(
            'SELECT * FROM deployment_failover_steps'
            ' WHERE record_id = ? ORDER BY step_index',
            (record_id,)).fetchall()
        return [{
            'step_index': row['step_index'],
            'step': row['step'],
            'evidence_ref': row['evidence_ref'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        } for row in rows]

    def _record_view(self, row, steps):
        if row['denial_ref'] is None:
            failover_state = 'NOT_REQUIRED'
        elif len(steps) == 0:
            failover_state = 'DENIAL_RECORDED'
        elif len(steps) < len(FAILOVER_STEPS):
            failover_state = 'IN_PROGRESS'
        else:
            failover_state = 'COMPLETE'
        return {
            'record_id': row['record_id'],
            'target_ref': row['target_ref'],
            'change_refs': json.loads(row['change_refs']),
            'change_count': row['change_count'],
            'change_state': (
                'NO_CHANGES_SUBMITTED'
                if row['change_count'] == 0
                else 'CHANGES_SUBMITTED'),
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'denial_ref': row['denial_ref'],
            'denial_state': (
                'MINOTAUR_DENIAL_RECORDED'
                if row['denial_ref'] is not None
                else 'NO_DENIAL_RECORDED'),
            'failover_state': failover_state,
            'failover_steps': steps,
            'failover_step_count': len(steps),
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def _view(self, db, record_id):
        row = db.execute(
            'SELECT * FROM deployment_records'
            ' WHERE record_id = ?', (record_id,)).fetchone()
        if row is None:
            return None
        return self._record_view(
            row, self._failover_steps(db, record_id))

    def create_record(self, actor, target_ref, change_refs,
                      scope_ref, *, region=None):
        """Record one deployment record (operator only) over a
        deployment target and a declared set of changes,
        presented by reference. The change set may be empty —
        the record then stands NO_CHANGES_SUBMITTED, exactly
        as the evidence discipline holds, and no determination
        can be recorded on it. Recording the record deploys
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('target_ref', target_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise DeploymentAgentDenied(f'A {label} is required')
        if not isinstance(change_refs, (list, tuple)):
            raise DeploymentAgentDenied(
                'change_refs must be a list of references')
        if len(change_refs) > MAX_CHANGE_REFS:
            raise DeploymentAgentDenied(
                f'At most {MAX_CHANGE_REFS} change'
                ' references per record')
        changes = []
        for ref in change_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise DeploymentAgentDenied(
                    'Every change reference must be a'
                    ' non-empty string')
            changes.append(ref.strip())
        now = self._now()
        record_id = f'deployment-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'DEPLOYMENT_AGENT_RECORD_RECORDED', actor=actor,
                    record_id=record_id,
                    target_ref=target_ref.strip(),
                    change_count=len(changes))
                db.execute(
                    'INSERT INTO deployment_records (record_id,'
                    ' target_ref, change_refs, change_count,'
                    ' scope_ref, status, outcome, evidence_ref,'
                    ' denial_ref, denial_recorded_by,'
                    ' denial_recorded_at, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, target_ref.strip(),
                     json.dumps(changes), len(changes),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     None, None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._view(db, record_id)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM deployment_records'
                ' ORDER BY requested_at',
            ).fetchall()
            return [self._record_view(
                row, self._failover_steps(db, row['record_id']))
                for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            view = self._view(db, record_id)
        if view is None:
            raise DeploymentAgentDenied('Deployment record not found')
        return view

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested deployment record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it deploys nothing and clears no path."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise DeploymentAgentDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM deployment_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise DeploymentAgentDenied(
                        'Deployment record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise DeploymentAgentDenied(
                        f"Cannot {action} a deployment record in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'DEPLOYMENT_AGENT_RECORD_ACTION', actor=actor,
                    record_id=record_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE deployment_records SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (new_status, actor, now, receipt_id, record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._view(db, record_id)

    def record_denial(self, actor, record_id, denial_ref, *,
                      region=None):
        """Record a MINOTAUR denial against one APPROVED
        deployment record (operator only), presented by
        reference. This platform does not consult MINOTAUR —
        the denial enters by reference, exactly as evidence
        does. Once recorded, the denial stands: the record's
        DEPLOYMENT_PATH_CLEARED determination is refused from
        here on (MASTER §10: denial = no proceed, no bypass),
        and the failover sequence is the record's only
        determination path. Recording a denial performs no
        containment and freezes no live action."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(denial_ref, str) or not denial_ref.strip():
            raise DeploymentAgentDenied(
                'A denial reference is required to record a'
                ' MINOTAUR denial')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM deployment_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise DeploymentAgentDenied(
                        'Deployment record not found')
                if row['status'] != 'APPROVED':
                    raise DeploymentAgentDenied(
                        'A MINOTAUR denial is recorded only for'
                        ' APPROVED deployment records (this one'
                        f" is {row['status']})")
                if row['denial_ref'] is not None:
                    raise DeploymentAgentDenied(
                        'MINOTAUR_DENIAL_ALREADY_RECORDED: a'
                        ' denial already stands on this record')
                receipt_id = self._record(
                    'DEPLOYMENT_AGENT_MINOTAUR_DENIAL_RECORDED',
                    actor=actor, record_id=record_id,
                    denial_ref=denial_ref.strip())
                db.execute(
                    'UPDATE deployment_records SET denial_ref = ?,'
                    ' denial_recorded_by = ?,'
                    ' denial_recorded_at = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (denial_ref.strip(), actor, now, actor, now,
                     receipt_id, record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._view(db, record_id)

    def record_failover_step(self, actor, record_id, step,
                             evidence_ref, *, region=None):
        """Record one step of the MASTER §10 failover sequence
        against a deployment record standing under a recorded
        MINOTAUR denial (operator only). Steps record in the
        designed order only — an out-of-order or repeated step
        is refused — and each step requires a presented
        evidence reference. Recording a step performs none of
        it: no action is frozen, no state is preserved by this
        platform, no route is activated."""
        self._geo(region)
        self._require_operator(actor)
        if step not in FAILOVER_STEPS:
            raise DeploymentAgentDenied(
                f'Unknown failover step: {step!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise DeploymentAgentDenied(
                'An evidence reference is required to record a'
                ' failover step')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM deployment_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise DeploymentAgentDenied(
                        'Deployment record not found')
                if row['status'] != 'APPROVED':
                    raise DeploymentAgentDenied(
                        'Failover steps are recorded only for'
                        ' APPROVED deployment records (this one'
                        f" is {row['status']})")
                if row['denial_ref'] is None:
                    raise DeploymentAgentDenied(
                        'NO_DENIAL_RECORDED: the failover'
                        ' sequence begins from a recorded'
                        ' MINOTAUR denial')
                recorded = self._failover_steps(db, record_id)
                expected = FAILOVER_STEPS[len(recorded)] \
                    if len(recorded) < len(FAILOVER_STEPS) else None
                if step != expected:
                    raise DeploymentAgentDenied(
                        'FAILOVER_STEP_OUT_OF_ORDER: the next'
                        f' step of the designed sequence is'
                        f' {expected!r}, not {step!r}')
                receipt_id = self._record(
                    'DEPLOYMENT_AGENT_FAILOVER_STEP_RECORDED',
                    actor=actor, record_id=record_id, step=step,
                    step_index=len(recorded),
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'INSERT INTO deployment_failover_steps'
                    ' (record_id, step_index, step, evidence_ref,'
                    ' recorded_by, recorded_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (record_id, len(recorded), step,
                     evidence_ref.strip(), actor, now, receipt_id),
                )
                db.execute(
                    'UPDATE deployment_records SET updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (actor, now, receipt_id, record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._view(db, record_id)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved deployment record's outcome
        (operator only), against a presented evidence
        reference. An outcome without evidence is refused. A
        determination (DEPLOYMENT_PATH_CLEARED or
        FAILOVER_PATH_RECORDED) on a record declared with no
        changes is refused — NO_CHANGES_SUBMITTED. Where a
        MINOTAUR denial stands on the record,
        DEPLOYMENT_PATH_CLEARED is refused (denial = no
        proceed, no bypass) and FAILOVER_PATH_RECORDED is the
        only determination; FAILOVER_PATH_RECORDED is refused
        until a denial stands and the full designed failover
        sequence is recorded (FAILOVER_INCOMPLETE). Recording
        an outcome deploys nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise DeploymentAgentDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise DeploymentAgentDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM deployment_records'
                    ' WHERE record_id = ?', (record_id,)).fetchone()
                if row is None:
                    raise DeploymentAgentDenied(
                        'Deployment record not found')
                if row['status'] != 'APPROVED':
                    raise DeploymentAgentDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" deployment records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['change_count'] == 0:
                    raise DeploymentAgentDenied(
                        'NO_CHANGES_SUBMITTED: a record declared'
                        ' with no changes cannot be determined'
                        f' {outcome}')
                if outcome == 'DEPLOYMENT_PATH_CLEARED' \
                        and row['denial_ref'] is not None:
                    raise DeploymentAgentDenied(
                        'MINOTAUR_DENIAL_RECORDED: a denial'
                        ' stands on this record — no proceed, no'
                        ' bypass; the failover sequence is the'
                        ' only determination path')
                if outcome == 'FAILOVER_PATH_RECORDED':
                    steps = self._failover_steps(db, record_id)
                    if row['denial_ref'] is None \
                            or len(steps) < len(FAILOVER_STEPS):
                        raise DeploymentAgentDenied(
                            'FAILOVER_INCOMPLETE: the failover'
                            ' outcome requires a recorded MINOTAUR'
                            ' denial and all'
                            f' {len(FAILOVER_STEPS)} designed'
                            ' failover steps recorded in order'
                            f' ({len(steps)} recorded)')
                receipt_id = self._record(
                    'DEPLOYMENT_AGENT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE deployment_records SET status = ?,'
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
            return self._view(db, record_id)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM deployment_records GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM deployment_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_changes = db.execute(
                'SELECT COUNT(*) AS n FROM deployment_records'
                ' WHERE change_count = 0').fetchone()['n']
            changes_total = db.execute(
                'SELECT COALESCE(SUM(change_count), 0) AS n'
                ' FROM deployment_records').fetchone()['n']
            denials = db.execute(
                'SELECT COUNT(*) AS n FROM deployment_records'
                ' WHERE denial_ref IS NOT NULL').fetchone()['n']
            steps_total = db.execute(
                'SELECT COUNT(*) AS n'
                ' FROM deployment_failover_steps').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_changes_submitted': no_changes,
            'changes_declared_total': changes_total,
            'records_minotaur_denial_recorded': denials,
            'failover_steps_recorded_total': steps_total,
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
                    raise DeploymentAgentDenied(str(exc)) from exc
                self._record('DEPLOYMENT_AGENT_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
