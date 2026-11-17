"""Local integration evidence using disposable identities and a fake Stripe client."""
import hashlib
import hmac
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from core_platform.appointments import AppointmentStore, AppointmentDenied
from core_platform.appointment_payments import AppointmentPayments
from core_platform.cases import CaseRegistry, CaseDenied
from core_platform.customer_app import create_customer_app
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.stripe_payments import PaymentLedger, PaymentDenied, verify_stripe_webhook
from core_platform.stripe_webhook_wsgi import make_app as make_webhook
from core_platform.upgrade_sidecar import CORE_LAWS


class FakeSessions:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.mismatch = False

    def create(self, params, options):
        self.calls.append((json.loads(json.dumps(params)), dict(options)))
        if self.fail:
            raise TimeoutError('test network failure')
        return {'id': 'cs_test_booking', 'url': 'https://checkout.stripe.com/c/pay/test',
            'client_reference_id': params['client_reference_id'], 'mode': 'payment',
            'currency': 'usd', 'livemode': False, 'amount_total': 1 if self.mismatch else sum(
                item['price_data']['unit_amount'] for item in params['line_items'])}


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'cases.db'
        self.now = 1800000000
        self.clock = lambda: self.now
        self.audit = GlassBoxAudit(Path(self.temp.name) / 'audit.db', clock=self.clock)
        self.cases = CaseRegistry(self.path, CORE_LAWS)
        self.appointments = AppointmentStore(self.cases, self.audit, clock=self.clock)
        self.ledger = PaymentLedger(self.path)
        self.sessions = FakeSessions()
        self.client = SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=self.sessions)))
        self.payments = AppointmentPayments(self.appointments, self.ledger, self.client,
            lambda actor: actor == 'operator', lambda *args: True, lambda *args: True,
            self.audit, 'https://example.test', clock=self.clock)
        self.data = dict(request_id='request-1', jurisdiction='CO', service='MOBILE_NOTARY',
            requested_start=datetime.fromtimestamp(self.now + 7200, timezone.utc).isoformat(),
            meeting_area='Test neighborhood', consent=True)
        self.app = self.make_app()

    def make_app(self, **kwargs):
        return create_customer_app(self.appointments,
            lambda env: 'customer-1' if env.get('HTTP_AUTHORIZATION') == 'Bearer test-only' else None,
            self.payments, lambda env, start: [b''], 'https://example.test', **kwargs)

    def call(self, method, path, data=None, *, auth=True, origin='https://example.test', app=None):
        raw = json.dumps(data).encode() if data is not None else b''
        env = dict(REQUEST_METHOD=method, PATH_INFO=path, CONTENT_TYPE='application/json',
                   CONTENT_LENGTH=str(len(raw)), HTTP_ORIGIN=origin)
        env['wsgi.input'] = io.BytesIO(raw)
        if auth:
            env['HTTP_AUTHORIZATION'] = 'Bearer test-only'
        result = []
        body = b''.join((app or self.make_app(release_verifier=lambda: True))(
            env, lambda status, headers: result.append((status, dict(headers)))))
        return result[0][0], body, result[0][1]

    def request(self, **changes):
        return self.appointments.request('customer-1', **dict(self.data, **changes))

    def approved(self):
        record = self.request()
        quote = self.payments.approve_quote(record['case_id'], 'operator',
            {'Notarial acts': 1000, 'Travel': 2000, 'Document support': 0}, self.now + 86400)
        return record['case_id'], quote['quote_id']

    def test_request_durable_private_and_pending(self):
        record = self.request()
        self.assertEqual(record['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        other = AppointmentStore(self.cases, self.audit, clock=self.clock)
        self.assertEqual(other.get(record['case_id'], 'customer-1'), record)
        with self.assertRaises(AppointmentDenied):
            other.get(record['case_id'], 'different-customer')
        self.assertTrue(self.audit.verify_audit())

    def test_idempotent_parallel_requests_create_one_case(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = list(pool.map(lambda _: self.request(), range(4)))
        self.assertEqual(len({r['case_id'] for r in records}), 1)
        with self.assertRaises(AppointmentDenied):
            self.request(meeting_area='Different neighborhood')
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cases').fetchone()[0], 1)

    def test_failed_appointment_insert_rolls_back_case(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON appointments BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.request()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cases').fetchone()[0], 0)

    def test_no_consent_past_naive_remote_or_unknown_state(self):
        for change in [{'consent': False}, {'consent': 'true'}, {'jurisdiction': 'FL'},
                       {'service': 'RON'}, {'requested_start': '2026-01-01T10:00:00'},
                       {'requested_start': '2000-01-01T00:00:00Z'}, {'meeting_area': '\ninvalid'}]:
            with self.subTest(change=change), self.assertRaises(AppointmentDenied):
                self.request(**change)
        self.assertEqual(self.appointments.list_owned('customer-1'), [])

    def test_audit_failure_creates_no_case(self):
        class FailedAudit:
            def preserve(self, event):
                raise OSError('test audit unavailable')
        self.appointments.audit = FailedAudit()
        with self.assertRaises(OSError):
            self.request()
        self.assertEqual(self.appointments.list_owned('customer-1'), [])

    def test_api_requires_release_and_authentication(self):
        self.assertEqual(self.call('POST', '/api/appointments', self.data, app=self.app)[0], '503 Service Unavailable')
        self.assertEqual(self.call('POST', '/api/appointments', self.data, auth=False)[0], '401 Unauthorized')
        self.assertEqual(self.appointments.list_owned('customer-1'), [])

    def test_cross_origin_and_browser_identity_or_price_denied(self):
        self.assertEqual(self.call('POST', '/api/appointments', self.data, origin='https://evil.test')[0], '403 Forbidden')
        for field, value in [('requester', 'operator'), ('paid', True), ('price', 1)]:
            self.assertEqual(self.call('POST', '/api/appointments', dict(self.data, **{field: value}))[0], '400 Bad Request')
        self.assertEqual(self.appointments.list_owned('customer-1'), [])

    def test_static_files_security_headers_and_traversal_denied(self):
        status, body, headers = self.call('GET', '/', auth=False, app=self.app)
        self.assertEqual(status, '200 OK')
        self.assertIn(b'Sanders Dash &amp; Seal', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.call('GET', '/assets/../AGENTS.md')[0], '404 Not Found')

    def test_no_quote_no_checkout_and_no_customer_quote_route(self):
        case_id = self.request()['case_id']
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', 'unknown', True)
        self.assertEqual(self.call('POST', '/api/quotes', {})[0], '404 Not Found')
        self.assertEqual(self.sessions.calls, [])

    def test_operator_and_fee_verification_required(self):
        case_id = self.request()['case_id']
        items = {'Notarial acts': 1000, 'Travel': 0, 'Document support': 0}
        with self.assertRaises(PaymentDenied):
            self.payments.approve_quote(case_id, 'customer-1', items, self.now + 3600)
        self.payments.fee_verifier = lambda *args: False
        with self.assertRaises(PaymentDenied):
            self.payments.approve_quote(case_id, 'operator', items, self.now + 3600)
        self.assertIsNone(self.payments.quote(case_id, 'customer-1'))

    def test_checkout_requires_acceptance_ownership_eligibility_and_current_quote(self):
        case_id, quote_id = self.approved()
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, False)
        with self.assertRaises(AppointmentDenied):
            self.payments.checkout(case_id, 'another', quote_id, True)
        self.payments.eligibility_verifier = lambda *a: False
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertEqual(self.sessions.calls, [])

    def test_retry_same_key_exact_params_and_single_ledger_binding(self):
        case_id, quote_id = self.approved()
        self.sessions.fail = True
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertIsNone(self.ledger.status(case_id))
        self.sessions.fail = False
        result = self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertEqual(self.sessions.calls[0], self.sessions.calls[1])
        self.assertEqual(self.ledger.status(case_id), 'PENDING')
        self.assertEqual(self.payments.checkout(case_id, 'customer-1', quote_id, True), result)
        self.assertEqual(len(self.sessions.calls), 2)

    def test_provider_response_mismatch_never_binds_payment(self):
        case_id, quote_id = self.approved()
        self.sessions.mismatch = True
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertIsNone(self.ledger.status(case_id))

    def test_environment_mismatch_never_exposes_checkout_url(self):
        case_id, quote_id = self.approved()
        self.payments.expected_livemode = True
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertIsNone(self.ledger.status(case_id))

    def test_customer_cannot_access_operator_queue_or_forge_quote_approval(self):
        case_id = self.request()['case_id']
        self.assertEqual(self.call('GET', '/api/operator/appointments')[0], '403 Forbidden')
        self.assertEqual(self.call('POST', '/api/operator/appointments/' + case_id + '/quote', {
            'actor': 'operator', 'items': {}, 'expires_at': self.now + 3600})[0], '403 Forbidden')
        self.assertIsNone(self.payments.quote(case_id, 'customer-1'))

    def test_operator_quote_api_derives_actor_from_verified_identity(self):
        case_id = self.request()['case_id']
        operator = create_customer_app(self.appointments, lambda env: 'operator', self.payments,
            lambda env, start: [b''], 'https://example.test', release_verifier=lambda: True)
        self.assertEqual(self.call('GET', '/api/operator/appointments', app=operator)[0], '200 OK')
        payload = {'items': {'Notarial acts': 1000, 'Travel': 0, 'Document support': 0},
                   'expires_at': self.now + 3600}
        route = '/api/operator/appointments/' + case_id + '/quote'
        self.assertEqual(self.call('POST', route, dict(payload, actor='anyone'), app=operator)[0], '400 Bad Request')
        self.assertEqual(self.call('POST', route, payload, app=operator)[0], '201 Created')
        self.assertEqual(self.call('POST', route, payload, app=operator)[0], '409 Conflict')

    def test_old_uncertain_attempt_and_expired_session_do_not_create_new_charge(self):
        case_id, quote_id = self.approved()
        self.sessions.fail = True
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.now += 23 * 3600
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertEqual(len(self.sessions.calls), 1)

    def test_expired_quote_or_session_does_not_reopen_checkout(self):
        case_id, quote_id = self.approved()
        self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.now += 86401
        with self.assertRaises(PaymentDenied):
            self.payments.checkout(case_id, 'customer-1', quote_id, True)
        self.assertEqual(len(self.sessions.calls), 1)

    def test_unknown_customer_cannot_read_quote_or_pay(self):
        case_id, quote_id = self.approved()
        other_app = create_customer_app(self.appointments, lambda env: 'customer-2',
            self.payments, lambda env, start: [b''], 'https://example.test',
            release_verifier=lambda: True)
        self.assertEqual(self.call('GET', '/api/appointments/' + case_id, app=other_app)[0], '404 Not Found')
        self.assertEqual(self.call('POST', '/api/appointments/' + case_id + '/checkout',
            {'quote_id': quote_id, 'accept_quote': True}, app=other_app)[0], '404 Not Found')
        self.assertEqual(self.sessions.calls, [])

    def test_complete_local_request_quote_checkout_signed_webhook_status(self):
        status, body, _ = self.call('POST', '/api/appointments', self.data)
        self.assertEqual(status, '201 Created')
        case_id = json.loads(body)['appointment']['case_id']
        quote = self.payments.approve_quote(case_id, 'operator',
            {'Notarial acts': 1000, 'Travel': 2000, 'Document support': 0}, self.now + 86400)
        route = '/api/appointments/' + case_id
        self.assertEqual(self.call('POST', route + '/checkout', {
            'quote_id': quote['quote_id'], 'accept_quote': True})[0], '200 OK')
        # Returning from Checkout cannot itself change the payment state.
        self.assertEqual(self.call('GET', '/appointments')[0], '200 OK')
        self.assertEqual(self.ledger.status(case_id), 'PENDING')
        params = self.sessions.calls[0][0]
        self.assertNotIn('payment_method_types', params)
        self.assertEqual([x['price_data']['unit_amount'] for x in params['line_items']], [1000, 2000])
        self.assertRegex(params['integration_identifier'], r'^sanders_dash_seal_[a-z]{8}$')
        event = {'id': 'evt_booking', 'type': 'checkout.session.completed', 'data': {'object': {
            'id': 'cs_test_booking', 'client_reference_id': case_id, 'amount_total': 3000,
            'currency': 'usd', 'mode': 'payment', 'payment_status': 'paid'}}}
        payload = json.dumps(event).encode()
        signature = hmac.new(b'test-only', str(self.now).encode() + b'.' + payload, hashlib.sha256).hexdigest()
        webhook = make_webhook(self.ledger, 'test-only', enabled=True)
        result = []
        env = {'PATH_INFO': '/stripe/webhook', 'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(payload)),
            'wsgi.input': io.BytesIO(payload), 'HTTP_STRIPE_SIGNATURE': f't={self.now},v1={signature}'}
        with patch('core_platform.stripe_payments.time.time', return_value=self.now):
            b''.join(webhook(env, lambda status, headers: result.append(status)))
        self.assertEqual(result, ['200 OK'])
        verified = verify_stripe_webhook(payload, f't={self.now},v1={signature}', 'test-only', now=self.now)
        self.assertEqual(self.ledger.record_event(verified), 'DUPLICATE')
        state = json.loads(self.call('GET', route)[1])
        self.assertEqual(state['payment'], 'PAID')
        self.assertEqual(state['appointment']['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        with self.assertRaises(CaseDenied):
            self.cases.authorize_notarization(case_id)

if __name__ == '__main__':
    unittest.main()
