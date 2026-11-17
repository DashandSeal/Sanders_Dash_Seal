# Sanders Corporations Secretary — architecture contracts

## Scope
A local event-driven corporate operations service, intended to serve the Sanders corporate family while keeping each legal entity separate.

- Headquarters is a coordinating brand/oversight record, not automatically a separate legal company.
- Sanders Home Healthcare & Caregivers LLC, Sanders Senior Living LLC, Sanders Legal Helpers LLC d/b/a Sanders Dash & Seal each have an independent entity ID and document boundary.
- S & G Security Inc. is the fourth operating company; its 1996 historical start must not be attributed to the three LLCs.

## Connection to established sovereign architecture
The broader Sanders Synthetic AI architecture is an external, separately governed system. This prototype is an **integration interface**, NOT an implementation or disclosure of unpublished proprietary internals. Extensions may be connected through reviewed adapters.

## Modules implemented in v0.1
1. **Registry**: owner-supplied company identifiers and seal library index.
2. **Audit**: per-write SHA-256 linked audit log with verify endpoint. Hash chain is tamper-evident, not an externally anchored or immutable ledger.
3. **Event stream**: authenticated Server-Sent Events for *locally recorded events*.
4. **Operations**: entity-scoped task registry, event intake, due notices, budget/filing signal routing stubs.
5. **Deterministic advisor**: transparent business-rule suggestions; no external large language model connected yet.
6. **Approval policy interface**: exposes which actions require the owner's direction; it does not act as a legal signer or alter external systems.

## Planned live adapters (not yet connected)
- GitHub repository archival: commit hashes, company-scoped document bundles, review status.
- Grants.gov/JustGrants: application status and deadline monitoring where officially accessible.
- State Secretary of State portals: entity information and filing alerts; only through lawful available APIs or documented processes.
- Gmail/notifications: notices with source references and owner-facing alert queue.
- Document engine: official letterhead and seal placement with versioned document history.
- AI analysis: optional model provider adapter with document grounding, strict company scope and human-visible citations.
- Owner sign-off, state sync and operational cryptographic signatures via an actual key-management service.

## Security model
By default bind to 127.0.0.1, require a bearer-equivalent secret in X-SCS-Token for all corporate data endpoints, keep `.env` and DB out of Git. Do not deploy this prototype to a publicly accessible host without TLS, individual users/roles, proper secret rotation, rate limiting, encrypted backups, compliance review, and connector permission scoping.