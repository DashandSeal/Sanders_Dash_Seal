"""Daedalus voice / audio: pluggable transcription and speech adapters.

Pipeline (spoken prompt -> transcribe -> generate -> speak) is
:func:`run_voice_turn`. Every provider is behind a small protocol so
tests run with fakes and no key, no network, and no spend:

- :class:`FakeTranscriber` / :class:`FakeSpeaker` — deterministic,
  clearly labelled fake audio (``application/x-daedalus-fake-audio``).
- :class:`OpenAIWhisperTranscriber` — ``POST {base_url}/audio/transcriptions``
  multipart ``file`` + ``model`` (default ``whisper-1``), JSON
  ``{"text": ...}`` response, 25 MB provider file limit.
- :class:`OpenAITTSSpeaker` — ``POST {base_url}/audio/speech`` JSON
  ``{model, input, voice, response_format}`` returning audio bytes.
  Provider input limit is 4096 characters.
- :class:`ElevenLabsSpeaker` — ``POST {base_url}/text-to-speech/{voice_id}``
  JSON ``{text, model_id?}`` with ``xi-api-key``, returning audio bytes.
  The voice id is owner-supplied (env ``DAEDALUS_ELEVENLABS_VOICE_ID``);
  no voice or model id is invented here.

All real adapters use only the standard library, accept an injectable
``base_url`` (so a local OpenAI-compatible server such as a self-hosted
Whisper endpoint can be used), and raise :class:`DaedalusProviderError`
with an HTTP status only — never the upstream body — on failure.
Without a key they raise ``ValueError`` honestly; no live Whisper,
TTS, or ElevenLabs call is claimed to work without one. Audio bytes
and transcript text are never written to logs.
"""
from __future__ import annotations

import json
import logging
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from .daedalus_claude_transport import DaedalusProviderError

__all__ = [
    "ElevenLabsSpeaker",
    "FakeSpeaker",
    "FakeTranscriber",
    "OpenAITTSSpeaker",
    "OpenAIWhisperTranscriber",
    "SpeechAudio",
    "TextGenerator",
    "Transcriber",
    "Transcription",
    "VoiceTurn",
    "run_voice_turn",
]

logger = logging.getLogger("daedalus.voice")

MAX_WHISPER_BYTES = 25 * 1024 * 1024
MAX_TTS_CHARS = 4096
_MAX_PROVIDER_RESPONSE_BYTES = 32 * 1024 * 1024

_TTS_MIME = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


logger = logging.getLogger("daedalus.voice")


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None
    provider: str


@dataclass(frozen=True)
class SpeechAudio:
    audio: bytes
    mime_type: str
    provider: str
    voice: str | None = None


@dataclass(frozen=True)
class VoiceTurn:
    transcript: str
    response_text: str
    audio: SpeechAudio
    transcriber: str
    speaker: str
    generator: str
    latency_ms: int


@runtime_checkable
class Transcriber(Protocol):
    PROVIDER: str

    def transcribe(
        self, audio: bytes, *, language: str | None = None,
        filename: str = "audio.webm", mime_type: str | None = None,
    ) -> Transcription: ...


@runtime_checkable
class Speaker(Protocol):
    PROVIDER: str

    def speak(self, text: str, **kwargs: Any) -> SpeechAudio: ...


@runtime_checkable
class TextGenerator(Protocol):
    def generate_text(self, prompt: str) -> str: ...


def _provider_name(adapter: Any) -> str:
    return str(getattr(adapter, "PROVIDER", type(adapter).__name__))


