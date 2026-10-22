# Sanders Dash & Seal — Twin-Gate connection status

Controlling source: MASTER sections 8–10 and 20. October 15, 2026.

`core_platform/clearance.py` connects the request/clearance sequence to the
existing Vault API. It takes separate IT AI Manager and MINOTAUR client objects.
Each client implements `approve(domain, material, agent_assertion)` and returns
only its own base64 Ed25519 signature. This is a local adapter interface, not a
claim that an existing remote API uses this wire format. Actual service adapters
must follow the deployed services' authenticated protocols.

The caller supplies a nested section 9 lease with its agent assertion signed and
both governance fields empty. The coordinator verifies the assertion, obtains
and verifies necessity approval, then obtains and verifies independent safety
clearance. Both approvals cover the existing `pbd-lease-v2` signing material.
Vault rechecks scope structure, expiry, agent assertion and both signatures
before inserting the one-use lease. No retry or fallback approval is attempted.
No private signing keys are held by the coordinator.

The coordinator does not evaluate operational necessity or Shield safety itself.
Distinct client objects and public keys cannot prove independent service custody;
that must be verified in the deployment. It does not execute a lease or replace
the Quality Agent, immutable Glass-Box Audit, revocation lifecycle or containment.
Denial evidence and the MASTER section 10 failover sequence still require the
external orchestration and audit integration. A denial is not a completed repair.

## Required existing-service connection information

- Hosting provider/account/project for the existing runtime and deployment target.
- IT AI Manager and MINOTAUR service locations and their actual API contracts.
- Public verification keys and their independently authenticated provenance.
- Service authentication mechanism and secret-store references; private keys and
  credentials remain in the service/secret store, not GitHub source or chat.
- Vault, containment controller and immutable Glass-Box Audit service interfaces.

The original routing example names `https://manager.internal` and
`https://minotaur.internal` as example initialization. These have not been verified
as deployed services and must not be treated as live configuration by inference.
The GitHub connection used here does not expose deployment/environment inventory
through its approved fetch endpoints; an attempted deployment-list read was
rejected. That says nothing about whether infrastructure exists elsewhere.

## Verification

84 tests pass locally: 73 existing plus 11 clearance tests covering valid issuance,
agent proof failure, either gate's rejection, timeout without retry, scope mutation,
expiry while awaiting clearance, wrong signer, duplicate lease, prefilled approval,
and shared client rejection. Tests use generated development keys.

Production release remains disabled. Executable pairs are unsigned. This change
completes the transport-neutral clearance handoff only; it does not establish live
service connectivity, production authorization or full MASTER conformance.
