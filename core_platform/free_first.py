"""Free-first resource selection for Sanders Dash and Seal.

Standing owner rule (Roosevelt Sanders, 2026-11-13): "They must must always
use the free resources available." Every capability in the platform must
default to a free resource. A paid provider is used only when all three are
true:

1. the free options are unavailable or their free tier is exhausted, AND
2. the owner explicitly opted in (``SDS_ALLOW_PAID_PROVIDERS=1``), AND
3. the provider key / credential for that provider is present.

Nothing in this module makes a live call, spends money, or reads a secret.
It only decides *which* provider to use and records usage against known
free-tier limits. Availability is supplied by the caller (installed package,
key present, credential file present) so the selection logic is testable
with fakes and never silently switches to a paid provider.

Free-tier limits below were verified 2026-11-13 from provider pricing
pages / documentation via web search, or from the repo itself. Each entry
carries a ``verified`` label: ``web-2026-11-13`` (checked against provider
pages that day), ``in-repo`` (asserted by the repo's own code), or
``well-known`` (no free tier exists for live LLM inference). Re-check list
prices before budgeting; limits change.

Notable corrections baked in here (do not regress):
- Oracle Always Free Ampere A1 was cut in June 2026 from 4 OCPU / 24 GB
  to 2 OCPU / 12 GB (1,500 OCPU-hours and 9,000 GB-hours per month).
  The instance ``sanders-dash-seal`` (1 OCPU / 6 GB, 47 GB boot) is
  inside the current limit. Idle Always Free instances may be reclaimed
  by Oracle if 95th-percentile CPU over 7 days is under 20%.
- Deepgram has NO permanent free plan: a one-time $200 credit, no card
  required. Pricing page says it lasts until used; Deepgram docs say
  promotional credits expire one year from signup. Treat as exhaustible.
- Google Cloud TTS free allowance (4M Standard/WaveNet chars/month)
  requires a GCP project with billing enabled, even inside the allowance.
- ElevenLabs free plan (10,000 credits/month, ~10 minutes) is
  non-commercial only, no rollover. Commercial use needs Starter ($6/mo).
- Anthropic Claude and OpenAI inference have NO free tier. They are
  paid-only and never the default.
- OpenAI ``whisper-1`` is deprecated and removed 26 Feb 2027;
  ``tts-1`` / ``tts-1-hd`` were deprecated 1 Oct 2026 and shut down
  6 Jan 2027. Do not build new on them. The repo defaults in
  ``core_platform/daedalus_config.py`` were fixed on this branch to
  ``gpt-transcribe`` / ``gpt-realtime-2.1-mini`` (free-first fixes, 2026-11-13).
  Note ``gpt-realtime-2.1-mini`` is a Realtime model, not an
  ``/audio/speech`` model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

__all__ = [
    "PAID_OPT_IN_ENV",
    "PaidOptInRequired",
    "FreeTierExhausted",
    "FreeTierLimit",
    "FREE_TIERS",
    "PRIORITY",
    "PAID_PROVIDERS",
    "FREE_STUN_SERVERS",
    "paid_opt_in_enabled",
    "select_provider",
    "FreeTierUsage",
    "check_oracle_always_free",
    "check_current_instance",
    "stripe_livemode_default",
    "default_ice_servers",
    "free_first_status",
]

PAID_OPT_IN_ENV = "SDS_ALLOW_PAID_PROVIDERS"


class PaidOptInRequired(ValueError):
    """A paid provider was requested but the owner has not opted in."""


class FreeTierExhausted(ValueError):
    """A free tier's known limit would be exceeded by the requested use."""


@dataclass(frozen=True)
class FreeTierLimit:
    """One verified free resource: what is free, how much, and what it costs after."""

    capability: str
    provider: str
    limit_value: float | None  # None = unlimited / no metered cap known
    limit_unit: str
    period: str
    cost_after: str
    notes: str = ""
    verified: str = "web-2026-11-13"


# ---------------------------------------------------------------------------
# Verified free-tier inventory (see module docstring for sources/caveats).
# ---------------------------------------------------------------------------

