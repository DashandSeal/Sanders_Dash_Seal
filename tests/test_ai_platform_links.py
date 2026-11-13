"""Tests for core_platform.ai_platform_links (central link registry).

Stdlib ``unittest`` only -- no pytest, no network, no live keys, no paid
calls. Environment facts are injected as fakes (``env`` mappings,
``import_checker`` and ``which_checker`` callables) so every status in
the registry is reachable deterministically:

* LINKED -- local modules import and a functional probe succeeds, or
  (for keyed platforms) a fake key + fake model + fake approval builds
  local wiring without any network call.
* MISSING_KEY -- a required key/secret/model/package is absent.
* MISSING_APPROVAL -- key present, approval env var absent.
* NOT_IMPLEMENTED -- no real local backend is installed.
* BROKEN -- local code fails to compile or a checker fails.

P2 adaptation (2026-11-13, unified branch): the grantwriter/bozly
BROKEN expectations from the links branch no longer hold here --
P1 rebuilt grantwriter (34 KB module, no syntax error) and restored
bozly_global_traceback.py from git, so both report LINKED and the
no-key table is LINKED 6 / MISSING_KEY 2 / NOT_IMPLEMENTED 1 /
BROKEN 0. The tests below pin the CURRENT table, not the old one.

Run from the repo root: ``python3 -m unittest tests.test_ai_platform_links -v``
or ``python3 -m unittest discover -s tests -p 'test_ai_platform_links.py'``.
"""

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core_platform import ai_platform_links as links  # noqa: E402


def _no_imports(name):
    """Fake import checker: nothing optional is installed."""
    return False


def _no_binaries(name):
    """Fake which checker: no optional binary is on PATH."""
    return None


class RegistryTest(unittest.TestCase):
    def test_registry_loads_and_declares_all_nine_platforms(self):
        registry = links.load_registry()
        self.assertEqual(registry["schema"], 1)
        ids = [p["id"] for p in registry["platforms"]]
        self.assertEqual(ids, list(links.PLATFORM_IDS))
        self.assertEqual(len(ids), 9)

    def test_registry_has_no_secrets(self):
        text = Path(links._DEFAULT_CONFIG).read_text(encoding="utf-8")
        lowered = text.lower()
        for banned in ("sk-", "whsec_", "api_key_value", "password"):
            self.assertNotIn(banned, lowered)
        data = json.loads(text)
        # Env var *names* are declared; no values are.
        for entry in data["platforms"]:
            for var in entry["env_vars"]:
                self.assertTrue(var.isupper())
        for provider in data["providers"].values():
            for var in provider["env_vars"]:
                self.assertTrue(var.isupper())

    def test_registry_declares_cost_tier_and_free_alternative(self):
        registry = links.load_registry()
        self.assertEqual(registry["cost_policy"], "free_first")
        for entry in registry["platforms"]:
            self.assertIn(entry["cost_tier"],
                          ("free", "paid", "free_first"))
            self.assertTrue(entry["free_alternative"])
            self.assertTrue(entry["local_modules"])
            self.assertTrue(entry["endpoint"])
            self.assertGreater(entry["timeout_seconds"], 0)

    def test_statuses_are_the_five_declared(self):
        self.assertEqual(links.STATUSES, (
            "LINKED", "MISSING_KEY", "MISSING_APPROVAL",
            "NOT_IMPLEMENTED", "BROKEN"))


