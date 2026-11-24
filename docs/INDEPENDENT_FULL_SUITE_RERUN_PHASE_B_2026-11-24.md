# Full-Suite Independent Re-Run — Phase B (Owner Sequence Item 4)

**Subject:** DashandSeal/Sanders_Dash_Seal at head `5c6db34273d9128337b52d376900c3f72f7098b8` (branch head verified identical before and after the run; no advancement occurred)
**Scope:** the complete original Phase B security suite (388 checks + 120 concurrency trials) re-executed fresh against the corrected + remediated code, plus targeted regression tests for the remediation (R-B superseded invites, R-C removal indistinguishability, the Glass Box rooms reconciler in `core_platform/rooms_reconciliation.py`)
**Tester posture:** independent — not the builder, the original tester, the fixer, or the remediator. All harnesses are my own, written for this re-run; no prior harness code was reused (the two prior reports were read for scope only). Strictly read-only toward the repo: no pushes, no edits, no deploys, no gate changes. Work was done in my own `/tmp/phaseb-rerun` tree assembled file-by-file from the head via the API.

## Headline verdict

**The corrected Phase B control plane holds under the full suite.** D-1, D-2 and D-3 remain **CLOSED** under fresh execution; the remediation verifies exactly as recorded (duplicate pending invites close SUPERSEDED inside the acceptance transaction with receipts naming the accepted invite; unauthorized removal refusals are indistinguishable across host/peer/nonexistent targets; the reconciler flags fault-injected orphan receipts precisely, catches a deleted receipt the hash chain alone cannot see, and writes nothing). **One new discrepancy was found — D-4 (low)** — a consent-visibility defect in the room view, detailed with reproduction in §9. It exposes no authorization path and is fail-closed for ordinary accounts in one direction, but it is a real confidentiality break for one attainable account name, and it contradicts a claim recorded in the original test report.

## Executed totals

| Suite (mine) | Executed | Passed |
|---|---|---|
| Service level — identity/participants, lifecycle matrix (10 states × 12 actions = 120 cells), targeted lifecycle, invites, consent/recording, case binding, retention | 240 | 239 |
| No-record-no-action + residual-#1 fault injection | 18 | 18 |
| Remediation targeted (R-B, R-C, reconciler) + consent-visibility probe | 33 | 32 |
| Composed application (routes, isolation, gates, commercial drive) | 43 | 43 |
| Concurrency — 130 barrier-synchronized trials + post-race chain verification | 131 | 131 |
| Record (gates, jurisdictions, model constants) | 9 | 9 |
| Supplementary probe (invite-accept revocation) | 2 | 2 |
| **Total** | **476** | **474** |

For comparability with the original run (388 checks, of which 5 checks comprised 120 race trials): this re-run executed **346 discrete checks + 130 barrier race trials**. The 2 failed checks are the two executed faces of the single new discrepancy D-4 (§9). All 130 race trials held their invariants.

## Method and hash verification

- Tree assembled in `/tmp/phaseb-rerun/tree` from the git tree at `5c6db342` (1,209 blobs, `truncated: False`), each file fetched individually through the API. The shared staged working copy was not used.
- Before executing anything, every exercised file was verified three ways — local SHA-256 == GitHub-API-at-head SHA-256 == `.pbd.json` manifest `payload_hash`:
  - `core_platform/rooms.py` — `3d46fb3439fe2b2e…` ✓
  - `core_platform/rooms_reconciliation.py` — `46dff1af6beb3280…` ✓
  - `app/customer_app.py` — `10d71e65d1816510…` ✓
  - `deploy/deployment.py` — `7a636751379d0092…` ✓
  - `deploy/production_bindings.py` — `359d18bc379dbe8a…` ✓
  - `core_platform/glass_box_audit.py` — `1ce1579ab2796bf4…` ✓
  - `core_platform/global_compliance.py` — `dda3d9154001c6ca…` ✓
  - `core_platform/ai_platform_approvals.json` — `1dd66856ac55bea3…` ✓
  The verification was repeated after all suites ran: **ALL_MATCH**, and the branch head was unchanged.
- The composed application under test is the real `deployment.create_application(bindings)`, with bindings assembled on scratch stores mirroring `deploy/production_bindings.py` exactly (its own `_stripe_client` / `_fee_verifier` / `_eligibility_verifier` / `_provider_clients` helpers imported and used), the real approvals file (0/9 gates approved) driving the gates, fictitious `LIVEKIT_*` keys set, and no Stripe keys (checkout therefore exercises the honest-409 path).
- The runtime's execution-risk check never fired; everything below was executed, not merely read.

