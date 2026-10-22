> October 22 owner correction: the custom authorize-release executable and SANDERS_RUNTIME_FACTORY are not deployment requirements. Earlier prerequisite language below is historical and superseded by infrastructure/resource-manager/README.md and the application installer. Business-operation authentication and authority controls remain separate.

# Existing platform deployment setup

October 21, 2026. This change supplies WSGI startup/composition for the existing
Python platform. It does not create a hosting subscription or publish the app.

## Entrypoints and domains

`wsgi:application` is a standard WSGI server target. `passenger_wsgi.py` exposes
the same application to Passenger where the hosting environment supports Python
and this repository's dependencies. No framework conversion is required.

| Host | Application behavior once DNS and hosting are configured |
|---|---|
| sandersdashandseal.com | Canonical platform origin |
| www.sandersdashandseal.com | Safe reads redirect to the canonical home |
| sanderslegalhelpersllc.com | Safe reads redirect to the canonical home |
| www.sanderslegalhelpersllc.com | Safe reads redirect to the canonical home |

An alias write is refused rather than replayed on another origin. Redirects
discard the request path/query to avoid forwarding sensitive or hostile request
targets. Unknown hosts are refused, including when forwarded headers claim an
allowed hostname. Configure the TLS frontend to enforce the same host allowlist,
issue certificates for all four names and redirect plaintext traffic to HTTPS.
These application rules do not create DNS records or certificates.

## Intentional default state

With no `SANDERS_RUNTIME_FACTORY` configured, startup exposes the existing
customer/operator static assets, `GET /healthz` and `GET /readyz`. Health reports
process liveness only. Readiness returns 503. All service APIs, authentication
routes and the payment webhook remain unavailable. No database, Stripe account,
signing identity, login credential or paid hosting resource is created.

This is diagnostic startup under the previously approved startup separation,
not an authenticated operational service or production-readiness attestation.
Do not publish this state as an operational booking/payment platform.

## Trusted production bindings

Install an administrator-controlled adapter package on the selected host. Set
`SANDERS_RUNTIME_FACTORY` in protected server configuration to its existing
`module:factory` reference. Never derive it from a request, customer field,
untrusted configuration file or uploaded document. An explicitly configured
factory must return a `core_platform.deployment.RuntimeBindings` instance; an
invalid reference, failed import or missing bindings fails startup.

The bindings supply:

- The existing `AppointmentStore` and `AppointmentPayments` sharing the same
  appointment object and protected SQLite database. Payments must use canonical
  origin `https://sandersdashandseal.com` for Checkout return URLs.
- A real independent session authenticator and auth application. The latter owns
  login, OIDC/session cookies, login CSRF and logout; the entry point does not
  invent customer identity or accept identity headers.
- A release verifier backed by actual independent artifact/runtime/integration
  evidence. Only literal `True` permits operations; exceptions and truthy values
  deny. Readiness is a result of this trusted verifier, not a boolean env flag.
- Optionally, the existing raw Stripe signature-verifying WSGI handler from
  `stripe_webhook_wsgi.make_app`, mounted at `/stripe/webhook`, with its existing
  ledger, protected signing secret and separate authorized enablement. The
  deployment wrapper also checks the release verifier on every webhook request.

The factory's implementation and production credentials are not present in this
change. No example that returns unconditional authorization is supplied. Source
and dependency authorization, authentic signatures, external bootstrap, enforced
runtime protection, persistent protected storage, backup/recovery and external
audit anchoring remain requirements. Loading a factory is not their enforcement.

## Deployment sequence

1. Locate a compatible Python runtime already available to the owner or resolve
   another owner-selected deployment route without an unapproved purchase.
2. Install the exact reviewed source and its dependencies in an isolated runtime.
   Complete the externally verified bootstrap and trusted adapter configuration.
3. Point a compatible WSGI server or Passenger at the supplied entry point.
4. Verify authentication, intake ownership, operator/fee/case authority, signed
   webhook settlement, failure/replay behavior and recovery through the real
   connections. Do not create a live charge as a test.
5. Obtain genuine required artifact approvals, configure the TLS virtual hosts,
   then set both domains' DNS using the actual host-issued values. Preserve
   unrelated mail, verification, domain-connect and nameserver records.
6. Verify public DNS, TLS, canonical routing and the complete authorized service
   journey before reporting the platform connected and operational.

No A record, CNAME target, signing key or provider secret is invented here.
