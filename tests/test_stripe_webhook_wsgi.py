import hashlib
import hmac
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from core_platform.stripe_payments import PaymentLedger
from core_platform.stripe_webhook_wsgi import make_app

class WebhookIngressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = PaymentLedger(Path(self.temp.name) / 'ledger.db')
        self.ledger.register_checkout('case-1', 'cs_test_1', 2500, 'usd')
        self.event = {'id':'evt_wsgi_1','type':'checkout.session.completed',
                      'data':{'object':{'id':'cs_test_1','client_reference_id':'case-1',
                                        'amount_total':2500,'currency':'usd','mode':'payment',
                                        'payment_status':'paid'}}}

    def call(self, *, body=None, signature=None, enabled=True, method='POST', path='/stripe/webhook'):
        if body is None:
            body = json.dumps(self.event).encode()
        if signature is None:
            stamp = int(time.time())
            digest = hmac.new(b'whsec_test', str(stamp).encode()+b'.'+body, hashlib.sha256).hexdigest()
            signature = f't={stamp},v1={digest}'
        env = {'PATH_INFO':path, 'REQUEST_METHOD':method,
               'CONTENT_TYPE':'application/json', 'CONTENT_LENGTH':str(len(body)),
               'wsgi.input':io.BytesIO(body),'HTTP_STRIPE_SIGNATURE':signature}
        result = []
        response = make_app(self.ledger,'whsec_test',enabled=enabled)(env,lambda status,headers:result.append(status))
        return result[0], b''.join(response)

    def test_signed_delivery_and_retry(self):
        self.assertEqual(self.call()[0], '200 OK')
        self.assertEqual(self.ledger.status('case-1'), 'PAID')
        self.assertEqual(self.call()[0], '200 OK')

    def test_disabled_by_default(self):
        self.assertEqual(self.call(enabled=False)[0], '503 Service Unavailable')
        self.assertEqual(self.ledger.status('case-1'), 'PENDING')

    def test_invalid_signature_and_wrong_route(self):
        self.assertEqual(self.call(signature='t=1,v1=bad')[0], '400 Bad Request')
        self.assertEqual(self.call(path='/admin')[0], '404 Not Found')
        self.assertEqual(self.call(method='GET')[0], '405 Method Not Allowed')
        self.assertEqual(self.ledger.status('case-1'), 'PENDING')

    def test_invalid_amount_rejected(self):
        self.event['data']['object']['amount_total']=1
        self.assertEqual(self.call()[0], '400 Bad Request')
        self.assertEqual(self.ledger.status('case-1'), 'PENDING')

if __name__ == '__main__':
    unittest.main()
