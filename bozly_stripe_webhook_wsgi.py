"""Bozly's independent Stripe WSGI receiver.

Each route is mapped by protected deployment configuration to exactly one legal
entity and webhook signing secret. Untrusted Stripe metadata never chooses an LLC.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import unquote

from bozly_cfo import BozlyCFOCore, BozlyLedgerError

BASE_PATH = "/v1/telemetry/webhooks/"
MAX_EVENT_BYTES = 1024 * 1024


def routes():
    raw = os.environ.get("BOZLY_STRIPE_ROUTES_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
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
    except (ValueError, TypeError):
        return {}


def valid_signature(raw_body: bytes, header: str, secret: str) -> bool:
    """Authenticate the unmodified body against Stripe's signed timestamp."""
    if not isinstance(header, str) or not secret or not header:
        return False
    parts = []
    for segment in header.split(","):
        key, sep, value = segment.strip().partition("=")
        if sep:
            parts.append((key, value))
    stamps = [v for k, v in parts if k == "t"]
    signatures = [v for k, v in parts if k == "v1" and len(v) == 64]
    if len(stamps) != 1 or not signatures:
        return False
    try:
        timestamp = int(stamps[0])
    except ValueError:
        return False
    now = int(time.time())
    if timestamp <= 0 or abs(now - timestamp) > 300:
        return False
    signed = str(timestamp).encode("ascii") + b"." + raw_body
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(digest, s) for s in signatures)


class RobustBozlyRouter:
    def __init__(self, ledger: BozlyCFOCore | None = None):
        self.engine_version = "BOZLY-CFO-v2.5.0-ROBUST-35"
        self.ledger = ledger

    def process_secure_event(self, raw_body, sig_header, route_id):
        route = routes().get(route_id)
        if route is None:
            return 404, {"status": "ROUTE_NOT_CONFIGURED"}
        if not valid_signature(raw_body, sig_header, route["signing_secret"]):
            return 400, {"status": "SIGNATURE_REJECTED"}
        try:
            event = json.loads(raw_body)
            if not isinstance(event, dict):
                return 400, {"status": "INVALID_EVENT"}
        except (ValueError, UnicodeDecodeError):
            return 400, {"status": "INVALID_EVENT"}
        try:
            ledger = self.ledger or BozlyCFOCore()
            receipt = ledger.reconcile_transaction(
                event,
                route_id=route_id,
                entity_id=route["entity_id"],
                jurisdiction=route["jurisdiction"],
                body_sha256=hashlib.sha256(raw_body).hexdigest(),
            )
        except (ValueError, TypeError, BozlyLedgerError):
            return 400, {"status": "INVALID_OR_CONFLICTING_EVENT"}
        except Exception:
            # Stripe can retry; do not acknowledge failed persistent writes.
            return 503, {"status": "LEDGER_UNAVAILABLE"}
        return 200, receipt


bozly_router = RobustBozlyRouter()


def application(environ, start_response):
    def send(code, obj):
        status = {
            200: "200 OK", 400: "400 Bad Request",
            404: "404 Not Found", 405: "405 Method Not Allowed",
            413: "413 Content Too Large", 415: "415 Unsupported Media Type",
            503: "503 Service Unavailable",
        }[code]
        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        start_response(status, [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(raw))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [raw]

    if environ.get("REQUEST_METHOD") != "POST":
        return send(405, {"status": "METHOD_NOT_ALLOWED"})
    path = environ.get("PATH_INFO", "")
    if not path.startswith(BASE_PATH):
        return send(404, {"status": "UNKNOWN_ROUTE"})
    route_id = unquote(path[len(BASE_PATH):])
    if not route_id or "/" in route_id:
        return send(404, {"status": "UNKNOWN_ROUTE"})
    if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
        return send(415, {"status": "JSON_REQUIRED"})
    try:
        size = int(environ.get("CONTENT_LENGTH", "-1"))
    except (ValueError, TypeError):
        return send(400, {"status": "INVALID_CONTENT_LENGTH"})
    if size < 1 or size > MAX_EVENT_BYTES:
        return send(413, {"status": "INVALID_EVENT_SIZE"})
    try:
        body = environ["wsgi.input"].read(size)
    except Exception:
        return send(400, {"status": "BODY_UNREADABLE"})
    if len(body) != size:
        return send(400, {"status": "BODY_INCOMPLETE"})
    code, receipt = bozly_router.process_secure_event(
        body, environ.get("HTTP_STRIPE_SIGNATURE", ""), route_id
    )
    return send(code, receipt)
