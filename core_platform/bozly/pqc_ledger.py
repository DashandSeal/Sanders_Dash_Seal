"""Post-quantum signing for Bozly CFO ledger entries.

Bozly is the platform's CFO: it records verified payment events as
observations in a hash-linked SQLite ledger. This module adds a
quantum-resistant signature layer on top of those records, using
ML-DSA-65 (FIPS 204) from :mod:`core_platform.pqc`.

Design rules:

- This module never touches the ledger database itself and never
  initiates a charge. It signs and verifies record dicts only; the
  caller (Bozly worker / ledger code) decides what to store.
- A signed entry carries its signature and public key alongside the
  record, so anyone with the entry can verify it without a live call.
- Fail-closed: if PQC is unavailable in this runtime, signing raises
  :class:`core_platform.pqc.PQCUnavailableError` and verification
  returns ``False``. A record is never reported as quantum-signed
  when it is not.
- No private key is stored here. The signing key is supplied per call
  by the caller; the owner stores it in the OCI Vault / Secure Vault.
  No key bytes are ever logged.
- No error detail from this module ever includes file paths, stack
  traces, or internal state. Callers return generic error codes.
"""

from __future__ import annotations

from typing import Mapping

from core_platform.pqc import (
    PQCUnavailableError,
    SIGNATURE_ALGORITHM,
    generate_signing_keypair,
    sign_record,
    verify_record,
)

__all__ = [
    "PQCUnavailableError",
    "SIGNATURE_ALGORITHM",
    "generate_ledger_signing_keypair",
    "sign_ledger_entry",
    "verify_ledger_entry",
]

# Fields added to a signed entry. Verification strips exactly these
# fields before re-canonicalising, so a signature covers the original
# record and nothing else.
_SIGNATURE_FIELDS = ("pqc_algorithm", "pqc_signature_hex", "pqc_public_key_hex")


def generate_ledger_signing_keypair() -> tuple[bytes, bytes]:
    """Generate a fresh ML-DSA-65 keypair for ledger signing.

    Returns ``(private_der, public_der)``. The private key must be
    stored by the owner in the Vault, never in the repo, never logged.
    """
    return generate_signing_keypair()


def sign_ledger_entry(
    signing_key_der: bytes, entry: Mapping
) -> dict:
    """Return a copy of ``entry`` with a PQC signature attached.

    Added fields: ``pqc_algorithm`` (``"ML-DSA-65"``),
    ``pqc_signature_hex``, ``pqc_public_key_hex``. The public key is
    derived from the signing key, so the entry is self-verifying.

    Raises :class:`PQCUnavailableError` if PQC cannot run here, and
    ``ValueError`` if the entry is not JSON-serialisable.
    """
    if not isinstance(entry, Mapping):
        raise ValueError("Ledger entry must be a mapping")
    for field in _SIGNATURE_FIELDS:
        if field in entry:
            raise ValueError(f"Ledger entry already carries {field}; refusing to re-sign")
    from core_platform.pqc import _load_private_key

    private_key = _load_private_key(signing_key_der)
    from cryptography.hazmat.primitives import serialization

    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signature = sign_record(signing_key_der, entry)
    signed = dict(entry)
    signed["pqc_algorithm"] = SIGNATURE_ALGORITHM
    signed["pqc_signature_hex"] = signature.hex()
    signed["pqc_public_key_hex"] = public_der.hex()
    return signed


def verify_ledger_entry(entry: Mapping) -> bool:
    """Verify a signed ledger entry. ``False`` for any tamper or missing field.

    The signature covers the entry with the ``pqc_*`` fields removed,
    so changing any recorded value, the algorithm label, or the
    signature itself fails verification.
    """
    if not isinstance(entry, Mapping):
        return False
    if entry.get("pqc_algorithm") != SIGNATURE_ALGORITHM:
        return False
    try:
        signature = bytes.fromhex(entry["pqc_signature_hex"])
        public_der = bytes.fromhex(entry["pqc_public_key_hex"])
    except (KeyError, TypeError, ValueError):
        return False
    record = {k: v for k, v in entry.items() if k not in _SIGNATURE_FIELDS}
    return verify_record(public_der, record, signature)
