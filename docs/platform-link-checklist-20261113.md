# Platform link checklist — Sanders Dash & Seal (2026-11-13)

**Snapshot, not a live dashboard.** Verified on branch
`fix/everything-20261113`, P2 head `f6f18ea` (2026-11-13), by the P2
verification pass and re-checked by the P3 live smoke test on the same
branch. Every row below states only what was verified then; a row that
says MISSING_KEY / NOT_IMPLEMENTED / UNAPPROVED is a fact about that
date, not a promise. The live source of truth is
`GET /api/platform/status` on a running instance (read-only, no live
calls, no secrets returned). `core_platform/platform_services.py`
(`platform_status()`, `gateway_status()`) is the code twin of this doc.

## Link registry (`core_platform/ai_platform_links.py`)

Verified verdicts with no keys and no environment set:
**LINKED 6 / MISSING_KEY 2 / NOT_IMPLEMENTED 1 / BROKEN 0.**

| Platform | Verdict | Evidence / missing piece |
|---|---|---|
| daedalus | MISSING_KEY | Needs `ANTHROPIC_API_KEY` + `DAEDALUS_CLAUDE_MODEL` |
| stream_api (Stripe webhook) | MISSING_KEY | Needs `STRIPE_WEBHOOK_SECRET` + `STRIPE_SECRET_KEY` |
| voice_audio_video | NOT_IMPLEMENTED | No local backend installed in the VM, no provider keys |
| grantwriter, bozly, + 4 others | LINKED | P1 rebuilt Grantwriter; P1 restored the Bozly traceback file |

## Approvals (`core_platform/ai_platform_approvals.json`)

**All 9 gates UNAPPROVED.** A gate flips only on an explicit owner
approval for that specific gate, or a real verifier returning True.
No blanket approval exists.

`ai_role_workers`, `anthropic_live_model`, `daedalus_live`,
`gateway_workflow_fix`, `grantwriter_purpose`,
`release_verifier_pr2_checkout`, `ron_notarial`, `stripe_live_keys`,
`voice_video_provider`.

## Service links (`core_platform/service_linking.py`)

19 rows. Live-call gating: provider voice adapters are constructed
only when the `voice_video_provider` gate is APPROVED; otherwise only
local/offline backends (faster-whisper, system TTS) are attempted.
LiveKit/Daily room/token POSTs additionally require the gate when a
provider is configured.

## Stripe

- Test mode is the default. Live requires BOTH `STRIPE_LIVEMODE` and
  `STRIPE_LIVE_VERIFIED` set to one of `1` / `true` / `yes`
  (canonical truthiness, P3 2026-11-13, shared by `wsgi.py`,
  `deploy/deployment.py` and `core_platform/platform_services.py`).
- Webhook secret comes ONLY from the environment; no default is baked in.
- Ledger handlers are real SQLite-backed methods since P1
  (`core_platform/stripe_payments.PaymentLedger`, idempotent, durable);
  per-event currency/amount is validated in the webhook dispatch since
  P3 (`core_platform/stream_api.py` + `global_payments.validate_webhook_event`).
- Payment confirmation does not authorize or execute a notarial act.

## Oracle Cloud

- Instance `sanders-dash-seal`, `129.146.111.166`, `us-phoenix-1`,
  tenancy `rooseveltsanders381`, VM.Standard.A1.Flex, Oracle Linux 9.
- **No code is deployed to Oracle.** SSH and HTTP/HTTPS from this
  environment are blocked by the egress proxy; the instance serves
  nothing as of 2026-11-13.
- Deploy layout: `/opt/sanders-dash-seal`, systemd units for gunicorn +
  nginx, env file `0600`. Backup policy: `deploy/oracle/backup-policy.md`.
- Free-first catalog: root `oci_free_resources.json`, 6 resources
  (A1 compute 2 OCPU/12 GB, block volume 200 GB, object storage
  10 GB, egress 10 TB/mo, autonomous DB 2× 20 GB, NoSQL 3× 25 GB),
  catalog date 2026-11-13.

## GoDaddy DNS

- Both apex domains (`sandersdashandseal.com`,
  `sanderslegalhelpersllc.com`) resolve to `129.146.111.166`.
- **Missing record:** `www.sanderslegalhelpersllc.com` A →
  `129.146.111.166` (verified NXDOMAIN 2026-11-13). The exact record
  dict is produced by `platform_services.dns_records_to_apply()`; this
  code never changes DNS — the owner applies the record in GoDaddy.

