# Automated OCI inventory

Sanders Dash & Seal now contains a read-only inventory function:
`deploy/oci_inventory.py`. The authorized production bootstrap and standardized
node staging install `sanders-oci-inventory.timer`. It runs after boot and every
six hours, with a small randomized delay and catch-up after downtime. No new OCI
resource, paid scheduler, extra VM, or browser scraping is needed.

The function uses Instance Principals and the installed OCI CLI. It discovers
subscribed READY regions and the active compartment hierarchy, then queries
OCI Search in each region and each compartment within the configured subtree.
Pagination is explicit; time/request/page bounds prevent an endless scan.
The expected list is supplied independently by the administrator, never inferred
as approved merely because a resource happens to exist.

## Configuration

Install OCI CLI for the system account on the approved host (the unit's PATH is
`/usr/local/bin:/usr/bin:/bin`). Provision Instance Principals with permission to
list region subscriptions/compartments and inspect the required resource types
within the selected scope. Search has no separate Search permission grant: its
results depend on resource-level inspection permissions. The program creates
no Dynamic Group or policy and grants no access itself.

Create `/etc/sanders-dash-seal/inventory.json`, owned by root with mode 0600.
Use the structure below, replacing every bracketed value with an actual identity.
Bracketed values are documentation only and are rejected by validation.
For the root compartment, use the actual tenancy OCID for both tenancy and scope.
Add an expectation for every resource required by the selected deployment,
including the VCN, subnet, gateways, security group, storage and optional pipeline.
Resource types use Search's names, such as Instance, Vcn, Subnet,
InternetGateway, NetworkSecurityGroup, Bucket, Stream, FunctionsFunction,
ServiceConnector, Image and InstanceConfiguration. Names alone do not establish
identity. Obtain actual bucket and service identifiers from OCI.

```json
{
  "schema": 1,
  "tenancy_id": "[actual tenancy OCID]",
  "compartment_id": "[actual root or compartment OCID]",
  "home_region": "us-phoenix-1",
  "expected": [
    {
      "identifier": "[actual sanders-dash-seal instance OCID]",
      "resource_type": "Instance",
      "region": "us-phoenix-1",
      "compartment_id": "[actual containing compartment OCID]",
      "allowed_states": ["RUNNING"]
    }
  ]
}
```

The program requires at least one explicit expectation. It stores only selected
resource identity, region, compartment, display name, lifecycle state and
availability domain; tags, object contents, documents and credentials are excluded.
Credentials do not belong in this file. Protect reports as infrastructure metadata.

## Results and platform operation

```bash
sudo systemctl start sanders-oci-inventory.service
sudo systemctl status sanders-oci-inventory.timer
sudo cat /var/lib/sanders-dash-seal/oci-inventory/latest.json
sudo journalctl -u sanders-oci-inventory.service --no-pager -n 30
```

`latest.json` is private and replaced atomically for each completed attempt.
`previous-complete.json` retains the last complete observation; a failed/partial
scan cannot overwrite it. Config fingerprint changes start a new comparison scope.
Added, changed and no-longer-observed resources are compared with that previous
observation. No automatic approved baseline or authority signature is minted.
The state directory holds fixed filenames rather than unbounded history.

| Result | Meaning |
| --- | --- |
| EXPECTED_RESOURCES_VISIBLE | All configured identities, types, compartments and lifecycle states matched the visible Search results. |
| ATTENTION_REQUIRED | One or more configured resources were not observed or mismatched. |
| INCOMPLETE | Configuration, region/compartment discovery, CLI, API, pagination or time-budget failure prevented a complete scan. |

A failure returns a nonzero exit status for systemd and records its stage without
exposing raw CLI errors. The timer continues scheduling future attempts.
No external email or other message is sent by this function.

The report is the platform's host-side infrastructure evidence. It is deliberately
not exposed through the public customer API. Production application adapters may
consume it through their existing authorized operator/audit path; this change
does not add a public infrastructure endpoint or replace runtime release gates.
The importable `inventory_status()` function returns `inventory_current: false`
for failed, missing, malformed, future-dated or more-than-seven-hour-old evidence.

## What an inventory can establish

Search supports most OCI resources, is permission-filtered and can lag changes.
NOT_OBSERVED therefore means absent from this observation, not proven deletion.
Even a complete scan does not verify full-tenancy permissions, security rule
contents, route correctness, live connectivity, billing eligibility, application
health, transaction commitment, backup restoration or zero downtime. Existing
`oci_preflight.py`, live and backup verification remain separate checks.
The function changes no cloud resources and never silently recreates missing
infrastructure. Reconciliation requires the existing authorized deployment path.

No real OCI discovery, IAM update or timer installation has occurred in this
development session. Scheduled operation starts when this approved revision is
deployed with actual configuration, OCI CLI and Instance Principals access.

Sources:

- https://docs.oracle.com/en-us/iaas/Content/General/Concepts/compartmentexplorer.htm
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/search/resource/structured-search.html
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/iam/compartment/list.html
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/iam/region-subscription/list.html
- https://docs.oracle.com/iaas/Content/Identity/Reference/searchpolicyreference.htm
