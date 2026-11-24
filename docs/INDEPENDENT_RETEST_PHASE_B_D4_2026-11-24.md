# Independent Retest — Phase B Corrective Fix D-4 (consent visibility in the room view)

**Head retested:** `5a62cf564f04bf2a29b5caf678ab6f1db57e05f5`, DashandSeal/Sanders_Dash_Seal
**Date:** 2026-11-24
**Retester:** independent — built neither the rooms, nor the test that found D-4, nor the fix.
**Posture:** strictly read-only toward the repo. Nothing pushed, edited, or deployed.

## Verdict

- **D-4 — CLOSED.** Both faces, at service level and through the real composed application.
- **Sibling defect (invitation filter) — CLOSED.** Same confirmation, same two levels.
- **Privileged views — UNCHANGED**, proven by cross-version execution against the parent head's code, not by assertion.
- **No still-open item found.** Regressions clean; the record is append-only; all nine gates remain UNAPPROVED; the approved RON jurisdiction set remains empty.

## Method

- **Own tree, own harnesses.** The retest tree was assembled by a depth-1 git fetch of the exact head into `~/workspace/.scratch-d4retest/tree` (the shared working copy and its named stash were never touched). One method note: the tree lives under `~/workspace/.scratch-d4retest` rather than `/tmp` because this machine's `/tmp` is a 512 MB tmpfs that was 100% full (a codeload tarball download failed with a write error); the scratch location does not affect any result. Neither the fixer's drives nor any prior harness was reused; both harnesses here were written for this retest.
- **Hash verification before execution.** For both files named in the task, local SHA-256 == GitHub-API-at-head content == manifest `payload_hash`:
  - `core_platform/rooms.py` — `8cc89851ba76013fae467942473a4e6b079f7b8670e61f621932363d76195042` (all three agree)
  - `app/customer_app.py` — `10d71e65d1816510b07469709c4de43422cf0ab1d86aa77ac171c8aaba1bf00d` (all three agree)
  The SPEC manifest was likewise verified (below). The runtime's execution-risk check never fired; every check below was executed.
- **Control run against the parent code.** The same service scenario was executed against `rooms.py` fetched from the pre-fix head `5c6db342`, in a copied tree with only that file swapped. All three defects (D-4 face A, D-4 face B, the invitation sibling) **reproduce** under the parent code with this retest's harness — so the harness is proven sensitive to the defects it then confirms closed at the fixed head.
- **Diff adjudication.** The parent→fixed diff of `rooms.py` is exactly: the `actor` parameter and its docstring on `_room_view`, the consent comparison (`participant['identity'] == viewer` → `== actor`), the invitation filter (`invite['invitee'] != viewer` → `!= actor`), and `actor` passed at all nine `_room_view` call sites. Nothing else in the file changed — authorization logic is untouched by construction of the diff, and D-1/D-2 behavior was additionally re-executed (below).

## Executed counts

| Suite | Executed | Passed |
|---|---|---|
| Service level, fixed head (D-4 faces, sibling, privileged views, outsider isolation, D-1/D-2/lifecycle/boundary regressions, audit chain) | 35 | 35 |
| Composed application, fixed head (standard drive + D-4/sibling over HTTP + D-3 byte-identity + gates) | 48 | 48 |
| Parent-code control run (defect reproduction) | 11 | 11 |
| Cross-version privileged projections (host/operator × participants/invites) | 4 | 4 MATCH |
| Record verifications (SPEC prefix, D-4 entry, SPEC manifest, file triple-matches, gates, jurisdictions) | 6 | 6 |

## 1. D-4 closure — both faces (service + HTTP)

Scenario (identical at both levels): room hosted by `alice`; participants the account literally named `participant`, `carol`, and `dave`; `participant` records GRANTED against the room's canonical notice version, `carol` records REFUSED, `dave` records nothing.

- **Own consent visible:** carol's view carries `consent: 'REFUSED'` on her own entry; `participant`'s view carries `consent: 'GRANTED'` on its own entry; dave's own entry carries the consent key with value `None` (no record) — the self-branch now fires for every identity.
- **No one else's consent visible:** in carol's view, the entries for `participant`, `dave`, and the host carry **no** consent key; symmetrically in `participant`'s and dave's views. The account named `participant` exposes nothing to co-participants and sees exactly its own state.
- Confirmed identically through the composed application's HTTP routes (register → create → add participants → consent → per-actor GET), and an outsider (`mallory`) still receives 404 / `RoomNotFound`.

## 2. The sibling — invitation visibility

Room with PENDING invites to `participant`, `carol`, `dave`; carol and `participant` accept.

- Carol's invite list is exactly `[('carol', 'ACCEPTED')]` — her own invite only; the `participant` and `dave` invites are absent. Under the parent code the same view returned exactly `[('participant', 'PENDING')]` — she saw the literally-named account's invitation and not her own (control reproduction).
- `participant`'s invite list is exactly its own accepted invite; carol's and dave's are hidden.
- Host and operator invite lists contain all three invites with correct statuses at both code versions (see §4).
- Confirmed at service level and over HTTP.

