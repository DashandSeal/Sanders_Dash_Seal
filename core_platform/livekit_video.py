"""
LiveKit / WebRTC video linking for Sanders Dash & Seal.

Canonical choice (P3, 2026-11-13): ``livekit_realtime.py`` is the
canonical LiveKit module -- it owns ``LiveKitClient`` / ``DailyClient`` /
``RealtimeConfig`` used by the live routes (``realtime_api.py``,
``deploy/deployment.py``) and the single shared JWT implementation.
This module is RETAINED, not merged away: it is the token issue/validate
+ status helper referenced by the service-linking table, and a full
merge is unsafe (see ``docs/LIVEKIT_CANONICAL.md``: identity charset,
TTL bounds, return shapes and error types all differ). Its JWT helpers
(``_b64url`` / ``_b64url_decode``) are imported from
``livekit_realtime`` since P3, so the crypto is implemented once; tokens
issued by either module validate under the other.

Scope, stated honestly
----------------------
* Video here is **signalling + session tokens only**.  This module
  does not open a camera or microphone, does not run an SFU, does
  not transport media and does not fabricate a live peer connection.
  Live multi-party video needs a real LiveKit server (self-hosted)
  or LiveKit Cloud; this module issues and validates the tokens
  that let a client join one.
* Token issuance is a standard LiveKit access token: a JWT signed
  with HMAC-SHA256 (``LIVEKIT_API_SECRET``) carrying the LiveKit
  video grant (room, identity, publish/subscribe).  It is built with
  the stdlib only — no ``livekit`` SDK is required.  When the SDK
  (``livekit-api``) is installed, :func:`sdk_available` reports True
  and callers may use it instead; the token shape is the same.
* :func:`issue_room_token` requires ``LIVEKIT_API_KEY``,
  ``LIVEKIT_API_SECRET`` and ``LIVEKIT_URL`` (or explicit arguments)
  and raises ``ValueError`` without them.  Tokens expire after
  ``ttl_seconds`` (default 3600, max 86400).
* :func:`validate_room_token` checks shape, signature, expiry and
  room/identity claims locally (no network).  It does not check the
  token against a LiveKit server — that check happens when the
  client actually joins.
* WebRTC signalling messages are validated by the existing
  ``daedalus_voice.validate_signaling_message`` /
  ``validate_video_session`` helpers; :func:`validate_signaling_message`
  here re-exports that contract so video callers have one import.
* Free-tier-first: LiveKit Cloud has a free tier; self-hosting on the
  Oracle Always Free instance costs $0 in provider fees.  Either way
  no spend is made by this module.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from typing import Any

from .daedalus_voice import (
    validate_signaling_message as _validate_signaling_message,
)
from .daedalus_voice import validate_video_session
from .livekit_realtime import _b64url, _b64url_decode

ROOM_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9_@.\-]{1,128}$")
MAX_TTL_SECONDS = 86400


class LiveKitError(RuntimeError):
    """LiveKit token / config failure."""


def sdk_available() -> bool:
    """True when the ``livekit-api`` SDK package is importable."""
    try:
        import livekit.api  # noqa: F401  (import check only)

        return True
    except ImportError:
        return False


# NOTE (P3, 2026-11-13): _b64url / _b64url_decode used to be duplicated
# here. They now come from .livekit_realtime (the canonical module);
# see the module docstring. Do not re-add local copies.


def livekit_config_from_env() -> dict[str, str]:
    """Read LiveKit config from the environment (no defaults, no secrets logged)."""
    missing = [
        n
        for n in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
        if not os.environ.get(n)
    ]
    if missing:
        raise ValueError(f"Missing LiveKit config: {', '.join(missing)}")
    url = os.environ["LIVEKIT_URL"]
    if not url.startswith(("https://", "http://", "wss://")):
        raise ValueError("LIVEKIT_URL must be an http(s) or wss URL")
    return {
        "url": url,
        "api_key": os.environ["LIVEKIT_API_KEY"],
        "api_secret": os.environ["LIVEKIT_API_SECRET"],
    }


def issue_room_token(
    *,
    room: str,
    identity: str,
    url: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    ttl_seconds: int = 3600,
    can_publish: bool = True,
    can_subscribe: bool = True,
    now: int | None = None,
) -> dict[str, Any]:
    """Issue a LiveKit room access token (JWT, HMAC-SHA256).

    Returns ``url``, ``room``, ``identity``, ``token`` and
    ``expires_at``.  Raises ``ValueError`` on a bad room/identity,
    a bad TTL, or missing key/secret/url.  The token grants access to
    exactly one room for one identity — it is not a server credential.
    """
    if not isinstance(room, str) or ROOM_RE.fullmatch(room) is None:
        raise ValueError("room must be 1-128 chars of [A-Za-z0-9_.-]")
    if not isinstance(identity, str) or IDENTITY_RE.fullmatch(identity) is None:
        raise ValueError("identity must be 1-128 chars of [A-Za-z0-9_@.-]")
    if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError("ttl_seconds must be an integer between 60 and 86400")
    cfg = {
        "url": url or os.environ.get("LIVEKIT_URL", ""),
        "api_key": api_key or os.environ.get("LIVEKIT_API_KEY", ""),
        "api_secret": api_secret or os.environ.get("LIVEKIT_API_SECRET", ""),
    }
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise ValueError(
            "Missing LiveKit config: "
            + ", ".join({"url": "LIVEKIT_URL", "api_key": "LIVEKIT_API_KEY",
                         "api_secret": "LIVEKIT_API_SECRET"}[k] for k in missing)
        )
    if not cfg["url"].startswith(("https://", "http://", "wss://")):
        raise ValueError("LIVEKIT_URL must be an http(s) or wss URL")
    issued_at = now if now is not None else int(time.time())
    expires_at = issued_at + ttl_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": cfg["api_key"],
        "sub": identity,
        "iat": issued_at,
        "exp": expires_at,
        "jti": f"{identity}-{issued_at}",
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
        },
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    signature = hmac.new(
        cfg["api_secret"].encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    token = signing_input + "." + _b64url(signature)
    return {
        "url": cfg["url"],
        "room": room,
        "identity": identity,
        "token": token,
        "expires_at": expires_at,
        "status": "token_issued_no_live_peer",
        "note": "Token only. Join a real LiveKit server/Cloud room with "
        "it; no peer connection, SFU or media exists in this module.",
    }


def validate_room_token(
    token: str, *, api_secret: str | None = None, now: int | None = None
) -> dict[str, Any]:
    """Validate a LiveKit room token locally (shape, signature, expiry).

    Returns ``room``, ``identity``, ``expires_at`` and ``valid``.
    Raises ``ValueError`` on a malformed token, a bad signature or an
    expired token.  No network call is made and the token is not
    checked against a LiveKit server.
    """
    secret = api_secret or os.environ.get("LIVEKIT_API_SECRET", "")
    if not secret:
        raise ValueError("LIVEKIT_API_SECRET is required to validate a room token")
    if not isinstance(token, str):
        raise ValueError("token must be a string")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("token must have three JWT segments")
    signing_input = parts[0] + "." + parts[1]
    try:
        expected = hmac.new(
            secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        provided = _b64url_decode(parts[2])
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
    except (ValueError, KeyError) as exc:
        raise ValueError("token is not a readable JWT") from exc
    if header.get("alg") != "HS256":
        raise ValueError("token alg must be HS256")
    if not hmac.compare_digest(expected, provided):
        raise ValueError("token signature invalid")
    clock = now if now is not None else int(time.time())
    if int(payload.get("exp", 0)) <= clock:
        raise ValueError("token is expired")
    video = payload.get("video") or {}
    room = video.get("room", "")
    identity = payload.get("sub", "")
    if not room or not identity:
        raise ValueError("token carries no room/identity grant")
    return {
        "valid": True,
        "room": room,
        "identity": identity,
        "expires_at": int(payload["exp"]),
        "can_publish": bool(video.get("canPublish")),
        "can_subscribe": bool(video.get("canSubscribe")),
    }


def validate_signaling_message(message: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    """Validate one WebRTC signalling message (offer/answer/ICE).

    Same contract as ``daedalus_voice.validate_signaling_message``:
    signalling validation only, no media, no peer connection.
    """
    return _validate_signaling_message(message, session_id=session_id)


def video_status() -> dict[str, Any]:
    """Honest video status: config present or missing; no live check."""
    configured = all(
        os.environ.get(n)
        for n in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    )
    return {
        "service": "livekit-webrtc",
        "signalling": "validate_only_no_live_peer",
        "sdk_installed": sdk_available(),
        "configured": configured,
        "live_status": "READY" if configured else "MISSING_KEY",
    }


__all__ = [
    "LiveKitError",
    "sdk_available",
    "livekit_config_from_env",
    "issue_room_token",
    "validate_room_token",
    "validate_signaling_message",
    "validate_video_session",
    "video_status",
]
