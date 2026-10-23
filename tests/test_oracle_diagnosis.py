import json
import unittest
from deploy.diagnose_oracle import diagnose,safe_lines


class OracleDiagnosisTests(unittest.TestCase):
    def test_reads_only_selected_host_and_redacts_output(self):
        calls=[]
        def api(args,raw=False):
            calls.append(args)
            if 'get-stack-tf-state' in args:return json.dumps({'outputs':{'application_install_command':{'value':{
                'compartment_id':'compartment','instance_id':'selected-instance'}}}})
            if 'list' in args:return {'data':[{'instance-agent-command-id':'command-one'}]}
            return {'data':{'lifecycle-state':'FAILED','content':{'exit-code':1,'text':
                'APPLICATION_INSTALL_FAILED exit=1\npassword=not-for-logs\nPackage not found\nhttps://host/private?token=hidden'}}}
        result=diagnose('ocid1.ormstack.oc1.phx.actual',api)
        self.assertFalse(result['cloud_changes_performed'])
        self.assertEqual(result['executions'][0]['exit_code'],1)
        self.assertIn('Package not found',result['executions'][0]['output'])
        self.assertNotIn('password',json.dumps(result));self.assertNotIn('token=',json.dumps(result))
        self.assertTrue(all(any(action in args for action in ('get-stack-tf-state','get','list')) for args in calls))
        for args in calls[1:]:self.assertEqual(args[args.index('--instance-id')+1],'selected-instance')

    def test_private_blocks_and_urls_are_not_published(self):
        result=safe_lines('before\n-----BEGIN PRIVATE KEY-----\nabcdefg\n-----END PRIVATE KEY-----\nafter\nDownload failed https://private/path?signature=hidden')
        self.assertNotIn('abcdefg',str(result));self.assertNotIn('signature=',str(result))
        self.assertIn('Download failed [URL]',result)

    def test_optional_host_probe_executes_only_fixed_os_queries(self):
        calls=[]
        def api(args,raw=False):
            calls.append(args)
            if 'get-stack-tf-state' in args:return json.dumps({'outputs':{'application_install_command':{'value':{
                'compartment_id':'compartment','instance_id':'selected-instance'}}}})
            if 'list' in args:return {'data':[]}
            if 'create' in args:
                content=json.loads(args[args.index('--content')+1])
                script=content['source']['text']
                self.assertIn('id -un',script);self.assertIn('sudo -n -l /bin/bash',script)
                for mutation in ('dnf install','chmod','chown','systemctl','rm -','curl'):
                    self.assertNotIn(mutation,script)
                return {'data':{'id':'inspection-command'}}
            return {'data':{'lifecycle-state':'SUCCEEDED','content':{'exit-code':0,'text':'SDS_HOST_CHECK_END'}}}
        result=diagnose('ocid1.ormstack.oc1.phx.actual',api,probe_host=True)
        self.assertFalse(result['infrastructure_changes_performed'])
        self.assertEqual(result['host_probe']['output'],['SDS_HOST_CHECK_END'])
