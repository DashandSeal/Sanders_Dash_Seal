"""Auditable intelligence with event evidence and owner-controlled action proposals."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from . import db, knowledge
from .registry import COMPANIES, COMPANY_BY_ID, SEALS, SEAL_LIBRARY_PATH

SENSITIVE={"external_filing","financial_disbursement","legal_signature","production_policy_change","git_publication","contract_execution"}

def evaluate_event(event_id: int) -> list[dict]:
    with db.connect() as cx:
        e=cx.execute("SELECT * FROM events WHERE id=?",(event_id,)).fetchone()
        if not e:raise ValueError("Unknown event")
        matches=[]
        if e['kind']=='filing.deadline':
            matches.append(("verify_filing_deadline","Verify official filing deadline", "Compare deadline, agency, and relevant company's filing status against primary source"))
        if e['kind']=='grant.opportunity':
            matches.append(("evaluate_grant","Check individual award amount and applicant eligibility","Check whether each distinct company is eligible and whether the amount is per award"))
        if e['kind']=='seal.updated':
            matches.append(("archive_seal","Preserve original approved seal","Record version and SHA-256 of approved source; do not replace master without owner direction"))
        if e['kind']=='document.created':
            matches.append(("review_document","Review document and corporate attribution","Verify the document uses the correct legal entity and corresponding letterhead"))
        if any(w in e['summary'].lower() for w in ('urgent','past due','overdue')):
            matches.append(("urgent_review","Review urgent corporate notice","Check the notice against the actual authoritative source"))
        for action_type,title,rationale in matches:
            cx.execute("INSERT OR IGNORE INTO action_proposals(company_id,action_type,title,rationale,source_kind,source_id,created_at) VALUES(?,?,?,?,?,?,?)",
              (e['company_id'],action_type,title,rationale,'event',event_id,db.utc_now()))
        rows=cx.execute("SELECT id,action_type,title,status FROM action_proposals WHERE source_kind='event' AND source_id=?",(event_id,)).fetchall()
        if rows:db.audit_insert(cx,'system','intelligence.evaluate',f'event:{event_id}',{"proposal_ids":[r['id'] for r in rows],"rules_version":"v2"})
    return [dict(r) for r in rows]

def _registry_sources(question:str,company_id:str|None)->list[dict]:
    q=question.lower();k=knowledge.terms(question)
    wants_registry=any(z in q for z in ['registry','sos','secretary of state','formation','founded','incorporat','year','legal name','entity id','entities'])
    wants_seal=any(z in q for z in ['seal','letterhead','crest'])
    if not(wants_registry or wants_seal):return []
    result=[]
    if wants_registry:
        cs=[COMPANY_BY_ID[company_id]] if company_id else COMPANIES
        for c in cs:
            result.append({"company_id":c['id'],"title":f"Corporate registry: {c['name']}","excerpt":f"Name: {c['name']}; founding year (owner-supplied): {c.get('founded_year') or 'not recorded'}; Colorado SOS ID: {c.get('co_sos_id') or 'not verified'}; {c.get('note') or ''}","source_ref":"owner-provided:app/registry.py","classification":"public","score":8.0})
    if wants_seal:
        for v in SEALS:
            if company_id and v['company_id']!=company_id:continue
            result.append({"company_id":v['company_id'],"title":v['name'],"excerpt":f"Electronic seal index: {SEAL_LIBRARY_PATH}/{v['file']} (Library only; not live-read).","source_ref":"owner-provided:app/registry.py","classification":"public","score":7.0})
    return result

def brief(question:str,company_id:str|None=None)->dict:
    matches=knowledge.search(question,company_id=company_id,limit=6)+_registry_sources(question,company_id)
    # Registry can be lengthy; group per-company grounded records only.
    matches.sort(key=lambda r:-r['score'])
    with db.connect() as cx:
        where=" WHERE company_id=?" if company_id else ""
        tasks=[dict(x) for x in cx.execute("SELECT id,company_id,title,status,due_date FROM tasks"+where+" ORDER BY id DESC LIMIT 20",(company_id,) if company_id else ())]
        events=[dict(x) for x in cx.execute("SELECT id,company_id,kind,summary,created_at FROM events"+where+" ORDER BY id DESC LIMIT 20",(company_id,) if company_id else ())]
        actions=[dict(x) for x in cx.execute("SELECT id,company_id,title,status FROM action_proposals"+where+" ORDER BY id DESC LIMIT 20",(company_id,) if company_id else ())]
    q=question.lower(); facts=[]; cited=[]
    if any(w in q for w in ['task','deadline','overdue','priority','due']):
        pending=[t for t in tasks if t['status']!='complete']
        facts.append(f"{len(pending)} open/in-progress recorded tasks in this scope.")
        facts.extend(f"[{t['company_id']}] {t['title']} (due {t['due_date'] or 'not set'})." for t in pending[:5])
        cited.append('local-db:tasks')
    if any(w in q for w in ['event','notice','activity','grant','filing']):
        facts.append(f"{len(events)} recent recorded events in this scope (not externally verified).")
        facts.extend(f"[{e['company_id']}] {e['summary']}." for e in events[:4])
        cited.append('local-db:events')
    if any(w in q for w in ['action','proposal','review','decision']):
        pending=[a for a in actions if a['status']=='proposed']
        facts.append(f"{len(pending)} open action proposals in this scope; proposals do not execute external actions.")
        facts.extend(f"[{a['company_id']}] {a['title']}." for a in pending[:4])
        cited.append('local-db:action_proposals')
    if matches:
        facts.append('Relevant registered evidence:')
        facts.extend(f"[{d['company_id']}] {d['title']}: {d['excerpt']} (source: {d['source_ref']})." for d in matches[:6])
        cited.extend(d['source_ref'] for d in matches[:6])
    if not facts:facts=["No supporting corporate records found for this question. Add an authoritative source or connect an approved provider before drawing a conclusion."]
    return {"answer":"\n".join(facts),"sources":sorted(set(cited)),"evidence":matches[:6],"mode":"evidence_retrieval_v2","external_ai_used":False,"external_sources_live":False,"can_execute_external_actions":False}