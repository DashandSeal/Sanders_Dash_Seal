"""Secure-by-default localhost proof of concept; integrations require separate configuration."""
from __future__ import annotations
from contextlib import asynccontextmanager, suppress
import asyncio, json, os, secrets
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from . import db, knowledge, intelligence, connectors, model_adapter
from .brain import action_policy, classify_event, recommend_tasks
from .registry import COMPANY_BY_ID, COMPANIES, SEALS, SEAL_LIBRARY_PATH

@asynccontextmanager
async def lifespan(_app):
    if not os.getenv("SCS_API_TOKEN"):
        raise RuntimeError("SCS_API_TOKEN is required. Set a strong random token before starting.")
    db.init_db()
    polling=int(os.getenv('SCS_GITHUB_POLL_SECONDS','0'))
    worker=None
    if polling:
        if polling<180:raise RuntimeError('SCS_GITHUB_POLL_SECONDS must be at least 180, or 0 to disable')
        async def poll_public_github():
            while True:
                try:await asyncio.to_thread(connectors.sync_public_github)
                except Exception:pass  # Connector failure never blocks local corporate operations.
                await asyncio.sleep(polling)
        worker=asyncio.create_task(poll_public_github())
    try:yield
    finally:
        if worker:
            worker.cancel()
            with suppress(asyncio.CancelledError):await worker

app=FastAPI(title="Sanders Corporations Secretary",version="0.2.0",docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
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
    return {"service":"Sanders Corporations Secretary","status":"running","mode":"local_rtsa_core_v2"}

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
    return {"id":eid,"advice":classify_event(item.kind,item.company_id,item.summary),"proposals":intelligence.evaluate_event(eid)}

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
    company_id: str | None=None
    use_hosted_model: bool=False

@app.post('/api/secretary/ask',dependencies=[Depends(authorized)])
def secretary_ask(q:Inquiry):
    if q.company_id:ensure_company(q.company_id)
    response=intelligence.brief(q.question,q.company_id)
    if q.use_hosted_model:
        if not response['evidence']:
            response['model_status']='skipped: no supporting evidence to send'
        else:
            try:
                response['answer']=model_adapter.infer(q.question,response['evidence'])
                response['external_ai_used']=True
                response['mode']='hosted_model_evidence_grounded_v2'
                response['model_status']='success'
            except Exception as ex:
                response['model_status']='not available: '+str(ex)
    return response

class KnowledgeNew(BaseModel):
    company_id: str
    title: str=Field(min_length=3,max_length=180)
    body: str=Field(min_length=5,max_length=30000)
    source_type: Literal['owner_record','official_record','public_document','external_notice','other']
    source_ref: str=Field(min_length=3,max_length=500)
    classification: Literal['internal','public']='internal'

@app.post('/api/knowledge',dependencies=[Depends(authorized)],status_code=201)
def knowledge_add(item:KnowledgeNew):
    ensure_company(item.company_id)
    return knowledge.add_knowledge(**item.model_dump())

@app.get('/api/knowledge/search',dependencies=[Depends(authorized)])
def knowledge_search(q:str=Query(min_length=3,max_length=300),company_id:str|None=None):
    if company_id:ensure_company(company_id)
    return knowledge.search(q,company_id)

@app.get('/api/intelligence/status',dependencies=[Depends(authorized)])
def intelligence_status():
    with db.connect() as cx:
        docs=cx.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]
        pending=cx.execute("SELECT COUNT(*) FROM action_proposals WHERE status='proposed'").fetchone()[0]
        events=cx.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    return {'engine':'evidence-grounded event intelligence v2','local_knowledge_records':docs,
      'pending_action_proposals':pending,'recorded_events':events,
      'realtime_event_stream':'local database SSE','connectors':connectors.status(),
      'hosted_model':model_adapter.model_config(),'live_external_portals_connected':False,'github_poll_seconds':int(os.getenv('SCS_GITHUB_POLL_SECONDS','0'))}

@app.get('/api/actions',dependencies=[Depends(authorized)])
def actions(company_id:str|None=None):
    if company_id:ensure_company(company_id)
    with db.connect() as cx:
        rows=cx.execute('SELECT * FROM action_proposals'+(' WHERE company_id=?' if company_id else '')+' ORDER BY id DESC LIMIT 200', (company_id,) if company_id else ()).fetchall()
    return [dict(x) for x in rows]

class ActionReview(BaseModel):
    status: Literal['acknowledged','dismissed']
    note: str=Field(default='',max_length=500)

@app.patch('/api/actions/{action_id}',dependencies=[Depends(authorized)])
def review_action(action_id:int,decision:ActionReview):
    with db.connect() as cx:
        row=cx.execute('SELECT * FROM action_proposals WHERE id=?',(action_id,)).fetchone()
        if not row:raise HTTPException(404,'Proposal not found')
        if row['status']!='proposed':raise HTTPException(409,'Proposal has already been reviewed')
        cx.execute('UPDATE action_proposals SET status=?,reviewed_at=?,review_note=? WHERE id=?', (decision.status,db.utc_now(),decision.note,action_id))
        db.audit_insert(cx,'owner','proposal.review',f'action:{action_id}',{'status':decision.status,'note':decision.note})
    return {'id':action_id,'status':decision.status,'external_action_executed':False}

@app.post('/api/connectors/github/sync',dependencies=[Depends(authorized)])
def github_sync():
    try:return connectors.sync_public_github()
    except Exception as ex:raise HTTPException(502,'GitHub public connector failed: '+str(ex))

@app.get('/api/connectors/status',dependencies=[Depends(authorized)])
def connector_status():
    return connectors.status()

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