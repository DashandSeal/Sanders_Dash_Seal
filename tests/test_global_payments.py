"""Tests for core_platform.global_payments.

Local only, stdlib unittest, fakes only. No network, no Stripe
SDK, no keys, no live calls. Every Stripe interaction is a plain
dict / parameter dict built by the module under test.

Run from the worktree root:
    python3 -m unittest tests.test_global_payments -v
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_platform.global_payments import (  # noqa: E402
    CurrencyError,
    LivePaymentDenied,
    TaxNotImplementedError,
    annotate_test_mode_event,
    build_stripe_checkout_params,
    calculate_tax,
    describe_scenario_total,
    format_amount,
    from_minor_units,
    is_zero_decimal_currency,
    live_gate,
    minor_unit_exponent,
    normalize_currency,
    quote_total,
    resolve_currency,
    tax_status,
    to_minor_units,
    validate_webhook_event,
)


def _checkout_event(amount_total=1099, currency="eur", livemode=False):
    return {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "livemode": livemode,
        "data": {
            "object": {
                "id": "cs_test_123",
                "amount_total": amount_total,
                "currency": currency,
                "payment_status": "paid",
            }
        },
    }


class TestNormalizeCurrency(unittest.TestCase):
    def test_lowercase_and_whitespace_normalised(self):
        self.assertEqual(normalize_currency("usd"), "USD")
        self.assertEqual(normalize_currency("  eur "), "EUR")

    def test_jpy_and_gbp_supported(self):
        self.assertEqual(normalize_currency("JPY"), "JPY")
        self.assertEqual(normalize_currency("gbp"), "GBP")

    def test_unknown_code_rejected(self):
        with self.assertRaises(CurrencyError):
            normalize_currency("XYZ")

    def test_malformed_codes_rejected(self):
        for bad in ("US", "USDD", "U5D", "", None, 123, True, "USD\nX"):
            with self.assertRaises(CurrencyError, msg=repr(bad)):
                normalize_currency(bad)


class TestMinorUnits(unittest.TestCase):
    def test_usd_two_decimal(self):
        self.assertEqual(to_minor_units("10.99", "USD"), 1099)
        self.assertEqual(to_minor_units(Decimal("0.50"), "EUR"), 50)
        self.assertEqual(to_minor_units(10, "USD"), 1000)

    def test_gbp_two_decimal(self):
        self.assertEqual(to_minor_units("5.00", "GBP"), 500)

    def test_jpy_zero_decimal(self):
        self.assertEqual(to_minor_units("500", "JPY"), 500)
        self.assertEqual(to_minor_units(500, "JPY"), 500)
        self.assertTrue(is_zero_decimal_currency("JPY"))
        self.assertEqual(minor_unit_exponent("JPY"), 0)
        self.assertEqual(minor_unit_exponent("KRW"), 0)

    def test_jpy_fractional_rejected_not_rounded(self):
        with self.assertRaises(CurrencyError):
            to_minor_units("500.5", "JPY")
        with self.assertRaises(CurrencyError):
            to_minor_units(Decimal("100.1"), "KRW")

    def test_usd_third_decimal_rejected_not_rounded(self):
        with self.assertRaises(CurrencyError):
            to_minor_units("10.999", "USD")

    def test_three_decimal_currency(self):
        self.assertEqual(minor_unit_exponent("BHD"), 3)
        self.assertEqual(to_minor_units("1.234", "BHD"), 1234)
        with self.assertRaises(CurrencyError):
            to_minor_units("1.2345", "BHD")

    def test_float_money_rejected(self):
        for bad in (10.99, 500.0):
            with self.assertRaises(CurrencyError, msg=repr(bad)):
                to_minor_units(bad, "USD")

    def test_negative_rejected(self):
        with self.assertRaises(CurrencyError):
            to_minor_units("-1.00", "USD")
        with self.assertRaises(CurrencyError):
            to_minor_units(-5, "EUR")

    def test_round_trip(self):
        self.assertEqual(from_minor_units(1099, "USD"), Decimal("10.99"))
        self.assertEqual(from_minor_units(500, "JPY"), Decimal("500"))
        self.assertEqual(from_minor_units(1234, "BHD"), Decimal("1.234"))
        with self.assertRaises(CurrencyError):
            from_minor_units(10.5, "USD")


class TestResolveCurrency(unittest.TestCase):
    def test_explicit_choice_wins_over_locale(self):
        code, source = resolve_currency(explicit="EUR", locale="ja-JP")
        self.assertEqual((code, source), ("EUR", "explicit_choice"))

    def test_locale_derived_currency(self):
        self.assertEqual(resolve_currency(locale="de-DE"), ("EUR", "locale"))
        self.assertEqual(resolve_currency(locale="fr-FR"), ("EUR", "locale"))
        self.assertEqual(resolve_currency(locale="ja-JP"), ("JPY", "locale"))
        self.assertEqual(resolve_currency(locale="en-GB"), ("GBP", "locale"))
        self.assertEqual(resolve_currency(locale="en-US"), ("USD", "locale"))

    def test_accept_language_header(self):
        code, source = resolve_currency(accept_language="de-DE,de;q=0.9,en;q=0.8")
        self.assertEqual((code, source), ("EUR", "accept_language"))

    def test_explicit_fallback_usd_only_when_passed(self):
        code, source = resolve_currency(fallback_currency="USD")
        self.assertEqual((code, source), ("USD", "explicit_fallback"))

    def test_no_silent_default(self):
        with self.assertRaises(CurrencyError):
            resolve_currency()
        with self.assertRaises(CurrencyError):
            resolve_currency(locale="xx-YY")
        with self.assertRaises(CurrencyError):
            resolve_currency(locale="es")  # language alone never guesses

    def test_invalid_explicit_rejected(self):
        with self.assertRaises(CurrencyError):
            resolve_currency(explicit="XXX")


class TestFormatAmount(unittest.TestCase):
    def test_usd_en_us(self):
        self.assertEqual(format_amount(1099, "USD", "en-US"), "$10.99")
        self.assertEqual(format_amount(123456, "USD", "en-US"), "$1,234.56")

    def test_eur_de_de(self):
        self.assertEqual(format_amount(1099, "EUR", "de-DE"), "10,99 €")
        self.assertEqual(format_amount(123456, "EUR", "de-DE"), "1.234,56 €")

    def test_gbp_en_gb(self):
        self.assertEqual(format_amount(1099, "GBP", "en-GB"), "£10.99")

    def test_jpy_no_decimals(self):
        self.assertEqual(format_amount(500, "JPY", "ja-JP"), "¥500")
        self.assertEqual(format_amount(1234567, "JPY", "ja-JP"), "¥1,234,567")

    def test_eur_fr_fr(self):
        self.assertEqual(format_amount(1099, "EUR", "fr-FR"), "10,99 €")

    def test_unknown_locale_rejected(self):
        with self.assertRaises(CurrencyError):
            format_amount(1099, "USD", "xx-YY")

    def test_unknown_currency_rejected(self):
        with self.assertRaises(CurrencyError):
            format_amount(1099, "XXX", "en-US")


class TestTaxNotImplemented(unittest.TestCase):
    def test_calculate_tax_always_raises(self):
        with self.assertRaises(TaxNotImplementedError) as ctx:
            calculate_tax(1099, "USD", jurisdiction="DE")
        self.assertIn("TAX_NOT_IMPLEMENTED", str(ctx.exception))

    def test_tax_status_declares_gap(self):
        status = tax_status()
        self.assertEqual(status["status"], "TAX_NOT_IMPLEMENTED")
        self.assertIsNone(status["engine"])
        self.assertIsNone(status["vat_rates"])

    def test_quote_total_without_tax_has_no_total(self):
        quote = quote_total(1099, "USD")
        self.assertEqual(quote["subtotal_minor"], 1099)
        self.assertIsNone(quote["tax_minor"])
        self.assertIsNone(quote["total_minor"])
        self.assertEqual(quote["tax_status"], "TAX_NOT_IMPLEMENTED")

    def test_quote_total_tax_requested_raises(self):
        with self.assertRaises(TaxNotImplementedError):
            quote_total(1099, "EUR", tax_requested=True)
        with self.assertRaises(TaxNotImplementedError):
            quote_total(1099, "EUR", tax_amount_minor=200)


class TestLiveGateAndCheckoutParams(unittest.TestCase):
    def test_test_mode_is_default(self):
        self.assertEqual(live_gate(livemode=False, live_verified=False), "TEST_MODE")

    def test_live_requires_both_flags(self):
        with self.assertRaises(LivePaymentDenied):
            live_gate(livemode=True, live_verified=False)
        self.assertEqual(live_gate(livemode=True, live_verified=True), "LIVE")

    def test_checkout_params_usd(self):
        params = build_stripe_checkout_params(
            "case-1", 1099, "USD", "Notarial service",
            "https://example.com/success", "https://example.com/cancel",
        )
        self.assertEqual(params["line_items"][0]["price_data"]["currency"], "usd")
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 1099)
        self.assertEqual(params["mode"], "payment")
        self.assertFalse(params["livemode"])

    def test_checkout_params_eur_gbp_jpy(self):
        for currency, amount in (("EUR", 2500), ("GBP", 3000), ("JPY", 500)):
            params = build_stripe_checkout_params(
                "case-1", amount, currency, "Service",
                "https://example.com/success", "https://example.com/cancel",
            )
            self.assertEqual(params["line_items"][0]["price_data"]["currency"],
                             currency.lower())

    def test_checkout_jpy_small_amount_not_blocked_by_usd_floor(self):
        # JPY 50 is a real small amount; the old 100-minor-unit floor
        # in stripe_payments would have rejected JPY amounts < 100
        # for the wrong reason (it is a USD-shaped rule, not a JPY one).
        params = build_stripe_checkout_params(
            "case-1", 50, "JPY", "Service",
            "https://example.com/success", "https://example.com/cancel",
        )
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 50)

    def test_checkout_live_without_verification_refused(self):
        with self.assertRaises(LivePaymentDenied):
            build_stripe_checkout_params(
                "case-1", 1099, "USD", "Service",
                "https://example.com/success", "https://example.com/cancel",
                livemode=True, live_verified=False,
            )

    def test_checkout_invalid_currency_amount_url_rejected(self):
        base = dict(case_id="case-1", amount_minor=1099, currency="USD",
                    service_label="Service",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel")
        with self.assertRaises(CurrencyError):
            build_stripe_checkout_params(**{**base, "currency": "XXX"})
        with self.assertRaises(CurrencyError):
            build_stripe_checkout_params(**{**base, "amount_minor": 0})
        with self.assertRaises(CurrencyError):
            build_stripe_checkout_params(**{**base, "amount_minor": 10.99})
        with self.assertRaises(CurrencyError):
            build_stripe_checkout_params(**{**base, "success_url": "http://example.com/success"})


class TestWebhookEventValidation(unittest.TestCase):
    def test_valid_test_mode_event(self):
        checked = validate_webhook_event(_checkout_event(), expected_livemode=False)
        self.assertEqual(checked["amount_minor"], 1099)
        self.assertEqual(checked["currency"], "EUR")
        self.assertFalse(checked["livemode"])

    def test_expected_amount_and_currency_match(self):
        checked = validate_webhook_event(
            _checkout_event(), expected_amount_minor=1099,
            expected_currency="EUR", expected_livemode=False)
        self.assertEqual(checked["currency"], "EUR")

    def test_currency_mismatch_rejected(self):
        # The existing PaymentLedger.record_event checks amount only;
        # a currency mismatch must NOT settle silently.
        with self.assertRaises(CurrencyError):
            validate_webhook_event(
                _checkout_event(currency="usd"), expected_amount_minor=1099,
                expected_currency="EUR", expected_livemode=False)

    def test_amount_mismatch_rejected(self):
        with self.assertRaises(CurrencyError):
            validate_webhook_event(
                _checkout_event(amount_total=2000), expected_amount_minor=1099,
                expected_currency="EUR", expected_livemode=False)

    def test_live_event_refused_on_test_path(self):
        with self.assertRaises(LivePaymentDenied):
            validate_webhook_event(_checkout_event(livemode=True),
                                   expected_livemode=False)
        with self.assertRaises(LivePaymentDenied):
            annotate_test_mode_event(_checkout_event(livemode=True))

    def test_unknown_event_currency_rejected(self):
        with self.assertRaises(CurrencyError):
            validate_webhook_event(_checkout_event(currency="xxx"))


class TestScenarioLabelling(unittest.TestCase):
    def test_136m_labelled_illustrative_not_price(self):
        labelled = describe_scenario_total(13_600_000_000, "USD")
        self.assertEqual(labelled["status"], "illustrative_not_forecast")
        self.assertFalse(labelled["is_real_price"])
        self.assertEqual(labelled["amount_minor"], 13_600_000_000)


if __name__ == "__main__":
    unittest.main()
