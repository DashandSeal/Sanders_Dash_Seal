"""Credential handoff ordering, confidentiality, concurrency and failure behavior."""
import base64
import json
from pathlib import Path
import tempfile
import unittest

from deploy.publish_provider_secrets import environment_values, publish
from deploy.refresh_provider_secrets import NAME


class ProviderTransferTests(unittest.TestCase):
    def test_environment_names_map_exactly_and_conflicts_are_not_silently_chosen(self):
        values = environment_values({'STRIPE_SECRET_KEY': 'sk_'+'live_'+'synthetic-only',
            'STRIPE_WEBHOOK_SECRET': 'whsec_synthetic-only', 'SIGNWELL_API_KEY': 'synthetic-signwell',
            'BLUENOTARY_API_KEY': 'synthetic-bluenotary', 'SIGNWELL_TEST_MODE': 'true'})
        self.assertEqual(set(values), {'stripe_api_key', 'stripe_webhook_secret', 'signwell_api_key',
                                     'bluenotary_api_key', 'signwell_test_mode'})
        with self.assertRaises(ValueError): environment_values({'STRIPE_SECRET_KEY': 'a', 'STRIPE_API_KEY': 'b'})
        with self.assertRaises(ValueError): environment_values({'STRIPE_LIVEMODE': 'yes'})
        self.assertEqual(environment_values({'SDS_SYSTEM_SECRET_KEY': 'not-an-independent-AI-service'}), {})

    def test_transfer_is_private_merges_checks_current_cleans_up_and_avoids_new_version_when_unchanged(self):
        current = {'stripe_livemode': True, 'stripe_webhook_secret': 'whsec_synthetic-only'}
        calls = []; files = []
        def api(args):
            calls.append(args)
            if args[:3] == ['vault','secret','list']:
                return {'data': [{'secret-name': NAME, 'id': 'selected', 'lifecycle-state': 'ACTIVE'}]}
            if args[:3] == ['vault','secret','get']: return {'data': {}, 'etag': 'original-etag'}
            if args[:3] == ['vault','secret','update-base64']:
                self.assertIn('--if-match', args); self.assertIn('original-etag', args)
                path = Path(args[args.index('--from-json')+1][7:]); files.append(path)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
                content = json.loads(path.read_text()); self.assertEqual(content['secretContentStage'], 'CURRENT')
                current.clear(); current.update(json.loads(base64.b64decode(content['secretContentContent'])))
                self.assertNotIn('synthetic-signwell', ' '.join(args))
                return {'data': {'lifecycle-state': 'ACTIVE'}}
            return {'data': {'secret-bundle-content': {'content-type': 'BASE64',
                    'content': base64.b64encode(json.dumps(current).encode()).decode()}}}
        self.assertEqual(publish('compartment', {'signwell_api_key': 'synthetic-signwell'}, api), 'PROVIDER_SECRET_TRANSFERRED')
        self.assertFalse(files[0].exists()); self.assertIn('stripe_webhook_secret', current)
        self.assertEqual(publish('compartment', {'signwell_api_key': 'synthetic-signwell'}, api), 'PROVIDER_SECRET_UNCHANGED')
        self.assertEqual(sum('update-base64' in c for c in calls), 1)

    def test_absent_ambiguous_or_concurrently_changed_destination_cannot_report_success(self):
        for records in ([], [{'secret-name': NAME, 'id': 'one', 'lifecycle-state': 'ACTIVE'}]*2):
            with self.assertRaises(ValueError): publish('compartment', {'signwell_api_key': 'synthetic-signwell'}, lambda args: {'data': records})
        self.assertEqual(publish('compartment', {}, lambda args: self.fail('No supplied secrets must not touch Vault')), 'PROVIDER_CONFIGURATION_PRESERVED')

    def test_gitops_supplies_transfer_hook_only_when_configured(self):
        from tests.test_gitops_deploy import GitOpsTests
        from deploy.gitops_deploy import release
        calls = []
        def api(args, **kwargs):
            if 'get-stack-tf-state' in args: return '{}'
            return {'data': {'variables': {}}}
        def activation(stack, **kwargs):
            self.assertTrue(callable(kwargs['before_install'])); calls.append('hook')
            return {'commit': 'a'*40}
        with tempfile.TemporaryDirectory() as folder:
            archive = GitOpsTests().archive(folder)
            release(archive, 'a'*40, 'ocid1.ormstack.oc1.phx.test', api=api, activation=activation,
                    provider_environment={'SIGNWELL_API_KEY': 'synthetic-signwell'})
        self.assertEqual(calls, ['hook'])
