# Owner-supplied serverless transaction function

The three submitted file bodies are preserved as supplied (formatting-only
whitespace normalization). This is a proposed implementation on the review
branch, not an OCI-deployed function. No production traffic is routed here and
the existing Compose stack does not launch this directory. The integrated
entrypoint, private Python route and Connector Hub request renderer are described
in [STREAMING_INTEGRATION.md](../../docs/STREAMING_INTEGRATION.md). Use the staging
command there to select the integrated entrypoint; the three supplied files below
remain intact.

## Validation status

Python syntax can be checked without installing dependencies or accessing OCI:

```bash
python -m py_compile serverless/sds-transaction-validator-fn/func.py
```

Syntax success does not establish an FDK image build, Connector Hub compatibility,
signature verification, durable storage, retry correctness or production readiness.
The requirements range is preserved; no locked FDK dependency resolution or
serverless container security audit has been completed.

The supplied code accepts unsigned records as VERIFIED, accepts missing IDs,
uses INSERT OR REPLACE for conflicting IDs and reports batch_status SUCCESS even
when a per-record write fails. The default /tmp database is not shared between
concurrent OCI function invocations and is not the existing platform's durable
SQLite volume. SHA-256 is a digest, not a verified digital signature. These are
recorded deviations, not silently repaired or accepted production behavior.
The original docstrings are preserved but do not constitute verification evidence.

Paired manifests without genuine authority signatures remain UNSIGNED_SOURCE_MANIFEST; that status alone does not prohibit ordinary installation or startup. The independently
verified receipt utility in core_platform/receipt_verification.py remains distinct;
this submitted function does not call it. No automatic deployment workflow was
added. See docs/SPEC_CONFORMANCE.md and docs/OCI_NEAR_ZERO_OPTIONS.md.

## Owner's diagnostic command (not executed on OCI)

```bash
oci limits value list \
    --compartment-id "ocid1.tenancy.oc1..your_master_root_ocid" \
    --service-name "functions" \
    --query "data[].{Name:name, Limit:value}" \
    --auth instance_principal
```

Replace the placeholder with the actual tenancy OCID, verify the Limits API
service identifier and effective permissions, and use --all if all result pages
are required. This is a resource-limit query, not a free-tier entitlement or
price check. It does not query Streaming limits. Instance Principals access for
these operations is unverified in this session. No OCI command was run.

Primary documentation checked October 21, 2026 (America/Denver):

- https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionsaccessinglocalfilesystem.htm
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/limits/value/list.html
