import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from core_platform.stripe_payments import (
    PaymentDenied, PaymentLedger, verify_stripe_webhook, checkout_parameters)

class StripePaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = PaymentLedger(Path(self.tmp.name) / 'payments.db')
        self.ledger.register_checkout('case-1', 'cs_test_1', 2500, 'usd')
        self.event = {'id': 'evt_1', 'type': 'checkout.session.completed',
                      'data': {'object': {'id': 'cs_test_1',
                          'client_reference_id': 'case-1',
                          'amount_total': 2500, 'currency': 'usd',
                          'mode': 'payment', 'payment_status': 'paid',
                          'payment_intent': 'pi_test_1'}}}

    def signed(self, event=None, timestamp=1000):
        payload = json.dumps(self.event if event is None else event).encode()
        digest = hmac.new(b'whsec_dev', str(timestamp).encode() + b'.' + payload,
                          hashlib.sha256).hexdigest()
        return payload, f't={timestamp},v1={digest}'

    def test_signed_payment_and_replay(self):
        payload, header = self.signed()
        event = verify_stripe_webhook(payload, header, 'whsec_dev', now=1000)
        self.assertEqual(self.ledger.record_event(event), 'RECORDED')
        self.assertEqual(self.ledger.status('case-1'), 'PAID')
        self.assertEqual(self.ledger.record_event(event), 'DUPLICATE')

    def test_bad_signature_and_expiry(self):
        payload, header = self.signed()
        with self.assertRaises(PaymentDenied):
            verify_stripe_webhook(payload + b' ', header, 'whsec_dev', now=1000)
        with self.assertRaises(PaymentDenied):
            verify_stripe_webhook(payload, header, 'whsec_dev', now=1400)

    def test_wrong_case_amount_and_session_fail_closed(self):
        for field, value in [('amount_total', 100), ('id', 'cs_other'),
                             ('client_reference_id', 'other')]:
            event = json.loads(json.dumps(self.event))
            event['data']['object'][field] = value
            with self.assertRaises(PaymentDenied):
                self.ledger.record_event(event)
            self.assertEqual(self.ledger.status('case-1'), 'PENDING')

    def test_unpaid_does_not_unlock(self):
        event = json.loads(json.dumps(self.event))
        event['data']['object']['payment_status'] = 'unpaid'
        self.assertEqual(self.ledger.record_event(event), 'RECORDED')
        self.assertEqual(self.ledger.status('case-1'), 'PENDING')

    def test_checkout_server_validation(self):
        params = checkout_parameters('case-1', 2500, 'usd', 'Authorized service',
                                     'https://example.org/success', 'https://example.org/cancel')
        self.assertEqual(params['client_reference_id'], 'case-1')
        with self.assertRaises(PaymentDenied):
            checkout_parameters('case-1', 0, 'usd', 'service',
                                'https://example.org/success', 'https://example.org/cancel')

    def test_duplicate_case_registration(self):
        with self.assertRaises(PaymentDenied):
            self.ledger.register_checkout('case-1', 'cs_test_2', 2500, 'usd')

if __name__ == '__main__':
    unittest.main()
