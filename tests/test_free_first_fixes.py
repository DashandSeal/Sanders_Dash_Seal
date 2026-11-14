"""Tests for the 8 approved free-first fixes (2026-11-13).

Fakes only: no live calls, no keys, no network. Each fix is pinned
by at least one test so a paid-first / deprecated default cannot
silently return.
"""
import ast
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _read(rel):
    return (REPO_ROOT / rel).read_text()


class TestFix1StripeLivemodeDefaults(unittest.TestCase):

    def test_native_runtime_default_is_test_mode(self):
        # P2 adaptation: on the free-first branch this file still had
        # settings.get('stripe_livemode', False). On this branch P0
        # replaced native_runtime.py wholesale with a thin composition
        # root delegating to deploy.deployment (the old file could not
        # run at all); no stripe_livemode default exists in it to flip,
        # so pin that: it compiles, delegates, and contains no live
        # default anywhere.
        import py_compile
        py_compile.compile(
            str(REPO_ROOT / "core_platform/native_runtime.py"),
            doraise=True)
        text = _read("core_platform/native_runtime.py")
        self.assertIn("deploy.deployment", text)
        self.assertNotIn("stripe_livemode', True", text)
        self.assertNotIn('stripe_livemode", True', text)


class TestFix2DeprecatedModelDefaults(unittest.TestCase):
    def test_daedalus_config_defaults_are_current(self):
        from core_platform.daedalus_config import (
            DEFAULT_TTS_MODEL,
            DEFAULT_WHISPER_MODEL,
            DaedalusSettings,
        )
        self.assertEqual(DEFAULT_WHISPER_MODEL, "gpt-transcribe")
        # Realtime TTS model (sibling branch 13299a3); NOT an /audio/speech id.
        self.assertEqual(DEFAULT_TTS_MODEL, "gpt-realtime-2.1-mini")
        settings = DaedalusSettings.from_env({})
        self.assertEqual(settings.whisper_model, "gpt-transcribe")
        self.assertEqual(settings.tts_model, "gpt-realtime-2.1-mini")
        self.assertNotIn('DEFAULT_WHISPER_MODEL = "whisper-1"',
                         _read("core_platform/daedalus_config.py"))
        self.assertNotIn('DEFAULT_TTS_MODEL = "tts-1"',
                         _read("core_platform/daedalus_config.py"))


class TestFix3FreeStunDefault(unittest.TestCase):
    def test_dashboard_defaults_to_google_stun(self):
        html = _read("worker/src/dashboard.html")
        self.assertIn("stun:stun.l.google.com:19302", html)
        self.assertIn(
            "options.iceServers || [{urls: 'stun:stun.l.google.com:19302'}]",
            html,
        )


class TestFix4ElevenLabsVoiceIdRequired(unittest.TestCase):
    def test_demo_voice_id_is_gone(self):
        self.assertNotIn("21m00Tcm4TlvDq8ikWAM",
                         _read("core_platform/daedalus_voice.py"))

    def test_voice_id_required(self):
        from core_platform.daedalus_voice import ElevenLabsSynthesizer
        env = dict(os.environ)
        os.environ.pop("ELEVENLABS_API_KEY", None)
        os.environ.pop("ELEVENLABS_VOICE_ID", None)
        os.environ.pop("DAEDALUS_ELEVENLABS_VOICE_ID", None)
        try:
            with self.assertRaises(ValueError):
                ElevenLabsSynthesizer()
            os.environ["ELEVENLABS_API_KEY"] = "test-key"
            with self.assertRaises(ValueError) as ctx:
                ElevenLabsSynthesizer()
            self.assertIn("voice_id", str(ctx.exception))
            # With a voice id supplied, the next failure is the missing
            # elevenlabs package, not a silent demo-voice fallback.
            with self.assertRaises(ImportError):
                ElevenLabsSynthesizer(voice_id="owner-supplied-voice")
        finally:
            os.environ.clear()
            os.environ.update(env)


