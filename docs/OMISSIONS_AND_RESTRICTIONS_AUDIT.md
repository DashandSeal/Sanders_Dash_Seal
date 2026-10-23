# Owner-directed audit — October 22, 2026

## October 23 operational-runtime increment

Latest observed Oracle deployment: authentication and Plan succeeded in run
40010092156. Installation then stopped because our validator treated ordinary
versioned-installer replacement as protected-data destruction. This increment
corrects that false rejection for the exact versioned release objects, retaining
original customer-data/infrastructure protections. The older authentication
failure below remains historical and is not the current diagnosis.

The native runtime now loads all ten laws. Durable read-only supervision observes
the twelve IT-agent roles; a recurring service is wired into the existing Oracle
installer. An operator-only status API records real observations, unknown states,
incidents and observed recoveries. This completes the local observation cycle,
not all independently operated synthetic-AI services. Inference, independent
signing/custody, actual governed repairs, model learning, external immutable
anchoring and live Oracle verification remain open in the inventory below.
See `AI_OPERATIONAL_RUNTIME.md` for exact behavior and scope.

Roosevelt Sanders is the platform owner and decision-maker. Assistant-authored
release policies do not amend the owner's MASTER design. This report distinguishes
unfinished implementation, external configuration and removed assistant controls.

## Restrictions removed in this correction

| Previously introduced control | Correction |
| --- | --- |
| Draft PR and development branch kept the code away from main | PR #3 was merged; subsequent owner-directed corrections are published to main. |
| Separate manual production-release workflow required an artifact path, release-evidence string and production environment | Replaced with a direct call to the actual GitOps deployment workflow, with no extra approval fields or environment. |
| Readiness audit always emitted BLOCKED and represented every external capability as failed | Source-only audit is observation-only. Unobserved external capabilities are unknown, not automatic failures or installation vetoes. |
| Every unsigned source manifest was labeled UNSIGNED_DEPLOYMENT_BLOCKED | Relabeled UNSIGNED_SOURCE_MANIFEST; signatures remain honestly unsigned. No fictitious signing or blanket install ban. |
| CI required the artificial blocked-status label | Removed the label requirement; actual source hashes remain checked. |
| Plan checker required assistant-selected resource names and rejected all compute/new-node profiles | Removed resource-name/type allowlist and existing-host-only restriction. The actual existing/new A1 stack profile is preserved automatically. |
| New-node GitOps updates could wait for a cloud-init rerun that never occurs | GitOps now completes Apply, dispatches the exact-release installer through Oracle Agent, then waits for execution. Private installer outputs exist for both profiles. |
| Generic deployment error concealed missing Actions secrets | Missing credential names are reported without their values. |
| Gunicorn integration silently skipped when the package was missing | Dependency skip removed; full-suite CI installs requirements-server.txt; actual HTTP/SIGTERM test runs. |

No custom release-authorizer, runtime-factory requirement or self-hosted runner
requirement is present in the active automatic deployment workflow.

## What remains unfinished or not connected

| Item | Actual state |
| --- | --- |
| GitHub-to-Oracle authentication | First main deployment run received empty OCI_TENANCY_OCID, OCI_USER_OCID, OCI_FINGERPRINT, OCI_PRIVATE_KEY and OCI_STACK_OCID values. No Oracle provisioning or installation completed. |
| Stripe runtime custody | Live account has charges/payouts enabled and webhook we_1UTPrCAgIE87JukG9yBNbUB4 is enabled at the canonical /stripe/webhook URL. The signing secret has not been installed in Oracle Vault; the application live API credential is not available in this workspace. |
| Complete live payment workflow | Local component integration passes with a synthetic Stripe client. No real platform Checkout-to-webhook-to-ledger round trip completed on Oracle. |
| DNS and HTTPS | The source includes certificate issuance/renewal and routing, but no registrar control, DNS cutover or live application certificate was completed here. |
| Owner account setup | First boot generates a one-use root-only setup secret. Delivery of that secret to the owner without host access is not automated in this build. |
| SignWell and BlueNotary execution | Operator workspace and native WSGI now create SignWell template signing documents and BlueNotary RON sessions, with persistent request references and duplicate protection. Actual credentials, provider completion callbacks, evidence retrieval, and human notarial execution are not connected live. A SignWell signing request is not itself a completed eNotarization. |
| Independent AI roles | The repository contains security contracts, libraries and synthetic tests. It does not implement every independently operated MICHAEL ANGELO/RTSA/IT-agent service in the MASTER design. |
| Authority and jurisdiction services | Account login and payment are implemented mechanics. They are not commissioned-notary identity verification or a completed production jurisdiction/authority engine. |
| Vault, isolation and immutable audit | Application and audit databases are separate; full independent key custody, network-jail enforcement and externally anchored immutable evidence are not completed by SQLite or source pairing. |
| Every Oracle free-resource category | All supplied categories are catalog-mapped. The code provisions/binds a subset; it does not make every listed managed service a functioning application integration. |
| Fault tolerance and scale | A single VM, local SQLite and online backups do not establish multi-node transactional failover, unlimited throughput or zero downtime. No benchmark establishes maximum production throughput. |
| $0 enforcement | The owner prohibits unapproved spending. OCI quotas/usage and GitHub account billing controls were not configured or verified here. Source code cannot declare paid usage free. |

