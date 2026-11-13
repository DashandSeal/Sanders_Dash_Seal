"""Tests for the real-world upgrade additions (Nov 13, 2026).

Covers only new behaviour: transport config from env, probe-driven L15
status, config-driven rate card with computed scenario total, and the
language allowlist. No network, no key, no live provider call.
"""
import os
import unittest
from unittest import mock

from core_platform.daedalus_claude_transport import DaedalusTransportConfig
from core_platform.daedalus_l15_capabilities import (
    CapabilityState,
    declared_profile,
    observed_profile,
    require_capability,
)
from core_platform.daedalus_portfolio_ip_pricing import (
    load_rate_card,
    proposed_rate_card,
)


class TestTransportConfigFromEnv(unittest.TestCase):
    def test_from_env_names_missing_fields(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                DaedalusTransportConfig.from_env()
            self.assertIn("DAEDALUS_CLAUDE_MODEL", str(ctx.exception))
            self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))

    def test_from_env_ok(self):
        env = {"DAEDALUS_CLAUDE_MODEL": "claude-test-model",
               "ANTHROPIC_API_KEY": "test-key-not-real"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = DaedalusTransportConfig.from_env()
        self.assertEqual(cfg.model, "claude-test-model")
        self.assertEqual(cfg.timeout_seconds, 45.0)


class TestObservedProfile(unittest.TestCase):
    def test_no_probe_means_unavailable(self):
        profile = observed_profile({})
        self.assertFalse(profile.fully_active)
        self.assertEqual(
            profile.capability_states["live_claude_reasoning"],
            CapabilityState.UNAVAILABLE)

    def test_passing_probe_flips_only_that_capability(self):
        profile = observed_profile(
            {"live_claude_reasoning": lambda: True})
        self.assertEqual(
            profile.capability_states["live_claude_reasoning"],
            CapabilityState.ACTIVE)
        self.assertEqual(
            profile.capability_states["cobol_bridge"],
            CapabilityState.UNAVAILABLE)
        self.assertFalse(profile.fully_active)

    def test_require_capability_refuses_unobserved(self):
        with self.assertRaises(RuntimeError):
            require_capability(declared_profile(), "live_claude_reasoning")
        profile = observed_profile({"live_claude_reasoning": lambda: True})
        require_capability(profile, "live_claude_reasoning")  # no raise


class TestRateCardConfig(unittest.TestCase):
    def test_scenario_total_is_computed_not_literal(self):
        card = load_rate_card()
        self.assertEqual(card["scenario_status"], "illustrative_not_forecast")
        result = proposed_rate_card()
        self.assertEqual(result["scenario_annual_revenue_usd"], "136000000")
        self.assertEqual(result["status"], "proposed_not_verified_market_rate")

    def test_custom_card_recomputes(self):
        card = load_rate_card()
        card["scenario_customers"] = {"enterprise_api": 1}
        result = proposed_rate_card(card)
        self.assertEqual(result["scenario_annual_revenue_usd"], "1200000")


class TestLanguageAllowlist(unittest.TestCase):
    def test_unlisted_language_rejected_before_transport(self):
        from core_platform.daedalus_runtime_integration import (
            DaedalusRuntimeIntegration,
        )
        from core_platform.daedalus_claude_transport import (
            DaedalusClaudeTransport,
        )
        transport = DaedalusClaudeTransport(
            model="test-model", api_key="test-key-not-real")
        runtime = DaedalusRuntimeIntegration(
            transport=transport, signing_key=b"x" * 32,
            persist_private_evidence=lambda record, sig: None)
        with self.assertRaises(ValueError) as ctx:
            runtime.generate_source(
                invention_id="inv-1", objective="x", language="COBOL",
                inventor_assertions=())
        self.assertIn("no 203-language registry exists", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
