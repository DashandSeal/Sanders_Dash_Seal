# Sanders Corporations Secretary (SCS) — v0.1 working local prototype

**Owner-directed corporate intelligence and records platform.** This is a functional, local-first foundation for a sovereign event-driven corporate secretary, not a fully deployed autonomous AI.

## Features available now
- Five identity records: headquarters coordinating identity and four distinct operating companies.
- Colorado SOS entity identifiers for three LLCs; 2025 founding year for each LLC, 1996 for S & G Security Inc.
- Company-specific task management, notice/event intake, owner-only API access token.
- Live server-sent event stream for changes *recorded in this service*.
- Deterministic event analysis for grant notices, filing deadlines, and seal updates.
- SQLite persistence, tamper-evident hash-chained audit and verification endpoint.
- Interactive dark-blue/gold browser dashboard with accurate Sanders crest assets.
- GitHub-ready source layout and no credentials or client records committed.

## Run locally (Python 3.11+)
```
python -m pip install -r requirements.txt
python -c "import secrets; print(secrets.token_urlsafe(32))"
export SCS_API_TOKEN="PASTE_YOUR_RANDOM_VALUE_HERE"
python start.py
```
Open `http://127.0.0.1:8765/` and enter the same token. On PowerShell: `$env:SCS_API_TOKEN='your-token'; python start.py`.

## Useful endpoints
- `GET /api/companies`, `/api/seals`, `/api/tasks`, `/api/dashboard`, `/api/audit/verify`
- `POST /api/tasks`, `PATCH /api/tasks/{id}`
- `POST /api/events`, `GET /api/events`, `GET /api/live` (SSE)

Example event:
```
curl -H "X-SCS-Token: $SCS_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"company_id":"home_healthcare","kind":"filing.deadline","summary":"Review official grant filing deadline","payload":{}}' \
  http://127.0.0.1:8765/api/events
```

## Current status (read before publication)
- Records are seeded from user-provided business records, not a live state registry lookup.
- The seal artwork is included as preview assets; full electronic originals remain in the user's Library.
- "Real-time" refers to locally recorded events being streamed via SSE, not to live external portals or autonomous external work.
- AI model access and external connectors are **not active**. The advisor is presently transparent deterministic logic.
- The source is published publicly under `DashandSeal/Sanders_Dash_Seal/sanders-corporations-secretary/`. This public release contains code and public company identifiers only. Do not commit actual corporate records, keys, client data, or private business files.
- Authentication is a single owner token suitable for a localhost prototype, not production multi-user security.

## Project lineage
Designed to interoperate with the Sanders Synthetic AI & Sovereign Mesh Architecture without inventing or exposing reserved proprietary implementation details. The owner is the final decision-maker for the corporate entities.