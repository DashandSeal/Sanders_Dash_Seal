# CI / platform modernization — 2026-11-13

Branch: `upgrade/sota-ci-platform-20261113`, off main `f4f72abe`.
Owner: Roosevelt Sanders (sole owner). Nothing here merges, deploys,
spends money, or adds secrets. The Gateway workflow file was NOT edited;
its fix is a proposed diff only (§3).

## 1. Outdated CI inventory (main `f4f72abe`, verified 2026-11-13)

Only three files under `.github/workflows/` are real workflows. Two more
workflow-shaped files sit at the repo root (`expressway-sync.yml`,
`verify-bozly-integrity.yml`); GitHub Actions never runs files outside
`.github/workflows/`, so they are inert until moved — see §5.

Latest majors verified against upstream release pages on 2026-11-13:

| Action | On main | Latest major (2026-11-13) | Latest tag seen |
|---|---|---|---|
| `actions/checkout` | v4 (6 uses) | **v7** | v7.0.1 |
| `actions/setup-python` | v5 (5 uses) | **v7** | v7.1.0 |
| `actions/setup-node` | not used | **v7** | v7.1.0 |
| `actions/upload-artifact` | not used | **v7** | v7.0.2 |
| `actions/download-artifact` | not used | **v7** | (same generation as upload-artifact) |
| `actions/cache` | not used | **v6** | v6.1.0 |
| `dorny/paths-filter` | v3 (1 use, Gateway only) | **v4** | v4.0.3 |

Why v4/v5 are outdated, not just old: v4/v5 run on the Node 20 action
runtime, which GitHub deprecated in 2026 (forced to Node 24, then removed);
v6/v7 are the Node 24 / ESM generations. v7 of setup-python also removes
the `pip-install` input, and v7 of setup-node changes `NODE_AUTH_TOKEN`
handling — neither affects this repo (neither input is used).

Runtimes in use on main:

| Runtime | On main | Status 2026-11-13 |
|---|---|---|
| Python 3.10 (`closeup_vmax_pipeline.yml`) | **END OF LIFE 2026-10-01** (final 3.10.22, no more fixes) | must move |
| Python 3.11 (`verify-bozly-integrity.yml`) | security fixes only, EOL Oct 2027 | move now, cheap |
| Python 3.12 (Gateway) | security fixes only, EOL Oct 2028 | current platform pin |
| Python 3.13 / 3.14 / 3.15 | unused | 3.13 security-only to Oct 2029; 3.14/3.15 still get bugfixes |
| Node | not pinned in any workflow; `worker/package.json` engines `>=20` | Node 20 is EOL; Node 22 is the active LTS used by the new CI |

## 2. What was upgraded on this branch

| File | Change |
|---|---|
| `.github/workflows/closeup_vmax_pipeline.yml` | `checkout@v4`→`@v7`, `setup-python@v5`→`@v7`, Python `'3.10'`→`'3.12'`, added top-level `permissions: contents: read` (it only reads the repo and calls a webhook). No step logic changed. |
| `.github/workflows/verify-bozly-integrity.yml` | `checkout@v4`→`@v7`, `setup-python@v5`→`@v7`, Python `"3.11"`→`'3.12'`. No step logic changed. It already had `permissions: contents: read`. |
| `.github/workflows/ci-sota.yml` | **New.** checkout v7 + setup-python v7. Four jobs: (1) strict `py_compile` over the known-good scope on Python 3.12+3.13 + YAML parse of all workflows + advisory full-tree compile; (2) `pytest sharpshooter/tests/` on 3.12; (3) `pip-audit` over `requirements.txt` + `requirements-server.txt`; (4) worker JS tests on Node 22 (`npm ci` + `npm test`, advisory — see §4). `permissions: contents: read`, concurrency cancel-in-progress. No push, no deploy, no secrets. |
| `sharpshooter/tests/test_ci_smoke.py` (+ `.pbd.json` pair) | **New.** Stdlib-only smoke test: own Shape A pair integrity (real sha256), upgraded workflows pin checkout v7 / setup-python v7, Gateway push step still present (guards that the §3 fix is proposal-only until approved). |
| This file | Inventory, proposals, blockers. |

Not changed: `parallel-build-verification.yml` (Gateway — proposal only, §3),
`expressway-sync.yml` (root, inert — §5), any application code, any
`requirements*.txt`, no secrets.

## 3. Architectural Integrity Gateway — proposed fix (NOT applied)

File: `.github/workflows/parallel-build-verification.yml`. Do not apply
without the owner's decision; the workflow file read did not pass a safety
check, so this is a diff to review, not a change.

