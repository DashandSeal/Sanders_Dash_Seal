"""Actual durable cycles and HTTP probes; no model or authority is impersonated."""
from contextlib import contextmanager
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import subprocess
import sys
import unittest

from core_platform.operational_runtime import (OperationalRuntime, AGENTS,
    ObservationError, observation, validated)
from core_platform.operational_probes import http_probe, database_probe, configured_probes
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.native_runtime import NativeRuntime
from core_platform.upgrade_sidecar import CORE_LAWS
from core_platform.accounts import digest, COOKIE


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'state.db'
        self.runtime = OperationalRuntime(self.path)

    def test_all_roles_and_ten_laws_are_available_without_models(self):
        self.assertEqual(len(CORE_LAWS), 10)
        self.assertEqual(CORE_LAWS[9], 'Sanders Dash & Seal shall always use only Oracle Always Free resources.')
        self.runtime.cycle({})
        value = self.runtime.status()
        self.assertEqual(len(value['agents']), 12)
        self.assertEqual(len({a['agent'] for a in value['agents']}), 12)
        self.assertTrue(all(a['state']=='UNKNOWN' for a in value['agents']))
        self.assertEqual(value['model_inference'], 'NOT_CONNECTED')
        self.assertEqual(value['autonomous_repair'], 'NOT_CONNECTED')

    def test_fault_unknown_and_verified_observed_recovery_survive_restart(self):
        self.runtime.cycle({'database': lambda: observation('FAULT','DATABASE_UNAVAILABLE')})
        self.runtime.cycle({'database': lambda: observation('FAULT','DATABASE_UNAVAILABLE')})
        self.runtime.cycle({})
        again = OperationalRuntime(self.path)
        self.assertEqual(len(again.status()['incidents']), 1)
        self.assertEqual(again.status()['incidents'][0]['state'], 'OPEN')
        again.cycle({'database': lambda: database_probe(self.path)})
        result = OperationalRuntime(self.path).status()
        self.assertEqual(result['observed_recoveries'], 1)
        self.assertEqual(result['incidents'][0]['state'], 'OBSERVED_RECOVERY')
        self.assertEqual(result['incidents'][0]['closed_cycle'], 4)

    def test_probe_exception_is_redacted_and_does_not_stop_other_roles(self):
        def fail(): raise RuntimeError('secret credential customer payload')
        self.runtime.cycle({'uptime': fail, 'database': lambda: database_probe(self.path)})
        value = self.runtime.status()
        self.assertEqual(value['agents'][0]['code'], 'OBSERVER_FAILED')
        self.assertEqual(value['agents'][2]['state'], 'HEALTHY')
        self.assertNotIn('secret',json.dumps(value))

    def test_untrusted_or_nonfinite_telemetry_is_not_stored(self):
        for bad in [float('nan'), float('inf'), -1, True, 'credential']:
            with self.subTest(value=bad), self.assertRaises(ObservationError):
                observation('HEALTHY','CHECKED', metric=bad)
        self.runtime.cycle({'uptime': lambda: {'state':'HEALTHY','code':'OK','metrics':{},'secret':'value'}})
        self.assertEqual(self.runtime.status()['agents'][0]['code'], 'OBSERVER_FAILED')
        with self.assertRaises(ObservationError): self.runtime.cycle({'unregistered': lambda: None})

    def test_concurrent_old_cycle_cannot_overwrite_newer_fault(self):
        started, finish = threading.Event(), threading.Event()
        errors=[]; results=[]
        def slow():
            started.set()
            if not finish.wait(5):raise RuntimeError('test timeout')
            return observation('HEALTHY','LATE_RESPONSE')
        def run():
            try:results.append(self.runtime.cycle({'uptime':slow}))
            except Exception as error: errors.append(error)
        thread=threading.Thread(target=run);thread.start()
        try:
            self.assertTrue(started.wait(5))
            self.runtime.cycle({'uptime':lambda:observation('FAULT','CURRENT_FAULT')})
        finally:finish.set();thread.join(5)
        self.assertFalse(errors)
        self.assertEqual(results[0]['state'],'SUPERSEDED')
        value=self.runtime.status()
        self.assertEqual(value['agents'][0]['code'],'CURRENT_FAULT')
        self.assertEqual(value['incidents'][0]['state'],'OPEN')

    def test_local_probes_actually_read_database_and_detect_source_tampering(self):
        from core_platform.operational_probes import source_probe
        import hashlib
        root=Path(self.temp.name)/'source';folder=root/'core_platform';folder.mkdir(parents=True)
        path=folder/'example.py';path.write_text('value = 1\n')
        Path(str(path)+'.pbd.json').write_text(json.dumps({'body':{'artifact':'core_platform/example.py',
            'payload_hash':hashlib.sha256(path.read_bytes()).hexdigest()}}))
        self.assertEqual(source_probe(root)['state'],'HEALTHY')
        path.write_text('value = 2\n')
        self.assertEqual(source_probe(root)['state'],'FAULT')
        absent=Path(self.temp.name)/'missing.db'
        self.assertEqual(database_probe(absent)['state'],'FAULT')
        self.assertFalse(absent.exists())

    def test_backup_observation_comes_from_verified_host_metadata(self):
        from deploy.bind_free_resources import backup_observation
        from core_platform.operational_probes import backup_probe
        path=Path(self.temp.name)/'backup-status.json'
        self.assertEqual(backup_probe(path)['state'],'UNKNOWN')
        backup_observation(path,clock=lambda:100,chown=lambda *args:None)
        self.assertEqual(path.stat().st_mode & 0o777,0o640)
        sample=backup_probe(path,clock=lambda:110)
        self.assertEqual(sample['code'],'BACKUP_RESTORE_OBSERVED')
        self.assertEqual(sample['metrics']['age_seconds'],10)
        self.assertEqual(backup_probe(path,clock=lambda:99)['state'],'UNKNOWN')
        value=json.loads(path.read_text());value['verified_at']=float('nan')
        path.write_text(json.dumps(value))
        self.assertEqual(backup_probe(path)['state'],'UNKNOWN')

    def test_actual_twelve_probe_cycle_and_audit_storage_are_separate(self):
        app=NativeRuntime(self.path)
        probes=configured_probes(self.path,app.audit,backup_status=Path(self.temp.name)/'missing.json')
        self.assertEqual(set(probes),{key for _,key in AGENTS})
        self.runtime.cycle(probes)
        status=self.runtime.status()
        self.assertEqual(next(a for a in status['agents'] if a['agent']=='ConfigurationAgent')['code'],'TEN_LAWS_MATCH')
        self.assertNotEqual(app.audit.path,self.runtime.path)
        app.audit.verify_audit()

    def test_operator_status_is_authenticated_read_only_and_not_a_startup_gate(self):
        import time
        setup='a'*43
        app=NativeRuntime(self.path,{'owner_setup_digest':digest(setup),'owner_setup_expires':time.time()+300})
        def request(path,token=None,method='GET',host='sandersdashandseal.com'):
            env={'HTTP_HOST':host,'PATH_INFO':path,'REQUEST_METHOD':method,'wsgi.input':io.BytesIO(b'')}
            if token:env['HTTP_COOKIE']=COOKIE+'='+token
            result={}
            def start(status,headers):result['status']=status
            result['body']=json.loads(b''.join(app(env,start)))
            return result
        path='/api/operator/ai/status'
        self.assertEqual(request(path)['status'],'401 Unauthorized')
        app.accounts.register('ordinary-user','ordinary test password phrase')
        token=app.accounts.login('ordinary-user','ordinary test password phrase')
        self.assertEqual(request(path,token)['status'],'403 Forbidden')
        app.accounts.register('owner-user','owner test password phrase',setup_token=setup)
        token=app.accounts.login('owner-user','owner test password phrase')
        response=request(path,token)
        self.assertEqual(response['status'],'200 OK')
        self.assertEqual(response['body']['model_inference'],'NOT_CONNECTED')
        self.assertEqual(request(path,token,'POST')['status'],'405 Method Not Allowed')
        self.assertEqual(request(path,token,host='wrong.example')['status'],'421 Misdirected Request')
        self.assertEqual(request('/readyz')['status'],'200 OK')
        roles='/api/operator/ai/roles'
        self.assertEqual(request(roles)['status'],'401 Unauthorized')
        self.assertEqual(request(roles,token,'POST')['status'],'405 Method Not Allowed')
        observed=request(roles,token)['body']
        self.assertEqual(len(observed['roles']),30)
        self.assertFalse(observed['authority_granted'])
        self.assertTrue(all(r['state']=='UNKNOWN' for r in observed['roles']))
        tasks='/api/operator/ai/tasks'
        self.assertEqual(request(tasks)['status'],'401 Unauthorized')
        self.assertEqual(request(tasks,token)['body'],{'tasks':[]})
        self.assertEqual(request(tasks,token,'POST')['status'],'405 Method Not Allowed')


