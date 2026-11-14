"""Bozly post-quantum identity and confidential alert envelopes.

FIPS 204 ML-DSA-65 is used to verify an externally signed identity manifest.
FIPS 203 ML-KEM-768 + HKDF-SHA-384 + AES-256-GCM secures alert envelopes.
Keys and signatures are never generated silently or stored in source control.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey, MLKEM768PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

BOZLY_IDENTITY = "BOZLY-CFO"
IDENTITY_CONTEXT = b"Sanders/Bozly/identity/v1"
ENVELOPE_AAD = b"Sanders/Bozly/priority-alert/v1"


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def verify_signed_identity(manifest: bytes, signature: bytes, public_key: bytes) -> dict:
    """Verify the named immutable engine identity against a pinned ML-DSA key.

    A valid signature anchors one manifest revision; it does not make mutable
    files or the runtime physically immutable. Protect key distribution out of band.
    """
    record = json.loads(manifest)
    if not isinstance(record, dict) or record.get("engine") != BOZLY_IDENTITY:
        raise ValueError("Unexpected Bozly identity")
    if not isinstance(record.get("revision"), str) or not record["revision"]:
        raise ValueError("Identity revision missing")
    MLDSA65PublicKey.from_public_bytes(public_key).verify(
        signature, manifest, IDENTITY_CONTEXT
    )
    return {
        "engine": BOZLY_IDENTITY,
        "revision": record["revision"],
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "algorithm": "ML-DSA-65",
        "signature_valid": True,
    }


def identity_status_from_config() -> dict:
    """Read an actual signed manifest from protected runtime-mounted files.

    This function never silently substitutes an unverified default identity.
    """
    manifest_path = os.environ.get("BOZLY_IDENTITY_MANIFEST_FILE")
    signature_path = os.environ.get("BOZLY_IDENTITY_SIGNATURE_FILE")
    pinned_key = os.environ.get("BOZLY_IDENTITY_PUBLIC_KEY_B64")
    if not (manifest_path and signature_path and pinned_key):
        return {"engine": BOZLY_IDENTITY, "signature_valid": False,
                "reason": "identity_anchor_not_provisioned"}
    with open(manifest_path, "rb") as f:
        manifest = f.read(65537)
    if len(manifest) > 65536:
        raise ValueError("Identity manifest size invalid")
    with open(signature_path, "rb") as f:
        signature = f.read(10000)
    return verify_signed_identity(manifest, signature, _unb64(pinned_key))


def _derive(shared_secret: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA384(), length=32, salt=None,
        info=ENVELOPE_AAD
    ).derive(shared_secret)


def encrypt_priority_envelope(message: bytes, recipient_public_key: bytes) -> dict:
    """Real recipient-side post-quantum encapsulation; no invented quantum mode."""
    if not isinstance(message, bytes):
        raise TypeError("Message must be bytes")
    public_key = MLKEM768PublicKey.from_public_bytes(recipient_public_key)
    shared, kem_ciphertext = public_key.encapsulate()
    nonce = os.urandom(12)
    ciphertext = AESGCM(_derive(shared)).encrypt(nonce, message, ENVELOPE_AAD)
    return {
        "format": "bozly-mlkem768-aes256gcm-v1",
        "kem": _b64(kem_ciphertext),
        "nonce": _b64(nonce),
        "ciphertext": _b64(ciphertext),
    }


def decrypt_priority_envelope(envelope: dict, recipient_seed: bytes) -> bytes:
    """Requires an authentic 64-byte ML-KEM seed provisioned outside Git."""
    if envelope.get("format") != "bozly-mlkem768-aes256gcm-v1":
        raise ValueError("Unsupported alert envelope format")
    private_key = MLKEM768PrivateKey.from_seed_bytes(recipient_seed)
    shared = private_key.decapsulate(_unb64(envelope["kem"]))
    return AESGCM(_derive(shared)).decrypt(
        _unb64(envelope["nonce"]),
        _unb64(envelope["ciphertext"]),
        ENVELOPE_AAD,
    )
