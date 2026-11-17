import os
os.environ.setdefault('SCS_API_TOKEN','test-secret-not-for-production')
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SCS_DB_PATH',str(tmp_path/'test.sqlite3'))
    with TestClient(app) as c:
        yield c

TOKEN={'X-SCS-Token':'test-secret-not-for-production'}

def test_requires_owner_authentication(client):
    assert client.get('/api/companies').status_code == 401
    assert client.get('/api/companies',headers=TOKEN).status_code == 200

def test_roster_is_distinct(client):
    r=client.get('/api/companies',headers=TOKEN).json()
    assert len(r)==5
    assert next(x for x in r if x['id']=='legal_helpers')['co_sos_id']=='20258029131'
    assert next(x for x in r if x['id']=='security')['founded_year']==1996
    assert next(x for x in r if x['id']=='home_healthcare')['founded_year']==2025

def test_event_and_audit_verification(client):
    r=client.post('/api/events',headers=TOKEN,json={'company_id':'home_healthcare','kind':'filing.deadline','summary':'Test filing deadline','payload':{}})
    assert r.status_code==201
    assert r.json()['advice']['signals'][0]['severity']=='high'
    assert len(client.get('/api/events',headers=TOKEN).json())==1
    check=client.get('/api/audit/verify',headers=TOKEN).json()
    assert check['valid'] and check['entries']==1

def test_task_lifecycle(client):
    r=client.post('/api/tasks',headers=TOKEN,json={'company_id':'senior_living','title':'Review annual registration'})
    assert r.status_code==201
    tid=r.json()['id']
    assert client.patch(f'/api/tasks/{tid}',headers=TOKEN,json={'status':'complete'}).status_code==200
    assert client.get('/api/tasks?company_id=senior_living',headers=TOKEN).json()[0]['status']=='complete'
    assert client.get('/api/audit/verify',headers=TOKEN).json()['entries']==2

def test_reject_wrong_entity(client):
    r=client.post('/api/tasks',headers=TOKEN,json={'company_id':'unknown','title':'Should fail'})
    assert r.status_code==400

def test_sensitive_action_policy(client):
    policy=client.get('/api/policy/financial_disbursement',headers=TOKEN).json()
    assert policy['owner_authorization_required'] is True
    assert policy['auto_executed'] is False


def test_secretary_grounded_inquiry(client):
    r=client.post('/api/secretary/ask',headers=TOKEN,json={'question':'What is the Colorado SOS ID for Legal Helpers?','company_id':'legal_helpers'})
    assert r.status_code==200
    data=r.json()
    assert '20258029131' in data['answer']
    assert data['external_ai_used'] is False

def test_audit_detects_tampering(client):
    from app import db
    client.post('/api/events',headers=TOKEN,json={'company_id':'legal_helpers','kind':'general.notice','summary':'Original business event','payload':{}})
    with db.connect() as cx:
        cx.execute("UPDATE audit SET payload=? WHERE id=1",('{"unexpected":"change"}',))
    assert client.get('/api/audit/verify',headers=TOKEN).json()['valid'] is False

def test_company_specific_task_isolation(client):
    client.post('/api/tasks',headers=TOKEN,json={'company_id':'home_healthcare','title':'Home Healthcare task'})
    client.post('/api/tasks',headers=TOKEN,json={'company_id':'legal_helpers','title':'Legal Helpers task'})
    names=[t['title'] for t in client.get('/api/tasks?company_id=legal_helpers',headers=TOKEN).json()]
    assert names==['Legal Helpers task']