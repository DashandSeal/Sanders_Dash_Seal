"""LiveKit / Daily.co realtime adapter for Sanders Dash & Seal.

Canonical LiveKit module (P3, 2026-11-13): this file owns
``LiveKitClient`` / ``DailyClient`` / ``RealtimeConfig`` used by the
live routes, and the single shared JWT implementation (``_b64url`` /
``_b64url_decode`` / ``_hs256_jwt``) that ``livekit_video`` imports.
The parallel ``livekit_video.py`` is retained, not merged away: it is
the token issue/validate + status helper referenced by the
service-linking table, and a full merge is unsafe -- see
``docs/LIVEKIT_CANONICAL.md`` for the concrete incompatibilities
(identity charset, TTL bounds, return shapes, error types).

Video / realtime linking layer (Phase 2).  No live peer, SFU, or provider
call is made here: every network operation goes through an injected
transport, and the default transport raises :class:`RealtimeNotConfigured`
when the provider is not configured.  Tests use the fake transports in
this module; a real deployment wires ``LiveKitClient`` with the
``livekit`` server SDK (``livekit==1.2.1`` / ``livekit-agents==1.8.11``,
see ``requirements-realtime.txt``) or the Daily REST API.

What this module DOES provide, without any key:

* ``issue_access_token`` -- a wire-compatible LiveKit access token
  (JWT, HS256, ``iss`` = API key, ``sub`` = identity, ``video`` grants).
  Implemented with the standard library only; when PyJWT is installed
  it is used instead (PyJWT==2.15.1 is already pinned in
  ``requirements.txt``).  The token is session-scoped: it is valid for
  exactly one room and one identity, and expires after ``ttl_seconds``.
* ``validate_room_name`` / ``validate_identity`` -- the same shape rules
  as the signalling contract in ``worker/src/webrtc.js`` (offer/answer/
  ICE, session-scoped) and ``core_platform.daedalus_voice.
  validate_video_session``: room/identity are 1-128 chars of
  ``[A-Za-z0-9_.-]``.
* ``LiveKitClient`` -- room create/list/delete through an injected
  transport.  With no transport and no configuration it reports
  ``status == "not_configured"`` and refuses to fabricate a room.
* ``DailyClient`` -- Daily.co fallback (REST room create through an
  injected transport).  Pricing note, from the task brief: $0.004 per
  participant-minute after 10,000 free minutes; no call is made and no
  minutes are consumed by this code.
* ``screen_share_requirements`` -- what the browser side needs for
  screen share (``getDisplayMedia``); the browser implementation lives
  in ``web/video.js``.

Signalling server requirement (read before going live)
-------------------------------------------------------
WebRTC signalling alone does not make a call.  A live call needs ONE of:

1. A LiveKit server (self-hosted on the Oracle instance, or LiveKit
   Cloud) reachable at ``LIVEKIT_URL``, with ``LIVEKIT_API_KEY`` /
   ``LIVEKIT_API_SECRET`` issued for it; or
2. A Daily.co domain + API key; or
3. The in-repo signalling relay in ``worker/src/webrtc.js`` (offer/
   answer/ICE relay only, no media server -- peers connect directly,
   which fails across symmetric NATs without a TURN server).

No signalling server, SFU, or peer exists in this repo today, and none
is fabricated here.  ``/api/realtime/status`` reports exactly which of
the above is configured.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RealtimeError(Exception):
    """Base error for the realtime adapter."""


class RealtimeNotConfigured(RealtimeError):
    """Raised when a realtime operation needs a provider that is not set up.

    This is an honest failure, not a fallback: callers must surface the
    503 / ``not_configured`` status instead of pretending a call works.
    """


class RealtimeUnavailable(RealtimeError):
    """Raised when the provider is configured but cannot be reached/used.

    E.g. the ``livekit`` server SDK is not installed in this environment,
    or the injected transport reports an error.  No live call is faked.
    """


# ---------------------------------------------------------------------------
# Validation (mirrors worker/src/webrtc.js + daedalus_voice.validate_video_session)
# ---------------------------------------------------------------------------

ROOM_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")


def validate_room_name(room: object) -> str:
    """Return ``room`` if it matches the signalling contract, else raise."""
    if not isinstance(room, str) or ROOM_RE.fullmatch(room) is None:
        raise ValueError("room must be 1-128 chars of [A-Za-z0-9_.-]")
    return room


def validate_identity(identity: object) -> str:
    """Return ``identity`` if it matches the signalling contract, else raise."""
    if not isinstance(identity, str) or IDENTITY_RE.fullmatch(identity) is None:
        raise ValueError("identity must be 1-128 chars of [A-Za-z0-9_.-]")
    return identity


# ---------------------------------------------------------------------------
# LiveKit access tokens (JWT HS256, stdlib; PyJWT when available)
# ---------------------------------------------------------------------------

LIVEKIT_VERSION = "1.2.1"          # livekit server SDK pinned in requirements-realtime.txt
LIVEKIT_AGENTS_VERSION = "1.8.11"  # livekit-agents pinned in requirements-realtime.txt
DEFAULT_TOKEN_TTL_SECONDS = 3600   # 1 hour, session-scoped


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """Decode unpadded base64url. Shared with ``livekit_video`` (P3
    2026-11-13): the JWT helpers live in this canonical module only, so
    both LiveKit implementations sign/verify the same way."""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _hs256_jwt(payload: dict[str, Any], secret: str) -> str:
    """Minimal HS256 JWT signer (stdlib only).

    Used when PyJWT is not installed.  The token this produces is a
    standard JWT and verifies against the LiveKit server the same way.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode("ascii")
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url(signature))
    return ".".join(segments)


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode (NOT verify) a JWT payload.  Test/debug helper only."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("not a JWT")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode())


