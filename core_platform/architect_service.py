"""ARCHITECT — the architecture/design RTSA platform.

The production build-out of the ARCHITECT role contract
(``core_platform/rtsa_registry.py``: canonical name ARCHITECT,
slug ``architect``, mission "architecture/design", SPECIFIED,
enabled: False), built whole as its own platform service over the
shared RTSA foundation (RTSA Build Program Q25).

The contract's own guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, production deployment — are
refused by name, in the service, every time. What the platform
does is the mission as governed records:

- **Design records**: architecture designs recorded as durable,
  receipted records (title, subject, summary, the design body
  held as a hash — content stays with its author systems) with a
  lifecycle: DRAFT, then UNDER_REVIEW, then APPROVED or REJECTED
  by a human operator's recorded decision, then SUPERSEDED when a
  later design replaces it. Approval here is a recorded human act
  about a design record; it authorizes nothing to execute — the
  contract stays enabled: False and no execution path exists in
  this platform.
- **Reviews**: recorded concurrences and non-concurrences against
  a design under review, by named actors, receipted.
- **Contract discipline**: the role contract is exposed as a view,
  and an operation check answers — fail-closed — whether a named
  operation is a record operation this platform may carry or a
  prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one. MASTER section 20 boundaries hold: ARCHITECT is not the IT
AI Manager, not TwinGate, and not any execution platform.
"""

from __future__ import annotations

import hashlib
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
    platform_id='architect',
    name='ARCHITECT',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['ARCHITECT']
RECORD_OPERATIONS = (
    'record_design', 'review_design', 'decide_design',
    'view_design', 'view_contract',
)
DESIGN_STATUSES = ('DRAFT', 'UNDER_REVIEW', 'APPROVED', 'REJECTED',
                   'SUPERSEDED')
DESIGN_TRANSITIONS = {
    'submit': {'DRAFT': 'UNDER_REVIEW'},
    'approve': {'UNDER_REVIEW': 'APPROVED'},
    'reject': {'UNDER_REVIEW': 'REJECTED'},
    'supersede': {'APPROVED': 'SUPERSEDED'},
    'withdraw': {'DRAFT': 'REJECTED', 'UNDER_REVIEW': 'REJECTED'},
}
REVIEW_VERDICTS = ('CONCUR', 'NON_CONCUR')


class ArchitectDenied(Exception):
    """The requested ARCHITECT operation is not allowed."""


class ArchitectForbidden(Exception):
    """The actor lacks authority for the requested operation."""


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False).encode('utf-8')).hexdigest()


