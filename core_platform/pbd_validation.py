"""Sanders Dash & Seal: signed PBD manifest verification.

Verification only. This module never executes a target script.
Production trust roots must be provisioned outside the repository.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

class ManifestRejected(PermissionError):
    pass

def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

@dataclass(frozen=True)
class TrustedSigner:
    role: str
    key_id: str
    public_key: Ed25519PublicKey

class PBDScriptValidationEngine:
    """Fail-closed signature and file-integrity gate; no process execution."""
    def __init__(self, trust_roots: dict[str, TrustedSigner]):
        required = {"it_manager", "minotaur"}
        if set(trust_roots) != required:
            raise ValueError("Both independent trust roots are required")
        if trust_roots["it_manager"].key_id == trust_roots["minotaur"].key_id:
            raise ValueError("Twin-Gate signers must be distinct")
        self._trust = trust_roots

    def verify(self, executable: Path, manifest: Path, *, expected_scope: str) -> dict:
        executable = Path(executable)
        manifest = Path(manifest)
        if manifest != executable.with_name(executable.name + ".pbd.json"):
            raise ManifestRejected("PAIR_PATH_MISMATCH")
        if executable.suffix not in (".py", ".js", ".sh"):
            raise ManifestRejected("EXECUTABLE_TYPE_NOT_GOVERNED")
        try:
            doc = json.loads(manifest.read_text(encoding="utf-8"))
            body = doc["signed_body"]
            signatures = doc["signatures"]
            if not isinstance(body, dict) or not isinstance(signatures, dict):
                raise ManifestRejected("INVALID_MANIFEST_SHAPE")
            if body["platform"] != "Sanders Dash & Seal":
                raise ManifestRejected("PLATFORM_IDENTITY_MISMATCH")
            if body["artifact"] != executable.name:
                raise ManifestRejected("ARTIFACT_MISMATCH")
            if body["scope"] != expected_scope:
                raise ManifestRejected("SCOPE_MISMATCH")
            if body["max_execution_limit"] != 1:
                raise ManifestRejected("EXECUTION_BOUND_INVALID")
            if body["sha256"] != sha256(executable.read_bytes()).hexdigest():
                raise ManifestRejected("PAYLOAD_HASH_MISMATCH")
            message = canonical_bytes(body)
            for role in ("it_manager", "minotaur"):
                signer = self._trust[role]
                item = signatures[role]
                if item["key_id"] != signer.key_id:
                    raise ManifestRejected("UNTRUSTED_SIGNER:" + role)
                signature = base64.b64decode(item["signature"], validate=True)
                signer.public_key.verify(signature, message)
            return {"verified": True, "artifact": executable.name,
                    "scope": expected_scope, "payload_sha256": body["sha256"]}
        except ManifestRejected:
            raise
        except (OSError, ValueError, KeyError, TypeError, InvalidSignature) as exc:
            raise ManifestRejected("SIGNATURE_OR_MANIFEST_INVALID") from exc