## 1. Authorization / identity — CONFIRMED

- All 11 rooms route/method combinations answer **401 `sign_in_required`** unauthenticated through the composed app; a signed-in POST from a foreign Origin answers **403 `origin_denied`**.
- Cross-customer isolation is byte-exact: a non-participant's GET on a real room and on a nonexistent room id return **identical status and body** (404 `{"error":"not_found"}`); a cross-customer transition answers the same 404; list views exclude invisible rooms — at service level (RoomNotFound) and route level alike.
- Participant attempts at host-only actions (transition, add, invite, authorize, remove-other) refuse with RoomForbidden / 403 `room_forbidden`. A removed participant immediately loses read, consent and list visibility. Self-leave works. The host cannot be removed by an operator or by the host themself. Second-HOST and duplicate admissions refuse. All six commercial roles admit; `NOTARY` and unknown roles refuse on add and on invite.
- No self-asserted or guest identities: the create route rejects a smuggled `host` field (400 `invalid_request`), the consent route rejects a smuggled `identity` field (400), the transition route rejects a smuggled `case_id` (400 — no rebinding path), and malformed actors (empty, spaced, overlong, None, non-string) refuse at the service boundary.
- Invites: wrong-account accept → RoomForbidden; unknown invite id and invite-under-wrong-room → RoomNotFound; double accept, revoked accept, double revoke all refuse; an expired invite (backdated in my own scratch store) refuses, persists its EXPIRED marking and receipts it; TTL bounds enforced (59s and 7d+1s refuse; 60s floor accepts); invites refuse in ENDED and ARCHIVED rooms.
- **One exception, in the room *view* only: see D-4 (§9).**

## 2. Lifecycle — CONFIRMED

- The full matrix was executed: **10 states × 12 actions = 120 cells**. Every allowed transition landed in exactly the expected target state; every disallowed transition refused *and preserved state* — including every action from ARCHIVED and CANCELLED.
- `schedule` without a start refuses and changes nothing; `schedule` with end ≤ start refuses; unknown actions refuse; stranger transitions raise RoomNotFound.
- `unlock` returns to the exact pre-lock state (verified from ACTIVE); `resume` lands in WAITING_ROOM, never ACTIVE.
- EVIDENCE_HOLD is operator-only (host `hold` → RoomForbidden); while held, operator `end`, host participant changes and invites all refuse as frozen; `release_hold` returns to the state recorded at hold. Hold from ENDED succeeds (non-terminal), from EVIDENCE_HOLD/ARCHIVED/CANCELLED refuses — matching the code's stated rule.

## 3. Consent / recording authorization — CONFIRMED (D-1, D-2 remain CLOSED)

- Authorization refuses in DRAFT, with no consent, with host-only consent, under a PROHIBITED policy despite unanimity; a REQUIRED policy cannot override a participant's REFUSED; double authorization refuses.
- Unanimous current GRANTED consent **against the room's canonical notice version** authorizes (D-2 enforced by execution, service and route level): mixed versions (`v1` + `v2-other`) cannot authorize; a canonical re-grant restores authorizability; a stale-version re-grant (`v9-stale`) revokes a standing authorization in the same step; the append-only history keeps every version ever recorded — nothing rewritten or deleted.
- Revocation in the same transaction on: withdrawal, refusal, participant add, participant remove, **invite acceptance**, room end, evidence hold — and (D-1) on **lock** and **suspend**, with unlock/resume landing revoked and a fresh pass re-earning authorization; WAITING_ROOM→ACTIVE preserves a live authorization.
- Consent authority: a non-participant operator cannot record consent for another (RoomForbidden); a stranger's consent is RoomNotFound; malformed decisions/versions refuse; withdrawal without a prior grant refuses; consent refuses in ARCHIVED and CANCELLED rooms.

## 4. Case binding — CONFIRMED (D-3 remains CLOSED)

- A customer binds only their own case; the room inherits the case's jurisdiction (CO verified at service and route level); an explicit jurisdiction overrides; an operator binds any case; binding with no cases store wired refuses.
- The two failure modes are indistinguishable at both levels: service level raises the identical `RoomDenied('Case cannot be bound')`; route level returns **byte-identical** status and body for another customer's case vs a nonexistent case. Binding exists only at creation — no rebind parameter on any later operation, and the route rejects a smuggled `case_id`.

## 5. No-record-no-action — CONFIRMED; residual #1 reproduced again

