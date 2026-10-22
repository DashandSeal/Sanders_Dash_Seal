# Sanders Dash & Seal automatic Oracle activation

This package now targets the existing `sanders-dash-seal` VM by default. It does
not allocate another VM, resize the existing VM, add a VCN, upgrade the account,
purchase a domain, or provision Streaming, Functions or API Gateway.

Upload the ZIP to Oracle Resource Manager and create a stack using Terraform
1.5.x and the actual tenancy and VM compartment. `deploy_existing_instance=true`
is the default; `create_instance=false` and `create_network=false` remain the
defaults. Existing subnet/NSG values are not needed for this existing-VM path.
Unzip a copy in authenticated Oracle Cloud Shell and run:

```sh
python3 activate_on_oracle.py --stack-id YOUR_ACTUAL_STACK_OCID
```

The launcher runs Plan, checks the structured plan against the owner zero-spend and non-destruction
set and destructive actions, then applies that exact plan. It dispatches the
private installer through OCI Run Command and waits for execution success with
exit code zero. It uses the Cloud Shell session; no SSH key or private Git token
is required. Apply in the console alone prepares resources; it does not dispatch
the existing VM's installation command. The launcher performs both steps.

Actual provisioned resources: private Standard release and ledger backup buckets;
an exact-instance dynamic group and scoped IAM policy; an operational notification
topic; two alarms for heartbeat loss and failed backup verification. The installer
binds the returned resource identifiers to root-owned configuration, installs the
supplied Nginx/Node/Python/SQLite application, executes the isolated regressions,
and immediately performs an online SQLite snapshot, private upload, download and
restore-integrity verification. It enables daily backup, five-minute resource
verification/heartbeat, six-hour inventory, integrity and certificate timers.
No email subscription is created or sent by this implementation; the topic is
visible in Oracle and can be subscribed to through the owner's chosen endpoint.

Run Command needs the actual plugin running, outbound connectivity, and existing
administrator permissions for `ocarun` (or execution as root). Those are Oracle
and Linux execution requirements. The launcher cannot grant itself host sudo.
IAM propagation can delay polling. Failure or timeout returns a nonzero result;
resource creation or a queued command is never labeled successful installation.
Resources already created remain in Terraform state for a controlled retry.

The full 26-category catalog is preserved. This implementation actively connects
Compute, existing networking, Resource Manager, Object Storage, Monitoring and
Notifications to the application. Other catalog categories remain catalog-mapped;
they are not silently claimed as provisioned or working application adapters.
For example, adding a managed database does not automatically migrate SQLite.
Terraform owns resource provisioning; the application automatically binds,
checks and uses the supported resources after activation. It does not hold broad
cloud administrator permissions or automatically provision every catalog entry.

The backup bucket uses the shared documented 20-GB free-only storage ceiling,
with a maximum 1-GB individual snapshot; neither value establishes remaining
account-wide storage headroom. Existing usage, old release artifacts and backups
all consume shared allowances. The code does not claim a billing cap or verify
the tenancy's actual free balance. It stops uploading when its configured backup
allocation is exhausted and does not delete ledger records or backups.

TLS activation uses the existing domain names and requires real DNS resolution to
the actual VM. Existing TLS configuration is preserved. New HTTP bootstrap exposes
public assets/health only; an existing timer obtains genuine ACME certificates
and activates the supplied HTTPS/WebSocket proxy when DNS is ready. This package
does not control the existing DNS provider or rewrite mail records.

Process health, successful backup, and cloud provisioning are distinct from full
business readiness: `/readyz` still reports missing business authority/adapters.
This package does not invent sessions, payments, notarial authority or signatures.
The source and generated scripts are hash paired without a custom release-authorizer
prerequisite. No live OCI Apply or host activation was executed in this workspace.
