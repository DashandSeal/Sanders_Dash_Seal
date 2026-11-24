# Independent Retest — Concurrency Closure (Stage 7 follow-on)

**Subject:** The claim recorded in `docs/SPEC_CONFORMANCE.md` at head
`9d0b0a0bad1d6d904544e042ec59f7e62559f326` ("Concurrency closure — the
completed-case provider-submission guard is now ordered by construction, not
by timing", commits `c78f6a2` + `9d0b0a0b`): `ProviderWorkflows.submit()` holds
`BEGIN IMMEDIATE` on the cases store across (i) an authoritative re-read of the
case status and (ii) the commit of the `provider_requests` insert, so a
provider-request creation cannot commit after the case's native completion
has committed; the completion path already flipped the status under
`BEGIN IMMEDIATE` on the same store and was not changed.

**Verdict: CONFIRMED** — in every area assigned. One precisely-bounded
observation on `quote()` is recorded in §4; it does not touch the claim.

**Method.** Fresh eyes, adversarial posture, strictly read-only against the
repo. I cloned the repository fresh, checked out the exact head
`9d0b0a0b`, and cross-verified the tree against the remote: the two files
under test were re-fetched through the GitHub API and are byte-identical to
the clone (see §5). No builder harness, script, or scratch database was used
(`~/workspace/concurrency-closure-verify/` was never opened); every check
below is my own code, written from the claims, driving the repo's real
modules against my own scratch databases under
`~/workspace/concurrency-retest/`. A counting provider double stood in for
the provider client; no live provider call, payment, or notarial act
occurred. Fixtures mirror the production wiring in
`deploy/production_bindings.py` (one shared file for `CaseRegistry` +
`PaymentLedger`; `ProviderWorkflows` and `CaseNativeBridge` receive the same
registry). Case settlement used the real `PaymentLedger.register_checkout` +
`record_event` path; native completion used the real chain (bridge
`open_session` → authority decisions → RON room consent/recording →
`NativeNotarySessions.complete` → bridge `refresh`). The real `GlassBoxAudit`
backs the sequential sections; a thread-safe in-memory audit sink backs the
race fixtures for timing isolation (the audit is not part of the claim).
`CaseRegistry` fixtures pass `core_laws=None`, skipping the architecture
gate, which is unrelated to the concurrency claim. Totals: **33 harness
checks, 33 passed; 110 barrier-race trials, 0 violations**; plus the
code-reading and API verifications in §1 and §5.

---

## 1. Design claims against the code — CONFIRMED

**(a) The critical section spans re-read + insert-commit under one held
write lock.** `core_platform/provider_workflows.py` at head:
`submit()` begins at line 131; the pre-existing entry read/refusal is at
lines 133–134. The guard connection opens at line 162
(`sqlite3.connect(cases_path, timeout=10)`, path resolved from the
registry's `db_path`/`path`); `guard.execute('BEGIN IMMEDIATE')` at line
164; the authoritative re-read at lines 165–166 with refusal
(`ProviderRequestConflict`, same message as the entry refusal) at lines
167–168; the provider-store insert transaction at lines 169–178
(`BEGIN IMMEDIATE` line 170, replay/conflict check, `INSERT` lines
176–177) — its commit happens at the `with` block's exit, **inside** the
guard's `try`. The lock is released only in the `finally` (`guard.rollback()`
line 181, `guard.close()` line 182), and the provider client is called at
line 184, after release. Exactly as the SPEC entry describes, including the
fail-closed `ProviderUnavailable('case_store_unavailable')` when the
registry exposes neither attribute (lines 159–161).

**(b) The completion flip runs under `BEGIN IMMEDIATE` on the same file,
unchanged.** `core_platform/native_case_bridge.py` lines 173–180:
`_propagate_completion` connects to `self.cases.db_path`, executes
`BEGIN IMMEDIATE`, performs the `UPDATE cases SET status =
'NATIVE_SESSION_COMPLETED'`, and commits. Production passes both modules
the same `CaseRegistry` instance (`deploy/production_bindings.py`), whose
`db_path` and `path` are the same file (cases.py lines 30–33). The two
closure commits touched only `provider_workflows.py` + its manifest and
`SPEC_CONFORMANCE.md` + its manifest (§5), so the completion path was
indeed not changed.

**(c) Every other writer of case status — enumerated whole-tree.** Exactly
one `UPDATE cases SET status` exists in the entire tree: the bridge's
propagation itself (§1b). The remaining writers of the `cases` table:
- `CaseRegistry._execute_insert` (cases.py line 75) — INSERT of a **new**
  case with initial status `AWAITING_HUMAN_REVIEW`; it cannot move an
  existing case into or out of `NATIVE_SESSION_COMPLETED`. Called three
  ways, all serialized on the same file's write lock: `CaseRegistry.create`
  without a handle wraps it in its own `BEGIN IMMEDIATE` (cases.py line
  65); `AppointmentStore.request` passes its connection from inside its
  own `BEGIN IMMEDIATE` block on the same file (appointments.py line 90;
  the in-code comment at lines 105–109 documents exactly this lock);
  `platform_integration` and the case API call `create` directly.
- `AuthorityReview.review` computes a `REVIEW_VERIFIED` decision and
  writes it to its **own** `human_authority_reviews` table; it never
  writes the `cases` table.
- `stripe_payments.py` updates `stripe_cases.state` and
  `bozly_financial_ethics.py` updates `bozly_ethics_cases` — different
  tables, not the case status.
No status writer bypasses the serialization: every write to the cases
store contends on the same single-writer lock the guard holds, and the
only transition into the guarded status is the bridge's, which takes
`BEGIN IMMEDIATE` on that store.

**(d) The rejected alternatives' stated reasons — sound as far as code and
config show.** No module sets `journal_mode` on any of the three stores in
play; measured on live scratch databases, `PRAGMA journal_mode` returns
`delete` (default rollback journal) for the cases/ledger, provider, and
native stores alike. (WAL appears only in Bozly modules, on their own
separate database files.) The ATTACH rejection is therefore a
configuration-dependence argument, and it is a fair one: journal mode is a
persistent property of the file that a future connection could change,
and cross-database atomicity under WAL is not the same guarantee — the
chosen design depends on no file property beyond SQLite's single-writer
rule. The mirror-row rejection (drift from the record of truth; coupling
in the wrong direction; the guarantee would cover the mirror, not the
case) is a design judgment the code layout supports: the case record is
the only status of truth every other consumer reads.

## 2. Deterministic choreography — CONFIRMED (6/6 checks)

**Submit inside its critical section; completion cannot commit.** With the
provider store externally write-locked so the submit sat provably inside
its guard section (verified by a probe connection: the cases store refused
a test `BEGIN IMMEDIATE` only once the submit held it), a concurrent
`bridge.refresh()` propagation was started. For the full 2.5 s observation
window the completion thread remained blocked and the case status remained
unflipped. On release, the submit's insert committed (receipt `CREATED`,
exactly 1 row, 1 provider call), the flip then landed, and a replay of the
request refused. The creation is ordered before completion by the lock,
not by timing.

