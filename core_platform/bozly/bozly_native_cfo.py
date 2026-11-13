"""Native Bozly CFO accounting, financial planning and variance intelligence.

Directly owned double-entry accounting for the three separate Sanders LLCs.
Actual records only; no fabricated bank balances, returns, tax filings or
third-party accounting software. Exact currency minor units throughout.
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from .bozly_purchasing import ENTITIES

DEFAULT_DB="/app/secure_ledgers/bozly_financial_core.db"
CODE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
SHA=re.compile(r"^[a-f0-9]{64}$")
CUR=re.compile(r"^[A-Z]{3}$")
TYPES=("ASSET","LIABILITY","EQUITY","INCOME","EXPENSE")


def _valid_entity(entity,currency):
    if entity not in ENTITIES or not isinstance(currency,str) or not CUR.fullmatch(currency):
        raise ValueError("Registered LLC and ISO currency required")


def _string(v,label,maxlen=256):
    if not isinstance(v,str) or not v.strip() or len(v)>maxlen:
        raise ValueError("Invalid "+label)
    return v


def _amount(v,negative=False):
    if type(v) is not int or abs(v)>9_000_000_000_000_000 or (v<0 and not negative):
        raise ValueError("Exact integer minor units required")
    return v


def _month(v):
    try:
        d=date.fromisoformat(v+"-01")
        if d.strftime("%Y-%m")!=v:
            raise ValueError()
        return d
    except (ValueError,TypeError) as e:
        raise ValueError("Use YYYY-MM month") from e


def _db():
    path=Path(os.getenv("BOZLY_DB_PATH",DEFAULT_DB))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_cfo_accounts(
       entity_id TEXT NOT NULL,code TEXT NOT NULL,currency TEXT NOT NULL,
       name TEXT NOT NULL,kind TEXT NOT NULL,created_at INTEGER NOT NULL,
       PRIMARY KEY(entity_id,code,currency)
    );
    CREATE TABLE IF NOT EXISTS bozly_cfo_journals(
       journal_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,
       currency TEXT NOT NULL,posting_date TEXT NOT NULL,
       source_reference TEXT NOT NULL,source_sha256 TEXT NOT NULL,
       explanation TEXT NOT NULL,actor TEXT NOT NULL,
       journal_sha256 TEXT NOT NULL,recorded_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bozly_cfo_journal_lines(
       journal_id TEXT NOT NULL REFERENCES bozly_cfo_journals(journal_id),
       line_number INTEGER NOT NULL,code TEXT NOT NULL,
       debit_minor INTEGER NOT NULL CHECK(debit_minor>=0),
       credit_minor INTEGER NOT NULL CHECK(credit_minor>=0),
       CHECK ((debit_minor>0 AND credit_minor=0) OR
              (credit_minor>0 AND debit_minor=0)),
       PRIMARY KEY(journal_id,line_number)
    );
    CREATE TABLE IF NOT EXISTS bozly_cfo_budgets(
       entity_id TEXT NOT NULL,currency TEXT NOT NULL,month TEXT NOT NULL,
       code TEXT NOT NULL,planned_net_minor INTEGER NOT NULL,
       source_reference TEXT NOT NULL,actor TEXT NOT NULL,
       updated_at INTEGER NOT NULL,
       PRIMARY KEY(entity_id,currency,month,code)
    );
    CREATE TABLE IF NOT EXISTS bozly_cfo_cash_forecasts(
       entity_id TEXT NOT NULL,currency TEXT NOT NULL,month TEXT NOT NULL,
       opening_cash_minor INTEGER NOT NULL,
       projected_inflows_minor INTEGER NOT NULL,
       projected_outflows_minor INTEGER NOT NULL,
       source_reference TEXT NOT NULL,actor TEXT NOT NULL,
       updated_at INTEGER NOT NULL,
       PRIMARY KEY(entity_id,currency,month)
    );
    """)
    return db


