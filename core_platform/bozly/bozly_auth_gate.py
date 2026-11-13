"""Bozly native cryptographic action-integrity receipts.

Authenticates existing authorized officers using real Ed25519 signatures and
owner-configured named public keys. The module does not introduce a new
multi-signature quorum, consent workflow or permission to spend/trade.
"""
from __future__ import annotations
import base64,hashlib,json,os,time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

class BozlyAuthGate:
    engine_id="BOZLY-NATIVE-ACTION-INTEGRITY"
    def generate_action_payload_hash(self,action,transaction_details):
        if not isinstance(action,str) or not action.strip() or not isinstance(transaction_details,dict):
            raise ValueError("Real action and structured payload required")
        body=json.dumps({"action":action,"details":transaction_details},
            sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        return hashlib.sha256(b"BOZLY-NATIVE-ACTION-v1\n"+body).hexdigest()

    def evaluate_executive_approvals(self,action,transaction_details,
                                    client_signatures,public_keys):
        # Compatibility with supplied method name; this confirms authentic
        # signatures, NOT a compulsory approval gate or transfer authority.
        digest=self.generate_action_payload_hash(action,transaction_details)
        if not isinstance(client_signatures,dict) or not isinstance(public_keys,dict):
            raise ValueError("Signed identities and provisioned public keys required")
        if not client_signatures:
            return {"payload_sha256":digest,"signature_results":{},
                "verified_signatories":[],"new_approval_gate_created":False}
        statuses={}
        for role,signature in client_signatures.items():
            key=public_keys.get(role)
            try:
                if not isinstance(key,str) or not isinstance(signature,str):
                    raise ValueError()
                raw_key=base64.b64decode(key,validate=True)
                raw_sig=base64.b64decode(signature,validate=True)
                Ed25519PublicKey.from_public_bytes(raw_key).verify(
                    raw_sig,bytes.fromhex(digest))
                statuses[role]="CRYPTOGRAPHIC_SIGNATURE_VALID"
            except (InvalidSignature,ValueError,TypeError):
                statuses[role]="INVALID_OR_UNPROVISIONED_SIGNATURE"
        return {"payload_sha256":digest,"signature_results":statuses,
            "verified_signatories":[r for r,s in statuses.items()
                if s=="CRYPTOGRAPHIC_SIGNATURE_VALID"],
            "funds_disbursed":False,"new_approval_gate_created":False}
