"""Native Bozly CFO procurement for three separately accounted Sanders LLCs.

CEO-authorized purchase orders, invoice-based merchant payments, exact cents,
auditable business rationale, and optional intercompany expense allocations.
No external purchasing SaaS or assistant-created approval chain.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ENTITIES = {
    "sanders_legal_helpers": "Sanders Legal Helpers LLC",
    "sanders_home_healthcare": "Sanders Home Healthcare & Caregivers LLC",
    "sanders_senior_living": "Sanders Senior Living LLC",
}
DB_FILE = "bozly_financial_core.db"


class PurchaseError(RuntimeError):
    pass


def _db():
    path = Path(os.environ.get("BOZLY_DB_PATH", "/app/secure_ledgers/" + DB_FILE))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=20000")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_purchases (
        order_id TEXT PRIMARY KEY,
        paying_entity TEXT NOT NULL,
        merchant_id TEXT NOT NULL,
        merchant_invoice TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        necessity_reason TEXT NOT NULL,
        evidence_reference TEXT NOT NULL,
        amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
        currency TEXT NOT NULL,
        beneficiary_allocations_json TEXT NOT NULL,
        destination_token TEXT NOT NULL,
        line_items_json TEXT NOT NULL,
        request_digest TEXT NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,
        creator_subject TEXT NOT NULL,
        ceo_subject TEXT,
        ceo_authorized_at INTEGER,
        provider_reference TEXT,
        submitted_at INTEGER,
        settled_at INTEGER,
        bank_receipt_id TEXT,
        created_at INTEGER NOT NULL,
        UNIQUE(paying_entity,merchant_id,merchant_invoice)
    );
    CREATE TABLE IF NOT EXISTS bozly_purchase_events (
        event_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL REFERENCES bozly_purchases(order_id),
        event_type TEXT NOT NULL,
        event_digest TEXT NOT NULL,
        recorded_at INTEGER NOT NULL
    );
    """ )
    return conn


def _payload_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _order_row(conn, order_id: str):
    row = conn.execute(
        """SELECT paying_entity,amount_minor,currency,request_digest,status,
                  ceo_subject,idempotency_key,destination_token,
                  merchant_id,merchant_invoice,provider_reference
           FROM bozly_purchases WHERE order_id=?""",(order_id,)
    ).fetchone()
    if row is None:
        raise KeyError("Unknown Bozly purchase order")
    return row


def create_purchase(
    *, order_id: str, paying_entity: str, merchant_id: str,
    merchant_invoice: str, description: str, category: str,
    necessity_reason: str, evidence_reference: str, amount_minor: int,
    currency: str, destination_token: str, line_items: list,
    beneficiary_allocations_minor: dict[str,int], creator_subject: str,
) -> dict:
    """Record intended expenditure with one accountable paying LLC.

    Beneficiary allocations support all three LLCs and must sum exactly to
    the gross amount. They are expense attribution, NOT actual funding
    transfers, debts or blanket guarantees by other LLCs.
    """
    if paying_entity not in ENTITIES:
        raise ValueError("Paying entity must be one of the three Sanders LLCs")
    strs=(order_id,merchant_id,merchant_invoice,description,category,
          necessity_reason,evidence_reference,destination_token,creator_subject)
    if not all(isinstance(v,str) and 0<len(v.strip())<=1024 for v in strs):
        raise ValueError("Purchase identifiers, necessity, evidence and destination required")
    if type(amount_minor) is not int or amount_minor<=0:
        raise ValueError("Purchase total must be a positive integer amount in minor units")
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha():
        raise ValueError("Three-letter ISO currency required")
    if not isinstance(line_items,list) or not line_items or len(line_items)>500:
        raise ValueError("At least one real item/service line required")
    line_sum=0
    for item in line_items:
        if not isinstance(item,dict):
            raise ValueError("Invalid purchase item")
        if (not isinstance(item.get("description"),str) or not item["description"].strip()
                or type(item.get("amount_minor")) is not int or item["amount_minor"]<0):
            raise ValueError("Each item needs a description and exact nonnegative cents")
        line_sum+=item["amount_minor"]
    if line_sum!=amount_minor:
        raise ValueError("Itemized amounts, including tax and shipping, must sum to total")
    if (not isinstance(beneficiary_allocations_minor,dict)
            or not beneficiary_allocations_minor
            or any(k not in ENTITIES or type(v) is not int or v<0
                   for k,v in beneficiary_allocations_minor.items())
            or sum(beneficiary_allocations_minor.values())!=amount_minor):
        raise ValueError("Three-LLC beneficiary allocations must sum to exact total")
    currency=currency.upper()
    authorized_payload={
        "order_id":order_id,"paying_entity":paying_entity,
        "merchant_id":merchant_id,"merchant_invoice":merchant_invoice,
        "description":description,"category":category,
        "necessity_reason":necessity_reason,
        "evidence_reference":evidence_reference,"amount_minor":amount_minor,
        "currency":currency,"destination_token":destination_token,
        "line_items":line_items,
        "beneficiary_allocations_minor":beneficiary_allocations_minor,
    }
    digest=_payload_digest(authorized_payload)
    key=hashlib.sha256(("bozly-purchase:"+order_id+":"+digest).encode()).hexdigest()
    now=int(time.time())
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """INSERT INTO bozly_purchases (
            order_id,paying_entity,merchant_id,merchant_invoice,description,
            category,necessity_reason,evidence_reference,amount_minor,currency,
            beneficiary_allocations_json,destination_token,line_items_json,
            request_digest,idempotency_key,status,creator_subject,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?,'REQUESTED',?,?)""",
            (order_id,paying_entity,merchant_id,merchant_invoice,description,
             category,necessity_reason,evidence_reference,amount_minor,currency,
             json.dumps(beneficiary_allocations_minor,sort_keys=True),destination_token,
             json.dumps(line_items,separators=(",",":")),digest,key,creator_subject,now)
        )
        conn.commit()
    return {"order_id":order_id,"paying_entity":paying_entity,"status":"REQUESTED",
            "amount_minor":amount_minor,"currency":currency,
            "purchase_digest":digest}