FREE_TIERS: tuple[FreeTierLimit, ...] = (
    # -- Oracle Always Free (tenancy rooseveltsanders381, us-phoenix-1) --
    FreeTierLimit("hosting", "oracle-always-free-a1", 2, "OCPU total",
                  "per month (1,500 OCPU-hours)", "$0.01/OCPU-hour after",
                  "12 GB memory total (9,000 GB-hours/mo). Instance "
                  "sanders-dash-seal uses 1 OCPU / 6 GB. Idle instances "
                  "may be reclaimed if 7-day p95 CPU < 20%."),
    FreeTierLimit("hosting", "oracle-always-free-e2-micro", 2, "VMs",
                  "always", "paid shape after",
                  "VM.Standard.E2.1.Micro, 1/8 OCPU + 1 GB each."),
    FreeTierLimit("storage", "oracle-always-free-block", 200, "GB total",
                  "always", "$0.0255/GB-month after",
                  "Boot + block volumes combined; 5 volume backups. "
                  "Boot volume sanders-dash-seal is 47 GB."),
    FreeTierLimit("storage", "oracle-always-free-object", 20, "GB total",
                  "per month", "$0.0255/GB-month (Standard) after",
                  "20 GB across Standard/Infrequent/Archive per the "
                  "Always Free page; the Limits page says 10 GB. "
                  "Plan to 10 GB until the console confirms 20 GB. "
                  "50,000 Object Storage API requests/month."),
    FreeTierLimit("networking", "oracle-always-free-egress", 10, "TB",
                  "per month", "paid egress after",
                  "Outbound data transfer. Oracle announced elimination "
                  "of egress charges Feb 2026; the Always Free page "
                  "still lists 10 TB, so plan to 10 TB."),
    FreeTierLimit("database", "oracle-always-free-autonomous", 2, "databases",
                  "always", "paid Autonomous DB after",
                  "1 OCPU + 20 GB each, up to 20 sessions. None is "
                  "currently in use (console check 2026-11-13: no items)."),
    FreeTierLimit("database", "oracle-always-free-nosql", 133_000_000,
                  "reads+writes", "per month",
                  "paid NoSQL after",
                  "Across 3 tables of 25 GB. Reported by third-party "
                  "summaries of Oracle docs; confirm in console."),
    # -- Local / offline ($0, no account, no key) --
    FreeTierLimit("stt", "faster-whisper-local", None, "minutes",
                  "unlimited", "$0",
                  "Local STT, offline after a one-time model download. "
                  "Default model tiny. No key, no account.", "in-repo"),
    FreeTierLimit("tts", "system-tts-pyttsx3", None, "characters",
                  "unlimited", "$0",
                  "Offline via pyttsx3 / espeak-ng. No key, no account.",
                  "in-repo"),
    FreeTierLimit("storage", "sqlite-ledger", None, "rows",
                  "unlimited", "$0",
                  "Local SQLite ledger on the free VM's disk.", "in-repo"),
    FreeTierLimit("inference", "local-inference-localhost", None, "requests",
                  "unlimited", "$0",
                  "Localhost OpenAI-compatible endpoint only "
                  "(core_platform/local_inference.py, /run/sds/ai-model.json). "
                  "Not wired into Daedalus yet.", "in-repo"),
    # -- Free tiers / one-time credits (hosted, account required) --
    FreeTierLimit("stt", "deepgram-nova-3", 200, "USD credit (one-time)",
                  "until used (docs say 1 year)", "$0.0043/min pre-recorded, "
                  "$0.0077/min streaming ($0.0048 promo)",
                  "No card required. ~43,000 min Nova-3 pre-recorded. "
                  "NOT a permanent free plan: once the $200 is gone, "
                  "usage is paid. Track the balance; never auto-top-up."),
    FreeTierLimit("stt", "openai-gpt-transcribe", 0, "minutes free",
                  "n/a", "$0.0045/min",
                  "No free tier. Paid-only, opt-in only. "
                  "whisper-1 is deprecated, removed 26 Feb 2027.",
                  "well-known"),
    FreeTierLimit("tts", "google-cloud-tts", 4_000_000, "characters",
                  "per month", "$4/1M chars (Standard/WaveNet) after",
                  "Standard + WaveNet share the 4M pool. Neural2: 1M free, "
                  "$16/1M after. Billing MUST be enabled on the GCP "
                  "project even inside the free allowance."),
    FreeTierLimit("tts", "elevenlabs-free", 10_000, "credits",
                  "per month", "Starter $6/mo after",
                  "~10 minutes of speech. NON-COMMERCIAL ONLY, no "
                  "rollover. Commercial use needs a paid plan."),
    FreeTierLimit("tts", "openai-tts", 0, "characters free",
                  "n/a", "paid per 1k chars",
                  "No free tier. Paid-only, opt-in only. "
                  "tts-1 / tts-1-hd deprecated 1 Oct 2026, shutdown "
                  "6 Jan 2027. Do not build new on them.", "well-known"),
    FreeTierLimit("inference", "anthropic-claude", 0, "tokens free",
                  "n/a", "paid per token",
                  "NO free tier for live Claude inference. Paid-only, "
                  "opt-in only, key + owner-named model required.",
                  "well-known"),
    FreeTierLimit("inference", "openai-realtime", 0, "minutes free",
                  "n/a", "paid per minute",
                  "NO free tier for live OpenAI inference / Realtime. "
                  "Paid-only, opt-in only.", "well-known"),
    # -- Video / realtime --
    FreeTierLimit("video", "webrtc-free-stun", None, "sessions",
                  "unlimited", "$0",
                  "WebRTC is a free open standard. Free public STUN "
                  "(Google stun:stun.l.google.com:19302) for NAT "
                  "discovery. TURN relay is NOT free: a TURN server "
                  "must be owner-provided or self-hosted.", "well-known"),
    FreeTierLimit("video", "livekit-self-hosted", None, "sessions",
                  "unlimited", "$0 + VM cost (free VM)",
                  "LiveKit server is open source (Apache-2.0). "
                  "Self-host on the Always Free VM. LiveKit Cloud "
                  "is a separate paid service.", "well-known"),
    FreeTierLimit("video", "daily-co-free", 10_000, "participant-minutes",
                  "per month", "$0.004/part-min after",
                  "Daily.co free tier as reported in repo research; "
                  "re-check before budgeting.", "well-known"),
    # -- Google services already connected (free) --
    FreeTierLimit("productivity", "google-workspace-connected", None, "use",
                  "ongoing", "$0",
                  "Gmail, Calendar, Docs, Sheets already connected "
                  "2026-11-13 (free Google accounts). Use only where "
                  "they actually help (Docs drafting, Calendar "
                  "scheduling, Gmail notifications).", "in-repo"),
    FreeTierLimit("hosting", "github-free", None, "use",
                  "ongoing", "$0",
                  "GitHub free tier for the public repo, Actions minutes "
                  "per the free plan. No paid runner.", "well-known"),
)

