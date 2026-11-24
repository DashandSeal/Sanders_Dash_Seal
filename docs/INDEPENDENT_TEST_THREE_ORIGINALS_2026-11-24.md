# Independent Test Report — Three Originals Reconstruction + Grantwriter Upgrade

**Head tested:** `683861f479735aa6e10ebf3b0ee0dced48f441b9` of `DashandSeal/Sanders_Dash_Seal`
(commit message: "Record Three Originals Reconstruction + Grantwriter maximum-level upgrade in SPEC_CONFORMANCE…", 2026-11-24T15:20:45Z).

**Tester posture:** independent — this tester built none of the code. All harnesses were written fresh for this test (in `/tmp/stage7/harness/`); the builders' `verify_*.py` scripts were **not** reused or executed. Read-only toward the repo: no pushes, no edits to any repo file.

**Method of obtaining the tree:** GitHub API tarball of the exact head SHA, fetched through the owner's-token helper (`~/workspace/custom-connectors/custom.github-pat/bin/gh_api.py` credential path), extracted to scratch at `/tmp/stage7/tree`. Execution used `~/workspace/.venv-simultaneous/bin/python` (Python 3.12.3).

**Verdict: NO DISCREPANCIES FOUND.** Every claim recorded in the five new `docs/SPEC_CONFORMANCE.md` entries at this head that was tested by execution behaved as recorded. 289 independent checks executed, 289 passed, plus the 9/9 triple-match and the SPEC prefix check below. (Counts differ from the builders' 60/77/68/82/76/116 because these are independently written harnesses with different granularity; the substance of each builder claim was exercised.)

---

## Setup verification

- **Head SHA verified** against the GitHub API commit object: `683861f479735aa6e10ebf3b0ee0dced48f441b9`.
- **Triple-match 9/9** — for each of the 5 new modules (`core_platform/rtsa_foundation.py`, `core_platform/uncle_nickey_mao.py`, `core_platform/carehive_os.py`, `core_platform/home_healthcare.py`, `core_platform/grantwriter_service.py`) and the 4 edited app/deploy files (`app/customer_app.py`, `deploy/deployment.py`, `deploy/production_bindings.py`, `deploy/sds_watchdog.sh`): local SHA-256 == GitHub-API-at-head SHA-256 == `.pbd.json` manifest `payload_hash`. All nine matched (e.g. foundation `cc49d4caf69f…`, grantwriter_service `e576fba70981…`, customer_app `06419ff3856e…`).

## 1. Foundation (`rtsa_foundation`) — 41/41

- Identity digest recomputed independently from the canonical JSON and matched; stable across calls; `validate_identity` rejects bad NAICS, bad region, empty id, non-identity.
- Geofence matrix (13 cases): authorized → `ALLOW` (incl. lowercase/whitespace normalization), well-formed unauthorized (`US-TX`, `FR`) → `STEP_UP`, malformed/empty/None/non-string → `DENY`. STEP_UP is a distinct token, never equal to ALLOW.
- AccessGuard: construction refused with no audit adapter, an adapter without `preserve`, and empty role scopes. Unauthorized access raises Forbidden and writes **no** receipt; empty actor likewise. Granted access returns a 64-hex block hash and writes **exactly one** `PLATFORM_RECORD_ACCESS` receipt with the correct platform attribution; the Glass-Box chain verifies. A broken audit sink converts access to `FoundationDenied` — nothing served.
- Check-in: integrity digest recomputed independently from stored fields and matched; identity digest bound; rollback leaves no record. **Tamper evidence:** after directly editing a stored check-in row's `operational_status` in SQLite, the recorded integrity digest no longer recomputes from the stored fields.

## 2. Identity binding + isolation between platforms — 22/22

Four services constructed on **separate stores sharing ONE Glass-Box audit chain**:

- Identity digests are pairwise distinct across the four platforms and stable; platform ids distinct.
- Cross-service id probing: an Uncle Nickey referral id presented to HH `intake_view`/`assignment_view` → denial (exception), not data; to CareHive `get_subject` → `None`; to Grantwriter `stage_for` → `None`. An HH intake id presented to Uncle Nickey `referral_view` → `BridgeDenied`.
- Operator-only operations do not cross: the UNM operator cannot check in through the HH service or run a CareHive cycle; the HH operator cannot check in through UNM or transition an UNM referral; the CareHive operator cannot transition an HH intake. Each platform's own operator succeeds on its own service.
- Shared-chain attribution: receipts carry the per-platform event prefixes `UNCLE_NICKEY_*`, `CAREHIVE_*`, `HOME_HEALTHCARE_*`, `GRANTWRITER_*` (each ≥1 on the one chain), and `PLATFORM_RECORD_ACCESS` receipts carry per-platform `platform_id` context. The single shared chain verifies end-to-end.

## 3. Uncle Nickey / Mao — 45/45

- Lifecycle matrix: full OPEN→ROUTED→ACCEPTED→COMPLETED path; every invalid transition refused (OPEN→ACCEPTED/COMPLETED, duplicate ROUTED, ACCEPTED→CANCELLED, unknown target, unknown id); stranger transition refused; non-operator cancellation refused; **terminal exits refused** from both COMPLETED and CANCELLED in all directions tried.
- Geofence step-up at service level: non-operator creating in `US-TX` → Forbidden; operator → allowed; malformed jurisdiction → Denied; same-industry and unknown-industry referrals refused; empty `subject_ref` refused.
- `referral_view` receipts **every** granted read: 3 granted reads (COORDINATOR, AUDITOR, OPERATOR) produced exactly 3 `PLATFORM_RECORD_ACCESS` receipts. An unknown-role read was refused and wrote **none**. (By documented design, a granted-role view of an *unknown* id is receipted first and then denied — the receipt is the evidence of the attempt.)
- Check-in operator-only; digest bound to the platform identity.
- **GUARDIAN_RECORD substance matches the recovered artifacts:** `rtsa_police_men/status.json` at this head has `topology.guardian_nodes == ["Uncle Nickey / Mao"]`, and `rtsa_police_men/index.html` contains the marker `GUARDIAN RELAY: UNCLE NICKEY / MAO [SYNCED]` verbatim. `guardian_relay_status()` returns the recovered record unchanged as one labeled half and live referral counts as the other.
- Registry: `uncle_nickey_mao` entry present (see §8) with a description stating the RECOVERED/REBUILT split.
- **No Guardian Watchdog (DeployPad) code is imported or referenced:** the module's imports are stdlib + `rtsa_foundation` only. The words "Guardian Watchdog"/"DeployPad" occur exactly once, in a docstring sentence stating that code is a separate platform's material and is **NOT used** in this module.

## 4. CareHive OS — 36/36

- **Challenge independence:** an unverified claim DISAGREES; claim + matching PASS postcondition AGREES; after a FAIL postcondition it DISAGREES again. With a PASS on record for a *different* observed state, the claim still DISAGREES. **Directly editing a subject's claim in the store** to an unmatched value → still DISAGREES; a forged claim with no postcondition at all → DISAGREES. The cycle never trusts the claim.
- Evidence chain: valid after appends; **directly tampering one entry's payload in SQLite → `verify_evidence_chain()` returns False.**
- Upgrade cycle: promotion without a PASS postcondition refused; two live candidates refused; duplicate version refused; promote demotes CURRENT→PREVIOUS_KNOWN_GOOD; rollback restores PKG to CURRENT and marks the displaced version RECOVERY; rollback with no PKG refused.
- Interop: all seven interfaces report `DOCUMENTED_INTERFACE_NOT_CONNECTED` in `status()` and in the module table; envelope validation behaves per family (FHIR/X12 positive and negative cases, unknown interface denied). `validate_envelope` transmits nothing — verified behaviorally (pure local return values) and by inspection: the module contains no network imports or calls (no urllib/requests/socket/http).
- **No patent filing is claimed:** every "patent" mention in the module is a negation — "not evidence of a patent filing or grant" / "No patent filing or grant is claimed" — and the documented-architecture bound ("design and invention-disclosure requirements, not proof of runtime implementation") is present verbatim.
- Operator-only subject registration and check-in; duplicates refused; audit chain verifies.

## 5. HH RTSA (Sanders Home Healthcare & Caregivers) — 37/37

- Service-line set is exactly the six recorded NAICS lines.
- Overlap matrix on one caregiver: partial overlap left, partial overlap right, exact, contained, containing, and one-second overlaps all refused; adjacency on both sides (`[0,1000)` and `[2000,3000)` around `[1000,2000)`) allowed; the window becomes reusable after COMPLETED and after CANCELLED. Inverted window and unknown intake refused; non-operator creation refused.
- Assignment completion: by a non-assigned caregiver → refused; from SCHEDULED (skipping CONFIRMED) → refused; by the assigned caregiver after CONFIRMED → succeeds.
- Access: cross-client `intake_view` refused **with** its access receipt present in the audit chain (receipt count +1); same-client view served; unknown-role view refused with **no** receipt.
- Consultation binding: `create_consultation_room` on a RECEIVED intake refused; on an ACCEPTED intake it creates a **real room in the real RoomService store** — the row exists in the rooms table with `room_type == 'CONSULTATION'` and `case_id` empty (no case binding faked). A service constructed with `rooms=None` refuses.
- **Schema inspection — actual columns (no name/diagnosis/free-text health columns anywhere):**
  - `client_intakes`: intake_id, client_ref, service_line, jurisdiction, status, created_by, created_at, updated_at
  - `caregiver_assignments`: assignment_id, intake_id, caregiver_ref, starts_at, ends_at, status, created_by, created_at, updated_at
  - `consultation_links`: intake_id, room_id, created_by, created_at
  - `platform_check_ins`: seq, platform_id, recorded_at, deployment_location, operational_status, identity_digest, integrity_digest

## 6. Grantwriter — 32/32

- **The gate, with the REAL `ai_platform_approvals.json` at this head:** `grantwriter_purpose` reads UNAPPROVED through the real `ai_platform_approval.is_approved`. Live drafting through the service was refused via **both** paths — (a) with the real `is_approved` bound as `approval_checker`, and (b) with no checker bound, i.e. the real `guarded_grantwriter_generation` path — and in both cases a **spy live generator was never invoked** (call count 0). A third construction with an explicitly-false checker also refused with the spy untouched. `status()` reports the gate UNAPPROVED; the designed level record is logic_level 12 of the 1–12 scale, professional.
- Offline draft proceeds and is labeled `mode='offline'` in the return value.
- Submission workflow: bare transition to SUBMITTED refused; DRAFT→READY skip refused; non-operator transitions refused; `record_submission` from READY records the operator-supplied external reference at SUBMITTED. Empty reference refused. **No transmission code path:** inspection of `grantwriter_service.py` finds no http/urllib/socket/requests usage at all; the module text states the submission is recorded state only and transmits nothing.
- Portfolio totals recompute independently from the base store by direct SQL: budget total 150000¢ and opportunity ceiling total 500000¢ and application count 1 all match `portfolio_view` exactly.
- Compliance evaluation truth values verified against a partially-complete application (budget ✓, evidence ✓, narrative ✗ → passed False).
- **The string "Mother" appears nowhere** in `core_platform/grantwriter_service.py`, in the registry's `grantwriter` description, or in `customer_app.py`'s grantwriter routes (grep over all three). (The pre-existing base *filename* `app/grantwriter_mother.py`, which the service imports, predates this build and is disclosed in the SPEC entry's residual limitations; it is not one of the three surfaces above.)
- Registry entries for all four platforms present and consistent — see §8.

## 7. Composed application (production bindings, WSGI) — 58/58

Driven in-process over WSGI against `deploy.production_bindings.create_production_bindings()` + `deploy.deployment.create_application()` on a fresh data directory, with a fictitious owner setup token and fictitious LiveKit/Daily keys in the environment.

- Standard regression: `GET /healthz` 200; storefront `/` 200; portal `/appointments` 200; customer intake `POST /api/appointments` 201; operator queue contains the case and is 403 for a customer; operator quote 201; checkout with the approved quote → **409** (honest Stripe-unavailable, no key configured); provider POST → **503 `approval_required`** (ron_notarial); native POST → **503 `approval_required`**; realtime room creation with fictitious keys → **503 `approval_required`** (voice_video_provider gate); voice turn refused when signed out; rooms drive (create 201, owner GET 200, stranger GET refused).
- **The four healthz routes** all answer 200 with the correct platform ids: `uncle_nickey_mao`, `carehive_os`, `sanders_home_healthcare`, `grantwriter`.
- Per-family discipline: signed-out platform status → **401**; wrong-Origin POST → **403 `origin_denied`**; a second app instance built with no platform bindings answers **503** on all four families' routes.
- One adversarial (non-happy-path) drive per family, at the route:
  - **Uncle Nickey:** out-of-region (`US-TX`) referral by a non-operator → **403**; the same referral by the operator → 201. Non-operator check-in → 403.
  - **CareHive:** promote attempt with **no PASS postcondition → 400 refused at the route**; after a PASS postcondition the cycle verdict is AGREES. Non-operator subject registration → 403; non-operator status → 403; local interop validation → 200.
  - **HH:** cross-client intake view at the route → **403, with the access receipt present in the composed audit db** (receipt count incremented by exactly 1).
  - **Grantwriter:** **LIVE draft at the route → refused** ("grantwriter_purpose approval required", gate unapproved); offline draft at the route → 200 labeled `mode='offline'`; status reports the gate UNAPPROVED; portfolio is operator-only (403 for a customer).
- The composed Glass-Box audit chain verifies end-to-end after the whole drive.

## 8. Record — 18/18

- **SPEC prefix:** `docs/SPEC_CONFORMANCE.md` at the prior head `e72a5709` (253,867 bytes, fetched via the GitHub API) is a **strict byte prefix** of the file at `683861f` (281,111 bytes) — append-only confirmed.
- **All 9 gates UNAPPROVED** at this head in `core_platform/ai_platform_approvals.json` (ai_role_workers, anthropic_live_model, daedalus_live, gateway_workflow_fix, grantwriter_purpose, release_verifier_pr2_checkout, ron_notarial, stripe_live_keys, voice_video_provider — every gate's status is `UNAPPROVED`).
- **`APPROVED_RON_JURISDICTIONS` is still empty** (imported and read: `frozenset()`).
- **Registry:** 49 entries, ids unique. Prior head had 47. `sanders_home_healthcare` and `grantwriter` existed at the prior head and were **updated in place (same ids)**; the only additions are `uncle_nickey_mao` and `carehive_os`; no prior id was lost.
- **The two interleaved automated "Verified Suite" commits, characterized by their diffs:**
  - `81ad126` (parent `74d9d16`, immediately after the HH RTSA commit): touches **3 files, all `.pbd.json` manifests** (`carehive_os.py.pbd.json`, `home_healthcare.py.pbd.json`, `uncle_nickey_mao.py.pbd.json`), 3 additions / 3 deletions — one payload-hash line refreshed per manifest. No source content changed.
  - `f35b428` (parent `08412a7`, immediately after the Grantwriter commit): touches **1 file, `grantwriter_service.py.pbd.json`**, 1 addition / 1 deletion — the same single-line manifest hash refresh.
  - Change class for both: automated manifest/hash bookkeeping only, trailing the build commit they follow. (Provenance of the automation itself was not assessed — only the diffs.)

## Observations (not discrepancies)

1. Uncle Nickey `referral_view` and HH `intake_view` receipt a *granted-role* access attempt before discovering the record does not exist / fails ownership, then deny. This is the documented design ("attempted accesses are evidence") and is consistent with the SPEC entries; the foundation rule "a refused access writes no receipt" holds for guard-level refusals (unauthorized role/category, broken sink), which is what was tested in §1.
2. HH `create_intake` raises `HomeHealthcareDenied` (rather than Forbidden) for a non-operator STEP_UP jurisdiction. The operation is refused either way; the SPEC entry does not specify an exception type.

## Scope limits

- All testing was **in-process** (direct module calls and in-process WSGI), against **scratch stores** in temporary directories. Nothing was deployed; no live server, network call, or external system was exercised.
- Keys and tokens used were **fictitious** (setup token, LiveKit/Daily keys). Stripe was unconfigured, so checkout's 409 is the honest-unavailable path, not a payment test.
- The builders' harness counts (60/77/68/82/76/116) were not reproduced as counts — they were not the object of the test; the SPEC-recorded claims behind them were, and each was exercised by an independent harness as detailed above.
