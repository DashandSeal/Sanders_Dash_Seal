> NOTE (2026-11-13, deploy/simultaneous-20261113): this file documents the
> deploy/immediate-20261113 branch. In the unified branch the nginx tripwire
> decision went the other way: the three `return 404` tripwires
> (/api/auth/verify, /api/transactions/process, /api/stream/transactions)
> are PRESERVED from upgrade/sota-web-nginx-20261113, so those paths return
> nginx 404, not the app's 404 JSON. The unified branch's nginx.conf uses
> container-DNS upstreams (wsgi-backend:8000, pipeline-worker:3000) from
> docker-compose.yml; the host-systemd path in this file needs those
> upstreams substituted with 127.0.0.1:8000 / 127.0.0.1:3000, or a Compose
> deploy. See docs/UNIFIED_DEPLOY_2026-11-13.md.

# Sanders Dash & Seal — immediate deploy notes (branch deploy/immediate-20261113)

Status: **build assembled and serve-tested locally; NOT deployed, NOT merged
to main.** This file is the handoff to the deploy worker.

## What this branch is

- Base: `upgrade/real-world-20261113` (200c6a6) + merge of
  `cleanup/deployment-placement-20261113` (5a7e308, clean) + merge of
  `rebuild/daedalus-20261113` (28521cb). Daedalus merge had 6 add/add
  conflicts; resolved by keeping the upgrade branch's versions (typed
  env config, probe-driven observed_profile, config-driven rate card,
  language allowlist) — the rebuild branch's copies were the older,
  less-guarded versions. The rebuild's unique wiring
  (`core_platform/daedalus_engine.py`, `core_platform/__init__.py`)
  merged cleanly.

## Single entry point

- `wsgi.py` — `app` / `application` = Stripe webhook WSGI app
  (`core_platform.stream_api.import_make_app`). Serves ONLY
  `POST /v1/payments/stripe/webhook`; every other path returns the app's
  own 404 JSON. `passenger_wsgi.py` and `backend/wsgi.py` are thin shims
  that import `application` from root `wsgi.py`.
- Gunicorn: `gunicorn --config deploy/gunicorn.conf.py wsgi:application`,
  bind `127.0.0.1:8000`, workers min(2*CPU+1, 3), sync, threads 2.
- Nginx: root `nginx.conf`, upstreams `127.0.0.1:8000`. TLS on 443 for
  sandersdashandseal.com / sanderslegalhelpersllc.com (host-managed certs).
- systemd: `deploy/systemd/sanders-dash-seal.service`
  (User/Group `sanders`, uid/gid 10001, WorkingDirectory
  `/opt/sanders-dash-seal`, EnvironmentFile
  `-/etc/sanders-dash-seal/environment`).

## Environment variables

- `STRIPE_WEBHOOK_SECRET` (whsec_...) — REQUIRED for the webhook to verify
  signatures. Unset = app still serves, webhook answers 503 (disabled).
- `STRIPE_LIVEMODE` — `false` (default, test events) or `true` (live only,
  and only with a LIVE secret).
- DO NOT SET (not read by this entry point): `STRIPE_API_KEY`,
  `ANTHROPIC_API_KEY`, `DAEDALUS_CLAUDE_MODEL`, `DAEDALUS_TIMEOUT_SECONDS`.

## Deploy worker — exact commands (Oracle Linux 9, Always Free VM)

```bash
sudo groupadd --gid 10001 sanders
sudo useradd --uid 10001 --gid 10001 --no-create-home \
  --home-dir /opt/sanders-dash-seal sanders
sudo mkdir -p /opt/sanders-dash-seal/data /etc/sanders-dash-seal
sudo chown -R sanders:sanders /opt/sanders-dash-seal
# copy this branch into /opt/sanders-dash-seal (git clone, branch
# deploy/immediate-20261113), then:
cd /opt/sanders-dash-seal
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
sudo install -d -m 0750 -o root -g sanders /etc/sanders-dash-seal
sudo install -m 0600 -o root -g sanders \
  deploy/systemd/sanders-dash-seal.environment.example \
  /etc/sanders-dash-seal/environment
# edit /etc/sanders-dash-seal/environment: real STRIPE_WEBHOOK_SECRET
sudo cp deploy/systemd/sanders-dash-seal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sanders-dash-seal
sudo cp nginx.conf /etc/nginx/nginx.conf   # after host certs exist
sudo nginx -t && sudo systemctl reload nginx
# verify:
curl -s http://127.0.0.1:8000/v1/payments/stripe/webhook -X POST -d '{}'
# -> 401 {"error":"missing_stripe_signature_header"} (app is up)
```

## Verified locally on this branch (2026-11-13)

- `gunicorn --check-config --config deploy/gunicorn.conf.py wsgi:application`
  → exit 0.
- Live gunicorn, no secret: every path → 503 `webhook_gateway_disabled`.
- Live gunicorn, test secret: signed test event → 200 `LEDGER_SETTLED`;
  duplicate → 200 `SUCCESS_ALREADY_PROCESSED`; bad signature → 401;
  unknown path → 404 `endpoint_not_found`; event row persisted in
  `data/ledger.db:stripe_processed_events`.
- Live nginx 1.30.6 (test cert, port 8443) → gunicorn: unsigned webhook
  → 401; signed webhook → 200 `LEDGER_SETTLED`; the three former tripwire
  paths return the app's 404 JSON (from an allowed client).
- `nginx -t` → syntax ok. `pytest tests/ sharpshooter/tests/` → 56 passed.
- `systemd-analyze verify` on the unit → no unit errors (only the expected
  "gunicorn binary not present on this dev VM" note).

## Still broken / not in this build

- `core_platform/native_runtime.py` still cannot run: line 141
  `RuntimeBindings(...)` mixes positional args after keywords, passes
  `auth_app` twice, uses a non-field `ORIGIN=`, and references
  `self.payments` (never assigned); its top-level imports (`from cases
  import ...`, `from deployment import ...`, etc.) name modules that do not
  exist at that path. Nothing in the serve path imports it. Line 130 was
  fixed (undefined `signwell_test_mode_settings` → `settings.get(...)`).
- The app serves ONLY the Stripe webhook. There is no `/api/auth/verify`,
  `/api/transactions/process`, `/api/stream/transactions`, dashboard, or
  Daedalus HTTP route in this build — those paths 404 by design.
  `/api/` in nginx is still restricted to `allow 10.0.0.0/24; deny all;`
  (pre-existing policy, left in place; external clients get nginx 403).
- Ledger handlers are stubs: `fulfill_checkout` / `record_subscription_renewal`
  / `process_reversal` are no-ops; only the idempotency row is recorded.
- `deploy/Dockerfile` is a real Dockerfile but was NOT build-tested
  (no Docker daemon on the build VM). Root `Dockerfile` is still 230 lines
  of Python — do not use it. `deploy.sh` / installer chain not fixed.
- Daedalus engine is present and unit-tested but has no HTTP route and no
  live provider call in this build; do not set its keys expecting traffic.
- Deploy host gotchas found during local testing: the venv and repo paths
  must be traversable/readable by uid 10001 (a restrictive umask 0007 home
  made lazy `stripe._webhook` imports fail with 500s under gunicorn
  workers); `data/` must be writable by that user (the unit's
  `ReadWritePaths` + `sanders`-owned `/opt/sanders-dash-seal/data` cover it).
