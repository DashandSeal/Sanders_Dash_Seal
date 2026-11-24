"""Sanders Signal — companies, routing identities and configuration.

All configuration comes from the environment (``SANDERS_SIGNAL_*``).
Missing configuration is diagnostic-only, never an exception at import.
No secrets, no addresses and no contact info are stored here.
"""
from __future__ import annotations

import json
import os

# The four companies. Routing identities only — no invented handles,
# page ids or tokens. S & G Security Inc. has a Facebook Page and no
# Instagram account yet.
COMPANIES: dict[str, dict[str, object]] = {
    "home_healthcare": {
        "legal_name": "Sanders Home Healthcare & Caregivers LLC",
        "instagram": "@sandershomehealthcare",
        "facebook_page": True,
    },
    "senior_living": {
        "legal_name": "Sanders Senior Living LLC",
        "instagram": "@sandersseniorlivingllc",
        "facebook_page": True,
    },
    "legal_helpers": {
        "legal_name": "Sanders Legal Helpers LLC (DBA Sanders Dash & Seal)",
        "instagram": "@sanderslegalhelpers",
        "facebook_page": True,
    },
    "s_and_g_security": {
        "legal_name": "S & G Security Inc. (corporate headquarters)",
        "instagram": None,
        "facebook_page": True,
    },
}

# The corporate headquarters company id.
HEADQUARTERS_COMPANY = "s_and_g_security"

# All company ids, in a stable order.
ALL_COMPANIES: list[str] = [
    "home_healthcare",
    "senior_living",
    "legal_helpers",
    "s_and_g_security",
]

# Networks the hub knows, in fan-out order.
NETWORKS: list[str] = [
    "facebook",
    "instagram",
    "linkedin",
    "threads",
    "youtube",
    "tiktok",
    "x",
]

# The one phone number the hub ever permits in post text.
PERMITTED_PHONE_DIGITS = "4145023325"


class AdapterStatus:
    """Diagnostic status of one network adapter for one company."""

    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_CONNECTED = "NOT_CONNECTED"

    def __init__(self, status: str, reason: str = "") -> None:
        self.status = status
        self.reason = reason

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "AdapterStatus(%r, %r)" % (self.status, self.reason)


def env(name: str, default: str | None = None) -> str | None:
    """Read one ``SANDERS_SIGNAL_*`` variable; never raises."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    return str(value)


def meta_env_name(company: str, field: str) -> str:
    """Per-company Meta env name, e.g. ``SANDERS_SIGNAL_META_HOME_HEALTHCARE_PAGE_TOKEN``."""
    return "SANDERS_SIGNAL_META_%s_%s" % (company.upper(), field)


def meta_status(company: str) -> AdapterStatus:
    """Whether the Meta adapter has what it needs for one company.

    Per-company values win; the global values are the fallback.
    Absent values mean NOT_CONFIGURED, never an exception.
    """
    token = env(meta_env_name(company, "PAGE_TOKEN")) or env(
        "SANDERS_SIGNAL_META_PAGE_TOKEN"
    )
    page_id = env(meta_env_name(company, "PAGE_ID")) or env(
        "SANDERS_SIGNAL_META_PAGE_ID"
    )
    if not token or not page_id:
        return AdapterStatus(
            AdapterStatus.NOT_CONFIGURED,
            "Meta not configured for %s: no Page token/id in the environment" % company,
        )
    return AdapterStatus(AdapterStatus.CONFIGURED, "Meta configured for %s" % company)


def roles_config() -> dict:
    """Role mapping from ``SANDERS_SIGNAL_ROLES_JSON``.

    Default: the owner holds writer, approver and publisher for all
    four companies. A bad value is ignored (diagnostic-only) and the
    default applies.
    """
    raw = env("SANDERS_SIGNAL_ROLES_JSON")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    return {
        "owner": {
            "writer": list(ALL_COMPANIES),
            "approver": list(ALL_COMPANIES),
            "publisher": list(ALL_COMPANIES),
        }
    }


def owner_address() -> str | None:
    """The owner's mailing address, only if the owner sets it in the
    environment. It is never written into this module."""
    return env("SANDERS_SIGNAL_OWNER_ADDRESS")


__all__ = [
    "COMPANIES",
    "HEADQUARTERS_COMPANY",
    "ALL_COMPANIES",
    "NETWORKS",
    "PERMITTED_PHONE_DIGITS",
    "AdapterStatus",
    "env",
    "meta_env_name",
    "meta_status",
    "roles_config",
    "owner_address",
]
