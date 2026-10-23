# Integrated event-driven Sanders Dash & Seal path

Streaming, Connector Hub, Functions and Object Storage now have connecting code
to the existing Nginx/Node/Python/SQLite platform. Original submitted func.py,
func.yaml and requirements.txt remain unchanged. Use the integrated build context
described below to select the connected entrypoint. This is implemented source
and development evidence; no live OCI provisioning or frontend cutover occurred.

## Responsibilities and explicit integration changes

1. An authenticated producer publishes a **signed event** using OCI's Streaming
   API or Kafka-compatible interface. The supplied producer tool implements the
   REST/CLI path with Instance Principals, base64 messages, actor partition keys
   and per-message error checks. Kafka client deployment is not fabricated.
2. Connector Hub consumes Streaming using TRIM_HORIZON and invokes the Function
   as a **task**, then sends its output to the private Object Storage target.
   This connects both processing and archiving; a Functions target alone would
   not forward its return data to an Object Storage target.
3. The integrated Function decodes the base64 batch, bounds its size/time,
   rejects malformed envelopes and sends each signed event to the existing
   Python core over verified HTTPS. It has no background listener or local
   authoritative SQLite database. Invalid batches and transport failures return
   HTTP 503, without sensitive payloads or internal exception details.
4. The Python core authenticates the signed actor using an independently
   configured public-key binding, checks release authority and invokes the real
   existing transaction processor. Business writes, the verified-signature row
   and idempotency receipt share **one SQLite transaction**. Nothing is called
   COMMITTED until that transaction succeeds. The processor still controls
   operation-specific authorization, human approvals and business auditing.
