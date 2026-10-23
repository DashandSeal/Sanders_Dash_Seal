import tempfile
import unittest
from pathlib import Path
from core_platform.authority_review import AuthorityReview, AuthorityDenied
from core_platform.cases import CaseRegistry
from core_platform.upgrade_sidecar import CORE_LAWS

class Audit:
    def __init__(self): self.events=[]
    def preserve(self,event): self.events.append(event)

class AuthorityReviewTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cases=CaseRegistry(Path(temp.name)/'cases.db',CORE_LAWS)
        self.cases.create('case-1','CO','E_NOTARY','customer-1')
        self.audit=Audit()
        self.db=Path(temp.name)/'reviews.db'

    def bridge(self, identity=True, authority=True, provider=True):
        return AuthorityReview(self.db,self.cases,
            lambda *args:identity,lambda *args:authority,
            lambda *args:provider,self.audit,CORE_LAWS)

    def test_verified_human_review_does_not_execute_notarial_act(self):
        result=self.bridge().review('case-1','reviewer-1','notary-1',{'authority_ref':'verified'})
        self.assertEqual(result['status'],'REVIEW_VERIFIED')
        self.assertFalse(result['notarial_act_executed'])
        self.assertEqual(len(self.audit.events),1)

    def test_denied_authority_no_review_record(self):
        with self.assertRaises(AuthorityDenied):
            self.bridge(authority=False).review('case-1','reviewer-1','notary-1',{'ref':'x'})
        self.assertEqual(len(self.audit.events),0)

    def test_denied_provider(self):
        with self.assertRaises(AuthorityDenied):
            self.bridge(provider=False).review('case-1','reviewer-1','notary-1',{'ref':'x'})

    def test_mobile_review_keeps_independent_checks_without_ron_provider(self):
        self.cases.create('mobile-1', 'WI', 'MOBILE_NOTARY', 'customer-1')
        seen = []
        bridge = AuthorityReview(self.db, self.cases, lambda *args: True,
            lambda *args: True,
            lambda case, provider, evidence: seen.append(provider) is None,
            self.audit, CORE_LAWS)
        result = bridge.review('mobile-1', 'reviewer-1', 'notary-1', {'ref': 'test-only'})
        self.assertEqual(seen, [None])
        self.assertFalse(result['notarial_act_executed'])
        self.assertEqual(self.cases.get('mobile-1')['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')

    def test_mobile_denied_authority_and_adapter_failure(self):
        self.cases.create('mobile-1', 'CO', 'MOBILE_NOTARY', 'customer-1')
        with self.assertRaises(AuthorityDenied):
            self.bridge(authority=False).review('mobile-1', 'reviewer-1', 'notary-1', {'ref': 'x'})
        def unavailable(*args):
            raise RuntimeError('verification unavailable')
        bridge = AuthorityReview(self.db, self.cases, unavailable, lambda *a: True,
                                 lambda *a: True, self.audit, CORE_LAWS)
        with self.assertRaises(AuthorityDenied):
            bridge.review('mobile-1', 'reviewer-1', 'notary-1', {'ref': 'x'})
        self.assertEqual(self.audit.events, [])

    def test_duplicate_review_denied(self):
        bridge=self.bridge()
        bridge.review('case-1','reviewer-1','notary-1',{'ref':'x'})
        with self.assertRaises(AuthorityDenied):
            bridge.review('case-1','reviewer-1','notary-1',{'ref':'x'})

if __name__=='__main__':
    unittest.main()