def register_account(*,entity_id,currency,code,name,kind):
    _valid_entity(entity_id,currency)
    if not isinstance(code,str) or not CODE.fullmatch(code) or kind not in TYPES:
        raise ValueError("Valid account code and kind required")
    _string(name,"account name")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_cfo_accounts
          (entity_id,code,currency,name,kind,created_at) VALUES(?,?,?,?,?,?)""",
          (entity_id,code,currency,name,kind,int(time.time())))
        db.commit()
    return {"entity_id":entity_id,"currency":currency,"code":code,"kind":kind}


def post_journal(*,entity_id,currency,journal_id,posting_date,
                 source_reference,source_sha256,explanation,actor,lines):
    _valid_entity(entity_id,currency)
    for v,n in ((journal_id,"journal id"),(source_reference,"source reference"),
                (explanation,"explanation"),(actor,"actor")):
        _string(v,n,1000 if n=="explanation" else 256)
    if not isinstance(source_sha256,str) or not SHA.fullmatch(source_sha256):
        raise ValueError("Source evidence SHA-256 required")
    try:
        if date.fromisoformat(posting_date).isoformat()!=posting_date:
            raise ValueError()
    except (ValueError,TypeError) as e:
        raise ValueError("Use ISO posting date") from e
    if not isinstance(lines,list) or not 2<=len(lines)<=100:
        raise ValueError("Two to one hundred actual lines required")
    checked=[]
    dr=cr=0
    for item in lines:
        if not isinstance(item,dict):
            raise ValueError("Invalid ledger line")
        code=item.get("code")
        if not isinstance(code,str) or not CODE.fullmatch(code):
            raise ValueError("Invalid ledger code")
        debit=_amount(item.get("debit_minor"))
        credit=_amount(item.get("credit_minor"))
        if (debit>0)==(credit>0):
            raise ValueError("Each line must have only a debit or a credit")
        checked.append({"code":code,"debit_minor":debit,"credit_minor":credit})
        dr+=debit
        cr+=credit
    if dr!=cr or dr<=0:
        raise ValueError("Journal must balance")
    body={"entity_id":entity_id,"currency":currency,"journal_id":journal_id,
          "posting_date":posting_date,"source_reference":source_reference,
          "source_sha256":source_sha256,"explanation":explanation,"lines":checked}
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,
               separators=(",",":")).encode()).hexdigest()
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        for line in checked:
            exists=db.execute("""SELECT 1 FROM bozly_cfo_accounts
              WHERE entity_id=? AND currency=? AND code=?""",
              (entity_id,currency,line["code"])).fetchone()
            if not exists:
                raise ValueError("Account not present for this LLC: "+line["code"])
        db.execute("""INSERT INTO bozly_cfo_journals
          (journal_id,entity_id,currency,posting_date,source_reference,
          source_sha256,explanation,actor,journal_sha256,recorded_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (journal_id,entity_id,currency,posting_date,source_reference,
          source_sha256,explanation,actor,digest,int(time.time())))
        for i,line in enumerate(checked,1):
            db.execute("""INSERT INTO bozly_cfo_journal_lines
              (journal_id,line_number,code,debit_minor,credit_minor)
              VALUES(?,?,?,?,?)""",
              (journal_id,i,line["code"],line["debit_minor"],
               line["credit_minor"]))
        db.commit()
    return {"entity_id":entity_id,"journal_id":journal_id,
            "posted":True,"debits_minor":dr,"credits_minor":cr,
            "journal_sha256":digest,"independently_audited":False}


def trial_balance(*,entity_id,currency,through_date=None):
    _valid_entity(entity_id,currency)
    if through_date is not None:
        date.fromisoformat(through_date)
    with _db() as db:
        chart=db.execute("""SELECT code,name,kind FROM bozly_cfo_accounts
            WHERE entity_id=? AND currency=? ORDER BY code""",
            (entity_id,currency)).fetchall()
        booked=db.execute("""SELECT l.code,SUM(l.debit_minor),SUM(l.credit_minor)
            FROM bozly_cfo_journal_lines l JOIN bozly_cfo_journals j
            ON j.journal_id=l.journal_id
            WHERE j.entity_id=? AND j.currency=?
              AND (? IS NULL OR j.posting_date<=?)
            GROUP BY l.code""",
            (entity_id,currency,through_date,through_date)).fetchall()
    indexed={code:(debit,credit) for code,debit,credit in booked}
    rows=[]
    total_debit=total_credit=0
    for code,name,kind in chart:
        d,c=indexed.get(code,(0,0))
        net=d-c
        debit=max(0,net)
        credit=max(0,-net)
        total_debit+=debit
        total_credit+=credit
        rows.append({"code":code,"name":name,"kind":kind,
                     "debit_minor":debit,"credit_minor":credit})
    return {"entity_id":entity_id,"currency":currency,"accounts":rows,
            "total_debit_minor":total_debit,"total_credit_minor":total_credit,
            "balanced":total_debit==total_credit,
            "not_audited_or_bank_reconciled":True}


def financial_statements(*,entity_id,currency,through_date=None):
    """Balance sheet and income statement from the native posted journal."""
    trial=trial_balance(entity_id=entity_id,currency=currency,through_date=through_date)
    totals={kind:0 for kind in TYPES}
    for account in trial["accounts"]:
        net=account["debit_minor"]-account["credit_minor"]
        if account["kind"] in ("LIABILITY","EQUITY","INCOME"):
            net=-net
        totals[account["kind"]]+=net
    earnings=totals["INCOME"]-totals["EXPENSE"]
    return {"entity_id":entity_id,"currency":currency,
            "assets_minor":totals["ASSET"],
            "liabilities_minor":totals["LIABILITY"],
            "equity_minor":totals["EQUITY"],
            "revenue_minor":totals["INCOME"],
            "expenses_minor":totals["EXPENSE"],
            "profit_minor":earnings,
            "accounting_equation_balanced":(
                totals["ASSET"]==totals["LIABILITY"]+
                totals["EQUITY"]+earnings
            ),
            "trial_balance":trial,
            "source":"Recorded Bozly journals; not independently audited"}


