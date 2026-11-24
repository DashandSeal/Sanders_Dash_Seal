# Independent Audit — Stage 7, Sanders Dash & Seal Notarization Program

**Auditor:** independent subagent (built none of the work under review)
**Directed:** 2026-11-24 04:12 MST by the owner
**Subject:** `DashandSeal/Sanders_Dash_Seal` at head `90375704b5b358356d2132fcef690f056f47f6a2`
**Commits in scope:** `f01600f`, `7dc896b`, `e318c04`, `378b347`, `6ce1693`, `9037570`
**Method:** fresh clone of the remote at the audited head into `~/workspace/stage7-audit/clone` (builder's working copy never used); full code reads; hash verification via the GitHub API; 66 behavior checks written by the auditor from the claims and exercised in scratch databases / in-process drives (`audit_adapters.py`, `audit_journal.py`, `audit_bridge.py`, `audit_route.py` in `~/workspace/stage7-audit/`). Strictly read-only against the repo: nothing pushed, edited, fixed, or deployed.

---

## Verdicts

### Claim 1 — The journal — **CONFIRMED**
`core_platform/native_journal.py` is append-only (INSERT-only, one entry per session, re-recording returns the existing entry) and hash-chained in the GlassBoxAudit style (genesis `0×64`, entry hash = SHA-256 of the canonical body, `previous_hash` links). `NativeNotarySessions.complete()` instantiates the journal and calls `record_completion(session_id, db=db)` **inside its completion transaction**, after the state update and before commit. Exercised (19/19 auditor checks): a full RON completion wrote exactly one entry with the correct act kind, case binding, genesis link, and digests of the four completion-evidence kinds (contents not stored); the entry was indexed as JOURNAL evidence under its own hash; `verify_chain()` returned the entry hash; a tampered copy of the database failed chain verification; an uncompleted session was refused; with no seal registered, `seal_digest` was `None` and no notary was bound (nothing manufactured); with a seal row present, the recorded digest equaled SHA-256 of that seal's own signature bytes and the sealing notary was bound; and with the journal table sabotaged, completion raised **and the session did not complete** — the transactional property holds behaviorally, not just by construction. The journal's only writer in the repo is `complete()`.

### Claim 2 — The verifier adapters — **CONFIRMED**
Exercised (24/24 auditor checks, including real SessionAuth accounts created through the setup/register flows): identity verifies only when reviewer **and** notary both hold OPERATOR accounts (customer reviewer, customer notary, and unknown identity all denied). The commission adapter returns False with no commission record, on a state mismatch, and — always — with no injected registry adapter; through `backend/commission_sync.py`'s contract it verified only on official-shaped ACTIVE evidence (source `CO_SOS`) and denied an unofficial source and a non-ACTIVE status. The provider adapter denied unconfigured SignWell/BlueNotary, verified configured clients, denied unknown provider names, and denied Navu unconditionally (even with a `navu` key stuffed into the client set, its key mapping is `None`). A service mapped to no provider passed the provider leg alone, as recorded. Composed through `create_authority_review()`, `AuthorityReview` recorded REVIEW_VERIFIED only when all three legs verified, and denied the MOBILE_NOTARY case outright (Navu leg).

### Claim 3 — The bridge — **DISCREPANCY (one clause)**
The bridge itself is exactly as recorded (10/10 auditor checks on the mechanics): `open_session` refuses a non-operator, an unknown case, and an unpaid case; settlement was proven through the real `PaymentLedger.record_event` webhook path; RON → RON and MOBILE_NOTARY → E_NOTARY mappings hold; AUTHORIZED_DOCUMENT_SERVICE is refused; reopening is idempotent; completion mirrors onto the binding and propagates to the case record as `NATIVE_SESSION_COMPLETED`. Of the four consumers the record names, three demonstrably treat that status fail-closed — quote (the production fee verifier requires `AWAITING_HUMAN_REVIEW`), checkout (the production eligibility verifier requires `AWAITING_HUMAN_REVIEW`/`REVIEW_VERIFIED`), and human review (`AuthorityReview` requires `AWAITING_HUMAN_REVIEW`); `cases.authorize_notarization` refuses it as well.

**The provider-submission clause does not hold.** `ProviderWorkflows.submit()` performs no case-status check — its `authorize()` verifies only the operator and that the case exists — and in the auditor's drive it **created a provider request (state `CREATED`) against a case whose status was `NATIVE_SESSION_COMPLETED`**, using a configured client. No status check exists in the customer-app provider route either; the only barrier there is the global `ron_notarial` gate, which is not a case-state check. The sentence in the SPEC_CONFORMANCE Stage 7 entry ("a state every existing consumer treats fail-closed: no further quote, checkout, review or provider submission is permitted against it") and the same sentence in `native_case_bridge.py`'s module docstring therefore overstate the implementation for one of the four named consumers. Everything else in the claim holds.

### Claim 4 — The operator native route gate — **CONFIRMED**
Read in code and exercised through the real composed customer app (8/8 auditor checks): POST `/api/operator/appointments/<case_id>/native` with the gate unapproved answers the identical 503 `approval_required` / `gate: ron_notarial` as the provider route; `deploy/deployment.py` injects both gates as the same `lambda: _is_approved('ron_notarial')`. With the gate approved, POST opens through the bridge (201); GET returns the binding; with no bridge wired, GET answers 200 with a null session; non-operator POST → 403; signed-out → 401; wrong action body → 400.

### Claim 5 — Integrity at head — **CONFIRMED**
Verified via the API at head `90375704`: all **9/9** Stage 7 source files' SHA-256 equal their `.pbd.json` manifest `payload_hash`. The six commits touch 20 files (9 sources + manifests + the record doc), and **none is a workflow file**. `APPROVED_RON_JURISDICTIONS` is still `frozenset()` (empty). `core_platform/ai_platform_approvals.json` still shows **0 of 9 gates approved**. The preserved record `docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md` is byte-identical to the map it preserves, and the SPEC_CONFORMANCE Stage 7 entry matches the code — with the single exception of the provider-submission sentence recorded under Claim 3.

### Claim 6 — The named gaps are accurate — **CONFIRMED**
- **No live HTTP review route:** `create_authority_review` and `authority_verifiers` have **zero callers** anywhere in the repo; no route invokes a review. Accurate — if anything, the adapters are not composed into production bindings at all, which the record's wording ("adapters compose through `create_authority_review()`, but no route invokes a review") fairly covers.
- **AuthorityReview does not write case status:** confirmed in code and exercised — after a REVIEW_VERIFIED decision, the case remained `AWAITING_HUMAN_REVIEW`.
- **No Navu client exists:** `Navu` appears only in the service→provider map, the verifier's key table (mapped to `None`), and a compliance note; `provider_connections.py` has no Navu client. Exercised: Navu verification cannot pass.
- **ACT_EXECUTION vs KINDS:** stands exactly as recorded. The SPEC completion acceptance (line 840) requires an independently verified **ACT_EXECUTION** decision; `NativeAuthority.KINDS` contains `RON_PROVIDER_AUTHORIZATION` instead and no ACT_EXECUTION kind. Unresolved, as the record says.

---

## Discrepancies

1. **Provider submission is not blocked on a natively completed case.** The record (SPEC_CONFORMANCE Stage 7 entry; `native_case_bridge.py` docstring) states that `NATIVE_SESSION_COMPLETED` permits "no further … provider submission." In fact `ProviderWorkflows.submit()` checks neither the case status nor any equivalent, and a submission against such a case succeeded in the auditor's drive (request created, state `CREATED`). Quote, checkout, review, and `authorize_notarization` do refuse the status. Severity in today's posture is limited — the composed provider route remains behind the unapproved `ron_notarial` gate — but the sentence in the record is not true of the code, and once the gate is approved a provider request could be opened against a case the native track has already completed. Reported, not repaired (audit is read-only).

No other discrepancies were found. Nothing else in the six claims failed to hold.

## Auditor's check counts
- Exercised behavior checks (auditor-written): **66 total — 65 passed, 1 failed** (the failure is the Claim 3 provider-submission probe, which demonstrated the discrepancy). By script: adapters/review 24/24; journal/native chain 19/19; bridge/consumers 14/15; route gating 8/8.
- Read/API verifications: 9/9 manifest hashes; 6 commit file lists (20 files, 0 workflow files); gates 0/9; jurisdictions empty; record byte-identical to the preserved map; full reads of every Stage 7 module plus `authority_review.py`, `commission_sync.py`, `cases.py`, `appointment_payments.py`, `provider_workflows.py`, and the production verifier wiring.
- The builder's "51/51" was not re-run and is not endorsed as a number; the auditor's independent program above covers the same claims and reaches the same results except for the one discrepancy.
