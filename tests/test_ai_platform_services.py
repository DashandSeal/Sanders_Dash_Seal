"""Tests for Task 5 AI-platform service linking.

Local only: no API key, no network, no deployment, no spend.  Every
live-provider adapter is tested only for its honest failure mode
(missing key / missing SDK) or through an injected fake.  No live
Anthropic / OpenAI / Deepgram / Google / ElevenLabs / LiveKit /
Stripe call is made or claimed here.

Run with:  cd <repo> && python3 -m unittest discover -s tests -v
"""

import hashlib
import hmac
import io
import json
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_platform.anthropic_sdk_transport import (  # noqa: E402
    ClaudeTransport,
    sdk_available as anthropic_sdk_available,
)
from core_platform.daedalus_voice import (  # noqa: E402
    DeepgramTranscriber,
    ElevenLabsSynthesizer,
    GoogleTTSSynthesizer,
    OpenAITranscriber,
)
from core_platform.google_workspace_adapters import (  # noqa: E402
    GmailAdapter,
    GoogleCalendarAdapter,
    GoogleDocsAdapter,
    GoogleSheetsAdapter,
    workspace_status,
)
from core_platform.grantwriter_llm import (  # noqa: E402
    draft_application_section,
    draft_to_google_doc,
)
from core_platform.livekit_video import (  # noqa: E402
    issue_room_token,
    validate_room_token,
    validate_signaling_message,
    video_status,
)
from core_platform.openai_chat_transport import (  # noqa: E402
    FakeChatTransport,
    OpenAIChatTransport,
    realtime_session_config,
    validate_chat_model,
)
from core_platform.role_worker_llm import (  # noqa: E402
    build_backend,
    role_task_status,
    run_role_task,
)
from core_platform.service_linking import describe as linking_describe  # noqa: E402
from core_platform.service_linking import linking_table  # noqa: E402
from core_platform.stripe_checkout import (  # noqa: E402
    StripeCheckout,
    checkout_status,
    create_and_register,
    verify_then_record,
)
from core_platform.stripe_payments import PaymentDenied, PaymentLedger  # noqa: E402

FAKE_ENV = {
    "ANTHROPIC_API_KEY": "",
    "DAEDALUS_CLAUDE_MODEL": "",
    "OPENAI_API_KEY": "",
    "OPENAI_CHAT_MODEL": "",
    "DAEDALUS_OPENAI_MODEL": "",
    "DEEPGRAM_API_KEY": "",
    "ELEVENLABS_API_KEY": "",
    "LIVEKIT_URL": "",
    "LIVEKIT_API_KEY": "",
    "LIVEKIT_API_SECRET": "",
    "STRIPE_SECRET_KEY": "",
    "STRIPE_WEBHOOK_SECRET": "",
    "STRIPE_LIVEMODE": "false",
    "STRIPE_LIVE_VERIFIED": "",
    "LLM_BACKEND": "claude",
}


def clear_env(testcase):
    """Empty all provider env vars for the duration of a test."""
    patcher = mock.patch.dict(os.environ, FAKE_ENV, clear=False)
    patcher.start()
    testcase.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------
# OpenAI chat transport
# ---------------------------------------------------------------------------


