"""Sanders Dash & Seal — bounded RTSA assessment lifecycle.

Advisory-only workflow: REQUEST -> CLEARANCE -> VERIFY -> PRESERVE -> REVOKE.
No external operations are executed. Production Twin-Gate requires separately
verified cryptographic identity, signatures, durable nonce storage, and receipts.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from core_platform.rtsa_registry import get_rtsa
from core_platform.rtsa_assessments import assess, Assessment
from core_platform.twin_gate import GlassBoxAudit

class LifecycleDenied(PermissionError):
    pass

@dataclass(frozen=True)
class AssessmentReceipt:
    rtsa: str
    correlation_id: str
    findings: tuple[str, ...]
    input_digest: str
    audit_hash: str
    execution_allowed: bool = False

class OfflineRTSAConductor:
    """Test-only conductor, never a replacement for MICHAEL ANGELO."""
    def __init__(self, audit: GlassBoxAudit):
        self.audit = audit
        self.seen: set[str] = set()

    def run(self, *, rtsa: str, data: dict, correlation_id: str,
            manager_clearance: bool, minotaur_clearance: bool,
            human_clearance: bool) -> AssessmentReceipt:
        if not isinstance(correlation_id, str) or not correlation_id.strip():
            raise LifecycleDenied("MISSING_CORRELATION_ID")
        if correlation_id in self.seen:
            raise LifecycleDenied("REPLAYED_CORRELATION_ID")
        role = get_rtsa(rtsa)
        if not all((manager_clearance, minotaur_clearance, human_clearance)):
            self.audit.record({"stage":"DENIED", "rtsa":role.canonical_name,
                               "correlation_id":correlation_id,
                               "reason":"CLEARANCE_MISSING"})
            raise LifecycleDenied("CLEARANCE_MISSING")
        # Clearance flags are accepted ONLY for offline advisory testing;
        # never interpret them as production cryptographic signatures.
        self.seen.add(correlation_id)
        try:
            result: Assessment = assess(rtsa, data)
            entry = self.audit.record({
                "stage":"PRESERVED", "rtsa":rtsa,
                "correlation_id":correlation_id,
                "input_digest":result.input_digest,
                "findings":list(result.findings),
                "outcome":"ADVISORY_ONLY",
                "timestamp_utc":datetime.now(timezone.utc).isoformat()
            })
            return AssessmentReceipt(
                rtsa=rtsa, correlation_id=correlation_id,
                findings=result.findings, input_digest=result.input_digest,
                audit_hash=entry["hash"])
        finally:
            self.audit.record({"stage":"REVOKED", "rtsa":rtsa,
                               "correlation_id":correlation_id})
