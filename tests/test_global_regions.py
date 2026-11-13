"""Tests for region-aware config (core_platform.global_regions).

Local only: no API key, no network, no deployment, no live call.
Every region / timeout / DNS value is asserted from the module's own
registry and from fake env mappings. The real primary IPv4 is never
asserted here; tests use the TEST-NET-3 placeholder 203.0.113.10.

Run with:  python3 -m unittest discover -s tests -v
(pytest is NOT installed in this environment, so unittest is the runner.)
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_platform.global_regions import (
    DEFAULT_PRIMARY_REGION,
    DEFAULT_TENANCY_NAME,
    DNS_TTL_SECONDS,
    GlobalRegionsConfig,
    daedalus_authorized_regions,
    deployed_regions,
    dns_plan,
    failover_plan,
    fallback_chain,
    free_first_plan,
    get_region,
    retry_policy_for,
    secondary_candidates,
    timeout_for,
)

FAKE_IPV4 = "203.0.113.10"  # TEST-NET-3, documentation-only address.


class DefaultsTest(unittest.TestCase):
    def test_defaults_are_primary_us_phoenix_1(self):
        cfg = GlobalRegionsConfig.from_env({})
        self.assertEqual(cfg.tenancy, DEFAULT_TENANCY_NAME)
        self.assertEqual(cfg.tenancy, "rooseveltsanders381")
        self.assertEqual(cfg.primary_region, "us-phoenix-1")
        self.assertEqual(cfg.primary_region, DEFAULT_PRIMARY_REGION)
        self.assertEqual(cfg.runtime_region, "us-phoenix-1")
        self.assertIsNone(cfg.primary_ipv4)

    def test_explicit_primary_and_tenancy_env(self):
        cfg = GlobalRegionsConfig.from_env({
            "OCI_TENANCY": "example-tenancy",
            "PRIMARY_REGION": "us-phoenix-1",
            "OCI_REGION": "us-phoenix-1",
            "SDS_PUBLIC_IPV4": FAKE_IPV4,
        })
        self.assertEqual(cfg.tenancy, "example-tenancy")
        self.assertEqual(cfg.primary_ipv4, FAKE_IPV4)

    def test_blank_env_values_fall_back_to_defaults(self):
        cfg = GlobalRegionsConfig.from_env({
            "OCI_TENANCY": "   ",
            "PRIMARY_REGION": "",
            "OCI_REGION": "  ",
            "SDS_PUBLIC_IPV4": "",
        })
        self.assertEqual(cfg.tenancy, DEFAULT_TENANCY_NAME)
        self.assertEqual(cfg.primary_region, DEFAULT_PRIMARY_REGION)
        self.assertEqual(cfg.runtime_region, DEFAULT_PRIMARY_REGION)
        self.assertIsNone(cfg.primary_ipv4)

    def test_only_phoenix_is_deployed(self):
        deployed = deployed_regions()
        self.assertEqual([region.key for region in deployed], ["us-phoenix-1"])
        self.assertEqual(deployed[0].status, "DEPLOYED")
        self.assertEqual(deployed[0].role, "primary")

    def test_daedalus_authorized_regions_is_deployed_only(self):
        self.assertEqual(daedalus_authorized_regions(), frozenset({"us-phoenix-1"}))


class UnknownRegionTest(unittest.TestCase):
    def test_unknown_runtime_region_rejected(self):
        with self.assertRaises(ValueError):
            GlobalRegionsConfig.from_env({"OCI_REGION": "eu-frankfurt-1"})

    def test_unknown_primary_region_rejected(self):
        with self.assertRaises(ValueError):
            GlobalRegionsConfig.from_env({"PRIMARY_REGION": "eu-frankfurt-1"})

    def test_get_region_rejects_unknown(self):
        with self.assertRaises(ValueError):
            get_region("eu-frankfurt-1")

    def test_get_region_rejects_blank(self):
        with self.assertRaises(ValueError):
            get_region("  ")

    def test_unknown_service_rejected(self):
        with self.assertRaises(ValueError):
            timeout_for("carrier-pigeon")
        with self.assertRaises(ValueError):
            retry_policy_for("carrier-pigeon")
        with self.assertRaises(ValueError):
            fallback_chain("carrier-pigeon")


class SecondaryRegionTest(unittest.TestCase):
    def test_secondary_candidates_are_not_provisioned(self):
        candidates = secondary_candidates()
        keys = {region.key for region in candidates}
        self.assertIn("us-ashburn-1", keys)
        self.assertIn("us-chicago-1", keys)
        for region in candidates:
            self.assertEqual(region.status, "NOT_PROVISIONED")
            self.assertNotIn(region.key, daedalus_authorized_regions())

    def test_secondary_region_status_is_not_deployed(self):
        ashburn = get_region("us-ashburn-1")
        self.assertEqual(ashburn.status, "NOT_PROVISIONED")
        self.assertNotEqual(ashburn.status, "DEPLOYED")

    def test_runtime_region_cannot_be_a_candidate(self):
        with self.assertRaises(ValueError):
            GlobalRegionsConfig.from_env({"OCI_REGION": "us-ashburn-1"})
        with self.assertRaises(ValueError):
            GlobalRegionsConfig.from_env({"OCI_REGION": "us-chicago-1"})

    def test_primary_region_cannot_be_a_candidate(self):
        with self.assertRaises(ValueError):
            GlobalRegionsConfig.from_env({"PRIMARY_REGION": "us-ashburn-1"})


class TimeoutRetryTest(unittest.TestCase):
    def test_daedalus_timeout_matches_known_default_plus_allowance(self):
        # Base 45 s + primary planning latency allowance 40 ms = 45.04.
        self.assertEqual(timeout_for("daedalus", "us-phoenix-1"), 45.04)
        self.assertEqual(timeout_for("daedalus"), 45.0)

    def test_realtime_service_is_fastest(self):
        self.assertLess(timeout_for("livekit", "us-phoenix-1"),
                        timeout_for("daedalus", "us-phoenix-1"))
        self.assertLess(timeout_for("livekit", "us-phoenix-1"),
                        timeout_for("openai", "us-phoenix-1"))
        self.assertEqual(timeout_for("livekit", "us-phoenix-1"), 15.04)

    def test_all_services_have_timeouts(self):
        expected = {"daedalus", "openai", "livekit", "deepgram", "elevenlabs", "google"}
        for service in expected:
            value = timeout_for(service, "us-phoenix-1")
            self.assertGreater(value, 0)
        self.assertEqual(timeout_for("openai", "us-phoenix-1"), 30.04)
        self.assertEqual(timeout_for("deepgram", "us-phoenix-1"), 30.04)
        self.assertEqual(timeout_for("elevenlabs", "us-phoenix-1"), 30.04)
        self.assertEqual(timeout_for("google", "us-phoenix-1"), 30.04)

    def test_secondary_region_gets_larger_allowance(self):
        # us-ashburn-1 planning latency 70 ms > us-phoenix-1 40 ms.
        self.assertGreater(timeout_for("daedalus", "us-ashburn-1"),
                           timeout_for("daedalus", "us-phoenix-1"))
        self.assertEqual(timeout_for("daedalus", "us-ashburn-1"), 45.07)

    def test_timeout_env_override(self):
        cfg = GlobalRegionsConfig.from_env({"SDS_TIMEOUT_LIVEKIT": "10"})
        self.assertEqual(cfg.timeout_for("livekit"), 10.04)
        self.assertEqual(timeout_for("livekit", "us-phoenix-1",
                                     env={"SDS_TIMEOUT_LIVEKIT": "10"}), 10.04)

    def test_timeout_env_override_rejects_bad_values(self):
        for bad in ("0", "-5", "not-a-number", "inf"):
            with self.assertRaises(ValueError, msg=bad):
                GlobalRegionsConfig.from_env({"SDS_TIMEOUT_LIVEKIT": bad})

    def test_retry_policy_realtime_retries_more_and_faster(self):
        livekit = retry_policy_for("livekit")
        daedalus = retry_policy_for("daedalus")
        self.assertEqual(livekit.max_attempts, 5)
        self.assertEqual(daedalus.max_attempts, 3)
        self.assertEqual(livekit.backoff_base_seconds, 0.5)
        self.assertEqual(daedalus.backoff_base_seconds, 1.0)
        self.assertEqual(livekit.backoff_factor, 2.0)
        self.assertEqual(livekit.max_backoff_seconds, 30.0)

    def test_retry_delay_grows_and_caps(self):
        policy = retry_policy_for("daedalus")
        self.assertEqual(policy.delay_before_attempt(1), 0.0)
        self.assertEqual(policy.delay_before_attempt(2), 1.0)
        self.assertEqual(policy.delay_before_attempt(3), 2.0)
        self.assertEqual(policy.delay_before_attempt(10), 30.0)
        with self.assertRaises(ValueError):
            policy.delay_before_attempt(0)


class FreeFirstTest(unittest.TestCase):
    def test_stt_tts_video_start_free(self):
        for service in ("stt", "tts", "video"):
            chain = fallback_chain(service)
            self.assertEqual(chain[0].tier, "free", service)
            self.assertIn(chain[0].name,
                          ("faster-whisper-local", "system-tts", "livekit-self-hosted"))

    def test_paid_steps_come_after_free_steps(self):
        for service in ("stt", "tts", "video", "hosting"):
            tiers = [step.tier for step in fallback_chain(service)]
            first_paid = next((i for i, t in enumerate(tiers) if t == "paid"), None)
            if first_paid is not None:
                self.assertNotIn("free", tiers[first_paid + 1:])

    def test_reasoning_has_no_free_equivalent_and_says_so(self):
        chain = fallback_chain("reasoning")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].name, "anthropic-claude")
        self.assertEqual(chain[0].tier, "paid")
        self.assertIn("No free local equivalent", chain[0].notes)

    def test_hosting_chain_is_free_first_and_secondary_not_provisioned(self):
        chain = fallback_chain("hosting")
        self.assertEqual(chain[0].name, "oracle-always-free-primary")
        self.assertEqual(chain[0].status, "deployed")
        self.assertEqual(chain[1].status, "not-provisioned")

    def test_free_first_plan_is_json_serializable(self):
        plan = free_first_plan()
        self.assertEqual(json.loads(json.dumps(plan)), plan)
        self.assertEqual(plan["stt"][0]["name"], "faster-whisper-local")


class DnsPlanTest(unittest.TestCase):
    def test_four_a_records_ttl_300(self):
        records = dns_plan(FAKE_IPV4)
        self.assertEqual(len(records), 4)
        hosts = {record["host"] for record in records}
        self.assertEqual(hosts, {
            "sandersdashandseal.com", "www.sandersdashandseal.com",
            "sanderslegalhelpersllc.com", "www.sanderslegalhelpersllc.com",
        })
        for record in records:
            self.assertEqual(record["type"], "A")
            self.assertEqual(record["ttl_seconds"], DNS_TTL_SECONDS)
            self.assertEqual(record["ttl_seconds"], 300)
            self.assertEqual(record["target"], FAKE_IPV4)

    def test_missing_www_sanderslegalhelpersllc_flagged(self):
        records = dns_plan(FAKE_IPV4)
        missing = [r for r in records if r["host"] == "www.sanderslegalhelpersllc.com"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["verified_status"], "missing-nxdomain-2026-11-13")
        self.assertIn("CREATE", missing[0]["action"])
        others = [r for r in records if r["host"] != "www.sanderslegalhelpersllc.com"]
        for record in others:
            self.assertEqual(record["verified_status"], "verified-2026-11-13")

    def test_unset_ipv4_renders_placeholder_not_a_real_address(self):
        records = dns_plan()
        for record in records:
            self.assertEqual(record["target"], "PRIMARY_INSTANCE_IP_UNSET")
            self.assertNotIn("129.146.111.166", record["target"])

    def test_config_dns_plan_uses_env_ipv4(self):
        cfg = GlobalRegionsConfig.from_env({"SDS_PUBLIC_IPV4": FAKE_IPV4})
        hosts = {r["host"]: r["target"] for r in cfg.dns_plan()}
        self.assertEqual(hosts["sandersdashandseal.com"], FAKE_IPV4)


class FailoverPlanTest(unittest.TestCase):
    def test_failover_is_plan_only(self):
        plan = failover_plan()
        self.assertEqual(plan["status"], "PLAN_ONLY")
        self.assertIs(plan["deployed"], False)
        self.assertEqual(plan["secondary_region_status"], "NOT_PROVISIONED")
        self.assertIn("Owner approval", plan["preconditions"][0])
        self.assertIn("No secondary region is provisioned", plan["explicitly_not_done"][0])
        self.assertTrue(any("backup" in step.lower() for step in plan["steps"]))

    def test_summary_is_json_serializable_and_marks_gap(self):
        cfg = GlobalRegionsConfig.from_env({})
        summary = cfg.summary()
        self.assertEqual(json.loads(json.dumps(summary)), summary)
        self.assertEqual(summary["failover_status"], "PLAN_ONLY (not deployed)")
        self.assertEqual(summary["dns_missing_records"],
                         ["www.sanderslegalhelpersllc.com"])
        self.assertIs(summary["primary_ipv4_set"], False)
        self.assertEqual(summary["services"]["livekit"]["max_attempts"], 5)
        self.assertEqual(summary["services"]["daedalus"]["free_first"],
                         "anthropic-claude")
        self.assertNotIn("129.146.111.166", cfg.redacted_summary())


if __name__ == "__main__":
    unittest.main()
