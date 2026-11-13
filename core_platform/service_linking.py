"""Per-platform service linking table for Sanders Dash & Seal.

Single source of truth for "which platform links to which real
service, through which file, with which env var, and is it live?"

* ``linking_table()`` returns one row per platform/service link:
  ``platform``, ``service``, ``adapter`` (repo file), ``env_var``,
  ``test`` (how it was tested with fakes) and ``live_status``.
* ``live_status`` is computed from the environment only — a key
  being present means ``READY`` (configured, not yet live-verified);
  anything else is ``MISSING_KEY``.  No provider call is ever made
  to compute this table, and no live success is claimed.
* Free-tier-first (owner direction, 2026-11-13): every row names
  its $0 path first — local/offline backends, provider free tiers
  and test mode — before any paid service.  Nothing here spends
  money on its own.
* This module is a registry of *links*, not a link-registry or
  approval module (those belong to other workers); it does not
  approve, gate or execute anything.
"""

from __future__ import annotations

import os
from typing import Any

# Each row: platform, service, adapter file, env var(s), fake-test note,
# free-tier note.  live_status is computed, never hardcoded.
_LINKS: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "Daedalus",
        "Anthropic Claude (Messages API)",
        "core_platform/anthropic_sdk_transport.py (+ daedalus_claude_transport.py stdlib)",
        "ANTHROPIC_API_KEY + DAEDALUS_CLAUDE_MODEL",
        "Fake urlopen / fake SDK client; missing key raises ValueError",
        "No $0 provider tier; rehearse offline with fakes",
    ),
    (
        "Daedalus",
        "OpenAI chat (gpt-*)",
        "core_platform/openai_chat_transport.py",
        "OPENAI_API_KEY + OPENAI_CHAT_MODEL (or DAEDALUS_OPENAI_MODEL)",
        "FakeChatTransport; deprecated models rejected",
        "No $0 provider tier; rehearse offline with fakes",
    ),
    (
        "Role workers (12 IT agents)",
        "Anthropic Claude / OpenAI chat",
        "core_platform/role_worker_llm.py",
        "LLM_BACKEND + ANTHROPIC_API_KEY/OPENAI_API_KEY",
        "Fake backend; unregistered agent raises ValueError",
        "No $0 provider tier; rehearse offline with fakes",
    ),
    (
        "Grantwriter (Mother)",
        "Anthropic Claude / OpenAI chat (drafting)",
        "core_platform/grantwriter_llm.py",
        "LLM_BACKEND + ANTHROPIC_API_KEY/OPENAI_API_KEY",
        "Fake backend; missing opportunity fields raise ValueError",
        "No $0 provider tier; rehearse offline with fakes",
    ),
    (
        "Grantwriter (Mother)",
        "Google Docs (draft export, optional)",
        "core_platform/google_workspace_adapters.py",
        "Connected Google account (no env key in this module)",
        "Injected fake docs client; no client raises ValueError",
        "$0 under the connected Google account",
    ),
    (
        "Voice (STT)",
        "Deepgram Nova-3",
        "core_platform/daedalus_voice.py (DeepgramTranscriber)",
        "DEEPGRAM_API_KEY",
        "Missing key raises ValueError; no live call",
        "$200 credit on signup (verify current offer)",
    ),
    (
        "Voice (STT)",
        "OpenAI gpt-transcribe",
        "core_platform/daedalus_voice.py (OpenAITranscriber)",
        "OPENAI_API_KEY",
        "Missing key raises ValueError; whisper-1 rejected",
        "No $0 tier; gpt-transcribe $0.0045/min (verify)",
    ),
    (
        "Voice (STT)",
        "faster-whisper (local)",
        "core_platform/daedalus_voice.py (FasterWhisperTranscriber)",
        "None (model tiny/base, local)",
        "Missing package raises ImportError; fake transcriber passes",
        "$0 offline after one model download",
    ),
    (
        "Voice (TTS)",
        "Google Cloud TTS (WaveNet)",
        "core_platform/daedalus_voice.py (GoogleTTSSynthesizer)",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "Missing package raises ImportError; no live call",
        "4M chars/month free, then $4/1M (verify)",
    ),
    (
        "Voice (TTS)",
        "ElevenLabs",
        "core_platform/daedalus_voice.py (ElevenLabsSynthesizer)",
        "ELEVENLABS_API_KEY",
        "Missing key raises ValueError; no live call",
        "10k free credits/month, non-commercial (verify)",
    ),
    (
        "Voice (TTS)",
        "System TTS (pyttsx3/espeak-ng)",
        "core_platform/daedalus_voice.py (SystemTTSSynthesizer)",
        "None (local)",
        "Missing package raises ImportError; fake synthesizer passes",
        "$0 offline",
    ),
    (
        "Voice (Realtime)",
        "OpenAI Realtime",
        "core_platform/openai_chat_transport.py (realtime_session_config)",
        "OPENAI_API_KEY + OPENAI_REALTIME_MODEL",
        "Config-only; missing key raises ValueError; no WS opened",
        "No $0 tier; config only, no session billed by this module",
    ),
    (
        "Video",
        "LiveKit / WebRTC signalling",
        "core_platform/livekit_video.py (+ daedalus_voice.py signalling)",
        "LIVEKIT_URL + LIVEKIT_API_KEY + LIVEKIT_API_SECRET",
        "Token issue/validate round-trip with fake time; bad sig rejected",
        "LiveKit Cloud free tier / self-host on Oracle Always Free $0",
    ),
    (
        "Payments",
        "Stripe Checkout + webhook (test-mode first)",
        "core_platform/stripe_checkout.py (+ stripe_payments.py ledger)",
        "STRIPE_SECRET_KEY (sk_test_*) + STRIPE_WEBHOOK_SECRET",
        "Fake Stripe client; live key refused without verifier gate",
        "$0 in test mode; live only after STRIPE_LIVE_VERIFIED=1",
    ),
    (
        "Scheduling",
        "Google Calendar (optional)",
        "core_platform/google_workspace_adapters.py",
        "Connected Google account (no env key in this module)",
        "Injected fake client; no client raises ValueError",
        "$0 under the connected Google account",
    ),
    (
        "Notifications",
        "Gmail (optional)",
        "core_platform/google_workspace_adapters.py",
        "Connected Google account (no env key in this module)",
        "Injected fake client; no client raises ValueError",
        "$0 under the connected Google account",
    ),
    (
        "Logging",
        "Google Sheets (optional)",
        "core_platform/google_workspace_adapters.py",
        "Connected Google account (no env key in this module)",
        "Injected fake client; no client raises ValueError",
        "$0 under the connected Google account",
    ),
    (
        "Hosting",
        "Oracle Cloud Always Free (systemd/gunicorn/nginx)",
        "deploy/systemd/sanders-dash-seal.service + deploy/gunicorn.conf.py + deploy/systemd/ai-platform-services.environment.example",
        "All keys UNSET in the env file until the owner fills it (0600)",
        "gunicorn/nginx config checked locally in prior work; SSH blocked, not deployed",
        "$0 Always Free tier only",
    ),
    (
        "Hosting",
        "GoDaddy DNS",
        "docs/AI_PLATFORM_SERVICES_LINKING.md (report only; DNS not changed)",
        "None (no change made)",
        "DoH check in prior work: both apex domains -> 129.146.111.166; www.sanderslegalhelpersllc.com NXDOMAIN",
        "$0 (record to be added by the owner in GoDaddy)",
    ),
)


