"""BOZLY native securities broker and investment book.

Owned native order management, securities quotes, entity-segregated portfolio,
cleared-cash evidence, order reservations and real venue execution records.
No external analytics platform, subscription, invented trading data, fake
positions, broker registration claim or automatic execution claim.

The operating entity must separately possess the applicable authority to
conduct regulated brokerage and exchange activity. Venue connectivity is an
exchange-access requirement, not a dependency on another brokerage product.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from .bozly_purchasing import ENTITIES

DB_DEFAULT="/app/secure_ledgers/bozly_financial_core.db"
MICRO=1_000_000
_ID=re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:/@+-]{0,127}$")
_SYMBOL=re.compile(r"^[A-Z0-9][A-Z0-9.^/-]{0,31}$")
_CURRENCY=re.compile(r"^[A-Z]{3}$")
_SHA=re.compile(r"^[a-f0-9]{64}$")
_ORDER_TYPES=("LIMIT",)
_STATES=("OPEN","PARTIALLY_FILLED","FILLED","CANCEL_REQUESTED","CANCELLED")


class BrokerBookError(ValueError):
    pass


def _field(value,label,pattern=_ID):
    if not isinstance(value,str) or not pattern.fullmatch(value):
        raise BrokerBookError("Invalid "+label)
    return value


def _money(v,label,positive=False):
    if type(v) is not int or v< (1 if positive else 0) or v>9_000_000_000_000_000:
        raise BrokerBookError("Invalid exact minor-unit "+label)
    return v


def _qty(v):
    if type(v) is not int or not 0<v<=10**14:
        raise BrokerBookError("Quantity must be positive integer millionths of a share")
    return v


def _notional(quantity_micro,price_minor):
    # A conservative charge reservation; no binary floating point.
    return (quantity_micro*price_minor+MICRO-1)//MICRO


def _digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,
        separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def _db():
    file=Path(os.getenv("BOZLY_DB_PATH",DB_DEFAULT))
    file.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(file),timeout=20,isolation_level=None)
    c.execute("PRAGMA busy_timeout=20000")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_security_quotes (
      quote_id TEXT PRIMARY KEY,venue_mic TEXT NOT NULL,symbol TEXT NOT NULL,
      currency TEXT NOT NULL,price_minor INTEGER NOT NULL CHECK(price_minor>0),
      observed_unix INTEGER NOT NULL,source_reference TEXT NOT NULL,
      source_sha256 TEXT NOT NULL,recorded_at INTEGER NOT NULL,
      UNIQUE(venue_mic,symbol,currency,observed_unix,source_reference)
    );
    CREATE INDEX IF NOT EXISTS bozly_quote_lookup
      ON bozly_security_quotes(venue_mic,symbol,currency,observed_unix DESC);

    CREATE TABLE IF NOT EXISTS bozly_broker_accounts (
      account_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,currency TEXT NOT NULL,
      account_reference TEXT NOT NULL,created_at INTEGER NOT NULL,
      UNIQUE(entity_id,currency,account_reference)
    );
    CREATE TABLE IF NOT EXISTS bozly_broker_cash_events (
      event_id TEXT PRIMARY KEY,account_id TEXT NOT NULL
         REFERENCES bozly_broker_accounts(account_id),
      direction TEXT NOT NULL CHECK(direction IN ('CREDIT','DEBIT')),
      amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
      source_reference TEXT NOT NULL,source_sha256 TEXT NOT NULL,
      event_kind TEXT NOT NULL,actor TEXT NOT NULL,recorded_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bozly_broker_orders (
      order_id TEXT PRIMARY KEY,account_id TEXT NOT NULL
         REFERENCES bozly_broker_accounts(account_id),
      venue_mic TEXT NOT NULL,symbol TEXT NOT NULL,currency TEXT NOT NULL,
      side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
      order_type TEXT NOT NULL CHECK(order_type='LIMIT'),
      quantity_micro INTEGER NOT NULL CHECK(quantity_micro>0),
      limit_price_minor INTEGER NOT NULL CHECK(limit_price_minor>0),
      filled_micro INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,trade_reason TEXT NOT NULL,
      actor TEXT NOT NULL,order_digest TEXT NOT NULL,
      created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS bozly_broker_orders_active
      ON bozly_broker_orders(account_id,symbol,venue_mic,status);
    CREATE TABLE IF NOT EXISTS bozly_broker_executions (
      execution_id TEXT PRIMARY KEY,order_id TEXT NOT NULL
         REFERENCES bozly_broker_orders(order_id),
      venue_mic TEXT NOT NULL,executed_micro INTEGER NOT NULL,
      executed_price_minor INTEGER NOT NULL,
      gross_minor INTEGER NOT NULL,fee_minor INTEGER NOT NULL,
      execution_at_unix INTEGER NOT NULL,source_sha256 TEXT NOT NULL,
      recorded_at INTEGER NOT NULL
    );
    """)
    return c


