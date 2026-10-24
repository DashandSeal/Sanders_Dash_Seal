# Dedicated role observation workers and recovered RTSA source

This increment carries forward the original fourteen RTSA registry/assessment
assets from foundation commit `3164db713b92fe7ec9332d41c0eb96175725bb62`.
The twelve MASTER IT roles, fourteen RTSAs, IT AI Manager, MICHAEL ANGELO #49,
Global PBD Sentinel and Sanders synthetic AI Sidecar have thirty distinct worker
identities. MINOTAUR and Shield each appear once with their separate original
identity; MICHAEL ANGELO is a separate conductor, never the IT Manager or a
replacement for fourteen RTSAs. See `architecture/RTSA_14_ARCHITECTURE.md` and
`RECOVERED_PLATFORM_HISTORY_2026-10-23.md` for preserved provenance and wider history.

## Implemented operation

Each service runs a separate process with one private observation key and one
writable output directory. Other role keys and the Docker socket are not mounted.
The backend receives only public keys and read-only results. Workers have no
capabilities, no new privileges, a read-only root filesystem, bounded CPU/memory
and no network except the three localhost health probes sharing the backend's
network namespace. Database readers have a read-only data-volume mount. They
never send observations to an external model/provider.

The host administrator initializes the observation identities using the already
built backend image. AI workers do not create signing credentials. Observation
keys are separate from all production Twin-Gate/Quality/Vault trust anchors and
sign only `sds-readonly-role-observation-v1` material. No source manifest, repair,
lease, notarial assertion or production authority is signed by this initializer.

Workers publish actual measured status every thirty seconds. Original RTSA
assessment rules continue to return advisory evidence gaps where live input or
inference is absent. Missing evidence is not fabricated as a passing assessment.
Shield reports its actual process bounds; MINOTAUR independently verifies that
signed Shield observation. This patrol is not proof of complete network/security
containment. Manager observes the twelve-agent matrix; MICHAEL ANGELO consumes
the fourteen distinct RTSA streams. Neither aggregate is a privileged approval.
The Sidecar explicitly reports L15_EXECUTION_NOT_CONNECTED rather than claiming
an observer implements full L15 reasoning or self-healing.

Records bind role, laws, sequence, timestamp and measured observation to a genuine
Ed25519 signature. Publishing is atomic and serialized; sequence survives restart.
The operator-only `GET /api/operator/ai/roles` validates signatures, rejects stale,
future, changed-role and tampered records, and persists replay watermarks across
backend restarts. Re-reading the same signed record is idempotent. Failed/absent
workers appear UNKNOWN. Exception messages and customer payloads are not published.

## Installation and limits

`deploy/compose.ai.yml` supplies thirty individual services using the same locally
built backend image. The existing Oracle installer starts them after core service
startup. Worker initialization/start failures are reported without disabling the
app. Private identities are under `/etc/sanders-dash-seal/ai-roles/identities`;
only its separate `public` directory is mounted into the backend. Nothing is
provisioned outside the existing Oracle VM and no paid resource is created.

This completes signed role observation/transport and local recurring processes,
not all synthetic-AI functionality. The recovered June 23 seven-field runtime
specification still requires named inference engines, measured latency/SLA,
fallback chains, exact inputs/outputs, explainability and governance boundaries.
Live model reasoning, learning, cryptographic approval services, protected
production authority custody, actual governed repairs and independent deployment
verification remain unfinished. Restored legacy boolean/disabled registry metadata
is not wired as a new runtime approval or application startup gate; the current
cryptographic authority path remains separate and controlling.

Local tests use genuine keys/signatures and actual child writer processes.
Ownership/chown metadata is modeled so tests can run under an unprivileged CI
account. This does not prove host ownership, container isolation or live Oracle
startup; those require runtime evidence after installation.