class ArchitectService:
    """ARCHITECT: governed architecture/design records under the
    role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ArchitectDenied(
                'ARCHITECT requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'architect', {
            'OPERATOR': {'DESIGN'},
            'AUDITOR': {'DESIGN'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS arc_designs (
                    design_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    body_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS arc_reviews (
                    review_id TEXT PRIMARY KEY,
                    design_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at REAL NOT NULL,
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
            raise ArchitectForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ArchitectForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ArchitectForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'DESIGN', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise ArchitectForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ArchitectDenied(str(exc)) from exc

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
            'note': 'The platform carries design records only. '
                    'Approval of a design record is a recorded '
                    'human act; it authorizes no execution. The '
                    'contract remains SPECIFIED and enabled: False '
                    '— deployment of the intelligence is the '
                    "owner's named approval, not this build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise ArchitectDenied(
                f'Operation {operation!r} is prohibited by the'
                ' ARCHITECT role contract')
        if operation not in RECORD_OPERATIONS:
            raise ArchitectDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- designs --------------------------------------------------------

    @staticmethod
    def _design_view(row, reviews=()):
        return {
            'design_id': row['design_id'],
            'title': row['title'],
            'subject_ref': row['subject_ref'],
            'summary': row['summary'],
            'body_hash': row['body_hash'],
            'status': row['status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
            'reviews': list(reviews),
        }

    @staticmethod
    def _review_view(row):
        return {
            'review_id': row['review_id'],
            'design_id': row['design_id'],
            'reviewer': row['reviewer'],
            'verdict': row['verdict'],
            'note': row['note'],
            'created_at': row['created_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_design(self, actor, title, subject_ref, summary, body,
                      *, region=None):
        """Record one architecture design (operator only). The
        design body is held as its SHA-256 hash — the platform
        governs the record; the content stays with its author."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('title', title),
                             ('subject_ref', subject_ref),
                             ('summary', summary)):
            if not isinstance(value, str) or not value.strip():
                raise ArchitectDenied(f'A {label} is required')
        if not isinstance(body, str) or not body.strip():
            raise ArchitectDenied('A design body is required')
        now = self._now()
        design_id = f'arc-design-{uuid.uuid4().hex[:16]}'
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'ARCHITECT_DESIGN_RECORDED', actor=actor,
                    design_id=design_id, subject_ref=subject_ref)
                db.execute(
                    'INSERT INTO arc_designs (design_id, title,'
                    ' subject_ref, summary, body_hash, status,'
                    ' created_by, created_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?)',
                    (design_id, title.strip(), subject_ref.strip(),
                     summary.strip(), body_hash, 'DRAFT', actor, now,
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM arc_designs WHERE design_id = ?',
                (design_id,)).fetchone()
        return self._design_view(row)

    def designs_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'designs', 'designs view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM arc_designs ORDER BY created_at',
            ).fetchall()
        return [self._design_view(row) for row in rows]

    def design_view(self, actor, role, design_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, design_id, 'design view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM arc_designs WHERE design_id = ?',
                (design_id,)).fetchone()
            if row is None:
                raise ArchitectDenied('Design not found')
            reviews = db.execute(
                'SELECT * FROM arc_reviews WHERE design_id = ?'
                ' ORDER BY created_at', (design_id,)).fetchall()
        return self._design_view(
            row, [self._review_view(r) for r in reviews])

    def design_action(self, actor, design_id, action, *, region=None):
        """Advance one design's lifecycle (operator only). The
        approve action is the recorded human decision the contract
        requires; it approves the RECORD, and authorizes no
        execution of anything."""
        self._geo(region)
        self._require_operator(actor)
        transitions = DESIGN_TRANSITIONS.get(action)
        if transitions is None:
            raise ArchitectDenied(f'Unknown design action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM arc_designs WHERE design_id = ?',
                    (design_id,)).fetchone()
                if row is None:
                    raise ArchitectDenied('Design not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ArchitectDenied(
                        f"Cannot {action} a design in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'ARCHITECT_DESIGN_ACTION', actor=actor,
                    design_id=design_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE arc_designs SET status = ?, updated_by ='
                    ' ?, updated_at = ?, receipt_id = ?'
                    ' WHERE design_id = ?',
                    (new_status, actor, now, receipt_id, design_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM arc_designs WHERE design_id = ?',
                (design_id,)).fetchone()
        return self._design_view(updated)

    def record_review(self, actor, role, design_id, verdict, note,
                      *, region=None):
        """Record one review of a design under review (guarded
        actors; the design must be UNDER_REVIEW)."""
        self._geo(region)
        self._guard_access(actor, role, design_id, 'design review')
        if verdict not in REVIEW_VERDICTS:
            raise ArchitectDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(note, str) or not note.strip():
            raise ArchitectDenied('A review note is required')
        now = self._now()
        review_id = f'arc-review-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT status FROM arc_designs WHERE design_id'
                    ' = ?', (design_id,)).fetchone()
                if row is None:
                    raise ArchitectDenied('Design not found')
                if row['status'] != 'UNDER_REVIEW':
                    raise ArchitectDenied(
                        'Reviews are recorded only while a design is'
                        ' UNDER_REVIEW')
                receipt_id = self._record(
                    'ARCHITECT_DESIGN_REVIEW', actor=actor,
                    design_id=design_id, verdict=verdict)
                db.execute(
                    'INSERT INTO arc_reviews (review_id, design_id,'
                    ' reviewer, verdict, note, created_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (review_id, design_id, actor, verdict,
                     note.strip(), now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            saved = db.execute(
                'SELECT * FROM arc_reviews WHERE review_id = ?',
                (review_id,)).fetchone()
        return self._review_view(saved)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in DESIGN_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM arc_designs'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            reviews_total = db.execute(
                'SELECT COUNT(*) AS n FROM arc_reviews',
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'designs_total': sum(by_status.values()),
            'designs_by_status': by_status,
            'reviews_total': reviews_total,
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
                    raise ArchitectDenied(str(exc)) from exc
                self._record('ARCHITECT_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
