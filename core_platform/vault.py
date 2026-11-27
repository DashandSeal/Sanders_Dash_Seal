"""
Module: core_platform.vault
Architectural Layer: Vault — the MASTER §20 temporary-authority
lifecycle platform: issuance, expiration, revocation, and
destruction of execution leases (§8 step 6: "Vault revokes /
burns temporary token"; §9: the Execution Lease). A separate
platform per §20 — never merged with PBDScriptValidationEngine,
PBDManifestGenerator, the Global PBD Sentinel, or Glass-Box
Audit.

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (records only, stated exactly): the platform's designed
purpose in the MASTER (Sanders_Dash_Seal_Actual_Build_Design_
MASTER_2026-10-11.md): §20, "Token / lease issuance,
expiration, revocation, destruction"; the §9 Execution Lease
record shape — lease_id, issued_timestamp, expiration_timestamp,
nonce, requesting agent identity, commanding authority
(IT_AI_Manager_v15.0), target endpoint, allowed execution verbs,
maximum execution limit — and its law: "The AI system may execute
only within the active lease boundary. When the lease expires or
the execution limit is reached, authority returns to baseline";
and §8's post-execution sequence — evidence preserved first,
then temporary authority destroyed, then return to baseline. No
Vault platform module existed in any examined source (the
143-identity reconciliation, catalog row 22). The small internal
`Vault` dataclass inside core_platform/twin_gate.py — which holds
that module's own approval entries — is a different component and
is untouched by this build; this platform does not read, wrap, or
replace it.

REBUILT (everything executable in this module): the lease
lifecycle service below, built 2026-11-24 under the owner's RTSA
build program on the shared foundation
(core_platform.rtsa_foundation): its own platform identity, a
lease ledger in its own store, Glass-Box receipts for every
lifecycle transition inside the ledger transaction, receipted
record access through the foundation AccessGuard, and
operator-only issuance, revocation, burn, sweep, and
recall-pattern check-in.

LEASE SEMANTICS — stated exactly:

* Issuance is an operator authority in this build. A lease is
  issued to a named requesting agent for ONE target endpoint and
  a named set of allowed execution verbs, with a maximum
  execution count and a short lifetime (build configuration: 60
  seconds minimum, 3600 seconds maximum — the MASTER's example
  lease is five minutes).
* The lease token is returned to the caller ONCE, at issuance.
  The ledger stores only the token's SHA-256 hash — never the
  token itself. A lost token cannot be recovered from this
  service; the lease must be revoked or burned and a new one
  issued.
* Verification is fail-closed and does not consume: an unknown,
  expired, revoked, burned, or exhausted token is invalid, as is
  a token presented for a different endpoint or verb than the
  lease allows.
* Consumption is the governed act: it validates the token against
  its boundary inside one transaction, increments the execution
  count, writes the Glass-Box receipt inside the same
  transaction, and — when the execution limit is reached — closes
  the lease EXHAUSTED: authority returns to baseline, per §9.
* Revocation suspends a lease immediately; burning destroys the
  temporary authority (§8 step 6). Both are terminal, as are
  EXPIRED and EXHAUSTED. No transition out of a terminal state
  exists.
* Authorization metadata presented at issuance (for example
  Twin-Gate sign-off references) is RECORDED, never verified by
  this platform and never fabricated: the Vault records what
  authority was presented; it does not confer the authority.

Fail-closed throughout: a Glass-Box audit adapter is required at
construction — no record, no action. Python standard library
only. No secrets beyond the lease tokens it issues, no network,
no external calls.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
518210, 541519, 561621, 541511, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
"""

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    latest_check_in as _foundation_latest_check_in,
    record_check_in as _foundation_record_check_in,
    validate_identity,
)


class VaultDenied(ValueError):
    """The requested lease operation is invalid or cannot be
    evidenced, so it does not occur."""


