"""Production runtime bindings for Sanders Dash & Seal.

The factory ``deploy.load_application`` / ``wsgi.create_native_application``
expects: ``create_production_bindings()`` returns a
``deploy.deployment.RuntimeBindings`` built from the repository's own
modules — the same modules the test fixture wires by hand
(``worker/test/python_fixture.py``), but against the production data
directory and the central Stripe connection, with a real session auth
instead of the fixture's stub authenticator.

What it wires:
- cases + appointments + quotes + the Stripe ledger share ONE SQLite file
  (``data/ledger.db`` — the same file the webhook ledger in ``wsgi.py``
  uses), because ``AppointmentPayments`` requires the ledger and the
  appointment store to resolve to the same file, and because a checkout
  registered here must be visible to the webhook path that settles it.
- the audit trail is ``GlassBoxAudit`` on ``data/audit.db``.
- sign-in is ``SessionAuth`` on ``data/accounts.db`` (no seeded accounts;
  the operator is created once through ``/auth/setup`` with the
  owner-held ``SDS_OWNER_SETUP_TOKEN``).
- the Stripe client is a real ``stripe.StripeClient`` built from the
  central connection (``core_platform.stripe_connection``). The module
  object that connection's ``stripe_client`` property returns has no
  ``.v1`` namespace in stripe 15.6.0 — only ``StripeClient`` instances
  do — and ``AppointmentPayments.checkout`` calls
  ``client.v1.checkout.sessions.create``; passing the module would
  409 every checkout. When no usable key is configured (or a live key
  is present without the verifier gate) the factory passes an adapter
  whose ``.v1`` raises ``PaymentDenied``, so checkout answers an
  honest 409 while sign-in, requests and quotes keep working.
- the release verifier is True once these bindings exist: this process
  has real bindings, so ``/readyz`` answers 200 and the customer API
  stops answering 503 ``appointments_unavailable``.
- the pipeline / stream bindings stay None: those routes keep their
  honest 503 until a transaction processor is supplied.

The factory never invents a boot mechanism: it is loaded only through
the existing ``deployment.load_application`` factory-reference mechanism,
named by the ``SANDERS_RUNTIME_FACTORY`` environment variable (set by
the systemd unit). It is not required for deployment — without the
variable ``wsgi.py`` keeps its diagnostic-only startup.
"""

from __future__ import annotations

import os
from pathlib import Path

from core_platform.appointment_payments import AppointmentPayments
from core_platform.appointments import AppointmentStore
from core_platform.cases import CaseRegistry
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.session_auth import SessionAuth
from core_platform.stripe_connection import StripeConnection
from core_platform.stripe_payments import PaymentDenied, PaymentLedger
from core_platform.upgrade_sidecar import CORE_LAWS
from deploy.deployment import ALIAS_HOSTS, ORIGIN, RuntimeBindings


def _fee_verifier(case, actor, items):
    """An operator may quote only a case still awaiting human review."""
    return (isinstance(case, dict)
            and case.get('status') == 'AWAITING_HUMAN_REVIEW')


def _eligibility_verifier(cases):
    """A case may pay only while it is awaiting review or review-verified."""
    def verify(appointment, requester):
        try:
            case = cases.get(appointment['case_id'])
            return case.get('status') in ('AWAITING_HUMAN_REVIEW', 'REVIEW_VERIFIED')
        except Exception:
            return False
    return verify


class _UnavailableStripeClient:
    """Stand-in for the Stripe SDK client when no usable key is configured.

    ``AppointmentPayments.checkout`` accesses ``client.v1``; raising
    ``PaymentDenied`` here makes checkout answer its honest 409
    ``checkout_unavailable`` instead of crashing, while the rest of the
    application process keeps working.
    """

    @property
    def v1(self):
        raise PaymentDenied(
            'Stripe client unavailable: no usable Stripe key is configured')


def _stripe_client(connection):
    """A real ``StripeClient`` when the connection permits one.

    Test-mode-first: a live key without the verifier gate
    (``STRIPE_LIVEMODE`` + ``STRIPE_LIVE_VERIFIED``) must never create
    live sessions, so it gets the unavailable adapter too.
    """
    if not connection.secret_key_set:
        return _UnavailableStripeClient()
    if connection.mode not in ('test', 'live'):
        return _UnavailableStripeClient()
    if connection.mode == 'live' and not connection.live_allowed:
        return _UnavailableStripeClient()
    try:
        import stripe
    except ImportError:
        return _UnavailableStripeClient()
    return stripe.StripeClient(connection.secret_key)


def create_production_bindings():
    """Build the production ``RuntimeBindings`` from the repo's own modules."""
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    shared_db = data_dir / 'ledger.db'

    cases = CaseRegistry(shared_db, CORE_LAWS)
    audit = GlassBoxAudit(data_dir / 'audit.db')
    appointments = AppointmentStore(cases, audit)
    ledger = PaymentLedger(shared_db)

    connection = StripeConnection.from_env()
    stripe_client = _stripe_client(connection)

    site_origins = frozenset(
        {ORIGIN} | {'https://' + host for host in ALIAS_HOSTS})
    auth = SessionAuth(
        data_dir / 'accounts.db', ORIGIN,
        setup_token=os.environ.get('SDS_OWNER_SETUP_TOKEN') or None,
        allowed_origins=site_origins)

    payments = AppointmentPayments(
        appointments, ledger, stripe_client,
        auth.operator_verifier, _fee_verifier,
        _eligibility_verifier(cases), audit, ORIGIN,
        expected_livemode=bool(
            connection.live_allowed and connection.mode == 'live'))

    return RuntimeBindings(
        appointments=appointments,
        payments=payments,
        authenticate=auth.authenticate,
        auth_app=auth.auth_app,
        release_verifier=lambda: True,
    )
