# BOZLY CFO — Mandatory P0 Asset-Diversion Alert Rule
**Owner instruction: November 3, 2026**

Bozly must never secretly divert money, assets, holdings, subsidiaries, company equity, or other value. Any attempted unauthorized redirection, concealment of asset movement, financial payee tampering, or request to withhold a required alert is a **P0 suspected-diversion incident**.

On detection Bozly shall:

1. Reject execution of an unauthorized diversion or an instruction to suppress the alert. Preserve the original CEO-authorized payment mechanisms for legitimate, disclosed operations.
2. Write the incident with entity, requested operation, actor, UTC timestamp, and SHA-256 evidence digest to the durable incident ledger; do not place private account credentials into alerts.
3. Queue alerts for **the CEO, the acting CEO, every Vice President, and the human CFO** at the same detection time; initiate delivery concurrently, without office hours, nighttime delay, queuing by role, or a second manual approval.
4. Track every individual delivery independently as PENDING, RETRY, DELIVERED or UNCONFIGURED. Never claim recipients were notified merely because a record was queued or a network request attempted.
5. Retry undelivered incidents continuously while the worker is operating and service credentials are available. Keep unconfigured roles visibly outstanding until actual owner-provided identities and delivery channels exist.
6. Keep legitimate human corporate officer succession and assignment rules as stated in `docs/SANDERS_EXECUTIVE_BLOODLINE_GOVERNANCE.md`. Bozly remains synthetic CFO software; he cannot invent an acting CEO, human CFO or Vice President, nor elect new officers.

## Native implementation

- `bozly_diversion_guard.py`: records suspected-diversion incidents and P0 executive fanout in SQLite.
- `bozly_human_api.py`: authenticated `POST /bozly/v1/diversion-incident` and `POST /bozly/v1/diversion-notification-status` endpoints. These require the caller's existing legal-entity scope.
- `bozly_cfo.py`: native reconciliation worker independently retries pending incident notifications.
- `Dockerfile.bozly`: includes the native guard.

## Real transport configuration (not yet present)

Set `BOZLY_FINANCIAL_ALERT_RECIPIENTS_JSON` as protected deployment configuration containing **real** contact endpoints and credentials for each role. Format:

```json
{
  "ceo": [{"id": "AUTHORIZED_CEO_RECIPIENT_ID", "url": "https://REAL_HTTPS_DELIVERY_ENDPOINT", "token": "PROTECTED_TOKEN"}],
  "acting_ceo": [{"id": "AUTHORIZED_ACTING_CEO_RECIPIENT_ID", "url": "https://REAL_HTTPS_DELIVERY_ENDPOINT", "token": "PROTECTED_TOKEN"}],
  "vp": [{"id": "EACH_ACTUAL_VP_RECIPIENT_ID", "url": "https://REAL_HTTPS_DELIVERY_ENDPOINT", "token": "PROTECTED_TOKEN"}],
  "human_cfo": [{"id": "AUTHORIZED_HUMAN_CFO_RECIPIENT_ID", "url": "https://REAL_HTTPS_DELIVERY_ENDPOINT", "token": "PROTECTED_TOKEN"}]
}
```

The placeholders above are schema descriptions, not valid identities, actual recipients, real credentials, or live delivery destinations. For VPs, include **each actual VP**, not only one. If any role is unoccupied or not configured, record it transparently as unconfigured; the rule is never silently relaxed.

A successful HTTP response means the configured delivery gateway accepted a message; it does **not** establish that a human read or received it. Human delivery/read receipts and independent redundant communications (call, SMS, email or satellite gateway) require actual integrations. Neither perfect simultaneity nor availability during every outage can be guaranteed.

## Security and business scope

This module does not independently observe external banking portals, email conversations or all other software. To enforce the rule on additional asset-moving entrypoints, those entrypoints must call `block_and_alert` or the same incident recorder **before** carrying out a suspected unauthorized diversion. The existing purchase and international-payment code still requires founder CEO authorization for submitted transactions. Recording this rule does not authorize unapproved payments or make Bozly a bank or an appointed officer.

**No tests or CI release gates added or run. No production notification delivery claimed.**
