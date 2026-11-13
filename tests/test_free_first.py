"""Tests for the free-first rule (core_platform/free_first.py).

Free-first rule (Roosevelt Sanders, 2026-11-13): always use the free
resources available. Paid providers are opt-in only and never the default.
All tests use fakes / in-memory state. No live calls, no keys, $0 spent.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_platform import free_first
from core_platform.free_first import (
    FreeTierExhausted,
    FreeTierUsage,
    PaidOptInRequired,
    check_current_instance,
    check_oracle_always_free,
    default_ice_servers,
    free_first_status,
    paid_opt_in_enabled,
    select_provider,
    stripe_livemode_default,
)


class TestPaidOptIn(unittest.TestCase):
    def test_opt_in_off_by_default(self):
        self.assertFalse(paid_opt_in_enabled({}))
        self.assertFalse(paid_opt_in_enabled({"SDS_ALLOW_PAID_PROVIDERS": "true"}))
        self.assertFalse(paid_opt_in_enabled({"SDS_ALLOW_PAID_PROVIDERS": "yes"}))
        self.assertFalse(paid_opt_in_enabled({"SDS_ALLOW_PAID_PROVIDERS": "0"}))

    def test_opt_in_on_only_with_exact_1(self):
        self.assertTrue(paid_opt_in_enabled({"SDS_ALLOW_PAID_PROVIDERS": "1"}))


class TestSelectProvider(unittest.TestCase):
    def test_stt_prefers_free_local_whisper(self):
        self.assertEqual(
            select_provider("stt", ["openai-gpt-transcribe", "faster-whisper-local"], env={}),
            "faster-whisper-local",
        )

    def test_stt_falls_to_deepgram_credit_after_local(self):
        self.assertEqual(
            select_provider("stt", ["deepgram-nova-3"], env={}),
            "deepgram-nova-3",
        )

    def test_stt_paid_openai_blocked_without_opt_in(self):
        with self.assertRaises(PaidOptInRequired):
            select_provider("stt", ["openai-gpt-transcribe"], env={})

    def test_stt_paid_openai_allowed_with_opt_in(self):
        self.assertEqual(
            select_provider(
                "stt", ["openai-gpt-transcribe"],
                env={"SDS_ALLOW_PAID_PROVIDERS": "1"},
            ),
            "openai-gpt-transcribe",
        )

    def test_tts_prefers_free_system_tts(self):
        self.assertEqual(
            select_provider(
                "tts",
                ["elevenlabs-free", "google-cloud-tts", "system-tts-pyttsx3"],
                env={},
            ),
            "system-tts-pyttsx3",
        )

    def test_tts_google_free_tier_before_elevenlabs(self):
        # Google TTS free tier (4M chars/mo) outranks ElevenLabs free
        # credits (10k/mo, non-commercial) once system TTS is unavailable.
        self.assertEqual(
            select_provider("tts", ["elevenlabs-free", "google-cloud-tts"], env={}),
            "google-cloud-tts",
        )

    def test_inference_has_no_free_default_without_local(self):
        with self.assertRaises(PaidOptInRequired):
            select_provider("inference", ["anthropic-claude"], env={})

    def test_inference_prefers_localhost_when_available(self):
        self.assertEqual(
            select_provider(
                "inference",
                ["anthropic-claude", "local-inference-localhost"], env={},
            ),
            "local-inference-localhost",
        )

    def test_video_prefers_free_stun_and_livekit_over_daily(self):
        self.assertEqual(
            select_provider(
                "video",
                ["daily-co-free", "livekit-self-hosted", "webrtc-free-stun"],
                env={},
            ),
            "webrtc-free-stun",
        )

    def test_storage_prefers_sqlite_over_object_storage(self):
        self.assertEqual(
            select_provider(
                "storage",
                ["oracle-always-free-object", "sqlite-ledger"], env={},
            ),
            "sqlite-ledger",
        )

    def test_nothing_available_raises(self):
        with self.assertRaises(ValueError):
            select_provider("stt", [], env={})

    def test_unknown_capability_raises(self):
        with self.assertRaises(ValueError):
            select_provider("teleportation", ["faster-whisper-local"], env={})


class TestFreeTierUsage(unittest.TestCase):
    def test_google_tts_within_4m_free_chars(self):
        usage = FreeTierUsage()
        self.assertEqual(usage.record("google-cloud-tts", 3_000_000, unit="chars"), 3_000_000)
        self.assertEqual(usage.remaining("google-cloud-tts"), 1_000_000)
        self.assertFalse(usage.exhausted("google-cloud-tts"))

    def test_google_tts_exhaustion_reports_instead_of_silently_paying(self):
        usage = FreeTierUsage()
        usage.record("google-cloud-tts", 4_000_000, unit="chars")
        self.assertTrue(usage.exhausted("google-cloud-tts"))
        with self.assertRaises(FreeTierExhausted):
            usage.record("google-cloud-tts", 1, unit="chars")

    def test_elevenlabs_10k_credit_limit(self):
        usage = FreeTierUsage()
        usage.record("elevenlabs-free", 10_000, unit="credits")
        with self.assertRaises(FreeTierExhausted):
            usage.record("elevenlabs-free", 1, unit="credits")

    def test_deepgram_200_credit_limit(self):
        usage = FreeTierUsage()
        # ~$200 of Nova-3 pre-recorded transcription at $0.0043/min.
        usage.record("deepgram-nova-3", 199.0, unit="USD")
        with self.assertRaises(FreeTierExhausted):
            usage.record("deepgram-nova-3", 2.0, unit="USD")

    def test_unlimited_local_provider_has_no_cap(self):
        usage = FreeTierUsage()
        self.assertIsNone(usage.remaining("faster-whisper-local"))
        self.assertFalse(usage.exhausted("faster-whisper-local"))
        self.assertEqual(usage.record("faster-whisper-local", 10_000_000), 10_000_000)

    def test_negative_usage_rejected(self):
        with self.assertRaises(ValueError):
            FreeTierUsage().record("google-cloud-tts", -1)


class TestOracleAlwaysFree(unittest.TestCase):
    def test_current_instance_is_within_always_free(self):
        result = check_current_instance()
        self.assertTrue(result["within_always_free"])
        self.assertTrue(result["checks"]["a1_ocpu"]["within"])
        self.assertTrue(result["checks"]["a1_memory_gb"]["within"])
        self.assertTrue(result["checks"]["block_volume_gb"]["within"])

    def test_3_ocpu_exceeds_current_2_ocpu_limit(self):
        # June 2026 cut: 4 OCPU / 24 GB -> 2 OCPU / 12 GB.
        result = check_oracle_always_free(
            ocpu=3, memory_gb=6, block_volume_gb=47)
        self.assertFalse(result["within_always_free"])
        self.assertFalse(result["checks"]["a1_ocpu"]["within"])

    def test_300gb_block_exceeds_200gb_limit(self):
        result = check_oracle_always_free(
            ocpu=1, memory_gb=6, block_volume_gb=300)
        self.assertFalse(result["within_always_free"])
        self.assertFalse(result["checks"]["block_volume_gb"]["within"])


class TestDefaults(unittest.TestCase):
    def test_stripe_defaults_to_test_mode(self):
        self.assertFalse(stripe_livemode_default())

    def test_default_ice_servers_are_free_stun_only(self):
        servers = default_ice_servers()
        self.assertEqual(len(servers), 1)
        self.assertTrue(servers[0]["urls"].startswith("stun:"))
        self.assertNotIn("turn:", str(servers))

    def test_free_first_status_covers_every_capability(self):
        status = free_first_status(env={})
        for capability in (
                "stt", "tts", "inference", "video", "storage", "hosting",
                "database"):
            self.assertIn(capability, status)
            self.assertFalse(status[capability]["paid_opt_in"])
            # The default provider in every capability is a free one.
            default = status[capability]["default_free_provider"]
            self.assertNotIn(default, free_first.PAID_PROVIDERS)


if __name__ == "__main__":
    unittest.main()
