# Owner's dependency fix and live deployment verification

The owner's ws 8.17.1-or-later instruction authorizes replacing the earlier exact
8.16.0 pin. package.json and overrides now select **8.22.0**, with a regenerated
lockfile. Existing metadata, Dockerfile layout and WebSocket APIs are preserved.
The maintainer's newer advisories cover releases below 8.20.1 (memory disclosure)
and below 8.21.0 (fragmentation memory exhaustion), so 8.17.1 alone is insufficient.
The current production npm audit reports no known vulnerabilities. This audit
result is scoped to the worker's resolved dependencies, not the entire platform.

## Real resource mappings, stored privately

No .env.secrets file was created or committed. The pasted friendly OCIDs are
illustrative, `://oraclecloud.com` is not a valid HTTPS message endpoint, and the
sample signature is not cryptographic proof. Obtain the exact identifiers from
the actual tenancy/resources; do not convert resource names into invented OCIDs.
For the root compartment use the actual tenancy OCID itself. The known instance
OCID does not reveal the tenancy's OCID or prove stream/function existence.

Store only the OCI mapping fields below in a private owner-controlled 0600 file,
for example /etc/sanders-dash-seal/oci.env. It can be named .env.secrets if dedicated
to these mappings; do not overwrite an existing file containing other application
secrets. The parser rejects unknown/duplicate keys and never sources shell code.
No placeholder values below are operational:

```dotenv
OCI_REGION=us-phoenix-1
OCI_TENANCY_OCID=ACTUAL_TENANCY_OCID
OCI_COMPARTMENT_OCID=ACTUAL_ROOT_TENANCY_OR_CHILD_COMPARTMENT_OCID
OCI_STREAM_POOL_OCID=ACTUAL_STREAM_POOL_OCID
OCI_STREAM_OCID=ACTUAL_STREAM_OCID
OCI_STREAM_ENDPOINT=ACTUAL_HTTPS_MESSAGES_ENDPOINT_FROM_STREAM_DETAILS
OCI_STREAM_TOPIC_NAME=sds-production-pipeline
OCI_FUNCTION_OCID=ACTUAL_INTEGRATED_FUNCTION_OCID
OCI_OBJECT_STORAGE_NAMESPACE=ACTUAL_NAMESPACE
OCI_BACKUP_BUCKET=sds-ledger-backups
```

From the approved source checkout on the real host:

```bash
sudo python3 deploy/oci_preflight.py --config /etc/sanders-dash-seal/oci.env
sudo python3 deploy/oci_preflight.py --config /etc/sanders-dash-seal/oci.env --verify-live
```

The first invocation checks syntax only. The second makes **read-only** CLI calls
with Instance Principals: tenancy, compartment ancestry if needed, active pool,
active stream and its exact message endpoint, active function, namespace and
private Standard bucket. Missing permissions or mismatched responses fail the
check. It never grants IAM, creates resources, changes routes or prints secrets.
RESOURCE_IDENTITIES_VERIFIED is not production readiness, route verification or
a claim that the Function's deployed image matches this source. The actual host
needs the OCI CLI and effective read permissions for these operations.

## Service Gateway routing for this VCN

The existing instance subnet is public and already has an Internet Gateway route.
Oracle explicitly documents that a public-subnet route table cannot combine an
Internet Gateway route with the **All PHX Services in Oracle Services Network**
Service Gateway route; asymmetric routing can break service-initiated access.
Do not apply that broad Service Gateway rule to the current default route table.

Supported choices depend on the actual topology:

- Preserve the public subnet's Internet Gateway route. If private Object Storage
  access is required there, use the **OCI PHX Object Storage** destination label
  and a compatible enabled Service Gateway label.
- For Functions in a private subnet, a separate private route table can direct
  **All PHX Services in Oracle Services Network** to the enabled Service Gateway.
  Check supported services, DNS resolution, security egress and IAM separately.
- A Streaming private endpoint has its own VCN/subnet routing requirements. A
  Service Gateway is not a substitute for configuring that private endpoint.
- Function-to-VM HTTPS still needs the private DNS/TLS route described in
  STREAMING_INTEGRATION.md. Service Gateway access to Oracle services does not
  create that application route or establish a public frontend producer identity.

No route or gateway was changed by this revision. No paid gateway was created.
Inspect the actual subnet/table/Service Gateway before any topology mutation.

## Apply the approved runtime without taking down the whole stack