def _env_present(spec: str) -> bool:
    """True when every env var named in ``spec`` is set and non-empty.

    Specs that name a connected account or 'None' have no env key to
    check and report False (MISSING_KEY / MISSING_CLIENT) unless the
    caller passes an explicit client — this table never claims a
    connected account is live from this process.
    """
    if "Connected Google account" in spec or spec.startswith("None"):
        return False
    if "All keys UNSET" in spec:
        return False
    import re

    # Parenthesised "(or ALT)" names are alternatives to the required
    # name immediately before them (e.g. OPENAI_CHAT_MODEL or
    # DAEDALUS_OPENAI_MODEL), not extra requirements.
    alt_match = re.search(r"([A-Z][A-Z0-9_]*)\s+\(or ([A-Z][A-Z0-9_]*)\)", spec)
    alt_target = alt_match.group(1) if alt_match else None
    alternative = alt_match.group(2) if alt_match else None
    spec_wo_alt = re.sub(r"\(or [A-Z][A-Z0-9_]*\)", "", spec)
    names = [
        token.strip("(),").rstrip("*")
        for token in spec_wo_alt.replace("+", " ").split()
        if token.strip("(),").isupper() and "_" in token.strip("(),")
    ]
    if not names:
        return False
    for name in names:
        if os.environ.get(name):
            continue
        if name == alt_target and alternative and os.environ.get(alternative):
            continue
        return False
    return True


def linking_table() -> list[dict[str, Any]]:
    """Per-platform linking table. No provider calls are made."""
    rows: list[dict[str, Any]] = []
    for platform, service, adapter, env_var, test, free_tier in _LINKS:
        rows.append(
            {
                "platform": platform,
                "service": service,
                "adapter": adapter,
                "env_var": env_var,
                "test": test,
                "free_tier_first": free_tier,
                "live_status": "READY"
                if _env_present(env_var)
                else "MISSING_KEY",
            }
        )
    return rows


def describe() -> dict[str, Any]:
    """Summary: row count, how many are READY, and the full table."""
    rows = linking_table()
    ready = [r for r in rows if r["live_status"] == "READY"]
    return {
        "links": len(rows),
        "ready": len(ready),
        "missing_key": len(rows) - len(ready),
        "note": "live_status is env presence only; READY means "
        "configured, not live-verified. No provider call was made.",
        "rows": rows,
    }


__all__ = ["linking_table", "describe"]
