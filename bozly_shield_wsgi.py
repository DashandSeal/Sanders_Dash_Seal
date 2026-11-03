"""Native Labyrinth Shield WSGI entrance for existing Bozly services.

Wraps real native WSGI applications without modifying their original code.
Uses the exact owner-supplied LabyrinthShield.evaluate_packet implementation.
When the Minotaur records a local file change, shared isolation state makes
requests fail closed until an owner-controlled recovery is performed.
"""
from __future__ import annotations

import hashlib
import io
import json
import os

from labyrinth_shield import LabyrinthShield
from bozly_security_response import isolation_state, record_request_rejection
from bozly_human_api import application as human_application
from bozly_stripe_webhook_wsgi import application as webhook_application

SHIELD = LabyrinthShield()
MAX_CAPTURE = 1024 * 1024


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
        if isolation_state()["isolated"]:
            return _reject(start_response, "503 Service Unavailable",
                           "MINOTAUR_SECURITY_ISOLATION_ACTIVE")

        address = environ.get("REMOTE_ADDR", "UNKNOWN")
        declared = environ.get("CONTENT_LENGTH", "")
        if declared and (not declared.isascii() or not declared.isdigit()
                         or int(declared) > MAX_CAPTURE):
            return _reject(start_response, "413 Content Too Large",
                           "REQUEST_SIZE_EXCEEDS_SECURITY_LIMIT")

        size = int(declared) if declared else 0
        if size > 0:
            # Restoring the stream allows the original Bozly service to
            # authenticate payment webhooks and JSON requests unmodified.
            body = environ["wsgi.input"].read(size)
            if len(body) != size:
                return _reject(start_response, "400 Bad Request",
                               "REQUEST_BODY_INCOMPLETE")
            envelope = body.decode("utf-8", "replace")
            environ["wsgi.input"] = io.BytesIO(body)
            denied_digest = hashlib.sha256(body).hexdigest()
        else:
            envelope = ""
            denied_digest = hashlib.sha256(b"").hexdigest()

        if not SHIELD.evaluate_packet(str(address), envelope):
            # Silent local forensic evidence, not interaction with remote
            # actor or attempts to identify an individual by IP alone.
            try:
                record_request_rejection(
                    remote_address=str(address),
                    path=str(environ.get("PATH_INFO", "")),
                    reason="OWNER_LABYRINTH_PATTERN_REJECTION",
                    request_sha256=denied_digest,
                )
            except (OSError, ValueError):
                return _reject(start_response, "503 Service Unavailable",
                               "SECURITY_AUDIT_UNAVAILABLE")
            return _reject(start_response, "403 Forbidden",
                           "LABYRINTH_SHIELD_REJECTION")

        if isolation_state()["isolated"]:
            return _reject(start_response, "503 Service Unavailable",
                           "MINOTAUR_SECURITY_ISOLATION_ACTIVE")
        return target(environ, start_response)
    return application


human_application_shielded = _wrap(human_application)
webhook_application_shielded = _wrap(webhook_application)
