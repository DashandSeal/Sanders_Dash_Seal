"""Post-quantum cryptography (PQC) for Sanders Dash & Seal — software only.

NIST-standard, free and open algorithms, run in real time in software:

- Key exchange: ML-KEM-768 (FIPS 203), via ``cryptography``.
- Signatures: ML-DSA-65 (FIPS 204), via ``cryptography``.

No quantum key distribution (QKD) hardware is involved: QKD needs
dedicated fibre and single-photon hardware, is not available over the
internet, and is not in Oracle Always Free. This module is PQC only.

Fail-closed by design:

- If the installed ``cryptography`` build cannot perform PQC (the
  pinned 47.0.0 build raises ``UnsupportedAlgorithm`` on hosts whose
  OpenSSL is older than 3.5; 50.0.2 is the minimum version verified
  working on this host), every operation raises
  :class:`PQCUnavailableError` and :func:`status` reports
  ``available: False``. Nothing here ever pretends to be quantum-safe.
- No key is ever generated from a default, stored in this module, or
  written to disk by this module. Callers supply key bytes; the owner
  stores private keys in the OCI Vault / Secure Vault, never in the repo.
- :func:`verify` returns ``False`` for a bad signature; it never raises
  for a bad signature, so callers can treat ``False`` as "reject".
"""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

KEM_ALGORITHM = "ML-KEM-768"
SIGNATURE_ALGORITHM = "ML-DSA-65"
# Minimum cryptography version verified to actually perform ML-KEM-768
# and ML-DSA-65 on this host (Python 3.12, system OpenSSL 3.0.13).
# 47.0.0 ships the classes but its backend raises UnsupportedAlgorithm
# for every PQC parameter set on that OpenSSL. See PQC_UPGRADE.md.
MIN_CRYPTOGRAPHY_VERSION = "50.0.2"


class PQCUnavailableError(RuntimeError):
    """Raised when post-quantum cryptography is unavailable in this runtime.

    The platform must treat this as "PQC not active", never as a reason
    to fall back silently to a weaker claim of quantum safety.
    """


class _Backend:
    """Lazily probed ``cryptography`` ML-KEM / ML-DSA backend.

    Importing the modules is not enough: 47.0.0 imports fine but its
    backend rejects every PQC operation. So availability is decided by
    actually generating one key of each kind, once, and caching the
    outcome. The probe uses ephemeral keys that are discarded.
    """

    def __init__(self) -> None:
        self.available = False
        self.library_version: str | None = None
        self.reason: str | None = None
        try:
            import cryptography
            from cryptography.hazmat.primitives.asymmetric import (
                mlkem as _mlkem,
                mldsa as _mldsa,
            )
        except Exception as exc:  # ImportError or any load failure.
            self.reason = "cryptography_pqc_import_failed: " + type(exc).__name__
            return
        self.library_version = getattr(cryptography, "__version__", "unknown")
        self._mlkem = _mlkem
        self._mldsa = _mldsa
        try:
            _mldsa.MLDSA65PrivateKey.generate()
            _mlkem.MLKEM768PrivateKey.generate()
        except Exception as exc:
            # UnsupportedAlgorithm on backends without PQC support.
            self.reason = "pqc_not_supported_by_backend: " + type(exc).__name__
            return
        self.available = True


_BACKEND: _Backend | None = None


def _backend() -> _Backend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = _Backend()
    return _BACKEND


def _reset_backend_cache() -> None:
    """Test-only hook: forget the probed backend so tests can simulate it."""
    global _BACKEND
    _BACKEND = None


def available() -> bool:
    """True only if this runtime can actually perform ML-KEM and ML-DSA."""
    return _backend().available


def require_available() -> None:
    """Raise :class:`PQCUnavailableError` unless PQC works in this runtime."""
    backend = _backend()
    if not backend.available:
        raise PQCUnavailableError(
            "Post-quantum cryptography is unavailable in this runtime"
            + (f" ({backend.reason})" if backend.reason else "")
            + f"; minimum verified cryptography version is {MIN_CRYPTOGRAPHY_VERSION}."
        )


def status() -> dict:
    """Honest, key-free report of PQC capability. Safe to serve over HTTP."""
    backend = _backend()
    return {
        "available": backend.available,
        "kem_algorithm": KEM_ALGORITHM if backend.available else None,
        "signature_algorithm": SIGNATURE_ALGORITHM if backend.available else None,
        "library": "cryptography",
        "library_version": backend.library_version,
        "min_verified_library_version": MIN_CRYPTOGRAPHY_VERSION,
        "reason": None if backend.available else backend.reason,
    }


def _serialization():
    from cryptography.hazmat.primitives import serialization

    return serialization


def _load_private_key(private_der: bytes):
    require_available()
    return _serialization().load_der_private_key(private_der, password=None)


