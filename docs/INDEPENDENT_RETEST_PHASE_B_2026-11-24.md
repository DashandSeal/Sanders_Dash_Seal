# Independent Retest — Phase B Corrective Fix (D-1, D-2, D-3)

**Subject:** DashandSeal/Sanders_Dash_Seal at head `cf34a228a9f18beb964a55944a3967026165ae63`
**Scope:** the corrective fix for the three discrepancies found by the independent security test of the Phase B build (head `1cd6915`; report: *Independent Security Test — Phase B (Commercial Rooms Core)*, 388 executed checks, 3 discrepancies)
**Tester posture:** independent — the retester built neither the rooms nor the fix. The fixer's own verification drives were not used or read for test logic; all harnesses here are the retester's own. Strictly read-only toward the repo: no pushes, no edits, no deploys, no gate changes. Working copy left clean at `cf34a228` with the pre-existing named stash (`phase-a-builder-local-copies-pre-retest`) intact.

## Headline verdict

**All three discrepancies are CLOSED, confirmed by execution.** D-1: recording authorization now exists only in WAITING_ROOM/ACTIVE — lock and suspend strip it in the same transaction, receipted; unlock and resume land revoked; a fresh pass re-earns it; 50 barrier-synchronized authorize-vs-lock/suspend race trials produced no interleaving with an authorization standing outside the live states. D-2: the notice version is now a check, not a label — mixed-version consents cannot authorize at service or route level, a non-counting re-grant revokes a standing authorization in the same step, the append-only history is untouched, and a pre-fix store migrates and fails closed. D-3: both case-binding failures raise the identical denial at service level and return byte-identical responses over WSGI, and neither failure writes any audit receipt. No regression was found: the full lifecycle, the composed application's standard drive, and the record (gates, jurisdictions, manifests, append-only SPEC) all hold.

## Method and hash verification

