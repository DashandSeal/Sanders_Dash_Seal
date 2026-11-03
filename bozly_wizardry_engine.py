"""Bozly owned quantitative allocation, wealth accumulation and debt retirement.

Owner-supplied portfolios are preserved. Global yields require sourced inputs,
never invented default benchmark rates, market returns or trading fills.
All money is exact integer US cents internally; no SaaS dependencies.
"""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
from pathlib import Path

PORTFOLIOS={
    "BALANCED":{"S&P500_US_LARGE_CAP":"0.40","EURO_STOXX_600":"0.15",
                "MSCI_EMERGING_MARKETS":"0.10","GLOBAL_BONDS":"0.35"},
    "CONSERVATIVE":{"S&P500_US_LARGE_CAP":"0.20","GLOBAL_BONDS":"0.70",
                    "CASH_RESERVES":"0.10"},
}
RATE_LABEL={"AGGRESSIVE":"GLOBAL_EQUITIES_AGGR",
            "BALANCED":"GLOBAL_EQUITIES_MOD",
            "CONSERVATIVE":"FIXED_INCOME_GLOBAL"}

def _d(value):
    if isinstance(value,bool) or not isinstance(value,(str,int,Decimal)):
        raise ValueError("Exact decimal input expected")
    v=Decimal(str(value))
    if not v.is_finite(): raise ValueError("Non-finite input")
    return v

def _cents(v):
    x=_d(v)
    if x<0 or x>Decimal("90000000000000") or x.as_tuple().exponent < -2:
        raise ValueError("Exact nonnegative USD with at most two decimals required")
    return int(x*100)

def _usd(v):
    return format(Decimal(v)/100,".2f")

class BozlyWizardryEngine:
    def __init__(self,global_benchmark_yields=None,aggressive_allocations=None):
        self.global_benchmark_yields=dict(global_benchmark_yields or {})
        self.aggressive_allocations=aggressive_allocations
        self.engine_id="BOZLY-NATIVE-QUANTITATIVE-WIZARDRY"

    def compute_hash_token(self):
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def model_global_equity_allocation(self,capital_pool_usd,profile_key):
        if profile_key not in RATE_LABEL: raise ValueError("Unknown risk profile")
        allocation=PORTFOLIOS.get(profile_key,self.aggressive_allocations)
        if not isinstance(allocation,dict) or not allocation:
            raise ValueError("Owner AGGRESSIVE allocation weights not supplied")
        weighted={}
        for name,percent in allocation.items():
            if not isinstance(name,str) or not name.strip(): raise ValueError("Invalid asset")
            w=_d(percent)
            if w<0 or w>1: raise ValueError("Weight outside 0-1")
            weighted[name]=w
        if sum(weighted.values())!=1: raise ValueError("Weights must total exactly 1")
        key=RATE_LABEL[profile_key]
        if key not in self.global_benchmark_yields:
            raise ValueError("Source-backed benchmark rate required for "+key)
        rate=_d(self.global_benchmark_yields[key])
        if rate < -1: raise ValueError("Return below -100%")
        capital=_cents(capital_pool_usd)
        allocation_cents={}
        remaining=capital
        for i,(asset,weight) in enumerate(weighted.items()):
            minor=remaining if i==len(weighted)-1 else int(
                (Decimal(capital)*weight).quantize(Decimal(1),rounding=ROUND_HALF_EVEN))
            allocation_cents[asset]=minor
            remaining-=minor
        projected=int((Decimal(capital)*rate).quantize(Decimal(1),rounding=ROUND_HALF_EVEN))
        return {"allocation_model_applied":profile_key,
            "total_capital_deployed_usd":_usd(capital),
            "blended_target_cagr":str(rate),
            "benchmark_provenance":"OWNER_PROVIDED_UNVERIFIED",
            "optimized_portfolio_distribution":{k:_usd(v) for k,v in allocation_cents.items()},
            "estimated_annual_organic_inflow_usd":_usd(projected),
            "orders_submitted":False,"scenario_not_guaranteed":True}

    def model_capital_accumulation(self,initial_usd,monthly_addition_usd,years,annual_rate):
        initial=_cents(initial_usd)
        monthly_add=_cents(monthly_addition_usd)
        if type(years)!=int or not 0<=years<=100: raise ValueError("Unsupported years")
        annual=_d(annual_rate)
        if not -1<=annual<=10: raise ValueError("Unsupported scenario rate")
        rate=(Decimal(1)+annual)**(Decimal(1)/Decimal(12))-1
        wealth=Decimal(initial)
        checkpoints=[]
        for month in range(1,12*years+1):
            wealth=(wealth+monthly_add)*(1+rate)
            if month%12==0:
                checkpoints.append({"year":month//12,
                    "projected_usd":_usd(int(wealth.quantize(Decimal(1),rounding=ROUND_HALF_EVEN)))})
        return {"scenario_only":True,"initial_usd":_usd(initial),
            "monthly_addition_usd":_usd(monthly_add),"years":years,
            "annual_return_assumption":str(annual),"yearly_curve":checkpoints,
            "projected_terminal_usd":_usd(int(wealth.quantize(Decimal(1),rounding=ROUND_HALF_EVEN)))}

    def model_debt_acceleration(self,principal_usd,annual_interest_rate,
                                monthly_payment_usd,extra_payment_usd="0",max_months=1200):
        balance=Decimal(_cents(principal_usd))
        payment=Decimal(_cents(monthly_payment_usd))
        extra=Decimal(_cents(extra_payment_usd))
        annual=_d(annual_interest_rate)
        if balance<=0 or not 0<=annual<=1: raise ValueError("Invalid debt or annual rate")
        if payment+extra<=0 or type(max_months)!=int or not 1<=max_months<=1200:
            raise ValueError("Invalid monthly repayment or horizon")
        monthly=annual/12
        interest_total=Decimal(0)
        for m in range(1,max_months+1):
            interest=(balance*monthly).quantize(Decimal(1),rounding=ROUND_HALF_EVEN)
            if balance+interest<=payment+extra:
                interest_total+=interest
                return {"months_to_payoff":m,"interest_usd":_usd(int(interest_total)),
                    "remaining_usd":"0.00","paid_off":True,"scenario_only":True}
            new_balance=balance+interest-(payment+extra)
            if new_balance>=balance:
                return {"paid_off":False,"reason":"NEGATIVE_AMORTIZATION","scenario_only":True}
            balance=new_balance
            interest_total+=interest
        return {"paid_off":False,"months_simulated":max_months,
            "remaining_usd":_usd(int(balance)),"interest_usd":_usd(int(interest_total)),
            "scenario_only":True}