def _load_public_key(public_der: bytes, kind: str):
    require_available()
    try:
        return _serialization().load_der_public_key(public_der)
    except Exception as exc:
        raise ValueError(f"Invalid {kind} public key bytes: {type(exc).__name__}") from exc


# ---------------------------------------------------------------------------
# Key exchange: ML-KEM-768 (FIPS 203)
# ---------------------------------------------------------------------------


def generate_kem_keypair() -> tuple[bytes, bytes]:
    """Generate an ML-KEM-768 keypair. Returns ``(private_der, public_der)``.

    The private key bytes must be stored by the caller in the owner's
    Vault, never in the repo and never logged.
    """
    require_available()
    private_key = _backend()._mlkem.MLKEM768PrivateKey.generate()
    ser = _serialization()
    private_der = private_key.private_bytes(
        ser.Encoding.DER, ser.PrivateFormat.PKCS8, ser.NoEncryption()
    )
    public_der = private_key.public_key().public_bytes(
        ser.Encoding.DER, ser.PublicFormat.SubjectPublicKeyInfo
    )
    return private_der, public_der


def kem_encapsulate(public_der: bytes) -> tuple[bytes, bytes]:
    """Encapsulate to a peer's ML-KEM-768 public key.

    Returns ``(shared_secret, ciphertext)`` — 32-byte secret, 1088-byte
    ciphertext. The caller sends only the ciphertext to the peer.
    """
    public_key = _load_public_key(public_der, "ML-KEM-768")
    return public_key.encapsulate()


def kem_decapsulate(private_der: bytes, ciphertext: bytes) -> bytes:
    """Recover the shared secret from a ciphertext with the private key."""
    private_key = _load_private_key(private_der)
    try:
        return private_key.decapsulate(ciphertext)
    except Exception as exc:
        raise ValueError(f"Invalid ML-KEM-768 ciphertext: {type(exc).__name__}") from exc


def derive_session_key(shared_secret: bytes, context: bytes) -> bytes:
    """Derive a 32-byte session key from a KEM shared secret (HKDF-SHA256).

    ``context`` binds the key to one use (e.g. a session id or route);
    different contexts give different keys from the same secret.
    """
    if not isinstance(shared_secret, bytes) or len(shared_secret) < 16:
        raise ValueError("Shared secret must be at least 16 bytes")
    if not isinstance(context, bytes):
        raise ValueError("Context must be bytes")
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes

    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"sds-pqc-v1:" + context
    ).derive(shared_secret)


# ---------------------------------------------------------------------------
# Signatures: ML-DSA-65 (FIPS 204)
# ---------------------------------------------------------------------------


def generate_signing_keypair() -> tuple[bytes, bytes]:
    """Generate an ML-DSA-65 keypair. Returns ``(private_der, public_der)``.

    The private key bytes must be stored by the caller in the owner's
    Vault, never in the repo and never logged.
    """
    require_available()
    private_key = _backend()._mldsa.MLDSA65PrivateKey.generate()
    ser = _serialization()
    private_der = private_key.private_bytes(
        ser.Encoding.DER, ser.PrivateFormat.PKCS8, ser.NoEncryption()
    )
    public_der = private_key.public_key().public_bytes(
        ser.Encoding.DER, ser.PublicFormat.SubjectPublicKeyInfo
    )
    return private_der, public_der


def sign(private_der: bytes, message: bytes) -> bytes:
    """Sign ``message`` with an ML-DSA-65 private key. Returns the signature."""
    if not isinstance(message, bytes):
        raise ValueError("Message must be bytes")
    return _load_private_key(private_der).sign(message)


def verify(public_der: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an ML-DSA-65 signature. ``False`` for any invalid signature."""
    if not isinstance(message, bytes) or not isinstance(signature, bytes):
        return False
    try:
        public_key = _load_public_key(public_der, "ML-DSA-65")
    except ValueError:
        return False
    try:
        public_key.verify(signature, message)
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------------
# Canonical records: deterministic bytes for signing ledger entries
# ---------------------------------------------------------------------------


def canonical_bytes(record: Mapping) -> bytes:
    """Deterministic JSON bytes for a record: sorted keys, no whitespace.

    The same record always signs to the same bytes, on any host.
    Non-JSON values raise ValueError rather than being silently coerced.
    """
    try:
        return json.dumps(
            dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Record is not JSON-serialisable: {exc}") from exc


def sign_record(private_der: bytes, record: Mapping) -> bytes:
    """Sign a record's canonical bytes with ML-DSA-65."""
    return sign(private_der, canonical_bytes(record))


def verify_record(public_der: bytes, record: Mapping, signature: bytes) -> bool:
    """Verify an ML-DSA-65 signature over a record's canonical bytes."""
    try:
        message = canonical_bytes(record)
    except ValueError:
        return False
    return verify(public_der, message, signature)


def record_fingerprint(record: Mapping) -> str:
    """SHA-256 hex of a record's canonical bytes (integrity check, not a signature)."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()
