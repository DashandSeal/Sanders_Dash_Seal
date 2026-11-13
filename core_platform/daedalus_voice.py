"""Audio, video and voice capabilities for Sanders Dash & Seal (Daedalus).

Scope, stated honestly
----------------------
* Speech-to-text and text-to-speech are *adapters* around provider
  libraries.  Nothing here makes a live provider call succeed on its own:
  every real adapter raises ``ValueError`` when its API key is missing and
  ``ImportError`` when its SDK/package is not installed.  No key, secret or
  credential is stored, hardcoded or logged anywhere in this module.
* The only backends that work with no key and no network are the fakes
  (``FakeTranscriber`` / ``FakeSynthesizer``) and the local
  ``FasterWhisperTranscriber`` (after a model download) and
  ``SystemTTSSynthesizer`` (after ``pyttsx3``/``espeak-ng`` are installed).
* Video is signalling only.  This module validates WebRTC signalling
  messages against the existing ``worker/src/webrtc.js`` contract
  (``offer`` / ``answer`` / ``ice_candidate``, session-scoped, 64-hex
  token issued by ``backend/auth_session.py``).  It does not open a camera
  or microphone, does not run an SFU, and does not transport media.
  Live multi-party video needs a separate SFU (LiveKit) or a provider
  (Daily.co); see ``voice_api.py`` / ``web/voice.html`` notes.
* Server code here never activates a microphone or camera.  Audio helpers
  operate on bytes/files only (WAV PCM-16).  Browser capture lives in
  ``web/voice.html`` and runs only after the user grants permission.
* Plain WSGI cannot hold a WebSocket, so live duplex voice needs a
  separate WS/ASGI process or a provider endpoint; the HTTP endpoints in
  ``voice_api.py`` are request/response (upload audio, get a transcript;
  send text, get audio back).

Provider notes (research, 2026-11-13; re-check prices before budgeting)
------------------------------------------------------------------------
* faster-whisper v1.2.1, ``tiny``/``base`` models: $0, offline after the
  model download.  Default here.
* Deepgram Nova-3 streaming: vendor page shows $0.0048/min ($200 credit);
  older pages show $0.0077/min -- figures conflict, verify before budgeting.
* OpenAI ``gpt-transcribe``: $0.0045/min.  Do NOT use ``whisper-1``:
  deprecated, removed 26 Feb 2027.
* Google Cloud TTS WaveNet/Standard: $4/1M chars after 4M free/month.
* ElevenLabs: $0.04-$0.08/1k chars, SDK 2.75.0, 10k free credits/month
  (non-commercial).  Do NOT build new on OpenAI ``tts-1``/``tts-1-hd``:
  deprecated, shutdown 6 Jan 2027, replacement is not a drop-in.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import struct
import tempfile
import wave
from abc import ABC, abstractmethod
from typing import Any

# ---------------------------------------------------------------------------
# Audio helpers: bytes/files only.  No microphone or camera is touched here.
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE = 16000
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB per request; generous for voice clips.
MAX_AUDIO_SECONDS = 600.0  # 10 minutes; providers cap single requests anyway.


def write_wav_bytes(
    samples: bytes,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Encode raw PCM-16 ``samples`` as a WAV file and return its bytes."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if channels not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    if sample_width != 2:
        raise ValueError("only PCM-16 (sample_width=2) is supported")
    if len(samples) % (sample_width * channels) != 0:
        raise ValueError("sample bytes are not a whole number of frames")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(samples)
    return buf.getvalue()


def read_wav_info(audio_bytes: bytes) -> dict[str, Any]:
    """Return ``{channels, sample_width, sample_rate, frames, seconds}``.

    Raises ``ValueError`` when the bytes are not a readable WAV file.
    """
    if not audio_bytes:
        raise ValueError("audio bytes are empty")
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            info = {
                "channels": wav.getnchannels(),
                "sample_width": wav.getsampwidth(),
                "sample_rate": rate,
                "frames": frames,
                "seconds": frames / rate if rate else 0.0,
            }
    except (wave.Error, EOFError, ValueError) as exc:
        raise ValueError("audio bytes are not a readable WAV file") from exc
    if info["sample_width"] != 2:
        raise ValueError("only PCM-16 WAV audio is supported")
    return info


def wav_duration_seconds(audio_bytes: bytes) -> float:
    """Duration of WAV PCM-16 bytes, in seconds."""
    return float(read_wav_info(audio_bytes)["seconds"])


def validate_audio_bytes(audio_bytes: bytes, *, max_bytes: int = MAX_AUDIO_BYTES) -> dict[str, Any]:
    """Validate uploaded audio bytes and return their WAV info.

    Raises ``ValueError`` on empty, oversized, over-long or non-WAV input.
    Callers that accept non-WAV uploads (Opus/WebM from Chrome/Firefox,
    AAC/MP4 from Safari) must normalise server-side with ffmpeg first;
    this helper deliberately only accepts WAV PCM-16.
    """
    if not isinstance(audio_bytes, (bytes, bytearray)):
        raise ValueError("audio must be bytes")
    audio_bytes = bytes(audio_bytes)
    if not audio_bytes:
        raise ValueError("audio bytes are empty")
    if len(audio_bytes) > max_bytes:
        raise ValueError(f"audio exceeds {max_bytes} bytes")
    info = read_wav_info(audio_bytes)
    if info["seconds"] > MAX_AUDIO_SECONDS:
        raise ValueError("audio exceeds 600 seconds")
    if info["sample_rate"] < 8000 or info["sample_rate"] > 48000:
        raise ValueError("sample rate must be between 8000 and 48000 Hz")
    return info


def make_silence_wav(duration_seconds: float = 0.5, *, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Deterministic silent WAV PCM-16 mono, for fakes and tests."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    frames = int(sample_rate * duration_seconds)
    return write_wav_bytes(b"\x00\x00" * frames, sample_rate=sample_rate)


# ---------------------------------------------------------------------------
# Transcribers (speech -> text)
# ---------------------------------------------------------------------------


class Transcriber(ABC):
    """Speech-to-text adapter.  ``transcribe`` takes audio bytes, returns text."""

    name: str = "transcriber"
    audio_format: str = "wav"

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        raise NotImplementedError


class Synthesizer(ABC):
    """Text-to-speech adapter.  ``synthesize`` takes text, returns audio bytes."""

    name: str = "synthesizer"
    audio_format: str = "wav"
    media_type: str = "audio/wav"

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError


class FakeTranscriber(Transcriber):
    """Deterministic test transcriber: no network, no model, no key.

    Returns the configured transcript for any non-empty audio, so the
    Daedalus voice chain can be tested end to end offline.
    """

    name = "fake"

    def __init__(self, transcript: str = "generate a python hello world function") -> None:
        if not transcript.strip():
            raise ValueError("fake transcript must not be empty")
        self.transcript = transcript

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        if not audio_bytes:
            raise ValueError("audio bytes are empty")
        return self.transcript


class FakeSynthesizer(Synthesizer):
    """Deterministic test synthesizer: returns silent WAV, records calls.

    ``calls`` holds every text passed to ``synthesize`` so tests can assert
    the Daedalus-generated text (not the transcript) was spoken.
    """

    name = "fake"
    audio_format = "wav"
    media_type = "audio/wav"

    def __init__(self, duration_seconds: float = 0.5) -> None:
        self.calls: list[str] = []
        self.duration_seconds = duration_seconds

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text to speak must not be empty")
        self.calls.append(text)
        return make_silence_wav(self.duration_seconds)


class FasterWhisperTranscriber(Transcriber):
    """Local/offline transcription with faster-whisper (no key, $0).

    Models ``tiny``/``base`` only by default.  The model downloads once
    (``~75 MB`` for tiny, ``~145 MB`` for base) and then runs offline.
    """

    name = "faster-whisper"
    SUPPORTED_MODELS = ("tiny", "base")

    def __init__(
        self,
        model: str = "tiny",
        *,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"faster-whisper model must be one of {self.SUPPORTED_MODELS}, got {model!r}"
            )
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is not installed; install faster-whisper==1.2.1 "
                "and download the model before using FasterWhisperTranscriber"
            ) from exc
        self._model = WhisperModel(model, device=device, compute_type=compute_type)
        self.model = model

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        if not audio_bytes:
            raise ValueError("audio bytes are empty")
        suffix = ".wav" if filename.endswith(".wav") else ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, _info = self._model.transcribe(tmp_path)
            text = "".join(segment.text for segment in segments).strip()
        finally:
            os.unlink(tmp_path)
        if not text:
            raise ValueError("faster-whisper returned no transcript")
        return text


class DeepgramTranscriber(Transcriber):
    """Production streaming/batch transcription via Deepgram Nova-3.

    Requires ``DEEPGRAM_API_KEY`` and the ``deepgram-sdk`` package.
    Not live-tested in this repo: no key was available and no live call
    was made.  Price note: vendor page $0.0048/min ($200 credit); older
    pages show $0.0077/min -- verify before budgeting.
    """

    name = "deepgram-nova-3"

    def __init__(self, *, api_key: str | None = None, model: str = "nova-3") -> None:
        self.api_key = api_key or os.environ.get("DEEPGRAM_API_KEY", "")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY is required for Deepgram transcription")
        try:
            from deepgram import DeepgramClient  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "deepgram-sdk is not installed; install deepgram-sdk before "
                "using DeepgramTranscriber"
            ) from exc
        self._client = DeepgramClient(self.api_key)
        self.model = model

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        if not audio_bytes:
            raise ValueError("audio bytes are empty")
        prerecorded = self._client.listen.prerecorded
        if not hasattr(prerecorded, "v"):
            raise RuntimeError("installed deepgram-sdk does not expose listen.prerecorded.v()")
        response = prerecorded.v("1").transcribe_file(
            {"buffer": audio_bytes},
            {"model": self.model, "smart_format": True},
        )
        try:
            text = response.results.channels[0].alternatives[0].transcript.strip()
        except (AttributeError, IndexError, KeyError) as exc:
            raise RuntimeError("Deepgram returned an unexpected response shape") from exc
        if not text:
            raise ValueError("Deepgram returned no transcript")
        return text


class OpenAITranscriber(Transcriber):
    """Production transcription via OpenAI ``gpt-transcribe``.

    Requires ``OPENAI_API_KEY`` and the ``openai`` package.  Do NOT use
    ``whisper-1``: deprecated, removed 26 Feb 2027.  Not live-tested here.
    """

    name = "openai-gpt-transcribe"

    def __init__(self, *, api_key: str | None = None, model: str = "gpt-transcribe") -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI transcription")
        if model == "whisper-1":
            raise ValueError("whisper-1 is deprecated and removed 26 Feb 2027; use gpt-transcribe")
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed; install openai before "
                "using OpenAITranscriber"
            ) from exc
        self._client = OpenAI(api_key=self.api_key)
        self.model = model

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        if not audio_bytes:
            raise ValueError("audio bytes are empty")
        result = self._client.audio.transcriptions.create(
            model=self.model,
            file=(filename, io.BytesIO(audio_bytes)),
        )
        text = (result.text or "").strip()
        if not text:
            raise ValueError("OpenAI returned no transcript")
        return text


# ---------------------------------------------------------------------------
# Synthesizers (text -> speech)
# ---------------------------------------------------------------------------


class GoogleTTSSynthesizer(Synthesizer):
    """Production TTS via Google Cloud Text-to-Speech (WaveNet).

    Requires the ``google-cloud-texttospeech`` package and Google
    credentials (``GOOGLE_APPLICATION_CREDENTIALS``).  WaveNet/Standard
    $4/1M chars after 4M free/month (verify current pricing).  Returns MP3
    bytes.  Not live-tested here.
    """

    name = "google-tts-wavenet"
    audio_format = "mp3"
    media_type = "audio/mpeg"

    def __init__(
        self,
        *,
        language_code: str = "en-US",
        voice_name: str = "en-US-Wavenet-D",
    ) -> None:
        try:
            from google.cloud import texttospeech  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-texttospeech is not installed; install it and "
                "set GOOGLE_APPLICATION_CREDENTIALS before using GoogleTTSSynthesizer"
            ) from exc
        self._client = texttospeech.TextToSpeechClient()
        self._tts = texttospeech
        self.language_code = language_code
        self.voice_name = voice_name

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text to speak must not be empty")
        tts = self._tts
        response = self._client.synthesize_speech(
            input=tts.SynthesisInput(text=text),
            voice=tts.VoiceSelectionParams(
                language_code=self.language_code, name=self.voice_name
            ),
            audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3),
        )
        if not response.audio_content:
            raise ValueError("Google TTS returned no audio")
        return bytes(response.audio_content)


class ElevenLabsSynthesizer(Synthesizer):
    """Production TTS via ElevenLabs.

    Requires ``ELEVENLABS_API_KEY`` and the ``elevenlabs`` package (SDK
    2.75.0).  $0.04-$0.08/1k chars; 10k free credits/month non-commercial.
    Returns MP3 bytes.  Not live-tested here.
    """

    name = "elevenlabs"
    audio_format = "mp3"
    media_type = "audio/mpeg"

    def __init__(self, *, api_key: str | None = None, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabs synthesis")
        try:
            from elevenlabs import ElevenLabs  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "elevenlabs package is not installed; install elevenlabs==2.75.0 "
                "before using ElevenLabsSynthesizer"
            ) from exc
        self._client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text to speak must not be empty")
        audio = self._client.text_to_speech.convert(
            voice_id=self.voice_id,
            output_format="mp3_44100_128",
            text=text,
        )
        data = b"".join(audio) if not isinstance(audio, (bytes, bytearray)) else bytes(audio)
        if not data:
            raise ValueError("ElevenLabs returned no audio")
        return data


class SystemTTSSynthesizer(Synthesizer):
    """Offline TTS via pyttsx3 / py3-tts with espeak-ng.

    ``save_to_file`` only: on a headless server there is no live playback,
    so this writes a WAV file and returns its bytes.  Requires ``pyttsx3``
    and an espeak-ng voice; raises an honest error when either is missing.
    """

    name = "system-tts"
    audio_format = "wav"
    media_type = "audio/wav"

    def __init__(self, *, rate: int = 175) -> None:
        try:
            import pyttsx3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "pyttsx3 is not installed; install pyttsx3==2.99 (py3-tts 4.1) "
                "with espeak-ng before using SystemTTSSynthesizer"
            ) from exc
        self._pyttsx3 = pyttsx3
        self.rate = rate

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text to speak must not be empty")
        engine = self._pyttsx3.init()
        try:
            engine.setProperty("rate", self.rate)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                engine.save_to_file(text, tmp_path)
                engine.runAndWait()
                with open(tmp_path, "rb") as handle:
                    data = handle.read()
            finally:
                os.unlink(tmp_path)
        finally:
            try:
                engine.stop()
            except Exception:
                pass
        if not data:
            raise ValueError("system TTS produced no audio")
        return data


# ---------------------------------------------------------------------------
# Video helpers: WebRTC *signalling* validation only -- no live call.
# Mirrors the existing worker/src/webrtc.js contract and the 64-hex token
# issued by backend/auth_session.py issue_webrtc_access_token (<=60 min,
# room-scoped).  Media transport / recording / identity proofing are
# separate services; see native_ron_rooms.py / native_recording_manifest.py.
# ---------------------------------------------------------------------------

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
TOKEN_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SIGNALING_ACTIONS = ("offer", "answer", "ice_candidate")
MAX_SDP_BYTES = 65536
MAX_CANDIDATE_BYTES = 4096


def is_valid_webrtc_token(token: object) -> bool:
    """True when ``token`` is a 64-hex string (``secrets.token_hex(32)``)."""
    return isinstance(token, str) and TOKEN_RE.fullmatch(token) is not None


def validate_video_session(*, session_id: str, token: str) -> dict[str, str]:
    """Validate a session-scoped WebRTC signalling session.

    Checks shape only: the session id matches the worker contract and the
    token is a 64-hex string.  It does NOT check the token against the
    SQLite ledger -- that lookup belongs to ``validate_worker_token_request``
    in ``backend/auth_session.py``.  Raises ``ValueError`` on bad input.
    """
    if not isinstance(session_id, str) or SESSION_ID_RE.fullmatch(session_id) is None:
        raise ValueError("session_id must be 1-128 chars of [A-Za-z0-9_.-]")
    if not is_valid_webrtc_token(token):
        raise ValueError("webrtc token must be a 64-hex string")
    return {"session_id": session_id, "token_sha256": hashlib.sha256(token.encode("ascii")).hexdigest()}


def validate_signaling_message(message: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    """Validate one WebRTC signalling message for ``session_id``.

    Accepts exactly the worker contract: ``action`` in
    ``offer``/``answer``/``ice_candidate``, ``targetSessionId`` equal to
    ``session_id``, an ``sdp`` object whose ``type`` matches the action
    (offer/answer), or a ``candidate`` object (ice_candidate).  Returns a
    normalised frame dict ready to relay; raises ``ValueError`` otherwise.
    No media is transported and no peer connection is opened.
    """
    if not isinstance(message, dict):
        raise ValueError("signaling message must be an object")
    if message.get("targetSessionId") != session_id:
        raise ValueError("targetSessionId does not match the session")
    action = message.get("action")
    if action not in SIGNALING_ACTIONS:
        raise ValueError(f"unknown signaling action: {action!r}")
    if action in ("offer", "answer"):
        sdp = message.get("sdp")
        if not isinstance(sdp, dict) or sdp.get("type") != action:
            raise ValueError("offer/answer requires an sdp object whose type matches the action")
        sdp_text = sdp.get("sdp")
        if not isinstance(sdp_text, str) or not 1 <= len(sdp_text) <= MAX_SDP_BYTES:
            raise ValueError("sdp text must be 1-65536 chars")
        return {
            "type": "webrtc_signal",
            "action": action,
            "targetSessionId": session_id,
            "sdp": {"type": action, "sdp": sdp_text},
        }
    candidate = message.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("candidate"), str):
        raise ValueError("ice_candidate requires a candidate object with a candidate string")
    if len(candidate["candidate"]) > MAX_CANDIDATE_BYTES:
        raise ValueError("ICE candidate exceeds 4096 chars")
    return {
        "type": "webrtc_signal",
        "action": "ice_candidate",
        "targetSessionId": session_id,
        "candidate": candidate,
    }


# ---------------------------------------------------------------------------
# Daedalus voice integration: transcribe -> generate_source -> speak.
#
# Uses DaedalusRuntimeIntegration.generate_source() because its
# ``response.text`` IS the generated source.  UnifiedDaedalusEngine.execute()
# returns only {engine, operation_id, invention_id, source_sha256} -- the
# source text itself -- so it cannot feed a synthesizer.  This function
# does not change daedalus_engine.py behaviour for text callers.
# ---------------------------------------------------------------------------


def voice_generate_source(
    *,
    transcriber: Transcriber,
    integration: object,
    synthesizer: Synthesizer,
    audio_bytes: bytes,
    invention_id: str,
    language: str = "Python",
    inventor_assertions: tuple[str, ...] = (),
    audio_filename: str = "audio.wav",
) -> dict[str, Any]:
    """Full voice chain: audio -> objective -> Daedalus source -> spoken audio.

    ``integration`` must be a ``DaedalusRuntimeIntegration`` (checked by
    duck-typing on ``generate_source`` so tests can pass a fake transport
    subclass).  Returns ``transcript``, ``source_text``, ``source_sha256``,
    ``invention_id``, ``audio_bytes`` (synthesized speech) and
    ``audio_format``.  Raises ``ValueError`` on empty audio/objective.
    """
    if not isinstance(transcriber, Transcriber):
        raise TypeError("a Transcriber is required")
    if not isinstance(synthesizer, Synthesizer):
        raise TypeError("a Synthesizer is required")
    generate_source = getattr(integration, "generate_source", None)
    if not callable(generate_source):
        raise TypeError("integration must expose generate_source()")
    if not invention_id or not invention_id.strip():
        raise ValueError("invention_id is required")
    transcript = transcriber.transcribe(audio_bytes, filename=audio_filename)
    if not transcript.strip():
        raise ValueError("transcription produced no objective")
    result = generate_source(
        invention_id=invention_id,
        objective=transcript,
        language=language,
        inventor_assertions=inventor_assertions,
    )
    source_text = result.response.text
    if not source_text.strip():
        raise ValueError("Daedalus returned no source text")
    spoken = synthesizer.synthesize(source_text)
    return {
        "transcript": transcript,
        "source_text": source_text,
        "source_sha256": result.source_sha256,
        "invention_id": result.invention_id,
        "evidence_signature": result.evidence_signature,
        "audio_bytes": spoken,
        "audio_format": synthesizer.audio_format,
        "media_type": synthesizer.media_type,
    }


# Short alias used by callers that think of the flow as "speak a prompt".
speak_prompt = voice_generate_source


__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "MAX_AUDIO_BYTES",
    "MAX_AUDIO_SECONDS",
    "Transcriber",
    "Synthesizer",
    "FakeTranscriber",
    "FakeSynthesizer",
    "FasterWhisperTranscriber",
    "DeepgramTranscriber",
    "OpenAITranscriber",
    "GoogleTTSSynthesizer",
    "ElevenLabsSynthesizer",
    "SystemTTSSynthesizer",
    "write_wav_bytes",
    "read_wav_info",
    "wav_duration_seconds",
    "validate_audio_bytes",
    "make_silence_wav",
    "SESSION_ID_RE",
    "TOKEN_RE",
    "SIGNALING_ACTIONS",
    "is_valid_webrtc_token",
    "validate_video_session",
    "validate_signaling_message",
    "voice_generate_source",
    "speak_prompt",
]
