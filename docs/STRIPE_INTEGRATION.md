# Sanders Dash & Seal — Stripe development boundary

Status: **DEVELOPMENT ONLY — NOT LIVE INTEGRATED OR PRODUCTION AUTHORIZED.**

Source precedence: the owner's `Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md` controls. This module does not override the Humanitarian Core Laws, Twin-Gate authorization, jurisdiction/capacity checks, or the PBD execution boundary.

## Scope and acceptance evidence

- `core_platform/stripe_payments.py` prepares server-authorized hosted Checkout parameters for one-time services. It does **not** call Stripe or create a live charge.
- Verify the Stripe signature on **raw bytes** using the endpoint signing secret and a timestamp tolerance before parsing or trusting an event.
- Persist Stripe event IDs with a unique constraint; duplicate delivery is harmless.
- Associate completed payments only with a pre-registered case, exact Checkout Session ID, amount and currency. A completed event marked unpaid does not mark a case paid.
- Payment is **never** proof of notarial authority or eligibility and must not automatically release a notarial act.
- Secrets must come from protected deployment configuration, never the repository. No live keys, customer data, real webhook endpoints or live transactions are used in tests.
- Current adapter is an isolated, testable boundary. Missing: authenticated human/customer case registry, verified provider access, approved price catalog, actual Stripe API session creation, protected webhook ingress, refund/dispute lifecycle, external immutable audit, PBD-authorized runtime, independent security assessment and deployment. Production stays blocked.

## Verification

Run `python -m unittest discover -s tests -v`. The paired `.pbd.json` manifests are unsigned development evidence, **not** permission to execute in production.