def _account(db,account_id,entity_id):
    row=db.execute("SELECT entity_id,currency FROM bozly_broker_accounts WHERE account_id=?",
                   (account_id,)).fetchone()
    if row is None or row[0]!=entity_id:
        raise PermissionError("Broker account does not belong to the authenticated LLC")
    return row


def register_account(*,account_id,entity_id,currency,account_reference):
    """An internal LLC book; not a claim of real exchange/custody membership."""
    if entity_id not in ENTITIES:
        raise BrokerBookError("Unknown Sanders legal entity")
    _field(account_id,"account id")
    _field(account_reference,"account reference")
    _field(currency,"currency",_CURRENCY)
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_broker_accounts
                   (account_id,entity_id,currency,account_reference,created_at)
                   VALUES(?,?,?,?,?)""",
                   (account_id,entity_id,currency,account_reference,int(time.time())))
        db.commit()
    return {"account_id":account_id,"entity_id":entity_id,"currency":currency,
            "book_registered":True,"external_broker_account_verified":False}


def record_market_price(*,quote_id,venue_mic,symbol,currency,
                        price_minor,observed_unix,source_reference,source_sha256):
    """Ingest observed real price provenance; no fake or polling feed."""
    for v,n in ((quote_id,"quote id"),(venue_mic,"MIC"),
                (source_reference,"source reference")):
        _field(v,n)
    _field(symbol,"symbol",_SYMBOL)
    _field(currency,"currency",_CURRENCY)
    _field(source_sha256,"source sha256",_SHA)
    _money(price_minor,"price",True)
    if (type(observed_unix) is not int or observed_unix<=0 or
        observed_unix>int(time.time())+120):
        raise BrokerBookError("Invalid genuine observation timestamp")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_security_quotes
                   (quote_id,venue_mic,symbol,currency,price_minor,observed_unix,
                   source_reference,source_sha256,recorded_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                   (quote_id,venue_mic,symbol,currency,price_minor,observed_unix,
                    source_reference,source_sha256,int(time.time())))
        db.commit()
    return {"quote_id":quote_id,"symbol":symbol,"currency":currency,
            "observed_price_minor":price_minor,"observed_unix":observed_unix,
            "live_stream_connected":False,"source_authenticated_externally":False}


def record_cash_movement(*,entity_id,account_id,event_id,direction,amount_minor,
                          source_reference,source_sha256,event_kind,actor):
    """Record genuine externally settled cash evidence into Bozly's own book.

    This records the asserted source receipt but does not itself move bank money
    or independently authenticate the issuing bank.
    """
    if direction not in ("CREDIT","DEBIT"):
        raise BrokerBookError("Cash movement must be CREDIT or DEBIT")
    for v,n in ((event_id,"event id"),(source_reference,"cash source"),
                (event_kind,"event kind"),(actor,"actor")):
        _field(v,n)
    _field(source_sha256,"SHA-256 evidence",_SHA)
    _money(amount_minor,"amount",True)
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        _account(db,account_id,entity_id)
        if direction=="DEBIT" and amount_minor>_cash_balance(db,account_id):
            raise BrokerBookError("Ledger cash insufficient for recorded debit")
        db.execute("""INSERT INTO bozly_broker_cash_events
                   (event_id,account_id,direction,amount_minor,source_reference,
                   source_sha256,event_kind,actor,recorded_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                   (event_id,account_id,direction,amount_minor,
                    source_reference,source_sha256,event_kind,actor,int(time.time())))
        db.commit()
    return {"event_id":event_id,"account_id":account_id,"amount_minor":amount_minor,
            "direction":direction,"actual_bank_transfer_performed":False,
            "source_bank_confirmation_independently_verified":False}


