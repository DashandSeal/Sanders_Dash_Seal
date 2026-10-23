"""Native session authority evidence registry.

This registry preserves externally verified decisions but does not itself
perform identity proofing, check commission status, or confer legal authority.
"""
import json
import re
import sqlite3
import time

ID=re.compile(r'[A-Za-z0-9_.-]{1,128}\Z',re.ASCII)
KINDS=frozenset(('IDENTITY','COMMISSION','JURISDICTION','METHOD','HUMAN_ATTESTATION','RON_PROVIDER_AUTHORIZATION'))
class AuthorityDenied(ValueError):pass

class NativeAuthority:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_authority_decisions (
                session_id TEXT NOT NULL, kind TEXT NOT NULL,
                evidence_id TEXT NOT NULL, verifier_id TEXT NOT NULL,
                verified_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                PRIMARY KEY(session_id,kind))""")

    def register(self,session_id,kind,evidence_id,verifier_id,verified_at,expires_at,*,trusted_verifier=None):
        if not all(isinstance(v,str) and ID.fullmatch(v) for v in (session_id,evidence_id,verifier_id)):
            raise AuthorityDenied('Invalid authority identity')
        if kind not in KINDS or type(verified_at)!=int or type(expires_at)!=int or not 0<verified_at<expires_at:
            raise AuthorityDenied('Invalid authority record')
        if expires_at<=int(time.time()):raise AuthorityDenied('Expired verification')
        if not callable(trusted_verifier) or trusted_verifier(session_id,kind,evidence_id,verifier_id,verified_at,expires_at) is not True:
            raise AuthorityDenied('Independent authority verification unavailable')
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            state=db.execute('SELECT state FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            if state!=('AWAITING_AUTHORITY',):raise AuthorityDenied('Session unavailable')
            existing=db.execute('SELECT evidence_id,verifier_id,verified_at,expires_at FROM native_authority_decisions WHERE session_id=? AND kind=?',(session_id,kind)).fetchone()
            expected=(evidence_id,verifier_id,verified_at,expires_at)
            if existing and existing!=expected:raise AuthorityDenied('Conflicting authority decision')
            if not existing:db.execute('INSERT INTO native_authority_decisions VALUES (?,?,?,?,?,?)',(session_id,kind,*expected))
        return {'session_id':session_id,'kind':kind,'evidence_id':evidence_id,'independently_verified':True}

    def missing(self,session_id):
        with sqlite3.connect(self.path) as db:
            method=db.execute('SELECT method FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            if not method:raise AuthorityDenied('Unknown session')
            rows=db.execute('SELECT kind,expires_at FROM native_authority_decisions WHERE session_id=?',(session_id,)).fetchall()
        valid={kind for kind,expiry in rows if expiry>int(time.time())}
        required=set(KINDS)-({'RON_PROVIDER_AUTHORIZATION'} if method[0]=='E_NOTARY' else set())
        return sorted(required-valid)
