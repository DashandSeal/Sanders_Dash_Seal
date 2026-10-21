# Oracle deployment candidate — existing Sanders Dash & Seal

This packages the existing Python/WSGI application with an optional Node
ingestion transport (see INGESTION_WORKER.md). It has not been installed on
the Oracle server. No production approval,
credentials, DNS changes or live charges are supplied by this package.

## Reviewed source and actual host evidence

The owner supplied a running Oracle Linux 9 ARM instance, 1 OCPU and 6 GB RAM,
in Phoenix AD-1, with a public IPv4, internet gateway/default route and attached
NSG. The last saved NSG table showed destination ports 80 and 443, source ports
All. That evidence does not prove a listening application or successful egress.
Keep the existing network. Do not recreate it because a quick-action card remains.
Earlier Cloud Agent messages included auth endpoint timeouts and Run Command IAM
guidance; their current status and the actual host firewall remain unverified.

The owner subsequently supplied a complete Node/Python role proposal. The new
optional worker preserves Python as the transactional authority. It forwards
authenticated appointment requests to the existing API, with bounded transport
and no shared document/Vault volume. Generic dispatch_transaction behavior,
PM2 and NATS are not implemented. See INGESTION_WORKER.md for the exact contract
and separate readiness, identity and deployment requirements.

## Packaging and storage

Dockerfile installs the pinned server requirement and runs the existing
wsgi:application as UID/GID 10001. The build uses explicit COPY targets and an
allowlist context to keep keys, environment files, databases and uploads out.
Before production release, resolve the base image to a reviewed multi-architecture
digest and validate dependency provenance, including transitive dependencies.
The current tag is a review candidate, not a reproducible signed release.

compose.yaml publishes only host loopback 127.0.0.1:8000, drops capabilities,
sets no-new-privileges and a read-only root, and uses a persistent named volume
at /var/lib/sanders. The production factory must explicitly put every SQLite
database there: mounting a volume alone does not configure application paths.
Provision ownership and secrets without chmod 777 or root application processes.
The container has no Docker socket or privileged sidecar access.

Use one WSGI worker initially; do not preload shared SQLite connections. Gunicorn
receives SIGTERM through the container init and gets 30 seconds to drain requests;
Compose waits 40 seconds before force termination. This is bounded shutdown, not
zero-downtime or unlimited-duration streaming. No raw URLs are written by the
server access logger. Container logs rotate locally.

## Command access before host changes

Establish an authenticated access path using the owner's existing key or correctly
scoped OCI Run Command permissions. Never paste the private key into chat or the
repository. No credential or command access was available to this implementation
session; its direct TCP attempt returned Network is unreachable locally.

After connecting, deploy/preflight.sh is a read-only inspection script. It does
not install software, alter IAM, grant sudo, restart services or dump environment
variables. It uses bounded requests and the correct IMDSv2 URL. sudo -n only
attempts inspection commands; it does not confer missing permissions.

If Run Command is used, scope a dynamic group to the exact instance and use the
current Oracle instance-agent-command-execution-family guidance, with its
request.instance.id=target.instance.id restriction. Root compartment and identity
domain syntax must be checked in the actual tenancy. Do not paste placeholder
compartment names or grant tenancy-wide metrics access just to enable commands.
An IAM denial and a network timeout are distinct failures. Diagnose their current
evidence before changing policies. Do not restart the agent merely to hide errors.

## Local review commands (not a production launch sequence)

    python3 -m pip install -r requirements-server.txt
    python3 -m unittest discover -s tests -v
    python3 -m gunicorn --check-config --config deploy/gunicorn.conf.py wsgi:application
    docker compose config --quiet
    docker compose build
    docker compose up -d
    curl -H 'Host: sandersdashandseal.com' http://127.0.0.1:8000/healthz
    curl -H 'Host: sandersdashandseal.com' http://127.0.0.1:8000/readyz

Default /healthz is 200; /readyz and all service operations remain 503 without
trusted runtime bindings. Compose deliberately uses /readyz for its healthcheck,
so the default container is unhealthy. Do not change the check to liveness to
claim the application is ready. Stop with docker compose down; preserve volumes.
Never use down --volumes for an operational deployment or backup workflow.

## Production connections still required

Supply a reviewed administrator-controlled adapter package and factory, authentic
independent release/signing authorities, authentication/session implementation,
provider credentials and webhook integration. See DEPLOYMENT_SETUP.md for the
RuntimeBindings contract. Mount credentials as separately permissioned read-only
files or through an approved secret manager, outside the build context; add only
the intended adapter to the production image. Do not add unconditional True
verifiers, identity headers, fabricated signatures or public development login.

Verify actual SQLite backup/restore and authority revocation after recovery before
accepting customer records. No assumed environment variable changes database
paths. A production override and secret wiring depend on the real factory contract.
The Stripe SDK and independent provider SDKs, if used by that factory, must also
be explicitly pinned and installed after that adapter is identified.

## Firewall, proxy, certificates and domains

Inspect the active Oracle Linux firewall manager and interface zone first. If
firewalld is active, add only http and https to that interface's actual zone in
both runtime and permanent settings, then verify. Do not insert iptables rules
at an assumed numeric position, flush rules, disable SELinux, or use Debian's
netfilter-persistent as an Oracle Linux installation command. Opening ports does
not start a server or increase throughput. Check inherited subnet security-list
rules as well as the NSG. SSH access, if selected, should have a specific source.

deploy/nginx.conf.example is a host include template, not a full nginx.conf.
It rejects unknown hosts, redirects HTTP to the fixed canonical HTTPS home, and
proxies TLS traffic to loopback while preserving the actual allowed Host. It
discards client-supplied forwarding identities and retains app host validation.
The public IP is not added to the application's allowed hosts.

Provision and renew a genuine certificate covering all four names before enabling
the TLS block. Nginx alone does not automatically obtain Let's Encrypt certificates.
Use an ACME client with validated HTTP-01 or DNS-01 ownership. The HTTP challenge
path is explicitly provided. On Oracle Linux, configure only the necessary SELinux
proxy access if denied by observed policy, and validate nginx -t before reload.

Use the actual assigned host IP for both domain A records only after readiness
and TLS validation; retain unrelated mail and verification records. The current
IPv4 is ephemeral, so verify it again before DNS changes and plan its lifecycle.
No load balancer is needed for the initial one-server topology. Adding one does
not remove the backend failure point or prove high availability.

## Validation and remaining limits

The local runtime test exercises real HTTP through pinned Gunicorn, confirms
unknown-host rejection and closed operational routes, then checks SIGTERM exits
cleanly. Docker/Compose and Nginx binaries were unavailable in the local execution
environment, so image build, ARM execution, proxy syntax/TLS, persistence on the
host, and real integrations require their own checks. CI adds container validation
on an ephemeral runner; it is not a deployment or independent release attestation.

References: Oracle Linux 9 firewalld documentation; Oracle Running Commands on an
Instance and Getting Instance Metadata; Docker Compose service specification;
Gunicorn settings and signal-handling documentation. Existing MASTER and all
authority boundaries remain controlling.
