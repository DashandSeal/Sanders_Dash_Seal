"""BOZLY native portfolio intelligence and investment planning.

No paid investment-analysis vendor. Exact minor-unit analysis from recorded
positions, source-dated observed prices and owner-specified financial inputs.
Not real-time feed acquisition, advisory registration, or guaranteed returns.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import json
import os
from pathlib import Path
import sqlite3
from .bozly_purchasing import ENTITIES
from .bozly_native_broker import portfolio, MICRO

DB_DEFAULT="/app/secure_ledgers/bozly_financial_core.db"
M=Decimal(MICRO)


def _decimal(v,name):
    if not isinstance(v,(str,int)) or isinstance(v,bool):
        raise ValueError("Decimal "+name+" required")
    try:
        r=Decimal(str(v))
    except InvalidOperation as e:
        raise ValueError("Invalid decimal "+name) from e
    if not r.is_finite():
        raise ValueError("Nonfinite "+name)
    return r


def _cash(v,name):
    if type(v) is not int or v<0 or v>9_000_000_000_000_000:
        raise ValueError("Exact nonnegative minor units required: "+name)
    return v


def _shares(v):
    if type(v) is not int or v<=0 or v>10**14:
        raise ValueError("Exact positive millionths of a share required")
    return v


def _round_minor(x):
    return int(x.to_integral_value(rounding=ROUND_HALF_EVEN))


def _db():
    file=Path(os.environ.get("BOZLY_DB_PATH",DB_DEFAULT))
    file.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(file),timeout=20,isolation_level=None)
    db.execute("PRAGMA busy_timeout=20000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_investment_policy(
        entity_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        currency TEXT NOT NULL,
        minimum_liquidity_minor INTEGER NOT NULL,
        maximum_single_holding_bps INTEGER NOT NULL,
        maximum_equity_exposure_bps INTEGER NOT NULL,
        rebalance_threshold_bps INTEGER NOT NULL,
        thesis TEXT NOT NULL,updated_by TEXT NOT NULL,updated_at INTEGER NOT NULL,
        PRIMARY KEY(entity_id,account_id)
    );
    """)
    return db