# Free-first priority order per capability: first available wins.
# Paid providers are last in every list and gated by opt-in (see below).
PRIORITY: dict[str, tuple[str, ...]] = {
    "stt": ("faster-whisper-local", "deepgram-nova-3",
            "openai-gpt-transcribe"),
    "tts": ("system-tts-pyttsx3", "google-cloud-tts", "elevenlabs-free",
            "openai-tts"),
    "inference": ("local-inference-localhost", "anthropic-claude",
                  "openai-realtime"),
    "video": ("webrtc-free-stun", "livekit-self-hosted", "daily-co-free"),
    "storage": ("sqlite-ledger", "oracle-always-free-object"),
    "hosting": ("oracle-always-free-a1", "oracle-always-free-e2-micro"),
    "database": ("sqlite-ledger", "oracle-always-free-autonomous",
                 "oracle-always-free-nosql"),
}

# Providers that have NO free allowance at all and therefore require
# explicit owner opt-in. Free-allowance providers (Deepgram $200 credit,
# Google TTS 4M chars/month, ElevenLabs 10k credits/month, Daily.co free
# minutes, Oracle Object Storage within its free GB) are usable by
# default -- that is the point of the free-first rule -- but their use
# must be tracked with FreeTierUsage, and exhaustion must raise
# FreeTierExhausted instead of silently switching to paid. Everything
# not listed here is free (local/offline or a free allowance).
PAID_PROVIDERS = frozenset({
    "openai-gpt-transcribe",
    "openai-tts",
    "anthropic-claude",
    "openai-realtime",
})

