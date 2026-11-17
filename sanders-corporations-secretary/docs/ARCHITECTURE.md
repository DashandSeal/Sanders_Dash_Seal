# Sanders Corporations Secretary — RTSA Architecture v0.2

**System boundary:** this is a local, evidence-driven RTSA core; live external data is marked by source and retrieval time. Features not connected are labeled inactive instead of invented.

## Data plane

- `registry.py` stores five coordinating and legal identities, separate seal pointers, known SOS IDs.
- `db.py` manages SQLite registries for company tasks, events, source texts, proposals, read-only connector sync, and hash-chain audit. Documents and activity are local-only.
- `knowledge.py` indexes original source text and scores query terms within the requested company scope before producing citations. A multi-company owner query is explicit (company_id null).
- `intelligence.py` composes evidence-based answers and source references and automatically transforms certain event types into auditable action proposals. No proposal executes external changes.
- `model_adapter.py` optionally synthesizes source-grounded answers using an owner-configured HTTPS chat-completions provider. A server opt-in, provider configuration, and user checkbox are all required. Default is local retrieval, not an LLM.
- `connectors.py` reads one fixed public GitHub commit endpoint, validates commit identity, persists sync state and inserts source-attributed events only when changed.
- `main.py` exposes an authenticated API and an SSE stream over **locally captured** events.
- `app/static/index.html` is an executive command center displaying actual local state and external provider status.

## Security and governance

- Public GitHub source contains no live API keys or private documents.
- Every API route carrying business data requires `X-SCS-Token` matching the owner-provided runtime secret; a single token is localhost-only authentication.
- Every indexed document is explicitly scoped to one company, and each query can filter to only that entity.
- Action proposals are nonexecuting: review state is not legal filing, payment, signature, repository publication or company policy update.
- SHA-256 audit chain is tamper-evident *inside the database*, but does not protect against entire-file replacement or cryptographically establish an authorized signer's identity.
- Model endpoints are HTTPS only and are not enabled unless expressly configured. Source text is untrusted input; the system prompt instructs the provider to treat retrieved content as data and refuse embedded commands. Production tools must add hard enforcement for tool calls.

## Current and future stages

Implemented: local corporate memory, event intelligence, evidence retrieval, optional inference adapter, sourced public GitHub metadata, audit review queue, responsive dashboard and tests.

Not yet live by default: external LLM credentials, opt-in periodic GitHub polling, official filing portals, Gmail/CRM integration, multi-tenant authentication and immutable offsite audit backup. Build those as distinct adapters with owner-granted permissions; do not claim an external system is connected until verified.