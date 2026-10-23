"""Identity mapping denial paths and mocked read-only OCI responses."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from deploy.oci_preflight import validate, load_env, verify_resources


class OCIPreflightTests(unittest.TestCase):
    def setUp(self):
        suffix = 'a' * 60
        self.config = {
            'OCI_REGION': 'us-phoenix-1', 'OCI_TENANCY_OCID': 'ocid1.tenancy.oc1..' + suffix,
            'OCI_COMPARTMENT_OCID': 'ocid1.tenancy.oc1..' + suffix,
            'OCI_STREAM_POOL_OCID': 'ocid1.streampool.oc1.phx.' + suffix,
            'OCI_STREAM_OCID': 'ocid1.stream.oc1.phx.' + suffix,
            'OCI_FUNCTION_OCID': 'ocid1.fnfunc.oc1.phx.' + suffix,
            'OCI_STREAM_ENDPOINT': 'https://cell-1.streaming.us-phoenix-1.oci.oraclecloud.com',
            'OCI_STREAM_TOPIC_NAME': 'sds-production-pipeline',
            'OCI_OBJECT_STORAGE_NAMESPACE': 'fixture_namespace', 'OCI_BACKUP_BUCKET': 'sds-ledger-backups'}
        c = self.config
        self.responses = {
            ('iam', 'tenancy', 'get'): {'id': c['OCI_TENANCY_OCID']},
            ('streaming', 'admin', 'stream-pool'): {'id': c['OCI_STREAM_POOL_OCID'],
                'compartment-id': c['OCI_COMPARTMENT_OCID'], 'lifecycle-state': 'ACTIVE'},
            ('streaming', 'admin', 'stream'): {'id': c['OCI_STREAM_OCID'],
                'compartment-id': c['OCI_COMPARTMENT_OCID'], 'lifecycle-state': 'ACTIVE',
                'stream-pool-id': c['OCI_STREAM_POOL_OCID'], 'name': c['OCI_STREAM_TOPIC_NAME'],
                'messages-endpoint': c['OCI_STREAM_ENDPOINT']},
            ('fn', 'function', 'get'): {'id': c['OCI_FUNCTION_OCID'],
                'compartment-id': c['OCI_COMPARTMENT_OCID'], 'lifecycle-state': 'ACTIVE'},
            ('os', 'ns', 'get'): c['OCI_OBJECT_STORAGE_NAMESPACE'],
            ('os', 'bucket', 'get'): {'name': c['OCI_BACKUP_BUCKET'],
                'namespace': c['OCI_OBJECT_STORAGE_NAMESPACE'], 'compartment-id': c['OCI_COMPARTMENT_OCID'],
                'public-access-type': 'NoPublicAccess', 'storage-tier': 'Standard'}}
        self.commands = []

    def runner(self, command, **kwargs):
        self.commands.append(command)
        self.assertIn('get', command)
        self.assertFalse(set(command) & {'create', 'update', 'delete', 'put'})
        self.assertIn('instance_principal', command)
        data = self.responses[tuple(command[1:4])]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({'data': data}))

    def test_read_only_identity_success_does_not_claim_live_readiness(self):
        result = verify_resources(self.config, runner=self.runner)
        self.assertEqual(result['status'], 'RESOURCE_IDENTITIES_VERIFIED')
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['routing_verified'])
        self.assertEqual(len(self.commands), 6)

    def test_supplied_friendly_ocids_and_malformed_endpoint_are_rejected(self):
        cases = [('OCI_TENANCY_OCID', 'ocid1.tenancy.oc1..aaaaaaaarooseveltsandersroot'),
                 ('OCI_STREAM_POOL_OCID', 'ocid1.streampool.oc1.phx.sds-pool-nearzero'),
                 ('OCI_STREAM_ENDPOINT', '://oraclecloud.com'),
                 ('OCI_STREAM_ENDPOINT', 'http://cell-1.streaming.us-phoenix-1.oci.oraclecloud.com')]
        for key, value in cases:
            with self.assertRaises(ValueError):
                verify_resources(dict(self.config, **{key: value}), runner=self.runner)
        self.assertEqual(self.commands, [])

    def test_missing_actual_stream_or_function_ids_prevent_queries(self):
        for key in ('OCI_STREAM_OCID', 'OCI_FUNCTION_OCID'):
            config = dict(self.config)
            del config[key]
            with self.assertRaises(ValueError):
                verify_resources(config, runner=self.runner)
        self.assertEqual(self.commands, [])

    def test_resource_endpoint_pool_and_state_mismatch_fail(self):
        stream = self.responses[('streaming', 'admin', 'stream')]
        for key, value in [('messages-endpoint', 'https://other.example'),
                           ('stream-pool-id', 'different'), ('lifecycle-state', 'CREATING')]:
            original = stream[key]
            stream[key] = value
            with self.assertRaises(ValueError):
                verify_resources(self.config, runner=self.runner)
            stream[key] = original

    def test_namespace_or_public_bucket_mismatch_fails(self):
        bucket = self.responses[('os', 'bucket', 'get')]
        bucket['public-access-type'] = 'ObjectRead'
        with self.assertRaises(ValueError):
            verify_resources(self.config, runner=self.runner)
        bucket['public-access-type'] = 'NoPublicAccess'
        self.responses[('os', 'ns', 'get')] = 'wrong_namespace'
        with self.assertRaises(ValueError):
            verify_resources(self.config, runner=self.runner)

    def test_iam_denial_is_not_relabelled_as_verified(self):
        def denied(command, **kwargs):
            raise subprocess.CalledProcessError(1, command)
        with self.assertRaises(subprocess.CalledProcessError):
            verify_resources(self.config, runner=denied)

    def test_child_compartment_ancestry_is_verified(self):
        child = 'ocid1.compartment.oc1..' + 'b' * 60
        self.config['OCI_COMPARTMENT_OCID'] = child
        self.responses[('iam', 'compartment', 'get')] = {'id': child,
            'compartment-id': self.config['OCI_TENANCY_OCID'], 'lifecycle-state': 'ACTIVE'}
        for item in self.responses.values():
            if isinstance(item, dict) and 'compartment-id' in item and item.get('id') != child:
                item['compartment-id'] = child
        self.assertEqual(verify_resources(self.config, runner=self.runner)['status'],
                         'RESOURCE_IDENTITIES_VERIFIED')

    def test_compartment_parent_cycle_is_rejected(self):
        child = 'ocid1.compartment.oc1..' + 'b' * 60
        self.config['OCI_COMPARTMENT_OCID'] = child
        self.responses[('iam', 'compartment', 'get')] = {'id': child,
            'compartment-id': child, 'lifecycle-state': 'ACTIVE'}
        with self.assertRaises(ValueError):
            verify_resources(self.config, runner=self.runner)

    def test_private_env_file_is_data_and_never_evaluated(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / '.env.secrets'
            path.write_text('\n'.join(key + '=' + value for key, value in self.config.items()) + '\n')
            path.chmod(0o600)
            self.assertEqual(load_env(path), self.config)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                load_env(path)
            path.chmod(0o600)
            path.write_text(path.read_text() + 'OCI_REGION=$(touch bad-file)\n')
            with self.assertRaises(ValueError):
                load_env(path)
            self.assertFalse((Path(temporary) / 'bad-file').exists())
