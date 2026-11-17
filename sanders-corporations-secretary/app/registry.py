"""Owner-provided entity roster. Not substitutes for current state-certified records."""
COMPANIES = [
    {"id": "headquarters", "name": "Sanders Corporate Headquarters", "type": "corporate_coordinating_identity", "founded_year": None, "co_sos_id": None, "seal_key": "headquarters", "note": "Shared corporate identity; not automatically a separate legal entity."},
    {"id": "home_healthcare", "name": "Sanders Home Healthcare & Caregivers LLC", "type": "limited_liability_company", "founded_year": 2025, "co_sos_id": "20251946893", "seal_key": "llc", "note": "For the currently proposed nonmedical home-care program."},
    {"id": "senior_living", "name": "Sanders Senior Living LLC", "type": "limited_liability_company", "founded_year": 2025, "co_sos_id": "20258000764", "seal_key": "llc", "note": "Distinct legal entity with independent records."},
    {"id": "legal_helpers", "name": "Sanders Legal Helpers LLC", "type": "limited_liability_company", "founded_year": 2025, "co_sos_id": "20258029131", "seal_key": "llc", "dba": "Sanders Dash & Seal", "note": "DBA is not a separate company."},
    {"id": "security", "name": "S & G Security Inc.", "type": "corporation", "founded_year": 1996, "co_sos_id": None, "seal_key": None, "note": "1996 historical company founding year; do not assert a current SOS ID without verifying."},
]
COMPANY_BY_ID = {c["id"]: c for c in COMPANIES}
SEAL_LIBRARY_PATH = "/Sanders Family of Companies/Official Corporate Seals/Electronic Seals"
SEALS = [
    {"company_id": "headquarters", "name": "Headquarters master seal", "file": "Headquarters_Electronic_Master_Full_Color.png"},
    {"company_id": "home_healthcare", "name": "Home Healthcare master seal", "file": "Home_Healthcare_Electronic_Master_Full_Color.png"},
    {"company_id": "senior_living", "name": "Senior Living master seal", "file": "Senior_Living_Electronic_Master_Full_Color.png"},
    {"company_id": "legal_helpers", "name": "Legal Helpers master seal", "file": "Legal_Helpers_Electronic_Master_Full_Color.png"},
]