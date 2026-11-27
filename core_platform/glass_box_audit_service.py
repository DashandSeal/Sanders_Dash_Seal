"""Glass-Box Audit — production build-out (RTSA Build Program Q10).

The recovered ``core_platform/glass_box_audit.py`` is the substrate
and is left untouched: ``GlassBoxAudit`` writes the append-only,
hash-chained receipt ledger every platform on the shared RTSA
foundation receipts its actions into, and ``verify_audit()``
recomputes that chain. The native notary journal
(``core_platform/native_journal.py``) is the second chain, with the
same self-referential shape.

Both chains verify only against themselves: whoever controls a
store can rewrite every entry and recompute a perfectly valid chain,
and a chain truncated at an earlier head still verifies. The
Glass-Box strengthening design of 2026-11-24
(``~/workspace/glass-box-strengthening/design.md``) names what a
self-verifying chain lacks — an outside witness to its heads, a
signature over them, a copy the platform cannot reach, and a
standing check that the record is complete. This module is that
design built as the Glass-Box Audit platform's own production
service, on the shared foundation, within the design's owner-gated
limits:

* **Completeness verification (design Priority 4).** Read-only
  verification runs over both evidence stores: full chain-integrity
  recompute, sequence-contiguity check (gaps enumerated), and the
  prefix property against the last anchored state (the current
  chain must *extend* its anchored head — a chain that verifies but
  does not contain its anchored head has been rewritten or
  truncated). A failed verification opens an incident record with a
  lifecycle; evidence is never repaired, silently or otherwise.
* **Anchored timestamps (design Priority 1).** Anchor bundles in
  the design's §2.1 shape — per-chain count, highest sequence, head
  hash, the evidence file-set manifest hash, and the key-registry
  document hash — chained to the previous anchor so a missing
  anchor is a visible gap. Producing an anchor first checks the
  prefix property itself: a head that does not extend the last
  anchored state is refused, loudly — anchoring a rewritten head
  would launder it. Witness copies (repo record, OpenTimestamps,
  Object Storage, RFC 3161) are external acts; this module records
  witness receipts presented by an operator and never claims a
  witness it was not given.
* **Signed receipts (design Priority 2) — verification side only.**
  Anchors are produced unsigned and marked exactly so
  (``signing_key_not_provisioned``): the design reserves
  ``SDS_EVIDENCE_SIGNING_KEY`` for the owner's provisioning, and no
  key is generated, held, or fabricated here. What is built is the
  consumption side: an Ed25519 signature presented over an anchor
  bundle (or over the key-registry document) is verified against a
  presented public key and, when that key is registered, against
  its registry status — a cryptographically valid signature from a
  revoked key is reported NOT_TRUSTED, never as verified.
* **Backup manifests (design Priority 3) — records only.** Snapshot
  manifests over the evidence file set, binding per-file SHA-256
  and size to both chains' heads and counts, with chain integrity
  recomputed before the manifest is recorded (a snapshot over a
  broken chain is marked FAILED, never as good). The copies
  themselves — Object Storage buckets, retention rules — are
  tenancy acts at the owner's direction; the irreversible retention
  lock (owner decision D4) is NOT applied by this build and nothing
  here locks anything. Restore drills are recorded as
  operator-reported records with their comparison outcomes; drill
  currency is reported in status.
* **Key registry (design Priority 5) — mechanical format only.**
  The registry document of design §6.2: key class (A–F), public
  fingerprint, holder *role*, purpose, rotation lineage, revocation
  status. It stores public material only — no private key field
  exists. Its adoption (D8), every custody ruling (D9–D11), and
  forensic provisioning (D12) remain the owner's; the registry
  ships unsigned and reports ``root_signature: NOT_PROVISIONED``
  until the owner provisions a root key and signs it.

MASTER section 20: Vault and Glass-Box Audit are separate systems;
this platform is the evidence side and holds no keys and no
temporary authority. CERBERUS (evidence, provenance, audit) is a
separate RTSA contract and is not merged into this platform.

Like every platform on the foundation, the service refuses to exist
without a working Glass-Box audit adapter: no record, no action.
Every store this service *verifies* is opened read-only
(``mode=ro``): the verifier physically cannot mutate what it
guards. Its own records live in its own store.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541211,
541512, 518210, 541690, 541219, 561499 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
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
from .security import verify as _ed25519_verify


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='glass_box_audit',
    name='Glass-Box Audit',
    legal_entities=(),
    naics_codes=('541211', '541512', '518210', '541690', '541219', '561499'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

GENESIS = '0' * 64
ANCHOR_FORMAT = 1
ANCHOR_SIGNATURE_DOMAIN = 'glass-box-anchor-v1'
REGISTRY_SIGNATURE_DOMAIN = 'glass-box-key-registry-v1'
SIGNING_KEY_ENV = 'SDS_EVIDENCE_SIGNING_KEY'
STORES = ('glassbox', 'journal')
WITNESS_KINDS = ('REPO_RECORD', 'OPEN_TIMESTAMP', 'OBJECT_STORAGE',
                 'RFC3161')
INCIDENT_KINDS = ('CHAIN_BROKEN', 'SEQUENCE_GAP', 'PREFIX_DIVERGED',
                  'COUNT_REGRESSED', 'STORE_UNREADABLE')
INCIDENT_STATUSES = ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED', 'CLOSED')
INCIDENT_TRANSITIONS = {
    'acknowledge': {'DETECTED': 'ACKNOWLEDGED'},
    'escalate': {'DETECTED': 'ESCALATED', 'ACKNOWLEDGED': 'ESCALATED'},
    'close': {'DETECTED': 'CLOSED', 'ACKNOWLEDGED': 'CLOSED',
              'ESCALATED': 'CLOSED'},
}
KEY_CLASSES = ('A', 'B', 'C', 'D', 'E', 'F')
KEY_STATUSES = ('REGISTERED', 'ACTIVE', 'REVOKED', 'RETIRED')
KEY_TRANSITIONS = {
    'activate': {'REGISTERED': 'ACTIVE'},
    'revoke': {'REGISTERED': 'REVOKED', 'ACTIVE': 'REVOKED'},
    'retire': {'ACTIVE': 'RETIRED'},
}
ANCHOR_FRESH_SECONDS = 26 * 3600
DRILL_CURRENT_SECONDS = 92 * 24 * 3600
_STORE_VERDICT_RANK = {'COMPLETE': 0, 'COMPLETE_UNANCHORED': 1,
                       'INCOMPLETE': 2, 'DIVERGED': 3, 'BROKEN': 4}


class GlassBoxAuditPlatformDenied(Exception):
    """The requested Glass-Box Audit operation is not allowed."""


class GlassBoxAuditPlatformForbidden(Exception):
    """The actor lacks authority for the requested operation."""


def _canonical_bytes(value) -> bytes:
    """The GlassBox canonicalization: sorted keys, compact
    separators, UTF-8 — one rule everywhere in this module, the
    same rule both evidence chains hash with."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False).encode('utf-8')


