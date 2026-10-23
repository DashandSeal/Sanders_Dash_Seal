"""Actual independent process observations, role isolation and negative paths."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from core_platform.ai_role_workers import (ROLES, ROLE_PROBES, SHIELD, CONDUCTOR,
    DOMAIN, protected_identity, public_keys, check_record, publish, role_snapshot,
    RoleObservationStore, measure, shield_observation)
from core_platform.security import sign, Denied
from core_platform.operational_runtime import OperationalRuntime, observation
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.rtsa_registry import RTSA_ROLES
from core_platform.rtsa_assessments import assess
from core_platform.michael_angelo import conductor_observation
from deploy.init_ai_roles import initialize


class RoleWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.config=self.root/'roles'
        # CI is unprivileged: model only OS ownership metadata/chown in the
        # administrator initializer; keys, signatures, files and child writers are real.
        original_stat=Path.stat
        def admin_stat(path,*args,**kwargs):
            values=list(original_stat(path,*args,**kwargs));values[4]=0
            return os.stat_result(values)
        for mocker in (patch('os.chown'),patch('os.fchown'),patch('os.geteuid',return_value=0),
                       patch.object(Path,'stat',admin_stat)):
            mocker.start();self.addCleanup(mocker.stop)
        initialize(self.config)
        self.registry=self.config/'public/public-keys.json'
        self.results=self.config/'public/results';self.keys=public_keys(self.registry)
        self.db=self.root/'state.db';OperationalRuntime(self.db)
        GlassBoxAudit(self.db.with_name('sds_audit.db'))

    def key(self,role):return protected_identity(self.config/'identities'/(role+'.json'),role)

    def write(self,role='UptimeAgent',clock=lambda:100,probe=lambda:observation('HEALTHY','MEASURED')):
        return publish(role,self.key(role),self.results/role,probe,clock=clock)

    def test_all_distinct_roles_and_recovered_rtsa_missions_are_preserved(self):
        self.assertEqual(len(ROLES),30);self.assertEqual(len(set(ROLES)),30)
        self.assertEqual(len(RTSA_ROLES),14);self.assertEqual(len(ROLE_PROBES),12)
        self.assertIn('HYDRA-Q',RTSA_ROLES);self.assertIn('LABYRINTH',RTSA_ROLES)
        self.assertNotEqual(self.keys[SHIELD],self.keys['MINOTAUR'])
        self.assertNotEqual(self.keys[CONDUCTOR],self.keys['IT_AI_Manager_v15.0'])
        for role in RTSA_ROLES:
            value=assess(role,{})
            self.assertEqual(value.rtsa,role);self.assertFalse(value.execution_allowed)

    def test_administrator_identity_setup_is_idempotent_and_never_silently_rotates(self):
        initialize(self.config);self.assertEqual(public_keys(self.registry),self.keys)
        other=dict(self.keys);other['MINOTAUR']=other['ARCHITECT']
        self.registry.write_text(json.dumps(other))
        with self.assertRaises(ValueError):initialize(self.config)

    def test_unprivileged_initialization_and_wrong_role_key_are_rejected(self):
        with patch('os.geteuid',return_value=10001),self.assertRaises(PermissionError):initialize(self.config)
        with self.assertRaises(ValueError):protected_identity(self.config/'identities/MINOTAUR.json',SHIELD)
        p=self.config/'identities/MINOTAUR.json';p.chmod(0o666)
        with self.assertRaises(ValueError):self.key('MINOTAUR')

    def test_signature_binds_role_laws_sequence_and_measured_state(self):
        record=self.write()
        check_record(record,'UptimeAgent',self.keys['UptimeAgent'],100)
        for field,value in [('role','MINOTAUR'),('laws_sha256','0'*64),('sequence',2),
                            ('observation',observation('FAULT','TAMPERED'))]:
            changed=deepcopy(record);changed['body'][field]=value
            with self.subTest(field=field),self.assertRaises((ValueError,Denied)):
                check_record(changed,'UptimeAgent',self.keys['UptimeAgent'],100)
        with self.assertRaises(Denied):check_record(record,'UptimeAgent',self.keys['MINOTAUR'],100)
        changed=deepcopy(record)
        changed['signature']=sign(self.key('UptimeAgent'),'pbd-lease-v2',changed['body'])
        with self.assertRaises(Denied):check_record(changed,'UptimeAgent',self.keys['UptimeAgent'],100)

    def test_stale_future_nonfinite_and_boolean_sequence_rejected(self):
        record=self.write()
        for now in (99,191):
            with self.assertRaises(ValueError):check_record(record,'UptimeAgent',self.keys['UptimeAgent'],now)
        for field,value in [('sequence',True),('observed_at',float('nan'))]:
            altered=deepcopy(record);altered['body'][field]=value
            with self.assertRaises(ValueError):check_record(altered,'UptimeAgent',self.keys['UptimeAgent'],100)

    def test_restart_preserves_sequence_and_redacts_probe_failure(self):
        self.write()
        def fail():raise RuntimeError('private customer secret')
        record=self.write(clock=lambda:101,probe=fail)
        self.assertEqual(record['body']['sequence'],2)
        self.assertEqual(record['body']['observation']['code'],'ROLE_PROBE_FAILED')
        self.assertNotIn('secret',json.dumps(record))

    def test_concurrent_writers_are_serialized(self):
        import threading
        errors=[]
        def run():
            try:self.write()
            except Exception as error:errors.append(error)
        threads=[threading.Thread(target=run) for _ in range(4)]
        for t in threads:t.start()
        for t in threads:t.join(5)
        self.assertFalse(errors)
        record=json.loads((self.results/'UptimeAgent/latest.json').read_text())
        self.assertEqual(record['body']['sequence'],4)

    def test_replay_watermark_survives_store_restart_and_identical_read_is_idempotent(self):
        now=time.time();first=self.write(clock=lambda:now)
        store=RoleObservationStore(self.db)
        store.status(self.results,self.registry)
        self.write(clock=lambda:now+0.001)
        with patch('core_platform.ai_role_workers.time.time',return_value=now+1):
            second=store.status(self.results,self.registry)
            same=RoleObservationStore(self.db).status(self.results,self.registry)
            self.assertEqual(second,same)
            (self.results/'UptimeAgent/latest.json').write_text(json.dumps(first))
            rejected=RoleObservationStore(self.db).status(self.results,self.registry)
        self.assertEqual(rejected['roles'][0]['code'],'ROLE_REPLAY_REJECTED')
        self.assertFalse(rejected['authority_granted']);self.assertFalse(rejected['model_inference_verified'])

    def test_duplicate_json_and_symlink_results_are_unverified(self):
        path=self.results/'UptimeAgent/latest.json'
        self.write();good=path.read_text();path.write_text('{"body":{},'+good[1:])
        self.assertEqual(role_snapshot(self.results,self.keys,now=100)[0]['record_status'],'NOT_VERIFIED')
        path.unlink();path.symlink_to(self.registry)
        self.assertEqual(role_snapshot(self.results,self.keys,now=100)[0]['record_status'],'NOT_VERIFIED')

    def test_separate_cli_processes_really_publish_and_retain_distinct_identities(self):
        root=Path(__file__).resolve().parents[1]
        children=[]
        for role in ('GlobalPBDSentinel',CONDUCTOR,'MINOTAUR'):
            script="""import json,sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.ai_role_workers import publish
