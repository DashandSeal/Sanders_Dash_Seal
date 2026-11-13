# AI Platform Services Linking — Task 5 (2026-11-13)

Base: `deploy/simultaneous-20261113` (snapshot `4342b230`). Branch:
`link/ai-platform-services-20261113`. Not merged, not deployed, $0
spent, no secrets, no live provider calls.

This document is the per-platform linking table: which platform links
to which real service, through which adapter/config file, with which
env var, how it was tested with fakes, and its live status. **Every
live status is `MISSING_KEY` until the owner supplies a key** — that
is the honest state, not a failure. `live_status` in
`core_platform/service_linking.py` is computed from env presence
only; no provider call is ever made to build this table.

Free-tier-first (owner direction, 2026-11-13): every platform must
always use the free resources available first — local/offline
backends, provider free tiers and test mode — before any paid
service. Each row names its $0 path first.

## Linking table

| Platform | Service | Adapter / config file | Env var | Test result (fakes) | Live status |
|---|---|---|---|---|---|
| Daedalus | Anthropic Claude (Messages API) | `core_platform/anthropic_sdk_transport.py` (SDK when installed, else stdlib `daedalus_claude_transport.py`) | `ANTHROPIC_API_KEY` + `DAEDALUS_CLAUDE_MODEL` | Fake urlopen returns canned message; missing key/model raises `ValueError`; `use_sdk=True` without SDK raises `ImportError` | MISSING_KEY |
| Daedalus | OpenAI chat (gpt-*) | `core_platform/openai_chat_transport.py` | `OPENAI_API_KEY` + `OPENAI_CHAT_MODEL` (or `DAEDALUS_OPENAI_MODEL`) | Fake urlopen + `FakeChatTransport`; deprecated models rejected | MISSING_KEY |
| Role workers (12 IT agents) | Anthropic Claude / OpenAI chat | `core_platform/role_worker_llm.py` (`LLM_BACKEND=claude\|openai`) | `LLM_BACKEND` + provider key/model | Fake backend returns canned text; unregistered agent raises; missing backend raises | MISSING_KEY |
| Grantwriter (Mother) | Anthropic Claude / OpenAI chat (drafting) | `core_platform/grantwriter_llm.py` | `LLM_BACKEND` + provider key/model | Fake backend drafts; missing opportunity fields raise `ValueError` | MISSING_KEY |
| Grantwriter (Mother) | Google Docs (draft export, optional) | `core_platform/google_workspace_adapters.py` | Connected Google account (no env key in this module) | Injected fake docs client round-trips; no client raises `ValueError` | MISSING_KEY |
| Voice (STT) | Deepgram Nova-3 | `core_platform/daedalus_voice.py` (`DeepgramTranscriber`) | `DEEPGRAM_API_KEY` | Missing key raises `ValueError`; no live call | MISSING_KEY |
| Voice (STT) | OpenAI gpt-transcribe | `core_platform/daedalus_voice.py` (`OpenAITranscriber`) | `OPENAI_API_KEY` | Missing key raises; `whisper-1` rejected (removed 26 Feb 2027) | MISSING_KEY |
| Voice (STT) | faster-whisper (local) | `core_platform/daedalus_voice.py` (`FasterWhisperTranscriber`) | None (model `tiny`/`base`, local) | Missing package raises `ImportError`; fake transcriber passes | $0 path — ready when package + model installed |
| Voice (TTS) | Google Cloud TTS (WaveNet) | `core_platform/daedalus_voice.py` (`GoogleTTSSynthesizer`) | `GOOGLE_APPLICATION_CREDENTIALS` | Missing package/credentials raises honestly; no live call | MISSING_KEY |
| Voice (TTS) | ElevenLabs | `core_platform/daedalus_voice.py` (`ElevenLabsSynthesizer`) | `ELEVENLABS_API_KEY` | Missing key raises `ValueError`; no live call | MISSING_KEY |
| Voice (TTS) | System TTS (pyttsx3/espeak-ng) | `core_platform/daedalus_voice.py` (`SystemTTSSynthesizer`) | None (local) | Missing package raises `ImportError`; fake synthesizer passes | $0 path — ready when package installed |
| Voice (Realtime) | OpenAI Realtime | `core_platform/openai_chat_transport.py` (`realtime_session_config`) | `OPENAI_API_KEY` + `OPENAI_REALTIME_MODEL` | Config-only; missing key raises; no WebSocket opened, no live session | MISSING_KEY |
| Video | LiveKit / WebRTC signalling | `core_platform/livekit_video.py` (+ `daedalus_voice.py` signalling validators) | `LIVEKIT_URL` + `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET` | Token issue/validate round-trip with fake time; bad signature and expiry rejected; bad signalling action rejected | MISSING_KEY |
| Payments | Stripe Checkout + webhook (test-mode first) | `core_platform/stripe_checkout.py` (+ `stripe_payments.py` ledger) | `STRIPE_SECRET_KEY` (`sk_test_*`) + `STRIPE_WEBHOOK_SECRET` | Fake Stripe client creates + registers session; live key refused without verifier gate; webhook verified before recording; duplicate deduplicated | MISSING_KEY |
| Scheduling | Google Calendar (optional) | `core_platform/google_workspace_adapters.py` | Connected Google account | Injected fake client; no client raises `ValueError` | MISSING_KEY |
| Notifications | Gmail (optional) | `core_platform/google_workspace_adapters.py` | Connected Google account | Injected fake client; no client raises `ValueError` | MISSING_KEY |
| Logging | Google Sheets (optional) | `core_platform/google_workspace_adapters.py` | Connected Google account | Injected fake client; no client raises `ValueError` | MISSING_KEY |
| Hosting | Oracle Cloud Always Free (systemd/gunicorn/nginx) | `deploy/systemd/sanders-dash-seal.service`, `deploy/gunicorn.conf.py`, `deploy/systemd/ai-platform-services.environment.example` | All keys UNSET in env file until owner fills it (mode 0600) | Config checked locally in prior work; SSH blocked, not deployed | MISSING_KEY / NOT DEPLOYED |
| Hosting | GoDaddy DNS | This doc (report only; DNS not changed) | None (no change made) | Prior DoH check: both apex domains → `129.146.111.166`; `www.sanderslegalhelpersllc.com` NXDOMAIN | Needs owner action (see below) |

