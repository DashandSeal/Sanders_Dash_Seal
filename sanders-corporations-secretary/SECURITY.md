# Security — Sanders Corporations Secretary v0.2

**This public repository holds software source only.** Keep credentials, private business files, private emails, client details, and databases outside GitHub.

- Require unique owner runtime token, network isolation and HTTPS for any remote deployment.
- Source text must be explicitly attributed to an entity and original source. No cross-entity access for company-scoped queries.
- Optional hosted reasoning sends selected evidence excerpts to the configured provider only after both server-side opt-in and per-question UI consent; no model credentials are included in source.
- Read-only public GitHub connector fetches a fixed endpoint; it does not use private GitHub permissions or publish company records.
- Event classification produces action proposals only; it cannot submit a regulatory filing, commit repository changes, send money or sign legal documents.
- SQLite's audit hash-chain helps detect row modification, not whole-file replacement. External immutable witness/backups are required for stronger assurance.
- Do not expose this version directly to the Internet: local single-token authorization is not production IAM. Before hosting, add per-user roles, CSRF protections as applicable, secret rotation, rate limiting, secure backups, and a hardened reverse proxy.