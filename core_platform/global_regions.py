"""Region-aware configuration for Sanders Dash & Seal (added 2026-11-13).

Single place where hosting regions, per-region latency/timeout policy,
free-first provider fallback order, the global DNS plan and the failover
plan are described. No live call, no credential and no deployment is
made or claimed by this module.

Verified facts this module is built around (checked 2026-11-13, not
re-proven here):

- Oracle tenancy ``rooseveltsanders381``, home region ``us-phoenix-1``.
- Exactly one Always Free Compute instance, ``sanders-dash-seal``
  (VM.Standard.A1.Flex, 1 OCPU, 6 GB, Oracle Linux 9), cost
  Nov 1-13 2026 $0.00. Nothing is deployed live by this module.
- Domains ``sandersdashandseal.com`` and ``sanderslegalhelpersllc.com``
  both resolve (A) to the primary instance; ``www.sanderslegalhelpersllc.com``
  was NXDOMAIN on 2026-11-13 and still needs an A record.

Design rules:

- ``us-phoenix-1`` is the *configured primary default*, read through
  :meth:`GlobalRegionsConfig.from_env`. Code paths must read the config,
  not a region literal. The literal appears here, once, as the default
  value of that config -- the same way a config file holds a default.
- Every other region is a *documented candidate only*. No secondary
  region is provisioned, deployed or live. Selecting one as the runtime
  or primary region is rejected until it is actually provisioned.
- Any region name not in :data:`REGION_REGISTRY` is rejected. There is
  no silent fallback to another region.
- Latency figures are *planning estimates*, not measurements. No probe
  has been run against a secondary region because none exists.
- Timeouts are per-service planning values. The Daedalus value (45 s)
  matches ``core_platform.daedalus_config.DEFAULT_TIMEOUT_SECONDS``.
- The public IPv4 address is never hardcoded here. It is read from
  ``SDS_PUBLIC_IPV4`` when a DNS plan is rendered; when unset, the plan
  renders an explicit ``PRIMARY_INSTANCE_IP_UNSET`` placeholder so a
  missing address can never silently become a wrong address.

Environment variables (all optional):

- ``OCI_REGION`` -- region this process runs in. Default: the primary
  region. Must name a DEPLOYED region.
- ``PRIMARY_REGION`` -- primary region. Default ``us-phoenix-1``. Must
  name a DEPLOYED region.
- ``OCI_TENANCY`` -- tenancy *name* (not OCID). Default
  ``rooseveltsanders381``. The tenancy OCID, when needed, stays in
  ``OCI_TENANCY_OCID`` and is never defaulted here.
- ``SDS_PUBLIC_IPV4`` -- primary instance public IPv4 for DNS-plan
  rendering. No default; unset renders a placeholder.
- ``SDS_TIMEOUT_<SERVICE>`` -- per-service timeout override in seconds,
  e.g. ``SDS_TIMEOUT_LIVEKIT=10``. Must be a finite positive number.
  Services: DAEDALUS, OPENAI, LIVEKIT, DEEPGRAM, ELEVENLABS, GOOGLE.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Literal, Mapping

__all__ = [
    "DEFAULT_PRIMARY_REGION",
    "DEFAULT_TENANCY_NAME",
    "DNS_TTL_SECONDS",
    "REGION_REGISTRY",
    "SERVICES",
    "DeploymentStatus",
    "FallbackStep",
    "GlobalRegionsConfig",
    "Region",
    "RetryPolicy",
    "daedalus_authorized_regions",
    "deployed_regions",
    "dns_plan",
    "failover_plan",
    "fallback_chain",
    "free_first_plan",
    "get_region",
    "retry_policy_for",
    "secondary_candidates",
    "timeout_for",
]

# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------

DeploymentStatus = Literal["DEPLOYED", "NOT_PROVISIONED", "NOT_DEPLOYED"]

#: The only region with anything running in it (verified 2026-11-13).
DEPLOYED: DeploymentStatus = "DEPLOYED"
#: Documented candidate. Nothing exists there; nothing is claimed live.
NOT_PROVISIONED: DeploymentStatus = "NOT_PROVISIONED"
#: Alias kept for readability in tests/docs: same meaning as NOT_PROVISIONED
#: for a secondary region (nothing provisioned, nothing deployed).
NOT_DEPLOYED: DeploymentStatus = "NOT_DEPLOYED"

#: Configured primary default. This is a config default, not a literal
#: buried in a code path: callers read it via GlobalRegionsConfig.
DEFAULT_PRIMARY_REGION = "us-phoenix-1"
#: Verified tenancy name (not OCID). Configured default, overridable.
DEFAULT_TENANCY_NAME = "rooseveltsanders381"

#: DNS TTL for the A records in the global DNS plan (seconds).
DNS_TTL_SECONDS = 300

#: Domains served by the platform. The www host of the second domain is
#: flagged in :func:`dns_plan` as missing (NXDOMAIN, verified 2026-11-13).
DOMAINS = ("sandersdashandseal.com", "sanderslegalhelpersllc.com")


@dataclass(frozen=True)
class Region:
    """One region entry in the registry.

    ``base_latency_ms`` is a *planning estimate* for a same-country
    caller, not a measurement. No probe has been run against a secondary
    region because none exists. ``public_ipv4`` is only ever set from
    the environment at render time; the registry itself holds no IP.
    """

    key: str
    display_name: str
    country: str
    status: DeploymentStatus
    role: str
    always_free_eligible: bool | None
    base_latency_ms: int
    notes: str
    public_ipv4: str | None = None


REGION_REGISTRY: tuple[Region, ...] = (
    Region(
        key="us-phoenix-1",
        display_name="US West (Phoenix)",
        country="US",
        status=DEPLOYED,
        role="primary",
        always_free_eligible=True,
        base_latency_ms=40,
        notes=(
            "Home region. Sole deployed region: one Always Free "
            "VM.Standard.A1.Flex instance (sanders-dash-seal). "
            "Cost Nov 1-13 2026 $0.00."
        ),
    ),
    Region(
        key="us-ashburn-1",
        display_name="US East (Ashburn)",
        country="US",
        status=NOT_PROVISIONED,
        role="secondary-candidate",
        always_free_eligible=True,
        base_latency_ms=70,
        notes=(
            "Documented secondary candidate only. NOT provisioned, NOT "
            "deployed, no instance, no DNS pointing at it. Same-country "
            "candidate so US data-residency posture is unchanged. "
            "Requires owner approval + provisioning before any use."
        ),
    ),
    Region(
        key="us-chicago-1",
        display_name="US Midwest (Chicago)",
        country="US",
        status=NOT_PROVISIONED,
        role="secondary-candidate",
        always_free_eligible=None,
        base_latency_ms=60,
        notes=(
            "Documented secondary candidate only. NOT provisioned, NOT "
            "deployed. Always Free eligibility not verified for this "
            "region; verify against Oracle's Always Free terms before "
            "any provisioning decision."
        ),
    ),
)

_REGIONS_BY_KEY: dict[str, Region] = {region.key: region for region in REGION_REGISTRY}


def get_region(key: str) -> Region:
    """Return the registry entry for ``key``; unknown regions are rejected.

    There is no fallback to the primary region: an unknown region is a
    configuration error, not something to guess around.
    """
    if not isinstance(key, str) or not key.strip():
        raise ValueError("region must be a non-empty string")
    region = _REGIONS_BY_KEY.get(key.strip())
    if region is None:
        raise ValueError(
            f"unknown region {key!r}; known regions: "
            + ", ".join(sorted(_REGIONS_BY_KEY))
        )
    return region


def deployed_regions() -> tuple[Region, ...]:
    """Regions with something actually running in them."""
    return tuple(region for region in REGION_REGISTRY if region.status == DEPLOYED)


def secondary_candidates() -> tuple[Region, ...]:
    """Documented secondary candidates (all NOT_PROVISIONED)."""
    return tuple(
        region
        for region in REGION_REGISTRY
        if region.status in (NOT_PROVISIONED, NOT_DEPLOYED)
    )


def daedalus_authorized_regions() -> frozenset[str]:
    """Region keys Daedalus may process in.

    Integration point for ``core_platform.daedalus_engine``: its
    ``DaedalusEngineConfig.authorized_cloud_regions`` currently hardcodes
    ``frozenset({"us-phoenix-1"})``. That default should in future be
    replaced by this call so the allow-list follows the registry instead
    of a literal. Only DEPLOYED regions are ever authorized.
    """
    return frozenset(region.key for region in deployed_regions())


# ---------------------------------------------------------------------------
# Per-service latency / timeout / retry policy
# ---------------------------------------------------------------------------

#: Per-service base timeouts (seconds) before any region allowance.
#: Daedalus 45 s matches daedalus_config.DEFAULT_TIMEOUT_SECONDS.
#: LiveKit is realtime signalling, so it fails fast and retries often.
SERVICES: dict[str, dict[str, float | int]] = {
    "daedalus": {"timeout_seconds": 45.0, "max_attempts": 3, "backoff_base_seconds": 1.0},
    "openai": {"timeout_seconds": 30.0, "max_attempts": 3, "backoff_base_seconds": 1.0},
    "livekit": {"timeout_seconds": 15.0, "max_attempts": 5, "backoff_base_seconds": 0.5},
    "deepgram": {"timeout_seconds": 30.0, "max_attempts": 3, "backoff_base_seconds": 1.0},
    "elevenlabs": {"timeout_seconds": 30.0, "max_attempts": 3, "backoff_base_seconds": 1.0},
    "google": {"timeout_seconds": 30.0, "max_attempts": 3, "backoff_base_seconds": 1.0},
}

_BACKOFF_FACTOR = 2.0
_MAX_BACKOFF_SECONDS = 30.0


@dataclass(frozen=True)
class RetryPolicy:
    """Retry/backoff policy for one service (planning values)."""

    service: str
    max_attempts: int
    backoff_base_seconds: float
    backoff_factor: float = _BACKOFF_FACTOR
    max_backoff_seconds: float = _MAX_BACKOFF_SECONDS

    def delay_before_attempt(self, attempt: int) -> float:
        """Backoff delay (seconds) before retry ``attempt`` (1-based retry).

        Attempt 1 is the first try and has no delay. Delay grows as
        ``base * factor ** (attempt - 2)`` and is capped at
        ``max_backoff_seconds``. Raises ValueError for attempt < 1.
        """
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        if attempt == 1:
            return 0.0
        delay = self.backoff_base_seconds * (self.backoff_factor ** (attempt - 2))
        return min(delay, self.max_backoff_seconds)


def _service_key(service: str) -> str:
    if not isinstance(service, str) or not service.strip():
        raise ValueError("service must be a non-empty string")
    key = service.strip().lower()
    if key not in SERVICES:
        raise ValueError(
            f"unknown service {service!r}; known services: "
            + ", ".join(sorted(SERVICES))
        )
    return key


def _timeout_override(service: str, env: Mapping[str, str]) -> float | None:
    raw = env.get(f"SDS_TIMEOUT_{service.upper()}")
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"SDS_TIMEOUT_{service.upper()} must be a number") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"SDS_TIMEOUT_{service.upper()} must be a finite positive duration"
        )
    return value


def timeout_for(
    service: str,
    region_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> float:
    """Timeout (seconds) for ``service`` from ``region_key``.

    ``base timeout + region latency allowance``, where the allowance is
    the region's planning latency estimate in seconds. The primary
    region therefore gets the base timeout plus its own small allowance;
    a future secondary region gets a slightly larger one. An
    ``SDS_TIMEOUT_<SERVICE>`` env override replaces the base timeout but
    the region allowance is still added, so a slow region can never be
    configured tighter than its own latency allowance.
    """
    key = _service_key(service)
    source = os.environ if env is None else env
    base = _timeout_override(key, source)
    if base is None:
        base = float(SERVICES[key]["timeout_seconds"])
    region = get_region(region_key) if region_key is not None else None
    allowance = (region.base_latency_ms if region is not None else 0) / 1000.0
    return round(base + allowance, 3)


def retry_policy_for(service: str) -> RetryPolicy:
    """Retry/backoff policy for ``service``."""
    key = _service_key(service)
    spec = SERVICES[key]
    return RetryPolicy(
        service=key,
        max_attempts=int(spec["max_attempts"]),
        backoff_base_seconds=float(spec["backoff_base_seconds"]),
    )


# ---------------------------------------------------------------------------
# Free-first fallback chains
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FallbackStep:
    """One step in a free-first fallback chain.

    ``tier`` is ``"free"`` or ``"paid"``. ``status`` is honest about
    what exists: ``"local-no-key-needed"`` (runs on the host),
    ``"requires-owner-key"`` (paid provider, no key held here),
    ``"requires-provisioning"`` (nothing exists yet), or
    ``"deployed"`` / ``"not-provisioned"`` for hosting.
    """

    name: str
    tier: Literal["free", "paid"]
    status: str
    notes: str


FALLBACK_CHAINS: dict[str, tuple[FallbackStep, ...]] = {
    "stt": (
        FallbackStep("faster-whisper-local", "free", "local-no-key-needed",
                     "Local STT on the host; try first, $0."),
        FallbackStep("deepgram", "paid", "requires-owner-key",
                     "Deepgram Nova-3; only if local STT cannot serve the request."),
        FallbackStep("openai-gpt-transcribe", "paid", "requires-owner-key",
                     "OpenAI gpt-transcribe; whisper-1 is deprecated and is never used."),
    ),
    "tts": (
        FallbackStep("system-tts", "free", "local-no-key-needed",
                     "Host system TTS; try first, $0."),
        FallbackStep("elevenlabs", "paid", "requires-owner-key",
                     "ElevenLabs TTS; owner picks the voice id."),
        FallbackStep("google-tts", "paid", "requires-owner-key",
                     "Google Cloud TTS WaveNet."),
        FallbackStep("openai-tts", "paid", "requires-owner-key",
                     "OpenAI TTS; tts-1 is deprecated and is never used."),
    ),
    "video": (
        FallbackStep("livekit-self-hosted", "free", "requires-provisioning",
                     "Self-hosted LiveKit on the Always Free host; $0 once provisioned."),
        FallbackStep("livekit-cloud", "paid", "requires-owner-key",
                     "LiveKit Cloud; only if self-hosted cannot serve."),
        FallbackStep("daily", "paid", "requires-owner-key",
                     "Daily fallback video provider."),
    ),
    "reasoning": (
        FallbackStep("anthropic-claude", "paid", "requires-owner-key",
                     "Daedalus reasoning via Claude. No free local equivalent "
                     "exists; the chain is honestly a single step, not a "
                     "pretend free tier. Model id comes from the owner only."),
    ),
    "hosting": (
        FallbackStep("oracle-always-free-primary", "free", "deployed",
                     "us-phoenix-1 Always Free instance sanders-dash-seal."),
        FallbackStep("oracle-always-free-secondary", "free", "not-provisioned",
                     "Secondary Always Free region (us-ashburn-1 candidate). "
                     "Not provisioned; requires owner approval first."),
    ),
}


#: First free-first step per timeout service, where one maps cleanly.
#: Daedalus reasoning maps to the "reasoning" chain; the remaining
#: services are providers inside the stt/tts/video chains instead.
_SERVICE_FREE_FIRST: dict[str, str] = {
    "daedalus": FALLBACK_CHAINS["reasoning"][0].name,
}


def fallback_chain(service: str) -> tuple[FallbackStep, ...]:
    """Free-first fallback chain for ``service`` (``stt``/``tts``/``video``/``reasoning``/``hosting``)."""
    if not isinstance(service, str) or not service.strip():
        raise ValueError("service must be a non-empty string")
    key = service.strip().lower()
    if key not in FALLBACK_CHAINS:
        raise ValueError(
            f"unknown fallback service {service!r}; known: "
            + ", ".join(sorted(FALLBACK_CHAINS))
        )
    return FALLBACK_CHAINS[key]


def free_first_plan() -> dict[str, list[dict[str, str]]]:
    """Whole free-first plan as JSON-serializable data (no live state)."""
    return {
        service: [
            {"name": step.name, "tier": step.tier, "status": step.status,
             "notes": step.notes}
            for step in chain
        ]
        for service, chain in FALLBACK_CHAINS.items()
    }


# ---------------------------------------------------------------------------
# Global DNS plan
# ---------------------------------------------------------------------------

#: Per-record verified status from the 2026-11-13 DNS check.
_DNS_VERIFIED_STATUS = {
    ("sandersdashandseal.com", ""): "verified-2026-11-13",
    ("sandersdashandseal.com", "www"): "verified-2026-11-13",
    ("sanderslegalhelpersllc.com", ""): "verified-2026-11-13",
    ("sanderslegalhelpersllc.com", "www"): "missing-nxdomain-2026-11-13",
}


def dns_plan(primary_ipv4: str | None = None) -> list[dict[str, str | int]]:
    """Global DNS plan for both domains (a plan, not a live zone).

    Four A records, TTL 300, all pointing at the primary instance.
    ``primary_ipv4`` should come from ``SDS_PUBLIC_IPV4``; when it is
    ``None`` the target renders as ``PRIMARY_INSTANCE_IP_UNSET`` so a
    missing address is visible instead of silently wrong. The
    ``www.sanderslegalhelpersllc.com`` record is flagged
    ``missing-nxdomain-2026-11-13``: it was NXDOMAIN on 2026-11-13 and
    still needs its A record creating in GoDaddy DNS.
    """
    records: list[dict[str, str | int]] = []
    for domain in DOMAINS:
        for prefix in ("", "www"):
            host = f"{prefix}.{domain}" if prefix else domain
            records.append({
                "host": host,
                "type": "A",
                "ttl_seconds": DNS_TTL_SECONDS,
                "target": primary_ipv4 or "PRIMARY_INSTANCE_IP_UNSET",
                "verified_status": _DNS_VERIFIED_STATUS[(domain, prefix)],
                "action": (
                    "CREATE A record (missing)"
                    if _DNS_VERIFIED_STATUS[(domain, prefix)].startswith("missing")
                    else "keep (verified)"
                ),
            })
    return records


# ---------------------------------------------------------------------------
# Failover plan (documented plan only -- NOT deployed, NOT live)
# ---------------------------------------------------------------------------

def failover_plan() -> dict[str, object]:
    """Documented multi-region failover plan. Status is PLAN_ONLY.

    Nothing here is automated, tested or live. The primary region is
    the only deployed region; failover cannot execute until a secondary
    region is provisioned, DNS is dual-pointed, and a backup-restore
    test has passed. RTO/RPO below are *targets* for that future work,
    not measured values.
    """
    return {
        "schema": 1,
        "status": "PLAN_ONLY",
        "deployed": False,
        "primary_region": DEFAULT_PRIMARY_REGION,
        "secondary_region_candidate": "us-ashburn-1",
        "secondary_region_status": NOT_PROVISIONED,
        "rto_target": "4 hours (manual, target only -- not measured)",
        "rpo_target": "1 hour (target only -- backup cadence not yet proven)",
        "preconditions": [
            "Owner approval for a secondary-region deploy (not granted).",
            "Secondary region provisioned (Always Free A1 instance + boot volume).",
            "Backup/restore test passed from primary to secondary.",
            "DNS dual-pointed with health checks; TTLs lowered before cutover.",
            "Secondary region verified serving /healthz before any traffic moves.",
        ],
        "steps": [
            "1. Confirm primary-region outage (not a proxy or DNS issue) and record the decision.",
            "2. Confirm the secondary region is healthy and on the same release commit as primary.",
            "3. Restore the latest verified backup into the secondary region and verify integrity.",
            "4. Lower DNS TTLs, then point both apexes and www hosts at the secondary region.",
            "5. Verify TLS, /healthz, /readyz and the voice/status endpoints from outside the region.",
            "6. Announce the failover; keep primary DNS records ready for failback.",
            "7. Fail back only after the primary region is verified healthy and re-synced.",
        ],
        "explicitly_not_done": [
            "No secondary region is provisioned or deployed.",
            "No failover has been executed or drilled.",
            "No automated health-check-driven DNS cutover exists.",
            "No cross-region backup replication is running.",
        ],
    }


# ---------------------------------------------------------------------------
# Env-driven config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GlobalRegionsConfig:
    """Validated region configuration, built from explicit args or env.

    ``primary_region`` and ``runtime_region`` must both name DEPLOYED
    regions. ``primary_ipv4`` is ``None`` unless ``SDS_PUBLIC_IPV4``
    is set -- the real address is never a default in code.
    """

    tenancy: str = DEFAULT_TENANCY_NAME
    primary_region: str = DEFAULT_PRIMARY_REGION
    runtime_region: str = DEFAULT_PRIMARY_REGION
    primary_ipv4: str | None = None
    timeout_overrides: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenancy or not self.tenancy.strip():
            raise ValueError("tenancy must not be empty")
        primary = get_region(self.primary_region)
        if primary.status != DEPLOYED:
            raise ValueError(
                f"PRIMARY_REGION {self.primary_region!r} is {primary.status}; "
                "the primary region must be DEPLOYED"
            )
        runtime = get_region(self.runtime_region)
        if runtime.status != DEPLOYED:
            raise ValueError(
                f"OCI_REGION {self.runtime_region!r} is {runtime.status}; "
                "the runtime region must be DEPLOYED (secondary regions "
                "are documented candidates only)"
            )
        if self.primary_ipv4 is not None and not self.primary_ipv4.strip():
            raise ValueError("primary_ipv4 must not be blank when set")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "GlobalRegionsConfig":
        """Build config from the process environment (or a supplied mapping)."""
        source = os.environ if env is None else env
        tenancy = (source.get("OCI_TENANCY") or "").strip() or DEFAULT_TENANCY_NAME
        primary = (source.get("PRIMARY_REGION") or "").strip() or DEFAULT_PRIMARY_REGION
        runtime = (source.get("OCI_REGION") or "").strip() or primary
        ipv4 = (source.get("SDS_PUBLIC_IPV4") or "").strip() or None
        overrides = {
            service: override
            for service in SERVICES
            if (override := _timeout_override(service, source)) is not None
        }
        return cls(
            tenancy=tenancy,
            primary_region=primary,
            runtime_region=runtime,
            primary_ipv4=ipv4,
            timeout_overrides=overrides,
        )

    def timeout_for(self, service: str) -> float:
        """Timeout for ``service`` from the runtime region, honouring overrides."""
        env = {
            f"SDS_TIMEOUT_{name.upper()}": repr(value)
            for name, value in self.timeout_overrides.items()
        }
        return timeout_for(service, self.runtime_region, env=env)

    def retry_policy_for(self, service: str) -> RetryPolicy:
        """Retry/backoff policy for ``service``."""
        return retry_policy_for(service)

    def dns_plan(self) -> list[dict[str, str | int]]:
        """Global DNS plan rendered with this config's primary IPv4."""
        return dns_plan(self.primary_ipv4)

    def summary(self) -> dict[str, object]:
        """JSON-serializable summary. Contains no secrets and no OCIDs."""
        return {
            "schema": 1,
            "tenancy": self.tenancy,
            "primary_region": self.primary_region,
            "runtime_region": self.runtime_region,
            "primary_ipv4_set": self.primary_ipv4 is not None,
            "deployed_regions": [region.key for region in deployed_regions()],
            "secondary_candidates": [
                {"region": region.key, "status": region.status}
                for region in secondary_candidates()
            ],
            "failover_status": "PLAN_ONLY (not deployed)",
            "dns_missing_records": [
                record["host"]
                for record in self.dns_plan()
                if str(record["verified_status"]).startswith("missing")
            ],
            "services": {
                service: {
                    "timeout_seconds": self.timeout_for(service),
                    "max_attempts": self.retry_policy_for(service).max_attempts,
                    # Only Daedalus maps onto a fallback chain (reasoning);
                    # the other services are single providers with their own
                    # chains defined under stt/tts/video in free_first_plan().
                    "free_first": _SERVICE_FREE_FIRST.get(service),
                }
                for service in sorted(SERVICES)
            },
        }

    def redacted_summary(self) -> str:
        """One-line safe summary (no secrets, no IPs, no OCIDs)."""
        return json.dumps(self.summary(), sort_keys=True)
