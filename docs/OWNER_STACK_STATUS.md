# Owner-selected Node/Python design: source assembly

The selected design is now assembled on the review branch. It is not installed
on Oracle and has not been merged into main. No paid service has been added.

## Owner-provided definitions

- worker/package.json retains the owner's exact Node engine and ws 8.16.0 pin.
- worker/Dockerfile retains the supplied node:20.12.2-alpine multi-stage definition.
- docker-compose.yml retains the supplied three service definitions, names,
  restart policies, network, volumes and configuration. compose.yaml now matches
  it byte-for-byte so default selection does not start the assistant's old stack.
- worker/src/index.js incorporates the supplied latest receipt, Python request,
  heartbeat and shutdown code. The imports, diagnostics, upgrade verification,
  session attachment, initial message parsing and pong handler are explicitly
  identified assembly code, using the earlier complete worker as the starting
  structure. This assembled file is not claimed to be one verbatim original file.

The old worker/src/worker.js and prior tests remain versioned historical code;
index.js no longer imports it. The selected image does not execute that module.

## Connecting code added

- Python /api/auth/verify calls the independently supplied authentication adapter.
  Its internal response carries the credential as session data; Python rechecks
  that credential on every /api/transactions/process submission. Node does not
  grant an actor, role or notarial authority by posting a session object.
- Generic transactions are passed intact to an independently supplied Python
  transaction_processor(transaction, actor, sqlite_connection). This is not
  restricted to appointments. A request_id is required for durable idempotency.
  The processor must validate its operation and permissions, retain distinct
  audit/authority duties and write transactional state using this connection.
  Irreversible external calls require an idempotent/outbox design of their own.
- Python records the processor's result and receipt in pipeline_receipts in the
  same SQLite transaction. Exceptions roll back; conflicting request ID reuse
  is rejected. A receipt means recording, not a notarial act or payment approval.
- RuntimeBindings exposes transaction_processor and transaction_store. The
  backend's SQLITE_DB_PATH supplies the default receipt store when the trusted
  factory supplies a processor. No production factory, identity or signature is
  fabricated. Missing independent authority continues to return 503.
- backend/Dockerfile and wsgi.py package the existing Python platform. Because
  the owner's build context is ./backend, platform-source.json is a reproducible
  source snapshot of the existing core and web files, not a rebuilt platform.
  backend/refresh_sources.py regenerates it; tests reject stale snapshots.
- nginx.conf is a full container configuration: public HTTP challenge/redirect,
  genuine TLS certificate paths, canonical/alias routing, /ws WebSocket upgrade
  to Node, and existing REST/forms/assets to Python. The two Node-to-Python
  endpoints are internal and not directly published through Nginx.
- package-lock.json now matches the owner's exact ws pin. Source manifests are
  updated without inventing approval signatures.

## Validation and actual remaining work

Local checks cover JSON/YAML parsing, JavaScript syntax, Python regression tests
and the selected Node process talking over HTTP to the real Python transaction
app and SQLite store with disposable test credentials. Tests verify recording,
repeat receipt, conflicting retry, invalid operation/frame, denied credentials,
revocation, release denial and rollback. These checks do not prove throughput.

The supplied worker Dockerfile still copies only package.json before npm ci;
its build therefore lacks the required lockfile at that step. The definition is
preserved, and CI reports the real build result rather than silently changing it.
The selected dependency audit is a separate visible CI job. No clean audit or
successful full-stack build is claimed from previous test results.

Real production authentication, authorized operation processors and source
signatures must come from the existing independent authority setup. The named
certificate volume must contain real certificate/key files covering the four
configured domain names; Nginx does not issue certificates itself. Browser-native
WebSocket clients cannot set an Authorization header directly; the assembled
handshake currently uses that header and needs a separately specified browser
credential exchange if browser sockets are desired. No such exchange is invented.

Oracle access, ARM execution, host firewall checks, TLS provisioning/renewal and
DNS cutover remain unperformed. Existing infrastructure is unchanged. The
architecture adds no required paid load balancer, database, hosting subscription
or software license. Oracle usage remains within the owner's free-resource plan.
