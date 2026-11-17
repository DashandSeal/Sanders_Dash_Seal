"""Standalone, testable WSGI app for voice endpoints.

Routes
------
* ``GET  /api/voice/status``     -- which transcriber/synthesizer is
  configured (names only; no secrets, no keys in the output).
* ``POST /api/voice/transcribe`` -- uploaded audio bytes in the request
  body (WAV PCM-16; see below) -> ``{"transcript": ...}``.
* ``POST /api/voice/speak``      -- JSON ``{"text": ...}`` -> spoken audio
  bytes (``audio/wav`` for fake/system TTS, ``audio/mpeg`` for Google /
  ElevenLabs).

With no backends configured (the default), transcribe/speak answer
``503 service_unavailable`` with an ``error`` code instead of pretending
to work.  Pass explicit fakes in tests, or use
``create_voice_app_from_env()`` which wires faster-whisper / system TTS
only when their packages are actually installed.

Audio format note: browsers record different codecs
(Chrome/Firefox Opus/WebM, Safari AAC/MP4).  This endpoint accepts WAV
PCM-16 only; non-WAV uploads must be normalised server-side with ffmpeg
first (not bundled here).  ``web/voice.html`` records with MediaRecorder
and uploads the blob as-is, so a WAV-capable recorder or an ffmpeg step
is still needed before a real browser round-trip works end to end.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from .daedalus_voice import (
    FakeSynthesizer,
    FakeTranscriber,
    Synthesizer,
    Transcriber,
    validate_audio_bytes,
)

MAX_TEXT_CHARS = 5000


def _json_response(start, status, payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    start(status, [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [body]


def _audio_response(start, status, audio_bytes, media_type):
    start(status, [
        ("Content-Type", media_type),
        ("Content-Length", str(len(audio_bytes))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [audio_bytes]


def _read_body(env):
    try:
        length = int(env.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return b""
    return env["wsgi.input"].read(length)


def create_voice_app(
    transcriber: Transcriber | None = None,
    synthesizer: Synthesizer | None = None,
) -> Callable:
    """Build the voice WSGI app with the given (possibly None) backends."""

    def application(env, start):
        method = env.get("REQUEST_METHOD", "")
        path = env.get("PATH_INFO", "")

        if path == "/api/voice/status" and method in ("GET", "HEAD"):
            payload = {
                "transcriber": transcriber.name if transcriber else None,
                "synthesizer": synthesizer.name if synthesizer else None,
                "synthesizer_audio_format": synthesizer.audio_format if synthesizer else None,
                "audio": "wav_pcm16",
                "video": "webrtc_signalling_only",
                "live_calls": False,
                "notes": (
                    "No live provider call is made by this app. "
                    "Configure a provider adapter (Deepgram/OpenAI/Google/ElevenLabs) "
                    "with its provider credential to enable live transcription/synthesis."
                ),
            }
            if method == "HEAD":
                start("200 OK", [("Content-Type", "application/json"), ("Content-Length", "0")])
                return [b""]
            return _json_response(start, "200 OK", payload)

        if path == "/api/voice/transcribe" and method == "POST":
            if transcriber is None:
                return _json_response(start, "503 Service Unavailable",
                                      {"error": "transcriber_not_configured"})
            audio = _read_body(env)
            try:
                validate_audio_bytes(audio)
            except ValueError as exc:
                return _json_response(start, "400 Bad Request", {"error": str(exc)})
            try:
                transcript = transcriber.transcribe(
                    audio, filename="audio.wav")
            except (ValueError, ImportError, RuntimeError) as exc:
                return _json_response(start, "502 Bad Gateway",
                                      {"error": f"transcription_failed: {exc}"})
            return _json_response(start, "200 OK", {"transcript": transcript})

        if path == "/api/voice/speak" and method == "POST":
            if synthesizer is None:
                return _json_response(start, "503 Service Unavailable",
                                      {"error": "synthesizer_not_configured"})
            raw = _read_body(env)
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (ValueError, UnicodeDecodeError):
                return _json_response(start, "400 Bad Request", {"error": "invalid_json"})
            text = payload.get("text", "") if isinstance(payload, dict) else ""
            if not isinstance(text, str) or not text.strip():
                return _json_response(start, "400 Bad Request", {"error": "text_required"})
            if len(text) > MAX_TEXT_CHARS:
                return _json_response(start, "400 Bad Request", {"error": "text_too_long"})
            try:
                audio = synthesizer.synthesize(text)
            except (ValueError, ImportError, RuntimeError) as exc:
                return _json_response(start, "502 Bad Gateway",
                                      {"error": f"synthesis_failed: {exc}"})
            return _audio_response(start, "200 OK", audio, synthesizer.media_type)

        if path.startswith("/api/voice/"):
            if method not in ("GET", "HEAD", "POST"):
                return _json_response(start, "405 Method Not Allowed",
                                      {"error": "method_not_allowed"})
            return _json_response(start, "404 Not Found", {"error": "voice_route_not_found"})

        return _json_response(start, "404 Not Found", {"error": "not_found"})

    return application


def create_voice_app_from_env() -> Callable:
    """Wire local/offline backends when their packages are installed.

    faster-whisper (tiny) for transcription and system TTS for synthesis;
    either stays ``None`` ( -> honest 503) when its package is missing.
    No provider keys are read here: provider adapters need explicit
    construction with a key, never an implicit environment fallback that
    could surprise a deployment.
    """
    transcriber = None
    synthesizer = None
    try:
        from .daedalus_voice import FasterWhisperTranscriber, SystemTTSSynthesizer

        try:
            transcriber = FasterWhisperTranscriber("tiny")
        except (ImportError, ValueError, RuntimeError):
            transcriber = None
        try:
            synthesizer = SystemTTSSynthesizer()
        except (ImportError, ValueError, RuntimeError):
            synthesizer = None
    except ImportError:
        pass
    return create_voice_app(transcriber, synthesizer)


def create_fake_voice_app() -> Callable:
    """Voice app with deterministic fake backends, for tests and demos."""
    return create_voice_app(FakeTranscriber(), FakeSynthesizer())


# Default WSGI entrypoint (diagnostic-only: no backends configured).
application = create_voice_app()


__all__ = [
    "create_voice_app",
    "create_voice_app_from_env",
    "create_fake_voice_app",
    "application",
    "MAX_TEXT_CHARS",
]