class NoKeyStatusTest(unittest.TestCase):
    """Honest no-live-key run: the exact table expected on this machine."""

    def setUp(self):
        self.registry = links.load_registry()
        self.env = {}  # no keys at all
        self.results = links.check_all(
            registry=self.registry, env=self.env,
            import_checker=_no_imports, which_checker=_no_binaries)

    def test_all_nine_platforms_report_a_status(self):
        self.assertEqual(set(self.results), set(links.PLATFORM_IDS))
        for pid, status in self.results.items():
            self.assertIn(status.status, links.STATUSES, pid)
            self.assertIsInstance(status.missing, list)
            self.assertTrue(status.detail, pid)

    def test_no_platform_is_linked_without_a_real_check(self):
        # With no keys and no optional packages installed, the only
        # LINKED platforms are the purely local ones whose functional
        # probes genuinely pass. (P2: grantwriter and bozly join the
        # four from the links branch -- P1 rebuilt grantwriter and
        # restored the truncated bozly traceback file.)
        linked = sorted(pid for pid, s in self.results.items()
                        if s.status == "LINKED")
        self.assertEqual(linked, ["ai_role_workers", "bozly", "grantwriter",
                                  "minotaur_sentinel", "sharpshooter",
                                  "twingate"])

    def test_daedalus_is_missing_key_and_names_it(self):
        s = self.results["daedalus"]
        self.assertEqual(s.status, "MISSING_KEY")
        self.assertIn("ANTHROPIC_API_KEY", s.missing)
        self.assertIn("DAEDALUS_CLAUDE_MODEL", s.missing)

    def test_grantwriter_is_linked_after_p1_rebuild(self):
        # P2 adaptation: on the links branch this was BROKEN (SyntaxError
        # line 115). P1 rebuilt app/grantwriter_mother.py, so it compiles
        # and reports LINKED here.
        s = self.results["grantwriter"]
        self.assertEqual(s.status, "LINKED")
        self.assertEqual(s.missing, [])

    def test_bozly_is_linked_after_p1_restore(self):
        # P2 adaptation: on the links branch this was BROKEN (truncated
        # bozly_global_traceback.py line 222). P1 restored that file
        # from git, so all Bozly modules compile and report LINKED here.
        s = self.results["bozly"]
        self.assertEqual(s.status, "LINKED")
        self.assertEqual(s.missing, [])

    def test_stream_api_is_missing_key_and_names_secret_and_package(self):
        s = self.results["stream_api"]
        self.assertEqual(s.status, "MISSING_KEY")
        self.assertIn("STRIPE_WEBHOOK_SECRET", s.missing)
        self.assertIn("package stripe not installed", s.missing)

    def test_voice_is_not_implemented_and_names_local_backends(self):
        s = self.results["voice_audio_video"]
        self.assertEqual(s.status, "NOT_IMPLEMENTED")
        joined = " ".join(s.missing)
        self.assertIn("faster-whisper", joined)
        self.assertIn("pyttsx3", joined)
        self.assertIn("OPENAI_API_KEY", s.missing)
        self.assertIn("DEEPGRAM_API_KEY", s.missing)
        self.assertIn("ELEVENLABS_API_KEY", s.missing)

    def test_local_platforms_auto_connected_something_real(self):
        for pid in ("ai_role_workers", "minotaur_sentinel", "twingate",
                    "sharpshooter"):
            self.assertTrue(self.results[pid].auto_connected, pid)

    def test_summarize_counts_cover_all_nine(self):
        summary = links.summarize(self.results)
        self.assertEqual(summary["total"], 9)
        self.assertTrue(summary["all_reported"])
        self.assertEqual(sum(summary["counts"].values()), 9)
        self.assertEqual(summary["counts"]["LINKED"], 6)
        self.assertEqual(summary["counts"]["MISSING_KEY"], 2)
        self.assertEqual(summary["counts"]["BROKEN"], 0)
        self.assertEqual(summary["counts"]["NOT_IMPLEMENTED"], 1)
        self.assertEqual(summary["counts"]["MISSING_APPROVAL"], 0)


class FakeKeyTest(unittest.TestCase):
    """Fakes stand in for environment facts only; no live call is made."""

    def setUp(self):
        self.registry = links.load_registry()

    def test_daedalus_fake_key_without_approval_is_missing_approval(self):
        env = {"ANTHROPIC_API_KEY": "fake-key-for-test",
               "DAEDALUS_CLAUDE_MODEL": "fake-model-for-test"}
        s = links.check_platform("daedalus", registry=self.registry, env=env,
                                 import_checker=_no_imports)
        self.assertEqual(s.status, "MISSING_APPROVAL")
        self.assertTrue(any("SDS_OWNER_APPROVAL_DAEDALUS" in m
                            for m in s.missing))

    def test_daedalus_fake_key_with_approval_links_locally(self):
        env = {"ANTHROPIC_API_KEY": "fake-key-for-test",
               "DAEDALUS_CLAUDE_MODEL": "fake-model-for-test",
               "SDS_OWNER_APPROVAL_DAEDALUS": "yes"}
        s = links.check_platform("daedalus", registry=self.registry, env=env,
                                 import_checker=_no_imports)
        self.assertEqual(s.status, "LINKED")
        self.assertIn("No live call", s.detail)

    def test_daedalus_key_without_model_is_missing_key(self):
        env = {"ANTHROPIC_API_KEY": "fake-key-for-test"}
        s = links.check_platform("daedalus", registry=self.registry, env=env,
                                 import_checker=_no_imports)
        self.assertEqual(s.status, "MISSING_KEY")
        self.assertIn("DAEDALUS_CLAUDE_MODEL", s.missing)

    def test_stream_api_fake_secret_without_approval_is_missing_approval(self):
        env = {"STRIPE_WEBHOOK_SECRET": "whsec_fake_for_test",
               "STRIPE_SECRET_KEY": "sk_test_fake_for_test"}
        s = links.check_platform("stream_api", registry=self.registry, env=env,
                                 import_checker=lambda name: name == "stripe")
        self.assertEqual(s.status, "MISSING_APPROVAL")

    def test_stream_api_fake_secret_with_approval_links_locally(self):
        # Only reachable where the stripe package is really installed;
        # the fake env supplies the secret, the real package does the work.
        try:
            import stripe  # noqa: F401
        except ImportError:
            self.skipTest("stripe package not installed in this interpreter")
        env = {"STRIPE_WEBHOOK_SECRET": "whsec_fake_for_test",
               "STRIPE_SECRET_KEY": "sk_test_fake_for_test",
               "SDS_OWNER_APPROVAL_STREAM_API": "yes"}
        s = links.check_platform("stream_api", registry=self.registry, env=env,
                                 import_checker=lambda name: name == "stripe")
        self.assertEqual(s.status, "LINKED")

    def test_stream_api_fake_package_claim_is_corrected_by_reality(self):
        # A fake import checker claiming stripe is present cannot fake the
        # real import: if stripe is really absent, the verdict is
        # MISSING_KEY naming the package.
        try:
            import stripe  # noqa: F401
        except ImportError:
            pass
        else:
            self.skipTest("stripe is really installed in this interpreter")
        env = {"STRIPE_WEBHOOK_SECRET": "whsec_fake_for_test",
               "STRIPE_SECRET_KEY": "sk_test_fake_for_test",
               "SDS_OWNER_APPROVAL_STREAM_API": "yes"}
        s = links.check_platform("stream_api", registry=self.registry, env=env,
                                 import_checker=lambda name: name == "stripe")
        self.assertEqual(s.status, "MISSING_KEY")
        self.assertTrue(any("stripe" in m for m in s.missing))

    def test_voice_fake_faster_whisper_links_local_only(self):
        env = {}
        s = links.check_platform(
            "voice_audio_video", registry=self.registry, env=env,
            import_checker=lambda name: name == "faster_whisper",
            which_checker=lambda name: "/usr/bin/ffmpeg"
            if name == "ffmpeg" else None)
        self.assertEqual(s.status, "LINKED")
        self.assertIn("faster-whisper", s.detail)

    def test_voice_fake_system_tts_links_local_only(self):
        s = links.check_platform(
            "voice_audio_video", registry=self.registry, env={},
            import_checker=lambda name: name == "pyttsx3",
            which_checker=lambda name: "/usr/bin/ffmpeg"
            if name == "ffmpeg" else None)
        self.assertEqual(s.status, "LINKED")
        self.assertIn("system TTS", s.detail)


