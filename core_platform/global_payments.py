"""Multi-currency payments for Sanders Dash & Seal (global, real-world).

Stdlib only. No network, no live calls, no keys, no Stripe SDK import.

What this module does
---------------------
* Currency is always an explicit, validated ISO 4217 code from an
  allowlist of Stripe-supported currencies.  There is no silent
  default: USD is used only when the caller passes it explicitly as
  ``fallback_currency="USD"`` (see :func:`resolve_currency`).
* Money is always integer minor units (cents, yen, fils, ...).
  Float money is rejected outright; amounts are ``int`` / ``str`` /
  ``Decimal`` only.  Zero-decimal currencies (JPY, KRW, ...) and
  three-decimal currencies (BHD, KWD, ...) use their ISO 4217
  minor-unit exponent, so JPY 500 is 500 minor units, not 50000.
* Amounts are formatted per locale from an explicit locale table
  (no ``babel``, no system-locale dependence).
* Tax / VAT is NOT computed.  There is no tax engine and no VAT
  rates in this codebase.  Anything that asks for tax fails honestly
  with :class:`TaxNotImplementedError` / ``TAX_NOT_IMPLEMENTED``.
  Rates must never be invented here.

What this module does NOT do
----------------------------
* It does not call Stripe, charge a card, or verify a webhook
  signature.  Signature verification stays in
  ``core_platform.stripe_payments.verify_stripe_webhook`` and the
  WSGI webhook apps.  :func:`build_stripe_checkout_params` only
  builds the parameter dict a caller would hand to a Stripe client
  in test mode; :func:`validate_webhook_event` only validates the
  currency/amount/livemode fields of an already-verified event dict.
* It does not change live behaviour.  Live Stripe is gated:
  ``livemode=True`` requires ``live_verified=True`` as well
  (the ``STRIPE_LIVEMODE=true`` AND ``STRIPE_LIVE_VERIFIED=true``
  pair).  No live Stripe keys exist in this repo; nothing here
  creates or reads one.
* It does not fix the existing USD-only paths in place.  The audit
  (``GLOBAL_PAYMENTS_AUDIT_20261113.md`` at the worktree root)
  lists them; ``core_platform/appointment_payments.py`` still
  hardcodes ``'usd'`` and ``core_platform/stripe_payments.py``
  still does not check event currency against the stored currency.
  This module is the replacement primitive those paths should
  adopt, subject to owner/verifier approval -- it is not wired
  into them by this change.

Wiring point (for the owner/verifier, not applied here)
-------------------------------------------------------
In the test-mode webhook path (``core_platform/stream_api.py``,
``import_make_app`` with ``expected_livemode=False``), after the
signature check and before ledger settlement, call::

    from core_platform.global_payments import validate_webhook_event
    checked = validate_webhook_event(event, expected_livemode=False)

and, where a checkout was registered, also pass the expected
``expected_amount_minor`` / ``expected_currency`` so a currency
mismatch cannot settle silently (the current
``stripe_payments.PaymentLedger.record_event`` checks amount only).
Do not wire this into any live-mode path until live is verified.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

__all__ = [
    "SUPPORTED_CURRENCIES",
    "ZERO_DECIMAL_CURRENCIES",
    "THREE_DECIMAL_CURRENCIES",
    "TAX_STATUS",
    "GlobalPaymentError",
    "CurrencyError",
    "TaxNotImplementedError",
    "LivePaymentDenied",
    "normalize_currency",
    "minor_unit_exponent",
    "is_zero_decimal_currency",
    "to_minor_units",
    "from_minor_units",
    "format_amount",
    "resolve_currency",
    "calculate_tax",
    "tax_status",
    "quote_total",
    "build_stripe_checkout_params",
    "validate_webhook_event",
    "annotate_test_mode_event",
    "describe_scenario_total",
    "live_gate",
]

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GlobalPaymentError(ValueError):
    """Base error for this module.  A ValueError so callers can catch broadly."""


class CurrencyError(GlobalPaymentError):
    """Unknown, malformed, or unsupported currency / locale / amount."""


class TaxNotImplementedError(GlobalPaymentError, NotImplementedError):
    """Tax was requested but no tax engine exists.  See TAX_STATUS."""


class LivePaymentDenied(GlobalPaymentError):
    """A live-mode payment was requested without the live verification gate."""


# ---------------------------------------------------------------------------
# Currency allowlist
# ---------------------------------------------------------------------------
# Conservative allowlist of Stripe-supported ISO 4217 codes, as of
# 2026-11-13 (Stripe's supported-currencies list).  Deliberately
# conservative: a currency missing here is rejected honestly instead
# of being accepted and mis-priced.  Re-verify against Stripe's
# current list before any live use; do not silently extend it.
# HRK is excluded (Croatia adopted the euro in 2023).
SUPPORTED_CURRENCIES = frozenset(
    {
        "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG",
        "AZN", "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND",
        "BOB", "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF",
        "CHF", "CLP", "CNY", "COP", "CRC", "CVE", "CZK", "DJF", "DKK",
        "DOP", "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "GBP",
        "GEL", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL",
        "HTG", "HUF", "IDR", "ILS", "IMP", "INR", "IQD", "IRR", "ISK",
        "JEP", "JMD", "JOD", "JPY", "KES", "KGS", "KHR", "KMF", "KRW",
        "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD",
        "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR",
        "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
        "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN",
        "PYG", "QAR", "RON", "RSD", "RWF", "SAR", "SBD", "SCR", "SDG",
        "SEK", "SGD", "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN",
        "SYP", "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD",
        "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VES", "VND",
        "VUV", "WST", "XAF", "XCD", "XOF", "XPF", "YER", "ZAR", "ZMW",
        "ZWL",
    }
)

# Stripe zero-decimal currencies: amounts are whole units, no cents.
ZERO_DECIMAL_CURRENCIES = frozenset(
    {
        "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG",
        "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
    }
)

# ISO 4217 three-decimal currencies (1 unit = 1000 minor units).
THREE_DECIMAL_CURRENCIES = frozenset(
    {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
)

TAX_STATUS = "TAX_NOT_IMPLEMENTED"


def normalize_currency(code) -> str:
    """Validate and normalise a currency code to upper-case ISO 4217.

    Raises :class:`CurrencyError` for anything not on the allowlist
    -- including well-formed but unsupported codes, so a typo can
    never silently become a different currency.
    """
    if not isinstance(code, str):
        raise CurrencyError("Currency code must be a string, got %r" % type(code).__name__)
    cleaned = code.strip().upper()
    if len(cleaned) != 3 or not cleaned.isalpha():
        raise CurrencyError("Currency code must be three letters, got %r" % code)
    if cleaned not in SUPPORTED_CURRENCIES:
        raise CurrencyError("Unsupported currency %r: not on the Stripe-supported allowlist" % cleaned)
    return cleaned


def minor_unit_exponent(currency: str) -> int:
    """Minor-unit exponent for a currency: 0, 2, or 3."""
    code = normalize_currency(currency)
    if code in ZERO_DECIMAL_CURRENCIES:
        return 0
    if code in THREE_DECIMAL_CURRENCIES:
        return 3
    return 2


def is_zero_decimal_currency(currency: str) -> bool:
    return normalize_currency(currency) in ZERO_DECIMAL_CURRENCIES


def _to_decimal(amount, *, what: str = "amount") -> Decimal:
    """Exact Decimal from int/str/Decimal only.  Floats are rejected:
    float money is never exact, so it is never accepted here."""
    if isinstance(amount, bool):
        raise CurrencyError("%s must not be a bool" % what)
    if isinstance(amount, float):
        raise CurrencyError(
            "%s must not be a float: float money is inexact; pass int, str or Decimal" % what
        )
    if isinstance(amount, Decimal):
        value = amount
    elif isinstance(amount, int):
        value = Decimal(amount)
    elif isinstance(amount, str):
        try:
            value = Decimal(amount.strip())
        except (InvalidOperation, ValueError, AttributeError):
            raise CurrencyError("%s is not a valid decimal amount: %r" % (what, amount)) from None
    else:
        raise CurrencyError(
            "%s must be int, str or Decimal, got %r" % (what, type(amount).__name__)
        )
    if not value.is_finite():
        raise CurrencyError("%s must be finite" % what)
    return value


def to_minor_units(amount, currency: str) -> int:
    """Convert a major-unit amount to integer minor units, exactly.

    ``to_minor_units("10.99", "USD") == 1099``;
    ``to_minor_units("500", "JPY") == 500`` (zero-decimal);
    ``to_minor_units("1.234", "BHD") == 1234`` (three-decimal).
    An amount with more decimal places than the currency allows
    (e.g. ``"10.999"`` USD, ``"500.5"`` JPY) raises
    :class:`CurrencyError` instead of being rounded -- rounding
    money silently is a pricing error.  Negative amounts raise.
    """
    code = normalize_currency(currency)
    value = _to_decimal(amount)
    if value < 0:
        raise CurrencyError("Amount must not be negative: %r" % (amount,))
    exponent = minor_unit_exponent(code)
    quantum = Decimal(1).scaleb(-exponent)
    if value != value.quantize(quantum):
        raise CurrencyError(
            "Amount %r has more decimal places than %s allows (exponent %d)"
            % (amount, code, exponent)
        )
    return int(value.scaleb(exponent))


def from_minor_units(minor_units: int, currency: str) -> Decimal:
    """Convert integer minor units back to a major-unit Decimal."""
    code = normalize_currency(currency)
    if isinstance(minor_units, bool) or not isinstance(minor_units, int):
        raise CurrencyError("Minor units must be an int, got %r" % type(minor_units).__name__)
    if minor_units < 0:
        raise CurrencyError("Minor units must not be negative")
    return Decimal(minor_units).scaleb(-minor_unit_exponent(code))


# ---------------------------------------------------------------------------
# Locale handling: currency resolution + formatting (explicit tables only)
# ---------------------------------------------------------------------------

# Exact locale (language-REGION) -> currency.  Language alone is NOT
# mapped: "es" could be EUR (Spain) or MXN (Mexico), so only a full
# locale resolves.  Unknown locales resolve to nothing (see below).
_LOCALE_CURRENCY = {
    "ar-AE": "AED", "ar-SA": "SAR", "cs-CZ": "CZK", "da-DK": "DKK",
    "de-AT": "EUR", "de-DE": "EUR", "el-GR": "EUR", "en-AU": "AUD",
    "en-CA": "CAD", "en-GB": "GBP", "en-IE": "EUR", "en-IN": "INR",
    "en-NZ": "NZD", "en-US": "USD", "en-ZA": "ZAR", "es-ES": "EUR",
    "es-MX": "MXN", "fi-FI": "EUR", "fr-BE": "EUR", "fr-FR": "EUR",
    "he-IL": "ILS", "hu-HU": "HUF", "id-ID": "IDR", "it-IT": "EUR",
    "ja-JP": "JPY", "ko-KR": "KRW", "ms-MY": "MYR", "nb-NO": "NOK",
    "nl-NL": "EUR", "pl-PL": "PLN", "pt-BR": "BRL", "pt-PT": "EUR",
    "sv-SE": "SEK", "th-TH": "THB", "tr-TR": "TRY", "uk-UA": "UAH",
    "zh-CN": "CNY", "zh-TW": "TWD",
}

# locale -> (decimal separator, grouping separator, symbol before amount,
#            space between symbol and amount, space character)
# fr-FR uses a non-breaking space before the symbol (French convention).
_LOCALE_FORMAT = {
    "de-DE": (",", ".", False, True, " "),
    "en-GB": (".", ",", True, False, " "),
    "en-US": (".", ",", True, False, " "),
    "es-ES": (",", ".", False, True, " "),
    "fr-FR": (",", "\u00a0", False, True, "\u00a0"),
    "it-IT": (",", ".", False, True, " "),
    "ja-JP": (".", ",", True, False, " "),
    "ko-KR": (".", ",", True, False, " "),
    "nl-NL": (",", ".", True, True, " "),
    "pt-BR": (",", ".", True, False, " "),
    "zh-CN": (".", ",", True, False, " "),
}

_CURRENCY_SYMBOLS = {
    "AED": "د.إ", "AUD": "A$", "BRL": "R$", "CAD": "CA$", "CHF": "CHF",
    "CNY": "¥", "CZK": "Kč", "DKK": "kr", "EUR": "€", "GBP": "£",
    "HKD": "HK$", "HUF": "Ft", "IDR": "Rp", "ILS": "₪", "INR": "₹",
    "JPY": "¥", "KRW": "₩", "MXN": "MX$", "MYR": "RM", "NOK": "kr",
    "NZD": "NZ$", "PHP": "₱", "PLN": "zł", "SAR": "ر.س", "SEK": "kr",
    "SGD": "S$", "THB": "฿", "TRY": "₺", "TWD": "NT$", "USD": "$",
    "ZAR": "R",
}


def _normalise_locale(locale) -> str:
    if not isinstance(locale, str):
        raise CurrencyError("Locale must be a string, got %r" % type(locale).__name__)
    cleaned = locale.strip().replace("_", "-")
    parts = cleaned.split("-")
    if len(parts) != 2 or not parts[0].isalpha() or not parts[1].isalpha():
        raise CurrencyError("Locale must look like 'de-DE', got %r" % locale)
    return parts[0].lower() + "-" + parts[1].upper()


def resolve_currency(explicit=None, locale=None, *, fallback_currency=None,
                     accept_language=None):
    """Resolve a currency, in priority order, without silent defaults.

    1. ``explicit`` -- the user's explicit choice; validated.
    2. ``locale`` (or the first entry of an ``Accept-Language``
       header value) -- only an exact ``language-REGION`` match
       resolves; a language alone never guesses a currency.
    3. ``fallback_currency`` -- used ONLY when the caller passes it
       explicitly, e.g. ``fallback_currency="USD"``.  This is the
       one place USD may appear as a default, and it is explicit
       in the call, never silent.

    Returns ``(currency_code, source)`` where source is one of
    ``"explicit_choice"``, ``"locale"``, ``"accept_language"`` or
    ``"explicit_fallback"``.  Raises :class:`CurrencyError` when
    nothing resolves -- the caller must then ask the user, not
    assume USD.
    """
    if explicit is not None:
        return normalize_currency(explicit), "explicit_choice"
    if accept_language is not None:
        if not isinstance(accept_language, str):
            raise CurrencyError("Accept-Language must be a string")
        first = accept_language.split(",")[0].strip().split(";")[0].strip()
        if first:
            code = _LOCALE_CURRENCY.get(_normalise_locale(first))
            if code is not None:
                return code, "accept_language"
    if locale is not None:
        code = _LOCALE_CURRENCY.get(_normalise_locale(locale))
        if code is not None:
            return code, "locale"
    if fallback_currency is not None:
        return normalize_currency(fallback_currency), "explicit_fallback"
    raise CurrencyError(
        "No currency could be resolved: no explicit choice, no known "
        "locale, and no explicit fallback was supplied (USD is never "
        "assumed silently)"
    )


def _group_integer(digits: str, sep: str) -> str:
    if not sep:
        return digits
    parts = []
    while digits:
        parts.append(digits[-3:])
        digits = digits[:-3]
    return sep.join(reversed(parts))


def format_amount(minor_units: int, currency: str, locale: str = "en-US") -> str:
    """Format integer minor units as a locale-correct money string.

    ``format_amount(1099, "USD", "en-US") == "$10.99"``;
    ``format_amount(1099, "EUR", "de-DE") == "10,99 €"``;
    ``format_amount(500, "JPY", "ja-JP") == "¥500"`` (no decimals).
    Unknown locales raise :class:`CurrencyError` instead of
    formatting in the wrong convention.  No float is involved.
    """
    code = normalize_currency(currency)
    if isinstance(minor_units, bool) or not isinstance(minor_units, int):
        raise CurrencyError("Minor units must be an int")
    if minor_units < 0:
        raise CurrencyError("Minor units must not be negative")
    loc = _normalise_locale(locale)
    if loc not in _LOCALE_FORMAT:
        raise CurrencyError("Unknown/unsupported formatting locale %r" % loc)
    dec_sep, group_sep, symbol_before, space, space_char = _LOCALE_FORMAT[loc]
    exponent = minor_unit_exponent(code)
    major = Decimal(minor_units).scaleb(-exponent)
    if exponent == 0:
        number = _group_integer(str(minor_units), group_sep)
    else:
        whole, _, frac = format(major, "f").partition(".")
        number = _group_integer(whole, group_sep) + dec_sep + frac.ljust(exponent, "0")
    symbol = _CURRENCY_SYMBOLS.get(code, code)
    join = space_char if space else ""
    if symbol_before:
        return symbol + join + number
    return number + join + symbol


# ---------------------------------------------------------------------------
# Tax / VAT: declared gap, fail honestly
# ---------------------------------------------------------------------------


def tax_status() -> dict:
    """Machine-readable statement of the tax gap.  No rates exist."""
    return {
        "status": TAX_STATUS,
        "engine": None,
        "vat_rates": None,
        "sales_tax_rates": None,
        "note": (
            "Tax/VAT is NOT computed by Sanders Dash & Seal: there is "
            "no tax engine and no VAT/sales-tax rates in this codebase. "
            "A total that needs tax cannot be quoted until the owner "
            "chooses a tax provider (e.g. Stripe Tax) and it is wired "
            "in with real credentials in test mode first."
        ),
    }


def calculate_tax(amount_minor: int, currency: str, *, jurisdiction=None,
                  **_kwargs):
    """Always raises: tax is not implemented.  Rates are never invented.

    ``jurisdiction`` is accepted only so callers can record what was
    asked for; it is included in the error message and nothing is
    computed from it.
    """
    raise TaxNotImplementedError(
        "%s: tax cannot be calculated for %s %s (jurisdiction=%r): "
        "no tax engine and no VAT/sales-tax rates exist in this "
        "codebase. Do not present a total as tax-inclusive."
        % (TAX_STATUS, amount_minor, currency, jurisdiction)
    )


def quote_total(subtotal_minor: int, currency: str, *, tax_requested: bool = False,
                tax_amount_minor=None) -> dict:
    """Return a quote that is honest about tax.

    Without tax, the total is *unknown*, not zero: ``total_minor``
    is ``None`` and ``tax_minor`` is ``None``, with status
    ``TAX_NOT_IMPLEMENTED``.  Presenting ``total == subtotal``
    would falsely imply tax is zero.  If tax is requested (or a
    tax amount is supplied), raise :class:`TaxNotImplementedError`.
    """
    code = normalize_currency(currency)
    if isinstance(subtotal_minor, bool) or not isinstance(subtotal_minor, int):
        raise CurrencyError("Subtotal must be an int in minor units")
    if subtotal_minor < 0:
        raise CurrencyError("Subtotal must not be negative")
    if tax_requested or tax_amount_minor is not None:
        calculate_tax(subtotal_minor, code)
    return {
        "subtotal_minor": subtotal_minor,
        "tax_minor": None,
        "total_minor": None,
        "currency": code,
        "tax_status": TAX_STATUS,
        "note": (
            "Total is not quotable: tax is not computed "
            "(TAX_NOT_IMPLEMENTED). Subtotal only."
        ),
    }


# ---------------------------------------------------------------------------
# Stripe test-mode wiring (parameter building + event validation only)
# ---------------------------------------------------------------------------


def live_gate(*, livemode: bool, live_verified: bool) -> str:
    """Return ``"TEST_MODE"`` or ``"LIVE"``; live needs both flags.

    Live requires ``STRIPE_LIVEMODE=true`` AND
    ``STRIPE_LIVE_VERIFIED=true``.  Anything else is test mode,
    and live without verification raises :class:`LivePaymentDenied`.
    """
    if type(livemode) is not bool or type(live_verified) is not bool:
        raise LivePaymentDenied("livemode and live_verified must both be bools")
    if livemode and not live_verified:
        raise LivePaymentDenied(
            "Live Stripe is not verified: live requires STRIPE_LIVEMODE=true "
            "AND STRIPE_LIVE_VERIFIED=true. No live Stripe keys exist; "
            "use test mode."
        )
    return "LIVE" if livemode else "TEST_MODE"


def build_stripe_checkout_params(case_id, amount_minor: int, currency: str,
                                 service_label: str, success_url: str,
                                 cancel_url: str, *, livemode: bool = False,
                                 live_verified: bool = False,
                                 metadata: dict | None = None) -> dict:
    """Build Stripe Checkout ``price_data`` params in integer minor units.

    No network call, no Stripe client, no key is read.  Test mode is
    the default; live is refused unless :func:`live_gate` passes.
    Unlike the existing ``stripe_payments.checkout_parameters`` this
    does NOT impose a currency-blind minimum of 100 minor units:
    100 means $1.00 in USD but ¥100 in JPY, so a single floor is
    wrong for zero-decimal currencies -- Stripe enforces its own
    per-currency minimum at API time, and this module does not
    invent one.  Amount must simply be a positive integer.
    """
    mode = live_gate(livemode=livemode, live_verified=live_verified)
    code = normalize_currency(currency)
    if not isinstance(case_id, str) or not case_id:
        raise CurrencyError("case_id must be a non-empty string")
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise CurrencyError("amount_minor must be an int in minor units")
    if amount_minor <= 0:
        raise CurrencyError("amount_minor must be positive")
    if not isinstance(service_label, str) or not service_label:
        raise CurrencyError("service_label must be a non-empty string")
    for name, url in (("success_url", success_url), ("cancel_url", cancel_url)):
        if not isinstance(url, str) or not url.startswith("https://"):
            raise CurrencyError("%s must be an https URL" % name)
    meta = {"case_id": case_id}
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise CurrencyError("metadata must be a dict")
        meta.update({str(k): str(v) for k, v in metadata.items()})
    return {
        "mode": "payment",
        "livemode": livemode,
        "live_gate": mode,
        "client_reference_id": case_id,
        "line_items": [
            {
                "price_data": {
                    "currency": code.lower(),
                    "product_data": {"name": service_label},
                    "unit_amount": amount_minor,
                },
                "quantity": 1,
            }
        ],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": meta,
    }


def validate_webhook_event(event: dict, *, expected_amount_minor=None,
                           expected_currency=None,
                           expected_livemode: bool = False) -> dict:
    """Validate currency/amount/livemode of an already-verified event.

    Signature verification must already have happened (Stripe
    webhook secret / ``verify_stripe_webhook``); this only checks
    the event's own fields, and -- unlike
    ``stripe_payments.PaymentLedger.record_event`` -- it checks
    currency as well as amount, so a currency mismatch can never
    settle silently.  Supports ``checkout.session.*``
    (``amount_total``) and ``payment_intent.succeeded``
    (``amount_received``).  Raises :class:`CurrencyError` /
    :class:`LivePaymentDenied` on any mismatch.
    """
    if not isinstance(event, dict):
        raise CurrencyError("Webhook event must be a dict")
    if type(expected_livemode) is not bool:
        raise CurrencyError("expected_livemode must be a bool")
    livemode = event.get("livemode")
    if livemode is not expected_livemode:
        raise LivePaymentDenied(
            "Webhook livemode %r does not match expected_livemode %r"
            % (livemode, expected_livemode)
        )
    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), dict) else {}
    if not isinstance(obj, dict):
        raise CurrencyError("Webhook event object must be a dict")
    if isinstance(event_type, str) and event_type.startswith("checkout.session."):
        amount = obj.get("amount_total")
    elif event_type == "payment_intent.succeeded":
        amount = obj.get("amount_received")
    else:
        amount = obj.get("amount_total", obj.get("amount_paid", obj.get("amount_received")))
    currency = obj.get("currency")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise CurrencyError("Webhook event amount must be a non-negative int in minor units")
    code = normalize_currency(currency)
    if expected_currency is not None:
        if code != normalize_currency(expected_currency):
            raise CurrencyError(
                "Webhook currency %s does not match expected currency %s"
                % (code, normalize_currency(expected_currency))
            )
    if expected_amount_minor is not None:
        if amount != expected_amount_minor:
            raise CurrencyError(
                "Webhook amount %d does not match expected amount %d"
                % (amount, expected_amount_minor)
            )
    return {
        "event_id": event.get("id"),
        "event_type": event_type,
        "amount_minor": amount,
        "currency": code,
        "livemode": livemode,
    }


def annotate_test_mode_event(event: dict, **kwargs) -> dict:
    """Validate an event on the test-mode webhook path only.

    Thin wrapper around :func:`validate_webhook_event` with
    ``expected_livemode=False``.  This is the intended wiring
    point for ``core_platform/stream_api.py`` in test mode; it
    refuses any live event.  See the module docstring.
    """
    return validate_webhook_event(event, expected_livemode=False, **kwargs)


def describe_scenario_total(amount_minor: int, currency: str = "USD") -> dict:
    """Label a scenario/illustrative total so it can never read as a price.

    The Daedalus $136M figure (13,600,000,000 USD cents) is a
    scenario total computed from a proposed rate card; it must
    always carry ``status == "illustrative_not_forecast"`` and
    ``is_real_price == False``.  Use this whenever a scenario
    total is surfaced.
    """
    code = normalize_currency(currency)
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise CurrencyError("Scenario amount must be an int in minor units")
    return {
        "amount_minor": amount_minor,
        "currency": code,
        "status": "illustrative_not_forecast",
        "is_real_price": False,
        "note": (
            "Illustrative scenario total only, computed from a proposed "
            "rate card. Not a price, not revenue, not a forecast."
        ),
    }
