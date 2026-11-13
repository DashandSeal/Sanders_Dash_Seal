# Daedalus Rebuild — 2026-11-13

Branch: `rebuild/daedalus-20261113`, off `main` (`f4f72abe`).
Source: PR #107 branch `feature/daedalus-live-upgrade-20261023`
(9 Daedalus modules + 2 docs). Not merged. Not deployed.

## What was rebuilt

- The 9 `core_platform/daedalus_*.py` modules (863 lines) integrated onto
  current main, with their 9 Shape A `.pbd.json` pairs
  (`UNSIGNED_SOURCE_MANIFEST`, sha256 hashes verified 12/12 on the PR
  branch and re-verified on this branch).
- New `core_platform/daedalus_engine.py`: wires the chain
  `DaedalusClaudeTransport` → `DaedalusRuntimeIntegration.generate_source()`
  → `UnifiedDaedalusEngine.execute()` (trust → capability → IP protection).
  Previously the transport, runtime facade, and unified engine were
  parallel and unconnected; nothing in the repo instantiated any of them.
- New `core_platform/__init__.py`: `core_platform` is now a regular
  package (it previously loaded only as a PEP 420 namespace package).
  Its pair file is included.
- This doc.

## What was verified locally (no network, no API key, no deployment)

- `python3 -m py_compile` on all 10 Daedalus modules: OK.
- `python3 -m core_platform.daedalus_engine`: prints the capability
  report; `fully_active` is `false`.
- End-to-end chain test with a fake transport (test script kept out of
  the repo): `execute()` returns the correct `source_sha256`, both
  persist callbacks fire once, audit events include
  `NATIVE_OPERATION_COMPLETED`. Passed.
- `build_engine` without `ANTHROPIC_API_KEY` / `DAEDALUS_CLAUDE_MODEL`
  raises `ValueError` instead of pretending to work.

## What is real vs. declared

- Real: Anthropic Messages API client (stdlib `urllib`, no SDK);
  HMAC-SHA256 evidence signing; publication gate; geofence / global-trust
  boolean policy predicates; continuity manifest; hardcoded proposed
  rate card (labeled illustrative, not a forecast).
- Declared only (all 13 capabilities report `UNAVAILABLE`):
  203-language registry, COBOL Bridge / Priority-1, ONNX language
  classification, SSS / SSSv3 / GSS shields, Polyglot Engine LLVM
  execution, L15 execution. No code implements these in this branch.
- `GeoFence` is never instantiated anywhere in the repo; enforcement
  needs a trusted attestation source and audit sink supplied by the caller.

## Still missing (owner input needed)

1. Anthropic API key + model, via the approved secure flow. No live
   Claude call has ever been observed from this code.
2. Live Daedalus runtime location — none was found on the Oracle
   instance (`sanders-dash-seal`, us-phoenix-1, $0.00, Free Trial).
   The instance is a healthy host; it does not prove Daedalus runs there.
3. Architectural Integrity Gateway: still failing on PR #107 and #108.
   Established cause is the workflow push step
   "Securely Push Verified Manifest Assets" (exit 128), not the pairs.
   The workflow file was not edited in this rebuild.
4. No Daedalus tests exist in the repo. The local chain test above is
   not committed; a real test suite still needs to be written.

## Deployment plan (not executed)

1. Merge this branch only after the Gateway check is green.
2. Provision `ANTHROPIC_API_KEY` and `DAEDALUS_CLAUDE_MODEL` as
   environment secrets on the Oracle instance (never in Git).
3. Provide a durable private evidence store and audit sink, plus a
   signing key of at least 32 bytes held outside the repo.
4. Deploy `main` to the `sanders-dash-seal` instance
   (129.146.111.166, us-phoenix-1) behind the existing nginx config,
   then run one live `generate_source` call and record the Anthropic
   request ID / latency / model ID as acceptance evidence.
5. Do not claim live reasoning, 203-language coverage, COBOL, ONNX,
   or SSS/GSS until each is observed working.
