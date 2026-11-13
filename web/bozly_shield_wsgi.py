"""Native Labyrinth Shield WSGI entrypoint for Bozly services.

Preserves the owner's LabyrinthShield.evaluate_packet and local forensic
recording. Assistant-added whole-service isolation and arbitrary 1 MB
request gate are removed. The owner's Shield still rejects suspicious
requests while legitimate Bozly operations remain available.
"""
from __future__ import annotations

import hashlib
import io
import json

from labyrinth_shield import LabyrinthShield
from core_platform.bozly.bozly_security_response import record_request_rejection
from core_platform.bozly.bozly_human_api import application as human_application
from .bozly_stripe_webhook_wsgi import application as webhook_application

SHIELD = LabyrinthShield()


def _reject(start_response, status: str, code: str):
    payload = json.dumps({"status": "REJECTED", "error": code},
                         separators=(",", ":")).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(payload))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [payload]


def _wrap(target):
    def application(environ, start_response):
        address = str(environ.get("REMOTE_ADDR", "UNKNOWN"))
        declared = environ.get("CONTENT_LENGTH", "")
        if declared and (not declared.isascii() or not declared.isdigit()):
            return _reject(start_response, "400 Bad Request",
                           "INVALID_CONTENT_LENGTH")

        size = int(declared) if declared else 0
        if size:
            body = environ["wsgi.input"].read(size)
            if len(body) != size:
                return _reject(start_response, "400 Bad Request",
                               "REQUEST_BODY_INCOMPLETE")
            envelope = body.decode("utf-8", "replace")
            environ["wsgi.input"] = io.BytesIO(body)
        else:
            body = b""
            envelope = ""

        if not SHIELD.evaluate_packet(address, envelope):
            try:
                record_request_rejection(
                    remote_address=address,
                    path=str(environ.get("PATH_INFO", "")),
                    reason="OWNER_LABYRINTH_PATTERN_REJECTION",
                    request_sha256=hashlib.sha256(body).hexdigest(),
                )
            except (OSError, ValueError):
                # The Shield decision is still applied if the local audit
                # ledger is temporarily unavailable; never admit rejected traffic.
                pass
            return _reject(start_response, "403 Forbidden",
                           "LABYRINTH_SHIELD_REJECTION")
        return target(environ, start_response)
    return application


human_application_shielded = _wrap(human_application)
webhook_application_shielded = _wrap(webhook_application)
