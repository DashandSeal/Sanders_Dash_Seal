"""Global trust policy for Daedalus geographic enforcement.

Global eligibility is the default; trust and legal residency remain mandatory.
Country codes are ISO 3166-1 alpha-2, cloud regions are provider-specific.
The trusted ingress supplies verified identity and location attestations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, FrozenSet, Mapping

from .daedalus_geofence import GeoFenceDenied, LocationAttestation

__all__ = [
    "GlobalTrustContext",
    "GlobalTrustEnforcer",
    "GlobalTrustPolicy",
]

logger = logging.getLogger("daedalus.trust")


@dataclass(frozen=True)
class GlobalTrustPolicy:
    authorized_cloud_regions: FrozenSet[str]
    prohibited_countries: FrozenSet[str] = frozenset()
    restricted_data_countries: FrozenSet[str] = frozenset()
    policy_version: str = "global-trust-v1"

    def __post_init__(self) -> None:
        if not self.authorized_cloud_regions or not self.policy_version:
            raise ValueError("Explicit trusted cloud regions and policy version required")


@dataclass(frozen=True)
class GlobalTrustContext:
    subject_id: str
    identity_verified: bool
    authorization_granted: bool
    location: LocationAttestation
    data_classification: str
    processing_country: str
    processing_cloud_region: str
    residency_permitted: bool


class GlobalTrustEnforcer:
    """Global access without nationality-based blanket exclusion.

    Infrastructure and upstream authentication must independently enforce
    identity, routing, data storage, and network restrictions.
    """

    def __init__(
        self, policy: GlobalTrustPolicy,
        audit: Callable[[Mapping[str, str]], None],
    ) -> None:
        if not callable(audit):
            raise TypeError("A durable geographic audit sink is required")
        self.policy = policy
        self.audit = audit

    def enforce(self, *, action: str, context: GlobalTrustContext) -> None:
        if action not in {"ingress", "execution", "egress", "storage"}:
            raise ValueError("Unknown geographic action")
        location = context.location
        allowed = (
            bool(context.subject_id)
            and context.identity_verified
            and context.authorization_granted
            and location.trusted
            and bool(location.source)
            and len(location.country) == 2
            and len(context.processing_country) == 2
            and location.country not in self.policy.prohibited_countries
            and context.processing_country not in self.policy.prohibited_countries
            and context.processing_cloud_region in self.policy.authorized_cloud_regions
            and context.residency_permitted
            and (
                context.data_classification != "restricted"
                or context.processing_country not in self.policy.restricted_data_countries
            )
        )
        # Never put personal identity, invention content, or credentials in logs.
        self.audit({
            "component": "DAEDALUS",
            "event": "GLOBAL_TRUST_DECISION",
            "action": action,
            "decision": "allow" if allowed else "deny",
            "country": location.country,
            "processing_country": context.processing_country,
            "cloud_region": context.processing_cloud_region,
            "policy_version": self.policy.policy_version,
        })
        logger.debug(
            "daedalus global trust action=%s decision=%s cloud_region=%s policy=%s",
            action, "allow" if allowed else "deny",
            context.processing_cloud_region, self.policy.policy_version,
        )
        if not allowed:
            raise GeoFenceDenied("Daedalus global trust policy denied operation")
