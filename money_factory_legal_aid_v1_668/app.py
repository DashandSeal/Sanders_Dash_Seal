from fastapi import FastAPI
from pydantic import BaseModel
from shield.sovereign_shield_v3 import SovereignShieldV3

app = FastAPI(title="Money Factory Legal Aid v1.668", version="1.668")


class SealRequest(BaseModel):
    node_id: str
    jurisdiction_code: str
    naics_code: str
    evidence_sha256: str
    base_cost_usd: str
    payload: dict


@app.get("/health")
def health():
    return {"status": "ACTIVE", "engine": "Money Factory Legal Aid v1.668", "pqc": "ML-DSA-65"}


@app.post("/v1/seal")
def seal_evidence(req: SealRequest):
    shield = SovereignShieldV3(req.node_id, req.jurisdiction_code)
    pricing = shield.calculate_locked_retail_price(req.base_cost_usd)
    coc = shield.generate_lattice_coc(req.payload, req.evidence_sha256, req.naics_code)
    return {"pricing": pricing, "chain_of_custody": coc}
