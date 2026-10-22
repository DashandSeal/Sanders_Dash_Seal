"""Deployment authentication and actual upload/activation failure propagation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from deploy.gitops_deploy import credentials, release


class GitOpsTests(unittest.TestCase):
    def environment(self):
        return dict(OCI_TENANCY_OCID='ocid1.tenancy.oc1..test',
            OCI_USER_OCID='ocid1.user.oc1..test', OCI_FINGERPRINT=':'.join(['ab']*16),
            OCI_PRIVATE_KEY='-----BEGIN PRIVATE KEY-----\nTEST-ONLY\n-----END PRIVATE KEY-----',
            OCI_REGION='us-phoenix-1')

    def archive(self, folder):
        path=Path(folder)/'release.zip'
        variables='variable "create_instance" {\n type = bool\n default = false\n}\n'
        manifest={'source_commit':'a'*40,'files':{'variables.tf':hashlib.sha256(variables.encode()).hexdigest()}}
        with zipfile.ZipFile(path,'w') as output:
            output.writestr('variables.tf',variables)
            output.writestr('package_manifest.json',json.dumps(manifest))
        return path

    def test_credentials_are_private_temporary_and_removed_even_on_failure(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):
                with credentials(self.environment()) as config:
                    private=config.parent/'signing.pem'
                    self.assertEqual(config.stat().st_mode & 0o777,0o600)
                    self.assertEqual(private.stat().st_mode & 0o777,0o600)
                    self.assertEqual(os.environ['OCI_CLI_AUTH'],'api_key')
                    raise RuntimeError('simulated runner failure')
            self.assertFalse(config.exists())
            self.assertFalse(private.exists())
            self.assertNotIn('OCI_CLI_CONFIG_FILE',os.environ)

    def test_missing_or_malformed_credentials_fail_without_printing_key(self):
        for bad in [{},dict(self.environment(),OCI_FINGERPRINT='invalid'),
                    dict(self.environment(),OCI_USER_OCID='username'),
                    dict(self.environment(),OCI_REGION='us-ashburn-1')]:
            with self.assertRaises(ValueError):
                with credentials(bad):pass

    def test_upload_uses_real_cli_flag_then_waiting_activation(self):
        calls=[]
        def api(args,**kwargs):
            calls.append(args)
            if 'get-stack-tf-state' in args:return json.dumps({'resources':[]})
            return {'data':{'variables':{}}}
        def activation(identifier,**kwargs):
            self.assertIn('update',calls[-1])
            return {'commit':'a'*40,'status':'AGENT_INSTALL_AND_BACKUP_VERIFIED'}
        with tempfile.TemporaryDirectory() as folder:
            result=release(self.archive(folder),'a'*40,'ocid1.ormstack.oc1.phx.test',api=api,activation=activation)
        self.assertEqual(result['status'],'AGENT_INSTALL_AND_BACKUP_VERIFIED')
        self.assertIn('--config-source',calls[-1])
        self.assertNotIn('--config-source-zip-file',calls[-1])

    def test_failed_install_does_not_report_success(self):
        def api(args,**kwargs):
            if 'get-stack-tf-state' in args:return '{}'
            return {'data':{'variables':{}}}
        def fail(*args,**kwargs):raise RuntimeError('Oracle installation failed')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                release(self.archive(folder),'a'*40,'ocid1.ormstack.oc1.phx.test',api=api,activation=fail)

    def test_different_release_and_existing_new_vm_do_not_mutate_stack(self):
        calls=[]
        def api(args,**kwargs):
            calls.append(args)
            if 'get-stack-tf-state' in args:
                return json.dumps({'resources':[{'mode':'managed','type':'oci_core_instance'}]})
            return {'data':{'variables':{}}}
        with tempfile.TemporaryDirectory() as folder:
            path=self.archive(folder)
            with self.assertRaises(ValueError):release(path,'b'*40,'ocid1.ormstack.oc1.phx.test',api=api)
            with self.assertRaises(ValueError):release(path,'a'*40,'ocid1.ormstack.oc1.phx.test',api=api)
        self.assertFalse(any('update' in call for call in calls))