def _cash_balance(db,account_id):
    posted=db.execute("""SELECT COALESCE(SUM(CASE WHEN direction='CREDIT'
        THEN amount_minor ELSE -amount_minor END),0)
        FROM bozly_broker_cash_events WHERE account_id=?""",
        (account_id,)).fetchone()[0]
    fills=db.execute("""SELECT COALESCE(SUM(CASE WHEN o.side='BUY'
        THEN -(x.gross_minor+x.fee_minor)
        ELSE x.gross_minor-x.fee_minor END),0)
        FROM bozly_broker_executions x
        JOIN bozly_broker_orders o ON o.order_id=x.order_id
        WHERE o.account_id=?""",(account_id,)).fetchone()[0]
    return posted+fills


def _shares(db,account_id,venue_mic,symbol):
    return db.execute("""SELECT COALESCE(SUM(CASE WHEN o.side='BUY'
        THEN x.executed_micro ELSE -x.executed_micro END),0)
        FROM bozly_broker_executions x JOIN bozly_broker_orders o
        ON o.order_id=x.order_id
        WHERE o.account_id=? AND o.venue_mic=? AND o.symbol=?""",
        (account_id,venue_mic,symbol)).fetchone()[0]


def _reservations(db,account_id,venue_mic=None,symbol=None):
    active=("OPEN","PARTIALLY_FILLED","CANCEL_REQUESTED")
    rows=db.execute("""SELECT side,venue_mic,symbol,quantity_micro,
        filled_micro,limit_price_minor FROM bozly_broker_orders
        WHERE account_id=? AND status IN (?,?,?)""",
        (account_id,*active)).fetchall()
    cash=0
    remaining_shares=0
    for side,mic,sym,qty,filled,price in rows:
        outstanding=qty-filled
        if side=="BUY":
            cash+=_notional(outstanding,price)
        elif venue_mic==mic and symbol==sym:
            remaining_shares+=outstanding
    return cash,remaining_shares


def create_limit_order(*,entity_id,account_id,order_id,venue_mic,symbol,
                       side,quantity_micro,limit_price_minor,trade_reason,actor):
    """Native order book reservation, not claimed market submission.

    No new arbitrary owner approval queue. Caller access is authorized by
    the existing authenticated CFO API. Orders cannot be claimed executed
    until the real execution evidence is received.
    """
    for v,n in ((order_id,"order id"),(venue_mic,"venue MIC"),(actor,"actor")):
        _field(v,n)
    _field(symbol,"security symbol",_SYMBOL)
    if not isinstance(trade_reason,str) or not trade_reason.strip() or len(trade_reason)>3000:
        raise BrokerBookError("Real investment rationale required")
    if side not in ("BUY","SELL"):
        raise BrokerBookError("BUY or SELL required")
    _qty(quantity_micro)
    _money(limit_price_minor,"limit price",True)
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        _,currency=_account(db,account_id,entity_id)
        cash_reserved,shares_reserved=_reservations(db,account_id,venue_mic,symbol)
        if side=="BUY":
            if _notional(quantity_micro,limit_price_minor)>(
                _cash_balance(db,account_id)-cash_reserved
            ):
                raise BrokerBookError("Insufficient available recorded cash after open orders")
        else:
            if quantity_micro>_shares(db,account_id,venue_mic,symbol)-shares_reserved:
                raise BrokerBookError("Insufficient available recorded shares")
        terms={
            "entity_id":entity_id,"account_id":account_id,"order_id":order_id,
            "venue_mic":venue_mic,"symbol":symbol,"currency":currency,
            "side":side,"order_type":"LIMIT","quantity_micro":quantity_micro,
            "limit_price_minor":limit_price_minor,"trade_reason":trade_reason,
        }
        now=int(time.time())
        db.execute("""INSERT INTO bozly_broker_orders
                   (order_id,account_id,venue_mic,symbol,currency,side,order_type,
                   quantity_micro,limit_price_minor,status,trade_reason,actor,
                   order_digest,created_at,updated_at)
                   VALUES(?,?,?,?,?,?, 'LIMIT',?,?,'OPEN',?,?,?,?,?)""",
                   (order_id,account_id,venue_mic,symbol,currency,side,
                    quantity_micro,limit_price_minor,trade_reason,actor,
                    _digest(terms),now,now))
        db.commit()
    return {**terms,"status":"OPEN","sent_to_exchange":False,
            "trade_filled":False,"terms_sha256":_digest(terms)}


