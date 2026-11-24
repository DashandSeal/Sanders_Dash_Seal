"""Sanders Signal — roles: writer, approver, publisher, per company.

Roles come from ``SANDERS_SIGNAL_ROLES_JSON``; the default is that the
owner holds all three roles for all four companies. Anyone not listed
is denied by default. A writer cannot approve; an approver cannot
publish without the publisher role. Every denial carries a reason.
"""
from __future__ import annotations

from .config import ALL_COMPANIES, roles_config

ROLES = ("writer", "approver", "publisher")


def _officer_roles(officer: str) -> dict[str, list[str]]:
    """The role -> company list for one officer (empty if unlisted)."""
    mapping = roles_config()
    entry = mapping.get(officer)
    if not isinstance(entry, dict):
        return {}
    result: dict[str, list[str]] = {}
    for role in ROLES:
        companies = entry.get(role)
        if isinstance(companies, list):
            result[role] = [str(c) for c in companies]
        else:
            result[role] = []
    return result


def _has_role(officer: str, role: str, company: str) -> tuple[bool, str]:
    companies = _officer_roles(officer).get(role, [])
    if company in companies or "all" in companies:
        return True, ""
    return (
        False,
        "denied: officer %r does not hold the %s role for %s" % (officer, role, company),
    )


def can_write(officer: str, company: str) -> tuple[bool, str]:
    """May this officer compose for this company?"""
    return _has_role(officer, "writer", company)


def can_approve(officer: str, company: str) -> tuple[bool, str]:
    """May this officer approve for this company?"""
    return _has_role(officer, "approver", company)


def can_publish(officer: str, company: str) -> tuple[bool, str]:
    """May this officer publish for this company?"""
    return _has_role(officer, "publisher", company)


def check_action(officer: str, company: str, action: str) -> tuple[bool, str]:
    """Generic role check for ``action`` in writer / approver / publisher."""
    if action not in ROLES:
        return False, "denied: unknown action %r" % (action,)
    return _has_role(officer, action, company)


__all__ = [
    "ROLES",
    "can_write",
    "can_approve",
    "can_publish",
    "check_action",
]
