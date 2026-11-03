# Bozly CFO — Native Sanders Finance Integration

## Scope
- Native event-driven Python financial observation engine, two isolated services
- SQLite WAL durable inbox, outbox/queue, and hash-linked event audit trail
- Stripe raw-body signature validation with timestamp tolerance and durable event-id dedup
- Server-controlled legal-entity routing: no routing from untrusted Stripe metadata
- Integer minor-unit amounts, no guessed processing fees or transfers
- No mock transactions, no unit-test workflow, no assistant-added approval gates
- Read-only evidence events are not authorization to move funds

## Setup
Use `docker-compose.bozly.yml` as an independent Compose project. It does not
replace existing Stripe webhook routes or Nginx configuration.

Provide `BOZLY_STRIPE_ROUTES_JSON` as a protected deployment secret mapping route
identifiers to legal entity, jurisdiction, and their actual distinct Stripe webhook
signing secrets. The JSON structure is:
```json
{"route-key":{"entity_id":"REGISTERED_LEGAL_ENTITY","jurisdiction":"STATE_OR_POLICY","signing_secret":"STRIPE_ISSUED_WEBHOOK_SIGNING_SECRET"}}
```
These labels are configuration schema names, not real credentials or deployed values.
Protect this secret from shell history, logs, Docker inspection, and repository commits.

Configure a real Stripe webhook destination pointing to
`https://sandersdashandseal.com/v1/telemetry/webhooks/route-key`.
This path is illustrative of the routing format and is not evidence that
a destination has been registered.

The public webhook can be routed through the Nginx location in
`deploy/bozly_nginx_location.conf`, but the snippet must be integrated
into the *actual* running proxy topology. The current repository has multiple
Nginx/Compose variants, so this change does not silently replace them.

## Accounting boundaries
Signed `invoice.paid`, `payment_intent.succeeded`, and paid Checkout events
are recorded as payment observations, not automatically as revenue or net cash
settlement. Do not add the observations across event types indiscriminately.
Invoice, payment intent, charge, fee, refund, dispute and payout reconciliation
must bind to actual Stripe balance-transaction identities when those feeds are
integrated. A separate signed account route identifies the legal entity;
each legal entity needs its own account policy/configuration.

Webhook delivery is at least once and may arrive out of order. Persistent event
IDs prevent repeat ingestion on process restart. DB constraints prevent the
same payment reference from being counted twice per entity; differing amounts
are marked as conflicts. Subscription event observations are stored separately.

Hash chaining is tamper-*evident* inside SQLite, not immutable or independently
anchored. Genuine forensic preservation needs a separately protected audit store
and periodic independent signed checkpoints when available.

## Operational truth
The source is committed but the running Oracle application has not been changed
in this operation. No payment, fee calculation, provider registration,
live API invocation, remote billing, or financial verification is claimed.
No tests were created or run.

Do not use the proposed GitHub Actions `verify-bozly-integrity.yml`: it runs
a sample transaction as a unit test and adds a blanket CI failure gate,
contrary to the owner's no-tests directive.