These are implementation/configuration facts, not assistant-created approvals
that the owner must satisfy before ordinary application installation. Privileged
operation signatures, Humanitarian Core Laws, human oversight, customer privacy
and access controls remain requirements of the owner's design.

## Evidence

Main merge: d45e1e46ba0388f442e2dc7ebaf6cb4d57649489. First GitOps run:
39829199275. Real Python tests, Node tests/audit, both application Docker builds,
source integrity and packaging succeeded. The cloud deployment step failed
before authentication because its credential values were empty. Separate main
development verification and forensic workflows succeeded. These results are
not an Oracle deployment success claim.


## Current completion inventory — owner request, October 22

The following is the known outstanding inventory against the preserved MASTER,
its existing expansion documents, deployment code and runtime. It supersedes
older counts and broad completion statements. Source-level integration does not
mean that a connected account has supplied a server credential.

| Workstream | What is still unfinished | What is connected in source now |
| --- | --- | --- |
| Oracle installation | Actual OCI identity/signing credentials, actual stack OCID, authenticated Plan/Apply and successful host installation | Main-branch GitOps, private source archive, existing/new A1 profiles and agent install |
| Provider credential custody | Actual live API credentials installed on Oracle; one existing ACTIVE designated Vault secret/key/vault and correct IAM access; verified live rotation | Actions secrets are mapped to a private CURRENT Vault update before agent installation; host refresh reads Stripe, SignWell and BlueNotary values |
| Payments | Deployed live Checkout → signed webhook → durable PAID receipt; live exception/refund/reconciliation operations beyond the existing booking flow | Native Checkout/webhook/ledger composition; either matching standard or restricted Stripe keys accepted |
| DNS and TLS | Registrar write access, DNS records targeting the selected deployed host, actual issuance and HTTPS cutover for the intended domains | Host certificate issue/renewal and routing scripts |
| Owner onboarding | Secure automatic delivery of the initial one-use owner setup credential; recovery lifecycle on a live host | Root-private initial setup file, one-use account setup and durable session authentication |
| SignWell | Live key/template binding, callback authentication and completion handling, signed document/evidence retrieval, full controlled document workspace | Actual template document POST from operator case workspace; provider references persist |
| BlueNotary | Live key/template/notary account binding, provider-registered authenticated callbacks, session completion/evidence/journal retrieval and reconciliation of uncertain submissions | Actual RON session POST from operator case workspace; assigned notary email and templates are explicit |
| Human authority | Live identity, commission, method/location/jurisdiction and provider-authorization adapters; journal/seal/retention workflow | Existing AuthorityReview contracts remain separate; requests do not forge notarial completion |
| Independent synthetic AI | Independently operating MICHAEL ANGELO/RTSA services and the full dedicated IT AI Manager, MINOTAUR, Shield and Quality services with actual inference/execution transports and independent custody | Existing contracts, dispatcher, lifecycle, repair and upgrade libraries; these are not all deployed intelligences |
| Twelve IT AI agents | Full live Uptime, Application, Database, Deployment, Infrastructure, Integration, Performance, Backup & Recovery, Observability, Quality, Configuration and IT Support agents operating under the separate manager/clearance/verification chain | Selected maintenance scripts and tested bounded adapters, not a complete autonomous agent matrix |
| Twin-Gate / PBD / Vault | Genuine independent signing services and trust anchors; protected lease custody/revocation, runtime dependency enforcement, network jails, emergency routing/quarantine and independently verified baseline restoration | Nested cryptographic checking and lifecycle mechanics; no forged source signatures |
| Sentinel / immutable audit | Complete continuous isolate-alert-preserve-verify-release/rebuild enforcement, independent containment, external immutable anchoring and protected retention | Source pairing, recurring scans, separate SQLite audit chain and backups |
| Learning / self-healing | Real production diagnosis, model learning under permitted data use, verified autonomous repairs/upgrades and rollback of actual distributed services | Local repair/upgrade mechanics and tests; naming an in-memory queue does not implement an AI service |
| Meetings / accessibility / translation | Native media rooms, invitations/roles, AV transport, secure document collaboration, recording/consent/retention, captions/ASL participation, validated real-time language/dialect translation | Expansion requirements are preserved; not represented as completed media/translation services |
| Oracle resource catalog | Application integration of each remaining catalog service (databases, certificates, load balancers, connectors, mail and other listed services), supported-region/account discovery and combined metering | Full supplied catalog, selected actual Terraform resources, resource inventory, backups and monitoring |
| Operations and resilience | Multi-node transactional coordination/failover, distributed state, disaster-recovery drills, load/latency benchmarks, real alert delivery subscriptions and operational response evidence | Single-host persistent data, private backup/restore checks, metrics and alarm-topic definitions |
| Cost control | Actual account-wide OCI/GitHub quotas, consumption and billing controls; provider plan entitlements and remaining included requests | Owner $0 instruction retained; no automatic paid upgrade or live provider call made during this increment |