Failure being fixed: `Securely Push Verified Manifest Assets` exits 128
on PR runs (run 43464067282, job 132018579559). The push fails, not the
pairs: on a PR run the step tries `git push origin main` from a PR
checkout, which the PR-run token cannot do. The same file's sync step
also writes non-canonical pairs (`"sha256"` key) instead of the canonical
Shape A (`"payload_hash"` + scope + `UNSIGNED_SOURCE_MANIFEST`), so
Gateway-generated pairs disagree with the pairs on main.

```diff
 --- a/.github/workflows/parallel-build-verification.yml
 +++ b/.github/workflows/parallel-build-verification.yml
 @@ jobs: analyze-changes
        steps:
          - name: Checkout Source Code
 -          uses: actions/checkout@v4
 +          uses: actions/checkout@v7
          - name: Categorize Modified Files
            id: filter
 -          uses: dorny/paths-filter@v3
 +          uses: dorny/paths-filter@v4
 @@ jobs: platform / sidecar / reconcile-and-sign (each checkout + python step)
 -        uses: actions/checkout@v4
 +        uses: actions/checkout@v7
 -        uses: actions/setup-python@v5
 +        uses: actions/setup-python@v7
          with:
            python-version: '3.12'   # unchanged
 @@ step: Execute Signatures Sync
                  if f_path.exists():
                      f_hash = hashlib.sha256(f_path.read_bytes()).hexdigest()
 -                    data = {"body": {"schema": 1, "platform": "Sanders Dash & Seal", "artifact": target, "sha256": f_hash}}
 +                    data = {
 +                        "body": {
 +                            "schema": 1,
 +                            "platform": "Sanders Dash & Seal",
 +                            "artifact": target,
 +                            "payload_hash": f_hash,
 +                            "scope": {
 +                                "endpoint": "local://development",
 +                                "method": "TEST",
 +                                "ip": "127.0.0.1",
 +                                "operation": "DEVELOPMENT_VALIDATION",
 +                            },
 +                        },
 +                        "signatures": {},
 +                        "status": "UNSIGNED_SOURCE_MANIFEST",
 +                    }
                      with open(e_path, "w") as f:
                          json.dump(data, f, indent=4)
 @@ step: Securely Push Verified Manifest Assets
        - name: Securely Push Verified Manifest Assets
 +        if: github.event_name == 'push'
          run: |
            git config --global user.name "Sanders Platform Watcher"
            git config --global user.email "rooseveltsanders381@gmail.com"
            git add "**/*.pbd.json"
            if ! git diff-index --quiet HEAD; then
              git commit -m "Auto-extracted, sorted, and cryptographically signed assets [Verified Suite]"
              git pull --rebase origin main
 -            git push origin main
 +            git push origin HEAD:${{ github.ref_name }}
            else
              echo "No changes to commit. Working tree is clean."
            fi
```

Effect: PR runs never push (no exit 128, no surprise commits to main
from a PR); push events still sync verified manifests to the branch that
triggered them; emitted pairs are canonical Shape A. Open follow-up, not
in this diff: the sync glob rewrites a pair for every `.py`/`.tf`/`.xml`/
`.html`/`.css`/`.js` file in the tree, which will keep regenerating pairs
for files whose canonical pairs already exist — narrowing that glob to
the listed structural targets needs an owner decision.

## 4. Local test results (this branch, 2026-11-13)

- Workflow YAML: all 4 `.github/workflows/*.yml` files parse (`yaml.safe_load`). PASS.
- `pytest sharpshooter/tests/` (pytest 9.2.0, Python 3.12.3): **8 passed**
  (5 pre-existing `test_core.py` + 3 new `test_ci_smoke.py`).
- Strict `py_compile` scope from `ci-sota.yml`: PASS on Python 3.12
  (`wsgi.py`, `core_platform/deployment.py`, `core_platform/stream_api.py`,
  `sharpshooter/*`, workflow helper scripts, `worker/test/*.py`).
- Full-tree `py_compile`: **6 files fail on main** (unchanged by this
  branch, hence advisory in CI, not gated):
  `app/grantwriter_mother.py:115`, `bozly_global_traceback.py:222`,
  `core_platform/free_resources.py:39`, `core_platform/local_inference.py:57`,
  `core_platform/native_runtime.py:130`, `core_platform/operational_runtime.py:140`.
- `pip-audit -r requirements.txt -r requirements-server.txt --disable-pip --no-deps`:
  **no known vulnerabilities found** (both files). Note: `--no-deps` audits
  only the pinned versions, not transitive deps; hashed requirements
  (`pip-compile`) are the follow-up.
- Worker JS tests (`node v24.22.1` locally, `npm ci` + `npm test`):
  **20 pass, 2 fail** — both failures are the Python fixture importing
  `core_platform.deployment`, which imports the broken
  `core_platform/free_resources.py:39`. The JS code itself passes.
  Hence the worker job is advisory in CI until that one file is fixed.

