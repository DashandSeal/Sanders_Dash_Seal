"""Tests for Daedalus audio/video/voice (core_platform.daedalus_voice).

Local only: no API key, no network, no deployment.  Every live-provider
adapter is tested only for its honest failure mode (missing key / missing
SDK).  No live Whisper / Deepgram / ElevenLabs / Google / WebRTC call is
made or claimed here.

Run with:  python3 -m unittest discover -s tests -v
(pytest is NOT installed in this environment, so unittest is the runner.)
"""

import hashlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_platform.daedalus_claude_transport import (
    DaedalusClaudeTransport,
    DaedalusResponse,
)
from core_platform.daedalus_engine import DaedalusEngineConfig, build_engine
from core_platform.daedalus_runtime_integration import DaedalusRuntimeIntegration
from core_platform.daedalus_voice import (
    DeepgramTranscriber,
    ElevenLabsSynthesizer,
    FakeSynthesizer,
    FakeTranscriber,
    FasterWhisperTranscriber,
    GoogleTTSSynthesizer,
    OpenAITranscriber,
    SystemTTSSynthesizer,
    is_valid_webrtc_token,
    make_silence_wav,
    read_wav_info,
    speak_prompt,
    validate_audio_bytes,
    validate_signaling_message,
    validate_video_session,
    voice_generate_source,
    wav_duration_seconds,
    write_wav_bytes,
)
from core_platform.voice_api import create_fake_voice_app, create_voice_app


class FakeTransport(DaedalusClaudeTransport):
    """Daedalus transport that returns canned source text, no network.

    Built via __new__ so DaedalusClaudeTransport.__init__ (which demands
    a real model + ANTHROPIC_API_KEY) is never called, while isinstance()
    checks in DaedalusRuntimeIntegration still pass.
    """

    def __init__(self, text="def hello():\n    return 'hello world'\n"):
        self.text = text

    @classmethod
    def create(cls, text="def hello():\n    return 'hello world'\n"):
        obj = cls.__new__(cls)
        obj.text = text
        return obj

    def generate(self, *, system, user_message, max_tokens=2048, metadata=None):
        return DaedalusResponse(
            model="fake-test-model",
            request_id=None,
            message_id="msg_fake_1",
            text=self.text,
            latency_ms=0,
            input_tokens=1,
            output_tokens=1,
        )


def make_integration(text="def hello():\n    return 'hello world'\n"):
    return DaedalusRuntimeIntegration(
        transport=FakeTransport.create(text),
        signing_key=b"x" * 32,
        persist_private_evidence=lambda record, signature: None,
    )


def wsgi_call(app, method, path, body=b"", content_type="application/octet-stream"):
    """Minimal WSGI test harness: returns (status, headers dict, body bytes)."""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.StringIO(),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(headers)

    chunks = app(environ, start_response)
    return captured["status"], captured["headers"], b"".join(chunks)


class TestAudioHelpers(unittest.TestCase):
    def test_wav_round_trip_and_duration(self):
        wav = make_silence_wav(0.5)
        info = read_wav_info(wav)
        self.assertEqual(info["channels"], 1)
        self.assertEqual(info["sample_width"], 2)
        self.assertEqual(info["sample_rate"], 16000)
        self.assertAlmostEqual(info["seconds"], 0.5, places=2)
        self.assertAlmostEqual(wav_duration_seconds(wav), 0.5, places=2)
        self.assertEqual(validate_audio_bytes(wav)["seconds"], info["seconds"])

    def test_write_wav_rejects_bad_params(self):
        with self.assertRaises(ValueError):
            write_wav_bytes(b"\x00", sample_rate=0)
        with self.assertRaises(ValueError):
            write_wav_bytes(b"\x00\x00\x00", sample_width=2, channels=1)

    def test_validate_rejects_garbage_and_empty(self):
        with self.assertRaises(ValueError):
            validate_audio_bytes(b"")
        with self.assertRaises(ValueError):
            validate_audio_bytes(b"not a wav file at all")