def issue_access_token(
    *,
    api_key: str,
    api_secret: str,
    room: str,
    identity: str,
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    can_publish: bool = True,
    can_subscribe: bool = True,
    can_publish_data: bool = True,
    now: int | None = None,
) -> str:
    """Mint a session-scoped LiveKit access token for one room + identity.

    Claims follow the LiveKit wire format: ``iss`` is the API key,
    ``sub`` the identity, ``jti`` a fresh id, ``video.roomJoin`` /
    ``video.room`` restrict the token to ``room``.  Raises ``ValueError``
    on a bad room/identity/ttl and ``RealtimeNotConfigured`` when the key
    or secret is missing/empty.  No network call is made.
    """
    if not api_key or not api_secret:
        raise RealtimeNotConfigured(
            "LiveKit API key/secret are not configured; set LIVEKIT_API_KEY "
            "and LIVEKIT_API_SECRET (see deploy/sanders-dash-seal.env.example)"
        )
    room = validate_room_name(room)
    identity = validate_identity(identity)
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0 or ttl_seconds > 86400:
        raise ValueError("ttl_seconds must be an int in 1..86400")
    issued_at = int(time.time()) if now is None else int(now)
    payload: dict[str, Any] = {
        "iss": api_key,
        "sub": identity,
        "jti": str(uuid.uuid4()),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + ttl_seconds,
        "video": {
            "roomJoin": True,
            "room": room,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
            "canPublishData": can_publish_data,
        },
    }
    try:
        import jwt  # PyJWT, pinned in requirements.txt; preferred when present

        return jwt.encode(payload, api_secret, algorithm="HS256")
    except ImportError:
        return _hs256_jwt(payload, api_secret)


