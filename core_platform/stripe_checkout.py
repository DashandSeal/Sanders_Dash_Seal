"""Stripe Checkout adapter — test-mode first, verifier gate before live.

The ledger and webhook verifier already exist
(``stripe_payments.PaymentLedger`` / ``verify_stripe_webhook`` /
``checkout_parameters``).  This module adds the missing piece: actually
creating a Checkout Session through the Stripe SDK, with two hard
gates that prevent accidental live charges:

1. **Test-mode first.**  ``create_checkout_session`` requires a
   ``sk_test_`` secret key unless the caller explicitly passes
   ``allow_live=True`` *and* the environment carries
   ``STRIPE_LIVE_VERIFIED=1`` (the verifier gate: a human/CI verifier
   has confirmed the live webhook secret, prices and success URLs).
   Without both, a live key raises ``PaymentDenied`` and nothing is
   created.
2. **Webhook gate.**  :func:`verify_then_record` verifies the webhook
   signature with ``verify_stripe_webhook`` *before* the ledger
   records anything, and rejects events whose ``livemode`` flag does
   not match ``STRIPE_LIVEMODE`` (default ``false`` = test mode).

* The Stripe SDK (``stripe`` package) is imported lazily; without
  it construction raises ``ImportError``.  Tests pass a fake client
  with the same ``checkout.Session.create`` shape — no network, no
  key, no charge.
* No key is stored or logged.  Amounts are integer cents, minimum
  100 (enforced by ``checkout_parameters``).  Success/cancel URLs
  must be ``https://``.
* Free-tier-first: test mode costs $0 and is the default.  Live
  mode moves real money and is never the default.
"""

from __future__ import annotations

import os
from typing import Any

from .stripe_payments import (
    PaymentDenied,
    PaymentLedger,
    checkout_parameters,
    verify_stripe_webhook,
)

LIVE_VERIFIED_ENV = "STRIPE_LIVE_VERIFIED"


class StripeCheckout:
    """Checkout Session creator with a test-mode-first gate."""

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        allow_live: bool = False,
        stripe_client=None,
    ) -> None:
        key = secret_key or os.environ.get("STRIPE_SECRET_KEY", "")
        if not key:
            raise ValueError("STRIPE_SECRET_KEY is required for Stripe Checkout")
        self._live = key.startswith("sk_live_")
        if self._live:
            verified = os.environ.get(LIVE_VERIFIED_ENV, "") == "1"
            if not (allow_live and verified):
                raise PaymentDenied(
                    "live Stripe key refused: test-mode first. Pass "
                    "allow_live=True only after the verifier gate "
                    f"({LIVE_VERIFIED_ENV}=1) confirms live mode."
                )
        elif not key.startswith("sk_test_"):
            raise ValueError(
                "STRIPE_SECRET_KEY must start with sk_test_ or sk_live_"
            )
        self.secret_key = key
        self.mode = "live" if self._live else "test"
        if stripe_client is not None:
            self._client = stripe_client
        else:
            try:
                import stripe  # type: ignore[import-not-found]
            except ImportError as exc:
                raise ImportError(
                    "stripe package is not installed; install stripe "
                    "before using StripeCheckout"
                ) from exc
            stripe.api_key = key
            self._client = stripe

    def create_checkout_session(
        self,
        *,
        case_id: str,
        amount_cents: int,
        currency: str,
        service_label: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create a Checkout Session; returns id, url, mode and case_id.

        The session is registered in the caller's ledger by
        :func:`create_and_register` instead; this method only creates
        it at Stripe (or at the injected fake client).
        """
        params = checkout_parameters(
            case_id, amount_cents, currency, service_label, success_url, cancel_url
        )
        session = self._client.checkout.Session.create(**params)
        session_id = session.get("id") if isinstance(session, dict) else getattr(
            session, "id", None
        )
        session_url = session.get("url") if isinstance(session, dict) else getattr(
            session, "url", None
        )
        if not session_id or not session_url:
            raise PaymentDenied("Stripe returned a Checkout Session without id/url")
        return {
            "id": session_id,
            "url": session_url,
            "mode": self.mode,
            "case_id": case_id,
            "amount_cents": amount_cents,
            "currency": currency.lower(),
        }


def create_and_register(
    *,
    checkout: StripeCheckout,
    ledger: PaymentLedger,
    case_id: str,
    amount_cents: int,
    currency: str,
    service_label: str,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Checkout Session and register it in the ledger.

    The ledger write happens only after Stripe (or the fake) returns
    a session id, so a failed creation never leaves a dangling
    PENDING case behind.
    """
    session = checkout.create_checkout_session(
        case_id=case_id,
        amount_cents=amount_cents,
        currency=currency,
        service_label=service_label,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    ledger.register_checkout(
        case_id, session["id"], amount_cents, currency
    )
    return session


def verify_then_record(
    *,
    ledger: PaymentLedger,
    payload: str,
    signature_header: str,
    signing_secret: str,
    now: int | None = None,
) -> str:
    """Verify a Stripe webhook signature, check livemode, then record.

    Returns ``'RECORDED'`` or ``'DUPLICATE'`` (from the ledger), and
    raises ``PaymentDenied`` on a bad signature, a stale timestamp,
    an invalid payload, or a livemode mismatch.  Nothing is recorded
    before verification passes.
    """
    event = verify_stripe_webhook(
        payload, signature_header, signing_secret, now=now
    )
    expected_livemode = os.environ.get("STRIPE_LIVEMODE", "false") == "true"
    if bool(event.get("livemode", False)) != expected_livemode:
        raise PaymentDenied(
            "webhook livemode does not match STRIPE_LIVEMODE "
            f"(expected {expected_livemode})"
        )
    return ledger.record_event(event, now=now)


def checkout_status() -> dict[str, Any]:
    """Honest Stripe status: key present or missing; mode; verifier gate."""
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        mode = "unknown"
        live_status = "MISSING_KEY"
    elif key.startswith("sk_live_"):
        mode = "live"
        live_status = (
            "READY"
            if os.environ.get(LIVE_VERIFIED_ENV, "") == "1"
            else "BLOCKED_LIVE_NOT_VERIFIED"
        )
    elif key.startswith("sk_test_"):
        mode = "test"
        live_status = "READY"
    else:
        mode = "unknown"
        live_status = "MISSING_KEY"
    return {
        "service": "stripe-checkout",
        "mode": mode,
        "verifier_gate": os.environ.get(LIVE_VERIFIED_ENV, "") == "1",
        "live_status": live_status,
        "note": "Test mode is the default; live requires the verifier gate.",
    }


__all__ = [
    "LIVE_VERIFIED_ENV",
    "StripeCheckout",
    "create_and_register",
    "verify_then_record",
    "checkout_status",
]
