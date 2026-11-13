"""Bozly CFO: region-aware multilingual voice and volumetric meeting capability registry.

195 is the owner's intended geographic reach, not a claim that 195 voice
languages, provider models, satellite terminals or holographic displays exist.
No artificial country allowlist or new approval process is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Mapping

IDENTITY="BOZLY-CFO"
GEOGRAPHIC_TARGET=195
VOICE_PROFILES={
    "male-1": {"presentation":"male","slot":1},
    "male-2": {"presentation":"male","slot":2},
    "female-1": {"presentation":"female","slot":1},
    "female-2": {"presentation":"female","slot":2},
}
# Browser/host providers select concrete real available voices. The profile
# labels describe the owner's requested voice presentations, not verified sex.
LANGUAGE_TAG=re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8}){0,12}$")
REGION_CODE=re.compile(r"^[A-Z]{2}$")

@dataclass(frozen=True)
class LocaleSession:
    region: str
    requested_language: str
    speech_recognition_provider: str | None
    tts_provider: str | None
    translator_provider: str | None
    selected_voice: str
    regional_access: str

    def __post_init__(self):
        if not REGION_CODE.fullmatch(self.region):
            raise ValueError("Use ISO 3166-1 alpha-2 regional identifiers")
        if not LANGUAGE_TAG.fullmatch(self.requested_language):
            raise ValueError("Use BCP 47 language tags")
        if self.selected_voice not in VOICE_PROFILES:
            raise ValueError("Use one of Bozly's four owner-defined profiles")
        if self.regional_access not in {"available","degraded","unavailable","unknown"}:
            raise ValueError("Invalid observed regional connectivity state")

    def report(self) -> dict:
        record=asdict(self)
        record.update({
            "engine":IDENTITY,
            "geographic_target":GEOGRAPHIC_TARGET,
            "voice_profile":VOICE_PROFILES[self.selected_voice],
            "language_support":(
                "configured" if (self.speech_recognition_provider and
                                 self.tts_provider and self.translator_provider)
                else "not_fully_configured"
            ),
            "coverage_claim":"target_only_until_provider_and_network_report_real_availability",
        })
        return record


def provider_language_status(
    language: str, *,
    recognition_languages: frozenset[str],
    synthesis_languages: frozenset[str],
    translation_languages: frozenset[str],
) -> dict:
    """Report *actual advertised* capabilities; never fabricate 195-language support."""
    if not LANGUAGE_TAG.fullmatch(language):
        raise ValueError("Invalid BCP 47 tag")
    return {
        "language":language,
        "recognition_available":language in recognition_languages,
        "synthesis_available":language in synthesis_languages,
        "translation_available":language in translation_languages,
    }


def hologram_session_descriptor(
    *,
    room_id: str, endpoint: str | None,
    renderer: str | None, connected: bool,
) -> dict:
    """Integration metadata for AR/volumetric/hologram hardware.

    A regular video call is not evidence of a holographic projection.
    """
    if not room_id or len(room_id)>160:
        raise ValueError("Room ID required")
    if endpoint is not None and not endpoint.startswith("https://"):
        raise ValueError("Renderer endpoint must use HTTPS")
    return {
        "engine":IDENTITY,"room_id":room_id,
        "mode":"volumetric_renderer" if connected and renderer and endpoint else "ordinary_video",
        "renderer":renderer if connected else None,
        "renderer_endpoint":endpoint if connected else None,
        "real_hologram_active":bool(connected and renderer and endpoint),
        "available_only_when_hardware_and_provider_are_actually_connected":True,
    }
