"""WSGI API for realtime/video + platform status (Phase 2 linker).

Routes
------
* ``GET  /api/realtime/status``   -- provider + config status (booleans only, no secrets).
* ``POST /api/realtime/room``     -- create a LiveKit/Daily room via the injected client.
                                     503 ``not_configured`` when no provider is set up.
* ``POST /api/realtime/token``    -- mint a session-scoped LiveKit token for one room +
                                     the authenticated identity. 503 when LiveKit is
                                     not configured.

Issuance security (Phase A remediation, 2026-11-24 — inventory findings
F-1/F-2/F-11): room creation and token issuance are enforced HERE, at the
module that performs them, so no router composition can bypass them:

* **Gate** — when a provider is configured, issuance requires the
  ``voice_video_provider`` approval gate (injected ``gate_approved``).
  Any failure while evaluating the provider or the gate denies with 503
  ``approval_required`` (fail closed); an unwired gate callable counts
  as unapproved.
* **Authentication** — issuance requires an authenticated platform
  session (injected ``authenticate``, the customer app's session
  verifier). An unwired authenticator refuses every issuance (401).
* **Identity binding** — the token's identity is the session's account
  username, never caller-supplied. A body asserting a different identity
  is refused 403 ``identity_mismatch``; an omitted identity is bound to
  the session.
* **Origin** — when ``allowed_origins`` is wired, a POST whose Origin
  is not in the set is refused 403 ``origin_denied`` (the customer app's
  pattern).
* **Audit** — every issuance decision, granted or denied, is written to
  the injected Glass-Box audit chain. A grant whose receipt cannot be
  written is not issued (503 ``audit_unavailable``): no record, no token.

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


def _approval_payload() -> dict[str, Any]:
    """The deployment's established gate-denial payload (503 shape)."""
    try:
        from .ai_platform_approval import http_failure
        payload = http_failure("voice_video_provider")
        return {k: v for k, v in payload.items() if k != "status"}
    except Exception:
        return {"error": "approval_required", "gate": "voice_video_provider"}


class _ListAudit:
    """In-memory audit stub for the fakes helper only: records receipts
    in a list so local/test issuance satisfies the no-record-no-token
    rule without touching a real evidence store."""

    def __init__(self) -> None:
        self.receipts: list[dict[str, Any]] = []

    def preserve(self, event, **kwargs):
        self.receipts.append({"event": event, **kwargs})
        return "stub-receipt"


