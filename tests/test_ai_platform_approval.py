"""Tests for the AI-platform approval gates — fakes only, no network.

Run from the repo root::

    python3 -m unittest tests.test_ai_platform_approval -v

Stdlib only. No real API key, model, provider call, or spend anywhere:
the "live-looking" key below is ``sk-ant-test-not-real`` — it only has
the live key *shape* so the guard can recognise it; it is never sent
anywhere, and no test performs a network call. Approval state is kept
in temporary files; the real ``core_platform/ai_platform_approvals.json``
is read (never written) by one test and never mutated by any test.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_platform.ai_platform_approval import (  # noqa: E402
    APPROVED,
    UNAPPROVED,
    ApprovalRequiredError,
    ApprovalStore,
    DEFAULT_STATE_PATH,
    GATE_IDS,
    GATES,
    approval_checklist,
    check_live,
    guarded_call,
    guarded_grantwriter_generation,
    http_failure,
    is_approved,
    load_store,
    render_checklist,
    require_approval,
)
from core_platform.daedalus_engine import (  # noqa: E402
    DaedalusEngineConfig,
    build_engine,
    build_live_engine,
    build_voice_runner,
)
from core_platform.daedalus_voice_pipeline import (  # noqa: E402
    FakeSpeaker,
    FakeTranscriber,
)

OWNER = "Roosevelt Sanders"
KEY = b"k" * 32
# Live *shape* only — a fake key that is never sent to any provider.
LIVE_SHAPE_KEY = "sk-ant-test-not-real"
FAKE_KEY = "test-key-not-real"
MODEL = "claude-test-model"


def _config(api_key=FAKE_KEY, model=MODEL):
    return DaedalusEngineConfig(
        signing_key=KEY,
        persist_private_evidence=lambda record, s: None,
        persist_confidential=lambda *a, **k: None,
        audit=lambda event: None,
        model=model,
        api_key=api_key,
        transport_backend="stdlib",
    )


def _approved_store(*gate_ids):
    """An in-memory store with exactly the given gates approved."""
    store = ApprovalStore()
    for gate_id in gate_ids:
        store.record_approval(gate_id, OWNER, at="2026-11-13T00:00:00+00:00")
    return store


class TestGateDeclarations(unittest.TestCase):
    def test_nine_gates_declared(self):
        self.assertEqual(len(GATES), 9)
        self.assertEqual(len(set(GATE_IDS)), 9)

    def test_expected_gate_ids(self):
        self.assertEqual(
            set(GATE_IDS),
            {
                "release_verifier_pr2_checkout",
                "gateway_workflow_fix",
                "stripe_live_keys",
                "anthropic_live_model",
                "grantwriter_purpose",
                "ron_notarial",
                "voice_video_provider",
                "daedalus_live",
                "ai_role_workers",
            },
        )

    def test_every_gate_has_label_description_and_how_to_approve(self):
        for gate in GATES:
            self.assertTrue(gate.label)
            self.assertTrue(gate.description)
            self.assertTrue(gate.unlocks)
            self.assertTrue(gate.how_to_approve)


class TestDefaultUnapproved(unittest.TestCase):
    def test_fresh_store_is_all_unapproved(self):
        store = ApprovalStore()
        for gate_id in GATE_IDS:
            self.assertEqual(store.status(gate_id), UNAPPROVED)
            self.assertFalse(store.is_approved(gate_id))

    def test_missing_file_loads_all_unapproved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = load_store(os.path.join(tmp, "no-such-file.json"))
            for gate_id in GATE_IDS:
                self.assertFalse(store.is_approved(gate_id))

    def test_on_disk_state_file_is_all_unapproved(self):
        # Read-only: the shipped state file must not claim any approval.
        store = load_store(DEFAULT_STATE_PATH)
        for gate_id in GATE_IDS:
            self.assertEqual(
                store.status(gate_id), UNAPPROVED, f"gate {gate_id}"
            )
        self.assertIn("0/9 gates approved", render_checklist(store))

    def test_unknown_gate_is_an_error_not_an_approval(self):
        store = ApprovalStore()
        for call in (
            lambda: store.status("nope"),
            lambda: store.is_approved("nope"),
            lambda: require_approval("nope", store=store),
            lambda: store.record_approval("nope", OWNER),
            lambda: store.record_verifier_result(
                "nope", True, verifier="v"
            ),
        ):
            with self.assertRaises(ValueError):
                call()


class TestExplicitApproval(unittest.TestCase):
    def test_approval_flips_only_that_gate(self):
        store = ApprovalStore()
        record = store.record_approval(
            "stripe_live_keys", OWNER, note="owner approved live Stripe"
        )
        self.assertEqual(record["status"], APPROVED)
        self.assertEqual(record["approved_by"], OWNER)
        self.assertEqual(record["method"], "owner_approval")
        self.assertTrue(store.is_approved("stripe_live_keys"))
        for gate_id in GATE_IDS:
            if gate_id != "stripe_live_keys":
                self.assertFalse(
                    store.is_approved(gate_id), f"gate {gate_id}"
                )

    def test_blank_approver_is_refused(self):
        store = ApprovalStore()
        for approver in ("", "   ", None):
            with self.assertRaises(ValueError):
                store.record_approval("stripe_live_keys", approver)
        self.assertFalse(store.is_approved("stripe_live_keys"))

    def test_verifier_false_does_not_flip(self):
        store = ApprovalStore()
        record = store.record_verifier_result(
            "gateway_workflow_fix", False,
            verifier="gateway-check", note="exit 128",
        )
        self.assertEqual(record["status"], UNAPPROVED)
        self.assertFalse(store.is_approved("gateway_workflow_fix"))

    def test_verifier_true_flips_with_method_verifier(self):
        store = ApprovalStore()
        record = store.record_verifier_result(
            "gateway_workflow_fix", True, verifier="gateway-check"
        )
        self.assertEqual(record["status"], APPROVED)
        self.assertEqual(record["method"], "verifier")
        self.assertEqual(record["verifier"], "gateway-check")
        self.assertTrue(store.is_approved("gateway_workflow_fix"))

    def test_failed_verifier_never_revokes_an_approval(self):
        store = _approved_store("stripe_live_keys")
        store.record_verifier_result(
            "stripe_live_keys", False, verifier="stripe-check"
        )
        self.assertTrue(store.is_approved("stripe_live_keys"))

    def test_revoke_returns_gate_to_unapproved(self):
        store = _approved_store("daedalus_live")
        store.revoke("daedalus_live", note="owner withdrew approval")
        self.assertFalse(store.is_approved("daedalus_live"))
        self.assertEqual(store.status("daedalus_live"), UNAPPROVED)

    def test_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            store = ApprovalStore(path=path)
            store.record_approval("ron_notarial", OWNER)
            store.save()
            reloaded = load_store(path)
            self.assertTrue(reloaded.is_approved("ron_notarial"))
            for gate_id in GATE_IDS:
                if gate_id != "ron_notarial":
                    self.assertFalse(reloaded.is_approved(gate_id))

    def test_corrupt_state_file_raises_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not json")
            with self.assertRaises(ValueError):
                load_store(path)

    def test_unknown_gate_in_state_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"version": 1, "gates": {"mystery_gate": {
                        "status": APPROVED}}},
                    handle,
                )
            with self.assertRaises(ValueError):
                load_store(path)

    def test_unknown_status_in_state_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"version": 1, "gates": {"stripe_live_keys": {
                        "status": "MAYBE"}}},
                    handle,
                )
            with self.assertRaises(ValueError):
                load_store(path)


class TestGuard(unittest.TestCase):
    def test_require_approval_raises_value_error_naming_gate(self):
        store = ApprovalStore()
        with self.assertRaises(ApprovalRequiredError) as ctx:
            require_approval("daedalus_live", store=store)
        error = ctx.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.http_status, 503)
        self.assertEqual(error.gate_id, "daedalus_live")
        self.assertIn("daedalus_live", str(error))
        self.assertIn("UNAPPROVED", str(error))

    def test_require_approval_allows_approved_gate(self):
        store = _approved_store("daedalus_live")
        require_approval("daedalus_live", store=store)  # no raise

    def test_check_live_returns_503_tuple_when_unapproved(self):
        allowed, status, message = check_live(
            "stripe_live_keys", store=ApprovalStore()
        )
        self.assertFalse(allowed)
        self.assertEqual(status, 503)
        self.assertIn("stripe_live_keys", message)

    def test_check_live_returns_200_tuple_when_approved(self):
        allowed, status, _message = check_live(
            "stripe_live_keys", store=_approved_store("stripe_live_keys")
        )
        self.assertTrue(allowed)
        self.assertEqual(status, 200)

    def test_http_failure_is_503_payload_naming_gate(self):
        payload = http_failure("voice_video_provider")
        self.assertEqual(payload["status"], 503)
        self.assertEqual(payload["error"], "approval_required")
        self.assertEqual(payload["gate"], "voice_video_provider")
        self.assertIn("voice_video_provider", payload["detail"])

    def test_http_failure_is_200_when_approved(self):
        payload = http_failure(
            "voice_video_provider",
            store=_approved_store("voice_video_provider"),
        )
        self.assertEqual(payload["status"], 200)
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["gate"], "voice_video_provider")

    def test_guarded_call_does_not_run_func_when_unapproved(self):
        calls = []
        with self.assertRaises(ApprovalRequiredError):
            guarded_call(
                "ai_role_workers", calls.append, "ran",
                store=ApprovalStore(),
            )
        self.assertEqual(calls, [])

    def test_guarded_call_runs_func_when_approved(self):
        result = guarded_call(
            "ai_role_workers", lambda x: x * 2, 21,
            store=_approved_store("ai_role_workers"),
        )
        self.assertEqual(result, 42)

    def test_is_approved_helper(self):
        self.assertFalse(is_approved("daedalus_live", ApprovalStore()))
        self.assertTrue(
            is_approved(
                "daedalus_live", _approved_store("daedalus_live")
            )
        )


class TestGrantwriterGuard(unittest.TestCase):
    def test_grantwriter_generation_blocked_when_unapproved(self):
        calls = []
        with self.assertRaises(ApprovalRequiredError) as ctx:
            guarded_grantwriter_generation(
                lambda: calls.append("generated") or "draft",
                store=ApprovalStore(),
            )
        self.assertEqual(calls, [])
        self.assertIn("grantwriter_purpose", str(ctx.exception))

    def test_grantwriter_generation_allowed_when_approved(self):
        result = guarded_grantwriter_generation(
            lambda prompt: f"draft for {prompt}",
            "community health grant",
            store=_approved_store("grantwriter_purpose"),
        )
        self.assertEqual(result, "draft for community health grant")


class TestChecklist(unittest.TestCase):
    def test_checklist_has_one_row_per_gate(self):
        rows = approval_checklist(ApprovalStore())
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["gate"] for row in rows}, set(GATE_IDS))
        for row in rows:
            self.assertEqual(row["status"], UNAPPROVED)
            self.assertTrue(row["label"])
            self.assertTrue(row["unlocks"])
            self.assertTrue(row["how_to_approve"])

    def test_render_checklist_shows_all_labels_and_status(self):
        text = render_checklist(ApprovalStore())
        for gate in GATES:
            self.assertIn(gate.label, text)
            self.assertIn(gate.gate_id, text)
        self.assertIn("0/9 gates approved", text)
        self.assertIn("Free resources first", text)

    def test_render_checklist_shows_single_approval(self):
        store = _approved_store("gateway_workflow_fix")
        text = render_checklist(store)
        self.assertIn("1/9 gates approved", text)
        self.assertIn("[APPROVED]   Gateway workflow fix", text)
        self.assertIn("[UNAPPROVED] Stripe live keys", text)


class TestDaedalusWiring(unittest.TestCase):
    def test_build_engine_with_fake_key_is_not_gated(self):
        # Local fake transport: not live operation, no approval needed.
        engine = build_engine(_config(), approval_store=ApprovalStore())
        self.assertIsNotNone(engine)

    def test_build_engine_with_live_key_blocked_when_unapproved(self):
        with self.assertRaises(ApprovalRequiredError) as ctx:
            build_engine(
                _config(api_key=LIVE_SHAPE_KEY),
                approval_store=ApprovalStore(),
            )
        self.assertIn("daedalus_live", str(ctx.exception))

    def test_build_engine_with_live_key_blocked_when_only_one_gate_approved(self):
        # Both daedalus_live AND anthropic_live_model are required.
        store = _approved_store("daedalus_live")
        with self.assertRaises(ApprovalRequiredError) as ctx:
            build_engine(_config(api_key=LIVE_SHAPE_KEY), approval_store=store)
        self.assertIn("anthropic_live_model", str(ctx.exception))

    def test_build_engine_with_live_key_allowed_when_both_gates_approved(self):
        store = _approved_store("daedalus_live", "anthropic_live_model")
        engine = build_engine(
            _config(api_key=LIVE_SHAPE_KEY), approval_store=store
        )
        self.assertIsNotNone(engine)

    def test_build_live_engine_requires_approval_even_for_fake_key(self):
        with self.assertRaises(ApprovalRequiredError):
            build_live_engine(_config(), approval_store=ApprovalStore())
        store = _approved_store("daedalus_live", "anthropic_live_model")
        engine = build_live_engine(_config(), approval_store=store)
        self.assertIsNotNone(engine)

    def test_build_voice_runner_with_live_key_blocked_when_unapproved(self):
        with self.assertRaises(ApprovalRequiredError):
            build_voice_runner(
                _config(api_key=LIVE_SHAPE_KEY),
                transcriber=FakeTranscriber("hello"),
                speaker=FakeSpeaker(),
                approval_store=ApprovalStore(),
            )

    def test_build_voice_runner_with_fake_key_not_gated(self):
        runner = build_voice_runner(
            _config(),
            transcriber=FakeTranscriber("hello"),
            speaker=FakeSpeaker(),
            approval_store=ApprovalStore(),
        )
        self.assertEqual(runner.language, "Python")


if __name__ == "__main__":
    unittest.main()