**Completion transaction open; submit blocks and refuses.** A transaction
replicating `_propagate_completion`'s exact statements (`BEGIN IMMEDIATE`
+ the same `UPDATE`) was held uncommitted on the cases store — stated
plainly: the real method cannot be paused mid-transaction from outside,
so its statements were held open verbatim; the full-chain races in §3 use
the real `refresh()` path. The submit passed its entry read (the
uncommitted flip is invisible to it), blocked at the guard for the full
1.5 s observation (thread alive, 0 rows, 0 provider calls), and the moment
the flip committed, refused with `ProviderRequestConflict` — still 0 rows,
0 calls.

## 3. Barrier races — CONFIRMED (110 trials, 0 violations)

My own harness: real modules, barrier-synchronized thread pairs, a
counting provider double, and commit-order instrumentation (the
provider-store connection is wrapped to timestamp the commit carrying the
`INSERT`; a watcher thread polls the case status at ~0.2 ms so a creation
is a **provable** violation only if its commit timestamp falls after the
flip was already observable, and **provably ordered** if it precedes the
last poll that still saw the case uncompleted). A violation is a
`provider_requests` row whose creation committed after the case's
completion committed. Every trial also re-attempted the submission
afterwards: all replays refused.

- **Full-chain** (real session completion, then `submit` vs
  `bridge.refresh`): 30 trials → **30 submit-first, every one provably
  ordered** by commit timestamps; 0 violations, 0 within poll granularity.
- **Tight** (`submit` vs `bridge._propagate_completion` directly):
  60 trials → 57 completion-first (submit refused, 0 rows, 0 calls),
  3 submit-first (provably ordered); 0 violations.