def create_realtime_app(
    *,
    livekit: LiveKitClient | None = None,
    daily: DailyClient | None = None,
    config: RealtimeConfig | None = None,
    platform_env: dict[str, str] | None = None,
    authenticate: Callable | None = None,
    audit: Any | None = None,
    gate_approved: Callable | None = None,
    allowed_origins: frozenset | None = None,
) -> Callable:
    """Build the realtime/platform WSGI app with injected (possibly fake) clients.

    ``authenticate`` / ``audit`` / ``gate_approved`` / ``allowed_origins``
    wire the issuance controls described in the module docstring. The
    deployment injects the platform session verifier, the Glass-Box
    audit chain, the ``voice_video_provider`` gate check and the site's
    origin set. Defaults are fail closed: no authenticator -> no
    issuance; no gate callable -> a configured provider counts as
    unapproved; no audit -> a grant cannot be recorded, so it is not
    issued.
    """
    livekit = livekit if livekit is not None else LiveKitClient.from_env(platform_env)
    daily = daily if daily is not None else DailyClient.from_env(platform_env)
    config = config if config is not None else RealtimeConfig.from_env(platform_env)

    def _record(stage: str, **fields: Any) -> bool:
        """Write one Glass-Box receipt; False when unwired or failed."""
        if audit is None:
            return False
        try:
            audit.preserve({"stage": stage, **fields})
            return True
        except Exception:
            return False

    def _gate_denial() -> str | None:
        """Reason issuance is gate-denied, or None when it may proceed.

        Fail closed: an exception while reading the provider or the
        gate denies, exactly as an unapproved gate does. When no
        provider is configured there is nothing for the gate to guard;
        the handlers then answer their honest ``not_configured`` 503.
        """
        try:
            provider_name = config.provider
        except Exception:
            return "gate_check_failed"
        if provider_name == "none":
            return None
        try:
            approved = bool(gate_approved()) if gate_approved is not None else False
        except Exception:
            approved = False
        return None if approved else "approval_required"

    def _session_identity(environ: dict[str, Any]) -> str | None:
        if authenticate is None:
            return None
        try:
            identity = authenticate(environ)
        except Exception:
            return None
        return identity if isinstance(identity, str) and identity else None

    def _issuance_guard(environ: dict[str, Any], start: Callable,
                        stage: str, room: str):
        """Gate -> session -> origin, in that order, before any issuance.

        Returns ``(identity, None)`` when issuance may proceed, or
        ``(None, response)`` with the denial already audited.
        """
        denial = _gate_denial()
        if denial is not None:
            _record(stage, room=room, identity=None,
                    gate="voice_video_provider", outcome="denied", reason=denial)
            return None, _json(start, "503 Service Unavailable",
                               _approval_payload())
        identity = _session_identity(environ)
        if identity is None:
            _record(stage, room=room, identity=None,
                    gate="voice_video_provider", outcome="denied",
                    reason="sign_in_required")
            return None, _json(start, "401 Unauthorized",
                               {"status": "error", "error": "sign_in_required"})
        if (allowed_origins is not None
                and environ.get("HTTP_ORIGIN") not in allowed_origins):
            _record(stage, room=room, identity=identity,
                    gate="voice_video_provider", outcome="denied",
                    reason="origin_denied")
            return None, _json(start, "403 Forbidden",
                               {"status": "error", "error": "origin_denied"})
        return identity, None

    def app(environ: dict[str, Any], start: Callable) -> list[bytes]:
        path = environ.get("PATH_INFO") or "/"
        method = environ.get("REQUEST_METHOD") or "GET"

        if path in ("/api/realtime/status", "/api/video/status") and method == "GET":
            return _json(start, "200 OK", {"status": "ok", **config.status()})

        if path == "/api/platform/status" and method == "GET":
            return _json(start, "200 OK", {"status": "ok", **platform_status(platform_env)})

        if path == "/api/realtime/room" and method == "POST":
            room = None
            identity = None
            try:
                data = _read_json(environ)
                room = validate_room_name(data.get("room"))
                identity, denial_response = _issuance_guard(
                    environ, start, "REALTIME_ROOM_DENIED", room)
                if denial_response is not None:
                    return denial_response
                configured_provider = config.provider if config.provider != "none" else ""
                provider = (data.get("provider") or configured_provider or "livekit").lower()
                if provider == "livekit":
                    result = livekit.create_room(room)
                elif provider == "daily":
                    result = daily.create_room(room)
                else:
                    return _json(start, "400 Bad Request", {"status": "error", "error": "unknown_provider"})
                if not _record("REALTIME_ROOM_CREATED", room=room,
                               identity=identity, provider=provider,
                               gate="voice_video_provider", outcome="granted"):
                    return _json(start, "503 Service Unavailable",
                                 {"status": "error", "error": "audit_unavailable"})
                return _json(start, "200 OK", {"status": "ok", "provider": provider, "room": result})
            except RealtimeNotConfigured as exc:
                _record("REALTIME_ROOM_DENIED", room=room, identity=identity,
                        gate="voice_video_provider", outcome="denied",
                        reason="not_configured")
                return _json(start, "503 Service Unavailable", {"status": "error", "error": "not_configured", "detail": str(exc)})
            except RealtimeError as exc:
                _record("REALTIME_ROOM_DENIED", room=room, identity=identity,
                        gate="voice_video_provider", outcome="denied",
                        reason="unavailable")
                return _json(start, "503 Service Unavailable", {"status": "error", "error": "unavailable", "detail": str(exc)})
            except (ValueError, KeyError) as exc:
                return _json(start, "400 Bad Request", {"status": "error", "error": "invalid_request", "detail": str(exc)})

        if path == "/api/realtime/token" and method == "POST":
            room = None
            identity = None
            try:
                data = _read_json(environ)
                room = validate_room_name(data.get("room"))
                identity, denial_response = _issuance_guard(
                    environ, start, "REALTIME_TOKEN_DENIED", room)
                if denial_response is not None:
                    return denial_response
                asserted = data.get("identity")
                if asserted is not None and asserted != identity:
                    _record("REALTIME_TOKEN_DENIED", room=room, identity=identity,
                            asserted_identity=asserted,
                            gate="voice_video_provider", outcome="denied",
                            reason="identity_mismatch")
                    return _json(start, "403 Forbidden",
                                 {"status": "error", "error": "identity_mismatch"})
                token = livekit.issue_token(room=room, identity=identity)
                if not _record("REALTIME_TOKEN_ISSUED", room=room,
                               identity=identity, provider="livekit",
                               gate="voice_video_provider", outcome="granted"):
                    return _json(start, "503 Service Unavailable",
                                 {"status": "error", "error": "audit_unavailable"})
                return _json(start, "200 OK", {
                    "status": "ok",
                    "provider": "livekit",
                    "room": room,
                    "identity": identity,
                    "url": livekit.url,
                    "token": token,
                })
            except RealtimeNotConfigured as exc:
                _record("REALTIME_TOKEN_DENIED", room=room, identity=identity,
                        gate="voice_video_provider", outcome="denied",
                        reason="not_configured")
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
    """Test/local helper: app wired to a FakeRoomService (no provider, no network).

    Explicitly local: a stub session (identity ``local-test-user``), a
    stub in-memory audit and an approved gate stand in for the platform
    wiring, so the helper exercises issuance without a real provider.
    Production compositions inject the real controls instead.
    """
    fake = FakeRoomService()
    livekit = LiveKitClient(url="https://livekit.example.invalid", api_key="APfake", api_secret="secret", transport=fake)
    return create_realtime_app(
        livekit=livekit, daily=DailyClient(transport=fake),
        authenticate=lambda environ: "local-test-user",
        audit=_ListAudit(), gate_approved=lambda: True)


def application(environ: dict[str, Any], start: Callable) -> list[bytes]:
    """Deployment default: env-wired clients, no transport (honest 503s until configured)."""
    return create_realtime_app()(environ, start)
