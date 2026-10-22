# Original-specification conformance audit

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
