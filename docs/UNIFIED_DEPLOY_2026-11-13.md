# Unified simultaneous-deploy branch — 2026-11-13

Branch: `deploy/simultaneous-20261113`, off `main` (`f4f72abe`).
Head at time of writing: merge of `deploy/immediate-20261113` (see `git log`).
NOT merged to main. NOT deployed. $0 spent, no secrets used.

## Merges (in order)

1. `cleanup/deployment-placement-20261113` (`2020ca55`) — clean
2. `rebuild/daedalus-20261113` (`ad2406cd`) — clean
3. `upgrade/real-world-20261113` (`200c6a6c`) — 6 add/add conflicts, all
   Daedalus modules; resolved by taking the real-world versions, which are
   strict supersets of the rebuild versions (typed transport config from
   env, probe-driven `observed_profile`, config-driven rate card,
   language allowlist in the runtime integration).
4. `upgrade/sota-python-deps-20261113` (`fee7f361`) — requirements
   conflicts; resolved to the newer pins (below).
5. `upgrade/sota-web-nginx-20261113` (`c44d60ce`) — Dockerfile/compose/
   requirements conflicts; resolved to the sota-web versions except
   gunicorn stays 27.0.1 (see table).
6. `upgrade/sota-daedalus-voice-20261113` (`969de1eb`) — one real
   conflict, `observed_profile` in `daedalus_l15_capabilities.py`;
   resolved with a single function accepting BOTH call styles (below).
7. `upgrade/sota-ci-platform-20261113` (`22b75db4`) — clean (3 files;
   no workflow files were in that branch, so no `.github/workflows`
   push was attempted).
8. `feature/audio-video-voice-20261113` (`15ecb07e`) — `daedalus_voice.py`
   add/add conflict; resolved by the voice split (below).
9. `deploy/immediate-20261113` (local `1dcf1dc`) — `nginx.conf`,
   `requirements.txt`, `daedalus_l15_capabilities.py` conflicts;
   resolved per the table below.

## Conflict choices (one consistent choice each)

