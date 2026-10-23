import io
import json
import tempfile
import unittest
from pathlib import Path
from core_platform.case_api_wsgi import create_app
from core_platform.cases import CaseRegistry
from core_platform.upgrade_sidecar import CORE_LAWS

class APITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.registry = CaseRegistry(Path(temp.name)/'cases.db', CORE_LAWS)
        self.app = create_app(self.registry, lambda env: 'human-1' if env.get('HTTP_AUTHORIZATION')=='Bearer valid' else None)

    def request(self, method, path, data=None, auth=True):
        raw = json.dumps(data).encode() if data is not None else b''
        env = {'REQUEST_METHOD':method,'PATH_INFO':path,
               'CONTENT_LENGTH':str(len(raw)),'CONTENT_TYPE':'application/json',
               'wsgi.input':io.BytesIO(raw)}
        if auth: env['HTTP_AUTHORIZATION']='Bearer valid'
        result=[]
        def start(status, headers): result.append(status)
        body = b''.join(self.app(env,start))
        return result[0], json.loads(body)

    def test_create_and_read_owned_case(self):
        status, body=self.request('POST','/v1/cases',{'case_id':'c-1','jurisdiction':'CO','service':'E_NOTARY'})
        self.assertEqual(status,'201 Created')
        self.assertEqual(body['case']['status'],'AWAITING_HUMAN_AUTHORITY_REVIEW')
        self.assertEqual(self.request('GET','/v1/cases/c-1')[0],'200 OK')

    def test_unauthenticated_denied(self):
        self.assertEqual(self.request('GET','/v1/cases/c-1',auth=False)[0],'401 Unauthorized')

    def test_mobile_intake_remains_pending_and_private(self):
        status, body = self.request('POST', '/v1/cases', {
            'case_id': 'mobile-1', 'jurisdiction': 'CO', 'service': 'MOBILE_NOTARY'})
        self.assertEqual(status, '201 Created')
        self.assertEqual(body['case']['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        other = create_app(self.registry, lambda env: 'another-human')
        result = []
        response = other({'PATH_INFO': '/v1/cases/mobile-1', 'REQUEST_METHOD': 'GET'},
                         lambda status, headers: result.append(status))
        self.assertEqual(result, ['404 Not Found'])
        self.assertNotIn(b'MOBILE_NOTARY', b''.join(response))

    def test_no_requester_spoofing(self):
        self.assertEqual(self.request('POST','/v1/cases',{'case_id':'c-2','jurisdiction':'CO',
            'service':'RON','requester':'another'})[0],'400 Bad Request')

    def test_no_unauthorized_act(self):
        self.assertEqual(self.request('POST','/v1/cases',{'case_id':'c-3','jurisdiction':'CO',
            'service':'NOTARIZE_NOW'})[0],'400 Bad Request')

if __name__=='__main__':
    unittest.main()
