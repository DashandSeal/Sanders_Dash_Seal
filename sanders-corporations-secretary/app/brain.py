"""Transparent deterministic advisory layer; not an external LLM or autonomous signer."""
from datetime import date
from .registry import COMPANY_BY_ID

SENSITIVE_ACTIONS={"external_filing", "financial_disbursement", "legal_signature", "production_policy_change", "git_publication"}

def classify_event(kind: str, company_id: str, summary: str):
    signals=[]
    lower=summary.lower()
    if kind == "filing.deadline":
        signals.append({"severity":"high","recommendation":"Verify the agency deadline and assign a filing owner."})
    if kind == "grant.opportunity":
        signals.append({"severity":"medium","recommendation":"Check eligible applicant type, individual award amount and allowable activities."})
    if kind == "seal.updated":
        signals.append({"severity":"medium","recommendation":"Preserve the original artwork and record the design version before distribution."})
    if "urgent" in lower or "past due" in lower:
        signals.append({"severity":"high","recommendation":"Review this item promptly against its original source."})
    return {"company": COMPANY_BY_ID[company_id]["name"],"signals":signals, "mode":"deterministic_rules_v1"}

def recommend_tasks(tasks):
    today=date.today().isoformat()
    result=[]
    for t in tasks:
        if t["status"]=="open" and t["due_date"] and t["due_date"]<=today:
            result.append({"company_id":t["company_id"],"task_id":t["id"],"severity":"high","recommendation":f"Review due or overdue: {t['title']}"})
    return result

def action_policy(action: str):
    return {"action":action,"owner_authorization_required":action in SENSITIVE_ACTIONS,"auto_executed":False,"explanation":"Actions affecting legal standing, money, policy or public records are owner-directed."}