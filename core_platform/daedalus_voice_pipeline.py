"""Daedalus voice TURN pipeline (stdlib HTTP adapters + run_voice_turn).

Split note (2026-11-13, deploy/simultaneous-20261113): this module is the
former ``core_platform/daedalus_voice.py`` from
upgrade/sota-daedalus-voice-20261113, moved here unchanged apart from this
header. ``core_platform/daedalus_voice.py`` itself is now the
feature/audio-video-voice-20261113 version (663 lines: audio + video
signalling + voice, with voice_api.py and web/voice.html), because that
version carries the WebRTC signalling validation and the 21-test suite
that the voice API depends on. Both modules define a ``FakeTranscriber``
with a different API, so they cannot share one file; the pipeline keeps
its own ``Transcriber``/``Speaker`` protocols, ``run_voice_turn``, and
the stdlib OpenAI/ElevenLabs adapters, and ``daedalus_engine.
build_voice_runner`` imports from here. See docs/UNIFIED_DEPLOY_2026-11-13.md.

Original module docstring follows.
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
    """OpenAI transcription over stdlib HTTP (``gpt-transcribe``).

    Default model is ``gpt-transcribe``. ``whisper-1`` is rejected:
    deprecated, shuts down 26 Feb 2027 (see ``openai_link``).
    """

    PROVIDER = "openai-gpt-transcribe"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-transcribe",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        import os

        from .openai_link import reject_deprecated_openai_model

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for Whisper transcription")
        reject_deprecated_openai_model(model)
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
    """Retired OpenAI ``/audio/speech`` TTS adapter — refuses to construct.

    ``tts-1`` / ``tts-1-hd`` (and ``gpt-4o-mini-tts``) shut down
    6 Jan 2027 and OpenAI's replacement, ``gpt-realtime-2.1-mini``,
    does **not** run on ``/v1/audio/speech`` — it runs only on the
    Realtime API. There is therefore no supported ``/audio/speech``
    TTS model left to call, so this class raises ``ValueError`` on
    construction and points at
    :class:`openai_link.OpenAIRealtimeTTSSpeaker`. Kept (rather than
    deleted) so existing imports fail loudly with the migration path
    instead of silently resolving to a dead endpoint.
    """

    PROVIDER = "openai-tts-retired"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ValueError(
            "OpenAI /audio/speech TTS is retired: tts-1/tts-1-hd shut down "
            "2027-01-06 with no /v1/audio/speech replacement; use "
            "openai_link.OpenAIRealtimeTTSSpeaker with model "
            "gpt-realtime-2.1-mini (Realtime API only)"
        )

    def speak(self, text: str, **kwargs: Any) -> Any:
        raise ValueError(
            "OpenAI /audio/speech TTS is retired; use "
            "openai_link.OpenAIRealtimeTTSSpeaker instead"
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
