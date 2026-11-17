# Sanders Corporations Secretary — RTSA Core v0.2

**Public source / locally hosted owner-controlled corporate intelligence platform.** Built for the Sanders family of companies. The headquarters record coordinates the separate legal entities; no merger of legal identities is implied.

## What is implemented

1. **Evidence-based Secretary** — source-attributed local retrieval, company-scoped search, explicit no-evidence responses. Optional hosted model inference is implemented behind independent server-side and per-question opt-in switches.
2. **Live operational engine** — local event ingestion, server-sent event updates, automatic event classification, persistent corporate action proposals, and a read-only GitHub commit connector with idempotent synchronization.
3. **Corporate memory vault** — company-bound text records with original source reference, SHA-256 digest, public/internal classification, local SQLite storage. Record text is not checked into public GitHub.
4. **Governance** — owner review queue, no automatic filings, transfers, signing, or public publication; hash-chained local audit of mutations and reviews. Acknowledgment is not execution.
5. **Executive interface** — status of intelligence, provenance, per-company roster, queries, tasks, events, knowledge index, action review and seal index.

## Run locally (Python 3.11+)

```bash
python -m pip install -r requirements.txt
python -c "import secrets; print(secrets.token_urlsafe(32))"
export SCS_API_TOKEN="YOUR_LONG_UNIQUE_LOCAL_TOKEN"
python start.py
```

Browse to **http://127.0.0.1:8765/**, enter the same token and connect.

### Optional hosted reasoning

By default, the evidence engine runs **without sending corporate records to external AI**. To enable a compatible HTTPS chat-completions model provider, set these only on the server (never in GitHub):

```bash
export SCS_MODEL_API_URL="https://YOUR_TRUSTED_PROVIDER_ENDPOINT/v1/chat/completions"
export SCS_MODEL_NAME="YOUR_PROVIDER_MODEL"
export SCS_MODEL_API_KEY="YOUR_PRIVATE_SECRET"
export SCS_ALLOW_REMOTE_INFERENCE="true"
```

The owner must **also check** `Use owner-configured hosted reasoning` for each inquiry. Up to six relevant evidence excerpts may then be sent to the provider. Choose your provider and privacy terms accordingly. The adapter requires an HTTPS endpoint and does not authorize external actions.

## API paths

- Read-only: `GET /api/intelligence/status`, `/api/companies`, `/api/seals`, `/api/dashboard`, `/api/audit/verify`, `/api/knowledge/search?q=...`, `/api/actions`, `/api/connectors/status`
- Grounded inquiry: `POST /api/secretary/ask` with `{ "question": "What ...?", "company_id": "legal_helpers" }`
- Ingest record: `POST /api/knowledge` with `{ "company_id": "legal_helpers", "title": "Record", "body": "Full original text", "source_type": "owner_record", "source_ref": "local archive reference", "classification": "internal" }`
- Event: `POST /api/events` — automatically generates relevant action proposals; `/api/live` provides live SSE of local event changes.
- Owner review: `PATCH /api/actions/{id}` — `acknowledged` / `dismissed`, no external action execution.
- Public GitHub connector: `POST /api/connectors/github/sync` — reads only the latest public repository commit; creates a sourced event only if changed.

All business API routes require the owner token.

## Status and boundaries

- v0.2 is a **working, tested local RTSA foundation**. Not a deployed always-on autonomous corporate AI.
- The event stream is real time for locally written events. GitHub updates occur on manual sync by default; `SCS_GITHUB_POLL_SECONDS=300` enables automatic periodic polling while the app is running. Secretary-of-State, Gmail, SAM.gov and other live business connectors are not yet integrated.
- Hosted model inference functions only when the owner supplies a provider and enables remote inference; none is bundled or secretly connected.
- Internal sources and the SQLite database belong in the private *runtime data store*, not in the public repository.
- Corporate founding dates / entity IDs are user-provided records pending source verification where applicable. S & G Security Inc. has no verified SOS ID in this build.
- SHA-256 chain detects modification to its own stored history but is not a notarized signature or proof against full database replacement. Production deployment requires HTTPS, identity/roles, encrypted backups and a hardened external immutable audit sink.
- No independent legal, financial, filing, or signing authority is conferred on the software.

## Tests

```bash
python -m pip install pytest httpx
pytest -q
```

Source published in `DashandSeal/Sanders_Dash_Seal/sanders-corporations-secretary/` under the user's public-repo choice. Existing corporate logos are for brand identity. Treat the separate `PROPRIETARY_NOTICE.txt` as the owner's rights statement; public GitHub visibility does not automatically grant an open-source license.