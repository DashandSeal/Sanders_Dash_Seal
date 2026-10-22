"""Actual WSGI/provider request persistence with only external HTTP replaced."""
import base64
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from core_platform.native_runtime import create_native_application, read_settings
from core_platform.provider_connections import WriteProviderClient, NoRedirect, ProviderConnectionError
from core_platform.provider_workflows import prepare
from core_platform.accounts import digest, COOKIE
from deploy.refresh_provider_secrets import retrieve, refresh, NAME
from core_platform.deployment import ORIGIN
import time


class ProviderWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'data' / 'database.sqlite'
        self.app = create_native_application(self.path, settings={
            'owner_setup_digest': digest('setup-secret-for-test-only-1234567890123456'), 'owner_setup_expires': time.time()+3600})
        self.app.accounts.register('owner-one', 'owner test passphrase here', setup_token='setup-secret-for-test-only-1234567890123456')
        self.token = self.app.accounts.login('owner-one', 'owner test passphrase here')
        # AccountStore.login returns the opaque session credential.
        self.calls = []
        def http(request, timeout):
            self.calls.append(request)
            payload = {'id': 'document-one'} if 'signwell.com' in request.full_url else {
                'response': 'Pass', 'bn_session_id': 'session-one', 'signing_urls': ['PRIVATE-LOGIN-URL']}
            return io.BytesIO(json.dumps(payload).encode())
        for provider in ('signwell', 'bluenotary'):
            self.app.providers.clients[provider] = WriteProviderClient(provider, 'synthetic-provider-credential', opener=http)
        self.app.cases.create('case-one', 'WI', 'AUTHORIZED_DOCUMENT_SERVICE', 'customer-one')

    def request(self, provider=None, data=None, *, token=True, origin=ORIGIN, case='case-one'):
        raw = json.dumps(data or {}).encode()
        path = '/api/operator/appointments/' + case + '/providers' + ('/' + provider if provider else '')
        env = {'HTTP_HOST': 'sandersdashandseal.com', 'PATH_INFO': path,
               'REQUEST_METHOD': 'POST' if provider else 'GET', 'HTTP_ORIGIN': origin,
               'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        if token: env['HTTP_COOKIE'] = COOKIE + '=' + self.token
        result = {}
        def start(status, headers): result['status'] = status
        result['body'] = json.loads(b''.join(self.app(env, start)))
        return result

    def signwell(self):
        return {'request_id': 'request-one', 'template_id': 'template-one', 'name': 'Document support',
                'recipients': [{'id': '1', 'placeholder_name': 'Customer', 'name': 'Test Customer', 'email': 'test@example.invalid'}]}

    def bluenotary(self):
        return {'request_id': 'request-one', 'document_templates': ['template-one'],
                'all_signers': [{'first_name': 'Test', 'last_name': 'Customer', 'email': 'test@example.invalid'}],
                'session_notary_email': 'notary@example.invalid', 'notarization_timing_type': 'notarize_now'}

    def test_signwell_route_creates_once_records_reference_and_survives_restart(self):
        result = self.request('signwell', self.signwell())
        self.assertEqual(result['status'], '201 Created', result)
        self.assertFalse(result['body']['notarial_act_executed'])
        self.assertEqual(self.request('signwell', self.signwell()), result)
        self.assertEqual(len(self.calls), 1)
        sent = self.calls[0]
        self.assertEqual(sent.method, 'POST')
        self.assertEqual(sent.full_url, 'https://www.signwell.com/api/v1/document_templates/documents/')
        self.assertEqual(sent.get_header('X-api-key'), 'synthetic-provider-credential')
        self.assertFalse(json.loads(sent.data)['test_mode'])
        self.app = create_native_application(self.path, settings={})
        self.assertEqual(self.request()['body']['requests'][0]['resource_id'], 'document-one')
        with sqlite3.connect(self.path) as db:
            stored = str(db.execute('SELECT * FROM provider_requests').fetchall())
        self.assertNotIn('test@example.invalid', stored)
        self.assertNotIn('synthetic-provider-credential', stored)

    def test_bluenotary_uses_documented_ron_schema_and_never_returns_login_urls(self):
        result = self.request('bluenotary', self.bluenotary())
        self.assertEqual(result['status'], '201 Created', result)
        sent = self.calls[0]; payload = json.loads(sent.data)
        self.assertEqual(sent.get_header('Authorization'), 'Bearer synthetic-provider-credential')
        self.assertEqual(payload['signing_type'], 'ron'); self.assertEqual(payload['session_type'], 'gnw')
        self.assertEqual(len(payload['notarization_id']), 64)
        self.assertNotIn('PRIVATE-LOGIN-URL', json.dumps(result))
        self.assertEqual(self.app.cases.get('case-one')['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')

    def test_customer_csrf_unknown_case_and_changed_request_cannot_submit(self):
        self.assertEqual(self.request('signwell', self.signwell(), token=False)['status'], '401 Unauthorized')
        self.assertEqual(self.request('signwell', self.signwell(), origin='https://bad.invalid')['status'], '403 Forbidden')
        self.assertEqual(self.request('signwell', self.signwell(), case='unknown')['status'], '404 Not Found')
        self.request('signwell', self.signwell())
        changed = self.signwell(); changed['name'] = 'Changed'
        self.assertEqual(self.request('signwell', changed)['status'], '409 Conflict')
        self.app.accounts.register('customer-one', 'customer test passphrase here')
        self.token = self.app.accounts.login('customer-one', 'customer test passphrase here')
        self.assertEqual(self.request('bluenotary', self.bluenotary())['status'], '403 Forbidden')
        self.assertEqual(len(self.calls), 1)

    def test_uncertain_post_is_persistent_and_never_automatically_retried(self):
        def fail(request, timeout):
            self.calls.append(request); raise urllib.error.URLError('private-provider-response')
        self.app.providers.clients['signwell'] = WriteProviderClient('signwell', 'synthetic-provider-credential', opener=fail)
        self.assertEqual(self.request('signwell', self.signwell())['status'], '503 Service Unavailable')
        self.assertEqual(self.request('signwell', self.signwell())['status'], '409 Conflict')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.request()['body']['requests'][0]['state'], 'OUTCOME_UNKNOWN')
        self.assertNotIn('private-provider-response', json.dumps(self.request()))

    def test_missing_credentials_do_not_create_records_or_disable_core(self):
        self.app.providers.clients.clear()
        self.assertEqual(self.request('signwell', self.signwell())['status'], '503 Service Unavailable')
        self.assertEqual(self.request()['body']['requests'], [])
        self.assertTrue(self.app.available())
        self.assertFalse(self.app.status()['independent_ai_authorities_connected'])

    def test_provider_failure_body_malformed_and_oversized_response_not_success(self):
        for raw in (b'[]', b'invalid-json', b'x' * (1024*1024+1), b'{"response":"Fail","bn_session_id":"session-one"}'):
            with self.subTest(raw_length=len(raw)):
                payload = self.bluenotary(); payload['request_id'] = 'request-' + str(len(self.calls))
                def http(request, timeout): self.calls.append(request); return io.BytesIO(raw)
                self.app.providers.clients['bluenotary'] = WriteProviderClient('bluenotary', 'synthetic-provider-credential', opener=http)
                self.assertEqual(self.request('bluenotary', payload)['status'], '503 Service Unavailable')

    def test_strict_provider_fields_timing_recipient_header_and_redirect_boundaries(self):
        payload = self.signwell(); payload['arbitrary_endpoint'] = 'https://bad.invalid'
        self.assertEqual(self.request('signwell', payload)['status'], '400 Bad Request')
        payload = self.bluenotary(); payload['notarization_timing_type'] = 'notarize_later'
        self.assertEqual(self.request('bluenotary', payload)['status'], '400 Bad Request')
        with self.assertRaises(ValueError): WriteProviderClient('signwell', 'synthetic\nheader')
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://bad.invalid'))
        self.assertEqual(self.calls, [])

    def test_vault_and_runtime_support_both_stripe_key_types_and_provider_keys(self):
        for prefix in ('rk_' + 'live_', 'sk_' + 'live_'):
            payload = {'stripe_api_key': prefix + 'synthetic-not-a-credential', 'stripe_livemode': True,
                       'signwell_api_key': 'synthetic-signwell', 'signwell_test_mode': False,
                       'bluenotary_api_key': 'synthetic-bluenotary'}
            def api(args):
                if args[0] == 'vault':
                    return {'data': [{'secret-name': NAME, 'id': 'selected', 'lifecycle-state': 'ACTIVE'}]}
                return {'data': {'secret-bundle-content': {'content-type': 'BASE64',
                        'content': base64.b64encode(json.dumps(payload).encode()).decode()}}}
            self.assertEqual(retrieve('compartment', api), payload)
            app = create_native_application(Path(self.temp.name) / prefix / 'database.sqlite', settings=payload)
            self.assertTrue(app.status()['signwell_credentials_configured'])
            self.assertTrue(app.status()['bluenotary_credentials_configured'])
            payload['stripe_livemode'] = False
            with self.assertRaises(ValueError): retrieve('compartment', api)
            with self.assertRaises(ValueError): create_native_application(self.path, settings=payload)


if __name__ == '__main__': unittest.main()
