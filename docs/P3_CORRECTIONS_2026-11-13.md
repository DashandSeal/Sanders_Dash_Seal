# P3 corrections log — docs contradictions C1–C18 (2026-11-13)

**Branch:** `fix/p3-docs-polish-20261113`, off P2 head `335588b`.
**Scope:** the 18 contradictions and 13 stale/superseded docs identified in
the line-by-line cleanup (`~/workspace/cleanup-report-20261113.md` §3,
docs section) and its worker report
(`~/workspace/docs-cleanup-report-f4f72abe.md`), re-verified against the P2
branch before editing. Nothing was invented: every resolution cites the
evidence it rests on. Where a contradiction could not be resolved from real
evidence it is marked **UNRESOLVED** with both sides and the owner decision
needed.

**Approach per doc** (task requirement): live procedures and specs were
corrected **in place** (the wrong sentence now says the right thing, with a
dated correction note so the change is auditable). Dated October 2026
evidence snapshots were **not rewritten as if they had said something else** —
they got an archive/dated banner on top and the original body was left intact
(rewriting history would be dishonest). New documents created here:
`docs/COMPOSE_RECONCILIATION.md` (the compose evidence) and this log.

## Per-contradiction record

### C1 — README / AGENTS test command vs no `tests/`
**RESOLVED (by changed facts).** At main `f4f72abe` the README command
`python -m unittest discover -s tests -v` failed: `tests/` had been deleted
in commit `c28e61a`. On this branch `tests/` exists again (restored during
the November 13 repair work; 36 Python tests) and the command runs. Fixed
in place: `README.md` now states the command is current and points at the
live suites; `docs/ORACLE_DEPLOYMENT.md` carries the same note. The
`AGENTS.md` rule 8 ("Do not add, restore or run tests") still conflicts with
running tests at all — that conflict was already recorded by P1/P2 and is
not resolved here; this task's explicit test requirement was followed
instead, as P1/P2 did.

### C2 — Test counts 379 / 407 / 401 / 325 mutually inconsistent
**RESOLVED as historical, not as a true number.** All four counts are October
2026 snapshots from suites that no longer exist (`tests/` deleted in
`c28e61a`); none can be re-run, and they disagree with each other — including
407 vs 401 inside `docs/AI_TASKS_VERIFICATION_2026-10-23.md` itself. No
"correct" count was invented. Resolution: each count's doc now labels it a
dated, unverifiable snapshot — archive banners on
`docs/AI_RUNTIME_VERIFICATION_2026-10-23.md` (379) and
`docs/AI_TASKS_VERIFICATION_2026-10-23.md` (407/401), a status block at the
top of `docs/SPEC_CONFORMANCE.md` (407/401/379/325 with line numbers), and
the README note. Current verifiable suites on this branch: `tests/` 36,
sharpshooter 5.

### C3 — OWNER_STACK_STATUS "assembled on the review branch… not merged into main"
**RESOLVED (stale wording).** The text is on `main`, so "not merged into
main" was false as written. Corrected in place with a dated correction note
preserving the original sentence below it. The same edit corrects the second
false clause in that file, "compose.yaml now matches it byte-for-byte"
(see `docs/COMPOSE_RECONCILIATION.md` for the diff evidence).

### C4 — OCI GitOps workflow missing
**RESOLVED (marked, not fixed).** `.github/workflows/oci-gitops-deploy.yml`
does not exist on this branch (verified: workflows dir holds only
`closeup_vmax_pipeline.yml`, `parallel-build-verification.yml`,
`verify-bozly-integrity.yml`). The workflow cannot be created honestly in a
docs pass — it needs real OCI/GitHub wiring and secrets. Resolution:
`docs/OCI_GITOPS.md` now carries a NOT ACTIVE banner stating the file is
missing and the document is the proposed specification. Creating the workflow
is owner/coordinator work, not P3.

