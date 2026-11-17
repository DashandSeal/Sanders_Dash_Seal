# Sanders Dash & Seal — customer appointment workflow

Status: implemented and locally tested development integration. Not deployed;
no real customer identity, live payment, confirmed appointment or notarial act.
This extends the existing platform and preserves MASTER and all separate roles.

## Available source

- `/appointments`: responsive mobile-notary/document-support request form,
  local-time display, owned request history, itemized quote and Checkout handoff.
- `/operator`: protected request queue and itemized quote approval interface.
- `AppointmentStore`: appointment and existing case creation in one transaction,
  consent timestamp, repeat-submission keys, time validation and private reads.
- `AppointmentPayments`: independent operator, fee and case eligibility checks;
  immutable quotes; instantiated StripeClient Checkout API; persisted exact
  request parameters and retry keys; payment-ledger binding.
- `create_customer_app`: WSGI composition with independent authentication and
  release-verification adapters. The default API behavior is HTTP 503.
- Existing `stripe_webhook_wsgi.make_app`: verifies raw signed events and uses
  the same payment ledger. Returning to the website does not mark a case paid.

Requests contain a general meeting area and preferred time, not uploaded
documents, identity numbers or a confirmed reservation. The human notary reviews
the service and confirms arrangements separately. Local libraries are not
advertised as company-owned offices or guaranteed appointment venues.

## Runtime assembly contract

Use the same protected database path for `CaseRegistry`, `AppointmentStore` and
`PaymentLedger` so appointment/case creation and session/ledger binding can commit
atomically. Supply a distinct audit component. The local GlassBoxAudit test store
does not establish production immutability.

`AppointmentPayments` requires an already instantiated StripeClient, a trusted
HTTPS site origin, and independently implemented operator, fee and case
eligibility verifiers. Quote approval accepts amounts only from the operator
route and verifies fee eligibility independently. Notarial, travel and document
support amounts are itemized; no live price catalog or legal fee determination
is supplied by the test values. Checkout defaults to expecting sandbox responses.
Do not set `expected_livemode=True` until live eligibility and release controls
are verified. Store restricted API keys and webhook signing secrets outside the
repository. No API keys were obtained or used for this development change.

Pass an independently verified session adapter and auth WSGI application to
`create_customer_app`. The auth application owns login/callback validation,
session expiration, Secure/HttpOnly/SameSite cookies, logout and login CSRF.
Do not substitute an incoming username/role header or the literal test bearer
token. Operator authority must be verified independently of customer identity.
The configured HTTPS origin is required for every JSON mutation; customer
identity, operator identity, price and paid flags cannot be supplied by clients.

`release_verifier` must be connected to the existing independently verified
startup/manifest/dependency and deployment boundary. It is an integration hook,
not a substitute for PBD signatures, Twin-Gate authorization, enforced isolation,
external audit or independently attested production evidence. Tests returning
True from this hook do not establish release permission. Mount the existing
webhook app at `/stripe/webhook` only through that same approved runtime.

The stored Checkout intent is committed before the provider call. Retries use
the same exact parameters and key. Ambiguous attempts older than 23 hours stop
for reconciliation rather than risking reuse after Stripe's idempotency retention
window. Expired quotes/sessions and an already-paid ledger cannot create another
Checkout. Operator reconciliation/quote revision, cancellation, refunds and
disputes are not yet implemented. Quote approval never authorizes or executes a
notarial act. No customer identity, signed document or notarial journal data is
included in the tests.

## Local verification

`python -m unittest discover -s tests -q` passes 128 tests, including 20 new
appointment/quote/customer-flow tests. The integration path exercises request,
operator quote approval, fake StripeClient session creation, raw signed webhook
ingress, payment-ledger update, private status retrieval and continued denial of
automatic notarial execution. Concurrency, storage rollback, missing consent,
cross-origin writes, actor/price spoofing, denied operator access, fee/eligibility
denials, provider mismatches, stable retries and expiry also have coverage.

Both frontend scripts pass `node --check`. Browser visual/interaction QA was
not run: this managed environment has no control-browser capability. All Python
and JavaScript source hashes are paired with unsigned development manifests.

## Existing hosting choice

Recovered owner choice from October 15: GoDaddy, account holder Roosevelt Sanders.
The exact hosting product/plan, domain and server configuration remain unknown.
Do not create substitute hosting or represent absence of a Sites project as
absence of the owner's GoDaddy account.

## Required to launch

Connect real customer authentication and operator identity; protect persistent
storage and secrets; implement current fee/case-authority verification; connect
independent signing and production runtime controls; configure and verify the
Stripe sandbox integration before live-mode promotion; complete refund/dispute
and operator reconciliation procedures; deploy the signed artifact; then verify
the complete transaction, failure, recovery and evidence paths. These are actual
missing connections and procedures, not permissions implied by a GitHub commit.

Official Stripe references used: https://docs.stripe.com/api/checkout/sessions/create
and https://docs.stripe.com/api/idempotent_requests .