class VaultForbidden(ValueError):
    """The actor lacks authority for this lease operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='vault',
    name='Vault',
    legal_entities=(),
    naics_codes=('541512', '518210', '541519', '561621', '541511', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The MASTER §9 commanding authority recorded on every lease.
COMMANDING_AUTHORITY = 'IT_AI_Manager_v15.0'

LEASE_STATUSES = ('ACTIVE', 'EXPIRED', 'REVOKED', 'BURNED', 'EXHAUSTED')
TERMINAL_STATUSES = frozenset(
    ('EXPIRED', 'REVOKED', 'BURNED', 'EXHAUSTED'))

# Build configuration: lease lifetimes are short-lived per §9
# (the MASTER's example lease is five minutes).
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 3600


class Vault:
    """The REBUILT Vault service: the full §9 lease lifecycle —
    operator-issued, hash-stored, boundary-verified,
    receipt-consumed, revocable, burnable temporary authority —
    every transition recorded in its own lease ledger and
    receipted to the Glass-Box chain inside the transaction."""

    def __init__(self, database, operator_verifier=None, audit=None,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise VaultDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'vault', {
            'OPERATOR': {'LEASE', 'STATUS'},
            'AUDITOR': {'LEASE', 'STATUS'},
            'COORDINATOR': {'LEASE', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS vault_leases (
                lease_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL UNIQUE,
                nonce TEXT NOT NULL,
                requesting_agent TEXT NOT NULL,
                commanding_authority TEXT NOT NULL,
                target_endpoint TEXT NOT NULL,
                allowed_verbs TEXT NOT NULL,
                max_executions INTEGER NOT NULL,
                executions_used INTEGER NOT NULL DEFAULT 0,
                authorization_metadata TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                issued_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                closed_at INTEGER
            );""")

    # -- plumbing ----------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row
        return db

    def _now(self):
        return int(self.clock())

    def _is_operator(self, actor):
        if self.operator_verifier is None:
            return False
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    @staticmethod
    def _check_actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise VaultDenied('Invalid actor identity')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @staticmethod
    def _lease_view(row):
        """The served lease view. The token is never in it (it is
        returned once, at issuance), and neither is the full token
        hash."""
        return {
            'lease_id': row['lease_id'],
            'requesting_agent': row['requesting_agent'],
            'commanding_authority': row['commanding_authority'],
            'target_endpoint': row['target_endpoint'],
            'allowed_verbs': json.loads(row['allowed_verbs']),
            'max_executions': row['max_executions'],
            'executions_used': row['executions_used'],
            'authorization_metadata': json.loads(
                row['authorization_metadata']),
            'status': row['status'],
            'issued_at': row['issued_at'],
            'expires_at': row['expires_at'],
            'closed_at': row['closed_at'],
        }

    def _counts(self, db):
        counts = {status: 0 for status in LEASE_STATUSES}
        for row in db.execute(
                "SELECT status, COUNT(*) AS n FROM vault_leases "
                "GROUP BY status;").fetchall():
            if row['status'] in counts:
                counts[row['status']] = row['n']
        return counts

    # -- issuance ------------------------------------------------------

    def issue_lease(self, actor, requesting_agent, target_endpoint,
                    allowed_verbs, ttl_seconds, max_executions=1,
                    authorization_metadata=None):
        """Issue one execution lease (operator-only) and return its
        view WITH the lease token — the only time the token is
        ever served. Only the token's SHA-256 hash is stored."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise VaultForbidden('Lease issuance is an operator authority')
        if not isinstance(requesting_agent, str) or \
                not requesting_agent.strip():
            raise VaultDenied('A requesting agent identity is required')
        if not isinstance(target_endpoint, str) or \
                not target_endpoint.strip():
            raise VaultDenied('A target endpoint is required')
        if not isinstance(allowed_verbs, (list, tuple)) or \
                not allowed_verbs or any(
                    not isinstance(verb, str) or not verb.strip()
                    for verb in allowed_verbs):
            raise VaultDenied(
                'allowed_verbs must be a non-empty list of verbs')
        verbs = sorted({verb.strip().upper() for verb in allowed_verbs})
        if not isinstance(ttl_seconds, int) or \
                ttl_seconds < MIN_TTL_SECONDS or \
                ttl_seconds > MAX_TTL_SECONDS:
            raise VaultDenied(
                f'Lease lifetime must be between {MIN_TTL_SECONDS} '
                f'and {MAX_TTL_SECONDS} seconds')
        if not isinstance(max_executions, int) or max_executions < 1:
            raise VaultDenied('max_executions must be at least 1')
        if authorization_metadata is None:
            metadata = {}
        elif isinstance(authorization_metadata, dict):
            metadata = authorization_metadata
        else:
            raise VaultDenied('authorization_metadata must be an object')
        now = self._now()
        lease_id = 'lease-' + secrets.token_urlsafe(12)
        token = 'sds-lease-' + secrets.token_urlsafe(32)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO vault_leases (lease_id, token_hash, "
                    "nonce, requesting_agent, commanding_authority, "
                    "target_endpoint, allowed_verbs, max_executions, "
                    "executions_used, authorization_metadata, status, "
                    "issued_at, expires_at, closed_at) VALUES (?, ?, "
                    "?, ?, ?, ?, ?, ?, 0, ?, 'ACTIVE', ?, ?, NULL);",
                    (lease_id, self._token_hash(token),
                     secrets.token_hex(16), requesting_agent.strip(),
                     COMMANDING_AUTHORITY, target_endpoint.strip(),
                     json.dumps(verbs), max_executions,
                     json.dumps(metadata, sort_keys=True),
                     now, now + ttl_seconds))
                self._record('VAULT_LEASE_ISSUED', actor=actor,
                             lease_id=lease_id,
                             requesting_agent=requesting_agent.strip(),
                             target_endpoint=target_endpoint.strip(),
                             max_executions=max_executions,
                             expires_at=now + ttl_seconds)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM vault_leases WHERE lease_id = ?;",
                (lease_id,)).fetchone()
            view = self._lease_view(row)
        view['token'] = token
        return view

    # -- verification and consumption -----------------------------------

    def _boundary_check(self, row, endpoint, verb):
        """Return (valid, reason) for a lease row against a
        presented endpoint/verb. Pure boundary logic; expiry is
        evaluated against the clock here so verification and
        consumption agree."""
        if row is None:
            return False, 'UNKNOWN_TOKEN'
        if row['status'] in TERMINAL_STATUSES:
            return False, f"LEASE_{row['status']}"
        if self._now() >= row['expires_at']:
            return False, 'LEASE_EXPIRED'
        if endpoint is not None and endpoint != row['target_endpoint']:
            return False, 'ENDPOINT_MISMATCH'
        if verb is not None and \
                verb.strip().upper() not in json.loads(row['allowed_verbs']):
            return False, 'VERB_NOT_ALLOWED'
        return True, 'WITHIN_BOUNDARY'

    def verify_token(self, token, endpoint=None, verb=None):
        """Fail-closed boundary verification. Read-only: verifies
        without consuming and without writing a receipt (a check is
        not an action; consumption is)."""
        if not isinstance(token, str) or not token.strip():
            return {'valid': False, 'reason': 'INVALID_TOKEN'}
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM vault_leases WHERE token_hash = ?;",
                (self._token_hash(token),)).fetchone()
        valid, reason = self._boundary_check(row, endpoint, verb)
        result = {'valid': valid, 'reason': reason}
        if row is not None:
            result['lease_id'] = row['lease_id']
        return result

    def consume_execution(self, actor, token, endpoint, verb):
        """Consume one execution under a lease: validate the token
        against its boundary, increment the execution count, and
        receipt — all inside one transaction. Reaching the
        execution limit closes the lease EXHAUSTED (authority
        returns to baseline, §9). A failed validation consumes
        nothing and records nothing."""
        self._check_actor(actor)
        if not isinstance(token, str) or not token.strip():
            raise VaultDenied('A lease token is required')
        if not isinstance(endpoint, str) or not endpoint.strip() or \
                not isinstance(verb, str) or not verb.strip():
            raise VaultDenied(
                'Consumption requires the target endpoint and verb')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = db.execute(
                    "SELECT * FROM vault_leases WHERE token_hash = ?;",
                    (self._token_hash(token),)).fetchone()
                valid, reason = self._boundary_check(row, endpoint, verb)
                if not valid:
                    raise VaultDenied(
                        f'Lease does not authorize this execution: '
                        f'{reason}')
                used = row['executions_used'] + 1
                new_status = 'EXHAUSTED' if used >= row['max_executions'] \
                    else 'ACTIVE'
                closed_at = self._now() if new_status in TERMINAL_STATUSES \
                    else None
                db.execute(
                    "UPDATE vault_leases SET executions_used = ?, "
                    "status = ?, closed_at = ? WHERE lease_id = ?;",
                    (used, new_status, closed_at, row['lease_id']))
                self._record('VAULT_EXECUTION_CONSUMED', actor=actor,
                             lease_id=row['lease_id'],
                             endpoint=endpoint,
                             verb=verb.strip().upper(),
                             executions_used=used,
                             status=new_status)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM vault_leases WHERE lease_id = ?;",
                (row['lease_id'],)).fetchone()
            return self._lease_view(row)

    # -- closure ---------------------------------------------------------

    def _close_lease(self, actor, lease_id, new_status, stage):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise VaultForbidden(
                'Lease closure is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = db.execute(
                    "SELECT * FROM vault_leases WHERE lease_id = ?;",
                    (lease_id,)).fetchone()
                if row is None:
                    raise VaultDenied('Unknown lease')
                if row['status'] in TERMINAL_STATUSES:
                    raise VaultDenied(
                        f"Lease is already {row['status']}; terminal "
                        'states have no outgoing transitions')
                db.execute(
                    "UPDATE vault_leases SET status = ?, closed_at = ? "
                    "WHERE lease_id = ?;",
                    (new_status, self._now(), lease_id))
                self._record(stage, actor=actor, lease_id=lease_id,
                             previous_status=row['status'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM vault_leases WHERE lease_id = ?;",
                (lease_id,)).fetchone()
            return self._lease_view(row)

    def revoke_lease(self, actor, lease_id):
        """Revoke a lease immediately (operator-only): its
        authority is suspended and the lease is terminal."""
        return self._close_lease(actor, lease_id, 'REVOKED',
                                 'VAULT_LEASE_REVOKED')

    def burn_lease(self, actor, lease_id):
        """Burn a lease (operator-only): the temporary authority
        is destroyed, per MASTER §8 step 6."""
        return self._close_lease(actor, lease_id, 'BURNED',
                                 'VAULT_LEASE_BURNED')

    def sweep_expired(self, actor):
        """Operator-only: close every ACTIVE lease past its
        expiration as EXPIRED, with one summary receipt. Returns
        the number of leases closed."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise VaultForbidden('Expiry sweep is an operator authority')
        now = self._now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                stale = db.execute(
                    "SELECT lease_id FROM vault_leases WHERE "
                    "status = 'ACTIVE' AND expires_at <= ?;",
                    (now,)).fetchall()
                for row in stale:
                    db.execute(
                        "UPDATE vault_leases SET status = 'EXPIRED', "
                        "closed_at = ? WHERE lease_id = ?;",
                        (now, row['lease_id']))
                if stale:
                    self._record('VAULT_LEASES_EXPIRED', actor=actor,
                                 leases_expired=len(stale))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'leases_expired': len(stale)}

    def lease_view(self, actor, role, lease_id):
        """Serve one lease under the access guard: access is
        authorized and receipted FIRST, and only then is the
        record fetched and served. The token and its full hash are
        never served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'LEASE', lease_id,
                              purpose='lease view')
        except FoundationForbidden as exc:
            raise VaultForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise VaultDenied(str(exc)) from exc
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM vault_leases WHERE lease_id = ?;",
                (lease_id,)).fetchone()
            if row is None:
                raise VaultDenied('Unknown lease')
            return self._lease_view(row)

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise VaultForbidden('Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise VaultDenied(str(exc)) from exc
                self._record('VAULT_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    # -- status --------------------------------------------------------

    def status(self):
        """Platform status: identity, the commanding authority,
        lease counts by status, and the latest check-in."""
        with self._connect() as db:
            counts = self._counts(db)
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'commanding_authority': COMMANDING_AUTHORITY,
            'lease_counts': counts,
            'latest_check_in': latest,
        }
