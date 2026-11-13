"""Tests for core_platform.global_time and core_platform.i18n.

Fakes only: fixed datetimes, stdlib zoneinfo, local JSON locale files.
No network, no keys, no live calls.
"""

import os
import sys
import unittest
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_platform import global_time as gt
from core_platform import i18n

UTC = timezone.utc


def aware(y, mo, d, h=0, mi=0, s=0, tz=UTC):
    return datetime(y, mo, d, h, mi, s, tzinfo=tz)


class TestAwareOnly(unittest.TestCase):
    def test_now_utc_is_aware(self):
        self.assertIsNotNone(gt.now_utc().tzinfo)
        self.assertEqual(gt.now_utc().utcoffset().total_seconds(), 0)

    def test_require_aware_rejects_naive(self):
        with self.assertRaises(gt.NaiveDatetimeError):
            gt.require_aware(datetime(2026, 11, 13, 10, 0, 0))
        self.assertEqual(gt.require_aware(aware(2026, 11, 13, 10)), aware(2026, 11, 13, 10))

    def test_to_utc_rejects_naive(self):
        with self.assertRaises(gt.NaiveDatetimeError):
            gt.to_utc(datetime(2026, 11, 13))

    def test_serialize_roundtrip(self):
        dt = aware(2026, 11, 13, 17, 48, 36)
        self.assertEqual(gt.serialize_utc(dt), "2026-11-13T17:48:36Z")
        self.assertEqual(gt.parse_iso8601("2026-11-13T17:48:36Z"), dt)

    def test_parse_rejects_naive_string(self):
        with self.assertRaises(gt.NaiveDatetimeError):
            gt.parse_iso8601("2026-11-13T10:00:00")

    def test_parse_offset_normalizes_to_utc(self):
        # 10:00 in Denver (MST, UTC-7) on 2026-11-13 == 17:00 UTC.
        self.assertEqual(gt.parse_iso8601("2026-11-13T10:00:00-07:00"),
                         aware(2026, 11, 13, 17, 0))

    def test_unknown_timezone(self):
        with self.assertRaises(gt.UnknownTimezoneError):
            gt.resolve_timezone("Mars/Olympus")
        with self.assertRaises(gt.UnknownTimezoneError):
            gt.resolve_timezone("")


class TestDisplayAcrossTimezones(unittest.TestCase):
    # Same instant: 2026-11-13 17:00 UTC.
    INSTANT = aware(2026, 11, 13, 17, 0)

    def test_five_timezones(self):
        expected = {
            "UTC": (17, 0),
            "America/Denver": (10, 0),   # MST, UTC-7 in November
            "Europe/London": (17, 0),    # GMT, UTC+0 in November
            "Asia/Tokyo": (2, 0),        # JST, UTC+9 (next day)
            "Australia/Sydney": (4, 0),  # AEDT, UTC+11 (next day)
        }
        for tz, (hour, minute) in expected.items():
            shown = gt.display_in_timezone(self.INSTANT, tz)
            self.assertEqual((shown.hour, shown.minute), (hour, minute), tz)
            if tz in ("Asia/Tokyo", "Australia/Sydney"):
                self.assertEqual(shown.day, 14, tz)

    def test_denver_summer_is_mdt(self):
        # 2026-07-01 17:00 UTC == 11:00 MDT (UTC-6), not MST.
        shown = gt.display_in_timezone(aware(2026, 7, 1, 17, 0), "America/Denver")
        self.assertEqual((shown.hour, shown.minute), (11, 0))


