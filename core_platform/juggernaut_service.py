"""JUGGERNAUT — the execution integrity and verification RTSA.

The production build-out of the JUGGERNAUT role contract
(``core_platform/rtsa_registry.py``: canonical name "JUGGERNAUT",
slug ``juggernaut``, mission "execution integrity and
verification", SPECIFIED, enabled: False), built whole as its
own platform service over the shared RTSA foundation (RTSA Build
Program Q33). This landing completes Band 2B's JUGGERNAUT
position in queue order.

Identity discipline: JUGGERNAUT is its own platform. The
recovered-history record holds Hades independent — "do not
merge with Michael Angelo or JUGGERNAUT" — and this build
merges nothing: JUGGERNAUT is not Hades, not MICHAEL ANGELO,
and not any other platform. Owner ruling (2026-11-24):
JUGGERNAUT has NO NAICS codes — its identity carries none, and
none are invented for it anywhere in this build.

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
This platform performs no execution of any kind: it neither
runs, re-runs, nor authorizes an execution. What it does is
the execution-integrity verification record, governed:

- **Verification records**: integrity verifications over
  executions presented by reference, carried as durable,
  receipted records (execution reference, the execution
  receipt's digest where one exists, scope reference) with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by a human
  operator's recorded decision, then a verdict recorded
  against presented verification evidence
  (VERDICT_RECORDED).
- **The designed receipt discipline** (the role's designed
  offline assessment in ``core_platform/rtsa_assessments.py``)
  is enforced in the record model: an execution presented
  without its receipt digest stands EXECUTION_RECEIPT_MISSING,
  and an INTEGRITY_VERIFIED verdict on such a record is
  refused — there is nothing to verify integrity against.
  Where a digest is presented, the designed assessment still
  holds: RECEIPT_SIGNATURE_VERIFICATION_REQUIRED — a digest
  is a fingerprint, not a verified signature, so every
  recorded verdict carries signature_verification_required,
  and no record in this platform ever stands as a completed
  signature verification.
- **Verdicts** are recorded only for APPROVED verifications
  and only against a presented verification-evidence
  reference, with a closed verdict set (INTEGRITY_VERIFIED /
  INTEGRITY_FAILED / INCONCLUSIVE). A verdict without
  evidence is refused: an integrity claim with nothing behind
  it is not a record.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed —
  whether a named operation is a record operation this
  platform may carry or a prohibited operation it refuses.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses to
exist without one.
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
    platform_id='juggernaut',
    name='JUGGERNAUT',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['JUGGERNAUT']
RECORD_OPERATIONS = (
    'record_verification', 'approve_verification',
    'record_verdict', 'view_verification', 'view_contract',
)
VERIFICATION_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                         'VERDICT_RECORDED')
VERIFICATION_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
VERDICTS = ('INTEGRITY_VERIFIED', 'INTEGRITY_FAILED',
            'INCONCLUSIVE')


class JuggernautDenied(Exception):
    """The requested JUGGERNAUT operation is not allowed."""


class JuggernautForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class JuggernautService:
    """JUGGERNAUT: governed execution-integrity verification
    records under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise JuggernautDenied(
                'JUGGERNAUT requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'juggernaut', {
            'OPERATOR': {'EXECUTION'},
            'AUDITOR': {'EXECUTION'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS jug_verifications (
                    verification_id TEXT PRIMARY KEY,
                    execution_ref TEXT NOT NULL,
                    receipt_digest TEXT,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    verification_evidence_ref TEXT,
                    signature_verification_required INTEGER
                        NOT NULL DEFAULT 0,
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
            raise JuggernautForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise JuggernautForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise JuggernautForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'EXECUTION', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise JuggernautForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise JuggernautDenied(str(exc)) from exc

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
            'note': 'The platform carries execution-integrity'
                    ' verification records over executions'
                    ' presented by reference only: it performs'
                    ' no execution of any kind — it neither runs,'
                    ' re-runs, nor authorizes an execution. An'
                    ' execution presented without its receipt'
                    ' digest stands EXECUTION_RECEIPT_MISSING and'
                    ' cannot be recorded INTEGRITY_VERIFIED; a'
                    ' presented digest still leaves receipt'
                    ' signature verification required, and no'
                    ' record here stands as a completed signature'
                    ' verification. JUGGERNAUT is its own'
                    ' platform — not Hades and not MICHAEL'
                    ' ANGELO — and carries no NAICS codes (owner'
                    " ruling, 2026-11-24). The contract remains"
                    ' SPECIFIED and enabled: False — deployment'
                    " of the intelligence is the owner's named"
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
            raise JuggernautDenied(
                f'Operation {operation!r} is prohibited by the'
                ' JUGGERNAUT role contract')
        if operation not in RECORD_OPERATIONS:
            raise JuggernautDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- verifications --------------------------------------------------

    @staticmethod
    def _verification_view(row):
        return {
            'verification_id': row['verification_id'],
            'execution_ref': row['execution_ref'],
            'receipt_digest': row['receipt_digest'],
            'receipt_present': row['receipt_digest'] is not None,
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'verification_evidence_ref':
                row['verification_evidence_ref'],
            'signature_verification_required':
                bool(row['signature_verification_required']),
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_verification(self, actor, execution_ref,
                            receipt_digest, scope_ref, *,
                            region=None):
        """Record one execution-integrity verification request
        (operator only) over an execution presented by
        reference. The receipt digest may be absent — the
        record then stands EXECUTION_RECEIPT_MISSING, exactly
        as the designed assessment holds, and no
        INTEGRITY_VERIFIED verdict can be recorded on it.
        Recording the request executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('execution_ref', execution_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise JuggernautDenied(f'A {label} is required')
        if receipt_digest is not None:
            if not isinstance(receipt_digest, str):
                raise JuggernautDenied(
                    'A receipt_digest must be a string or None')
            receipt_digest = receipt_digest.strip() or None
        now = self._now()
        verification_id = f'jug-verification-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'JUGGERNAUT_VERIFICATION_RECORDED', actor=actor,
                    verification_id=verification_id,
                    execution_ref=execution_ref.strip(),
                    receipt_present=receipt_digest is not None)
                db.execute(
                    'INSERT INTO jug_verifications (verification_id,'
                    ' execution_ref, receipt_digest, scope_ref,'
                    ' status, verdict, verification_evidence_ref,'
                    ' signature_verification_required, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?)',
                    (verification_id, execution_ref.strip(),
                     receipt_digest, scope_ref.strip(),
                     'REQUESTED', None, None, 0,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM jug_verifications'
                ' WHERE verification_id = ?',
                (verification_id,)).fetchone()
        return self._verification_view(row)

    def verifications_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'verifications',
                           'verifications view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM jug_verifications'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._verification_view(row) for row in rows]

    def verification_view(self, actor, role, verification_id, *,
                          region=None):
        self._geo(region)
        self._guard_access(actor, role, verification_id,
                           'verification view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM jug_verifications'
                ' WHERE verification_id = ?',
                (verification_id,)).fetchone()
        if row is None:
            raise JuggernautDenied('Verification not found')
        return self._verification_view(row)

    def verification_action(self, actor, verification_id, action, *,
                            region=None):
        """Approve or reject one requested verification
        (operator only) — the recorded human decision the
        contract requires. Approval approves the RECORD; it
        executes and authorizes nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = VERIFICATION_TRANSITIONS.get(action)
        if transitions is None:
            raise JuggernautDenied(
                f'Unknown verification action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM jug_verifications'
                    ' WHERE verification_id = ?',
                    (verification_id,)).fetchone()
                if row is None:
                    raise JuggernautDenied('Verification not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise JuggernautDenied(
                        f"Cannot {action} a verification in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'JUGGERNAUT_VERIFICATION_ACTION', actor=actor,
                    verification_id=verification_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE jug_verifications SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE verification_id = ?',
                    (new_status, actor, now, receipt_id,
                     verification_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM jug_verifications'
                ' WHERE verification_id = ?',
                (verification_id,)).fetchone()
        return self._verification_view(updated)

    def record_verdict(self, actor, verification_id, verdict,
                       verification_evidence_ref, *, region=None):
        """Record one approved verification's verdict (operator
        only), against a presented verification-evidence
        reference. A verdict without evidence is refused. An
        INTEGRITY_VERIFIED verdict on a record whose execution
        was presented without its receipt digest is refused —
        EXECUTION_RECEIPT_MISSING: there is nothing to verify
        integrity against. Every recorded verdict carries
        signature_verification_required: a presented digest
        leaves receipt signature verification required, exactly
        as the designed assessment holds, and this platform
        completes no signature verification."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise JuggernautDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(verification_evidence_ref, str) \
                or not verification_evidence_ref.strip():
            raise JuggernautDenied(
                'A verification evidence reference is required'
                ' to record a verdict')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM jug_verifications'
                    ' WHERE verification_id = ?',
                    (verification_id,)).fetchone()
                if row is None:
                    raise JuggernautDenied('Verification not found')
                if row['status'] != 'APPROVED':
                    raise JuggernautDenied(
                        'Verdicts are recorded only for APPROVED'
                        f" verifications (this one is"
                        f" {row['status']})")
                if verdict == 'INTEGRITY_VERIFIED' \
                        and row['receipt_digest'] is None:
                    raise JuggernautDenied(
                        'EXECUTION_RECEIPT_MISSING: an execution'
                        ' presented without its receipt digest'
                        ' cannot be recorded INTEGRITY_VERIFIED')
                receipt_id = self._record(
                    'JUGGERNAUT_VERDICT_RECORDED', actor=actor,
                    verification_id=verification_id, verdict=verdict,
                    verification_evidence_ref=
                    verification_evidence_ref.strip())
                db.execute(
                    'UPDATE jug_verifications SET status = ?,'
                    ' verdict = ?, verification_evidence_ref = ?,'
                    ' signature_verification_required = 1,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE verification_id = ?',
                    ('VERDICT_RECORDED', verdict,
                     verification_evidence_ref.strip(), actor, now,
                     receipt_id, verification_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM jug_verifications'
                ' WHERE verification_id = ?',
                (verification_id,)).fetchone()
        return self._verification_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in VERIFICATION_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' jug_verifications GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM'
                    ' jug_verifications WHERE verdict IS NOT NULL'
                    ' GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            receipt_missing = db.execute(
                'SELECT COUNT(*) AS n FROM jug_verifications'
                ' WHERE receipt_digest IS NULL').fetchone()['n']
            sig_required = db.execute(
                'SELECT COUNT(*) AS n FROM jug_verifications'
                ' WHERE signature_verification_required = 1'
                ).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'verifications_total': sum(by_status.values()),
            'verifications_by_status': by_status,
            'verifications_by_verdict': by_verdict,
            'receipt_missing': receipt_missing,
            'signature_verification_required': sig_required,
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
                    raise JuggernautDenied(str(exc)) from exc
                self._record('JUGGERNAUT_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
