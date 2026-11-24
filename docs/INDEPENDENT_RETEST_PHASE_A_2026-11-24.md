# Independent Security Retest — Phase A Remediation (P0 Human-Workflows Program)

**Retester:** independent, fresh eyes, adversarial posture. The builder's drive (`verify_phase_a.py`) was not opened or used; the inventory agent's probe instrument was not used. All checks below are my own, written from the claims in the Phase A SPEC entry and the Phase 1 findings (F-1/F-2/F-5/F-6/F-11).
**Repo / head:** `DashandSeal/Sanders_Dash_Seal`, main head `dea8dbfad60e05bdad7fa4ff401e61cb0b51000b`.
**Date:** 2026-11-24.

---

## Method note — and an execution limitation, stated plainly

A fresh `git clone` of the head timed out and left only a `.git` skeleton (no working tree); the tarball fallback for the same tree then **failed the runtime's execution-risk check**, with an instruction not to run, extract, import, or execute that content and not to make exceptions on my own. I complied. I did **not** execute any repo module in this retest.

Everything below was therefore verified by the two means that remained:

1. **Plain-text reading of the exact head files**, fetched individually through the GitHub API at commit `dea8dbfa` (byte counts and blob SHAs recorded by the API): `core_platform/realtime_api.py` (15,964 B), `core_platform/voice_api.py` (18,469 B), `core_platform/session_auth.py` (15,057 B), `core_platform/livekit_realtime.py` (18,892 B), `core_platform/glass_box_audit.py` (3,752 B), `core_platform/global_compliance.py` (30,416 B), `deploy/deployment.py` (39,054 B), `deploy/production_bindings.py` (9,975 B), `web/video.js` (10,854 B), `core_platform/ai_platform_approvals.json` (2,083 B), `docs/SPEC_CONFORMANCE.md` (221,995 B).
2. **API record verification**: SHA-256 of API-fetched file bytes against each file's `.pbd.json` manifest; commit file-lists for the three Phase A commits; a byte-prefix diff of `SPEC_CONFORMANCE.md` between the prior head (`1a8e04bb`) and this head.

