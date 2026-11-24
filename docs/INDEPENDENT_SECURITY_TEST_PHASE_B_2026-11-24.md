# Independent Security Test — Phase B (Commercial Rooms Core)

**Subject:** DashandSeal/Sanders_Dash_Seal at head `1cd6915cfee61d4aba060f6c6e26be5ee58758e9`
**Scope:** `core_platform/rooms.py` (RoomService), `/api/rooms` routes in `app/customer_app.py`, wiring in `deploy/deployment.py` + `deploy/production_bindings.py`
**Tester posture:** adversarial, independent — the builder's harnesses (`verify_phase_b.py`, `verify_phase_b_app.py`) were not used or read for test logic; all harnesses here are the tester's own. Strictly read-only toward the repo: no pushes, no edits, no deploys, no gate changes. Working copy left clean at `1cd6915` with the pre-existing named stash intact.

## Headline verdict

**No critical bypass found.** Identity binding, participant isolation, the lifecycle state machine, consent unanimity, case-binding ownership, no-record-no-action, and exactly-once concurrency all survive adversarial execution. **Three discrepancies** were found — two moderate breaks in the recording-authorization invariants, one low-severity information leak — detailed in §10 with reproductions. The builder's five named residuals were all re-verified as accurately stated; residual #1 was reproduced exactly by fault injection.

## Method and hash verification