class TestDST(unittest.TestCase):
    def test_us_spring_forward_gap(self):
        # 2026-03-08 02:30 never occurs in America/Denver.
        tz = gt.resolve_timezone("America/Denver")
        naive = datetime(2026, 3, 8, 2, 30)
        self.assertTrue(gt.is_nonexistent(naive, tz))
        self.assertFalse(gt.is_ambiguous(naive, tz))

    def test_us_fall_back_ambiguous(self):
        # 2026-11-01 01:30 occurs twice in America/Denver.
        tz = gt.resolve_timezone("America/Denver")
        naive = datetime(2026, 11, 1, 1, 30)
        self.assertTrue(gt.is_ambiguous(naive, tz))
        self.assertFalse(gt.is_nonexistent(naive, tz))

    def test_europe_spring_forward_gap(self):
        tz = gt.resolve_timezone("Europe/London")
        self.assertTrue(gt.is_nonexistent(datetime(2026, 3, 29, 1, 30), tz))

    def test_europe_fall_back_ambiguous(self):
        tz = gt.resolve_timezone("Europe/London")
        self.assertTrue(gt.is_ambiguous(datetime(2026, 10, 25, 1, 30), tz))

    def test_next_occurrence_normal(self):
        nxt, status = gt.next_daily_occurrence(
            9, 0, "America/Denver", after=aware(2026, 11, 13, 17, 0))
        self.assertEqual(status, "ok")
        self.assertEqual(nxt, aware(2026, 11, 14, 16, 0))  # 09:00 MST = 16:00 UTC

    def test_next_occurrence_spring_gap_shifted(self):
        # 02:30 on 2026-03-08 does not exist in Denver; must be shifted
        # forward to the first valid instant (03:00 MDT = 09:00 UTC) and
        # flagged, not invented.
        nxt, status = gt.next_daily_occurrence(
            2, 30, "America/Denver", after=aware(2026, 3, 7, 12, 0))
        self.assertEqual(status, "nonexistent_shifted")
        self.assertEqual(nxt, aware(2026, 3, 8, 9, 0))

    def test_next_occurrence_fall_back_first(self):
        # 01:30 on 2026-11-01 is ambiguous; first occurrence (MDT, UTC-6).
        nxt, status = gt.next_daily_occurrence(
            1, 30, "America/Denver", after=aware(2026, 10, 31, 12, 0))
        self.assertEqual(status, "ambiguous_first")
        self.assertEqual(nxt, aware(2026, 11, 1, 7, 30))

    def test_next_occurrence_rejects_naive_after(self):
        with self.assertRaises(gt.NaiveDatetimeError):
            gt.next_daily_occurrence(9, 0, "UTC",
                                     after=datetime(2026, 11, 13, 10, 0))


class TestNegotiation(unittest.TestCase):
    def test_q_values(self):
        self.assertEqual(i18n.negotiate_locale("es;q=0.9, en;q=0.5"), "es")
        self.assertEqual(i18n.negotiate_locale("en;q=0.5, es;q=0.9"), "es")

    def test_fallback_chain(self):
        self.assertEqual(i18n.negotiate_locale("es-MX, es;q=0.8"), "es")
        self.assertEqual(i18n.negotiate_locale("fr-FR, de;q=0.8"), "en")
        self.assertEqual(i18n.negotiate_locale("ES-mx"), "es")

    def test_empty_and_malformed(self):
        self.assertEqual(i18n.negotiate_locale(None), "en")
        self.assertEqual(i18n.negotiate_locale(""), "en")
        self.assertEqual(i18n.negotiate_locale(";;;, ,"), "en")

    def test_wildcard_falls_back(self):
        self.assertEqual(i18n.negotiate_locale("*;q=0.1"), "en")


class TestTranslationAndFormatting(unittest.TestCase):
    def test_translate_en_es(self):
        self.assertEqual(i18n.translate("common.submit", "en"), "Submit")
        self.assertEqual(i18n.translate("common.submit", "es"), "Enviar")
        self.assertEqual(i18n.translate("greeting", "es", name="Rosa"), "Hola, Rosa")

    def test_translate_fallback(self):
        # Unknown locale falls back to English; unknown key returns the key.
        self.assertEqual(i18n.translate("common.submit", "fr"), "Submit")
        self.assertEqual(i18n.translate("no.such.key", "es"), "no.such.key")

    def test_number_formatting(self):
        self.assertEqual(i18n.format_number(1234.56, "en"), "1,234.56")
        self.assertEqual(i18n.format_number(1234.56, "es"), "1.234,56")
        self.assertEqual(i18n.format_number(-9876543.2, "es", decimals=1), "-9.876.543,2")

    def test_currency_formatting(self):
        self.assertEqual(i18n.format_currency(1234.56, "USD", "en"), "$1,234.56")
        self.assertEqual(i18n.format_currency(1234.56, "EUR", "es"), "1.234,56 €")
        self.assertEqual(i18n.format_currency(500, "JPY", "en"), "¥500")

    def test_date_formatting(self):
        day = date(2026, 11, 13)
        self.assertEqual(i18n.format_date(day, "en"), "November 13, 2026")
        self.assertEqual(i18n.format_date(day, "es"), "13 de noviembre de 2026")
        self.assertEqual(i18n.format_date(day, "en", "short"), "11/13/2026")
        self.assertEqual(i18n.format_date(day, "es", "short"), "13/11/2026")

    def test_rtl_detection(self):
        for lang in ("ar", "he", "fa", "ur"):
            self.assertTrue(i18n.is_rtl(lang), lang)
            self.assertEqual(i18n.text_direction(lang), "rtl")
        for lang in ("en", "es"):
            self.assertFalse(i18n.is_rtl(lang), lang)
            self.assertEqual(i18n.text_direction(lang), "ltr")


if __name__ == "__main__":
    unittest.main()
