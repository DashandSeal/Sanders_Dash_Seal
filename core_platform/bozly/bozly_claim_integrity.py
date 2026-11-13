"""Bozly native claim integrity engine: documentary contradictions, not mind-reading.

Compares a submitted factual claim with an actual recorded transaction from the
same legal entity. Returns supported, contradicted or insufficient-evidence
classifications. Intent to deceive is never inferred from speech, gender,
appearance, behavior, accents or demographic attributes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .bozly_purchasing import ENTITIES

DB = "/app/secure_ledgers/bozly_financial_core.db"
FIELDS = frozenset({"amount_minor","currency","status","merchant_id","merchant_invoice"})
RECORD_TYPES = frozenset({"purchase","global_transaction"})


def _db():
    path=Path(os.environ.get("BOZLY_DB_PATH",DB))
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_claim_integrity_reviews (
      review_id TEXT PRIMARY KEY,
      entity_id TEXT NOT NULL,
      record_type TEXT NOT NULL,
      record_id TEXT NOT NULL,
      claimed_field TEXT NOT NULL,
      claimed_value_json TEXT NOT NULL,
      source_value_json TEXT,
      observation TEXT NOT NULL,
      evidence_sha256 TEXT,
      requested_by TEXT NOT NULL,
      observed_at INTEGER NOT NULL
    );
    """)
    return conn


def _source_record(db,entity_id,record_type,record_id):
    if record_type=="purchase":
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bozly_purchases'"
        ).fetchone():
            return None
        row=db.execute(
            """SELECT amount_minor,currency,status,merchant_id,merchant_invoice
            FROM bozly_purchases WHERE paying_entity=? AND order_id=?""",
            (entity_id,record_id)
        ).fetchone()
        return (dict(zip(
            ("amount_minor","currency","status","merchant_id","merchant_invoice"),row
        )) if row else None)
    if record_type=="global_transaction":
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bozly_global_transactions'"
        ).fetchone():
            return None
        row=db.execute(
            """SELECT source_minor,source_currency,status
            FROM bozly_global_transactions
            WHERE paying_entity=? AND transaction_id=?""",
            (entity_id,record_id)
        ).fetchone()
        return ({"amount_minor":row[0],"currency":row[1],"status":row[2]}
                if row else None)
    return None


def assess_documented_claim(*,entity_id: str,record_type: str,record_id: str,
                            claimed_field: str,claimed_value,requested_by: str) -> dict:
    """Evaluate a single factual assertion against the current recorded source."""
    if entity_id not in ENTITIES:
        raise ValueError("Unknown paying legal entity")
    if record_type not in RECORD_TYPES or claimed_field not in FIELDS:
        raise ValueError("Unsupported financial assertion")
    if not all(isinstance(x,str) and x.strip() and len(x)<=256
               for x in (record_id,requested_by)):
        raise ValueError("Real record reference and actor required")
    if claimed_field=="amount_minor":
        if type(claimed_value) is not int or claimed_value<0:
            raise ValueError("Money must be exact nonnegative integer minor units")
    elif not isinstance(claimed_value,str) or len(claimed_value)>512:
        raise ValueError("Exact string claimed value required")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        record=_source_record(db,entity_id,record_type,record_id)
        observed=record.get(claimed_field) if record else None
        if observed is None:
            assessment="INSUFFICIENT_EVIDENCE"
        elif observed==claimed_value:
            assessment="CONSISTENT_WITH_RECORD"
        else:
            assessment="CONTRADICTED_BY_RECORD"
        evidence=hashlib.sha256(
            json.dumps(record,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest() if record else None
        review_id="claim_"+uuid.uuid4().hex
        db.execute(
            """INSERT INTO bozly_claim_integrity_reviews
            (review_id,entity_id,record_type,record_id,claimed_field,
             claimed_value_json,source_value_json,observation,evidence_sha256,
             requested_by,observed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (review_id,entity_id,record_type,record_id,claimed_field,
             json.dumps(claimed_value),json.dumps(observed),assessment,evidence,
             requested_by,int(time.time()))
        )
        db.commit()
    return {
        "review_id":review_id,"entity_id":entity_id,"record_type":record_type,
        "record_id":record_id,"field":claimed_field,"claimed_value":claimed_value,
        "recorded_value":observed,"assessment":assessment,
        "evidence_sha256":evidence,
        "deception_or_intent_proven":False,
        "explanation":(
            "Recorded value disagrees with assertion; examine original records,"
            " timestamps and context before drawing conclusions."
            if assessment=="CONTRADICTED_BY_RECORD" else
            "Recorded value matches this assertion, but does not independently prove intent or full truth."
            if assessment=="CONSISTENT_WITH_RECORD" else
            "No applicable source record is available; no determination made."
        ),
    }
