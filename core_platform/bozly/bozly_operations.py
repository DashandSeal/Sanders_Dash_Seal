"""Bozly global human workflow, priority alert, incident and learning ledger.

Data is per-entity. This is an operational records layer, not a grant of
payment authority, a simulated AI model, or a production SOC service.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

DB_PATH = os.getenv("BOZLY_CONTROL_DB", "/app/secure_ledgers/bozly_controls.db")
LEVELS = {"P0", "P1", "P2", "P3"}
WORKFLOW_STATES = {"OPEN", "CLAIMED", "IN_PROGRESS", "RESOLVED", "CANCELLED"}
TRANSITIONS = {
    "OPEN": {"CLAIMED", "CANCELLED"},
    "CLAIMED": {"IN_PROGRESS", "RESOLVED", "CANCELLED"},
    "IN_PROGRESS": {"RESOLVED", "CANCELLED"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}


def _db():
    path = Path(os.getenv("BOZLY_CONTROL_DB", DB_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS workflows (
      workflow_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL,
      title TEXT NOT NULL, category TEXT NOT NULL,
      status TEXT NOT NULL, assigned_to TEXT, created_by TEXT NOT NULL,
      created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
      revision INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS alerts (
      alert_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL,
      priority TEXT NOT NULL, category TEXT NOT NULL,
      description TEXT NOT NULL, created_at INTEGER NOT NULL,
      acknowledged_at INTEGER, acknowledged_by TEXT,
      dedupe_key TEXT NOT NULL, UNIQUE (entity_id, dedupe_key)
    );
    CREATE TABLE IF NOT EXISTS risk_signals (
      signal_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL,
      source_id TEXT NOT NULL, signal_type TEXT NOT NULL,
      evidence_digest TEXT NOT NULL,
      outcome TEXT NOT NULL, created_at INTEGER NOT NULL,
      UNIQUE(entity_id, source_id, signal_type)
    );
    CREATE TABLE IF NOT EXISTS learning_feedback (
      feedback_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL,
      subject_kind TEXT NOT NULL, signal_id TEXT,
      disposition TEXT NOT NULL, model_version TEXT,
      actor TEXT NOT NULL, created_at INTEGER NOT NULL,
      FOREIGN KEY (signal_id) REFERENCES risk_signals(signal_id)
    );
    CREATE TABLE IF NOT EXISTS uplink_outbox (
      message_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL,
      priority TEXT NOT NULL, payload_ciphertext TEXT NOT NULL,
      transport TEXT NOT NULL, status TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_id TEXT NOT NULL, event TEXT NOT NULL,
      subject TEXT NOT NULL, actor TEXT NOT NULL,
      at INTEGER NOT NULL, previous_hash TEXT NOT NULL,
      entry_hash TEXT NOT NULL
    );
    """)
    return db


def _audit(db, *, entity, event, subject, actor):
    now = int(time.time())
    previous = db.execute("SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    previous_hash = previous[0] if previous else "0" * 64
    entry_hash = hashlib.sha256(
        json.dumps([previous_hash, entity, event, subject, actor, now],
                   separators=(",", ":")).encode()
    ).hexdigest()
    db.execute(
        "INSERT INTO audit(entity_id,event,subject,actor,at,previous_hash,entry_hash) VALUES(?,?,?,?,?,?,?)",
        (entity,event,subject,actor,now,previous_hash,entry_hash)
    )


def new_workflow(entity: str, title: str, category: str, actor: str) -> dict:
    if not all(isinstance(v, str) and 0 < len(v.strip()) <= 240
               for v in (entity,title,category,actor)):
        raise ValueError("Invalid workflow attributes")
    now = int(time.time())
    ident = "wf_" + uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO workflows
        (workflow_id,entity_id,title,category,status,created_by,created_at,updated_at)
        VALUES(?,?,?,?,'OPEN',?,?,?)""",
        (ident,entity,title,category,actor,now,now))
        _audit(db,entity=entity,event="WORKFLOW_OPEN",subject=ident,actor=actor)
        db.commit()
    return {"workflow_id":ident,"entity_id":entity,"status":"OPEN"}


def advance_workflow(entity: str, ident: str, state: str, actor: str,
                     expected_revision: int) -> dict:
    if state not in WORKFLOW_STATES:
        raise ValueError("Invalid workflow state")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        record = db.execute(
            "SELECT status,revision FROM workflows WHERE entity_id=? AND workflow_id=?",
            (entity,ident)).fetchone()
        if record is None:
            raise KeyError("Workflow not found")
        if record[1] != expected_revision:
            raise ValueError("Concurrent workflow update")
        if state not in TRANSITIONS[record[0]]:
            raise ValueError("Invalid state transition")
        db.execute(
            """UPDATE workflows SET status=?,revision=revision+1,updated_at=?,
            assigned_to=CASE WHEN ?='CLAIMED' THEN ? ELSE assigned_to END
            WHERE entity_id=? AND workflow_id=?""",
            (state,int(time.time()),state,actor,entity,ident))
        _audit(db,entity=entity,event="WORKFLOW_"+state,subject=ident,actor=actor)
        db.commit()
    return {"workflow_id":ident,"entity_id":entity,"status":state,
            "revision":expected_revision+1}


def priority_alert(entity: str, level: str, category: str, description: str,
                   dedupe_key: str) -> dict:
    if level not in LEVELS:
        raise ValueError("Invalid priority")
    if not all(isinstance(v,str) and 0 < len(v) <= 512
               for v in (entity,category,description,dedupe_key)):
        raise ValueError("Invalid alert fields")
    ident = "alert_" + uuid.uuid4().hex
    now = int(time.time())
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT OR IGNORE INTO alerts
            (alert_id,entity_id,priority,category,description,created_at,dedupe_key)
            VALUES(?,?,?,?,?,?,?)""",
            (ident,entity,level,category,description,now,dedupe_key))
        row = db.execute("SELECT alert_id,priority FROM alerts WHERE entity_id=? AND dedupe_key=?",
                         (entity,dedupe_key)).fetchone()
        if row[0] == ident:
            _audit(db,entity=entity,event="ALERT_"+level,subject=ident,actor="bozly")
        db.commit()
    return {"alert_id":row[0],"priority":row[1],"new":row[0]==ident}


