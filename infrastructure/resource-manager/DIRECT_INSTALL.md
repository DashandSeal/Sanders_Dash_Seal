# Sanders Dash & Seal direct installation

Upload **sds-direct-install.zip** to Oracle Resource Manager, create the stack
with Terraform 1.5.x, and run Plan then Apply. The ZIP defaults to one NEW
VM.Standard.A1.Flex node with 1 OCPU, 6 GB RAM and a 50-GB boot volume. It leaves
the original `sanders-dash-seal` VM running. It does not resize it or select E4.
The owner-supplied existing node is 1 OCPU/6 GB, so these two nodes total 2/12;
this does not verify other tenancy usage or promise capacity availability.

The stack discovers the existing VM's real compartment, primary network and NSG.
For the supplied root-compartment VM it also derives the tenancy OCID, so the
normal supplied-account path does not require typing replacement OCIDs. An
actual non-root compartment requires the actual tenancy OCID. Resource Manager
uses its job authentication, not the application VM's principal to launch itself.

The complete application archive is inside the ZIP. There is no private Git
clone, deploy token, custom approval file or runtime-factory prerequisite.
Cloud-init installs OL9 tools, Docker Compose and OCI CLI, fetches the exact
private release through the new VM's own Instance Principal, verifies source
hashes, runs isolated application tests, builds Nginx/Node/Python, initializes
persistent SQLite, binds the created private backup and monitoring resources,
and enables background maintenance. The job waits for an exact-release health
marker written only after installation and the first verified backup complete.

The existing-VM variant is still available as **sds-automation-stack.zip**; it
uses Oracle Run Command and the included Cloud Shell launcher rather than
allocating a new VM. These are alternatives, not two stacks to apply together.

Apply provisions private Standard release/backup storage, scoped IAM, a notification
topic, and heartbeat/backup alarms. The application then uses the real bucket
and emits metrics, checks resources every five minutes, snapshots and verifies
SQLite daily, and performs the existing six-hour inventory and integrity checks.
No email subscription is silently created. Remaining catalog categories stay
catalog-mapped, not falsely reported as provisioned application integrations.
The shared free storage allowance includes existing objects and both buckets;
this package does not measure remaining tenancy-wide free headroom or impose a
billing cap. No paid managed streaming, Functions, API Gateway or E4 is deployed.

The new node receives a new public IP shown in the stack output. The original
IP is not transferred. Existing domain DNS must resolve to that IP for genuine
TLS issuance; the certificate activation timer handles issuance automatically
when DNS is ready. It preserves mail records. HTTP initially serves public assets
and health only. /readyz separately reports unfinished business integrations.
No live deployment has been completed from the development workspace.
