"""Native Bozly CFO forensic accounting: source-ledger anomaly analysis and evidence custody.

Identifies documented exceptions, not guilt or criminal conduct. Every amount
remains in its native ISO currency's minor units; no unverified bank balance,
tax deduction, wrongdoing or settlement is inferred.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from bozly_purchasing import ENTITIES

DEFAULT_DB="/app/secure_ledgers/bozly_financial_core.db"

class ForensicError(RuntimeError):
    pass


def _digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def _db():
    path=Path(os.environ.get("BOZLY_DB_PATH",DEFAULT_DB))
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=20000")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_forensic_cases(
      case_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, title TEXT NOT NULL,
      scope TEXT NOT NULL, opened_by TEXT NOT NULL, opened_at INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'OPEN'
    );
    CREATE TABLE IF NOT EXISTS bozly_forensic_evidence(
      case_id TEXT NOT NULL REFERENCES bozly_forensic_cases(case_id),
      evidence_id TEXT NOT NULL, evidence_type TEXT NOT NULL,
      source_reference TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      collected_by TEXT NOT NULL, collected_at INTEGER NOT NULL,
      PRIMARY KEY(case_id,evidence_id)
    );
    CREATE TABLE IF NOT EXISTS bozly_forensic_findings(
      finding_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES bozly_forensic_cases(case_id),
      source_reference TEXT NOT NULL, finding_code TEXT NOT NULL,
      description TEXT NOT NULL, amount_minor INTEGER, currency TEXT,
      source_record_sha256 TEXT NOT NULL, observed_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bozly_forensic_history(
      event_id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES bozly_forensic_cases(case_id),
      event_type TEXT NOT NULL,details_sha256 TEXT NOT NULL,previous_sha256 TEXT,
      event_sha256 TEXT NOT NULL, recorded_at INTEGER NOT NULL
    );
    """)
    return con


def _entity(db,case_id):
    row=db.execute("SELECT entity_id FROM bozly_forensic_cases WHERE case_id=?",
                   (case_id,)).fetchone()
    if not row:
        raise KeyError("Forensic case not found")
    return row[0]


def _history(db,case_id,kind,details):
    prior=db.execute("SELECT event_sha256 FROM bozly_forensic_history WHERE case_id=? ORDER BY rowid DESC LIMIT 1",
                     (case_id,)).fetchone()
    before=prior[0] if prior else None
    item_id=uuid.uuid4().hex
    timestamp=int(time.time())
    details_hash=_digest(details)
    link=_digest([item_id,case_id,kind,details_hash,before,timestamp])
    db.execute("INSERT INTO bozly_forensic_history VALUES(?,?,?,?,?,?,?)",
               (item_id,case_id,kind,details_hash,before,link,timestamp))


def open_case(*,entity_id,title,scope,opened_by,case_id=None):
    if entity_id not in ENTITIES:
        raise ValueError("Unknown Sanders legal entity")
    if any(not isinstance(v,str) or not v.strip() or len(v)>1000
           for v in (title,scope,opened_by)):
        raise ValueError("Case title, scope and opener required")
    case_id=case_id or ("for_"+uuid.uuid4().hex)
    if not isinstance(case_id,str) or not 1<=len(case_id)<=160:
        raise ValueError("Invalid case ID")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO bozly_forensic_cases VALUES(?,?,?,?,? ,?,'OPEN')",
                   (case_id,entity_id,title,scope,opened_by,int(time.time())))
        _history(db,case_id,"CASE_OPENED",{
            "entity_id":entity_id,"title":title,"scope":scope,"opened_by":opened_by
        })
        db.commit()
    return {"case_id":case_id,"entity_id":entity_id,"status":"OPEN"}


def attach_evidence(*,case_id,evidence_id,evidence_type,source_reference,
                    source_sha256,collected_by):
    """Index already-preserved original evidence, without inventing its content."""
    values=(evidence_id,evidence_type,source_reference,collected_by)
    if any(not isinstance(v,str) or not v.strip() or len(v)>1000 for v in values):
        raise ValueError("Evidence reference and collector required")
    if (not isinstance(source_sha256,str) or len(source_sha256)!=64
            or any(c not in "0123456789abcdef" for c in source_sha256)):
        raise ValueError("A genuine source SHA-256 is required")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        _entity(db,case_id)
        row=db.execute(
            "SELECT source_sha256,source_reference FROM bozly_forensic_evidence WHERE case_id=? AND evidence_id=?",
            (case_id,evidence_id)
        ).fetchone()
        if row and row!=(source_sha256,source_reference):
            raise ForensicError("Evidence identity conflicts with an existing original")
        if not row:
            db.execute("""INSERT INTO bozly_forensic_evidence VALUES(?,?,?,?,?,?,?)""",
                       (case_id,evidence_id,evidence_type,source_reference,source_sha256,
                        collected_by,int(time.time())))
            _history(db,case_id,"EVIDENCE_REFERENCED",{
                "evidence_id":evidence_id,"source_sha256":source_sha256,
                "source_reference":source_reference
            })
        db.commit()
    return {"case_id":case_id,"evidence_id":evidence_id,
            "original_evidence_bytes_preserved_by_this_module":False}


