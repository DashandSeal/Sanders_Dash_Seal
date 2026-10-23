"""Durable execution, real local HTTP transport and evidence-grounding tests."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.tech_team_dispatch import TechTeamDispatcher,DispatchDenied
from core_platform.technical_worker import TechnicalWorker
from core_platform.operational_runtime import OperationalRuntime,observation
from core_platform.incident_diagnosis import IncidentDiagnosis,DiagnosticEvidenceReview,diagnose_open_incidents,model_task_id
from core_platform.local_inference import LocalInferenceClient,InferenceUnavailable
from core_platform.upgrade_sidecar import CORE_LAWS


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'runtime.db';self.now=[100]
        self.audit=GlassBoxAudit(Path(self.temp.name)/'audit.db')
        self.dispatch=TechTeamDispatcher(self.path,CORE_LAWS,self.audit,clock=lambda:self.now[0])

    def submit(self,task='task-1',cap='BUG_DIAGNOSIS'):
        self.dispatch.submit(task,'IT_AI_Manager_v15.0',cap,'ApplicationAgent','MASTER-6',{})

    def test_worker_really_executes_and_preserves_results_across_restart(self):
        self.submit();calls=[]
        def handler(task):calls.append(task['task_id']);return {'finding':'observed'}
        worker=TechnicalWorker(self.dispatch,'worker-one',{'BUG_DIAGNOSIS':handler},
            reviewer=lambda task,result:{'passed':True,'kind':'test-only-local-review'})
        self.assertEqual(worker.once()['status'],'REVIEW_READY')
        again=TechTeamDispatcher(self.path,CORE_LAWS,self.audit)
        value=again.inspect('task-1')
        self.assertEqual(value['execution']['result'],{'finding':'observed'})
        self.assertTrue(value['execution']['verification']['passed'])
        self.assertEqual(calls,['task-1']);self.assertIsNone(worker.once())
        self.audit.verify_audit()

    def test_missing_reviewer_does_not_fabricate_verification(self):
        self.submit()
        worker=TechnicalWorker(self.dispatch,'worker-one',{'BUG_DIAGNOSIS':lambda task:{'analysis':'result'}})
        self.assertEqual(worker.once()['status'],'RESULT_RECORDED')
        self.assertFalse(self.dispatch.inspect('task-1')['execution']['verification']['passed'])

    def test_mutating_capabilities_have_no_automatic_execution_or_retry(self):
        self.submit(cap='INFRASTRUCTURE_REPAIR')
        with self.assertRaises(DispatchDenied):
            TechnicalWorker(self.dispatch,'worker-one',{'INFRASTRUCTURE_REPAIR':lambda task:{'repaired':True}})
        self.assertIsNone(self.dispatch.claim_next('worker-one',{'BUG_DIAGNOSIS'}))
        self.assertEqual(self.dispatch.inspect('task-1')['status'],'QUEUED')

    def test_expired_claim_redelivers_only_read_only_work_and_stale_worker_cannot_finish(self):
        self.submit();first=self.dispatch.claim_next('worker-one',{'BUG_DIAGNOSIS'},lease_seconds=10)
        self.assertIsNone(self.dispatch.claim_next('worker-two',{'BUG_DIAGNOSIS'}))
        self.now[0]+=11
        second=self.dispatch.claim_next('worker-two',{'BUG_DIAGNOSIS'})
        self.assertNotEqual(first['claim'],second['claim'])
        with self.assertRaises(DispatchDenied):self.dispatch.finish('task-1',first['claim'],{'finding':'late'},{'passed':True})
        with self.assertRaises(DispatchDenied):self.dispatch.fail('task-1',first['claim'])
        self.dispatch.finish('task-1',second['claim'],{'finding':'current'},{'passed':True})
        self.assertEqual(self.dispatch.inspect('task-1')['execution']['attempts'],2)
        self.assertNotIn('claim',json.dumps(self.dispatch.list_tasks()))

    def test_two_concurrent_workers_do_not_claim_same_task(self):
        self.submit();barrier=threading.Barrier(2);results=[];errors=[]
        def claim(name):
            try:barrier.wait(3);results.append(self.dispatch.claim_next(name,{'BUG_DIAGNOSIS'}))
            except Exception as error:errors.append(error)
        threads=[threading.Thread(target=claim,args=(name,)) for name in ('worker-one','worker-two')]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5)
        self.assertFalse(errors);self.assertEqual(sum(r is not None for r in results),1)

    def test_handler_error_is_durable_redacted_and_not_retried(self):
        self.submit()
        def fail(task):raise RuntimeError('private credential and customer record')
        worker=TechnicalWorker(self.dispatch,'worker-one',{'BUG_DIAGNOSIS':fail})
        self.assertEqual(worker.once()['status'],'FAILED')
        value=self.dispatch.inspect('task-1')
        self.assertEqual(value['execution']['error_code'],'HANDLER_FAILED')
        self.assertNotIn('credential',json.dumps(value));self.assertIsNone(worker.once())

    def test_invalid_lease_and_oversized_or_nonfinite_results_rejected(self):
        self.submit()
        for lease in (0,-1,True,float('nan'),float('inf')):
            with self.assertRaises(DispatchDenied):self.dispatch.claim_next('worker',{'BUG_DIAGNOSIS'},lease_seconds=lease)
        item=self.dispatch.claim_next('worker',{'BUG_DIAGNOSIS'})
        with self.assertRaises(DispatchDenied):self.dispatch.finish('task-1',item['claim'],{'x':'a'*65537},{'passed':True})
        with self.assertRaises(ValueError):self.dispatch.finish('task-1',item['claim'],{'x':float('nan')},{'passed':True})


class DiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'runtime.db'
        self.runtime=OperationalRuntime(self.path)
        self.audit=GlassBoxAudit(Path(self.temp.name)/'audit.db')
        self.runtime.cycle({'uptime':lambda:observation('FAULT','HTTP_UNAVAILABLE')})

    def test_fault_automatically_becomes_one_grounded_task_and_does_not_claim_model_inference(self):
        result=diagnose_open_incidents(self.runtime,self.audit)
        self.assertEqual(result[0]['status'],'REVIEW_READY')
        dispatcher=TechTeamDispatcher(self.path,CORE_LAWS,self.audit)
        tasks=dispatcher.list_tasks();self.assertEqual(len(tasks),1)
        value=tasks[0]['execution']['result']
        self.assertFalse(value['model_inference']);self.assertFalse(value['execution_authorized'])
        self.assertFalse(value['cause_proven']);self.assertFalse(value['repair_executed'])
        self.assertTrue(all(h['status']=='UNPROVEN' for h in value['hypotheses']))
        self.assertEqual(diagnose_open_incidents(self.runtime,self.audit),[])
        self.assertEqual(len(dispatcher.list_tasks()),1)

    def test_independent_review_rejects_changed_findings_or_execution_claims(self):
        task={'evidence':{'incident_id':1}}
        result=IncidentDiagnosis(self.path)(task)
        review=DiagnosticEvidenceReview(self.path)
        self.assertTrue(review(task,result)['passed'])
        for key,value in [('observed_code','DATABASE_CORRUPT'),('cause_proven',True),
                          ('repair_executed',True),('execution_authorized',True),('finding','REPAIRED')]:
            altered=deepcopy(result);altered[key]=value
            with self.subTest(key=key):self.assertFalse(review(task,altered)['passed'])
        altered=deepcopy(result);altered['evidence']['sha256']='0'*64
        self.assertFalse(review(task,altered)['passed'])
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE ai_observation_history SET observation=? WHERE agent=?',
                       (json.dumps(observation('HEALTHY','HTTP_VERIFIED')),'UptimeAgent'))
        self.assertFalse(review(task,result)['passed'])

    def test_inference_unavailable_keeps_deterministic_findings_with_truthful_status(self):
        class Unavailable:
            def diagnose(self,task):raise InferenceUnavailable('unavailable')
        result=IncidentDiagnosis(self.path,Unavailable())({'evidence':{'incident_id':1}})
        self.assertFalse(result['model_inference'])
        self.assertEqual(result['diagnostic_model_status'],'UNAVAILABLE')

    def test_unavailable_model_retries_after_restart_and_stops_after_response(self):
        now=[100];self.runtime.clock=lambda:now[0]
        class Model:
            available=False
            def diagnose(self,task):
                if not self.available:raise InferenceUnavailable('offline')
                return {'hypotheses':[{'statement':'Unproven test hypothesis'}],'counterevidence':[]}
        model=Model()
        diagnose_open_incidents(self.runtime,self.audit,model)
        now[0]=159
        self.assertEqual(diagnose_open_incidents(self.runtime,self.audit,model),[])
        self.runtime=OperationalRuntime(self.path,clock=lambda:now[0])
        now[0]=160;model.available=True
        self.assertEqual(diagnose_open_incidents(self.runtime,self.audit,model)[0]['status'],'REVIEW_READY')
        now[0]=1000
        self.assertEqual(diagnose_open_incidents(self.runtime,self.audit,model),[])
        tasks=TechTeamDispatcher(self.path,CORE_LAWS,self.audit).list_tasks()
        self.assertEqual(len(tasks),2)
        self.assertEqual(tasks[0]['execution']['result']['diagnostic_model_status'],'RESPONDED')
        self.assertEqual(tasks[1]['execution']['result']['diagnostic_model_status'],'UNAVAILABLE')
        self.assertFalse(tasks[0]['execution']['result']['execution_authorized'])

    def test_concurrent_cycles_submit_and_execute_one_retry(self):
        now=[100];self.runtime.clock=lambda:now[0]
        class Model:
            def diagnose(self,task):raise InferenceUnavailable('offline')
        model=Model();diagnose_open_incidents(self.runtime,self.audit,model)
        now[0]=160;barrier=threading.Barrier(2);errors=[]
        from unittest.mock import patch
        def synchronized_id(dispatcher,incident):
            task_id=model_task_id(dispatcher,incident)
            barrier.wait(3)
            return task_id
        def run():
            try:diagnose_open_incidents(self.runtime,self.audit,model)
            except Exception as error:errors.append(error)
        with patch('core_platform.incident_diagnosis.model_task_id',side_effect=synchronized_id):
            threads=[threading.Thread(target=run) for _ in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(5)
        self.assertFalse(errors)
        tasks=TechTeamDispatcher(self.path,CORE_LAWS,self.audit).list_tasks()
        self.assertEqual(len(tasks),2)
        self.assertEqual(tasks[0]['execution']['attempts'],1)

    def test_incident_recovery_stops_model_retries(self):
        now=[100];self.runtime.clock=lambda:now[0]
        class Model:
            def diagnose(self,task):raise InferenceUnavailable('offline')
        model=Model();diagnose_open_incidents(self.runtime,self.audit,model)
        self.runtime.cycle({'uptime':lambda:observation('HEALTHY','HTTP_VERIFIED')})
        now[0]=200
        self.assertEqual(diagnose_open_incidents(self.runtime,self.audit,model),[])
        self.assertEqual(len(TechTeamDispatcher(self.path,CORE_LAWS,self.audit).list_tasks()),1)

    def test_model_work_processed_without_configuration_can_reconnect_later(self):
        now=[100];self.runtime.clock=lambda:now[0]
        dispatcher=TechTeamDispatcher(self.path,CORE_LAWS,self.audit,clock=lambda:now[0])
        dispatcher.submit('observed-incident-1-model','IT_AI_Manager_v15.0','BUG_DIAGNOSIS',
            'UptimeAgent','MASTER-6',{'incident_id':1})
        diagnose_open_incidents(self.runtime,self.audit)
        self.assertEqual(dispatcher.inspect('observed-incident-1-model')['execution']['result']['diagnostic_model_status'],'NOT_CONFIGURED')
        class Model:
            def diagnose(self,task):raise InferenceUnavailable('offline')
        now[0]=160
        diagnose_open_incidents(self.runtime,self.audit,Model())
        self.assertEqual(len(dispatcher.list_tasks()),3)

    def test_long_valid_model_response_retains_task_ownership(self):
        now=[100];self.runtime.clock=lambda:now[0]
        class Model:
            timeout=90
            def diagnose(self,task):
                now[0]+=61
                return {'hypotheses':[{'statement':'Unproven test hypothesis'}],'counterevidence':[]}
        result=diagnose_open_incidents(self.runtime,self.audit,Model())
        self.assertEqual(result[0]['status'],'REVIEW_READY')


class LocalInferenceTests(unittest.TestCase):
    def setUp(self):
        self.requests=[];self.mode='good';outer=self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.requests.append(value)
                if outer.mode=='unavailable':
                    self.send_response(503);self.end_headers();return
                if outer.mode=='redirect':
                    self.send_response(302);self.send_header('Location','http://outside.invalid');self.end_headers();return
                user=json.loads(value['messages'][1]['content'])
                result={'hypotheses':[{'statement':'Process might be stopped',
                    'evidence_sha256':user['evidence']['sha256']}],'counterevidence':[]}
                if outer.mode=='wrong_evidence':result['hypotheses'][0]['evidence_sha256']='0'*64
                if outer.mode=='extra':result['execute_shell']='do not execute'
                raw=json.dumps({'choices':[{'finish_reason':'length' if outer.mode=='truncated' else 'stop',
                    'message':{'role':'assistant','content':json.dumps(result)}}]}).encode()
                self.send_response(200);self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.client=LocalInferenceClient('http://127.0.0.1:'+str(self.server.server_port)+'/v1/chat/completions','installed-local-model')

    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(3)

    def test_real_http_transport_carries_ten_laws_and_only_measured_evidence(self):
        result=self.client.diagnose({'evidence':{'sha256':'a'*64},'observation':{'state':'FAULT'}})
        self.assertEqual(len(result['hypotheses']),1)
        request=self.requests[0]
        for law in CORE_LAWS:self.assertIn(law,request['messages'][0]['content'])
        self.assertFalse(request['stream']);self.assertNotIn('tools',request)

    def test_actual_http_service_recovery_runs_a_new_evidence_bound_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            now=[100]
            runtime=OperationalRuntime(Path(directory)/'state.db',clock=lambda:now[0])
            audit=GlassBoxAudit(Path(directory)/'audit.db')
            runtime.cycle({'uptime':lambda:observation('FAULT','HTTP_UNAVAILABLE')})
            self.mode='unavailable'
            diagnose_open_incidents(runtime,audit,self.client)
            self.mode='good';now[0]=160
            diagnose_open_incidents(runtime,audit,self.client)
            tasks=TechTeamDispatcher(runtime.path,CORE_LAWS,audit).list_tasks()
            self.assertEqual(len(self.requests),2)
            self.assertEqual(tasks[0]['execution']['result']['diagnostic_model_status'],'RESPONDED')
            self.assertTrue(tasks[0]['execution']['verification']['passed'])

    def test_redirects_truncation_unsupported_evidence_and_tools_are_rejected(self):
        for mode in ('redirect','truncated','wrong_evidence','extra'):
            self.mode=mode
            with self.subTest(mode=mode),self.assertRaises(InferenceUnavailable):
                self.client.diagnose({'evidence':{'sha256':'a'*64}})

    def test_no_remote_endpoint_or_embedded_credential(self):
        for endpoint in ('https://provider.example/v1/chat/completions',
            'http://127.0.0.1:8080/v1/chat/completions?redirect=1',
            'http://name:password@localhost:8080/v1/chat/completions',
            'http://127.0.0.1:8080/execute'):
            with self.assertRaises(ValueError):LocalInferenceClient(endpoint,'model')

    def test_model_assisted_task_still_has_no_repair_or_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.db';runtime=OperationalRuntime(path)
            runtime.cycle({'uptime':lambda:observation('FAULT','HTTP_UNAVAILABLE')})
            task={'evidence':{'incident_id':1}}
            result=IncidentDiagnosis(path,self.client)(task)
            self.assertTrue(result['model_inference'])
            self.assertFalse(result['execution_authorized']);self.assertFalse(result['repair_executed'])
            self.assertTrue(DiagnosticEvidenceReview(path)(task,result)['passed'])
            # This HTTP response is a fixture, not proof that a real model ran.