- Working copy: the established staged copy (owner's 2026-11-24 03:53 MST go-ahead), already clean at `1cd6915`; the named stash `phase-a-builder-local-copies-pre-retest` was preserved untouched.
- Before executing anything, the exercised files were verified three ways — local SHA-256 == GitHub-API-at-head SHA-256 == `.pbd.json` manifest `payload_hash`:
  - `core_platform/rooms.py` — `a8aab915…` triple-match ✓
  - `app/customer_app.py` — `6a60236c…` triple-match ✓
  - `deploy/deployment.py` — `7a636751…` triple-match ✓
  - `deploy/production_bindings.py` — `359d18bc…` triple-match ✓
- The composed application under test is the real `deployment.create_application(bindings)`, with bindings assembled on scratch stores mirroring `deploy/production_bindings.py` wiring exactly (its own `_stripe_client` / `_fee_verifier` / `_eligibility_verifier` helpers imported and used), including the real approvals file (0/9 gates approved) driving the provider/native/realtime gates.
- The runtime's execution-risk check never fired; everything below was executed, not merely read.

## Executed check totals

| Suite | Checks | Result |
|---|---|---|
| Service level, part 1 (lifecycle matrix, identity, invites, consent) | 279 | 278 as expected; 1 refusal with a different exception type than my harness predicted (fail-closed held — see R-C) |
| Service level, part 2 (case binding, retention, audit destruction, fault injection, races) | 47 | 47/47 |
| Composed application (routes, isolation, gates, regressions) | 62 | 62/62 |
| **Total** | **388** | **3 discrepancies (§10)** |

The concurrency item inside part 2 is 5 checks comprising **120 barrier-synchronized race trials** (20 duplicate-open + 20 duplicate-end + 30 authorize-vs-withdraw + 30 authorize-vs-add + 20 authorize-vs-remove), all holding their invariants.

## 1. Authorization / identity — CONFIRMED

- Every rooms route (11 route/method combinations: list, create, detail, transition, add participant, remove participant, issue invite, accept invite, revoke invite, consent, recording) answers **401 `sign_in_required`** unauthenticated through the composed app; wrong-Origin POST answers **403 `origin_denied`**.
- Cross-customer isolation is exact: a non-participant's GET on a real room and GETs on a nonexistent room id return **identical status and body** (404 `{"error":"not_found"}`), for both the stranger and the host. All six cross-customer write routes answer the same indistinguishable 404. List views exclude invisible rooms.
- A participant attempting host-only actions (transition, add, invite, authorize, remove-other) is refused — 403 `room_forbidden` at route level, `RoomForbidden` at service level.
- No self-asserted or guest identities exist anywhere: participants are added by host/operator or admitted by accepting an invitation as themselves; the consent route's strict field set rejects a smuggled `identity` field with 400 `invalid_request`; create rejects a smuggled `host` field the same way.
- A removed participant immediately loses all visibility (`RoomNotFound` on read, transition, and consent) and disappears from their own list. Self-leave works. The host cannot be removed — by an operator, or by the host themself.
- Second-HOST admission is refused; duplicate admission is refused.

## 2. Lifecycle integrity — CONFIRMED

- The full state×action matrix was executed: **10 states × 10 actions = 100 pairs**. Every allowed transition succeeded; every disallowed transition refused *and left the state unchanged* — including every action attempted from the terminal states ARCHIVED and CANCELLED.
- `schedule` without a start refuses and changes nothing; `schedule` with end ≤ start refuses.
- `resume` from SUSPENDED lands in **WAITING_ROOM**, never ACTIVE. `unlock` returns to the exact pre-lock state (verified from both WAITING_ROOM and ACTIVE). `release_hold` returns to the state recorded at hold.
- EVIDENCE_HOLD is operator-only: host `hold` and host `release_hold` raise `RoomForbidden`; while held, host *and* operator `end`/`cancel`/repeat-`hold` all refuse, and participant changes refuse. Hold on ARCHIVED/CANCELLED refuses.
- Participant changes and invitations refuse in ENDED and EVIDENCE_HOLD states. Unknown transition actions refuse. Transitions by a stranger raise `RoomNotFound` (no existence leak).

## 3. Consent / recording authorization — DISCREPANCY (see D-1, D-2)

Confirmed by execution:
- Authorization refuses in DRAFT; refuses with no consent; refuses with host-only consent; refuses under a `PROHIBITED` policy even with unanimous consent; a `REQUIRED` policy **cannot override a participant's REFUSED**; double-authorization refuses.
- Unanimous current GRANTED consent from every admitted participant (host included) authorizes.
- Revocation in the same transaction on: consent **withdrawal**, consent **refusal**, participant **add**, participant **remove**, **invite accept**, room **end**, room **cancel**, and **evidence hold**.
- An operator who is not a participant cannot record consent (`RoomForbidden`) — consent cannot be recorded on another's behalf; a stranger's consent raises `RoomNotFound`. Withdrawal without a prior grant refuses. Malformed decisions and malformed notice versions refuse.
- Consent refuses in ARCHIVED and CANCELLED rooms. A participant's room view exposes only their own consent state, never another participant's.

**Not confirmed — two breaks found (D-1, D-2 in §10):** authorization survives LOCKED and SUSPENDED (and therefore resume), and the notice version is recorded but never enforced.

## 4. Case binding — DISCREPANCY (low severity, see D-3)

Confirmed by execution:
- A customer binds only their own case; the room **inherits the case's jurisdiction** (CO verified). An operator may bind any case. An explicit jurisdiction at creation overrides inheritance. Binding with no cases store wired refuses. Binding happens at creation only — no rebind parameter exists on any later operation, and the transition route rejects a smuggled `case_id` field with 400 `invalid_request`.

**Not confirmed:** the refusal for another customer's case is distinguishable from the refusal for a nonexistent case (D-3).

## 5. No-record-no-action — CONFIRMED; builder's residual #1 reproduced exactly

- Construction without a working audit adapter refuses (`RoomDenied`): a RoomService without a Glass-Box sink does not exist.
- With an audit adapter whose `preserve` always raises: create raises and leaves **zero** room rows.
- **Root-proof destruction mid-life** (the audit DB file deleted and replaced with a *directory* — permission-bit tricks do not count, this environment runs as root): transition raises and the room's state is unchanged in the store; consent raises and writes **zero** consent rows; create raises and adds no room.
- **Residual #1 fault injection:** with a real GlassBoxAudit on its own store and the rooms-store connection's `commit()` made to raise after the audit write succeeded — create raised, **no room exists**, yet the audit chain contains exactly one `ROOM_CREATED` receipt for the uncommitted creation, and `verify_audit()` still validates the chain. The same injection on a transition left the state at DRAFT with exactly one orphaned `ROOM_TRANSITION` receipt. This is precisely the builder's stated residual: *receipt exists for an action that did not commit; room state unchanged.* The characterization is accurate and the blast radius is as stated — an evidence-of-attempt receipt, never a phantom state change.

## 6. Concurrency — CONFIRMED

120 barrier-synchronized trials across two independent RoomService instances on one store:
- Duplicate `open`: exactly one success, 20/20. Duplicate `end`: exactly one success, 20/20.
- Authorize-vs-withdraw (30), authorize-vs-add-participant (30), authorize-vs-remove-participant (20): in every trial, the final state satisfies **AUTHORIZED ⇒ every currently admitted participant holds a current GRANTED consent**. No interleaving left recording authorized over a withdrawn consent or a changed participant set.
- The audit chain verifies end-to-end after all races.

## 7. Regulated boundary — CONFIRMED

- `NOTARIAL` room type refused at service level *and* route level (400 `room_denied`). `NOTARY` role refused at both levels on add and on invite. The model's type set is exactly {CONSULTATION, COMMERCIAL_TRANSACTION, CONFERENCE, INTERNAL_COLLABORATION} and role set exactly {HOST, PARTICIPANT, INTERPRETER, WITNESS, OBSERVER, SUPPORT}.
- Rooms mint no tokens and touch no payment/document flow: the only case interaction is the creation-time reference + jurisdiction inheritance verified in §4.
- Gates untouched through the real composition: realtime token POST with fictitious LiveKit keys → **503 `approval_required`**; provider POST → **503 `approval_required`** (`ron_notarial`); native POST → **503 `approval_required`**. Voice transcribe signed-out → 401.

## 8. Regressions — CONFIRMED

Through the composed application: `/healthz` 200; storefront `/` 200; portal `/appointments` 200; intake → 201 with case id; operator queue 401 signed-out / 403 as customer / 200 as operator with the case listed; operator quote → 201; checkout → **409 `checkout_unavailable`**; unwired-rooms composition → **503 `rooms_unavailable`**.

## 9. Record — CONFIRMED

- Gates file: **9/9 UNAPPROVED** (read from the file the composed app itself enforces).
- `APPROVED_RON_JURISDICTIONS` is the empty frozenset.
- Manifest hashes: §Method — all four Phase B files triple-match.
- SPEC Phase B entry claims checked against code and execution: role set ✓; type set ✓; NOTARIAL/NOTARY deliberately absent ✓; retention default **365 days with basis `PLATFORM_DEFAULT`** ✓ (the Colorado 10-year RON figure is *not* imported — default verified 365, not 3650); host-set retention bounds **1–3650** enforced (0, −5, 3651, bool, string, float all refuse), basis `HOST_POLICY` when host-set ✓; deletion-eligibility instant computed only once ARCHIVED (= `state_changed_at + days×86400`) ✓; **no deletion operation exists** on the service ✓; invite TTL bounds 60s–7d enforced ✓ (default 72h per code); resume-lands-in-WAITING_ROOM ✓; lock/unlock pre-lock-state return ✓; case binding at creation only ✓; host transfer absent ✓. Two SPEC design claims do **not** hold in execution — decisions (2) and (7) as they interact with recording authorization; see D-1/D-2.

## 10. Discrepancies (with reproductions)

### D-1 — MODERATE: recording authorization survives LOCKED and SUSPENDED — and therefore resume
`transition()` revokes recording authorization only when the target is ENDED, CANCELLED, ARCHIVED, or EVIDENCE_HOLD. Lock and suspend are not in that set.
**Reproduction (service level, executed):** room → open → all participants GRANTED → activate → `authorize_recording` (state AUTHORIZED) → `lock` → recording_state is still **AUTHORIZED**; `unlock` → back in ACTIVE, still AUTHORIZED. Separately: `suspend` → still AUTHORIZED; `resume` → lands in WAITING_ROOM (correctly, per decision 7) **with the recording authorization still in force**.
**Why it matters:** the helper's own docstring states revocation covers "room left its live states," and SPEC decision (7) justifies resume-landing-in-WAITING_ROOM precisely because resumption "requires a fresh authorization pass" — yet the recording authorization, the one authorization the consent gate exists to control, passes through lock, suspend, and resume unexamined. The media plane is gated off today, so no recording can actually occur; but the control-plane invariant *authorization describes a live, continuously-authorized room* is broken, and Phase C inherits it if uncorrected.

### D-2 — MODERATE: notice_version is recorded but never enforced — mismatched/superseded notices authorize
`record_consent` accepts any string matching the version format; `authorize_recording` checks only that each admitted participant's current decision equals `GRANTED`. No canonical current notice version exists anywhere in the service, so "stale" is unenforceable as built.
**Reproduction (executed):** host grants against `notice_version="v1-old"`, participant grants against `notice_version="v2-new"` → `authorize_recording` succeeds. The two participants consented under *different notice texts* and the authorization issued anyway.
**Why it matters:** SPEC decision (2) presents the notice-version binding as the mechanism tying consent to the notice actually presented. As built, the binding is a label, not a check: a participant who granted under a superseded notice counts identically to one who granted under the current notice.

### D-3 — LOW: case-existence enumeration oracle at room creation
**Reproduction (route level, executed):** as customer bob, `POST /api/rooms` with alice's real case_id → `400 {"error":"room_denied","detail":"Case cannot be bound by this actor"}`; with a nonexistent case_id → `400 {"error":"room_denied","detail":"Unknown case"}`. The differing `detail` lets any authenticated account distinguish *case exists but is not yours* from *case does not exist* — enumerating which case IDs exist. (Service level identical.)
**Why it matters:** severity is low — case IDs are unguessable tokens, so this confirms existence only for an ID the caller already possesses — but it contradicts the isolation discipline this same build applies rigorously to rooms, where invisible and nonexistent are deliberately indistinguishable. The `detail` field on `RoomDenied` responses is the carrier; the room routes' own not-found handling shows the intended pattern.

## 11. New residuals beyond the builder's five

- **R-A — Consent mutates under EVIDENCE_HOLD.** `CONSENT_STATES` is every non-terminal state, including EVIDENCE_HOLD. While a room is frozen for evidence, participants can still record, refuse, and withdraw consent — and a withdrawal under hold runs the recording-revocation bookkeeping inside the frozen room. SPEC decision (8) says the hold "freezes every other transition"; consent is not a transition, so this is arguably within the letter — but whether evidence-relevant consent state should move during an evidence hold is unexamined by the builder and is a design call for the owner.
- **R-B — Duplicate pending invitations linger.** Multiple PENDING invites for the same invitee can coexist. Accepting one makes the invitee a participant; the other stays PENDING, and accepting it then raises "Already a participant" with a rollback that leaves it PENDING — it can never succeed and remains until expiry or revoke. Hygiene only; no authority is granted by it.
- **R-C — Host-removal error precedence leaks one bit of shape.** `remove_participant` checks "the host cannot be removed" *before* the authority check, so an unauthorized participant probing removal of the host receives `RoomDenied: The host cannot be removed` rather than `RoomForbidden`. Fail-closed throughout (my part-1 harness's single non-matching expectation was exactly this); recorded only so the shape difference is known.
- **R-D — Expired-invite marking is a deliberate commit-inside-refusal.** `accept_invite` on an expired invite commits the EXPIRED marking and the audit receipt, then raises. Verified working as intended (status persists as EXPIRED after the refusal) — recorded because it is the one place a refused operation intentionally leaves a state change, by design.

## Scope limits, stated plainly

- Verified in-process against scratch stores and fictitious keys, through the real composed application — **not deployed, not live**. Nothing here establishes production behavior.
- The media plane was not and cannot be tested: the `voice_video_provider` gate is unapproved and rooms mint no tokens (builder residual #5 stands as stated — per-participant grant scoping remains Phase C work).
- Fault injection for residual #1 was performed at the rooms-connection boundary of my own harness (commit made to raise after a genuine audit write). It reproduces the exact storage-failure class the builder named; it is not a reproduction of a physical disk failure.
- Invitation expiry was tested by backdating `expires_at` in my own scratch database (a fixture action on test data, not a code path) — the accept-side expiry logic, marking, and receipt are the production code's.
- The builder's five residuals were each re-verified as accurately stated (1: §5; 2: no host-transfer operation exists; 3: §4; 4: §9; 5: §7/scope). Nothing in this test contradicts them.

## Bottom line

Phase B's control plane enforces what it claims on identity, isolation, lifecycle, consent unanimity, case ownership, evidence, and concurrency — 385 of 388 executed checks as expected, 120 race trials clean. The corrections belong to the recording authorization's edges: **revoke on lock and suspend (D-1)**, **enforce the notice version the consent was recorded against (D-2)**, and **make case-binding refusals indistinguishable (D-3)**. None of the three is reachable by an unauthenticated or unauthorized actor, and none opens the regulated track — but under the ecosystem's own standard, the authorization that survives a suspension is an authorization that was never re-earned, and it should not stand as recorded.
