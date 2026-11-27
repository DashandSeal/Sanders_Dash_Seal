"""Bozly — the corporate CFO and integrity witness, on the live path.

Bozly is the Sanders corporate headquarters CFO (owner correction,
2026-11-21): not a payment switch but the integrity witness —
cryptographic receipts proving which authorized officer signed each
executive action, and claim-integrity checks comparing documented
claims against recorded transactions. Bozly has NO power to move
money: it never initiates a charge, never disburses funds, and
``funds_disbursed`` is False on every receipt it issues.

What already existed before this build, and where it stood:

- The CFO ledger core (``core_platform/bozly/bozly_cfo.py``) and its
  recorder wiring (``core_platform/bozly_wiring.py``) record
  signature-verified Stripe events in the hash-linked ledger. That
  path is live in the webhook composition and is untouched here.
- ``BozlyAuthGate`` (``core_platform/bozly/bozly_auth_gate.py``)
  verifies Ed25519 officer signatures against named public keys,
  but its only caller was the Sanders Signal hub with
  caller-supplied keys: no officer public-key configuration
  mechanism existed on the CFO path and no route carried an officer
  action to it.
- ``assess_documented_claim``
  (``core_platform/bozly/bozly_claim_integrity.py``) assesses a
  documented claim against a recorded transaction, but its only
  surface was the standalone Bozly shield service's human API —
  OIDC-gated and not part of the running deployment — so no claim
  could be assessed through the live path.
- Platform machine events (self-repair incidents, watchdog
  escalations, deploy events) had NO Bozly receipt path at all:
  Bozly witnessed money movement and nothing else.

This service is the live-path completion, on the shared RTSA
foundation, in the platform pattern of the build program:

- **Machine-event receipts**: an operator records a platform
  machine event (closed type set) and Bozly issues a durable,
  hash-chained receipt for it in its own store, with the Glass-Box
  receipt written inside the same transaction. A repeated
  ``event_ref`` returns the original receipt (idempotent, the CFO
  ledger's DUPLICATE discipline) — an event is witnessed once.
- **Officer action receipts**: an operator presents an executive
  action, its structured details, and the officers' Ed25519
  signatures. The action is verified through the recovered
  ``BozlyAuthGate`` against the owner-configured officer public
  keys (``BOZLY_OFFICER_PUBLIC_KEYS_JSON``: role name -> base64
  Ed25519 public key; this module parses and validates the
  configuration and reports role names and key fingerprints only —
  it provisions no keys and never returns key material). The
  verification outcome is recorded as a durable receipt whether or
  not signatures verify; with no keys configured the receipt
  states exactly that and verifies nothing.
- **Claim integrity on the live path**: an operator assesses a
  documented claim through the recovered
  ``assess_documented_claim``, against the recorded transactions
  in the production Bozly ledger (the same database the verified
  Stripe-event recorder writes). The assessment itself is the
  claim module's durable review record; this service adds the
  platform Glass-Box receipt and the route.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction (the claim module
keeps its own durable review record by design, and the platform
receipt is written before the assessment is returned). Bozly's
scope is corporate headquarters: all four Sanders companies.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
541211, 541219, 518210, 541511, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

from .bozly.bozly_auth_gate import BozlyAuthGate
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
    platform_id='bozly',
    name='Bozly',
    legal_entities=('s_and_g_security_inc', 'sanders_legal_helpers',
                    'sanders_home_healthcare', 'sanders_senior_living'),
    naics_codes=('541512', '541211', '541219', '518210', '541511', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

MACHINE_EVENT_TYPES = (
    'SELF_REPAIR_INCIDENT', 'WATCHDOG_ESCALATION', 'DEPLOY_EVENT',
    'SECURITY_EVENT', 'OPERATOR_EVENT',
)
RECORD_OPERATIONS = (
    'record_machine_event', 'verify_officer_action', 'assess_claim',
    'view_machine_event', 'view_officer_receipt', 'view_claims',
    'view_officer_keys',
)
OFFICER_KEYS_ENV = 'BOZLY_OFFICER_PUBLIC_KEYS_JSON'


class BozlyDenied(Exception):
    """The requested Bozly operation is not allowed."""


class BozlyForbidden(Exception):
    """The actor lacks authority for the requested operation."""


def parse_officer_public_keys(raw=None):
    """Parse and validate BOZLY_OFFICER_PUBLIC_KEYS_JSON.

    The value is a JSON object mapping an officer role name to the
    base64 encoding of that officer's raw 32-byte Ed25519 public
    key. Returns ``{role: base64_key}`` for well-formed entries
    only; anything malformed returns ``{}`` or drops the entry —
    never raises, never logs the value. This is the configuration
    mechanism only: keys are provisioned by the owner, never by
    this module.
    """
    if raw is None:
        raw = os.environ.get(OFFICER_KEYS_ENV)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    allowed = {}
    for role, key in data.items():
        if not isinstance(role, str) or not role.strip() \
                or len(role) > 64 or not isinstance(key, str):
            continue
        try:
            raw_key = base64.b64decode(key, validate=True)
        except (ValueError, TypeError):
            continue
        if len(raw_key) != 32:
            continue
        allowed[role.strip()] = key
    return allowed


def _key_fingerprint(b64_key):
    """SHA-256 hex of the raw public-key bytes: a fingerprint is
    safe to report; the key material itself is never returned."""
    return hashlib.sha256(base64.b64decode(b64_key)).hexdigest()


class BozlyService:
    """Bozly on the live path: machine-event receipts, officer
    action-integrity receipts, and claim integrity, over the
    recovered Bozly engines."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 ledger_db_path=None, officer_public_keys=None,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise BozlyDenied(
                'Bozly requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'bozly', {
            'OPERATOR': {'FINANCE'},
            'AUDITOR': {'FINANCE'},
        })
        self._ledger_db_path = (
            str(ledger_db_path) if ledger_db_path
            else os.environ.get('BOZLY_DB_PATH'))
        if officer_public_keys is None:
            officer_public_keys = parse_officer_public_keys()
        self._officer_keys = dict(officer_public_keys)
        self._gate = BozlyAuthGate()
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS bozly_machine_events (
                    event_ref TEXT PRIMARY KEY,
                    source_platform TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    prev_receipt_sha256 TEXT NOT NULL,
                    receipt_sha256 TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    glass_receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bozly_officer_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    keys_configured INTEGER NOT NULL,
                    signature_results_json TEXT NOT NULL,
                    verified_signatories_json TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    glass_receipt_id TEXT NOT NULL
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
            raise BozlyForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise BozlyForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise BozlyForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'FINANCE', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise BozlyForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise BozlyDenied(str(exc)) from exc

    @staticmethod
    def _text(value, label, limit=512):
        if not isinstance(value, str) or not value.strip() \
                or len(value) > limit:
            raise BozlyDenied(f'A {label} is required')
        return value.strip()

    # -- officer key configuration -----------------------------------

    def officer_keys_view(self, actor, role, *, region=None):
        """The owner-configured officer public keys, as role names
        and fingerprints only. Key material is never returned."""
        self._geo(region)
        self._guard_access(actor, role, 'officer-keys',
                           'officer key configuration view')
        return {
            'keys_configured': bool(self._officer_keys),
            'roles': sorted(self._officer_keys),
            'fingerprints': {
                role: _key_fingerprint(self._officer_keys[role])
                for role in sorted(self._officer_keys)},
            'configuration_env': OFFICER_KEYS_ENV,
            'note': ('Officer public keys are provisioned by the'
                     ' owner as deployment configuration. Bozly'
                     ' verifies signatures against them; it holds'
                     ' no private keys and provisions none.'),
        }

    # -- machine-event receipts ----------------------------------------

    @staticmethod
    def _machine_event_view(row, duplicate=False):
        return {
            'event_ref': row['event_ref'],
            'source_platform': row['source_platform'],
            'event_type': row['event_type'],
            'entity_id': row['entity_id'],
            'summary': row['summary'],
            'evidence_ref': row['evidence_ref'],
            'evidence_sha256': row['evidence_sha256'],
            'receipt_sha256': row['receipt_sha256'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'duplicate': duplicate,
        }

    def record_machine_event(self, actor, source_platform, event_type,
                             entity_id, summary, evidence_ref,
                             event_ref, *, region=None):
        """Receipt one platform machine event (operator only).

        The receipt is hash-chained in Bozly's own store and its
        Glass-Box receipt is written in the same transaction. A
        repeated ``event_ref`` returns the original receipt with
        ``duplicate: True`` — an event is witnessed exactly once.
        """
        self._geo(region)
        self._require_operator(actor)
        if event_type not in MACHINE_EVENT_TYPES:
            raise BozlyDenied(f'Unknown machine event type:'
                              f' {event_type!r}')
        source_platform = self._text(source_platform,
                                     'source_platform', 128)
        entity_id = self._text(entity_id, 'entity_id', 128)
        summary = self._text(summary, 'summary', 1024)
        evidence_ref = self._text(evidence_ref, 'evidence_ref', 512)
        event_ref = self._text(event_ref, 'event_ref', 128)
        evidence_sha256 = hashlib.sha256(json.dumps(
            {'source_platform': source_platform,
             'event_type': event_type, 'entity_id': entity_id,
             'summary': summary, 'evidence_ref': evidence_ref},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                existing = db.execute(
                    'SELECT * FROM bozly_machine_events'
                    ' WHERE event_ref = ?', (event_ref,)).fetchone()
                if existing is not None:
                    db.commit()
                    return self._machine_event_view(existing,
                                                    duplicate=True)
                prev = db.execute(
                    'SELECT receipt_sha256 FROM bozly_machine_events'
                    ' ORDER BY recorded_at DESC, event_ref DESC'
                    ' LIMIT 1').fetchone()
                prev_hash = prev[0] if prev else '0' * 64
                receipt_sha256 = hashlib.sha256(
                    (prev_hash + ':' + event_ref + ':'
                     + evidence_sha256).encode()).hexdigest()
                glass_receipt_id = self._record(
                    'BOZLY_MACHINE_EVENT_RECEIPTED', actor=actor,
                    event_ref=event_ref, event_type=event_type,
                    source_platform=source_platform,
                    receipt_sha256=receipt_sha256)
                db.execute(
                    'INSERT INTO bozly_machine_events (event_ref,'
                    ' source_platform, event_type, entity_id, summary,'
                    ' evidence_ref, evidence_sha256,'
                    ' prev_receipt_sha256, receipt_sha256, recorded_by,'
                    ' recorded_at, glass_receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (event_ref, source_platform, event_type, entity_id,
                     summary, evidence_ref, evidence_sha256, prev_hash,
                     receipt_sha256, actor, now, glass_receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM bozly_machine_events WHERE event_ref = ?',
                (event_ref,)).fetchone()
        return self._machine_event_view(row)

    def machine_events_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'machine-events',
                           'machine event receipts view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM bozly_machine_events'
                ' ORDER BY recorded_at DESC, event_ref DESC'
                ' LIMIT 200').fetchall()
        return [self._machine_event_view(row) for row in rows]

    def machine_event_view(self, actor, role, event_ref, *,
                           region=None):
        self._geo(region)
        self._guard_access(actor, role, event_ref,
                           'machine event receipt view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM bozly_machine_events WHERE event_ref = ?',
                (event_ref,)).fetchone()
        if row is None:
            raise BozlyDenied('Machine event receipt not found')
        return self._machine_event_view(row)

    # -- officer action-integrity receipts -----------------------------

    @staticmethod
    def _officer_receipt_view(row):
        return {
            'receipt_id': row['receipt_id'],
            'action': row['action'],
            'payload_sha256': row['payload_sha256'],
            'keys_configured': bool(row['keys_configured']),
            'signature_results': json.loads(
                row['signature_results_json']),
            'verified_signatories': json.loads(
                row['verified_signatories_json']),
            'funds_disbursed': False,
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
        }

    def verify_officer_action(self, actor, action, details,
                              signatures, *, region=None):
        """Verify an executive action's officer signatures through
        the recovered BozlyAuthGate and record the receipt
        (operator only).

        Verification runs against the owner-configured officer
        public keys. With no keys configured, the action's payload
        hash is still recorded and the receipt states that no
        signature could be verified — no signature is ever
        invented. ``funds_disbursed`` is False: this receipt
        witnesses an action; it authorizes no movement of money.
        """
        self._geo(region)
        self._require_operator(actor)
        action = self._text(action, 'action', 256)
        if not isinstance(details, dict):
            raise BozlyDenied('Structured action details are required')
        if signatures is None:
            signatures = {}
        if not isinstance(signatures, dict):
            raise BozlyDenied('Signatures must be a role-to-signature'
                              ' object')
        try:
            payload_sha256 = self._gate.generate_action_payload_hash(
                action, details)
        except (ValueError, TypeError) as exc:
            raise BozlyDenied(str(exc)) from exc
        keys_configured = bool(self._officer_keys)
        if keys_configured:
            try:
                outcome = self._gate.evaluate_executive_approvals(
                    action, details, signatures, self._officer_keys)
            except (ValueError, TypeError) as exc:
                raise BozlyDenied(str(exc)) from exc
            signature_results = outcome['signature_results']
            verified = outcome['verified_signatories']
        else:
            signature_results = {}
            verified = []
        now = self._now()
        receipt_id = f'bozly-officer-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                glass_receipt_id = self._record(
                    'BOZLY_OFFICER_ACTION_VERIFIED', actor=actor,
                    receipt_id=receipt_id, action=action,
                    payload_sha256=payload_sha256,
                    keys_configured=keys_configured,
                    verified_signatories=verified)
                db.execute(
                    'INSERT INTO bozly_officer_receipts (receipt_id,'
                    ' action, payload_sha256, keys_configured,'
                    ' signature_results_json,'
                    ' verified_signatories_json, recorded_by,'
                    ' recorded_at, glass_receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (receipt_id, action, payload_sha256,
                     1 if keys_configured else 0,
                     json.dumps(signature_results, sort_keys=True),
                     json.dumps(verified, sort_keys=True),
                     actor, now, glass_receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM bozly_officer_receipts'
                ' WHERE receipt_id = ?', (receipt_id,)).fetchone()
        return self._officer_receipt_view(row)

    def officer_receipts_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'officer-actions',
                           'officer action receipts view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM bozly_officer_receipts'
                ' ORDER BY recorded_at DESC, receipt_id DESC'
                ' LIMIT 200').fetchall()
        return [self._officer_receipt_view(row) for row in rows]

    def officer_receipt_view(self, actor, role, receipt_id, *,
                             region=None):
        self._geo(region)
        self._guard_access(actor, role, receipt_id,
                           'officer action receipt view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM bozly_officer_receipts'
                ' WHERE receipt_id = ?', (receipt_id,)).fetchone()
        if row is None:
            raise BozlyDenied('Officer action receipt not found')
        return self._officer_receipt_view(row)

    # -- claim integrity on the live path ------------------------------

    def _align_ledger_env(self):
        """Point the recovered claim module at the production
        Bozly ledger — the same database the verified Stripe-event
        recorder writes. The claim module reads BOZLY_DB_PATH at
        call time; without this alignment it would assess against
        its standalone default path, a different file."""
        if self._ledger_db_path:
            os.environ['BOZLY_DB_PATH'] = self._ledger_db_path

    def assess_claim(self, actor, entity_id, record_type, record_id,
                     claimed_field, claimed_value, *, region=None):
        """Assess one documented claim against the recorded
        transaction, through the recovered claim-integrity engine
        (operator only). The engine's durable review record is the
        assessment's own record; the platform Glass-Box receipt is
        written before the assessment is returned."""
        self._geo(region)
        self._require_operator(actor)
        self._align_ledger_env()
        from .bozly.bozly_claim_integrity import assess_documented_claim
        try:
            result = assess_documented_claim(
                entity_id=entity_id, record_type=record_type,
                record_id=record_id, claimed_field=claimed_field,
                claimed_value=claimed_value, requested_by=actor)
        except ValueError as exc:
            raise BozlyDenied(str(exc)) from exc
        glass_receipt_id = self._record(
            'BOZLY_CLAIM_ASSESSED', actor=actor,
            review_id=result['review_id'], entity_id=entity_id,
            record_type=record_type, record_id=record_id,
            assessment=result['assessment'])
        result = dict(result)
        result['glass_receipt_id'] = glass_receipt_id
        return result

    def claims_list(self, actor, role, *, region=None):
        """Recorded claim-integrity reviews from the production
        Bozly ledger (read-only; empty when none exist)."""
        self._geo(region)
        self._guard_access(actor, role, 'claims',
                           'claim integrity reviews view')
        if not self._ledger_db_path:
            return []
        path = Path(self._ledger_db_path)
        if not path.exists():
            return []
        db = sqlite3.connect(f'file:{path}?mode=ro', uri=True,
                             timeout=10)
        db.row_factory = sqlite3.Row
        try:
            if not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table'"
                    " AND name='bozly_claim_integrity_reviews'"
            ).fetchone():
                return []
            rows = db.execute(
                'SELECT review_id, entity_id, record_type, record_id,'
                ' claimed_field, claimed_value_json,'
                ' source_value_json, observation, evidence_sha256,'
                ' requested_by, observed_at FROM'
                ' bozly_claim_integrity_reviews'
                ' ORDER BY rowid DESC LIMIT 200').fetchall()
            return [{
                'review_id': row['review_id'],
                'entity_id': row['entity_id'],
                'record_type': row['record_type'],
                'record_id': row['record_id'],
                'claimed_field': row['claimed_field'],
                'claimed_value': json.loads(row['claimed_value_json']),
                'recorded_value': json.loads(row['source_value_json']),
                'assessment': row['observation'],
                'evidence_sha256': row['evidence_sha256'],
                'requested_by': row['requested_by'],
                'observed_at': row['observed_at'],
            } for row in rows]
        finally:
            db.close()

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            machine_total = db.execute(
                'SELECT COUNT(*) FROM bozly_machine_events'
            ).fetchone()[0]
            by_type = {t: 0 for t in MACHINE_EVENT_TYPES}
            for row in db.execute(
                    'SELECT event_type, COUNT(*) AS n FROM'
                    ' bozly_machine_events GROUP BY event_type'):
                by_type[row['event_type']] = row['n']
            officer_total = db.execute(
                'SELECT COUNT(*) FROM bozly_officer_receipts'
            ).fetchone()[0]
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        try:
            from .bozly_wiring import bozly_status
            wiring = bozly_status(db_path=self._ledger_db_path)
        except Exception:
            wiring = {'wired': True, 'configured': False}
        return {
            'identity': IDENTITY.to_dict(),
            'machine_events_total': machine_total,
            'machine_events_by_type': by_type,
            'officer_receipts_total': officer_total,
            'officer_keys_configured': bool(self._officer_keys),
            'officer_key_roles': sorted(self._officer_keys),
            'ledger_wiring': wiring,
            'funds_disbursed': False,
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
                    raise BozlyDenied(str(exc)) from exc
                self._record('BOZLY_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
