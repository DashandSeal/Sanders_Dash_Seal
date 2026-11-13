"""Daedalus test suite — LOCAL ONLY, /tmp. Not pushed, not part of the repo.

Run:  cd /tmp/sds-daedalus && python3 -m unittest discover -s /tmp/daedalus-tests -v
Stdlib only. No network: the Anthropic transport is exercised through a
fake urlopen. No real API key is used anywhere; fake key is "test-key".
"""
import hashlib
import hmac
import io
import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, "/tmp/sds-daedalus")

from core_platform.daedalus_claude_transport import (  # noqa: E402
    DaedalusClaudeTransport, DaedalusProviderError,
)
from core_platform.daedalus_continuity import (  # noqa: E402
    Bridge, Generation, continuity_manifest,
)
from core_platform.daedalus_engine import build_context, build_engine, describe  # noqa: E402
from core_platform.daedalus_engine import DaedalusEngineConfig  # noqa: E402
from core_platform.daedalus_geofence import (  # noqa: E402
    GeoFence, GeoFenceDenied, GeographicPolicy, LocationAttestation,
)
from core_platform.daedalus_global_trust import (  # noqa: E402
    GlobalTrustContext, GlobalTrustEnforcer, GlobalTrustPolicy,
)
from core_platform.daedalus_ip_protection import (  # noqa: E402
    InventionRecord, publication_guard, sanitize_provenance,
    sign_evidence, verify_evidence,
)
from core_platform.daedalus_l15_capabilities import (  # noqa: E402
    CAPABILITIES, CapabilityState, DaedalusCapabilityProfile, declared_profile,
)
from core_platform.daedalus_portfolio_ip_pricing import (  # noqa: E402
    PRICE_USD_ANNUAL, PRICE_USD_MONTHLY, PortfolioProtection, proposed_rate_card,
)
from core_platform.daedalus_runtime_integration import DaedalusRuntimeIntegration  # noqa: E402
from core_platform.daedalus_unified_engine import (  # noqa: E402
    UnifiedDaedalusEngine, UnifiedEngineContext,
)

KEY = b"k" * 32
FAKE_MODEL = "claude-test-model"
FAKE_KEY = "test-key-not-real"


def no_env(test):
    """Run a test with Daedalus env vars removed."""
    def wrapper(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("DAEDALUS_CLAUDE_MODEL", None)
            return test(self)
    return wrapper


class FakeHTTPResponse:
    def __init__(self, payload, request_id="req-test-1"):
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = {"request-id": request_id}

    def read(self, n=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_message_response(text="print('hello')\n", model=FAKE_MODEL):
    return {
        "type": "message", "id": "msg-test-1", "model": model,
        "content": [{"type": "text", "text": text[:7]},
                    {"type": "text", "text": text[7:]}],
        "usage": {"input_tokens": 12, "output_tokens": 8},
    }


def fake_urlopen_ok(response=None):
    def _open(req, timeout=None, context=None):
        assert req.full_url == "https://api.anthropic.com/v1/messages"
        assert req.headers.get("X-api-key") == FAKE_KEY  # key sent, never logged
        return FakeHTTPResponse(response or fake_message_response())
    return _open


def good_location(**kw):
    d = dict(country="US", region="us-az", cloud_region="us-phoenix-1",
             source="trusted-attestor", trusted=True)
    d.update(kw)
    return LocationAttestation(**d)


def good_trust(**kw):
    d = dict(subject_id="subj-1", identity_verified=True,
             authorization_granted=True, location=good_location(),
             data_classification="restricted", processing_country="US",
             processing_cloud_region="us-phoenix-1", residency_permitted=True)
    d.update(kw)
    return GlobalTrustContext(**d)


class TestTransportConfig(unittest.TestCase):
    @no_env
    def test_missing_model_raises(self):
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport(api_key=FAKE_KEY)

    @no_env
    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport(model=FAKE_MODEL)

    @no_env
    def test_missing_both_raises(self):
        with self.assertRaises(ValueError):
            DaedalusClaudeTransport()

    def test_env_config_works(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY,
                                          "DAEDALUS_CLAUDE_MODEL": FAKE_MODEL}):
            t = DaedalusClaudeTransport()
        self.assertEqual(t.model, FAKE_MODEL)

    @no_env
    def test_bad_timeout_raises(self):
        for bad in (0, -5, float("inf"), float("nan")):
            with self.assertRaises(ValueError, msg=str(bad)):
                DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY,
                                        timeout_seconds=bad)