## 3. Sweep confirmation (retester's own reading)

Every use of `viewer` in `rooms.py` was enumerated and read. The view builder's only identity-keyed exposure decisions are the two comparisons above, both now keyed to the viewer's account identity (`actor`). The remaining category uses are categories used as categories: `_visibility` *produces* the category (`'host' | 'operator' | 'participant' | None`), and `privileged = viewer in ('host', 'operator')` tests it. **No other identity-vs-category comparison remains in the view path.** The `viewer is None` branch returns the base view (metadata only, no participants or invites) and is used where the caller has no standing — it exposes no consent or invitation data.

## 4. Privileged views unchanged

The host and operator projections — `(identity, consent)` for every participant and `(invitee, status)` for every invitation, from the identical scenario — are **byte-identical between the parent head's code and the fixed head's code** (4/4 MATCH). Host and operator continue to see the full participant/consent/invitation picture exactly as before the fix. (Projections were compared rather than full view dicts because timestamps legitimately differ between runs.)

## 5. Regressions

- **D-1 spot checks:** unanimous canonical consent authorizes in WAITING_ROOM; `lock` strips the authorization; after unlock, a fresh pass re-authorizes.
- **D-2 spot checks:** a GRANTED consent recorded against a stale notice version (`v9-stale`) cannot authorize; re-recording against the canonical version authorizes.
- **D-3 at route level:** room creation by alice against carol's case and against a nonexistent case returns **byte-identical** responses (`400 {"error":"room_denied","detail":"Case cannot be bound"}`); carol binding her own case succeeds with jurisdiction `CO` inherited.
- **Lifecycle:** invalid transitions from DRAFT refuse (activate/end/archive); schedule → SCHEDULED; open → WAITING_ROOM; activate → ACTIVE; end → archive → ARCHIVED; no transition out of ARCHIVED.
- **Regulated boundary:** `NOTARIAL` room type and `NOTARY` role both refused at service level; provider and native POSTs through the composition answer 503 `approval_required` (gate `ron_notarial`); realtime token issuance answers 503 `approval_required` signed-out and signed-in with fictitious LiveKit keys set.
- **Composed standard drive:** `/healthz`, storefront `/`, portal `/appointments` all 200; operator setup and five registrations 200; intake 201 with case id; operator queue 401 signed-out / 403 as customer / 200 as operator with the case listed; operator quote 201; checkout 409 `checkout_unavailable`; voice transcribe signed-out 401; unwired-rooms composition 503 `rooms_unavailable`; Glass Box audit chain verifies after both harnesses.

## 6. Record

- **SPEC append-only:** `docs/SPEC_CONFORMANCE.md` at `5c6db342` (247,185 bytes, fetched via the API) is a strict byte prefix of the head's SPEC (252,832 bytes) — additions only across the whole span, which includes the preservation pointers and the fix. The D-4 corrective entry stands at head ("Phase B corrective fix — consent visibility in the room view (D-4)"), naming the discrepancy and the correction; the original Phase B claims are unedited.
- **Manifests:** `rooms.py` and `customer_app.py` triple-matched (above); the head SPEC's SHA-256 equals its manifest `payload_hash`, and the tree's SPEC is byte-identical to the API's head SPEC.
- **Gates:** `core_platform/ai_platform_approvals.json` carries exactly 9 gate statuses, all `UNAPPROVED`.
- **Jurisdictions:** `APPROVED_RON_JURISDICTIONS: frozenset = frozenset()` (`core_platform/global_compliance.py:227`) — still empty.

## Scope limits, stated plainly

- Verified in-process against scratch stores and fictitious credentials, through the real composed application — **not deployed, not live**. Nothing here establishes production behavior.
- The privileged-view comparison (§4) compares consent/invitation projections, not entire view payloads; fields outside the documented property (timestamps, ordering metadata) were not cross-compared.
- The media plane remains untestable behind the unapproved `voice_video_provider` gate; rooms mint no tokens; per-participant grant scoping remains Phase C work, untouched by this fix and this retest.
- R-A (consent mutable under EVIDENCE_HOLD) is an open owner design question outside this retest's scope; nothing here re-litigates or contradicts it.
- The fix's own SPEC entry cites the fixer's 62-check drive; this retest neither reused nor re-ran that drive — the counts above are this retest's alone.

## Bottom line

The D-4 correction does exactly what the documented property requires and nothing more: consent and invitation visibility are keyed to the viewer's identity at every call site, the literally-named-account leak is gone in both the consent branch and the invitation filter, a participant can once again see their own recorded consent state, and the host/operator picture is provably unchanged — demonstrated against the parent code, which exhibits all three defects under the same harness. **D-4: CLOSED. Sibling: CLOSED.**