`SDS_SYSTEM_SECRET_KEY` is not used as a substitute for the independent role
identities, distinct signing keys, inference services or complete AI architecture.
No such substitution was introduced.

## Credential handoff behavior

The workflow reads `OCI_TENANCY_OCID`, `OCI_USER_OCID`, `OCI_FINGERPRINT`,
`OCI_PRIVATE_KEY`, `OCI_STACK_OCID` and optional `OCI_REGION` for deployment.
Provider inputs are `STRIPE_SECRET_KEY` (or `STRIPE_API_KEY`),
`STRIPE_WEBHOOK_SECRET`, `SIGNWELL_API_KEY`, and `BLUENOTARY_API_KEY`.
Optional Actions variables `STRIPE_LIVEMODE` and `SIGNWELL_TEST_MODE` take the
literal values true/false. They do not override a mismatched payment key.

When provider inputs are supplied, GitOps merges them into the single existing
ACTIVE `sds-runtime-provider-config` secret in the deployment compartment,
checks its etag, updates CURRENT through a private temporary file, verifies the
CURRENT bundle, and only then dispatches installation. With no supplied provider
inputs it preserves existing Vault settings. It does not create a vault/key/secret
or pretend one already exists. Identical inputs do not create a new version.
The existing host refresh timer installs that configuration in the private runtime
mount and restarts the backend when it changes. Source archives contain no keys.

The provider workspace sends explicit human-directed requests. Neither HTTP
acceptance nor `CREATED` means signed/notarized. After timeout or ambiguous
response, the persistent request cannot issue another automatic POST with the
same ID. Provider-side reconciliation of such uncertain requests remains work.

Primary API references used for this implementation:
- https://developers.signwell.com/reference/createdocumentfromtemplate
- https://developers.signwell.com/reference/create-a-document
- https://bluenotary.readme.io/reference/create-new-notarization-session
- https://bluenotary.readme.io/reference/getting-started-with-your-api
- https://bluenotary.readme.io/reference/session-event-webhooks
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/vault/secret/update-base64.html

Validation for this increment: 325 local Python tests passed, zero skipped, plus
operator JavaScript syntax validation. Provider HTTP and OCI API tests use doubles;
there is no new live integration, production deployment or completed AI-service
claim. Earlier sidecar package searches yielded no retrievable results; this does
not establish that the owner's prior work never existed.
