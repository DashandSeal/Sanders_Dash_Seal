import tempfile
import unittest
from pathlib import Path
from core_platform.cases import CaseRegistry, CaseDenied
from core_platform.upgrade_sidecar import CORE_LAWS

class CaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cases.db'
        self.cases = CaseRegistry(self.path, CORE_LAWS)

    def test_intake_is_durable_and_not_automatically_authorized(self):
        record = self.cases.create('case-1','CO','E_NOTARY','client-1')
        self.assertEqual(record['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        self.assertEqual(CaseRegistry(self.path, CORE_LAWS).get('case-1'), record)
        with self.assertRaises(CaseDenied):
            self.cases.authorize_notarization('case-1')

    def test_duplicate_and_unknown_service_denied(self):
        self.cases.create('case-1','WI','RON','client-1')
        with self.assertRaises(CaseDenied):
            self.cases.create('case-1','WI','RON','client-1')
        with self.assertRaises(CaseDenied):
            self.cases.create('case-2','WI','UNKNOWN','client-1')

    def test_laws_required(self):
        with self.assertRaises(Exception):
            CaseRegistry(self.path, CORE_LAWS[:-1])

if __name__ == '__main__':
    unittest.main()