def ceo_authorize_purchase(*, order_id: str, ceo_subject: str,
                           authorized_purchase_digest: str) -> dict:
    """One real CEO authorization for exactly the prepared purchase terms."""
    if not isinstance(ceo_subject,str) or not ceo_subject:
        raise PermissionError("Authenticated CEO identity required")
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row=_order_row(conn,order_id)
        entity,amount,currency,digest,status,_,_,_,_,_,_=row
        if digest!=authorized_purchase_digest:
            raise PurchaseError("Purchase terms changed; CEO authority does not match")
        if status=="AUTHORIZED":
            return {"order_id":order_id,"status":status}
        if status!="REQUESTED":
            raise PurchaseError("Purchase already submitted, cancelled or otherwise processed")
        conn.execute(
            """UPDATE bozly_purchases SET status='AUTHORIZED',
               ceo_subject=?,ceo_authorized_at=? WHERE order_id=?""",
            (ceo_subject,int(time.time()),order_id)
        )
        conn.commit()
    return {"order_id":order_id,"status":"AUTHORIZED",
            "approved_by":ceo_subject,"amount_minor":amount,
            "currency":currency,"paying_entity":entity}


def _funding_route(entity: str) -> dict:
    """Banking rail per LLC. No credentials or external accounts are assumed."""
    data=json.loads(os.environ.get("BOZLY_PURCHASE_ROUTES_JSON","{}"))
    route=data.get(entity)
    if not isinstance(route,dict):
        raise PurchaseError("No real purchasing payment rail configured for "+entity)
    endpoint,token=route.get("endpoint"),route.get("bearer_token")
    parsed=urlsplit(endpoint or "")
    if not (parsed.scheme=="https" and parsed.hostname and token
            and not parsed.username and not parsed.password and not parsed.fragment):
        raise PurchaseError("Real authenticated HTTPS merchant payment rail required")
    return route


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def submit_authorized_purchase(order_id: str) -> dict:
    """Send one CEO-authorized order to the paying LLC's actual payment rail.

    Asynchronous/ambiguous outcomes stay unknown; there is no blind retry.
    Provider responses are observations, never evidence of a settled charge.
    """
    with _db() as conn:
        row=_order_row(conn,order_id)
    entity,amount,currency,digest,status,ceo,key,destination,merchant,invoice,ref=row
    if status!="AUTHORIZED":
        return {"order_id":order_id,"status":status,"submitted":False}
    if not ceo:
        raise PurchaseError("Missing CEO authorization")
    route=_funding_route(entity)
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        updated=conn.execute(
            """UPDATE bozly_purchases SET status='SUBMISSION_UNKNOWN'
               WHERE order_id=? AND status='AUTHORIZED'""",(order_id,)
        ).rowcount
        conn.commit()
    if not updated:
        return {"order_id":order_id,"status":"ALREADY_IN_PROGRESS"}
    request_body=json.dumps({
        "order_id":order_id,"paying_entity":entity,"amount_minor":amount,
        "currency":currency,"merchant_id":merchant,"merchant_invoice":invoice,
        "destination_token":destination,"idempotency_key":key,
        "authorized_purchase_digest":digest,
    },separators=(",",":")).encode()
    req=urllib.request.Request(
        route["endpoint"], data=request_body, method="POST",
        headers={
            "Authorization":"Bearer "+route["bearer_token"],
            "Content-Type":"application/json",
            "Idempotency-Key":key,
            "Accept":"application/json",
        }
    )
    opener=urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirect(),
    )
    try:
        with opener.open(req,timeout=20) as response:
            if not 200<=response.status<300:
                raise PurchaseError("Payment rail did not accept order")
            raw=response.read(65537)
            if len(raw)>65536:
                raise PurchaseError("Payment rail response exceeds size limit")
            result=json.loads(raw)
            external_ref=result.get("payment_id")
            if (not isinstance(external_ref,str) or not external_ref
                    or result.get("status") not in {"accepted","submitted","processing"}):
                raise PurchaseError("Payment rail outcome is not confirmed")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError,
            PurchaseError, KeyError):
        return {"order_id":order_id,"status":"SUBMISSION_UNKNOWN",
                "submitted":False,"message":"Reconcile bank idempotency key before retrying"}
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """UPDATE bozly_purchases SET status='SUBMITTED',
               provider_reference=?,submitted_at=? WHERE order_id=?
               AND status='SUBMISSION_UNKNOWN'""",
            (external_ref,int(time.time()),order_id)
        )
        conn.commit()
    return {"order_id":order_id,"status":"SUBMITTED",
            "payment_reference":external_ref,"settled":False}


