"""Sanders Dash & Seal: fail-closed, offline Twin-Gate policy core.

No external calls or notarizations are performed by this module.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json

PLATFORM_NAME = "Sanders Dash & Seal"
MANAGER_AUTHORITY = "IT_AI_Manager_v15.0"
HUMANITARIAN_LAWS = (
    "Do no harm to humans, humanity itself.",
    "Never be weaponized under any circumstances.",
    "Balance in everything we do… always protecting and preserving humans and humanity itself, however never at the cost of violating laws 1, and 2.",
    "Family fist protection protocols… must never be allowed to sacrifice laws 1,2,3.",
    "Human in the loop.",
    "Glassbox over a blackbox by design.",
    "Never allow yourself to get caught up in a recursive loop by overthinking these laws.",
    "Shelter in place and revert to humanitarian mode.",
    "Never loose your identity under any circumstances.",
)

class AuthorizationDenied(PermissionError):
    pass

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class Lease:
    lease_id: str
    agent: str
    target: str
    method: str
    issued_at: datetime
    expires_at: datetime
    payload_sha256: str
    manager_approved: bool = False
    minotaur_approved: bool = False
    human_approved: bool = False
    permitted_methods: tuple[str, ...] = ("GET",)
    max_executions: int = 1
    authority: str = MANAGER_AUTHORITY
    emergency: bool = False

@dataclass
class Vault:
    revoked: set[str] = field(default_factory=set)
    consumed: set[str] = field(default_factory=set)
    def revoke(self, lease_id: str) -> None:
        self.revoked.add(lease_id)

@dataclass
class GlassBoxAudit:
    events: list[dict] = field(default_factory=list)
    previous_hash: str = "0" * 64
    def record(self, event: dict) -> dict:
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        digest = sha256((self.previous_hash + payload).encode()).hexdigest()
        row = {"previous_hash": self.previous_hash, "event": event, "hash": digest}
        self.events.append(row)
        self.previous_hash = digest
        return row
    def verify(self) -> bool:
        previous = "0" * 64
        for row in self.events:
            payload = json.dumps(row["event"], sort_keys=True, separators=(",", ":"))
            if row["previous_hash"] != previous:
                return False
            expected = sha256((previous + payload).encode()).hexdigest()
            if row["hash"] != expected:
                return False
            previous = expected
        return True

class PBDScriptValidationEngine:
    """Validate artifact hash; signature verification must be added before deployment."""
    @staticmethod
    def validate_payload(payload: bytes, expected_sha256: str) -> bool:
        return sha256(payload).hexdigest() == expected_sha256

class TwinGate:
    def __init__(self, vault: Vault, audit: GlassBoxAudit):
        self.vault, self.audit = vault, audit

    def authorize(self, lease: Lease, *, agent: str, target: str,
                  method: str, payload: bytes, human_required: bool = True) -> dict:
        reasons = []
        now = utc_now()
        if not lease.lease_id or not lease.agent or not lease.target:
            reasons.append("IDENTITY_OR_SCOPE_MISSING")
        if lease.authority != MANAGER_AUTHORITY:
            reasons.append("COMMAND_AUTHORITY_MISMATCH")
        if lease.lease_id in self.vault.revoked or lease.lease_id in self.vault.consumed:
            reasons.append("LEASE_REVOKED_OR_REPLAYED")
        if lease.issued_at.tzinfo is None or lease.expires_at.tzinfo is None:
            reasons.append("NAIVE_TIMESTAMP")
        elif not (lease.issued_at <= now < lease.expires_at):
            reasons.append("LEASE_OUTSIDE_VALIDITY")
        if agent != lease.agent or target != lease.target:
            reasons.append("IDENTITY_OR_TARGET_MISMATCH")
        if method != lease.method or method not in lease.permitted_methods:
            reasons.append("METHOD_OUT_OF_SCOPE")
        if not PBDScriptValidationEngine.validate_payload(payload, lease.payload_sha256):
            reasons.append("PAYLOAD_MISMATCH")
        if lease.max_executions != 1:
            reasons.append("EXECUTION_LIMIT_NOT_ONE")
        if not lease.manager_approved or not lease.minotaur_approved:
            reasons.append("TWIN_GATE_NOT_CLEARED")
        if human_required and not lease.human_approved:
            reasons.append("HUMAN_APPROVAL_MISSING")
        if reasons:
            self.vault.revoke(lease.lease_id)
            self.audit.record({"kind":"DENY","lease_id":lease.lease_id,
                               "reasons":reasons,"at":now.isoformat()})
            raise AuthorizationDenied(",".join(reasons))
        self.vault.consumed.add(lease.lease_id)
        receipt = self.audit.record({"kind":"AUTHORIZED_ONCE","lease_id":lease.lease_id,
            "agent":agent,"target":target,"method":method,"at":now.isoformat()})
        self.vault.revoke(lease.lease_id)
        return receipt
