"""Concrete server composition for customer intake, payments and ingestion.

Customer accounts prove account access, never commission, signer identity or
independent AI authority. Those authorities remain separate from this runtime.
"""
import hashlib
import io
import json
import os
import re
from pathlib import Path
import sqlite3

from .provider_connections import WriteProviderClient
from .provider_workflows import ProviderWorkflows, ProviderUnavailable, ProviderRequestConflict
from .cases import CaseDenied
from .accounts import AccountStore, auth_app
from .appointments import AppointmentStore
from .appointment_payments import AppointmentPayments
from .native_notary import NativeNotarySessions, NativeNotaryDenied
from .native_evidence import NativeEvidenceIndex, EvidenceDenied
from .native_documents import NativeDocuments, DocumentDenied
from .native_journal import NativeJournal, JournalDenied
from .native_signatures import NativeSignatures, SignatureDenied
from .native_ron_rooms import NativeRonRooms, RoomDenied
from .native_authority import NativeAuthority, AuthorityDenied
from .native_seals import NativeSeals, SealDenied
from .cases import CaseRegistry
from .deployment import RuntimeBindings, create_application, ORIGIN, _response
from .glass_box_audit import GlassBoxAudit
from .pipeline_api import TransactionStore, TransactionRejected, create_pipeline_app
from .stripe_payments import PaymentLedger, PaymentDenied
from .stripe_webhook_wsgi import make_app
from .stream_api import strict_json
from .upgrade_sidecar import CORE_LAWS
from backend.auth_session import validate_worker_token_request


class UnconfiguredStripeClient:
    def __getattr__(self,name):raise PaymentDenied('Stripe credentials unavailable')


def read_settings(path):
    path=Path(path)
    if not path.exists():return {}
    info=path.stat()
    if path.is_symlink() or info.st_uid!=0 or info.st_mode & 0o037 or info.st_size>16384:
        raise ValueError('Runtime secret configuration must be root-owned, private and bounded')
    settings=json.loads(path.read_text())
    if not isinstance(settings,dict) or set(settings)-{
        'owner_setup_digest','owner_setup_expires','stripe_api_key','stripe_webhook_secret','stripe_livemode',
        'signwell_api_key','signwell_test_mode','bluenotary_api_key'}:
        raise ValueError('Invalid runtime configuration fields')
    return settings