| Conflict | Choice | Why |
|---|---|---|
| `daedalus_voice.py`: sota (465 lines, stdlib adapters, `run_voice_turn`) vs audio-video-voice (663 lines, WebRTC signalling validation, faster-whisper/Deepgram/Google TTS, `voice_api.py`, `web/voice.html`, 21 tests) | **AVV version is `core_platform/daedalus_voice.py`.** Sota version preserved unchanged as **`core_platform/daedalus_voice_pipeline.py`** (new file, header note explains the split). `daedalus_engine.build_voice_runner` and `core_platform/tests/test_daedalus_sota.py` now import from the pipeline module. | Both define `FakeTranscriber` with a different API, so one file cannot hold both. AVV covers audio+video+voice (the owner's directive) and the voice API depends on its API; the sota pipeline keeps `run_voice_turn` and the stdlib adapters. No capability was dropped. |
| `nginx.conf` tripwires: preserved (sota-web) vs removed (immediate) | **PRESERVED.** The three `return 404` locations (`/api/auth/verify`, `/api/transactions/process`, `/api/stream/transactions`) stay. The unified `nginx.conf` is the sota-web 293-line rewrite (rate limits, gzip, HSTS/security headers, HTTP->HTTPS + ACME, modern TLS, container-DNS upstreams). | 404 tripwire is the safer default for unimplemented endpoints (PR #30 recommendation); the sota-web config was the verified one (`nginx -t` PASS, live HTTPS 200 with HSTS). |
| `stream_api.py` `stripe.error` fix | **`from stripe import SignatureVerificationError`** (identical in sota-python-deps and immediate; merged cleanly). | Both branches made the same fix; no conflict. |
| gunicorn 26.2.0 vs 27.0.1 | **27.0.1** everywhere (`requirements-server.txt`; `Dockerfile.bozly` keeps 27.0.1 with the sota-web python 3.14 base). | 27.0.1 was verified via pip download in the real-world upgrade and is what the immediate deploy tested live. The sota-web 26.2.0 pin was stale (pre-dated the bump). |
| nginx 1.30-alpine vs 1.30.6-alpine | **1.30.6-alpine** in `compose.yaml`, `docker-compose.yml`, `deploy/compose.production.yml`, `nginx.conf` header. | 1.30.6 is the current stable with the 14 Oct 2026 security fixes; 1.30-alpine was the real-world intermediate pin. |
| Node 20.20.2 vs 24 | **24** (`node:24-alpine` in `worker/Dockerfile`, `node:24-bookworm-slim` in `deploy/preflight.Dockerfile`, `engines >=24` in `worker/package.json`). | Local Node is v24.22.1; worker JS passes `node --check` under 24 (see test section in the handoff report). `npm ci --omit=dev` replaces `--only` (removed in npm 11). |
| `observed_profile` signature: probe style (real-world) vs explicit style (sota) | **One function accepting both.** `observed_profile(probes=None, *, live_reasoning_configured=False, **states)`. Probes drive ACTIVE/UNAVAILABLE; explicit states override; unknown names rejected in both styles. | Both test suites call it with incompatible signatures; the unified signature keeps both suites green without forking the function. |
| `requirements.txt` stripe 15.6.0 vs 15.6.2; Flask/requests | **stripe 15.6.2, Flask 3.1.3, requests 2.34.2, PyJWT 2.15.1, cryptography 50.0.2.** gunicorn lives only in `requirements-server.txt` (27.0.1). | Newer pins, all verified via pip download in their source branches. |
| `requirements-dev.txt` cryptography range | **`cryptography>=50.0.0,<51.0.0`** (sota-web). | Narrows the real-world `>=46,<51` range to match the pinned 50.0.2. |
| `Dockerfile.bozly` python base | **python 3.14** (sota-web) + gunicorn 27.0.1 (real-world/immediate). | Newer base, current gunicorn pin; the two lines came from different branches and do not conflict semantically. |
| `docker-compose.yml` / `compose.yaml` | **sota-web versions** (nginx 1.30.6, `version:` key removed, services renamed `reverse-proxy`/`wsgi-backend`/`pipeline-worker`, wsgi-backend builds the real `backend/Dockerfile`, certbot v5.10.0 in production compose). | The sota-web rewrite fixes a build that could never run (root Dockerfile was a Python script) and aligns service names with `nginx.conf` upstreams. |

## Known caveats (not hidden)

- The unified `nginx.conf` uses **container-DNS upstreams**
  (`wsgi-backend:8000`, `pipeline-worker:3000`). That matches the
  Compose deployment in this branch. The host-systemd deploy path from
  `deploy/immediate-20261113` needs those upstreams substituted with
  `127.0.0.1:8000` / `127.0.0.1:3000`, or a Compose deploy. A note to
  this effect was prepended to `deploy/IMMEDIATE_DEPLOY_NOTES.md`.
- `core_platform/native_runtime.py` still cannot run (pre-existing;
  documented in the immediate notes). Nothing in the serve path imports
  it. `bozly_global_traceback.py` truncated, `app/grantwriter_mother.py`
  corrupt, `deploy.sh` unclosed `main()` — all pre-existing, unchanged
  by this branch (see the 2026-11-13 cleanup report).
- `.github/workflows/` were NOT touched in this branch (GitHub App 403
  on workflow writes, as before). The Gateway workflow still writes
  Shape B pairs and its push step exits 128; that failure is unchanged.
- `daedalus_voice.py` (AVV) and `daedalus_voice_pipeline.py` (sota)
  both exist and both define `FakeTranscriber` with different APIs.
  Import from the right one: voice API/tests use `daedalus_voice`;
  engine voice turns use `daedalus_voice_pipeline`.

## `.pbd.json` pairs

Shape A / `UNSIGNED_SOURCE_MANIFEST`, `payload_hash` = real sha256 of
the file bytes. No signatures fabricated. Regenerated 14 stale pairs
and created 6 new ones (including `core_platform/
daedalus_voice_pipeline.py` and `web/voice.html`) for files changed
vs `main`; 41 pairs already matched.
## Test results (this branch, 2026-11-13)

- `py_compile` over the 32 changed `.py` files vs main: **31/32 pass**.
  `core_platform/native_runtime.py` fails (line 141, positional arg after
  keyword) — pre-existing: main's copy fails too (at line 130; this branch
  fixed line 130 only). Nothing in the serve path imports it.
- `python -m unittest discover -s tests`: **72 passed, 0 failed**.
- `python -m unittest discover -s sharpshooter/tests`: **8 passed, 0 failed**
  (after applying the sota-ci workflow upgrades below; it was 7/8 before,
  because the workflow files the test guards had never landed).
- `python -m unittest discover -s core_platform/tests`: **41 passed,
  0 failed, 6 skipped** (Anthropic SDK not installed; SDK-path tests skip).
- `node --check` on all `worker/**/*.js` + `web/*.js` under Node v24.22.1:
  **all pass** — Node 24 choice validated for the worker.
- `nginx -t` (nginx 1.30.6, test self-signed cert, upstreams substituted
  127.0.0.1 for the container-DNS names): **syntax ok, test successful**
  (one warning only: `ssl_stapling` ignored, no OCSP URL in the test cert).
- `gunicorn --check-config --config deploy/gunicorn.conf.py wsgi:application`
  (gunicorn 27.0.1, venv with the branch's pinned deps): **exit 0**.
- Live gunicorn smoke (test secret only, stripe 15.6.2): unsigned webhook
  → 401 `missing_stripe_signature_header`; signed test event → 200
  `LEDGER_SETTLED`; duplicate → 200 `SUCCESS_ALREADY_PROCESSED`; bad
  signature → 401 `invalid_cryptographic_signature`; unknown path → 404
  `endpoint_not_found`.

## Workflow files (applied in this branch)

The sota-ci branch shipped a test (`sharpshooter/tests/test_ci_smoke.py`)
guarding workflow upgrades that had never landed (GitHub App 403 on
`.github/workflows/` writes), so the test failed 7/8 on its own branch.
Applied here, exactly as specified in
`docs/ci-platform-modernization-20261113.md` §2:

- `closeup_vmax_pipeline.yml`: checkout v4→v7, setup-python v5→v7,
  Python '3.10'→'3.12', added top-level `permissions: contents: read`.
- `verify-bozly-integrity.yml`: checkout v4→v7, setup-python v5→v7,
  Python "3.11"→'3.12' (it already had `permissions: contents: read`).
- `ci-sota.yml`: **new**, per that doc's §2 job list (py_compile scope,
  workflow YAML parse, sharpshooter pytest, pip-audit, worker JS tests).
  Node is 24 here, not the 22 named in the doc — the unified branch
  chose Node 24. `permissions: contents: read`, concurrency
  cancel-in-progress, no push/deploy/secrets.
- `parallel-build-verification.yml` (Architectural Integrity Gateway)
  was **NOT touched**: its push step and Shape B sync remain exactly as
  the test guards. Its proposed fix is still a diff in that doc, not
  applied. The Gateway will still fail on PR runs (exit 128) until the
  owner approves that fix.
- No `.pbd.json` pairs exist for any `.github/workflows/*.yml` in this
  repo, so none were created for these three files (consistent with
  repo state; the Gateway sync only covers .py/.tf/.xml/.html/.css/.js).

