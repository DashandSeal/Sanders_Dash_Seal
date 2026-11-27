"""HYDRA-Q — the quantum-resistant cryptographic security RTSA.

The production build-out of the HYDRA-Q role contract
(``core_platform/rtsa_registry.py``: canonical name "HYDRA-Q",
slug ``hydra-q``, mission "quantum-resistant cryptographic
security", SPECIFIED, enabled: False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q28).

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, and production deployment —
are refused by name, in the service, every time. This platform
holds no key material, generates no keys, and performs no
cryptography of any kind: credential access is prohibited by its
own contract. What it does is the post-quantum readiness record,
governed:

- **Cryptographic asset records**: an inventory of cryptographic
  assets by reference (asset reference, algorithm family), each
  classified at registration by the algorithm family's quantum
  exposure — CLASSICAL (RSA, ECDSA, ECDH, DSA, AES, SHA-2,
  SHA-3), POST_QUANTUM (ML-KEM, ML-DSA, SLH-DSA — the finalized
  NIST post-quantum families), or HYBRID. The classification is
  a property of the named family, computed by this platform from
  its closed family table; it is never caller-asserted.
- **Assessment records**: a human operator records a migration
  determination for a registered asset — PQ_READY,
  MIGRATION_REQUIRED, or ACCEPTED_RISK — only against a
  presented evidence reference. A determination without evidence
  is refused: a readiness claim with nothing behind it is not a
  record.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether a
  named operation is a record operation this platform may carry
  or a prohibited operation it refuses.

Honest attribution boundary: post-quantum code exists elsewhere
in this repository, but no examined document attributes it to
HYDRA-Q (the canonical catalog records that attribution as an
owner decision). This build claims none of it: HYDRA-Q's own
build is this governed readiness register, and nothing more.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one. MASTER section 20 boundaries hold: HYDRA-Q is not the Vault
(key custody), not Glass-Box Audit (evidence), and not any
cryptographic executor.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
541715, 541519, 518210, 561621, 541690 — ADOPTED_EXISTING
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
    platform_id='hydra_q',
    name='HYDRA-Q',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('541512', '541715', '541519', '518210', '561621', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['HYDRA-Q']
RECORD_OPERATIONS = (
    'register_asset', 'record_assessment', 'view_asset',
    'view_contract',
)
# The closed algorithm-family table: each family's quantum
# exposure class. POST_QUANTUM names the finalized NIST
# post-quantum families (ML-KEM, ML-DSA, SLH-DSA); HYBRID names a
# classical + post-quantum combination recorded as one asset.
ALGORITHM_CLASSES = {
    'RSA': 'CLASSICAL',
    'ECDSA': 'CLASSICAL',
    'ECDH': 'CLASSICAL',
    'DSA': 'CLASSICAL',
    'AES': 'CLASSICAL',
    'SHA2': 'CLASSICAL',
    'SHA3': 'CLASSICAL',
    'ML_KEM': 'POST_QUANTUM',
    'ML_DSA': 'POST_QUANTUM',
    'SLH_DSA': 'POST_QUANTUM',
    'HYBRID_PQ': 'HYBRID',
}
CLASSIFICATIONS = ('CLASSICAL', 'POST_QUANTUM', 'HYBRID')
ASSET_STATUSES = ('REGISTERED', 'ASSESSED')
DETERMINATIONS = ('PQ_READY', 'MIGRATION_REQUIRED', 'ACCEPTED_RISK')


class HydraQDenied(Exception):
    """The requested HYDRA-Q operation is not allowed."""


class HydraQForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class HydraQService:
    """HYDRA-Q: the governed post-quantum readiness register
    under the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise HydraQDenied(
                'HYDRA-Q requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'hydra_q', {
            'OPERATOR': {'CRYPTOGRAPHY'},
            'AUDITOR': {'CRYPTOGRAPHY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS hydraq_assets (
                    asset_id TEXT PRIMARY KEY,
                    asset_ref TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    determination TEXT,
                    evidence_ref TEXT,
                    registered_by TEXT NOT NULL,
                    registered_at REAL NOT NULL,
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
            raise HydraQForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise HydraQForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise HydraQForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'CRYPTOGRAPHY',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise HydraQForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise HydraQDenied(str(exc)) from exc

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
            'algorithm_classes': dict(ALGORITHM_CLASSES),
            'note': 'The platform carries the post-quantum'
                    ' readiness register only: it holds no key'
                    ' material, generates no keys, and performs no'
                    ' cryptography — credential access is'
                    ' prohibited by its own contract. Post-quantum'
                    ' code elsewhere in the repository is not'
                    ' attributed to HYDRA-Q by any examined'
                    ' document and is not claimed here. The'
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
            raise HydraQDenied(
                f'Operation {operation!r} is prohibited by the'
                ' HYDRA-Q role contract')
        if operation not in RECORD_OPERATIONS:
            raise HydraQDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- assets ---------------------------------------------------------

    @staticmethod
    def _asset_view(row):
        return {
            'asset_id': row['asset_id'],
            'asset_ref': row['asset_ref'],
            'algorithm': row['algorithm'],
            'classification': row['classification'],
            'status': row['status'],
            'determination': row['determination'],
            'evidence_ref': row['evidence_ref'],
            'registered_by': row['registered_by'],
            'registered_at': row['registered_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def register_asset(self, actor, asset_ref, algorithm, *,
                       region=None):
        """Register one cryptographic asset by reference
        (operator only). The classification is computed here
        from the closed family table — never caller-asserted.
        Registering a reference holds no key material and
        performs no cryptography."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(asset_ref, str) or not asset_ref.strip():
            raise HydraQDenied('An asset_ref is required')
        classification = ALGORITHM_CLASSES.get(algorithm)
        if classification is None:
            raise HydraQDenied(
                f'Unknown algorithm family: {algorithm!r}')
        now = self._now()
        asset_id = f'hydraq-asset-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'HYDRAQ_ASSET_REGISTERED', actor=actor,
                    asset_id=asset_id, asset_ref=asset_ref.strip(),
                    algorithm=algorithm,
                    classification=classification)
                db.execute(
                    'INSERT INTO hydraq_assets (asset_id, asset_ref,'
                    ' algorithm, classification, status,'
                    ' determination, evidence_ref, registered_by,'
                    ' registered_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?)',
                    (asset_id, asset_ref.strip(), algorithm,
                     classification, 'REGISTERED', None, None, actor,
                     now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM hydraq_assets WHERE asset_id = ?',
                (asset_id,)).fetchone()
        return self._asset_view(row)

    def assets_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'assets', 'assets view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM hydraq_assets ORDER BY registered_at',
            ).fetchall()
        return [self._asset_view(row) for row in rows]

    def asset_view(self, actor, role, asset_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, asset_id, 'asset view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM hydraq_assets WHERE asset_id = ?',
                (asset_id,)).fetchone()
        if row is None:
            raise HydraQDenied('Asset not found')
        return self._asset_view(row)

    def record_assessment(self, actor, asset_id, determination,
                          evidence_ref, *, region=None):
        """Record one registered asset's migration determination
        (operator only), against a presented evidence reference.
        A determination without evidence is refused: a readiness
        claim with nothing behind it is not a record."""
        self._geo(region)
        self._require_operator(actor)
        if determination not in DETERMINATIONS:
            raise HydraQDenied(
                f'Unknown determination: {determination!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise HydraQDenied(
                'An evidence reference is required to record an'
                ' assessment')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM hydraq_assets WHERE asset_id = ?',
                    (asset_id,)).fetchone()
                if row is None:
                    raise HydraQDenied('Asset not found')
                if row['status'] != 'REGISTERED':
                    raise HydraQDenied(
                        'Assessments are recorded only for'
                        ' REGISTERED assets (this one is'
                        f" {row['status']})")
                receipt_id = self._record(
                    'HYDRAQ_ASSESSMENT_RECORDED', actor=actor,
                    asset_id=asset_id, determination=determination,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE hydraq_assets SET status = ?,'
                    ' determination = ?, evidence_ref = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE asset_id = ?',
                    ('ASSESSED', determination,
                     evidence_ref.strip(), actor, now, receipt_id,
                     asset_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM hydraq_assets WHERE asset_id = ?',
                (asset_id,)).fetchone()
        return self._asset_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ASSET_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM hydraq_assets'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_classification = {c: 0 for c in CLASSIFICATIONS}
            for row in db.execute(
                    'SELECT classification, COUNT(*) AS n FROM'
                    ' hydraq_assets GROUP BY classification'):
                by_classification[row['classification']] = row['n']
            by_determination = {d: 0 for d in DETERMINATIONS}
            for row in db.execute(
                    'SELECT determination, COUNT(*) AS n FROM'
                    ' hydraq_assets WHERE determination IS NOT NULL'
                    ' GROUP BY determination'):
                by_determination[row['determination']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'assets_total': sum(by_status.values()),
            'assets_by_status': by_status,
            'assets_by_classification': by_classification,
            'assets_by_determination': by_determination,
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
                    raise HydraQDenied(str(exc)) from exc
                self._record('HYDRAQ_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