def _hash(value) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _fingerprint(public_key_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()


class GlassBoxAuditService:
    """The Glass-Box Audit platform: completeness verification,
    anchor production, snapshot manifests, drill records, and the
    key registry — over evidence stores it opens read-only."""

    def __init__(self, database_path, glassbox_store_path,
                 journal_store_path, evidence_files,
                 operator_verifier, audit, *, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise GlassBoxAuditPlatformDenied(
                'Glass-Box Audit requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._store_paths = {
            'glassbox': Path(glassbox_store_path),
            'journal': Path(journal_store_path),
        }
        self._evidence_files = tuple(Path(p) for p in evidence_files)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'glass_box_audit', {
            'OPERATOR': {'EVIDENCE'},
            'AUDITOR': {'EVIDENCE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS gba_anchors (
                    anchor_id TEXT PRIMARY KEY,
                    anchored_at REAL NOT NULL,
                    bundle_json TEXT NOT NULL,
                    bundle_hash TEXT NOT NULL,
                    previous_anchor_hash TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gba_witnesses (
                    witness_id TEXT PRIMARY KEY,
                    anchor_id TEXT NOT NULL,
                    witness_kind TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gba_verifications (
                    verification_id TEXT PRIMARY KEY,
                    verified_at REAL NOT NULL,
                    verified_by TEXT NOT NULL,
                    glassbox_json TEXT NOT NULL,
                    journal_json TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gba_incidents (
                    incident_id TEXT PRIMARY KEY,
                    verification_id TEXT,
                    store TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS gba_incidents_open_idx
                    ON gba_incidents (store, kind, status);
                CREATE TABLE IF NOT EXISTS gba_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    produced_at REAL NOT NULL,
                    produced_by TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    manifest_hash TEXT NOT NULL,
                    chain_integrity TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gba_drills (
                    drill_id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL,
                    drilled_at REAL NOT NULL,
                    recorded_by TEXT NOT NULL,
                    glassbox_head_match INTEGER NOT NULL,
                    journal_head_match INTEGER NOT NULL,
                    counts_match INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gba_keys (
                    key_id TEXT PRIMARY KEY,
                    key_class TEXT NOT NULL,
                    fingerprint TEXT,
                    public_key_hex TEXT,
                    holder_role TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL,
                    predecessor_key_id TEXT,
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
            raise GlassBoxAuditPlatformForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GlassBoxAuditPlatformForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise GlassBoxAuditPlatformForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'EVIDENCE', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise GlassBoxAuditPlatformForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise GlassBoxAuditPlatformDenied(str(exc)) from exc

    # -- read-only chain inspection ----------------------------------

    def _read_chain(self, store):
        """Inspect one evidence store, opened read-only. Returns the
        chain state: presence, entry count, highest sequence, head
        hash, integrity (OK / EMPTY / BROKEN / UNREADABLE), the
        enumerated sequence gaps, and the first break position.
        This never writes to the store it inspects."""
        path = self._store_paths[store]
        state = {
            'store': store,
            'present': path.exists(),
            'count': 0,
            'highest_seq': 0,
            'head': GENESIS,
            'integrity': 'ABSENT',
            'gaps': [],
            'first_break_seq': None,
        }
        if not state['present']:
            return state
        if store == 'glassbox':
            table, seq_col, hash_col = 'receipts', 'seq', 'hash'
        else:
            table = 'native_notarial_journal'
            seq_col, hash_col = 'entry_seq', 'entry_hash'
        try:
            db = sqlite3.connect(f'file:{path}?mode=ro', uri=True,
                                 timeout=10)
            try:
                rows = db.execute(
                    f'SELECT {seq_col}, body, {hash_col} FROM {table}'
                    f' ORDER BY {seq_col} ASC').fetchall()
            finally:
                db.close()
        except sqlite3.Error:
            state['integrity'] = 'UNREADABLE'
            return state
        state['count'] = len(rows)
        if not rows:
            state['integrity'] = 'EMPTY'
            return state
        state['highest_seq'] = rows[-1][0]
        seqs = [row[0] for row in rows]
        seen = set(seqs)
        state['gaps'] = [s for s in range(seqs[0], seqs[-1] + 1)
                         if s not in seen]
        previous = GENESIS
        integrity = 'OK'
        for seq, body_text, stored_hash in rows:
            try:
                body = json.loads(body_text)
            except (ValueError, TypeError):
                integrity = 'BROKEN'
                state['first_break_seq'] = seq
                break
            if body.get('previous_hash') != previous:
                integrity = 'BROKEN'
                state['first_break_seq'] = seq
                break
            if _hash(body) != stored_hash:
                integrity = 'BROKEN'
                state['first_break_seq'] = seq
                break
            previous = stored_hash
        state['integrity'] = integrity
        state['head'] = previous if integrity == 'OK' else rows[-1][2]
        return state

    def _chain_anchor_view(self, state):
        return {
            'present': state['present'],
            'count': state['count'],
            'highest_seq': state['highest_seq'],
            'head': state['head'],
            'integrity': state['integrity'],
            'gaps': list(state['gaps']),
        }

    def _prefix_check(self, store, anchored, current):
        """Full prefix check with row access: the entry at the
        anchored highest sequence must carry the anchored head."""
        if anchored is None:
            return 'NO_ANCHOR'
        if current['count'] < anchored['count']:
            return 'COUNT_REGRESSED'
        if anchored['count'] == 0:
            return 'EXTENDS'
        if not current['present'] or current['integrity'] in (
                'UNREADABLE', 'ABSENT'):
            return 'PREFIX_DIVERGED'
        path = self._store_paths[store]
        if store == 'glassbox':
            table, seq_col, hash_col = 'receipts', 'seq', 'hash'
        else:
            table = 'native_notarial_journal'
            seq_col, hash_col = 'entry_seq', 'entry_hash'
        try:
            db = sqlite3.connect(f'file:{path}?mode=ro', uri=True,
                                 timeout=10)
            try:
                row = db.execute(
                    f'SELECT {hash_col} FROM {table}'
                    f' WHERE {seq_col} = ?',
                    (anchored['highest_seq'],)).fetchone()
            finally:
                db.close()
        except sqlite3.Error:
            return 'PREFIX_DIVERGED'
        if row is None or row[0] != anchored['head']:
            return 'PREFIX_DIVERGED'
        return 'EXTENDS'

    # -- file-set manifests -------------------------------------------

    def _file_manifest(self):
        files = []
        for path in self._evidence_files:
            if path.exists():
                data = path.read_bytes()
                files.append({
                    'file': path.name,
                    'present': True,
                    'size': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(),
                })
            else:
                files.append({
                    'file': path.name,
                    'present': False,
                    'size': None,
                    'sha256': None,
                })
        return files

    def _evidence_manifest(self, states):
        manifest = {
            'files': self._file_manifest(),
            'chains': {
                store: {
                    'count': states[store]['count'],
                    'highest_seq': states[store]['highest_seq'],
                    'head': states[store]['head'],
                } for store in STORES
            },
        }
        return manifest, _hash(manifest)

    # -- key registry ---------------------------------------------------

    @staticmethod
    def _key_view(row):
        return {
            'key_id': row['key_id'],
            'key_class': row['key_class'],
            'fingerprint': row['fingerprint'],
            'public_key_hex': row['public_key_hex'],
            'holder_role': row['holder_role'],
            'purpose': row['purpose'],
            'status': row['status'],
            'predecessor_key_id': row['predecessor_key_id'],
            'registered_by': row['registered_by'],
            'registered_at': row['registered_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def _registry_document(self, db):
        rows = db.execute(
            'SELECT * FROM gba_keys ORDER BY registered_at, key_id',
        ).fetchall()
        return {
            'format': 1,
            'platform_id': IDENTITY.platform_id,
            'platform': 'Sanders Dash & Seal',
            'keys': [self._key_view(row) for row in rows],
        }

    def registry_document(self, actor, role, *, region=None):
        """The canonical key-registry document (design §6.2). Its
        hash is bound into every anchor bundle."""
        self._geo(region)
        self._guard_access(actor, role, 'key-registry',
                           'key registry view')
        with self._connect() as db:
            document = self._registry_document(db)
        return {'document': document,
                'document_hash': _hash(document),
                'root_signature': 'NOT_PROVISIONED'}

    def keys_list(self, actor, role, *, region=None):
        """Every registered key's public record (guarded read)."""
        self._geo(region)
        self._guard_access(actor, role, 'key-registry', 'keys view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_keys ORDER BY registered_at, key_id',
            ).fetchall()
        return [self._key_view(row) for row in rows]

    def register_key(self, actor, key_class, holder_role, purpose,
                     public_key_hex=None, predecessor_key_id=None,
                     *, region=None):
        """Register one key's PUBLIC material (operator only). No
        private key field exists in this registry; a registration
        carrying anything but a 32-byte Ed25519 public key as hex is
        refused."""
        self._geo(region)
        self._require_operator(actor)
        if key_class not in KEY_CLASSES:
            raise GlassBoxAuditPlatformDenied(
                f'Unknown key class: {key_class!r}')
        if not isinstance(holder_role, str) or not holder_role.strip():
            raise GlassBoxAuditPlatformDenied(
                'A holder role is required (roles, not persons — '
                'custody names are the owner\'s ruling)')
        if not isinstance(purpose, str) or not purpose.strip():
            raise GlassBoxAuditPlatformDenied('A purpose is required')
        fingerprint = None
        if public_key_hex is not None:
            if not isinstance(public_key_hex, str) \
                    or len(public_key_hex) != 64:
                raise GlassBoxAuditPlatformDenied(
                    'public_key_hex must be a 32-byte Ed25519 public'
                    ' key in hex')
            try:
                bytes.fromhex(public_key_hex)
            except ValueError:
                raise GlassBoxAuditPlatformDenied(
                    'public_key_hex is not valid hex')
            public_key_hex = public_key_hex.lower()
            fingerprint = _fingerprint(public_key_hex)
        now = self._now()
        key_id = f'gb-key-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                if predecessor_key_id is not None:
                    prior = db.execute(
                        'SELECT key_id FROM gba_keys WHERE key_id = ?',
                        (predecessor_key_id,)).fetchone()
                    if prior is None:
                        raise GlassBoxAuditPlatformDenied(
                            'Predecessor key not found')
                receipt_id = self._record(
                    'GLASS_BOX_KEY_REGISTERED', actor=actor,
                    key_id=key_id, key_class=key_class,
                    fingerprint=fingerprint)
                db.execute(
                    'INSERT INTO gba_keys (key_id, key_class,'
                    ' fingerprint, public_key_hex, holder_role,'
                    ' purpose, status, predecessor_key_id,'
                    ' registered_by, registered_at, updated_by,'
                    ' updated_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (key_id, key_class, fingerprint, public_key_hex,
                     holder_role.strip(), purpose.strip(),
                     'REGISTERED', predecessor_key_id, actor, now,
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gba_keys WHERE key_id = ?',
                (key_id,)).fetchone()
        return self._key_view(row)

    def key_action(self, actor, key_id, action, *, region=None):
        """Advance one registry key's status (operator only):
        activate / revoke / retire, per the design's rotation and
        compromise procedures — a revocation is a record, and the
        key's history stays verifiable."""
        self._geo(region)
        self._require_operator(actor)
        transitions = KEY_TRANSITIONS.get(action)
        if transitions is None:
            raise GlassBoxAuditPlatformDenied(
                f'Unknown key action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM gba_keys WHERE key_id = ?',
                    (key_id,)).fetchone()
                if row is None:
                    raise GlassBoxAuditPlatformDenied('Key not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise GlassBoxAuditPlatformDenied(
                        f"Cannot {action} a key in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'GLASS_BOX_KEY_ACTION', actor=actor, key_id=key_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE gba_keys SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ? WHERE key_id = ?',
                    (new_status, actor, now, receipt_id, key_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM gba_keys WHERE key_id = ?',
                (key_id,)).fetchone()
        return self._key_view(updated)

    def _verify_presented_signature(self, value, domain, signature,
                                    public_key_hex):
        """The consumption side of design Priority 2: verify a
        presented Ed25519 signature over a presented value against
        a presented public key, and report the key's registry
        standing. Cryptographic validity and trust are reported
        separately — a valid signature from a revoked or unknown
        key is never reported as trusted."""
        result = {'cryptographic_valid': False, 'key_id': None,
                  'key_status': None, 'trusted': False,
                  'reason': None}
        if not isinstance(signature, str) or not signature.strip():
            result['reason'] = 'no_signature_presented'
            return result
        if not isinstance(public_key_hex, str) \
                or len(public_key_hex) != 64:
            result['reason'] = 'no_valid_public_key_presented'
            return result
        try:
            bytes.fromhex(public_key_hex)
        except ValueError:
            result['reason'] = 'no_valid_public_key_presented'
            return result
        fingerprint = _fingerprint(public_key_hex.lower())
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gba_keys WHERE fingerprint = ?',
                (fingerprint,)).fetchone()
        if row is not None:
            result['key_id'] = row['key_id']
            result['key_status'] = row['status']
        try:
            _ed25519_verify(public_key_hex.lower(), signature, domain,
                            value)
            result['cryptographic_valid'] = True
        except Exception:
            result['reason'] = 'signature_invalid'
            return result
        if row is None:
            result['reason'] = 'key_not_registered'
        elif row['status'] != 'ACTIVE':
            result['reason'] = f"key_status_{row['status'].lower()}"
        else:
            result['trusted'] = True
            result['reason'] = 'verified_against_active_registered_key'
        return result

    # -- anchors ---------------------------------------------------------

    @staticmethod
    def _anchor_view(row, witnesses=()):
        bundle = json.loads(row['bundle_json'])
        return {
            'anchor_id': row['anchor_id'],
            'anchored_at': row['anchored_at'],
            'bundle': bundle,
            'bundle_hash': row['bundle_hash'],
            'previous_anchor_hash': row['previous_anchor_hash'],
            'receipt_id': row['receipt_id'],
            'witnesses': list(witnesses),
        }

    @staticmethod
    def _witness_view(row):
        return {
            'witness_id': row['witness_id'],
            'anchor_id': row['anchor_id'],
            'witness_kind': row['witness_kind'],
            'reference': row['reference'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def _last_anchor_row(self, db):
        return db.execute(
            'SELECT * FROM gba_anchors ORDER BY anchored_at DESC,'
            ' anchor_id DESC LIMIT 1').fetchone()

    def produce_anchor(self, actor, *, region=None):
        """Produce one anchor bundle over both chains (operator
        only), in the design's §2.1 shape. The prefix-freeze rule is
        enforced first: if either chain no longer extends the last
        anchored state, the anchor is REFUSED and the refusal is
        receipted — a rewritten head is never laundered by a fresh
        witness. The bundle is produced unsigned and marked exactly
        so; signing awaits the owner's provisioned key (D2)."""
        self._geo(region)
        self._require_operator(actor)
        states = {store: self._read_chain(store) for store in STORES}
        with self._connect() as db:
            last = self._last_anchor_row(db)
            registry_document = self._registry_document(db)
        previous_anchor_hash = GENESIS
        if last is not None:
            previous_anchor_hash = last['bundle_hash']
            last_bundle = json.loads(last['bundle_json'])
            for store in STORES:
                anchored = last_bundle['chains'][store]
                result = self._prefix_check(store, anchored,
                                            states[store])
                if result in ('COUNT_REGRESSED', 'PREFIX_DIVERGED'):
                    self._record(
                        'GLASS_BOX_ANCHOR_REFUSED', actor=actor,
                        store=store, reason=result)
                    raise GlassBoxAuditPlatformDenied(
                        f'Anchor refused: the {store} chain does not'
                        f' extend its last anchored state ({result})'
                        ' — a rewritten or truncated head is never'
                        ' witnessed')
        manifest, manifest_hash = self._evidence_manifest(states)
        now = self._now()
        bundle_core = {
            'format': ANCHOR_FORMAT,
            'platform': 'Sanders Dash & Seal',
            'platform_id': IDENTITY.platform_id,
            'anchored_at': now,
            'anchor_time_source': 'platform_clock_untrusted',
            'chains': {store: self._chain_anchor_view(states[store])
                       for store in STORES},
            'evidence_manifest': manifest,
            'evidence_manifest_hash': manifest_hash,
            'key_registry_hash': _hash(registry_document),
            'previous_anchor_hash': previous_anchor_hash,
        }
        bundle_hash = _hash(bundle_core)
        bundle = dict(bundle_core)
        bundle['bundle_hash'] = bundle_hash
        bundle['signature'] = {
            'status': 'NOT_PROVISIONED',
            'alg': None,
            'signature': None,
            'key_fingerprint': None,
            'reason': 'signing_key_not_provisioned',
            'reserved_env': SIGNING_KEY_ENV,
        }
        anchor_id = f'gb-anchor-{uuid.uuid4().hex[:16]}'
        bundle_json = json.dumps(bundle, sort_keys=True,
                                 separators=(',', ':'),
                                 ensure_ascii=False)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'GLASS_BOX_ANCHOR', actor=actor,
                    anchor_id=anchor_id, bundle_hash=bundle_hash)
                db.execute(
                    'INSERT INTO gba_anchors (anchor_id, anchored_at,'
                    ' bundle_json, bundle_hash, previous_anchor_hash,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (anchor_id, now, bundle_json, bundle_hash,
                     previous_anchor_hash, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gba_anchors WHERE anchor_id = ?',
                (anchor_id,)).fetchone()
        return self._anchor_view(row)

    def anchors_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'anchors', 'anchors view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_anchors ORDER BY anchored_at',
            ).fetchall()
        return [self._anchor_view(row) for row in rows]

    def anchor_view(self, actor, role, anchor_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, anchor_id, 'anchor view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gba_anchors WHERE anchor_id = ?',
                (anchor_id,)).fetchone()
            if row is None:
                raise GlassBoxAuditPlatformDenied('Anchor not found')
            witnesses = db.execute(
                'SELECT * FROM gba_witnesses WHERE anchor_id = ?'
                ' ORDER BY recorded_at', (anchor_id,)).fetchall()
        return self._anchor_view(
            row, [self._witness_view(w) for w in witnesses])

    def record_witness(self, actor, anchor_id, witness_kind, reference,
                       *, region=None):
        """Record one witness receipt for an anchor (operator only).
        Witness copies are external acts (a repo commit, an
        OpenTimestamps submission, an Object Storage write, an RFC
        3161 token); this records the reference an operator presents
        and never fabricates one."""
        self._geo(region)
        self._require_operator(actor)
        if witness_kind not in WITNESS_KINDS:
            raise GlassBoxAuditPlatformDenied(
                f'Unknown witness kind: {witness_kind!r}')
        if not isinstance(reference, str) or not reference.strip():
            raise GlassBoxAuditPlatformDenied(
                'A witness reference is required')
        now = self._now()
        witness_id = f'gb-wit-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                anchor = db.execute(
                    'SELECT anchor_id FROM gba_anchors'
                    ' WHERE anchor_id = ?', (anchor_id,)).fetchone()
                if anchor is None:
                    raise GlassBoxAuditPlatformDenied('Anchor not found')
                receipt_id = self._record(
                    'GLASS_BOX_WITNESS', actor=actor,
                    anchor_id=anchor_id, witness_kind=witness_kind,
                    reference=reference.strip())
                db.execute(
                    'INSERT INTO gba_witnesses (witness_id, anchor_id,'
                    ' witness_kind, reference, recorded_by,'
                    ' recorded_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (witness_id, anchor_id, witness_kind,
                     reference.strip(), actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gba_witnesses WHERE witness_id = ?',
                (witness_id,)).fetchone()
        return self._witness_view(row)

    def verify_anchor_signature(self, actor, role, anchor_id,
                                signature, public_key_hex, *,
                                region=None):
        """Verify a presented Ed25519 signature over one anchor
        bundle (design Priority 2, consumption side). The signed
        value is the bundle core — the bundle without its signature
        block — under the module's signature domain."""
        self._geo(region)
        self._guard_access(actor, role, anchor_id,
                           'anchor signature verification')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gba_anchors WHERE anchor_id = ?',
                (anchor_id,)).fetchone()
        if row is None:
            raise GlassBoxAuditPlatformDenied('Anchor not found')
        bundle = json.loads(row['bundle_json'])
        core = {k: v for k, v in bundle.items() if k != 'signature'}
        result = self._verify_presented_signature(
            core, ANCHOR_SIGNATURE_DOMAIN, signature, public_key_hex)
        result['anchor_id'] = anchor_id
        result['bundle_hash'] = row['bundle_hash']
        return result

    def verify_registry_signature(self, actor, role, signature,
                                  public_key_hex, *, region=None):
        """Verify a presented signature over the current key-
        registry document (the root-signature consumption side;
        the registry itself ships unsigned until the owner signs
        it — D8/D10)."""
        self._geo(region)
        self._guard_access(actor, role, 'key-registry',
                           'registry signature verification')
        with self._connect() as db:
            document = self._registry_document(db)
        result = self._verify_presented_signature(
            document, REGISTRY_SIGNATURE_DOMAIN, signature,
            public_key_hex)
        result['document_hash'] = _hash(document)
        return result

    # -- completeness verification --------------------------------------

    @staticmethod
    def _incident_view(row):
        return {
            'incident_id': row['incident_id'],
            'verification_id': row['verification_id'],
            'store': row['store'],
            'kind': row['kind'],
            'detail': row['detail'],
            'status': row['status'],
            'detected_at': row['detected_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def _open_incident(self, db, verification_id, store, kind, detail,
                       actor, now):
        """Open an incident inside the caller's transaction, or
        carry the already-open one for the same store and kind —
        an incident is opened once and stays visible until a human
        closes it; evidence is never repaired by this platform."""
        open_row = db.execute(
            "SELECT * FROM gba_incidents WHERE store = ? AND kind = ?"
            " AND status IN ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED')"
            ' ORDER BY detected_at LIMIT 1', (store, kind)).fetchone()
        if open_row is not None:
            view = self._incident_view(open_row)
            view['carried'] = True
            return view
        incident_id = f'gb-inc-{uuid.uuid4().hex[:16]}'
        receipt_id = self._record(
            'GLASS_BOX_INCIDENT', actor=actor,
            incident_id=incident_id, store=store, kind=kind)
        db.execute(
            'INSERT INTO gba_incidents (incident_id, verification_id,'
            ' store, kind, detail, status, detected_at, updated_by,'
            ' updated_at, receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?,'
            ' ?, ?, ?)',
            (incident_id, verification_id, store, kind, detail,
             'DETECTED', now, actor, now, receipt_id),
        )
        row = db.execute(
            'SELECT * FROM gba_incidents WHERE incident_id = ?',
            (incident_id,)).fetchone()
        view = self._incident_view(row)
        view['carried'] = False
        return view

    def run_verification(self, actor, *, region=None):
        """Run one completeness verification over both evidence
        stores (operator only), per design Priority 4: full chain
        integrity, sequence contiguity, and the prefix property
        against the last anchor. The run and every incident it
        opens are receipted; the stores verified are opened
        read-only and are never written."""
        self._geo(region)
        self._require_operator(actor)
        states = {store: self._read_chain(store) for store in STORES}
        with self._connect() as db:
            last = self._last_anchor_row(db)
        last_bundle = json.loads(last['bundle_json']) if last else None
        results = {}
        problems = {}
        for store in STORES:
            state = states[store]
            anchored = (last_bundle['chains'][store]
                        if last_bundle else None)
            prefix = self._prefix_check(store, anchored, state)
            if state['integrity'] == 'BROKEN':
                verdict = 'BROKEN'
                problems.setdefault(store, []).append(
                    ('CHAIN_BROKEN',
                     f"integrity broken at seq"
                     f" {state['first_break_seq']}"))
            elif state['integrity'] == 'UNREADABLE':
                verdict = 'BROKEN'
                problems.setdefault(store, []).append(
                    ('STORE_UNREADABLE', 'store could not be opened'
                                         ' read-only'))
            elif prefix in ('COUNT_REGRESSED', 'PREFIX_DIVERGED'):
                verdict = 'DIVERGED'
                kind = ('COUNT_REGRESSED' if prefix == 'COUNT_REGRESSED'
                        else 'PREFIX_DIVERGED')
                problems.setdefault(store, []).append(
                    (kind, f'prefix property failed: {prefix}'))
            elif state['gaps']:
                verdict = 'INCOMPLETE'
                problems.setdefault(store, []).append(
                    ('SEQUENCE_GAP',
                     f"missing sequences: {state['gaps']}"))
            elif prefix == 'NO_ANCHOR':
                verdict = 'COMPLETE_UNANCHORED'
            else:
                verdict = 'COMPLETE'
            results[store] = {
                'store': store,
                'present': state['present'],
                'count': state['count'],
                'highest_seq': state['highest_seq'],
                'head': state['head'],
                'integrity': state['integrity'],
                'gaps': list(state['gaps']),
                'first_break_seq': state['first_break_seq'],
                'prefix': prefix,
                'verdict': verdict,
            }
        present = [s for s in STORES if states[s]['present']]
        if not present:
            overall = 'NO_EVIDENCE_STORES'
        else:
            overall = max(
                (results[s]['verdict'] for s in present),
                key=lambda v: _STORE_VERDICT_RANK[v])
        now = self._now()
        verification_id = f'gb-ver-{uuid.uuid4().hex[:16]}'
        incidents = []
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'GLASS_BOX_VERIFICATION', actor=actor,
                    verification_id=verification_id, verdict=overall)
                db.execute(
                    'INSERT INTO gba_verifications (verification_id,'
                    ' verified_at, verified_by, glassbox_json,'
                    ' journal_json, verdict, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (verification_id, now, actor,
                     json.dumps(results['glassbox'], sort_keys=True),
                     json.dumps(results['journal'], sort_keys=True),
                     overall, receipt_id),
                )
                for store, items in problems.items():
                    for kind, detail in items:
                        incidents.append(self._open_incident(
                            db, verification_id, store, kind, detail,
                            actor, now))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'verification_id': verification_id,
            'verified_at': now,
            'verified_by': actor,
            'glassbox': results['glassbox'],
            'journal': results['journal'],
            'verdict': overall,
            'incidents': incidents,
        }

    @staticmethod
    def _verification_view(row):
        return {
            'verification_id': row['verification_id'],
            'verified_at': row['verified_at'],
            'verified_by': row['verified_by'],
            'glassbox': json.loads(row['glassbox_json']),
            'journal': json.loads(row['journal_json']),
            'verdict': row['verdict'],
            'receipt_id': row['receipt_id'],
        }

    def verifications_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'verifications',
                           'verifications view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_verifications ORDER BY verified_at',
            ).fetchall()
        return [self._verification_view(row) for row in rows]

    def verification_view(self, actor, role, verification_id, *,
                          region=None):
        self._geo(region)
        self._guard_access(actor, role, verification_id,
                           'verification view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gba_verifications'
                ' WHERE verification_id = ?',
                (verification_id,)).fetchone()
        if row is None:
            raise GlassBoxAuditPlatformDenied('Verification not found')
        return self._verification_view(row)

    def incidents_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'incidents', 'incidents view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_incidents ORDER BY detected_at',
            ).fetchall()
        return [self._incident_view(row) for row in rows]

    def incident_view(self, actor, role, incident_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, incident_id, 'incident view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM gba_incidents WHERE incident_id = ?',
                (incident_id,)).fetchone()
        if row is None:
            raise GlassBoxAuditPlatformDenied('Incident not found')
        return self._incident_view(row)

    def incident_action(self, actor, incident_id, action, *,
                        region=None):
        """Advance one incident's lifecycle (operator only):
        acknowledge / escalate / close. Closing is a human act on
        the record — it never edits the evidence the incident is
        about."""
        self._geo(region)
        self._require_operator(actor)
        transitions = INCIDENT_TRANSITIONS.get(action)
        if transitions is None:
            raise GlassBoxAuditPlatformDenied(
                f'Unknown incident action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM gba_incidents WHERE incident_id = ?',
                    (incident_id,)).fetchone()
                if row is None:
                    raise GlassBoxAuditPlatformDenied(
                        'Incident not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise GlassBoxAuditPlatformDenied(
                        f"Cannot {action} an incident in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'GLASS_BOX_INCIDENT_ACTION', actor=actor,
                    incident_id=incident_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE gba_incidents SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE incident_id = ?',
                    (new_status, actor, now, receipt_id, incident_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM gba_incidents WHERE incident_id = ?',
                (incident_id,)).fetchone()
        return self._incident_view(updated)

    # -- snapshot manifests and restore drills ---------------------------

    @staticmethod
    def _snapshot_view(row):
        return {
            'snapshot_id': row['snapshot_id'],
            'produced_at': row['produced_at'],
            'produced_by': row['produced_by'],
            'manifest': json.loads(row['manifest_json']),
            'manifest_hash': row['manifest_hash'],
            'chain_integrity': row['chain_integrity'],
            'receipt_id': row['receipt_id'],
        }

    def produce_snapshot_manifest(self, actor, *, region=None):
        """Produce one snapshot manifest over the evidence file set
        (operator only), per design §4.2: per-file SHA-256 and size
        bound to both chains' heads and counts, with chain
        integrity recomputed first. A manifest over a broken chain
        is recorded FAILED and opens an incident — it is never
        recorded as good. The copy itself (Object Storage upload,
        retention) is a tenancy act outside this module; nothing
        here creates a bucket or locks anything (D4)."""
        self._geo(region)
        self._require_operator(actor)
        states = {store: self._read_chain(store) for store in STORES}
        manifest, manifest_hash = self._evidence_manifest(states)
        broken = [s for s in STORES
                  if states[s]['integrity'] in ('BROKEN', 'UNREADABLE')]
        chain_integrity = 'FAILED' if broken else 'VERIFIED'
        now = self._now()
        snapshot_id = f'gb-snap-{uuid.uuid4().hex[:16]}'
        manifest_json = json.dumps(manifest, sort_keys=True,
                                   separators=(',', ':'),
                                   ensure_ascii=False)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'GLASS_BOX_SNAPSHOT_MANIFEST', actor=actor,
                    snapshot_id=snapshot_id,
                    manifest_hash=manifest_hash,
                    chain_integrity=chain_integrity)
                db.execute(
                    'INSERT INTO gba_snapshots (snapshot_id,'
                    ' produced_at, produced_by, manifest_json,'
                    ' manifest_hash, chain_integrity, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (snapshot_id, now, actor, manifest_json,
                     manifest_hash, chain_integrity, receipt_id),
                )
                for store in broken:
                    self._open_incident(
                        db, None, store, 'CHAIN_BROKEN',
                        'snapshot manifest produced over a chain'
                        ' that does not verify', actor, now)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gba_snapshots WHERE snapshot_id = ?',
                (snapshot_id,)).fetchone()
        return self._snapshot_view(row)

    def snapshots_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'snapshots', 'snapshots view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_snapshots ORDER BY produced_at',
            ).fetchall()
        return [self._snapshot_view(row) for row in rows]

    @staticmethod
    def _drill_view(row):
        return {
            'drill_id': row['drill_id'],
            'snapshot_id': row['snapshot_id'],
            'drilled_at': row['drilled_at'],
            'recorded_by': row['recorded_by'],
            'glassbox_head_match': bool(row['glassbox_head_match']),
            'journal_head_match': bool(row['journal_head_match']),
            'counts_match': bool(row['counts_match']),
            'outcome': row['outcome'],
            'reported': 'OPERATOR_REPORTED',
            'receipt_id': row['receipt_id'],
        }

    def record_restore_drill(self, actor, snapshot_id,
                             glassbox_head_match, journal_head_match,
                             counts_match, *, region=None):
        """Record one restore drill (operator only), per design
        §4.5: the drill restores a snapshot into scratch and
        compares heads and counts against the snapshot manifest
        and its anchor; the comparisons an operator reports are
        recorded here, labelled operator-reported. The outcome is
        PASSED only when every comparison matches. Restore-to-live
        is a separate owner-gated operation this platform does not
        perform."""
        self._geo(region)
        self._require_operator(actor)
        for flag in (glassbox_head_match, journal_head_match,
                     counts_match):
            if not isinstance(flag, bool):
                raise GlassBoxAuditPlatformDenied(
                    'Drill comparisons must be booleans')
        outcome = ('PASSED' if (glassbox_head_match
                                and journal_head_match and counts_match)
                   else 'FAILED')
        now = self._now()
        drill_id = f'gb-drill-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                snap = db.execute(
                    'SELECT snapshot_id FROM gba_snapshots'
                    ' WHERE snapshot_id = ?',
                    (snapshot_id,)).fetchone()
                if snap is None:
                    raise GlassBoxAuditPlatformDenied(
                        'Snapshot not found')
                receipt_id = self._record(
                    'GLASS_BOX_RESTORE_DRILL', actor=actor,
                    drill_id=drill_id, snapshot_id=snapshot_id,
                    outcome=outcome)
                db.execute(
                    'INSERT INTO gba_drills (drill_id, snapshot_id,'
                    ' drilled_at, recorded_by, glassbox_head_match,'
                    ' journal_head_match, counts_match, outcome,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (drill_id, snapshot_id, now, actor,
                     int(glassbox_head_match), int(journal_head_match),
                     int(counts_match), outcome, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM gba_drills WHERE drill_id = ?',
                (drill_id,)).fetchone()
        return self._drill_view(row)

    def drills_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'drills', 'drills view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM gba_drills ORDER BY drilled_at',
            ).fetchall()
        return [self._drill_view(row) for row in rows]

    # -- status / check-in --------------------------------------------------

    def status(self) -> dict:
        now = self._now()
        states = {store: self._read_chain(store) for store in STORES}
        with self._connect() as db:
            anchors_total = db.execute(
                'SELECT COUNT(*) AS n FROM gba_anchors',
            ).fetchone()['n']
            last_anchor = self._last_anchor_row(db)
            verifications_total = db.execute(
                'SELECT COUNT(*) AS n FROM gba_verifications',
            ).fetchone()['n']
            last_verification = db.execute(
                'SELECT verification_id, verified_at, verdict'
                ' FROM gba_verifications ORDER BY verified_at DESC,'
                ' verification_id DESC LIMIT 1').fetchone()
            incidents_by_status = {s: 0 for s in INCIDENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM gba_incidents'
                    ' GROUP BY status'):
                incidents_by_status[row['status']] = row['n']
            snapshots_total = db.execute(
                'SELECT COUNT(*) AS n FROM gba_snapshots',
            ).fetchone()['n']
            last_drill = db.execute(
                'SELECT drill_id, drilled_at, outcome FROM gba_drills'
                ' ORDER BY drilled_at DESC, drill_id DESC LIMIT 1',
            ).fetchone()
            keys_total = db.execute(
                'SELECT COUNT(*) AS n FROM gba_keys',
            ).fetchone()['n']
            keys_by_status = {s: 0 for s in KEY_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM gba_keys'
                    ' GROUP BY status'):
                keys_by_status[row['status']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        anchor_view = None
        if last_anchor is not None:
            age = now - last_anchor['anchored_at']
            anchor_view = {
                'anchor_id': last_anchor['anchor_id'],
                'anchored_at': last_anchor['anchored_at'],
                'bundle_hash': last_anchor['bundle_hash'],
                'age_seconds': age,
                'fresh': age <= ANCHOR_FRESH_SECONDS,
            }
        drill_view = None
        if last_drill is not None:
            age = now - last_drill['drilled_at']
            drill_view = {
                'drill_id': last_drill['drill_id'],
                'drilled_at': last_drill['drilled_at'],
                'outcome': last_drill['outcome'],
                'age_seconds': age,
                'current': age <= DRILL_CURRENT_SECONDS,
            }
        return {
            'identity': IDENTITY.to_dict(),
            'chains': {store: self._chain_anchor_view(states[store])
                       for store in STORES},
            'anchors_total': anchors_total,
            'last_anchor': anchor_view,
            'anchor_freshness_threshold_seconds': ANCHOR_FRESH_SECONDS,
            'verifications_total': verifications_total,
            'last_verification': (dict(last_verification)
                                  if last_verification else None),
            'incidents_by_status': incidents_by_status,
            'snapshots_total': snapshots_total,
            'last_drill': drill_view,
            'drill_currency_threshold_seconds': DRILL_CURRENT_SECONDS,
            'signing': {
                'status': 'NOT_PROVISIONED',
                'reason': 'signing_key_not_provisioned',
                'reserved_env': SIGNING_KEY_ENV,
            },
            'key_registry': {
                'keys_total': keys_total,
                'keys_by_status': keys_by_status,
                'root_signature': 'NOT_PROVISIONED',
            },
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
                    raise GlassBoxAuditPlatformDenied(str(exc)) from exc
                self._record('GLASS_BOX_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
