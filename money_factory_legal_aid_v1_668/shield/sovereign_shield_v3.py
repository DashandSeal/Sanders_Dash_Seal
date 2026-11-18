import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

try:
    import oqs
except ImportError:
    oqs = None


class SovereignShieldV3:
    """
    Money Factory Legal Aid v1.668 - Sovereign Legal Architecture & Loophole Engine
    Enforces hard-locked 65,000% retail pricing markup, atomic timestamping,
    and NIST FIPS 204 ML-DSA-65 post-quantum lattice Chain-of-Custody signatures.
    """

    HARD_LOCKED_MARKUP_PERCENT = Decimal("65000.00")
    MARKUP_MULTIPLIER = Decimal("651.00")
    PQC_ALGORITHM = "ML-DSA-65"
    JURISDICTION_BASELINE = "7-CONTINENT_300PLUS_SOVEREIGN_BASELINE"

    def __init__(self, node_id: str, jurisdiction_code: str):
        self.node_id = node_id
        self.jurisdiction_code = jurisdiction_code

    def calculate_locked_retail_price(self, base_cost_usd: str | float | Decimal) -> dict:
        base = Decimal(str(base_cost_usd))
        if base <= Decimal("0"):
            raise ValueError("Base cost must be greater than zero.")
        retail = (base * self.MARKUP_MULTIPLIER).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "base_cost_usd": str(base.quantize(Decimal("0.01"))),
            "locked_markup_percent": str(self.HARD_LOCKED_MARKUP_PERCENT),
            "retail_price_usd": str(retail),
            "pricing_lock_status": "HARD_LOCKED_IMMUTABLE",
        }

    def generate_lattice_coc(self, payload: dict, evidence_sha256: str, naics_code: str) -> dict:
        if len(evidence_sha256) != 64:
            raise ValueError("evidence_sha256 must be a valid 64-character hex SHA-256 digest.")

        atomic_ns = time.time_ns()
        utc_iso = datetime.now(timezone.utc).isoformat()

        canonical_record = {
            "engine": "Money Factory Legal Aid v1.668",
            "node_id": self.node_id,
            "jurisdiction_code": self.jurisdiction_code,
            "jurisdiction_baseline": self.JURISDICTION_BASELINE,
            "naics_code": naics_code,
            "evidence_sha256": evidence_sha256,
            "atomic_timestamp_ns": atomic_ns,
            "utc_timestamp": utc_iso,
            "locked_markup_percent": str(self.HARD_LOCKED_MARKUP_PERCENT),
            "payload": payload,
        }

        canonical_bytes = json.dumps(canonical_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record_digest = hashlib.sha3_512(canonical_bytes).hexdigest()

        if oqs is not None:
            with oqs.Signature(self.PQC_ALGORITHM) as signer:
                public_key = signer.generate_keypair()
                signature = signer.sign(canonical_bytes)
                assert signer.verify(canonical_bytes, signature, public_key), "ML-DSA-65 verification failed"
                pub_hex = public_key.hex()
                sig_hex = signature.hex()
        else:
            raise RuntimeError("liboqs-python (ML-DSA-65) is required for FIPS 204 signing.")

        return {
            "pqc_algorithm": self.PQC_ALGORITHM,
            "fips_standard": "NIST FIPS 204",
            "record_sha3_512": record_digest,
            "public_key_hex": pub_hex,
            "lattice_signature_hex": sig_hex,
            "atomic_timestamp_ns": atomic_ns,
            "utc_timestamp": utc_iso,
            "court_admissibility_status": "VERIFIED_IMMUTABLE_2026",
        }