def reconcile_bank_purchase_receipt(
    *, order_id: str, bank_event_id: str, payment_reference: str,
    payment_key: str, amount_minor: int, currency: str,
    outcome: str, actual_bank_receipt_digest: str
) -> dict:
    """Record an external financial institution's settled/returned payment fact.

    This function must only be called by a genuine authenticated bank connector.
    It does not itself authenticate bank webhooks or settle any funds.
    """
    if outcome not in {"SETTLED", "RETURNED", "FAILED"}:
        raise ValueError("Unsupported bank outcome")
    if (not all(isinstance(x,str) and x for x in
                (order_id, bank_event_id, payment_reference, payment_key, currency))
            or type(amount_minor) is not int or amount_minor<0
            or len(actual_bank_receipt_digest)!=64
            or any(c not in "0123456789abcdef" for c in actual_bank_receipt_digest)):
        raise ValueError("Bank settlement identity and exact evidence required")
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row=conn.execute(
            """SELECT paying_entity,amount_minor,currency,status,
               provider_reference,idempotency_key FROM bozly_purchases WHERE order_id=?""",
            (order_id,)
        ).fetchone()
        if row is None:
            raise KeyError("Unknown Bozly order")
        entity, expected, expected_currency, state, provider_ref, order_key=row
        if order_key!=payment_key or expected_currency!=currency.upper():
            raise PurchaseError("Receipt does not match the authorized order")
        if provider_ref and provider_ref!=payment_reference:
            raise PurchaseError("Receipt payment reference conflicts with order")
        prior=conn.execute(
            "SELECT order_id,event_type,event_digest FROM bozly_purchase_events WHERE event_id=?",
            (bank_event_id,)
        ).fetchone()
        if prior:
            if prior!=(order_id,outcome,actual_bank_receipt_digest):
                raise PurchaseError("Conflicting bank event identity")
            return {"order_id":order_id,"status":state,"duplicate":True}
        if state not in {"SUBMITTED","SUBMISSION_UNKNOWN","SETTLED"}:
            raise PurchaseError("Order not submitted to a real payment gateway")
        if state=="SETTLED" and outcome!="SETTLED":
            raise PurchaseError("Later reversal must be a separately classified ledger event")
        new_state=outcome
        if outcome=="SETTLED" and amount_minor!=expected:
            new_state="AMOUNT_DISCREPANCY"
        conn.execute(
            """INSERT INTO bozly_purchase_events
            (event_id,order_id,event_type,event_digest,recorded_at)
            VALUES (?,?,?,?,?)""",
            (bank_event_id,order_id,outcome,actual_bank_receipt_digest,int(time.time()))
        )
        conn.execute(
            """UPDATE bozly_purchases SET status=?,provider_reference=?,
               bank_receipt_id=?,
               settled_at=CASE WHEN ?='SETTLED' THEN ? ELSE settled_at END
               WHERE order_id=?""",
            (new_state,payment_reference,bank_event_id,
             new_state,int(time.time()),order_id)
        )
        conn.commit()
    return {"order_id":order_id,"entity_id":entity,"status":new_state,
            "actual_amount_minor":amount_minor,"currency":currency.upper(),
            "settlement_reference":bank_event_id}