from core_platform.operational_runtime import observation
role,keyfile,output=sys.argv[1:]
key=Ed25519PrivateKey.from_private_bytes(bytes.fromhex(json.loads(Path(keyfile).read_text())['private_key']))
publish(role,key,output,lambda:observation('HEALTHY','CHILD_PROCESS_OBSERVED'))
"""
            args=[sys.executable,'-c',script,role,
                str(self.config/'identities'/(role+'.json')),str(self.results/role)]
            children.append(subprocess.Popen(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
        self.assertEqual(len({p.pid for p in children}),3)
        for child in children:
            out,err=child.communicate(timeout=15)
            self.assertEqual(child.returncode,0,err.decode());self.assertEqual(out,b'')
        snapshot=role_snapshot(self.results,self.keys)
        for role in ('GlobalPBDSentinel',CONDUCTOR,'MINOTAUR'):
            self.assertEqual(next(v for v in snapshot if v['role']==role)['record_status'],'VERIFIED_RECENT_OBSERVATION')

    def test_shield_patrol_is_distinct_and_does_not_infer_clearance(self):
        self.write(SHIELD,clock=time.time,probe=lambda:observation('FAULT','PROCESS_BOUNDS_OBSERVED'))
        value=measure('MINOTAUR',self.db,self.root,self.results,self.keys)
        self.assertEqual(value['state'],'FAULT');self.assertEqual(value['metrics']['verified_shield'],1)
        fake=self.root/'proc-status';fake.write_text('CapEff:\t00000000\nNoNewPrivs:\t1\n')
        with patch('os.geteuid',return_value=10001):
            self.assertEqual(shield_observation(fake)['state'],'HEALTHY')
        with patch('os.geteuid',return_value=0):
            self.assertEqual(shield_observation(fake)['state'],'FAULT')

    def test_conductor_requires_fourteen_distinct_verified_rtsa_inputs(self):
        snapshots=[{'role':name,'record_status':'VERIFIED_RECENT_OBSERVATION','state':'HEALTHY'} for name in RTSA_ROLES]
        self.assertEqual(conductor_observation(snapshots)['state'],'HEALTHY')
        self.assertEqual(conductor_observation(snapshots[:-1])['state'],'UNKNOWN')
        with self.assertRaises(ValueError):conductor_observation(snapshots+[snapshots[0]])
        snapshots[0]['state']='FAULT'
        self.assertEqual(conductor_observation(snapshots)['state'],'FAULT')

    def test_deployment_has_one_bounded_service_and_one_private_key_mount_per_role(self):
        root=Path(__file__).resolve().parents[1]
        services=json.loads((root/'deploy/compose.ai.yml').read_text())['services']
        self.assertEqual(len(services),30)
        for service in services.values():
            role=service['command'][-1];self.assertIn(role,ROLES)
            self.assertEqual(service['user'],'10001:10001');self.assertTrue(service['read_only'])
            identities=[m for m in service['volumes'] if '/identities/' in m]
            self.assertEqual(len(identities),1);self.assertIn('/'+role+'.json:',identities[0])
            self.assertNotIn('/var/run/docker.sock',json.dumps(service))


if __name__=='__main__':unittest.main()
