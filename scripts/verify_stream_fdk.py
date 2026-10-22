"""Exercise the actual FDK invocation/response protocol with a simulated HTTPS core."""
import asyncio
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fdk import fixtures


MODULE_PATH = Path(os.environ.get('SDS_FUNCTION_MODULE',
    str(Path(__file__).resolve().parents[1] / 'serverless/sds-transaction-validator-fn/integrated.py')))
spec = importlib.util.spec_from_file_location('sds_fdk_module', MODULE_PATH)
function = importlib.util.module_from_spec(spec)
spec.loader.exec_module(function)


class ActualFDKTests(unittest.TestCase):
    def invoke(self, raw):
        async def run():
            call = await fixtures.setup_fn_call(function.handler, content=io.BytesIO(raw))
            return await call
        return asyncio.run(run())

    def test_malformed_batch_has_real_503_response(self):
        body, status, headers = self.invoke(b'{}')
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': 'stream_batch_not_committed'})

    def test_real_fdk_and_dispatch_return_matching_committed_receipt_list(self):
        event = {'actor': 'fixture', 'transaction_id': 'fixture1', 'signature': 'fixture-only',
                 'transaction': {'request_id': 'fixture1'}}
        receipt = {'transaction_id': 'fixture1', 'status': 'COMMITTED',
                   'receipt': {'request_id': 'fixture1'}}
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return json.dumps(receipt).encode()
        class Opener:
            def open(self, request, timeout):
                assert json.loads(request.data) == event
                assert request.full_url == 'https://sandersdashandseal.com/api/stream/transactions'
                return Response()
        batch = json.dumps([{'value': base64.b64encode(json.dumps(event).encode()).decode()}]).encode()
        with patch.dict(os.environ, {'SDS_STREAM_BACKEND_URL':
                'https://sandersdashandseal.com/api/stream/transactions'}), \
                patch.object(function.urllib.request, 'build_opener', return_value=Opener()):
            body, status, headers = self.invoke(batch)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), [receipt])

    def test_backend_transport_failure_produces_no_false_acknowledgement(self):
        event = {'actor': 'fixture', 'transaction_id': 'fixture1', 'signature': 'fixture-only',
                 'transaction': {'request_id': 'fixture1'}}
        batch = json.dumps([{'value': base64.b64encode(json.dumps(event).encode()).decode()}]).encode()
        with patch.dict(os.environ, {'SDS_STREAM_BACKEND_URL':
                'https://sandersdashandseal.com/api/stream/transactions'}), \
                patch.object(function.urllib.request, 'build_opener', side_effect=OSError('private detail')):
            body, status, headers = self.invoke(batch)
        self.assertEqual(status, 503)
        self.assertNotIn('private detail', body)


if __name__ == '__main__':
    unittest.main()
