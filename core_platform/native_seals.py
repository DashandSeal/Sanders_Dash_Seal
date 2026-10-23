"""Cryptographic electronic seal evidence for native notarial documents.

A valid signature proves possession of a key, not the signer's commission.
The key-to-commission binding must be established by independent verification.
"""
import base64
import re
import sqlite3
import time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

IDENT=re.compile(r'[A-Za-z0-9_.-]{1,128}\Z',re.ASCII)
class SealDenied(ValueError): pass

class NativeSeals:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_document_seals (
                session_id TEXT NOT NULL, document_id TEXT NOT NULL,
                seal_id TEXT NOT NULL, notary_id TEXT NOT NULL,
                document_sha256 TEXT NOT NULL, key_bytes BLOB NOT NULL,
                signature_bytes BLOB NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(session_id,seal_id))""")

    @staticmethod
    def message(session_id,document_id,notary_id,digest):
        return ('SDS-NATIVE-NOTARIAL-SEAL-V1\n'+session_id+'\n'+document_id+'\n'+notary_id+'\n'+digest).encode()

    def register(self,session_id,document_id,seal_id,notary_id,key_b64,signature_b64):
        if not all(isinstance(v,str) and IDENT.fullmatch(v) for v in (session_id,document_id,seal_id,notary_id)):
            raise SealDenied('Invalid seal identity')
        try:
            key=base64.b64decode(key_b64,validate=True)
            signature=base64.b64decode(signature_b64,validate=True)
            if len(key)!=32 or len(signature)!=64: raise ValueError('Invalid signature length')
        except (TypeError,ValueError) as exc: raise SealDenied('Invalid seal encoding') from exc
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            state=db.execute('SELECT state FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            if state!=('AWAITING_AUTHORITY',): raise SealDenied('Session unavailable')
            doc=db.execute('SELECT sha256 FROM native_documents WHERE session_id=? AND document_id=?',(session_id,document_id)).fetchone()
            if not doc: raise SealDenied('Document unavailable')
            digest=doc[0]
            try:
                Ed25519PublicKey.from_public_bytes(key).verify(signature,self.message(session_id,document_id,notary_id,digest))
            except (InvalidSignature,ValueError) as exc: raise SealDenied('Seal cryptographic verification failed') from exc
            expected=(document_id,notary_id,digest,key,signature)
            old=db.execute('SELECT document_id,notary_id,document_sha256,key_bytes,signature_bytes FROM native_document_seals WHERE session_id=? AND seal_id=?',(session_id,seal_id)).fetchone()
            if old and old!=expected: raise SealDenied('Conflicting seal identifier')
            if not old:
                db.execute('INSERT INTO native_document_seals VALUES (?,?,?,?,?,?,?,?)',
                    (session_id,document_id,seal_id,notary_id,digest,key,signature,int(time.time())))
        return {'session_id':session_id,'seal_id':seal_id,'cryptographic_seal_verified':True,'commission_verified':False}
