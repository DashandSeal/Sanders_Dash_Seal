# Sanders Dash & Seal

Official Sanders Dash & Seal platform source code and Platinum Blue Diamond architecture.
Legal entity: Sanders Legal Helpers LLC; platform identity: **Sanders Dash & Seal**.

## Current build

This development foundation implements selected mechanics from the October 11, 2026 actual build design. It is **not fully specification-conformant**; see [the audit](docs/SPEC_CONFORMANCE.md):

- Independent IT AI Manager and MINOTAUR Ed25519 approval verification.
- Agent proof of possession, exact payload/scope binding, maximum 60-second leases.
- Persistent atomic one-use claims, explicit revocation, and replay rejection.
- PBD manifest preparation/validation and integrity scanning, including `pbd_` files.
- Independent signed Quality Agent, reconciliation, and integrity evidence.
- Execution intent, result, and revocation records in a hash-linked audit chain.
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

See [authentication](docs/AUTHENTICATION.md), [build status](docs/BUILD_STATUS.md),
[source mapping](docs/SOURCE_MAPPING.md), and [governance](docs/GOVERNANCE.md).
No passwords, API secrets, private keys, or service credentials are committed.
