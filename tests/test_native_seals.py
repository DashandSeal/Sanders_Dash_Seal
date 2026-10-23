import base64
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.native_notary import NativeNotarySessions
from core_platform.native_documents import NativeDocuments
from core_platform.native_seals import NativeSeals, SealDenied

class NativeSealsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'notary.db'
        self.sessions=NativeNotarySessions(path)
        self.sessions.create('s-1','c-1','E_NOTARY','CO')
        self.docs=NativeDocuments(path,Path(self.temp.name)/'docs')
        self.digest=self.docs.put('s-1','d-1',b'notarial document')['sha256']
        self.seals=NativeSeals(path)
        self.private=Ed25519PrivateKey.generate()
        self.public=base64.b64encode(self.private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()

    def sign(self,digest=None):
        return base64.b64encode(self.private.sign(self.seals.message('s-1','d-1','notary-1',digest or self.digest))).decode()

    def test_valid_idempotent_seal(self):
        args=('s-1','d-1','seal-1','notary-1',self.public,self.sign())
        result=self.seals.register(*args)
        self.assertTrue(result['cryptographic_seal_verified'])
        self.assertFalse(result['commission_verified'])
        self.assertEqual(result,self.seals.register(*args))

    def test_wrong_digest_rejected(self):
        with self.assertRaises(SealDenied):
            self.seals.register('s-1','d-1','seal-1','notary-1',self.public,self.sign('0'*64))

    def test_cancelled_session_rejected(self):
        self.sessions.cancel('s-1')
        with self.assertRaises(SealDenied):
            self.seals.register('s-1','d-1','seal-1','notary-1',self.public,self.sign())
