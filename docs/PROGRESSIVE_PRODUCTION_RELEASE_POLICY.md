# Sanders Dash & Seal — progressive live production release policy

**Status:** Policy established; **no deployment authorized or performed by this document**. The MASTER actual build design of October 11, 2026 controls, including all original Humanitarian Core Laws and distinct MINOTAUR, Labyrinth Shield, Vault and Glass-Box roles.

## Operating mode

Production is the target environment for every component. Development, tests and staging remain non-production. A component may be promoted independently **only if** all its direct and transitive runtime dependencies are production-approved and its deployment cannot expose unfinished or unauthorized functions. A service is not considered live solely because its source, unit tests or development manifests are complete.

## Mandatory promotion gates (all must pass)

1. **Original-spec conformance:** Source mapping and acceptance evidence against MASTER, no unresolved security deviation.
2. **Authority:** Explicit authorized human production-release approval for the specific artifact, version, scope, environment and capabilities; not inferred from a GitHub commit.
3. **Cryptographic controls:** Verified artifact/dependency hashes and genuine independently issued IT AI Manager and MINOTAUR signatures; PBD manifest validation, bounded one-use Vault lease, identity and network scope enforcement.
4. **Safety:** Nine Humanitarian Core Laws, human-in-the-loop where required, safe denial, shelter-in-place, rollback and revocation.
5. **Operational readiness:** Authenticated service identity, protected secret custody, deployed runtime, network isolation, logging, monitoring, backups, incident response and recovery test.
6. **Integration readiness:** Actual connected dependencies, correct legal/jurisdiction/provider authorization, signed inbound/outbound requests, retries and idempotency.
7. **Verification:** Positive, negative, replay, tampering, concurrency, failure and end-to-end integration tests pass; Quality Agent, IT AI Manager reconciliation and MINOTAUR integrity confirmation remain independent.
8. **Evidence:** Glass-Box append-only externally protected evidence of approval, manifest, deployment, tests, health checks, incidents and rollback.
9. **Post-deploy:** Health and synthetic transaction checks pass; no unintended customer charge, notarial act or disclosure; otherwise automatic deny/revert to last verified safe state.

## Release state machine

`DEVELOPMENT → INTEGRATION_VERIFIED → PRODUCTION_ELIGIBLE → RELEASE_AUTHORIZED → DEPLOYED_DARK → LIVE_VERIFIED`

Any failed gate yields `BLOCKED` or `SHELTERED`, revokes execution authority, preserves evidence and prevents activation. `DEPLOYED_DARK` means running with external actions disabled; it is **not** production activation. Changes to artifact, dependencies, scope, authority, signing keys or jurisdiction invalidate previous approval and require fresh verification.

## End-to-end constraint

A component's production activation cannot be declared complete until its relevant full service journey is verified through the production boundary. Never activate a dependent capability ahead of its dependencies. Payment confirmation is not notarial authorization. SignWell eNotary and BlueNotary RON remain distinct and jurisdiction-limited.

## Stripe account versus platform

Stripe account `acct_1UQTehAgIE87JukG` was verified live, with charges and payouts enabled. That **does not** authorize an unverified Sanders Dash & Seal webhook or checkout flow to take live traffic. The webhook development adapter remains default-deny. Register a live webhook endpoint only after a deployed HTTPS URL, protected endpoint secret, signed PBD approval, full verification and release authorization exist. Do not create live charges as an integration test.

## Current release verdict

**BLOCKED — NOT PRODUCTION READY.** No independently signed production PBD manifests, verified runtime containment, deployment target, immutable external audit, full orchestration or end-to-end notarial integration evidence has been established. GitHub workflow success is a development gate, not production authorization.
