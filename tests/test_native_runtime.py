"""Real local application workflows; only the external payment provider is doubled."""
import hashlib
import hmac
import io
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest

from core_platform.accounts import AccountStore,AccountDenied,COOKIE,digest
from core_platform.native_runtime import create_native_application,read_settings
from core_platform.deployment import ORIGIN


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'data'/'sds_production.db'
        self.setup=secrets.token_urlsafe(32)
        self.webhook='whsec_'+'synthetic-test-secret'
        self.calls=[]
        def checkout(params,options):
            self.calls.append((params,options))
            return {'id':'cs_test_synthetic','url':'https://checkout.stripe.com/c/pay/synthetic',
                'client_reference_id':params['client_reference_id'],'livemode':False,
                'amount_total':sum(i['price_data']['unit_amount'] for i in params['line_items']),
                'currency':'usd','mode':'payment'}
        client=SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=SimpleNamespace(create=checkout))))
        self.app=create_native_application(self.path,settings={'owner_setup_digest':digest(self.setup),
            'owner_setup_expires':time.time()+3600,'stripe_webhook_secret':self.webhook,
            'stripe_api_key':'rk_'+'test_'+'synthetic-not-a-credential','stripe_livemode':False},stripe_client=client)
        self.password='correct horse battery test phrase'

    def request(self,path,body=None,*,token=None,method=None,headers=None,raw=None):
        raw=raw if raw is not None else json.dumps(body if body is not None else {}).encode()
        env={'HTTP_HOST':'sandersdashandseal.com','PATH_INFO':path,
            'REQUEST_METHOD':method or ('POST' if body is not None else 'GET'),
            'HTTP_ORIGIN':ORIGIN,'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),
            'wsgi.input':io.BytesIO(raw)}
        if token:env['HTTP_COOKIE']=COOKIE+'='+token
        env.update(headers or {})
        result={}
        def start(status,headers):result.update(status=status,headers=dict(headers))
        result['body']=b''.join(self.app(env,start))
        if result['headers'].get('Content-Type','').startswith('application/json'):
            result['json']=json.loads(result['body'])
        return result

    def account(self,name,*,operator=False):
        path='/auth/setup' if operator else '/auth/register'
        data={'username':name,'password':self.password}
        if operator:data['setup_token']=self.setup
        self.assertEqual(self.request(path,data)['status'],'201 Created')
        login=self.request('/auth/login',{'username':name,'password':self.password})
        self.assertEqual(login['status'],'200 OK')
        return login['headers']['Set-Cookie'].split(';')[0].split('=',1)[1]

    def appointment(self,token,request_id='booking-1'):
        data={'request_id':request_id,'jurisdiction':'WI','service':'MOBILE_NOTARY',
            'requested_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+86400)),
            'meeting_area':'Milwaukee','consent':True}
        result=self.request('/api/appointments',data,token=token)
        self.assertEqual(result['status'],'201 Created',result)
        return result['json']['appointment']['case_id']

    def test_account_intake_quote_checkout_webhook_and_durable_paid_record(self):
        customer=self.account('customer-one');operator=self.account('roosevelt',operator=True)
        case=self.appointment(customer)
        quote=self.request('/api/operator/appointments/'+case+'/quote',{'items':{
            'Notarial acts':0,'Travel':1500,'Document support':15000},
            'expires_at':int(time.time())+7200},token=operator)
        self.assertEqual(quote['status'],'201 Created',quote)
        quote_id=quote['json']['quote']['quote_id']
        checkout=self.request('/api/appointments/'+case+'/checkout',{'quote_id':quote_id,'accept_quote':True},token=customer)
        self.assertEqual(checkout['status'],'200 OK',checkout)
        self.assertEqual(checkout['json']['url'],'https://checkout.stripe.com/c/pay/synthetic')
        self.assertEqual(len(self.calls),1)
        duplicate=self.request('/api/appointments/'+case+'/checkout',{'quote_id':quote_id,'accept_quote':True},token=customer)
        self.assertEqual(duplicate['status'],'200 OK');self.assertEqual(len(self.calls),1)
        event={'id':'evt_test_synthetic','type':'checkout.session.completed','livemode':False,
            'data':{'object':{'id':'cs_test_synthetic','client_reference_id':case,
                'payment_intent':'pi_test_synthetic','amount_total':16500,'currency':'usd',
                'mode':'payment','payment_status':'paid'}}}
        raw=json.dumps(event).encode();timestamp=int(time.time())
        signature=hmac.new(self.webhook.encode(),str(timestamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        result=self.request('/stripe/webhook',{},raw=raw,headers={'HTTP_STRIPE_SIGNATURE':f't={timestamp},v1={signature}'})
        self.assertEqual(result['status'],'200 OK')
        detail=self.request('/api/appointments/'+case,token=customer)
        self.assertEqual(detail['json']['payment'],'PAID')
        self.assertEqual(detail['json']['appointment']['status'],'AWAITING_HUMAN_AUTHORITY_REVIEW')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM stripe_events').fetchone()[0],1)
        self.assertEqual(self.request('/stripe/webhook',{},raw=raw,headers={'HTTP_STRIPE_SIGNATURE':f't={timestamp},v1={signature}'})['status'],'200 OK')
        self.app.audit.verify_audit()

    def test_cross_customer_data_and_operator_spoofing_denied(self):
        one=self.account('customer-one');two=self.account('customer-two');case=self.appointment(one)
        self.assertEqual(self.request('/api/appointments/'+case,token=two)['status'],'404 Not Found')
        result=self.request('/api/operator/appointments',token=two,headers={'HTTP_X_ROLE':'OPERATOR','HTTP_X_USER':'roosevelt'})
        self.assertEqual(result['status'],'403 Forbidden')
        self.assertEqual(self.request('/api/appointments',{'actor':'someone'},token=one,headers={'HTTP_ORIGIN':'https://evil.example'})['status'],'403 Forbidden')

    def test_setup_is_one_use_and_never_recreated_on_restart(self):
        self.account('owner-one',operator=True)
        self.assertEqual(self.request('/auth/setup',{'username':'owner-two','password':self.password,'setup_token':self.setup})['status'],'400 Bad Request')
        again=AccountStore(self.path,setup_digest=digest(self.setup),setup_expires=time.time()+10000)
        with self.assertRaises(AccountDenied):again.register('owner-three',self.password,setup_token=self.setup)

    def test_sessions_are_hashed_expire_revoke_and_api_tokens_follow_logout(self):
        token=self.account('customer-one')
        minted=self.request('/auth/token',{},token=token)
        self.assertEqual(minted['status'],'200 OK')
        api=minted['json']['token']
        with sqlite3.connect(self.path) as db:
            self.assertNotIn(token,str(db.execute('SELECT * FROM customer_sessions').fetchall()))
        env={'HTTP_AUTHORIZATION':'Bearer '+api}
        self.assertIsNotNone(self.app.accounts.authenticate(env))
        self.assertEqual(self.request('/auth/logout',{},token=token)['status'],'200 OK')
        self.assertIsNone(self.app.accounts.authenticate(env))
        self.assertIsNone(self.app.accounts.authenticate({'HTTP_COOKIE':COOKIE+'='+token}))
        self.app.accounts.clock=lambda:time.time()+100000
        self.assertIsNone(self.app.accounts.authenticate(env))

    def test_authenticated_ingestion_is_atomic_idempotent_and_not_a_notarial_act(self):
        token=self.account('customer-one')
        data={'request_id':'txn-1','action':'dispatch_transaction','payload':{'value':'example'}}
        first=self.request('/api/pipeline/events',data,token=token)
        self.assertEqual(first['status'],'200 OK',first)
        self.assertEqual(first['json']['result']['status'],'RECEIVED')
        self.assertFalse(first['json']['result']['notarial_act_executed'])
        self.assertEqual(self.request('/api/pipeline/events',data,token=token)['json'],first['json'])
        data['payload']['value']='conflict'
        self.assertEqual(self.request('/api/pipeline/events',data,token=token)['status'],'422 Unprocessable Entity')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM sds_ingestion_events').fetchone()[0],1)
        self.assertEqual(self.request('/api/pipeline/events',data)['status'],'401 Unauthorized')

    def test_unconfigured_payments_do_not_disable_intake_or_fake_complete_readiness(self):
        app=create_native_application(Path(self.temp.name)/'other'/'db.sqlite',settings={})
        old=self.app;self.app=app
        token=self.account('customer-free');self.appointment(token)
        ready=self.request('/readyz')['json']
        self.assertTrue(ready['service_ready']);self.assertFalse(ready['complete_build_ready'])
        self.assertFalse(ready['capabilities']['stripe_credentials_configured'])
        self.assertEqual(self.request('/stripe/webhook',{})['status'],'503 Service Unavailable')
        self.app=old

    def test_auth_pages_cookie_flags_csrf_invalid_json_and_throttling(self):
        for path in ('/auth/login','/auth/register','/auth/setup','/auth/logout'):
            self.assertEqual(self.request(path)['status'],'200 OK')
        token=self.account('customer-one')
        result=self.request('/auth/login',{'username':'customer-one','password':self.password})
        for flag in ('Secure','HttpOnly','SameSite=Strict','Path=/'):
            self.assertIn(flag,result['headers']['Set-Cookie'])
        bad=self.request('/auth/logout',{},token=token,headers={'HTTP_ORIGIN':'https://evil.example'})
        self.assertEqual(bad['status'],'403 Forbidden')
        self.assertEqual(self.request('/auth/login',{},raw=b'{"username":"one","username":"two"}')['status'],'400 Bad Request')
        for _ in range(11):self.request('/auth/login',{'username':'unknown-user','password':self.password})
        self.assertEqual(self.request('/auth/login',{'username':'unknown-user','password':self.password})['status'],'429 Too Many Requests')

    def test_native_notary_operator_workflow_and_evidence(self):
        customer=self.account('customer-one')
        operator=self.account('roosevelt',operator=True)
        self.app.cases.create('native-case-1','WI','RON','customer-one')
        base='/api/operator/native-notary/sessions'
        payload={'session_id':'native-session-1','case_id':'native-case-1','method':'RON','jurisdiction':'WI'}
        self.assertEqual(self.request(base,payload,token=customer)['status'],'403 Forbidden')
        self.assertEqual(self.request(base,payload)['status'],'401 Unauthorized')
        self.assertEqual(self.request(base,payload,token=operator,
            headers={'HTTP_ORIGIN':'https://evil.example'})['status'],'403 Forbidden')
        created=self.request(base,payload,token=operator)
        self.assertEqual(created['status'],'201 Created',created)
        self.assertEqual(created['json']['state'],'AWAITING_AUTHORITY')
        self.assertEqual(self.request(base,payload,token=operator)['status'],'409 Conflict')
        evidence={'evidence_id':'record-1','kind':'AV_RECORDING','sha256':'a'*64}
        route=base+'/native-session-1/evidence'
        self.assertEqual(self.request(route,evidence,token=operator)['status'],'201 Created')
        self.assertEqual(self.request(route,evidence,token=operator)['status'],'201 Created')
        self.assertEqual(len(self.request(route,token=operator)['json']['evidence']),1)
        conflict=dict(evidence,sha256='b'*64)
        self.assertEqual(self.request(route,conflict,token=operator)['status'],'409 Conflict')
        self.assertEqual(self.request(base+'/native-session-1',{'action':'cancel'},token=operator)['status'],'201 Created')
        self.assertEqual(self.request(route,evidence,token=operator)['status'],'409 Conflict')
        self.assertEqual(self.request(base+'/native-session-1',token=customer)['status'],'403 Forbidden')
        self.app.audit.verify_audit()

    def test_native_notary_case_method_and_ron_evidence_isolation(self):
        operator=self.account('roosevelt',operator=True)
        self.app.cases.create('native-co','CO','E_NOTARY','requester')
        base='/api/operator/native-notary/sessions'
        payload={'session_id':'native-co-1','case_id':'native-co','method':'RON','jurisdiction':'CO'}
        self.assertEqual(self.request(base,payload,token=operator)['status'],'409 Conflict')
        payload['method']='E_NOTARY'
        self.assertEqual(self.request(base,payload,token=operator)['status'],'201 Created')
        evidence={'evidence_id':'record-1','kind':'AV_RECORDING','sha256':'a'*64}
        self.assertEqual(self.request(base+'/native-co-1/evidence',evidence,token=operator)['status'],'409 Conflict')

    def test_wrong_payment_environment_or_invalid_signature_cannot_mark_paid(self):
        token=self.account('customer-one');case=self.appointment(token)
        event={'id':'evt_forged','type':'checkout.session.completed','livemode':True,'data':{'object':{}}}
        raw=json.dumps(event).encode();stamp=int(time.time())
        sig=hmac.new(self.webhook.encode(),str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        self.assertEqual(self.request('/stripe/webhook',{},raw=raw,headers={'HTTP_STRIPE_SIGNATURE':f't={stamp},v1={sig}'})['status'],'400 Bad Request')
        self.assertIsNone(self.app.ledger.status(case))


if __name__=='__main__':unittest.main()
