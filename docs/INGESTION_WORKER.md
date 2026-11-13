# Selected ingestion worker

The owner-selected generic Node/Python worker is worker/src/index.js. Its source,
provenance, Python API contract, packaging and validation are documented in
OWNER_STACK_STATUS.md. The earlier appointment-only worker is superseded.

Use docker-compose.yml (compose.yaml is identical). No changes to the owner's
supplied versions, Docker commands or Compose configuration were substituted.
The internal endpoints are /api/auth/verify and /api/transactions/process; Nginx
routes /ws to Node and other public service paths to the existing Python app.

Do not reuse the previous implementation's test results as validation of this
selected stack. See the current source-verification workflow's separate source,
backend/Nginx, full-stack build and selected-dependency audit jobs.
