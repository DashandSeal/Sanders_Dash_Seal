# Original-specification conformance audit

> **STATUS 2026-11-13 (C2).** This file is the binding build record and a
> dated acceptance log, not a current conformance statement. The test counts
> inside it — **407** (line 17), **401** (line 42), **379** (line 94) and
> **325** (line 804) Python tests — are October 2026 snapshots from a `tests/`
> directory deleted in commit `c28e61a`. They are mutually inconsistent and
> none can be re-run or re-verified against this checkout. Read every
> "Verification: N tests passed" line below as "N tests passed on the stated
> October 2026 date, on that date's baseline", never as a result for the
> current HEAD. Current suites on this branch: `tests/` 36 Python tests,
> sharpshooter 5 tests. Full per-contradiction record:
> `docs/P3_CORRECTIONS_2026-11-13.md`.

## Model diagnostic recovery — October 23, 2026

Source: MASTER §§6–8 and 19–20; owner instruction to continue the real-time AIs.
Acceptance: a transient unavailable local model must not permanently suppress
future analysis of an open measured incident. Preserve each result and review,
retry only read-only diagnostic work with a durable minimum 60-second spacing,
avoid duplicate retry tasks across concurrent cycles, and stop creating retries
after a successful model response or observed incident recovery. Missing models
must preserve deterministic diagnosis and normal application availability. A
model timeout longer than the default work claim must receive an adequate
ownership interval; this is not a privileged execution lease. Test unavailable →
responding recovery, restart/concurrency, missing-model transitions and lease
ownership. Do not represent fixture responses as installed production inference.

Verification: **407 Python tests passed**, no skips; **219 source hashes match**.
Six added cases cover actual HTTP fixture 503 → responding recovery, preserved
attempts across restart, concurrent retry submission/ownership, observed recovery,
missing-model reconnection and response time exceeding the old claim. No installed
production model or new live authority is asserted by these tests.

## Oracle installer OS privilege repair — October 23, 2026

Source: MASTER §§6–8, 19–20, existing Oracle deployment, and owner directive to
remove artificial installation handoffs while preserving actual provider/OS
authorization. Live probe 40016589134 observed Oracle Linux 9.8, user `ocarun`
(uid 988), and failed passwordless sudo for both id and bash.

Acceptance: prepare a one-time administrator bootstrap, installing a root-owned
helper bound to the owner's private release bucket. Permit only a full commit
identifier; download only `installers/<commit>.sh` from that bound bucket using
Instance Principals, then execute the root-private downloaded file. Do not grant
arbitrary bash, caller paths, environment injection, bucket writes or general
sudo. Preserve existing IAM and source verification. Subsequent root installations
configure this helper automatically. An unprivileged agent cannot grant itself
OS administrator rights; record the initial administrator action as outstanding
until observed, rather than claiming the live deployment repaired.

## Durable technical-task execution — October 23, 2026

Verification so far: 401 Python tests passed, zero skipped. The new cases cover
concurrent ownership, expired claims, stale completion, persistent results,
redacted failures, no automatic mutation retry, grounding review, actual local
HTTP inference transport and rejected unsupported model output. The HTTP model
responder in tests is a fixture, not a real inference engine. Source pairs and
the embedded backend snapshot are synchronized; no authority signatures created.

Deployment follow-up: real Oracle Apply succeeded, followed by an actual failed
VM installation command. Read-only diagnostics retrieve the existing command
output with credential/key/URL redaction. The exit-code parser now handles OCI's
documented `content.exit-code`, retaining rejection of nonzero/boolean codes.
References: https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/instance-agent/command-execution/list.html
and https://docs.oracle.com/en-us/iaas/tools/python/latest/api/compute_instance_agent/models/oci.compute_instance_agent.models.InstanceAgentCommandExecutionOutputViaTextDetails.html.

Source: MASTER §§6–8 and 19–20; owner instruction to continue the unfinished AIs.
Acceptance: the existing technical dispatcher must run registered read-only
diagnosis work, preserve result and verification evidence across restarts, and
atomically assign work so concurrent workers do not execute the same active task.
An expired ownership claim may redeliver only explicitly read-only handlers;
stale workers cannot complete work after reassignment. Diagnose real stored
observations, mark hypotheses as hypotheses, and independently verify every
factual finding against observation history. Automatically create one diagnosis
task per observed incident. Preserve Manager/Quality/MINOTAUR/Vault/audit role
boundaries and application availability. Diagnostic completion grants no repair,
shell, signing or notarial authority. Preserve model-inference/live-authority
gaps explicitly; deterministic diagnosis must not be labeled model inference.

## Operational supervision completion increment — October 23, 2026

Live deployment diagnosis during this increment: main GitOps run 40010092156
authenticated with OCI and completed its real Plan, then the validator rejected
`oci_objectstorage_object.existing_installer[0]` as destructive replacement.
That object is a versioned release installer, not customer data. Acceptance:
permit replacement of only the known versioned installer/source objects within
the same private release bucket/namespace, retaining rejection of VM/bucket/data
destruction, unrelated object replacements, unknown destinations and paid compute.
Positive and negative regression cases cover both Terraform replacement orders.

Source: MASTER §§3–8, 15, 19–20; owner request to finish the real-time synthetic AIs.
Acceptance: carry all ten laws into running components; add a durable, recurring
observation/incident/recovery path; preserve separate role identities; expose actual
status only to the authenticated operator; retain application startup independently
of monitoring, inference or external authority availability. Persist observations,
diagnosis and recovery evidence across restarts; never equate an observation or a
model recommendation with Twin-Gate authorization, signed Quality approval, an
autonomous repair, or verified model inference. Preserve original privileged
execution checks. Tests must cover persistence, fault/recovery, malformed data,
one failed observer, concurrent cycles, API authorization and real HTTP probes.

The full independent inference, signing/custody, model learning and governed live
repair workstreams remain explicitly open until connected and demonstrated.

Verification: 379 Python tests and 22 Node tests passed, with no skips. Actual
local worker processes observed HTTP outage/recovery and retained SQLite history.
See `AI_RUNTIME_VERIFICATION_2026-10-23.md` for scope and unresolved live work.

Current owner-directed completion inventory: `OMISSIONS_AND_RESTRICTIONS_AUDIT.md`.
Earlier dated audit paragraphs are historical findings, not a blanket ban on
installation. The October 22 owner instructions and current implementation
records below govern ordinary startup; original privileged-operation authority
requirements remain distinct.

## Clearance handoff — October 15, 2026

Source: MASTER sections 8–10, with section 20 role separation. Acceptance criteria:
validate the requesting agent's assertion before contacting either authority;
request IT AI Manager necessity approval, verify it, then request independent
MINOTAUR clearance for exactly the same signing material; mint only after both
proofs verify and lifetime is rechecked; no retries, broadened scope, fallback
signatures, or token on a rejection or unavailable service. Preserve the nested
section 9 record and existing domain-separated signature format.

Implementation scope: a transport-neutral clearance coordinator using separately
injected authority clients and the existing Vault. This is not a new authority,
a signer implementation, a production transport, or deployment authorization.
Authenticated service adapters, production public trust keys and independent
key custody remain external integration requirements. Tests use generated keys
only. Production release remains blocked until all required controls are real.

Date: October 15, 2026. Initial build audited: `6027aefdb239a7e4e5471b698cb3c8b2a97089b5`.
Scope: all 15 files of the initial build against the four source documents already read in this conversation. This is a source review and targeted local test result, not a certification of the full platform.

**Overall: NOT fully conformant. Production remains blocked.** The original specifications remain requirements; incomplete implementation does not amend them.

## Current correction status — subsequent implementation

The original audit below remains as historical evidence. These findings have now changed:

- Flat lease fields were replaced with the MASTER section 9 nested metadata, identity, bounds and gate names. UTC timestamps, nonce, requesting-agent identity, commanding authority, verb/IP lists and one-use limit are present. An explicit signed `execution_binding` holds concrete public key, operation, request hash, executable hash and token class required to enforce the symbolic signature bindings; it is documented rather than hidden.
- Universal 60-second policy was removed. Vault requires an explicit deployment lifetime policy. Development tests exercise both 60-second and five-minute leases; this does not set production policy.
- Execution receipts now contain the MASTER's named metadata, telemetry, clearance and audit-trail groups. Unknown HTTP/transfer telemetry stays null. SQLite still does not meet immutability.
- The unrelated callback path was removed. A development runner verifies a signed source snapshot and the lease binds its executable hash. Altering even independently signed source under the same lease is rejected. Full production isolation, dependency closure and bootstrap enforcement remain pending.
- 30 distinct tests pass. Independent-signature checking also rejects equivalent authority keys written with different hex letter case.

**Overall remains NOT fully conformant for production.** No real synthetic-AI authority services, runtime isolation, network jail, immutable sink, provider integrations or human identity services have been created by these changes.

## Corrections made in this audit

| Finding | Original requirement | Correction and evidence |
|---|---|---|
| Vault also implemented Glass-Box Audit | MASTER 20 expressly requires separate responsibilities | Moved evidence persistence and chain verification into `GlassBoxAudit`, with a separate database in tests. Vault contains lease functions only. Role-separation regression test added. |
| All postcondition callbacks ran before the first result was verified | MASTER 8 and 19 require verified lifecycle completion | Verify Quality Agent output before requesting reconciliation, and verify reconciliation before requesting integrity reseal. Failed quality cannot advance those callbacks. |
| Final evidence-write failures escaped without triggering shelter state | MASTER 3, 16, 19: shelter, containment, evidence as a success condition | Finalization failure now contains the claimed agent and raises; revocation is attempted even if result evidence cannot be written. Tests cover result and revocation-receipt storage failures. This is still in-process containment only. |
| Documentation treated saved assistant interpretations as implementation authority | Owner's October 15 instruction: original specifications control | Added AGENTS.md and this audit; assistant interpretations are not accepted amendments. No claim of full conformance remains. |

## Requirement-by-requirement review

Status meanings: **partial** means some mechanics exist but the complete original requirement is unmet; **pending** means not implemented; **decision** means source conflict or unspecified semantics must be resolved by the owner.

| Original source | Requirement | Current implementation / gap | Status |
|---|---|---|---|
| MASTER 1 | Exact immutable platform identity | Literal name preserved in documents and signed body checks; no whole-platform identity enforcement | Partial |
| MASTER 2 | Multi-jurisdictional notarial operations; human/capacity separation | No notarial workflow, authority registry or human identity service | Pending |
| MASTER 3; RAW A | All nine Humanitarian Core Laws | Verbatim in GOVERNANCE; no semantic policy engine or human approval service | Partial |
| MASTER 4; RAW A | Self-healing, always learning, L15/L15+ | No learning, repair or complete L15 completion mechanism | Pending |
| MASTER 5 | MINOTAUR patrols separate real-time Shield | Separate verifier and containment classes only; no real-time intelligence or patrol | Partial |
| MASTER 6 | Dedicated IT AI Manager repair/recovery duties | Signature/reconciliation verifier only; no diagnosis, recovery, rollback or orchestration | Partial |
| MASTER 7 | Twelve specialized IT agent roles | No specialized operational agents implemented; Quality verifier is not a complete agent | Pending |
| MASTER 8; RAW C | Request → Clearance → Execute → Verify → Preserve → Revoke | Cryptographic checking and local lifecycle exist; no independent approval services, production execution boundary or complete failure orchestration | Partial |
| MASTER 9; RAW B, D | Exact nested lease and receipt standards | Initial implementation substitutes flat fields, epoch timestamps, one method/IP, public key identity and simplified receipts; commanding authority, explicit nonce, telemetry and other required fields absent | Decision / nonconformant |
| MASTER 10 | MINOTAUR denial: no token/bypass; full failover sequence | Missing signature prevents minting; no active denial-state service, approved failover, isolation, recheck or restoration sequence | Partial |
| MASTER 11; RAW E | PBD emergency class, bounded priority, short lifetime, melt/quarantine | Tier label, checks and revocation exist; no emergency trigger evidence, priority routing, continuous tamper response or durable requester quarantine | Partial |
| MASTER 12; RAW F | Normal route, real fault, PBD elevation, verified recovery | No routing engine; development callbacks are not routing implementation | Pending |
| MASTER 13; RAW G | Every executable has valid paired manifest before execution | Source has unsigned pairs; Python imports/tests run outside a production verifier. Manifest verifies supplied payload bytes, not the actual Python callback or its dependency graph | Nonconformant for production |
| MASTER 14; RAW H | Manifest generator binds script/scope/endpoint/manager/version/authorization | Generic unsigned body preparation exists; no original schema or signing-service flow | Partial |
| MASTER 15; RAW J | Continuous Sentinel Detect → Compare → Isolate → Alert → Preserve → Verify → Release/Rebuild | One-shot read-only scanning only; no isolation, notifications, evidence dispatch, continuous service or recovery | Partial |
| MASTER 16; RAW I | Immediate isolation, tamper-proof records, independent deterministic containment | Process-local flag and local hash chain do not meet these requirements | Pending production enforcement |
| MASTER 17; RAW K | Required directory/file pairing | Generic core modules only; payment_gateway.py, agent_matrix/integration_agent.py and pbd_global_sentinel.py topology not implemented | Pending |
| MASTER 18; RAW L | Working device is not root of trust | Injected public keys help; no remote attestation, external trust anchor or protected key custody | Partial |
| MASTER 19 | Success includes verified function, integrity, reconciliation, preserved evidence, destroyed authority | Signed checks and local revocation exist; no independent observations, immutable sink or demonstrated baseline restoration | Partial |
| MASTER 20 | Keep all named responsibilities separate | Audit/Vault merger corrected; remaining names are libraries, not independent production services | Partial |
| MASTER 21 | Treat design as actual build baseline | Documented in AGENTS and source mapping | Recorded requirement |

## Standing owner decision — October 15, 2026

Owner-confirmed precedence (October 15, 2026): **Sanders_Dash_Seal_Actual_Build_Design_MASTER_2026-10-11.md always controls wherever an earlier original protocol or example conflicts with it.** Apply this standing decision without asking again. Earlier material supplies detail only where consistent with MASTER. Assistant interpretations do not amend MASTER. Escalate only genuine ambiguities within MASTER or requirements MASTER does not resolve.

This resolves source hierarchy. In particular, MASTER section 11 governs emergency scope: urgency never expands cryptographically signed authority. Earlier wildcard or external-routing examples cannot override that rule. This decision does not make unimplemented features conformant, approve flat replacement schemas, or establish a universal lease lifetime from sample timestamps.

## Remaining implementation deviations and details

1. **Lease duration:** original standard examples span approximately five minutes; the original PBD emergency example specifies 60 seconds. I imposed a 60-second maximum across all classes. That generalization was not authorized. Class-specific policy and exact expiry rules need confirmation before changing signing semantics.
2. **Schema and scope:** original records use nested fields, permitted-method/IP lists, UTC timestamps and explicit nonce/authority metadata. I flattened them and restricted scopes to one method and IP. Original emergency examples also contain wildcard endpoints, while MASTER requires exact scope locks. MASTER section 9 supplies the production structure; MASTER sections 11 and 13 require exact signed scope locks. Earlier wildcard examples cannot expand an individual execution grant.
3. **External routing:** original Token Protocol version 1 describes forcing external tunnels and bypassing outside rate limits/geofencing; MASTER 11 states urgency cannot enlarge signed authority. The earlier build adopted the assistant interpretation without an owner decision. The owner has now resolved source precedence in favor of MASTER; compliance must be justified directly from MASTER rather than that interpretation. No external routing exists in this build. An internal credential alone cannot technically cause an outside service to honor priority; implementing this requires a receiving service's actual supported interface/authorization. No substitute is presented as satisfying the original claim.
4. **Manifest vs request payload:** original paired-file rule binds executable script bytes. The first lifecycle checks a caller-supplied payload while executing a separately supplied Python callback. It is therefore not a production execution gate. Artifact loading, dependency verification and enforcement must be designed against the original rule before enabling execution.
5. **Revocation/duplication:** one-use consumption is an implementation mechanism; it does not prove detection of silent copying, memory destruction, immediate cancellation of in-flight work, or the original complete quarantine protocol. Transport identity is also required to attribute a rejected request without allowing an attacker to quarantine another agent merely by naming its lease.
6. **Bootstrap:** original rule says no valid manifest means no execution. Current tests execute unsigned development source. No source-specified bootstrap/development exception has been approved. Development tests are evidence of mechanics only; this gap remains explicitly unresolved.

## Verification and next work

20 distinct local tests pass after corrections (16 existing, 4 additional). They verify the listed mechanics, not the missing operational infrastructure. Separate audit storage is tested; evidence-write failures produce no successful completion. Unit tests use disposable keys and do not establish real MINOTAUR, manager or Quality Agent approval.

Before further feature building: apply the confirmed MASTER precedence and resolve only remaining ambiguities within it; restore the approved original schemas and file topology; build a real artifact enforcement boundary; then implement the missing roles and infrastructure with source-linked acceptance tests. Do not merge or deploy this foundation as fully conformant.

## Next implementation acceptance criteria — MASTER sections 9, 13, 19

- Restore original nested lease field names, explicit UTC timestamps, nonce, commanding authority, verb/IP lists and one-operation bound. Bind agent identity and the exact operation payload cryptographically; preserve proof validation and durable replay rejection.
- Do not impose a universal duration inferred from an example. Require an explicit deployment lease-duration policy; tests provide their own policy.
- Preserve all named execution-receipt groups; record observed outcomes and signed postcondition evidence rather than simulated success.
- Separate executable artifact bytes from request payload bytes. A governed execution interface must accept a verified artifact, not an unrelated callable. Full production execution remains unavailable until an enforceable runtime boundary exists.


## October 16 owner-requested continuity and startup changes

Sources: MASTER Humanitarian Core Law 9 (identity), section 20 (separate roles),
section 22.24 upgrade mandate; owner's supplied screenshots preserving the agreed
Twin-Gate diagnostic-startup separation. This addition does not replace MASTER.

Acceptance: diagnostic readiness must not require consequential-operation grants;
unknown/sensitive operations deny on missing authorization or owner halt. A shared
upgrade guard must reject identity, role, or authority-boundary changes and loss
of recorded capabilities/protections before staging, while retaining existing
executor checks. Caller declarations alone are not independent identity evidence.
Tests must run under the repository's unittest runner; executable pairs must match.

Limits: this is development policy enforcement, not restored historical AI runtime,
cryptographic identity issuance, production deployment, or a replacement for the
previously approved Twin-Gate design. Production adapters must independently attest
artifact-bound identity records against owner-controlled baselines.

Validation: 100 unittest cases pass locally after adding the missing startup
module and shared IdentityPreservingExecutor adapter. The adapter composes with
UpgradeSidecar's existing executor interface but is not yet wired to a production
identity verifier. Existing executor policy failures propagate; rollback delegates
to the existing recovery adapter. Missing/stale Python manifest pairs repaired
with unsigned development manifests; no signatures or production approval created.

## October 20 mobile service acceptance

See [MOBILE_SERVICE_READINESS.md](MOBILE_SERVICE_READINESS.md) for MASTER-linked acceptance criteria, findings, changes and unresolved live connections. Mobile intake retains independent authority review; payment confirmation never authorizes an act. Validation: 108 local unittest tests pass. No production release or signatures created.

## Customer appointment workflow acceptance — October 20

Source: MASTER sections 1–3 (identity, human capacity and human review), 13–14
(executable pairing), 19–20 (evidence and separate roles), and the existing
END_TO_END_PRODUCTION_ACCEPTANCE.md payment/case acceptance contract.

Build an appointment-request interface connected to durable cases. Appointment
requests must never claim a confirmed time, current notarial authority or payment.
Authenticate reads and writes with an independent session adapter; no browser
identity headers, roles, price or paid flags are trusted. Reject cross-origin
writes, malformed inputs and another customer's case access. Preserve idempotent
request submission and pending human review. Quote approval is a separate trusted
operator operation and must verify fee eligibility before any Checkout call.
Use the existing payment ledger and raw signed webhook; redirects never mark paid.
No new identity provider, production keys, real charges or deployment approvals
are invented. Live release remains subject to the existing independent gates.

Customer-flow implementation evidence: see CUSTOMER_APPOINTMENTS.md. The operator
queue requires separately verified operator authority; quote approval additionally
requires independent fee verification. 128 local tests pass with fake identities
and a fake StripeClient; webhook verification uses signed test events. Browser QA
and production connections remain incomplete. Unsigned development manifests do
not authorize deployment. No live charge or notarial execution occurred.

## October 21 deployment entry point acceptance

Sources: MASTER sections 1–3 (platform identity and human authority), 13–14
(paired executables), 19–20 (evidence and distinct roles), and the October 16
owner-approved separation of diagnostic startup from consequential operations.
Owner request: deploy the existing platform and connect sandersdashandseal.com
and sanderslegalhelpersllc.com without a new hosting purchase.

Acceptance: provide a conventional WSGI entry point over the existing customer
application, not a replacement website. Missing production adapters must leave
all service operations unavailable. Readiness must never report success from
process liveness alone. Reject unrecognized Host values; ignore forwarded-host
claims. Use the Dash & Seal domain as the canonical service origin and redirect
safe reads from the Legal Helpers alias; never replay an alias write. Production
bindings must share the existing appointment/payment objects and canonical
Checkout origin. Webhook routing must retain independent release checks and the
existing raw signature-verifying handler. Load adapters only from trusted server
configuration, never from HTTP input. Pair every new executable with an unsigned
development manifest; do not fabricate production credentials or signatures.

This entry point supplies composition/startup mechanics. It does not supply a
hosting entitlement, production authentication/signing services, trusted adapter
implementation, external bootstrap validation or deployment authority. A local
diagnostic response is not a live or production-ready platform.

Validation: 140 unittest cases pass, including 12 new deployment boundary tests.
All 51 Python/JavaScript source-manifest hashes match, including both root WSGI
entry points. No production signatures, live charge, deployment or DNS change
was created by this source change.

## October 21 Oracle runtime packaging acceptance

Sources: MASTER 13–14 executable/dependency pairing and 19–20 verified evidence
and separate authority roles; existing deployment-entrypoint acceptance above.
Preserve the existing Python/WSGI application. Add non-root container packaging,
loopback-only host publication, persistent storage, bounded SIGTERM handling and
an HTTPS proxy include without granting missing release or customer authority.
Keep secrets and customer databases outside build contexts and source control.
Readiness must stay denied when real runtime adapters are absent. Do not infer
a Node worker or pipeline implementation from an incomplete pasted fragment.

Acceptance evidence and external limits are in ORACLE_DEPLOYMENT.md. A real
HTTP/SIGTERM runtime test supplements the application regressions. Container,
ARM, TLS and host configuration are separate validation requirements. No source
approvals, production identities or signatures are fabricated; all new executable
pairs remain UNSIGNED_DEPLOYMENT_BLOCKED. No Oracle or DNS mutations occur here.

## October 21 Node ingestion integration acceptance

Source: owner's complete Node/Python architecture proposal, MASTER 13–14 and
19–20, and the existing appointment request contract. Node owns transport;
Python retains authentication, release verification, transactional storage,
idempotency, auditing and human review. Do not create an alternative transaction
store, share document/Vault files with Node or treat receipt as approval.

Acceptance: exact canonical Host/Origin and socket path, independently verified
Python session before upgrade, Python reauthorization on every submission,
bounded connections/payloads/rates/in-flight work/response buffers/timeouts,
heartbeat and bounded SIGTERM drainage. Acknowledge only Python's successful
appointment request receipt; errors and uncertain timeouts never return success.
Retry uses the same request ID and Python's existing idempotency checks. No
generic dispatch_transaction authority or fabricated production session adapter.
Use an optional isolated container profile, current supported Node LTS and a
locked dependency. Test real HTTP/WebSocket denial and lifecycle paths. Keep
missing production bindings, signatures, ARM/host/TLS checks explicit blockers.

Implementation evidence: 141 Python tests and 16 Node tests pass locally,
including real loopback WSGI/SQLite integration using disposable fake identities.
The locked worker dependency audit reported zero known vulnerabilities at this
check. Container and combined Nginx syntax verification are added to CI, which
does not deploy. See INGESTION_WORKER.md for supported behavior and limits.


## October 21 owner-selected stack

The owner explicitly selects the latest supplied stack AS IS. Its exact
package.json, worker/Dockerfile and docker-compose.yml supersede the assistant's
appointment-only transport choices. Preserve supplied versions, endpoints and
service definitions without substituting assistant preferences.

The latest index.js submission begins inside a message handler. The complete
file is still needed; do not invent a prefix or combine it with the earlier,
different implementation. Previous 157-test evidence applies only to that
previous implementation. The supplied Dockerfile copies no lockfile before
npm ci; record this limitation without silently editing the owner's file.
No Oracle or DNS changes or production authorization are implied.


## October 21 complete selected design assembly acceptance

Owner instruction: add the entire supplied design to GitHub. Sources: the
complete earlier worker and subsequent transaction/session/heartbeat/shutdown
revision, owner-selected Compose/Docker/package files, MASTER 13–14 and 19–20.
Keep the supplied latest JavaScript helper and shutdown bodies verbatim; assemble
only missing imports, HTTP/upgrade/session/message setup around them. Identify
this connecting code explicitly. Add /api/auth/verify and
/api/transactions/process over independently supplied Python authentication and
transaction processing, durable SQLite receipts, Nginx HTTP/WebSocket routing and
backend container context. Generic transactions must not be replaced with an
appointment-only transport. No supplied version or Compose setting is changed.

Validation must separate source assembly from successful production build.
Maintain denial when real authentication, processing and release adapters are
absent. Session data is credential input, never trusted as an identity assertion.
Tests must exercise successful recording, rejected authentication, revocation,
failed processing, replay conflicts and default denial. No paid resource,
production credentials or authority signatures are invented.


Selected-stack assembly evidence: 152 Python tests pass. The actual selected
index.js process passes its integration test against the real Python pipeline
API/SQLite store using disposable credentials. All 79 paired artifact hashes
match. The selected ws 8.16.0 dependency audit reports one affected package with
high severity; no version substitution was made. Full stack build, backend
container and actual root Nginx syntax have separate CI checks. No prior clean
build/audit result is transferred to this selected stack.