### C5 — Forensic-audit workflow missing
**RESOLVED (marked, not fixed).** `.github/workflows/forensic-audit.yml`
does not exist; the proposal lives at
`docs/owner-submitted/forensic-audit.proposed.yml.txt` (draft PR #3).
`docs/FORENSIC_SECURITY.md` now carries a PROPOSED banner. The same edit
removes the false "identical compose.yaml and docker-compose.yml" sentence
(see COMPOSE_RECONCILIATION.md).

### C6 — `deploy_backup.sh` path missing
**RESOLVED (real correction).** No `deploy_backup.sh` exists anywhere in the
repo (verified by filename search). The work is split across two real files:
`deploy/deploy_backup.py` (local SQLite online backup, no CLI flags) and
`deploy/ledger_backup.py` (Object Storage copies, real `--check` CLI).
`docs/LEDGER_BACKUPS.md` was corrected in place to name both files and give
the real commands. The old commands (`sudo bash deploy_backup.sh --check`)
would have failed with "file not found".

### C7 — LIVE_VERIFICATION title vs body
**RESOLVED.** Title said "live deployment verification"; the body itself says
no live rollout, OCI identity query, transaction, archive check or recovery
drill has been executed. Retitled in place to "Live verification procedures
(not yet executed)" with a dated correction note. Body untouched.

### C8 — October 22 banner vs body (4 files)
**RESOLVED (annotation, history preserved).** The banner (owner correction:
authorize-release / SANDERS_RUNTIME_FACTORY are not deployment requirements)
is correct; the body passages in `docs/DEPLOYMENT_SETUP.md` (2 passages),
`docs/ORACLE_BOOTSTRAP.md` (2), `docs/OCI_STANDARDIZATION.md` (2) and
`docs/RENDER_DEPLOYMENT_REVIEW.md` (1, plus the stale "main contains only
the README" observation) still stated the superseded requirement. Each
passage now carries a dated inline note marking it as pre-correction
procedure text describing the *optional* trusted-binding mechanism, not a
gate. The original sentences were left in place — deleting them would hide
what the October procedure said.

### C9 — GOVERNANCE "no valid .pbd.json = no production execution" vs AGENTS/OMISSIONS unsigned-is-not-a-blanket-ban
**RESOLVED (sourced narrowing).** The two rules genuinely conflicted as
written. Resolution uses the owner's own later instruction: AGENTS.md rule 7
records the October 22 owner instruction that an unsigned pair "is not
authorization for privileged application operations" and "is not a blanket
blocker to installing or starting the platform". `docs/GOVERNANCE.md` now
scopes its sentence to privileged application operations and quotes that
instruction, with a dated note. No owner decision remains on this point
unless the owner wants the stricter blanket rule restored.

### C10 — passenger/backend WSGI import vs native_runtime
**RESOLVED (by P0 code fix, docs updated).** `passenger_wsgi.py` and
`backend/wsgi.py` imported `create_native_application` from
`core_platform.native_runtime`, which never defined it. P0 rewired both to
the root `wsgi.py` factory (verified on this branch: both docstrings record
the rewire; `native_runtime.py:33` now defines the factory as a shim).
Docs updated: `docs/JADE_STOREFRONT_INTEGRATION.md` — its "still required"
items are now all done (portrait `web/sds-founder.png` exists, `/landing`
and `/assets/jade-landing.*` plus `/assets/sds-founder.png` are wired in
`app/customer_app.py:24–30`, `.pbd.json` manifests exist for the Jade files)
and the entry-point caveat was removed, keeping the "staging integration,
not a completed deployment" caveat.

### C11 — SOURCE_MAPPING cites RAW_PROTOCOLS file that is missing
**PARTLY RESOLVED (marked; restoration is owner work).** Three of the four
cited source files are absent from the repo (verified):
`Sanders_Dash_Seal_Actual_Build_Design_RAW_PROTOCOLS_2026-10-11.md`,
`Sanders_Dash_Seal_PBD_Routing_Logic_Both_Versions.md`,
`Sanders_Dash_Seal_Platinum_Blue_Diamond_Token_Protocol.md`. The citations
were kept (they are the October 15, 2026 record of what was read) and each
now carries a "[file not present…]" annotation. `docs/governance/HUMANITARIAN_CORE.md`
notes its "pending reconciliation" cannot be checked until the raw-protocols
file is restored. **UNRESOLVED remainder:** restoring the missing files, or
an owner direction that they are intentionally absent, is still needed.

### C12 — (no definition in the source report)
**UNRESOLVABLE — never defined.** The cleanup worker report enumerates C1–C11,
C13, C14, C15, C17, C18 and states there are 18 contradictions, but it never
states what C12 (or C16) is. There is nothing to resolve. If the coordinator
has a C12 definition elsewhere, it can be added to this log.

### C13 — STREAMING vs LIVE_VERIFICATION on live deployment
**NOT A CONTRADICTION (verified).** The cleanup report checked this and found
both documents agree live deployment is unproven. No change made.

### C14 — "Complete" catalog vs 2-resource file
**RESOLVED.** `docs/OCI_FREE_RESOURCE_MAPPING.md` retitled in place to
"Oracle free-resource incorporation (partial catalog)" with a dated note:
the canonical catalog `oci_free_resources.json` holds 2 resources (A1
allowance, boot-volume allowance, catalog date 2026-10-26). The allowance
figures in the body are published Oracle figures for planning, not measured
usage — that scope was already stated in the body and is now in the title
note too.

### C15 — Stripe account-enabled vs dev-only
**RESOLVED (clarification, both sides were already true).**
`docs/END_TO_END_PRODUCTION_ACCEPTANCE.md` (account `acct_1UQTehAgIE87JukG`
queried live Oct 15, 2026: charges/payouts enabled) and
`docs/STRIPE_INTEGRATION.md` ("DEVELOPMENT ONLY — NOT LIVE") describe
different things: the *account* is enabled, the *integration* is not live
(secret not in Vault, no live round trip). Each doc now cross-references the
other with that distinction stated explicitly. No Stripe configuration was
changed; real keys still need the secure flow (P0/P1 open item).

### C16 — (no definition in the source report)
**UNRESOLVABLE — never defined.** Same as C12: the source report never
states what C16 is.

### C17 — Progressive release policy vs missing GitOps workflow
**RESOLVED (marked, not fixed).** The policy authorizes automatic GitOps
deployment and describes "the active workflow" running tests, building the
ZIP and applying the stack — but no such workflow exists (see C4).
`docs/PROGRESSIVE_PRODUCTION_RELEASE_POLICY.md` now carries a status banner:
the policy is the owner's authorization, not evidence of automation, and its
workflow-dependent sentences must be read as the authorized design. Creating
the workflow is the same open work as C4.

### C18 — Bootstrap procedure vs unperformed setup
**RESOLVED (labelled).** `docs/INSTANCE_INITIALIZER.md` now carries a status
banner: procedure only, not proof of a live install, citing
`docs/OMISSIONS_AND_RESTRICTIONS_AUDIT.md` ("Initial OS administrator setup
remains unperformed"). `docs/ORACLE_AGENT_BOOTSTRAP.md` needed no change —
it is already written as an incident record (diagnostic run 40016589134,
failed passwordless sudo, installer not completed). The banner also corrects
the script path: `instance_init.sh` now lives at `deploy/instance_init.sh`
(P2 move).

## Claims checked and NOT found (do not cite)

- **"420 tests passed": 0 hits** in docs / README / AGENTS / MASTER or the
  repo (re-verified 2026-11-13). There is no such claim to correct.
- **"Daedalus": 0 hits** in docs / README / AGENTS / MASTER at main
  `f4f72abe`, as the cleanup reported. On this branch the only hit is
  `tests/README.md`, which honestly states no Daedalus code exists on this
  branch. Daedalus/voice code lives on separate unmerged branches
  (`rebuild/daedalus-20261113`, `feature/audio-video-voice-20261113`, and the
  November 13 synthetic-AI linking branches
  `link/synthetic-ai-daedalus-voice-20261113` /
  `link/synthetic-ai-platforms-20261113`). No Daedalus claim was added to
  any doc here.

## 13 stale/superseded docs — per-doc decision

| Doc | Decision | Reason |
|---|---|---|
| `docs/AI_RUNTIME_VERIFICATION_2026-10-23.md` | Archive-marked (banner, body kept) | Dated Oct 23 snapshot; counts unverifiable (C2) |
| `docs/AI_TASKS_VERIFICATION_2026-10-23.md` | Archive-marked (banner, body kept) | Same; internally inconsistent 407 vs 401 |
| `docs/MOBILE_SERVICE_READINESS.md` | Dated-snapshot banner | Oct 20 review of branch `build/security-foundation` @ `c1a8ffd`, not current HEAD |
| `docs/OCI_GITOPS.md` | NOT ACTIVE banner, spec kept | Workflow missing (C4) |
| `docs/FORENSIC_SECURITY.md` | PROPOSED banner + false sentence fixed | Workflow missing (C5); identical-compose claim false |
| `docs/SOURCE_MAPPING.md` | Missing-file annotations, entries kept | Citations are the Oct 15 record (C11) |
| `docs/OWNER_STACK_STATUS.md` | Opening + byte-for-byte claim fixed in place | Stale branch statement, false claim (C3) |
| `docs/ORACLE_DEPLOYMENT.md` | Test-command note added | Command valid again on this branch (C1) |
| `README.md` | Test-command note updated | Same (C1, C2) |
| `docs/DEPLOYMENT_SETUP.md` | Body passages annotated | Banner-vs-body (C8) |
| `docs/ORACLE_BOOTSTRAP.md` | Body passages annotated | Banner-vs-body (C8) |
| `docs/OCI_STANDARDIZATION.md` | Body passages annotated | Banner-vs-body (C8) |
| `docs/RENDER_DEPLOYMENT_REVIEW.md` | Stale sentence annotated | "main contains only the README" no longer true (C8) |

No doc was deleted. The 12 owner-submitted proposals under
`docs/owner-submitted/` were left as labelled provenance, per the cleanup
report — none is presented as current runnable source.

## What still needs owner input (from this pass)

1. **C11 remainder:** restore the three missing source files or direct that
   they are intentionally absent.
2. **C12 / C16:** supply the definitions if they exist; otherwise confirm
   there are only 16 defined contradictions.
3. **C4 / C17:** create `.github/workflows/oci-gitops-deploy.yml` (or
   direct that GitOps stays unimplemented) — the workflow is the missing
   piece behind both the GitOps doc and the progressive-release policy.
4. **C5:** create `.github/workflows/forensic-audit.yml` from the preserved
   proposal, or direct that the forensic pipeline stays a proposal.
5. **Compose canonical choice:** adopt `compose.yaml` as the single canonical
   file (proposal in `docs/COMPOSE_RECONCILIATION.md` §4) or direct otherwise;
   the volume/data decision (step 7) must be answered before
   `docker-compose.yml` can be retired.
6. **Root `deploy.sh` move (carried from P2):** still blocked — `deploy/deploy.sh`
   already exists as a different 62-line legacy script; moving the 212-line
   root bootstrap would collide and changes an owner-documented bootstrap
   location.
7. **Stripe config / verifier approval / deployment gates:** unchanged P0/P1
   open items; no deployment is claimed by this P3 work.

## Addendum — re-verified on `fix/everything-20261113` (P3 fix-everything, 2026-11-13)

This log was written on `fix/p3-docs-polish-20261113` (commit `afe1906`),
which is an ancestor of `fix/everything-20261113`. The P3 fix-everything
pass re-verified C1–C18 on that branch's P2 head `f6f18ea` before
changing anything. Results:

- **C1–C10, C13–C15, C17–C18: still resolved as recorded above.**
  The banners, retitles, annotations and scoped GOVERNANCE rule are
  present on this branch (pinned by `tests/test_p3_polish.py`, 22 tests).
- **C11: still partly open.** The three source files are still absent
  from this checkout (verified 2026-11-13): the RAW_PROTOCOLS archive,
  the PBD routing-logic file and the Platinum Blue Diamond token
  protocol file named in `docs/SOURCE_MAPPING.md`. Citations are kept
  as the October 15, 2026 record; nothing was invented to fill them.
- **C12 / C16: still undefined.** No definition exists in the source
  report; nothing to resolve.
- **C4 / C5 / C17: still open.** `.github/workflows/oci-gitops-deploy.yml`
  and `.github/workflows/forensic-audit.yml` still do not exist on this
  branch (verified 2026-11-13). Creating either is coordinator/owner
  work, not a docs fix.
- **New staleness found and fixed by this pass (P0–P2 introduced it
  after `afe1906`):**
  - C14 note re-staled: P2 rebuilt `oci_free_resources.json` to
    **6 resources, catalog date 2026-11-13**; the doc still said
    2 resources / 2026-10-26. Corrected in place in
    `docs/OCI_FREE_RESOURCE_MAPPING.md` (still a partial catalog
    against the full mapping table).
  - `docs/LEDGER_BACKUPS.md` and `docs/LIVE_VERIFICATION.md` still
    named the ledger volume `sqlite_storage`; P2 converged it to
    `sds-ledger-volume` (named `sds_production_ledger_data`). Both
    corrected in place with a dated note.
  - `core_platform/platform_services.py` module docstring still called
    the ledger handlers "stubs" and said `STRIPE_LIVEMODE=true`; P1
    made the handlers real SQLite-backed methods and P3 unified the
    livemode truthiness to `1` / `true` / `yes`. Corrected in place.
  - `README.md` still said `tests/` holds "36 Python tests"; the
    suite grew to the P3 final count (see the README note, updated
    with the verified count).
  - `platform_services.gateway_status()` referenced
    `docs/platform-link-checklist-20261113.md`, which did not exist.
    The checklist now exists, written from verified facts only
    (link registry 6/2/1/0, 9 gates UNAPPROVED, Gateway exit 128
    proposed-diff-only, DNS missing record, no deployment).
- **Root `deploy.sh` note:** this log (item 6 above) calls the root
  bootstrap "212-line"; on this branch it is **225 lines** and
  `bash -n` passes. A 2026-11-13 Oracle Run Command finding reported
  a 212-line `deploy.sh` with a syntax error at line 213 — that was
  the *simultaneous* branch (`deploy/simultaneous-20261113` @
  `4342b23`), not this branch; it is recorded for the coordinator,
  not fixed here.