5. The Function returns a list of committed receipts; Connector Hub archives
   it under **stream_receipts/**. The prior database backup routine retains its
   separate **ledger_snapshots/** prefix. A raw event archive does not replace
   a database recovery snapshot or independently verify business authorization.

This preserves the Python transactional authority and existing Node/WebSocket
path while adding on-demand stream processing. It is an explicit hybrid: the
durable Python core remains on the VM. It does **not** claim zero idle resources
for the whole platform, unrestricted throughput, exactly-once message delivery,
zero-cost active Streaming or elimination of the existing VM. A fully serverless
ledger would require a separately selected durable transactional store.

## Signed event contract

The event has exactly four fields:

```json
{
  "actor": "registered-producer",
  "transaction_id": "unique-request-id",
  "transaction": {
    "request_id": "unique-request-id",
    "action": "actual-processor-supported-operation"
  },
  "signature": "BASE64_ED25519_SIGNATURE"
}
```

The example is a schema, not a usable signed transaction. Actor and ID follow
the platform identifier rules; request_id must equal transaction_id. Sign
`receipt_signing_material(transaction_id, stream_signing_payload(event))`, using
the existing core_platform helpers. The canonical payload binds actor and
transaction, excludes signature itself and rejects nonfinite values. Register
the signer's public key independently; no request can install its own trusted key.
Never put bearer tokens, account signing keys, private keys or secrets in events.

The administrator's existing RuntimeBindings factory must supply:

- the real transaction_processor and durable transaction_store (or the existing
  transaction_db configuration used by load_application);
- the existing genuine release_verifier;
- stream_verifiers mapping each approved actor to a ReceiptSignatureVerifier
  constructed from that actor's independently verified Ed25519 public key.

No production signing key, issuer, business processor or approval is generated.
The stream namespace is separate from ordinary Node request receipts to prevent
an earlier Node request from bypassing signed stream recording. Signed ledger
transaction IDs are globally unique; conflicting reuse is rejected, not replaced.

## Private HTTPS route

Nginx now exposes /api/stream/transactions only to direct peers in the existing
10.0.0.0/24 VCN subnet, ignoring forwarded-address headers. Signature and release
verification are still required by Python. This source range must be reviewed
against the actual Functions subnet before deployment; no wider range is added
automatically. Existing public application and WebSocket paths remain available.

Set Function configuration SDS_STREAM_BACKEND_URL to the approved HTTPS URL
ending in /api/stream/transactions. An example logical URL is:
https://sandersdashandseal.com/api/stream/transactions

The Function must resolve that certificate hostname to the backend's **private**
address through an independently configured private DNS view, and its VCN must
permit the connection. Public DNS alone does not establish this route. No NAT
gateway, DNS record, security rule, IAM grant or certificate was created. Do not
disable TLS checks or expose Docker port 8000 publicly to make a test pass.

## Stage the actual integrated Function

From the repository root:

```bash
python -m serverless.oci_pipeline stage-function --output /tmp/sds-function-review
docker build -t sds-integrated-function-review /tmp/sds-function-review
```

Choose a new output directory; staging refuses overwrite. It copies integrated.py,
the owner's FDK requirements, a Python 3.11 Dockerfile and func.integrated.yaml
renamed to func.yaml. The custom Docker runtime sets the actual /usr/local/bin/fdk
entrypoint and runs as UID 10001. The original manifest retains the supplied
/python/bin/fdk entrypoint; it is not the integrated deployment entrypoint.
No build command publishes an image or creates a Function/application.

CI builds the integrated container and invokes its actual FDK response protocol
on the runner architecture. Production ARM64 build, OCIR publishing, image
signatures and deployment are separate uncompleted checks. The original FDK
range remains unpinned; a successful build is not a dependency security audit.

## Render OCI requests without executing them

```bash
python -m serverless.oci_pipeline render \
  --compartment-id ACTUAL_COMPARTMENT_OR_TENANCY_OCID \
  --pool-id ACTUAL_STREAM_POOL_OCID \
  --stream-id ACTUAL_STREAM_OCID \
  --function-id ACTUAL_INTEGRATED_FUNCTION_OCID \
  --namespace ACTUAL_OBJECT_STORAGE_NAMESPACE \
  --output /tmp/sds-oci-request-review
```

The placeholders deliberately fail validation. Supply verified identifiers.
Outputs are pool.json, stream.json and connector.json. Relevant actual CLI groups
are `oci streaming admin stream-pool create`, `oci streaming admin stream create`
and `oci sch service-connector create`. The renderer does not execute them.
Create resources only once and use their returned OCIDs for later requests;
rendering a request does not prove that the referenced resources exist. Creating
a connector can immediately activate data movement. Cost authorization, effective
IAM permissions and network readiness must precede any such operation.

IAM responsibilities remain separate: producer STREAM_PUBLISH access, deployer
resource creation, connector STREAM_READ/STREAM_CONSUME, Functions invocation
and bucket object creation. Instance Principals on the VM do not automatically
grant the connector or public clients these rights. Scope real policies to the
specific compartments, stream, function and bucket; do not grant public access.

The conservative template uses one partition, a 1 KB / 5 second function batch
setting, and a 1 MB / 60 second archive rollover setting. These are integration
defaults for validation, **not maximum-throughput tuning**. Check service-specific
accepted ranges in the actual tenancy before creation. Runtime limits are 1 MiB
transport batch, 128 records, 256 KiB per event, 24 second batch processing budget
and at most three seconds per backend call. These are intentionally below OCI's
general maximum invocation payload. Tune batching from observed latency and load.

## Explicit publish action

After real resource/network/identity setup, an already signed event can be admitted
to an existing stream using the operator's Instance Principals credentials:

```bash
python -m serverless.oci_pipeline publish \
  --stream-id ACTUAL_STREAM_OCID \
  --endpoint ACTUAL_HTTPS_STREAM_MESSAGE_ENDPOINT \
  --event /protected/path/signed-event.json
```

Successful output is STREAM_ADMITTED, **not COMMITTED**. It proves broker admission
only. A real committed receipt and storage-sink object must be verified separately.
The source frontend has not been switched to direct OCI publishing: it needs an
actual client identity and signing arrangement. Do not ship tenancy API secrets
or instance credentials in browser JavaScript. Existing authenticated API and
WebSocket flows are preserved while that identity binding is completed.

## Failure, replay and recovery behavior

Streaming/Connector Hub retries can redeliver records. Identical signed retries
return the existing durable receipt without another business write. Invalid
signatures are checked even on replay. Changed payloads with reused IDs conflict;
processor failure rolls back both business state and the signature receipt.
A batch may commit some records before a later transport failure; the invocation
then fails and a replay safely reuses the committed receipts. Duplicate archive
objects can still occur: do not interpret them as duplicate business transactions.

Invalid events, exhausted batch deadlines, persistent backend failures and
revoked signing identities require operational remediation. This implementation
does not silently skip poison messages, advance their checkpoint or invent a
dead-letter queue. Monitor connector failures/lag and retain source data until
reconciliation; the one-day stream setting is finite. Size batches so retries can
finish within the Function timeout. External irreversible effects still require
the business processor's idempotent outbox/dispatcher.

The automated backup's dedicated-bucket budget does not throttle Connector Hub
writes. Streaming archives share the bucket's free-space allocation and need
separate account/connector usage controls before activation. No unlimited-free
storage claim is made and no paid service is provisioned by this code.

## Development evidence and primary references

Tests exercise actual Ed25519 signing/verification and SQLite atomic commits,
Function batch decoding, partial retries, revocation, conflicting IDs, missing
bindings and producer admission failures. Actual FDK fixture invocation checks
HTTP 200 receipt lists and HTTP 503 error propagation; its HTTPS peer is simulated.
These do not establish a live stream, private route, public client, ARM deployment
or maximum measured throughput. Unsigned source pairs do not impose a blanket deployment or diagnostic-startup veto; privileged execution still requires valid independent authorization.

- https://docs.oracle.com/en-us/iaas/Content/connector-hub/create-service-connector-streaming-source.htm
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/streaming/admin/stream/create.html
- https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/streaming/stream/message/put.html
- https://docs.oracle.com/en-us/iaas/tools/python/latest/api/sch/models/oci.sch.models.FunctionTaskDetails.html
- https://docs.oracle.com/en-us/iaas/tools/python/latest/api/sch/models/oci.sch.models.ObjectStorageTargetDetails.html
- https://blogs.oracle.com/developers/archiving-stream-data-to-object-storage-with-service-connectors

The latest owner-authorized dependency/security and live-verification procedure
is recorded in [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md). It includes the
public-subnet Service Gateway routing constraint and read-only identity checks.
