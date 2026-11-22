"""
WSGI deployment boundary for the existing Sanders Dash & Seal application.


Default startup serves existing assets and diagnostics only. Trusted production
adapters are supplied by the administrator, behind an external verified bootstrap.
Neither environment configuration nor an HTTP request grants production authority.
"""


from dataclasses import dataclass, replace
import importlib
import json
import os
import re
from pathlib import Path


from app.customer_app import create_customer_app
from core_platform.free_resources import catalog as free_resource_catalog
from core_platform.pipeline_api import create_pipeline_app, TransactionStore
from core_platform.stream_api import create_stream_app


CANONICAL_HOST = 'sandersdashandseal.com'
ALIAS_HOSTS = {'www.sandersdashandseal.com', 'sanderslegalhelpersllc.com', 'www.sanderslegalhelpersllc.com', 'sanderssixshield.com', 'www.sanderssixshield.com', 'sanderssecurestack.com', 'www.sanderssecurestack.com', 'sandersemergencyglobalcommunication.com', 'www.sandersemergencyglobalcommunication.com'}
ORIGIN = 'https://' + CANONICAL_HOST
FACTORY = re.compile(r'([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))*(?::([A-Za-z_]\w*))?', re.ASCII)
WEB_ROOT = Path(__file__).resolve().parent.parent / 'web'


class DeploymentConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeBindings:
    appointments: object = None
    payments: object = None
    authenticate: object = None
    auth_app: object = None
    release_verifier: object = None
    webhook_app: object = None
    transaction_processor: object = None
    transaction_store: object = None
    stream_verifier: object = None


def _response(start, status, payload, extra=None):
    body = json.dumps(payload, separators=(',', ':')).encode()
    start(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-store'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Referrer-Policy', 'no-referrer'),
        *(extra or ())
    ])
    return [body]


def _unavailable(env, start):
    return _response(start, '503 Service Unavailable', {'error': 'service_unavailable'})


def _denied():
    return False


# ---------------------------------------------------------------------------
# P2 (2026-11-13): AI-platform / voice / realtime / global wiring.
# Every optional module is imported lazily inside a helper and guarded:
# a missing or broken optional module degrades its own routes to an
# honest 503 and can never break the core app (/, /healthz, webhook).
# No live provider call is made by any route below without (a) the