# Providers with a free allowance that is exhaustible or carries a
# caveat (account/billing-enabled, non-commercial only, one-time credit).
# Usable by default; track usage and stop at the limit.
FREE_ALLOWANCE_PROVIDERS = frozenset({
    "deepgram-nova-3",
    "google-cloud-tts",
    "elevenlabs-free",
    "daily-co-free",
    "oracle-always-free-object",
})

FREE_STUN_SERVERS: tuple[str, ...] = ("stun:stun.l.google.com:19302",)


def paid_opt_in_enabled(env: Mapping[str, str] | None = None) -> bool:
    """True only when the owner explicitly opted into paid providers.

    The flag is ``SDS_ALLOW_PAID_PROVIDERS=1``. Any other value (including
    unset, ``"true"``, ``"yes"``) means opt-in is OFF. This is deliberate:
    paid use must be an explicit, unambiguous act, never a default.
    """
    source = os.environ if env is None else env
    return source.get(PAID_OPT_IN_ENV) == "1"


def select_provider(capability: str, available: Sequence[str], *,
                    env: Mapping[str, str] | None = None) -> str:
    """Return the free-first provider to use for ``capability``.

    ``available`` is the list of providers that are actually usable right
    now (package installed, key present, credential file present, model
    downloaded). The first provider in the free-first priority order that
    is available wins. Free-allowance providers (Deepgram $200 credit,
    Google TTS free tier, ElevenLabs free credits) are usable by default;
    track their use with FreeTierUsage so exhaustion is reported instead
    of silently switching to paid. A strictly paid provider (no free
    allowance) is skipped unless the owner opted in. Raises
    :class:`PaidOptInRequired` when only paid providers are available
    and opt-in is off, and ``ValueError`` when nothing is available at
    all. Never returns a paid provider by default.
    """
    order = PRIORITY.get(capability)
    if order is None:
        raise ValueError(f"Unknown capability: {capability!r}")
    available_set = set(available)
    paid_seen: list[str] = []
    for provider in order:
        if provider not in available_set:
            continue
        if provider in PAID_PROVIDERS:
            paid_seen.append(provider)
            if not paid_opt_in_enabled(env):
                continue
        return provider
    if paid_seen:
        raise PaidOptInRequired(
            f"Only paid provider(s) available for {capability}: "
            f"{', '.join(paid_seen)}. Free options are unavailable and "
            f"the owner has not opted in ({PAID_OPT_IN_ENV}=1). "
            f"Enable a free provider or opt in explicitly."
        )
    raise ValueError(
        f"No provider available for {capability}. Free-first order is "
        f"{', '.join(order)}; none of them is usable right now."
    )


@dataclass
class FreeTierUsage:
    """Usage recorded against known free-tier limits.

    ``limits`` maps provider name -> monthly (or one-time) allowance in
    the provider's own unit (characters, minutes, credits, USD).
    Recording usage past the limit raises :class:`FreeTierExhausted`
    instead of silently switching to paid. A provider with no entry in
    ``limits`` is treated as unlimited (local/offline).
    """

    limits: Mapping[str, float] = field(default_factory=lambda: {
        "google-cloud-tts": 4_000_000,      # chars/month, Standard/WaveNet
        "elevenlabs-free": 10_000,          # credits/month
        "deepgram-nova-3": 200,             # USD one-time credit
        "daily-co-free": 10_000,            # participant-minutes/month
        "oracle-always-free-object": 20,    # GB (plan to 10 until confirmed)
    })
    used: dict[str, float] = field(default_factory=dict)

    def record(self, provider: str, amount: float, *, unit: str = "") -> float:
        """Record ``amount`` of use. Returns the new total used.

        Raises FreeTierExhausted if the new total would exceed the known
        free allowance. Raises ValueError for negative amounts.
        """
        if amount < 0:
            raise ValueError("Usage amount must not be negative")
        limit = self.limits.get(provider)
        total = self.used.get(provider, 0.0) + amount
        if limit is not None and total > limit:
            raise FreeTierExhausted(
                f"{provider}: {total:g} {unit or 'units'} would exceed "
                f"the free allowance of {limit:g}. Free tier exhausted; "
                f"do not switch to paid without explicit owner opt-in "
                f"({PAID_OPT_IN_ENV}=1)."
            )
        self.used[provider] = total
        return total

    def remaining(self, provider: str) -> float | None:
        """Free allowance left for ``provider``; None means unlimited."""
        limit = self.limits.get(provider)
        if limit is None:
            return None
        return max(0.0, limit - self.used.get(provider, 0.0))

    def exhausted(self, provider: str) -> bool:
        """True when the known free allowance for ``provider`` is used up."""
        remaining = self.remaining(provider)
        return remaining is not None and remaining <= 0

    def status(self) -> dict[str, dict[str, float | None]]:
        """Per-provider usage report: used / limit / remaining."""
        out: dict[str, dict[str, float | None]] = {}
        for provider, limit in self.limits.items():
            used = self.used.get(provider, 0.0)
            out[provider] = {
                "used": used,
                "limit": limit,
                "remaining": max(0.0, limit - used),
            }
        return out


