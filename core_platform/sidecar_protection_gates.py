"""Sanders synthetic AI Sidecar: fail-closed owner halt and crypto-readiness gates.

Development integration component. This does NOT implement post-quantum
cryptography, hardware-backed owner authentication, or a production trust root.
Those require separately verified adapters and real key material.
"""
import json
import os
import tempfile
from pathlib import Path


class ProtectionDenied(RuntimeError):
    pass


class OwnerHalt:
    """Persistent, default-halted development gate. Only the trusted local
    administrator can call resume after separately authenticating the owner.
    A caller-supplied string or bool is NOT authentication.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "owner_halt.json"

    def halted(self):
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return True
        return state.get("halted") is not False

    def _write(self, halted):
        fd, temp = tempfile.mkstemp(prefix=".halt-", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump({"halted": halted}, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def halt(self):
        self._write(True)

    def resume(self, owner_authenticator, proof):
        if not callable(owner_authenticator) or owner_authenticator(proof) is not True:
            raise ProtectionDenied("Independently verified owner authentication required")
        self._write(False)

    def require_running(self):
        if self.halted():
            raise ProtectionDenied("Owner halt active or halt state unavailable")


class ProtectedUpgradeExecutor:
    """Development adapter enforcing gates before staging.

    quantum_verifier must verify an actual approved PQ/hybrid cryptographic
    proof with pinned trust roots. Merely setting a 'quantum_safe' flag is not
    sufficient. No verifier means deny.
    """
    def __init__(self, executor, owner_halt, pbd_validator,
                 independent_health_verifier, quantum_verifier):
        self.executor = executor
        self.owner_halt = owner_halt
        self.pbd_validator = pbd_validator
        self.health = independent_health_verifier
        self.quantum = quantum_verifier

    def stage(self, record, artifact_path):
        self.owner_halt.require_running()
        artifact = Path(artifact_path)
        if not artifact.is_file() or artifact.is_symlink():
            raise ProtectionDenied("Regular artifact required")
        payload = artifact.read_bytes()
        evidence = record.get("evidence", {})
        manifest = evidence.get("pbd_manifest")
        scope = evidence.get("approved_scope")
        if not isinstance(manifest, dict) or not isinstance(scope, dict):
            raise ProtectionDenied("Signed PBD manifest and scope required")
        if not callable(self.pbd_validator) or self.pbd_validator(
                payload, artifact.name, scope, manifest) is not True:
            raise ProtectionDenied("Independent PBD validation failed")
        if not callable(self.quantum) or self.quantum(
                payload, record, evidence) is not True:
            raise ProtectionDenied("Post-quantum verification unavailable or failed")
        self.owner_halt.require_running()
        return self.executor.stage(record, artifact_path)

    def verify(self, record):
        self.owner_halt.require_running()
        receipt = self.executor.verify(record)
        if not isinstance(receipt, dict) or receipt.get("healthy") is not True:
            raise ProtectionDenied("Artifact verification failed")
        if not callable(self.health) or self.health(record) is not True:
            raise ProtectionDenied("Independent service health verification failed")
        return {"healthy": True, "artifact_receipt": receipt,
                "independent_service_health": True}

    def rollback(self, record):
        # Halt never prevents recovery.
        return self.executor.rollback(record)