**Consequence for the verdicts:** claims about code construction, ordering, and the record are fully testable by these means and are verdicted below. Claims that are inherently dynamic (the live attack reproduction, JWT delivery, audit-failure simulation, session-rotation behavior, the composed-app regression drive) are marked **CONFIRMED BY CONSTRUCTION — dynamic reproduction not executed**, with the exact code path that determines the outcome quoted or cited by line. They should be re-run dynamically by an agent whose scratch copy clears the execution-risk check (the owner's 2026-11-24 03:53 MST working-copy go-ahead is on record in the program history) before anyone calls this retest dynamically complete. I do not smooth this over: **0 dynamic checks were executed; all dynamic-sounding builder numbers (60/60) remain the builder's, not mine.**

No discrepancy was found in any claim at the code or record level.

---

## Claim 1 — F-1: gate enforced inside `create_realtime_app`; the inventory attack is closed; error paths deny

**Verdict: CONFIRMED BY CONSTRUCTION — dynamic reproduction not executed (see method note).**

- `core_platform/realtime_api.py`, `_gate_denial()`: reads `config.provider` inside `try/except` — **any exception returns `"gate_check_failed"`, which denies**. If the provider is not `"none"`, approval is `bool(gate_approved())` with `gate_approved is None` counting as **False**, and **any exception from the gate callable also sets `approved = False`**. Unapproved/unwired/erroring → denial, 503 with `_approval_payload()` (`approval_required`, gate `voice_video_provider`). This is exactly the claimed fail-closed semantics, including the config-whose-provider-raises case: `RealtimeConfig.provider` is a `@property` (livekit_realtime.py line 261) and is now read as a property, never called.
- The inventory's attack, traced through the code: fictitious `LIVEKIT_*` env → `RealtimeConfig.from_env()` sets all three LiveKit flags → `provider` returns `"livekit"` (livekit_realtime.py lines 262–263) → provider ≠ `"none"` → the gate is consulted → `ai_platform_approvals.json` at head shows `voice_video_provider` **UNAPPROVED** → the deployment-injected `gate_approved=lambda: _is_approved("voice_video_provider")` (deployment.py line 424; `_is_approved` itself fails closed on any exception, lines 103–107) returns False → `_issuance_guard` returns the 503 **before** session, origin, or any call to `issue_token`. No token can be minted on this path.
- The defective router block is gone: in `deploy/deployment.py`, the string `.provider()` occurs **only** inside the history comment at line 567. The realtime branch (line ~558) now delegates unconditionally to the per-instance `realtime_app()` with `authenticate`, `audit`, `gate_approved`, and `allowed_origins=SITE_ORIGINS` injected (lines 419–426).
- One precision note (not a discrepancy): when **no** provider is configured, the gate is not consulted and an unauthenticated token request is answered **401 `sign_in_required`** (the session check is next in the guard order) rather than the pre-fix 503 `not_configured`; an authenticated caller still reaches the honest `not_configured` 503 from the client. Issuance is impossible in both branches.

## Claim 2 — F-2: order gate → session → origin → binding; identity is the session account; JWT subject and room scoping; video.js

**Verdict: CONFIRMED by code reading (dynamic issuance not executed).**

- `_issuance_guard` (realtime_api.py) runs in exactly the claimed order: gate denial → session (`_session_identity`, unwired authenticator returns None → **401 `sign_in_required`**) → origin (`allowed_origins is not None and Origin not in set` → **403 `origin_denied`**) → returns the session identity. Both POST `/api/realtime/room` and POST `/api/realtime/token` pass through it before any client call.
- Binding: in the token handler, `asserted = data.get("identity")`; `asserted is not None and asserted != identity` → the denial is recorded and **403 `identity_mismatch`** returned **before** `livekit.issue_token` is called — nothing is minted. An omitted identity is bound to the session identity.
- The minted token (livekit_realtime.py, mint function): payload `"sub": identity` (the session identity passed in), `"iss": api_key`, fresh `jti`, TTL-bound `exp`, and the video grant carries `"room": room` with `roomJoin: True` — scoped to the one room. Grant capability defaults are the residual under Claim 7.
- `web/video.js`: no identity is constructed or sent — the grep for identity construction finds only the explanatory comment (line ~197: "No identity is sent: the server binds the token to the signed-in…") and the display of the server-returned `data.identity`. The `'user-' + room` self-assertion is gone.

## Claim 3 — F-5: voice transcribe/speak authenticated; honest 503s; status exposes names only

**Verdict: CONFIRMED by code reading.**

- `core_platform/voice_api.py`: `_guard` (session → origin) runs **before** any transcription/synthesis work on both POST `/api/voice/transcribe` and POST `/api/voice/speak`; an unwired authenticator refuses every call (**401 `sign_in_required`**, fail closed, lines ~100–123); foreign origin → 403 `origin_denied`.
- Signed in with no backend wired: transcribe answers **503 `transcriber_not_configured`** (line ~153) and speak the synthesizer equivalent (line ~173) — honest backend 503s, as claimed.
- `GET /api/voice/status` is public and returns backend **names only** (`transcriber.name if transcriber else None`, synthesizer likewise, line ~131) — no keys, URLs, or configuration values.

## Claim 4 — F-6 slice: rotation at login; logout and lockout as before; constant-time setup comparison

**Verdict: CONFIRMED by code reading.**

- Rotation: `SessionAuth._open_session` (session_auth.py line ~152) executes `DELETE FROM sds_sessions WHERE username = ?;` **before** inserting the new token, with the F-6 comment stating the intent. Login, register, and setup all issue sessions through this single method, so a second login invalidates the first session's token server-side (the old token's row no longer exists; `authenticate` also deletes expired tokens on sight, line ~114). The new token is unaffected (inserted after the delete, same transaction scope of the caller's connection handling).
- Logout (line ~291): deletes only the presented token — unchanged from before, as claimed.
- Lockout: `_check_password` (lines 167–199) — failed-attempt counter increments, `locked_until = now + LOCKOUT_SECONDS` once `failed >= MAX_FAILED_ATTEMPTS`, locked accounts raise `try_again_later`, success resets the counter. Behavior preserved; the password hash comparison itself also uses `hmac.compare_digest` (line 182).
- Setup token (lines ~266–276): `provided = data['setup_token']`; the check is `not self.setup_token or not isinstance(provided, str) or not hmac.compare_digest(provided, self.setup_token)` → 503 `setup_unavailable`. The `isinstance` guard runs **before** `compare_digest`, so non-string input (int/list/dict/null) cannot raise a TypeError out of the comparison and cannot be coerced into acceptance; an unset setup token also denies. Constant-time comparison confirmed by reading.

## Claim 5 — F-11: every issuance decision audited; chain verifies; a grant whose receipt cannot be written is not issued

**Verdict: CONFIRMED by code reading + interface verification (audit-failure simulation not executed).**

- Coverage: `_record` is invoked on **every** decision path in realtime_api.py — gate denial, sign-in denial, origin denial, identity mismatch, `not_configured`, `unavailable`, room granted, token granted — with fields `room`, `identity`, `gate="voice_video_provider"`, `outcome`, and `reason` (denials) under stage names `REALTIME_TOKEN_ISSUED` / `REALTIME_TOKEN_DENIED` / `REALTIME_ROOM_CREATED` / `REALTIME_ROOM_DENIED`.
- Interface compatibility (checked because a signature mismatch would silently break this): `GlassBoxAudit.preserve(self, event, **kwargs)` (glass_box_audit.py) accepts the single positional dict that `_record` passes — `audit.preserve({"stage": stage, **fields})` — storing it as the receipt's `event` with an empty context; the receipt is hash-chained (`previous_hash` from the last row, genesis `0×64`, `BEGIN IMMEDIATE` insert). `verify_audit()` recomputes every block's digest and link and raises `Denied` on mismatch — the chain-verification mechanism the claim relies on exists and matches.
- Fail-closed grant: after a successful client operation, `if not _record(...granted...)` → **503 `audit_unavailable`** and the success response (including the token) is **not** returned. An unwired audit (`audit is None`) makes `_record` return False, so in the bare module no grant can ever be issued — fail closed by construction. (See Residual R-1 for the mint-ordering nuance.)

## Claim 6 — Regressions and the record

**Verdict: record CONFIRMED via API; dynamic regression drive NOT EXECUTED (method note).**

- **Manifests: 7/7 MATCH.** SHA-256 of the API-fetched bytes at head equals `body.payload_hash` in each `.pbd.json` for: `core_platform/realtime_api.py` (`abac96aa…`), `core_platform/session_auth.py` (`8c998fa2…`), `core_platform/voice_api.py` (`964b65d8…`), `deploy/deployment.py` (`02676d09…`), `deploy/production_bindings.py` (`d26b96fa…`), `web/video.js` (`ff788702…`), `docs/SPEC_CONFORMANCE.md` (`e12295c6…`). All manifests remain `UNSIGNED_SOURCE_MANIFEST`.
- **SPEC append-only: CONFIRMED.** `SPEC_CONFORMANCE.md` at the prior head (`1a8e04bb`, 215,721 bytes) is a **strict byte prefix** of the file at this head (221,995 bytes); the appended 6,274 bytes are exactly the Phase A entry, which is present with its residual-limitations section. No prior entry was altered.
- **Gates: 9/9 UNAPPROVED** in `core_platform/ai_platform_approvals.json` at head (ai_role_workers, anthropic_live_model, daedalus_live, gateway_workflow_fix, grantwriter_purpose, release_verifier_pr2_checkout, ron_notarial, stripe_live_keys, voice_video_provider — every `status` is `UNAPPROVED`, all approval fields null).
- **Jurisdictions: empty.** `core_platform/global_compliance.py` line 227: `APPROVED_RON_JURISDICTIONS: frozenset = frozenset()`.
- **Phase A commits touch no workflow files: CONFIRMED.** Via the API: `3694057a` (modules) — realtime_api, session_auth, voice_api + manifests; `bbb47871` (wiring) — deployment.py, production_bindings.py, web/video.js + manifests; `dea8dbfa` (SPEC) — SPEC_CONFORMANCE.md + manifest. Fourteen files total, none under `.github/workflows/`.
- **Static regression bound:** the Phase A commits did not modify `app/customer_app.py` or any portal/operator/provider/native module, so the code behind healthz, storefront, portal, intake, operator queue/quote/checkout, and the provider/native `ron_notarial` 503 shapes is byte-identical to the prior head except for deployment.py's media wiring. The composed-app drive itself (status codes exercised live) was **not** re-run by me and remains verified only by the builder's drive.

## Claim 7 — Scope honesty: F-7 stands open; named residuals as stated

**Verdict: CONFIRMED.**

- **F-7 stands open, behavior unchanged either way:** POST `/api/realtime/signaling/validate` in realtime_api.py still calls `validate_video_session` + `validate_signaling_message` — shape validation only, no session, origin, gate, or ledger check was added, and none was removed. `core_platform/daedalus_voice.py` (which holds `validate_video_session`) is **not** among the Phase A commits' files, so its behavior is byte-identical to the prior head. The SPEC entry declares F-7 open and outside the change's enumerated scope — accurate.
- **Residual (1), token grant scoping defaults: as stated.** The mint function defaults `can_publish=True`, `can_subscribe=True`, `can_publish_data=True`, and `issue_token` passes the defaults — grants keep the LiveKit client's existing defaults; no per-participant scoping was added.
- **Residual (2), Daedalus turn route unwired: as stated.** deployment.py `voice_apps()` constructs `create_daedalus_voice_app(runtime=None, …)` with the comment that POST /api/voice/turn therefore answers 503 `daedalus_runtime_not_configured`; the route received no session binding in this change, exactly as the SPEC residual declares.

---

## Residuals I found that the builder did not name

- **R-1 — Mint-before-receipt ordering (observation, not a discrepancy).** In the token handler, `livekit.issue_token(...)` is called **before** the grant receipt is written; if the receipt fails, the handler returns 503 `audit_unavailable` and the token string is discarded. Because LiveKit JWTs are stateless, "not issued" holds in the only sense that matters — the token is never delivered to a caller. But the no-record-no-token rule currently depends on this return-path discipline; a future refactor that returns the token earlier would break it silently. Worth a comment or a reorder (record-then-mint is impossible for a grant receipt that should describe a delivered token; the clean fix is minting into a local, recording, and only then responding — which is what the code does — so this is a fragility note for maintainers, not a defect).
- **R-2 — Denial receipts depend on the wired composition.** When `audit is None` (bare module / diagnostic startup with no bindings), `_record` returns False and denials are still answered but **not recorded**. No grant can escape recording in that state (grants fail with `audit_unavailable`), and the production wiring always injects the bindings' `GlassBoxAudit` (production_bindings.py line 190, exposed as `bindings.audit` line 230; deployment.py line 423), so the "every denial is recorded" claim holds for the deployed composition — but it is a property of the wiring, not of the module alone. The SPEC entry's phrasing ("every denial is recorded") does not make this distinction.
- **R-3 — Unauthenticated answer changed on the unconfigured path.** With no provider configured, an unauthenticated token/room request now answers 401 `sign_in_required` instead of the pre-fix 503 `not_configured` (gate is consulted only when a provider exists). Harmless and arguably more correct, but it is a behavior change the SPEC entry does not mention.
- **R-4 — This retest's own limit.** All dynamic reproductions (the F-1 attack POST, foreign-origin and identity-mismatch POSTs, JWT decoding of a live issuance, audit-store failure simulation, second-login invalidation, and the composed-app regression drive) were **not executed** because the recovered head tree failed the runtime's execution-risk check and I was instructed not to execute it. The construction evidence for each is cited to the line above, but construction is not execution; the program's own standard (demonstrated execution) requires one dynamic pass by an authorized agent to close this retest.

---

## Bottom line

At the level of code and record, the Phase A claims are **true**: the gate now lives in the module that mints and fails closed on unapproved, unwired, and erroring evaluation alike; issuance is session-bound, origin-checked, identity-bound, and audit-gated; the voice routes are authenticated; login rotation and the constant-time setup comparison are in the code as described; F-7 and both named residuals are exactly as the builder declared; and the record (7/7 manifests, append-only SPEC, 9/9 gates unapproved, empty jurisdictions, no workflow files) verifies independently. The one open item is this retest's own: the dynamic reproductions were blocked by an execution-risk check on the recovered tree and must be run — by an agent working in a copy that clears that check — before the retest is called dynamically complete.