def set_policy(*,entity_id,account_id,currency,minimum_liquidity_minor,
               maximum_single_holding_bps,maximum_equity_exposure_bps,
               rebalance_threshold_bps,thesis,actor):
    if entity_id not in ENTITIES or not isinstance(currency,str) or len(currency)!=3:
        raise ValueError("Registered LLC and currency required")
    if not all(isinstance(x,str) and x.strip() and len(x)<=1500
               for x in (account_id,thesis,actor)):
        raise ValueError("Real account, thesis and actor required")
    _cash(minimum_liquidity_minor,"minimum liquidity")
    for b in (maximum_single_holding_bps,maximum_equity_exposure_bps,
              rebalance_threshold_bps):
        if type(b) is not int or not 0<=b<=10000:
            raise ValueError("Policy basis points must be 0–10000")
    # Read native broker account ownership and currency, do not assume it.
    portfolio_data=portfolio(entity_id=entity_id,account_id=account_id)
    if portfolio_data["currency"]!=currency:
        raise ValueError("Account and policy currencies differ")
    from datetime import datetime,timezone
    now=int(datetime.now(timezone.utc).timestamp())
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO bozly_investment_policy(
          entity_id,account_id,currency,minimum_liquidity_minor,
          maximum_single_holding_bps,maximum_equity_exposure_bps,
          rebalance_threshold_bps,thesis,updated_by,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(entity_id,account_id) DO UPDATE SET
          currency=excluded.currency,
          minimum_liquidity_minor=excluded.minimum_liquidity_minor,
          maximum_single_holding_bps=excluded.maximum_single_holding_bps,
          maximum_equity_exposure_bps=excluded.maximum_equity_exposure_bps,
          rebalance_threshold_bps=excluded.rebalance_threshold_bps,
          thesis=excluded.thesis,updated_by=excluded.updated_by,
          updated_at=excluded.updated_at""",
          (entity_id,account_id,currency,minimum_liquidity_minor,
           maximum_single_holding_bps,maximum_equity_exposure_bps,
           rebalance_threshold_bps,thesis,actor,now))
        db.commit()
    return {"entity_id":entity_id,"account_id":account_id,
            "policy_recorded":True,"policy_set_by":actor}


def portfolio_analysis(*,entity_id,account_id):
    """Current recorded portfolio, concentration and liquidity diagnostics.

    Positions with no observed price are left UNMARKED; no invented market
    value or inferred zero price. No assumption that quote is still current.
    """
    book=portfolio(entity_id=entity_id,account_id=account_id)
    with _db() as db:
        policy=db.execute("""SELECT minimum_liquidity_minor,
          maximum_single_holding_bps,maximum_equity_exposure_bps,
          rebalance_threshold_bps,thesis,updated_at
          FROM bozly_investment_policy WHERE entity_id=? AND account_id=?""",
          (entity_id,account_id)).fetchone()
    holdings=book["positions"]
    priced=[x for x in holdings if x["marked_value_minor"] is not None]
    unpriced=[{"venue_mic":x["venue_mic"],"symbol":x["symbol"]}
              for x in holdings if x["marked_value_minor"] is None and x["shares_micro"]!=0]
    exposure=sum(x["marked_value_minor"] for x in priced)
    cash=book["recorded_book_cash_minor"]
    gross=exposure+cash
    concentration=[]
    if gross>0:
        for x in priced:
            bps=round(10000*x["marked_value_minor"]/gross)
            concentration.append({
                "symbol":x["symbol"],"venue_mic":x["venue_mic"],
                "weight_bps":bps,
                "mark_unix":x["quote_as_of_unix"],
            })
    liquidity=book["available_recorded_cash_minor"]
    alerts=[]
    if policy:
        min_cash,single_max,equity_max,rebalance,thesis,updated=policy
        if liquidity<min_cash:
            alerts.append({"type":"RECORDED_LIQUIDITY_BELOW_POLICY",
                           "available_minor":liquidity,
                           "required_minor":min_cash})
        for h in concentration:
            if h["weight_bps"]>single_max:
                alerts.append({"type":"RECORDED_HOLDING_CONCENTRATION",
                               "symbol":h["symbol"],
                               "weight_bps":h["weight_bps"],
                               "policy_bps":single_max})
        if gross>0:
            equity_bps=round(exposure*10000/gross)
            if equity_bps>equity_max:
                alerts.append({"type":"RECORDED_EQUITY_EXPOSURE_ABOVE_POLICY",
                               "weight_bps":equity_bps,"policy_bps":equity_max})
    else:
        thesis=None
    return {
        "entity_id":entity_id,"account_id":account_id,
        "currency":book["currency"],
        "marked_holdings_minor":exposure,
        "recorded_cash_minor":cash,
        "recorded_total_value_minor":gross if not unpriced else None,
        "available_recorded_cash_minor":liquidity,
        "holding_concentration":concentration,
        "unpriced_positions":unpriced,
        "price_observation_dates_may_be_stale":True,
        "policy_defined":bool(policy),
        "policy_thesis":thesis,
        "policy_alerts":alerts,
        "source":"Actual recorded ledger observations and owner-provided sourced prices",
        "actual_live_market_connection_confirmed":False,
    }


def compound_projection(*,starting_minor,monthly_contribution_minor,
                        months,annual_return_percent):
    """Deterministic CFO scenario math, not an expected or guaranteed return."""
    _cash(starting_minor,"starting principal")
    _cash(monthly_contribution_minor,"contribution")
    if type(months) is not int or not 0<=months<=1200:
        raise ValueError("Horizon must be 0–1200 months")
    percent=_decimal(annual_return_percent,"return percentage")
    if not Decimal("-100")<=percent<=Decimal("1000"):
        raise ValueError("Scenario percentage out of defined range")
    # An effective monthly rate from the annual scenario.
    if percent == Decimal("-100"):
        monthly=Decimal("-1")
    else:
        monthly=(Decimal("1")+percent/Decimal("100"))**(Decimal("1")/Decimal("12"))-1
    value=Decimal(starting_minor)
    rows=[]
    for m in range(1,months+1):
        value=(value+Decimal(monthly_contribution_minor))*(1+monthly)
        if m%12==0 or m==months:
            rows.append({"month":m,"scenario_balance_minor":_round_minor(value)})
    return {
        "scenario_only":True,
        "starting_minor":starting_minor,
        "monthly_contribution_minor":monthly_contribution_minor,
        "months":months,
        "annual_scenario_return_percent":str(percent),
        "projected_balance_minor":_round_minor(value),
        "annual_checkpoints":rows,
        "market_returns_predicted_or_guaranteed":False,
        "inflation_taxes_fees_not_assumed":True,
    }
