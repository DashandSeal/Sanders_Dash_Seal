"""WSGI API for realtime/video + platform status (Phase 2 linker).

Routes
------
* ``GET  /api/realtime/status``   -- provider + config status (booleans only, no secrets).
* ``POST /api/realtime/room``     -- create a LiveKit/Daily room via the injected client.
                                     503 ``not_configured`` when no provider is set up.
* ``POST /api/realtime/token``    -- mint a session-scoped LiveKit token for one room +
                                     identity. 503 when LiveKit is not configured.
* ``POST /api/realtime/signaling/validate`` -- validate one offer/answer/ICE message
                                     against the worker contract (pure validation,
                                     no relay, no peer connection).
* ``GET  /api/platform/status``   -- combined platform-services status (see
                                     ``core_platform.platform_services``).
* ``GET  /api/video/status``      -- alias of /api/realtime/status for the voice page.

Everything here fails honestly: unconfigured providers answer 503 with an
``error`` code instead of pretending a call works, and no secret value is
ever returned.  Backends are injected (fakes in tests); the deployment
default wires clients from the environment with no transport, so room
operations raise ``RealtimeNotConfigured`` / ``RealtimeUnavailable``
until a real SDK/transport is installed.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .daedalus_voice import validate_signaling_message, validate_video_session
from .livekit_realtime import (
    DailyClient,
    FakeRoomService,
    LiveKitClient,
    RealtimeConfig,
    RealtimeError,
    RealtimeNotConfigured,
    validate_identity,
    validate_room_name,
)
from .platform_services import platform_status

MAX_BODY = 65536


def _json(start: Callable, status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    start(status, [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [body]


def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0 or length > MAX_BODY:
        raise ValueError("invalid body length")
    raw = environ["wsgi.input"].read(length)
    if len(raw) != length:
        raise ValueError("incomplete body")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def create_realtime_app(
    *,
    livekit: LiveKitClient | None = None,
    daily: DailyClient | None = None,
    config: RealtimeConfig | None = None,
    platform_env: dict[str, str] | None = None,
) -> Callable:
    """Build the realtime/platform WSGI app with injected (possibly fake) clients."""
    livekit = livekit if livekit is not None else LiveKitClient.from_env(platform_env)
    daily = daily if daily is not None else DailyClient.from_env(platform_env)
    config = config if config is not None else RealtimeConfig.from_env(platform_env)

    def app(environ: dict[str, Any], start: Callable) -> list[bytes]:
        path = environ.get("PATH_INFO") or "/"
        method = environ.get("REQUEST_METHOD") or "GET"

        if path in ("/api/realtime/status", "/api/video/status") and method == "GET":
            return _json(start, "200 OK", {"status": "ok", **config.status()})

        if path == "/api/platform/status" and method == "GET":
            return _json(start, "200 OK", {"status": "ok", **platform_status(platform_env)})

        if path == "/api/realtime/room" and method == "POST":
            try:
                data = _read_json(environ)
                room = validate_room_name(data.get("room"))
                configured_provider = config.provider if config.provider != "none" else ""
                provider = (data.get("provider") or configured_provider or "livekit").lower()
                if provider == "livekit":
                    result = livekit.create_room(room)
                elif provider == "daily":
                    result = daily.create_room(room)
                else:
                    return _json(start, "400 Bad Request", {"status": "error", "error": "unknown_provider"})
                return _json(start, "200 OK", {"status": "ok", "provider": provider, "room": result})
            except RealtimeNotConfigured as exc:
                return _json(start, "503 Service Unavailable", {"status": "error", "error": "not_configured", "detail": str(exc)})
            except RealtimeError as exc:
                return _json(start, "503 Service Unavailable", {"status": "error", "error": "unavailable", "detail": str(exc)})
            except (ValueError, KeyError) as exc:
                return _json(start, "400 Bad Request", {"status": "error", "error": "invalid_request", "detail": str(exc)})

        if path == "/api/realtime/token" and method == "POST":
            try:
                data = _read_json(environ)
                room = validate_room_name(data.get("room"))
                identity = validate_identity(data.get("identity"))
                token = livekit.issue_token(room=room, identity=identity)
                return _json(start, "200 OK", {
                    "status": "ok",
                    "provider": "livekit",
                    "room": room,
                    "identity": identity,
                    "url": livekit.url,
                    "token": token,
                })
            except RealtimeNotConfigured as exc:
                return _json(start, "503 Service Unavailable", {"status": "error", "error": "not_configured", "detail": str(exc)})
            except (ValueError, KeyError) as exc:
                return _json(start, "400 Bad Request", {"status": "error", "error": "invalid_request", "detail": str(exc)})

        if path == "/api/realtime/signaling/validate" and method == "POST":
            try:
                data = _read_json(environ)
                session = validate_video_session(
                    session_id=data.get("session_id", ""),
                    token=data.get("token", ""),
                )
                frame = validate_signaling_message(data.get("message") or {}, session_id=session["session_id"])
                return _json(start, "200 OK", {"status": "ok", "valid": True, "frame": frame})
            except (ValueError, KeyError) as exc:
                return _json(start, "400 Bad Request", {"status": "error", "error": "invalid_request", "detail": str(exc)})

        return _json(start, "404 Not Found", {"status": "error", "error": "not_found"})

    return app


def create_realtime_app_with_fakes() -> Callable:
    """Test/local helper: app wired to a FakeRoomService (no provider, no network)."""
    fake = FakeRoomService()
    livekit = LiveKitClient(url="https://livekit.example.invalid", api_key="APfake", api_secret="secret", transport=fake)
    return create_realtime_app(livekit=livekit, daily=DailyClient(transport=fake))


def application(environ: dict[str, Any], start: Callable) -> list[bytes]:
    """Deployment default: env-wired clients, no transport (honest 503s until configured)."""
    return create_realtime_app()(environ, start)
