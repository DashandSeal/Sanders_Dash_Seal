"""LABYRINTH — the zero-trust and attack-path security RTSA.

The production build-out of the LABYRINTH role contract
(``core_platform/rtsa_registry.py``: canonical name "LABYRINTH",
slug ``labyrinth``, mission "zero-trust and attack-path
security", SPECIFIED, enabled: False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q29).

Identity discipline (MASTER section 5 / section 20, catalog
decision D-N8): LABYRINTH is a SEPARATE platform from Sanders
Labyrinth Shield (the real-time defensive perimeter environment,
queue Q8) and from RTSA Minotaur (the patrol that certifies the
Shield's safety, queue Q9). The Shield enforces; the Minotaur
patrols; LABYRINTH analyzes. The three are never merged, and this
module imports neither of them.

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, and production deployment —
are refused by name, in the service, every time. This platform
performs no scan, no probe, and no enforcement. What it does is
the attack-path analysis record, governed:

- **Analysis records**: attack-path analyses over declared
  system models, carried as durable, receipted records (subject
  reference, declared entry-point reference, target reference,
  scope reference) with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then a
  result recorded against presented evidence (RESULT_RECORDED).
  The analysis reasons over the declared model an operator
  presents by reference; it does not reach into any live system.
- **Results** are recorded only for APPROVED analyses and only
  against a presented evidence reference, with a closed verdict
  set (PATH_EXISTS / NO_PATH_WITHIN_SCOPE / INCONCLUSIVE) —
  NO_PATH_WITHIN_SCOPE is scoped to the declared model and scope
  by construction, never a claim about a live environment.
- **Zero-trust discipline**: no analysis result is inherited,
  assumed, or carried over — every subject is analyzed on its own
  recorded approval, and a result binds only to the analysis,
  model, and scope it names.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether a
  named operation is a record operation this platform may carry
  or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one.
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
    platform_id='labyrinth',
    name='LABYRINTH',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['LABYRINTH']
RECORD_OPERATIONS = (
    'record_analysis', 'approve_analysis', 'record_result',
    'view_analysis', 'view_contract',
)
ANALYSIS_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                     'RESULT_RECORDED')
ANALYSIS_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
VERDICTS = ('PATH_EXISTS', 'NO_PATH_WITHIN_SCOPE', 'INCONCLUSIVE')


class LabyrinthDenied(Exception):
    """The requested LABYRINTH operation is not allowed."""


class LabyrinthForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class LabyrinthService:
    """LABYRINTH: governed attack-path analysis records under
    the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise LabyrinthDenied(
                'LABYRINTH requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'labyrinth', {
            'OPERATOR': {'SECURITY'},
            'AUDITOR': {'SECURITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS lab_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    entry_ref TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
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
            raise LabyrinthForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise LabyrinthForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise LabyrinthForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SECURITY', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise LabyrinthForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise LabyrinthDenied(str(exc)) from exc

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
            'note': 'The platform carries attack-path analysis'
                    ' records over declared models only: it'
                    ' performs no scan, no probe, and no'
                    ' enforcement, and a NO_PATH_WITHIN_SCOPE'
                    ' verdict binds only to the declared model and'
                    ' scope it names. LABYRINTH is a separate'
                    ' platform from Sanders Labyrinth Shield (the'
                    ' defensive perimeter) and from RTSA Minotaur'
                    ' (its patrol) — the three are never merged.'
                    ' The contract remains SPECIFIED and enabled:'
                    " False — deployment of the intelligence is"
                    " the owner's named approval, not this"
                    " build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise LabyrinthDenied(
                f'Operation {operation!r} is prohibited by the'
                ' LABYRINTH role contract')
        if operation not in RECORD_OPERATIONS:
            raise LabyrinthDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- analyses -------------------------------------------------------

    @staticmethod
    def _analysis_view(row):
        return {
            'analysis_id': row['analysis_id'],
            'subject_ref': row['subject_ref'],
            'entry_ref': row['entry_ref'],
            'target_ref': row['target_ref'],
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_analysis(self, actor, subject_ref, entry_ref,
                        target_ref, scope_ref, *, region=None):
        """Record one attack-path analysis request (operator
        only) over a declared model, presented by reference. The
        record governs the analysis; recording it scans nothing
        and reaches into no live system."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('entry_ref', entry_ref),
                             ('target_ref', target_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise LabyrinthDenied(f'A {label} is required')
        now = self._now()
        analysis_id = f'lab-analysis-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_ANALYSIS_RECORDED', actor=actor,
                    analysis_id=analysis_id,
                    subject_ref=subject_ref.strip(),
                    target_ref=target_ref.strip())
                db.execute(
                    'INSERT INTO lab_analyses (analysis_id,'
                    ' subject_ref, entry_ref, target_ref, scope_ref,'
                    ' status, verdict, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?)',
                    (analysis_id, subject_ref.strip(),
                     entry_ref.strip(), target_ref.strip(),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(row)

    def analyses_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'analyses', 'analyses view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM lab_analyses ORDER BY requested_at',
            ).fetchall()
        return [self._analysis_view(row) for row in rows]

    def analysis_view(self, actor, role, analysis_id, *,
                      region=None):
        self._geo(region)
        self._guard_access(actor, role, analysis_id, 'analysis view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        if row is None:
            raise LabyrinthDenied('Analysis not found')
        return self._analysis_view(row)

    def analysis_action(self, actor, analysis_id, action, *,
                        region=None):
        """Approve or reject one requested analysis (operator
        only) — the recorded human decision the contract
        requires. Approval approves the RECORD; it executes
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ANALYSIS_TRANSITIONS.get(action)
        if transitions is None:
            raise LabyrinthDenied(
                f'Unknown analysis action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lab_analyses'
                    ' WHERE analysis_id = ?',
                    (analysis_id,)).fetchone()
                if row is None:
                    raise LabyrinthDenied('Analysis not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise LabyrinthDenied(
                        f"Cannot {action} an analysis in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'LABYRINTH_ANALYSIS_ACTION', actor=actor,
                    analysis_id=analysis_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE lab_analyses SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE analysis_id = ?',
                    (new_status, actor, now, receipt_id, analysis_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(updated)

    def record_result(self, actor, analysis_id, verdict,
                      evidence_ref, *, region=None):
        """Record one approved analysis's result (operator only),
        against a presented evidence reference. A result without
        evidence is refused: an attack-path claim with nothing
        behind it is not a record. A NO_PATH_WITHIN_SCOPE verdict
        binds only to the declared model and scope the analysis
        names."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise LabyrinthDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise LabyrinthDenied(
                'An evidence reference is required to record a'
                ' result')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lab_analyses'
                    ' WHERE analysis_id = ?',
                    (analysis_id,)).fetchone()
                if row is None:
                    raise LabyrinthDenied('Analysis not found')
                if row['status'] != 'APPROVED':
                    raise LabyrinthDenied(
                        'Results are recorded only for APPROVED'
                        f" analyses (this one is {row['status']})")
                receipt_id = self._record(
                    'LABYRINTH_RESULT_RECORDED', actor=actor,
                    analysis_id=analysis_id, verdict=verdict,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE lab_analyses SET status = ?, verdict'
                    ' = ?, evidence_ref = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE analysis_id = ?',
                    ('RESULT_RECORDED', verdict,
                     evidence_ref.strip(), actor, now, receipt_id,
                     analysis_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ANALYSIS_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM lab_analyses'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM lab_analyses'
                    ' WHERE verdict IS NOT NULL GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'analyses_total': sum(by_status.values()),
            'analyses_by_status': by_status,
            'analyses_by_verdict': by_verdict,
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
                    raise LabyrinthDenied(str(exc)) from exc
                self._record('LABYRINTH_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
