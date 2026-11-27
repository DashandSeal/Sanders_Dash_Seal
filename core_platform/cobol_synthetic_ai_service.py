"""COBOL Synthetic AI — the legacy systems and modernization RTSA.

The production build-out of the COBOL Synthetic AI role
contract (``core_platform/rtsa_registry.py``: canonical name
"COBOL Synthetic AI", slug ``cobol-synthetic-ai``, mission
"legacy systems and modernization", SPECIFIED, enabled:
False), built whole as its own platform service over the shared
RTSA foundation (RTSA Build Program Q32).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform reads, parses, converts, and executes no legacy
code, and it migrates nothing. What it does is the
modernization assessment record, governed:

- **Assessment records**: legacy modernization assessments
  carried as durable, receipted records (system reference,
  language reference, target reference, scope reference) with
  a lifecycle: REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then a compatibility
  determination recorded against presented evidence
  (DETERMINATION_RECORDED).
- **Determinations** are recorded only for APPROVED
  assessments and only against presented compatibility
  evidence, with a closed verdict set
  (COMPATIBILITY_CONFIRMED / COMPATIBILITY_FAILED /
  INCONCLUSIVE). Without compatibility evidence no
  determination is recorded at all — the legacy system stands
  LEGACY_COMPATIBILITY_UNTESTED, exactly as the role's
  designed offline assessment holds.
- **Migration discipline**: every recorded determination
  carries migration_review_required. The platform never
  records a migration approval and never clears a system for
  migration: with compatibility evidence presented, a
  migration review by humans remains required
  (MIGRATION_REVIEW_REQUIRED), and the decision is theirs.
- **Attribution discipline**: Daedalus's COBOL Bridge is a
  Daedalus component (owner-held, queue Q13). No examined
  document equates it with this platform; this module imports
  no Daedalus module and claims none of Daedalus's components
  or figures.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether
  a named operation is a record operation this platform may
  carry or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the
shared foundation's audit adapter; the service refuses to exist
without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541511,
541512, 541513, 518210, 541519, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
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
    platform_id='cobol_synthetic_ai',
    name='COBOL Synthetic AI',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541511', '541512', '541513', '518210', '541519', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['COBOL Synthetic AI']
RECORD_OPERATIONS = (
    'record_assessment', 'approve_assessment',
    'record_determination', 'view_assessment', 'view_contract',
)
ASSESSMENT_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                       'DETERMINATION_RECORDED')
ASSESSMENT_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
VERDICTS = ('COMPATIBILITY_CONFIRMED', 'COMPATIBILITY_FAILED',
            'INCONCLUSIVE')


class CobolDenied(Exception):
    """The requested COBOL Synthetic AI operation is not
    allowed."""


class CobolForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class CobolSyntheticAiService:
    """COBOL Synthetic AI: governed legacy modernization
    assessment records under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise CobolDenied(
                'COBOL Synthetic AI requires a working Glass-Box'
                ' audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'cobol_synthetic_ai', {
            'OPERATOR': {'LEGACY'},
            'AUDITOR': {'LEGACY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS cobol_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    system_ref TEXT NOT NULL,
                    language_ref TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    compatibility_evidence_ref TEXT,
                    migration_review_required INTEGER,
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
            raise CobolForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise CobolForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise CobolForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'LEGACY', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise CobolForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise CobolDenied(str(exc)) from exc

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
            'note': 'The platform carries legacy modernization'
                    ' assessment records over systems presented'
                    ' by reference only: it reads, parses,'
                    ' converts, and executes no legacy code, and'
                    ' it migrates nothing. Without compatibility'
                    ' evidence a legacy system stands'
                    ' LEGACY_COMPATIBILITY_UNTESTED and no'
                    ' determination is recorded; every recorded'
                    ' determination carries'
                    ' migration_review_required — the platform'
                    ' never records a migration approval.'
                    " Daedalus's COBOL Bridge is a Daedalus"
                    ' component, not this platform; no examined'
                    ' document equates the two. The contract'
                    ' remains SPECIFIED and enabled: False —'
                    ' deployment of the intelligence is the'
                    " owner's named approval, not this build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise CobolDenied(
                f'Operation {operation!r} is prohibited by the'
                ' COBOL Synthetic AI role contract')
        if operation not in RECORD_OPERATIONS:
            raise CobolDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- assessments ----------------------------------------------------

    @staticmethod
    def _assessment_view(row):
        return {
            'assessment_id': row['assessment_id'],
            'system_ref': row['system_ref'],
            'language_ref': row['language_ref'],
            'target_ref': row['target_ref'],
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'compatibility_evidence_ref':
                row['compatibility_evidence_ref'],
            'migration_review_required': (
                None if row['migration_review_required'] is None
                else bool(row['migration_review_required'])),
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_assessment(self, actor, system_ref, language_ref,
                          target_ref, scope_ref, *, region=None):
        """Record one legacy modernization assessment request
        (operator only) over a system presented by reference.
        The record governs the assessment; recording it reads
        no legacy code and tests nothing by itself."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('system_ref', system_ref),
                             ('language_ref', language_ref),
                             ('target_ref', target_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise CobolDenied(f'A {label} is required')
        now = self._now()
        assessment_id = f'cobol-assessment-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'COBOL_ASSESSMENT_RECORDED', actor=actor,
                    assessment_id=assessment_id,
                    system_ref=system_ref.strip(),
                    target_ref=target_ref.strip())
                db.execute(
                    'INSERT INTO cobol_assessments (assessment_id,'
                    ' system_ref, language_ref, target_ref,'
                    ' scope_ref, status, verdict,'
                    ' compatibility_evidence_ref,'
                    ' migration_review_required, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?, ?, ?)',
                    (assessment_id, system_ref.strip(),
                     language_ref.strip(), target_ref.strip(),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     None, actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM cobol_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(row)

    def assessments_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assessments',
                           'assessments view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM cobol_assessments'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._assessment_view(row) for row in rows]

    def assessment_view(self, actor, role, assessment_id, *,
                        region=None):
        self._geo(region)
        self._guard_access(actor, role, assessment_id,
                           'assessment view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM cobol_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        if row is None:
            raise CobolDenied('Assessment not found')
        return self._assessment_view(row)

    def assessment_action(self, actor, assessment_id, action, *,
                          region=None):
        """Approve or reject one requested assessment (operator
        only) — the recorded human decision the contract
        requires. Approval approves the RECORD; it tests
        nothing and migrates nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ASSESSMENT_TRANSITIONS.get(action)
        if transitions is None:
            raise CobolDenied(
                f'Unknown assessment action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM cobol_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise CobolDenied('Assessment not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise CobolDenied(
                        f"Cannot {action} an assessment in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'COBOL_ASSESSMENT_ACTION', actor=actor,
                    assessment_id=assessment_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE cobol_assessments SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE assessment_id = ?',
                    (new_status, actor, now, receipt_id,
                     assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM cobol_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    def record_determination(self, actor, assessment_id, verdict,
                             compatibility_evidence_ref, *,
                             region=None):
        """Record one approved assessment's compatibility
        determination (operator only), against presented
        compatibility evidence. A determination without
        compatibility evidence is refused: without it the
        legacy system stands LEGACY_COMPATIBILITY_UNTESTED.
        Every recorded determination carries
        migration_review_required — this platform records no
        migration approval, ever."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise CobolDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(compatibility_evidence_ref, str) \
                or not compatibility_evidence_ref.strip():
            raise CobolDenied(
                'A compatibility evidence reference is required'
                ' to record a determination: without it the'
                ' legacy system stands'
                ' LEGACY_COMPATIBILITY_UNTESTED')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM cobol_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise CobolDenied('Assessment not found')
                if row['status'] != 'APPROVED':
                    raise CobolDenied(
                        'Determinations are recorded only for'
                        ' APPROVED assessments (this one is'
                        f" {row['status']})")
                receipt_id = self._record(
                    'COBOL_DETERMINATION_RECORDED', actor=actor,
                    assessment_id=assessment_id, verdict=verdict,
                    compatibility_evidence_ref=
                    compatibility_evidence_ref.strip(),
                    migration_review_required=True)
                db.execute(
                    'UPDATE cobol_assessments SET status = ?,'
                    ' verdict = ?, compatibility_evidence_ref'
                    ' = ?, migration_review_required = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id'
                    ' = ? WHERE assessment_id = ?',
                    ('DETERMINATION_RECORDED', verdict,
                     compatibility_evidence_ref.strip(), 1, actor,
                     now, receipt_id, assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM cobol_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ASSESSMENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' cobol_assessments GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM'
                    ' cobol_assessments WHERE verdict IS NOT NULL'
                    ' GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            review_pending = db.execute(
                'SELECT COUNT(*) AS n FROM cobol_assessments'
                ' WHERE migration_review_required = 1',
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'assessments_total': sum(by_status.values()),
            'assessments_by_status': by_status,
            'assessments_by_verdict': by_verdict,
            'migration_review_pending': review_pending,
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
                    raise CobolDenied(str(exc)) from exc
                self._record('COBOL_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
