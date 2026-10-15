# Authentication and bounded authority

This foundation authenticates **operational agents**, not customer browser sessions.

| Component | Implemented responsibility |
|---|---|
| TwinGate | Verify separate IT AI Manager and MINOTAUR signatures using configured public keys |
| Vault | Store approved leases; enforce expiry, exact request matching, proof of possession, one-use claims and revocation |
| PBDManifestGenerator | Prepare unsigned payload and scope bindings |
| PBDScriptValidationEngine | Verify matching artifact bytes, scope and both approvals |
| QualityAgent | Verify signed result-hash-specific functional attestation |
| ITAIManager | Verify result-specific reconciliation attestation |
| Minotaur | Verify result-specific integrity attestation |
| LabyrinthShield | Maintain separate in-process shelter/containment state |
| GlobalPBDSentinel | Report missing, altered or invalid artifact manifests |

## Request flow

1. Prepare a request with a random lease ID, agent public key, exact endpoint/method/IP/operation, payload hash, tier and expiry.
2. External authorities independently sign the same canonical request. Minting requires both trusted signatures.
3. The agent signs that lease using its own private key. An intercepted lease ID alone grants no execution.
4. Vault compares the supplied request with the approved request, verifies possession and atomically consumes the lease.
5. The lifecycle checks containment and the signed manifest, then records intent before entering the trusted adapter.
6. Independent check adapters produce signed Quality Agent, manager reconciliation and MINOTAUR integrity attestations tied to the actual result hash.
7. The lifecycle records the outcome, revokes the lease even on failure, and records revocation. Failure after a valid claim enters humanitarian containment mode.

A returned HTTP success is never sufficient for `VERIFIED`.

## Credentials and tokens

Production private keys belong in separately administered remote signing/KMS services; this repository contains no production key issuer. Public-key trust is injected into constructors, never read from an untrusted token. Test private keys are generated transiently in memory.

Signing domains separate manifests, leases, agent proofs and each verification attestation. Signatures cover canonical JSON and the domain. SHA-256 binds the payload; Ed25519 provides signatures. Ed25519 is not claimed to be post-quantum cryptography.

Vault uses SQLite and durable unique lease IDs. `BEGIN IMMEDIATE` makes simultaneous claims mutually exclusive. Any observed invalid claim for a known lease revokes it. This intentionally favors denial over availability and requires transport-level authentication/rate limiting before exposing an API. Copying an unused token is not detectable until use is attempted.

SQLite state must remain on a protected persistent host. Restoring an old database can resurrect authority; deployment must use a nonrollback revocation service or invalidate all leases after recovery. Host clock integrity is required. Consumed authority is not restored on an operation failure.

## Trust boundary and limits

The functions run on a trusted host. Python does not sandbox the adapter, enforce network egress, bind a DNS resolution to a socket, or protect itself from a hostile administrator. Endpoint/IP checks compare declared scope only. Production needs an enforced egress proxy, workload identity, isolated authority services and an external manifest-verifying bootstrap covering imports and dependencies.

Hash chaining detects ordinary record alterations but does not make a database immutable. An administrator can rewrite a chain or remove its suffix. Production needs independently anchored checkpoints and append-only external storage. Revocation is logical invalidation, not assured memory erasure.

No customer login, passwords, cookies, OAuth sessions, payment credentials, SignWell credentials or BlueNotary credentials are implemented or collected here. Provider integrations and human authentication are future work.