def set_budget(*,entity_id,currency,month,code,planned_net_minor,
               source_reference,actor):
    _valid_entity(entity_id,currency)
    _month(month)
    _amount(planned_net_minor,True)
    _string(source_reference,"budget source")
    _string(actor,"actor")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("""SELECT 1 FROM bozly_cfo_accounts
          WHERE entity_id=? AND currency=? AND code=?""",
          (entity_id,currency,code)).fetchone():
            raise ValueError("Unknown entity account")
        db.execute("""INSERT INTO bozly_cfo_budgets
            (entity_id,currency,month,code,planned_net_minor,
            source_reference,actor,updated_at) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(entity_id,currency,month,code) DO UPDATE SET
            planned_net_minor=excluded.planned_net_minor,
            source_reference=excluded.source_reference,
            actor=excluded.actor,updated_at=excluded.updated_at""",
            (entity_id,currency,month,code,planned_net_minor,
             source_reference,actor,int(time.time())))
        db.commit()
    return {"entity_id":entity_id,"month":month,
            "code":code,"planned_net_minor":planned_net_minor}


def budget_variance(*,entity_id,currency,month):
    _valid_entity(entity_id,currency)
    start=_month(month)
    end=date(start.year+(start.month==12),1 if start.month==12 else start.month+1,1)
    with _db() as db:
        planned=db.execute("""SELECT code,planned_net_minor FROM bozly_cfo_budgets
            WHERE entity_id=? AND currency=? AND month=? ORDER BY code""",
            (entity_id,currency,month)).fetchall()
        actual=db.execute("""SELECT l.code,
          SUM(l.debit_minor-l.credit_minor)
          FROM bozly_cfo_journal_lines l JOIN bozly_cfo_journals j
          ON j.journal_id=l.journal_id
          WHERE j.entity_id=? AND j.currency=?
          AND j.posting_date>=? AND j.posting_date<?
          GROUP BY l.code""",
          (entity_id,currency,start.isoformat(),end.isoformat())).fetchall()
    actuals=dict(actual)
    rows=[]
    for code,plan in planned:
        observed=actuals.get(code,0)
        rows.append({"code":code,"budget_net_minor":plan,
                     "actual_net_minor":observed,
                     "variance_net_minor":observed-plan})
    return {"entity_id":entity_id,"currency":currency,
            "month":month,"variances":rows,
            "actuals_are_only_posted_journal_entries":True}


def set_cash_plan(*,entity_id,currency,month,opening_cash_minor,
                  projected_inflows_minor,projected_outflows_minor,
                  source_reference,actor):
    _valid_entity(entity_id,currency)
    _month(month)
    for amount in (opening_cash_minor,projected_inflows_minor,
                   projected_outflows_minor):
        _amount(amount)
    _string(source_reference,"planning source")
    _string(actor,"actor")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_cfo_cash_forecasts
         (entity_id,currency,month,opening_cash_minor,projected_inflows_minor,
          projected_outflows_minor,source_reference,actor,updated_at)
         VALUES(?,?,?,?,?,?,?,?,?)
         ON CONFLICT(entity_id,currency,month) DO UPDATE SET
         opening_cash_minor=excluded.opening_cash_minor,
         projected_inflows_minor=excluded.projected_inflows_minor,
         projected_outflows_minor=excluded.projected_outflows_minor,
         source_reference=excluded.source_reference,actor=excluded.actor,
         updated_at=excluded.updated_at""",
         (entity_id,currency,month,opening_cash_minor,projected_inflows_minor,
          projected_outflows_minor,source_reference,actor,int(time.time())))
        db.commit()
    return cash_plan(entity_id=entity_id,currency=currency,month=month)


def cash_plan(*,entity_id,currency,month):
    _valid_entity(entity_id,currency)
    _month(month)
    with _db() as db:
        row=db.execute("""SELECT opening_cash_minor,projected_inflows_minor,
            projected_outflows_minor,source_reference,updated_at
            FROM bozly_cfo_cash_forecasts
            WHERE entity_id=? AND currency=? AND month=?""",
            (entity_id,currency,month)).fetchone()
    if not row:
        return {"entity_id":entity_id,"currency":currency,"month":month,
                "forecast_status":"NO_ACTUAL_INPUTS","projected_closing_minor":None}
    opening,inflows,outflows,source,updated=row
    return {"entity_id":entity_id,"currency":currency,"month":month,
            "opening_cash_minor":opening,"projected_inflows_minor":inflows,
            "projected_outflows_minor":outflows,
            "projected_closing_minor":opening+inflows-outflows,
            "source_reference":source,"updated_at":updated,
            "forecast_is_not_actual_bank_balance":True}
