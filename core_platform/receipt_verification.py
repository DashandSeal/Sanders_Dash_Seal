"""Verified Ed25519 consumer receipts; hashing alone never grants VERIFIED status."""
import base64
import binascii
import hashlib
import json
import re
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def receipt_signing_material(transaction_id, payload_bytes):
    return json.dumps({'domain': 'SDS_LEDGER_RECEIPT_V1',
        'transaction_id': transaction_id,
        'sha256_digest': hashlib.sha256(payload_bytes).hexdigest()},
        sort_keys=True, separators=(',', ':')).encode()


class ReceiptSignatureVerifier:
    """The caller installs a trusted consumer public key, never a payload key."""
    def __init__(self, public_key):
        if not isinstance(public_key, Ed25519PublicKey):
            raise TypeError('Independent Ed25519 public key required')
        self.public_key = public_key

    def verify(self, transaction_id, payload_bytes, signature):
        try:
            raw = base64.b64decode(signature, validate=True)
            self.public_key.verify(raw, receipt_signing_material(transaction_id, payload_bytes))
            return True
        except (InvalidSignature, ValueError, TypeError, binascii.Error):
            return False


def verify_and_log_receipt(db_path, transaction_id, payload_bytes, consumer_signature,
                           *, verifier=None, connection=None):
    """Owner function interface plus independent verification and optional atomic connection.

    A supplied connection must be in the processor's existing transaction. The
    function does not commit/close that connection. A False result requires the
    caller to reject/roll back its operation. No signing secret is created here.
    """
    if (not isinstance(transaction_id, str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', transaction_id)
            or not isinstance(payload_bytes, bytes) or len(payload_bytes) > 1048576
            or not isinstance(consumer_signature, str)
            or len(consumer_signature) > 256
            or not isinstance(verifier, ReceiptSignatureVerifier)
            or verifier.verify(transaction_id, payload_bytes, consumer_signature) is not True):
        return False
    calculated_digest = hashlib.sha256(payload_bytes).hexdigest()

    def record(db):
        db.execute('''CREATE TABLE IF NOT EXISTS sds_ledger_receipts (
            transaction_id TEXT PRIMARY KEY, sha256_digest TEXT NOT NULL,
            operational_signature TEXT NOT NULL, status TEXT NOT NULL,
            recorded_at TEXT NOT NULL)''')
        rows = db.execute('SELECT sha256_digest,operational_signature,status FROM '
                          'sds_ledger_receipts WHERE transaction_id=?', (transaction_id,)).fetchall()
        if rows:
            return len(rows) == 1 and tuple(rows[0]) == (calculated_digest, consumer_signature, 'VERIFIED')
        db.execute('''INSERT INTO sds_ledger_receipts
            (transaction_id,sha256_digest,operational_signature,status,recorded_at)
            VALUES (?,?,?,?,datetime('now','utc'))''',
            (transaction_id, calculated_digest, consumer_signature, 'VERIFIED'))
        return True

    try:
        if connection is not None:
            if not isinstance(connection, sqlite3.Connection) or not connection.in_transaction:
                return False
            return record(connection)
        with sqlite3.connect(db_path, timeout=5) as database:
            database.execute('BEGIN IMMEDIATE')
            return record(database)
    except sqlite3.Error:
        return False
