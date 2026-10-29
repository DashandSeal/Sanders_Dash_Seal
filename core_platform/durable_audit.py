"""
Sanders Dash & Seal - persistent offline replay and audit store.

SQLite-backed development component. It provides atomic uniqueness and restart
persistence, NOT immutable evidence or production cryptographic attestation.
"""

from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class ReplayRejected(PermissionError):
    pass

class DurableAuditStore:
    def __init__(self, database_path: str | Path):
        self.path = str(database_path)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.execute("PRAGMA busy_timeout=5000;")
        self.connection.execute("PRAGMA synchronous=FULL;")
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                correlation_id TEXT NOT NULL UNIQUE,
                rtsa TEXT NOT NULL,
                event_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_utc TEXT NOT NULL
            )
            """
        )

    def close(self):
        self.connection.close()

    def preserve_once(self, correlation_id: str, rtsa: str, event: dict) -> dict:
        if not isinstance(correlation_id, str) or not correlation_id.strip():
            raise ValueError("CORRELATION_ID_REQUIRED")
        if not isinstance(rtsa, str) or not rtsa.strip():
            raise ValueError("RTSA_REQUIRED")
            
        payload = json.dumps(event, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False)
        try:
            self.connection.execute("BEGIN IMMEDIATE;")
            previous = self.connection.execute(
                "SELECT event_hash FROM receipts ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous[0] if previous else '0' * 64
            
            digest = hashlib.sha256(
                (previous_hash + correlation_id + rtsa + payload).encode('utf-8')
            ).hexdigest()
            
            cursor = self.connection.execute(
                """
                INSERT INTO receipts
                (correlation_id, rtsa, event_json, previous_hash, event_hash, created_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    correlation_id, rtsa, payload, previous_hash, digest,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            self.connection.execute("COMMIT")
            return {
                "sequence": cursor.lastrowid,
                "correlation_id": correlation_id,
                "event_hash": digest,
                "previous_hash": previous_hash
            }
        except sqlite3.IntegrityError as exc:
            self.connection.execute("ROLLBACK")
            raise ReplayRejected("CORRELATION_ID_ALREADY_USED") from exc
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def verify_chain(self) -> bool:
        previous_hash = '0' * 64
        rows = self.connection.execute(
            "SELECT correlation_id, rtsa, event_json, previous_hash, event_hash "
            "FROM receipts ORDER BY sequence"
        )
        for correlation_id, rtsa, payload, previous, digest in rows:
            if previous != previous_hash:
                return False
            expected = hashlib.sha256(
                (previous_hash + correlation_id + rtsa + payload).encode('utf-8')
            ).hexdigest()
            if expected != digest:
                return False
            previous_hash = digest
        return True
