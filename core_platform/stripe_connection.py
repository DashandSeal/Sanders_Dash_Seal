"""Central Stripe connection — the one shared connection every platform inherits.

Owner direction (2026-11-21): every platform must be connected to the
owner's Stripe account (acct_1UQTehAgIE87JukG) and must inherit the
connection — past, present, and future builds by design. Before this
module, each payments module read the same environment variables
separately: the connection was shared only by convention (same variable
names), not by inheritance. This module is the single place that reads
them; every payments module imports it instead of reading the
environment directly. A future build inherits the connection by
importing this module — no per-platform Stripe setup.

What it holds (all from the environment, never from code):
- ``STRIPE_SECRET_KEY`` — the Stripe API key (``sk_test_`` / ``sk_live_``)
- ``STRIPE_WEBHOOK_SECRET`` — the webhook signing secret (``whsec_``)
- ``STRIPE_LIVEMODE`` — live requested (canonical truthiness)
- ``STRIPE_LIVE_VERIFIED`` — verifier-approved (canonical truthiness)

What it enforces (unchanged from the existing gates):
- Test mode is the default. Live requires BOTH ``STRIPE_LIVEMODE`` and
  ``STRIPE_LIVE_VERIFIED`` (the verifier gate, P3 2026-11-13). A live key
  without the gate raises ``PaymentDenied`` — the same behavior
  ``StripeCheckout`` had before this module existed.
- Canonical truthiness (``"1"`` / ``"true"`` / ``"yes"``, case-insensitive,
  whitespace-tolerant) is the one shared reading, as established by the
  P3 pass and already used by ``wsgi.py``, ``platform_services.py`` and
  ``deploy/deployment.py``.
- No key or secret is ever stored in code, logged, or returned by
  :meth:`StripeConnection.status` — presence only, never values.

What it exposes:
- :meth:`StripeConnection.from_env` — build from ``os.environ`` (or a
  mapping, for callers that inject an environment).
- ``secret_key`` / ``webhook_secret`` — the values themselves.
- ``livemode_requested`` / ``live_verified`` / ``live_allowed`` — the gate.
- ``mode`` — ``"test"`` / ``"live"`` / ``"unknown"`` (same rules as the
  checkout status had before).
- ``stripe_client`` — the Stripe SDK client, lazily imported, with
  ``api_key`` set (same behavior ``StripeCheckout`` had).
- :meth:`StripeConnection.checkout` — a ``StripeCheckout`` bound to this
  connection (lazy import; no import cycle).
- :meth:`StripeConnection.verify_webhook` — signature verification via
  ``stripe_payments.verify_stripe_webhook`` with this connection's
  webhook secret.
- :func:`construct_webhook_event` — the one place the Stripe SDK builds a
  webhook event (used by the webhook path in ``stream_api``).
- :meth:`StripeConnection.status` — honest presence-only status.

Bozly is NOT moved here: the CFO's own wiring
(``core_platform/bozly_wiring.py``) reads its own ``BOZLY_*`` variables
and went live on that path (2026-11-22, configured, one route). This
module changes nothing about Bozly.
"""

from __future__ import annotations

import os
from typing import Any

from .stripe_payments import PaymentDenied, verify_stripe_webhook

SECRET_KEY_ENV = "STRIPE_SECRET_KEY"
WEBHOOK_SECRET_ENV = "STRIPE_WEBHOOK_SECRET"
LIVEMODE_ENV = "STRIPE_LIVEMODE"
LIVE_VERIFIED_ENV = "STRIPE_LIVE_VERIFIED"


def env_truthy(value: str | None) -> bool:
    """Canonical Stripe truthiness (P3, 2026-11-13).

    ``"1"`` / ``"true"`` / ``"yes"``, case-insensitive and
    whitespace-tolerant. This is the one shared reading every Stripe
    module uses; previously ``wsgi.py``, ``platform_services.py`` and
    ``deploy/deployment.py`` each implemented it separately.
    """
    return isinstance(value, str) and value.strip().lower() in (
        "1", "true", "yes")


