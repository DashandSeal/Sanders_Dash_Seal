"""Real signature + Function adapter + Python + SQLite tests, no OCI credentials."""
import base64
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core_platform.pipeline_api import TransactionStore, TransactionRejected
from core_platform.receipt_verification import ReceiptSignatureVerifier, receipt_signing_material
from core_platform.stream_api import create_stream_app, stream_signing_payload
from core_platform.deployment import create_application
from serverless.oci_pipeline import requests, stage_function, publish


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sds_function_integrated',
    ROOT / 'serverless/sds-transaction-validator-fn/integrated.py')
integrated = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrated)


class StreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.store = TransactionStore(self.directory / 'ledger.db')
        with self.store.connect() as db:
            db.execute('CREATE TABLE business(value TEXT)')
        self.key = Ed25519PrivateKey.generate()  # Ephemeral fixture only.
        self.state = {'release': True, 'fail': False, 'calls': 0}
        self.verifiers = {'test-owner': ReceiptSignatureVerifier(self.key.public_key())}
        def processor(transaction, actor, db):
            self.assertEqual(actor, 'test-owner')
            self.state['calls'] += 1
            db.execute('INSERT INTO business VALUES (?)', (transaction['value'],))
            if self.state['fail']:
                raise TransactionRejected('Private failure detail')
            return {'recorded': True}
        self.app = create_stream_app(processor, lambda: self.state['release'],
                                     self.store, self.verifiers)

    def event(self, request_id='event1', value='signed business record'):
        event = {'actor': 'test-owner', 'transaction_id': request_id,
                 'transaction': {'request_id': request_id, 'value': value}, 'signature': ''}
        event['signature'] = base64.b64encode(self.key.sign(receipt_signing_material(
            request_id, stream_signing_payload(event)))).decode()
        return event

    def call(self, event, *, raw=None, method='POST', app=None, host='sandersdashandseal.com'):
        raw = json.dumps(event).encode() if raw is None else raw
        env = {'REQUEST_METHOD': method, 'PATH_INFO': '/api/stream/transactions',
            'HTTP_HOST': host, 'CONTENT_TYPE': 'application/json',
            'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        result = {}
        def start(status, headers):
            result['status'] = int(status.split()[0])
        result['body'] = json.loads(b''.join((app or self.app)(env, start)))
        return result

    def send(self, event, endpoint, timeout):
        result = self.call(event)
        if result['status'] != 200:
            raise integrated.BatchRejected('Commit denied')
        return result['body']

    def batch(self, *events):
        return json.dumps([{'value': base64.b64encode(json.dumps(event).encode()).decode(),
                            'offset': index, 'partition': '0'}
                           for index, event in enumerate(events)]).encode()

    def test_function_to_python_commits_business_signature_and_stable_receipt(self):
        raw = self.batch(self.event())
        first = integrated.process_batch(raw, 'fixture', send=self.send)
        self.assertEqual(first, integrated.process_batch(raw, 'fixture', send=self.send))
        self.assertEqual(first[0]['status'], 'COMMITTED')
        self.assertEqual(self.state['calls'], 1)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM business').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT status FROM sds_ledger_receipts').fetchone()[0], 'VERIFIED')

    def test_conflicting_signed_retry_cannot_replace_ledger(self):
        first = self.call(self.event())
        self.assertEqual(first['status'], 200)
        self.assertEqual(self.call(self.event(value='changed'))['status'], 409)
        self.assertEqual(self.call(self.event()), first)
        self.assertEqual(self.state['calls'], 1)

    def test_unsigned_missing_and_wrong_actor_key_are_rejected(self):
        for alteration in ({'signature': 'UNSIGNED'}, {'signature': ''}, {'actor': 'unknown'},
                           {'actor': 'someone-else'}):
            self.assertEqual(self.call(dict(self.event(), **alteration))['status'], 401)
        event = self.event()
        del event['transaction_id']
        self.assertEqual(self.call(event)['status'], 400)
        self.assertEqual(self.state['calls'], 0)

    def test_tampered_payload_and_invalid_signature_on_replay_denied(self):
        event = self.event()
        self.call(event)
        event['signature'] = 'UNSIGNED'
        self.assertEqual(self.call(event)['status'], 401)
        event = self.event()
        event['transaction']['value'] = 'tampered'
        self.assertEqual(self.call(event)['status'], 401)

    def test_release_or_key_revocation_denies_even_existing_receipt(self):
        event = self.event()
        self.call(event)
        self.state['release'] = False
        self.assertEqual(self.call(event)['status'], 503)
        self.state['release'] = True
        self.verifiers.clear()
        self.assertEqual(self.call(event)['status'], 503)

    def test_processor_failure_rolls_back_business_and_signed_receipt(self):
        self.state['fail'] = True
        result = self.call(self.event())
        self.assertEqual(result['status'], 409)
        self.assertNotIn('Private failure', str(result))
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM business').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM pipeline_receipts').fetchone()[0], 0)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='sds_ledger_receipts'").fetchone())

    def test_partial_batch_retry_does_not_repeat_already_committed_business(self):
        events = self.event('one'), self.event('two')
        count = 0
        def interrupted(event, endpoint, timeout):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('Simulated transport loss')
            return self.send(event, endpoint, timeout)
        with self.assertRaises(OSError):
            integrated.process_batch(self.batch(*events), 'fixture', send=interrupted)
        receipts = integrated.process_batch(self.batch(*events), 'fixture', send=self.send)
        self.assertEqual(len(receipts), 2)
        self.assertEqual(self.state['calls'], 2)

    def test_concurrent_identical_deliveries_commit_once(self):
        event = self.event()
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(self.call, [event, event]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['status'], 200)
        self.assertEqual(self.state['calls'], 1)

    def test_registered_actor_with_wrong_key_is_denied(self):
        self.verifiers['test-owner'] = ReceiptSignatureVerifier(Ed25519PrivateKey.generate().public_key())
        self.assertEqual(self.call(self.event())['status'], 401)
        self.assertEqual(self.state['calls'], 0)

    def test_expired_batch_budget_stops_before_commit(self):
        clock = iter([0, 25])
        with self.assertRaises(integrated.BatchRejected):
            integrated.process_batch(self.batch(self.event()), 'fixture',
                                     send=self.send, clock=lambda: next(clock))
        self.assertEqual(self.state['calls'], 0)

    def test_known_actor_cannot_claim_another_actors_transaction_id(self):
        self.call(self.event())
        other_key = Ed25519PrivateKey.generate()
        self.verifiers['other-owner'] = ReceiptSignatureVerifier(other_key.public_key())
        event = self.event()
        event['actor'] = 'other-owner'
        event['signature'] = base64.b64encode(other_key.sign(receipt_signing_material(
            event['transaction_id'], stream_signing_payload(event)))).decode()
        self.assertEqual(self.call(event)['status'], 409)
        self.assertEqual(self.state['calls'], 1)

    def test_duplicate_json_keys_and_nonfinite_input_denied(self):
        for raw in (b'{"actor":"a","actor":"b"}', b'{"value":NaN}'):
            self.assertEqual(self.call(None, raw=raw)['status'], 400)
            with self.assertRaises(ValueError):
                integrated.process_batch(raw, 'fixture', send=self.send)

    def test_bad_transport_batch_rejected_before_any_commit(self):
        bad = json.loads(self.batch(self.event())) + [{'value': 'not-base64'}]
        for raw in (b'[]', b'{}', json.dumps(bad).encode(), b'x' * 1048577):
            with self.assertRaises(ValueError):
                integrated.process_batch(raw, 'fixture', send=self.send)
        self.assertEqual(self.state['calls'], 0)

    def test_default_application_recognizes_route_but_denies_without_bindings(self):
        for host in ('wsgi-backend:8000', 'sandersdashandseal.com'):
            self.assertEqual(self.call(self.event(), app=create_application(), host=host)['status'], 503)

    def test_signed_stream_namespace_does_not_reuse_node_receipt(self):
        self.store.process(self.event()['transaction'], 'test-owner', lambda tx, actor, db: {'other': True})
        self.assertEqual(self.call(self.event())['status'], 200)
        self.assertEqual(self.state['calls'], 1)

    def test_rendered_connector_includes_function_task_storage_and_cursor(self):
        result = requests('ocid1.tenancy.oc1.test', 'ocid1.streampool.oc1.test',
            'ocid1.stream.oc1.test', 'ocid1.fnfunc.oc1.test', 'test_namespace')
        connector = result['connector.json']
        self.assertEqual(connector['source']['cursor']['kind'], 'TRIM_HORIZON')
        self.assertEqual(connector['tasks'][0]['kind'], 'function')
        self.assertEqual(connector['target']['kind'], 'objectStorage')
        self.assertEqual(connector['target']['objectNamePrefix'], 'stream_receipts/')
        self.assertNotIn('compartmentId', result['stream.json'])

    def test_staging_uses_integrated_entrypoint_and_never_overwrites(self):
        destination = self.directory / 'function'
        stage_function(destination)
        self.assertIn('integrated.py handler', (destination / 'func.yaml').read_text())
        self.assertFalse((destination / 'func.py').exists())
        with self.assertRaises(FileExistsError):
            stage_function(destination)

    def test_producer_checks_admission_failures_and_cleans_private_file(self):
        captured = []
        def runner(command, **kwargs):
            path = Path(command[command.index('--messages') + 1][7:])
            captured.append(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            event = json.loads(base64.b64decode(json.loads(path.read_text())[0]['value']))
            self.assertEqual(event, self.event())
            self.assertIn('instance_principal', command)
            return subprocess.CompletedProcess(command, 0,
                stdout=json.dumps({'data': {'failures': 1, 'entries': [{'error': 'Throttled'}]}}))
        with self.assertRaises(ValueError):
            publish(self.event(), 'ocid1.stream.oc1.test',
                'https://cell-1.streaming.us-phoenix-1.oci.oraclecloud.com', runner=runner)
        self.assertFalse(captured[0].exists())

    def test_producer_admission_is_not_a_committed_receipt(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 0,
                stdout=json.dumps({'data': {'failures': 0, 'entries': [{'offset': 0}]}}))
        result = publish(self.event(), 'ocid1.stream.oc1.test',
            'https://cell-1.streaming.us-phoenix-1.oci.oraclecloud.com', runner=runner)
        self.assertEqual(result['status'], 'STREAM_ADMITTED')
        self.assertEqual(self.state['calls'], 0)

    def test_insecure_or_redirecting_backend_endpoints_denied(self):
        for endpoint in ('http://example.com/api/stream/transactions',
                         'https://name:password@example.com/api/stream/transactions',
                         'https://example.com/wrong', 'https://example.com/api/stream/transactions?x=1'):
            with self.assertRaises(ValueError):
                integrated.dispatch(self.event(), endpoint, 1)
        with self.assertRaises(ValueError):
            integrated.NoRedirect().redirect_request(None, None, 302, None, None, 'http://other')

    def test_function_failure_is_503_without_private_error_details(self):
        class Response:
            def __init__(self, ctx, **kwargs):
                self.values = kwargs
        fake = types.ModuleType('fdk')
        fake.response = types.SimpleNamespace(Response=Response)
        with patch.dict('sys.modules', {'fdk': fake}):
            result = integrated.handler(None, io.BytesIO(b'{}'))
        self.assertEqual(result.values['status_code'], 503)
        self.assertEqual(result.values['response_data'], '{"error":"stream_batch_not_committed"}')