class HttpProbeTests(unittest.TestCase):
    def test_real_http_success_failure_invalid_json_and_redirect(self):
        class Handler(BaseHTTPRequestHandler):
            mode='healthy'
            def do_GET(self):
                if self.mode=='redirect':
                    self.send_response(302);self.send_header('Location','http://external.invalid');self.end_headers();return
                self.send_response(503 if self.mode=='fault' else 200);self.end_headers()
                self.wfile.write(b'not-json' if self.mode=='invalid' else b'{"process_alive":true}')
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url='http://127.0.0.1:'+str(server.server_port)+'/healthz'
            self.assertEqual(http_probe(url)['state'],'HEALTHY')
            Handler.mode='fault';self.assertEqual(http_probe(url)['state'],'FAULT')
            Handler.mode='invalid';self.assertEqual(http_probe(url)['state'],'FAULT')
            Handler.mode='redirect';self.assertEqual(http_probe(url)['metrics']['http_status'],302)
        finally:server.shutdown();server.server_close();thread.join(3)


class WorkerProcessTests(unittest.TestCase):
    def test_real_worker_records_http_outage_and_recovery(self):
        # Use real subprocesses, SQLite and local HTTP. No Oracle or provider calls.
        from unittest.mock import patch
        import time
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sds_production.db'
            NativeRuntime(path)
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200);self.end_headers()
                    self.wfile.write(b'{"process_alive":true,"service_ready":true}')
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            root=Path(__file__).resolve().parents[1]
            # The production URLs remain fixed; a trusted test shim substitutes
            # only this ephemeral local HTTP port inside the child process.
            code='''import sys
from pathlib import Path
from core_platform import operational_probes as probes
from core_platform import operational_worker as worker
original=probes.http_probe
port=sys.argv.pop(1)
probes.http_probe=lambda url: original(url.replace(':8000/',':'+port+'/'))
worker.main()
'''
            command=[sys.executable,'-c',code,str(server.server_port),'--database',str(path)]
            try:
                first=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=20)
                self.assertEqual(first.returncode,0,first.stderr)
                self.assertEqual(json.loads(first.stdout)['state'],'COMPLETED')
                observed=OperationalRuntime(path).status()
                self.assertEqual(observed['agents'][0]['state'],'HEALTHY')
                server.shutdown();thread.join(3)
                # Closing the listening socket produces a real refused connection.
                old_port=server.server_port;server.server_close()
                failure=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=20)
                self.assertEqual(failure.returncode,0,failure.stderr)
                self.assertEqual(OperationalRuntime(path).status()['agents'][0]['state'],'FAULT')
                server=ThreadingHTTPServer(('127.0.0.1',old_port),Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                recovered=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=20)
                self.assertEqual(recovered.returncode,0,recovered.stderr)
                status=OperationalRuntime(path).status()
                self.assertGreaterEqual(status['observed_recoveries'],3)
                self.assertEqual(status['agents'][0]['state'],'HEALTHY')
                GlassBoxAudit(path.with_name('sds_audit.db')).verify_audit()
            finally:
                server.shutdown();server.server_close();thread.join(3)
