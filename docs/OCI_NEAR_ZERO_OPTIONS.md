# Owner's separate ARM and serverless options

These options are preserved for evaluation alongside the selected VM stack. No
second instance, API Gateway, Function, Stream or new network route was created.
The existing free VM architecture has not been silently migrated.

## Separate ARM ingestion host

The proposal places Python/SQLite on the existing host and moves Node/WebSockets
to `sds-worker-node-arm`. Before applying, verify the second host exists, actual
private address, remaining Always Free compute/storage allocation, image/OS,
private route, source-restricted TCP 3000 ingress and an authenticated backend
path from that host back to Python. Current Docker DNS `wsgi-backend:8000` does
not resolve across VMs. Do not publish Python's business routes to the internet
to work around that. Preserve the Python validation and commit authority.

Correct Nginx syntax separates the keepalive pool directive from the server:

```nginx
upstream node_worker_cluster {
    server ACTUAL_VERIFIED_PRIVATE_IP:3000;
    keepalive 32;
}
```

This is an illustrative non-executable placeholder, not a live config. Set the
relevant `/ws` proxy_pass to this upstream only after connectivity, authentication
and a real transaction receipt test pass. Keepalive pools do not remove the CPU,
memory and live socket state used by WebSocket connections, or provide additional
replicas by themselves. No extra host is needed for the backup implementation.

## Scale-to-zero services and the $0 constraint

Checked against Oracle primary documentation on October 21, 2026:

| Component | Documented pricing/persistence behavior | Implication |
| --- | --- | --- |
| Existing Always Free VM | Account allocation applies; no new resource proposed | Keep existing topology while measuring idle load |
| Object Storage backups | 20 GB combined free storage, 50,000 API requests/month | Bound the bucket allocation and account for other usage |
| OCI API Gateway | Metered per million API calls; listed $3 per million | Idle compute is not proof that active traffic costs $0 |
| OCI Functions | First 2 million invocations and 400,000 GB-seconds/month free; excess billed | Free allowances exist, but are finite; verify account eligibility and ancillary usage |
| Functions provisioned concurrency | Unused provisioned concurrency is billed at a fraction of execution rate | Keeping functions warm can introduce idle charges |
| OCI Streaming | Oracle FAQ explicitly says it does not operate in free tier; storage and data transfer pricing | Does not satisfy the standing no-additional-cost requirement for active use |

Functions write to bounded `/tmp`, which is **not shared between concurrent
invocations**. Therefore a local SQLite file there cannot serve as the current
authoritative shared ledger. An object upload is also not a drop-in replacement
for SQLite's multi-statement transactions and idempotency records. Migration
would need an explicit durable-state/concurrency design and receipt recovery
tests. Function execution has configured timeouts and possible cold starts;
millisecond completion is not guaranteed. API Gateway's documented HTTP/S routes
to Functions do not establish that this blueprint preserves the worker's
long-lived WebSocket sessions. That requires a separately verified protocol design.

Your event-driven direction is viable for bounded stateless work. It does not
require replacing the durable ledger or introducing a paid streaming service.
No load balancer, NAT gateway, provisioned concurrency, serverless conversion or
new resource purchase is implemented here. This note documents actual limits,
not an amendment to your chosen architecture.

Primary sources:

- https://www.oracle.com/cloud/price-list/ (API Management, Streaming)
- https://www.oracle.com/cloud/streaming/faq/ (Pricing / free tier)
- https://www.oracle.com/cloud/cloud-native/functions/ (Invocation and execution pricing)
- https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionsaccessinglocalfilesystem.htm
- https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionscustomizing.htm
- https://docs.oracle.com/en-us/iaas/Content/APIGateway/Concepts/apigatewayoverview.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
