# Security and privacy

SCS v0.1 is **local development software**, not a certified or production-hardening release.

- Bind only to loopback (`127.0.0.1`). Never forward port 8765 to the public Internet.
- Set `SCS_API_TOKEN` to a random private value; do not place it in source control, screenshots or public messages.
- Keep the SQLite file, internal records, client information, keys, and secrets **outside** GitHub.
- The source repository is public by owner direction. Keep confidential corporate archives in access-controlled storage separate from this repository. Review every commit for confidential content.
- Live event streaming only covers events received by the local SCS server. It does not imply external account or government portal access.
- The audit hash chain is a tamper-evident integrity check; there is no external timestamp anchor, notarization or independently verified digital signature in v0.1.
- Business actions such as filings, contracts, and financial transactions are not performed by this prototype.
- Before any public exposure: implement TLS, multi-factor identity, company-scoped roles, CSRF/XSS protections, service-to-service auth, encryption, monitoring, backups, recovery and a full threat model.