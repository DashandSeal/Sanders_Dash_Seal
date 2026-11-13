# tests/ — the single home for Python tests

Run from the repo root with the venv that has stripe installed:

```sh
~/workspace/sds-p0-work/venv/bin/python -m unittest discover -s tests -v
```

All tests use fake providers only: fake `whsec_test_...` webhook secrets,
locally computed HMAC signatures, temp SQLite files. No live keys, no live
Stripe calls, no network.

## What lives here (P1, 2026-11-13)

- `test_p1_secrets.py` — no literal webhook secret in code or compose files;
  `wsgi.create_native_application()` raises when `STRIPE_WEBHOOK_SECRET` is
  missing; `deploy/refresh_provider_secrets.write_runtime_env` writes the
  systemd env file (0600) from Vault provider data.
- `test_p1_wsgi.py` — repaired WSGI entry: diagnostic `/healthz` 200 /
  `/readyz` 503 / stream 503 without bindings; webhook GET 405, missing/bad
  signature 401, valid signed event settles and replays idempotently.
- `test_p1_ledger_dispatch.py` — `stream_api.py` fails closed with 503
  `ledger_method_unavailable` when the ledger lacks the method for the event
  type (including the real `PaymentLedger`, which still has none of the three
  methods), instead of AttributeError → 500.
- `test_p1_sentinel_traceback.py` — integrity patrols no longer list the
  never-existent `bozly_global_cfo.py`; `bozly_global_traceback.py` (restored
  from git history) compiles and imports; `app/grantwriter_mother.py` is gone.

## Why worker/test/ and sharpshooter/tests/ were NOT moved here

The P1 task allowed documenting the split with a real reason instead of
moving them, and moving them would break their owners:

- `worker/test/` is the pipeline worker's own suite, run by
  `worker/package.json` (`"test": "node --test test/*.test.js"`) and by the
  preflight compose service. Its tests import `../src/*` by relative path
  (`require('../src/webrtc')`, the `python_fixture.py` used by the worker
  integration tests). Moving them under `tests/` would break those relative
  imports and the worker's `npm test` command. Run them with
  `node --test worker/test/*.test.js` from `worker/` — the WebRTC signaling
  tests (the voice/video transport on this branch) pass 3/3.
- `sharpshooter/tests/test_core.py` imports `sharpshooter.core` as a
  top-level package (`from sharpshooter.core import ...`) and is the
  sharpshooter suite's own test. Moving it under `tests/` would break that
  import layout. Run it with `python -m unittest discover -s
  sharpshooter/tests -v` from the repo root.

## Conflict note: repo AGENTS.md rule 8

The repo's `AGENTS.md` rule 8 says "Do not add, restore or run tests as part
of Sanders build work". That conflicts with the P1 assignment from the
coordinator, which explicitly requires real tests and reporting pass/fail per
test. The coordinator's task was followed (tests were added and run); the
conflict is recorded here rather than silently obeyed or silently ignored.
These tests are not a gate on delivering code — they are verification evidence
for the P1 repairs, and nothing in this branch makes a test pass a condition
of building, installing, or starting the platform.

## Not covered here (honest gaps)

- **Daedalus chain:** no Daedalus code exists on this branch at all (no
  `daedalus_*` module anywhere in the tree), so no Daedalus test can be
  written honestly here. The Daedalus rebuild lives on the separate branch
  `rebuild/daedalus-20261113` (commit `ad2406cd`, not merged); its tests
  belong with that branch.
- **Voice/audio/video beyond WebRTC signaling:** no voice, STT, TTS, or video
  implementation exists on this branch. The WebRTC signaling tests in
  `worker/test/webrtc.test.js` (session-scoped SDP/ICE routing, 3 tests) are
  the only voice/video-adjacent tests that exist here and they pass. The
  voice implementation lives on the separate branch
  `feature/audio-video-voice-20261113` (not merged); its 21 tests belong
  with that branch.
- **Live paths:** no Docker build, no Oracle host run, no live Stripe call
  was attempted. Those remain owner/environment verification.
