"""Automatic Oracle execution contracts, without contacting or mutating a tenancy."""
import json
from pathlib import Path
import subprocess
import unittest
from deploy.activate_on_oracle import validate_plan, wait_command, wait_job
from deploy.bind_free_resources import validate, verify, metric
from scripts.package_resource_manager import contents

ROOT=Path(__file__).resolve().parents[1]


def binding():
    return dict(schema=1, instance_id='ocid1.instance.oc1.phx.test',
        compartment_id='ocid1.tenancy.oc1..test',namespace='testnamespace',region='us-phoenix-1',
        bucket='sds-ledger-backups-test',topic_id='ocid1.onstopic.oc1.phx.test',metric_namespace='sds_platform',
        budget_bytes=20000000000,max_snapshot_bytes=1000000000)


class OracleActivationTests(unittest.TestCase):
    def test_plan_rejects_paid_compute_deletion_and_bucket_exposure(self):
        def plan(kind,name,actions,after=None):
            return {'resource_changes':[{'type':kind,'name':name,'address':kind+'.'+name,
                'change':{'actions':actions,'after':after or {}}}]}
        self.assertTrue(validate_plan(plan('oci_monitoring_alarm','platform',['create'])))
        for bad in [plan('oci_core_instance','sds_automated',['create']),
                    plan('oci_objectstorage_bucket','ledger',['delete','create']),
                    plan('oci_objectstorage_bucket','ledger',['create'],{'access_type':'ObjectRead','storage_tier':'Standard'}),
                    plan('oci_functions_function','unrequested',['create'])]:
            with self.assertRaises(ValueError): validate_plan(bad)
        with self.assertRaises(ValueError): validate_plan({})

    def test_execution_success_requires_zero_exit_code(self):
        def api(record): return lambda args: {'data':record}
        good={'lifecycle-state':'SUCCEEDED','exit-code':0}
        self.assertEqual(wait_command('command','instance',api(good)),good)
        for record in [{'lifecycle-state':'SUCCEEDED'}, {'lifecycle-state':'SUCCEEDED','exit-code':1},
                       {'lifecycle-state':'FAILED','exit-code':1}, {'lifecycle-state':'TIMED_OUT'}]:
            with self.assertRaises(ValueError): wait_command('command','instance',api(record))
        with self.assertRaises(ValueError): wait_job('job',api({'lifecycle-state':'FAILED'}))

    def test_pending_execution_has_bounded_deadline(self):
        now=[0]
        def pause(amount): now[0]+=amount
        with self.assertRaises(TimeoutError):
            wait_command('c','i',lambda args:{'data':{'lifecycle-state':'ACCEPTED'}},
                clock=lambda:now[0],pause=pause,timeout=1)

    def test_resource_verification_does_not_trust_config_or_public_bucket(self):
        cfg=binding()
        def api(args):
            if args[:3]==['os','bucket','get']:
                return {'data':{'public-access-type':'NoPublicAccess','storage-tier':'Standard',
                                'compartment-id':cfg['compartment_id']}}
            return {'data':{'lifecycle-state':'ACTIVE','compartment-id':cfg['compartment_id']}}
        self.assertTrue(verify(cfg,api)['private_backup_bucket_verified'])
        with self.assertRaises(ValueError):
            verify(cfg,lambda args:{'data':{'public-access-type':'ObjectRead'}})
        for key,value in [('metric_namespace','arbitrary'),('region','us-ashburn-1'),('budget_bytes',True)]:
            bad=dict(cfg);bad[key]=value
            with self.assertRaises(ValueError):validate(bad)

    def test_metrics_include_identity_but_no_transaction_payload(self):
        calls=[]
        metric(binding(),'PlatformHeartbeat',1,lambda args:calls.append(args))
        data=json.loads(calls[0][calls[0].index('--metric-data')+1])[0]
        self.assertEqual(data['namespace'],'sds_platform')
        self.assertEqual(set(data['dimensions']),{'resourceId'})
        self.assertNotIn('transaction',json.dumps(data))

    def test_generated_existing_installer_is_executable_bash_without_literal_escapes(self):
        files=contents('a'*40,source_names=['docker-compose.yml','backend/platform-source.json',
            'worker/package-lock.json','deploy/install_application.sh','scripts/verify_release_source.py'])
        text=files['install-existing.sh.tftpl'].replace('${release_config_base64}','e30=')
        result=subprocess.run(['bash','-n'],input=text,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('exec sudo -n /bin/bash "$0"',text)
        self.assertIn('activate_on_oracle.py',files)
        self.assertIn('free-platform.tf',files)
        self.assertNotIn('https://github.com .',text)



class ActivationFlowTests(unittest.TestCase):
    def test_exact_plan_applied_before_agent_dispatch(self):
        from deploy.activate_on_oracle import deploy
        calls=[]
        def api(args,raw=False):
            calls.append(args)
            if args[:3]==['resource-manager','stack','get']: return {'data':{'variables':{}}}
            if 'create-plan-job' in args:return {'data':{'id':'plan'}}
            if 'get-job-tf-plan' in args:return json.dumps({'resource_changes':[]})
            if 'create-apply-job' in args:
                self.assertEqual(args[args.index('--execution-plan-job-id')+1],'plan')
                return {'data':{'id':'apply'}}
            if 'get-job-tf-state' in args:return json.dumps({'outputs':{'existing_install_command':{'value':{
                'instance_id':'instance','compartment_id':'compartment','namespace':'ns','bucket':'release',
                'object':'installer','commit':'a'*40}}}})
            if args[:3]==['resource-manager','job','get']:return {'data':{'lifecycle-state':'SUCCEEDED'}}
            if args[:3]==['instance-agent','command','create']:return {'data':{'id':'command'}}
            if 'command-execution' in args:return {'data':{'lifecycle-state':'SUCCEEDED','exit-code':0}}
            raise AssertionError(args)
        result=deploy('ocid1.ormstack.oc1.phx.test',api)
        self.assertEqual(result['status'],'AGENT_INSTALL_AND_BACKUP_VERIFIED')
        self.assertFalse(result['billing_verified'])
        self.assertLess(next(i for i,a in enumerate(calls) if 'create-apply-job' in a),
                        next(i for i,a in enumerate(calls) if a[:3]==['instance-agent','command','create']))

    def test_rejected_plan_never_applies_or_dispatches(self):
        from deploy.activate_on_oracle import deploy
        calls=[]
        def api(args,raw=False):
            calls.append(args)
            if 'stack' in args:return {'data':{'variables':{}}}
            if 'create-plan-job' in args:return {'data':{'id':'plan'}}
            if 'get-job-tf-plan' in args:return json.dumps({'resource_changes':[{
                'type':'oci_core_instance','name':'paid','address':'paid',
                'change':{'actions':['create'],'after':{}}}]})
            return {'data':{'lifecycle-state':'SUCCEEDED'}}
        with self.assertRaises(ValueError):deploy('ocid1.ormstack.oc1.phx.test',api)
        self.assertFalse(any('create-apply-job' in args or 'instance-agent' in args for args in calls))


class DirectProfileTests(unittest.TestCase):
    def test_direct_package_uses_a1_and_bundled_source_not_placeholder_clone(self):
        files=contents('a'*40,source_names=['docker-compose.yml','backend/platform-source.json',
            'worker/package-lock.json','deploy/install_application.sh','scripts/verify_release_source.py'],direct=True)
        self.assertIn('variable "create_instance" {\n  type = bool\n  default = true',files['variables.tf'])
        self.assertIn('variable "deploy_existing_instance" {\n  type = bool\n  default = false',files['variables.tf'])
        self.assertIn('VM.Standard.A1.Flex',files['main.tf'])
        self.assertNotIn('VM.Standard.E4.Flex',files['main.tf'])
        self.assertIn('selected_compartment = var.compartment_ocid',files['main.tf'])
        self.assertIn('data.oci_core_vnic.existing_target[0].subnet_id',files['main.tf'])
        self.assertNotIn('git clone',files['cloud-init-application.yaml.tftpl'])
        self.assertIn('application.tgz',files)


if __name__=='__main__':unittest.main()