## October 21 owner-directed Docker lockfile correction

Source: owner's hardened Dockerfile fix, exact manifest guardrail and lockfile/
audit commands. Acceptance: copy package.json and package-lock.json together
before npm ci; retain Node 20.12.2, npm >=10, direct ws 8.16.0 and the requested
matching override. Regenerate the lockfile and run the requested non-forced audit
fix. Do not claim an audit passes merely because a vulnerable version is pinned.
Push the updated paired hashes to PR #3 and verify actual CI results. No
production deployment, credentials, paid resources or version substitutions.


Correction validation: lockfile generation completed, and the requested audit
fix exited 1 with one high-severity affected package (direct ws, not a hidden
nested package). It retained the exact ws 8.16.0 pin/override; no --force was run.
152 Python tests and the selected worker/Python transaction integration pass.
Build verification is delegated to the actual CI container build.


## October 21 forensic pipeline and signed receipt acceptance

Source: owner's Platinum Forensic Security Audit proposal and receipt function;
MASTER 13–14 cryptographic executable pairing and 19–20 separate audit/authority.
Preserve the supplied workflow and receipt snippets as provenance. Implement the
same checkout/digest/drift/incident stages, six-hour schedule, main/release push
and main PR events, and recipient rooseveltsanders381@gmail.com. Explicit fixes:
outputs outside the checkout, include tracked dot-directories, compare actual
bytes to paired expected hashes, fail the check on detected anomalies, validate
permissions/duplication and verify a consumer signature before VERIFIED writes.
No checksum is described as a digital signature or deployment approval.

Use read-only token permissions, pinned action commits and no credential-bearing
checkout. Keep SMTP in GitHub Secrets and a separate notification job that does
not execute checked-out code or expose mail secrets to PR code. Record missing
mail configuration; do not claim activation or delivery. No automatic repair,
release, paid service or production signing key is created. Keep the existing
ws dependency audit result visible; a forensic workflow does not resolve it.


Forensic extension validation: all 168 Python tests pass, including 8 tripwire
and 8 real-signature receipt regressions. An isolated clean snapshot containing
207 current repository files passes the forensic scan with zero anomalies.
Unsigned source pairs remain explicitly unsigned; this is not signature approval.
SMTP secret inventory is unavailable through the connector, no email was sent,
and the scheduled workflow is not active while it remains on the review branch.


## October 21 Oracle host bootstrap acceptance

Source: owner's deploy.sh/Compose v2/firewalld/integrity monitor/Let's Encrypt
proposal and MASTER 13–14, 19–20. Preserve the Node/Python/SQLite topology,
existing free Oracle host, domains and public-IP context. Supply actual
Compose maintenance services, initial HTTP ACME staging, renewal and graceful
Nginx reload, host integrity monitoring and readiness validation. Correct the
non-repository Docker URL, fixed-zone assumption, missing source staging,
missing certbot service, incomplete IP test and premature success message.

Do not stop the entire running stack before replacement, delete volumes,
overwrite deployment credentials or manufacture source/signing authority. A
real independently installed release-authorizer and runtime adapter configuration
must precede production host changes. Scripts must not report live from an Up
process alone or promise zero downtime from one instance. Keep operational
changes explicit and test failure paths. Save on GitHub; this session has no
Oracle SSH/session access and cannot write the instance's home directory.


Bootstrap preparation evidence: all 177 Python tests pass, including mocked
active-zone rules, zone refusal, missing authorizer, OS rejection, host source
integrity drift and conditional certificate renewal/reload. bash -n passes;
systemd accepts the twice-daily UTC calendar. A clean 229-file source snapshot
passes the forensic audit and all 95 paired artifact hashes match. Production
Compose/HTTP ACME syntax and Certbot container checks are added to CI. No live
ACME request, Oracle operation, DNS cutover or authenticated public socket test
was run. Existing ws audit findings are unchanged.

## October 21 ledger backups and near-zero architecture acceptance

Source: owner's private sds-ledger-backups bucket, Instance Principals upload,
midnight backup proposal, separate ARM worker and API Gateway/Functions/Streaming
proposal; MASTER 13–14 and 19–20. Preserve these proposals as source material.
Implement an online SQLite backup from the actual backend named volume, integrity
and restore verification, private temporary files, checksum-verified OCI upload,
explicit instance-principal authentication, bounded dedicated-bucket allocation,
no overwrite/deletion and a separately enabled midnight UTC timer. A hash is not
a signature. Verify prerequisites rather than assume IAM, bucket or second host.
Do not create paid services, silently replace the chosen VM topology, claim
account-wide billing enforcement, or activate a schedule before a real successful
backup. Document remote-worker syntax and serverless persistence/cost limits.

Backup preparation evidence: 190 Python tests pass, including 13 new real-WAL,
container-helper streaming, committed/uncommitted state, source absence, size,
privacy/versioning, IAM/Docker/upload failure cleanup, restore corruption and
changed-content regressions. Shell syntax and the midnight UTC calendar pass.
An isolated 243-file candidate snapshot passes forensic checks with zero issues;
all 100 source/config pairs match and remain unsigned. OCI CLI syntax was checked
against official documentation; OCI/Docker boundaries in upload tests are mocked.
No real bucket, IAM policy, upload, schedule, extra VM or managed service was
created. Existing ws audit findings remain unresolved. Oracle's Streaming FAQ
explicitly excludes it from the free tier; Functions has finite free allowances
and API Gateway is metered. Preserve the optional proposal without claiming $0
active managed-service usage or migrating the durable SQLite/WebSocket design.

## October 21 owner-supplied OCI Function source preservation

Source: owner's repeated complete func.py, func.yaml, requirements.txt and
limits-query submission. Preserve the three file bodies exactly in
serverless/sds-transaction-validator-fn; do not replace their business logic or
route production traffic to them. Pair the source/config files with unsigned
hash manifests. Record syntax verification separately from security acceptance.
The submitted handler's VERIFIED writes do not verify a signature; INSERT OR
REPLACE permits conflicting receipt replacement; missing IDs are accepted;
per-record failures still yield batch_status SUCCESS; default /tmp SQLite is
not shared durable ledger storage. Keep these known deviations visible under
MASTER 13–14 and 19–20, and leave production use blocked. The limits command
reports resource limits, not pricing, free-tier eligibility or available usage.
No function application, stream, connector, frontend cutover or paid resource
is authorized merely by saving these proposed files.

Preservation validation: Python compilation succeeds and all three new source/
configuration hash pairs match. An isolated temporary-database execution of the
actual submitted function (FDK response replaced only by a local capture stub)
reproduces unsigned VERIFIED writes, conflicting replacement, missing IDs and
batch SUCCESS on a failed write. This characterizes known deviations; it does
not approve them. No dependency installation, image build, OCI invocation or
live Limits API query was performed for this function.

## October 21 integrated event-driven implementation acceptance

Source: owner's instruction to use everything supplied and proceed with full
integration, including Streaming, Connector Hub, Functions, Object Storage and
the existing Nginx/Node/Python/SQLite core. Preserve original Function files.
Add a separately named integrated entrypoint and explicit integration manifest,
OCI request renderer and authenticated producer utility. Connect function-task
output to the storage target; accept receipts only after the existing Python
core commits. Retain Node/WebSockets and existing application routes.

MASTER 13–14 and 19–20 require independent signature/release authority and durable
transactional receipts. Add a signed stream boundary with trusted actor-key
bindings from the administrator's runtime factory; never accept a payload key,
UNSIGNED, conflicting retry or a failed-write success acknowledgement. Use the
existing receipt verifier and transaction processor in one SQLite transaction.
Function retries must be idempotent and failures visible. Keep /tmp out of the
integrated authoritative ledger path. Restrict the backend stream route to the
private subnet at Nginx and require independently verified signatures as well.

Record the explicit hybrid: Functions handles events on demand while the selected
Python/SQLite core remains durable on the existing VM. This does not establish
zero idle resources for the whole platform, maximum measured throughput or free
Streaming. Render requests locally without creating resources. The no-additional-
cost requirement and missing authenticated OCI access still preclude actual
metered provisioning. Frontend production cutover requires real producer identity,
network, resources and business-authority bindings; never invent these.

Integration evidence: 211 Python regressions pass (21 new stream integration
checks), plus the selected real Node/Python/SQLite relay test. Three actual FDK
0.1.128 fixture checks pass locally for response protocol, committed receipt
output and transport failure propagation; peer HTTPS is simulated. Tests cover
real Ed25519 verification, atomic rollback, simultaneous duplicates, partial
batch retry, conflicting actor/ID reuse, key/release revocation and publisher
admission failures. Rendered JSON field names match OCI SDK 2.189.0 model maps;
service-side ranges, resource existence and permissions are not claimed.
An isolated 265-file candidate passes forensic scanning with zero anomalies;
all 110 source/config pairs match and remain unsigned. The original three
Function files are unchanged. CI now builds the integrated Python 3.11 container
and runs the actual FDK protocol checks. Live OCI resources, ARM64 image release,
private DNS/TLS route, signing identities, business bindings and frontend direct
publishing remain external dependencies. Existing ws 8.16.0 audit failures are
not removed or bypassed. No paid service or production deployment occurred.

## October 21 owner-authorized ws upgrade and live verification acceptance

Source: owner's Step 1–3 dependency remediation, OCI mapping, private service
routing and deployment/receipt/backup loop. The explicit ws 8.17.1-or-later
instruction supersedes the earlier exact 8.16.0 pin/override. Preserve metadata
and architecture; select current patched 8.x, regenerate lockfile, run npm ci,
production audit, existing relay tests and CI builds without suppressing findings.
Current registry/audit and maintainer advisories identify 8.22.0 as the latest
8.x; 8.17.1 remains affected by later disclosure/fragmentation advisories.

Do not label the supplied readable OCIDs, ://oraclecloud.com endpoint or sample
signature as verified identities/credentials. Do not check .env.secrets into git.
Add read-only environment/resource identity validation that rejects placeholders,
checks real CLI API responses and never creates resources or changes routes.
Correct the deployment verification procedure to preserve the existing Compose
project/production override, use the actual named SQLite volume, real signed
supported operations and independent backup restore evidence. No compose down,
notarial verification assertion, fake signature, public root-path receipt test
or bucket listing alone establishes live production readiness. Actual Oracle
queries/deployment remain unavailable without authenticated host access.

Remediation evidence: package and override both pin ws 8.22.0; npm install
--package-lock-only and npm ci --ignore-scripts completed. npm audit --omit=dev
reports zero known vulnerabilities. The selected Node/Python/SQLite relay and
all 220 Python tests pass, including nine read-only identity/placeholder/IAM/
compartment/privacy checks. An isolated 270-file snapshot passes forensic audit
with zero anomalies; all 112 paired hashes match and remain unsigned. No actual
OCI API request or host change occurred. Oracle's documented public-subnet
Internet Gateway + All Services Service Gateway conflict is reflected in the
live-verification guide; no unsupported route was applied. The supplied sample
notarial payload/signature is not represented as a real authorized transaction.

## October 22 repeatable OCI instance standardization acceptance

Source: owner's golden image → instance configuration → cloud-init → production
roll blueprint, named SDS-Platinum-Golden-Image and SDS-Standard-Production-Template.
Preserve the submitted YAML as provenance. Supply a real fail-fast bootstrap,
immutable commit selection, standard instance-configuration/cloud-init renderer,
optional persistent owner-requested sysctl profile, integrity monitoring and
explicit staged versus activated states. Reuse the existing deploy.sh authority,
active-interface firewall handling, Docker layout and readiness gates. Do not
clone main blindly, treat YAML runcmd cd as persistent shell state, print success
on an earlier failure or bake credentials/production data into a reusable image.

Oracle documents downtime during custom-image capture and image storage charges;
images contain the boot disk, not attached block volume data. Instance
configurations are selected templates, not retroactive tenancy-wide policy or
proof of installed software. Retain the $0 constraint: no image/instance creation,
100-node launch, paid storage or production capture is performed. Do not clone
an authoritative SQLite ledger into multiple independent production writers.
Unsigned pairs and missing independent runtime/release authority remain blockers.

## October 22 automated OCI inventory acceptance

Source: owner's request to make Tenancy Explorer resource discovery an automated
Sanders Dash & Seal function. Add read-only Instance Principals discovery across
subscribed regions, including the chosen root/child compartment subtree; paginate
Search results, compare explicitly configured expected identities/states and
previous successful observations, and preserve private machine-readable evidence.
Install a six-hour host timer through the existing authorized deployment and
staging paths. Report failed/partial visibility and stale previous success
honestly; an invisible resource is NOT_OBSERVED, not proof it was deleted.
Do not grant IAM, provision resources, silently repair routes, send external mail,
claim full tenancy visibility, or treat inventory as billing/transaction/readiness
verification. Search is eventually consistent and permission-filtered. No actual
OCI query or timer installation is possible without authenticated host access.

## October 22 production automation profile integration acceptance

Source: owner's staged multi-node instance_init.sh and six-hour inventory cron
proposal. Preserve the submitted script verbatim as provenance, including its
incomplete final conditional. Provide a runnable instance_init.sh entrypoint
using the existing release-authorized bootstrap; require a full commit SHA,
separate stage/activate invocations and a verified per-node public IP for
activation. Preserve failure exit status and do not turn a successful worker
build/test into production authority. Retain the existing six-hour systemd
inventory timer rather than installing a duplicate cron job or nonexistent scan
script. Do not issue malformed IMDS requests, run a missing npm test script,
claim a Node test runs the whole Python suite, pull uncontrolled images, remove
orphans or rewrite the current production stack. Clarify that current inventory
observes selected identity/state metadata, not IAM policy or bucket-setting
contents, and that passing development CI is not complete live verification.

## October 22 dual-engine preflight and local IMDS integration acceptance

Source: owner's run_preflight_checks.sh, revised initializer and local metadata
helper. Preserve submitted scripts separately. Implement actual Node and Python
regressions in disposable validation containers containing their test sources,
without production volumes/ports/secrets or missing pytest/npm commands. Require
an exact clean source commit; use the existing independent release verifier
before bootstrap invokes source validation. Run preflight on stage/activation
without making a passing suite grant release authority. Preserve original exit
codes, separate activation, and the existing cross-region inventory timer.
Add a bounded fixed-endpoint IMDSv2 helper using the documented instance id,
hostname, canonicalRegionName and state keys, not an invalid URL/lifecycleState
key or success-looking fallback. Local metadata is supplemental evidence and
must not replace compartment inventory or be called cryptographic attestation.
Do not hardcode an unverified SHA, require .git in the archived production tree,
claim static test totals or 100% full production verification. No live host calls
or application start are authorized merely by running development tests.

## October 22 first-boot system audit acceptance

Source: owner's interactive stacking diagnostic and cloud-init telemetry profile.
Preserve the submitted cloud-config separately. Add an observational architecture,
Git/Docker/OCI binary, bounded Compose-plugin and protected-directory permissions
audit. Evaluate shell variables/date at runtime (no literal escaped dollars),
store a private bounded log and print it to cloud-init output. Integrate into the
existing single cloud-init execution chain before the approved bootstrap, rather
than replacing its source/release/preflight controls. Place the embedded audit in
/usr/local/sbin, outside the managed /opt application tree, so it cannot create
untracked drift before source staging. Missing initial tools/directories are
reported as gaps rather than false success or installation. Reject symlink logs,
preserve actual audit errors and do not install software, alter permissions,
create OCI resources or claim a live SSH connection merely from supplied commands.

## October 22 OCI Resource Manager automation stack acceptance

Source: owner's master Terraform/main.tf/cloud-init ZIP provisioning blueprint.
Preserve submitted sources. Package a real Resource Manager stack with managed
provider authentication, A1 1-OCPU/6-GB shape, current compatible platform image
lookup or explicit image selection, actual compartment/AD/network inputs and
existing-network reuse by default. Add optional isolated VCN/subnet/IGW/route/
NSG creation. Pin application source to a full commit and include the established
first-boot audit and approved bootstrap profile; no mutable main or fake OCIDs.
Supply a browser-uploadable ZIP, tests and Terraform validation in CI. Do not
apply a stack or create paid/cloud resources in this workspace. Make explicit
that Terraform provisioning does not prove cloud-init/application completion;
private Git access, genuine runtime/release bindings and capacity still need
provisioning. Audit-only first boot must be labeled, and approved stage must keep
existing independent gates. No zero-downtime guarantee or invented 283-test pass.
Do not import, replace, stop or overwrite the existing sanders-dash-seal VM.

## October 22 Resource Manager application activation acceptance

Source: owner's correction that the uploaded stack must deploy Sanders Dash &
Seal itself fully, rather than stop at infrastructure or audit-only staging.
Expose the existing approved activation path in the stack, including exact
source checkout, dual-engine regressions, production Compose, DNS/TLS, durable
SQLite identity, readiness checks and timers. Discover this node's assigned
public IPv4 from authenticated OCI VNIC records bound to its local IMDS identity;
never inherit the original server address. Make Resource Manager wait for actual
external TLS/readiness and canonical aliases when activation is selected, failing
the job on missing readiness rather than promoting VM provisioning to success.
Retain explicit provisioning/staging profiles for deliberate diagnostic use.

This change cannot create genuine external runtime adapters, release authority,
private repository access or DNS control from absent inputs. Prepared image
prerequisites must be explicit and validated before activation; no paid image
capture or bypass of independent production controls is introduced. Missing
requirements remain blockers to a turnkey deployment package, not reasons to
label diagnostics a full application. No actual OCI Apply, DNS edit or production
activation is performed here.

## October 22 owner-directed removal of imposed deployment prerequisites

The owner explicitly directs removal of the custom authorize-release executable
and SANDERS_RUNTIME_FACTORY deployment prerequisite, and requires the ZIP to
install/start Sanders Dash & Seal itself. This instruction supersedes earlier
assistant-authored statements making these interfaces or unsigned development
pairs blanket infrastructure/deployment blockers. Retain hash/pair integrity,
source identity, independent application authorization, human notarial review
and truthful feature readiness. Starting containers does not grant a notarial act,
create an authenticated session, verify a payment or fabricate signatures.

Acceptance: supply application source inside the upload ZIP; securely transfer
it via a private OCI artifact bucket using per-instance IAM, with no private Git
credential, prebuilt custom image or separate authorizer/runtime-factory file.
Install OL9 dependencies, validate payload SHA and file hashes, run disposable
regressions, start the supplied Node/Python/Nginx/SQLite stack, install monitoring
and automatic DNS-dependent TLS activation. Report installed application health
separately from still-unconfigured business integrations; never turn a 503
service-authority result into a claim that authentication/payments are operational.
No actual cloud Apply or live readiness is asserted from local checks.

## October 22 explicit owner spending restriction

Owner reiterates sole control of spending and strict $0 Oracle Free Tier scope.
No OCI Apply or cloud resource creation has been executed. Disable additional
instance/artifact provisioning by default; do not present assumed free capacity
as verified billing eligibility, upgrade an account or add paid services. The
new-node installer does not yet automate installation onto the existing VM and
must not be labeled a completed full production deployment. Preserve removal
of the imposed authorizer/runtime-factory prerequisites. Actual OCI session
access, remaining allowance and application integrations have not been verified.

## October 22 complete free-resource incorporation acceptance

Source: owner's three supplied documents: InfoQ's July 3, 2026 Ampere allowance
report; Oracle Always Free Resources (June 12, 2026); and Oracle Viewing All
Resources in a Compartment (September 18, 2026). Owner asks to incorporate the
entire documented free resource set into Sanders Dash & Seal immediately, under
sole owner spending authority and strict $0 scope. Record all free resource
categories and their quantitative/conditional limits, shared pools, intended
platform roles and source provenance; include supporting discovery semantics.

Acceptance: integrate a machine-readable catalog and read-only application
resource view; connect the existing scheduled inventory to catalog mapping
without confusing observable resource counts with metered free usage. Supply
advisory capacity comparisons only when explicit usage is available. A resource
appearing in Tenancy Explorer is not evidence of Always Free entitlement.
Functions' published pricing allowances are distinct from this supplied catalog.
No blanket authorizer/runtime-factory requirement, new deployment dependency,
cloud creation, paid activation, account upgrade or replacement of SQLite is
introduced. Keep inventory permission/freshness limitations, document trial vs
free-only differences and do not claim deployment or live provider integration
from catalog incorporation. Pair source changes and test denied/unknown states.


## October 22 owner instruction: automatic Oracle implementation and hosting

Source: owner request that Sanders Dash & Seal automatically implement the free resources and establish effective hosting on Oracle. Acceptance: replace catalog-only behavior with executable existing-instance deployment; provision private Standard backup storage, monitoring/notification resources and exact-instance IAM; bind actual identifiers to host configuration, enable online SQLite backup/restore verification and recurring resource checks. Reuse the owner's 1-OCPU/6-GB VM by default, with no additional compute, paid service, DNS purchase or account upgrade. Preserve all 26 documented categories; report unimplemented integrations explicitly. Resource Manager remains the cloud state owner. A Cloud Shell activation helper must run Plan, reject destructive/unsupported resource actions, Apply, dispatch the application install through the Oracle agent, and check actual execution status. Missing Oracle credentials or agent administrator permissions must return failure, never a false deployment success. This workspace cannot independently authenticate to the owner's Oracle account.


Owner's direct-install follow-up: preserve immediate cloud-init start and Resource Manager Apply. Correct paid E4 to Always Free-eligible A1; use the supplied existing instance to discover actual compartment/network instead of fake OCIDs; package actual private source instead of invalid `https://github.com .`. A separately named direct ZIP selects NEW 1/6 A1 explicitly, while the existing-host ZIP remains available. Do not claim DNS control, actual cloud success or all-category service provisioning. Do not stop the existing platform with compose down.


Validation for automatic activation: 297 local Python tests, one skipped; generated installer Bash syntax and HCL parsing pass. Official Terraform 1.5.7 initialized the signed OCI 9.11.0 provider successfully. Full Terraform validate could not start the provider because this workspace denies its Unix listening socket (`operation not permitted`); Oracle Resource Manager Plan is not reported as run. No actual Oracle provisioning, administrator permission change, DNS change or deployment was executed.


## October 22 complete application composition request

Controlling source: MASTER sections 2, 3 (human loop), 18 and 20; owner request for an end-to-end Oracle upload and instruction that installation not depend on a custom authorizer or runtime factory. Acceptance: default deployed WSGI must compose actual persistent customer accounts/sessions, customer/operator appointment flows, itemized quote and existing Stripe Checkout/webhook adapters, and authenticated Node/Python ingestion. Separate customer account authentication from human notary identity/commission and independent AI approvals. Never promote a first public registrant to operator or grant authority from a supplied role header. Generate a single-use owner-setup secret on the host, keep it out of archives/logs, and persist consumed status. Ordinary intake must start without provider credentials; provider-dependent actions must report precise unconfigured status and never fake success. Add working sign-in/register/logout/owner-setup screens, opaque hashed sessions, expiry/revocation, CSRF/origin controls, bounded requests and durable throttling. Prove account → login → intake → quote → Checkout adapter → signed webhook → paid record and independent customer authorization, plus authenticated ingestion/deduplication and rollback, using real components and synthetic provider doubles. This test evidence does not claim a real external payment/notarial act or complete implementation of MASTER's synthetic-intelligence services.


Owner's consolidated-artifact instruction supersedes the earlier two-artifact presentation: deliver only `sds-unified-production-stack.zip`, containing the direct new 1-OCPU/6-GB application installation profile and complete source. No separate activation launcher is required.

Current validation: 308 local tests, 307 passed and one skipped; JavaScript and installer Bash syntax pass. The rebuilt backend source snapshot matches the actual source. Stripe account access was rechecked on October 22: the owner's connected account is live, charges_enabled and payouts_enabled are true; no webhook endpoints were returned. The previous expired-connection finding is superseded. This account access does not install a runtime API credential or webhook signing secret on Oracle. No live payment, Oracle Apply or DNS cutover is asserted.


## October 22 owner GitOps automation instruction

Source: owner's supplied GitHub Actions → OCI Resource Manager deployment workflow. Acceptance: on main pushes, run real Python and Node regressions, build the complete single ZIP using the repository packager and actual commit, authenticate the GitHub runner through protected OCI API-key secrets, update the explicitly configured real stack, automatically Plan and Apply with the existing-host activation implementation, and wait for zero-exit agent installation. Use the existing 1-OCPU/6-GB VM without adding paid compute or account upgrades. Never substitute printed test counts for execution or job submission for completed deployment. GitHub-hosted runner inclusion and account budgets must not be represented as unlimited free service. No private key is stored in source, ZIP, artifacts or logs; no custom manual release-approval field is introduced. Existing new-node stacks must not be silently converted or destroyed.


Owner's "absolutely no restrictions" follow-up: do not add manual approval environments, a required self-hosted runner, custom authorizer tokens or verification checkboxes. Use the supplied standard GitHub-hosted Linux runner. Retain actual failure reporting, API authentication, source integrity and the owner's preceding $0/no-paid-resources scope. Hosted-runner overage billing cannot be disabled by source code or the available GitHub connector. Current local GitOps validation: 313 Python tests, 312 passed and one skipped; five new authentication/upload/failure tests pass; workflow YAML parses. OCI credentials, actual stack ID and repository secret-write capability are not available in this workspace, so no live GitOps deployment is asserted. Docker is unavailable locally; container builds remain an actual workflow step, not a claimed local success.

Node validation completed separately: all 17 tests passed after npm ci; npm audit reported zero vulnerabilities.


## October 22 skipped-server-test investigation

Source: owner's request to identify the repeatedly skipped test and reason. Acceptance: report actual remote branches, install pinned server dependencies, execute real Gunicorn HTTP and SIGTERM integration, remove its dependency-based silent skip, update assertions to the current concrete application's actual readiness/authentication contract, and use an isolated temporary database. Full-suite CI must install requirements-server.txt. Initial unskipped execution exposed stale expectations of 503 on /readyz and appointment APIs; current native runtime correctly reports core readiness and requires customer authentication. Preserve unknown-host rejection, clean shutdown and explicit complete-build readiness=false; never weaken production authority checks or call local HTTP proof an Oracle deployment.