def _http_post(
    url: str,
    *,
    data: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
    opener: Callable[..., Any] | None = None,
) -> tuple[bytes, Mapping[str, str]]:
    """POST bytes; returns (body, headers). Status only on failure."""
    request = urllib.request.Request(url, data=data, method="POST", headers=dict(headers))
    call = opener or urllib.request.urlopen
    try:
        with call(request, timeout=timeout_seconds) as response:
            body = response.read(_MAX_PROVIDER_RESPONSE_BYTES + 1)
            if len(body) > _MAX_PROVIDER_RESPONSE_BYTES:
                raise DaedalusProviderError("Provider response exceeds size limit")
            return body, dict(response.headers)
    except urllib.error.HTTPError as exc:
        logger.warning("daedalus voice provider HTTP %s at %s", exc.code, url.rsplit("/", 1)[0])
        raise DaedalusProviderError(
            f"Voice provider returned HTTP {exc.code}"
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("daedalus voice transport failure %s", type(exc).__name__)
        raise DaedalusProviderError(
            f"Voice provider transport failure: {type(exc).__name__}"
        ) from None


def _encode_multipart(
    fields: Mapping[str, str],
    *,
    file_field: str,
    filename: str,
    file_bytes: bytes,
    file_mime_type: str,
    boundary: str | None = None,
) -> tuple[bytes, str]:
    """Encode a multipart/form-data body. Pure function, unit-tested."""
    chosen = boundary or ("----DaedalusVoice" + secrets.token_hex(16))
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{chosen}\r\n".encode("ascii"))
        lines.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii")
        )
        lines.append(value.encode("utf-8"))
        lines.append(b"\r\n")
    lines.append(f"--{chosen}\r\n".encode("ascii"))
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("ascii")
    )
    lines.append(f"Content-Type: {file_mime_type}\r\n\r\n".encode("ascii"))
    lines.append(file_bytes)
    lines.append(f"\r\n--{chosen}--\r\n".encode("ascii"))
    return b"".join(lines), f"multipart/form-data; boundary={chosen}"


class FakeTranscriber:
    """Deterministic stand-in: always returns the configured transcript."""

    PROVIDER = "fake"

    def __init__(self, transcript: str, language: str | None = "en") -> None:
        if not transcript.strip():
            raise ValueError("FakeTranscriber requires a non-empty transcript")
        self._transcript = transcript
        self._language = language

    def transcribe(
        self, audio: bytes, *, language: str | None = None,
        filename: str = "audio.webm", mime_type: str | None = None,
    ) -> Transcription:
        if not audio:
            raise ValueError("Audio bytes are required")
        return Transcription(
            text=self._transcript,
            language=language or self._language,
            provider=self.PROVIDER,
        )


class FakeSpeaker:
    """Deterministic stand-in: returns labelled fake audio bytes.

    The bytes are not playable audio; the mime type says so explicitly
    so no player mistakes them for real speech.
    """

    PROVIDER = "fake"

    def __init__(self, voice: str | None = "fake-voice") -> None:
        self._voice = voice

    def speak(self, text: str, **kwargs: Any) -> SpeechAudio:
        if not text.strip():
            raise ValueError("Text to speak must not be empty")
        return SpeechAudio(
            audio=b"FAKE-AUDIO:" + text.encode("utf-8"),
            mime_type="application/x-daedalus-fake-audio",
            provider=self.PROVIDER,
            voice=self._voice,
        )


class OpenAIWhisperTranscriber:
    """OpenAI-compatible Whisper transcription over stdlib HTTP."""

    PROVIDER = "openai-whisper"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "whisper-1",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        import os

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for Whisper transcription")
        if not model.strip():
            raise ValueError("Whisper model must not be empty")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def transcribe(
        self, audio: bytes, *, language: str | None = None,
        filename: str = "audio.webm", mime_type: str | None = None,
    ) -> Transcription:
        if not audio:
            raise ValueError("Audio bytes are required")
        if len(audio) > MAX_WHISPER_BYTES:
            raise ValueError("Audio exceeds the Whisper 25 MB file limit")
        fields: dict[str, str] = {"model": self.model, "response_format": "json"}
        if language:
            fields["language"] = language
        body, content_type = _encode_multipart(
            fields,
            file_field="file",
            filename=filename,
            file_bytes=audio,
            file_mime_type=mime_type or "application/octet-stream",
        )
        raw, _headers = _http_post(
            f"{self.base_url}/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": content_type,
                "Accept": "application/json",
            },
            timeout_seconds=self.timeout_seconds,
            opener=self._opener,
        )
        try:
            result = json.loads(raw)
            text = str(result["text"])
        except (ValueError, KeyError, TypeError):
            raise DaedalusProviderError("Invalid Whisper transcription response") from None
        if not text.strip():
            raise DaedalusProviderError("Whisper returned an empty transcript")
        return Transcription(text=text, language=language, provider=self.PROVIDER)


