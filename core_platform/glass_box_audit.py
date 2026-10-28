"""Glass-Box Audit: separate evidence responsibility from Vault.

Local hash chaining is development storage, not production immutability.
"""
import json
import sqlite3
import time
from .security import canonical, digest, Denied

class GlassBoxAudit:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts (seq INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL, hash TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def preserve(self, event):
        """Chained evidence; no secrets or business document payloads are included."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT hash FROM receipts ORDER BY seq DESC LIMIT 1').fetchone()
            body = {'previous_hash': previous[0] if previous else '0' * 64,
                    'timestamp': self.clock(), 'event': event}
            encoded = canonical(body)
            block_hash = digest(encoded)
            db.execute('INSERT INTO receipts(body, hash) VALUES (?, ?)', (encoded.decode(), block_hash))
        return block_hash

    def verify_audit(self):
        previous = '0' * 64
        with self.connect() as db:
            rows = db.execute('SELECT body, hash FROM receipts ORDER BY seq').fetchall()
        for raw, block_hash in rows:
            body = json.loads(raw)
            if body.get('previous_hash') != previous or digest(canonical(body)) != block_hash:
                raise Denied('Audit chain changed')
            previous = block_hash
        return previous

    def preserve_execution(self, receipt):
        # The digest addresses the stored record; it cannot be included in its own preimage.
        block_hash = self.preserve({'stage': 'EXECUTION_RESULT', 'execution_receipt': receipt})
        return {**receipt, 'immutable_audit_trail': {
            'glass_box_block_id': 'GB-' + block_hash,
            'immutable_audit_hash': 'sha256:' + block_hash}}
