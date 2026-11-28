"""Self-serve product checkout service (Track B, 2026-11-28).

Built under the Founder's Commercial Ecosystem order of 2026-11-28:
payment integration proceeds with price visibility and service
development; the objective is a functioning commercial ecosystem
that generates revenue and delivers what customers purchase.

Until now the only money path in the house was operator-mediated:
appointment, operator quote, amount-keyed Checkout. This service is
the product door beside it. A customer names a product — by
platform id or by Stripe product id — and this service:

1. resolves it in the product catalog of record
   (``core_platform/product_catalog.py``), which is also where the
   boundary lives: a platform whose price is ruled but whose Stripe
   product does not exist resolves to a record that is not
   purchasable, and this service refuses it as
   :class:`ProductNotPurchasable` naming the exact blocker — no
   dead checkout is ever created for it;
2. builds the success/cancel URLs on the house's own origin, back
   to the product's own public page;
3. creates the Checkout Session through the existing gated adapter
   (``StripeCheckout`` — test-mode first; a live key is refused
   unless the caller passes allow_live AND the environment carries
   the verifier gate ``STRIPE_LIVE_VERIFIED=1``), keyed by the
   catalog's Stripe price of record, never by a composed amount;
4. registers the purchase in the ledger in both shapes: the
   case-shaped row the existing webhook validation reads, and the
   product-shaped row (``stripe_product_purchases``).

A ``dry_run`` start builds and returns the exact session parameters
without calling Stripe and without writing the ledger — the
zero-risk probe the route and the operators use to prove the door
is wired before any session is created.

No key is stored or logged here; the connection is the house's one
shared Stripe connection (``core_platform/stripe_connection.py``),
read from the environment. The default ledger is the house ledger
file the webhook app settles into (``<repo>/data/ledger.db``, the
same path ``wsgi.py`` builds), so a purchase registered here is
settled by the verified webhook there.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from . import product_catalog
from .stripe_checkout import StripeCheckout, create_product_and_register
from .stripe_connection import StripeConnection
from .stripe_payments import PaymentDenied, PaymentLedger, product_checkout_parameters


class UnknownProduct(PaymentDenied):
    """The named platform/product stands in no catalog of record."""


class ProductNotPurchasable(PaymentDenied):
    """The product is of record but cannot be sold yet (exact boundary)."""


class ProductCheckoutService:
    """Resolves catalog products to Checkout Sessions."""

    def __init__(
        self,
        *,
        ledger: PaymentLedger,
        site_origin: str,
        connection: StripeConnection | None = None,
        checkout: StripeCheckout | None = None,
    ) -> None:
        origin = site_origin.strip().rstrip("/")
        if not origin.startswith("https://"):
            raise ValueError("site_origin must be an https origin")
        self.ledger = ledger
        self.site_origin = origin
        self.connection = connection or StripeConnection.from_env()
        self._checkout = checkout

    @classmethod
    def from_env(
        cls,
        site_origin: str,
        *,
        ledger_path: str | None = None,
    ) -> "ProductCheckoutService":
        """Build the production service: house ledger + shared connection.

        The ledger defaults to ``<repo>/data/ledger.db`` — the file
        ``wsgi.py`` builds the webhook ledger engine on — so product
        purchases registered here settle through the verified
        webhook path there.
        """
        if ledger_path is None:
            repo_root = Path(__file__).resolve().parent.parent
            ledger_path = str(repo_root / "data" / "ledger.db")
        return cls(
            ledger=PaymentLedger(ledger_path),
            site_origin=site_origin,
            connection=StripeConnection.from_env(),
        )

    def _adapter(self) -> StripeCheckout:
        if self._checkout is not None:
            return self._checkout
        # allow_live=True is this door's standing instruction to the
        # adapter; the adapter still refuses a live key unless the
        # environment's verifier gate (STRIPE_LIVE_VERIFIED=1) is
        # set. A test key needs no gate and is the default.
        return self.connection.checkout(allow_live=True)

    def _return_path(self, record: dict[str, Any]) -> str:
        platform_id = record.get("platform_id")
        if platform_id:
            return f"/platforms/{platform_id}"
        return "/fees-packages"

    def start(
        self,
        *,
        platform_id: str | None = None,
        product_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Start (or, with dry_run, preview) a product purchase.

        Returns the session's checkout URL and purchase reference,
        or the would-be session parameters for a dry run. Raises
        UnknownProduct for a name that stands in no catalog,
        ProductNotPurchasable for a ruled product whose Stripe
        objects do not exist yet, and PaymentDenied from the adapter
        when the live gate refuses a live key.
        """
        record = product_catalog.resolve_checkout_record(
            platform_id=platform_id, product_id=product_id
        )
        if record is None:
            raise UnknownProduct(
                "no product of record stands under that name")
        if record.get("purchasable") is not True:
            reason = record.get("blocked_reason") or "not_purchasable"
            raise ProductNotPurchasable(
                f"product is not purchasable yet: {reason}")
        purchase_ref = "purchase_" + secrets.token_hex(12)
        return_path = self._return_path(record)
        success_url = (
            f"{self.site_origin}{return_path}?checkout=success"
            f"&ref={purchase_ref}"
        )
        cancel_url = f"{self.site_origin}{return_path}?checkout=cancelled"
        if dry_run:
            params = product_checkout_parameters(
                purchase_ref, record, success_url, cancel_url
            )
            return {
                "dry_run": True,
                "purchase_ref": purchase_ref,
                "platform_id": record.get("platform_id"),
                "item_key": record.get("item_key"),
                "stripe_product_id": record.get("stripe_product_id"),
                "stripe_price_id": record.get("stripe_price_id"),
                "amount_cents": record.get("amount_cents"),
                "currency": record.get("currency"),
                "params": params,
            }
        session = create_product_and_register(
            checkout=self._adapter(),
            ledger=self.ledger,
            purchase_ref=purchase_ref,
            record=record,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {
            "dry_run": False,
            "purchase_ref": purchase_ref,
            "checkout_url": session["url"],
            "session_id": session["id"],
            "mode": session["mode"],
            "platform_id": record.get("platform_id"),
            "item_key": record.get("item_key"),
            "stripe_product_id": record.get("stripe_product_id"),
            "stripe_price_id": record.get("stripe_price_id"),
            "amount_cents": record.get("amount_cents"),
            "currency": record.get("currency"),
        }

    def status(self, purchase_ref: str) -> str:
        """Ledger state of a product purchase: PENDING/PAID/UNKNOWN."""
        return self.ledger.product_purchase_status(purchase_ref)


__all__ = [
    "ProductCheckoutService",
    "ProductNotPurchasable",
    "UnknownProduct",
]