## 5. Platform modernization proposals (not implemented)

### Home for `/api/operator/ai/roles` (PR #14)

**Recommendation: mount it in `core_platform/deployment.py::create_application`.**
That function is the only real routing table on main: a raw WSGI
dispatcher with explicit path branches (`/healthz`, `/readyz`,
`/api/platform/free-resources`, `/stripe/webhook`, `/api/auth/verify`,
`/api/transactions/process`, `/api/stream/transactions`, else the customer
app). The realistic mount is a `roles_app` entry on `RuntimeBindings`
plus a branch next to the existing `/api/auth/verify` branch, gated
behind `ready()` (the release verifier) the way `/stripe/webhook`
already is. Do NOT mount in `wsgi.py` (it only wires the Stripe webhook
app via `core_platform.stream_api.import_make_app`) and NOT in
`core_platform/native_runtime.py` (it has no WSGI routing at all — it is
a class of methods — and it does not compile on main, line 130). No
`/api/operator/ai/roles` route exists anywhere on main today.

**Honest fallback:** if no trusted roles binding exists yet, ship the
roles workers + docs with no API route rather than inventing an endpoint.
An unmounted route is better than a route with no authorization binding.

**Blocker before either option can be tested:** `deployment.py` cannot
even be imported on main, because it imports `core_platform.free_resources`
(SyntaxError, line 39). There is also a latent bug in the same file:
line 83 reads `bindings.stream_verifiers` (plural) while `RuntimeBindings`
defines `stream_verifier` (singular, line 37) — any bindings-backed
startup hits `AttributeError`. Both need fixing before a roles mount can
be verified; neither is fixed on this branch (application code is out of
this branch's CI scope, and the `free_resources.py:39` fix requires
choosing semantics for `count` over multiple inventory types — see §4).

### Test home

**Python: `sharpshooter/tests/`.** It already exists on main, is stdlib
`unittest`, pytest-compatible, and green (5/5, now 8/8 with the smoke
test). New Python tests go here. **JS: `worker/test/`** (`node --test`,
20/22, the 2 failures are the Python breakage above). Do NOT resurrect
the deleted `tests/` directory (112 files deleted on main): there is no
surviving inventory of what those tests covered, and blind resurrection
would reintroduce tests for deleted code.

### Other findings (not fixed here)

- `requirements-dev.txt` pins `cryptography>=46.0.0,<47.0.0` while
  `requirements.txt` pins `cryptography==50.0.2` — the two files cannot
  both be satisfied. Needs an owner decision, not a silent edit.
- `expressway-sync.yml` at the repo root uses `checkout@v5` and contains
  its own self-push pattern; it is inert where it is. Do not move it into
  `.github/workflows/` until its push behaviour is reviewed like §3.
- `closeup_vmax_pipeline.yml` installs unpinned `requests flask` and
  calls an `OCI_CLOSEUP_WEBHOOK_URL` secret; left as-is, flag for the
  next dependency pass.
- `wsgi.py` contains a hardcoded fallback Stripe webhook secret default.
  It should be removed (fail closed when the secret is absent); the value
  is not reproduced here.
- A sibling branch (`upgrade/real-world-20261113`, commit `200c6a6c`)
  already upgraded runtime dependencies (gunicorn, stripe, PyJWT,
  cryptography cap, nginx, node) and reported that the GitHub App
  **cannot write workflow files (403)**. If this branch's workflow files
  also fail to push for that reason, they are ready to apply from the
  branch contents / this report — the non-workflow files (smoke test,
  pair, this doc) can still land.

## 6. What still needs owner input

1. **Gateway decision:** approve/reject the §3 diff (push gating +
   canonical `payload_hash`). Until approved, PR runs keep failing at
   the push step.
2. **Release-verifier approval:** the Gateway and PR #107/#14/#108/#2
   merge path still goes through the Architectural Integrity Gateway and
   the release verifier; this branch merges nothing.
3. **Stripe keys:** PR #2 (Checkout/Stripe) is still a draft and NOT
   DEPLOYED; no Stripe keys were added or touched here. Going live needs
   real Stripe webhook/secret configuration, not the hardcoded fallback
   noted in §5.
4. **`free_resources.py:39` semantics:** `count` over multiple inventory
   types — sum, mapping, or first? One-line fix once decided; it unblocks
   the worker suite (22/22) and `deployment.py` import.
5. **`requirements-dev.txt` cryptography conflict** (§5) and the
   `deployment.py:83` `stream_verifiers` typo — both one-line fixes
   awaiting a decision, not silently applied here.
