"""Track B (2026-11-28) product-checkout tests: the structured
product catalog, product-keyed Checkout parameters, product-shaped
ledger recording, the self-serve checkout service, the public
/api/checkout route, and the storefront buy form.

Fake Stripe clients only, temp SQLite files. No live keys, no live
Stripe calls, no network.
"""

import io
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core_platform import product_catalog
from core_platform.platform_definitions import DEFINITIONS
from core_platform.platform_storefront import render_storefront
from core_platform.product_checkout import (
    ProductCheckoutService,
    ProductNotPurchasable,
    UnknownProduct,
)
from core_platform.stripe_checkout import StripeCheckout
from core_platform.stripe_payments import (
    PaymentDenied,
    PaymentLedger,
    product_checkout_parameters,
)


def _parsed_amount(price_of_record):
    match = re.search(r"\$([\d,]+(?:\.\d+)?)", price_of_record or "")
    if not match:
        return None
    return int(round(float(match.group(1).replace(",", "")) * 100))


class FakeSession:
    counter = 0
    params = None

    @classmethod
    def create(cls, **params):
        cls.counter += 1
        cls.params = params
        sid = "cs_test_%d" % cls.counter
        return {"id": sid, "url": "https://checkout.stripe.com/pay/" + sid}


class FakeClient:
    class checkout:
        Session = FakeSession


class TestCatalog(unittest.TestCase):
    def test_census(self):
        summary = product_catalog.catalog_summary()
        self.assertEqual(summary["platform_products_total"], 32)
        self.assertEqual(summary["platform_products_purchasable"], 32)
        self.assertEqual(summary["flagship_products_total"], 6)
        self.assertEqual(summary["flagship_products_purchasable"], 6)
        self.assertEqual(summary["ruled_not_in_stripe"], 23)

    def test_platform_amounts_match_definitions_and_stripe_shape(self):
        for pid, record in product_catalog.PLATFORM_PRODUCTS.items():
            defn = DEFINITIONS[pid]
            self.assertTrue((defn.stripe_product or "").startswith("YES"))
            self.assertIn(record["stripe_product_id"], defn.stripe_product)
            self.assertEqual(
                record["amount_cents"], _parsed_amount(defn.price_of_record),
                pid)
            self.assertTrue(record["stripe_price_id"].startswith("price_"))
            self.assertEqual(record["currency"], "usd")
            self.assertIn(record["mode"], ("payment", "subscription"))

    def test_flagship_six_amounts(self):
        amounts = sorted(
            r["amount_cents"]
            for r in product_catalog.FLAGSHIP_PRODUCTS.values())
        self.assertEqual(
            amounts, [15000, 25000, 49900, 50000, 500000, 2000000])

    def test_ruled_platforms_blocked_with_exact_reason(self):
        for pid, record in product_catalog.RULED_NOT_IN_STRIPE.items():
            self.assertFalse(record["purchasable"], pid)
            self.assertEqual(
                record["blocked_reason"], "stripe_product_not_created", pid)
            self.assertIsNone(record["stripe_product_id"], pid)
            self.assertTrue(record["tiers"], pid)

    def test_daedalus_and_metered_umbrella_absent(self):
        self.assertIsNone(
            product_catalog.resolve_checkout_record(platform_id="daedalus"))
        self.assertIsNone(product_catalog.resolve_checkout_record(
            product_id="prod_VROcwixC8EoX2G"))

    def test_grantwriter_resolves_to_blocked_record(self):
        record = product_catalog.resolve_checkout_record(
            platform_id="grantwriter")
        self.assertIsNotNone(record)
        self.assertFalse(record["purchasable"])
        labels = [t["label"] for t in record["tiers"]]
        self.assertTrue(any("$49" in label for label in labels))


class TestProductCheckoutParameters(unittest.TestCase):
    def test_subscription_shape(self):
        record = product_catalog.platform_product("sanders_analytics")
        params = product_checkout_parameters(
            "purchase_x", record,
            "https://sandersdashandseal.com/ok",
            "https://sandersdashandseal.com/no")
        self.assertEqual(params["mode"], "subscription")
        self.assertEqual(params["line_items"],
                         [{"price": record["stripe_price_id"], "quantity": 1}])
        self.assertEqual(params["client_reference_id"], "purchase_x")
        self.assertEqual(params["metadata"]["kind"], "product_purchase")
        self.assertEqual(
            params["subscription_data"]["metadata"]["case_id"], "purchase_x")

    def test_payment_shape_has_no_subscription_data(self):
        record = product_catalog.platform_product("sanders_finance")
        params = product_checkout_parameters(
            "purchase_x", record,
            "https://sandersdashandseal.com/ok",
            "https://sandersdashandseal.com/no")
        self.assertEqual(params["mode"], "payment")
        self.assertNotIn("subscription_data", params)

    def test_refuses_blocked_record_and_http_urls(self):
        record = product_catalog.ruled_record("grantwriter")
        with self.assertRaises(PaymentDenied):
            product_checkout_parameters(
                "purchase_x", record,
                "https://sandersdashandseal.com/ok",
                "https://sandersdashandseal.com/no")
        record = product_catalog.platform_product("sanders_finance")
        with self.assertRaises(PaymentDenied):
            product_checkout_parameters(
                "purchase_x", record,
                "http://sandersdashandseal.com/ok",
                "https://sandersdashandseal.com/no")


class TestProductLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = PaymentLedger(str(Path(self.tmp.name) / "ledger.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def _product_session(self, ref, session_id, amount, **over):
        obj = {
            "id": session_id,
            "client_reference_id": ref,
            "amount_total": amount,
            "currency": "usd",
            "payment_intent": "pi_1",
            "payment_status": "paid",
            "metadata": {
                "case_id": ref,
                "kind": "product_purchase",
                "platform_id": "sanders_finance",
                "item_key": "sanders_finance",
                "stripe_product_id": "prod_Vh6YjFk8GUDCRG",
                "stripe_price_id": "price_1UfiLDAgIE87JukG1p9gJ3XT",
            },
        }
        obj.update(over)
        return obj

    def test_register_then_fulfill_settles_both_shapes(self):
        record = product_catalog.platform_product("sanders_finance")
        self.ledger.register_checkout(
            "purchase_1", "cs_1", record["amount_cents"], "usd")
        self.ledger.register_product_checkout(
            "purchase_1", "sanders_finance", "sanders_finance",
            record["stripe_product_id"], record["stripe_price_id"],
            "cs_1", record["amount_cents"], "usd")
        self.assertEqual(
            self.ledger.product_purchase_status("purchase_1"), "PENDING")
        result = self.ledger.fulfill_checkout(self._product_session(
            "purchase_1", "cs_1", record["amount_cents"]))
        self.assertEqual(result, "FULFILLED")
        self.assertEqual(self.ledger.status("purchase_1"), "PAID")
        self.assertEqual(
            self.ledger.product_purchase_status("purchase_1"), "PAID")
        replay = self.ledger.fulfill_checkout(self._product_session(
            "purchase_1", "cs_1", record["amount_cents"]))
        self.assertEqual(replay, "ALREADY_FULFILLED")

    def test_record_event_settles_product_row(self):
        record = product_catalog.platform_product("sanders_finance")
        self.ledger.register_checkout(
            "purchase_2", "cs_2", record["amount_cents"], "usd")
        self.ledger.register_product_checkout(
            "purchase_2", "sanders_finance", "sanders_finance",
            record["stripe_product_id"], record["stripe_price_id"],
            "cs_2", record["amount_cents"], "usd")
        event = {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {"object": self._product_session(
                "purchase_2", "cs_2", record["amount_cents"])},
        }
        self.assertEqual(
            self.ledger.record_event(event, now=int(time.time())), "RECORDED")
        self.assertEqual(
            self.ledger.product_purchase_status("purchase_2"), "PAID")
        self.assertEqual(
            self.ledger.record_event(event, now=int(time.time())), "DUPLICATE")

    def test_case_session_leaves_no_product_row(self):
        self.ledger.register_checkout("case-1", "cs_9", 5000, "usd")
        session = {
            "id": "cs_9", "client_reference_id": "case-1",
            "amount_total": 5000, "currency": "usd",
            "payment_intent": "pi_2", "payment_status": "paid",
        }
        self.assertEqual(self.ledger.fulfill_checkout(session), "FULFILLED")
        self.assertEqual(
            self.ledger.product_purchase_status("case-1"), "UNKNOWN")


class TestProductCheckoutService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = PaymentLedger(str(Path(self.tmp.name) / "ledger.db"))
        checkout = StripeCheckout(
            secret_key="sk_test_fake", stripe_client=FakeClient)
        self.service = ProductCheckoutService(
            ledger=self.ledger,
            site_origin="https://sandersdashandseal.com",
            checkout=checkout)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_writes_nothing(self):
        result = self.service.start(platform_id="sanders_finance", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(
            self.ledger.product_purchase_status(result["purchase_ref"]),
            "UNKNOWN")
        self.assertEqual(
            result["params"]["line_items"][0]["price"],
            result["stripe_price_id"])

    def test_start_registers_pending_purchase(self):
        result = self.service.start(platform_id="sanders_analytics")
        self.assertEqual(result["mode"], "test")
        self.assertEqual(
            self.ledger.product_purchase_status(result["purchase_ref"]),
            "PENDING")
        self.assertEqual(FakeSession.params["mode"], "subscription")

    def test_flagship_by_product_id(self):
        result = self.service.start(product_id="prod_Vh6SAAiDNgOphe")
        self.assertEqual(result["amount_cents"], 49900)
        self.assertEqual(result["item_key"],
                         "flagship:business_formation_support")

    def test_boundaries(self):
        with self.assertRaises(ProductNotPurchasable):
            self.service.start(platform_id="grantwriter")
        with self.assertRaises(UnknownProduct):
            self.service.start(platform_id="daedalus")
        with self.assertRaises(UnknownProduct):
            self.service.start(platform_id="no_such_platform")

    def test_live_key_refused_without_verifier_gate(self):
        with self.assertRaises(PaymentDenied):
            StripeCheckout(secret_key="sk_live_fake", allow_live=True)


class _StubProductCheckout:
    """Route-test double: behaves like the service at its boundaries."""

    def start(self, *, platform_id=None, product_id=None, dry_run=False):
        if platform_id == "grantwriter":
            raise ProductNotPurchasable(
                "product is not purchasable yet: stripe_product_not_created")
        if platform_id == "sanders_finance" or product_id:
            return {
                "dry_run": dry_run,
                "purchase_ref": "purchase_stub",
                "checkout_url": "https://checkout.stripe.com/pay/cs_stub",
                "session_id": "cs_stub",
                "mode": "test",
                "platform_id": platform_id,
                "item_key": platform_id or "flagship:x",
                "stripe_product_id": product_id or "prod_x",
                "stripe_price_id": "price_x",
                "amount_cents": 100,
                "currency": "usd",
            }
        raise UnknownProduct("no product of record stands under that name")


def _call(app, method, path, body=b"", content_type="application/json",
          origin="https://sandersdashandseal.com"):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "sandersdashandseal.com",
        "SERVER_PORT": "443",
        "HTTP_HOST": "sandersdashandseal.com",
        "HTTP_ORIGIN": origin,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.StringIO(),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    status = {}

    def start_response(code, headers):
        status["code"] = code
        status["headers"] = dict(headers)

    chunks = app(environ, start_response)
    return status["code"], status["headers"], b"".join(chunks)


class TestCheckoutRoute(unittest.TestCase):
    def setUp(self):
        from app.customer_app import create_customer_app

        self.app = create_customer_app(
            appointments=object(),
            authenticate=lambda env: None,
            payments=object(),
            auth_app=lambda env, start: [],
            site_origin="https://sandersdashandseal.com",
            release_verifier=lambda: True,
            product_checkout=_StubProductCheckout(),
        )

    def test_json_checkout_success(self):
        code, _, body = _call(
            self.app, "POST", "/api/checkout",
            json.dumps({"platform_id": "sanders_finance"}).encode())
        self.assertTrue(code.startswith("200"), code)
        payload = json.loads(body)
        self.assertEqual(payload["checkout"]["checkout_url"],
                         "https://checkout.stripe.com/pay/cs_stub")

    def test_json_not_purchasable_is_409(self):
        code, _, body = _call(
            self.app, "POST", "/api/checkout",
            json.dumps({"platform_id": "grantwriter"}).encode())
        self.assertTrue(code.startswith("409"), code)
        self.assertEqual(json.loads(body)["error"], "not_purchasable")

    def test_json_unknown_is_404(self):
        code, _, body = _call(
            self.app, "POST", "/api/checkout",
            json.dumps({"platform_id": "daedalus"}).encode())
        self.assertTrue(code.startswith("404"), code)
        self.assertEqual(json.loads(body)["error"], "unknown_product")

    def test_origin_and_method_discipline(self):
        code, _, _ = _call(
            self.app, "POST", "/api/checkout",
            json.dumps({"platform_id": "sanders_finance"}).encode(),
            origin="https://evil.example")
        self.assertTrue(code.startswith("403"), code)
        code, _, _ = _call(self.app, "GET", "/api/checkout")
        self.assertTrue(code.startswith("405"), code)

    def test_form_post_redirects_to_checkout(self):
        code, headers, _ = _call(
            self.app, "POST", "/api/checkout",
            b"platform_id=sanders_finance",
            content_type="application/x-www-form-urlencoded")
        self.assertTrue(code.startswith("303"), code)
        self.assertEqual(headers.get("Location"),
                         "https://checkout.stripe.com/pay/cs_stub")

    def test_form_post_not_purchasable_redirects_back(self):
        code, headers, _ = _call(
            self.app, "POST", "/api/checkout",
            b"platform_id=grantwriter",
            content_type="application/x-www-form-urlencoded")
        self.assertTrue(code.startswith("303"), code)
        self.assertEqual(headers.get("Location"),
                         "/platforms/grantwriter?checkout=not_purchasable")


class TestStorefrontBuyForm(unittest.TestCase):
    def test_live_platform_storefront_has_buy_form(self):
        status, body = render_storefront("sanders_finance")
        self.assertEqual(status, "200 OK")
        text = body.decode("utf-8")
        self.assertIn('action="/api/checkout"', text)
        self.assertIn('name="platform_id" value="sanders_finance"', text)
        self.assertIn("Buy now", text)

    def test_recurring_platform_button_says_subscribe(self):
        _, body = render_storefront("sanders_analytics")
        self.assertIn("Subscribe", body.decode("utf-8"))

    def test_ruled_and_enterprise_platforms_have_no_buy_form(self):
        for pid in ("grantwriter", "daedalus", "oikos"):
            _, body = render_storefront(pid)
            self.assertNotIn('action="/api/checkout"',
                             body.decode("utf-8"), pid)


if __name__ == "__main__":
    unittest.main()