class StripeConnection:
    """The owner's single Stripe connection, read once from the environment.

    Constructed from explicit values or from the environment via
    :meth:`from_env`. Holds the values; never logs them, never stores
    them in code. Every payments module builds or receives one of
    these instead of calling ``os.environ.get("STRIPE_...")`` itself.
    """

    def __init__(
        self,
        *,
        secret_key: str = "",
        webhook_secret: str = "",
        livemode_requested: bool = False,
        live_verified: bool = False,
    ) -> None:
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.livemode_requested = bool(livemode_requested)
        self.live_verified = bool(live_verified)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "StripeConnection":
        """Build the connection from ``os.environ`` (or an injected mapping).

        Values are taken exactly as set; presence checks strip
        whitespace, matching the readers this replaces.
        """
        src = os.environ if env is None else env
        return cls(
            secret_key=src.get(SECRET_KEY_ENV) or "",
            webhook_secret=src.get(WEBHOOK_SECRET_ENV) or "",
            livemode_requested=env_truthy(src.get(LIVEMODE_ENV)),
            live_verified=env_truthy(src.get(LIVE_VERIFIED_ENV)),
        )

    @property
    def secret_key_set(self) -> bool:
        return bool(self.secret_key.strip())

    @property
    def webhook_secret_set(self) -> bool:
        return bool(self.webhook_secret.strip())

    @property
    def live_allowed(self) -> bool:
        """The live gate: live requested AND verifier-approved."""
        return bool(self.livemode_requested and self.live_verified)

    @property
    def expected_livemode(self) -> bool:
        """Alias for ``livemode_requested`` (webhook-path naming)."""
        return self.livemode_requested

    @property
    def test_mode(self) -> bool:
        return not self.livemode_requested

    @property
    def configured_for_test(self) -> bool:
        """Test-mode Checkout/webhook can run when both secrets are set."""
        return (self.secret_key_set and self.webhook_secret_set
                and self.test_mode)

    @property
    def mode(self) -> str:
        """``"test"`` / ``"live"`` / ``"unknown"`` from the secret-key prefix."""
        if self.secret_key.startswith("sk_live_"):
            return "live"
        if self.secret_key.startswith("sk_test_"):
            return "test"
        return "unknown"

    @property
    def stripe_client(self) -> Any:
        """The Stripe SDK client with this connection's key set.

        Lazily imported (the ``stripe`` package may be absent where
        only the status is needed); raises ``ValueError`` without a key
        and ``ImportError`` without the package — the same behavior
        ``StripeCheckout`` had before this module existed.
        """
        if not self.secret_key:
            raise ValueError(
                "STRIPE_SECRET_KEY is required for the Stripe connection")
        try:
            import stripe  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "stripe package is not installed; install stripe "
                "before using the Stripe client"
            ) from exc
        stripe.api_key = self.secret_key
        return stripe

    def checkout(self, *, allow_live: bool = False,
                 stripe_client: Any = None) -> Any:
        """A ``StripeCheckout`` bound to this connection.

        Lazy import (no import cycle: ``stripe_checkout`` imports this
        module). The checkout keeps its own test-mode-first gate; this
        only supplies the connection's key and client.
        """
        from .stripe_checkout import StripeCheckout

        return StripeCheckout(
            secret_key=self.secret_key,
            allow_live=allow_live,
            stripe_client=stripe_client,
        )

    def verify_webhook(self, payload: str, signature_header: str,
                       *, now: int | None = None) -> dict[str, Any]:
        """Verify a Stripe webhook signature with this connection's secret.

        Delegates to ``stripe_payments.verify_stripe_webhook``; raises
        ``PaymentDenied`` on a bad signature, stale timestamp, invalid
        payload, or a missing secret. Nothing is recorded here.
        """
        if not self.webhook_secret:
            raise PaymentDenied(
                "STRIPE_WEBHOOK_SECRET is not set; cannot verify a webhook")
        return verify_stripe_webhook(
            payload, signature_header, self.webhook_secret, now=now)

    def status(self) -> dict[str, Any]:
        """Honest Stripe status: key present or missing; mode; verifier gate.

        Presence only — no key or secret value is ever returned. Same
        shape and values as ``stripe_checkout.checkout_status()`` had
        before this module existed.
        """
        if not self.secret_key:
            mode = "unknown"
            live_status = "MISSING_KEY"
        elif self.secret_key.startswith("sk_live_"):
            mode = "live"
            live_status = (
                "READY" if self.live_verified
                else "BLOCKED_LIVE_NOT_VERIFIED"
            )
        elif self.secret_key.startswith("sk_test_"):
            mode = "test"
            live_status = "READY"
        else:
            mode = "unknown"
            live_status = "MISSING_KEY"
        return {
            "service": "stripe-connection",
            "mode": mode,
            "verifier_gate": self.live_verified,
            "live_status": live_status,
            "note": "Test mode is the default; live requires the verifier gate.",
        }


def get_connection(env: dict[str, str] | None = None) -> StripeConnection:
    """The one-line entry point for future builds: the shared connection."""
    return StripeConnection.from_env(env)


def construct_webhook_event(payload: bytes, sig_header: str,
                            signing_secret: str) -> Any:
    """Construct a Stripe webhook Event through the SDK.

    The one place the Stripe SDK builds a webhook event: the webhook
    path in ``stream_api`` calls this instead of touching the SDK
    directly. Same call, same arguments, same exceptions (``ValueError``
    / ``SignatureVerificationError``) as the direct call it replaces.
    """
    try:
        import stripe  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "stripe package is not installed; install stripe "
            "before verifying webhooks"
        ) from exc
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret = signing_secret,
    )


__all__ = [
    "SECRET_KEY_ENV",
    "WEBHOOK_SECRET_ENV",
    "LIVEMODE_ENV",
    "LIVE_VERIFIED_ENV",
    "StripeConnection",
    "construct_webhook_event",
    "env_truthy",
    "get_connection",
]
