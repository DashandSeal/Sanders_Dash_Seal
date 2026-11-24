# Independent Retest — Stage 7 Corrective Fix

**Subject:** the corrective fix for the Stage 7 audit's one discrepancy, on `DashandSeal/Sanders_Dash_Seal` at head `9d45b578e69cc8d42e4f0bf573b5434c1683d49e`.
**Directed:** 2026-11-24 04:32 MST (audit → corrective commit → independent retest → all preserved as permanent corporate records); scope extension (bypass vectors) 04:46 MST.
**Retester's position:** not the fixer, not the original builder. Strictly read-only against the repo — nothing pushed, edited, or deployed.
**Fix under test:** commits `2d38e04f` (submit() refuses `NATIVE_SESSION_COMPLETED`) + `85c40507` (SPEC corrective entry); preservation commit `676a62d6` (audit report as `docs/INDEPENDENT_AUDIT_STAGE7_2026-11-24.md`); pointer commit `9d45b578`.

## Method — and one recovery, stated plainly

Three `git clone` attempts of the remote failed on this machine (two processes contended on the same directory; a runtime restart then left the third without a confirmed result, its partial directory corrupt). Rather than repeat an action with an uncertain outcome, the working copy was recovered as **the official tarball of the exact head tree** (`codeload.github.com/.../tar.gz/9d45b578…`, 140 MB) extracted to `~/workspace/stage7-audit/retest-tree`, and its content was **cross-verified against the remote**: the preserved audit document's SHA-256 in the tree (`c0bb20b5…`) equals the API-fetched file at head, and `provider_workflows.py` / `SPEC_CONFORMANCE.md` hashes equal their manifests at head (see Check 4). History questions (commit file lists, the SPEC before/after diff) were answered through the GitHub API. No builder or fixer working copy, and none of their scripts, was used; every check below was written by the retester from the claims. Dependencies: the repo's own pinned `requirements.txt` in a scratch venv.

## Verdicts

### Check 1 — The auditor's original probe, reproduced end to end — **CONFIRMED**
Case settled through the real `PaymentLedger.record_event` webhook path (`register_checkout` → `checkout.session.completed` → PAID) → bridge opened the native session → six authority decisions, RON room consent + recording → native completion → `bridge.refresh` propagated `NATIVE_SESSION_COMPLETED` → `ProviderWorkflows.submit()`:
- refuses with the codebase's own **`ProviderRequestConflict`** ("Case status does not permit provider submission."),
- **zero** provider-client calls (SignWell and BlueNotary doubles both at 0),
- **zero** `provider_requests` rows created.
The discrepancy's exact probe now closes. (3/3 exercised checks.)

### Check 2 — The replay clause — **CONFIRMED**
A provider request created against the case *before* native completion (BlueNotary, state CREATED, one provider call), then the case completed natively, then the identical submit replayed:
- the replay **refuses** with `ProviderRequestConflict` — no second provider call (count stays 1), no new row;
- `records()` still returns the earlier request (CREATED, `bn-session-1`) — pre-completion history remains readable, exactly as the fix claimed. (4/4.)

### Check 3 — Regressions — **CONFIRMED**
Against a settled, non-completed case: fresh submit CREATED; identical replay returns the stored receipt with no second provider call; conflicting reuse of the same request id raises `ProviderRequestConflict`; an unconfigured provider raises `ProviderUnavailable`; a non-operator raises `PermissionError`. Against the natively completed case, the other consumers still refuse: `cases.authorize_notarization` → `CaseDenied`; `AuthorityReview.review` → `AuthorityDenied`; quote (`approve_quote`) → `AppointmentDenied`; checkout → `AppointmentDenied`. (9/9.)

### Check 4 — Record integrity — **CONFIRMED**
- The preserved audit document at head is **byte-identical** to the original `~/workspace/stage7-audit/audit-report.md` (9,432 bytes; SHA-256 `c0bb20b5b3239613…` both sides), and its `.pbd.json` manifest `payload_hash` equals that hash.
- `core_platform/provider_workflows.py` and `docs/SPEC_CONFORMANCE.md` SHA-256 == their manifests at head.
- The SPEC between the Stage 7 head (`90375704`) and this head: **14 lines added, 0 deleted**. The corrective entry (line 1294, "Corrective entry — independent audit of stage 7: provider submission now refuses a natively completed case — November 24, 2026") and the preservation pointer were **appended**; the original Stage 7 entry — including the sentence the audit found overstated — stands **unchanged**. The record corrected itself without rewriting itself.
- `APPROVED_RON_JURISDICTIONS` still `frozenset()` (empty); approvals still **0 of 9**.
- Fix-era commit file lists (via API): `2d38e04f` = provider_workflows.py + its manifest; `85c40507` = SPEC + manifest; `676a62d6` = audit doc + manifest; `9d45b578` = SPEC + manifest. **No workflow file touched.**

