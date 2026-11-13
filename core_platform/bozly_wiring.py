"""Wire Bozly, the platform CFO, into the live webhook path.

Bozly is an event-driven financial observation and reconciliation engine.
It records previously signature-verified Stripe events in a SQLite WAL
hash-linked ledger, in integer minor units. It never initiates a charge,
never changes Stripe settings, and never infers a payout from a webhook.

Wiring rules (owner direction, 2026-11-13):

- Only events that already passed Stripe signature verification in
  ``core_platform.stream_api`` are handed to Bozly. An unverified event
  is never recorded: signature failure answers 401 before this module
  is ever called.
- Bozly is an observation, not a gate. If Bozly is not configured, or
  its ledger is unavailable, the webhook still settles normally and the
  response says so honestly (``bozly: {"status": "not_configured"}`` or
  ``"ledger_unavailable"``). Bozly must never fail a verified webhook.
- Fail-closed without keys. Live CFO operation needs
  ``BOZLY_STRIPE_ROUTES_JSON`` (per-route signing secrets, entity and
  jurisdiction, server-owned) and, for the traceback component, its
  source/storage keys. None are set by this module and none are read
  back here: only a boolean ``keys_configured`` is ever reported.
- No traceback internals, file paths, or stack traces ever appear in
  any response, log line, or status payload from this module. Errors
  are generic codes only.
- No secret value is ever returned, logged, or included in a status
  payload. Route ids are configuration names, not secrets.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("bozly_wiring")

ENGINE_ID = "BOZLY-CFO-v2.5.0-ROBUST-35"


def parse_routes(raw=None):
    """Parse and validate BOZLY_STRIPE_ROUTES_JSON (server-owned config).

    Returns ``{route_id: {"entity_id", "jurisdiction", "signing_secret"}}``
    for well-formed routes only. Anything malformed, missing, or
    non-dict returns ``{}`` — never raises, never logs the value.
    """
    if raw is None:
        raw = os.environ.get("BOZLY_STRIPE_ROUTES_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    allowed = {}
    for route_id, cfg in data.items():
        if (not isinstance(route_id, str) or not route_id.isascii()
                or not route_id.replace("-", "").replace("_", "").isalnum()
                or not isinstance(cfg, dict)):
            continue
        if not all(isinstance(cfg.get(k), str) and cfg[k] for k in
                   ("entity_id", "jurisdiction", "signing_secret")):
            continue
        allowed[route_id] = cfg
    return allowed


def resolve_route_id(routes, explicit=None):
    """Pick the Bozly route for the main webhook.

    ``BOZLY_ROUTE_ID`` names it explicitly. With exactly one configured
    route that route is the default. With several routes and no explicit
    choice the route is ambiguous and ``None`` is returned (fail-closed:
    Bozly records nothing rather than guessing an entity).
    """
    if explicit:
        return explicit if explicit in routes else None
    env_route = os.environ.get("BOZLY_ROUTE_ID")
    if env_route:
        return env_route if env_route in routes else None
    if len(routes) == 1:
        return next(iter(routes))
    return None


class BozlyRecorder:
    """Best-effort recorder of verified Stripe events into the Bozly ledger.

    Construction never raises and never touches the ledger database:
    the CFO core is created lazily on the first recording, and only
    when at least one route is configured. Every public method returns
    a plain dict and never raises into the webhook path.
    """

    def __init__(self, db_path=None, route_id=None, routes=None):
        self.db_path = db_path
        self.routes = routes if routes is not None else parse_routes()
        self.route_id = resolve_route_id(self.routes, route_id)
        self._core = None

    @property
    def configured(self):
        return bool(self.routes) and self.route_id is not None

    def _core_or_none(self):
        if self._core is not None:
            return self._core
        if not self.configured:
            return None
        try:
            from core_platform.bozly.bozly_cfo import BozlyCFOCore
            self._core = BozlyCFOCore(
                db_path=self.db_path or os.environ.get("BOZLY_DB_PATH"))
        except Exception:
            logger.warning("Bozly CFO ledger unavailable")
            self._core = None
        return self._core

    def record_verified_event(self, event, raw_body):
        """Record a previously signature-verified Stripe event.

        ``event`` must be the plain-dict event Stripe already verified;
        ``raw_body`` is the exact signed bytes, for the body digest.
        Returns ``{"available": bool, "status": ..., "route_id": ...}``
        where status is RECORDED, DUPLICATE, not_configured, or
        ledger_unavailable. Never raises.
        """
        if not self.configured:
            return {"available": False, "status": "not_configured",
                    "route_id": self.route_id}
        core = self._core_or_none()
        if core is None:
            return {"available": False, "status": "ledger_unavailable",
                    "route_id": self.route_id}
        route = self.routes[self.route_id]
        try:
            if not isinstance(raw_body, (bytes, bytearray)):
                raise ValueError("raw body required")
            receipt = core.reconcile_transaction(
                event,
                route_id=self.route_id,
                entity_id=route["entity_id"],
                jurisdiction=route["jurisdiction"],
                body_sha256=hashlib.sha256(bytes(raw_body)).hexdigest(),
            )
            try:
                reconciled = core.process_pending()
            except Exception:
                reconciled = None
            result = {"available": True,
                      "status": receipt.get("transaction_status"),
                      "route_id": self.route_id,
                      "event_id": receipt.get("event_id")}
            if reconciled is not None:
                result["reconciled"] = reconciled
            return result
        except Exception:
            logger.warning("Bozly CFO ledger unavailable")
            return {"available": False, "status": "ledger_unavailable",
                    "route_id": self.route_id}


def build_recorder_from_env(db_path=None):
    """Build a recorder from the current environment, never raising."""
    try:
        return BozlyRecorder(db_path=db_path)
    except Exception:
        return None


def bozly_status(db_path=None):
    """Honest, read-only Bozly status for /api/bozly/status and
    /api/platform/status. No secret values, no file paths, no internals.

    ``db_present`` is a boolean only: the ledger file path is never
    returned. ``keys_configured`` is a boolean only.
    """
    routes = parse_routes()
    route_id = resolve_route_id(routes)
    configured = bool(routes) and route_id is not None
    # Ledger presence: check the configured path first, then the
    # conventional locations (the wsgi composition root writes the
    # ledger to <repo>/data/bozly_ledger.db; the CFO core default is
    # its own path). Only a boolean is reported, never a path.
    candidates = []
    if db_path:
        candidates.append(Path(db_path))
    db_env = os.environ.get("BOZLY_DB_PATH")
    if db_env:
        candidates.append(Path(db_env))
    candidates.append(
        Path(__file__).resolve().parent.parent / "data" / "bozly_ledger.db")
    try:
        from core_platform.bozly.bozly_cfo import DEFAULT_DB
        candidates.append(Path(DEFAULT_DB))
    except Exception:
        pass
    db_present = False
    for candidate in candidates:
        try:
            if candidate.exists():
                db_present = True
                break
        except (OSError, ValueError):
            continue
    return {
        "engine": ENGINE_ID,
        "wired": True,
        "configured": configured,
        "routes_configured": len(routes),
        "route_ids": sorted(routes),
        "route_id": route_id,
        "db_present": db_present,
        "keys_configured": bool(os.environ.get("BOZLY_STRIPE_ROUTES_JSON")),
        "live": configured,
        "note": ("Bozly records only signature-verified Stripe events, "
                 "as observations. It never initiates a charge and never "
                 "infers a payout."),
    }
