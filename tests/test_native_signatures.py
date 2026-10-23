import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from core_platform.native_notary import NativeNotarySessions
from core_platform.native_documents import NativeDocuments
from core_platform.native_signatures import NativeSignatures, SignatureDenied

class NativeSignatureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'notary.db'
        self.sessions=NativeNotarySessions(path)
        self.sessions.create('s-1','c-1','E_NOTARY','CO')
        self.docs=NativeDocuments(path,Path(self.temp.name)/'docs')
        self.docs.put('s-1','d-1',b'document')
        self.signatures=NativeSignatures(path)
        self.key=Ed25519PrivateKey.generate()
        self.public=base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        self.digest=hashlib.sha256(b'document').hexdigest()

    def signature(self,digest=None):
        message=self.signatures.message('s-1','d-1','signer-1',digest or self.digest)
        return base64.b64encode(self.key.sign(message)).decode()

    def test_valid_and_idempotent(self):
        args=('s-1','d-1','sig-1','signer-1',self.public,self.signature())
        first=self.signatures.record(*args)
        self.assertTrue(first['cryptographic_signature_verified'])
        self.assertFalse(first['notarial_act_completed'])
        self.assertEqual(self.signatures.record(*args),first)

    def test_wrong_digest_rejected(self):
        with self.assertRaises(SignatureDenied):
            self.signatures.record('s-1','d-1','sig-1','signer-1',self.public,self.signature('0'*64))

    def test_cancelled_session_rejected(self):
        self.sessions.cancel('s-1')
        with self.assertRaises(SignatureDenied):
            self.signatures.record('s-1','d-1','sig-1','signer-1',self.public,self.signature())

    def test_unknown_document_rejected(self):
        with self.assertRaises(SignatureDenied):
            self.signatures.record('s-1','missing','sig-1','signer-1',self.public,self.signature())
