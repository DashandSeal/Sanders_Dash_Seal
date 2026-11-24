# Independent Phase A Retest — Dynamic Completion Pass (Supplement)

**Date:** 2026-11-24 (America/Denver)
**Scope:** the executed half of the independent Phase A retest. The first retest
(`phase-a-retest-report.md`) confirmed every claim by construction and record but
executed **zero** dynamic checks (its fresh clone timed out and the tarball tripped
the runtime execution-risk check). This pass executes those checks, with a harness
written by this retester from the claims. It does not use the builder's drive
(`verify_phase_a.py`) or the first retester's materials.
**Head under test:** `dea8dbfad60e05bdad7fa4ff401e61cb0b51000b`
**Verdict: every dynamic claim CONFIRMED by execution — 55 checks executed;
all six items pass. One initial check failure was a defect in this retester's
own simulation method (explained at Item 5), corrected and re-executed with a
control; it was not a defect in the code under test.**

## Method

- **Source of code:** the established working copy `~/workspace/notarization-build/repo`
  (owner's 2026-11-24 03:53 MST go-ahead). The copy held the Phase A builder's
  uncommitted copies of the 7 changed file pairs; they were preserved in a named,
  recoverable git stash (`phase-a-builder-local-copies-pre-retest`) and the exact
  head `dea8dbfa` was checked out clean. The runtime execution-risk check did not
  fire at any point in this pass.
- **Checkout verification (before anything ran):** for the 8 files the harness
  exercises (`core_platform/realtime_api.py`, `session_auth.py`, `voice_api.py`,
  `glass_box_audit.py`, `deploy/deployment.py`, `deploy/production_bindings.py`,
  `app/customer_app.py`, `web/video.js`), SHA-256 of the local checkout bytes ==
  SHA-256 of the bytes fetched through the GitHub API at `dea8dbfa` == the
  `body.payload_hash` of each file's `.pbd.json` manifest — **8/8 triple-match**.
- **Composition:** the composed application is the real
  `deploy.deployment.create_application(bindings)`. Bindings were assembled by
  this harness mirroring `deploy/production_bindings.py` wiring exactly — same
  modules, and its own `_stripe_client` / `_fee_verifier` /
  `_eligibility_verifier` / `_provider_clients` helpers imported and used —
  but on scratch SQLite stores under `/tmp`, because
  `create_production_bindings()` hardcodes the repo `data/` directory.
  The composed app's gate state is the real approvals file at head (0 of 9)
  through `deployment._is_approved`; no gate was approved anywhere in the
  composed app. Approved-gate behavior (Item 2) uses test-only injection into
  `create_realtime_app`, as designed.
- **Interpreter:** a Python 3.12 environment carrying the repo's dependencies
  (the system `python3` lacks `stripe` and cannot import the deployment module).
- All keys, tokens, and accounts are fictitious and exist only in scratch
  stores under `/tmp`. Nothing was pushed, edited in the repo, or deployed.

## Item 1 — F-1: the gate check is real and fail-closed — CONFIRMED (8/8)

Composed app, fictitious `LIVEKIT_*` keys present in the environment, gate
unapproved (the original inventory attack, reproduced):

| Check | Result |
|---|---|
| Unauthenticated `POST /api/realtime/token` (arbitrary room + identity) | **503 `approval_required`**, no token |
| Unauthenticated `POST /api/realtime/room` | **503 `approval_required`** |
| Authenticated (operator session) token POST | **503 `approval_required`** — the gate is evaluated before the session, exactly as designed |
| Error path: a `RealtimeConfig` whose `provider` property **raises** | **503 `approval_required`**, no token |
| Error path: the injected `gate_approved` callable **raises** | **503 `approval_required`**, no token |
| Gate unwired (`gate_approved=None`) with a provider configured | **503 `approval_required`**, no token |
| No-keys control (second composed app, no `LIVEKIT_*`/`DAILY_*` env), authenticated caller | **503 `not_configured`**, no token — the honest pre-Phase-A behavior is preserved |

## Item 2 — F-2: authentication and identity binding — CONFIRMED (9/9)

Direct realtime app with a test-only approved gate, the real `SessionAuth`
verifier and the production-wired `GlassBoxAudit` injected (as production
injects them):

- No session → **401 `sign_in_required`**.
- Foreign `Origin` → **403 `origin_denied`**.
- Body asserting a foreign identity → **403 `identity_mismatch`**, nothing minted.
- Legitimate issuance → **200** with a JWT whose **`sub` is the session account**
  (`operator1`), whose **`video` grant is scoped to the one room**
  (`room: room-alpha`, `roomJoin: true`), whose **HS256 signature verifies**
  against the configured secret, and whose response `identity` field equals the
  session account.
- A body asserting the *matching* identity also issues (200) — identity is
  bound to the session, not merely taken from the request.

## Item 3 — F-5: voice routes authenticated — CONFIRMED (6/6)

Driven through `create_voice_app` with the real session verifier (backends
`None`: the deployment's backend factory attempts optional local model
construction unrelated to the authentication claim), plus one composed-app check:

- `POST /api/voice/transcribe` signed-out → **401 `sign_in_required`**;
  `POST /api/voice/speak` signed-out → **401 `sign_in_required`**.
- Signed-in, no backend → **503 `transcriber_not_configured`** /
  **503 `synthesizer_not_configured`** (honest, no work performed).
- `GET /api/voice/status` is public and exposes backend names only
  (nulls when unconfigured; no key/secret material in the payload).
- Composed app: `POST /api/voice/transcribe` signed-out → **401
  `sign_in_required`** through the full deployment routing.

## Item 4 — F-6 slice: session rotation and lockout — CONFIRMED (11/11)

Against a scratch `SessionAuth` through its real `auth_app`:

- Setup issues a session; two subsequent logins issue two **distinct** tokens.
- After the second login, the **first login token authenticates as no one**
  (rotation), the setup token is likewise dead, and the second token
  authenticates as the account.
- Logout answers 200 and the **presented token is dead** afterwards.
- Lockout unchanged: failed attempts 1–4 → **400 `sign_in_failed`**; the 5th →
  **429 `try_again_later`**; the **correct password while locked is still
  refused** with 429 `try_again_later`.

## Item 5 — F-11: Glass Box receipts on every media decision — CONFIRMED (7 executed checks)

Receipts were read back from the production-wired chain (the same
`GlassBoxAudit` instance the composed app and the Item 2 app wrote to):

- Granted issuance receipts present (`REALTIME_TOKEN_ISSUED`, outcome granted): **2**
  (the two Item 2 issuances).
- Gate-denial receipts present (`REALTIME_TOKEN_DENIED`, reason
  `approval_required`): **4** (composed-app unauthenticated + authenticated,
  gate-raising, and gate-unwired denials; the room-POST denial lands under the
  `REALTIME_ROOM_DENIED` stage, as designed).
- `identity_mismatch` denial receipt: **1**. `sign_in_required` denial receipt: **1**.
- `verify_audit()` over that chain returns its head hash — **chain verifies**.

**Unwritable-store check — method note and one honest failure.** This retester's
first attempt simulated an unwritable store with `chmod 0444` on the audit
database and the grant was issued (200). That result is an artifact of the
test environment, not the code: the harness runs as **uid 0 (root)**, which
ignores file permission bits — a direct control confirmed an `INSERT` succeeds
on a `0444` SQLite file as root, so the store was never actually unwritable.
The check was re-executed with a simulation that fails at the same interface
regardless of privilege: a real `GlassBoxAudit` whose backing path was
replaced by a directory after construction, so every `preserve()` fails to
open the store. With a healthy-audit control issuing normally (200 + token),
the destroyed store produced **503 `audit_unavailable` with no token
delivered** — the no-record-no-token rule **CONFIRMED by execution**. (On the
production instance the app runs as the unprivileged `sanders` user, where a
permission-unwritable store fails the same way.)

## Item 6 — Regression drive of the composed app — CONFIRMED (13/13)

Against the Item 1 composed app (real bindings shape, scratch stores):

- `GET /healthz` → 200; `GET /` (storefront) → 200; `GET /appointments`
  (portal) → 200.
- Sign-in flow through the composed app: operator setup → 200 + session
  cookie; customer register → 200 + cookie; `GET /api/session` signed-in →
  200 `authenticated: true`.
- Intake `POST /api/appointments` (customer session) → **201** with a case id.
- Operator queue: signed-out → **401 `sign_in_required`**; as customer →
  **403 `operator_required`**; as operator → **200** with the new case listed.
- Operator quote → **201** with a quote id.
- Checkout with the unavailable-Stripe adapter → **409
  `checkout_unavailable`** (the pre-Phase-A shape).
- Provider POST and native POST (operator session) → **503
  `approval_required`** with `gate: ron_notarial` — the regulated track's
  gate is untouched by Phase A.

## Bottom line

The dynamic half now stands executed, not inferred: the F-1 attack that
minted a token against the old wiring is refused at the gate in the composed
application; identity is bound to the session in the minted JWT itself
(subject, room-scoped grant, and signature all verified); voice work refuses
the unsigned-in; a second login kills the first token; every media decision —
granted, gate-denied, identity-denied, sign-in-denied — is on the Glass Box
chain, and a grant whose receipt cannot be written is not delivered; and the
customer/operator surface behaves exactly as it did before Phase A, apart
from the intended media binding. **No discrepancy was found.** The single
non-pass in the first run of this pass was this retester's own invalid
simulation under root, disclosed above and corrected with a control.

*Counts: 53 checks in the main harness (52 passed as designed; the 53rd was
the invalid chmod simulation), 2 further checks in the corrected
unwritable-store execution (control + refusal, both passed), and the 8/8
checkout hash verification — 55 executed checks in the supplement's scope,
plus the method controls.*
