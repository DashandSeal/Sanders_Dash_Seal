# Compose-file reconciliation — Sanders Dash & Seal

**Date:** 2026-11-13 (P3). **Status: DOCUMENTED, NOT CONVERGED.** No compose
file was deleted, renamed or rewritten in this pass: all three variants are
accounted for below, two of them are load-bearing on different paths, and a
safe convergence needs the owner decision and the migration steps in §4.
All three files parse as valid YAML (verified with PyYAML; no Docker binary
exists in this VM, so `docker compose config` could not be run).

## 1. The false claim being corrected

Several docs claimed `compose.yaml` and `docker-compose.yml` are "identical"
or "match byte-for-byte" (`docs/OWNER_STACK_STATUS.md`,
`docs/INGESTION_WORKER.md`, `docs/FORENSIC_SECURITY.md`). That was false.
The three files differ in service names, container names, networks, volumes,
build contexts and environment handling. The false sentences were corrected
in place on 2026-11-13; this document is the evidence.

## 2. Real differences (verified by diff and YAML parse)

All three define `version: '3.8'` and pin `nginx:1.25-alpine` for the proxy
(the 1.25 pin is itself stale — 1.25 went EOL May 2024 — but updating the
image is out of scope for this P3 pass and is recorded, not changed).

| Aspect | `docker-compose.yml` (1,866 B) | `compose.yaml` (1,652 B) | `Sanders_Dash_Seal` (1,024 B) |
|---|---|---|---|
| Services | reverse-proxy, wsgi-backend, pipeline-worker | reverse-proxy, pipeline-worker, wsgi-backend | nginx-edge, wsgi-core (no pipeline-worker) |
| Proxy container | `sds_nginx_edge` | `sds_reverse_proxy` | `sds_nginx_edge` |
| Proxy network | `sds-secure-bridge` (named `sds_isolated_network_perimeter`) | `sds_production_network` | `network_mode: "host"` (no network) |
| Proxy cert volumes | host path `/etc/letsencrypt:/etc/letsencrypt:ro` | named volumes `certs_volume`, `certbot_validation_volume` | host path `/etc/letsencrypt:/etc/letsencrypt:ro` |
| wsgi-backend build | root `Dockerfile` | `backend/Dockerfile` | root `Dockerfile` |
| wsgi-backend container | `sds_wsgi_core` | `sds_wsgi_backend` | `sds_wsgi_core` |
| wsgi-backend env | `STRIPE_WEBHOOK_SECRET=${...:?…must be set…}` (hard-required), `OPERATOR_EMAIL=daddydik323@gmail.com` | `STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}` (empty default; app fails closed), `SQLITE_DB_PATH=/app/data/sds_production.db`, no `OPERATOR_EMAIL` | `STRIPE_WEBHOOK_SECRET=${...:?…must be set…}` (hard-required), no `OPERATOR_EMAIL` |
| wsgi-backend volumes | `sds-ledger-volume:/app/data` + `.:/app` (whole repo bind-mounted) | `sqlite_storage:/app/data:rw` only | `sds-ledger-volume:/app/data` + loopback port `127.0.0.1:8000:8000` |
| pipeline-worker | build `./worker/Dockerfile`, `PYTHON_BACKEND_URL=http://wsgi-backend:8000` | identical worker definition (same container name, env, build) | **absent** |
| Volumes defined | `sds-ledger-volume` | `certs_volume`, `certbot_validation_volume`, `sqlite_storage` | `sds-ledger-volume` |

Notes:

- Service names `wsgi-backend` / `pipeline-worker` in both `docker-compose.yml`
  and `compose.yaml` match the upstreams in `nginx.conf`, so either file's
  service discovery works — but container names, networks and volumes differ,
  so the two stacks are **not** interchangeable: data written under
  `sds-ledger-volume` is not visible to the `sqlite_storage` stack and vice
  versa, and `sds-secure-bridge` and `sds_production_network` are separate
  networks.
- `Sanders_Dash_Seal` is the oldest variant: pre-rename service names
  (`nginx-edge`, `wsgi-core`) that match nothing `nginx.conf` proxies to,
  host networking on the proxy, and no worker service at all.
- Both live files pin `nginx:1.25-alpine`. The real-world upgrade branch
  (`upgrade/real-world-20261113`) moved nginx to 1.30-alpine in its own
  files; that upgrade is unmerged, so the pins here are unchanged.

## 3. Which file is canonical for which path (verified references)

| Path | Canonical file | Evidence |
|---|---|---|
| Installer / bootstrap | **`compose.yaml`** | Root `deploy.sh` `compose()` uses `-f compose.yaml -f deploy/compose.production.yml` and states "docker-compose.yml defines different service names and is not used here"; `deploy/install_application.sh` runs bare `compose config/build/up` with no `-f`, so Docker Compose's default file lookup selects `compose.yaml` (it precedes `docker-compose.yml`); `deploy/refresh_provider_secrets.py` restarts with `-f /opt/sanders-dash-seal/compose.yaml` and comments "compose.yaml is the file the stack runs under" |
| Legacy services / backup | **`docker-compose.yml`** | `deploy/deploy.sh:47` checks for `docker-compose.yml`; `deploy/ledger_backup.py:119` runs `docker compose -f /opt/sanders-dash-seal/docker-compose.yml`; `deploy/sanders_manager.service:27–29` and `deploy/systemd/sanders-ai-observe.service:9` both pass `-f docker-compose.yml -f deploy/compose.production.yml`; the Gateway workflow (`.github/workflows/parallel-build-verification.yml:36`) lists `docker-compose.yml` (not `compose.yaml`) as a structural file in its paths filter; `docs/ORACLE_BOOTSTRAP.md` uses `docker-compose.yml` in its operator commands |
| Nothing | `Sanders_Dash_Seal` | Zero runtime references anywhere (code, services, workflows, installer). Only mention is the P1 test pinning its content. Stale duplicate. |

