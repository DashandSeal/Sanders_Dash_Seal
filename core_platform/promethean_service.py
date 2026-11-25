"""PROMETHEAN — the adversarial-reasoning and red-team RTSA platform.

The production build-out of the PROMETHEAN role contract
(``core_platform/rtsa_registry.py``: canonical name "PROMETHEAN",
slug ``promethean``, mission "adversarial reasoning and red-team
evaluation", SPECIFIED, enabled: False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q27).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, and production deployment —
are refused by name, in the service, every time. This platform
performs no attack, no probe, and no execution of any kind. What
it does is the evaluation record, governed:

- **Evaluation records**: red-team exercises and adversarial
  reviews as durable, receipted records (kind, target reference,
  scenario reference) with a lifecycle: PROPOSED, then AUTHORIZED
  or REJECTED by a human operator's recorded decision, then
  findings recorded against presented evidence
  (FINDINGS_RECORDED). Authorizing a record is a recorded human
  decision about the record; any exercise itself happens outside
  this platform, under its own authority — this platform carries
  the governance record of it, never the execution.
- **Findings** are recorded only for AUTHORIZED evaluations and
  only against a presented evidence reference, with a closed
  verdict set (VULNERABILITY_CONFIRMED / NO_VULNERABILITY_FOUND /
  INCONCLUSIVE) and a closed severity set. A findings claim with
  nothing behind it is not a record.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether a
  named operation is a record operation this platform may carry
  or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one. MASTER section 20 boundaries hold: PROMETHEAN is not
Sharpshooter (remediation), not Sanders Recon, and not any
execution platform.
"""

from __future__ import annotations

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
    platform_id='promethean',
    name='PROMETHEAN',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['PROMETHEAN']
RECORD_OPERATIONS = (
    'record_evaluation', 'authorize_evaluation', 'record_findings',
    'view_evaluation', 'view_contract',
)
EVAL_KINDS = ('RED_TEAM_EXERCISE', 'ADVERSARIAL_REVIEW')
EVAL_STATUSES = ('PROPOSED', 'AUTHORIZED', 'REJECTED',
                 'FINDINGS_RECORDED')
EVAL_TRANSITIONS = {
    'approve': {'PROPOSED': 'AUTHORIZED'},
    'reject': {'PROPOSED': 'REJECTED'},
}
VERDICTS = ('VULNERABILITY_CONFIRMED', 'NO_VULNERABILITY_FOUND',
            'INCONCLUSIVE')
SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE')


class PrometheanDenied(Exception):
    """The requested PROMETHEAN operation is not allowed."""


class PrometheanForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class PrometheanService:
    """PROMETHEAN: governed red-team evaluation records under the
    role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise PrometheanDenied(
                'PROMETHEAN requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'promethean', {
            'OPERATOR': {'SECURITY'},
            'AUDITOR': {'SECURITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS prom_evaluations (
                    eval_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    scenario_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    severity TEXT,
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
            raise PrometheanForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PrometheanForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise PrometheanForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SECURITY', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise PrometheanForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise PrometheanDenied(str(exc)) from exc

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
            'note': 'The platform carries red-team evaluation'
                    ' records only: it performs no attack, no'
                    ' probe, and no execution. Authorizing an'
                    ' evaluation record is a recorded human'
                    ' decision about the record; any exercise'
                    ' itself happens outside this platform under'
                    ' its own authority. The contract remains'
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
            raise PrometheanDenied(
                f'Operation {operation!r} is prohibited by the'
                ' PROMETHEAN role contract')
        if operation not in RECORD_OPERATIONS:
            raise PrometheanDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- evaluations ----------------------------------------------------

    @staticmethod
    def _eval_view(row):
        return {
            'eval_id': row['eval_id'],
            'kind': row['kind'],
            'target_ref': row['target_ref'],
            'scenario_ref': row['scenario_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'severity': row['severity'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_evaluation(self, actor, kind, target_ref, scenario_ref,
                          *, region=None):
        """Record one evaluation proposal (operator only). The
        record proposes an evaluation governed elsewhere;
        recording it executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        if kind not in EVAL_KINDS:
            raise PrometheanDenied(
                f'Unknown evaluation kind: {kind!r}')
        for label, value in (('target_ref', target_ref),
                             ('scenario_ref', scenario_ref)):
            if not isinstance(value, str) or not value.strip():
                raise PrometheanDenied(f'A {label} is required')
        now = self._now()
        eval_id = f'prom-eval-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'PROMETHEAN_EVALUATION_RECORDED', actor=actor,
                    eval_id=eval_id, kind=kind, target_ref=target_ref)
                db.execute(
                    'INSERT INTO prom_evaluations (eval_id, kind,'
                    ' target_ref, scenario_ref, status, verdict,'
                    ' severity, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?)',
                    (eval_id, kind, target_ref.strip(),
                     scenario_ref.strip(), 'PROPOSED', None, None,
                     None, actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM prom_evaluations WHERE eval_id = ?',
                (eval_id,)).fetchone()
        return self._eval_view(row)

    def evaluations_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'evaluations',
                           'evaluations view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM prom_evaluations'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._eval_view(row) for row in rows]

    def evaluation_view(self, actor, role, eval_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, eval_id, 'evaluation view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM prom_evaluations WHERE eval_id = ?',
                (eval_id,)).fetchone()
        if row is None:
            raise PrometheanDenied('Evaluation not found')
        return self._eval_view(row)

    def evaluation_action(self, actor, eval_id, action, *,
                          region=None):
        """Authorize or reject one proposed evaluation (operator
        only) — the recorded human decision the contract
        requires. Authorization authorizes the RECORD; any
        exercise happens outside this platform."""
        self._geo(region)
        self._require_operator(actor)
        transitions = EVAL_TRANSITIONS.get(action)
        if transitions is None:
            raise PrometheanDenied(
                f'Unknown evaluation action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM prom_evaluations'
                    ' WHERE eval_id = ?',
                    (eval_id,)).fetchone()
                if row is None:
                    raise PrometheanDenied('Evaluation not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise PrometheanDenied(
                        f"Cannot {action} an evaluation in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'PROMETHEAN_EVALUATION_ACTION', actor=actor,
                    eval_id=eval_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE prom_evaluations SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE eval_id = ?',
                    (new_status, actor, now, receipt_id, eval_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM prom_evaluations WHERE eval_id = ?',
                (eval_id,)).fetchone()
        return self._eval_view(updated)

    def record_findings(self, actor, eval_id, verdict, severity,
                        evidence_ref, *, region=None):
        """Record one authorized evaluation's findings (operator
        only), against a presented evidence reference. Findings
        without evidence are refused: a vulnerability claim with
        nothing behind it is not a record."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise PrometheanDenied(f'Unknown verdict: {verdict!r}')
        if severity not in SEVERITIES:
            raise PrometheanDenied(
                f'Unknown severity: {severity!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise PrometheanDenied(
                'An evidence reference is required to record'
                ' findings')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM prom_evaluations'
                    ' WHERE eval_id = ?',
                    (eval_id,)).fetchone()
                if row is None:
                    raise PrometheanDenied('Evaluation not found')
                if row['status'] != 'AUTHORIZED':
                    raise PrometheanDenied(
                        'Findings are recorded only for AUTHORIZED'
                        f" evaluations (this one is {row['status']})")
                receipt_id = self._record(
                    'PROMETHEAN_FINDINGS_RECORDED', actor=actor,
                    eval_id=eval_id, verdict=verdict,
                    severity=severity,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE prom_evaluations SET status = ?,'
                    ' verdict = ?, severity = ?, evidence_ref = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE eval_id = ?',
                    ('FINDINGS_RECORDED', verdict, severity,
                     evidence_ref.strip(), actor, now, receipt_id,
                     eval_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM prom_evaluations WHERE eval_id = ?',
                (eval_id,)).fetchone()
        return self._eval_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in EVAL_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' prom_evaluations GROUP BY status'):
                by_status[row['status']] = row['n']
            by_kind = {k: 0 for k in EVAL_KINDS}
            for row in db.execute(
                    'SELECT kind, COUNT(*) AS n FROM'
                    ' prom_evaluations GROUP BY kind'):
                by_kind[row['kind']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'evaluations_total': sum(by_status.values()),
            'evaluations_by_status': by_status,
            'evaluations_by_kind': by_kind,
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
                    raise PrometheanDenied(str(exc)) from exc
                self._record('PROMETHEAN_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
