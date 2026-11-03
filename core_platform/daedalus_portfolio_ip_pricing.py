"""Portfolio-wide IP protection and premium licensing policy.

Applies to registered past, present and future platforms/subsystems.
A policy is not a patent filing, patent grant, or legal determination.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Callable, Mapping

from .daedalus_ip_protection import InventionRecord, sign_evidence, publication_guard


PRICE_USD_MONTHLY = {
    "enterprise_api": Decimal("100000"),
    "cobol_bridge_enterprise": Decimal("350000"),
    "global_infrastructure": Decimal("750000"),
    "sovereign_deployment": Decimal("1500000"),
}
PRICE_USD_ANNUAL = {"strategic_enterprise_license": Decimal("20000000")}
IP_SERVICE_USD = {
    "portfolio_ip_governance_annual": Decimal("250000"),
    "invention_intake_per_subsystem": Decimal("2500"),
    "confidential_provenance_setup_per_platform": Decimal("15000"),
    "enterprise_ip_licensing_administration_annual": Decimal("100000"),
}
# Commercial proposals only; actual legal filing, prosecution, renewal and
# attorney costs are separately scoped, quoted and paid to appropriate parties.


@dataclass(frozen=True)
class ProtectedAsset:
    asset_id: str
    platform_id: str
    subsystem_id: str
    generation: str
    source_sha256: str
    invention_id: str
    classification: str = "restricted"

    def __post_init__(self) -> None:
        if self.generation not in {"past", "present", "future"}:
            raise ValueError("Explicit asset generation required")
        if not all((self.asset_id, self.platform_id, self.subsystem_id, self.invention_id)):
            raise ValueError("Asset identity must be complete")
        if len(self.source_sha256) != 64:
            raise ValueError("SHA-256 digest required")


class PortfolioProtection:
    """Secure evidence and controlled publication for all registered assets."""

    def __init__(
        self, *, signing_key: bytes,
        persist_confidential: Callable[[ProtectedAsset, InventionRecord, str], None],
    ) -> None:
        if len(signing_key) < 32 or not callable(persist_confidential):
            raise ValueError("Secure signing key and private evidence store required")
        self.signing_key = signing_key
        self.persist_confidential = persist_confidential

    def protect(
        self, *, asset_id: str, platform_id: str, subsystem_id: str,
        generation: str, invention_id: str, title: str,
        inventor_assertions: tuple[str, ...], source: bytes,
    ) -> ProtectedAsset:
        record = InventionRecord.from_source(
            invention_id=invention_id, title=title,
            inventor_assertions=inventor_assertions, source=source,
        )
        asset = ProtectedAsset(
            asset_id=asset_id, platform_id=platform_id,
            subsystem_id=subsystem_id, generation=generation,
            source_sha256=sha256(source).hexdigest(), invention_id=invention_id,
        )
        signature = sign_evidence(record, self.signing_key)
        self.persist_confidential(asset, record, signature)
        return asset

    @staticmethod
    def authorize_publication(
        asset: ProtectedAsset, *,
        explicit_publication_authorization: bool,
        patent_counsel_clearance: bool,
    ) -> None:
        publication_guard(
            classification=asset.classification,
            explicit_publication_authorization=explicit_publication_authorization,
            patent_counsel_clearance=patent_counsel_clearance,
        )


def proposed_rate_card() -> Mapping[str, object]:
    return {
        "currency": "USD",
        "status": "proposed_not_verified_market_rate",
        "monthly": {k: str(v) for k, v in PRICE_USD_MONTHLY.items()},
        "annual": {k: str(v) for k, v in PRICE_USD_ANNUAL.items()},
        "ip_services": {k: str(v) for k, v in IP_SERVICE_USD.items()},
        "core_ip_safeguards": "included_in_enterprise_license",
        "specialist_ip_services": "optional_separately_negotiated",
        "scenario_customers": {"enterprise_api": 10, "cobol_bridge_enterprise": 5, "global_infrastructure": 3, "sovereign_deployment": 2, "strategic_enterprise_license": 2},
        "scenario_annual_revenue_usd": "136000000",
        "scenario_status": "illustrative_not_forecast",
        "scope": "all registered past present and future platforms and subsystems",
        "legal_patent_fees": "excluded_quoted_separately",
        "ownership": "no transfer of underlying IP by subscription",
    }
