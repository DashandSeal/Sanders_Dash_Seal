"""Secure-by-default localhost proof of concept; integrations require separate configuration."""
from __future__ import annotations
from contextlib import asynccontextmanager
import asyncio, json, os, secrets
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from . import db
from .brain import action_policy, classify_event, recommend_tasks
from .registry import COMPANY_BY_ID, COMPANIES, SEALS, SEAL_LIBRARY_PATH

@asynccontextmanager
async def lifespan(_app):
    if not os.getenv("SCS_API_TOKEN"):
        raise RuntimeError("SCS_API_TOKEN is required. Set a strong random token before starting.")
    db.init_db()
    yield

app=FastAPI(title="Sanders Corporations Secretary",version="0.1.0",docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
STATIC=Path(__file__).resolve().parent/"static"
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")


def authorized(x_scs_token: str | None=Header(default=None)):
    expected=os.getenv("SCS_API_TOKEN","")
    if not expected or not x_scs_token or not secrets.compare_digest(x_scs_token,expected):
        raise HTTPException(status_code=401,detail="Owner access token required")
    return "owner"

def ensure_company(company_id: str):
    if company_id not in COMPANY_BY_ID:
        raise HTTPException(status_code=400,detail="Unknown corporate entity")

class TaskNew(BaseModel):
    company_id: str
    title: str=Field(min_length=3,max_length=240)
    due_date: date | None=None

class TaskUpdate(BaseModel):
    status: Literal["open","in_progress","complete"]

class EventNew(BaseModel):
    company_id: str
    kind: Literal["filing.deadline","grant.opportunity","document.created","seal.updated","governance.notice","general.notice"]
    summary: str=Field(min_length=3,max_length=300)
    payload: dict=Field(default_factory=dict)

@app.get("/",response_class=HTMLResponse)
def home():
    return (STATIC/"index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"service":"Sanders Corporations Secretary","status":"running","mode":"local_prototype"}

@app.get("/api/companies",dependencies=[Depends(authorized)])
def companies():
    return COMPANIES

@app.get("/api/seals",dependencies=[Depends(authorized)])
def seals():
    return {"library_path":SEAL_LIBRARY_PATH,"seals":SEALS,"source":"Library asset metadata; not live-fetched"}

@app.get("/api/tasks",dependencies=[Depends(authorized)])
def tasks(company_id:str|None=None):
    if company_id: ensure_company(company_id)
    with db.connect() as cx:
        rows=cx.execute("SELECT * FROM tasks "+("WHERE company_id=? " if company_id else "")+"ORDER BY id DESC LIMIT 200",(company_id,) if company_id else ()).fetchall()
    return [dict(x) for x in rows]

@app.post("/api/tasks",dependencies=[Depends(authorized)],status_code=201)
def add_task(item:TaskNew):
    ensure_company(item.company_id)
    with db.connect() as cx:
        cursor=cx.execute("INSERT INTO tasks(company_id,title,due_date,created_at) VALUES (?,?,?,?)",(item.company_id,item.title,str(item.due_date) if item.due_date else None,db.utc_now()))
        tid=cursor.lastrowid
        db.audit_insert(cx,"owner","task.create",f"task:{tid}",item.model_dump(mode="json"))
    return {"id":tid,"status":"open"}

@app.patch("/api/tasks/{task_id}",dependencies=[Depends(authorized)])
def change_task(task_id:int,item:TaskUpdate):
    with db.connect() as cx:
        cursor=cx.execute("UPDATE tasks SET status=? WHERE id=?",(item.status,task_id))
        if cursor.rowcount==0:
            raise HTTPException(404,"Task not found")
        db.audit_insert(cx,"owner","task.update",f"task:{task_id}",item.model_dump())
    return {"id":task_id,"status":item.status}

@app.get("/api/events",dependencies=[Depends(authorized)])
def events(company_id:str|None=None,after_id:int=0):
    if company_id: ensure_company(company_id)
    sql="SELECT * FROM events WHERE id> ?"+(" AND company_id=?" if company_id else "")+" ORDER BY id DESC LIMIT 150"
    with db.connect() as cx:
        rows=cx.execute(sql,(after_id,company_id) if company_id else (after_id,)).fetchall()
    return [{**dict(x),"payload":json.loads(x["payload"])} for x in rows]

@app.post("/api/events",dependencies=[Depends(authorized)],status_code=201)
def add_event(item:EventNew):
    ensure_company(item.company_id)
    with db.connect() as cx:
        cursor=cx.execute("INSERT INTO events(company_id,kind,summary,payload,created_at) VALUES (?,?,?,?,?)",(item.company_id,item.kind,item.summary,json.dumps(item.payload,sort_keys=True),db.utc_now()))
        eid=cursor.lastrowid
        db.audit_insert(cx,"owner","event.record",f"event:{eid}",item.model_dump())
    return {"id":eid,"advice":classify_event(item.kind,item.company_id,item.summary)}

@app.get("/api/dashboard",dependencies=[Depends(authorized)])
def dashboard():
    with db.connect() as cx:
        count_tasks=cx.execute("SELECT status,COUNT(*) cnt FROM tasks GROUP BY status").fetchall()
        count_events=cx.execute("SELECT COUNT(*) cnt FROM events").fetchone()["cnt"]
        recent=[dict(x) for x in cx.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 30")]
    return {"entities":len(COMPANIES),"task_counts":{x["status"]:x["cnt"] for x in count_tasks},"event_count":count_events,"due_alerts":recommend_tasks(recent),"audit":db.verify_audit()}

@app.get("/api/audit/verify",dependencies=[Depends(authorized)])
def audit_verify():
    return db.verify_audit()

class Inquiry(BaseModel):
    question: str=Field(min_length=3,max_length=500)
    company_id: str | None = None

@app.post("/api/secretary/ask",dependencies=[Depends(authorized)])
def secretary_ask(q:Inquiry):
    if q.company_id: ensure_company(q.company_id)
    lower=q.question.lower()
    with db.connect() as cx:
        tasks=[dict(x) for x in cx.execute("SELECT * FROM tasks "+("WHERE company_id=? " if q.company_id else "")+"ORDER BY id DESC LIMIT 50",(q.company_id,) if q.company_id else ())]
        events=[dict(x) for x in cx.execute("SELECT * FROM events "+("WHERE company_id=? " if q.company_id else "")+"ORDER BY id DESC LIMIT 10",(q.company_id,) if q.company_id else ())]
    if any(x in lower for x in ("registration", "entity", "secretary of state", "sos", "founded", "year")):
        chosen=[COMPANY_BY_ID[q.company_id]] if q.company_id else COMPANIES
        answer="; ".join(f"{c['name']}: founded {c['founded_year'] or 'not stated'}; Colorado SOS ID {c['co_sos_id'] or 'not stored'}" for c in chosen)
        sources=["owner_provided_registry:registry.py"]
    elif any(x in lower for x in ("seal", "letterhead", "crest")):
        answer="The electronic seal source index is "+SEAL_LIBRARY_PATH+". Headquarters and the three LLCs have separate seal designs; S & G Security's design has not been added to this prototype."
        sources=["owner_provided_registry:registry.py", "library_path_reference"]
    elif any(x in lower for x in ("task", "deadline", "due", "priority")):
        open_items=[t for t in tasks if t['status']!='complete']
        answer=f"There are {len(open_items)} current open/in-progress tasks in this scope. "+("Most recent: "+"; ".join(t['title'] for t in open_items[:5]) if open_items else "No tasks have been recorded here yet.")
        sources=["local_db:tasks"]
    elif any(x in lower for x in ("event", "news", "activity", "notice", "grant")):
        answer=f"There are {len(events)} recent stored events in this scope. "+("Most recent: "+"; ".join(e['summary'] for e in events[:5]) if events else "No external events or grants have been connected to this system yet.")
        sources=["local_db:events"]
    elif any(x in lower for x in ("audit", "integrity", "security")):
        audit=db.verify_audit()
        answer=f"Local hash-chain verification: {audit['valid']}; entries: {audit['entries']}. This does not establish external notarial or cryptographic signature authority."
        sources=["local_db:audit"]
    else:
        answer="I can answer questions grounded in the local corporate registry, seals, tasks, events, and audit log. To answer other questions, add approved sources and an AI retrieval/model adapter."
        sources=["system_capabilities:v0.1"]
    return {"answer":answer,"sources":sources,"mode":"transparent_local_inquiry","external_ai_used":False}

@app.get("/api/policy/{action}",dependencies=[Depends(authorized)])
def policy(action:str):
    return action_policy(action)

@app.get("/api/live",dependencies=[Depends(authorized)])
async def live(after_id:int=0):
    async def stream():
        latest=after_id
        yield ": connected\n\n"
        while True:
            with db.connect() as cx:
                rows=cx.execute("SELECT id,company_id,kind,summary,created_at FROM events WHERE id>? ORDER BY id ASC LIMIT 50",(latest,)).fetchall()
            for r in rows:
                latest=r["id"]
                yield f"event: corporate_event\\nid: {latest}\\ndata: {json.dumps(dict(r))}\\n\\n".replace("\\n","\n")
            yield ": heartbeat\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})