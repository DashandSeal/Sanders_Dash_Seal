"""Tests for core_platform.platform_services (presence flags only; no secrets)."""

import json
import unittest

from core_platform.platform_services import (
    DNS_APEX_IP,
    ORACLE_INSTANCE,
    StripeLink,
    dns_records_to_apply,
    dns_status,
    gateway_status,
    google_service_links,
    oracle_status,
    platform_status,
    stripe_live_gate,
)


class TestStripeGate(unittest.TestCase):
    def test_test_mode_is_default_and_live_needs_both_flags(self):
        test = StripeLink.from_env({})
        self.assertTrue(test.test_mode)
        self.assertFalse(stripe_live_gate(test))
        half = StripeLink.from_env({"STRIPE_LIVEMODE": "true"})
        self.assertFalse(stripe_live_gate(half))
        live = StripeLink.from_env({"STRIPE_LIVEMODE": "true", "STRIPE_LIVE_VERIFIED": "true"})
        self.assertTrue(stripe_live_gate(live))
        self.assertFalse(live.test_mode)

    def test_livemode_truthiness_is_1_true_yes_everywhere(self):
        # P3 (2026-11-13): canonical truthiness shared with wsgi.py
        # (_env_truthy) and deploy/deployment.py. Previously this reader
        # accepted "true" only, so STRIPE_LIVEMODE=1 reported test mode
        # here while the webhook app ran live.
        for value in ("1", "true", "TRUE", "True", "yes", "YES", " 1 "):
            link = StripeLink.from_env({
                "STRIPE_LIVEMODE": value, "STRIPE_LIVE_VERIFIED": value})
            self.assertTrue(link.livemode_requested, value)
            self.assertTrue(link.live_verified, value)
            self.assertTrue(stripe_live_gate(link), value)
            self.assertFalse(link.test_mode, value)
        for value in ("", "0", "false", "no", "off", "2"):
            link = StripeLink.from_env({
                "STRIPE_LIVEMODE": value, "STRIPE_LIVE_VERIFIED": value})
            self.assertFalse(link.livemode_requested, value)
            self.assertFalse(link.live_verified, value)
            self.assertFalse(stripe_live_gate(link), value)
            self.assertTrue(link.test_mode, value)
        # Mixed spellings across the two flags still gate live.
        mixed = StripeLink.from_env({
            "STRIPE_LIVEMODE": "1", "STRIPE_LIVE_VERIFIED": "yes"})
        self.assertTrue(stripe_live_gate(mixed))

    def test_test_mode_configured_needs_both_secrets(self):
        self.assertFalse(StripeLink.from_env({}).configured_for_test)
        self.assertFalse(StripeLink.from_env({"STRIPE_SECRET_KEY": "sk_test_x"}).configured_for_test)
        self.assertTrue(StripeLink.from_env({
            "STRIPE_SECRET_KEY": "sk_test_x", "STRIPE_WEBHOOK_SECRET": "whsec_x",
        }).configured_for_test)

    def test_status_never_leaks_secret_values(self):
        env = {"STRIPE_SECRET_KEY": "sk_live_SENTINEL1", "STRIPE_WEBHOOK_SECRET": "whsec_SENTINEL2"}
        blob = json.dumps(StripeLink.from_env(env).status())
        self.assertNotIn("SENTINEL1", blob)
        self.assertNotIn("SENTINEL2", blob)
        # P2 adaptation: the ledger handlers are real SQLite-backed
        # methods since P1 (2026-11-13), not stubs -- the status says so.
        self.assertIn("real SQLite-backed", blob)


class TestOracleAndDns(unittest.TestCase):
    def test_oracle_facts_match_verified_instance(self):
        status = oracle_status()
        self.assertEqual(status["instance"]["public_ip"], "129.146.111.166")
        self.assertEqual(status["instance"]["region"], "us-phoenix-1")
        self.assertEqual(status["instance"]["tenancy"], "rooseveltsanders381")
        self.assertFalse(status["instance"]["code_deployed"])
        self.assertEqual(status["deploy_root"], "/opt/sanders-dash-seal")
        self.assertIn("backup-policy.md", status["backup_policy"])

    def test_missing_www_record_is_exact(self):
        records = dns_records_to_apply()
        missing = [r for r in records if r["state"].startswith("MISSING")]
        self.assertEqual(len(missing), 1)
        rec = missing[0]
        self.assertEqual(rec["host"], "www")
        self.assertEqual(rec["domain"], "sanderslegalhelpersllc.com")
        self.assertEqual(rec["type"], "A")
        self.assertEqual(rec["value"], DNS_APEX_IP)
        apexes = [r for r in records if r["host"] == "@"]
        self.assertEqual(len(apexes), 2)
        self.assertTrue(all(r["value"] == "129.146.111.166" for r in apexes))

    def test_dns_status_counts_missing(self):
        self.assertEqual(dns_status()["missing_records"], 1)


class TestGatewayAndGoogle(unittest.TestCase):
    def test_gateway_is_proposal_only_workflow_not_edited(self):
        status = gateway_status()
        self.assertFalse(status["workflow_file_edited"])
        self.assertIn("exit 128", status["failing_step"])
        self.assertEqual(status["pair_format"], "Shape A / UNSIGNED_SOURCE_MANIFEST")
        self.assertIn("Shape A", status["fix"])

    def test_google_links_invent_no_server_integration(self):
        links = google_service_links()
        self.assertEqual(links["connection"], "muse_connected_no_server_integration")
        for use in links["uses"]:
            self.assertEqual(use["server_integration"][:4], "none")
        self.assertIn("No Google OAuth", links["not_invented"])


class TestCombinedStatus(unittest.TestCase):
    def test_all_platforms_present_and_no_secret_leaks(self):
        env = {
            "STRIPE_SECRET_KEY": "sk_SENTINEL",
            "LIVEKIT_API_SECRET": "lk_SENTINEL",
            "DAILY_API_KEY": "daily_SENTINEL",
        }
        status = platform_status(env)
        for key in ("stripe", "oracle", "dns", "github_gateway", "google", "realtime"):
            self.assertIn(key, status, key)
        blob = json.dumps(status)
        self.assertNotIn("SENTINEL", blob)
        # P2 adaptation: the ledger handlers are real SQLite-backed
        # methods since P1 (2026-11-13), not stubs -- the warning says so.
        self.assertIn("real since the P1 pass", status["ledger_stub_warning"])
        self.assertTrue(any("SSH blocked" in b for b in status["deploy_blockers"]))


if __name__ == "__main__":
    unittest.main()