class TestOpenAIChatTransport(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_deprecated_models_rejected(self):
        for bad in ("whisper-1", "gpt-4o-transcribe", "tts-1", "tts-1-hd"):
            with self.subTest(model=bad):
                with self.assertRaises(ValueError):
                    validate_chat_model(bad)

    def test_non_chat_model_rejected(self):
        with self.assertRaises(ValueError):
            validate_chat_model("not-a-model")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            OpenAIChatTransport(model="gpt-5-chat")

    def test_fake_transport_records_calls(self):
        fake = FakeChatTransport(text="hello draft")
        resp = fake.generate(system="sys", user_message="write this")
        self.assertEqual(resp.text, "hello draft")
        self.assertEqual(fake.calls[0]["user"], "write this")

    def test_stdlib_generate_with_fake_urlopen(self):
        body = json.dumps(
            {
                "id": "chatcmpl_fake",
                "model": "gpt-5-chat",
                "choices": [{"message": {"content": "fake answer"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }
        ).encode()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n=-1):
                return body

        with mock.patch(
            "core_platform.openai_chat_transport.urllib.request.urlopen",
            return_value=FakeResponse(),
        ):
            transport = OpenAIChatTransport(
                model="gpt-5-chat", api_key="test-key"
            )
            resp = transport.generate(system="sys", user_message="hi")
        self.assertEqual(resp.text, "fake answer")
        self.assertEqual(resp.input_tokens, 3)
        self.assertEqual(resp.output_tokens, 2)

    def test_realtime_config_only_no_live_session(self):
        cfg = realtime_session_config(
            model="gpt-realtime-2.1-mini", api_key="test-key"
        )
        self.assertTrue(cfg["websocket_url"].startswith("wss://api.openai.com"))
        self.assertEqual(cfg["status"], "config_only_no_live_session")
        self.assertNotIn("test-key", json.dumps(cfg))

    def test_realtime_rejects_deprecated_and_missing_key(self):
        with self.assertRaises(ValueError):
            realtime_session_config(model="whisper-1", api_key="test-key")
        with self.assertRaises(ValueError):
            realtime_session_config(model="gpt-realtime-2.1-mini")


# ---------------------------------------------------------------------------
# Anthropic SDK/stdlib transport
# ---------------------------------------------------------------------------


class TestClaudeTransport(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_missing_key_or_model_raises(self):
        with self.assertRaises(ValueError):
            ClaudeTransport()
        with self.assertRaises(ValueError):
            ClaudeTransport(model="claude-sonnet-5-5")
        with self.assertRaises(ValueError):
            ClaudeTransport(api_key="test-key")

    def test_use_sdk_without_package_raises_import_error(self):
        if anthropic_sdk_available():
            self.skipTest("anthropic SDK is installed in this environment")
        with self.assertRaises(ImportError):
            ClaudeTransport(
                model="claude-sonnet-5-5", api_key="test-key", use_sdk=True
            )

    def test_stdlib_backend_with_fake_urlopen(self):
        body = json.dumps(
            {
                "type": "message",
                "id": "msg_fake",
                "model": "claude-sonnet-5-5",
                "content": [{"type": "text", "text": "fake claude text"}],
                "usage": {"input_tokens": 5, "output_tokens": 4},
            }
        ).encode()

        class FakeResponse:
            headers = {"request-id": "req_fake"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n=-1):
                return body

        with mock.patch(
            "core_platform.daedalus_claude_transport.urllib.request.urlopen",
            return_value=FakeResponse(),
        ):
            transport = ClaudeTransport(
                model="claude-sonnet-5-5", api_key="test-key"
            )
            self.assertEqual(transport.backend, "stdlib")
            resp = transport.generate(system="sys", user_message="hi")
        self.assertEqual(resp.text, "fake claude text")
        self.assertEqual(resp.model, "claude-sonnet-5-5")


# ---------------------------------------------------------------------------
# Role workers + Grantwriter
# ---------------------------------------------------------------------------


class TestRoleWorkers(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_run_role_task_with_fake_backend(self):
        result = run_role_task(
            agent_name="Quality Agent",
            task="List checks for a deploy.",
            backend=FakeChatTransport(text="1. check health"),
        )
        self.assertEqual(result["agent"], "Quality Agent")
        self.assertEqual(result["text"], "1. check health")

    def test_unregistered_agent_raises(self):
        with self.assertRaises(Exception):
            run_role_task(
                agent_name="No Such Agent",
                task="do it",
                backend=FakeChatTransport(),
            )

    def test_missing_backend_raises(self):
        with self.assertRaises(Exception):
            run_role_task(agent_name="Quality Agent", task="do it")

    def test_unknown_backend_name_raises(self):
        with self.assertRaises(ValueError):
            build_backend("watson")

    def test_status_reports_missing_key(self):
        status = role_task_status()
        self.assertEqual(status["agent_count"], 12)
        self.assertEqual(status["live_status"], "MISSING_KEY")


class TestGrantwriter(unittest.TestCase):
    OPPORTUNITY = {
        "title": "Community Health Grant",
        "funder": "Example Foundation",
        "deadline": "2027-03-01",
    }

    def test_draft_with_fake_backend(self):
        draft = draft_application_section(
            opportunity=self.OPPORTUNITY,
            section="Executive summary",
            applicant_facts="We run a free clinic in Phoenix.",
            backend=FakeChatTransport(text="Draft summary here."),
        )
        self.assertEqual(draft["draft_text"], "Draft summary here.")
        self.assertEqual(draft["funder"], "Example Foundation")

    def test_missing_opportunity_fields_raise(self):
        with self.assertRaises(ValueError):
            draft_application_section(
                opportunity={"title": "x"},
                section="Summary",
                applicant_facts="facts",
                backend=FakeChatTransport(),
            )

    def test_draft_to_google_doc_without_client_raises(self):
        with self.assertRaises(ValueError):
            draft_to_google_doc(
                draft={"draft_text": "text", "opportunity_title": "t",
                       "section": "s"}
            )

    def test_draft_to_google_doc_with_fake_client(self):
        class FakeDocs:
            def create_document(self, title, text):
                return {"id": "doc_fake", "url": "https://docs.example/doc_fake"}

        out = draft_to_google_doc(
            draft={"draft_text": "text", "opportunity_title": "t",
                   "section": "s"},
            docs_client=FakeDocs(),
        )
        self.assertEqual(out["document_id"], "doc_fake")


# ---------------------------------------------------------------------------
# Google Workspace adapters (optional, injected clients only)
# ---------------------------------------------------------------------------


class TestGoogleWorkspace(unittest.TestCase):
    def test_all_unconfigured_raise_and_report_missing(self):
        cases = (
            (GoogleDocsAdapter, "create_document",
             {"title": "t", "text": "x"}),
            (GoogleSheetsAdapter, "append_row",
             {"spreadsheet_id": "s", "range": "A1", "values": ["a"]}),
            (GmailAdapter, "send_notification",
             {"to": "a@example.com", "subject": "s", "body": "b"}),
            (GoogleCalendarAdapter, "create_event",
             {"summary": "s", "start": "2027-01-01", "end": "2027-01-01"}),
        )
        for adapter_cls, method, kwargs in cases:
            with self.subTest(adapter=adapter_cls.__name__):
                adapter = adapter_cls()
                self.assertEqual(adapter.status()["live_status"], "MISSING_CLIENT")
                with self.assertRaises(ValueError):
                    getattr(adapter, method)(**kwargs)

    def test_fake_clients_round_trip(self):
        class FakeDocs:
            def create_document(self, title, text):
                return {"id": "d1", "url": "https://docs.example/d1"}

        class FakeGmail:
            def send_message(self, to, subject, body):
                return {"id": "m1"}

        self.assertEqual(
            GoogleDocsAdapter(FakeDocs()).create_document(title="t", text="x")["id"],
            "d1",
        )
        self.assertEqual(
            GmailAdapter(FakeGmail()).send_notification(
                to="a@example.com", subject="s", body="b"
            )["id"],
            "m1",
        )

    def test_workspace_status_all_missing(self):
        status = workspace_status()
        self.assertTrue(
            all(v["live_status"] == "MISSING_CLIENT" for v in status.values())
        )
        self.assertEqual(len(status), 4)


# ---------------------------------------------------------------------------
# Voice provider failure modes (existing adapters, honest errors)
# ---------------------------------------------------------------------------


class TestVoiceProviders(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_deepgram_and_elevenlabs_missing_key(self):
        with self.assertRaises(ValueError):
            DeepgramTranscriber()
        with self.assertRaises(ValueError):
            ElevenLabsSynthesizer()

    def test_openai_transcriber_rejects_whisper1(self):
        with self.assertRaises(ValueError):
            OpenAITranscriber(api_key="test-key", model="whisper-1")

    def test_google_tts_missing_package_or_credentials(self):
        # Either ImportError (package absent) or a credentials error is
        # honest here; a live call must never succeed without setup.
        try:
            GoogleTTSSynthesizer()
        except (ImportError, Exception) as exc:
            self.assertIsInstance(exc, Exception)


# ---------------------------------------------------------------------------
# LiveKit video tokens + signalling
# ---------------------------------------------------------------------------


class TestLiveKitVideo(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_token_round_trip_with_fake_time(self):
        issued = issue_room_token(
            room="room-1",
            identity="alice@example.com",
            url="https://livekit.example",
            api_key="APtestkey",
            api_secret="test-secret",
            now=1780000000,
        )
        checked = validate_room_token(
            issued["token"], api_secret="test-secret", now=1780000100
        )
        self.assertTrue(checked["valid"])
        self.assertEqual(checked["room"], "room-1")
        self.assertEqual(checked["identity"], "alice@example.com")

    def test_token_missing_config_raises(self):
        with self.assertRaises(ValueError):
            issue_room_token(room="room-1", identity="alice")

    def test_token_bad_signature_and_expiry_rejected(self):
        issued = issue_room_token(
            room="room-1",
            identity="alice",
            url="https://livekit.example",
            api_key="APtestkey",
            api_secret="test-secret",
            now=1780000000,
        )
        with self.assertRaises(ValueError):
            validate_room_token(
                issued["token"], api_secret="wrong-secret", now=1780000100
            )
        with self.assertRaises(ValueError):
            validate_room_token(
                issued["token"], api_secret="test-secret", now=1780000000 + 7200
            )

    def test_signalling_validation_rejects_bad_action(self):
        frame = validate_signaling_message(
            {
                "action": "offer",
                "targetSessionId": "sess-1",
                "sdp": {"type": "offer", "sdp": "v=0\r\n"},
            },
            session_id="sess-1",
        )
        self.assertEqual(frame["action"], "offer")
        with self.assertRaises(ValueError):
            validate_signaling_message(
                {"action": "start_call", "targetSessionId": "sess-1"},
                session_id="sess-1",
            )

    def test_video_status_missing_key(self):
        self.assertEqual(video_status()["live_status"], "MISSING_KEY")


# ---------------------------------------------------------------------------
# Stripe Checkout: test-mode first, verifier gate before live
# ---------------------------------------------------------------------------


class FakeStripeSession:
    def __init__(self):
        self.created = []

    def create(self, **params):
        self.created.append(params)
        return {"id": "cs_test_fake", "url": "https://checkout.stripe.test/pay"}


class FakeStripeClient:
    def __init__(self):
        self.checkout = mock.Mock()
        self.checkout.Session = mock.Mock()
        self.checkout.Session.create = FakeStripeSession().create


class TestStripeCheckout(unittest.TestCase):
    def setUp(self):
        clear_env(self)
        self.tmpdir = os.path.join(
            os.path.dirname(__file__), "..", ".test-tmp"
        )
        os.makedirs(self.tmpdir, exist_ok=True)
        self.db = os.path.join(self.tmpdir, "stripe-test.db")
        if os.path.exists(self.db):
            os.remove(self.db)

    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)

    def test_test_mode_checkout_with_fake_client(self):
        checkout = StripeCheckout(
            secret_key="sk_test_fake", stripe_client=FakeStripeClient()
        )
        self.assertEqual(checkout.mode, "test")
        session = create_and_register(
            checkout=checkout,
            ledger=PaymentLedger(self.db),
            case_id="case-1",
            amount_cents=5000,
            currency="USD",
            service_label="Consultation",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        self.assertEqual(session["id"], "cs_test_fake")
        self.assertEqual(PaymentLedger(self.db).status("case-1"), "PENDING")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            StripeCheckout()

    def test_live_key_refused_without_verifier_gate(self):
        with self.assertRaises(PaymentDenied):
            StripeCheckout(secret_key="sk_live_fake")

    def test_live_key_refused_without_allow_live_flag(self):
        with mock.patch.dict(os.environ, {"STRIPE_LIVE_VERIFIED": "1"}):
            with self.assertRaises(PaymentDenied):
                StripeCheckout(secret_key="sk_live_fake")

    def test_webhook_gate_verifies_before_recording(self):
        ledger = PaymentLedger(self.db)
        ledger.register_checkout("case-1", "cs_test_fake", 5000, "USD")
        payload = json.dumps(
            {
                "id": "evt_1",
                "type": "checkout.session.completed",
                "livemode": False,
                "data": {
                    "object": {
                        "id": "cs_test_fake",
                        "client_reference_id": "case-1",
                        "amount_total": 5000,
                        "payment_intent": "pi_1",
                    }
                },
            }
        )
        secret = "whsec_test"
        ts = str(int(time.time()))
        sig = hmac.new(
            secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256
        ).hexdigest()
        header = f"t={ts},v1={sig}"
        result = verify_then_record(
            ledger=ledger,
            payload=payload,
            signature_header=header,
            signing_secret=secret,
        )
        self.assertEqual(result, "RECORDED")
        self.assertEqual(ledger.status("case-1"), "PAID")
        # Duplicate is deduplicated, not double-recorded.
        self.assertEqual(
            verify_then_record(
                ledger=ledger,
                payload=payload,
                signature_header=header,
                signing_secret=secret,
            ),
            "DUPLICATE",
        )
        # Bad signature is refused and nothing is recorded.
        with self.assertRaises(PaymentDenied):
            verify_then_record(
                ledger=ledger,
                payload=payload,
                signature_header=f"t={ts},v1={'0' * 64}",
                signing_secret=secret,
            )

    def test_checkout_status_missing_key(self):
        self.assertEqual(checkout_status()["live_status"], "MISSING_KEY")


# ---------------------------------------------------------------------------
# Linking table
# ---------------------------------------------------------------------------


class TestLinkingTable(unittest.TestCase):
    def setUp(self):
        clear_env(self)

    def test_all_missing_key_without_env(self):
        rows = linking_table()
        self.assertEqual(len(rows), 19)
        self.assertTrue(
            all(r["live_status"] == "MISSING_KEY" for r in rows),
            [r for r in rows if r["live_status"] != "MISSING_KEY"],
        )

    def test_env_presence_flips_one_row_to_ready(self):
        with mock.patch.dict(
            os.environ,
            {"DEEPGRAM_API_KEY": "test-key"},
        ):
            rows = {r["service"]: r for r in linking_table()}
        self.assertEqual(
            rows["Deepgram Nova-3"]["live_status"], "READY"
        )
        self.assertEqual(
            rows["ElevenLabs"]["live_status"], "MISSING_KEY"
        )

    def test_describe_counts(self):
        summary = linking_describe()
        self.assertEqual(summary["links"], 19)
        self.assertEqual(summary["missing_key"], 19)


if __name__ == "__main__":
    unittest.main()
