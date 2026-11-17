# Sanders Dash & Seal

Official Sanders Dash & Seal platform source code and Platinum Blue Diamond architecture.
Legal entity: Sanders Legal Helpers LLC; platform identity: **Sanders Dash & Seal**.

## Current build

This development foundation implements selected mechanics from the October 11, 2026 actual build design. It is **not fully specification-conformant**; see [the audit](docs/SPEC_CONFORMANCE.md):

- Independent IT AI Manager and MINOTAUR Ed25519 approval verification.
- MASTER-shaped nested leases, UTC timestamps, explicit nonce, agent assertion, permitted verb/IP lists and deployment-supplied lifetime policy.
- Persistent atomic one-use claims, explicit revocation, and replay rejection.
- PBD manifest preparation/validation and integrity scanning, including `pbd_` files.
- Independent signed Quality Agent, reconciliation, and integrity evidence in MASTER-shaped receipt groups.
- Execution intent, result, and revocation records in a separate hash-linked audit store.
- Separate Labyrinth Shield containment state and MINOTAUR verification roles.

This is development source, not a deployed notarial service or the complete synthetic-AI platform.
Production manifests are deliberately unsigned and deployment is blocked pending separate authority signing.
The trusted test harness may exercise source with disposable test keys; it is not a production launcher.

## Run development tests

Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The development runner executes the exact independently signed source snapshot and binds its hash into the lease. It rejects unrelated callbacks and source substitution. It is not an OS sandbox or a production runtime.

**128 local tests pass.**

The customer appointment interface, operator quote review and Checkout handoff
are implemented in development. See [customer workflow](docs/CUSTOMER_APPOINTMENTS.md)
for runtime assembly and remaining production connections. No live appointment,
customer authentication or payment deployment is claimed.

See [authentication](docs/AUTHENTICATION.md), [build status](docs/BUILD_STATUS.md),
[source mapping](docs/SOURCE_MAPPING.md), and [governance](docs/GOVERNANCE.md).
No passwords, API secrets, private keys, or service credentials are committed.