### Check 5 — Spot regressions on adjacent audited claims — **CONFIRMED (as scoped)**
- **Journal:** the completion in Check 1 wrote exactly one entry to `native_notarial_journal`; `verify_chain()` returns the head hash. Tamper case: my first tamper string did not occur in the entry body (a no-op edit — reported for honesty); a precise tamper (altering the case id inside a stored body) makes `verify_chain()` raise `JournalDenied` ("entry mismatch"). Tamper-evidence holds.
- **Native route gate shape:** through the real composed app — signed-out POST → 401; operator with the gate unapproved → 503 `{"error": "approval_required", "gate": "ron_notarial"}`, identical in shape to the provider route's.
- **Not re-run:** the auditor's full 66 (the adapter matrix, the bridge mechanics beyond what the probe exercises, the full route matrix). The fix touched one function in one file; the spot checks above cover the claims that function could plausibly have disturbed, and Check 3 covers its direct consumers.

## Scope extension — the three bypass vectors (owner, 04:46 MST)

### Check 6 — Concurrent submissions — **CONFIRMED, with the guarantee stated precisely**
Races actually executed (threads, separate `ProviderWorkflows` instances on the same DB):
- **(a) Duplicate submits racing:** exactly **1** `provider_requests` row, exactly **1** provider-client call. The winner returned the CREATED receipt; the loser received `ProviderRequestConflict` (it observed the winner's SUBMITTING row). No duplicate creation; no exception escaped as a success; no stray exception types.
- **(b1) Submit in flight while completion lands:** the submit's creation (SUBMITTING insert + provider call, client entry timestamped) provably **began before** the case status flipped; it completed as pre-completion history (CREATED, 1 row), and its identical replay after completion **refused**.
- **(b2) Completion first, then submit:** refuses; zero rows; zero calls.
- **(b3) Simultaneous release, 6 trials:** every trial ended in exactly one of the two legitimate outcomes — submit won cleanly (creation began before the flip) or completion won (submit refused, nothing created). **Zero violations.**

*What the code's locking actually guarantees, precisely:* the duplicate-submit path is serialized — `BEGIN IMMEDIATE` plus the `(case_id, provider, request_id)` primary key make creation exactly-once per request id. The completion guard itself is a **status read at `submit()` entry** against the case store, which lives in a different database than `provider_requests`; the read and the insert are not one cross-store transaction. The executed guarantee is therefore: any submit whose entry read observes `NATIVE_SESSION_COMPLETED` creates nothing and calls nothing; a submit already past that read when completion lands finishes as pre-completion history and can never be re-submitted. No interleaving executed produced a creation that began on or after the completed status.

### Check 7 — Alternate entry points — **CONFIRMED: exactly one path, and it is guarded**
Whole-tree enumeration at head (grep, not sampled):
- `ProviderWorkflows` is constructed in exactly one place: `deploy/production_bindings.py:209`.
- `submit()` has exactly one caller in the tree: the operator route in `app/customer_app.py:190` (`POST /api/operator/appointments/<case_id>/provider`), which funnels through the guarded `submit()`.
- The only `INSERT`/`UPDATE` statements against `provider_requests` anywhere in the tree are inside `provider_workflows.py` itself (the submit path and its outcome updates).
- The only other reference, `core_platform/operational_probes.py:71`, is a read-only `SELECT … GROUP BY state` health probe — it cannot create.
**No bypass exists: every creation path inherits the guard because there is only one creation path.**

### Check 8 — Direct API calls — **CONFIRMED**
- **(a) Module level:** Check 1 is exactly this level — restated explicitly: a direct `ProviderWorkflows.submit()` call against a natively completed case refuses before any provider call or record.
- **(b) Through the composed HTTP app, gate approved in-process:** POST `/api/operator/appointments/<case>/provider` with an operator session against the natively completed case → **409 `{"error": "provider_request_conflict"}`**, with zero rows created and zero provider-client calls. Controls in the same drive: signed-out → 401; gate unapproved → 503 `approval_required` (submit never reached); the same request against a non-completed case with the gate approved → **201 CREATED** — proving the 409 is the status guard, not a broken route.

## Counts

- Retester-written exercised behavior checks: **36 — 36 passed, 0 failed** (Check 1: 3 · Check 2: 4 · Check 3: 9 · Check 5: 5 · Check 6: 8, covering 6 additional simultaneous-race trials · Check 8: 7, plus 2 auth-plumbing steps that succeeded but are not counted as verdicts).
- API/record verifications: 9 items (byte identity, 3 manifest hashes, SPEC additions-only diff 14/0, jurisdictions empty, gates 0/9, 4 commit file lists workflow-clean, entry-point enumeration).
- The fixer's own exercise numbers were not re-run and are not endorsed; the verdicts above rest on the retester's checks alone.

## Bottom line

**The discrepancy is closed.** `submit()` refuses a natively completed case before any provider call or record, with the codebase's own conflict error; the replay clause resolves fail-closed while pre-completion history stays readable; no regression was found in the submit path or its sibling consumers; no concurrent or alternate-path bypass exists in the tree; the HTTP surface returns the designed 409; and the corporate record — original claim, audit, corrective entry — stands complete and unrewritten, with the preserved audit byte-identical to the original.
