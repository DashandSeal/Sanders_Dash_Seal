"""Daedalus SOTA tests (added 2026-11-13).

Stdlib ``unittest`` only — no pytest, no network, no keys, no spend.
Live-provider behaviour is verified against fakes and a local HTTP
server on 127.0.0.1; the Anthropic SDK tests run only when the
``anthropic`` package (and its ``httpx2`` transport) is installed,
and use an ``httpx2.MockTransport`` that returns canned Messages API
JSON — they never reach api.anthropic.com.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import importlib.util
import json
import os
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import core_platform
from core_platform.daedalus_claude_transport import (
    AsyncDaedalusClaudeTransport,
    DaedalusClaudeSDKTransport,
    DaedalusClaudeTransport,
    DaedalusProviderError,
    DaedalusResponse,
    build_transport,
)
from core_platform.daedalus_config import DaedalusSettings
from core_platform.daedalus_continuity import bridge_by_source
from core_platform.daedalus_engine import (
    DaedalusEngineConfig,
    VoiceTurnRunner,
    build_engine,
    build_voice_runner,
)
from core_platform.daedalus_geofence import (
    GeoFence,
    GeoFenceDenied,
    GeographicPolicy,
    LocationAttestation,
)
from core_platform.daedalus_global_trust import (
    GlobalTrustContext,
    GlobalTrustEnforcer,
    GlobalTrustPolicy,
)
from core_platform.daedalus_ip_protection import (
    InventionRecord,
    sign_evidence,
    verify_evidence,
)
from core_platform.daedalus_l15_capabilities import (
    CapabilityState,
    declared_profile,
    observed_profile,
)
from core_platform.daedalus_portfolio_ip_pricing import RateCard
from core_platform.daedalus_runtime_integration import DaedalusRuntimeIntegration
from core_platform.daedalus_voice_pipeline import (
    ElevenLabsSpeaker,
    FakeSpeaker,
    FakeTranscriber,
    OpenAITTSSpeaker,
    OpenAIWhisperTranscriber,
    _encode_multipart,
    run_voice_turn,
)

HAS_SDK = importlib.util.find_spec("anthropic") is not None and (
    importlib.util.find_spec("httpx2") is not None
)

FAKE_KEY = "test-key-not-real"
FAKE_MODEL = "test-model"
SIGNING_KEY = b"k" * 32

CANNED_MESSAGE = {
    "id": "msg_01Test",
    "type": "message",
    "role": "assistant",
    "model": FAKE_MODEL,
    "content": [{"type": "text", "text": "print('hello')"}],
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 12, "output_tokens": 5},
}


class FakeTransport:
    """Stdlib-shaped fake Claude transport for runtime/engine tests."""

    def __init__(self, text: str = "print('hello')") -> None:
        self.text = text
        self.calls: list[dict] = []

    def generate(self, *, system, user_message, max_tokens=2048, metadata=None):
        self.calls.append({"system": system, "user_message": user_message})
        return DaedalusResponse(
            model=FAKE_MODEL, request_id="req_fake", message_id="msg_fake",
            text=self.text, latency_ms=1, input_tokens=3, output_tokens=4,
        )


class FakeAsyncTransport(FakeTransport):
    async def agenerate(self, *, system, user_message, max_tokens=2048, metadata=None):
        return self.generate(
            system=system, user_message=user_message,
            max_tokens=max_tokens, metadata=metadata,
        )


class FakeGenerator:
    def __init__(self, reply: str = "spoken reply") -> None:
        self.reply = reply

    def generate_text(self, prompt: str) -> str:
        return self.reply


class FakeHTTPResponse:
    def __init__(self, body: bytes, headers=None):
        self._body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size=-1):
        return self._body if size in (-1, None) else self._body[:size]


def make_settings(**overrides):
    values = {
        "anthropic_api_key": FAKE_KEY,
        "claude_model": FAKE_MODEL,
    }
    values.update(overrides)
    return DaedalusSettings(**values)


_PROXY_VARS = (
    "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
    "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
)


class _clear_proxy_env:
    """SDK clients build their HTTP client from proxy env vars.

    The sandbox sets proxy vars the SDK's URL parser rejects, which
    would fail client construction before any request is made. Tests
    remove them so the MockTransport path is exercised; production
    construction failure is covered by the typed error instead.
    """

    def __enter__(self):
        self._saved = {k: os.environ.pop(k) for k in _PROXY_VARS if k in os.environ}
        return self

    def __exit__(self, *exc):
        os.environ.update(self._saved)
        return False


# ---------------------------------------------------------------- config

class TestConfig(unittest.TestCase):
    def test_from_env_mapping(self):
        settings = DaedalusSettings.from_env({
            "ANTHROPIC_API_KEY": FAKE_KEY,
            "DAEDALUS_CLAUDE_MODEL": FAKE_MODEL,
            "DAEDALUS_TRANSPORT_BACKEND": "stdlib",
            "DAEDALUS_TIMEOUT_SECONDS": "30",
            "DAEDALUS_MAX_TOKENS": "512",
        })
        self.assertTrue(settings.is_live_reasoning_configured)
        self.assertEqual(settings.transport_backend, "stdlib")
        self.assertEqual(settings.timeout_seconds, 30.0)
        self.assertEqual(settings.max_tokens, 512)

    def test_from_env_empty_is_not_configured(self):
        settings = DaedalusSettings.from_env({})
        self.assertFalse(settings.is_live_reasoning_configured)
        with self.assertRaises(ValueError):
            settings.require_live_reasoning()

    def test_require_live_reasoning_raises_without_key_or_model(self):
        with self.assertRaises(ValueError):
            DaedalusSettings().require_live_reasoning()
        with self.assertRaises(ValueError):
            DaedalusSettings(claude_model=FAKE_MODEL).require_live_reasoning()
        with self.assertRaises(ValueError):
            DaedalusSettings(anthropic_api_key=FAKE_KEY).require_live_reasoning()

    def test_redacted_summary_never_contains_key(self):
        summary = make_settings().redacted_summary()
        self.assertNotIn(FAKE_KEY, json.dumps(summary))
        self.assertTrue(summary["anthropic_api_key_present"])

    def test_invalid_timeout_and_backend_raise(self):
        with self.assertRaises(ValueError):
            DaedalusSettings(timeout_seconds=0)
        with self.assertRaises(ValueError):
            DaedalusSettings(timeout_seconds=float("inf"))
        with self.assertRaises(ValueError):
            DaedalusSettings.from_env({"DAEDALUS_TRANSPORT_BACKEND": "bogus"})
        with self.assertRaises(ValueError):
            DaedalusSettings.from_env({"DAEDALUS_TIMEOUT_SECONDS": "soon"})


# ------------------------------------------------------- stdlib transport

class TestStdlibTransport(unittest.TestCase):
    def test_missing_key_or_model_raises(self):
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport(model=FAKE_MODEL)
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport(api_key=FAKE_KEY)
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY, timeout_seconds=-1)

    def test_empty_messages_raise(self):
        transport = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        with self.assertRaises(ValueError):
            transport.generate(system=" ", user_message="hi")
        with self.assertRaises(ValueError):
            transport.generate(system="sys", user_message="hi", max_tokens=0)

    def test_success_parses_canned_response_and_audits_without_prompt(self):
        body = json.dumps(CANNED_MESSAGE).encode()
        seen_requests = []
        audits = []

        def fake_urlopen(request, timeout=None, context=None):
            seen_requests.append(request)
            return FakeHTTPResponse(body, {"request-id": "req_test123"})

        transport = DaedalusClaudeTransport(
            model=FAKE_MODEL, api_key=FAKE_KEY, audit=audits.append
        )
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            response = transport.generate(system="sys", user_message="hi")
        self.assertEqual(response.text, "print('hello')")
        self.assertEqual(response.model, FAKE_MODEL)
        self.assertEqual(response.message_id, "msg_01Test")
        self.assertEqual(response.request_id, "req_test123")
        self.assertEqual((response.input_tokens, response.output_tokens), (12, 5))
        self.assertEqual(seen_requests[0].get_header("Anthropic-version"), "2026-10-21")
        self.assertEqual(len(audits), 1)
        self.assertNotIn("hi", json.dumps(audits[0]))

    def test_http_error_hides_body(self):
        def fake_urlopen(request, timeout=None, context=None):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", {}, None
            )

        transport = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(DaedalusProviderError) as caught:
                transport.generate(system="sys", user_message="hi")
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("Unauthorized body", str(caught.exception))

    def test_oversize_response_rejected(self):
        def fake_urlopen(request, timeout=None, context=None):
            return FakeHTTPResponse(b"x" * (8 * 1024 * 1024 + 2))

        transport = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(DaedalusProviderError):
                transport.generate(system="sys", user_message="hi")


class TestStdlibAsync(unittest.IsolatedAsyncioTestCase):
    async def test_agenerate_runs_off_loop(self):
        body = json.dumps(CANNED_MESSAGE).encode()

        def fake_urlopen(request, timeout=None, context=None):
            return FakeHTTPResponse(body, {"request-id": "req_async"})

        transport = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            response = await transport.agenerate(system="sys", user_message="hi")
        self.assertEqual(response.text, "print('hello')")


# ---------------------------------------------------------- SDK transport

@unittest.skipUnless(HAS_SDK, "anthropic SDK / httpx2 not installed")
class TestSDKTransport(unittest.TestCase):
    def _mock_client(self, handler):
        import anthropic
        import httpx2

        return anthropic.Anthropic(
            api_key=FAKE_KEY,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        )

    def test_sdk_success_via_mock_transport(self):
        import httpx2

        def handler(request):
            return httpx2.Response(200, json=CANNED_MESSAGE)

        with _clear_proxy_env():
            transport = DaedalusClaudeSDKTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        transport._client = self._mock_client(handler)
        response = transport.generate(system="sys", user_message="hi")
        self.assertEqual(response.text, "print('hello')")
        self.assertEqual((response.input_tokens, response.output_tokens), (12, 5))
        self.assertIsNone(response.request_id)  # SDK does not expose it; not invented
        transport.close()

    def test_sdk_auth_error_mapped_without_body(self):
        import httpx2

        def handler(request):
            return httpx2.Response(
                401,
                json={"type": "error", "error": {"type": "authentication_error",
                                                 "message": "secret-detail-must-not-leak"}},
            )

        with _clear_proxy_env():
            transport = DaedalusClaudeSDKTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        transport._client = self._mock_client(handler)
        with self.assertRaises(DaedalusProviderError) as caught:
            transport.generate(system="sys", user_message="hi")
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("secret-detail-must-not-leak", str(caught.exception))
        transport.close()

    def test_factory_auto_prefers_sdk_when_installed(self):
        with _clear_proxy_env():
            transport = build_transport(settings=make_settings(), backend="auto")
        self.assertIsInstance(transport, DaedalusClaudeSDKTransport)
        transport.close()

    def test_factory_stdlib_and_unknown_backend(self):
        transport = build_transport(settings=make_settings(), backend="stdlib")
        self.assertIsInstance(transport, DaedalusClaudeTransport)
        with self.assertRaises(ValueError):
            build_transport(settings=make_settings(), backend="bogus")


@unittest.skipUnless(HAS_SDK, "anthropic SDK / httpx2 not installed")
class TestAsyncSDKTransport(unittest.IsolatedAsyncioTestCase):
    async def test_async_agenerate_via_mock_transport(self):
        import anthropic
        import httpx2

        def handler(request):
            return httpx2.Response(200, json=CANNED_MESSAGE)

        with _clear_proxy_env():
            transport = AsyncDaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        transport._client = anthropic.AsyncAnthropic(
            api_key=FAKE_KEY,
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        )
        response = await transport.agenerate(system="sys", user_message="hi")
        self.assertEqual(response.text, "print('hello')")
        self.assertEqual(response.message_id, "msg_01Test")
        await transport.aclose()

    async def test_async_transport_rejects_sync_generate(self):
        with _clear_proxy_env():
            transport = AsyncDaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY)
        with self.assertRaises(TypeError):
            transport.generate(system="sys", user_message="hi")
        await transport.aclose()


# ------------------------------------------------------------- local server

class _CaptureHandler(BaseHTTPRequestHandler):
    requests: list = []
    body_to_return: bytes = b"{}"
    content_type: str = "application/json"
    status: int = 200

    def do_POST(self):  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length") or 0)
        payload = self.rfile.read(length)
        type(self).requests.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": payload,
        })
        self.send_response(type(self).status)
        self.send_header("Content-Type", type(self).content_type)
        self.send_header("Content-Length", str(len(type(self).body_to_return)))
        self.end_headers()
        self.wfile.write(type(self).body_to_return)

    def log_message(self, *args):  # silence test server logging
        pass


class LocalServerCase(unittest.TestCase):
    def setUp(self):
        _CaptureHandler.requests = []
        _CaptureHandler.status = 200
        _CaptureHandler.content_type = "application/json"
        _CaptureHandler.body_to_return = b"{}"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()


class TestVoiceAdapters(LocalServerCase):
    def test_multipart_encoder_shape(self):
        body, content_type = _encode_multipart(
            {"model": "gpt-transcribe"},
            file_field="file", filename="a.webm",
            file_bytes=b"FAKEBYTES", file_mime_type="audio/webm",
            boundary="----TestBoundary",
        )
        self.assertIn(b"gpt-transcribe", body)
        self.assertIn(b"FAKEBYTES", body)
        self.assertIn(b'filename="a.webm"', body)
        self.assertIn("boundary=----TestBoundary", content_type)

    def test_whisper_against_local_server(self):
        _CaptureHandler.body_to_return = json.dumps({"text": "hello world"}).encode()
        transcriber = OpenAIWhisperTranscriber(
            api_key=FAKE_KEY, base_url=self.base
        )
        result = transcriber.transcribe(b"\x00\x01audio-bytes", language="en")
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.provider, "openai-gpt-transcribe")
        request = _CaptureHandler.requests[0]
        self.assertEqual(request["path"], "/audio/transcriptions")
        self.assertIn(b"gpt-transcribe", request["body"])
        self.assertIn(b"\x00\x01audio-bytes", request["body"])
        self.assertTrue(request["headers"]["Content-Type"].startswith("multipart/form-data"))

    def test_whisper1_is_rejected(self):
        with self.assertRaises(ValueError):
            OpenAIWhisperTranscriber(api_key="test-key-not-real", model="whisper-1",
                                     base_url=self.base)

    def test_whisper_missing_key_and_oversize(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                OpenAIWhisperTranscriber(api_key=None, base_url=self.base)
            with self.assertRaises(ValueError):
                OpenAIWhisperTranscriber(base_url=self.base)
        transcriber = OpenAIWhisperTranscriber(api_key=FAKE_KEY, base_url=self.base)
        with self.assertRaises(ValueError):
            transcriber.transcribe(b"x" * (25 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            transcriber.transcribe(b"")

    def test_openai_audio_speech_tts_is_retired(self):
        # tts-1/tts-1-hd shut down 2027-01-06; the replacement runs only
        # on the Realtime API (openai_link.OpenAIRealtimeTTSSpeaker).
        with self.assertRaises(ValueError) as ctx:
            OpenAITTSSpeaker(api_key="test-key-not-real", base_url=self.base)
        self.assertIn("Realtime", str(ctx.exception))

    def test_elevenlabs_against_local_server(self):
        _CaptureHandler.body_to_return = b"FAKE-ELEVEN-AUDIO"
        _CaptureHandler.content_type = "audio/mpeg"
        speaker = ElevenLabsSpeaker(
            api_key="el-fake", voice_id="voice_123", base_url=f"{self.base}/v1"
        )
        result = speaker.speak("hello there")
        self.assertEqual(result.audio, b"FAKE-ELEVEN-AUDIO")
        self.assertEqual(result.voice, "voice_123")
        request = _CaptureHandler.requests[0]
        self.assertTrue(request["path"].endswith("/text-to-speech/voice_123"))
        self.assertIn("Xi-Api-Key", request["headers"])
        self.assertEqual(json.loads(request["body"])["text"], "hello there")

    def test_elevenlabs_missing_voice_or_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ElevenLabsSpeaker(api_key="el-fake", voice_id=None, base_url=self.base)
            with self.assertRaises(ValueError):
                ElevenLabsSpeaker(voice_id="voice_123", base_url=self.base)


class TestVoicePipeline(unittest.TestCase):
    def test_fake_pipeline_end_to_end(self):
        turn = run_voice_turn(
            audio=b"fake-audio-bytes",
            transcriber=FakeTranscriber("write hello"),
            generator=FakeGenerator("spoken reply"),
            speaker=FakeSpeaker(),
        )
        self.assertEqual(turn.transcript, "write hello")
        self.assertEqual(turn.response_text, "spoken reply")
        self.assertTrue(turn.audio.audio.startswith(b"FAKE-AUDIO:"))
        self.assertEqual(turn.audio.mime_type, "application/x-daedalus-fake-audio")
        self.assertGreaterEqual(turn.latency_ms, 0)

    def test_voice_turn_rejects_empty_transcript_and_generation(self):
        with self.assertRaises(ValueError):
            run_voice_turn(
                audio=b"", transcriber=FakeTranscriber("x"),
                generator=FakeGenerator(), speaker=FakeSpeaker(),
            )
        with self.assertRaises(ValueError):
            run_voice_turn(
                audio=b"audio", transcriber=FakeTranscriber("x"),
                generator=FakeGenerator("   "), speaker=FakeSpeaker(),
            )


# ------------------------------------------------------- runtime + engine

class TestRuntimeWithFakeTransport(unittest.TestCase):
    def test_generate_source_signs_and_persists(self):
        persisted = []
        runtime = DaedalusRuntimeIntegration(
            transport=FakeTransport("print('hello')"),
            signing_key=SIGNING_KEY,
            persist_private_evidence=lambda record, sig: persisted.append((record, sig)),
        )
        result = runtime.generate_source(
            invention_id="inv-1", objective="say hello",
            language="Python", inventor_assertions=(),
        )
        self.assertEqual(result.response.text, "print('hello')")
        self.assertEqual(
            result.source_sha256,
            hashlib.sha256(b"print('hello')").hexdigest(),
        )
        self.assertEqual(len(persisted), 1)
        self.assertTrue(verify_evidence(persisted[0][0], SIGNING_KEY, persisted[0][1]))

    def test_runtime_rejects_non_transport(self):
        with self.assertRaises(TypeError):
            DaedalusRuntimeIntegration(
                transport=object(), signing_key=SIGNING_KEY,
                persist_private_evidence=lambda r, s: None,
            )


class TestRuntimeAsync(unittest.IsolatedAsyncioTestCase):
    async def test_agenerate_source_with_async_fake(self):
        persisted = []
        runtime = DaedalusRuntimeIntegration(
            transport=FakeAsyncTransport("print('async')"),
            signing_key=SIGNING_KEY,
            persist_private_evidence=lambda record, sig: persisted.append(record),
        )
        result = await runtime.agenerate_source(
            invention_id="inv-2", objective="say hello",
            language="Python", inventor_assertions=(),
        )
        self.assertEqual(result.response.text, "print('async')")
        self.assertEqual(len(persisted), 1)


class TestEngineVoiceWiring(unittest.TestCase):
    def _config(self, **overrides):
        values = {
            "signing_key": SIGNING_KEY,
            "persist_private_evidence": lambda r, s: None,
            "persist_confidential": lambda *a: None,
            "audit": lambda event: None,
            "model": FAKE_MODEL,
            "api_key": FAKE_KEY,
            "transport_backend": "stdlib",
        }
        values.update(overrides)
        return DaedalusEngineConfig(**values)

    def test_build_engine_without_key_or_model_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                build_engine(self._config(model=None, api_key=None))

    def test_build_engine_succeeds_with_stdlib_backend(self):
        engine = build_engine(self._config())
        self.assertEqual(engine.IDENTITY, "DAEDALUS")

    def test_voice_turn_runner_end_to_end_with_fakes(self):
        runtime = DaedalusRuntimeIntegration(
            transport=FakeTransport("print('spoken')"),
            signing_key=SIGNING_KEY,
            persist_private_evidence=lambda r, s: None,
        )
        runner = VoiceTurnRunner(
            runtime=runtime,
            transcriber=FakeTranscriber("write hello"),
            speaker=FakeSpeaker(),
        )
        turn = runner.run(b"audio-bytes", invention_id="inv-voice")
        self.assertEqual(turn.transcript, "write hello")
        self.assertEqual(turn.response_text, "print('spoken')")
        self.assertTrue(turn.audio.audio.startswith(b"FAKE-AUDIO:print('spoken')"))

    def test_build_voice_runner_uses_engine_config(self):
        runner = build_voice_runner(
            self._config(),
            transcriber=FakeTranscriber("write hello"),
            speaker=FakeSpeaker(),
        )
        self.assertIsInstance(runner, VoiceTurnRunner)
        self.assertEqual(runner.language, "Python")


# ------------------------------------------------------- capabilities etc.

class TestCapabilitiesAndPricing(unittest.TestCase):
    def test_declared_profile_all_unavailable(self):
        profile = declared_profile()
        self.assertFalse(profile.fully_active)
        self.assertTrue(all(
            state is CapabilityState.UNAVAILABLE
            for state in profile.capability_states.values()
        ))

    def test_observed_profile_configured_not_active(self):
        profile = observed_profile(live_reasoning_configured=True)
        self.assertEqual(
            profile.capability_states["live_claude_reasoning"],
            CapabilityState.CONFIGURED,
        )
        self.assertFalse(profile.fully_active)
        with self.assertRaises(ValueError):
            observed_profile(nonexistent_capability=CapabilityState.ACTIVE)

    def test_rate_card_default_and_validation(self):
        card = RateCard.default()
        self.assertEqual(str(card.monthly["enterprise_api"]), "100000")
        with self.assertRaises(ValueError):
            RateCard.from_mapping({"monthly": {"bogus_key": "1"}, "annual": {}, "ip_services": {}})
        with self.assertRaises(ValueError):
            RateCard.from_mapping({
                "monthly": {"enterprise_api": "-5"},
                "annual": {"strategic_enterprise_license": "20000000"},
                "ip_services": {},
            })

    def test_bridge_lookup(self):
        bridge = bridge_by_source("COBOL")
        self.assertIsNotNone(bridge)
        self.assertEqual(bridge.destination, "Polyglot Engine LLVM")
        self.assertIsNone(bridge_by_source("NO-SUCH-TECH"))


class TestTrustAndIP(unittest.TestCase):
    def _location(self, **overrides):
        values = {
            "country": "US", "region": "AZ",
            "cloud_region": "us-phoenix-1", "source": "test-attestation",
            "trusted": True,
        }
        values.update(overrides)
        return LocationAttestation(**values)

    def test_geofence_allow_and_deny(self):
        fence = GeoFence(
            policy=GeographicPolicy(
                allowed_countries=frozenset({"US"}),
                allowed_regions=frozenset({"AZ"}),
                allowed_cloud_regions=frozenset({"us-phoenix-1"}),
                policy_version="v1",
            ),
            audit=lambda event: None,
        )
        fence.enforce(action="execution", location=self._location())
        with self.assertRaises(GeoFenceDenied):
            fence.enforce(action="execution", location=self._location(trusted=False))
        with self.assertRaises(GeoFenceDenied):
            fence.enforce(action="execution", location=self._location(cloud_region="eu-west-1"))

    def test_global_trust_denies_unverified_identity(self):
        enforcer = GlobalTrustEnforcer(
            policy=GlobalTrustPolicy(authorized_cloud_regions=frozenset({"us-phoenix-1"})),
            audit=lambda event: None,
        )
        context = GlobalTrustContext(
            subject_id="subject-1", identity_verified=False,
            authorization_granted=True, location=self._location(),
            data_classification="restricted", processing_country="US",
            processing_cloud_region="us-phoenix-1", residency_permitted=True,
        )
        with self.assertRaises(GeoFenceDenied):
            enforcer.enforce(action="ingress", context=context)

    def test_hmac_roundtrip_and_tamper(self):
        record = InventionRecord.from_source(
            invention_id="inv-9", title="t", inventor_assertions=(),
            source=b"print(1)",
        )
        signature = sign_evidence(record, SIGNING_KEY)
        self.assertTrue(verify_evidence(record, SIGNING_KEY, signature))
        self.assertFalse(verify_evidence(record, SIGNING_KEY, "0" * 64))
        self.assertEqual(
            signature,
            hmac_mod.new(SIGNING_KEY, record.canonical_bytes(), "sha256").hexdigest(),
        )


class TestPackageExports(unittest.TestCase):
    def test_lazy_exports_resolve(self):
        self.assertTrue(callable(core_platform.build_engine))
        self.assertIs(core_platform.DaedalusEngineConfig, DaedalusEngineConfig)
        self.assertIn("build_voice_runner", dir(core_platform))
        with self.assertRaises(AttributeError):
            core_platform.no_such_daedalus_name


if __name__ == "__main__":
    unittest.main()