## GitHub

- **Gateway workflow is the one failing check.**
  Workflow: `.github/workflows/parallel-build-verification.yml`.
  Failing step: `Securely Push Verified Manifest Assets` (exit 128).
  Cause: the step pushes to main from PR runs, and the sync step writes
  Shape B pairs (bare sha256, no `payload_hash` / `signatures` /
  `status`); the canonical format is Shape A (`payload_hash`,
  `signatures {}`, `status UNSIGNED_SOURCE_MANIFEST`).
- Fix status: **PROPOSED DIFF ONLY, not applied.** Gate the push step
  to push events (`if: github.event_name == 'push'`), emit Shape A
  pairs, remove auto-push to main from PR runs. The workflow file was
  not edited: its read did not pass a safety check on 2026-11-13 and
  it needs a clean read + fresh approval before any edit.
- Owner direction (2026-11-13): deploy directly to Oracle, bypassing
  the Gateway for now. The Gateway fix is therefore not on the deploy
  path; it remains open, gated by `gateway_workflow_fix` (UNAPPROVED).
- Nothing in this pass is merged to `main` or deployed.

## Google

- Gmail, Google Calendar, Google Docs and Google Sheets are connected
  through Muse (owner accounts, 2026-11-13). There is **no server-side
  Google integration** in this repo: no Google OAuth flow, no service
  account, no server-side Drive/Docs call. The three legitimate Google
  uses named in the linking work are STUN (`stun:stun.l.google.com:19302`),
  Google TTS (WaveNet, only when the owner configures it) and the
  connected Muse apps above.

## Realtime / LiveKit / video

- No provider configured: `/api/realtime/status` reports provider
  `none`. No signalling server or SFU is running in this repo.
- A live call needs a LiveKit server (self-hosted on Oracle Always
  Free, or LiveKit Cloud) at `LIVEKIT_URL` with `LIVEKIT_API_KEY` /
  `LIVEKIT_API_SECRET`, or a Daily.co domain + API key, or the in-repo
  relay in `worker/src/webrtc.js` plus a TURN server for NAT traversal.
- Canonical module: `core_platform/livekit_realtime.py`
  (`LiveKitClient` / `DailyClient` / `RealtimeConfig`); see
  `docs/LIVEKIT_CANONICAL.md`. `core_platform/livekit_video.py` is
  retained as the token issue/validate + status helper.
- With no provider, room/token POSTs honestly 503 (`not_configured`).

## Daedalus / voice

- `/api/daedalus/describe` returns 200 with `fully_active: false`
  (no key, no model, no signing key, gates unapproved).
- `/api/voice/turn` honestly 503 (`daedalus_runtime_not_configured`).
  Transcribe/speak 503 (`transcriber_not_configured` /
  `synthesizer_not_configured`) with no backends.
- Free-first order: faster-whisper (local STT) then Deepgram then
  OpenAI; synthesizers System → Google → ElevenLabs → OpenAI Realtime.
  ElevenLabs demo voice id was removed; `voice_id` is required from
  arg/env. No live Claude/OpenAI/Deepgram/ElevenLabs/Google call is
  made without keys + the matching approval gate.

## RON / notarial

- Gate `ron_notarial` UNAPPROVED. `global_compliance` approved set is
  EMPTY by design; gating is fail-closed.
- Live check: `GET /api/compliance/ron?jurisdiction=XX` returns 403
  `NOT_APPROVED_IN_JURISDICTION` for every jurisdiction until the
  owner approves one by name. No jurisdiction is approved by this doc.

## Global

- Timestamps are UTC (`global_time`). Locales: `en` / `es`
  (Accept-Language negotiated; `GET /` sets `Content-Language`).
- Currency resolves per request (`GET /api/payments/currency`,
  explicit `?currency=` wins, then Accept-Language, never silently
  USD); per-event currency is validated in the webhook dispatch.
- Regions: `us-phoenix-1` primary from env; no secondary region is
  provisioned; failover is PLAN_ONLY.
- Connectivity policy (`global_connectivity`) is reported on
  `/api/platform/status` (`connectivity`, region `us`); eu/apac
  policies are declared only, no deployment there.
- Tax raises `TaxNotImplementedError` by design (no tax provider).