- **Duplicate-submit races** (identical payload, two threads): 20 trials
  → every trial exactly 1 row and exactly 1 provider call; in all 20 the
  loser observed the winner's finished `CREATED` row and received the
  stored receipt (the pre-existing sequential-replay semantics; no
  `SUBMITTING`-state conflict occurred with an instant double — a
  distribution note, not a defect).

## 4. Regressions and the named residuals — CONFIRMED (21/21 checks), one observation

Sequential behavior is unchanged: fresh submit `CREATED`; identical replay
returns the stored receipt with no second provider call; conflicting reuse
→ `ProviderRequestConflict`; unconfigured provider → `ProviderUnavailable`;
non-operator → `PermissionError`. Against a natively completed case:
submit refuses with 0 rows / 0 provider calls (complete-first fixture);
a pre-completion request's identical replay refuses while `records()`
still returns the historical row; a fresh submission refuses and creates
nothing. Sibling consumers refuse the completed case:
`CaseRegistry.authorize_notarization` → `CaseDenied`;
`AuthorityReview.review` → `AuthorityDenied`; `AppointmentPayments.checkout`
with the production eligibility verifier → `PaymentDenied('Independent
case eligibility required')`. Journal spot checks: exactly one journal
entry per completion across two completions, and `verify_chain()` returns
its head after each.

**Observation (precisely bounded, not a bypass):** `AppointmentPayments.quote()`
is a read-only lookup; for a case whose quote was approved *before*
completion it returns that stored quote rather than refusing. It creates
nothing, charges nothing, and writes nothing — and the only consumer that
can act on a quote, `checkout`, refuses the completed case (above). The
Stage 7-era shorthand "quote refuses the completed case" is exact for the
payment flow's eligibility verifier and for `checkout`; as a statement
about the `quote()` getter it holds only when no quote was previously
approved. This does not touch the concurrency claim; it is recorded here
because the assigned regression list named quote among the refusing
consumers.

**Residual (1) — in-flight provider call: behaves exactly as recorded.**
With a provider double delayed 1.5 s, completion committed (via the real
`refresh()`) while the pre-completion request's provider call was still in
flight; the submit then returned `CREATED` as pre-completion history, and
its replay refused. No request can be created or re-submitted after
completion; one legitimately created before it may finish its call.

**Residual (2) — lock timeout fails closed: verified by execution.** With
the cases store's write lock held externally, `submit()` raised
`sqlite3.OperationalError('database is locked')` after 10.0 s (the guard
connection's busy timeout), creating 0 rows and making 0 provider calls.

## 5. Record integrity — CONFIRMED

- Via the GitHub API at head `9d0b0a0b`: SHA-256 of
  `core_platform/provider_workflows.py` equals its manifest's
  `body.payload_hash` (`342111c9…`); SHA-256 of `docs/SPEC_CONFORMANCE.md`
  equals its manifest's (`57f07703…`). API bytes are byte-identical to the
  fresh clone used for all checks above.
- The concurrency-closure SPEC entry is present (final entry of
  `SPEC_CONFORMANCE.md`). Diff of the SPEC between `624c3308` and
  `9d0b0a0b`: **14 lines added, 0 deleted** — all prior entries, including
  the original Stage 7 entry and the corrective entry, stand unchanged.
- The two closure commits touch only their intended pairs: `c78f6a2` =
  `provider_workflows.py` + its manifest; `9d0b0a0b` =
  `SPEC_CONFORMANCE.md` + its manifest. No workflow files.
- `APPROVED_RON_JURISDICTIONS` is still `frozenset()` (empty) in
  `core_platform/global_compliance.py`.
- `core_platform/ai_platform_approvals.json`: 9 gates, **0 approved**
  (every status `UNAPPROVED`).

## Residuals I add

- None against the claim. The builder's two named residuals are both real
  and both verified by execution (§4). The `quote()` observation in §4 is
  the only statement in the surrounding record my checks could not
  reproduce literally, and it is a read-only getter outside the creation
  paths this closure governs.
- Scope note, for the record: verification ran in-process against scratch
  databases on this machine, as did the builder's; the closure is not
  deployed — it rides the owner's gated deploy path, and the live
  exposure remains zero while the `ron_notarial` gate is unapproved.

**Bottom line:** the record's claim is now true by construction, not by
timing. Submission and completion contend on one storage-engine write
lock; the re-read and the insert commit sit inside it; every writer of
the case record serializes on the same lock; and 110 executed races plus
deterministic lock choreography produced no interleaving in which a
creation committed after a completion.