def _finding(db,case_id,source,code,description,amount,currency,record):
    uid=_digest([case_id,source,code])
    row=db.execute("SELECT source_record_sha256 FROM bozly_forensic_findings WHERE finding_id=?",
                   (uid,)).fetchone()
    digest=_digest(record)
    if row and row[0]!=digest:
        # Changed source ledger facts require a *new* finding, not overwritten evidence.
        uid=_digest([case_id,source,code,digest])
        row=db.execute("SELECT 1 FROM bozly_forensic_findings WHERE finding_id=?",
                       (uid,)).fetchone()
    if row:
        return 0
    db.execute("""INSERT INTO bozly_forensic_findings
       (finding_id,case_id,source_reference,finding_code,description,
        amount_minor,currency,source_record_sha256,observed_at)
       VALUES(?,?,?,?,?,?,?,?,?)""",
       (uid,case_id,source,code,description,amount,currency,digest,int(time.time())))
    _history(db,case_id,"EXCEPTION_DETECTED",{
        "finding_id":uid,"code":code,"source":source,"source_sha256":digest
    })
    return 1


def investigate(*,case_id,entity_id):
    """Analyze recorded Bozly purchases/global transfers without assuming fraud."""
    if entity_id not in ENTITIES:
        raise ValueError("Unknown legal entity")
    new=0
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        if _entity(db,case_id)!=entity_id:
            raise PermissionError("Forensic case belongs to another LLC")
        tables={r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "bozly_purchases" in tables:
            rows=db.execute(
                """SELECT order_id,merchant_id,merchant_invoice,amount_minor,currency,
                status,provider_reference,settled_at
                FROM bozly_purchases WHERE paying_entity=?""",(entity_id,)
            ).fetchall()
            for order,merchant,invoice,cents,curr,status,reference,settled in rows:
                record=[order,merchant,invoice,cents,curr,status,reference,settled]
                if status=="AMOUNT_DISCREPANCY":
                    new+=_finding(db,case_id,order,"BANK_AMOUNT_MISMATCH",
                        "Recorded banking receipt and authorized purchase amount disagree",
                        cents,curr,record)
                if status=="SUBMISSION_UNKNOWN":
                    new+=_finding(db,case_id,order,"PAYMENT_OUTCOME_UNKNOWN",
                        "Outbound payment request has no confirmed submission outcome",
                        cents,curr,record)
            # Duplicate merchant invoice references across LLCs are possible shared
            # costs, not proof of wrongdoing. Record only this entity's references.
            grouped=db.execute(
                """SELECT p1.merchant_id,p1.merchant_invoice,COUNT(DISTINCT p1.paying_entity)
                FROM bozly_purchases p1
                WHERE p1.paying_entity=? AND EXISTS(
                    SELECT 1 FROM bozly_purchases p2
                    WHERE p2.merchant_id=p1.merchant_id
                    AND p2.merchant_invoice=p1.merchant_invoice
                    AND p2.paying_entity!=p1.paying_entity)
                GROUP BY p1.merchant_id,p1.merchant_invoice""",(entity_id,)
            ).fetchall()
            for merchant,invoice,_ in grouped:
                new+=_finding(db,case_id,merchant+":"+invoice,
                    "CROSS_LLC_INVOICE_REFERENCE",
                    "Same merchant invoice identifier appears in more than one LLC; reconcile documented allocations",
                    None,None,[merchant,invoice,entity_id])
        if "bozly_global_transactions" in tables:
            rows=db.execute(
                """SELECT transaction_id,source_minor,source_currency,status,
                final_source_minor,final_fees_minor,quoted_fees_source_minor,
                fx_quote_reference,settlement_receipt
                FROM bozly_global_transactions WHERE paying_entity=?""",
                (entity_id,)
            ).fetchall()
            for ident,amount,currency,status,final,final_fees,quoted_fees,fx_ref,receipt in rows:
                record=[ident,amount,currency,status,final,final_fees,quoted_fees,fx_ref,receipt]
                if status=="SETTLED" and final is not None and final!=amount:
                    new+=_finding(db,case_id,ident,"FX_SETTLEMENT_VARIANCE",
                        "Actual source debit differs from the quoted transfer amount",
                        final,currency,record)
                if status=="SETTLED" and final_fees is not None and final_fees!=quoted_fees:
                    new+=_finding(db,case_id,ident,"FX_FEE_VARIANCE",
                        "Reported actual financial institution fee differs from quote",
                        final_fees,currency,record)
                if status=="SUBMISSION_UNKNOWN":
                    new+=_finding(db,case_id,ident,"GLOBAL_TRANSFER_OUTCOME_UNKNOWN",
                        "No confirmed cross-border payment submission outcome",
                        amount,currency,record)
        db.commit()
        findings=db.execute(
            """SELECT finding_id,finding_code,source_reference,description,
                      amount_minor,currency,source_record_sha256,observed_at
               FROM bozly_forensic_findings WHERE case_id=?
               ORDER BY observed_at,finding_id""",(case_id,)
        ).fetchall()
    return {
        "case_id":case_id,"entity_id":entity_id,"new_findings":new,
        "findings":[{
            "finding_id":fid,"rule":code,"source":ref,"observation":desc,
            "amount_minor":cents,"currency":curr,"source_sha256":digest,
            "observed_at_unix":when,
        } for fid,code,ref,desc,cents,curr,digest,when in findings],
        "legal_conclusion":"No finding alone establishes wrongdoing, money laundering or tax violations.",
        "evidence_note":"Original evidence must be separately preserved and access protected.",
    }