# ---------------------------------------------------------------------------
# Configuration (env names only; never log or return secret values)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealtimeConfig:
    """Realtime provider configuration read from the environment.

    ``*_configured`` flags report presence only.  Secret *values* are
    never stored in a reportable field and never appear in ``status()``.
    """

    livekit_url: str = ""
    livekit_api_key_set: bool = False
    livekit_api_secret_set: bool = False
    daily_api_key_set: bool = False
    daily_domain: str = ""
    worker_signalling_available: bool = True  # worker/src/webrtc.js ships in-repo

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "RealtimeConfig":
        src = os.environ if env is None else env
        return cls(
            livekit_url=(src.get("LIVEKIT_URL") or "").strip(),
            livekit_api_key_set=bool((src.get("LIVEKIT_API_KEY") or "").strip()),
            livekit_api_secret_set=bool((src.get("LIVEKIT_API_SECRET") or "").strip()),
            daily_api_key_set=bool((src.get("DAILY_API_KEY") or "").strip()),
            daily_domain=(src.get("DAILY_DOMAIN") or "").strip(),
        )

    @property
    def livekit_configured(self) -> bool:
        return bool(self.livekit_url and self.livekit_api_key_set and self.livekit_api_secret_set)

    @property
    def daily_configured(self) -> bool:
        return bool(self.daily_api_key_set and self.daily_domain)

    @property
    def provider(self) -> str:
        if self.livekit_configured:
            return "livekit"
        if self.daily_configured:
            return "daily"
        return "none"

    def status(self) -> dict[str, Any]:
        """Public status dict: provider + booleans only, no secrets."""
        return {
            "provider": self.provider,
            "livekit_configured": self.livekit_configured,
            "livekit_url_set": bool(self.livekit_url),
            "daily_configured": self.daily_configured,
            "worker_signalling_available": self.worker_signalling_available,
            "signalling_server_required": True,
            "livekit_sdk_version": LIVEKIT_VERSION,
            "livekit_agents_version": LIVEKIT_AGENTS_VERSION,
            "note": (
                "No signalling server / SFU is running in this repo. "
                "A live call needs LIVEKIT_URL (self-hosted or LiveKit Cloud) "
                "or a Daily.co domain, or the in-repo relay in "
                "worker/src/webrtc.js plus a TURN server for NAT traversal."
            ),
        }


# ---------------------------------------------------------------------------
# Fake transports (tests + local verification; record calls, make no network)
# ---------------------------------------------------------------------------


@dataclass
class FakeRoomService:
    """In-memory stand-in for LiveKit RoomService / Daily REST rooms.

    Records every call in ``calls`` and keeps created rooms in ``rooms``.
    """

    rooms: dict[str, dict[str, Any]] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def create_room(self, name: str, **options: Any) -> dict[str, Any]:
        validate_room_name(name)
        self.calls.append({"op": "create_room", "name": name, **options})
        room = {"name": name, "sid": f"RM_fake_{name}", "empty_timeout": options.get("empty_timeout", 300)}
        self.rooms[name] = room
        return dict(room)

    def list_rooms(self) -> list[dict[str, Any]]:
        self.calls.append({"op": "list_rooms"})
        return [dict(r) for r in self.rooms.values()]

    def delete_room(self, name: str) -> bool:
        validate_room_name(name)
        self.calls.append({"op": "delete_room", "name": name})
        return self.rooms.pop(name, None) is not None


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


