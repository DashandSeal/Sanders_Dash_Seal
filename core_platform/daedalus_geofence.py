"""Daedalus geographic policy enforcement for ingress, execution and egress.

No default geographic entitlement is assumed. The trusted runtime supplies
an authoritative jurisdiction attestation, not an untrusted request header or
IP-derived guess. Cloud-region and data-residency enforcement additionally
require deployment/network/storage controls outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, FrozenSet, Mapping


class GeoFenceDenied(PermissionError):
    pass


@dataclass(frozen=True)
class GeographicPolicy:
    allowed_countries: FrozenSet[str]
    allowed_regions: FrozenSet[str]
    allowed_cloud_regions: FrozenSet[str]
    policy_version: str

    def __post_init__(self) -> None:
        if not self.allowed_cloud_regions:
            raise ValueError("Cloud-region restrictions must be configured for data residency")
        if not self.policy_version.strip():
            raise ValueError("Geographic policy version required")


@dataclass(frozen=True)
class LocationAttestation:
    country: str
    region: str
    cloud_region: str
    source: str
    trusted: bool


class GeoFence:
    def __init__(
        self, policy: GeographicPolicy,
        audit: Callable[[Mapping[str, str]], None],
    ) -> None:
        if not callable(audit):
            raise TypeError("Geographic audit sink required")
        self.policy = policy
        self.audit = audit

    def enforce(self, *, action: str, location: LocationAttestation) -> None:
        if action not in {"ingress", "execution", "egress", "storage"}:
            raise ValueError("Unknown geographic action")
        allowed = (
            location.trusted
            and bool(location.source)
            and (not self.policy.allowed_countries or location.country in self.policy.allowed_countries)
            and location.cloud_region in self.policy.allowed_cloud_regions
            and (
                not self.policy.allowed_regions
                or location.region in self.policy.allowed_regions
            )
        )
        event = {
            "component": "DAEDALUS",
            "event": "GEOFENCE_DECISION",
            "action": action,
            "result": "allow" if allowed else "deny",
            "country": location.country,
            "region": location.region,
            "cloud_region": location.cloud_region,
            "attestation_source": location.source,
            "policy_version": self.policy.policy_version,
            "time_utc": datetime.now(timezone.utc).isoformat(),
        }
        # Fail closed if a required audit record cannot be written.
        self.audit(event)
        if not allowed:
            raise GeoFenceDenied("Daedalus geographic policy denied operation")
