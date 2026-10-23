# Original-specification conformance audit

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