So the repo currently has **two live stacks that disagree**: the installer
deploys `compose.yaml`, while the service units and the backup job address
`docker-compose.yml`. On a host where both paths run, they would manage
different containers, networks and volumes under the same project name
`sanders-dash-seal`. That split is the real defect — not the existence of
three files as such.

## 4. Proposed single canonical file (migration note — NOT applied)

**Proposal: converge on `compose.yaml`.** Reasons: it is the file the
installer/bootstrap path already uses (the path that actually creates the
stack); its wsgi-backend builds `backend/Dockerfile` (the container-context
Dockerfile, which does not bind-mount the whole repo into the container);
its secret handling fails closed in the app instead of hard-requiring the
variable at compose time; and its named volumes are explicit.

Migration steps required before `docker-compose.yml` can be retired (owner
decision; each step is a real change, none was made here):

1. `deploy/deploy.sh` (legacy sync script): change its `docker-compose.yml`
   check to `compose.yaml`, or retire the script if the root bootstrap
   supersedes it (it is a different file from root `deploy.sh` — see P2).
2. `deploy/ledger_backup.py:119`: change the `-f` argument to
   `/opt/sanders-dash-seal/compose.yaml`.
3. `deploy/sanders_manager.service:27–29` and
   `deploy/systemd/sanders-ai-observe.service:9`: change `-f
   docker-compose.yml` to `-f compose.yaml`. (Verified 2026-11-13:
   `install_application.sh:125–131` *does* install and enable
   `sanders_manager.service`; its WorkingDirectory is already the correct
   `/opt/sanders-dash-seal` and it already has an `EnvironmentFile` — the
   older cleanup claims to the contrary were fixed on the P0/P1 branches.
   The only change this unit needs for the migration is the `-f` argument.)
4. `.github/workflows/parallel-build-verification.yml:36`: change the watched
   path to `compose.yaml`.
5. `docs/ORACLE_BOOTSTRAP.md` operator commands: change `-f
   docker-compose.yml` to `-f compose.yaml`.
6. Decide the `OPERATOR_EMAIL` difference: `compose.yaml` drops it;
   confirm nothing in the container needs it before deleting the
   `docker-compose.yml` definition.
7. Decide the volume migration: existing ledger data lives in
   `sds-ledger-volume` (`sds_production_ledger_data`); the `compose.yaml`
   stack uses `sqlite_storage`. Either rename the volume in `compose.yaml`
   to keep the data, or copy the data over once. **Do not delete
   `docker-compose.yml` until the data question is answered.**
8. Delete `Sanders_Dash_Seal` (no migration needed — nothing references it)
   and update the P1 test that pins its content
   (`tests/test_p1_secrets.py` interpolation assertions).
9. After the migration, re-test: `docker compose -f compose.yaml config`
   on a host with Docker, plus the `tests/` suite and the backup `--check`
   path.

**Blocked on:** owner approval of `compose.yaml` as canonical, the volume /
data decision (step 7), and the `deploy/deploy.sh` vs root `deploy.sh`
decision carried from P2. No Docker binary exists in this VM, so no live
`compose config` verification was possible here.

## 5. P2 decision and convergence (2026-11-13, branch `fix/everything-20261113`)

**Decision (this branch): `compose.yaml` is canonical.** The installer /
bootstrap path already uses it, and Docker Compose's default file lookup
selects it first. This is a branch decision recorded here, not a deletion:
`docker-compose.yml` is still present and still load-bearing for the
legacy-service / backup path (`deploy/ledger_backup.py:119`,
`deploy/sanders_manager.service`, `deploy/systemd/sanders-ai-observe.service`),
and `Sanders_Dash_Seal` is still present (stale, nothing references it).

**Convergence applied in P2 (safe, no file deleted):** the ledger volume
in `compose.yaml` was renamed from `sqlite_storage` to
`sds-ledger-volume` (explicit name `sds_production_ledger_data`), the
same volume `docker-compose.yml` uses. The installer stack and the
legacy/backup stack no longer keep separate ledger data. Migration note:
a host that previously ran the `compose.yaml` stack under the old volume
name must copy that data into `sds-ledger-volume` once; the old volume
is orphaned, not deleted, by this change.

**Still owner decisions (unchanged from §4):** steps 1–6, 8–9 of the
migration (repointing `deploy/deploy.sh`, `deploy/ledger_backup.py`,
the two service units, the Gateway workflow path filter, and
`docs/ORACLE_BOOTSTRAP.md`; the `OPERATOR_EMAIL` difference;
deleting `Sanders_Dash_Seal` and updating the P1 test that pins it;
re-testing with `docker compose -f compose.yaml config` on a Docker
host). The `deploy/deploy.sh` vs root `deploy.sh` decision is still
open from P2: they are different files and root `deploy.sh` is the
owner-documented bootstrap, so no forced move was made.
