# Selected ingestion worker

The owner-selected generic Node/Python worker is worker/src/index.js. Its source,
provenance, Python API contract, packaging and validation are documented in
OWNER_STACK_STATUS.md. The earlier appointment-only worker is superseded.

Use docker-compose.yml for the service-unit / backup path, or compose.yaml for
the installer / bootstrap path. The two files are **not** identical and are
not interchangeable — see `docs/COMPOSE_RECONCILIATION.md` for the real
differences and which file each path uses. (Corrected 2026-11-13: the earlier
sentence claiming they were identical was wrong.) No changes to the owner's
supplied versions, Docker commands or Compose configuration were substituted.
The internal endpoints are /api/auth/verify and /api/transactions/process; Nginx
routes /ws to Node and other public service paths to the existing Python app.

Do not reuse the previous implementation's test results as validation of this
selected stack. See the current source-verification workflow's separate source,
backend/Nginx, full-stack build and selected-dependency audit jobs.