- Construction without a working audit adapter refuses (RoomDenied) — a RoomService without a Glass-Box sink does not exist. With a `preserve` that always raises, create raises and leaves zero room rows.
- **Root-proof mid-life destruction** (audit DB file deleted and replaced with a *directory*; permission-bit tricks do not count, this environment runs as root): transition raises with the room's state unchanged; consent raises with zero consent rows written; create raises with no new room committed.
- **Fault injection** (rooms-store `commit()` made to raise after a genuine audit write): create leaves no room and exactly one orphaned `ROOM_CREATED` receipt; transition leaves the state at DRAFT and exactly one orphaned `ROOM_TRANSITION` receipt; `verify_audit()` still validates the chain after both. The residual-#1 characterization remains accurate — an evidence-of-attempt receipt, never a phantom state change (and §7 shows the reconciler now surfaces precisely these orphans).

## 6. Concurrency — CONFIRMED (130 trials)

Two independent RoomService instances on one store, barrier-synchronized:

- Duplicate `open`: exactly one success, 20/20. Duplicate `end`: exactly one success, 20/20.
- Authorize-vs-withdraw (30), authorize-vs-add-participant (20), authorize-vs-remove-participant (20), authorize-vs-lock (20): in every trial the final committed state satisfies **AUTHORIZED ⇒ room in WAITING_ROOM/ACTIVE and every currently admitted participant holds a current counting consent (GRANTED against the room's canonical notice version)**. Zero invariant violations.
- The audit chain verifies end-to-end after a raced history.

## 7. Remediation verification (targeted) — CONFIRMED

- **R-B (superseded invites):** three pending invites for one invitee (plus one for another invitee) were issued; accepting one closed the other two as **SUPERSEDED inside the acceptance transaction**, each with a `ROOM_INVITE_SUPERSEDED` receipt whose `superseded_by` names the accepted invite and whose `invite_id` names the superseded one; the other invitee's pending invite was untouched; the invitee was admitted with the *accepted* invite's role; a SUPERSEDED invite can never be accepted (refuses, status intact).
- **R-C (removal indistinguishability):** an unauthorized participant's removal attempts against the **host**, a **peer**, and a **nonexistent** identity return the identical refusal — `RoomForbidden('Host or operator authority required')` in all three cases. An authorized actor (the host removing themself) still receives the specific host-rule refusal, and legitimate removal still succeeds.
- **Reconciler (`core_platform/rooms_reconciliation.py`):**
  - A rich clean history (creation, invites incl. a supersede, consents, authorization, activation, end, archive, a cancelled room) reconciles to `ok: True` — chain valid, **zero** orphaned/missing/divergence findings, both rooms examined.
  - **Read-only proven:** SHA-256 and mtime of both stores are byte-identical before and after `reconcile()` (both stores are also opened `mode=ro` by construction).
  - The fault-injected orphan **transition** receipt is flagged precisely (exactly one orphan, stage `ROOM_TRANSITION`, correct room); the fault-injected orphan **creation** receipt likewise (exactly one, stage `ROOM_CREATED`); both reports `ok: False`.
  - A **semantically tampered** receipt (an event field rewritten in place, hash untouched) makes the reconciler report `chain_valid: False`, and `GlassBoxAudit.verify_audit()` independently rejects the same chain.
  - A **deleted** consent receipt is flagged precisely as missing evidence (`ROOM_CONSENT_RECORDED` deficit of 1). Notable and correct: the hash chain alone does *not* see a tail deletion (the remaining receipts form a valid prefix chain — `chain_valid` stays True), which is exactly the gap the cross-check exists to close; the report is `ok: False` on the missing-evidence finding.

## 8. Regulated boundary + regressions — CONFIRMED

- `NOTARIAL` room type refused at service level *and* route level (400 `room_denied`); `NOTARY` role refused at both levels, on add and on invite. The model's type set is exactly {CONSULTATION, COMMERCIAL_TRANSACTION, CONFERENCE, INTERNAL_COLLABORATION} and the role set exactly {HOST, PARTICIPANT, INTERPRETER, WITNESS, OBSERVER, SUPPORT} — re-verified by import at this head.
- Gates through the real composition: provider POST → **503 `approval_required`** (`ron_notarial`); native POST → **503 `approval_required`**; realtime token POST with fictitious LiveKit keys → **503 `approval_required`** (`voice_video_provider`); voice transcribe signed-out → **401**.
- Gates file: **9/9 UNAPPROVED**. `APPROVED_RON_JURISDICTIONS` remains the empty frozenset.
- Composed-app standard drive unchanged: `/healthz` 200; storefront `/` 200; portal `/appointments` 200; intake → **201** with case id; operator queue 401 signed-out / 403 as customer / 200 as operator with the case listed; operator quote → **201**; checkout → **409 `checkout_unavailable`**; unwired-rooms composition → **503 `rooms_unavailable`**; audit chain verifies after the full drive.
- Retention record (re-verified at this head): default **365 days, basis PLATFORM_DEFAULT**; host-set basis HOST_POLICY; bounds 1–3650 enforced (0, −5, 3651, bool, string, float all refuse); deletion eligibility computed only once ARCHIVED (= `state_changed_at + days×86400`); no deletion operation exists on the service; invite TTL default 72h, bounds 60s–7d.

## 9. New discrepancy

### D-4 — LOW: consent visibility in the room view is keyed to a category literal, not the viewer — own consent never shown; the account named "participant" leaks its consent to co-participants

**Where:** `core_platform/rooms.py`, `_room_view`. The view receives the viewer's *visibility category* (`'host' | 'operator' | 'participant'`) as `viewer`, and attaches a participant's consent state under the rule `privileged or participant['identity'] == viewer` — comparing an **account identity** against the **category literal**. For a participant viewer the self-branch is dead for every ordinary identity (no identity equals the string `'participant'`), and it fires for exactly one identity: the account literally named `participant`, in *every* participant's view.

**Reproduction (executed at this head):** room hosted by alice with participants `participant` and `carol`; `participant` records GRANTED, carol records REFUSED. In **carol's** `get_room` view: (a) carol's own participant entry carries **no** `consent` key — she cannot see her own current consent state (the check "participant view exposes own consent state" failed); (b) the entry for identity `participant` **does** carry `consent: 'GRANTED'` — another participant's consent decision is exposed to her (the check "no participant's consent exposed to another participant" failed). The host's privileged view correctly shows all consent states.

**Why it matters:** the recorded design property (original test report §3: a participant's view "exposes only their own consent state, never another participant's") fails in **both** directions as executed at this head. Direction (a) is fail-closed — a participant cannot confirm their own recorded consent from the room view. Direction (b) is a genuine, if narrow, confidentiality break: consent decisions are exactly the class of information the view deliberately withholds between participants, and the account name `participant` is freely attainable at ordinary registration. There is **no authorization impact**: `authorize_recording` derives unanimity from the store, never from the view, and no state can be changed through this path. Severity **low**; the correction is to key the self-branch to the viewer's identity (pass the actor into `_room_view`, as the privileged branch already effectively assumes) rather than to the category string.

## Scope limits, stated plainly

- Verified in-process against scratch stores and fictitious keys, through the real composed application — **not deployed, not live**. Nothing here establishes production behavior; the corrected + remediated code rides the owner's gated deploy path.
- The media plane was not and cannot be tested: the `voice_video_provider` gate is unapproved and rooms mint no tokens; per-participant grant scoping remains Phase C work, unchanged by this re-run.
- Fault injection was performed at the rooms-connection boundary of my own harness (commit made to raise after a genuine audit write) — the exact storage-failure class named as residual #1, not a physical disk failure.
- Invitation expiry was tested by backdating `expires_at` in my own scratch database (a fixture action on test data); the accept-side expiry logic, marking and receipt are the production code's.
- The legacy pre-fix store migration exercised by the earlier retest was not re-run here (it is not part of the original 388-check scope); nothing in this re-run contradicts it.
- Race trials ran two service instances on one store in-process; they do not measure cross-process timing on the production host.
- The earlier residuals stand as previously recorded and were not contradicted by anything in this re-run: R-A (consent mutable under EVIDENCE_HOLD) remains an open owner design question — my matrix confirms consent is not a transition and the hold freezes transitions only, exactly as recorded; R-D (expired-invite marking commits inside the refusal) re-verified incidentally in §1.

## Bottom line

Against the corrected and remediated head, the full original suite re-executes clean: **346 discrete checks + 130 race trials; D-1, D-2, D-3 remain CLOSED; R-B, R-C and the Glass Box reconciler verify as recorded; the regulated boundary, all nine unapproved gates and the empty jurisdiction set are untouched; no regression anywhere in the commercial drive.** The single new finding, **D-4**, is a view-layer consent-visibility defect — a participant cannot see their own consent state, and the one account named `participant` has its consent state shown to co-participants. It grants nothing, changes nothing, and authorizes nothing; under the ecosystem's own standard it should still be corrected and the correction retested, because consent information is the information this system exists to handle exactly.
