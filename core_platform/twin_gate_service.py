"""TwinGate — production RTSA platform (RTSA Build Program Q6).

RECOVERED / REBUILT, stated exactly:

RECOVERED (prototype, untouched): ``core_platform/twin_gate.py`` —
the Twin-Gate prototype: the ``Lease`` shape (lease id, agent,
target, method, permitted methods, payload hash, authority,
human-required flag, single-execution limit, validity window),
the sign-off rule (an authorization is executable only with BOTH
the IT AI Manager's sign-off AND MINOTAUR clearance recorded —
neither substitutes for the other), the human-sign-off gate
(Core Law 5), the §11 quarantine model (any integrity failure —
payload mismatch, replay, scope change, or duplication — destroys
the lease and quarantines the requester), the in-memory
``Vault`` (leases, executions, revocations, verifications) and
its ``GlassBoxAudit``. The prototype's vault is process memory:
leases do not survive a restart, sign-offs are fields rather
than receipted acts, and nothing is queryable after the fact.

REBUILT (this module, 2026-11-24): the production TwinGate
platform — the MASTER §8 Twin-Gate Authorization Chain as a
durable state machine on the shared RTSA foundation
(``core_platform/rtsa_foundation.py``). Every step of the chain
is a receipted act in the platform's own ledger:

    REQUESTED → CLEARED → EXECUTED → VERIFIED → PRESERVED →
    REVOKED   (chain complete: token burned, record closed)
    DENIED    (terminal: refusal — including a MINOTAUR denial,
               which under §10 means no token and no bypass)
    QUARANTINED (terminal: an integrity-class failure under §11;
               the requesting agent is quarantined and cannot
               open new requests until an operator lifts it)

CLEARED is reachable only when BOTH sign-offs are recorded
(§8 step 3: Twin-Gate verifies the dual signature). Execution
authorization re-validates the exact lease at the moment of
execution — identity, target, method scope, payload hash,
commanding authority, validity window, human sign-off — and
binds the Glass-Box receipt hash of the authorization into the
record, so the durable receipt the chain's Preserve step keeps
(§8 step 5) is the authorization's own chain entry. Sign-offs,
clearances, and verifications enter as RECORDED attestation
references from the operator surface: this platform records
them and never fabricates them; the signers are the IT AI
Manager (Q5), MINOTAUR (Q9), the Quality Agent design, and the
human operator, each in its own platform's build.

§20 separation, preserved exactly: TwinGate is not the Vault
(Q3 — lease issuance, revocation authority, and burn records)
and not the prototype's in-memory dataclass of the same name;
this platform authorizes executions under dual control and
keeps the chain record. The prototype module remains in the
repo untouched: ``rtsa_lifecycle`` and the registry probe
import its ``GlassBoxAudit`` and policy dataclasses.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
541519, 518210, 561621, 541690, 561110 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .agent_registry import IT_MANAGER
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
    platform_id='twin_gate',
    name='TwinGate',
    legal_entities=(),
    naics_codes=('541512', '541519', '518210', '561621', '541690', '561110'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

MANAGER_AUTHORITY = IT_MANAGER
"""The only commanding authority a lease may carry (§9)."""

VERIFIER_AGENT = 'Quality Agent'
FAILOVER_AGENT = 'Deployment Agent'
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 3600
EMERGENCY_MAX_TTL_SECONDS = 300
EMERGENCY_CLASS = 'PLATINUM BLUE DIAMOND EMERGENCY'
STANDARD_CLASS = 'STANDARD'
CHAIN_STEPS = ('REQUEST', 'CLEARANCE', 'EXECUTE', 'VERIFY',
               'PRESERVE', 'REVOKE')

STATES = ('REQUESTED', 'CLEARED', 'EXECUTED', 'VERIFIED',
          'PRESERVED', 'REVOKED', 'DENIED', 'QUARANTINED')
TERMINAL_STATES = ('REVOKED', 'DENIED', 'QUARANTINED')

# Integrity-class failures destroy the lease and quarantine the
# requester (§11); every other failure is an ordinary denial.
INTEGRITY_REASONS = frozenset({
    'PAYLOAD_MISMATCH',
    'IDENTITY_OR_TARGET_MISMATCH',
    'METHOD_OUT_OF_SCOPE',
    'COMMAND_AUTHORITY_MISMATCH',
    'REPLAY_OF_CONSUMED_LEASE',
    'POST_EXECUTION_VERIFICATION_FAILED',
})


class TwinGateServiceDenied(Exception):
    """The requested TwinGate operation is not allowed."""


class TwinGateServiceForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class TwinGateService:
    """Durable Twin-Gate authorization chain (§8)."""

    def __init__(self, database_path, operator_verifier, audit, *,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise TwinGateServiceDenied(
                'TwinGate requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'twin_gate', {
            'OPERATOR': {'AUTHORIZATION', 'STATUS'},
            'AUDITOR': {'AUTHORIZATION', 'STATUS'},
            'COORDINATOR': {'AUTHORIZATION', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS twin_gate_authorizations (
                    auth_id TEXT PRIMARY KEY,
                    lease_id TEXT NOT NULL UNIQUE,
                    agent TEXT NOT NULL,
                    target TEXT NOT NULL,
                    method TEXT NOT NULL,
                    permitted_methods TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    authority_class TEXT NOT NULL,
                    emergency INTEGER NOT NULL,
                    max_executions INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    manager_signoff_ref TEXT,
                    minotaur_clearance_ref TEXT,
                    human_signoff_ref TEXT,
                    verification_ref TEXT,
                    execution_receipt_hash TEXT,
                    preserved_ref TEXT,
                    reasons TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    closed_at REAL
                );
                CREATE TABLE IF NOT EXISTS twin_gate_quarantine (
                    agent TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    auth_id TEXT NOT NULL,
                    created_at REAL NOT NULL
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
            raise TwinGateServiceForbidden('an identified actor is required')

    def _is_operator(self, actor):
        if self.operator_verifier is None:
            return False
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise TwinGateServiceForbidden(
                'TwinGate operations require the operator')

    def _record(self, event, **fields):
        return self._audit.preserve(event, platform=IDENTITY.platform_id,
                                    **fields)

    @staticmethod
    def _view(row) -> dict:
        record = dict(row)
        record['permitted_methods'] = json.loads(record['permitted_methods'])
        record['reasons'] = json.loads(record['reasons'])
        record['emergency'] = bool(record['emergency'])
        return record

    def _fetch(self, db, auth_id):
        row = db.execute(
            'SELECT * FROM twin_gate_authorizations WHERE auth_id = ?',
            (auth_id,)).fetchone()
        if row is None:
            raise TwinGateServiceDenied(f'Unknown authorization: {auth_id}')
        return row

    def _quarantined(self, db, agent) -> bool:
        return db.execute(
            'SELECT 1 FROM twin_gate_quarantine WHERE agent = ?',
            (agent,)).fetchone() is not None

    def _quarantine(self, db, agent, reason, auth_id, now):
        db.execute(
            'INSERT OR REPLACE INTO twin_gate_quarantine'
            ' (agent, reason, auth_id, created_at) VALUES (?, ?, ?, ?)',
            (agent, reason, auth_id, now))

    # -- step 1: request ---------------------------------------------

    def open_request(self, actor, agent, target, method, payload_sha256,
                     ttl_seconds, *, emergency=False) -> dict:
        """§8 step 1 + §9 lease shape: open an authorization request.

        The lease binds one agent, one target, one method, and
        one payload hash, under the IT AI Manager's commanding
        authority, for exactly one execution. A quarantined
        agent cannot open requests (§11).
        """
        self._require_operator(actor)
        agent = (agent or '').strip()
        target = (target or '').strip()
        method = (method or '').strip().upper()
        if not agent or not target or not method:
            raise TwinGateServiceDenied(
                'agent, target, and method are all required')
        payload_sha256 = (payload_sha256 or '').strip().lower()
        if (len(payload_sha256) != 64
                or any(c not in '0123456789abcdef' for c in payload_sha256)):
            raise TwinGateServiceDenied(
                'payload_sha256 must be a SHA-256 hex digest')
        ttl = int(ttl_seconds)
        if not MIN_TTL_SECONDS <= ttl <= MAX_TTL_SECONDS:
            raise TwinGateServiceDenied(
                f'ttl_seconds must be between {MIN_TTL_SECONDS} and '
                f'{MAX_TTL_SECONDS}')
        if emergency and ttl > EMERGENCY_MAX_TTL_SECONDS:
            raise TwinGateServiceDenied(
                f'emergency leases are capped at '
                f'{EMERGENCY_MAX_TTL_SECONDS} seconds (§11)')
        now = self._now()
        auth_id = f'auth-{secrets.token_hex(8)}'
        lease_id = f'lease-{secrets.token_hex(8)}'
        with self._connect() as db:
            if self._quarantined(db, agent):
                raise TwinGateServiceDenied(
                    f'Requesting agent is quarantined: {agent}')
            db.execute(
                'INSERT INTO twin_gate_authorizations'
                ' (auth_id, lease_id, agent, target, method,'
                '  permitted_methods, payload_sha256, authority,'
                '  authority_class, emergency, max_executions, state,'
                '  reasons, created_at, expires_at, updated_at)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1,'
                "  'REQUESTED', '[]', ?, ?, ?)",
                (auth_id, lease_id, agent, target, method,
                 json.dumps([method]), payload_sha256, MANAGER_AUTHORITY,
                 EMERGENCY_CLASS if emergency else STANDARD_CLASS,
                 1 if emergency else 0, now, now + ttl, now))
            self._record('TWIN_GATE_REQUEST_OPENED', auth_id=auth_id,
                         lease_id=lease_id, agent=agent, target=target,
                         method=method,
                         authority_class=(EMERGENCY_CLASS if emergency
                                          else STANDARD_CLASS))
            row = self._fetch(db, auth_id)
        return self._view(row)

    # -- step 2/3: sign-offs and clearance ----------------------------

    def record_manager_signoff(self, actor, auth_id, signoff_ref) -> dict:
        """Record the IT AI Manager's sign-off (an attestation
        reference; the Manager's own act lives in its platform).
        CLEARED requires BOTH sign-offs — this one never
        substitutes for MINOTAUR clearance."""
        self._require_operator(actor)
        signoff_ref = (signoff_ref or '').strip()
        if not signoff_ref:
            raise TwinGateServiceDenied('a sign-off reference is required')
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] != 'REQUESTED':
                raise TwinGateServiceDenied(
                    f"sign-off requires REQUESTED, found {row['state']}")
            if row['manager_signoff_ref']:
                raise TwinGateServiceDenied(
                    'manager sign-off already recorded')
            cleared = row['minotaur_clearance_ref'] is not None
            db.execute(
                'UPDATE twin_gate_authorizations SET'
                ' manager_signoff_ref = ?, state = ?, updated_at = ?'
                ' WHERE auth_id = ?',
                (signoff_ref, 'CLEARED' if cleared else 'REQUESTED',
                 now, auth_id))
            self._record('TWIN_GATE_MANAGER_SIGNOFF', auth_id=auth_id,
                         signoff_ref=signoff_ref,
                         cleared='yes' if cleared else 'no')
            row = self._fetch(db, auth_id)
        return self._view(row)

    def record_minotaur_clearance(self, actor, auth_id, clearance_ref,
                                  decision='CLEARED') -> dict:
        """Record MINOTAUR's independent clearance decision.

        A DENIED decision closes the authorization as DENIED —
        under §10 a MINOTAUR denial means no token and no
        bypass, terminally. A CLEARED decision never substitutes
        for the Manager's sign-off.
        """
        self._require_operator(actor)
        clearance_ref = (clearance_ref or '').strip()
        if not clearance_ref:
            raise TwinGateServiceDenied('a clearance reference is required')
        decision = (decision or '').strip().upper()
        if decision not in ('CLEARED', 'DENIED'):
            raise TwinGateServiceDenied(
                "decision must be 'CLEARED' or 'DENIED'")
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] != 'REQUESTED':
                raise TwinGateServiceDenied(
                    f"clearance requires REQUESTED, found {row['state']}")
            if row['minotaur_clearance_ref']:
                raise TwinGateServiceDenied(
                    'MINOTAUR clearance already recorded')
            if decision == 'DENIED':
                db.execute(
                    'UPDATE twin_gate_authorizations SET'
                    ' minotaur_clearance_ref = ?, state = ?,'
                    ' reasons = ?, updated_at = ?, closed_at = ?'
                    ' WHERE auth_id = ?',
                    (clearance_ref, 'DENIED',
                     json.dumps(['MINOTAUR_DENIED']), now, now, auth_id))
                self._record('TWIN_GATE_MINOTAUR_DENIED', auth_id=auth_id,
                             clearance_ref=clearance_ref)
            else:
                cleared = row['manager_signoff_ref'] is not None
                db.execute(
                    'UPDATE twin_gate_authorizations SET'
                    ' minotaur_clearance_ref = ?, state = ?,'
                    ' updated_at = ? WHERE auth_id = ?',
                    (clearance_ref, 'CLEARED' if cleared else 'REQUESTED',
                     now, auth_id))
                self._record('TWIN_GATE_MINOTAUR_CLEARANCE',
                             auth_id=auth_id, clearance_ref=clearance_ref,
                             cleared='yes' if cleared else 'no')
            row = self._fetch(db, auth_id)
        return self._view(row)

    def record_human_signoff(self, actor, auth_id, signoff_ref) -> dict:
        """Record the human operator's sign-off (Core Law 5).

        Required before execution; may be recorded while the
        authorization is REQUESTED or CLEARED.
        """
        self._require_operator(actor)
        signoff_ref = (signoff_ref or '').strip()
        if not signoff_ref:
            raise TwinGateServiceDenied('a sign-off reference is required')
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] not in ('REQUESTED', 'CLEARED'):
                raise TwinGateServiceDenied(
                    f"human sign-off requires REQUESTED or CLEARED,"
                    f" found {row['state']}")
            if row['human_signoff_ref']:
                raise TwinGateServiceDenied(
                    'human sign-off already recorded')
            db.execute(
                'UPDATE twin_gate_authorizations SET'
                ' human_signoff_ref = ?, updated_at = ? WHERE auth_id = ?',
                (signoff_ref, now, auth_id))
            self._record('TWIN_GATE_HUMAN_SIGNOFF', auth_id=auth_id,
                         signoff_ref=signoff_ref)
            row = self._fetch(db, auth_id)
        return self._view(row)

    # -- step 3/4: execution authorization ----------------------------

    def authorize_execution(self, actor, auth_id, agent, target, method,
                            payload_sha256) -> dict:
        """§8 steps 3–4: re-validate the lease exactly, then
        authorize the single execution.

        Every presented field is compared against the recorded
        lease. Integrity-class mismatches (payload, identity or
        target, method scope, authority, replay of a consumed
        lease) destroy the authorization and quarantine the
        requesting agent (§11); ordinary failures (not cleared,
        outside the validity window, human sign-off missing)
        deny and close it. On success the Glass-Box receipt hash
        of this authorization is bound into the record — the
        durable receipt the Preserve step keeps.
        """
        self._check_actor(actor)
        now = self._now()
        denial = None
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            state = row['state']
            reasons: list[str] = []
            if state in ('EXECUTED', 'VERIFIED', 'PRESERVED', 'REVOKED'):
                reasons.append('REPLAY_OF_CONSUMED_LEASE')
            elif state != 'CLEARED':
                reasons.append('TWIN_GATE_NOT_CLEARED')
            if (agent or '').strip() != row['agent'] \
                    or (target or '').strip() != row['target']:
                reasons.append('IDENTITY_OR_TARGET_MISMATCH')
            presented_method = (method or '').strip().upper()
            if presented_method != row['method'] \
                    or presented_method not in json.loads(
                        row['permitted_methods']):
                reasons.append('METHOD_OUT_OF_SCOPE')
            if (payload_sha256 or '').strip().lower() \
                    != row['payload_sha256']:
                reasons.append('PAYLOAD_MISMATCH')
            if row['authority'] != MANAGER_AUTHORITY:
                reasons.append('COMMAND_AUTHORITY_MISMATCH')
            if not row['created_at'] <= now < row['expires_at']:
                reasons.append('LEASE_OUTSIDE_VALIDITY')
            if not row['human_signoff_ref']:
                reasons.append('HUMAN_APPROVAL_MISSING')
            if reasons:
                integrity = [r for r in reasons if r in INTEGRITY_REASONS]
                if integrity:
                    db.execute(
                        'UPDATE twin_gate_authorizations SET state = ?,'
                        ' reasons = ?, updated_at = ?, closed_at = ?'
                        ' WHERE auth_id = ?',
                        ('QUARANTINED', json.dumps(reasons), now, now,
                         auth_id))
                    self._quarantine(db, row['agent'], integrity[0],
                                      auth_id, now)
                    self._record('TWIN_GATE_QUARANTINED', auth_id=auth_id,
                                 agent=row['agent'],
                                 reasons=','.join(reasons))
                else:
                    db.execute(
                        'UPDATE twin_gate_authorizations SET state = ?,'
                        ' reasons = ?, updated_at = ?, closed_at = ?'
                        ' WHERE auth_id = ?',
                        ('DENIED', json.dumps(reasons), now, now, auth_id))
                    self._record('TWIN_GATE_EXECUTION_DENIED',
                                 auth_id=auth_id, agent=row['agent'],
                                 reasons=','.join(reasons))
                # The denial/quarantine state change must COMMIT
                # before the refusal is raised: raising inside the
                # transaction would roll the containment back.
                denial = reasons
            else:
                receipt_hash = self._record(
                    'TWIN_GATE_EXECUTION_AUTHORIZED', auth_id=auth_id,
                    lease_id=row['lease_id'], agent=row['agent'],
                    target=row['target'], method=row['method'])
                db.execute(
                    'UPDATE twin_gate_authorizations SET state = ?,'
                    ' execution_receipt_hash = ?, reasons = ?,'
                    ' updated_at = ? WHERE auth_id = ?',
                    ('EXECUTED', receipt_hash, '[]', now, auth_id))
                row = self._fetch(db, auth_id)
                return self._view(row)
        raise TwinGateServiceDenied(
            'Twin-Gate execution denied: ' + ', '.join(denial))

    # -- step 4 (second half): post-execution verification ------------

    def record_verification(self, actor, auth_id, verification_ref,
                            result) -> dict:
        """§8 step 4: record the post-execution verification
        (bound to the Quality Agent design; the verification
        enters as its recorded reference). A FAILED verification
        is an integrity event: the authorization is quarantined
        and the requesting agent quarantined with it (§11)."""
        self._require_operator(actor)
        verification_ref = (verification_ref or '').strip()
        if not verification_ref:
            raise TwinGateServiceDenied(
                'a verification reference is required')
        result = (result or '').strip().upper()
        if result not in ('VERIFIED', 'FAILED'):
            raise TwinGateServiceDenied(
                "result must be 'VERIFIED' or 'FAILED'")
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] != 'EXECUTED':
                raise TwinGateServiceDenied(
                    f"verification requires EXECUTED, found {row['state']}")
            if result == 'FAILED':
                reasons = ['POST_EXECUTION_VERIFICATION_FAILED']
                db.execute(
                    'UPDATE twin_gate_authorizations SET state = ?,'
                    ' verification_ref = ?, reasons = ?, updated_at = ?,'
                    ' closed_at = ? WHERE auth_id = ?',
                    ('QUARANTINED', verification_ref, json.dumps(reasons),
                     now, now, auth_id))
                self._quarantine(db, row['agent'], reasons[0], auth_id, now)
                self._record('TWIN_GATE_QUARANTINED', auth_id=auth_id,
                             agent=row['agent'],
                             reasons=','.join(reasons),
                             verification_ref=verification_ref)
            else:
                db.execute(
                    'UPDATE twin_gate_authorizations SET state = ?,'
                    ' verification_ref = ?, updated_at = ?'
                    ' WHERE auth_id = ?',
                    ('VERIFIED', verification_ref, now, auth_id))
                self._record('TWIN_GATE_POST_EXECUTION_VERIFIED',
                             auth_id=auth_id,
                             verification_ref=verification_ref,
                             verifier=VERIFIER_AGENT)
            row = self._fetch(db, auth_id)
        return self._view(row)

    # -- step 5: preserve ----------------------------------------------

    def preserve_receipt(self, actor, auth_id) -> dict:
        """§8 step 5: preserve the execution receipt in the
        Glass-Box record — the preserved reference is the digest
        of the authorization record together with its bound
        execution receipt hash."""
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] != 'VERIFIED':
                raise TwinGateServiceDenied(
                    f"preserve requires VERIFIED, found {row['state']}")
            canonical = json.dumps(
                {'auth_id': row['auth_id'], 'lease_id': row['lease_id'],
                 'agent': row['agent'], 'target': row['target'],
                 'method': row['method'],
                 'payload_sha256': row['payload_sha256'],
                 'execution_receipt_hash': row['execution_receipt_hash'],
                 'verification_ref': row['verification_ref']},
                sort_keys=True, separators=(',', ':'))
            preserved_ref = hashlib.sha256(
                canonical.encode('utf-8')).hexdigest()
            db.execute(
                'UPDATE twin_gate_authorizations SET state = ?,'
                ' preserved_ref = ?, updated_at = ? WHERE auth_id = ?',
                ('PRESERVED', preserved_ref, now, auth_id))
            self._record('TWIN_GATE_RECEIPT_PRESERVED', auth_id=auth_id,
                         preserved_ref=preserved_ref)
            row = self._fetch(db, auth_id)
        return self._view(row)

    # -- step 6: revoke --------------------------------------------------

    def revoke(self, actor, auth_id) -> dict:
        """§8 step 6: revoke the lease and burn the token.

        From PRESERVED this completes the chain (baseline
        restored, record closed). From REQUESTED or CLEARED it is
        the operator's pre-execution revocation. From EXECUTED
        or VERIFIED it is refused — the chain completes through
        verification and preservation first (deterministic
        containment, never a silent skip)."""
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            row = self._fetch(db, auth_id)
            if row['state'] in TERMINAL_STATES:
                raise TwinGateServiceDenied(
                    f"authorization is already {row['state']}")
            if row['state'] in ('EXECUTED', 'VERIFIED'):
                raise TwinGateServiceDenied(
                    f"revocation from {row['state']} is refused: the"
                    ' chain completes through verification and'
                    ' preservation first')
            phase = ('CHAIN_COMPLETE' if row['state'] == 'PRESERVED'
                     else 'PRE_EXECUTION')
            db.execute(
                'UPDATE twin_gate_authorizations SET state = ?,'
                ' updated_at = ?, closed_at = ? WHERE auth_id = ?',
                ('REVOKED', now, now, auth_id))
            self._record('TWIN_GATE_REVOKED', auth_id=auth_id,
                         lease_id=row['lease_id'], phase=phase)
            row = self._fetch(db, auth_id)
        return self._view(row)

    # -- quarantine administration ---------------------------------------

    def lift_quarantine(self, actor, agent) -> dict:
        """Operator-only: lift a requester's quarantine (§11 —
        quarantine is a containment state, lifted only by an
        operator act, never automatically)."""
        self._require_operator(actor)
        agent = (agent or '').strip()
        now = self._now()
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM twin_gate_quarantine WHERE agent = ?',
                (agent,)).fetchone()
            if row is None:
                raise TwinGateServiceDenied(
                    f'Agent is not quarantined: {agent}')
            db.execute('DELETE FROM twin_gate_quarantine WHERE agent = ?',
                       (agent,))
            self._record('TWIN_GATE_QUARANTINE_LIFTED', agent=agent,
                         reason=row['reason'])
            return {'agent': agent, 'reason': row['reason'],
                    'auth_id': row['auth_id'], 'lifted_at': now}

    def quarantined_agents(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM twin_gate_quarantine ORDER BY agent'
            ).fetchall()
        return [dict(r) for r in rows]

    # -- reads -------------------------------------------------------------

    def authorization_view(self, actor, role, auth_id) -> dict:
        """Serve one authorization under the access guard: access
        is authorized and receipted FIRST, and only then is the
        record fetched and served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'AUTHORIZATION', auth_id,
                              purpose='authorization view')
        except FoundationForbidden as exc:
            raise TwinGateServiceForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise TwinGateServiceDenied(str(exc)) from exc
        with self._connect() as db:
            return self._view(self._fetch(db, auth_id))

    def status(self) -> dict:
        with self._connect() as db:
            counts = {state: 0 for state in STATES}
            for row in db.execute(
                    'SELECT state, COUNT(*) AS n FROM'
                    ' twin_gate_authorizations GROUP BY state'):
                counts[row['state']] = row['n']
            quarantined = db.execute(
                'SELECT COUNT(*) AS n FROM twin_gate_quarantine'
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'commanding_authority': MANAGER_AUTHORITY,
            'chain_steps': list(CHAIN_STEPS),
            'authorization_counts': counts,
            'quarantined_agents': quarantined,
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
                    raise TwinGateServiceDenied(str(exc)) from exc
                self._record('TWIN_GATE_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
