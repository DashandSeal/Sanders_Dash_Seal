"""
Persistent Sanders Dash & Seal application server entry point.
Architectural Layer: Enterprise WSGI Application Orchestrator
Design Standard: Platinum Blue Diamond Standard
Description: Initializes local persistence configurations, pulls environmental
             cryptographic anchors, and binds the rewired stream_api gateway 
             to match Dockerfile and Nginx reverse proxy parameters.
"""

import os
import sys
from pathlib import Path

# Ensure application workspace context is accessible along the python runtime path
repo_root = Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from deploy.deployment import create_application
from core_platform.stream_api import WebhookConfigurationError, import_make_app
from core_platform.stripe_payments import PaymentLedger

class MockLedgerEngine:
    """
    High-Resilience Persistent Storage Ledger Hub.
    Ensures zero runtime overhead across the Always Free ecosystem.

    The three webhook dispatch methods are real, durable SQLite-backed
    implementations delegated to core_platform.stripe_payments.PaymentLedger
    (same database file): fulfill_checkout settles a checkout session to
    PAID idempotently by session id, record_subscription_renewal records
    invoice.paid renewals idempotently by invoice id, and process_reversal
    records charge.refunded cumulatively by charge id. They used to be
    pass-only stubs, so a verified checkout/invoice/refund event was
    answered 200 LEDGER_SETTLED while nothing was recorded; that is fixed
    here. PaymentLedger.__init__ also creates the ledger tables, so a
    fresh ledger.db works on first webhook.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self._ledger = PaymentLedger(db_path)

    def connect(self):
        import sqlite3
        # Connect natively using enterprise WAL parameter bounds
        return sqlite3.connect(self.db_path, timeout=15)

    def fulfill_checkout(self, session, db):
        return self._ledger.fulfill_checkout(session, db)

    def record_subscription_renewal(self, invoice, db):
        return self._ledger.record_subscription_renewal(invoice, db)

    def process_reversal(self, charge, db):
        return self._ledger.process_reversal(charge, db)


def create_native_application():
    """
    Factory initializer constructing rewired runtime environments.
    Reads environment variables securely to minimize local configuration leakage risks.

    Returns one composed WSGI application: Stripe webhook requests
    (``/v1/payments/stripe/webhook`` and the deployment boundary's
    ``/stripe/webhook``) go to the verified webhook app; every other request
    goes to the deployment-boundary application from
    ``deploy.deployment``. With no production bindings installed that
    boundary runs diagnostic-only and fails closed (503) on authority-gated
    routes; the webhook app is the only live route until the owner supplies
    trusted bindings through ``deployment.load_application``.
    """
    # Define local state isolation storage path
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file_path = data_dir / "ledger.db"

    # Gunicorn drops to uid/gid 10001 (deploy/gunicorn.conf.py), so the
    # workers -- not the master -- write ledger.db. If this directory was
    # created by a root run (fresh checkout, umask 0007 -> mode 770,
    # root-owned), the workers cannot create or write the ledger and every
    # signed webhook 500s with "unable to open database file" -- found
    # twice by the live smoke test 2026-11-13. Hand the directory (and a
    # pre-existing ledger file, e.g. left by a root test run) to the
    # runtime user now, while this process still runs as root at preload.
    # Best effort only: a non-root start cannot chown, and the directory
    # may already be correctly owned (Docker creates /app/data owned by
    # 10001 in the Dockerfile). UIDs come from SDS_RUNTIME_UID/GID so a
    # deployer using a different runtime user can override them.
    try:
        uid = int(os.environ.get("SDS_RUNTIME_UID", "10001"))
        gid = int(os.environ.get("SDS_RUNTIME_GID", "10001"))
        os.chown(data_dir, uid, gid)
        if db_file_path.exists():
            os.chown(db_file_path, uid, gid)
    except (OSError, ValueError):
        pass

    # Initialize persistence framework layers
    ledger = MockLedgerEngine(str(db_file_path))

    # The webhook secret comes ONLY from the environment (systemd
    # EnvironmentFile /etc/sanders-dash-seal/runtime.env, written from the
    # owner's OCI Vault by deploy/refresh_provider_secrets.py, or exported
    # by the installer). There is deliberately no default: a missing secret
    # must fail loudly here, never silently verify with a baked-in value.
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise WebhookConfigurationError(
            "STRIPE_WEBHOOK_SECRET is not set. Set it in the environment "
            "(e.g. /etc/sanders-dash-seal/runtime.env via the provider-secrets "
            "flow) before starting the app; no default secret is baked into the code."
        )

    # Stripe environment comes from the environment, test mode by
    # default. Live mode requires BOTH STRIPE_LIVEMODE=1 AND
    # STRIPE_LIVE_VERIFIED=1: the second flag is set only after the
    # owner has explicitly confirmed live eligibility and release
    # controls. import_make_app raises (fail closed, no app) if live
    # is requested without verification; a live webhook secret alone
    # can never enable live acceptance.
    def _env_truthy(name):
        return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")

    expected_livemode = _env_truthy("STRIPE_LIVEMODE")
    live_verified = _env_truthy("STRIPE_LIVE_VERIFIED")

    webhook_app = import_make_app(
        ledger_engine=ledger,
        webhook_secret=webhook_secret,
        enabled=True,
        expected_livemode=expected_livemode,
        live_verified=live_verified,
    )
    platform_app = create_application()

    def application(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path in ('/v1/payments/stripe/webhook', '/stripe/webhook'):
            if path == '/stripe/webhook':
                environ = dict(environ, PATH_INFO='/v1/payments/stripe/webhook')
            return webhook_app(environ, start_response)
        return platform_app(environ, start_response)

    return application


# Aligned variable name to match your Dockerfile WSGI boot commands
app = create_native_application()
application = app