Installed requirements-server.txt and reran the actual Gunicorn integration: PASS, including correct core readiness, unauthenticated-request rejection, unknown-host rejection and clean SIGTERM. Full local suite: 313 passed, zero skipped. Removed Gunicorn missing-dependency skip. The separate owner-file ownership test still has an explicit non-root-only skip condition; it ran and passed in this root workspace. Full-suite GitHub workflows now install pinned server dependencies. Remote main was independently read at 032d4a455490a6665e245bd3b85faf3b39cb16ce; deployment work was on build/domain-deployment-entrypoint, not merged to main.


## October 22 owner restriction-removal and omissions audit

Source: owner asks what was omitted, removal of assistant-added restrictions, and recognition that the owner is the final decision-maker. Acceptance: remove the obsolete manual release-evidence/environment-approval workflow; replace hardcoded BLOCKED readiness observations with honest known/unknown reporting that cannot authorize or block installation; remove unsigned-manifest wording implying a blanket installation ban without inventing signatures; remove the assistant-created existing-host-only GitOps mismatch and support the owner's actual existing/new A1 stack profile while preserving its state. Continue to stop on real deployment failures, preserve credentials/private records, retain MASTER Humanitarian Core Laws and independent authority requirements for privileged operations, and honor the owner's $0/no-unapproved-paid-resources instruction. Identify unmet provider integration and independent-AI service implementation separately from imposed restrictions. First merged GitOps job evidence: actual Python tests, Node tests/audit, both Docker builds, integrity scan and package creation passed; deployment step received empty OCI identity/private-key/stack secrets and failed. No authenticated Oracle deployment is implied.

Restriction-removal validation: all 313 local Python tests pass with zero skips. The owner-bootstrap unit now models only the privileged ownership boundary and runs actual file creation/modes/hash/recovery on non-root runners too; it does not claim independent proof of deployed filesystem ownership. Legacy assistant progressive-release policy and blanket activation verdicts are superseded. Current omissions are enumerated in OMISSIONS_AND_RESTRICTIONS_AUDIT.md.

## October 22 owner-directed completion of provider connections

Controlling sources: MASTER sections 2–3 (human/capacity separation and human in the loop), 8–9 and 19–20 (independent AI authority and truthful receipts), and the owner's instruction to connect unfinished functions to Sanders Dash & Seal itself. Acceptance for this increment: provide operator-authenticated, case-bound SignWell template document creation and BlueNotary RON session creation in the actual native WSGI runtime and operator workspace; use the providers' documented fixed HTTPS endpoints and authentication; persist request fingerprints/resource references without storing signer payloads, credentials or provider login URLs in audit records; reject cross-case request reuse and prevent automatic duplicate POSTs after uncertain outcomes. Report provider acceptance separately from signing, notarial completion or jurisdiction approval. Keep customer intake available without keys. Extend the existing designated OCI Vault loader for actual SignWell/BlueNotary credentials and explicit SignWell test mode. Accept either the owner's standard Stripe secret key or a restricted key with matching live/test environment; recommend restricted keys without making that recommendation a startup requirement. No live provider transaction, account upgrade, paid activation, invented key/prefix, fabricated authority signature or Oracle connection is authorized by a test double. The independent AI services remain separate unfinished implementations; these human-directed provider requests do not replace their privileged autonomous execution chain.

Primary API references checked October 22: https://developers.signwell.com/reference/createdocumentfromtemplate and /reference/create-a-document; https://bluenotary.readme.io/reference/create-new-notarization-session and /reference/getting-started-with-your-api. BlueNotary's overview contains a contradictory sample signing_type; use the endpoint schema's ron/esign/ipen enum, with ron for the owner's RON track. This increment uses provider-hosted templates, not a purported completed encrypted document vault. Provider completion webhooks, evidence retrieval and jurisdiction authorization remain explicitly unfinished.

Credential-transfer acceptance for the same request: read the owner's STRIPE_SECRET_KEY (or STRIPE_API_KEY), STRIPE_WEBHOOK_SECRET, SIGNWELL_API_KEY and BLUENOTARY_API_KEY only from the GitHub runner environment; merge them into the single existing ACTIVE sds-runtime-provider-config Vault secret after Apply and before dispatching installation. Use an etag, CURRENT stage and a root-private temporary CLI input file; never put secret content in Terraform state, user-data, command arguments, artifacts or logs. No supplied provider fields means preserve existing Vault configuration. Identical content must not create another secret version. Missing/ambiguous destination, invalid values, failed transfer or failed installation cannot be reported as connected. Provisioning the designated Vault/key/secret itself remains an external setup gap in this increment; no arbitrary existing vault is silently chosen.

Completion-increment validation: all 325 local Python tests pass, zero skipped. The 12 new provider/credential tests exercise actual WSGI authentication and case binding, SQLite persistence/restart, documented POST construction, uncertain-outcome duplicate rejection, redaction/redirect boundaries, matching standard/restricted Stripe keys, private temporary handoff, merge/concurrency/current-bundle behavior, and configured GitOps hook wiring. HTTP provider responses and OCI APIs are test doubles; no real signing invitation, notarial session, cloud write or payment was executed. JavaScript syntax passes. A search for earlier sidecar packages returned no results; that search is not proof that earlier work never existed. It supplies no missing runnable independent services to this checkout.

## October 22 supplied Oracle stack binding

Source: owner's existing Resource Manager stack and instruction to add to the
current deployment, without replacing its infrastructure or reducing MASTER scope.
Acceptance: main GitOps uses the actual supplied Phoenix stack when no override
is configured; an existing Actions secret or variable takes precedence. The OCID
is a resource identifier, not an API signing credential. No fake credentials,
new stack, automatic account upgrade or production-success claim is introduced.
All 17 unfinished workstreams remain in scope.

## Native document custody and integrity correction — October 23, 2026

**Controlling requirements:** October 11 MASTER §§2, 8, 13, 15, 19 and 20. The exact executable/document identity, tamper detection and evidence verification are mandatory, while independently verified commission and human execution remain distinct from an Ed25519 signature.

**Acceptance criteria:** Signature and seal modules must verify actual bytes from the same protected document store as upload, reject changed/missing documents before recording a cryptographic assertion, and preserve the native runtime's existing default storage directory. Nonstandard trusted storage paths must be supplied explicitly; no caller-controlled upload path is inferred. Each executable source must have a matching hash-accurate PBD development manifest; no production signatures may be invented. The embedded backend source snapshot must reproduce the tracked source exactly.

**Implemented correction under verification:** Optional constructor-level `storage_dir` for native signatures/seals, matching document tests, and regeneration of missing/stale paired source manifests. This is a native code/test correction, not an additional installation approval control.

## Native completion is bound to independently verified authority — October 23, 2026

**Authority:** October 11 MASTER §§2, 8, 15, 19, 20. A self-asserted `verified: true` field is not independently validated evidence of notarial commission, signer identity, human execution, or completion. The authority registry requires a trusted independent verifier to register decisions.

**Acceptance:** Exact per-session, unexpired decisions for IDENTITY, COMMISSION, JURISDICTION, METHOD, HUMAN_ATTESTATION and independently verified ACT_EXECUTION must all exist before session completion; RON additionally requires RON_PROVIDER_AUTHORIZATION and a room with consent and indexed recording digests that match its stored session evidence. The supplied human/identity/commission/act evidence identifiers must exactly match the registered decisions. Mismatch, expired or future-dated authority, missing registries, incomplete RON media, cancelled sessions and replay must not mark completion. Changes are limited to the native completion operation, preserving all independent human authority and the original MASTER architecture; ordinary installation has no extra gate.

**Implementation:** The native session completion transition checks the durable authority registry and RON evidence index in its existing atomic SQLite transaction. The registered ACT_EXECUTION entry is independently checked by the separate registry client, not inferred from signatures, seals, receipts or a boolean sent by the operator. Unit regression tests exercise fail-closed cases and positive registry-backed E_NOTARY/RON transitions with disposable test verifiers. Production identity, commission, authorized provider and actual recording verification still require live independent integrations before factual notarial execution is represented to a customer.


## Owner amendment: Humanitarian Core Law 10 — October 23, 2026

Source: Roosevelt Sanders' explicit instruction to add the tenth core law, together with his instruction not to add blockers or restrictions to the application. MASTER §3 now includes verbatim:

> Sanders Dash & Seal shall always use only Oracle Always Free resources.

Acceptance criteria: preserve laws 1–9 verbatim; add law 10 to MASTER and GOVERNANCE; embed its exact text and source in the existing OCI resource catalog exposed by the application; synchronize the embedded backend source snapshot and hash manifests. Do not introduce a blanket startup, execution, shutdown, or additional approval gate. Preserve existing privileged-operation safeguards and the owner's no-unapproved-spend instruction.

Implementation: governing-source and runtime-catalog amendment. The existing catalog API exposes the added governing_core_law field. This amendment records the owner's law; it does not establish tenancy-wide enforcement, verify live Oracle usage or billing, or change OCI resources. Existing comparisons remain advisory. Live deployment is separate from this source change.



## Core Law 10 owner-wide scope — October 23, 2026

Source: Roosevelt Sanders: “That shall be the tenth law for every platform,past, present, and future builds of mine”.

Acceptance: preserve the exact Sanders Dash & Seal law and laws 1–9; explicitly record all owner platforms and past/present/future builds in governing sources, contributor instructions, and the application resource catalog; synchronize source snapshots and hashes; introduce no blanket application execution, startup, shutdown, or extra approval gate. Record source incorporation separately from live adoption and from modifications to other platforms.

Implementation: added an owner-wide directive document, MASTER/GOVERNANCE applicability statements, standing AGENTS instructions, and structured catalog applicability. This increment changes this repository branch only; other repositories and live deployments are not asserted updated.


## Binary founder portrait packaging repair — October 24, 2026

Acceptance: retain the approved PNG unchanged at web/sds-founder.png, represent binary assets in backend/platform-source.json as validated base64 with SHA-256, restore exact bytes in the backend container, reject malformed or altered snapshots, and preserve existing UTF-8 entries and booking flows. Remove the duplicate legacy web/sds-founder-1.png so the forensic duplicate-content audit does not fail. The production deployment and integrations require independent live verification.


## Owner amendment: Humanitarian Core Law 11 — October 24, 2026

Owner-directed authoritative wording:

> Sanders Dash & Seal shall always actually use Oracle Always Free resources in its real operations, not merely catalog or document them.

Owner-wide wording:

> Every platform owned by Roosevelt Sanders shall always actually use Oracle Always Free resources in its real operations, not merely catalog or document them.

Acceptance criteria: retain Humanitarian Laws 1–10 verbatim, add Law 11 to MASTER §3 and GOVERNANCE, carry it to past/present/future Sanders platforms via standing engineering instructions, and incorporate it into the application's Oracle resource catalog and actual runtime resource-use evidence. The system must use Oracle Always Free services for genuine business and operational workloads, not treat documentation, discovery or a Terraform plan as proof of use. Successful real Oracle Monitoring metric submission or verified private backup upload/restore may prove use of their respective services when observed. No simulated API responses may establish live resource usage. Other integrations remain unverified until live evidence exists. Do not insert an assistant-imposed blanket startup gate or claim other repositories/instances have been updated by this repository commit.

Implementation status: source and operational-evidence code are tracked separately from Oracle deployment. GitHub checks validate source behavior, not live Oracle execution. Current stack update has failed in GitHub Actions and no complete production adoption is claimed.


## Zone Watch — ICANN CZDS brand protection and global DNS check — November 21, 2026

**Source:** Owner instruction, November 21, 2026: incorporate the owner's ICANN CZDS zone-file access (all requested zones approved, including com, requested 23 April 2026) for brand protection through the watchdog and Sentinel platforms, and for whatever the platforms need to function globally. Controlling requirements: October 11 MASTER §3 (Humanitarian Core Laws 10 and 11 — Oracle Always Free only, actually used in real operations) and §§15 and 20 (Global PBD Sentinel; role separation — Zone Watch feeds the watchdog and Sentinel platforms and does not merge with them).

**Acceptance criteria:** Stream approved TLD zone files from CZDS with credentials from the environment only; never load a whole zone file into memory and never store a whole zone file on disk; match only the Sanders brands and the 35 shared platform hostnames plus the 10 Sanders Dash & Seal site names; store only matches in a small SQLite database; flag names not seen before as new registrations, separately from known names; emit one JSON event per match with no invented wire protocol; verify every platform hostname resolves through public DNS (Google DNS-over-HTTPS), never the local resolver; pair every new executable source file with its `.pbd.json` hash manifest (signatures stay UNSIGNED_SOURCE_MANIFEST, no signatures fabricated); add no tests and no verification or approval gate.

