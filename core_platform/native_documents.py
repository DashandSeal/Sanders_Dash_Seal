"""
Module: core_platform.native_documents
Architectural Layer: Secure Bounded Document Custody Vault
Description: Handles immutable, sandboxed document storage for Sanders Dash & Seal.
             Provides cryptographic SHA256 content deduplication, atomic writes,
             and explicit boundary isolation inside your Oracle block volumes.
"""

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import tempfile
import time

IDENT = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
MAX_DOCUMENT = 20 * 1024 * 1024  # 20 MB Hard Boundary Limit

class DocumentDenied(ValueError):
    pass

class NativeDocuments:
    """Secure atomic document repository providing absolute file boundary sandboxing."""

    def __init__(self, db_path, storage_dir):
        self.db_path = str(db_path)
        self.storage_dir = pathlib.Path(storage_dir).resolve()

        # Enforce highly restricted local folder access metrics natively
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.storage_dir, 0o0700)

        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_documents (
                session_id TEXT NOT NULL, document_id TEXT NOT NULL,
                sha256 TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(session_id, document_id)
            );""")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row
        return db

    def _calculate_filename(self, session_id, document_id):
        """Constructs safe, absolute deterministic path targets to isolate from traversal risks."""
        # Use proper explicit byte combination instead of broken string null tokens
        combined = f"{session_id}:{document_id}".encode("utf-8")
        secure_hash = hashlib.sha256(combined).hexdigest()

        target_path = (self.storage_dir / secure_hash).resolve()
        # Enforce that the calculated absolute file destination resides strictly within the vault folder boundaries
        if not str(target_path).startswith(str(self.storage_dir)):
            raise DocumentDenied('Unauthorized directory traversal vector detected')
        return target_path

    def put(self, session_id, document_id, content):
        if not all(isinstance(v, str) and IDENT.fullmatch(v) for v in (session_id, document_id)):
            raise DocumentDenied('Invalid document tracking identities')
        if not isinstance(content, bytes) or not 0 < len(content) <= MAX_DOCUMENT:
            raise DocumentDenied('Invalid document size or empty payload content')

        digest = hashlib.sha256(content).hexdigest()
        filename = self._calculate_filename(session_id, document_id)

        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")

            # Check the parental notarial session baseline states safely
            session = db.execute("SELECT 1 FROM native_notarial_sessions WHERE session_id = ?;", (session_id,)).fetchone()
            if not session:
                raise DocumentDenied('Associated notarial session identifier not found or inactive')

            existing = db.execute("SELECT sha256, size FROM native_documents WHERE session_id = ? AND document_id = ?;",
                                  (session_id, document_id)).fetchone()
            if existing:
                if existing['sha256'] != digest or existing['size'] != len(content):
                    raise DocumentDenied('Conflicting or missing document footprint correlation detected')
                if filename.exists():
                    db.rollback()
                    return {'session_id': session_id, 'document_id': document_id, 'sha256': digest, 'status': 'EXISTS'}

            # Execute safe enterprise atomic file streams
            fd, tmp_path_str = tempfile.mkstemp(dir=str(self.storage_dir), prefix="tmp_sdm_")
            tmp_path = pathlib.Path(tmp_path_str)
            try:
                with os.fdopen(fd, "wb") as out:
                    os.fchmod(out.fileno(), 0o0600)
                    out.write(content)
                    out.flush()
                    os.fsync(out.fileno())

                # Atomic Hotswap via filesystem rename
                tmp_path.replace(filename)
                db.execute("INSERT OR REPLACE INTO native_documents VALUES (?, ?, ?, ?, ?);",
                           (session_id, document_id, digest, len(content), int(time.time())))
                db.commit()
            except Exception as exc:
                if tmp_path.exists():
                    tmp_path.unlink()
                raise DocumentDenied('Vault atomic write synchronization failure') from exc

        return {'session_id': session_id, 'document_id': document_id, 'sha256': digest, 'status': 'STORED'}

    def read(self, session_id, document_id):
        if not all(isinstance(v, str) and IDENT.fullmatch(v) for v in (session_id, document_id)):
            raise DocumentDenied('Invalid document tracking identities')

        with self._connect() as db:
            row = db.execute("SELECT sha256, size FROM native_documents WHERE session_id = ? AND document_id = ?;",
                             (session_id, document_id)).fetchone()
            if not row:
                raise DocumentDenied('Document record not found inside database index')

        filename = self._calculate_filename(session_id, document_id)
        try:
            content = filename.read_bytes()
            if len(content) != row['size'] or hashlib.sha256(content).hexdigest() != row['sha256']:
                raise DocumentDenied('Document integrity validation failure: file payload corrupted')
            return content
        except OSError as exc:
            raise DocumentDenied('Physical document file unavailable on persistent storage volume') from exc
