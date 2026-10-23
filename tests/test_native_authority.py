import tempfile
import time
import unittest
from pathlib import Path
from core_platform.native_notary import NativeNotarySessions
from core_platform.native_authority import NativeAuthority, AuthorityDenied

class NativeAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'notary.db'
        self.sessions=NativeNotarySessions(path)
        self.sessions.create('ron-1','case-1','RON','WI')
        self.sessions.create('enotary-1','case-2','E_NOTARY','CO')
        self.authority=NativeAuthority(path)

    def test_independent_verifier_required(self):
        now=int(time.time())
        args=('ron-1','IDENTITY','evidence-1','verifier-1',now,now+3600)
        with self.assertRaises(AuthorityDenied):
            self.authority.register(*args)
        with self.assertRaises(AuthorityDenied):
            self.authority.register(*args,trusted_verifier=lambda *a: False)
        self.assertIn('IDENTITY',self.authority.missing('ron-1'))

    def test_method_specific_requirements(self):
        self.assertIn('RON_PROVIDER_AUTHORIZATION',self.authority.missing('ron-1'))
        self.assertNotIn('RON_PROVIDER_AUTHORIZATION',self.authority.missing('enotary-1'))


    def test_future_dated_authority_evidence_denied(self):
        now=int(time.time())
        with self.assertRaises(AuthorityDenied):
            self.authority.register('ron-1','IDENTITY','future-evidence','verifier-1',
                now+300,now+3600,trusted_verifier=lambda *a: True)
        self.assertIn('ACT_EXECUTION',self.authority.missing('enotary-1'))

    def test_expired_decision_rejected(self):
        now=int(time.time())
        with self.assertRaises(AuthorityDenied):
            self.authority.register('ron-1','IDENTITY','evidence-1','verifier-1',now-3600,now-1,
                trusted_verifier=lambda *a: True)