## What already existed (reused, not rebuilt)

- Claude stdlib transport, Daedalus engine wiring, voice adapters
  (Deepgram / OpenAI gpt-transcribe / Google TTS / ElevenLabs /
  faster-whisper / system TTS), WebRTC signalling validation, voice
  WSGI app, Stripe ledger + webhook verifier + checkout parameters.
- systemd unit, gunicorn config, nginx configs, env example (0600).

## What Task 5 added

- `core_platform/openai_chat_transport.py` — OpenAI chat (stdlib +
  optional SDK), deprecation rejects (`whisper-1`,
  `gpt-4o-transcribe`, `tts-1`, `tts-1-hd`), Realtime session config
  (config-only, no live handshake).
- `core_platform/anthropic_sdk_transport.py` — Claude SDK-first with
  stdlib fallback; same `generate()` shape as the stdlib transport.
- `core_platform/role_worker_llm.py` — 12 registered IT agents wired
  to Claude/OpenAI via an injectable backend.
- `core_platform/grantwriter_llm.py` — grant section drafting +
  optional Google Docs export via an injected docs client.
- `core_platform/google_workspace_adapters.py` — optional Docs /
  Sheets / Gmail / Calendar adapters; injected clients only, no live
  calls, no Google imports at module load.
- `core_platform/livekit_video.py` — LiveKit room tokens (stdlib
  HMAC-SHA256 JWT), local validation, signalling re-export.
- `core_platform/stripe_checkout.py` — Checkout creation, test-mode
  first, live refused without `allow_live=True` +
  `STRIPE_LIVE_VERIFIED=1`, webhook verified before ledger record.
- `core_platform/service_linking.py` — the linking table as code.
- `requirements-ai-services.txt` — optional provider deps, pinned
  (anthropic 2.8.0, openai 3.49.0, elevenlabs 2.78.0,
  faster-whisper 1.2.1, deepgram-sdk 3.11.0 — the 3.x API the
  adapter targets — google-cloud-texttospeech 2.38.0,
  livekit-api 1.2.2, pyttsx3 2.99).
- `deploy/systemd/ai-platform-services.environment.example` — all
  keys UNSET, install at mode 0600.
- `tests/test_ai_platform_services.py` — fake-only tests (see below).

