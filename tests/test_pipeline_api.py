"""Owner-stack Python contracts with disposable authority, never live credentials."""
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from core_platform.pipeline_api import create_pipeline_app, TransactionStore, TransactionRejected


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'transactions.db'
        self.store = TransactionStore(self.path)
        self.state = {'release': True, 'session': True, 'calls': 0}
        def authenticate(env):
            return ('owner-test' if self.state['session'] and
                    env.get('HTTP_AUTHORIZATION') == 'Bearer test-only' else None)
        self.authenticate = authenticate
        def processor(transaction, actor, db):
            self.state['calls'] += 1
            if transaction.get('action') != 'test_record':
                raise TransactionRejected('Unsupported operation')
            db.execute('CREATE TABLE IF NOT EXISTS fixture_business(value TEXT)')
            db.execute('INSERT INTO fixture_business VALUES (?)', (transaction['value'],))
            return {'recorded': True}
        self.processor = processor
        self.app = create_pipeline_app(authenticate, processor,
            lambda: self.state['release'], self.store)

    def call(self, path, data=None, *, authorization='Bearer test-only', app=None):
        raw = json.dumps(data).encode() if data is not None else b''
        env = {'PATH_INFO': path, 'REQUEST_METHOD': 'POST',
            'HTTP_AUTHORIZATION': authorization, 'CONTENT_TYPE': 'application/json',
            'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        result = {}
        def start(status, headers):
            result.update(status=int(status.split()[0]), headers=dict(headers))
        result['body'] = json.loads(b''.join((app or self.app)(env, start)))
        return result

    def envelope(self, **change):
        transaction = {'request_id': 'r1', 'action': 'test_record', 'value': 'test'}
        transaction.update(change)
        return {'transaction': transaction, 'session': {'authorization': 'Bearer test-only'}}

    def test_default_denies_both_operations(self):
        app = create_pipeline_app()
        for path in ('/api/auth/verify', '/api/transactions/process'):
            self.assertEqual(self.call(path, self.envelope(), app=app)['status'], 503)

    def test_session_verification_checks_real_adapter(self):
        self.assertEqual(self.call('/api/auth/verify')['body'], {'authorization': 'Bearer test-only'})
        self.assertEqual(self.call('/api/auth/verify', authorization='forged')['status'], 401)

    def test_receipt_commit_and_idempotency_survive_store_restart(self):
        first = self.call('/api/transactions/process', self.envelope())
        self.assertEqual(first['status'], 200)
        self.assertEqual(first['body']['request_id'], 'r1')
        self.app = create_pipeline_app(self.authenticate, self.processor,
            lambda: True, TransactionStore(self.path))
        self.assertEqual(self.call('/api/transactions/process', self.envelope()), first)
        self.assertEqual(self.state['calls'], 1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fixture_business').fetchone()[0], 1)

    def test_conflicting_retry_is_rejected(self):
        self.call('/api/transactions/process', self.envelope())
        self.assertEqual(self.call('/api/transactions/process', self.envelope(value='different'))['status'], 422)
        self.assertEqual(self.state['calls'], 1)

    def test_session_is_reauthenticated_and_never_a_claimed_identity(self):
        self.state['session'] = False
        self.assertEqual(self.call('/api/transactions/process', self.envelope())['status'], 401)
        data = self.envelope()
        data['session'] = {'actor': 'owner-test', 'role': 'admin'}
        self.assertEqual(self.call('/api/transactions/process', data)['status'], 400)
        self.assertEqual(self.state['calls'], 0)

    def test_release_revocation_and_missing_processor_deny(self):
        self.state['release'] = False
        self.assertEqual(self.call('/api/auth/verify')['status'], 503)
        self.assertEqual(self.call('/api/transactions/process', self.envelope())['status'], 503)
        app = create_pipeline_app(self.authenticate, release_verifier=lambda: True)
        self.assertEqual(self.call('/api/transactions/process', self.envelope(), app=app)['status'], 503)

    def test_processor_exception_rolls_back_business_and_receipt(self):
        with self.store.connect() as db:
            db.execute('CREATE TABLE fixture_business(value TEXT)')
        def fail(transaction, actor, db):
            db.execute('INSERT INTO fixture_business VALUES (?)', ('rollback',))
            raise RuntimeError('Private backend detail')
        app = create_pipeline_app(self.authenticate, fail, lambda: True, self.store)
        result = self.call('/api/transactions/process', self.envelope(), app=app)
        self.assertEqual(result['status'], 503)
        self.assertNotIn('Private', str(result))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fixture_business').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM pipeline_receipts').fetchone()[0], 0)

    def test_envelope_and_operation_validation(self):
        for envelope in (None, [], {'transaction': {}}, self.envelope(action='notarial_act'),
                         self.envelope(request_id='invalid request id')):
            self.assertIn(self.call('/api/transactions/process', envelope)['status'], (400, 422))
