# Sanders Dash & Seal application deployment

This replaces the earlier audit-only ZIP. Upload the ZIP to OCI Resource Manager,
select Terraform 1.5.x, provide your actual tenancy/compartment and existing
Phoenix public subnet/NSG OCIDs, then Plan and Apply. Default create_instance=true
launches ONE NEW A1 node (1 OCPU, 6 GB, 50 GB boot). create_network=false reuses
the supplied network; true creates a separate network. The original VM is not
modified, imported, stopped or deleted. Check remaining tenancy allowance first.
The documented original 1/6 node plus this 1/6 node totals 2 OCPUs/12 GB before
any other instances. Standard Object Storage uses a small private source archive
within your shared storage allowance. No paid Streaming, Functions, custom image,
NAT gateway or load balancer is provisioned. No unlimited/free-usage guarantee.

The ZIP includes the application source itself. Resource Manager uploads it to a
private artifact bucket and creates an instance-specific dynamic group/policy
allowing the new VM to read that bucket and VNIC metadata. The account running
Apply needs normal permissions to create these OCI resources. No API key,
preauthenticated URL or private Git token is embedded in user data. Only the
artifact identifiers, exact commit and SHA-256 are passed to cloud-init.

First boot installs OL9 host tools, Docker Compose and OCI CLI, downloads and
verifies the artifact through Instance Principals, validates the source inventory,
runs the actual Node/Python regressions in isolated containers, builds the supplied
Node/Python containers, and starts them with Nginx and persistent SQLite storage.
It installs the integrity/inventory/certificate timers. The Resource Manager job
waits for the exact release marker and public process health; failed application
installation fails the job instead of treating VM creation as application success.
There is no custom authorize-release file or SANDERS_RUNTIME_FACTORY prerequisite.

The new VM receives its own public IP. Public HTTP initially serves the existing
application assets and health; it refuses API/auth/WebSocket traffic until TLS is
installed. Point the four existing domains' A records to the new VM's public IP,
preserving mail and verification records. A timer checks DNS and obtains real
Let's Encrypt certificates, then activates the supplied HTTPS/WebSocket proxy.
DNS changes require your existing DNS provider access; this ZIP does not pretend
to control a registrar. The TLS operation can briefly recreate Nginx and makes no
zero-downtime guarantee. This is a fresh deployment, not ledger migration; do not
run two authoritative independent SQLite ledgers for the same business records.

Application installation and business integration are distinct states. The
repository currently contains static customer/operator interfaces and core
components, but no complete live session-authentication/business adapter
composition. /healthz reports the running Python process. /readyz continues to
report 503 for unconfigured business authority. Existing human-review, signed
receipt, payment and privileged-operation controls remain enforced; this installer
never invents sessions, provider keys, payment confirmation or notarial authority.
Installing every source file does not make those incomplete integrations ready.
This package is therefore an application installer, not evidence that all business
features are complete. No live cloud Apply has been performed from this workspace.

The private source archive includes repository code/docs/tests, excludes private
keys, runtime secrets, Git internals and dependencies, and is checked against its
recorded hashes. Hashes are integrity checks, not fabricated authority signatures.
Source pairing remains available without becoming a blanket server-start blocker.
Production secrets and customer data must not be put in this upload ZIP.

If Apply times out, inspect OCI Console cloud-init output; IAM propagation,
capacity, egress, RPM installation and image pulls can fail independently. The new
instance has prevent_destroy protection. A failed job may leave provisioned
resources; review its Terraform state/Plan before retrying. No automatic destroy,
replacement or rollback of the existing VM occurs. The deployment script refuses
to overwrite an existing source tree and is intended for first boot.
