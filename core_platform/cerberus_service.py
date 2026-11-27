"""CERBERUS — the evidence, provenance, and audit RTSA.

The production build-out of the CERBERUS role contract
(``core_platform/rtsa_registry.py``: canonical name "CERBERUS",
slug ``cerberus``, mission "evidence, provenance, audit",
SPECIFIED, enabled: False), built whole as its own platform
service over the shared RTSA foundation (RTSA Build Program Q30).

Identity discipline (MASTER section 20): CERBERUS is kept
DISTINCT from Glass-Box Audit (queue Q10). Glass-Box Audit is the
immutable provenance and execution record itself — the chains,
their completeness verification, their anchors. CERBERUS is the
audit attestation register that stands in front of evidence
chains it does not hold: it records governed determinations
about evidence chains presented to it by reference — whether a
presented chain stands verified, and whether an external anchor
stands behind it. CERBERUS opens no other platform's store,
recomputes no chain, holds no evidence, and anchors nothing;
this module imports neither ``glass_box_audit`` nor
``glass_box_audit_service``. The designed offline assessment for
this role states the same discipline: a chain whose verification
is not presented stands EVIDENCE_CHAIN_UNVERIFIED, and a verified
chain still requires its external anchor.

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access,
notarization, legal filing, financial transfer, and production
deployment — are refused by name, in the service, every time.
What the platform carries is the determination record, governed:

- **Assessment records**: evidence-chain assessments over
  chains presented by reference (subject reference, chain
  reference, scope reference) with a lifecycle: REQUESTED, then
  APPROVED or REJECTED by a human operator's recorded decision,
  then a determination recorded against presented verification
  evidence (DETERMINATION_RECORDED).
- **Determinations** are recorded only for APPROVED assessments
  and only against a presented verification-evidence reference,
  with a closed verdict set (CHAIN_VERIFIED / CHAIN_UNVERIFIED /
  INCONCLUSIVE). A determination may also carry an external
  anchor reference; a CHAIN_VERIFIED determination recorded
  without one stands anchor-required in the platform's status,
  exactly as the designed assessment holds.
- **Provenance discipline**: no determination is inherited,
  assumed, or carried over — every chain is assessed on its own
  recorded approval, and a determination binds only to the
  chain and scope it names.
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
identity record carries the reconciled six: 541512,
518210, 541211, 541690, 519190, 561499 — ADOPTED_EXISTING
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
    platform_id='cerberus',
    name='CERBERUS',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541512', '518210', '541211', '541690', '519190', '561499'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['CERBERUS']
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
VERDICTS = ('CHAIN_VERIFIED', 'CHAIN_UNVERIFIED', 'INCONCLUSIVE')


class CerberusDenied(Exception):
    """The requested CERBERUS operation is not allowed."""


class CerberusForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class CerberusService:
    """CERBERUS: governed evidence-chain assessment and
    determination records under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise CerberusDenied(
                'CERBERUS requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'cerberus', {
            'OPERATOR': {'EVIDENCE'},
            'AUDITOR': {'EVIDENCE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS cerb_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    chain_ref TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    verification_evidence_ref TEXT,
                    anchor_ref TEXT,
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
            raise CerberusForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise CerberusForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise CerberusForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'EVIDENCE', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise CerberusForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise CerberusDenied(str(exc)) from exc

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
            'note': 'The platform carries evidence-chain'
                    ' assessment and determination records over'
                    ' chains presented by reference only: it'
                    ' opens no store, recomputes no chain, holds'
                    ' no evidence, and anchors nothing. Glass-Box'
                    ' Audit — the immutable provenance and'
                    ' execution record, with its own completeness'
                    ' verification — is a separate platform'
                    ' (MASTER section 20); the two are never'
                    ' merged. A CHAIN_VERIFIED determination'
                    ' recorded without an external anchor'
                    ' reference stands anchor-required. The'
                    ' contract remains SPECIFIED and enabled:'
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
            raise CerberusDenied(
                f'Operation {operation!r} is prohibited by the'
                ' CERBERUS role contract')
        if operation not in RECORD_OPERATIONS:
            raise CerberusDenied(
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
            'subject_ref': row['subject_ref'],
            'chain_ref': row['chain_ref'],
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'verification_evidence_ref':
                row['verification_evidence_ref'],
            'anchor_ref': row['anchor_ref'],
            'anchor_required': (
                row['verdict'] == 'CHAIN_VERIFIED'
                and not row['anchor_ref']),
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_assessment(self, actor, subject_ref, chain_ref,
                          scope_ref, *, region=None):
        """Record one evidence-chain assessment request (operator
        only) over a chain presented by reference. The record
        governs the assessment; recording it opens nothing and
        verifies nothing by itself."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('chain_ref', chain_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise CerberusDenied(f'A {label} is required')
        now = self._now()
        assessment_id = f'cerb-assessment-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'CERBERUS_ASSESSMENT_RECORDED', actor=actor,
                    assessment_id=assessment_id,
                    subject_ref=subject_ref.strip(),
                    chain_ref=chain_ref.strip())
                db.execute(
                    'INSERT INTO cerb_assessments (assessment_id,'
                    ' subject_ref, chain_ref, scope_ref, status,'
                    ' verdict, verification_evidence_ref,'
                    ' anchor_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (assessment_id, subject_ref.strip(),
                     chain_ref.strip(), scope_ref.strip(),
                     'REQUESTED', None, None, None, actor, now,
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM cerb_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(row)

    def assessments_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assessments',
                           'assessments view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM cerb_assessments'
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
                'SELECT * FROM cerb_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        if row is None:
            raise CerberusDenied('Assessment not found')
        return self._assessment_view(row)

    def assessment_action(self, actor, assessment_id, action, *,
                          region=None):
        """Approve or reject one requested assessment (operator
        only) — the recorded human decision the contract
        requires. Approval approves the RECORD; it verifies
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ASSESSMENT_TRANSITIONS.get(action)
        if transitions is None:
            raise CerberusDenied(
                f'Unknown assessment action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM cerb_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise CerberusDenied('Assessment not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise CerberusDenied(
                        f"Cannot {action} an assessment in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'CERBERUS_ASSESSMENT_ACTION', actor=actor,
                    assessment_id=assessment_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE cerb_assessments SET status = ?,'
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
                'SELECT * FROM cerb_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    def record_determination(self, actor, assessment_id, verdict,
                             verification_evidence_ref,
                             anchor_ref=None, *, region=None):
        """Record one approved assessment's determination
        (operator only), against presented verification
        evidence. A determination without evidence is refused:
        an unverified chain stands EVIDENCE_CHAIN_UNVERIFIED,
        and no determination is recorded on nothing. An anchor
        reference may be recorded with the determination; a
        CHAIN_VERIFIED determination without one stands
        anchor-required."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise CerberusDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(verification_evidence_ref, str) \
                or not verification_evidence_ref.strip():
            raise CerberusDenied(
                'A verification evidence reference is required'
                ' to record a determination')
        if anchor_ref is not None:
            if not isinstance(anchor_ref, str):
                raise CerberusDenied(
                    'anchor_ref must be a string when given')
            anchor_ref = anchor_ref.strip() or None
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM cerb_assessments'
                    ' WHERE assessment_id = ?',
                    (assessment_id,)).fetchone()
                if row is None:
                    raise CerberusDenied('Assessment not found')
                if row['status'] != 'APPROVED':
                    raise CerberusDenied(
                        'Determinations are recorded only for'
                        ' APPROVED assessments (this one is'
                        f" {row['status']})")
                receipt_id = self._record(
                    'CERBERUS_DETERMINATION_RECORDED', actor=actor,
                    assessment_id=assessment_id, verdict=verdict,
                    verification_evidence_ref=
                    verification_evidence_ref.strip(),
                    anchor_ref=anchor_ref)
                db.execute(
                    'UPDATE cerb_assessments SET status = ?,'
                    ' verdict = ?, verification_evidence_ref'
                    ' = ?, anchor_ref = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE assessment_id = ?',
                    ('DETERMINATION_RECORDED', verdict,
                     verification_evidence_ref.strip(), anchor_ref,
                     actor, now, receipt_id, assessment_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM cerb_assessments'
                ' WHERE assessment_id = ?',
                (assessment_id,)).fetchone()
        return self._assessment_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ASSESSMENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' cerb_assessments GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM'
                    ' cerb_assessments WHERE verdict IS NOT NULL'
                    ' GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            anchor_required = db.execute(
                'SELECT COUNT(*) AS n FROM cerb_assessments'
                " WHERE verdict = 'CHAIN_VERIFIED' AND"
                ' (anchor_ref IS NULL OR anchor_ref = ?)',
                ('',)).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'assessments_total': sum(by_status.values()),
            'assessments_by_status': by_status,
            'assessments_by_verdict': by_verdict,
            'anchor_required': anchor_required,
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
                    raise CerberusDenied(str(exc)) from exc
                self._record('CERBERUS_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