def record_execution(*,entity_id,order_id,execution_id,venue_mic,
                     executed_micro,executed_price_minor,fee_minor,
                     executed_at_unix,source_sha256):
    """Ingest a distinct actual venue fill receipt for the native order book."""
    _field(execution_id,"external execution id")
    _field(venue_mic,"MIC")
    _field(source_sha256,"evidence digest",_SHA)
    _qty(executed_micro)
    _money(executed_price_minor,"execution price",True)
    _money(fee_minor,"executed fee")
    if (type(executed_at_unix) is not int or executed_at_unix<=0
        or executed_at_unix>int(time.time())+120):
        raise BrokerBookError("Invalid execution timestamp")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("""SELECT a.entity_id,o.account_id,o.venue_mic,
            o.side,o.quantity_micro,o.filled_micro,o.limit_price_minor,o.status
            FROM bozly_broker_orders o JOIN bozly_broker_accounts a
            ON a.account_id=o.account_id WHERE o.order_id=?""",
            (order_id,)).fetchone()
        if row is None or row[0]!=entity_id:
            raise PermissionError("Order not owned by this LLC")
        _,account_id,expected_mic,side,qty,filled,limit,status=row
        if expected_mic!=venue_mic or status not in (
            "OPEN","PARTIALLY_FILLED","CANCEL_REQUESTED"
        ):
            raise BrokerBookError("Venue or order state incompatible with receipt")
        if executed_micro>qty-filled:
            raise BrokerBookError("Cannot overfill native order")
        if side=="BUY" and executed_price_minor>limit:
            raise BrokerBookError("Buy execution violates limit price")
        if side=="SELL" and executed_price_minor<limit:
            raise BrokerBookError("Sell execution violates limit price")
        gross=_notional(executed_micro,executed_price_minor)
        if side=="BUY":
            other_reserved,_=_reservations(db,account_id)
            # Remaining order reservations include the current fill's limit,
            # which is consumed by this execution. Fees may need extra cash.
            current_reserve=_notional(qty-filled,limit)
            free=_cash_balance(db,account_id)-(other_reserved-current_reserve)
            if gross+fee_minor>free:
                raise BrokerBookError("Recorded book cash cannot cover fill and fees")
        else:
            if gross<fee_minor:
                raise BrokerBookError("Execution fees exceed recorded sale proceeds")
        now=int(time.time())
        db.execute("""INSERT INTO bozly_broker_executions
                   (execution_id,order_id,venue_mic,executed_micro,
                   executed_price_minor,gross_minor,fee_minor,
                   execution_at_unix,source_sha256,recorded_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                   (execution_id,order_id,venue_mic,executed_micro,
                    executed_price_minor,gross,fee_minor,executed_at_unix,
                    source_sha256,now))
        new_filled=filled+executed_micro
        new_status="FILLED" if new_filled==qty else "PARTIALLY_FILLED"
        db.execute("""UPDATE bozly_broker_orders SET filled_micro=?,
                   status=?,updated_at=? WHERE order_id=?""",
                   (new_filled,new_status,now,order_id))
        db.commit()
    return {"execution_id":execution_id,"order_id":order_id,
            "executed_micro":executed_micro,"gross_minor":gross,
            "fee_minor":fee_minor,"status":new_status,
            "venue_evidence_sha256":source_sha256,
            "cash_or_stock_settled_at_external_custodian":False}


def request_cancel(*,entity_id,order_id,actor):
    _field(actor,"actor")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("""SELECT o.status FROM bozly_broker_orders o
           JOIN bozly_broker_accounts a ON a.account_id=o.account_id
           WHERE o.order_id=? AND a.entity_id=?""",(order_id,entity_id)).fetchone()
        if not row:
            raise PermissionError("Order not found for entity")
        if row[0] not in ("OPEN","PARTIALLY_FILLED"):
            raise BrokerBookError("This order cannot request cancellation")
        db.execute("""UPDATE bozly_broker_orders
                   SET status='CANCEL_REQUESTED',updated_at=? WHERE order_id=?""",
                   (int(time.time()),order_id))
        db.commit()
    return {"order_id":order_id,"status":"CANCEL_REQUESTED",
            "exchange_cancellation_confirmed":False}


def confirm_cancel(*,entity_id,order_id,source_sha256):
    _field(source_sha256,"evidence sha256",_SHA)
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("""SELECT o.status FROM bozly_broker_orders o
           JOIN bozly_broker_accounts a ON a.account_id=o.account_id
           WHERE o.order_id=? AND a.entity_id=?""",(order_id,entity_id)).fetchone()
        if not row:
            raise PermissionError("Order not found for entity")
        if row[0]!="CANCEL_REQUESTED":
            raise BrokerBookError("No cancellation request in progress")
        db.execute("UPDATE bozly_broker_orders SET status='CANCELLED',updated_at=? WHERE order_id=?",
                   (int(time.time()),order_id))
        db.commit()
    return {"order_id":order_id,"status":"CANCELLED",
            "cancellation_source_sha256":source_sha256}


def portfolio(*,entity_id,account_id):
    """Native recorded portfolio: not verified custody or guaranteed live prices."""
    with _db() as db:
        _,currency=_account(db,account_id,entity_id)
        cash=_cash_balance(db,account_id)
        reserved,_=_reservations(db,account_id)
        positions=db.execute("""SELECT o.venue_mic,o.symbol,
            SUM(CASE WHEN o.side='BUY' THEN x.executed_micro ELSE -x.executed_micro END)
            FROM bozly_broker_executions x JOIN bozly_broker_orders o
            ON x.order_id=o.order_id
            WHERE o.account_id=?
            GROUP BY o.venue_mic,o.symbol ORDER BY o.venue_mic,o.symbol""",
            (account_id,)).fetchall()
        holdings=[]
        for mic,symbol,shares in positions:
            quote=db.execute("""SELECT price_minor,observed_unix,source_sha256
                FROM bozly_security_quotes WHERE venue_mic=? AND symbol=?
                AND currency=? ORDER BY observed_unix DESC LIMIT 1""",
                (mic,symbol,currency)).fetchone()
            holdings.append({
                "venue_mic":mic,"symbol":symbol,"shares_micro":shares,
                "last_observed_price_minor":quote[0] if quote else None,
                "quote_as_of_unix":quote[1] if quote else None,
                "quote_source_sha256":quote[2] if quote else None,
                "marked_value_minor":(shares*quote[0]//MICRO) if quote else None,
            })
    return {
        "account_id":account_id,"entity_id":entity_id,"currency":currency,
        "recorded_book_cash_minor":cash,"reserved_buy_cash_minor":reserved,
        "available_recorded_cash_minor":cash-reserved,
        "positions":holdings,"independently_verified_custody":False,
        "prices_not_guaranteed_realtime":True,
    }
