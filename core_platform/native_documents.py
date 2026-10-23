"""Native document custody for Sanders Dash & Seal; not a notarization or e-signature."""
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time

IDENT = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z', re.ASCII)
MAX_DOCUMENT = 20 * 1024 * 1024

class DocumentDenied(ValueError):
    pass

class NativeDocuments:
    def __init__(self, db_path, storage_dir):
        self.db_path = str(db_path)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.storage_dir, 0o700)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS native_documents (
                session_id TEXT NOT NULL, document_id TEXT NOT NULL,
                sha256 TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(session_id,document_id))''')

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.execute('PRAGMA busy_timeout=10000')
        return db

    def put(self, session_id, document_id, content):
        if not all(isinstance(v, str) and IDENT.fullmatch(v) for v in (session_id,document_id)):
            raise DocumentDenied('Invalid document identity')
        if not isinstance(content, bytes) or not 0 < len(content) <= MAX_DOCUMENT:
            raise DocumentDenied('Invalid document size or content')
        digest = hashlib.sha256(content).hexdigest()
        filename = self.storage_dir / (hashlib.sha256((session_id+'\0'+document_id).encode()).hexdigest()+'.bin')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            session = db.execute('SELECT state FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            if not session or session[0] != 'AWAITING_AUTHORITY':
                raise DocumentDenied('Session cannot accept documents')
            existing = db.execute('SELECT sha256,size FROM native_documents WHERE session_id=? AND document_id=?',(session_id,document_id)).fetchone()
            if existing:
                if existing != (digest,len(content)) or not filename.is_file() or hashlib.sha256(filename.read_bytes()).hexdigest()!=digest:
                    raise DocumentDenied('Conflicting or missing document')
                return {'session_id':session_id,'document_id':document_id,'sha256':digest,'size':len(content)}
            fd, tmp = tempfile.mkstemp(dir=self.storage_dir, prefix='.pending-')
            try:
                with os.fdopen(fd,'wb') as out:
                    os.fchmod(out.fileno(),0o600)
                    out.write(content)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp,filename)
                db.execute('INSERT INTO native_documents VALUES (?,?,?,?,?)',(session_id,document_id,digest,len(content),int(time.time())))
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
        return {'session_id':session_id,'document_id':document_id,'sha256':digest,'size':len(content)}

    def read(self, session_id, document_id):
        if not all(isinstance(v,str) and IDENT.fullmatch(v) for v in (session_id,document_id)):
            raise DocumentDenied('Invalid document identity')
        with self._connect() as db:
            row = db.execute('SELECT sha256,size FROM native_documents WHERE session_id=? AND document_id=?',(session_id,document_id)).fetchone()
        if not row: raise DocumentDenied('Unknown document')
        filename = self.storage_dir / (hashlib.sha256((session_id+'\0'+document_id).encode()).hexdigest()+'.bin')
        try: content=filename.read_bytes()
        except OSError as exc: raise DocumentDenied('Document unavailable') from exc
        if len(content)!=row[1] or hashlib.sha256(content).hexdigest()!=row[0]:
            raise DocumentDenied('Document integrity failure')
        return content