class ProvidersTest(unittest.TestCase):
    def setUp(self):
        self.registry = links.load_registry()

    def test_all_providers_missing_key_without_keys(self):
        providers = links.check_providers(registry=self.registry, env={},
                                          import_checker=_no_imports)
        self.assertEqual(set(providers), {
            "anthropic", "openai", "deepgram", "elevenlabs", "google_tts",
            "stripe", "livekit", "signwell", "bluenotary"})
        for pid, info in providers.items():
            self.assertEqual(info["status"], "MISSING_KEY", pid)
            self.assertTrue(info["missing"], pid)
            self.assertTrue(info["free_alternative"], pid)

    def test_signwell_and_bluenotary_name_their_keys(self):
        providers = links.check_providers(registry=self.registry, env={},
                                          import_checker=_no_imports)
        self.assertIn("SIGNWELL_API_KEY",
                      providers["signwell"]["missing"])
        self.assertIn("BLUENOTARY_API_KEY",
                      providers["bluenotary"]["missing"])

    def test_provider_with_fake_key_but_no_approval_is_missing_approval(self):
        env = {"ANTHROPIC_API_KEY": "fake-key-for-test"}
        providers = links.check_providers(
            registry=self.registry, env=env,
            import_checker=lambda name: name == "anthropic")
        self.assertEqual(providers["anthropic"]["status"], "MISSING_APPROVAL")


class AutoConnectTest(unittest.TestCase):
    def test_auto_connect_reports_connected_and_cannot(self):
        results = links.check_all(
            registry=links.load_registry(), env={},
            import_checker=_no_imports, which_checker=_no_binaries)
        out = links.auto_connect(results)
        self.assertIn("ai_role_workers", out["connected"])
        self.assertIn("minotaur_sentinel", out["connected"])
        self.assertIn("twingate", out["connected"])
        self.assertIn("sharpshooter", out["connected"])
        # Nothing keyed is ever auto-connected.
        for pid in ("daedalus", "stream_api", "voice_audio_video"):
            self.assertNotIn(pid, out["connected"])
        self.assertIn("daedalus", out["cannot_auto_connect"])
        self.assertIn("ANTHROPIC_API_KEY",
                      out["cannot_auto_connect"]["daedalus"])

    def test_check_all_never_raises_on_a_broken_checker(self):
        # Even if the registry pointed at a missing module, every
        # platform still gets a status.
        registry = links.load_registry()
        broken = json.loads(json.dumps(registry))
        broken["platforms"][0]["local_modules"] = ["core_platform/nope.py"]
        results = links.check_all(registry=broken, env={},
                                  import_checker=_no_imports,
                                  which_checker=_no_binaries)
        self.assertEqual(len(results), 9)
        self.assertIn(results["daedalus"].status,
                      ("BROKEN", "NOT_IMPLEMENTED"))


if __name__ == "__main__":
    unittest.main()
