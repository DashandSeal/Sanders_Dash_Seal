"""Deployment composition checks; no live identities, payments or credentials."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core_platform.deployment import (create_application, load_application,
    RuntimeBindings, DeploymentConfigurationError, ORIGIN, CANONICAL_HOST)


class DeploymentTests(unittest.TestCase):
    def request(self, app, path='/', *, host=CANONICAL_HOST, method='GET', **extra):
        result = {}
        def start(status, headers):
            result.update(status=status, headers=dict(headers))
        env = {'HTTP_HOST': host, 'PATH_INFO': path, 'REQUEST_METHOD': method,
               'wsgi.input': io.BytesIO(b''), **extra}
        result['body'] = b''.join(app(env, start))
        return result

    def bindings(self, verifier=lambda: True, webhook=None):
        appointments = object()
        payments = SimpleNamespace(appointments=appointments, origin=ORIGIN)
        def auth_app(env, start):
            start('204 No Content', [('Content-Length', '0')])
            return [b'']
        return RuntimeBindings(appointments, payments, lambda env: 'customer',
            auth_app, verifier, webhook)

    def test_default_serves_existing_customer_assets(self):
        result = self.request(create_application())
        self.assertEqual(result['status'], '200 OK')
        self.assertIn(b'Sanders Dash', result['body'])
        self.assertIn(b'booking.js', result['body'])

    def test_liveness_does_not_imply_readiness(self):
        app = create_application()
        self.assertEqual(self.request(app, '/healthz')['status'], '200 OK')
        ready = self.request(app, '/readyz')
        self.assertEqual(ready['status'], '503 Service Unavailable')
        self.assertEqual(json.loads(ready['body']), {'service_ready': False})

    def test_default_operations_are_unavailable(self):
        for path in ('/api/session', '/auth/login', '/api/appointments', '/stripe/webhook'):
            with self.subTest(path=path):
                self.assertEqual(self.request(create_application(), path)['status'],
                                 '503 Service Unavailable')

    def test_aliases_redirect_only_to_fixed_origin(self):
        for host in ('sanderslegalhelpersllc.com', 'www.sanderslegalhelpersllc.com',
                     'www.sandersdashandseal.com'):
            with self.subTest(host=host):
                result = self.request(create_application(), '//evil.test/\r\nInjected:x',
                                      host=host, QUERY_STRING='token=private')
                self.assertEqual(result['status'], '308 Permanent Redirect')
                self.assertEqual(result['headers']['Location'], ORIGIN + '/')
                self.assertNotIn(b'private', result['body'])

    def test_alias_writes_are_not_replayed(self):
        self.assertEqual(self.request(create_application(), '/api/appointments',
            host='sanderslegalhelpersllc.com', method='POST')['status'], '421 Misdirected Request')

    def test_unknown_or_malformed_host_denied_despite_forwarding_headers(self):
        for host in ('evil.test', CANONICAL_HOST + '.evil.test', CANONICAL_HOST + ':80',
                     CANONICAL_HOST + '\r\nX:1', None, ''):
            with self.subTest(host=host):
                self.assertEqual(self.request(create_application(), host=host,
                    HTTP_X_FORWARDED_HOST=CANONICAL_HOST)['status'], '421 Misdirected Request')

    def test_canonical_case_and_tls_port(self):
        self.assertEqual(self.request(create_application(), '/healthz',
            host=CANONICAL_HOST.upper() + ':443')['status'], '200 OK')

    def test_readiness_and_webhook_deny_after_release_revocation(self):
        state = {'allowed': True, 'calls': 0}
        def webhook(env, start):
            state['calls'] += 1
            start('204 No Content', [('Content-Length', '0')])
            return [b'']
        app = create_application(self.bindings(lambda: state['allowed'], webhook))
        self.assertEqual(self.request(app, '/readyz')['status'], '200 OK')
        self.assertEqual(self.request(app, '/stripe/webhook', method='POST')['status'], '204 No Content')
        state['allowed'] = False
        self.assertEqual(self.request(app, '/stripe/webhook', method='POST')['status'], '503 Service Unavailable')
        self.assertEqual(state['calls'], 1)

    def test_verifier_exception_or_nonboolean_is_not_authority(self):
        def failed():
            raise RuntimeError('private configuration')
        for verifier in (failed, lambda: 'yes', lambda: 1):
            with self.subTest(verifier=verifier):
                result = self.request(create_application(self.bindings(verifier)), '/readyz')
                self.assertEqual(result['status'], '503 Service Unavailable')
                self.assertNotIn(b'private', result['body'])

    def test_readiness_probe_cannot_accept_writes(self):
        self.assertEqual(self.request(create_application(), '/healthz', method='POST')['status'],
                         '405 Method Not Allowed')

    def test_bindings_reject_separate_appointment_store_and_wrong_payment_origin(self):
        for key, value in (('appointments', object()), ('origin', 'https://evil.test')):
            bindings = self.bindings()
            setattr(bindings.payments, key, value)
            with self.assertRaises(DeploymentConfigurationError):
                create_application(bindings)

    def test_explicit_bad_factory_does_not_silently_fall_back(self):
        for reference in ('', 'bad reference', 'x:y:z', 'https://evil.test'):
            with self.subTest(reference=reference), self.assertRaises(DeploymentConfigurationError):
                load_application(reference)
        with patch('core_platform.deployment.importlib.import_module',
                   return_value=SimpleNamespace(factory=lambda: None)):
            with self.assertRaises(DeploymentConfigurationError):
                # An explicitly configured factory returning no bindings must
                # not be mistaken for an intentionally unconfigured startup.
                load_application('trusted:factory')
