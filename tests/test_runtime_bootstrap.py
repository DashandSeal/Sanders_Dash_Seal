"""Secret initialization and retrieval must be repeatable and fail without leakage."""
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from deploy.init_runtime import initialize
from deploy.refresh_provider_secrets import retrieve,refresh,NAME


class RuntimeBootstrapTests(unittest.TestCase):
    def test_owner_secret_is_private_repeatable_and_partial_creation_recovers(self):
        if os.geteuid()!=0:self.skipTest('Host ownership test requires root')
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/'runtime';ownership=[]
            chown=lambda *args:ownership.append(args)
            initialize(folder,clock=lambda:1000,chown=chown)
            self.assertTrue(all(args[1:]==(0,10001) for args in ownership))
            original=(folder/'runtime.json').read_text();owner=folder.parent/'owner-setup.txt'
            self.assertEqual(owner.stat().st_mode & 0o777,0o600)
            self.assertEqual((folder/'runtime.json').stat().st_mode & 0o777,0o640)
            self.assertNotIn('Single-use',original)
            initialize(folder,clock=lambda:2000,chown=chown)
            self.assertEqual(original,(folder/'runtime.json').read_text())
            (folder/'runtime.json').unlink()
            initialize(folder,clock=lambda:3000,chown=chown)
            self.assertEqual(original,(folder/'runtime.json').read_text())

    def test_only_designated_current_vault_secret_is_loaded(self):
        calls=[];payload={'stripe_livemode':False,'stripe_webhook_secret':'whsec_'+'synthetic-test'}
        def api(args):
            calls.append(args)
            if args[:3]==['vault','secret','list']:
                return {'data':[{'secret-name':'unrelated','id':'wrong','lifecycle-state':'ACTIVE'},
                    {'secret-name':NAME,'id':'selected','lifecycle-state':'ACTIVE'}]}
            self.assertIn('selected',args);self.assertIn('CURRENT',args)
            return {'data':{'secret-bundle-content':{'content-type':'BASE64',
                'content':base64.b64encode(json.dumps(payload).encode()).decode()}}}
        self.assertEqual(retrieve('compartment',api),payload)
        self.assertEqual(len(calls),2)
        self.assertIsNone(retrieve('compartment',lambda args:{'data':[]}))

    def test_ambiguous_and_arbitrary_secret_configuration_is_denied(self):
        duplicate=[{'secret-name':NAME,'id':'one','lifecycle-state':'ACTIVE'}]*2
        with self.assertRaises(ValueError):retrieve('comp',lambda args:{'data':duplicate})
        def api(args):
            if args[0]=='vault':return {'data':duplicate[:1]}
            return {'data':{'secret-bundle-content':{'content-type':'BASE64',
                'content':base64.b64encode(b'{"owner_setup_digest":"override"}').decode()}}}
        with self.assertRaises(ValueError):retrieve('comp',api)