class TestTransportGenerateFake(unittest.TestCase):
    def setUp(self):
        self.audits = []
        self.t = DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY,
                                         audit=self.audits.append)

    def test_fake_happy_path(self):
        with mock.patch("urllib.request.urlopen", fake_urlopen_ok()):
            r = self.t.generate(system="sys", user_message="make hello")
        self.assertEqual(r.text, "print('hello')\n")
        self.assertEqual((r.input_tokens, r.output_tokens), (12, 8))
        self.assertEqual(r.model, FAKE_MODEL)
        self.assertEqual(r.message_id, "msg-test-1")
        self.assertEqual(len(self.audits), 1)
        audit = self.audits[0]
        self.assertNotIn("system", str(audit))
        self.assertNotIn(FAKE_KEY, str(audit))  # key never in audit record

    def test_empty_messages_raise(self):
        for sys_msg, user_msg in (("", "x"), ("s", ""), ("  ", "x")):
            with self.assertRaises(ValueError):
                self.t.generate(system=sys_msg, user_message=user_msg)

    def test_http_error_hides_body(self):
        def _open(req, timeout=None, context=None):
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized",
                                         {}, io.BytesIO(b'{"error": "bad key leaked"}'))
        with mock.patch("urllib.request.urlopen", _open):
            with self.assertRaises(DaedalusProviderError) as cm:
                self.t.generate(system="s", user_message="u")
        self.assertIn("401", str(cm.exception))
        self.assertNotIn("bad key leaked", str(cm.exception))

    def test_url_error_becomes_provider_error(self):
        def _open(req, timeout=None, context=None):
            raise urllib.error.URLError("dns fail")
        with mock.patch("urllib.request.urlopen", _open):
            with self.assertRaises(DaedalusProviderError):
                self.t.generate(system="s", user_message="u")

    def test_non_message_response_rejected(self):
        bad = {"type": "error", "content": [], "usage": {}}
        with mock.patch("urllib.request.urlopen", fake_urlopen_ok(bad)):
            with self.assertRaises(DaedalusProviderError):
                self.t.generate(system="s", user_message="u")


class TestHmac(unittest.TestCase):
    def test_sign_verify_roundtrip(self):
        rec = InventionRecord.from_source(invention_id="inv-1", title="t",
                                          inventor_assertions=("a",), source=b"src")
        sig = sign_evidence(rec, KEY)
        self.assertTrue(verify_evidence(rec, KEY, sig))

    def test_tampered_record_fails(self):
        rec = InventionRecord.from_source(invention_id="inv-1", title="t",
                                          inventor_assertions=("a",), source=b"src")
        sig = sign_evidence(rec, KEY)
        other = InventionRecord.from_source(invention_id="inv-1", title="t",
                                            inventor_assertions=("a",), source=b"SRC")
        self.assertFalse(verify_evidence(other, KEY, sig))

    def test_wrong_key_fails(self):
        rec = InventionRecord.from_source(invention_id="inv-1", title="t",
                                          inventor_assertions=(), source=b"src")
        sig = sign_evidence(rec, KEY)
        self.assertFalse(verify_evidence(rec, b"x" * 32, sig))

    def test_short_key_raises(self):
        rec = InventionRecord.from_source(invention_id="inv-1", title="t",
                                          inventor_assertions=(), source=b"src")
        with self.assertRaises(ValueError):
            sign_evidence(rec, b"short")