No link-registry or approval module was built here; other workers
own those. Note: two sibling local-only Phase 2 branches exist with
overlapping scope (`link/synthetic-ai-daedalus-voice-20261113`,
`link/synthetic-ai-platforms-20261113`, not merged). This branch was
built on the assigned base (`deploy/simultaneous-20261113`) with
different filenames (`openai_chat_transport.py` vs `openai_link.py`,
`service_linking.py` vs `platform_services.py`), so the branches do
not collide file-for-file; the orchestrator should reconcile them
before merging more than one.

## Deprecation handling

- `whisper-1` — removed 26 Feb 2027. Rejected in both the OpenAI
  chat transport and the transcriber. Use `gpt-transcribe`.
- `gpt-4o-transcribe` — deprecated, removed 26 Feb 2027. Rejected.
  Use `gpt-transcribe`.
- `tts-1` / `tts-1-hd` — shutdown 6 Jan 2027. Rejected. Use Google
  TTS, ElevenLabs or system TTS.
- Models are never defaulted: a missing model env var raises
  `ValueError` naming the var instead of silently picking a model.

## Oracle hosting

- Instance `sanders-dash-seal`, `129.146.111.166`, us-phoenix-1,
  Always Free only. Service: `deploy/systemd/sanders-dash-seal.service`
  (gunicorn, `EnvironmentFile=-/etc/sanders-dash-seal/environment`).
- Env file: copy `deploy/systemd/ai-platform-services.environment.example`
  to `/etc/sanders-dash-seal/environment`, mode 0600, fill in only the
  services the owner enables, `systemctl restart sanders-dash-seal`.
- **Not deployed by this task**: SSH from this environment is blocked
  by the egress proxy (prior work), so nothing was installed or
  restarted on the instance. That needs SSH unblocking + the owner
  (or an agent with shell access) running the install.

## GoDaddy DNS (report only — nothing changed)

- `sandersdashandseal.com` and `sanderslegalhelpersllc.com` apex
  domains already point at `129.146.111.166` (prior DoH check).
- `www.sanderslegalhelpersllc.com` has **no A record (NXDOMAIN)** and
  needs one pointing at `129.146.111.166`. This task does not change
  DNS; the owner adds the record in GoDaddy.

## Google Workspace (only where it actually helps)

- Grantwriter draft → Google Docs export (optional).
- Grant deadlines / reminders → Google Calendar events (optional).
- Status / deadline notifications → Gmail (optional).
- Pipeline / payment logs → Google Sheets (optional).
- All four are injected-client adapters with no live calls from this
  repo; the connected Google account does the auth. Nothing else in
  the platform needs Google, so nothing else was wired to it.

## Tests

Run: `python3 -m unittest discover -s tests -v` (repo root).
Fake-only: no keys, no network, no spend. Covers the OpenAI chat
transport (fake urlopen + deprecation rejects + Realtime config),
Claude SDK/stdlib transport, role workers, Grantwriter drafting +
Docs export, Google adapters (unconfigured + fake clients), voice
provider failure modes, LiveKit token round-trip + signalling,
Stripe test-mode checkout + verifier gate + webhook gate, and the
linking table (19 rows, all `MISSING_KEY` with no env).

## Still needs owner input

1. **API keys** (one per service enabled): `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`,
   `LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET`, `STRIPE_SECRET_KEY`
   (test first) + `STRIPE_WEBHOOK_SECRET`, Google TTS credentials
   file. No key = honest `MISSING_KEY`, nothing breaks.
2. **Model choices**: `DAEDALUS_CLAUDE_MODEL`, `OPENAI_CHAT_MODEL`
   (or `DAEDALUS_OPENAI_MODEL`), `OPENAI_REALTIME_MODEL`,
   `LLM_BACKEND` (`claude` default / `openai`).
3. **Stripe verifier approval**: set `STRIPE_LIVE_VERIFIED=1` only
   after a verifier confirms the live webhook secret, prices and
   success URLs. Live keys are refused without it.
4. **SSH / deploy**: unblock SSH to `129.146.111.166`, install the
   env file (0600), install + restart the systemd service.
5. **Gateway fix**: the Architectural Integrity Gateway workflow
   still fails on PRs (exit 128 push step) — needs the owner
   hand-apply (see `gateway-workflow-fix-owner-steps.md`). Merging
   this branch will hit the same gate.
6. **DNS**: add the `www.sanderslegalhelpersllc.com` A record in
   GoDaddy → `129.146.111.166`.
7. **Reconcile sibling branches**: `link/synthetic-ai-daedalus-voice-20261113`
   and `link/synthetic-ai-platforms-20261113` overlap this work;
   pick one set of adapters before merging.
