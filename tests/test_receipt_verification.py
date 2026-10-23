"""Real cryptographic receipt checks with disposable generated test keys."""
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core_platform.receipt_verification import (ReceiptSignatureVerifier,
    receipt_signing_material, verify_and_log_receipt)
from core_platform.pipeline_api import TransactionStore


class ReceiptVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'ledger.db'
        self.key = Ed25519PrivateKey.generate()
        self.verifier = ReceiptSignatureVerifier(self.key.public_key())

    def sign(self, transaction_id='txn-1', payload=b'test bytes', key=None):
        return base64.b64encode((key or self.key).sign(
            receipt_signing_material(transaction_id, payload))).decode()

    def record(self, transaction_id='txn-1', payload=b'test bytes', signature=None, **kwargs):
        return verify_and_log_receipt(self.path, transaction_id, payload,
            signature or self.sign(), verifier=self.verifier, **kwargs)

    def test_missing_independent_verifier_does_not_record(self):
        self.assertFalse(verify_and_log_receipt(self.path, 'txn-1', b'test bytes', self.sign()))
        self.assertFalse(self.path.exists())

    def test_real_signature_and_idempotent_receipt(self):
        self.assertTrue(self.record())
        self.assertTrue(self.record())
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT status,COUNT(*) FROM sds_ledger_receipts').fetchone(),
                             ('VERIFIED', 1))

    def test_signature_binds_payload_and_transaction_id(self):
        self.assertFalse(self.record(payload=b'changed'))
        self.assertFalse(self.record(transaction_id='txn-2'))
        self.assertFalse(self.path.exists())

    def test_forged_or_malformed_signature_does_not_record(self):
        self.assertFalse(self.record(signature=self.sign(key=Ed25519PrivateKey.generate())))
        self.assertFalse(self.record(signature='not a signature'))
        self.assertFalse(self.path.exists())

    def test_conflicting_signed_reuse_and_corrupted_ledger_detected(self):
        self.assertTrue(self.record())
        self.assertFalse(self.record(payload=b'other', signature=self.sign(payload=b'other')))
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE sds_ledger_receipts SET sha256_digest='changed'")
        self.assertFalse(self.record())

    def test_parallel_replays_record_only_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertTrue(all(pool.map(lambda _: self.record(), range(2))))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sds_ledger_receipts').fetchone()[0], 1)

    def test_processor_rollback_also_rolls_back_verified_ledger_receipt(self):
        self.assertTrue(self.record())
        store = TransactionStore(self.path)
        signature = self.sign('txn-2', b'atomic bytes')
        def processor(transaction, actor, connection):
            self.assertTrue(self.record('txn-2', b'atomic bytes', signature, connection=connection))
            raise RuntimeError('Deliberate rollback')
        with self.assertRaises(RuntimeError):
            store.process({'request_id': 'request-2'}, 'fixture-actor', processor)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sds_ledger_receipts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM pipeline_receipts').fetchone()[0], 0)

    def test_transaction_connection_is_required_for_atomic_integration(self):
        with sqlite3.connect(self.path) as db:
            self.assertFalse(self.record(connection=db))