def acknowledge_alert(entity: str, ident: str, actor: str) -> bool:
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute(
            """UPDATE alerts SET acknowledged_at=?,acknowledged_by=?
               WHERE entity_id=? AND alert_id=? AND acknowledged_at IS NULL""",
            (int(time.time()),actor,entity,ident)).rowcount
        if changed:
            _audit(db,entity=entity,event="ALERT_ACK",subject=ident,actor=actor)
        db.commit()
    return changed == 1


def record_risk_signal(entity: str, source_id: str, kind: str, evidence_digest: str,
                       outcome: str="REVIEW_SUGGESTED") -> dict:
    if len(evidence_digest) != 64 or not all(c in "0123456789abcdef" for c in evidence_digest):
        raise ValueError("Evidence must be represented by a SHA-256 digest")
    if not all(isinstance(v,str) and 0 < len(v) <= 180
               for v in (entity,source_id,kind,outcome)):
        raise ValueError("Invalid risk signal")
    ident = "risk_" + uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT OR IGNORE INTO risk_signals
               VALUES(?,?,?,?,?,?,?)""",
            (ident,entity,source_id,kind,evidence_digest,outcome,int(time.time())))
        row = db.execute(
            "SELECT signal_id FROM risk_signals WHERE entity_id=? AND source_id=? AND signal_type=?",
            (entity,source_id,kind)).fetchone()
        if row[0] == ident:
            _audit(db,entity=entity,event="RISK_RECORDED",subject=ident,actor="bozly")
        db.commit()
    return {"signal_id":row[0],"outcome":outcome}


def record_learning_feedback(entity: str, signal_id: str, disposition: str,
                             actor: str, model_version: str | None=None) -> str:
    """Append an outcome label, not raw confidential records or autonomous training."""
    if disposition not in {"CONFIRMED_FRAUD","FALSE_POSITIVE","NEEDS_REVIEW","RESOLVED"}:
        raise ValueError("Unsupported feedback disposition")
    ident = "feedback_" + uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        found = db.execute("SELECT 1 FROM risk_signals WHERE entity_id=? AND signal_id=?",
                           (entity,signal_id)).fetchone()
        if not found:
            raise KeyError("Signal not found in this legal entity")
        db.execute("""INSERT INTO learning_feedback
        VALUES(?,?,?,?,?,?,?,?)""",
        (ident,entity,"RISK_SIGNAL",signal_id,disposition,model_version,actor,int(time.time())))
        _audit(db,entity=entity,event="LEARNING_FEEDBACK",subject=ident,actor=actor)
        db.commit()
    return ident


def queue_uplink(entity: str, priority: str, ciphertext: str,
                 transport: str="configured-satellite-gateway") -> str:
    if priority not in LEVELS or not ciphertext or len(ciphertext)>131072:
        raise ValueError("Encrypted uplink message required")
    ident = "uplink_" + uuid.uuid4().hex
    now = int(time.time())
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO uplink_outbox VALUES(?,?,?,?,?,'PENDING',0,?,?)""",
                   (ident,entity,priority,ciphertext,transport,now,now))
        _audit(db,entity=entity,event="UPLINK_QUEUED",subject=ident,actor="bozly")
        db.commit()
    return ident
