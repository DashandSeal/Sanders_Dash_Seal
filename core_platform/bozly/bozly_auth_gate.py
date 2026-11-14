"""Bozly native cryptographic action-integrity receipts.

Authenticates existing authorized officers using real Ed25519 signatures and
owner-configured named public keys. The module does not introduce a new
multi-signature quorum, consent workflow or permission to spend/trade.
"""
from __future__ import annotations
import hashlib,json

class BozlyAuthGate:
    engine_id="BOZLY-NATIVE-ACTION-INTEGRITY"
    def generate_action_payload_hash(self,action,transaction_details):
        if not isinstance(action,str) or not action.strip() or not isinstance(transaction_details,dict):
            raise ValueError("Real action and structured payload required")
        body=json.dumps({"action":action,"details":transaction_details},
            sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        return hashlib.sha256(b"BOZLY-NATIVE-ACTION-v1\n"+body).hexdigest()