Use the existing release-authorized bootstrap procedure in ORACLE_BOOTSTRAP.md:

```bash
sudo bash deploy.sh --apply
```

It requires the independently installed release authorizer and genuine runtime
bindings, preserves the Compose project identity, stages the authorized commit,
uses the production override and validates readiness/TLS. Do not replace this
with `docker compose down --remove-orphans`: that introduces downtime and is
unnecessary for the prepared update. Container replacement on this single VM
can still interrupt sockets; no zero-downtime guarantee is made.

The integrated Function is built from the staged integrated manifest described
in STREAMING_INTEGRATION.md. Verify its real deployed image, configuration,
private routing and connector source/task/target before publishing events. A
locally passing build does not prove that OCI has deployed that image.

## Verify a real supported signed transaction

The sample `PLATINUM_BLUE_DIAMOND_SIGNATURE_99` must be rejected. Do not invent a
signature or mark a notarial action verified just to receive HTTP 200. Use an
actual registered actor/key and a real processor-supported, authorized operation
with a fresh transaction ID. The signed envelope is exactly actor,
transaction_id, transaction and signature; transaction.request_id matches the ID.
See STREAMING_INTEGRATION.md for canonical signing material and producer usage.

`POST /` on the public domain is not the stream transaction endpoint. The private
/api/stream/transactions route requires a private-subnet source and real signature;
the broker admission command reports STREAM_ADMITTED, not a committed receipt.
Successful end-to-end verification requires the correlated COMMITTED receipt,
durable database record and Connector Hub archive object. A rejected transaction
must not be counted as a successful live test.

## Inspect the actual durable volume

SQLite lives in **sqlite_storage:/app/data/sds_production.db** inside wsgi-backend,
not in /opt/sanders-dash-seal/backend/data on the host. The host-path sqlite3
command could create a different empty database. Use a read-only connection in
the running backend and pass the actual transaction ID and actor as arguments:

```bash
cd /opt/sanders-dash-seal
sudo docker compose -p sanders-dash-seal \
  -f docker-compose.yml -f deploy/compose.production.yml exec -T wsgi-backend \
  python -c 'import json,sqlite3,sys; db=sqlite3.connect("file:/app/data/sds_production.db?mode=ro",uri=True); row=db.execute("SELECT s.transaction_id,s.sha256_digest,s.status,p.receipt FROM sds_ledger_receipts s JOIN pipeline_receipts p ON p.request_id=s.transaction_id WHERE s.transaction_id=? AND p.actor=?",(sys.argv[1],"stream:"+sys.argv[2])).fetchone(); db.close(); print(json.dumps({"found":bool(row),"transaction_id":row[0],"sha256":row[1],"status":row[2],"receipt_id":json.loads(row[3])["receipt_id"]}) if row else "Receipt not found"); sys.exit(0 if row and row[2]=="VERIFIED" else 1)' \
  ACTUAL_TRANSACTION_ID ACTUAL_REGISTERED_ACTOR
```

Correlate the ID/receipt with the actual Function result and storage archive.
This query avoids printing entire business records or performing writes. Verify
that business-state changes match the authorized operation as a separate check.

## Backup and restore proof

Use the existing private backup configuration and verified Instance Principals
permissions in LEDGER_BACKUPS.md, then run:

```bash
sudo bash /opt/sanders-dash-seal/deploy_backup.sh
```

Require exit zero and BACKUP_RESTORE_VERIFIED. The routine creates an online
SQLite snapshot, uploads it, downloads it, checks database integrity and compares
the content hash. It reports the actual object name/digest for correlation.
An Object Storage listing alone proves neither recoverability nor transaction
presence. Full recovery readiness additionally requires an isolated application
restore with receipt/business-state checks and real authority bindings.

No live rollout, OCI identity query, transaction, archive check or recovery drill
has been executed from this session: authenticated Oracle host access is absent.
Source/security checks and live production evidence remain distinct.

## Primary references checked October 21, 2026 (America/Denver)

- https://github.com/websockets/ws/security/advisories/GHSA-3h5v-q93c-6h6q
- https://github.com/websockets/ws/security/advisories/GHSA-58qx-3vcg-4xpx
- https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p
- https://github.com/websockets/ws/releases/tag/8.22.0
- https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/servicegateway.htm
- https://docs.oracle.com/en-us/iaas/Content/Network/Reference/known_issues_for_networking.htm