# ---------------------------------------------------------------------------
# Oracle Always Free guard
# ---------------------------------------------------------------------------

ORACLE_A1_OCPU_LIMIT = 2
ORACLE_A1_MEMORY_GB_LIMIT = 12
ORACLE_BLOCK_GB_LIMIT = 200
ORACLE_OBJECT_GB_LIMIT = 20  # plan to 10 GB until the console confirms 20
ORACLE_EGRESS_TB_LIMIT = 10


def check_oracle_always_free(*, ocpu: float, memory_gb: float,
                             block_volume_gb: float, object_gb: float = 0,
                             egress_tb: float = 0) -> dict[str, object]:
    """Check a planned footprint against Always Free limits (June 2026)."""
    checks = {
        "a1_ocpu": (ocpu, ORACLE_A1_OCPU_LIMIT),
        "a1_memory_gb": (memory_gb, ORACLE_A1_MEMORY_GB_LIMIT),
        "block_volume_gb": (block_volume_gb, ORACLE_BLOCK_GB_LIMIT),
        "object_storage_gb": (object_gb, ORACLE_OBJECT_GB_LIMIT),
        "egress_tb": (egress_tb, ORACLE_EGRESS_TB_LIMIT),
    }
    detail = {
        name: {"used": used, "limit": limit, "within": used <= limit}
        for name, (used, limit) in checks.items()
    }
    return {
        "within_always_free": all(item["within"] for item in detail.values()),
        "checks": detail,
    }


def check_current_instance() -> dict[str, object]:
    """Check the real instance (1 OCPU / 6 GB, 47 GB boot) vs Always Free."""
    return check_oracle_always_free(
        ocpu=1, memory_gb=6, block_volume_gb=47)


def stripe_livemode_default() -> bool:
    """The platform-wide Stripe default: test mode (livemode False).

    Live charges require an explicit owner decision and a release-verifier
    approval; no code path may default to live. Several existing files
    still default to True (native_runtime.py:104, stream_api.py:24,
    deploy/init_runtime.py:43, deploy/refresh_provider_secrets.py:37,43)
    and must be changed to call this (or to False) before live use.
    """
    return False


def default_ice_servers() -> list[dict[str, str]]:
    """Free STUN servers for WebRTC when the caller supplies none.

    TURN relay is not free and is deliberately NOT defaulted here: if a
    call needs relay, the owner must provide a TURN server.
    """
    return [{"urls": url} for url in FREE_STUN_SERVERS]


def free_first_status(env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Per-capability free-first report: default, order, paid gate."""
    return {
        capability: {
            "default_free_provider": order[0],
            "priority_order": list(order),
            "free_allowance_providers": [
                p for p in order if p in FREE_ALLOWANCE_PROVIDERS],
            "paid_alternatives": [p for p in order if p in PAID_PROVIDERS],
            "paid_opt_in": paid_opt_in_enabled(env),
        }
        for capability, order in PRIORITY.items()
    }