class LiveKitClient:
    """LiveKit room management + token issuance.

    ``transport`` is any object with ``create_room`` / ``list_rooms`` /
    ``delete_room`` (the real ``livekit`` SDK RoomService, or
    ``FakeRoomService`` in tests).  With ``transport=None`` the client
    only mints tokens from explicit key/secret arguments and refuses
    room operations with :class:`RealtimeNotConfigured` -- it never
    invents a room or a peer.
    """

    def __init__(
        self,
        *,
        url: str = "",
        api_key: str = "",
        api_secret: str = "",
        transport: Any | None = None,
    ) -> None:
        self.url = url.strip()
        self.api_key = api_key
        self.api_secret = api_secret
        self.transport = transport

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, transport: Any | None = None) -> "LiveKitClient":
        src = os.environ if env is None else env
        return cls(
            url=src.get("LIVEKIT_URL") or "",
            api_key=src.get("LIVEKIT_API_KEY") or "",
            api_secret=src.get("LIVEKIT_API_SECRET") or "",
            transport=transport,
        )

    @property
    def configured(self) -> bool:
        return bool(self.url and self.api_key and self.api_secret)

    def _require_transport(self) -> Any:
        if self.transport is None:
            if not self.configured:
                raise RealtimeNotConfigured(
                    "LiveKit is not configured (LIVEKIT_URL / LIVEKIT_API_KEY / "
                    "LIVEKIT_API_SECRET). No room was created and no peer was contacted."
                )
            raise RealtimeUnavailable(
                "LiveKit is configured but the livekit server SDK is not "
                "installed in this environment (livekit==%s). Install "
                "requirements-realtime.txt or inject a transport." % LIVEKIT_VERSION
            )
        return self.transport

    def create_room(self, name: str, **options: Any) -> dict[str, Any]:
        validate_room_name(name)
        return dict(self._require_transport().create_room(name, **options))

    def list_rooms(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._require_transport().list_rooms()]

    def delete_room(self, name: str) -> bool:
        validate_room_name(name)
        return bool(self._require_transport().delete_room(name))

    def issue_token(self, *, room: str, identity: str, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> str:
        return issue_access_token(
            api_key=self.api_key,
            api_secret=self.api_secret,
            room=room,
            identity=identity,
            ttl_seconds=ttl_seconds,
        )

    def room_url(self, room: str) -> str:
        """Browser join URL base for ``room`` (needs a token from ``issue_token``)."""
        validate_room_name(room)
        if not self.url:
            raise RealtimeNotConfigured("LIVEKIT_URL is not set; no join URL exists")
        return self.url.rstrip("/") + "/room/" + room


class DailyClient:
    """Daily.co fallback (REST rooms through an injected transport).

    Pricing (task brief): $0.004 per participant-minute after 10,000
    free minutes.  This client makes no call and consumes no minutes
    without a configured key + transport.
    """

    FREE_MINUTES = 10_000
    PRICE_PER_PARTICIPANT_MINUTE_USD = 0.004

    def __init__(self, *, api_key: str = "", domain: str = "", transport: Any | None = None) -> None:
        self.api_key = api_key
        self.domain = domain.strip()
        self.transport = transport

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, transport: Any | None = None) -> "DailyClient":
        src = os.environ if env is None else env
        return cls(
            api_key=src.get("DAILY_API_KEY") or "",
            domain=src.get("DAILY_DOMAIN") or "",
            transport=transport,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.domain)

    def create_room(self, name: str, **options: Any) -> dict[str, Any]:
        validate_room_name(name)
        if self.transport is None:
            if not self.configured:
                raise RealtimeNotConfigured(
                    "Daily.co is not configured (DAILY_API_KEY / DAILY_DOMAIN). "
                    "No room was created."
                )
            raise RealtimeUnavailable("Daily.co is configured but no HTTP transport is wired in this environment.")
        room = self.transport.create_room(name, **options)
        return {"provider": "daily", "domain": self.domain, **dict(room)}

    def room_url(self, name: str) -> str:
        validate_room_name(name)
        if not self.domain:
            raise RealtimeNotConfigured("DAILY_DOMAIN is not set; no join URL exists")
        return "https://%s.daily.co/%s" % (self.domain, name)


# ---------------------------------------------------------------------------
# Screen share (browser capability contract; implementation in web/video.js)
# ---------------------------------------------------------------------------


def screen_share_requirements() -> dict[str, Any]:
    """What the browser side needs for screen share.  No capture happens here."""
    return {
        "api": "navigator.mediaDevices.getDisplayMedia",
        "requires": ["secure context (HTTPS or localhost)", "user gesture", "user picks a screen/window/tab"],
        "video_only": True,
        "audio_note": "System-audio capture via getDisplayMedia is browser-dependent (Chrome: optional, Safari/Firefox: limited). Do not promise it.",
        "implemented_in": "web/video.js (startScreenShare)",
        "server_side": "none -- the shared track is published over the same WebRTC/LiveKit session as camera/mic",
    }
