"""Small, deterministic, auditable SQLite registry and event ledger."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, os, sqlite3
from pathlib import Path
from .registry import COMPANIES

DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "state" / "secretary.sqlite3")

def get_db_path() -> str:
    return os.getenv("SCS_DB_PATH", DEFAULT_DB)

@contextmanager
def connect():
    path = get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS companies (id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_type TEXT NOT NULL, founded_year INTEGER, co_sos_id TEXT, note TEXT);
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT NOT NULL REFERENCES companies(id), title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', due_date TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT NOT NULL REFERENCES companies(id), kind TEXT NOT NULL, summary TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, actor TEXT NOT NULL, operation TEXT NOT NULL, object_ref TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
        """)
        for c in COMPANIES:
            db.execute("INSERT OR IGNORE INTO companies(id,name,entity_type,founded_year,co_sos_id,note) VALUES (?,?,?,?,?,?)",(c["id"],c["name"],c["type"],c.get("founded_year"),c.get("co_sos_id"),c["note"]))

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def audit_insert(db, actor, operation, object_ref, payload):
    ts = utc_now()
    data = json.dumps(payload,sort_keys=True, separators=(",",":"))
    prev = db.execute("SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    previous_hash = prev["entry_hash"] if prev else "GENESIS"
    message = "|".join((previous_hash,ts,actor,operation,object_ref,data))
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    db.execute("INSERT INTO audit(created_at,actor,operation,object_ref,payload,previous_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",(ts,actor,operation,object_ref,data,previous_hash,digest))
    return digest

def verify_audit():
    with connect() as db:
        rows=db.execute("SELECT * FROM audit ORDER BY id").fetchall()
    last="GENESIS"
    for row in rows:
        message="|".join((last,row["created_at"],row["actor"],row["operation"],row["object_ref"],row["payload"]))
        expected=hashlib.sha256(message.encode("utf-8")).hexdigest()
        if row["previous_hash"]!=last or row["entry_hash"]!=expected:
            return {"valid":False,"entries":len(rows),"first_invalid_id":row["id"]}
        last=row["entry_hash"]
    return {"valid":True,"entries":len(rows),"last_hash":last}