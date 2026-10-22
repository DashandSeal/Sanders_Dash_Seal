"""Python authority and durable receipts for the owner-selected Node transport.

Connecting code: adapters are independent production authority, not identities
claimed by Node. A processor validates its operation and writes business state
using the supplied SQLite connection. No generic payload grants notarial power.
"""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid


IDENT = re.compile(r'[A-Za-z0-9_.-]{1,128}', re.ASCII)


class TransactionRejected(ValueError):
    pass


class TransactionStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS pipeline_receipts (
                actor TEXT NOT NULL, request_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, receipt TEXT NOT NULL,
                PRIMARY KEY(actor, request_id))''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def process(self, transaction, actor, processor):
        if (not isinstance(transaction, dict)
                or not isinstance(transaction.get('request_id'), str)
                or not IDENT.fullmatch(transaction['request_id'])):
            raise TransactionRejected('request_id required')
        canonical = json.dumps(transaction, sort_keys=True, separators=(',', ':'), allow_nan=False)
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT fingerprint,receipt FROM pipeline_receipts '
                'WHERE actor=? AND request_id=?', (actor, transaction['request_id'])).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise TransactionRejected('Conflicting request reuse')
                return json.loads(previous[1])
            # Business validation, human authority and auditing remain obligations
            # of the trusted processor. External irreversible effects require an
            # outbox/idempotent dispatcher, not a network call inside this commit.
            result = processor(transaction, actor, db)
            if not isinstance(result, dict):
                raise TransactionRejected('Processor must provide a validated result')
            receipt = {'receipt_id': uuid.uuid4().hex,
                'request_id': transaction['request_id'], 'recorded_at': int(time.time()),
                'result': result}
            encoded = json.dumps(receipt, separators=(',', ':'), allow_nan=False)
            if len(encoded.encode()) > 65536:
                raise TransactionRejected('Receipt too large')
            db.execute('INSERT INTO pipeline_receipts VALUES (?,?,?,?)',
                (actor, transaction['request_id'], fingerprint, encoded))
        return receipt


def create_pipeline_app(authenticate=None, processor=None, release_verifier=None, store=None):
    def app(env, start):
        def respond(status, payload):
            raw = json.dumps(payload, separators=(',', ':')).encode()
            start(status, [('Content-Type', 'application/json'),
                ('Content-Length', str(len(raw))), ('Cache-Control', 'no-store')])
            return [raw]
        try:
            ready = (callable(authenticate) and callable(release_verifier)
                     and release_verifier() is True)
        except Exception:
            ready = False
        if not ready:
            return respond('503 Service Unavailable', {'error': 'authority_unavailable'})
        if env.get('REQUEST_METHOD') != 'POST':
            return respond('405 Method Not Allowed', {'error': 'post_required'})
        path = env.get('PATH_INFO')
        if path not in ('/api/auth/verify', '/api/transactions/process'):
            return respond('404 Not Found', {'error': 'not_found'})
        data = None
        authorization = env.get('HTTP_AUTHORIZATION')
        if path == '/api/transactions/process':
            if processor is None or store is None:
                return respond('503 Service Unavailable', {'error': 'processor_unavailable'})
            if env.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
                return respond('415 Unsupported Media Type', {'error': 'json_required'})
            try:
                length = int(env.get('CONTENT_LENGTH', '0'))
                if not 0 < length <= 1048576:
                    raise ValueError('length')
                raw = env['wsgi.input'].read(length)
                if len(raw) != length:
                    raise ValueError('short body')
                def invalid_constant(value):
                    raise ValueError('Nonfinite JSON')
                data = json.loads(raw, parse_constant=invalid_constant)
                if not isinstance(data, dict) or set(data) != {'transaction', 'session'}:
                    raise ValueError('envelope')
                session = data['session']
                if not isinstance(session, dict) or set(session) != {'authorization'}:
                    raise ValueError('session')
                authorization = session['authorization']
            except (ValueError, TypeError, KeyError, UnicodeError):
                return respond('400 Bad Request', {'error': 'invalid_request'})
        if (not isinstance(authorization, str) or not 1 <= len(authorization) <= 4096
                or any(ord(c) < 32 or ord(c) > 126 for c in authorization)):
            return respond('401 Unauthorized', {'error': 'session_unavailable'})
        # Reconstruct credentials only, never accept a forwarded actor/role.
        authentication_env = dict(env, HTTP_AUTHORIZATION=authorization)
        for key in ('HTTP_COOKIE', 'HTTP_X_USER', 'HTTP_X_ROLE', 'HTTP_X_FORWARDED_USER'):
            authentication_env.pop(key, None)
        try:
            actor = authenticate(authentication_env)
        except Exception:
            actor = None
        if not isinstance(actor, str) or not IDENT.fullmatch(actor):
            return respond('401 Unauthorized', {'error': 'session_unavailable'})
        if path == '/api/auth/verify':
            # Internal response to Node only; no invented session issuer. Every
            # submission revalidates the original credential independently.
            return respond('200 OK', {'authorization': authorization})
        try:
            receipt = store.process(data['transaction'], actor, processor)
            return respond('200 OK', receipt)
        except (TransactionRejected, ValueError, TypeError):
            return respond('422 Unprocessable Entity', {'error': 'transaction_rejected'})
        except Exception:
            return respond('503 Service Unavailable', {'error': 'transaction_unavailable'})
    return app
