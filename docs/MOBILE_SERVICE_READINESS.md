# Sanders Dash & Seal — mobile intake and payment review

Review date: October 20, 2026 (America/Denver).
Source inspected: build/security-foundation at c1a8ffd0b2bbcd710a6e14c1076b4d904c5fff7b.

## Findings

The existing platform is preserved. Main contains the initial README; the executable foundation is on build/security-foundation in draft PR #1. No customer-facing frontend, hosting manifest, booking calendar, server-side Checkout Session creation or deployed authentication adapter was found in that branch. Sites returned no owned projects in this account. This does not establish the absence of hosting elsewhere.

The baseline suite passed 100 tests. Local inspection found no explicit mobile-notary intake category, despite the owner's mobile business model. Signed malformed payment events with a null/list data container previously raised unexpected exceptions, producing retryable server failures. Python boolean amounts could compare equal to one-cent integer registrations. Checkout registration did not validate currency format or identifier types.

## Source and acceptance criteria

Controlling source: Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md, sections 2 (notarial operating scope and human capacity), 3 law 5 (human in the loop), 13–14 (executable pairing), and 19–20 (verified outcomes and role separation). Existing payment acceptance is defined in STRIPE_INTEGRATION.md and END_TO_END_PRODUCTION_ACCEPTANCE.md.

- MOBILE_NOTARY intake must persist in the existing case registry and remain awaiting human authority review.
- A mobile case must retain independent human identity, commission/jurisdiction and applicability checks. It must not select a remote/electronic provider automatically or execute a notarial act.
- Another authenticated customer must not retrieve the case.
- Malformed payment event containers, types and boolean amounts must deny without changing payment state or consuming the event ID. A corrected retry must remain processable.
- Existing signed asynchronous payment success and duplicate delivery behavior must continue to work.
- Changed executable bytes must have matching unsigned development manifest hashes. No authority signatures may be fabricated.

## Changes and validation

Added the missing unsigned manifest for the existing l15_repair_engine.py so every executable has a paired file. Added MOBILE_NOTARY to case intake and to the authority review provider mapping (no remote provider selected). Independent verification callbacks remain mandatory. Tightened checkout registration and event validation. Added eight regression tests; 108 tests pass locally. This is local development evidence, not a live transaction or independent production verification.

## Remaining connections for paid appointments

1. Customer-facing intake and scheduling connected to independently verified authentication and protected case storage.
2. Human-approved service/fee catalog, availability, travel quote and cancellation/refund rules.
3. Independently operated signing authorities and source/dependency verification, enforced runtime isolation and external audit/backup infrastructure required by MASTER.
4. Server-side Stripe Checkout creation, protected credentials, deployed signed webhook, quote/case/session binding, refund/dispute handling and a verified complete transaction.
5. Current commission and provider verification through actual authority adapters; mobile work remains separate from electronic/remote operations.

No production keys, customer records, payment, release or deployment was created. Production readiness is not established.


## Customer-flow continuation

The same branch now includes the customer appointment page, operator quote review,
transactional case/request storage and StripeClient handoff described in
CUSTOMER_APPOINTMENTS.md. Local suite: 128 tests pass. This supersedes the absence
of customer UI in the earlier source snapshot; deployed authentication, hosting,
independent release controls and real payment configuration remain unconnected.