class TestGeofence(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.fence = GeoFence(
            GeographicPolicy(allowed_countries=frozenset({"US"}),
                             allowed_regions=frozenset(),
                             allowed_cloud_regions=frozenset({"us-phoenix-1"}),
                             policy_version="geo-v1"),
            audit=self.events.append)

    def test_allow(self):
        self.fence.enforce(action="ingress", location=good_location())
        self.assertEqual(self.events[-1]["result"], "allow")

    def test_deny_untrusted(self):
        with self.assertRaises(GeoFenceDenied):
            self.fence.enforce(action="execution", location=good_location(trusted=False))

    def test_deny_wrong_cloud_region(self):
        with self.assertRaises(GeoFenceDenied):
            self.fence.enforce(action="egress", location=good_location(cloud_region="eu-west-1"))

    def test_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            self.fence.enforce(action="teleport", location=good_location())

    def test_audit_failure_fails_closed(self):
        def boom(event):
            raise RuntimeError("audit store down")
        fence = GeoFence(self.fence.policy, audit=boom)
        with self.assertRaises(RuntimeError):
            fence.enforce(action="ingress", location=good_location())


class TestGlobalTrust(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.enf = GlobalTrustEnforcer(
            GlobalTrustPolicy(authorized_cloud_regions=frozenset({"us-phoenix-1"}),
                              prohibited_countries=frozenset({"XX"}),
                              restricted_data_countries=frozenset({"YY"})),
            audit=self.events.append)

    def test_allow(self):
        self.enf.enforce(action="ingress", context=good_trust())
        self.assertEqual(self.events[-1]["decision"], "allow")

    def test_deny_unverified_identity(self):
        with self.assertRaises(GeoFenceDenied):
            self.enf.enforce(action="execution", context=good_trust(identity_verified=False))

    def test_deny_prohibited_country(self):
        ctx = good_trust(location=good_location(country="XX"))
        with self.assertRaises(GeoFenceDenied):
            self.enf.enforce(action="ingress", context=ctx)

    def test_deny_wrong_cloud_region(self):
        with self.assertRaises(GeoFenceDenied):
            self.enf.enforce(action="storage",
                             context=good_trust(processing_cloud_region="eu-west-1"))

    def test_deny_restricted_data_country(self):
        with self.assertRaises(GeoFenceDenied):
            self.enf.enforce(action="egress",
                             context=good_trust(processing_country="YY"))


class TestL15HonestStatus(unittest.TestCase):
    def test_declared_all_unavailable(self):
        profile = declared_profile()
        self.assertEqual(set(profile.capability_states), set(CAPABILITIES))
        self.assertEqual(len(CAPABILITIES), 13)
        for state in profile.capability_states.values():
            self.assertIs(state, CapabilityState.UNAVAILABLE)
        self.assertFalse(profile.fully_active)

    def test_report_marks_not_active(self):
        rep = declared_profile().report()
        self.assertFalse(rep["fully_active"])
        self.assertEqual(rep["capabilities"]["live_claude_reasoning"], "unavailable")
        self.assertEqual(rep["capabilities"]["cobol_bridge"], "unavailable")
        self.assertEqual(rep["capabilities"]["onnx_language_classification"], "unavailable")

    def test_incomplete_inventory_rejected(self):
        states = {n: CapabilityState.UNAVAILABLE for n in CAPABILITIES[:-1]}
        with self.assertRaises(ValueError):
            DaedalusCapabilityProfile(identity="DAEDALUS", level_target="L15+",
                                      language_target=203, platform_target=41,
                                      capability_states=states)


class TestPricingConfigDriven(unittest.TestCase):
    def test_rate_card_is_labeled_proposed_not_revenue(self):
        card = proposed_rate_card()
        self.assertEqual(card["status"], "proposed_not_verified_market_rate")
        self.assertEqual(card["scenario_status"], "illustrative_not_forecast")
        self.assertEqual(card["currency"], "USD")

    def test_scenario_arithmetic_recomputes(self):
        """136,000,000 must equal counts x prices from the card itself."""
        card = proposed_rate_card()
        counts = card["scenario_customers"]
        total = 0
        for k, n in counts.items():
            if k in PRICE_USD_MONTHLY:
                total += n * int(PRICE_USD_MONTHLY[k]) * 12
            else:
                total += n * int(PRICE_USD_ANNUAL[k])
        self.assertEqual(total, int(card["scenario_annual_revenue_usd"]))
        self.assertEqual(total, 136000000)

    def test_protect_roundtrip_and_publication_guard(self):
        saved = []
        pp = PortfolioProtection(signing_key=KEY,
                                 persist_confidential=lambda a, r, s: saved.append((a, r, s)))
        asset = pp.protect(asset_id="op-1", platform_id="p", subsystem_id="s",
                           generation="present", invention_id="inv-1", title="t",
                           inventor_assertions=(), source=b"code")
        self.assertEqual(asset.source_sha256, hashlib.sha256(b"code").hexdigest())
        self.assertEqual(len(saved), 1)
        self.assertTrue(verify_evidence(saved[0][1], KEY, saved[0][2]))
        with self.assertRaises(PermissionError):
            PortfolioProtection.authorize_publication(
                asset, explicit_publication_authorization=False,
                patent_counsel_clearance=True)
        PortfolioProtection.authorize_publication(
            asset, explicit_publication_authorization=True,
            patent_counsel_clearance=False)  # owner auth, no counsel gate


class TestPublicationGuardAndSanitize(unittest.TestCase):
    def test_public_needs_no_auth(self):
        publication_guard(classification="public",
                          explicit_publication_authorization=False)

    def test_sanitize_drops_secrets(self):
        out = sanitize_provenance({"invention_id": "i", "source_sha256": "x",
                                   "api_key": "SECRET", "prompt": "p"})
        self.assertEqual(set(out), {"invention_id", "source_sha256"})
        self.assertNotIn("SECRET", str(out))


class TestRuntimeIntegrationFake(unittest.TestCase):
    def test_generate_source_fake_transport(self):
        saved = []
        rt = DaedalusRuntimeIntegration(
            transport=DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY),
            signing_key=KEY, persist_private_evidence=lambda r, s: saved.append((r, s)))
        with mock.patch("urllib.request.urlopen", fake_urlopen_ok()):
            res = rt.generate_source(invention_id="inv-1", objective="hello",
                                     language="Python", inventor_assertions=("a",))
        self.assertEqual(res.source_sha256, hashlib.sha256(b"print('hello')\n").hexdigest())
        self.assertEqual(len(saved), 1)
        self.assertTrue(verify_evidence(saved[0][0], KEY, saved[0][1]))
        self.assertEqual(res.evidence_signature, saved[0][1])

    def test_empty_provider_text_rejected(self):
        saved = []
        rt = DaedalusRuntimeIntegration(
            transport=DaedalusClaudeTransport(model=FAKE_MODEL, api_key=FAKE_KEY),
            signing_key=KEY, persist_private_evidence=lambda r, s: saved.append((r, s)))
        with mock.patch("urllib.request.urlopen",
                        fake_urlopen_ok(fake_message_response(text="   "))):
            with self.assertRaises(ValueError):
                rt.generate_source(invention_id="inv-1", objective="x",
                                   language="Python", inventor_assertions=())
        self.assertEqual(saved, [])  # nothing persisted on empty output


class TestUnifiedEngineFakeCapability(unittest.TestCase):
    def _engine(self, capability=None, trust=None):
        events = []
        enf = GlobalTrustEnforcer(
            GlobalTrustPolicy(authorized_cloud_regions=frozenset({"us-phoenix-1"})),
            audit=lambda e: events.append(e))
        pp = PortfolioProtection(signing_key=KEY,
                                 persist_confidential=lambda a, r, s: None)
        eng = UnifiedDaedalusEngine(
            global_trust=enf, portfolio_protection=pp,
            capability=capability or (lambda ctx, obj: b"print(1)\n"),
            audit=lambda e: events.append(e))
        ctx = UnifiedEngineContext(operation_id="op-1", platform_id="p",
                                   subsystem_id="s", invention_id="inv-1",
                                   generation="present",
                                   trust=trust or good_trust())
        return eng, ctx, events

    def test_execute_fake_capability(self):
        eng, ctx, events = self._engine()
        out = eng.execute(ctx, "make one", title="t", inventor_assertions=())
        self.assertEqual(out["source_sha256"], hashlib.sha256(b"print(1)\n").hexdigest())
        kinds = [e.get("event") for e in events]
        self.assertIn("NATIVE_OPERATION_STARTED", kinds)
        self.assertIn("NATIVE_OPERATION_COMPLETED", kinds)

    def test_trust_deny_blocks_capability(self):
        called = []
        eng, ctx, _ = self._engine(
            capability=lambda c, o: called.append(o) or b"x",
            trust=good_trust(identity_verified=False))
        with self.assertRaises(GeoFenceDenied):
            eng.execute(ctx, "x", title="t", inventor_assertions=())
        self.assertEqual(called, [])

    def test_empty_source_rejected(self):
        eng, ctx, _ = self._engine(capability=lambda c, o: b"")
        with self.assertRaises(ValueError):
            eng.execute(ctx, "x", title="t", inventor_assertions=())


class TestBuildEngine(unittest.TestCase):
    def _config(self, **kw):
        d = dict(signing_key=KEY, persist_private_evidence=lambda r, s: None,
                 persist_confidential=lambda a, r, s: None,
                 audit=lambda e: None, model=FAKE_MODEL, api_key=FAKE_KEY)
        d.update(kw)
        return DaedalusEngineConfig(**d)

    @no_env
    def test_build_without_key_or_model_raises(self):
        with self.assertRaises(ValueError):
            build_engine(self._config(model=None, api_key=None))

    def test_build_short_signing_key_raises(self):
        with self.assertRaises(ValueError):
            build_engine(self._config(signing_key=b"short"))

    def test_full_chain_fake_transport(self):
        eng = build_engine(self._config())
        ctx = build_context(operation_id="op-1", platform_id="p", subsystem_id="s",
                            invention_id="inv-1", subject_id="subj-1",
                            location=good_location())
        with mock.patch("urllib.request.urlopen", fake_urlopen_ok()):
            out = eng.execute(ctx, "hello", title="t", inventor_assertions=())
        self.assertEqual(out["engine"], "DAEDALUS")
        self.assertEqual(out["source_sha256"],
                         hashlib.sha256(b"print('hello')\n").hexdigest())

    def test_describe_is_honest(self):
        d = describe()
        self.assertFalse(d["fully_active"])
        self.assertFalse(d["capabilities"]["fully_active"])
        self.assertEqual(d["status"],
                         "rebuild_20261113_integration_contract_not_production_deployment")
        self.assertEqual(d["commercial"]["scenario_status"], "illustrative_not_forecast")


class TestContinuity(unittest.TestCase):
    def test_manifest_has_three_bridges(self):
        m = continuity_manifest()
        self.assertEqual(len(m["bridges"]), 3)
        self.assertTrue(all(b["preserves_source"] for b in m["bridges"]))
        self.assertEqual(m["bridges"][0]["source"], "COBOL")

    def test_bridge_must_preserve_source(self):
        with self.assertRaises(ValueError):
            Bridge("A", "B", Generation.LEGACY, Generation.CURRENT,
                   "x", "y", preserves_source=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