**Implementation:** New service `core_platform/zone_watch/` — `downloader.py` (streaming CZDS download over HTTPS with basic auth from CZDS_USERNAME/CZDS_PASSWORD, TLDs from CZDS_TLDS defaulting to com,app,global, transparent gzip handling), `filter.py` (brand and hostname matching, SQLite match store), `global_dns.py` (public DNS-over-HTTPS check of all 45 hostnames), `feed.py` (JSONL events file plus importable `publish_event`), `run.py` (daily entry point writing matches, events and a summary JSON), `__init__.py`, and `README.md`. No watchdog or Sentinel module in this repository exposes an event intake, so nothing is wired into one; the file-based feed and the importable function are the feed. The daily workflow `.github/workflows/zone-watch-daily.yml` is written but deliberately not pushed with this change (the GitHub App has no Workflows permission); it is placed through the GitHub web UI. Owner steps still needed: CZDS credentials in the Secure Vault and as repository secrets, workflow placement via the web UI, and deployment of this code to the instance (a deploy run waits on the owner's Production-Authorization-Gate). Live operation is unverified until the first scheduled run produces a summary on the instance.

## The Judge — Python 3.9 annotation compatibility (November 21, 2026)

**Source:** Owner instruction, November 21, 2026: "We've got to code the judge." Defect found in the TwoStep deploy runs #21 (attempt 2) and #22: the Judge service failed to start on the Oracle instance, `/tmp/judge-startup.log` showing `TypeError: unsupported operand type(s) for |: 'type' and 'type'` at `the_judge.py` line 111, `def __init__(self, state_dir: str | Path, ...)`. Root cause: the instance runs `/usr/bin/python3` (Oracle Linux 9, Python 3.9), where the `X | Y` union syntax in an evaluated annotation is not supported (it needs Python 3.10+). The `str | Path` annotation on that one line was the only `X | Y` annotation in the TwoStep code.

**Acceptance criteria:** The Judge starts on the instance's Python without changing what the annotation means and without changing the Judge's behavior; no other file changed for this fix.

**Implementation:** Added `from __future__ import annotations` at the top of `sanders-twostep/the_judge.py` (after the module docstring), so annotations are stored unevaluated and the `str | Path` annotation is never evaluated at runtime. Paired with the updated `.pbd.json` hash for the file. Live operation is unverified until the next TwoStep deploy run starts the Judge on port 9405.

## Central Stripe connection — one shared connection every platform inherits (November 22, 2026)

**Source:** Owner instruction, November 21, 2026: every platform must be connected to his Stripe account (acct_1UQTehAgIE87JukG) and must inherit the connection — past, present, and future builds by design. Audit `~/workspace/repo-audit-20261121/STRIPE_INHERITANCE_AUDIT.md` (2026-11-21): central pieces existed (webhook routing in `wsgi.py`, `stripe_live_gate` in `platform_services.py`, the injectable client in `stripe_checkout.py`, Bozly wiring, the payments modules) but there was no single shared Stripe connection module — each module read the same env vars separately, so the connection was shared by convention only.

**Acceptance criteria:** One central module in the core holds the client + keys + livemode gate + webhook verification, reading the same env vars (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_LIVEMODE`, `STRIPE_LIVE_VERIFIED`); every payments module imports it instead of reading the environment directly; future builds inherit it by importing the core module. No livemode behavior change: test mode stays the default until named live approvals exist. Bozly's wiring keeps working exactly as it does now (Bozly went live 2026-11-22 00:28 MST, configured, one route "main", entity sanders_legal_helpers_llc, jurisdiction ALL_50_STATES_GLOBAL).

**Implementation:** New module `core_platform/stripe_connection.py` — `StripeConnection.from_env()` (or `get_connection()`), canonical truthiness `env_truthy` (P3, 2026-11-13: `"1"`/`"true"`/`"yes"`), `live_allowed` gate (live requested AND verifier-approved), `mode` (`"test"`/`"live"`/`"unknown"`), lazily-imported `stripe_client`, `checkout()` factory returning a `StripeCheckout` bound to the connection, `verify_webhook()` delegating to `stripe_payments.verify_stripe_webhook`, `construct_webhook_event()` as the one place the SDK builds a webhook event, and presence-only `status()`. Migrated: `core_platform/stripe_checkout.py` (key, live-verified flag, livemode check, and `checkout_status()` now come from the connection; public API and error behavior unchanged), `core_platform/platform_services.py` (`StripeLink.from_env` maps the connection's fields; `stripe_live_gate` unchanged), `core_platform/stream_api.py` (webhook event construction via `construct_webhook_event`; secret and livemode flags still arrive by injection from `wsgi.py`, now sourced from the connection), `wsgi.py` (webhook secret and livemode flags from the connection; the fail-loudly missing-secret error and the local `_env_truthy` helper are replaced by the central reading). Two deliberate alignments, both toward the repo's own P3 canonical truthiness: `stripe_checkout.verify_then_record` and `checkout_status()` previously read `STRIPE_LIVEMODE`/`STRIPE_LIVE_VERIFIED` with a strict `"true"`/`"1"` comparison, while `wsgi.py`, `platform_services.py` and `deploy/deployment.py` already used canonical truthiness — all readers now agree (`STRIPE_LIVEMODE=1` means live everywhere). Deliberately unchanged: `core_platform/bozly_wiring.py` (Bozly's own `BOZLY_*` variables and live path untouched), `core_platform/global_payments.py` and `core_platform/appointment_payments.py` (pure/injection-based, they read no Stripe env vars; their callers pass the central connection's flags and client), `core_platform/stripe_payments.py` (the ledger/verification layer the connection delegates to), `deploy/` (secrets publishing, not connection readers), and `core_platform/ai_platform_links.py` (presence-only health check). No tests added, run, or restored. Live operation is unverified until one real test-mode verified event is recorded end to end; live only after named approvals and a verifier.

## Secretary — convert to a systemd user service (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: the corporate Secretary has the same corporate-headquarters scope as Bozly — it serves all four LLCs and all platforms. Defect found by the diagnostic workflow run #1 (commit 553f5e5, November 21, 2026): `sanders-corporations-secretary.service` fails 203/EXEC, "Failed to locate executable /home/opc/.local/share/sanders-corporations-secretary/venv/bin/uvicorn: Permission denied", restart counter in the thousands, while `uvicorn --version` works interactively as opc. Root cause (leading explanation, not proven): the Secretary is a systemd *system* service running under SELinux system rules (Enforcing, targeted) that cannot execute home-data-labelled files, while the interactive shell runs unconfined. TwoStep and Judge work because they are systemd *user* services.

**Acceptance criteria:** The Secretary starts and answers on loopback port 8791 using the same pattern as the working TwoStep/Judge services; the old failing system service is retired, not left restarting; the venv, token, database path, probe port (8792), and loopback check are unchanged.

**Implementation:** `sanders-corporations-secretary/deploy/oracle/deploy_secretary.sh` now writes the unit to `$HOME/.config/systemd/user/` (no sudo), drops the `User=`/`Group=` lines (invalid in a user unit), uses `WantedBy=default.target`, and controls it with `systemctl --user` (daemon-reload, enable --now, restart, status, journal) — mirroring `sanders-twostep/deploy/oracle/deploy_twostep.sh`. Before writing the new unit it retires the old system unit (`systemctl disable --now`, remove `/etc/systemd/system/sanders-corporations-secretary.service`, daemon-reload) so it stops restarting. `loginctl enable-linger opc` is kept (with the TwoStep fallback) so the user manager survives logout. Paired with the updated `.pbd.json` hash for the script. Pushed November 22, 2026 (commit c58286c) on the owner's go-ahead; deployed and live the same night — push-triggered run #24 succeeded in 36s and manual run #25 succeeded in 24s, loopback HTTP 200 on port 8791.

## Platform registry: Secretary, Judge, Police Men (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: the Secretary is a platform too, and the Judge and the Police Men too. The main repo's platform registry (`core_platform/ai_platform_links.json`) listed nine platforms and none of the three.

**Acceptance criteria:** Each of the three is listed in the registry with the same fields as the existing entries, using only verified facts (live endpoints, real module paths, real env vars); the existing nine entries are unchanged.

**Implementation:** Appended three entries to `core_platform/ai_platform_links.json` (9 → 12): `secretary` — "Sanders Corporations Secretary", corporate-headquarters platform serving all four LLCs and all platforms, endpoint http://127.0.0.1:8791, env vars SCS_API_TOKEN and SCS_DB_PATH, local modules `sanders-corporations-secretary/app/*.py`, live since November 22, 2026; `judge` — "The Judge", RTSA Constitutional Adjudicator, endpoint http://127.0.0.1:9405, local module `sanders-twostep/the_judge.py`, deployed with TwoStep, live since November 21, 2026; `police_men` — "The Police Men", S & G Security Inc. sovereign RTSA status dashboard, endpoint https://sanderslegalhelpersllc.com/rtsa/status, local files `rtsa_police_men/index.html` and `rtsa_police_men/status.json`. Paired with the updated `.pbd.json` hash for the registry. TwoStep was added separately right after, at the owner's direction (see the next section).

## Platinum Blue Diamond Standard: Bozly containment assets at expected paths (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: the Platinum Blue Diamond Standard check matters because that IS the Fortune 500 standard. Investigation of run #180 (commit c58286c): the workflow's only job "Validate Sovereign Laws" failed in 13s at step "Execute Asset Integration Scan" with `Error: Required infrastructure asset missing: infrastructure/resource-manager/bozly_apparmor.profile` (exit code 1). The check (`verify_assets.py`, "Platinum Blue Diamond Standard | Level 35+ Hyper-State Environment Gate") requires two files at `infrastructure/resource-manager/`: `bozly_apparmor.profile` and `bozly_watchdog_trigger.py`. Both existed in the repo only at mangled duplicated paths (`infrastructure/infrastructure/resource-manager/bozly_apparmor.profile` and `infrastructure/infrastructure/resource-manager/infrastructure/resource-manager/bozly_watchdog_trigger.py`). The failure predates c58286c (same paths 404 on parent 98bda1e) and is unrelated to the Secretary change. The repo's own code already expects the clean paths: `minotaur_sentinel.py` runs the trigger at `infrastructure/resource-manager/bozly_watchdog_trigger.py`, and the trigger reads the profile from `infrastructure/resource-manager/bozly_apparmor.profile`.

**Acceptance criteria:** Both files exist at the paths `verify_assets.py` expects, byte-identical to the copies already in the repo; nothing is deleted and no script is changed.

**Implementation:** Copied both files to `infrastructure/resource-manager/` (hashes verified identical to the sources: profile e0e05e1c…, trigger 994a0fa8…), each paired with a new `.pbd.json` manifest mirroring its nested copy's manifest with only the artifact path changed. The nested copies are left in place. Live operation of the check is unverified until the next Platinum Blue Diamond Standard run on main.

## Platform registry: TwoStep (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: "TwoStep too." Follow-up to the Secretary/Judge/Police Men registry addition (commit 145e883).

**Acceptance criteria:** TwoStep is listed in the registry with the same fields as the existing entries, using only verified facts; the existing twelve entries are unchanged.

**Implementation:** Appended the `twostep` entry to `core_platform/ai_platform_links.json` (12 → 13): "TwoStep", The Sanders TwoStep v2 — Sanders Legal Helpers LLC (CO SOS ID 20258029131), DBA Sanders Dash & Seal, endpoint http://127.0.0.1:9400, local module `sanders-twostep/sanders_twostep_v2.py`, deployed with the Judge, live since November 21, 2026. Paired with the updated `.pbd.json` hash for the registry.

## Serve the Sanders Dash & Seal app at the public root on two domains (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: "DashandSeal deserves to be running prominent on his domain name, let's make it a reality" and "All specs fully defined and make ready natively be hosting two domain names cohesively and fully Defined with everything in tact fully operational end to end." The two domains are sandersdashandseal.com and sanderslegalhelpersllc.com (the two original domains; confirmed by the owner November 22, 2026, ~03:39 MST: "No you're right"). The Police Men dashboard is not for public viewing (owner, November 22, 2026) and its security details must not be public, so the dashboard comes off the public root on every domain. Both domains are hosted natively and cohesively by the same Dash & Seal app (gunicorn on port 8000, behind the one nginx server block), which already routes each host to its own home page — this change only stops nginx from masking the app with the static dashboard.

**Acceptance criteria:** On every one of the ten site names the public root "/" is served by the Sanders Dash & Seal app on port 8000, never by the static Police Men dashboard; no deploy copies the dashboard to the public web root again; the two domains in scope behave exactly as defined below; /healthz, /legal-aid/, /rtsa/status, the Stripe webhook paths, and the app's API routes keep working on both domains.

**Per-domain definition:**
- sandersdashandseal.com (canonical host, `CANONICAL_HOST` in `deploy/deployment.py`): "/" serves `web/index.html` — the Secure Notarization Portal (header "Sanders Dash & Seal", tagline "From the Road to Remote, We Seal the Deal.", intake form for Mobile Notary / Remote Online Notarization / Document Support with service, state, city, date/time, and consent, "Your Timeline" feed, "What Happens Next" — quote, then Stripe checkout). Its assets `/assets/booking.css` and `/assets/booking.js` are served by the app from `web/` (new `_api_route` branch in `deploy/deployment.py`; without it the canonical host 308-redirects those asset paths and the portal loads with no styling and no working form). `/api/session`, `/api/appointments`, and `/api/operator/appointments` are delegated to the customer app. Every other non-API path on this host 308-redirects to `https://sandersdashandseal.com/` (unchanged existing behavior — customer static pages, including `/appointments`, `/auth/login`, and `/landing`, stay alias-only).
- sanderslegalhelpersllc.com (alias host, `ALIAS_HOSTS`): "/" serves the customer app's `web/jade-landing.html` — the Imperial Jade landing page (hero "From the Road to Remote, We Seal the Deal.", founder portrait, service packages with published starting prices, Wall of Valor, appointment and sign-in calls to action). Its assets (`/assets/jade-landing.css`, `/assets/jade-landing.js`, `/assets/sds-founder.png`, `/assets/wall-of-valor-primary.jpg`, `/assets/wall-of-valor-secondary.jpg`) and its pages (`/appointments`, `/operator`, `/auth/login`, `/auth/register`, `/auth/setup`, `/auth/logout`, `/landing`) are served by the customer app, unchanged.
- The other eight site names (`www.sandersdashandseal.com`, `www.sanderslegalhelpersllc.com`, `sanderssixshield.com`, `www.sanderssixshield.com`, `sanderssecurestack.com`, `www.sanderssecurestack.com`, `sandersemergencyglobalcommunication.com`, `www.sandersemergencyglobalcommunication.com`) are alias hosts and serve the same Imperial Jade landing at "/" as sanderslegalhelpersllc.com; their behavior is unchanged by this change except that the dashboard no longer masks it.
- The two domains serve DIFFERENT home pages by the app's own design (portal on the canonical host, landing on alias hosts). They are not unified by this change; unifying them is the owner's call and is not decided here.
- Unchanged on both domains: `/healthz` and `/readyz` (app diagnostics, 200 JSON); `/legal-aid/` (Money Factory on 8668; `/legal-aid/health` ACTIVE); `/rtsa/status` (nginx alias to `/var/www/rtsa/status.json` — still publicly reachable and still exposing the same security details; closing it is part of the owner's pending dashboard decision, not part of this change); `/stripe/webhook` and `/v1/payments/stripe/webhook` (both go to the verified webhook app at the `wsgi.py` entrypoint, host-independent, reached through the snippet's `location /` proxy); every `/api/` route (`_api_route` handles them before the host fall-through, so they behave identically on both domains).

**Implementation:** Four files, all prepared, none pushed. (1) `money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal.conf` now carries `location /healthz` and `location /` (both proxying to 127.0.0.1:8000 with the same headers as the existing `/legal-aid/` location) ahead of the unchanged `/legal-aid/` → 8668 location; `/rtsa/status` is not in the file because `deploy_all` appends it if missing. New paired `.pbd.json` manifest (nested, 2-space indent, no trailing newline), hash verified against the file bytes. The added locations match the live instance snippet byte-for-byte (as restored by `.github/workflows/restore-nginx-443-20261121.yml`). (2) `deploy/deployment.py`: new `_api_route` branch serving `/assets/booking.css` and `/assets/booking.js` from `web/` via the existing `_serve_web_file` helper, for non-alias hosts only (alias hosts return None so they keep serving these files from the customer app with its own headers); missing files answer 404. Paired with the updated `.pbd.json` hash. (3) `.github/workflows/deploy_all_simultaneous.yml`: step 4b no longer copies `rtsa_police_men/index.html` to `/usr/share/nginx/html/index.html` (it still copies `status.json` to `/var/www/rtsa/status.json` for `/rtsa/status`); the port-80 server template (written only when the cert file is absent) drops `root`, `index`, and the `location = / { try_files /index.html =404; }` block, and its `server_name` gains the two legalhelpers names so it matches the live 443 block's ten names. The `/rtsa/status` append, the snippet copy, the health check, and the Production-Authorization-Gate are unchanged. (4) New one-time workflow `.github/workflows/serve-app-root-20261122.yml` (workflow_dispatch, modeled on the restore workflow): backs up the nginx config, moves the dashboard `index.html` out of the web root into the backup directory (recoverable), removes every `location = / { try_files /index.html =404; }` block from `/etc/nginx/conf.d/money_factory_legal_server.conf` (both server blocks if present; the `root`/`index` lines are left in place so certbot's assumptions are preserved), runs `nginx -t` with restore-on-failure, reloads nginx, then verifies per domain — "/" returns 200 and contains the portal markers on the canonical host and the Imperial Jade markers on legalhelpers, with no "POLICE MEN" text on either; `/assets/booking.css` and `/assets/booking.js` return 200 on the canonical host; `/assets/jade-landing.css` returns 200 on legalhelpers; `/healthz`, `/legal-aid/health`, and `/rtsa/status` return 200 on both; both Stripe webhook paths answer (not 502). The live 443 block is changed ONLY by this repair workflow: `deploy_all` writes the server conf only when the cert file is absent, and the cert exists, so no deploy can update the live 443 block. Order of operations: push the repo change, run `deploy_all` (owner approves at the gate) so the new `deployment.py` and snippet go live, then run the repair workflow. Live operation is unverified until the repair workflow reports ALL_CHECKS_PASSED.

**Open decisions (owner's):** the dashboard's new home and his own access (password-protected vs taken down entirely); whether the two domains should serve the same home page instead of the portal/landing split; whether `/rtsa/status` stays public. The prepared change decides none of these.

## Wire production bindings and repair the application process (November 22, 2026)

**Source:** Owner instruction, November 22, 2026, 09:41–09:48 MST: "Lets repair everything is everything in place to run on the 2 domain names like we agreed, full suite application process form everything not short sit or broken websites correct", "Yes, build it", "Immediately", "Pricing structure everything." Pre-flight verification against main @ 1077bf3 (2026-11-22 ~09:46 MST) found the full application process NOT in place: the app boots diagnostic-only, so every API route answers 503 `appointments_unavailable`, and nine further mismatches break the process even with bindings.

**Acceptance criteria:** The app boots with real production bindings when the deployment names the factory; a customer can sign in, request an appointment, and track it on both domains (sandersdashandseal.com and sanderslegalhelpersllc.com); an operator can reach the operator UI, approve an itemized quote, and the customer can check out through Stripe (test mode first); a deploy restarts the app; the deploy health check proves the app (not just nginx) is live.

**Implementation:**

**1. Production bindings factory.** New module `deploy/production_bindings.py` — `create_production_bindings()` builds a `RuntimeBindings` from the repo's own modules, the same modules the test fixture wires by hand (`worker/test/python_fixture.py`) but against the production data directory with a real session auth: `CaseRegistry` + `AppointmentStore` + `PaymentLedger` share ONE SQLite file (`data/ledger.db` — the same file the webhook ledger in `wsgi.py` uses, so a checkout registered here is visible to the webhook path that settles it); `GlassBoxAudit` on `data/audit.db`; `SessionAuth` on `data/accounts.db`; the Stripe client is a real `stripe.StripeClient` from the central connection (`core_platform/stripe_connection.py`); the release verifier is True once these bindings exist, so `/readyz` answers 200. Pipeline/stream bindings stay None, so those routes keep their honest 503. `wsgi.py` loads the factory through the existing `deployment.load_application` factory-reference mechanism when `SANDERS_RUNTIME_FACTORY` is set (e.g. `deploy.production_bindings:create_production_bindings`); when the variable is unset the boundary keeps its diagnostic-only startup, and when the factory fails the app still starts diagnostic-only with a stderr note instead of refusing to boot — the factory is never a deployment blocker (owner instruction, October 22, 2026). All three entry points (`wsgi.py`, `passenger_wsgi.py`, `backend/wsgi.py`) call `create_native_application`, so the wiring reaches each of them. No new boot mechanism was invented.

**2. Jurisdiction: CO / WI / AZ.** The form offered free text (its own example was Wisconsin) while `core_platform/appointments.py` accepted only `('CO', 'WY')`. WY appears nowhere else in the owner's context; WI is the form's example, his location, and a state he named for the business; CO and AZ are the states he named for the business. The evidence-based set is Colorado, Wisconsin, Arizona. `appointments.py` now accepts `('CO', 'WI', 'AZ')`; `web/index.html` offers those three as a dropdown instead of free text (booking.js reads the select value unchanged). The owner can expand the set by naming a state — the dropdown is the one place to add it. The RON compliance gate (`core_platform/global_compliance.py` `APPROVED_RON_JURISDICTIONS`) is deliberately unchanged and still empty: RON appointments can be requested, but `/api/compliance/ron` denies every jurisdiction until the owner approves jurisdictions with legal counsel / verifier confirmation.

**3. Service spellings: one canonical set.** The form sends `MOBILE_NOTARY` / `RON` / `AUTHORIZED_DOCUMENT_SERVICE`; `appointments.py` accepted only `MOBILE_NOTARY` / `AUTHORIZED_DOCUMENT`; `core_platform/cases.py` `VALID_SERVICES` was `(MOBILE_NOTARY, E_NOTARY, RON, AUTHORIZATION)`. Only `MOBILE_NOTARY` survived all three layers. Both store layers now accept exactly the customer-facing set `(MOBILE_NOTARY, RON, AUTHORIZED_DOCUMENT_SERVICE)`. `E_NOTARY` and `AUTHORIZATION` are no longer accepted as services; no code in the repo sends them through the appointment flow.

**4. Quote item keys.** `web/operator.js` builds `'Notarial Acts'`, `'Travel'`, `'Document Support'`; `core_platform/appointment_payments.py` required exactly `{'Notarial acts', 'Travel', 'Document support'}` — every quote approval raised `PaymentDenied` → 409. The validator now requires the operator UI keys. The Stripe line items in `checkout()` are built from the same keys, so the customer sees the same item names the operator entered.

**5. Sign-in.** New module `core_platform/session_auth.py` — the auth backend the repo did not have: SQLite accounts (username validated against the same `IDENT` pattern the appointment store uses; scrypt password hashes via the standard library; roles `CUSTOMER` / `OPERATOR`) and sessions (random token, 7-day expiry, `HttpOnly` + `SameSite=Lax` + `Secure` cookie). `authenticate(env)` reads the `session` cookie; `operator_verifier(identity)` is True only for OPERATOR accounts; `auth_app` serves POST `/auth/login` / `/auth/register` / `/auth/setup` / `/auth/logout` with the `{ok, role}` / `{error}` shape `web/auth.js` already expects, including the `try_again_later` lockout (5 failures → 15 minutes). No seeded accounts and no invented credentials: customers register; the single operator is created once through `/auth/setup` with the owner-held setup token `SDS_OWNER_SETUP_TOKEN` (unset → setup unavailable; once an operator exists → setup unavailable). **Owner step:** set `SDS_OWNER_SETUP_TOKEN` in `/etc/sanders-dash-seal/runtime.env` (any value only the owner knows), then use it once at `/auth/setup` to create the operator account — nobody can approve quotes until then. `deploy/deployment.py` now delegates the customer static pages and `/auth/*` routes to the customer app on the canonical host too (previously only the API paths were delegated, so `/auth/login`, `/auth/login.html` and `/operator.html` 308-redirected to `/` and a POST there 405d; the alias host served them). `app/customer_app.py` ASSETS gains the `.html` spellings the pages link to (`/auth/login.html`, `/auth/register.html`, `/auth/setup.html`, `/auth/logout.html`, `/operator.html`, `/index.html`, `/resources.html` — `web/resources.html` exists). `web/auth.js` now redirects a signed-in customer to `/` instead of `/index.html` (which 308d on the canonical host); the operator redirect to `/operator.html` and the logout redirect to `/auth/login.html` are unchanged and now served. Brand links in `web/index.html`, `web/auth.html` and `web/operator.html` now point to `/` instead of `/index.html` for the same reason; the alternative link in `auth.html` likewise.

**6. Operator UI.** `/operator.html` is now served on both domains (ASSETS entry + canonical delegation above), so the operator can open the dashboard, see the queue (`GET /api/operator/appointments`, operator-authorized), approve itemized quotes, and open the provider workspace. New `PROVIDER_ROUTE` (`GET /api/operator/appointments/<id>/provider`) returns `{"requests": []}` — no provider backend exists yet, and the operator UI already renders an empty list as "No remote connection requests initialized yet." Previously the route 404d.

**7. Gunicorn restart (the 421 fix).** `deploy/sanders-dash-seal.service` did not exist anywhere in the repository — `deploy/install-simultaneous.sh` step 7 installs it from `deploy/` but the file was absent, and `deploy_all`'s restart loop only restarts the service if a unit file already exists on the instance. Deploys therefore landed code without restarting the app, which is how the running copy went stale (the overnight 421 `host_denied` regression on the three new domains: the running `deployment.py` did not match main). New unit `deploy/sanders-dash-seal.service`: runs as the `sanders` runtime user (uid 10001, created by the installer, the uid `wsgi.py` hands the data directory to), `WorkingDirectory=/opt/Sanders_Dash_Seal` — the checkout `deploy_all` maintains — `ExecStart` the venv gunicorn with `deploy/gunicorn.conf.py` and `wsgi:application`, `ExecReload` SIGHUP, `EnvironmentFile` for `/etc/sanders-dash-seal/environment` then `/etc/sanders-dash-seal/runtime.env` (runtime.env last, so the Vault-written values win), and `Environment=SANDERS_RUNTIME_FACTORY=deploy.production_bindings:create_production_bindings`. The unit pins the app to the checkout deploys update; the previously-running unit's working directory was never in the repo, so the first deploy after this lands must install this unit — the prepared workflow change below does that.

**8. Deploy health check (PREPARED, NOT PUSHED).** Workflow file `.github/workflows/deploy_all_simultaneous.yml` is changed in the working clone but deliberately NOT pushed (the GitHub App has no Workflows permission; workflow files go through the web UI). The prepared change: after the restart loop, install `deploy/sanders-dash-seal.service` to `/etc/systemd/system/`, `daemon-reload`, `enable --now`, `restart`; and extend the health check loop to also require `GET http://127.0.0.1:8000/healthz` with `Host: sandersdashandseal.com`, `GET /` on both domains through nginx, and an unauthenticated `GET /api/session` on the canonical host expecting 401 (401 proves production bindings are live; 503 proves diagnostic-only). The existing `/legal-aid/health` + `/rtsa/status` checks are unchanged.

**9. Pricing structure.** Source of truth for packages: the landing's published starting prices (`web/jade-landing.html`), unchanged — Notary Service Packages From $150; Document Preparation Support From $250; Business Formation Support From $499; Contracts & Agreements From $500; Enterprise & Government From $5,000; High-Value Projects $20,000+. The portal's service select now shows the published starting price for its service (`Mobile Notary — from $150`, `Remote Online Notarization (RON) — from $150`, `Document Support — from $250`), so the two pages map services to prices consistently. The quote flow's price basis is what exists in code: operator-entered itemized dollar amounts (`web/operator.js` — the operator sets Notarial Acts / Travel / Document Support in dollars, converted to cents), not a price table; no per-service rate table exists anywhere in the repo and none was invented. Two alignments: `approve_quote` now requires the total to be at least 100 cents ($1.00), matching the minimum `checkout_parameters` enforces — previously a quote under $1.00 could be approved and then fail at checkout; and the landing copy now reads "serving Colorado, Wisconsin, and Arizona" to match the jurisdiction set. **Owner-supplied values still needed (flagged, no fake numbers):** whether RON shares the Notary Service Packages starting price of $150 (the landing does not name RON separately — assumed yes for the select label, owner to confirm); any fixed per-service rates, if the owner wants quotes priced from a table instead of operator-entered amounts; and the operator account (see item 5).

**Further defects found while building (all fixed in this change):** (a) `AppointmentStore` had no public `connect()` method, but `AppointmentPayments` calls `appointments.connect()` — every quote approval and checkout raised `AttributeError`; added `connect()` delegating to `_connect()`. (b) `PaymentLedger` exposed only `self_path`, but `AppointmentPayments` reads `ledger.path` and requires it to resolve to the same file as the appointment store — construction raised `AttributeError`; added `self.path = self.self_path`. (c) `PaymentLedger.register_checkout` ignored the `connection` kwarg `checkout()` passes and opened a second connection to write — inside `checkout()`'s `BEGIN IMMEDIATE` block that write blocked on the caller's lock until the busy timeout, so every first checkout failed; it now uses the passed connection without committing (mirroring `fulfill_checkout`'s `db` parameter in the same module) and opens its own only when none is passed. `status()` takes the same optional connection and `checkout()` passes it. (d) `app/customer_app.py` called `payments.quote_for_case_id(identity)`, a method `AppointmentPayments` does not have — the appointment-details GET 503d; it now calls `payments.quote(case_id, identity)`. The details route itself was also unreachable: the router's 404 check only recognised the `/checkout` route shape, so `GET /api/appointments/<id>` — the route `web/booking.js` uses for the quote/payment details panel — 404d; new `CASE_DETAIL_ROUTE` recognises it (GET only) and the handler uses it for the case id. (e) POST Origin checks compared against the canonical origin only, so every POST from an alias host (sign-in, appointment request, quote, checkout) answered 403 `origin_denied`; `create_customer_app` and `SessionAuth` now accept an `allowed_origins` set (`deploy/deployment.py` `SITE_ORIGINS` — canonical plus all nine alias origins), defaulting to the site origin alone. (f) The Stripe client: `StripeConnection.stripe_client` returns the `stripe` module, which has no `.v1` namespace in stripe 15.6.0 (verified against the pinned wheel: `.v1` exists only on `StripeClient` instances) — `AppointmentPayments.checkout` calls `client.v1.checkout.sessions.create`, so the module client would 409 every checkout; the factory builds a real `stripe.StripeClient(secret_key)`, and with no usable key (or a live key without the verifier gate) passes an adapter whose `.v1` raises `PaymentDenied`, keeping checkout honestly 409 while the rest of the process works. Stripe stays test-mode-first: `expected_livemode` is True only when the live gate (`STRIPE_LIVEMODE` + `STRIPE_LIVE_VERIFIED`) allows it and the key is a live key.

**Live operation is unverified until the deploy runs:** the push triggers a `deploy_all` run that waits on the owner's Production-Authorization-Gate; after approval, the prepared workflow change must be pushed via the web UI and the serve-app-root repair workflow dispatched, then both domains verified (sign-in, appointment request, quote, checkout in test mode).

## Stop the stale non-systemd gunicorn before the app unit binds (November 22, 2026)

**Source:** Owner direction, November 22, 2026: fix everything immediately in order of importance. Failure: `deploy_all` run #101 (https://github.com/DashandSeal/Sanders_Dash_Seal/actions/runs/45050232584, head `bc36a04`) failed in 27s; `verify-legal-engine` passed. The deploy job's diagnostics showed the app on port 8000 answering `/healthz` 200 with `process_alive: true` while `sanders-dash-seal.service` was `activating (auto-restart) (Result: exit-code)`, `Main process exited, code=exited, status=1/FAILURE`; unauthenticated `GET /api/session` answered 503 where the deploy health check requires 401.

**Root cause (established from the workflow, the unit, and the run evidence):** the live app is a bare nohup gunicorn started 2026-11-21 from `/tmp/sds-app` with `--bind 0.0.0.0:8000`, not systemd-managed, and no deploy step ever stopped it. It still holds port 8000, so the new systemd unit's gunicorn cannot bind `127.0.0.1:8000` (`deploy/gunicorn.conf.py`) and exits 1 in a restart loop — while the stale copy keeps answering health checks. The stale copy predates the production bindings, so `/api/session` answers 503 (diagnostic-only) instead of 401, which is what fails the deploy health check. The full job log could not be read (GitHub log download requires admin rights; unauthenticated API returns 403), so the exact gunicorn stderr line (bind error vs import error) is unconfirmed — but the port conflict alone is a proven blocking cause: with a live listener on 0.0.0.0:8000 the unit cannot bind 127.0.0.1:8000 under any circumstances.

**Acceptance criteria:** on the next approved deploy, the unit starts, binds 127.0.0.1:8000, serves the current checkout code, and the health check passes (`/healthz` 200, both home pages 200, unauthenticated `/api/session` 401).

**Implementation:** `deploy/sanders-dash-seal.service` gains one root-privileged `ExecStartPre` (`+` prefix — the stale process runs as `ocarun`, which `User=sanders` cannot signal) that stops any `gunicorn ... wsgi:application` process (TERM, 2s wait, then KILL) before `ExecStart`. The `'[n]'` bracket in the pkill pattern keeps pkill from matching its own shell command line (verified locally: the pattern matches the stale and unit command lines and matches neither the invoking shell nor an unrelated process). The unit's own previous gunicorn is already stopped by systemd before `ExecStartPre` on restart, so only the stale copy is targeted. `deploy_all` installs this unit on every deploy, so the fix rides the next approved deploy; no workflow file was changed. Paired `.pbd.json` hash updated (nested format preserved, only `payload_hash` changed; hash verified against file bytes).

**Open check for the next deploy (owner/instance step, not repo code):** `wsgi.py` raises `WebhookConfigurationError` at import when `STRIPE_WEBHOOK_SECRET` is unset, and the unit reads it only from `/etc/sanders-dash-seal/environment` (installer template, empty by default) and `/etc/sanders-dash-seal/runtime.env` (written by `deploy/refresh_provider_secrets.py` from the OCI Vault). Whether `runtime.env` currently holds a real secret on the instance could not be established from the repo or the run record. If it does not, the unit will still exit 1 at import after the port is freed. Before approving the next deploy, confirm on the instance that `/etc/sanders-dash-seal/runtime.env` contains a `STRIPE_WEBHOOK_SECRET` value (or run the Vault refresh flow); if it does not, populate it first. Live operation is unverified until that deploy runs and the health check passes.

## Permanent deploy repair — preflight, repo-owned nginx server config, and real failure diagnostics (November 23, 2026)

**Source:** Owner direction, November 23, 2026: "We've got to have a permanent repair" — fixing the deploy issues immediately is the top priority. Evidence base: the OCI Run Command diagnostics the owner authorized and completed sign-in for on the instance (2026-11-23, ~09:45–10:31 MST), which established from inside the instance: `/etc/sanders-dash-seal/runtime.env` **does not exist at all**; `sanders-dash-seal.service` is in an exit-1 auto-restart loop with nothing listening on port 8000 (gunicorn traceback in the arbiter/setup path); nginx is running but listening only on port 80 (Money Factory healthy on 127.0.0.1:8668) — **there is no port 443 listener**; and DNS for all five domains still points at 129.146.111.166 (verified via Google DNS-over-HTTPS the same morning). Outside checks the same morning progressed from 502 at 07:05 MST (nginx answering, app down) to connection resets at 09:54 MST (no 443 listener to answer).

**Root cause (two structural defects in the deploy itself, not in the app):** (1) No deploy step ever checked the app environment before restarting services. `wsgi.py` raises `WebhookConfigurationError` at import when `STRIPE_WEBHOOK_SECRET` is unset; the unit reads it only from `/etc/sanders-dash-seal/environment` (installer template, empty by default) and `/etc/sanders-dash-seal/runtime.env` (written by `deploy/refresh_provider_secrets.py` from the OCI Vault). With `runtime.env` absent, every deploy restarted the app into an exit-1 loop — runs #101, #102 and #103 all failed this way after the port-conflict fix (07554d7) had already landed and was verified working (`ExecStartPre` pkill exits 0/SUCCESS in every run). (2) The nginx server config was not repo-owned: `deploy_all` wrote the port-80 server block only when the TLS cert file was absent, and the port-443 block existed only as a one-time append made by `.github/workflows/restore-nginx-443-20261121.yml`. When the server file was later rewritten without that append, nginx came up with no 443 listener at all. Compounding both defects, the deploy's failure diagnostics printed only `systemctl status`, never the service journal, so the app's real startup error never appeared in any run log and the cause stayed unproven across three failed runs.

**Acceptance criteria:** a deploy whose instance environment is missing or malformed fails BEFORE any service is restarted, naming the missing file or key (never printing a secret value), leaving the running site untouched; every deploy installs the complete nginx server config (port 80 + port 443, all ten site names) from the repository, with a timestamped backup of the previous file; a failed health check prints the app service journal and the listener table into the run log, so the real startup error is always visible; and the workflow shrinks to checkout-sync plus one call into the repo, so future deploy fixes land in the repository without a web-UI workflow push.

**Implementation (committed locally on branch `permanent-deploy-repair`, NOT pushed):**

**1. `deploy/deploy_all.sh` (new).** The deploy script extracted from the workflow's inline SSH script — same `set -euo pipefail`, step order, comments and checks — so the deploy itself is now a repo file. Paired `.pbd.json` manifest created (nested format matching `deploy/deploy.sh.pbd.json`, trailing newline), hash verified against the file bytes.

**2. `.github/workflows/deploy_all_simultaneous.yml` thinned to a caller.** Name, triggers (push to main + workflow_dispatch), the `verify-legal-engine` job (byte-identical, verified against the previous file), and the deploy job's `environment: Production-Authorization-Gate` and `appleboy/ssh-action@v1.2.0` step are unchanged. The SSH script now only installs git if missing, clones or syncs the checkout at `/opt/Sanders_Dash_Seal` (including the existing `chown .git` self-heal from bc36a04 and `git reset --hard origin/main`), then runs `bash deploy/deploy_all.sh`. The script keeps its own bootstrap/clone steps, so it stays self-contained and idempotent when run on the instance directly. Paired `.pbd.json` manifest created in the flat format of the one existing workflow manifest (`.github/workflows/deploy_scs_to_oracle_always_free.yml.pbd.json`). **Owner step:** this file must still be pushed through the GitHub web UI (the GitHub App has no Workflows permission) — that is the last workflow push this repair needs; every later deploy change is a normal repo commit.

**3. Preflight (new step 2b in `deploy_all.sh`).** Placed after checkout and dependency installation, before any service restart: the deploy verifies `/etc/sanders-dash-seal/runtime.env` exists (`sudo test -f`) AND contains a `STRIPE_WEBHOOK_SECRET` entry whose value starts with `whsec_` (shape check only — the value is never printed). On failure it prints a clear error naming the missing file or key, the owner step that fixes it (the Vault refresh flow, `deploy/refresh_provider_secrets.py`), and exits 1 before any restart. This preserves the app's own fail-closed import check; it moves the discovery of a bad environment to before the restart instead of after it.

**4. Nginx server config as repo source of truth.** New `money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal_server.conf`: the port-80 block in the same shape as the deploy's former no-cert branch (all ten hostnames plus `129.146.111.166` and `_`, `server_tokens off`, the three security `add_header`s, the snippet include), and a port-443 `ssl` block for the same ten hostnames modeled on the known-good restore in `.github/workflows/restore-nginx-443-20261121.yml` (`ssl_certificate`/`ssl_certificate_key` at `/etc/letsencrypt/live/sandersdashandseal.com/`, the `options-ssl-nginx.conf` include, `ssl_dhparam`, `root /usr/share/nginx/html`, `index index.html`, the same headers with `always`, `location = /` with `try_files /index.html =404`, and the snippet include). `deploy_all.sh` step 4 now installs this file to `/etc/nginx/conf.d/money_factory_legal_server.conf` on EVERY run (timestamped backup of any previous file first), replacing the conditional no-cert-only write; step 5's existing `nginx -t` still runs before any service restart, so a bad config fails the deploy without touching the running nginx. The snippet source `money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal.conf` already carried `/healthz`, `/` and `/legal-aid/`; it now also carries `location = /rtsa/status` (alias `/var/www/rtsa/status.json`) in the file's existing style, so all four locations exist in source — the deploy's append-if-missing logic for `/rtsa/status` is retained unchanged. Paired `.pbd.json` manifests created/updated for both conf files (nested format matching the snippet's existing manifest, no trailing newline), hashes verified against the file bytes.

**5. Diagnostics (step 7 failure path in `deploy_all.sh`).** On health-check failure the diagnostics now also print `sudo journalctl -u sanders-dash-seal.service -n 60 --no-pager` and the listener table (`sudo ss -ltnp | grep -E ':(80|443|8000|8668)' || true`) before `exit 1`, so the real startup error and the bound-port picture land in the run log.

**Manifests:** every added/changed file above is paired with its `.pbd.json` (this file's manifest included); each `payload_hash` is the SHA-256 of the file's bytes, each manifest's existing JSON format and structure preserved, signatures left `UNSIGNED_SOURCE_MANIFEST` — none fabricated.

**Open items (owner/instance steps, not repo code):** `/etc/sanders-dash-seal/runtime.env` must be populated on the instance (Vault refresh flow or owner-created file with the real Stripe values) before the next deploy can pass the new preflight — the deploy will now stop safely until it is; the thinned workflow file must be pushed via the web UI (item 2). The deploy health check is unchanged and probes the app and nginx over loopback HTTP as before; it does not itself probe 443 — external HTTPS verification of the five domains remains the post-deploy check (the new listener diagnostics print the bound ports on any failure). Live operation is unverified until an approved deploy runs with `runtime.env` in place and the health check passes, followed by the external HTTPS check.

## Automatic recovery — watchdog health checks, restart hardening, and reboot return (November 23, 2026)

**Source:** Owner direction, November 23, 2026: "We've got to set up a way for everything to automatically reconnect if the connection is interrupted for any reason." This entry extends the permanent deploy repair recorded directly above (same day, same branch) with the self-healing layer that repair did not cover: the preflight and the repo-owned nginx config stop a deploy from taking the site down, but until this entry nothing brought a service back on its own if it crashed, wedged while alive, or the instance rebooted.

**Root cause (the recovery gaps this closes):** (1) The app unit carried `Restart=on-failure` with `StartLimitIntervalSec=60` / `StartLimitBurst=3` in `[Service]` — after a short burst of crashes systemd would park `sanders-dash-seal.service` in a failed state and stop trying, so a transient fault became a permanent outage until a human intervened. (2) No component health-checked the running services: a process that stayed alive but stopped answering (a wedged worker, a lost listener — the 2026-11-23 outage included nginx running with no port 443 listener at all) was never detected or restarted. (3) The Secretary, TwoStep, and Judge services are systemd `--user` services owned by `opc`; a user manager without linger stops at logout and does not start at boot, so a reboot could silently leave all three down.

**Acceptance criteria:** every platform service restarts itself when it crashes, with no systemd start-limit give-up; every service is health-checked on a timer against its real loopback health endpoint and restarted if it stops answering while alive — only after 2 consecutive failed checks, and at most one watchdog restart per service per 5 minutes, so a hard configuration error is never spun in a tight loop and its failure stays visible in the journal; nginx is additionally checked for listeners on BOTH port 80 and port 443; all services, including the `opc` `--user` services, return on their own after a reboot (enabled units plus linger); and every deploy installs and enables the whole layer from the repository.

**Implementation (committed locally on branch `permanent-deploy-repair`, NOT pushed):**

**1. `deploy/sds_watchdog.sh` (new).** A root-run bash watchdog (`set -u`; individual check failures never abort the run). It probes each service with `curl` (connect timeout 3s, max time 5s), keeps per-service failure counters and last-restart stamps in `/var/lib/sds-watchdog/` (falling back to `/run/sds-watchdog/`), and logs every failed check, restart, and recovery through `logger -t sds-watchdog` and stdout. A service is DOWN after 2 consecutive failed checks; a restart is then issued only if the service's last watchdog restart was at least 5 minutes ago (cooldown), and the failure counter resets on the restart. It exits 0 unless the watchdog itself is misconfigured (no `curl`, or no usable state directory). Per-service table, every entry established from the repository (not assumed):

| Service | Unit | Owner | Health check | Restart form |
|---|---|---|---|---|
| Sanders Dash & Seal app | `sanders-dash-seal.service` | system | HTTP 200 from `http://127.0.0.1:8000/healthz` | `systemctl restart` |
| Money Factory Legal Aid | `money-factory-legal.service` | system | HTTP 200 from `http://127.0.0.1:8668/health` | `systemctl restart` |
| Secretary | `sanders-corporations-secretary.service` | `opc` (`--user`) | HTTP 200 from `http://127.0.0.1:8791/api/health` (the real route: `@app.get("/api/health")` in `sanders-corporations-secretary/app/main.py`) | opc user manager (below) |
| TwoStep | `sanders-twostep.service` | `opc` (`--user`) | HTTP 200 from `http://127.0.0.1:9400/healthz` (route in `sanders-twostep/sanders_twostep_v2.py`) | opc user manager (below) |
| Judge | `sanders-judge.service` | `opc` (`--user`) | HTTP 200 from `http://127.0.0.1:9405/healthz` (route in `sanders-twostep/the_judge.py`) | opc user manager (below) |
| nginx | `nginx.service` | system | `ss -ltn` shows listeners on BOTH port 80 and port 443 (ports matched exactly, so 8000/8668 never count as 80) | `systemctl restart` |

The three `--user` units are owned by `opc`: their deploy scripts (`sanders-corporations-secretary/deploy/oracle/deploy_secretary.sh`, `sanders-twostep/deploy/oracle/deploy_twostep.sh`) install them under opc's `~/.config/systemd/user` and call `loginctl enable-linger opc`. The watchdog therefore restarts them through opc's user manager — primarily `systemctl --machine=opc@ --user restart`, falling back to `runuser -u opc` with `XDG_RUNTIME_DIR` set to opc's runtime directory; if `opc` does not exist or both forms fail, the failure is logged and that service is skipped for the round, never guessed at.

**2. `deploy/sds-watchdog.service` and `deploy/sds-watchdog.timer` (new).** The service is a `Type=oneshot`, `User=root` unit running the watchdog from `/usr/local/sbin/sds_watchdog.sh` — the installed location chosen for the script (installed fresh from the repo copy `deploy/sds_watchdog.sh` on every deploy, so it never depends on the checkout's state). The timer fires `OnBootSec=2min` and then `OnUnitActiveSec=2min`, with `Persistent=true` and `WantedBy=timers.target`, so checks run every 2 minutes and a check missed while the instance was off is caught up at boot.

**3. Unit hardening.** `deploy/sanders-dash-seal.service`: `StartLimitIntervalSec=0` moved into `[Unit]` (no start-rate give-up), `StartLimitBurst` removed from `[Service]`, `Restart=on-failure` → `Restart=always`, `RestartSec=5` → `RestartSec=10`; everything else — `EnvironmentFile` lines, the `ExecStartPre` stale-gunicorn pkill, `SANDERS_RUNTIME_FACTORY`, user/group, working directory — is byte-identical. `money_factory_legal_aid_v1_668/infra/oracle_linux_9/money-factory-legal.service`: the same hardening (`StartLimitIntervalSec=0` added in `[Unit]`, `RestartSec=3` → `RestartSec=10`; it already carried `Restart=always`); a paired `.pbd.json` manifest is created for it with this entry — it previously had none.

**4. `deploy/deploy_all.sh` step 5c (new).** Every deploy now installs the watchdog script to `/usr/local/sbin/sds_watchdog.sh` (mode 0755), installs `sds-watchdog.service` and `sds-watchdog.timer` into `/etc/systemd/system`, reloads systemd, and enables and starts the timer (guarded, so a timer failure never fails the deploy); it also runs `loginctl enable-linger opc` (guarded) so the opc user manager — and with it the Secretary, TwoStep, and Judge services — survives logouts and returns at boot. All existing steps, including the step 2b preflight, are unchanged.

**Manifests:** every added/changed file above is paired with its `.pbd.json` (this file's manifest included); each `payload_hash` is the SHA-256 of the file's bytes, each manifest's existing JSON format and structure preserved (nested format throughout; trailing newline in `deploy/`, none in the Money Factory infra directory or `docs/`), signatures left `UNSIGNED_SOURCE_MANIFEST` — none fabricated.

**Open items (honest gaps, not silently papered over):** the Secretary, TwoStep, and Judge units are not standalone files in this repository — they are generated by heredocs inside their own deploy scripts (`deploy_secretary.sh`, `deploy_twostep.sh`). Those generated units already carry `Restart=always`, but they do not set `StartLimitIntervalSec=0`, so a user-manager start limit could still park one after a crash burst; hardening them means editing those two deploy scripts, which this entry deliberately does not do — the watchdog covers the gap from outside by restarting any of the three that stops answering. The Secretary's `start.py` refers to port 8765 while its deployed unit binds 8791; the watchdog checks the deployed port (8791) and the app's real `/api/health` route — the 8765 reference is left for the Secretary's own deploy path to reconcile. The watchdog restarts a service whose health endpoint fails; it cannot repair the underlying cause (a missing secret, a bad config) — by design it rate-limits itself and leaves the evidence in the journal instead. Live operation is unverified until an approved deploy installs the watchdog on the instance and its timer has run there; nothing in this entry has been pushed or deployed.

## Deploy creates the app data directory (November 23, 2026)

**Source:** Live diagnosis, November 23, 2026. Restoring /etc/sanders-dash-seal/runtime.env let startup advance past the webhook-secret check, and the app still crash-looped: the journal traceback now ends in wsgi.py create_native_application() at data_dir.mkdir(parents=True, exist_ok=True) for <repo>/data, the app's ledger directory. Under systemd the whole gunicorn process runs as the sanders service user, which cannot create that directory inside the opc-owned checkout at /opt/Sanders_Dash_Seal; the ownership repair inside wsgi.py runs only after a successful mkdir and only helps a root-started process, so it never gets the chance.

**Acceptance criteria:** every deploy creates /opt/Sanders_Dash_Seal/data if missing and leaves it owned by sanders:sanders before the app unit is restarted, idempotently, so app startup never depends on the directory already existing with the right owner.

**Implementation:** deploy/deploy_all.sh, inside the app-unit block, immediately after the sanders user and group are ensured and before the unit file is installed and the service restarted: `sudo mkdir -p "$REPO_DIR/data"` and `sudo chown sanders:sanders "$REPO_DIR/data"`. No other step changed.

**Manifests:** deploy/deploy_all.sh.pbd.json payload_hash updated to the new file bytes; this file's manifest likewise. Signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** live verification waits on the next owner-approved deploy, which runs this step before restarting the app. The exact exception line from the live journal was still being captured when this entry was written; if it names a different cause, this entry will be corrected. (Correction, later on November 23, 2026: the short grep Run Command captured it — `PermissionError: [Errno 13] Permission denied: '/opt/Sanders_Dash_Seal/data'`, with the checkout owned opc:opc `drwxr-xr-x`. The cause named in this entry is confirmed; no change to the fix.)

## Full self-repair — env guard, diagnose-and-repair playbook, and last-known-good snapshots (November 23, 2026)

**Source:** Owner decision, November 23, 2026 (options widget, 11:05 MST): "Build the full self-repair layer — playbook repairs run on their own, secrets, gates, and money always stay mine." This entry builds the layer the owner approved in the same conversation where the automatic-recovery entry above was written: the watchdog restarts a service that stops answering, but it cannot fix WHY the service stopped — a missing env file, a data directory the app user cannot create, a stale process holding the port, a broken nginx config. Those causes are now a playbook: the machine classifies the failure from evidence, applies the one matching pre-written repair, and records everything. Autonomous diagnose-and-repair is authorized for playbook repairs only.

**Hard boundaries (owner's words, in substance — encoded in the header of deploy/sds_repair.sh and binding on every playbook entry):** never create, rotate, or guess a secret value — the only secret handling allowed is re-fetching the owner's existing OCI Vault secret unchanged (P1) and restoring the byte-for-byte runtime.env copy held in a root-only last-known-good snapshot; never approve any gate, in GitHub or anywhere else; never touch Stripe settings, payments, or money; never edit or push the repository (repairs act on installed files and live state; P4 copies FROM the checkout, and P5's chown of .git metadata ownership changes no content); never delete application data — the only process action allowed is P3's kill of a stale non-unit gunicorn process holding port 8000, and P3 refuses to kill anything whose command line is not gunicorn.

**Acceptance criteria:** (1) at every app start, a conditional env guard leaves a shape-valid /etc/sanders-dash-seal/runtime.env in place — regenerating it from the OCI Vault via the repo's own refresh path when it is missing or malformed — without ever blocking the start attempt when it cannot; (2) when a plain watchdog restart has already failed to recover a service in the same incident, the watchdog escalates to the repair playbook instead of restarting again, under the same 5-minute cooldown; (3) the playbook classifies each incident into exactly one playbook entry or UNKNOWN, mutates only what that entry prescribes, caps itself at 3 repair attempts per service per incident (an incident ends when the service passes a health check), and escalates with a written record — never a guess — when nothing matches or the cap is reached; (4) every classification, action, and outcome is recorded as JSON lines in /var/lib/sds-repair/incidents.jsonl (root-only) and in the journal; (5) every deploy that passes its health check snapshots the verified-working configuration as a last-known-good set the playbook can restore, keeping at most 3 snapshots; a failed health check takes no snapshot.

**Implementation (committed locally on branch `permanent-deploy-repair`, NOT pushed):**

**1. `deploy/sds_env_guard.sh` (new) + app unit wiring.** A root-run bash guard (`set -u`). If /etc/sanders-dash-seal/runtime.env exists AND a line matches the deploy preflight's shape pattern (`^[[:space:]]*STRIPE_WEBHOOK_SECRET=whsec_`), it exits 0 and does nothing — the normal path costs one grep. Otherwise it runs the repo's refresh path, deploy/refresh_provider_secrets.py, exactly as that script requires: as root, no `--restart` (that flag drives docker compose, which is not how this instance runs the app; systemd restarts the unit itself). What reading that script forced into the design: it reads the compartment id from /etc/sanders-dash-seal/release.json before anything else, so on an instance without that file the refresh cannot run at all; it exits 0 with PROVIDER_SECRET_NOT_CONFIGURED when the Vault holds no matching secret; and it can exit 1 at its settings-file step AFTER already writing a valid runtime.env. The guard therefore never trusts the refresh's exit code: it re-checks the file's shape afterwards and exits 0 only if a shape-valid file now exists, 1 otherwise — and the refresh's own status token (which carries no secret material by that script's design) is logged for diagnosis. The refresh writes ONLY STRIPE_WEBHOOK_SECRET, atomically, root:root 0600, and only when the Vault config actually carries a webhook secret; if the Vault yields nothing shape-valid, any existing file is left untouched and the guard fails loudly (`logger -t sds-env-guard`). The secret value is never printed or logged anywhere in the guard; every check is shape-only. Wiring: deploy/sanders-dash-seal.service gains `ExecStartPre=-+/usr/local/sbin/sds_env_guard.sh` — `-` so a guard failure never blocks the start attempt (the app and the preflight surface the real state), `+` so it runs as root (the refresh requires euid 0; runtime.env is root-owned) even though the unit's user is sanders. It is placed BEFORE the existing ExecStartPre pkill, deliberately: the Vault refresh can take some seconds when the network is slow, and the port-clearing kill should remain the last thing that happens before gunicorn binds.

**2. `deploy/sds_repair.sh` (new).** The playbook, invoked by the watchdog as `sds_repair.sh <service-key>` (app, money-factory, secretary, twostep, judge, nginx — the watchdog's own service table) and by hand as `sds_repair.sh gitperms` or `sds_repair.sh restore-lkg <nginx|app|env|watchdog>`. It gathers bounded evidence per service (unit state through the unit's own manager, the last journal exception lines via `journalctl -o cat`, file checks, listener checks), classifies into exactly one entry or UNKNOWN, and acts:

| Class | Service | Evidence signature | Repair |
|---|---|---|---|
| P1 env | app | runtime.env missing, or STRIPE_WEBHOOK_SECRET not whsec_-shaped | Run the env guard's Vault refresh path; re-verify the shape; restart the app. If the shape is still invalid, escalate (the remaining cause is the Vault secret's content — an owner step). |
| P2 datadir | app | Journal shows PermissionError / permission denied / mkdir at data_dir, OR /opt/Sanders_Dash_Seal/data missing or not owned by sanders | `mkdir -p` + `chown sanders:sanders` the data directory (and the two ledger files wsgi.py writes, ledger.db and bozly_ledger.db, if they exist — ownership only, data never deleted); restart the app. |
| P3 port | app | Port 8000 listening, holder PID ≠ the app unit's MainPID | Verify each stale holder's command line is gunicorn (refuse and escalate otherwise); TERM, then KILL after 3s if still holding; restart the app. |
| P4 nginx | nginx | `nginx -t` fails, OR 80/443 listener missing | Reinstall the server conf + snippet from the repo checkout (the same sources and destinations deploy_all.sh step 4 uses, including its /rtsa/status append), `nginx -t`, restart nginx. If the checkout copies are unavailable or fail `nginx -t`, restore from the newest last-known-good snapshot (hash-verified). If neither passes, the previously installed files are put back and nginx is NOT restarted into a bad config. |
| P5 gitperms | checkout | Manual entry point only: `find` shows entries under /opt/Sanders_Dash_Seal/.git not owned by opc (the deploy_all run #100 signature) | `chown -R opc:opc /opt/Sanders_Dash_Seal/.git`; re-verify. No automatic trigger exists — the watchdog never syncs the repo, so there is no sync failure for it to observe; the entry point is exposed for the owner and for any future deploy-side caller. |
| P6 parked | any | Unit in a failed state (for the app, only after P1–P3 are excluded; the journal's start-limit signature is recorded when observable) | `reset-failed` + restart through the unit's own manager (system, or opc's user manager for the Secretary, TwoStep, and Judge — the same two forms the watchdog uses). |
| UNKNOWN | any | No signature matches | NO mutation. An escalation record with the gathered evidence is appended to the incident log; exit 2. |

Caps and records: the attempt counter is incremented BEFORE any mutation; at most 3 attempts per service per incident; counters live in /var/lib/sds-watchdog/repair-attempts-<service-key>, shared with the watchdog, which clears them when it sees the service pass a health check (the repair script also clears on its own healthy entry check and on a passing post-repair check — that pass is what ends an incident). Every classification, repair action, and outcome is appended as one JSON object per line to /var/lib/sds-repair/incidents.jsonl (directory 0700 root, file 0600) with fields ts, service, class, evidence (short), action, result, and mirrored to the journal via `logger -t sds-repair`. Bozly witnessing was checked before being claimed: the repo's Bozly recorder (core_platform/bozly_wiring.BozlyRecorder) is an in-process component of the WSGI app that records VERIFIED STRIPE EVENTS, and the repo exposes no machine-event or receipt route a root shell script could submit an incident record to — so no Bozly submission is made and none was invented; incidents.jsonl + the journal are the record (open item below).

**3. Watchdog integration (`deploy/sds_watchdog.sh`).** maybe_restart now counts plain restarts per incident (restarts-<name> in the state directory). When a service is DOWN and that count is already ≥ 1 — a plain restart was attempted in an earlier round of the same incident without recovery — the watchdog invokes /usr/local/sbin/sds_repair.sh <service-key> instead of restarting again, consuming the same 5-minute cooldown stamp and resetting the failure counter exactly as a restart does; the playbook's own 3-attempt cap governs further rounds. When the service passes a health check, note_result clears both the plain-restart count and the playbook's attempt counter (incident end). If sds_repair.sh is not installed, behavior is exactly the previous plain-restart loop. All existing checks, counters, cooldown, and logging are otherwise unchanged.

**4. Last-known-good snapshots (`deploy/deploy_all.sh` step 8, new).** After the step 7 health check passes — and only then; a failed health check exits before this step and takes no snapshot — the deploy snapshots the verified-working configuration to /var/lib/sds-lkg/<timestamp>/ on the instance: the installed nginx server conf and snippet (copied from /etc, as installed), the installed app unit, the watchdog + repair + env-guard scripts as installed in /usr/local/sbin, a MANIFEST.txt with the sha256 of every snapshotted file (sha256sum format; the repair script verifies hashes before any restore), and DEPLOYED_COMMIT with the git commit the deploy put live. At most the 3 newest snapshots are kept. runtime.env is copied too, and this is deliberate and bounded: the snapshot directory is created root-only (0700) on the instance, the copy is forced 0600 root:root, and the file NEVER enters the repository — its only purpose is `sds_repair.sh restore-lkg env`, putting back byte-for-byte the exact secret file a passing deploy verified, which is a restore, not a creation, rotation, or guess. The playbook's P4 fallback and `restore-lkg <nginx|app|env|watchdog>` restore from the newest snapshot, each file hash-verified against MANIFEST.txt first. Snapshot problems during a deploy are loud warnings, never a deploy failure — the deploy has already passed at that point.

**5. Installs (`deploy/deploy_all.sh` step 5c, extended).** Every deploy now also installs deploy/sds_repair.sh and deploy/sds_env_guard.sh to /usr/local/sbin (mode 0755, guarded like the watchdog install). The deploy header comment records steps 5c and 8.

**Manifests:** deploy/sds_env_guard.sh and deploy/sds_repair.sh are new files with new paired manifests in the deploy/ format (nested, 2-space indent, trailing newline); the manifests for deploy/sds_watchdog.sh, deploy/deploy_all.sh, deploy/sanders-dash-seal.service, and this file are updated in place, formats preserved. Every payload_hash is the SHA-256 of the file's bytes, re-verified after the commit; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items (honest gaps, not silently papered over):** (1) Whether the OCI Vault secret sds-runtime-provider-config actually holds the current provider config is UNVERIFIED — the guard is safe either way (it acts only when the live file is missing or shape-invalid, verifies by shape, and leaves the file untouched when the Vault yields nothing), but if the Vault config is stale or absent, P1 escalates to the owner instead of healing; verifying the Vault content is an owner-side console check. The refresh also requires /etc/sanders-dash-seal/release.json (compartment id) on the instance; if that file is absent the refresh cannot run and P1 escalates with that named in the log. (2) Bozly witnessing of repair incidents is NOT wired: no machine-event/receipt route suitable for a root shell script exists in the repo (the Bozly recorder is in-process and records verified Stripe events only). If the owner wants Bozly receipts for repairs, a machine-event route must be built as its own change; until then incidents.jsonl + the journal are the record. (3) Escalation is an on-instance record (incidents.jsonl + journal) only — there is no off-instance alerting, because no reporting channel the owner has approved exists; the morning briefing reads the journal, and adding a push channel is an owner decision. (4) The app unit sets no TimeoutStartSec: a Vault refresh on a slow network runs inside ExecStartPre and counts toward systemd's start timeout. The guard's common path is one grep, and a timed-out start is retried by Restart=always, but if live operation shows refresh-time starts timing out, raising TimeoutStartSec on the unit is the follow-up. (5) The Secretary/TwoStep/Judge generated units still lack StartLimitIntervalSec=0 (noted in the automatic-recovery entry above); P6 covers the parked case from outside. (6) Live operation of the whole layer is unverified until an owner-approved deploy installs it and an incident (or a manual `sds_repair.sh` run) exercises it on the instance; nothing in this entry has been pushed or deployed.

## Police Men backend taken off public view — Dash & Seal is the face of its own domains (November 23, 2026)

**Owner's orders:** 2026-11-22 01:37/01:48 MST — the Police Men dashboard is not for public viewing and its operational details are the platforms' security features; 2026-11-22 03:43 — the dashboard's new home is a password-protected page; 2026-11-23 14:35 MST — "Take the backend off public view now"; 2026-11-23 14:37 MST — Dash & Seal itself is the public face on its own domain.

**Why Dash & Seal was not showing:** the 443 server block in `money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal_server.conf` carried `location = / { try_files /index.html =404; }`. An exact-match location beats the snippet's prefix `location /` proxy, so every request to `/` on every domain served the static Police Men dashboard copy from the web root and never reached the Dash & Seal app on 127.0.0.1:8000. The snippet already proxied `/` to the app; the dashboard block shadowed it. Verified live 2026-11-23 14:35 MST: the dashboard was the home page on sandersdashandseal.com and sanderslegalhelpersllc.com, and `/rtsa/status` answered publicly with the full telemetry JSON.

**Changes (this entry):** (1) The `location = /` dashboard block is removed from the server config; `/` now reaches the app through the snippet on both the portal and the landing domain. (2) The snippet's `location = /rtsa/status` gains `allow 127.0.0.1; allow ::1; deny all;` — the telemetry stays available to the server itself (the dashboard's future password-protected home will sit in front of it) and answers 403 to the public. The live dashboard copy in the web root is moved to a backup folder by the one-time takedown workflow, not deleted; the password-protected page build is the follow-up step.

**Manifests:** the manifests for both nginx files and this file are updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** (1) The password-protected Police Men page (owner decision 2026-11-22) is not built yet; until it is, the dashboard is reachable only from the server itself. (2) A future deploy installs these same files (deploy step 4), so the takedown survives deploys; the watchdog's P4 repair reinstalls from the same repo sources.

## Certificate coverage by design — watchdog guard and deploy-time warning (November 23, 2026)

**Owner's directive (2026-11-23 14:53–14:54 MST):** every domain and its www must have its certificate correctly assigned, and "we've got to ensure they always have the right certification by design globally correct."

**The incident that proved the need (same day):** www.sanderslegalhelpersllc.com went live in DNS at 14:49 MST and immediately showed visitors a "connection is not private" warning — the Let's Encrypt certificate's 9 names never included it, because it had no DNS record when the certificate was issued on 2026-11-22. Nothing in the platform noticed; the owner found it on his phone. The owner approved expanding the certificate (14:51 MST); the one-time workflow expand-cert-www-20261123.yml (run 45274265668) added the name — the certificate now carries all 10 names, expires 2027-02-21, and strict verification passed on every name.

**Changes (this entry):** (1) `deploy/sds_watchdog.sh` gains a cert-coverage guard, run every watchdog cycle (2 minutes): it parses the served names from the installed nginx server conf, reads the names on the certificate nginx actually serves (loopback TLS), and fails the check if any served name is missing from the certificate or the certificate has under 21 days to expiry (automatic renewal should keep it far ahead; a short fuse means renewal is broken). The guard DETECTS and ESCALATES only — one escalation journal record per incident, cleared on recovery — and never restarts anything and never touches the certificate: issuing or expanding a certificate is an owner-approved action under the 2026-11-23 boundary (secrets, gates, and money stay the owner's). (2) `deploy/deploy_all.sh` gains step 7b, the same comparison at deploy time, printed as a loud CERT COVERAGE WARNING in the deploy log — never a deploy failure (the deployment law: nothing stops deployment).

**Manifests:** the manifests for deploy/sds_watchdog.sh, deploy/deploy_all.sh, and this file are updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** (1) Whether certbot's automatic renewal timer is enabled and active on the instance is to be reported by the install run for this change; the guard's 21-day expiry fuse is the backstop either way. (2) The guard derives served names from the one installed server conf; a future second server conf would need the parser widened.

## Portal presentation repair — blue-and-gray corporate styling, mobile formatting, seals and tagline (November 23, 2026)

**Owner's direction (2026-11-23):** the live appointment page shows the intake and timeline content but does not prove the booking process works; a mobile styling / stylesheet problem is visible. Correct it by repairing the presentation and verifying the functionality WITHOUT rebuilding or replacing the platform and WITHOUT removing any existing functionality: consistent blue-and-gray corporate styling; mobile-responsive formatting; every form field clearly visible and usable on a phone; the sign-in, appointment submission, timeline, and quote-display workflow fixed; service-location and appointment-time presentation corrected; all six service packages, client records, Stripe integration, and owner administration preserved; the exact authorized corporate seals and the complete tagline displayed.

**Diagnosis (from the sources, before any change):** `web/booking.css` was a 48-line theme patch, not the stylesheet the page was built for. It defined almost none of the classes `web/index.html` and `web/booking.js` use (no `.sds-action-card`, `.sds-main-viewport`, `.sds-button-primary`, `.request-item`, `.quote-row`, badge, or form-control rules), forced a black (#111) background with white text, and contained no layout or media-query rules at all. The intake fields carried inline dark styles (#2A2A2A backgrounds, #444 borders) that sit nearly invisible on the dark cards in daylight; the accent was bright cyan #00A3E0, not the corporate blue and gray; the viewport meta disabled pinch zoom (`maximum-scale=1.0, user-scalable=no`); no corporate seal appeared anywhere on the page; the header carried a different line ("From the Road to Remote, We Seal the Deal.", marked aria-hidden) instead of the corporate tagline, and the closing "The Sanders Way!" was absent. The workflow code itself (booking.js: session check → timeline load → submit → details → itemized quote → accept → Stripe checkout with the destination host validated) was complete; its one wrong behavior was the submit handler's 401 branch, which told a signed-out customer to "check your requested time and details" instead of asking them to sign in.

**Changes:** (1) `web/booking.css` rewritten as the complete portal stylesheet — corporate blue (#1d5c99 / #123c63 / #0d2c4a) and gray palette on a light gray page with white cards; every class used by the page and script defined; mobile-first responsive layout (720px column, larger-screen adjustments at 640px); form controls are white, dark-text, 16px (no iOS focus zoom), with clear gray borders and a blue focus ring; timeline items, quote rows, badges, notices, and the seal strip styled; reduced-motion respected. (2) `web/index.html` — viewport zoom restored; the dark inline field styles removed (presentation now lives in the stylesheet); the corporate headquarters seal (S & G Security Inc., the owner's exact supplied file) added to the header; the header tagline replaced with the corporate tagline "Our family will take great care of your family" (visible, no longer aria-hidden); the footer gains all four companies' exact seals with their names, the tagline, and the closing "The Sanders Way!". Every element id, field name, option value, published price, and script hook is unchanged. (3) `web/booking.js` — only the submit 401 branch changed: it now says "Please sign in to continue.", reveals the sign-in link, and disables the fields, matching the timeline's existing 401 handling. (4) The four seal images added under `web/` as byte-identical copies of the owner-supplied files, each with its own source manifest; `/assets/seal-*.png` routes added in `app/customer_app.py` (alias hosts) and in the canonical-host asset branch of `deploy/deployment.py`.

**Preserved, deliberately untouched:** the six service packages and everything else on the Imperial Jade landing (`web/jade-landing.*`); the intake's three canonical services and their published prices; client records and the appointments API; the Stripe checkout flow and its host validation; owner/operator administration (`web/operator.*`, the operator quote/provider routes); the sign-in pages (`web/auth.*`).

**Manifests:** manifests for every changed or added file are created/updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** (1) A live end-to-end booking with a real signed-in customer account has not been exercised by the assistant; live verification covers the served page, stylesheet, script, and seal assets over strict HTTPS, the unauthenticated session answer (401, the platform's own health expectation), and the health endpoints. (2) The landing page still uses its Imperial Jade styling with a text "SDS" badge and no seals — the owner's repair direction named the appointment page; whether the same seal/tagline treatment should extend to the landing is the owner's call.

## Relaunch of the real Dash & Seal — the Imperial Jade storefront on its own domain (November 23, 2026)

**Owner's direction (2026-11-23 15:16–15:18 MST):** the owner supplied the official banner artwork ("This is what it's supposed to look like") and directed: "You must go to the repo and relaunch the real Dash and Seal", "Everything must be fortune 500", and "The real Dash and Seal RTSA platform is ready for deployment." This entry supersedes the palette portion of the portal-repair entry above: the portal's structural repair stands (complete stylesheet, visible fields, workflow fix), but its interim blue-and-gray palette is replaced by the platform's own Imperial Jade and gold, and the header tagline returns to the brand line the banner carries.

**What the banner establishes as the design:** deep Imperial Jade green and gold; "SANDERS DASH & SEAL — Sanders Legal Helpers LLC — Premium Notary & Document Solutions"; the Sanders Legal Helpers seal (DBA Sanders Dash & Seal) and the Sanders Corporate Headquarters seal; the founder's portrait; the four service lines (Notary Services, Document Preparation, Business Support, Business Formation); the ribbon line "From The Road To Remote, We Seal The Deal."; and the closing "The Sanders Way!".

**Changes:** (1) `web/dash-seal-banner.png` added — the owner's exact supplied artwork, byte-identical, with its own source manifest; `/assets/dash-seal-banner.png` routes added in `app/customer_app.py` and in the canonical-host asset branch of `deploy/deployment.py`. (2) `web/jade-landing.html` rebuilt from its one-line staging form into a complete, formatted storefront: the headquarters seal in the topbar (replacing the text "SDS" badge), the banner as the hero, then the original hero copy and founder portrait, all six service packages at their published prices, the founder-led about section, the Wall of Valor with both photographs, and the Start Your Request call to action — every pre-existing content element preserved verbatim — and a footer carrying all four companies' seals, the corporate tagline "Our family will take great care of your family", the brand line, and "The Sanders Way!". (3) `web/jade-landing.css` gains only appended rules (banner hero, brand seal, seal strip, footer lines); no existing rule changed. (4) `deploy/deployment.py`: the canonical host now serves the storefront at `/`, exactly as the alias hosts already did — Dash & Seal is the public face on its own domain; the appointment portal remains at `/appointments` on every host, and all API, auth, operator, voice, and video routing is unchanged. (5) `web/booking.css` re-paletted to Imperial Jade and gold (jade gradient background and panels, gold headings and buttons, cream text) with the repair's structure intact — white high-contrast fields with a gold focus ring; `web/index.html`'s header tagline returns to "From the Road to Remote, We Seal the Deal." (the corporate tagline and "The Sanders Way!" remain in its footer).

**Preserved:** all six packages and prices; the intake, timeline, quote, Stripe checkout, sign-in, operator administration, client records, and every API route; the Wall of Valor; the founder section; both domains' cohesion (one storefront, one portal, everywhere).

**Manifests:** manifests for every changed or added file are created/updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** (1) Live verification at deployment covers the storefront and banner on the canonical and alias hosts, the portal and its assets at /appointments, the six prices on the served page, the unauthenticated session answer, and the health endpoints; a live end-to-end booking with a real signed-in customer account has still not been exercised by the assistant. (2) The gated deploy_all runs remain parked at the owner's Production-Authorization-Gate; this relaunch reaches the server by the same one-time sync pattern as the day's earlier repairs, and a full deploy pass (with its step-8 last-known-good snapshot) still awaits the owner's approval of a deploy run.

## Layout uplift to the Imperial Jade design system — auth, operator, voice, and video pages (November 23, 2026)

**Owner's directive (2026-11-23 18:22–18:27 MST):** the platform layouts must change — everything runs on Fortune 500 standards end to end, past, present, and future builds, and the layouts represent his brand: "Premium all the way." The 2026-11-23 layout audit graded the pages below D (auth, operator) and F (voice, video) against the owner's banner design; the extracted design system (Imperial Jade + gold tokens, white-field form standard, required header/footer brand elements) is the working reference for this repair.

**Changes:** (1) `web/booking.css` — the form-field selector list is extended to `input[type="password"]`, `input[type="email"]`, and `textarea` (base and `:focus` rules), closing the latent gap that forced the auth page onto inline dark styles; `#auth-message` gains the gold-bright message color; a new voice/video section styles `video`, `pre`, and `audio` elements and the `.sds-media-actions` secondary buttons, all in design-system tokens, so the media pages need no stylesheet of their own. (2) `web/auth.html` — the anti-zoom viewport (`maximum-scale=1.0, user-scalable=no`) is removed; all three cyan `#00A3E0` uses are deleted; the dark inline field styles (`background: #2A2A2A; color: #FFF; border: 1px solid #444`) are removed from the username, password, and setup-token inputs and their labels, so the shared white-field standard applies; the `#E5E5E5` description text becomes cream-dim `#cfe0d6` and the `#888` cancel link falls back to the shared gold link color; the headquarters seal is added to the header and the bare footer is replaced with the standard footer (four-seal strip, corporate tagline, "The Sanders Way!") copied from `web/index.html`. (3) `web/operator.html` — the same template repair: anti-zoom viewport removed; cyan removed from the eyebrow (an inline override of `.sds-eyebrow`'s gold), from `#notice`, and from the `#details` card border; the bright-red `#FF4444` sign-out link becomes gold `#e8c879`, the design system's standard link treatment; headquarters seal in the header and the standard footer added. (4) `web/voice.html` and `web/video.html` — rebuilt inside the platform's standard chrome: the shared `booking.css` replaces their per-page `<style>` blocks (system-ui, `#111`/`#f4f4f4` grays gone), the header carries the headquarters seal and road line, the content sits in an `.sds-action-card`, and the standard footer closes each page; pinch zoom is allowed. The developer comment blocks describing ffmpeg/WebRTC/SFU internals are removed from the served source, as is the ffmpeg note in the voice page's recording status text. Every element id, field name, endpoint, and script hook on all four pages is unchanged — presentation only.

**Preserved, deliberately untouched:** `web/resources.html` and `web/dashboard.html` (owner decisions pending on both — gate/retire the public free-tier catalog; retire or rebuild the rival-palette dashboard artifact); `web/index.html` and `web/jade-landing.*` (the reference implementation); every script (`auth.js`, `operator.js`, `booking.js`, `video.js`, and the voice page's inline logic apart from the comment and status-text removals named above).

**Manifests:** the manifests for web/auth.html, web/operator.html, web/voice.html, web/video.html, web/booking.css, and this file are updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated.

**Open items:** (1) This change is pushed to main; it reaches the live site through the owner's gated deploy path, and live re-verification of the four pages follows that deploy. (2) The audit's remaining items stand: `web/resources.html` and `web/dashboard.html` await owner decisions, and the systemic watchdog public-face guard (served source must carry the seal strip/tagline/closing and must not contain the banned tokens) is a separate build.

## Resources page retired from public serving — "No tiers are free" (November 23, 2026)

**Owner's ruling (2026-11-23 18:59 MST):** "No tiers are free." Nothing in the platforms is presented as free-tier, and the standing rule that Always Free is never public knowledge applies in full. `web/resources.html` was publicly titled "Cloud Free Tier Status" and advertised zero-cost allowance records; it is retired from public serving on this ruling.

**Changes:** `app/customer_app.py` — the `'/resources.html'` and `'/resources.js'` entries are removed from the `ASSETS` route map, replaced by a comment recording the retirement. `'/resources.js'` is removed with the page: `web/resources.js` is exclusively the retired page's viewer script (it loads and renders the free-resources catalog) and no other page references it. No served page linked to `/resources.html`, so no link removals were needed in the landing, portal, auth, or operator pages.

**Route behavior after this change:** the route map was the only way in — `deploy/deployment.py` serves `web/` files only through fixed allowlists that never included this page, and no nginx root points at the repo `web/` directory — so the files `web/resources.html` and `web/resources.js` remain in the repo, unrouted. On the canonical host an unknown path now answers exactly as other unserved paths do (308 redirect to `/`); on alias hosts the customer app answers 404 `not_found`, the same as any path not in the map.

**Preserved, deliberately untouched:** the page and script files themselves (kept for the record, reachable by no route); the internal `/api/platform/free-resources` catalog route in `deploy/deployment.py` (an API route, not the public page — outside this change); `web/dashboard.html` (separate owner decision, still pending).

**Manifests:** the manifests for `app/customer_app.py` and this file are updated in place, formats preserved; every payload_hash is the SHA-256 of the file's bytes; signatures remain UNSIGNED_SOURCE_MANIFEST — none fabricated. The manifests for `web/resources.html` and `web/resources.js` are unchanged because the files are unchanged.

**Open items:** this change is pushed to main; it reaches the live site through the owner's gated deploy path, and live re-verification (the page's URL no longer serving the free-tier catalog) follows that deploy.

## Sanders Signal social-distribution hub — November 22, 2026

Source: owner direction 2026-11-22 14:43–14:49 MST ("Yes, start building the
hub"; audio/video top-notch globally; the seven additions; real-time
language, sign language, Braille, globally) and
`social-distribution-build-plan.md` (working name Sanders Signal; owner
picks the final name). No MASTER section covers social distribution; this is
a new owner-directed platform inside Sanders Dash & Seal, built native
(not a third-party scheduler), under Core Laws 10 and 11 (Always Free only,
actually used).

Acceptance: one composed post fans out to the four companies' Facebook Pages
and Instagram Business accounts (Meta Graph API, token from env only);
a company post reaches that company only; an S & G Security Inc. broadcast
reaches all four companies only after explicit owner approval (default deny);
every publish is logged with what, where, when and who approved it; a failed
post on one network never blocks the others and reports its reason; no
address or contact info is added by the hub; unconfigured adapters report
not-configured diagnostically and never block import or startup; no live post
is made without configured tokens. Audio/video: the post model carries
vertical video, standard video and standalone audio; each adapter declares
its accepted formats and the hub declines unsupported formats with a reason,
never silently. Global: no region, no geo-gating, no language restriction.
Accessibility metadata (language, sign-language track, Braille-ready text)
travels with the post through queue, approval and fan-out. Scheduling is
timezone-aware; guardrails block address / wrong phone / wrong-company posts;
roles are writer / approver / publisher per company, tied to the Bozly
officer model; the media library stores references, not file copies;
notifications fire on approval-waiting, published, and failed-with-reason.

Bozly scope decision: the HQ approval is recorded through
`BozlyAuthGate.generate_action_payload_hash` and, when the owner supplies
signatures and provisioned public keys, `evaluate_executive_approvals`; no
signature or receipt is ever invented, and an unconfigured Bozly hook is
recorded as such on the approval record. `bozly_claim_integrity` is not used
(the post is not a recorded financial transaction).

Verification: local dry-run 2026-11-22, 11/11 cases passed, offline with a
recording stub transport (urllib.urlopen monkeypatched to raise, proving no
request left the machine): (1) import + hub constructs with no env set, all
adapters NOT_CONFIGURED; (2) company text post routes to that company only,
FB+IG published; (3) company vertical video, Meta published, others
decline/not-configured with reasons; (4) company audio post, all networks
decline with reasons, zero publish attempts; (5) HQ broadcast without
approval denied, awaiting_approval, zero attempts; (6) HQ broadcast with
approval routes to all four companies, Bozly hook note recorded;
(7) scheduled post queued until due, then published; (8) guardrails block
address / wrong phone / wrong-company posts; (9) role denial, writer cannot
approve or publish, zero attempts; (10) accessibility metadata (language
es, sign-language ASL, Braille-ready text) identical through queue,
approval and fan-out; (11) analytics aggregate per network/company, missing
metrics NOT_AVAILABLE. No live posting, no tokens, HTTP layer stubbed. Do
not claim live posting until a Meta app + tokens exist and one real publish
is observed.

Named next increments (not silently dropped): translation engine (the hook
is the interface; no engine invented); sign-language interpretation
production and which sign languages are covered (owner decision); Braille
rendering (Braille-ready text ships now; embosser/display rendering is a
later increment); notification delivery channel; LinkedIn/Threads/YouTube
live connections; TikTok app approval; X paid-tier decision (owner).

## Platform registry: 33 verifiable platforms (November 22, 2026)

**Source:** Owner instruction, November 22, 2026: "Everything with an actual name stay it a platform too." Follow-up to the Secretary/Judge/Police Men (commit 145e883) and TwoStep (commit 9938bc9) registry additions. The name inventory (`~/workspace/named-platforms-inventory/main-repo-inventory.md`, base 9938bc9) lists 76 named platforms in the main repo; 13 were in the registry, 63 missing.

**Acceptance criteria:** The 33 verifiable missing entries are listed in the registry with the same fields as the existing entries, using only verified facts; the existing thirteen entries are unchanged; nothing is invented for entries with no stated endpoint or module.

**Implementation:** Appended 33 entries to `core_platform/ai_platform_links.json` (13 → 46): Sanders Dash & Seal itself (https://sandersdashandseal.com, app on 0.0.0.0:8000, module `wsgi.py`) and Money Factory Legal Aid v1.668 (http://127.0.0.1:8668, module `money_factory_legal_aid_v1_668/app.py`), plus 26 grid entries from `deploy/oracle/sanders_master_grid.json` ids 1–8 and 10–27 (grid id 9 is Grantwriter, already in the registry; grid id 28, Sanders Travel, is EXCLUDED — the grid file is truncated mid-entry, so its endpoint is partial only), each at http://<host>:<port>/v1/status with no local module, plus 5 module-only entries with `local://` endpoints (Zone Watch, Sanders Conductor, Sanders Labyrinth Shield, Sovereign Shield V3, Glass-Box Audit), mirroring the existing `local://` convention used by Bozly, Minotaur Sentinel, and the others. Grid caveats recorded in each grid entry's description: the grid hosts are Google Cloud IPs (34.133.172.131, 35.238.209.6, 34.27.70.1), not the Oracle instance (129.146.111.166); the grid's "ACTIVE" health is a claim in the file, not a verified live check; the grid file is truncated at id 28 and is invalid JSON. Spelling conflicts recorded as written: grid "Sanders Omniconn" vs Zone Watch hostname omniconm, grid "Gai Mind" vs gia-mind; grid nickname "Beta" for Lil Mama conflicts with the separate watchdog-beta hostname. Zone Watch reads CZDS_USERNAME, CZDS_PASSWORD, CZDS_DOWNLOAD_BASE_URL, and ZONE_WATCH_DATA_DIR from the environment (all four listed as env_vars); the other four module-only entries read no env vars. The 29 named-only entries with neither endpoint nor module (including the 13 RTSA role contracts, explicitly "NOT deployed intelligences", and the 12 IT AI agents, INTERFACE_ONLY) are NOT added — they have no verifiable facts to list. Paired with the updated `.pbd.json` hashes for the registry and this file. Consumer note: `core_platform/ai_platform_links.py` never reads `endpoint` and has no checker for any id outside its hardcoded set, so the 33 new entries report NOT_IMPLEMENTED ("no checker for <id>") from `check_all()`, exactly like secretary/judge/police_men/twostep do today; the registry still loads, `summarize()` still covers only its hardcoded 9 ids, and `deploy/deployment.py` only reports the statuses (no gate). The stale test `tests/test_ai_platform_links.py` already fails on current main (it asserts 9 ids == PLATFORM_IDS, but the registry has 13) and its per-entry assertions require non-empty `local_modules`, which the 26 grid entries (no local module) do not have — reported, not changed, per the no-test-work rule. PREPARED, NOT PUSHED — November 22, 2026.

## Watchdog public-face guard — November 23, 2026

**Source:** Owner standing rule, November 23, 2026 16:01 MST: "Everything that has its own domain name should always be the public facing RTSA platform"; push ordered November 23, 2026 21:57 MST ("Everything to main immediately"). Companion to the certificate-coverage guard and its deploy-time warning (step 7b).

**Acceptance criteria:** Every served name's / response carries the public storefront marker; a failure is detected and escalated with no restart and no mutation of what any name serves; a deploy reports a wrong face loudly without failing.

**Implementation:** `deploy/sds_watchdog.sh` gains `check_public_face`, called every cycle after `check_cert_coverage`: the served names come from the same installed server-conf parse as the certificate guard; each name is fetched over loopback TLS (`curl --resolve <name>:443:127.0.0.1`) and the body must contain the marker `dash-seal-banner` (verified live on all 10 served names November 23, 2026). Outcomes go through `note_face_result`, mirroring `note_cert_result`: counter `fails-public-face` under /var/lib/sds-watchdog/, one escalation per incident (public-face-escalated stamp), journal via `logger -t sds-watchdog`. The guard never restarts a service and never changes what a name serves. `deploy/deploy_all.sh` gains step 7c: the same comparison at deploy time as a loud warning, never a failure. Code only — installation to the instance follows the owner's gated deploy path. Paired with the updated `.pbd.json` hashes for both scripts and this file.

## Ownership record: Living Trust stewardship replaced by Roosevelt Sanders — November 23, 2026

**Owner directive (November 23, 2026):** "Everything that is held by the living trust gets put in my name immediately" — confirmed the same evening: his name only, for now.

**Change:** Every record in this repository that named the Sanders Family Living Trust as steward now names Roosevelt Sanders: the stewardship headers in `nginx.conf` and `core_platform/~/Sanders_Dash_Seal/core_platform/Docker_file`, the `stewardship` field in `rtsa_police_men/status.json`, the stewardship and ownership lines embedded in `backend/platform-source.json`, and the Stewardship & Ops line in `rtsa_police_men/index.html`. The "& Bloodline Descendants" clause in the stewardship headers is unchanged, as are the Bloodline Governance Directive and the operator authorization gate. Sibling `.pbd.json` source manifests regenerated for each edited file.

## Notarization rollout: provider path wired, native chain repaired, jurisdiction framework completed — November 24, 2026

**Source:** Owner directive, November 24, 2026 00:00–00:03 MST: the platform has no working way to notarize anything; "It's all in Dash and Seal itself — you have to read everything to fix those issues"; "This is a global rollout fortune 500 style"; "you have to ensure nothing is left to chance." Controlling design: MASTER §2 (multi-jurisdictional notarial operations; Colorado track, Wisconsin upon commission approval, Florida Commissioner of Deeds upon its authority path; electronic and remote notarization where authorized), the October 22, 2026 provider increment recorded in this file (operator-authenticated, case-bound SignWell template document creation and BlueNotary RON session creation in the native WSGI runtime and operator workspace, using the providers' documented fixed HTTPS endpoints), and the native completion acceptance recorded in this file (exact, unexpired IDENTITY, COMMISSION, JURISDICTION, METHOD, HUMAN_ATTESTATION — plus RON_PROVIDER_AUTHORIZATION and room consent/recording evidence for RON — before session completion).

**Acceptance criteria:** (1) The operator provider route stops fabricating an empty history: GET returns the real `ProviderWorkflows` records for the case; POST submits a case-bound provider request through the same workflows module, with live provider calls gated by the owner's `ron_notarial` approval gate (the rule `deploy/deployment.py` already applies to every live provider route) and by key presence (absent key = the workflow layer's honest `<provider>_credentials_not_configured`). (2) Provider clients are built only from the owner's configured keys (`SIGNWELL_API_KEY`, `BLUENOTARY_API_KEY`, `SIGNWELL_TEST_MODE` — the names `deploy/publish_provider_secrets.py` uses), each bound to the provider's documented fixed endpoint: SignWell `POST https://www.signwell.com/api/v1/document_templates/documents/`, BlueNotary `POST https://app.bluenotary.us/api/integrationsv2/sessions`. (3) The native session chain is internally consistent and fail-closed: authority decisions register while a session is `AWAITING_AUTHORITY` (the polarity every sibling module already used), `NativeAuthority.missing()` reads all decision rows, the recording manifest reads the room table that actually exists (`native_ron_rooms`), and `NativeNotarySessions.complete()` enforces the recorded completion acceptance inside its existing transaction. (4) The jurisdiction framework answers for every jurisdiction the platform contemplates: AZ (owner-named appointment set, November 22, 2026) gains a registry entry; stale WY/appointments statements are corrected; `APPROVED_RON_JURISDICTIONS` is NOT changed — jurisdiction approval remains the owner's named decision. (5) Portal copy speaks plainly: the three machine-speak strings and the intake heading in `web/index.html` are replaced with human language. No gate is weakened, no jurisdiction is approved, no secret is created or rotated, no operator account is created, Stripe stays exactly as configured.

**Implementation:** `app/customer_app.py` — `create_customer_app` accepts injected `provider_workflows` / `provider_gate`; the provider route serves real records on GET and submits on POST (201 receipt; `ProviderUnavailable` → 503 with its status detail, `ProviderRequestConflict` → 409, gate absent/unapproved → 503 `approval_required`/`ron_notarial`). `deploy/deployment.py` — `RuntimeBindings.provider_workflows`; the bindings branch passes the workflows and a `ron_notarial` gate lambda into the customer app. `deploy/production_bindings.py` — builds `ProviderWorkflows` on `data/provider_requests.db` with the same cases/operator verifier/audit as the rest of the factory, plus `_ProviderClient` adapters over the repo's `WriteProviderClient` bound to the two documented endpoints, constructed only for configured keys. `core_platform/provider_connections.py` — documented-endpoint corrections: BlueNotary auth is the documented Bearer key for API v2 (was `X-Authorization-Token`); the read URLs were truncated placeholders and now name the documented resources (SignWell `GET /api/v1/documents/{id}`; BlueNotary `GET /api/integrationsv2/sessions/{id}`). `core_platform/native_authority.py` — `register()` state polarity repaired (`!=` `AWAITING_AUTHORITY` denies, matching seals/signatures/rooms); `missing()` uses `fetchall()`. `core_platform/native_recording_manifest.py` — room table name corrected to `native_ron_rooms` and a missing room row now denies instead of raising `TypeError`. `core_platform/native_notary.py` — `complete()` checks the durable authority registry (required kinds mirror `NativeAuthority.missing()`: all six kinds for RON, five for E_NOTARY) and, for RON, the room's `RECORDING_INDEXED` state with consent and recording digests, inside its existing atomic transaction; missing tables fail closed. `core_platform/global_compliance.py` — AZ `JurisdictionRule` added (`needs_owner_approval`, RON NOT approved); header and WY notes corrected to the November 22, 2026 appointment set (CO, WI, AZ). `web/index.html` — plain-language session, timeline and next-steps copy; heading now "Request an Appointment".

**Verification (exercised, not assumed):** all edited Python files compile; every edited file's `.pbd.json` payload hash regenerated and matching. The composed production application was built through the real factory and driven in-process: `/healthz` 200; `/api/compliance/ron?jurisdiction=CO` 403 fail-closed; the provider route answers 401 unauthenticated, 403 for a non-operator, 200 with real records for the operator, 503 `approval_required` with the gate unapproved, 503 `bluenotary_credentials_not_configured` with the gate approved but no key, 201 `CREATED` with a provider double at the client boundary, the record then listed by GET, an identical replay returning the stored receipt without a second provider call, and conflicting reuse answering 409 (24/24 checks). The native chain was exercised end-to-end in a scratch database: session → six registered authority decisions → room consent/recording → recording manifest (10-year retention) → document custody → verified signer signature → verified notary seal (commission honestly reported `False`) → completion; completion is denied without the room evidence and denied for an E_NOTARY session with no decisions, and succeeds for E_NOTARY with its five kinds (13/13 checks). No live provider call, no real payment and no factual notarial act occurred or is claimed.

**Still owner-named / unfinished, recorded not smoothed over:** the `ron_notarial` approval gate (0 of 9 gates approved); `APPROVED_RON_JURISDICTIONS` (empty by the owner's design); `SDS_OWNER_SETUP_TOKEN` and the one-time operator account creation; `SIGNWELL_API_KEY` / `BLUENOTARY_API_KEY` presence in the designated OCI Vault secret `sds-runtime-provider-config` (existence unverified from the build environment); the commission-verification registry adapter (`backend/commission_sync.py` has no in-repo data source and its own docstring forbids undocumented endpoints), which `AuthorityReview`'s authority verifier likewise awaits; provider completion webhooks and evidence retrieval (declared unfinished in the October 22 increment); the case-to-native-session bridge (no designed link exists in the repo); Stripe live mode (its own gate). Deployment to the instance follows the owner's gated path; a one-time deploy workflow for this rollout is prepared alongside the build record, not pushed (workflow files cannot go through the connector).

**Permanent record:** the full notarization rollout map — design vs. code vs. live wiring, the fix list as a rollout plan, and the pre-rollout checklist — is preserved as a permanent corporate engineering and technical accountability record at `docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md`.

## Notarization rollout stage 7: native infrastructure completed — journal, authority verifier adapters, case-to-native-session bridge — November 24, 2026

**Source:** Owner direction, November 24, 2026 (external review shared by the owner and adopted by him): preserve the notarization rollout map as a permanent corporate engineering and technical accountability record (done: `docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md`); production readiness requires demonstrated execution, particularly given the missing journal, the verification adapters and the native-session connection; external provider integrations must not become permanent substitutes for completing the platform's own native infrastructure — the objective is a fully functional, independently controlled Sanders Dash & Seal platform, with providers as integrations rather than the sole means of operation. Controlling design: MASTER (native notarial operations and the Glass-Box evidence discipline), the native completion acceptance recorded in this file, and `core_platform/authority_review.py`'s own contract (a review is recorded only when identity, notarial authority and provider are each independently verified).

**Acceptance criteria:** (1) The journal module named by the orphaned manifest `core_platform/native_journal.py.pbd.json` exists and is real: an append-only, hash-chained notarial journal that records a native session's completed act (session and case, act kind, the parties the session record binds, the seal's own digest where a seal is registered, digests of the completion evidence), written through the existing completion path in the same transaction as the completion itself, and indexed as JOURNAL evidence. A session that has not completed is never journaled; a digest is never manufactured for a seal that does not exist. (2) `AuthorityReview`'s three verifier adapters exist and verify only from evidence the platform itself holds: identity from the platform's own account records, notarial authority through the fail-closed contract in `backend/commission_sync.py`, provider from the provider clients the owner has configured. An adapter that cannot verify returns False; no adapter manufactures evidence, and no official endpoint is invented. (3) A case whose payment has settled can be carried into the native track: an operator opens the corresponding native session, case and session ids are bound durably, the session's state is mirrored, and native completion propagates back to the case record. An unpaid case, a non-operator, and an unknown case open nothing.

**Implementation:** `core_platform/native_journal.py` (new; its pre-existing orphaned manifest now names a real file) — `NativeNotaryJournal`: table `native_notarial_journal`, entries hash-chained in the GlassBoxAudit style (`previous_hash` genesis `'0' * 64`, entry hash = SHA-256 of the canonical entry body), `verify_chain()` recomputes every link; `record_completion()` reads the completed session row, the registered seal (latest by creation) and the completion evidence, stores digests rather than evidence contents, and inserts the JOURNAL row into `native_evidence_index` in the same step. `core_platform/native_notary.py` — `NativeNotarySessions.complete()` instantiates the journal and calls `record_completion(session_id, db=db)` inside its existing transaction after the completion update, so a completion that cannot be journaled rolls back and does not complete. `core_platform/authority_verifiers.py` (new) — `SessionIdentityVerifier` (reviewer and notary identity must both be OPERATOR accounts in `SessionAuth`'s own records), `CommissionAuthorityVerifier` (the notary's commission on record — state, commission id, legal name — must match the case's jurisdiction, and verification is delegated to `backend/commission_sync.verify_notary_commission` with an injected registry adapter; with no adapter it returns False), `ConfiguredProviderVerifier` (the mapped provider must be present in the owner's configured client set; Navu has no client anywhere in this repository and cannot verify; a service mapped to no provider has no external dependency to verify), and `create_authority_review()` composing `AuthorityReview` with the three. `core_platform/native_case_bridge.py` (new) — `CaseNativeBridge` over table `case_native_sessions` in the native chain database: `open_session()` requires the operator verifier, a known case, and `PaymentLedger.status(case_id) == 'PAID'`; service-to-method mapping RON → RON and MOBILE_NOTARY → E_NOTARY (the native chain is the platform's electronic session/evidence layer; the mobile act's records are kept in that same layer — mapping recorded here as a build decision, not silently assumed); `AUTHORIZED_DOCUMENT_SERVICE` has no notarial act and no mapping, and is denied. `refresh()` mirrors the session state onto the binding and, on completion, sets the case record's status to `NATIVE_SESSION_COMPLETED` (a state every existing consumer treats fail-closed: no further quote, checkout, review or provider submission is permitted against it). Wiring: `app/customer_app.py` gains the operator route `GET|POST /api/operator/appointments/<case_id>/native` alongside the provider workspace (GET returns the binding or null; POST `{"action": "open"}` opens a session and, like every live notarial operation, requires the owner's `ron_notarial` gate — absent or unapproved answers 503 `approval_required`); `deploy/deployment.py` — `RuntimeBindings.native_bridge`, passed with the same `ron_notarial` gate lambda as the provider workspace; `deploy/production_bindings.py` — builds `NativeNotarySessions` and `CaseNativeBridge` on `data/native_notary.db` with the factory's own cases, ledger, operator verifier and audit.

**Verification (exercised, not assumed):** all new and edited Python files compile; every touched file's `.pbd.json` payload hash regenerated and matching. Exercised in scratch databases and in-process drives (no repository tests added, restored or run): identity adapter verified an operator reviewer/notary pair from real `SessionAuth` accounts created through the setup/register flows and denied a customer reviewer, an unknown notary and a customer notary (4/4); commission adapter failed closed with no registry adapter, verified against official-shaped ACTIVE evidence at the documented `commission_sync` interface, and denied an unofficial source, a state mismatch and a missing commission record (5/5); provider adapter verified configured SignWell/BlueNotary clients, denied unconfigured providers, Navu and unknown provider names, and passed the no-provider-mapped service (6/6); `AuthorityReview` composed with the adapters recorded REVIEW_VERIFIED only when all three verified, and denied when the official adapter was absent and when the provider was Navu (3/3). The bridge carried a case from a webhook-settled ledger payment (real `PaymentLedger.record_event` path) to a native RON session, refused a non-operator, an unpaid case, an unknown case and a document-service case, reopened idempotently, and mapped a paid MOBILE_NOTARY case to an E_NOTARY session (9/9). The native chain was driven end to end — six authority decisions, document custody, verified signer signature, verified notary seal (commission honestly `False`), room consent/recording, recording manifest — and completion through `NativeNotarySessions.complete()` wrote exactly one journal entry in the same step: act kind, case/notary party binding, seal signature digest, four evidence digests, JOURNAL evidence indexed under the entry hash, chain verification returning the entry hash, idempotent re-record, and a tampered copy failing chain verification (13/13). Completion propagated through the bridge to the binding and to the case record's `NATIVE_SESSION_COMPLETED` status (3/3). The composed customer application served the native route: null binding when no bridge is wired, 503 `approval_required` without the gate, 201 with the gate, the binding on GET, and 403 for a non-operator (5/5); `RuntimeBindings` carries the bridge (1/1). Total: 51/51 checks. No live provider call, no real payment and no factual notarial act occurred or is claimed.

**Still owner-named / unfinished, recorded not smoothed over:** (a) **The official commission registry source.** `CommissionAuthorityVerifier` verifies nothing until the owner confirms and supplies a `registry_adapter` for `backend/commission_sync.py` validated against the official source for each state: Colorado — the Colorado Secretary of State's notary commission records (the contract's source id `CO_SOS`); Wisconsin — the Wisconsin Department of Financial Institutions' notary commission records (source id `WI_DFI`). The adapter must return exactly `{source, state, commission_id, name, status, verified_at, expires_at}` drawn from that official source; the module's own rule stands — no undocumented or speculative government endpoint is treated as authoritative, and none has been invented here. The owner must also place the notary's commission on record for the adapter (state, commission number, legal name as commissioned). Until both exist, human authority review cannot verify the authority leg and records no REVIEW_VERIFIED decision on that basis. (b) The live operator route for human authority review is not built: the adapters compose through `create_authority_review()`, but no route invokes a review and `AuthorityReview` still does not write the case record's status — recorded as the remaining named gap on the provider track's human gate. (c) Navu has no client in this repository, so MOBILE_NOTARY provider verification cannot pass until a Navu integration exists. (d) Everything named in the November 24, 2026 rollout entry remains owner-named and unchanged: the `ron_notarial` gate (0 of 9 approved), `APPROVED_RON_JURISDICTIONS` (empty by design), `SDS_OWNER_SETUP_TOKEN` and operator creation, provider keys in the designated OCI Vault secret, Stripe live mode, and deployment through the owner's gated path (a one-time deploy workflow covering stages 1–4 is prepared alongside the build record; stage 7 rides the same gated path when the owner approves a deploy).

## Corrective entry — independent audit of stage 7: provider submission now refuses a natively completed case — November 24, 2026

**Source:** The independent audit of stage 7 (owner-directed November 24, 2026; preserved at `docs/INDEPENDENT_AUDIT_STAGE7_2026-11-24.md`). The auditor — who built none of the work — confirmed five of the six audited claims in full (journal, verifier adapters, route gate, integrity at head, named gaps) and found **one discrepancy, recorded here rather than silently corrected over**: the stage 7 entry above states that the `NATIVE_SESSION_COMPLETED` case status is "a state every existing consumer treats fail-closed: no further quote, checkout, review or provider submission is permitted against it," and `core_platform/native_case_bridge.py`'s module docstring says the same. That sentence was true of quote, checkout, review and `cases.authorize_notarization`, but **not of provider submission**: `ProviderWorkflows.submit()` checked only the operator and the case's existence, and the auditor demonstrated it creating a provider request (state `CREATED`) against a natively completed case. The record overstated the code for one of the four consumers it named. Exposure at the time was bounded by the unapproved `ron_notarial` gate on the composed route, but once that gate is approved a provider request could have been opened against a case the native track already completed.

**Fix:** `core_platform/provider_workflows.py` — `ProviderWorkflows.submit()` now reads the case's current status immediately after authorization, before any payload preparation, provider client lookup or request record, and refuses a case in status `NATIVE_SESSION_COMPLETED` with `ProviderRequestConflict('Case status does not permit provider submission.')` — the module's own conflict exception (the composed route answers 409 `provider_request_conflict`, the same shape as checkout's state refusals), worded after the case registry's own status denial in `cases.authorize_notarization` ("Case status does not permit notarization authorization."). **Replay boundary, resolved fail-closed and recorded:** the refusal triggers on the case's status at submit time, so it also refuses an identical replay of a request created before completion. No new provider request may be created from a natively completed case by any submit call; the request history created before completion is not erased and remains readable through `records()` — submission is closed, history is not rewritten. With this fix, the stage 7 sentence quoted above and the bridge docstring now hold as written for all four named consumers; neither text was altered to fit the code — the code was brought to the record.

**Verification (exercised, not assumed):** the edited file compiles; its `.pbd.json` payload hash is regenerated and matching. The auditor's probe was reproduced in a scratch drive (case settled through the real `PaymentLedger.record_event` path → native RON session opened through the bridge → session completed → completion propagated to `NATIVE_SESSION_COMPLETED`): provider submission against that case now raises the refusal above, no provider client is called and no request row is created (previously the same probe created one). The replay boundary was exercised (a request created before completion submits `CREATED`; after completion the identical replay refuses, and `records()` still returns the earlier request). Regression on a non-completed case: a fresh submission creates, an identical replay returns the stored receipt without a second provider call, conflicting reuse still conflicts, an unconfigured provider still answers unavailable, and a non-operator is still denied. Quote, checkout, review and `authorize_notarization` refusals of the completed case are unchanged (18/18 exercise checks). No live provider call, no real payment and no factual notarial act occurred or is claimed. An independent retest of this correction follows separately; this entry records the fix, not its re-audit.

**Still owner-named / unfinished:** unchanged from the stage 7 entry above — the commission registry source (`CO_SOS` / `WI_DFI`) and the notary's commission on record, the live HTTP review route, the Navu client, the `ron_notarial` gate, `APPROVED_RON_JURISDICTIONS`, `SDS_OWNER_SETUP_TOKEN`, provider keys, Stripe live mode, and deployment through the owner's gated path (this correction rides the same approval).

## Independent audit of stage 7 preserved as a permanent record — November 24, 2026

**Permanent record:** the independent audit of stage 7 (owner-directed November 24, 2026) is preserved as an original corporate technical record at `docs/INDEPENDENT_AUDIT_STAGE7_2026-11-24.md`, standing alongside the rollout record (`docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md`) and the corrective entry above, which answers its one discrepancy.


## Independent retest of the stage 7 corrective fix preserved as a permanent record — November 24, 2026

**Permanent record:** the independent retest of the stage 7 corrective fix (owner-directed November 24, 2026) is preserved as an original corporate technical record at `docs/INDEPENDENT_RETEST_STAGE7_2026-11-24.md`. It stands alongside the rollout record (`docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md`), the independent audit (`docs/INDEPENDENT_AUDIT_STAGE7_2026-11-24.md`), and the Stage 7 corrective entry above; the audited provider-submission discrepancy is thereby CLOSED.

## Concurrency closure — the completed-case provider-submission guard is now ordered by construction, not by timing — November 24, 2026

**Source:** Owner direction, November 24, 2026: formally address the remaining theoretical concurrency window identified by the independent retest (preserved at `docs/INDEPENDENT_RETEST_STAGE7_2026-11-24.md`), to establish a stronger mathematical guarantee against future race conditions. The retest stated the prior guarantee precisely: duplicate creation was exactly-once (`BEGIN IMMEDIATE` plus the `(case_id, provider, request_id)` primary key), but the completion guard was a status read at `submit()` entry against the cases store — a different database from `provider_requests` — so the read and the insert were not one cross-store transaction, and a submit already past its entry read when completion committed finished as pre-completion history. That classification was honest and safe (such a request can never be re-submitted), but the ordering rested on when the read happened, not on a lock both paths contend on.

**Design analysis (mechanisms weighed against the actual store layout):** the case status lives in the cases store (`CaseRegistry.db_path`); request records live in `data/provider_requests.db`; the native completion path propagates to the case record in `CaseNativeBridge._propagate_completion`, which already executes its status flip under `BEGIN IMMEDIATE` on the cases store. (a) **A shared cross-store serialization point both paths contend on — CHOSEN**, instantiated on the cases store's own write lock: SQLite admits exactly one writer to a database file at a time, so if `submit()` holds `BEGIN IMMEDIATE` on the cases store across both its authoritative status re-read and the commit of its request-record insert, then either completion committed before the lock was taken (the re-read observes `NATIVE_SESSION_COMPLETED` and refuses) or completion's flip cannot commit until after the insert has committed (the creation is provably ordered before completion). No new file, table, column or cross-module coupling is introduced; the completion path required no change, because it already serializes on the same lock; and because the lock is enforced by the storage engine on the very file that holds the status, the guarantee binds every present and future writer of that store, not only the bridge. (b) **A single cross-store transaction via SQLite ATTACH — rejected:** locking and atomicity across attached databases depend on journal mode (under WAL, readers hold snapshots and do not block writers, which would silently reopen the window), and it would have required restructuring both modules' connection handling to obtain a weaker, configuration-dependent guarantee. (c) **A status/epoch mirror row maintained in the provider_requests store, written by the completion path and checked inside submit()'s own transaction — rejected:** it creates a second copy of the case status that can drift from the record of truth, forces the bridge to write into the provider store (new coupling in the wrong direction), and relocates the meaning of "completion committed" from the case record to the mirror's write — the guarantee would then cover the mirror, not the case.

**Change:** `core_platform/provider_workflows.py` — `ProviderWorkflows.submit()` only. The existing entry status read is unchanged (it still refuses a completed case before any payload preparation, provider client lookup or audit record, exactly as the corrective entry recorded). Immediately before the request-record insert transaction, submit now opens a connection to the cases store (resolved through the registry's `db_path`/`path` attribute), takes `BEGIN IMMEDIATE`, re-reads the case status under that lock and refuses with the same `ProviderRequestConflict('Case status does not permit provider submission.')` if it is `NATIVE_SESSION_COMPLETED`, executes the existing insert transaction (previous-record replay/conflict logic unchanged) and commits it while the lock is still held, then releases the lock before the provider client is called. Nothing else in the module changed; no native module changed, so native completion still journals inside its existing transaction, and a completion that cannot journal still rolls back.

**Verification (exercised, not assumed):** the edited file compiles; its `.pbd.json` payload hash is regenerated and matching. An adversarial harness was written from the claims and executed against the real modules in scratch databases (no repository tests added, restored or run; no live provider call — a counting provider double stood in): regressions 12/12 (fresh submit CREATED; identical replay returns the stored receipt with no second provider call; conflicting reuse conflicts; unconfigured provider unavailable; non-operator denied; submit after completion refuses with zero provider calls and zero rows; replay of a pre-completion request after completion refuses while `records()` still returns the history; `authorize_notarization`, authority review, and the quote/checkout verifiers still refuse the completed case; the journal chain verifies with exactly one entry per completion across two completions). Deterministic lock choreography 4/4: with the provider store externally locked so the submit was provably inside its critical section holding the cases-store guard, a concurrent completion propagation could not commit (the case status remained unflipped for the whole observation window); once the submit's insert committed and the guard released, the flip landed, and a replay then refused — and conversely, with a completion transaction in progress holding the cases store while it flipped the status, a submit blocked at the guard and, once the flip committed, refused with zero rows and zero provider calls. Barrier-synchronized races, with a violation defined as a `provider_requests` row whose creation committed after the case's completion committed: 40 full-chain submit-vs-completion trials (34 ordered submit-first, 6 completion-first) and 40 tight submit-vs-propagation trials (37 submit-first, 3 completion-first) — every trial ended in exactly one of the two legitimate outcomes, zero violations; 12 duplicate-submit races each produced exactly one row and exactly one provider call, the loser taking either the designed conflict (it observed the winner's SUBMITTING row) or the stored receipt (it observed the finished CREATED row — the pre-existing sequential-replay semantics). Total: 19/19 harness checks.

**Residual limitations, stated exactly:** (1) The guarantee orders request-record *creation* against the case-status flip. The provider's external call still happens after creation commits, so a request created legitimately before completion may still be in flight at the provider when completion lands; it stands as pre-completion history, exactly as the corrective entry recorded — no new request can be created, and none can be re-submitted, after completion. (2) The guard adds one bounded wait: if another writer holds the cases store's write lock beyond the connection's 10-second busy timeout, submit raises `sqlite3.OperationalError` instead of creating anything — fail-closed (no row, no provider call), but a named failure mode under pathological lock contention; the guard's critical section itself is one status read plus one insert commit. (3) A case-registry object exposing neither `db_path` nor `path` now fails closed with `ProviderUnavailable('case_store_unavailable')` rather than creating unguarded; the one production construction passes `CaseRegistry`, which exposes both. (4) Verification ran in-process against scratch databases; this closure is not deployed — it rides the owner's gated deploy path like the corrective fix before it. An independent retest of this closure follows separately; this entry records the change, not its re-audit.

**Still owner-named / unfinished:** unchanged — the gates remain 0 of 9 approved and `APPROVED_RON_JURISDICTIONS` remains empty; the commission registry source (`CO_SOS` / `WI_DFI`) and the notary's commission on record, the live HTTP review route, the Navu client, `SDS_OWNER_SETUP_TOKEN`, provider keys, and Stripe live mode all remain as recorded in the stage 7 entry above.

## RON provider readiness map retained as an official internal reference — November 24, 2026

**Official internal reference:** the RON provider readiness map (owner-ruled November 24, 2026) is preserved at `docs/RON_PROVIDER_READINESS_2026-11-24.md` and stands as the official internal development and compliance reference for Sanders Legal Helpers LLC's path to recognition as an approved RON technology provider in Colorado and Wisconsin; every filing, certification, and binding representation in it remains the owner's alone.

## Independent retest of the concurrency closure preserved as a permanent record — November 24, 2026

**Permanent record:** the independent retest of the concurrency closure (November 24, 2026) is preserved as an original corporate technical record at `docs/INDEPENDENT_RETEST_CONCURRENCY_2026-11-24.md`. It stands alongside the independent audit of stage 7 (`docs/INDEPENDENT_AUDIT_STAGE7_2026-11-24.md`), the independent retest of the stage 7 corrective fix (`docs/INDEPENDENT_RETEST_STAGE7_2026-11-24.md`), and the concurrency-closure entry above; the concurrency closure is independently CONFIRMED (33/33 checks, 110 race trials, zero violations).

## Phase A remediation — the realtime/media access paths are closed (F-1, F-2, F-5, F-6, F-11) — November 24, 2026

**Source:** The owner's P0 Corporate Headquarters directive (November 24, 2026) and its Phase 1 inventory (`inventory-and-plan.md`, findings F-1, F-2, F-5, F-6, F-11; §4 Phase A). F-1 was proven by execution in that inventory: `deploy/deployment.py` computed `RealtimeConfig.from_env().provider()` — calling a `@property` as a method — the `TypeError` was swallowed, the provider read as `'none'`, and the `voice_video_provider` gate check never ran, so with provider keys set an unauthenticated caller could mint a valid LiveKit JWT while the gate stood unapproved.

**Change (the gate was NOT approved; the existing gate now enforces):** enforcement moved to the module that mints, so no router composition can bypass it and every denial is recorded. `core_platform/realtime_api.py` — `create_realtime_app` now takes injected `authenticate`, `audit`, `gate_approved` and `allowed_origins` and guards `POST /api/realtime/room` and `POST /api/realtime/token` in the order gate → session → origin → identity binding: when a provider is configured, an unapproved (or unwired, or erroring) gate evaluation denies 503 `approval_required`, fail closed; issuance requires an authenticated platform session (401 `sign_in_required`); a POST from an origin outside the site set is refused 403 `origin_denied`; the token's identity is the session's account username — a body asserting a different identity is refused 403 `identity_mismatch`, an omitted identity is bound to the session. Every issuance decision writes a Glass-Box receipt (`REALTIME_TOKEN_ISSUED` / `REALTIME_TOKEN_DENIED` / `REALTIME_ROOM_CREATED` / `REALTIME_ROOM_DENIED`, with room, identity, gate and reason); a grant whose receipt cannot be written is not issued (503 `audit_unavailable`) — no record, no token. The honest `not_configured` answer for an authenticated caller with no provider keys is preserved. `deploy/deployment.py` — the defective router gate block is removed (its history is recorded in a comment at the branch); the voice/realtime apps are now built lazily per application instance, wired with that application's session verifier, the bindings' audit chain and the `voice_video_provider` gate check; `RuntimeBindings` gains an `audit` field and `deploy/production_bindings.py` passes the production `GlassBoxAudit` into it. `core_platform/voice_api.py` — `POST /api/voice/transcribe` and `POST /api/voice/speak` require the same session + origin control (F-5); `GET /api/voice/status` stays public (backend names only). `core_platform/session_auth.py` — issuing a session now invalidates every prior session for the account (rotation at login/register/setup, F-6), and the owner setup token is compared with `hmac.compare_digest` (F-6). `web/video.js` — the page no longer asserts an identity (`'user-' + room` is gone); it sends the room only and surfaces the 401 sign-in requirement.

**Verification (exercised, not assumed):** every edited file compiles; each `.pbd.json` payload hash is regenerated and matching. A purpose-built drive (60 checks, all passing) exercised: the inventory's own F-1 probe re-run against the fixed composition — `TOKEN_UNAUTH 503 approval_required, token_minted=False` (before: 200 with a minted JWT); the composed application with production-style bindings — authenticated and anonymous token/room requests alike refused at the unapproved gate, with the denials present on the Glass-Box chain and the chain verifying; voice transcribe/speak answering 401 signed out and the honest backend 503 signed in; login rotation (the prior session answers 401, the new session works); the full regression surface unchanged — healthz, storefront, portal, intake 201, operator queue 200/403/401 shapes, operator quote 201, checkout 409 with an unavailable Stripe client, and the provider/native operator POSTs still answering 503 `approval_required` on the `ron_notarial` gate. At module level with an injected approved gate (a stub standing in for the owner's future approval, so the grant path itself is exercised): authenticated issuance mints a token whose `sub` is the session account and whose grant is scoped to the one room; an asserted foreign identity is refused; a foreign origin is refused; a gate callable that raises, an unwired gate, and a config whose provider evaluation raises each deny 503 with no token; a grant against a broken audit store is not issued. All 9 approval gates remain UNAPPROVED and `APPROVED_RON_JURISDICTIONS` remains empty (verified by read-back at the end of the drive).

**Residual limitations, stated exactly:** (1) Token grants (publish/subscribe/data) keep the LiveKit client's existing defaults: per-participant grant scoping belongs to the Phase B rooms service, where participant roles exist — no grant policy was invented here. (2) The Daedalus voice-turn route (`POST /api/voice/turn`) is unchanged: it performs no work while its runtime is unwired (503 `daedalus_runtime_not_configured`); when a runtime is wired it must receive the same session binding. (3) Finding F-7 (signalling validation checks token shape, not authenticity; the ledger issuer it defers to does not exist) is Phase A item 5 of the inventory plan and was outside this change's enumerated scope; it stands open. (4) Session token lifetime (7 days), the absence of MFA/2FA, and operator step-up are unchanged by design: they are behavior/policy changes recorded here as named residuals for the owner's ruling (inventory F-6), not silently imposed. (5) Verified in-process against scratch stores and fictitious keys; not deployed — this change rides the owner's gated deploy path, and whether any `LIVEKIT_*` keys are set on the production instance remains as the inventory left it: unverified.

**Still owner-named / unfinished:** all 9 gates remain the owner's to approve by name (`voice_video_provider` included — this change makes it enforce, it does not approve it); `APPROVED_RON_JURISDICTIONS` remains empty; the Section 22 incorporation ruling and the LiveKit identity-charset/TTL decision (F-12) remain the owner's; Phases B–F of the inventory plan proceed under the same directive.

## Independent retest of the Phase A remediation preserved as a permanent record — November 24, 2026

**Permanent record:** the independent retest of the Phase A remediation (November 24, 2026) is preserved as original corporate technical records at `docs/INDEPENDENT_RETEST_PHASE_A_2026-11-24.md` (construction and record review) and `docs/INDEPENDENT_RETEST_PHASE_A_DYNAMIC_2026-11-24.md` (dynamic completion pass). They stand alongside the Phase A remediation entry above. Phase A is confirmed by construction AND by execution — 55 dynamic checks executed against the real composed app at the Phase A head, no discrepancy — and the first retest's own residuals (R-1–R-4) stand as recorded in `docs/INDEPENDENT_RETEST_PHASE_A_2026-11-24.md`.

## Phase B — the commercial meeting rooms core (control plane) — November 24, 2026

**Source:** The owner's P0 Corporate Headquarters directive (November 24, 2026) and its Phase 1 inventory (`inventory-and-plan.md`, finding F-3 — no meeting-room service existed — and §4 Phase B), against the requirements baseline of MASTER Section 22, "Secure Virtual Meeting Rooms and Conference Capabilities" (a DRAFT expansion; its incorporation into the authoritative MASTER remains the owner's ruling under §22.15 and is NOT effected by this entry). This phase builds the rooms CONTROL PLANE only: the media plane stays behind the existing `voice_video_provider` gate, unapproved and untouched, exactly as Phase A left it.

**Change:** `core_platform/rooms.py` (new) — `RoomService`, a durable rooms store (`data/rooms.db` in production wiring) following the codebase's store idioms (SQLite, `BEGIN IMMEDIATE` write transactions, busy timeout, Glass-Box audit adapter required at construction — a service without a working audit sink refuses to exist). The model implements the commercial subset of Section 22: room types CONSULTATION, COMMERCIAL_TRANSACTION, CONFERENCE, INTERNAL_COLLABORATION (§22.2); participant roles HOST, PARTICIPANT, INTERPRETER, WITNESS, OBSERVER, SUPPORT (§22.4 — INTERPRETER is a first-class role in the model now; captions/ASL presentation layers are Phase D and are not faked here); the §22.3 lifecycle DRAFT → SCHEDULED → WAITING_ROOM → ACTIVE → ENDED → ARCHIVED plus CANCELLED, LOCKED, SUSPENDED and EVIDENCE_HOLD, where every transition is an explicit, checked operation that fails closed on an invalid move, is serialized under `BEGIN IMMEDIATE` with state re-validated inside the lock, and writes its Glass-Box receipt inside the same critical section — a transition whose receipt cannot be written does not occur (no record, no action). Participants are bound to platform accounts, either added by the host/operator or admitted by accepting a host-issued, time-limited invitation recorded on the room; there are no self-asserted identities (Phase A's binding rule). Consultation and transaction rooms may bind to a customer case at creation (validated against the cases store; a non-operator creator must be the case's requester; the room inherits the case's jurisdiction); document and payment actions stay with the existing case/checkout flows — the room references the case, it does not duplicate or bypass them. Recording consent is captured per participant (each account records only its own decision, against a recording-notice version identifier) and a room's recording state can become AUTHORIZED only when every admitted participant holds a current GRANTED consent and the room's recording policy permits it; the media plane itself is not built or activated. Each room record carries a retention policy (category COMMERCIAL_MEETING_RECORD, a day count, its basis, the room's jurisdiction) and, once ARCHIVED, a computed deletion-eligibility instant. `app/customer_app.py` — authenticated routes alongside the existing families: `GET|POST /api/rooms`, `GET /api/rooms/<id>`, and POST routes for transition, participants (add/remove), invites (issue/accept/revoke), consent and recording authorization, with the platform's existing shapes (401 signed out, 403 wrong origin, 404 for a room the caller cannot see — participant isolation is indistinguishable from nonexistence — 403 `room_forbidden`, 400 `room_denied`, 503 `rooms_unavailable` when unwired). `deploy/deployment.py` — `RuntimeBindings` gains a `rooms` field, passed into the customer app; `/api/rooms` paths join the customer-API host routing. `deploy/production_bindings.py` — builds `RoomService` on `data/rooms.db` bound to the production cases store, the session operator verifier and the production audit chain. The regulated boundary is absolute: the NOTARIAL meeting type and the NOTARY participant role are deliberately ABSENT from this model (notary authority is verified independently of platform role, §22.4, and notarial sessions belong to the gated regulated track, §22.9); nothing in this change touches the RON/native/provider flows or their gates.

**Design decisions made in this build, each named:** (1) Invitations are issued only to platform account identities — no guest links and no self-asserted names (basis: §22.5's authenticated, time-limited invitations, and Phase A's session-binding rule). (2) Consent records bind the notice by a version identifier (`notice_version`); the notice text and its presentation belong to the client surface and to Phase D's accessibility/language work — the service records which notice version each participant decided against, it does not invent notice copy. (3) A room recording policy of REQUIRED still cannot override a participant's refusal in the commercial track (basis: §22.8 — no universal recording or retention rule is presumed, and policies may prohibit recording). (4) Any participant-set change while recording is AUTHORIZED revokes the authorization in the same transaction: the unanimous consent on record described a different room than the one that now exists, so authorization must be re-earned. (5) The retention default of 365 days is recorded with basis PLATFORM_DEFAULT — a platform policy default, NOT a statutory period; the 10-year Colorado figure in the RON provider readiness map belongs to the regulated RON track and was deliberately NOT imported into commercial rooms (basis: §22.8). A host may set 1–3650 days at creation (basis HOST_POLICY); jurisdiction is recorded on the room for future jurisdiction schedules. (6) Case binding happens at creation only. (7) Resuming a SUSPENDED room lands in WAITING_ROOM, never directly in ACTIVE (basis: §22.3 — rejoin/transfer/resume require new authorization checks). (8) EVIDENCE_HOLD and its release are operator-only and freeze every other transition while held.

**Verification (exercised, not assumed):** every new/edited file compiles; each `.pbd.json` payload hash is regenerated and matching. Two purpose-built drives (102 checks, all passing) exercised the real modules and the composed application with production-style bindings: service level (62) — the full lifecycle driven through every state incl. lock/unlock returning to the pre-lock state, resume landing in WAITING_ROOM, invalid transitions refusing (activate from DRAFT, archive from ACTIVE, anything from ARCHIVED, schedule without a start), evidence hold operator-only and freezing transitions, participant/role enforcement (second HOST refused, participant cannot transition or add, non-participant detail/list indistinguishable from nonexistence, removed participant loses visibility, self-leave), invitations (wrong-account accept refused, expired invitation rejected and marked, revoked invitation unusable, re-accept refused), case binding (own case binds with jurisdiction inherited, another customer's case refused, unknown case refused, operator may bind any), consent-before-recording (authorization refused with missing consent, with the host's consent alone, under a PROHIBITED policy, and in DRAFT; granted when every admitted participant consented; a withdrawal revokes authorization in the same step; an operator cannot consent on participants' behalf), audit failure (a create and a transition against a broken audit sink raise and change no state; the real chain verifies), and barrier-synchronized duplicate open/end races each succeeding exactly once; composed application (40) — auth setup/register, signed-out 401 and wrong-origin 403 on the rooms routes, room create/list/detail/transition/participants/invites/consent/recording driven end to end over WSGI (including the NOTARIAL type refused at the route and end-of-meeting revoking recording authorization), rooms answering 503 `rooms_unavailable` in an unwired composition, and the full regression surface unchanged: healthz, storefront, intake 201, operator queue 200/403/401 shapes, operator quote 201, checkout 409 with an unavailable Stripe client, provider and native POSTs answering 503 `approval_required` on the `ron_notarial` gate, the realtime token POST answering 503 `approval_required` on the unapproved `voice_video_provider` gate with fictitious provider keys set, and voice answering 401 signed out. All 9 approval gates remain UNAPPROVED and `APPROVED_RON_JURISDICTIONS` remains empty (verified by read-back).

**Residual limitations, stated exactly:** (1) No-record-no-action holds by construction for every failure before the rooms-store commit; one narrow storage-failure class remains: if the audit write succeeds and the rooms-store commit itself then fails (disk-level failure), a receipt exists for a transition that did not commit — the receipt is evidence of the attempt, and the room state is unchanged. (2) Host transfer is not built: the creating host is permanent for a room's life in this phase (a transfer operation with its own authorization checks is future work, not silently absent). (3) Case rebinding after creation is not built (decision 6 above). (4) No deletion operation is built: retention is policy, recording and eligibility computation only — actual disposition under a retention schedule is future, separately gated work. (5) Realtime token grants are still not scoped to room participants: Phase A's residual (1) carries forward — participant roles now exist in the rooms model, but binding media issuance to room membership is Phase C, where the media plane's activation is decided; rooms mint no tokens in this phase. (6) Verified in-process against scratch stores and fictitious keys; not deployed — this change rides the owner's gated deploy path.

**Still owner-named / unfinished:** the Section 22 incorporation ruling (§22.15) and the F-12 LiveKit identity-charset/TTL decision remain the owner's; all 9 gates remain the owner's to approve by name (`voice_video_provider` included — rooms are governed objects while media stays gated); `SDS_OWNER_SETUP_TOKEN`, provider keys and Stripe live mode remain as recorded in the Phase A entry; Phases C–F of the inventory plan proceed under the same directive, and an independent security test of this phase follows separately (Phase F pattern) — this entry records the build, not its re-audit.

## Phase B corrective fix — recording-authorization edges (D-1, D-2, D-3) — November 24, 2026

**Source:** The independent security test of the Phase B build (388 executed checks against head `1cd6915`, including 120 barrier-synchronized race trials; report: *Independent Security Test — Phase B (Commercial Rooms Core)*). The test confirmed the build's identity binding, participant isolation, lifecycle state machine, consent unanimity, case-binding ownership, no-record-no-action and exactly-once concurrency, and found three discrepancies at the recording authorization's edges. The original Phase B entry above is NOT edited; this entry names the test, quotes the discrepancies, and states the corrections. The standard was not lowered — the code was corrected to the documented design, as with the Stage 7 corrective fix.

**The discrepancies, as recorded by the test:** D-1 (moderate) — "recording authorization survives LOCKED and SUSPENDED — and therefore resume": `transition()` revoked recording authorization only when the target was ENDED, CANCELLED, ARCHIVED or EVIDENCE_HOLD, and the test reproduced the authorization still in force after `lock`, after `suspend`, and after `resume` into WAITING_ROOM — contradicting decision (7) above, which justifies resume landing in WAITING_ROOM precisely because resumption "requires a fresh authorization pass". D-2 (moderate) — "notice_version is recorded but never enforced — mismatched/superseded notices authorize": decision (2) above presents the notice-version binding as the mechanism tying consent to the notice actually presented, but as built no canonical version existed anywhere in the service and `authorize_recording` checked only that each current decision equalled GRANTED; the test authorized recording on consents granted under two different notice versions ("v1-old" and "v2-new"). D-3 (low) — "case-existence enumeration oracle at room creation": the refusal for another customer's case ("Case cannot be bound by this actor") was distinguishable from the refusal for a nonexistent case ("Unknown case"), letting any authenticated account confirm which case identities exist — against the isolation discipline this same build applies to rooms, where invisible and nonexistent are deliberately indistinguishable.

**Corrections (`core_platform/rooms.py`; `app/customer_app.py` gains one create field):** (D-1) The rule is now stated from the state machine itself: recording authorization may exist only while the room is in WAITING_ROOM or ACTIVE, and `transition()` revokes it — receipted `ROOM_RECORDING_REVOKED` inside the same transaction — on ANY transition landing anywhere else (lock, suspend, end, cancel, archive, hold, schedule). Unlock and resume therefore land with the authorization revoked, and a fresh authorization pass re-earns it; the WAITING_ROOM→ACTIVE step is not a revocation, so a live authorization survives `activate` as before. (D-2) The version binding is now a check, not a label. Each room records a canonical consent notice version at creation — the create input `consent_notice_version`, defaulting to the platform constant `DEFAULT_CONSENT_NOTICE_VERSION` — stored on the room record (a new `consent_notice_version` column; a store created before this fix is migrated at construction, and its pre-existing rooms fail closed because no recorded consent can match a NULL canonical version), carried on the `ROOM_CREATED` and `ROOM_RECORDING_AUTHORIZED` receipts, and exposed in the room view so participants can see the version they are deciding against. `authorize_recording` counts a participant's current consent only when its decision is GRANTED **and** its `notice_version` equals the room's canonical version. Consents recorded against any other version remain on the append-only record untouched — they simply do not count — so if a room's canonical version is ever advanced, prior consents stop counting by re-derivation at authorization time, never by deletion or rewriting (no advance operation is built in this fix). `record_consent` also revokes a standing authorization in the same transaction whenever the actor's newly recorded consent stops counting (a refusal, a withdrawal, or a grant recorded against a non-canonical version), closing the path where an authorization outlived the consent record it rested on. The create route's accepted field set gains `consent_notice_version`. (D-3) `create_room` now raises the single caller-facing denial `RoomDenied('Case cannot be bound')` for both a nonexistent case and a case the actor may not bind; the two responses are identical in status and detail at the service level and byte-identical over WSGI. No denial receipt is written for either, as before.

**Not decided here:** The test's residual R-A — consent may still be recorded, refused and withdrawn while a room is under EVIDENCE_HOLD, and a withdrawal under hold runs the recording-revocation bookkeeping inside the frozen room — stays named as an OPEN design question for the owner; this fix does not change consent-under-hold behavior in either direction. The test's hygiene notes R-B (duplicate pending invitations linger) and R-C (host-removal error precedence) were not touched; no D-fix forced them.

**Verification (the fixer's own executed drives, 74 checks, all passing):** the tester's three reproductions now refuse correctly — lock and suspend strip the authorization with `room_locked`/`room_suspended` revocation receipts on the chain, resume lands in WAITING_ROOM with the authorization revoked, and a fresh pass re-authorizes in WAITING_ROOM and ACTIVE; mixed-version consents cannot authorize at service or route level, unanimous canonical-version consent authorizes, a re-grant under a non-canonical version revokes a standing authorization in the same step, the append-only consent history is untouched (all versions remain on record), and a legacy store without the new column migrates and fails closed; both case-binding denials are byte-identical over WSGI while own-case binding (jurisdiction inherited) and operator binding still work. The full lifecycle still drives (schedule/open/activate/lock/unlock/suspend/resume/end/archive/cancel/hold/release, invalid transitions refusing, PROHIBITED policy refusing despite consent, no consent on another's behalf), and concurrency spot-races are unchanged (duplicate open and duplicate end each succeed exactly once; the authorize-vs-withdraw invariant — AUTHORIZED implies every admitted participant holds a current counting consent — holds across 40 barrier-synchronized trials). The composed-application regression is unchanged: healthz, storefront and portal 200, intake 201, operator queue 200/403/401, operator quote 201, checkout 409 `checkout_unavailable`, provider and native POSTs 503 `approval_required` on `ron_notarial`, realtime token 503 `approval_required` with fictitious LiveKit keys set, voice 401 signed out, and the audit chain verifies end to end. All 9 approval gates remain UNAPPROVED and `APPROVED_RON_JURISDICTIONS` remains empty (verified by read-back at the new head). Not deployed — this fix rides the owner's gated deploy path with the Phase B build.

**Permanent record:** the independent security test of the Phase B build and the independent retest of its corrective fix (November 24, 2026) are preserved as original corporate technical records at `docs/INDEPENDENT_SECURITY_TEST_PHASE_B_2026-11-24.md` (388 executed checks) and `docs/INDEPENDENT_RETEST_PHASE_B_2026-11-24.md` (96 executed checks). They stand alongside the Phase B build entry and the Phase B corrective entry above. The test found no critical bypass and three discrepancies — D-1 (recording authorization survived LOCKED and SUSPENDED, and therefore resume), D-2 (the consent `notice_version` was recorded but never enforced), and D-3 (a case-existence enumeration oracle in the room-creation denial wording) — and the retest confirms all three CLOSED by execution against the corrected head (96/96). The test's residual R-A — consent may be recorded, refused and withdrawn while a room is under EVIDENCE_HOLD — remains an OPEN owner decision, undecided in either direction, exactly as recorded in the corrective entry above.

## Phase B residual remediation — duplicate invitations (R-B), removal error shape (R-C), Glass-Box reconciliation of room evidence — November 24, 2026

**Source:** The owner's recommended development sequence (November 24, 2026, 06:22 MST — correct the discrepancies, address the additional residual findings, reconcile attempted and committed Glass-Box audit records) and the independent Phase B security test's residuals R-B and R-C, together with the builder's residual #1 (a Glass-Box receipt can exist for a rooms action whose store commit then failed at the storage layer).

**R-B — duplicate pending invitations (`core_platform/rooms.py`, `accept_invite`):** when an invitation for a (room, invitee) is ACCEPTED, every other PENDING invitation for the same room and invitee is closed in the same transaction. **Mechanism choice, named:** the closed invitations take the terminal status **SUPERSEDED** — distinct from EXPIRED (its lifetime ran out) and REVOKED (the host withdrew it), because neither describes an invitation displaced by the invitee's own acceptance — and each closure is receipted as `ROOM_INVITE_SUPERSEDED` naming the closed invitation and the accepted invitation that superseded it (`superseded_by`). A superseded invitation can never be accepted. Hygiene only: no caller gains any new power, and no other invitation path changes.

**R-C — removal error precedence (`core_platform/rooms.py`, `remove_participant`):** the authority check (may this actor remove anyone at all) now runs BEFORE the host-removal check. An actor with no removal authority receives the identical `RoomForbidden` refusal whether the target is the host, another participant, or no participant at all, so the refusal's shape no longer reveals that the target is the host. Authorized actors see unchanged behavior: the host still cannot be removed (by an operator, or by the host themself), self-leave still works, and fail-closed behavior is unchanged throughout — only the ordering, and the one bit of information it leaked, changed.

**Glass-Box reconciliation (`core_platform/rooms_reconciliation.py`, new):** `reconcile_room_evidence(rooms_database, audit_database)` / `RoomEvidenceReconciler` — a READ-ONLY reconciliation of the audit chain's room receipts against committed room state. Both stores are opened through SQLite `mode=ro` connections, so the routine cannot write to either store even by accident. It verifies the chain's hash linkage, then reports, with the specific receipt identifiers (chain sequence and block hash): receipts whose referenced room, transition, participant, invitation or consent has no committed counterpart (the attempted-but-uncommitted orphan class of residual #1 — transition orphans are identified by replaying each room's transition receipts from DRAFT against the committed state); committed rooms, invitations and consents that lack their expected receipts; recording-state/receipt divergences; and chain-validity failures. The report is structured data (counts plus the individual orphaned/missing/divergent entries). It performs NO repair: per the Glass Box strengthening program's hard boundary, discrepancies are surfaced for investigation, never silently fixed — an orphaned receipt is evidence of an attempt and is preserved as such. No new route is exposed: the codebase has no established operator-diagnostic route pattern for this class of check, so the callable and this description are the shipped surface.

**Not decided here:** residual R-A — consent may still be recorded, refused and withdrawn while a room is under EVIDENCE_HOLD — remains OPEN for the owner's ruling and is untouched by this remediation, as are the semantics of the D-1/D-2/D-3 corrective fix.

**Verification (the remediator's own executed drives, 77 checks, all passing):** service level 49/49 — R-B: three duplicate pending invites issued, one accepted, the other two SUPERSEDED with two `ROOM_INVITE_SUPERSEDED` receipts naming the accepted invite, a superseded invite refuses acceptance, a single-invite acceptance produces no supersede receipts, chain verifies; R-C: an unauthorized participant's removal attempts against the host, a peer, and a nonexistent target return the identical type and message, while host self-removal and operator-versus-host still refuse as the host, and self-leave and host removal of a member still work; reconciliation: a clean two-room history (lifecycle, consent, authorization, superseded duplicates) reports ok with zero orphans/missing/divergences and the reconciler provably writes nothing (store hashes and mtimes identical across a run); the residual-#1 fault injection (real audit write, rooms commit forced to fail) on a transition and on a creation each produces exactly one orphan and the reconciler flags precisely that receipt while the chain still verifies; a semantically tampered receipt body is flagged as a chain failure; a deleted consent receipt is flagged as a missing receipt with the chain still valid; lifecycle regression incl. the D-1 (lock strips authorization) and D-2 (mixed notice versions refuse) invariants. Composed application 28/28 — healthz/storefront/portal, operator setup and customer registration, intake 201, operator queue 200/403, quote 201, checkout 409 `checkout_unavailable`, rooms driven end-to-end through the routes with R-B (duplicate invite SUPERSEDED in the room view) and R-C (unauthorized removal of host vs peer returns indistinguishable 403 bodies) verified at route level, provider and native POSTs 503 `approval_required`, realtime token 503 `approval_required` with fictitious LiveKit keys, voice 401 signed-out, unwired rooms 503 `rooms_unavailable`. All 9 approval gates remain UNAPPROVED and `APPROVED_RON_JURISDICTIONS` remains empty. Not deployed.

## Full-suite independent re-run of Phase B preserved as a permanent record — November 24, 2026

**Permanent record:** the full-suite independent re-run of Phase B (owner sequence item 4, November 24, 2026) is preserved as an original corporate technical record at `docs/INDEPENDENT_FULL_SUITE_RERUN_PHASE_B_2026-11-24.md`. It stands alongside the Phase B build entry, the Phase B corrective entry, the Phase B residual remediation entry, and the preserved independent security test (`docs/INDEPENDENT_SECURITY_TEST_PHASE_B_2026-11-24.md`) and retest (`docs/INDEPENDENT_RETEST_PHASE_B_2026-11-24.md`) above. The re-run executed 476 checks and race trials (346 discrete checks + 130 barrier-synchronized race trials) against head `5c6db342`: D-1, D-2 and D-3 are confirmed still CLOSED under fresh execution, and the residual remediation (R-B superseded invitations, R-C removal indistinguishability, and the Glass-Box rooms reconciler) is independently verified as recorded. The re-run records one new discrepancy — D-4 (LOW): consent visibility in the room view is keyed to the category literal rather than the viewer's identity, so a participant cannot see their own consent state and the account named `participant` has its consent state exposed to co-participants; it has no authorization impact, and its corrective fix follows the standing pattern (correct the code to the documented standard, independent retest, preservation). Residual R-A remains an OPEN owner decision, as recorded above.
