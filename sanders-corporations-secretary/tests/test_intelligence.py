"""Substantial RTSA behavior: source-scoped intelligence, governance and connectors."""
import os
os.environ.setdefault('SCS_API_TOKEN','test-secret-not-for-production')
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import connectors, model_adapter

TOKEN={'X-SCS-Token':'test-secret-not-for-production'}

@pytest.fixture()
def c(tmp_path,monkeypatch):
    monkeypatch.setenv('SCS_DB_PATH',str(tmp_path/'scs.sqlite3'))
    monkeypatch.delenv('SCS_MODEL_API_KEY',raising=False)
    monkeypatch.delenv('SCS_MODEL_API_URL',raising=False)
    monkeypatch.delenv('SCS_MODEL_NAME',raising=False)
    monkeypatch.delenv('SCS_ALLOW_REMOTE_INFERENCE',raising=False)
    with TestClient(app) as client:yield client

def add(c,company,title,body,reference='official-source-1'):
    return c.post('/api/knowledge',headers=TOKEN,json={'company_id':company,'title':title,'body':body,'source_type':'official_record','source_ref':reference,'classification':'internal'})

def test_company_scoped_knowledge_search_and_no_other_company_leak(c):
    assert add(c,'legal_helpers','Contract records','Legal Helpers has confidential contract files 21A').status_code==201
    assert add(c,'senior_living','Care plan records','Senior Living business care plans 17B','care-plan').status_code==201
    res=c.get('/api/knowledge/search',headers=TOKEN,params={'q':'confidential contract','company_id':'senior_living'}).json()
    assert res==[]
    res=c.get('/api/knowledge/search',headers=TOKEN,params={'q':'confidential contract','company_id':'legal_helpers'}).json()
    assert len(res)==1 and res[0]['source_ref']=='official-source-1'
    assert 'body' not in res[0]

def test_evidence_inquiry_with_sources(c):
    add(c,'home_healthcare','Agency filing record','Verified county services phase-one nonmedical operations','ref-HH')
    r=c.post('/api/secretary/ask',headers=TOKEN,json={'question':'What are the nonmedical county services?','company_id':'home_healthcare'}).json()
    assert 'ref-HH' in r['sources']
    assert 'Verified county services' in r['answer']
    assert r['external_ai_used'] is False
    assert r['external_sources_live'] is False

def test_no_evidence_no_invention(c):
    r=c.post('/api/secretary/ask',headers=TOKEN,json={'question':'What are the quarterly profits for 2027?','company_id':'security'}).json()
    assert 'No supporting corporate records' in r['answer']
    assert not r['evidence']

def test_event_creates_reviewable_intelligence_proposal(c):
    e=c.post('/api/events',headers=TOKEN,json={'company_id':'senior_living','kind':'filing.deadline','summary':'Annual filing deadline confirmed','payload':{}})
    assert e.status_code==201
    proposal=e.json()['proposals'][0]
    assert proposal['action_type']=='verify_filing_deadline'
    queue=c.get('/api/actions',headers=TOKEN).json()
    assert len(queue)==1 and queue[0]['status']=='proposed'
    approved=c.patch(f'/api/actions/{proposal["id"]}',headers=TOKEN,json={'status':'acknowledged','note':'Reviewed by owner'})
    assert approved.json()['external_action_executed'] is False
    assert c.get('/api/intelligence/status',headers=TOKEN).json()['pending_action_proposals']==0
    assert c.patch(f'/api/actions/{proposal["id"]}',headers=TOKEN,json={'status':'dismissed'}).status_code==409
    assert c.get('/api/audit/verify',headers=TOKEN).json()['valid']

def test_connector_ingest_is_idempotent_and_source_anchored(c,monkeypatch):
    sha='a'*40
    monkeypatch.setattr(connectors,'read_github_head',lambda fetcher=None:{'sha':sha,'url':'https://github.com/DashandSeal/Sanders_Dash_Seal/commit/'+sha,'message':'SCS integration tests','retrieved_at':'2026-11-17T12:00:00+00:00','source':'GitHub public REST API'})
    a=connectors.sync_public_github()
    b=connectors.sync_public_github()
    assert a['changed'] is True and b['changed'] is False
    e=c.get('/api/events',headers=TOKEN).json()
    assert len(e)==1 and e[0]['company_id']=='headquarters'
    assert e[0]['payload']['sha']==sha
    assert c.get('/api/audit/verify',headers=TOKEN).json()['valid']

def test_inference_is_off_without_explicit_owner_enablement(c):
    add(c,'legal_helpers','Corporate scope','Legal Helpers company-specific document management')
    r=c.post('/api/secretary/ask',headers=TOKEN,json={'question':'What is company document management?','company_id':'legal_helpers','use_hosted_model':True}).json()
    assert r['external_ai_used'] is False
    assert 'not available' in r['model_status']

def test_optional_model_adapter_enforces_https_and_owner_switch(monkeypatch):
    monkeypatch.setenv('SCS_MODEL_API_KEY','TEST_KEY_DO_NOT_USE')
    monkeypatch.setenv('SCS_MODEL_NAME','configured-model')
    monkeypatch.setenv('SCS_MODEL_API_URL','http://localhost:9000')
    monkeypatch.setenv('SCS_ALLOW_REMOTE_INFERENCE','true')
    with pytest.raises(ValueError,match='HTTPS'):
        model_adapter.infer('Test?', [{'source_ref':'id','company_id':'security','title':'X','excerpt':'text'}],sender=lambda u,p:{'choices':[{'message':{'content':'okay'}}]})
    monkeypatch.setenv('SCS_MODEL_API_URL','https://inference.example.org/v1/chat/completions')
    result=model_adapter.infer('Test?', [{'source_ref':'id','company_id':'security','title':'X','excerpt':'text'}],sender=lambda u,p:{'choices':[{'message':{'content':'[id] grounded'}}]})
    assert result=='[id] grounded'
    monkeypatch.setenv('SCS_ALLOW_REMOTE_INFERENCE','false')
    with pytest.raises(ValueError,match='not enabled'):
        model_adapter.infer('Test?', [])

def test_all_new_endpoints_require_auth(c):
    for url in ['/api/intelligence/status','/api/knowledge/search?q=test','/api/actions','/api/connectors/status']:
        assert c.get(url).status_code==401
    assert c.post('/api/connectors/github/sync').status_code==401


def test_company_registry_does_not_invent_security_sos_id(c):
    r=c.post('/api/secretary/ask',headers=TOKEN,json={'question':'What is the Security Inc SOS ID?','company_id':'security'}).json()
    assert 'not verified' in r['answer']