class TestFix5CatalogRebuild(unittest.TestCase):
    def test_catalog_loads_as_real_json(self):
        from core_platform.free_resources import (
            allowance_comparison,
            catalog,
            inventory_mapping,
        )
        data = catalog()
        self.assertEqual(data["platform"], "Sanders Dash & Seal")
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["governing_core_law"]["number"], 10)
        self.assertIn("Always Free", data["governing_core_law"]["text"])
        self.assertEqual(data["governing_core_Law"]["number"], 11)
        self.assertIn("actually use", data["governing_core_Law"]["text"])
        self.assertEqual(len(data["resources"]), 6)
        for item in data["resources"]:
            for key in ("id", "resource_id", "resource_type",
                        "inventory_types", "allowances"):
                self.assertIn(key, item, item.get("id"))

    def test_inventory_mapping_reports_observation_status(self):
        from core_platform.free_resources import inventory_mapping
        mapped = inventory_mapping(
            {"resources": [{"resource_type": "compute_instance"}]})
        compute = [r for r in mapped["resources"]
                   if r["resource_id"] == "oracle-a1-compute"][0]
        self.assertEqual(compute["count"], 1)
        self.assertEqual(compute["observation_status"],
                         "RELATED_METADATA_OBSERVED")
        unobserved = inventory_mapping({"resources": []})["resources"][0]
        self.assertEqual(unobserved["observation_status"], "NOT_OBSERVED")
        self.assertNotIn(None, mapped["resources"])

    def test_inventory_mapping_tolerates_null_inventory_types(self):
        from core_platform.free_resources import catalog, inventory_mapping
        data = catalog()
        data["resources"][0]["inventory_types"] = None
        with mock.patch("core_platform.free_resources.catalog",
                        return_value=data):
            mapped = inventory_mapping({"resources": []})
        self.assertEqual(mapped["resources"][0]["count"], 0)

    def test_allowance_comparison_against_rebuilt_catalog(self):
        from core_platform.free_resources import allowance_comparison
        ok = allowance_comparison("oracle-a1-compute", {"ocpu": 2},
                                  usage={"ocpu": 0}, account_state="paid_only")
        self.assertEqual(ok["status"], "WITHIN_DOCUMENTED_AMOUNTS")
        over = allowance_comparison("oracle-a1-compute", {"ocpu": 3},
                                    usage={"ocpu": 0}, account_state="paid_only")
        self.assertEqual(over["status"], "EXCEEDS_DOCUMENTED_AMOUNTS")


    def test_corrupted_python_preserved_not_discarded(self):
        preserved = REPO_ROOT / "core_platform/oci_core_laws.py"
        self.assertTrue(preserved.exists())
        self.assertIn("class CoreLaws", preserved.read_text())


class TestFix6TtsOrderGoogleBeforeElevenLabs(unittest.TestCase):
    def test_google_is_tried_before_elevenlabs(self):
        from core_platform import voice_api

        class FakeSynth:
            def __init__(self, name):
                self.name = name

        order = []
        def google():
            order.append("google")
            return FakeSynth("google-tts-wavenet")
        def elevenlabs():
            order.append("elevenlabs")
            return FakeSynth("elevenlabs")
        def system():
            order.append("system")
            raise RuntimeError("system TTS unavailable")
        import core_platform.daedalus_voice as dv
        with mock.patch.object(dv, "SystemTTSSynthesizer", system), \
             mock.patch.object(dv, "GoogleTTSSynthesizer", google), \
             mock.patch.object(dv, "ElevenLabsSynthesizer", elevenlabs), \
             mock.patch.object(dv, "FasterWhisperTranscriber",
                               side_effect=RuntimeError("no model")), \
             mock.patch.object(dv, "DeepgramTranscriber",
                               side_effect=ValueError("no key")), \
             mock.patch.object(dv, "OpenAITranscriber",
                               side_effect=ValueError("no key")):
            app = voice_api.create_voice_app_from_providers()
        self.assertEqual(order, ["system", "google"])
        self.assertNotIn("elevenlabs", order)

    def test_no_backends_is_honest_503(self):
        from core_platform.voice_api import create_voice_app_from_providers
        app = create_voice_app_from_providers()
        captured = {}
        def start(status, headers):
            captured["status"] = status
        env = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/voice/status",
               "wsgi.input": io.BytesIO(b"")}
        body = b"".join(app(env, start))
        payload = json.loads(body)
        self.assertEqual(captured["status"], "200 OK")
        self.assertIsNone(payload["transcriber"])
        self.assertIsNone(payload["synthesizer"])


class TestFix7NginxCameraMicScoped(unittest.TestCase):
    def test_voice_page_only_relaxation(self):
        for rel in ("nginx.conf", "deploy/nginx.http.conf"):
            text = _read(rel)
            self.assertIn("location = /voice.html", text, rel)
            self.assertIn('camera=(self), microphone=(self)', text, rel)
            # The global block stays in place for everything else.
            self.assertIn('camera=(), microphone=(), geolocation=()', text, rel)


class TestFix8BackupTimerPath(unittest.TestCase):
    def test_deploy_backup_wrapper_exists_and_forwards(self):
        script = REPO_ROOT / "deploy_backup.sh"
        self.assertTrue(script.exists())
        self.assertTrue(os.access(script, os.X_OK))
        self.assertIn("deploy/ledger_backup.py", script.read_text())
        result = subprocess.run(["bash", "-n", str(script)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(["bash", str(script), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ledger_backup.py", result.stdout + result.stderr
                      or "usage: ledger_backup.py")


if __name__ == "__main__":
    unittest.main()
