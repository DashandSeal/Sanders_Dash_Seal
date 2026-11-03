"""Bozly native multicurrency transaction ledger.

Cross-border transfer terms, FX amounts and banking receipts are recorded to
the smallest stated currency units. No fabricated exchange quotes, exchange
rates, settlements, legal eligibility or availability promises.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from bozly_purchasing import ENTITIES

DEFAULT_DB = "/app/secure_ledgers/bozly_financial_core.db"


class GlobalTransactionError(RuntimeError):
    pass


def _open():
    path=Path(os.getenv("BOZLY_DB_PATH",DEFAULT_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_global_transactions (
      transaction_id TEXT PRIMARY KEY,
      paying_entity TEXT NOT NULL,
      recipient_reference TEXT NOT NULL,
      recipient_country TEXT NOT NULL,
      purpose TEXT NOT NULL,
      necessity_evidence TEXT NOT NULL,
      source_currency TEXT NOT NULL,
      source_minor INTEGER NOT NULL CHECK (source_minor>0),
      destination_currency TEXT NOT NULL,
      destination_minor INTEGER NOT NULL CHECK (destination_minor>=0),
      source_exponent INTEGER NOT NULL,
      destination_exponent INTEGER NOT NULL,
      fx_rate_decimal TEXT NOT NULL,
      fx_quote_reference TEXT NOT NULL,
      fx_provider_reference TEXT NOT NULL,
      quote_expires_utc INTEGER NOT NULL,
      quoted_fees_source_minor INTEGER NOT NULL,
      transaction_digest TEXT NOT NULL,
      ceo_subject TEXT,
      authorized_at INTEGER,
      payment_reference TEXT,
      status TEXT NOT NULL,
      final_source_minor INTEGER,
      final_destination_minor INTEGER,
      final_fees_minor INTEGER,
      settled_at INTEGER,
      settlement_receipt TEXT,
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bozly_global_transaction_events (
      event_id TEXT PRIMARY KEY,
      transaction_id TEXT NOT NULL REFERENCES bozly_global_transactions(transaction_id),
      event_kind TEXT NOT NULL,
      evidence_digest TEXT NOT NULL,
      observed_at INTEGER NOT NULL
    );
    """)
    return db


def _require_currency(code, exponent):
    if not isinstance(code,str) or len(code)!=3 or not code.isascii() or not code.isalpha():
        raise ValueError("ISO 4217 three-letter currency required")
    # Use provider-confirmed currency exponent: some currencies use 0 or 3.
    if type(exponent) is not int or exponent not in (0,1,2,3,4):
        raise ValueError("Real provider-confirmed currency minor-unit exponent required")
    return code.upper()


