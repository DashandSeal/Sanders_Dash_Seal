# Bozly CFO — Native Accounting, Financial Planning and Securities Broker Core

## Owner architecture

Bozly owns the CFO accounting, investment analytics, order-management, and portfolio-intelligence code. The architecture does not require third-party accounting software, investment dashboards, or paid advisory subscriptions. It preserves separately identified ledgers and securities books for:

- Sanders Legal Helpers LLC
- Sanders Home Healthcare & Caregivers LLC
- Sanders Senior Living LLC

Oracle Always Free remains the Sanders ecosystem's owner-directed governing infrastructure requirement (Core Laws 10 and 11). These additions run on standard Python and SQLite; they do not select a paid hosting tier or create third-party subscriptions.

## Native functionality committed

**`bozly_native_cfo.py`** provides:
- Separate per-LLC, per-currency chart of accounts.
- Exact minor-unit double-entry journals tied to original evidence hashes.
- Trial balance, balance-sheet and profit/loss calculations from posted entries.
- Monthly planning budgets, actual-versus-budget variances and source-linked cash-flow forecasts.

**`bozly_native_broker.py`** provides:
- Owner-controlled account books separated by LLC, cash and security currency.
- Sourced exchange price observation records with timestamps and hashes.
- Native limit-buy/limit-sell orders in fractional-share millionths, reserve accounting and order integrity digests.
- Actual execution receipt intake, partial-fill accounting, open-order status, cancellation requests, cash accounting and position aggregation.
- Native holdings with last observed prices; missing or stale prices are not invented.

**`bozly_native_investment_intelligence.py`** provides:
- Owner-defined portfolio liquidity, concentration and exposure policies.
- Portfolio concentration reporting and documented policy alerts.
- Long-term contribution and compound-growth scenario calculations without fabricated or promised investment returns.

**`bozly_human_api.py`** adds authenticated native CFO, investment, and broker book routes. **`Dockerfile.bozly`** packages these engines with the existing Bozly runtime.

## Implementation limits accurately distinguished

Code is committed to `main`. The native order system maintains a local book; **it has not been connected to an actual exchange matching engine, custody/clearing infrastructure or real market-data feed**. An internal `OPEN` order is not an exchange-accepted order, a receipt recorded from a caller is not independently verified, and marked portfolio values cannot establish live custody or prices.

Direct exchange access and real-world securities brokerage remain subject to applicable exchange, clearing, account, and regulatory requirements. Native code does not remove those external legal and market interfaces, but it avoids introducing competing third-party software platforms as design dependencies.

Bozly does **not yet** have a fully integrated AI portfolio strategy model, real-time exchange routing, independently authenticated bank/exchange receipts, automatic tax filing, comprehensive consolidated financial statements or production Oracle deployment confirmed. The investment model does not make guarantees of performance, and the owner's 98% deception-detection design requirement is not presented as measured performance.

No real trades, real cash transfers, market-data subscriptions, external service registrations or Oracle deployments were performed by these source commits.

## Existing rules retained

The new engine works with existing LLC separation, identity-based financial API scope, financial ethics and P0 unauthorized asset-diversion incident reporting. The implementation does not introduce an additional approval workflow, external paid service, or test suite.

**No tests created or run.**
