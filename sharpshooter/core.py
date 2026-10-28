"""Provider-independent TLS diagnostics and authorized remediation orchestration."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse
import socket
import ssl
import json
import hashlib
import uuid

@dataclass
class Incident:
    id: str
    hostname: str
    detected_at: str
    status: str
    observations: dict
    action: str = "none"
    verification: dict | None = None

def diagnose(hostname: str, timeout: float = 6.0) -> dict:
    """Public endpoint diagnosis; never bypass TLS verification."""
    if not hostname or any(c in hostname for c in "/:@?# ") or len(hostname) > 253:
        raise ValueError("hostname must be a DNS name")
    result = {"hostname": hostname, "dns": [], "tcp443": False, "tls": False}
    try:
        result["dns"] = sorted({x[4][0] for x in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
    except OSError as e:
        result["error"] = "dns: " + str(e)
        return result
    try:
        with socket.create_connection((hostname, 443), timeout=timeout) as raw:
            result["tcp443"] = True
            with ssl.create_default_context().wrap_socket(raw, server_hostname=hostname) as tls:
                cert = tls.getpeercert()
                result["tls"] = True
                result["tls_version"] = tls.version()
                result["expires"] = cert.get("notAfter")
                result["subject_alt_names"] = cert.get("subjectAltName", [])
    except (OSError, ssl.SSLError) as e:
        result["error"] = "connection/tls: " + str(e)
    return result

def new_incident(hostname: str, observation: dict) -> Incident:
    return Incident(str(uuid.uuid4()), hostname, datetime.now(timezone.utc).isoformat(),
                    "healthy" if observation.get("tls") else "detected", observation)

class Adapter:
    """Provider implementations must explicitly verify credentials and resource ownership."""
    name = "abstract"
    def capabilities(self) -> set[str]:
        return set()
    def execute(self, operation: str, hostname: str, *, authorization: dict) -> dict:
        raise NotImplementedError

class Remediator:
    def __init__(self, adapter: Adapter):
        self.adapter = adapter
    def repair(self, incident: Incident, operation: str, authorization: dict, *, execute: bool = False) -> Incident:
        if incident.status == "healthy":
            return incident
        if operation not in self.adapter.capabilities():
            incident.status = "provider_action_required"
            incident.action = "unsupported_operation"
            return incident
        if not authorization.get("approved") or authorization.get("provider") != self.adapter.name:
            incident.status = "authorization_required"
            return incident
        if not execute:
            incident.status = "planned"
            incident.action = operation
            return incident
        outcome = self.adapter.execute(operation, incident.hostname, authorization=authorization)
        incident.action = operation
        incident.verification = diagnose(incident.hostname)
        incident.status = "resolved" if outcome.get("success") and incident.verification.get("tls") else "verification_failed"
        return incident

def evidence(incident: Incident) -> str:
    payload = json.dumps(asdict(incident), sort_keys=True)
    return json.dumps({"incident": asdict(incident), "sha256": hashlib.sha256(payload.encode()).hexdigest()}, indent=2)
