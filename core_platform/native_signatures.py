"""Native Ed25519 document signature verification; not proof of notarial authority."""
import base64
from pathlib import Path
from .native_documents import NativeDocuments, DocumentDenied
import re
import sqlite3
import time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ID = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z', re.ASCII)

class SignatureDenied(ValueError):
    pass

class NativeSignatures:
    def __init__(self, path, *, storage_dir=None):
        self.path=str(path)
        self.storage_dir=Path(storage_dir) if storage_dir is not None else Path(self.path).with_name('native_documents')
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_document_signatures (
                session_id TEXT NOT NULL, signature_id TEXT NOT NULL,
                document_id TEXT NOT NULL, signer_id TEXT NOT NULL,
                document_digest TEXT NOT NULL, public_key BLOB NOT NULL,
                signature BLOB NOT NULL, recorded_at INTEGER NOT NULL,
                PRIMARY KEY(session_id,signature_id))""")

    @staticmethod
    def message(session_id,document_id,signer_id,digest):
        return ('SDS-NATIVE-DOCUMENT-SIGNATURE-V1\n'+session_id+'\n'+document_id+'\n'+signer_id+'\n'+digest).encode()

    def record(self,session_id,document_id,signature_id,signer_id,public_key_b64,signature_b64):
        if not all(isinstance(v,str) and ID.fullmatch(v) for v in (session_id,document_id,signature_id,signer_id)):
            raise SignatureDenied('Invalid identifier')
        try:
            key=base64.b64decode(public_key_b64,validate=True)
            sig=base64.b64decode(signature_b64,validate=True)
            if len(key)!=32 or len(sig)!=64: raise ValueError('Invalid key length')
        except (ValueError,TypeError) as exc:
            raise SignatureDenied('Invalid signature encoding') from exc
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            state=db.execute('SELECT state FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            if state!=('AWAITING_AUTHORITY',): raise SignatureDenied('Session unavailable')
            row=db.execute('SELECT sha256 FROM native_documents WHERE session_id=? AND document_id=?',(session_id,document_id)).fetchone()
            if not row: raise SignatureDenied('Document unavailable')
            digest=row[0]
            try:
                NativeDocuments(self.path,self.storage_dir).read(session_id,document_id)
            except DocumentDenied as exc:
                raise SignatureDenied('Stored document integrity failure') from exc
            try:
                Ed25519PublicKey.from_public_bytes(key).verify(sig,self.message(session_id,document_id,signer_id,digest))
            except (InvalidSignature,ValueError) as exc:
                raise SignatureDenied('Signature verification failed') from exc
            existing=db.execute('SELECT document_id,signer_id,document_digest,public_key,signature FROM native_document_signatures WHERE session_id=? AND signature_id=?',(session_id,signature_id)).fetchone()
            expected=(document_id,signer_id,digest,key,sig)
            if existing and existing!=expected: raise SignatureDenied('Conflicting signature identifier')
            if not existing:
                db.execute('INSERT INTO native_document_signatures VALUES (?,?,?,?,?,?,?,?)',
                    (session_id,signature_id,document_id,signer_id,digest,key,sig,int(time.time())))
        return {'session_id':session_id,'signature_id':signature_id,'document_sha256':digest,
                'cryptographic_signature_verified':True,'notarial_act_completed':False}