def prepare_global_transaction(
    *, transaction_id, paying_entity, recipient_reference, recipient_country,
    purpose, necessity_evidence, source_currency, source_minor,
    source_exponent, destination_currency, destination_minor,
    destination_exponent, fx_rate_decimal, fx_quote_reference,
    fx_provider_reference, quote_expires_utc, quoted_fees_source_minor
) -> dict:
    """Prepare a quote-backed international payment for a single Sanders LLC."""
    if paying_entity not in ENTITIES:
        raise ValueError("Paying legal entity is not registered in Bozly")
    args=(transaction_id,recipient_reference,purpose,necessity_evidence,
          fx_quote_reference,fx_provider_reference)
    if not all(isinstance(a,str) and a.strip() and len(a)<=2000 for a in args):
        raise ValueError("Real transaction identity, purpose and provider quote required")
    if (not isinstance(recipient_country,str) or len(recipient_country)!=2
            or not recipient_country.isascii() or not recipient_country.isalpha()):
        raise ValueError("ISO 3166-1 alpha-2 recipient country required")
    if type(source_minor) is not int or source_minor<=0:
        raise ValueError("Source amount must be positive integer minor units")
    if type(destination_minor) is not int or destination_minor<0:
        raise ValueError("Destination amount must be nonnegative integer minor units")
    if type(quoted_fees_source_minor) is not int or quoted_fees_source_minor<0:
        raise ValueError("Provider fee must be an exact nonnegative minor unit integer")
    src=_require_currency(source_currency,source_exponent)
    dst=_require_currency(destination_currency,destination_exponent)
    try:
        rate=Decimal(str(fx_rate_decimal))
    except (InvalidOperation,ValueError) as exc:
        raise ValueError("Invalid quoted decimal FX rate") from exc
    if not rate.is_finite() or rate<=0:
        raise ValueError("FX quote must be finite and positive")
    if type(quote_expires_utc) is not int or quote_expires_utc<=int(time.time()):
        raise ValueError("Current unexpired real provider quote required")
    details={
      "transaction_id":transaction_id,"paying_entity":paying_entity,
      "recipient_reference":recipient_reference,
      "recipient_country":recipient_country.upper(),
      "purpose":purpose,"necessity_evidence":necessity_evidence,
      "source_currency":src,"source_minor":source_minor,
      "source_exponent":source_exponent,"destination_currency":dst,
      "destination_minor":destination_minor,
      "destination_exponent":destination_exponent,"fx_rate_decimal":str(rate),
      "fx_quote_reference":fx_quote_reference,
      "fx_provider_reference":fx_provider_reference,
      "quote_expires_utc":quote_expires_utc,
      "quoted_fees_source_minor":quoted_fees_source_minor
    }
    digest=hashlib.sha256(json.dumps(details,sort_keys=True,
                      separators=(",",":")).encode()).hexdigest()
    with _open() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_global_transactions (
          transaction_id,paying_entity,recipient_reference,recipient_country,
          purpose,necessity_evidence,source_currency,source_minor,
          destination_currency,destination_minor,source_exponent,
          destination_exponent,fx_rate_decimal,fx_quote_reference,
          fx_provider_reference,quote_expires_utc,quoted_fees_source_minor,
          transaction_digest,status,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'QUOTED',?)""",
          (transaction_id,paying_entity,recipient_reference,recipient_country.upper(),
           purpose,necessity_evidence,src,source_minor,dst,destination_minor,
           source_exponent,destination_exponent,str(rate),fx_quote_reference,
           fx_provider_reference,quote_expires_utc,quoted_fees_source_minor,
           digest,int(time.time())))
        db.commit()
    return {"transaction_id":transaction_id,"status":"QUOTED",
            "transaction_digest":digest,"source_minor":source_minor,
            "destination_minor":destination_minor,
            "quoted_fees_source_minor":quoted_fees_source_minor,
            "source_currency":src,"destination_currency":dst}


def authorize_global_transaction(*, transaction_id, ceo_subject, transaction_digest):
    """Pin one exact CEO instruction to the previously quoted transfer terms."""
    if not ceo_subject or not isinstance(ceo_subject,str):
        raise PermissionError("Real CEO identity required")
    with _open() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT transaction_digest,status,quote_expires_utc FROM bozly_global_transactions WHERE transaction_id=?",
                       (transaction_id,)).fetchone()
        if not row:
            raise KeyError("Unknown transaction")
        if row[0]!=transaction_digest or row[1]!="QUOTED":
            raise GlobalTransactionError("Instruction does not match quoted transfer terms")
        if row[2]<=int(time.time()):
            raise GlobalTransactionError("FX quote expired")
        db.execute("UPDATE bozly_global_transactions SET status='CEO_AUTHORIZED',ceo_subject=?,authorized_at=? WHERE transaction_id=?",
                   (ceo_subject,int(time.time()),transaction_id))
        db.commit()
    return {"transaction_id":transaction_id,"status":"CEO_AUTHORIZED"}


def record_global_settlement(*, transaction_id, event_id, payment_reference,
                             actual_source_minor, actual_destination_minor,
                             actual_fees_minor, evidence_digest):
    """Record actual bank-verified settlement after authenticated rail ingestion.

    The caller must authenticate the financial institution evidence; this
    module cannot substitute for actual bank or sanctions/AML enforcement.
    """
    if (not all(isinstance(v,str) and v for v in
                (transaction_id,event_id,payment_reference,evidence_digest))
            or len(evidence_digest)!=64
            or any(c not in "0123456789abcdef" for c in evidence_digest)
            or any(type(v) is not int or v<0 for v in
                   (actual_source_minor,actual_destination_minor,actual_fees_minor))):
        raise ValueError("Authenticated receipt identifiers and exact amounts required")
    with _open() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute(
            "SELECT status,payment_reference FROM bozly_global_transactions WHERE transaction_id=?",
            (transaction_id,)).fetchone()
        if not row:
            raise KeyError("Unknown transaction")
        if row[0] not in ("SUBMITTED","SETTLED"):
            raise GlobalTransactionError("Settlement without submitted transfer evidence")
        if row[1] and row[1]!=payment_reference:
            raise GlobalTransactionError("Payment reference conflict")
        existing=db.execute("SELECT transaction_id,evidence_digest FROM bozly_global_transaction_events WHERE event_id=?",
                            (event_id,)).fetchone()
        if existing:
            if existing!=(transaction_id,evidence_digest):
                raise GlobalTransactionError("Conflicting receipt")
            return {"transaction_id":transaction_id,"duplicate":True,"status":row[0]}
        db.execute("INSERT INTO bozly_global_transaction_events VALUES(?,?,?,?,?)",
                   (event_id,transaction_id,"SETTLEMENT",evidence_digest,int(time.time())))
        db.execute("""UPDATE bozly_global_transactions
            SET status='SETTLED',payment_reference=?,settlement_receipt=?,
                final_source_minor=?,final_destination_minor=?,final_fees_minor=?,
                settled_at=? WHERE transaction_id=?""",
            (payment_reference,event_id,actual_source_minor,
             actual_destination_minor,actual_fees_minor,int(time.time()),transaction_id))
        db.commit()
    return {"transaction_id":transaction_id,"status":"SETTLED",
            "actual_source_minor":actual_source_minor,
            "actual_destination_minor":actual_destination_minor,
            "actual_fees_minor":actual_fees_minor}


def global_transaction_summary(entity):
    """Exact minor-unit totals; currencies are never mixed without FX facts."""
    if entity not in ENTITIES:
        raise ValueError("Unknown paying entity")
    with _open() as db:
        rows=db.execute(
            """SELECT source_currency,destination_currency,status,
             COUNT(*),SUM(source_minor),SUM(destination_minor),
             SUM(quoted_fees_source_minor)
             FROM bozly_global_transactions WHERE paying_entity=?
             GROUP BY source_currency,destination_currency,status
             ORDER BY source_currency,destination_currency,status""",
            (entity,)).fetchall()
    return [{"source_currency":src,"destination_currency":dst,"status":status,
             "count":n,"source_minor":a,"destination_minor":b,
             "quoted_fees_source_minor":fee} for src,dst,status,n,a,b,fee in rows]