- Working copy: the established staged copy (owner's 2026-11-24 03:53 MST go-ahead), checked out clean at `cf34a228`; the named stash was preserved untouched.
- Before executing anything, the exercised files were verified three ways — local SHA-256 == GitHub-API-at-head SHA-256 == `.pbd.json` manifest `payload_hash`:
  - `core_platform/rooms.py` — `37cf53aa…` triple-match ✓ (changed by the fix)
  - `app/customer_app.py` — `10d71e65…` triple-match ✓ (changed by the fix)
  - `deploy/deployment.py` — `7a636751…` triple-match ✓ (unchanged source)
  - `deploy/production_bindings.py` — `359d18bc…` triple-match ✓ (unchanged source)
- The composed application under test is the real `deployment.create_application(bindings)`, with bindings assembled on scratch stores mirroring `deploy/production_bindings.py` wiring exactly (its own `_stripe_client` / `_fee_verifier` / `_eligibility_verifier` / `_provider_clients` helpers imported and used), including the real approvals file (0/9 gates approved) driving the provider/native/realtime gates, and fictitious `LIVEKIT_*` keys set.
- The legacy-store test built a rooms store with the **pre-fix** `rooms.py` (extracted from head `1cd6915`), drove a room to AUTHORIZED under the old code, then opened the same store with the fixed service.
- The runtime's execution-risk check never fired; everything below was executed, not merely read.

## Executed check totals

| Suite | Checks | Result |
|---|---|---|
| Service level (D-1, D-2, D-3, lifecycle regression) | 51 | 51/51 |
| — of which barrier-synchronized race trials (30 authorize-vs-lock + 20 authorize-vs-suspend) | 50 trials | 0 invariant violations |
| Legacy pre-fix store (migration + fail-closed) | 11 | 11/11 |
| Composed application (routes, D-3 byte-identity, standard regression drive) | 34 | 34/34 |
| **Total executed** | **96** | **96/96** |

Plus record verifications (§5) performed by read-back and diff inspection.

## 1. D-1 — CLOSED: recording authorization survives only in the live states

Executed at service level and again through the composed application's routes:

- Authorize in WAITING_ROOM → AUTHORIZED; `activate` (WAITING_ROOM→ACTIVE) **preserves** the live authorization — the one transition the fix must not revoke, and does not.
- `lock` → state LOCKED, recording_state NOT_AUTHORIZED, with a `ROOM_RECORDING_REVOKED` receipt carrying reason `room_locked` on the audit chain. `unlock` → back in ACTIVE, still NOT_AUTHORIZED. Authorize attempted while LOCKED refuses.
- `suspend` → NOT_AUTHORIZED, receipted `room_suspended`. `resume` → lands in WAITING_ROOM (never ACTIVE) with the authorization revoked — the fresh-authorization-pass semantics SPEC decision (7) always described.
- After unlock and after resume, a fresh authorization pass on the still-unanimous canonical consents succeeds — revocation is a state correction, not a lockout.
- Lock from WAITING_ROOM likewise revokes; unlock returns to WAITING_ROOM revoked.
- The pre-existing revocations still hold: evidence hold and end strip the authorization as before.
- **Races:** two RoomService instances on one store, barrier-synchronized authorize-vs-lock (30 trials) and authorize-vs-suspend (20 trials). In every trial the final state satisfies **AUTHORIZED ⇒ room in WAITING_ROOM or ACTIVE**. Zero violations.

The fix's construction matches its claim: `transition()` revokes — inside the same `BEGIN IMMEDIATE` transaction, before commit — on *any* target outside `RECORDING_AUTHORIZABLE_STATES`, so there is no ordering in which the room leaves the live states still holding the authorization.

## 2. D-2 — CLOSED: the notice version is enforced

- Each room carries a canonical `consent_notice_version`: the platform default `v1` (`DEFAULT_CONSENT_NOTICE_VERSION`) unless set at creation (`notice-2026.1` verified stored and exposed in the room view). Malformed, empty, and non-string versions at creation refuse.
- **Mixed versions cannot authorize:** host GRANTED under the canonical version + participant GRANTED under `v2-other` → `authorize_recording` refuses, state unchanged — at service level and, repeated through the routes, at the WSGI level (400 `room_denied`, then unanimous canonical consent authorizes with 200).
- **A non-counting grant revokes a standing authorization in the same step:** with the room AUTHORIZED, the participant's re-grant under `v9-stale` immediately returns recording_state to NOT_AUTHORIZED, receipted `ROOM_RECORDING_REVOKED` / `consent_changed`. Refusal and withdrawal still revoke as before.
- **Append-only history is untouched:** after the full sequence, the room's consent rows hold every version ever recorded (`v1`, `v2-other`, `v9-stale`) with no row deleted or rewritten — non-counting consents are preserved on the record and excluded by re-derivation at authorization time, exactly as the fix describes.
- Re-earning works: a canonical re-grant after the stale one restores authorizability.
- **Legacy store fails closed:** a store built by the pre-fix code (no `consent_notice_version` column, a room standing AUTHORIZED under the old rules) migrates at construction — column added, pre-existing rooms' canonical version NULL. On the migrated store: authorize refuses even though the recorded consents are unanimous GRANTED `v1` (nothing matches a NULL canonical), and *fresh* `v1` consents recorded under the fixed code still cannot authorize that room. New rooms created on the migrated store receive the canonical default and authorize normally. One bounded observation, not a discrepancy: migration does not retroactively rewrite the historical `AUTHORIZED` value the old code recorded on that room — the fail-closed property the fix claims is about authorization, and it holds (the state cannot be newly earned or re-earned, and the first consent event or non-live transition under the fixed code revokes it). The point is also moot for production: Phase B is not deployed, so no pre-fix production rooms store exists.

## 3. D-3 — CLOSED: case-binding refusals are indistinguishable

- **Service level:** binding another customer's case and binding a nonexistent case both raise `RoomDenied` with the identical message `Case cannot be bound` — same exception type, same string.
- **Route level:** as customer bob through the composed app, `POST /api/rooms` with alice's real case_id and with a nonexistent case_id return the **identical status line and byte-identical bodies** (`400 {"error":"room_denied","detail":"Case cannot be bound"}`).
- **Audit receipts do not reintroduce the distinction:** repeating both failures leaves the audit chain's receipt count unchanged — neither failure writes any receipt (case validation precedes the creation transaction), so there is no caller-visible artifact in which the two cases differ.
- The legitimate paths still work: the owner binds her own case (jurisdiction CO inherited, verified at both levels) and an operator binds any case.

## 4. Regressions — CONFIRMED

- **Lifecycle:** full drives still pass (schedule/open/activate/lock/unlock/suspend/resume/end/archive; cancel from DRAFT); invalid transitions refuse (double-open, activate from DRAFT, schedule without a start, any transition from ARCHIVED); a PROHIBITED-policy room refuses authorization despite unanimous canonical consent; consent on another's behalf remains forbidden for a non-participant operator; NOTARIAL type and NOTARY role still refuse; the audit chain verifies end-to-end in every suite.
- **Composed application standard drive:** `/healthz` 200; storefront `/` 200; portal `/appointments` 200; intake → 201 with case id; operator queue 401 signed-out / 403 as customer / 200 as operator with the case listed; operator quote → 201; checkout → **409 `checkout_unavailable`**; provider POST → **503 `approval_required`** (`ron_notarial`); native POST → **503 `approval_required`**; realtime token POST with fictitious LiveKit keys → **503 `approval_required`**; voice transcribe signed-out → 401; unwired-rooms composition → **503 `rooms_unavailable`**.

## 5. Record — CONFIRMED

- **SPEC append-only:** `git diff 1cd6915..cf34a228 -- docs/SPEC_CONFORMANCE.md` contains **zero removed lines**; the corrective entry is appended after the Phase B entry, which stands unedited. The entry names the test, quotes the three discrepancies, states the corrections and the residuals it deliberately did not decide (R-A consent-under-hold stays open as an owner design question; R-B/R-C untouched) — the record matches the code as executed.
- **Intervening automated commit `d1d39c9`:** the characterization is accurate. Its diff touches only the four `.pbd.json` manifests (`app/customer_app.py`, `core_platform/rooms.py`, `deploy/deployment.py`, `deploy/production_bindings.py`) and in each removes exactly the file's trailing newline (`\ No newline at end of file`); no `payload_hash`, no source file, and no other content changed.
- **Manifests:** every source file changed across `1cd6915..cf34a228` with a manifest pair matches it — `core_platform/rooms.py`, `app/customer_app.py`, `docs/SPEC_CONFORMANCE.md` (SHA-256 == `payload_hash`), in addition to the four-file triple-match in §Method.
- **Gates:** `ai_platform_approvals.json` — **9/9 UNAPPROVED** (ai_role_workers, anthropic_live_model, daedalus_live, gateway_workflow_fix, grantwriter_purpose, release_verifier_pr2_checkout, ron_notarial, stripe_live_keys, voice_video_provider); the composed app enforced `ron_notarial` and `voice_video_provider` as unapproved during the drive.
- **Jurisdictions:** `APPROVED_RON_JURISDICTIONS` remains the empty frozenset (`core_platform/global_compliance.py`).

## Scope limits, stated plainly

- Verified in-process against scratch stores and fictitious keys, through the real composed application — **not deployed, not live**. Nothing here establishes production behavior; the fix rides the owner's gated deploy path with the Phase B build.
- The media plane was not and cannot be tested: the `voice_video_provider` gate is unapproved and rooms mint no tokens. D-1's closure is a control-plane invariant — the authorization record can no longer describe a non-live room as authorized — which is the property Phase C will inherit.
- The legacy store was constructed with the genuine pre-fix module extracted from head `1cd6915`, not a hand-built schema, so the migration path tested is the one a real pre-fix store would take.
- Race trials ran two service instances on one store in-process (the same shape as the original test); they do not measure cross-process timing on the production host.

## Bottom line

The corrective fix closes all three discrepancies by execution, not by description: the recording authorization is now a property of a live, continuously authorized room (D-1); consent counts only against the notice version the room itself carries, with history preserved and nothing rewritten (D-2); and room creation can no longer be used as a case-existence oracle, at the service, over the wire, or in the audit record (D-3). The original test's reproductions were re-run in substance and now refuse at every step. **D-1 CLOSED, D-2 CLOSED, D-3 CLOSED — 96/96 executed checks, 50/50 race trials, record verified.** The Phase B control plane, as corrected, stands as its SPEC entry records it.