class OpenAITTSSpeaker:
    """OpenAI text-to-speech over stdlib HTTP (``/audio/speech``)."""

    PROVIDER = "openai-tts"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "tts-1",
        voice: str = "alloy",
        response_format: str = "mp3",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        import os

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for text-to-speech")
        if not model.strip() or not voice.strip():
            raise ValueError("TTS model and voice must not be empty")
        if response_format not in _TTS_MIME:
            raise ValueError(f"Unsupported TTS response_format: {response_format}")
        self.model = model
        self.voice = voice
        self.response_format = response_format
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def speak(self, text: str, **kwargs: Any) -> SpeechAudio:
        voice = str(kwargs.get("voice") or self.voice)
        model = str(kwargs.get("model") or self.model)
        if not text.strip():
            raise ValueError("Text to speak must not be empty")
        if len(text) > MAX_TTS_CHARS:
            raise ValueError("Text exceeds the TTS 4096 character input limit")
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": self.response_format,
        }
        raw, _headers = _http_post(
            f"{self.base_url}/audio/speech",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": _TTS_MIME[self.response_format],
            },
            timeout_seconds=self.timeout_seconds,
            opener=self._opener,
        )
        if not raw:
            raise DaedalusProviderError("TTS provider returned no audio")
        return SpeechAudio(
            audio=raw,
            mime_type=_TTS_MIME[self.response_format],
            provider=self.PROVIDER,
            voice=voice,
        )


class ElevenLabsSpeaker:
    """ElevenLabs text-to-speech over stdlib HTTP."""

    PROVIDER = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
        base_url: str = "https://api.elevenlabs.io/v1",
        timeout_seconds: float = 120.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        import os

        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        if not self._api_key:
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabs speech")
        self.voice_id = voice_id or os.environ.get("DAEDALUS_ELEVENLABS_VOICE_ID", "")
        if not self.voice_id:
            raise ValueError(
                "An ElevenLabs voice_id is required (DAEDALUS_ELEVENLABS_VOICE_ID)"
            )
        self.model_id = model_id or os.environ.get("DAEDALUS_ELEVENLABS_MODEL_ID") or None
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def speak(self, text: str, **kwargs: Any) -> SpeechAudio:
        voice_id = str(kwargs.get("voice_id") or self.voice_id)
        if not text.strip():
            raise ValueError("Text to speak must not be empty")
        payload: dict[str, Any] = {"text": text}
        if self.model_id:
            payload["model_id"] = self.model_id
        raw, _headers = _http_post(
            f"{self.base_url}/text-to-speech/{voice_id}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            timeout_seconds=self.timeout_seconds,
            opener=self._opener,
        )
        if not raw:
            raise DaedalusProviderError("ElevenLabs returned no audio")
        return SpeechAudio(
            audio=raw, mime_type="audio/mpeg", provider=self.PROVIDER, voice=voice_id
        )


def run_voice_turn(
    *,
    audio: bytes,
    transcriber: Transcriber,
    generator: TextGenerator | Callable[[str], str],
    speaker: Speaker,
    language: str | None = None,
    filename: str = "audio.webm",
    mime_type: str | None = None,
) -> VoiceTurn:
    """One spoken turn: transcribe -> generate text -> speak the reply.

    ``generator`` is any ``generate_text(prompt) -> str`` object or a
    plain ``Callable[[str], str]`` (for example a closure over a live
    Daedalus runtime), so a live Daedalus runtime, a fake, or another
    model can drive the turn. Only lengths and provider names are
    logged — never audio bytes, transcripts, or generated text.
    """
    if not audio:
        raise ValueError("Audio bytes are required")
    started = time.monotonic()
    transcription = transcriber.transcribe(
        audio, language=language, filename=filename, mime_type=mime_type
    )
    if not transcription.text.strip():
        raise ValueError("Transcription returned empty text")
    generate = getattr(generator, "generate_text", None) or generator
    response_text = generate(transcription.text)
    if not response_text or not response_text.strip():
        raise ValueError("Text generation returned empty text")
    spoken = speaker.speak(response_text)
    if not spoken.audio:
        raise DaedalusProviderError("Speech provider returned no audio")
    latency_ms = round((time.monotonic() - started) * 1000)
    logger.debug(
        "daedalus voice turn transcriber=%s speaker=%s audio_bytes=%d "
        "transcript_chars=%d response_chars=%d latency_ms=%d",
        _provider_name(transcriber), _provider_name(speaker), len(audio),
        len(transcription.text), len(response_text), latency_ms,
    )
    return VoiceTurn(
        transcript=transcription.text,
        response_text=response_text,
        audio=spoken,
        transcriber=_provider_name(transcriber),
        speaker=_provider_name(speaker),
        generator=getattr(generator, "__name__", None) or type(generator).__name__,
        latency_ms=latency_ms,
    )
