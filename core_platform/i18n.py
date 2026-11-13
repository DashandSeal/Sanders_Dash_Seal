"""Minimal i18n for Sanders Dash & Seal — stdlib only, no system locales.

- Locale negotiation from an ``Accept-Language`` header (q-values,
  fallback chain, e.g. ``es-MX`` -> ``es`` -> ``en``).
- Number / currency / date formatting driven by small per-locale
  tables in this module, NOT by the OS ``locale`` module, so results
  do not depend on which system locales happen to be installed.
- RTL detection: ``ar``, ``he``, ``fa``, ``ur``, ``yi`` (and friends)
  are right-to-left. No full RTL locale is shipped yet — see the gap
  note in ``docs/TIME_LOCALE_NOTES.md``.
- Translations live in ``locales/<lang>.json`` next to this package
  (``core_platform/locales/``); missing keys fall back to English,
  and a key missing everywhere returns the key itself (never a crash).

Shipped locales: ``en``, ``es``. The Daedalus 203-language registry
is declared_not_connected and is NOT claimed here.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime

__all__ = [
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "RTL_LOCALES",
    "negotiate_locale",
    "translate",
    "format_number",
    "format_currency",
    "format_date",
    "is_rtl",
    "text_direction",
    "month_name",
]

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "es")
RTL_LOCALES = frozenset({"ar", "he", "fa", "ur", "yi", "ps", "sd", "ug"})

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
_CACHE: dict[str, dict] = {}

# Locale-independent formatting tables (do not depend on OS locales).
_FORMATS = {
    "en": {
        "decimal_sep": ".", "group_sep": ",", "grouping": 3,
        "currency_symbol": {"USD": "$", "EUR": "€", "GBP": "£", "MXN": "$",
                            "JPY": "¥", "CAD": "$", "AUD": "$", "BRL": "R$"},
        "currency_position": "before",  # $1,234.56
        "currency_space": False,
        "months": ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November",
                   "December"],
        "date_long": "{month} {day}, {year}",   # November 13, 2026
        "date_short": "{month_num:02d}/{day:02d}/{year}",  # 11/13/2026
    },
    "es": {
        "decimal_sep": ",", "group_sep": ".", "grouping": 3,
        "currency_symbol": {"USD": "$", "EUR": "€", "GBP": "£", "MXN": "$",
                            "JPY": "¥", "CAD": "$", "AUD": "$", "BRL": "R$"},
        "currency_position": "after",   # 1.234,56 €
        "currency_space": True,
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                   "julio", "agosto", "septiembre", "octubre", "noviembre",
                   "diciembre"],
        "date_long": "{day} de {month} de {year}",  # 13 de noviembre de 2026
        "date_short": "{day:02d}/{month_num:02d}/{year}",  # 13/11/2026
    },
}

# Fallback format table for a locale we know the direction of but have
# no full translation/format table for yet (e.g. ar/he RTL detection).
_GENERIC = {
    "decimal_sep": ".", "group_sep": ",", "grouping": 3,
    "currency_symbol": {}, "currency_position": "before",
    "currency_space": False,
    "months": _FORMATS["en"]["months"],
    "date_long": "{month} {day}, {year}",
    "date_short": "{month_num:02d}/{day:02d}/{year}",
}


def _base_language(tag: str) -> str:
    return tag.strip().lower().split("-")[0].split("_")[0]


def _load_locale(lang: str) -> dict:
    lang = _base_language(lang)
    if lang in _CACHE:
        return _CACHE[lang]
    data: dict = {}
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    _CACHE[lang] = data
    return data


def _format_spec(locale: str) -> dict:
    return _FORMATS.get(_base_language(locale), _GENERIC)


def negotiate_locale(header: str | None, supported=SUPPORTED_LOCALES,
                     default: str = DEFAULT_LOCALE) -> str:
    """Pick the best locale from an Accept-Language header.

    Parses q-values, prefers the highest-q match, and walks the
    fallback chain (``es-MX`` -> ``es`` -> default). Unknown, empty or
    malformed input returns ``default``.
    """
    if not header or not isinstance(header, str):
        return default
    candidates: list[tuple[float, int, str]] = []
    for order, part in enumerate(header.split(",")):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})?)\s*"
                         r"(?:;\s*q=([0-9.]+))?$", part)
        if not match:
            continue
        tag, q = match.group(1), match.group(2)
        try:
            qval = float(q) if q is not None else 1.0
        except ValueError:
            qval = 1.0
        if not 0.0 <= qval <= 1.0:
            continue
        candidates.append((qval, -order, tag))
    # Highest q first; earlier in the header wins ties.
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    supported_set = set(supported)
    for _, _, tag in candidates:
        base = _base_language(tag)
        if tag.lower() in supported_set:
            return tag.lower()
        if base in supported_set:
            return base
    return default


def translate(key: str, locale: str = DEFAULT_LOCALE, **variables) -> str:
    """Translate *key*; fall back to English, then to the key itself."""
    lang = _base_language(locale)
    text = _load_locale(lang).get(key)
    if text is None and lang != DEFAULT_LOCALE:
        text = _load_locale(DEFAULT_LOCALE).get(key)
    if text is None:
        return key
    if variables:
        try:
            return text.format(**variables)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def month_name(month: int, locale: str = DEFAULT_LOCALE) -> str:
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {month}")
    return _format_spec(locale)["months"][month - 1]


def _group_integer(digits: str, spec: dict) -> str:
    size = spec["grouping"]
    groups = []
    while digits:
        groups.append(digits[-size:])
        digits = digits[:-size]
    return spec["group_sep"].join(reversed(groups))


def format_number(value: float | int, locale: str = DEFAULT_LOCALE,
                  decimals: int = 2) -> str:
    """Locale-formatted number, e.g. en ``1,234.56`` / es ``1.234,56``."""
    spec = _format_spec(locale)
    negative = value < 0
    text = f"{abs(value):.{decimals}f}"
    whole, _, frac = text.partition(".")
    out = _group_integer(whole, spec)
    if decimals:
        out = out + spec["decimal_sep"] + frac
    return ("-" if negative else "") + out


def format_currency(amount: float | int, currency: str = "USD",
                    locale: str = DEFAULT_LOCALE) -> str:
    """Locale-formatted money, e.g. en ``$1,234.56`` / es ``1.234,56 €``.

    Unknown currency codes render as the code itself after the number.
    """
    spec = _format_spec(locale)
    number = format_number(amount, locale, decimals=0 if currency.upper() in ("JPY",) else 2)
    symbol = spec["currency_symbol"].get(currency.upper())
    if symbol is None:
        return f"{number} {currency.upper()}"
    space = " " if spec["currency_space"] else ""
    if spec["currency_position"] == "before":
        return f"{symbol}{space}{number}"
    return f"{number}{space}{symbol}"


def format_date(value: date | datetime, locale: str = DEFAULT_LOCALE,
                style: str = "long") -> str:
    """Locale-formatted date. *style* is ``"long"`` or ``"short"``."""
    spec = _format_spec(locale)
    if style not in ("long", "short"):
        raise ValueError(f"unknown date style: {style!r}")
    pattern = spec[f"date_{style}"]
    return pattern.format(month=month_name(value.month, locale),
                          month_num=value.month,
                          day=value.day, year=value.year)


def is_rtl(locale: str) -> bool:
    """True for right-to-left languages (ar, he, fa, ur, ...)."""
    return _base_language(locale) in RTL_LOCALES


def text_direction(locale: str) -> str:
    """``"rtl"`` for RTL locales, else ``"ltr"`` (for the HTML dir attr)."""
    return "rtl" if is_rtl(locale) else "ltr"
