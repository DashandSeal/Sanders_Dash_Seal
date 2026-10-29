"""
Module: core_platform.glass_box_audit
Architectural Layer: Immutable Tamper-Evident Ledger Audit Core
Description: Glass-Box Audit trail system. Implements local cryptographic hash-chaining
over system receipts to ensure append-only transactional integrity.
"""

import json
import sqlite3
import time
from security import digest, Denied

class GlassBoxAudit:
    """Glass-Box Audit engine: handles separate evidence accountability tracking."""

    def __init__(self, db_path, clock=time.time):
        self.path = str(db_path)
        self.clock = clock
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                body TEXT NOT NULL,
                hash TEXT NOT NULL
            );""")

    def _connect(self):
        """Enforce strict transaction insulation boundaries."""
        return sqlite3.connect(self.path, timeout=10, isolation_level='IMMEDIATE')

    def preserve(self, event, **kwargs):
        """Chained evidence; no secrets or payment payloads are stored here."""
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            
            # Fetch the previous block's hash link to build the immutable blockchain
            row = db.execute("SELECT hash FROM receipts ORDER BY seq DESC LIMIT 1;").fetchone()
            previous_hash = row[0] if row else '0' * 64

            payload = {
                'previous_hash': previous_hash,
                'timestamp': self.clock(),
                'event': event,
                'context': kwargs
            }

            # Create a deterministic, sorted canonical text format for hashing
            encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            block_hash = digest(encoded)

            db.execute("INSERT INTO receipts (body, hash) VALUES (?, ?);", (encoded, block_hash))
            db.commit()
            return block_hash

    def verify_audit(self):
        """Verifies the complete integrity of the cryptographic chain layout."""
        previous = '0' * 64
        with self._connect() as db:
            cursor = db.execute("SELECT body, hash FROM receipts ORDER BY seq ASC;")
            rows = cursor.fetchall()

            for row in rows:
                raw_body = row[0]
                stored_hash = row[1]

                body = json.loads(raw_body)

                # Verify backward hash pointer matches previous link
                if body.get('previous_hash') != previous:
                    raise Denied('Audit chain changed: linked hash mismatch')

                # Re-verify deterministic block footprint calculation match
                calculated_body_str = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                if digest(calculated_body_str) != stored_hash:
                    raise Denied('Audit chain changed: block footprint calculation mismatch')

                previous = stored_hash

        return previous

    def preserve_execution(self, event, receipt):
        """Advisory wrapper targeting stored transaction result tracking frames."""
        block_hash = self.preserve(event, target_stage='EXECUTION_RESULT')
        return {
            'receipt': receipt,
            'immutable_audit_trail': {
                'glass_box_id': f'GB-{block_hash[:8].upper()}',
                'immutable_audit_hash': f'sha256:{block_hash}'
            }
        }
