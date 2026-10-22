# Dual-engine preflight and host identity

`run_preflight_checks.sh` implements the owner's separate Node/Python verification
sequence. It requires a full actual commit and clean source checkout. Production
source at `/opt/sanders-dash-seal` is an archive without `.git`; the runner uses
the separately approved `/opt/sds-approved-source` checkout there. It checks Git
HEAD and drift, archives that exact commit into a temporary build context and
uses `deploy/compose.preflight.yml` under a unique disposable project name.

```bash
sudo bash /opt/sanders-dash-seal/run_preflight_checks.sh --commit "$APPROVED_COMMIT"
sudo systemctl status sanders-oci-inventory.timer
```

The standard initializer and node-bootstrap paths invoke this runner after
independent source authorization. Stage runs both regression engines before
installing monitors; activation runs local metadata and regression checks before
calling the existing runtime/DNS/TLS/readiness deployment path. A Node or Python
failure preserves its nonzero exit status and cannot fall through to activation.
An explicit user-run preflight never activates application services.

The validation images include tests and their actual locked dependencies:

- Node 20.12.2: `npm test` runs all three worker test files, including the selected
  transaction relay and other Node-to-real-Python tests.
- Python 3.12: `python -m unittest discover -s tests -v` discovers the actual suite.
  Neither `pytest` nor a static 211/232/253-test success claim is inserted.

Each test container is nonroot, uses a read-only filesystem and private temporary
space, and has no production volumes, secrets, published ports or external
runtime network. Local loopback remains available for integration fixtures.
Build-time dependency resolution still needs registry/package access. Node tests
and Python tests run sequentially under memory/CPU limits. Cleanup removes only
the unique test project's containers/images and temporary source. Failed tests
do not trigger a production stack shutdown or orphan removal.

The production worker/backend images remain deployment images. They do not gain
test suites, pytest, or a mounted production ledger for validation. Source files
and tests are copied into separate validation images instead. The Node runtime
production Dockerfile still omits package metadata/tests in its final stage, so
do not run `docker compose run pipeline-worker npm test` on the live topology.

The full CI also checks production builds, Nginx, ACME tools, source integrity,
dependency findings and the actual integrated Function FDK protocol. A successful
local preflight reports LOCAL_REGRESSION_PASSED for the selected commit; it does
not assert that live infrastructure is stable or that production authority exists.

## Local metadata helper

`scripts/scan_identity_metadata.py` uses the fixed endpoint
`http://169.254.169.254/opc/v2/instance/` with `Authorization: Bearer Oracle`.
It requests only `id`, `hostname`, `canonicalRegionName` and `state`. Oracle's
documented lifecycle metadata key is `state`, not `lifecycleState`; `region`
alone can return the short value `phx`. Each request has a five-second timeout
and a bounded response. Proxies and redirects are disabled. Missing, malformed,
nonrunning or mismatched data returns failure rather than a fallback hostname.

```bash
python3 /opt/sanders-dash-seal/scripts/scan_identity_metadata.py \
  --expected-instance-id "$VERIFIED_INSTANCE_OCID"
```

The expected instance ID is optional for an observation, and required by an
operator when comparing against a specific independently configured host.
Metadata is host-local observation, not cryptographic identity attestation or
proof of network/application health. The existing six-hour regional inventory
continues to inspect configured compartment resource identities and lifecycle
states. This helper does not replace its scope, timer or reports.

The submitted ERR hook lost the original status after printing; the implemented
hook captures `$?` first and exits with that saved value. No unverified literal
SHA is committed as an approved production target. The original submitted scripts
remain separately preserved in `docs/owner-submitted/`.

Reference: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/gettingmetadata.htm

Development runs use disposable fixtures. No actual IMDS request, OCI deployment
or host timer inspection was executed in this workspace.