class TestFakeBackends(unittest.TestCase):
    def test_fake_transcriber_returns_configured_text(self):
        audio = make_silence_wav(0.25)
        self.assertEqual(
            FakeTranscriber("do the thing").transcribe(audio), "do the thing"
        )
        with self.assertRaises(ValueError):
            FakeTranscriber("do the thing").transcribe(b"")

    def test_fake_synthesizer_records_calls_and_returns_wav(self):
        synth = FakeSynthesizer()
        audio = synth.synthesize("hello world")
        self.assertEqual(synth.calls, ["hello world"])
        self.assertEqual(read_wav_info(audio)["sample_width"], 2)
        with self.assertRaises(ValueError):
            synth.synthesize("   ")


class TestProviderAdaptersFailHonestly(unittest.TestCase):
    def test_faster_whisper_missing_package_or_bad_model(self):
        with self.assertRaises(ValueError):
            FasterWhisperTranscriber("large-v3")
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            with self.assertRaises(ImportError):
                FasterWhisperTranscriber("tiny")

    def test_deepgram_requires_key(self):
        env = dict(os.environ)
        os.environ.pop("DEEPGRAM_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                DeepgramTranscriber()
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_openai_requires_key_and_rejects_whisper1(self):
        env = dict(os.environ)
        os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                OpenAITranscriber()
            with self.assertRaises(ValueError):
                OpenAITranscriber(api_key="sk-test", model="whisper-1")
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_elevenlabs_requires_key(self):
        env = dict(os.environ)
        os.environ.pop("ELEVENLABS_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                ElevenLabsSynthesizer()
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_google_and_system_tts_missing_sdk(self):
        try:
            import google.cloud.texttospeech  # noqa: F401
        except ImportError:
            with self.assertRaises(ImportError):
                GoogleTTSSynthesizer()
        try:
            import pyttsx3  # noqa: F401
        except ImportError:
            with self.assertRaises(ImportError):
                SystemTTSSynthesizer()


class TestVideoSignalling(unittest.TestCase):
    def test_token_shape(self):
        self.assertTrue(is_valid_webrtc_token("a" * 64))
        self.assertFalse(is_valid_webrtc_token("abc"))
        self.assertFalse(is_valid_webrtc_token("g" * 64))

    def test_validate_video_session(self):
        result = validate_video_session(session_id="room-1", token="b" * 64)
        self.assertEqual(result["session_id"], "room-1")
        self.assertEqual(
            result["token_sha256"], hashlib.sha256(("b" * 64).encode()).hexdigest()
        )
        with self.assertRaises(ValueError):
            validate_video_session(session_id="bad room!", token="b" * 64)
        with self.assertRaises(ValueError):
            validate_video_session(session_id="room-1", token="short")

    def test_validate_signaling_message_offer_answer_ice(self):
        offer = validate_signaling_message(
            {"action": "offer", "targetSessionId": "room-1",
             "sdp": {"type": "offer", "sdp": "v=0\r\n..."}},
            session_id="room-1",
        )
        self.assertEqual(offer["action"], "offer")
        answer = validate_signaling_message(
            {"action": "answer", "targetSessionId": "room-1",
             "sdp": {"type": "answer", "sdp": "v=0\r\n..."}},
            session_id="room-1",
        )
        self.assertEqual(answer["sdp"]["type"], "answer")
        ice = validate_signaling_message(
            {"action": "ice_candidate", "targetSessionId": "room-1",
             "candidate": {"candidate": "candidate:1 1 udp 1 10.0.0.1 5000 typ host"}},
            session_id="room-1",
        )
        self.assertEqual(ice["action"], "ice_candidate")
        with self.assertRaises(ValueError):
            validate_signaling_message(
                {"action": "offer", "targetSessionId": "room-1",
                 "sdp": {"type": "answer", "sdp": "v=0"}},
                session_id="room-1",
            )
        with self.assertRaises(ValueError):
            validate_signaling_message(
                {"action": "offer", "targetSessionId": "other-room",
                 "sdp": {"type": "offer", "sdp": "v=0"}},
                session_id="room-1",
            )
        with self.assertRaises(ValueError):
            validate_signaling_message(
                {"action": "hangup", "targetSessionId": "room-1"},
                session_id="room-1",
            )


class TestVoiceGenerateSource(unittest.TestCase):
    def test_fake_chain_end_to_end(self):
        synth = FakeSynthesizer()
        result = voice_generate_source(
            transcriber=FakeTranscriber("generate a python hello world function"),
            integration=make_integration(),
            synthesizer=synth,
            audio_bytes=make_silence_wav(0.25),
            invention_id="inv-voice-test-1",
            language="Python",
            inventor_assertions=("test",),
        )
        self.assertEqual(result["transcript"], "generate a python hello world function")
        self.assertIn("def hello", result["source_text"])
        self.assertEqual(
            result["source_sha256"],
            hashlib.sha256(result["source_text"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(result["invention_id"], "inv-voice-test-1")
        # The synthesizer must be called once, with the GENERATED text,
        # not with the transcript.
        self.assertEqual(synth.calls, [result["source_text"]])
        self.assertEqual(read_wav_info(result["audio_bytes"])["sample_width"], 2)

    def test_speak_prompt_alias(self):
        self.assertIs(speak_prompt, voice_generate_source)

    def test_empty_audio_and_missing_invention_rejected(self):
        with self.assertRaises(ValueError):
            voice_generate_source(
                transcriber=FakeTranscriber("x"),
                integration=make_integration(),
                synthesizer=FakeSynthesizer(),
                audio_bytes=b"",
                invention_id="inv-1",
            )
        with self.assertRaises(ValueError):
            voice_generate_source(
                transcriber=FakeTranscriber("x"),
                integration=make_integration(),
                synthesizer=FakeSynthesizer(),
                audio_bytes=make_silence_wav(0.1),
                invention_id="",
            )

    def test_build_engine_without_key_or_model_raises(self):
        with self.assertRaises(ValueError):
            build_engine(DaedalusEngineConfig(
                signing_key=b"x" * 32,
                persist_private_evidence=lambda r, s: None,
                persist_confidential=lambda *a, **k: None,
                audit=lambda m: None,
                model=None,
                api_key=None,
            ))


class TestVoiceApi(unittest.TestCase):
    def test_status_reports_fake_backends_no_secrets(self):
        app = create_fake_voice_app()
        status, headers, body = wsgi_call(app, "GET", "/api/voice/status")
        self.assertTrue(status.startswith("200"))
        payload = json.loads(body)
        self.assertEqual(payload["transcriber"], "fake")
        self.assertEqual(payload["synthesizer"], "fake")
        self.assertEqual(payload["video"], "webrtc_signalling_only")
        self.assertNotIn("key", json.dumps(payload).lower())
        self.assertNotIn("secret", json.dumps(payload).lower())

    def test_transcribe_and_speak_with_fakes(self):
        app = create_fake_voice_app()
        status, _, body = wsgi_call(
            app, "POST", "/api/voice/transcribe", make_silence_wav(0.25))
        self.assertTrue(status.startswith("200"))
        self.assertEqual(
            json.loads(body)["transcript"], "generate a python hello world function")
        status, headers, body = wsgi_call(
            app, "POST", "/api/voice/speak",
            json.dumps({"text": "hello"}).encode(), "application/json")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(headers["Content-Type"], "audio/wav")
        self.assertEqual(read_wav_info(body)["sample_width"], 2)

    def test_unconfigured_backends_return_503(self):
        app = create_voice_app()
        status, _, body = wsgi_call(
            app, "POST", "/api/voice/transcribe", make_silence_wav(0.25))
        self.assertTrue(status.startswith("503"))
        self.assertEqual(json.loads(body)["error"], "transcriber_not_configured")
        status, _, body = wsgi_call(
            app, "POST", "/api/voice/speak",
            json.dumps({"text": "hi"}).encode(), "application/json")
        self.assertTrue(status.startswith("503"))
        self.assertEqual(json.loads(body)["error"], "synthesizer_not_configured")

    def test_bad_requests(self):
        app = create_fake_voice_app()
        status, _, _ = wsgi_call(app, "POST", "/api/voice/transcribe", b"garbage")
        self.assertTrue(status.startswith("400"))
        status, _, _ = wsgi_call(
            app, "POST", "/api/voice/speak", b"{not json", "application/json")
        self.assertTrue(status.startswith("400"))
        status, _, _ = wsgi_call(
            app, "POST", "/api/voice/speak",
            json.dumps({"text": ""}).encode(), "application/json")
        self.assertTrue(status.startswith("400"))
        status, _, body = wsgi_call(app, "GET", "/api/voice/nope")
        self.assertTrue(status.startswith("404"))


if __name__ == "__main__":
    unittest.main()
