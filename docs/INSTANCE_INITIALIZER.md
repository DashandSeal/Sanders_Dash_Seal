# Production automation profile

`instance_init.sh` integrates the owner's staged initializer with the existing
release-authorized deployment. The submitted source is preserved in
`docs/owner-submitted/instance_init.proposed.sh.txt`; the runnable integration
does not silently treat its placeholders or incomplete shell conditional as valid.

From an independently approved installed source tree, prepare a fresh node:

```bash
sudo bash /opt/sanders-dash-seal/instance_init.sh --stage --commit "$APPROVED_COMMIT"
```

Supply the full actual 40-character commit SHA, not a PR label or moving branch.
The bootstrap checks out that revision, verifies independent release authority
before loading repository code as root, and checks protected runtime bindings.
Stage mode builds the worker/backend, runs isolated dual-engine preflight, and installs integrity/inventory timers.
It starts no application containers and refuses to rebaseline an existing host.
The selected revision must include the bootstrap and monitoring functions.

After reviewing the node's role and confirming its assigned public IP, DNS,
durable state, independent release approval and CI evidence for the exact release:

```bash
sudo bash /opt/sanders-dash-seal/instance_init.sh --activate \
  --commit "$APPROVED_COMMIT" --public-ipv4 "$VERIFIED_NODE_PUBLIC_IPV4"
```

Activation observes local IMDSv2 identity/state and runs the same isolated
preflight before delegating to `deploy.sh --apply`; the existing Compose project and production
override, ACME, runtime authority and readiness checks still apply. Stage and
activate are separate invocations. A failed stage cannot fall through into an
activation command. Errors propagate a nonzero status; errors are not automatically
rolled back, and the initializer does not claim to provide atomic live releases.
An inherited SDS_PUBLIC_IPV4 is discarded. Optional `--tune-kernel` passes the
owner's explicitly requested profile to its verified application/rollback helper.

This entrypoint is part of the source installed during deployment. On a new
unprepared machine, the existing cloud-init/approved-source bootstrap prepares
the source tree; creating `/opt` by hand is not an application installation.
Private Git access, OCI CLI, runtime configuration and independent authority are
still provisioned through the established secure path.

## Corrections to the submitted commands

- The supplied metadata URL is incomplete. The supplemental helper now observes
  documented IMDSv2 fields; OCI assigns each VNIC's network addresses. Passing a distinct
  public address here selects deployment/DNS validation; it does not assign DHCP,
  reserve a public IP, modify a VNIC or configure a subnet address.
- `TARGET_COMMIT` in the submitted script only printed a placeholder. The real
  initializer passes a full commit to the checkout and independent verifier.
- The newly added worker `npm test` command runs all actual Node test files in
  the dedicated validation image. The Python validation image runs unittest
  discovery, matching this repository's suite. Production images do not contain
  these full test environments; see `docs/PREFLIGHT_VALIDATION.md`. Approval of
  the exact release and real runtime remains independent of a passing suite.
- The existing deployment builds both app images and retains the production
  Compose override/project identity. No uncontrolled image pull, forced no-cache
  rebuild, stack shutdown or orphan deletion is introduced.
- The supplied conditional is missing `fi`; the runnable initializer passes
  `bash -n`. The original remains intact as nonexecutable provenance.

## Inventory scheduling and scope

Use `sanders-oci-inventory.timer`, already enabled through the authorized
production and fresh-node staging paths. Do not also add the proposed cron entry;
`scripts/scan_oci_inventory.sh` is not the implementation. The actual function is
`deploy/oci_inventory.py`, with fixed private report files and a six-hour timer.
See `docs/OCI_AUTOMATED_INVENTORY.md` for configuration and status commands.

Inventory observes resource identity, location, type and lifecycle metadata.
It does not currently inspect IAM policy statements, NSG rule contents, bucket
privacy/retention changes or arbitrary service configuration. Therefore it cannot
promise to detect every policy or bucket-setting change within six hours. Existing
OCI preflight separately checks bucket privacy when explicitly run. Search lag,
permissions, failed queries and stale reports remain explicit limitations.

Passing CI verifies the implemented development behavior at the tested commit.
It does not establish complete security certification, maximum throughput,
production uptime, activated OCI timers or a live deployment.