class NativeRuntime:
    def __init__(self,path,settings=None,*,stripe_client=None):
        self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
        os.umask(0o077)
        os.chmod(Path(path).parent,0o700)
        settings={} if settings is None else settings
        self.accounts=AccountStore(path,setup_digest=settings.get('owner_setup_digest'),
            setup_expires=settings.get('owner_setup_expires',0))
        self.audit=GlassBoxAudit(Path(path).with_name('sds_audit.db'))
        self.cases=CaseRegistry(path,CORE_LAWS)
        self.native_sessions=NativeNotarySessions(path)
        self.native_evidence=NativeEvidenceIndex(path)
        self.native_documents=NativeDocuments(path,Path(path).with_name('native_documents'))
        self.native_journal=NativeJournal(path)
        self.native_signatures=NativeSignatures(path)
        self.native_ron_rooms=NativeRonRooms(path)
        self.native_authority=NativeAuthority(path)
        self.native_seals=NativeSeals(path)
        self.appointments=AppointmentStore(self.cases,self.audit)
        self.ledger=PaymentLedger(path)
        self.store=TransactionStore(path)
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS sds_ingestion_events (
                actor TEXT NOT NULL, request_id TEXT NOT NULL, payload TEXT NOT NULL,
                sha256_digest TEXT NOT NULL, status TEXT NOT NULL,
                PRIMARY KEY(actor,request_id))''')
        livemode=settings.get('stripe_livemode',True)
        if type(livemode) is not bool:raise ValueError('Explicit Stripe environment must be boolean')
        key=settings.get('stripe_api_key')
        secret=settings.get('stripe_webhook_secret')
        if key:
            prefix=('rk_live_','sk_live_') if livemode else ('rk_test_','sk_test_')
            if not isinstance(key,str) or not key.startswith(prefix):
                raise ValueError('Stripe key must match configured environment')
        if secret and (not isinstance(secret,str) or not secret.startswith('whsec_')):
            raise ValueError('Invalid Stripe webhook secret configuration')
        if key and secret and stripe_client is None:
            from stripe import StripeClient
            stripe_client=StripeClient(key,stripe_version='2026-08-26.dahlia',max_network_retries=2)
        if type(settings.get('signwell_test_mode',False)) is not bool:
            raise ValueError('Explicit SignWell environment must be boolean')
        clients={}
        for provider in ('signwell','bluenotary'):
            if settings.get(provider+'_api_key'):
                clients[provider]=WriteProviderClient(provider,settings[provider+'_api_key'])
        self.providers=ProviderWorkflows(path,self.cases,self.accounts.operator,self.audit,clients,
            signwell_test_mode=settings.get('signwell_test_mode',False))
        self.payments_configured=bool(key and secret)
        # A test-supplied client never changes whether production credentials exist.
        client=stripe_client or UnconfiguredStripeClient()
        self.payments=AppointmentPayments(self.appointments,self.ledger,client,
            self.accounts.operator,self.fee_review,self.checkout_eligibility,self.audit,ORIGIN,
            expected_livemode=livemode)
        self.webhook=make_app(self.ledger,secret,enabled=bool(secret),expected_livemode=livemode)
        self.bindings=RuntimeBindings(self.appointments,self.payments,self.accounts.authenticate,
            auth_app(self.accounts,ORIGIN),self.available,self.webhook,self.process_event,self.store)
        self.base=create_application(self.bindings)
        self.pipeline=create_pipeline_app(self.accounts.authenticate,self.process_event,self.available,self.store)

    def available(self):
        # Core service readiness is not permission to perform a privileged AI/notarial operation.
        try:
            self.audit.verify_audit()
            with self.store.connect() as db:
                return db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        except Exception:
            return False

    def fee_review(self,case,actor,items):
        # The authenticated operator's itemized approval is a human decision,
        # not an automated certification of statutory fee or commission compliance.
        if not self.accounts.operator(actor):return False
        self.audit.preserve({'stage':'HUMAN_ITEMIZED_QUOTE_REVIEW', 'case_id':case['case_id'],
                            'actor':actor,'items_sha256':hashlib.sha256(json.dumps(items,sort_keys=True).encode()).hexdigest()})
        return True

    def checkout_eligibility(self,appointment,requester):
        self.appointments.get(appointment['case_id'],requester)
        with self.appointments.connect() as db:
            row=db.execute('SELECT 1 FROM appointment_quotes WHERE case_id=?',(appointment['case_id'],)).fetchone()
        return bool(row)

    def process_event(self,transaction,actor,db):
        if (set(transaction)!={'request_id','action','payload'} or transaction['action']!='dispatch_transaction'
            or not isinstance(transaction['payload'],dict)):
            raise TransactionRejected('Only authenticated ingestion is available through this transport')
        raw=json.dumps(transaction['payload'],sort_keys=True,separators=(',',':'),allow_nan=False)
        if len(raw.encode())>65536:raise TransactionRejected('Payload too large')
        checksum=hashlib.sha256(raw.encode()).hexdigest()
        db.execute('INSERT INTO sds_ingestion_events VALUES (?,?,?,?,?)',
                   (actor,transaction['request_id'],raw,checksum,'RECEIVED'))
        return {'status':'RECEIVED','sha256_digest':checksum,'notarial_act_executed':False}

    def status(self):
        return {'platform':'Sanders Dash & Seal','accounts':True,'appointment_intake':True,
            'operator_quotes':True,'durable_ingestion':True,'stripe_credentials_configured':self.payments_configured,
            'signwell_credentials_configured':'signwell' in self.providers.clients,
            'bluenotary_credentials_configured':'bluenotary' in self.providers.clients,
            'provider_request_workflows_implemented':True,'native_notarial_session_intake':True,
            'native_evidence_digest_index':True,'native_document_custody':True,'native_workflow_journal':True,'native_cryptographic_signature_verification':True,'native_ron_room_lifecycle':True,
            'native_authority_evidence_registry':True,'native_cryptographic_seal_evidence':True,'live_payment_verified':False,'notarial_execution_connected':False,
            'independent_ai_authorities_connected':False,'complete_build_verified':False}

    def __call__(self,env,start):
        path=env.get('PATH_INFO','');host=env.get('HTTP_HOST','')
        if host not in ('sandersdashandseal.com','sandersdashandseal.com:443'):
            return self.base(env,start)
        if path == '/api/auth/verify':
            if env.get('REQUEST_METHOD') != 'POST':
                return _response(start,'405 Method Not Allowed',{'error':'post_required'})
            # This endpoint must only be reachable from the trusted worker network.
            # The token itself is verified against the hashed, expiring ledger.
            auth = env.get('HTTP_AUTHORIZATION','')
            if not auth.startswith('Bearer '):
                return _response(start,'401 Unauthorized',{'error':'bearer_required'})
            result = validate_worker_token_request(auth[7:])
            if not result['isValid']:
                return _response(start,'401 Unauthorized',{'error':'invalid_token'})
            return _response(start,'200 OK',result['session'])
        ron_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/ron-room',path)
        if ron_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            sid=ron_route.group(1)
            if env.get('REQUEST_METHOD')=='GET':
                try:return _response(start,'200 OK',self.native_ron_rooms.get(sid))
                except RoomDenied:return _response(start,'404 Not Found',{'error':'room_not_found'})
            if env.get('REQUEST_METHOD')!='POST':
                return _response(start,'405 Method Not Allowed',{'error':'method_not_allowed'})
            if env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=4096:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                data=strict_json(raw)
                if not isinstance(data,dict):raise ValueError('Invalid room request')
                if set(data)=={'room_id'}:result=self.native_ron_rooms.create(sid,data['room_id'])
                elif set(data)=={'consent_digest'}:result=self.native_ron_rooms.consent(sid,data['consent_digest'])
                elif set(data)=={'recording_digest'}:result=self.native_ron_rooms.recording(sid,data['recording_digest'])
                else:raise ValueError('Invalid room operation')
                self.audit.preserve({'stage':'NATIVE_RON_ROOM','actor':actor,'session_id':sid,'room_state':result['state']})
                return _response(start,'201 Created',result)
            except RoomDenied:return _response(start,'409 Conflict',{'error':'room_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        authority_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/authority',path)
        if authority_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            if env.get('REQUEST_METHOD')!='GET':
                return _response(start,'405 Method Not Allowed',{'error':'read_only'})
            try:return _response(start,'200 OK',{'missing':self.native_authority.missing(authority_route.group(1))})
            except AuthorityDenied:return _response(start,'404 Not Found',{'error':'session_not_found'})
        seal_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/seals',path)
        if seal_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            if env.get('REQUEST_METHOD')!='POST':
                return _response(start,'405 Method Not Allowed',{'error':'post_required'})
            if env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=8192:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                data=strict_json(raw)
                if not isinstance(data,dict) or set(data)!=set(('document_id','seal_id','notary_id','key_b64','signature_b64')):
                    raise ValueError('Invalid seal envelope')
                result=self.native_seals.register(seal_route.group(1),**data)
                self.audit.preserve({'stage':'NATIVE_CRYPTOGRAPHIC_SEAL','actor':actor,
                    'session_id':result['session_id'],'seal_id':result['seal_id']})
                return _response(start,'201 Created',result)
            except SealDenied:
                return _response(start,'409 Conflict',{'error':'seal_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        signature_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/signatures',path)
        if signature_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            if env.get('REQUEST_METHOD')!='POST':
                return _response(start,'405 Method Not Allowed',{'error':'post_required'})
            if env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=8192:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                data=strict_json(raw)
                if not isinstance(data,dict) or set(data)!=set(('document_id','signature_id','signer_id','public_key_b64','signature_b64')):
                    raise ValueError('Invalid signature envelope')
                result=self.native_signatures.record(signature_route.group(1),**data)
                self.audit.preserve({'stage':'NATIVE_DOCUMENT_SIGNATURE','actor':actor,
                    'session_id':result['session_id'],'signature_id':result['signature_id'],
                    'document_sha256':result['document_sha256']})
                return _response(start,'201 Created',result)
            except SignatureDenied:
                return _response(start,'409 Conflict',{'error':'signature_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        journal_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/journal',path)
        if journal_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            session_id=journal_route.group(1)
            if env.get('REQUEST_METHOD')=='GET':
                try:
                    self.native_sessions.get(session_id)
                    count=self.native_journal.verify()
                    return _response(start,'200 OK',{'integrity_verified':True,'total_events':count})
                except (NativeNotaryDenied,JournalDenied):
                    return _response(start,'409 Conflict',{'error':'journal_unavailable'})
            if env.get('REQUEST_METHOD')!='POST':
                return _response(start,'405 Method Not Allowed',{'error':'method_not_allowed'})
            if env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=4096:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                data=strict_json(raw)
                if not isinstance(data,dict) or set(data)!=set(('event_id','event_type','evidence_digest')):
                    raise ValueError('Invalid journal envelope')
                result=self.native_journal.append(session_id,actor=actor,**data)
                self.audit.preserve({'stage':'NATIVE_NOTARY_JOURNAL','actor':actor,
                    'session_id':session_id,'event_id':result['event_id'],'entry_hash':result['entry_hash']})
                return _response(start,'201 Created',result)
            except JournalDenied:
                return _response(start,'409 Conflict',{'error':'journal_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        document_route=re.fullmatch(r'/api/operator/native-notary/sessions/([A-Za-z0-9_.-]{1,128})/documents/([A-Za-z0-9_.-]{1,128})',path)
        if document_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            session_id,document_id=document_route.groups()
            method=env.get('REQUEST_METHOD')
            try:
                if method=='GET':
                    content=self.native_documents.read(session_id,document_id)
                    start('200 OK',[('Content-Type','application/octet-stream'),
                        ('Content-Length',str(len(content))),('Cache-Control','no-store'),
                        ('X-Content-Type-Options','nosniff')])
                    return [content]
                if method!='PUT':return _response(start,'405 Method Not Allowed',{'error':'method_not_allowed'})
                if env.get('HTTP_ORIGIN')!=ORIGIN:
                    return _response(start,'403 Forbidden',{'error':'origin_denied'})
                if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/octet-stream':
                    return _response(start,'415 Unsupported Media Type',{'error':'binary_required'})
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=20971520:raise ValueError('Invalid content length')
                content=env['wsgi.input'].read(n)
                if len(content)!=n:raise ValueError('Incomplete document')
                result=self.native_documents.put(session_id,document_id,content)
                self.audit.preserve({'stage':'NATIVE_DOCUMENT_CUSTODY','actor':actor,
                    'session_id':session_id,'document_id':document_id,'sha256':result['sha256']})
                return _response(start,'201 Created',result)
            except DocumentDenied:
                return _response(start,'409 Conflict',{'error':'document_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        native_route=re.fullmatch(r'/api/operator/native-notary/sessions(?:/([A-Za-z0-9_.-]{1,128})(?:/evidence)?)?',path)
        if native_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            method=env.get('REQUEST_METHOD')
            session_id=native_route.group(1)
            evidence_route=path.endswith('/evidence')
            if method=='GET' and session_id:
                try:
                    session=self.native_sessions.get(session_id)
                    self.cases.get(session['case_id'])
                    result={'session':session}
                    if evidence_route:result={'evidence':self.native_evidence.list_for_session(session_id)}
                    return _response(start,'200 OK',result)
                except (NativeNotaryDenied,CaseDenied,EvidenceDenied):
                    return _response(start,'404 Not Found',{'error':'session_not_found'})
            if method!='POST':
                return _response(start,'405 Method Not Allowed',{'error':'method_not_allowed'})
            if env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=8192:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                data=strict_json(raw)
                if not isinstance(data,dict):raise ValueError('Invalid envelope')
                if evidence_route:
                    if set(data)!=set(('evidence_id','kind','sha256')):raise ValueError('Invalid evidence fields')
                    result=self.native_evidence.register(session_id,**data)
                elif session_id is None:
                    if set(data)!=set(('session_id','case_id','method','jurisdiction')):
                        raise ValueError('Invalid session fields')
                    case=self.cases.get(data['case_id'])
                    if case['jurisdiction']!=data['jurisdiction'] or case['service']!=data['method']:
                        raise NativeNotaryDenied('Case mismatch')
                    result=self.native_sessions.create(**data)
                elif set(data)=={'action'} and data['action']=='cancel':
                    result=self.native_sessions.cancel(session_id)
                else:raise ValueError('Unsupported operation')
                self.audit.preserve({'stage':'NATIVE_NOTARY_WORKFLOW','actor':actor,
                    'session_id':result['session_id'],'operation':'EVIDENCE_INDEX' if evidence_route else 'SESSION'})
                return _response(start,'201 Created',result)
            except CaseDenied:
                return _response(start,'404 Not Found',{'error':'case_not_found'})
            except (NativeNotaryDenied,EvidenceDenied):
                return _response(start,'409 Conflict',{'error':'native_workflow_rejected'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        provider_route=re.fullmatch(r'/api/operator/appointments/([A-Za-z0-9_.-]{1,128})/providers(?:/(signwell|bluenotary))?',path)
        if provider_route:
            actor=self.accounts.authenticate(env)
            if actor is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if not self.accounts.operator(actor):return _response(start,'403 Forbidden',{'error':'operator_required'})
            case_id,provider=provider_route.groups()
            try:
                if provider is None and env.get('REQUEST_METHOD')=='GET':
                    return _response(start,'200 OK',{'requests':self.providers.records(case_id,actor)})
                if provider is None or env.get('REQUEST_METHOD')!='POST':
                    return _response(start,'405 Method Not Allowed',{'error':'method_not_allowed'})
                if env.get('HTTP_ORIGIN')!=ORIGIN:
                    return _response(start,'403 Forbidden',{'error':'origin_denied'})
                if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json':
                    return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=32768:raise ValueError('Invalid body length')
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError('Incomplete body')
                result=self.providers.submit(case_id,actor,provider,strict_json(raw))
                return _response(start,'201 Created',result)
            except PermissionError:
                return _response(start,'403 Forbidden',{'error':'operator_required'})
            except CaseDenied:
                return _response(start,'404 Not Found',{'error':'case_not_found'})
            except ProviderRequestConflict:
                return _response(start,'409 Conflict',{'error':'request_conflict_or_outcome_unknown'})
            except ProviderUnavailable:
                return _response(start,'503 Service Unavailable',{'error':'provider_unavailable',
                    'detail':'Check provider configuration or the existing request outcome before resubmitting.'})
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
        if path=='/api/platform/status':
            if env.get('REQUEST_METHOD')!='GET':return _response(start,'405 Method Not Allowed',{'error':'read_only'})
            return _response(start,'200 OK',self.status())
        if path=='/readyz' and env.get('REQUEST_METHOD')=='GET':
            ready=self.available()
            return _response(start,'200 OK' if ready else '503 Service Unavailable',
                {'service_ready':ready,'complete_build_ready':False,'capabilities':self.status()})
        if path=='/api/pipeline/events':
            if env.get('REQUEST_METHOD')!='POST':return _response(start,'405 Method Not Allowed',{'error':'post_required'})
            if self.accounts.authenticate(env) is None:return _response(start,'401 Unauthorized',{'error':'sign_in_required'})
            if 'HTTP_AUTHORIZATION' not in env and env.get('HTTP_ORIGIN')!=ORIGIN:
                return _response(start,'403 Forbidden',{'error':'origin_denied'})
            if env.get('CONTENT_TYPE','').split(';')[0]!='application/json':
                return _response(start,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                n=int(env.get('CONTENT_LENGTH','0'))
                if not 0<n<=70000:raise ValueError()
                raw=env['wsgi.input'].read(n)
                if len(raw)!=n:raise ValueError()
                transaction=strict_json(raw)
                data=json.dumps({'transaction':transaction,'session':{
                    'authorization':'Bearer '+self.accounts.credential(env)}}).encode()
            except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                return _response(start,'400 Bad Request',{'error':'invalid_request'})
            internal=dict(env,PATH_INFO='/api/transactions/process',CONTENT_LENGTH=str(len(data)),
                          **{'wsgi.input':io.BytesIO(data)})
            return self.pipeline(internal,start)
        return self.base(env,start)


def create_native_application(path=None,*,config_path=None,settings=None,stripe_client=None):
    path=path or os.environ.get('SQLITE_DB_PATH','/app/data/sds_production.db')
    if settings is None:
        settings=read_settings(config_path or '/run/sds/runtime.json')
    return NativeRuntime(path,settings,stripe_client=stripe_client)
