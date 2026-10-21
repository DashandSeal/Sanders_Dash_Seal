# Node ingestion transport

The optional worker implements the owner's Node/Python role split over the
existing Python appointment API. This is development source, not a production
deployment or a complete generic transaction pipeline.

`wss://sandersdashandseal.com/ingest` requires the exact canonical Host/Origin
and a session Cookie verified by Python `/api/session` before upgrade. No token
in a URL, shared master key or user-supplied identity header grants authority.
Production authentication must support the same secure, HttpOnly session cookie
at `/ingest` and independently verify each call. The currently unconfigured
Python runtime deliberately rejects admission.

The supported message is:

```json
{"action":"request_appointment","payload":{"request_id":"client-generated-stable-id","jurisdiction":"CO","service":"MOBILE_NOTARY","requested_start":"2027-01-01T10:00:00Z","meeting_area":"Denver area","consent":true}}
```

Python `/api/appointments` validates fields, reauthorizes the session and release,
performs its audited SQLite transaction and checks request ID reuse. After a
valid HTTP 201 receipt, the worker returns only `ack`, `request_id`, `case_id`
and `status: request_recorded`. This records a request; booking, payment,
notarial acts and legal authority retain their separate approval requirements.
Unsupported `dispatch_transaction` messages and document uploads are rejected.

On `outcome_unconfirmed`, disconnect or timeout, Python may already have
committed. Retry the **same request_id and unchanged payload**, never a new ID.
No local queue promises delivery. Wait for the current request before sending
another message. No raw payload files are written by the worker.

## Bounds and lifecycle

Limits: 64 active/pending upgrades, 16 concurrent backend calls, 4 KiB messages,
one pending submission per connection and 30 messages/minute per connection.
Compression is disabled. Backend calls have a 3 second absolute deadline and
16 KiB response limit. Excess outbound buffering terminates a stalled peer.
Heartbeats every 30 seconds remove unresponsive peers. Python reauthorizes each
message; open sockets do not preserve revoked authority. Reconnecting resets
the per-connection rate counter. These bounds are not a capacity/abuse test.

SIGTERM stops admission, aborts backend calls, closes peers with code 1001 and
forces teardown after 5 seconds. It waits for upgraded sockets rather than
exiting when only HTTP closes. Container limits: 512 MiB, 64 processes and
0.5 CPU; V8 heap limit: 256 MiB. These are conservative review settings for the
1 OCPU/6 GiB server, not measured throughput claims.

The worker has no data volume and no Python signing, Stripe, Vault or document
secrets. Docker local named volumes are host-local storage, not network storage.
Python retains transactional data ownership. Session cookies travel only over
the dedicated host's internal Docker network/loopback. Multi-host deployment
requires a separate secure transport review. No NLB or paid resource is added.

## Local verification and optional packaging

```sh
python3 -m pip install -r requirements-server.txt
cd worker
npm ci --ignore-scripts
npm audit --omit=dev
npm test
cd ..
docker compose --profile ingestion config --quiet
docker compose --profile ingestion build
docker compose --profile ingestion up -d
```

The final commands start **local review containers** with loopback-only host
ports. `/healthz` reports liveness; `/readyz` remains 503 until Python's real
independent bindings verify. `depends_on` does not grant readiness. The optional
`deploy/nginx-ingestion.conf.example` belongs inside the genuine HTTPS server
block after certificates and the approved worker are installed. It forwards
actual Host/Origin/Cookie, strips forwarded identity claims and upgrades only
`/ingest`. Alias hosts cannot establish sockets. Existing Python paths use
`deploy/nginx.conf.example`. No TLS issuance/renewal service is provisioned here.

Node 24 is the selected supported LTS line. `ws` is pinned with registry integrity
in package-lock.json; Docker uses npm ci without install scripts. Base image
tags still require approved digest capture, dependency pairing and vulnerability
review at release. Source manifests remain unsigned; configuration grants no
independent source approval.

Tests exercise real WebSocket traffic against a disposable Python WSGI app and
real SQLite appointment store using explicitly fake test-only sessions/release
authority. They check idempotent receipts, conflicting reuse and extra-field
rejection. Fixtures are excluded from the worker image. Other cases cover
missing authority, host/origin/path/session denial, revocation, malformed/binary/
oversized frames, backend timeout/response bounds, connection/rate/in-flight
limits, heartbeat and shutdown.

Unverified: production authentication/bootstrap/signatures, ARM execution on
Oracle, host firewall, real TLS/renewal, public reachability and load/soak behavior.
Oracle, DNS and secrets have not been changed by this work.
