"""Phase 2 synthetic-AI linking tests (added 2026-11-13).

Stdlib ``unittest`` only — no pytest, no network beyond a local
127.0.0.1 server, no keys, no spend, no live provider calls. Every
live adapter is exercised through an injected fake (a fake HTTP
``opener``, a fake WebSocket, a fake Claude transport), plus the
honest-failure paths (missing key → ``ValueError``, missing package →
``ImportError``, retired model → ``ValueError``, unconfigured voice
app → 503).

Coverage
--------
* Claude: deprecation warning for claude-sonnet-4-5 (retires
  2026-11-30, replacement claude-sonnet-5-5); stdlib transport against
  a local Messages-API server (request id, latency, audit without
  prompt text); ``build_transport`` auto/stdlib selection and the
  honest SDK-missing error; two distinct Daedalus prompts through
  ``DaedalusRuntimeIntegration`` produce distinct source text/hashes.
* OpenAI: gpt-transcribe via fake opener (model id on the wire,
  whisper-1 rejected); Realtime session minting via fake opener
  (ephemeral key never in the redacted summary); Realtime TTS via a
  fake WebSocket (audio deltas assembled, tts-1 rejected); config
  defaults and deprecation rejection.
* Voice: Deepgram/ElevenLabs missing-key failures; faster-whisper /
  Google / system TTS missing-package failures (skipped when the
  package happens to be installed); ``voice_generate_source`` /
  ``speak_prompt`` through ``generate_source`` with fakes (the spoken
  text is the Daedalus-generated source, not the transcript); the
  Daedalus voice WSGI app (503 unconfigured, 200 with fakes).
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from core_platform.daedalus_claude_transport import (
    DaedalusClaudeTransport,
    DaedalusProviderError,
    DaedalusResponse,
    build_transport,
    claude_model_deprecation_warning,
)
from core_platform.daedalus_config import DaedalusSettings
from core_platform.daedalus_runtime_integration import DaedalusRuntimeIntegration
from core_platform.daedalus_voice import (
    DeepgramTranscriber,
    ElevenLabsSynthesizer,
    FakeSynthesizer,
    FakeTranscriber,
    make_silence_wav,
    speak_prompt,
    voice_generate_source,
)
from core_platform.daedalus_voice_pipeline import OpenAIWhisperTranscriber
from core_platform.openai_link import (
    DEFAULT_REALTIME_MODEL,
    OpenAIGPTTranscribeTranscriber,
    OpenAIRealtimeTTSSpeaker,
    create_realtime_session,
    reject_deprecated_openai_model,
)
from core_platform.voice_api import (
    create_daedalus_voice_app,
    create_voice_app,
    describe_voice_backends,
)

FAKE_KEY = "test-key-not-real"
FAKE_MODEL = "test-model"
SIGNING_KEY = b"k" * 32


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeHTTPResponse:
    """Minimal urllib response: read() + headers mapping."""

    def __init__(self, body: bytes, headers: dict | None = None) -> None:
        self._body = body
        self.headers = headers or {}

    def read(self, *args) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


class FakeOpener:
    """Records requests; returns a canned body per URL path."""

    def __init__(self, bodies: dict[str, bytes]) -> None:
        self.bodies = bodies
        self.requests: list[dict] = []

    def __call__(self, request, timeout=None):
        self.requests.append({
            "url": request.full_url,
            "body": request.data or b"",
            "headers": dict(request.header_items()),
        })
        key = next((k for k in self.bodies if request.full_url.endswith(k)), None)
        body = self.bodies.get(key or "", b"{}")
        return FakeHTTPResponse(body, {"request-id": "req_fake_123"})


class FakeClaudeTransport:
    """Echo transport: generated text names the objective, so two
    distinct prompts produce distinct source text and hashes."""

    def generate(self, *, system, user_message, max_tokens=2048, metadata=None):
        objective = user_message.split("Objective:\n", 1)[-1]
        return DaedalusResponse(
            model=FAKE_MODEL,
            request_id="req_fake_1",
            message_id="msg_fake_1",
            text=f"# generated for: {objective}",
            latency_ms=7,
            input_tokens=10,
            output_tokens=12,
        )


class FakeWebSocket:
    """Feeds canned Realtime events; records what was sent."""

    def __init__(self, events: list[dict]) -> None:
        self._events = [json.dumps(e) for e in events]
        self.sent: list[str] = []

    def send(self, message: str) -> None:
        self.sent.append(message)

    def recv(self) -> str:
        if not self._events:
            raise AssertionError("fake websocket ran out of events")
        return self._events.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


def _wsgi_call(app, method, path, body=b"", headers=None):
    """Minimal WSGI invocation; returns (status, headers, body)."""
    import io

    captured: dict = {}

    def start(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    for key, value in (headers or {}).items():
        env["HTTP_" + key.upper().replace("-", "_")] = value
    chunks = app(env, start)
    return captured["status"], captured["headers"], b"".join(chunks)


def _fake_runtime():
    return DaedalusRuntimeIntegration(
        transport=FakeClaudeTransport(),
        signing_key=SIGNING_KEY,
        persist_private_evidence=lambda record, sig: None,
    )


# ---------------------------------------------------------------------------
# Claude / Daedalus
# ---------------------------------------------------------------------------


class TestClaudeDeprecation(unittest.TestCase):
    def test_sonnet_45_warns_with_replacement_and_date(self):
        for model in ("claude-sonnet-4-5", "claude-sonnet-4-5-20250929"):
            warning = claude_model_deprecation_warning(model)
            self.assertIsNotNone(warning)
            assert warning is not None
            self.assertIn("2026-11-30", warning)
            self.assertIn("claude-sonnet-5-5", warning)

    def test_unknown_model_has_no_warning(self):
        self.assertIsNone(claude_model_deprecation_warning("claude-sonnet-5-5"))
        self.assertIsNone(claude_model_deprecation_warning(""))

    def test_build_transport_requires_model_and_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                build_transport(backend="stdlib")
            with self.assertRaises(ValueError):
                build_transport(backend="stdlib", model=FAKE_MODEL)

    def test_build_transport_stdlib_without_sdk(self):
        settings = DaedalusSettings(
            anthropic_api_key=FAKE_KEY, claude_model=FAKE_MODEL)
        transport = build_transport(settings=settings, backend="stdlib")
        self.assertIsInstance(transport, DaedalusClaudeTransport)
        self.assertEqual(transport.BACKEND, "stdlib")

    def test_build_transport_sdk_missing_is_honest(self):
        if importlib.util.find_spec("anthropic") is not None:
            self.skipTest("anthropic SDK is installed in this environment")
        settings = DaedalusSettings(
            anthropic_api_key=FAKE_KEY, claude_model=FAKE_MODEL)
        with self.assertRaises(DaedalusProviderError):
            build_transport(settings=settings, backend="sdk")


class _ClaudeHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []
    body_to_return = b"{}"

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler name
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        type(self).requests.append({
            "path": self.path,
            "body": body,
            "headers": dict(self.headers),
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("request-id", "req_local_456")
        self.send_header("Content-Length", str(len(type(self).body_to_return)))
        self.end_headers()
        self.wfile.write(type(self).body_to_return)

    def log_message(self, *args):
        pass


class TestClaudeStdlibLocalServer(unittest.TestCase):
    def setUp(self):
        _ClaudeHandler.requests = []
        _ClaudeHandler.body_to_return = json.dumps({
            "type": "message",
            "id": "msg_local_1",
            "model": FAKE_MODEL,
            "content": [{"type": "text", "text": "def hello():\n    return 1\n"}],
            "usage": {"input_tokens": 11, "output_tokens": 9},
        }).encode()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ClaudeHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_generate_round_trip_and_audit(self):
        transport = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        transport.ENDPOINT = self.base + "/v1/messages"
        seen: list[dict] = []
        transport.audit = seen.append
        out = transport.generate(
            system="You are DAEDALUS.", user_message="write hello", max_tokens=64)
        self.assertEqual(out.text, "def hello():\n    return 1\n")
        self.assertEqual(out.request_id, "req_local_456")
        self.assertEqual(out.message_id, "msg_local_1")
        self.assertEqual((out.input_tokens, out.output_tokens), (11, 9))
        self.assertIsInstance(out.latency_ms, int)
        request = _ClaudeHandler.requests[0]
        payload = json.loads(request["body"])
        self.assertEqual(payload["model"], FAKE_MODEL)
        self.assertEqual(request["headers"].get("Anthropic-Version"), "2026-10-21")
        self.assertNotIn(FAKE_KEY, json.dumps(seen))
        self.assertEqual(seen[0]["model"], FAKE_MODEL)
        self.assertNotIn("write hello", json.dumps(seen))

    def test_two_distinct_prompts_give_distinct_source(self):
        runtime = _fake_runtime()
        first = runtime.generate_source(
            invention_id="inv-1", objective="a hello function",
            language="Python", inventor_assertions=())
        second = runtime.generate_source(
            invention_id="inv-1", objective="a goodbye function",
            language="Python", inventor_assertions=())
        self.assertNotEqual(first.source_sha256, second.source_sha256)
        self.assertIn("hello", first.response.text)
        self.assertIn("goodbye", second.response.text)
        self.assertEqual(
            first.source_sha256,
            hashlib.sha256(first.response.text.encode()).hexdigest(),
        )

    def test_short_signing_key_rejected(self):
        with self.assertRaises(ValueError):
            DaedalusRuntimeIntegration(
                transport=FakeClaudeTransport(),
                signing_key=b"short",
                persist_private_evidence=lambda r, s: None,
            )


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class TestOpenAIDeprecations(unittest.TestCase):
    def test_reject_whisper1_and_tts1(self):
        for model in ("whisper-1", "tts-1", "tts-1-hd",
                      "gpt-4o-transcribe", "gpt-4o-mini-tts",
                      "gpt-4o-realtime", "gpt-realtime"):
            with self.assertRaises(ValueError, msg=model):
                reject_deprecated_openai_model(model)

    def test_current_models_not_rejected(self):
        reject_deprecated_openai_model("gpt-transcribe")
        reject_deprecated_openai_model("gpt-realtime-2.1-mini")
        reject_deprecated_openai_model("gpt-live-transcribe")

    def test_gpt_transcribe_via_fake_opener(self):
        opener = FakeOpener({"/audio/transcriptions": json.dumps(
            {"text": "hello from audio"}).encode()})
        transcriber = OpenAIGPTTranscribeTranscriber(
            api_key=FAKE_KEY, opener=opener)
        self.assertEqual(transcriber.model, "gpt-transcribe")
        self.assertEqual(transcriber.transcribe(b"\x00\x01audio"), "hello from audio")
        request = opener.requests[0]
        self.assertTrue(request["url"].endswith("/audio/transcriptions"))
        self.assertIn(b"gpt-transcribe", request["body"])
        self.assertNotIn(b"whisper-1", request["body"])
        self.assertIn(b"\x00\x01audio", request["body"])
        self.assertNotIn(FAKE_KEY.encode(), request["body"])

    def test_gpt_transcribe_rejects_whisper1_and_missing_key(self):
        with self.assertRaises(ValueError):
            OpenAIGPTTranscribeTranscriber(api_key=FAKE_KEY, model="whisper-1")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                OpenAIGPTTranscribeTranscriber()

    def test_pipeline_whisper_adapter_now_defaults_to_gpt_transcribe(self):
        transcriber = OpenAIWhisperTranscriber(api_key=FAKE_KEY)
        self.assertEqual(transcriber.model, "gpt-transcribe")
        self.assertEqual(transcriber.PROVIDER, "openai-gpt-transcribe")
        with self.assertRaises(ValueError):
            OpenAIWhisperTranscriber(api_key=FAKE_KEY, model="whisper-1")

    def test_realtime_session_minting_via_fake_opener(self):
        opener = FakeOpener({"/realtime/sessions": json.dumps({
            "id": "sess_123",
            "client_secret": {"value": "ek_fake_secret"},
            "expires_at": 1790000000,
        }).encode()})
        session = create_realtime_session(
            api_key=FAKE_KEY, model=DEFAULT_REALTIME_MODEL,
            voice="alloy", opener=opener)
        self.assertEqual(session.session_id, "sess_123")
        self.assertEqual(session.model, DEFAULT_REALTIME_MODEL)
        self.assertEqual(session.ephemeral_key, "ek_fake_secret")
        self.assertNotIn("ek_fake_secret", json.dumps(session.redacted()))
        self.assertTrue(session.redacted()["ephemeral_key_present"])
        request = json.loads(opener.requests[0]["body"])
        self.assertEqual(request["model"], DEFAULT_REALTIME_MODEL)
        self.assertEqual(request["voice"], "alloy")

    def test_realtime_session_rejects_retired_model_and_missing_key(self):
        with self.assertRaises(ValueError):
            create_realtime_session(api_key=FAKE_KEY, model="gpt-4o-realtime")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                create_realtime_session(model=DEFAULT_REALTIME_MODEL)

    def test_realtime_tts_via_fake_websocket(self):
        pcm = b"\x00\x01\x00\x02"
        ws = FakeWebSocket([
            {"type": "response.audio.delta",
             "delta": base64.b64encode(pcm).decode("ascii")},
            {"type": "response.done"},
        ])
        factory_calls: list[dict] = []

        def factory(url, headers):
            factory_calls.append({"url": url, "headers": headers})
            return ws

        speaker = OpenAIRealtimeTTSSpeaker(
            api_key=FAKE_KEY, model=DEFAULT_REALTIME_MODEL,
            voice="alloy", ws_factory=factory)
        out = speaker.speak("hello world")
        self.assertEqual(out.audio, pcm)
        self.assertEqual(out.provider, "openai-realtime")
        self.assertIn("wss://api.openai.com/v1/realtime", factory_calls[0]["url"])
        self.assertIn(DEFAULT_REALTIME_MODEL, factory_calls[0]["url"])
        # The auth header carries the key by design; what must never
        # contain it is the message stream / logs.
        self.assertNotIn(FAKE_KEY, json.dumps(ws.sent))
        sent = [json.loads(m) for m in ws.sent]
        self.assertEqual([m["type"] for m in sent], [
            "session.update", "conversation.item.create", "response.create"])
        self.assertEqual(sent[1]["item"]["content"][0]["text"], "hello world")
        self.assertNotIn("/audio/speech", json.dumps(sent))

    def test_realtime_tts_rejects_tts1_and_empty_text(self):
        with self.assertRaises(ValueError):
            OpenAIRealtimeTTSSpeaker(api_key=FAKE_KEY, model="tts-1")
        speaker = OpenAIRealtimeTTSSpeaker(
            api_key=FAKE_KEY, ws_factory=lambda u, h: FakeWebSocket([]))
        with self.assertRaises(ValueError):
            speaker.speak("   ")


class TestDaedalusSettings(unittest.TestCase):
    def test_defaults_are_current_models(self):
        settings = DaedalusSettings.from_env({})
        self.assertEqual(settings.whisper_model, "gpt-transcribe")
        self.assertEqual(settings.tts_model, "gpt-realtime-2.1-mini")
        self.assertEqual(settings.realtime_model, "gpt-realtime-2.1-mini")
        self.assertFalse(settings.is_live_reasoning_configured)

    def test_deprecated_models_rejected_from_env(self):
        for env in (
            {"DAEDALUS_WHISPER_MODEL": "whisper-1"},
            {"DAEDALUS_TTS_MODEL": "tts-1"},
            {"DAEDALUS_TTS_MODEL": "tts-1-hd"},
            {"OPENAI_REALTIME_MODEL": "gpt-4o-realtime"},
        ):
            with self.assertRaises(ValueError, msg=str(env)):
                DaedalusSettings.from_env(env)

    def test_redacted_summary_never_contains_keys(self):
        settings = DaedalusSettings(
            anthropic_api_key=FAKE_KEY, claude_model=FAKE_MODEL,
            openai_api_key=FAKE_KEY)
        summary = json.dumps(settings.redacted_summary())
        self.assertNotIn(FAKE_KEY, summary)
        self.assertTrue(settings.redacted_summary()["anthropic_api_key_present"])


# ---------------------------------------------------------------------------
# Voice providers: honest failure + Daedalus voice turn + WSGI
# ---------------------------------------------------------------------------


class TestVoiceHonestFailure(unittest.TestCase):
    def test_deepgram_and_elevenlabs_require_keys(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                DeepgramTranscriber()
            with self.assertRaises(ValueError):
                ElevenLabsSynthesizer()

    def test_missing_packages_raise_import_error(self):
        # Only the import is probed here: constructing the adapter when
        # its package IS installed would download a model (faster-whisper)
        # or build a client, which this offline test must not do.
        for package in ("faster_whisper", "google.cloud.texttospeech", "pyttsx3"):
            try:
                spec = importlib.util.find_spec(package)
            except (ImportError, ModuleNotFoundError, ValueError):
                spec = None  # parent package missing == package missing
            if spec is None:
                with self.assertRaises(ImportError, msg=package):
                    __import__(package)
            else:
                self.skipTest(f"{package} is installed in this environment")

    def test_describe_backends_reports_without_secrets(self):
        report = describe_voice_backends()
        self.assertIn("faster-whisper", report)
        self.assertIn("openai-gpt-transcribe", report)
        self.assertIn("openai-realtime-tts", report)
        self.assertNotIn(FAKE_KEY, json.dumps(report))


class TestVoiceGenerateSource(unittest.TestCase):
    def test_turn_speaks_generated_source_not_transcript(self):
        audio = make_silence_wav(0.5)
        speaker = FakeSynthesizer()
        result = voice_generate_source(
            transcriber=FakeTranscriber("generate a python hello world function"),
            integration=_fake_runtime(),
            synthesizer=speaker,
            audio_bytes=audio,
            invention_id="inv-voice-1",
        )
        self.assertEqual(result["transcript"], "generate a python hello world function")
        self.assertIn("hello world", result["source_text"])
        self.assertEqual(result["source_sha256"],
                         hashlib.sha256(result["source_text"].encode()).hexdigest())
        # The synthesizer received the Daedalus-generated source text.
        self.assertEqual(speaker.calls, [result["source_text"]])
        self.assertTrue(result["audio_bytes"])

    def test_speak_prompt_alias_is_the_same_turn(self):
        result = speak_prompt(
            transcriber=FakeTranscriber("generate a python hello world function"),
            integration=_fake_runtime(),
            synthesizer=FakeSynthesizer(),
            audio_bytes=make_silence_wav(0.5),
            invention_id="inv-voice-2",
        )
        self.assertIn("hello world", result["source_text"])


class TestDaedalusVoiceApp(unittest.TestCase):
    def test_unconfigured_turn_app_answers_503(self):
        app = create_daedalus_voice_app()
        status, _headers, body = _wsgi_call(
            app, "POST", "/api/voice/turn", make_silence_wav(0.5),
            {"X-Invention-Id": "inv-1"})
        self.assertTrue(status.startswith("503"))
        self.assertIn("daedalus_runtime_not_configured", body.decode())
        status, _headers, body = _wsgi_call(app, "GET", "/api/voice/daedalus/status")
        self.assertTrue(status.startswith("200"))
        self.assertFalse(json.loads(body)["live_turn_possible"])

    def test_turn_app_with_fakes_answers_200(self):
        app = create_daedalus_voice_app(
            runtime=_fake_runtime(),
            transcriber=FakeTranscriber("generate a python hello world function"),
            synthesizer=FakeSynthesizer(),
        )
        status, _headers, body = _wsgi_call(
            app, "POST", "/api/voice/turn", make_silence_wav(0.5),
            {"X-Invention-Id": "inv-9"})
        self.assertTrue(status.startswith("200"), body[:200])
        payload = json.loads(body)
        self.assertEqual(payload["invention_id"], "inv-9")
        self.assertIn("hello world", payload["source_text"])
        self.assertTrue(base64.b64decode(payload["audio_base64"]))
        status, _headers, body = _wsgi_call(app, "GET", "/api/voice/daedalus/status")
        self.assertTrue(json.loads(body)["live_turn_possible"])

    def test_turn_app_requires_invention_id(self):
        app = create_daedalus_voice_app(
            runtime=_fake_runtime(),
            transcriber=FakeTranscriber("generate a python hello world function"),
            synthesizer=FakeSynthesizer(),
        )
        status, _headers, body = _wsgi_call(
            app, "POST", "/api/voice/turn", make_silence_wav(0.5))
        self.assertTrue(status.startswith("400"))

    def test_plain_voice_app_still_503_when_unconfigured(self):
        app = create_voice_app()
        status, _headers, body = _wsgi_call(
            app, "POST", "/api/voice/transcribe", make_silence_wav(0.5))
        self.assertTrue(status.startswith("503"))
        status, _headers, body = _wsgi_call(
            app, "POST", "/api/voice/speak", json.dumps({"text": "hi"}).encode())
        self.assertTrue(status.startswith("503"))


if __name__ == "__main__":
    unittest.main()
