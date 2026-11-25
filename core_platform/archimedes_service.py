"""ARCHIMEDES #43 — the build-engineering RTSA platform.

The production build-out of the ARCHIMEDES #43 role contract
(``core_platform/rtsa_registry.py``: canonical name
"ARCHIMEDES #43", slug ``archimedes-43``, mission "build
engineering, coding, testing, deployment", SPECIFIED, enabled:
False), built whole as its own platform service over the shared
RTSA foundation (RTSA Build Program Q26).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, and production deployment
itself — are refused by name, in the service, every time. This
platform performs no build, no test run, and no deployment. What
it does is the engineering record, governed:

- **Job records**: build, test, and deployment-record jobs as
  durable, receipted records (kind, target, source reference)
  with a lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome recorded
  against presented evidence (RECORDED_COMPLETE /
  RECORDED_FAILED). An outcome without an evidence reference is
  refused — a completion claim with nothing behind it is not a
  record.
- **Deployment records** are evidence records of deployments that
  occurred through the owner's gated production path (the
  evidence reference names the run); the platform records them
  and never performs one — production deployment is a prohibited
  operation under its own contract.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether a
  named operation is a record operation this platform may carry
  or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one. MASTER section 20 boundaries hold: ARCHIMEDES #43 is not
the IT AI Manager, not TwinGate, and not the deploy path itself.
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
from .rtsa_registry import RTSA_ROLES


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='archimedes_43',
    name='ARCHIMEDES #43',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['ARCHIMEDES #43']
RECORD_OPERATIONS = (
    'record_job', 'approve_job', 'record_outcome', 'view_job',
    'view_contract',
)
JOB_KINDS = ('BUILD', 'TEST', 'DEPLOYMENT_RECORD')
JOB_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                'RECORDED_COMPLETE', 'RECORDED_FAILED')
JOB_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = {'COMPLETE': 'RECORDED_COMPLETE', 'FAILED': 'RECORDED_FAILED'}


class ArchimedesDenied(Exception):
    """The requested ARCHIMEDES #43 operation is not allowed."""


class ArchimedesForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ArchimedesService:
    """ARCHIMEDES #43: governed build-engineering records under
    the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ArchimedesDenied(
                'ARCHIMEDES #43 requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'archimedes_43', {
            'OPERATOR': {'ENGINEERING'},
            'AUDITOR': {'ENGINEERING'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS arc43_jobs (
                    job_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
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
            raise ArchimedesForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ArchimedesForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ArchimedesForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'ENGINEERING', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise ArchimedesForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ArchimedesDenied(str(exc)) from exc

    # -- contract -----------------------------------------------------

    @staticmethod
    def contract_view() -> dict:
        return {
            'canonical_name': CONTRACT.canonical_name,
            'slug': CONTRACT.slug,
            'mission': CONTRACT.mission,
            'contract_status': CONTRACT.status.value,
            'enabled': CONTRACT.enabled,
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'prohibited_operations':
                list(CONTRACT.prohibited_operations),
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The platform carries engineering records only:'
                    ' it performs no build, no test run, and no'
                    ' deployment. Deployment records are evidence'
                    " of deployments through the owner's gated"
                    ' production path. The contract remains'
                    ' SPECIFIED and enabled: False — deployment of'
                    " the intelligence is the owner's named"
                    " approval, not this build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise ArchimedesDenied(
                f'Operation {operation!r} is prohibited by the'
                ' ARCHIMEDES #43 role contract')
        if operation not in RECORD_OPERATIONS:
            raise ArchimedesDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- jobs -----------------------------------------------------------

    @staticmethod
    def _job_view(row):
        return {
            'job_id': row['job_id'],
            'kind': row['kind'],
            'target_ref': row['target_ref'],
            'source_ref': row['source_ref'],
            'status': row['status'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_job(self, actor, kind, target_ref, source_ref, *,
                   region=None):
        """Record one engineering job request (operator only). The
        job is a record of work governed elsewhere; recording it
        executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        if kind not in JOB_KINDS:
            raise ArchimedesDenied(f'Unknown job kind: {kind!r}')
        for label, value in (('target_ref', target_ref),
                             ('source_ref', source_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ArchimedesDenied(f'A {label} is required')
        now = self._now()
        job_id = f'arc43-job-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'ARCHIMEDES_JOB_RECORDED', actor=actor,
                    job_id=job_id, kind=kind, target_ref=target_ref)
                db.execute(
                    'INSERT INTO arc43_jobs (job_id, kind, target_ref,'
                    ' source_ref, status, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (job_id, kind, target_ref.strip(),
                     source_ref.strip(), 'REQUESTED', None, actor, now,
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM arc43_jobs WHERE job_id = ?',
                (job_id,)).fetchone()
        return self._job_view(row)

    def jobs_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'jobs', 'jobs view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM arc43_jobs ORDER BY requested_at',
            ).fetchall()
        return [self._job_view(row) for row in rows]

    def job_view(self, actor, role, job_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, job_id, 'job view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM arc43_jobs WHERE job_id = ?',
                (job_id,)).fetchone()
        if row is None:
            raise ArchimedesDenied('Job not found')
        return self._job_view(row)

    def job_action(self, actor, job_id, action, *, region=None):
        """Approve or reject one requested job (operator only) —
        the recorded human decision the contract requires. Approval
        approves the RECORD; it executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = JOB_TRANSITIONS.get(action)
        if transitions is None:
            raise ArchimedesDenied(f'Unknown job action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM arc43_jobs WHERE job_id = ?',
                    (job_id,)).fetchone()
                if row is None:
                    raise ArchimedesDenied('Job not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ArchimedesDenied(
                        f"Cannot {action} a job in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'ARCHIMEDES_JOB_ACTION', actor=actor, job_id=job_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE arc43_jobs SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ? WHERE job_id = ?',
                    (new_status, actor, now, receipt_id, job_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM arc43_jobs WHERE job_id = ?',
                (job_id,)).fetchone()
        return self._job_view(updated)

    def record_outcome(self, actor, job_id, outcome, evidence_ref, *,
                       region=None):
        """Record one approved job's outcome (operator only),
        against a presented evidence reference. An outcome without
        evidence is refused: a completion claim with nothing behind
        it is not a record. For a DEPLOYMENT_RECORD the evidence
        reference names the owner's gated production run the record
        attests to."""
        self._geo(region)
        self._require_operator(actor)
        new_status = OUTCOMES.get(outcome)
        if new_status is None:
            raise ArchimedesDenied(f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ArchimedesDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM arc43_jobs WHERE job_id = ?',
                    (job_id,)).fetchone()
                if row is None:
                    raise ArchimedesDenied('Job not found')
                if row['status'] != 'APPROVED':
                    raise ArchimedesDenied(
                        'Outcomes are recorded only for APPROVED jobs'
                        f" (this job is {row['status']})")
                receipt_id = self._record(
                    'ARCHIMEDES_JOB_OUTCOME', actor=actor,
                    job_id=job_id, outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE arc43_jobs SET status = ?, evidence_ref'
                    ' = ?, updated_by = ?, updated_at = ?, receipt_id'
                    ' = ? WHERE job_id = ?',
                    (new_status, evidence_ref.strip(), actor, now,
                     receipt_id, job_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM arc43_jobs WHERE job_id = ?',
                (job_id,)).fetchone()
        return self._job_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in JOB_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM arc43_jobs'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_kind = {k: 0 for k in JOB_KINDS}
            for row in db.execute(
                    'SELECT kind, COUNT(*) AS n FROM arc43_jobs'
                    ' GROUP BY kind'):
                by_kind[row['kind']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'jobs_total': sum(by_status.values()),
            'jobs_by_status': by_status,
            'jobs_by_kind': by_kind,
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
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
                    raise ArchimedesDenied(str(exc)) from exc
                self._record('ARCHIMEDES_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