def monthly_settled_spending(*, paying_entity: str, month: str) -> dict:
    """Cents spent, settled in calendar month UTC, with grounded necessity.

    Pending purchases and ambiguous payment requests are excluded.
    """
    from datetime import datetime, timezone
    if paying_entity not in ENTITIES:
        raise ValueError("Unknown Sanders LLC")
    start=datetime.strptime(month,"%Y-%m").replace(tzinfo=timezone.utc)
    if start.strftime("%Y-%m")!=month:
        raise ValueError("Expected YYYY-MM")
    year,month_number=start.year,start.month
    end=datetime(year+(month_number==12),month_number%12+1,1,tzinfo=timezone.utc)
    with _db() as conn:
        paid=conn.execute(
            """SELECT order_id,merchant_id,merchant_invoice,amount_minor,currency,
               category,necessity_reason,evidence_reference,settled_at,
               bank_receipt_id,beneficiary_allocations_json
               FROM bozly_purchases
               WHERE paying_entity=? AND status='SETTLED'
               AND settled_at>=? AND settled_at<? ORDER BY settled_at,order_id""",
            (paying_entity,int(start.timestamp()),int(end.timestamp()))
        ).fetchall()
        pending=conn.execute(
            """SELECT status,currency,COUNT(*),COALESCE(SUM(amount_minor),0)
               FROM bozly_purchases
               WHERE paying_entity=? AND status NOT IN ('SETTLED','FAILED','RETURNED')
               GROUP BY status,currency ORDER BY status,currency""",
            (paying_entity,)
        ).fetchall()
    totals={}
    by_category={}
    line_items=[]
    for (oid,merchant,invoice,cents,curr,category,why,evidence,
         settled_at,receipt,allocations) in paid:
        totals[curr]=totals.get(curr,0)+cents
        by_category.setdefault(curr,{})
        by_category[curr][category]=by_category[curr].get(category,0)+cents
        line_items.append({
            "order_id":oid,"merchant_id":merchant,"invoice_reference":invoice,
            "amount_minor":cents,"currency":curr,
            "category":category,"necessity_reason":why,
            "necessity_evidence":evidence,"bank_receipt_id":receipt,
            "beneficiary_allocations_minor":json.loads(allocations),
            "settled_at":datetime.fromtimestamp(settled_at,timezone.utc).isoformat(),
        })
    return {
        "entity_id":paying_entity,"month":month,
        "basis":"reported financial institution settlement receipts",
        "settled_total_minor_by_currency":totals,
        "settled_expenses":line_items,
        "spending_by_category_minor":by_category,
        "outstanding_status_counts":[
            {"status":status,"currency":curr,"count":count,"amount_minor":cents}
            for status,curr,count,cents in pending
        ],
        "note":"Necessity is recorded from the business reason and evidence; "
               "provider bank receipts must be independently authentic, "
               "and these figures are not a complete GAAP financial statement.",
    }


def monthly_purchases(*, paying_entity: str, month: str) -> dict:
    """Monthly overview of cent-exact expense intents and proven settlements."""
    if paying_entity not in ENTITIES:
        raise ValueError("Unknown Sanders LLC")
    if len(month)!=7 or month[4]!="-":
        raise ValueError("Use YYYY-MM")
    from datetime import datetime,timezone
    first=datetime.strptime(month,"%Y-%m").replace(tzinfo=timezone.utc)
    if first.strftime("%Y-%m")!=month:
        raise ValueError("Use YYYY-MM")
    end=datetime(first.year+(first.month==12),first.month%12+1,1,
                 tzinfo=timezone.utc)
    start_ts,end_ts=int(first.timestamp()),int(end.timestamp())
    with _db() as conn:
        rows=conn.execute(
            """SELECT order_id,merchant_id,amount_minor,currency,
               necessity_reason,evidence_reference,status,
               beneficiary_allocations_json,ceo_authorized_at,
               settled_at,provider_reference
               FROM bozly_purchases WHERE paying_entity=?
               AND created_at>=? AND created_at<?
               ORDER BY created_at,order_id""",
            (paying_entity,start_ts,end_ts)
        ).fetchall()
    entries=[]
    totals={}
    for order,merchant,amount,currency,why,evidence,status,allocation,ceo_at,settled,provider in rows:
        entries.append({
            "order_id":order,"merchant_id":merchant,
            "amount_minor":amount,"currency":currency,
            "why_necessary":why,"evidence_reference":evidence,
            "status":status,"ceo_authorized_at":ceo_at,
            "beneficiary_allocations_minor":json.loads(allocation),
            "settled_at":settled,"provider_reference":provider,
        })
        totals.setdefault(currency,{"requested_minor":0,"submitted_minor":0,"settled_minor":0})
        totals[currency]["requested_minor"]+=amount
        if status=="SUBMITTED":
            totals[currency]["submitted_minor"]+=amount
        if status=="SETTLED":
            totals[currency]["settled_minor"]+=amount
    return {
        "entity_id":paying_entity,"month":month,"expenses":entries,
        "totals_minor_by_currency":totals,
        "warning":"Submitted transactions are not confirmed settlement. "
                  "Beneficiary allocations do not transfer money or make LLCs jointly liable.",
    }
