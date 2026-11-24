"""Sanders Signal — pre-publish brand guardrails.

Every post passes :func:`check_post` before it can publish. A failed
check blocks the publish with the exact reason recorded. The hub never
adds an address or contact info, and it never routes a post to the
wrong company.
"""
from __future__ import annotations

import re

from .config import ALL_COMPANIES, HEADQUARTERS_COMPANY, PERMITTED_PHONE_DIGITS, owner_address

# Street words that mark a street-address pattern.
_STREET_WORDS = (
    "Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|"
    "Boulevard|Blvd|Way|Parkway|Pkwy|Place|Pl|Circle|Cir|Trail|Trl"
)
_STATES = r"CO|WI|AZ|Colorado|Wisconsin|Arizona"
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9'.\- ]{2,60}?\b(?:%s)\b.{0,100}?\b(?:%s)\b.{0,25}?\b\d{5}(?:-\d{4})?\b"
    % (_STREET_WORDS, _STATES),
    re.IGNORECASE,
)

# Phone-like digit runs: optional country code, separators allowed.
_PHONE_RE = re.compile(r"\+?1?[\s\-.]*\(?\d{3}\)?[\s\-.]*\d{3}[\s\-.]*\d{4}\b")
_DIGITS_RE = re.compile(r"\d+")

# Media references must be a known library asset id or an http(s) URL.
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _digits(value: str) -> str:
    return "".join(_DIGITS_RE.findall(value))


def _find_phones(text: str) -> list[str]:
    """Phone-like strings in the text, normalised to digits."""
    found: list[str] = []
    for match in _PHONE_RE.finditer(text or ""):
        digits = _digits(match.group(0))
        if len(digits) >= 10:
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            found.append(digits)
    return found


def check_post(
    post,
    known_asset_ids: set | frozenset | None = None,
    require_approval: bool = False,
) -> list[str]:
    """Return the list of blocking reasons for a post (empty = pass).

    Checks, in order: no address; no wrong phone number; no
    wrong-company routing; no empty post; media references resolve.
    The approval-record check runs only when ``require_approval`` is
    set (publish time): a headquarters broadcast is composed without
    its approval and waits for it — composing must not block on an
    approval that has not happened yet.
    """
    reasons: list[str] = []
    text = post.text or ""

    # 1. No address. The owner's address is never written into this
    # module; it is read from the environment only if the owner sets it.
    configured_address = owner_address()
    if configured_address and configured_address.strip().lower() in text.lower():
        reasons.append("blocked: post contains the owner's mailing address")
    elif _ADDRESS_RE.search(text):
        reasons.append("blocked: post contains a street address")

    # 2. No wrong phone number. Only (414) 502-3325 is permitted.
    for digits in _find_phones(text):
        if digits != PERMITTED_PHONE_DIGITS:
            reasons.append(
                "blocked: post contains a phone number other than (414) 502-3325"
            )
            break

    # 3. No wrong-company routing.
    if post.reach == "company":
        if post.author_company not in ALL_COMPANIES:
            reasons.append("blocked: unknown author company %r" % (post.author_company,))
    elif post.reach == "headquarters":
        if post.author_company != HEADQUARTERS_COMPANY:
            reasons.append(
                "blocked: headquarters broadcast must come from %s" % HEADQUARTERS_COMPANY
            )
        if post.approval is None and require_approval:
            reasons.append("blocked: headquarters broadcast has no approval record")
    else:
        reasons.append("blocked: unknown reach %r" % (post.reach,))

    # 4. No empty post.
    if not text.strip() and not post.attachments:
        reasons.append("blocked: empty post (no text and no attachments)")

    # 5. Media references resolve.
    known = set(known_asset_ids or set())
    for attachment in post.attachments:
        reference = attachment.reference or ""
        if _URL_RE.match(reference) or reference in known:
            continue
        reasons.append(
            "blocked: attachment reference does not resolve: %r" % (reference,)
        )

    return reasons


__all__ = ["check_post"]
