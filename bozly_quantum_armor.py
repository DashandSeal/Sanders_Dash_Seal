"""Bozly real post-quantum protected event envelopes.

Uses existing FIPS 203 ML-KEM-768 + AES-256-GCM from bozly_pq_identity;
cryptographic failures are NOT proof of an identified intruder.
No fake lattice sponge, homegrown encryption, unprovisioned passphrases,
mock tampering incidents, or hidden host traceback.
"""
from __future__ import annotations
import base64,hashlib,json,time
from cryptography.exceptions import InvalidTag
from bozly_pq_identity import encrypt_priority_envelope,decrypt_priority_envelope

class BozlyQuantumArmor:
    engine_id="BOZLY-FIPS203-ENVELOPE"
    def compute_self_signature(self):
        from pathlib import Path
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def armor_payload(self,action_type,transaction_details,recipient_public_key_b64):
        if not isinstance(action_type,str) or not action_type.strip():
            raise ValueError("Action type required")
        if not isinstance(transaction_details,dict):
            raise ValueError("Structured real transaction details required")
        pub=base64.b64decode(recipient_public_key_b64,validate=True)
        plain=json.dumps({"action_type":action_type,"details":transaction_details,
             "sealed_at_unix":int(time.time())},sort_keys=True,separators=(",",":")).encode()
        sealed=encrypt_priority_envelope(plain,pub)
        return {"envelope":sealed,"plaintext_sha256":hashlib.sha256(plain).hexdigest(),
            "security_primitive":"ML-KEM-768 HKDF-SHA-384 AES-256-GCM",
            "tamper_attribution_claimed":False}

    def verify_and_dearmor_payload(self,armored_package,recipient_seed_b64):
        if not isinstance(armored_package,dict) or not isinstance(
             armored_package.get("envelope"),dict):
            raise ValueError("Protected envelope required")
        seed=base64.b64decode(recipient_seed_b64,validate=True)
        try:
            plain=decrypt_priority_envelope(armored_package["envelope"],seed)
            if not isinstance(armored_package.get("plaintext_sha256"),str):
                raise ValueError("Missing original digest")
            if hashlib.sha256(plain).hexdigest()!=armored_package["plaintext_sha256"]:
                raise ValueError("Plaintext evidence digest mismatch")
            return True,json.loads(plain)
        except (InvalidTag,ValueError,TypeError,KeyError) as exc:
            return False,{"status":"CRYPTOGRAPHIC_INTEGRITY_FAILURE",
                          "error_type":type(exc).__name__,
                          "attribution":"UNKNOWN"}
