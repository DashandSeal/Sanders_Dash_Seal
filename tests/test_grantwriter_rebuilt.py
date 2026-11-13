"""Tests for the REBUILT (not restored) Grantwriter module.

app/grantwriter_mother.py was rebuilt 2026-11-13 because no compiling
original exists in git history. These tests use only stdlib fakes and a
temporary SQLite file: no network, no keys, no live Google/Anthropic/
OpenAI calls. Run: python3 -m unittest tests.test_grantwriter_rebuilt -v
(from the repo root).
"""

import importlib.util
import os
import py_compile
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "app" / "grantwriter_mother.py"

OWNER = "owner-test-1"
OTHER_OWNER = "owner-test-2"


def load_module():
    spec = importlib.util.spec_from_file_location("grantwriter_mother_rebuilt", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gw = load_module()


def make_opportunity_body(**overrides):
    body = {
        "title": "Community Health Grant",
        "funder": "Test Foundation",
        "source_url": "https://example.invalid/grants/1",
        "deadline": "2027-03-01",
        "ceiling": "50000.00",
        "eligibility": ["nonprofit", "health"],
        "requirements": ["narrative", "budget"],
    }
    body.update(overrides)
    return body


class GrantwriterTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._db_path = Path(self._tmp.name) / "grantwriter.sqlite3"
        self._env = mock.patch.dict(
            os.environ,
            {
                "SANDERS_GRANTWRITER_DB": str(self._db_path),
                "ANTHROPIC_API_KEY": "",
                "OPENAI_API_KEY": "",
                "ANTHROPIC_MODEL": "",
                "OPENAI_MODEL": "",
            },
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.conn = gw.database()
        self.addCleanup(self.conn.close)

    def make_application(self, owner=OWNER):
        opp = gw.create_opportunity(self.conn, owner, make_opportunity_body())
        app = gw.create_application(
            self.conn,
            owner,
            {
                "opportunity_id": opp["id"],
                "organization": "Sanders Test Org",
                "project": "Community clinic outreach",
            },
        )
        return opp["id"], app["id"]


class TestModuleIntegrity(GrantwriterTestBase):
    def test_file_compiles(self):
        py_compile.compile(str(MODULE_PATH), doraise=True)

    def test_labeled_rebuilt_not_restored(self):
        self.assertTrue(gw.REBUILT_NOT_RESTORED)
        self.assertIn("REBUILT NOT RESTORED", gw.__doc__)

    def test_no_realtime_ai_import(self):
        self.assertNotIn("from realtime_ai", MODULE_PATH.read_text())

    def test_platform_identity_preserved(self):
        self.assertEqual(gw.PLATFORM.name, "Grantwriter")
        self.assertEqual(gw.PLATFORM.nickname, "Mother")
        self.assertEqual(
            gw.PLATFORM.codes, ("541611", "541612", "541613", "541614", "541618", "541690")
        )
        self.assertIn("Grantwriter service domain", gw.PLATFORM.system_instruction)

    def test_database_creates_all_tables(self):
        tables = {
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertTrue(
            {"opportunities", "applications", "budget_lines", "evidence", "audit"}
            <= tables
        )

    def test_synchronize_cloud_state_does_not_raise_without_oci(self):
        result = gw.synchronize_cloud_state()
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)


class TestMoneyAndValidation(GrantwriterTestBase):
    def test_money_cents(self):
        self.assertEqual(gw.money_cents("1234.56"), 123456)
        self.assertEqual(gw.money_cents("0"), 0)
        self.assertEqual(gw.money_cents(10), 1000)
        self.assertEqual(gw.money_cents("100000000000"), 10000000000000)

    def test_money_cents_rejects_bad_values(self):
        for bad in ("-1", "10.005", "100000000001", "not-a-number", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    gw.money_cents(bad)

    def test_require_string_rejects_blank_and_too_long(self):
        with self.assertRaises(ValueError):
            gw.require_string({}, "title")
        with self.assertRaises(ValueError):
            gw.require_string({"title": "x" * 2001}, "title")


class TestOpportunitiesApplicationsEvidence(GrantwriterTestBase):
    def test_create_opportunity_and_application_round_trip(self):
        opp_id, app_id = self.make_application()
        opp = gw.list_opportunities(self.conn, OWNER)
        self.assertEqual(len(opp), 1)
        self.assertEqual(opp[0]["id"], opp_id)
        self.assertEqual(opp[0]["ceiling_cents"], 5000000)
        self.assertEqual(opp[0]["eligibility"], ["nonprofit", "health"])
        view = gw.get_application(self.conn, OWNER, app_id)
        self.assertEqual(view["status"], "draft")
        self.assertEqual(view["version"], 1)
        self.assertEqual(view["organization"], "Sanders Test Org")
        self.assertEqual(view["opportunity"]["title"], "Community Health Grant")
        self.assertEqual(view["evidence"], [])
        self.assertEqual(view["budget_lines"], [])

    def test_add_evidence_stores_row_bumps_version_and_audits(self):
        _, app_id = self.make_application()
        before = gw.get_application(self.conn, OWNER, app_id)
        result = gw.add_evidence(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "label": "IRS determination letter",
                "reference": "doc://irs-501c3",
                "notes": "Confirms nonprofit status.",
            },
        )
        self.assertIn("id", result)
        after = gw.get_application(self.conn, OWNER, app_id)
        self.assertEqual(after["version"], before["version"] + 1)
        self.assertEqual(len(after["evidence"]), 1)
        self.assertEqual(after["evidence"][0]["label"], "IRS determination letter")
        actions = [a["action"] for a in gw.list_audit(self.conn, OWNER, app_id)]
        self.assertIn("evidence_added", actions)

    def test_add_evidence_rejects_overlong_notes(self):
        _, app_id = self.make_application()
        with self.assertRaises(ValueError):
            gw.add_evidence(
                self.conn,
                OWNER,
                {
                    "application_id": app_id,
                    "label": "x",
                    "reference": "y",
                    "notes": "n" * 4001,
                },
            )

    def test_add_budget_line(self):
        _, app_id = self.make_application()
        gw.add_budget_line(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "category": "Personnel",
                "description": "Outreach coordinator",
                "amount": "12000.50",
            },
        )
        view = gw.get_application(self.conn, OWNER, app_id)
        self.assertEqual(len(view["budget_lines"]), 1)
        self.assertEqual(view["budget_lines"][0]["amount_cents"], 1200050)

    def test_owner_isolation(self):
        _, app_id = self.make_application(owner=OWNER)
        with self.assertRaises(ValueError) as ctx:
            gw.get_application(self.conn, OTHER_OWNER, app_id)
        self.assertEqual(str(ctx.exception), "not_found")
        with self.assertRaises(ValueError):
            gw.add_evidence(
                self.conn,
                OTHER_OWNER,
                {
                    "application_id": app_id,
                    "label": "x",
                    "reference": "y",
                    "notes": "z",
                },
            )

    def test_update_narrative_version_conflict_and_success(self):
        _, app_id = self.make_application()
        with self.assertRaises(ValueError) as ctx:
            gw.update_narrative(
                self.conn,
                OWNER,
                {"application_id": app_id, "narrative": "v1", "expected_version": 99},
            )
        self.assertEqual(str(ctx.exception), "version_conflict")
        result = gw.update_narrative(
            self.conn,
            OWNER,
            {"application_id": app_id, "narrative": "Our story.", "expected_version": 1},
        )
        self.assertEqual(result["version"], 2)
        view = gw.get_application(self.conn, OWNER, app_id)
        self.assertEqual(view["narrative"], "Our story.")
        self.assertEqual(view["status"], "draft")
        actions = [a["action"] for a in gw.list_audit(self.conn, OWNER, app_id)]
        self.assertIn("narrative_updated", actions)

    def test_audit_trail_order(self):
        _, app_id = self.make_application()
        gw.add_evidence(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "label": "a",
                "reference": "b",
                "notes": "c",
            },
        )
        actions = [a["action"] for a in gw.list_audit(self.conn, OWNER, app_id)]
        self.assertEqual(
            actions, ["application_created", "evidence_added"]
        )


class FakeDocsClient:
    def __init__(self):
        self.calls = []

    def create_document(self, title, text):
        self.calls.append({"title": title, "text": text})
        return {"documentId": "fake-doc-1", "title": title, "chars": len(text)}


class TestDraftGenerationAndExport(GrantwriterTestBase):
    def test_generate_draft_with_fake_generator(self):
        _, app_id = self.make_application()
        gw.add_evidence(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "label": "IRS determination letter",
                "reference": "doc://irs-501c3",
                "notes": "Confirms nonprofit status.",
            },
        )
        gw.add_budget_line(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "category": "Personnel",
                "description": "Coordinator",
                "amount": "1000",
            },
        )
        result = gw.generate_draft(self.conn, OWNER, app_id)
        self.assertEqual(result["generator"], "fake_template")
        self.assertEqual(result["evidence_count"], 1)
        self.assertIn("IRS determination letter", result["draft"])
        self.assertIn("TEMPLATE DRAFT", result["draft"])
        self.assertIn("[UNVERIFIED]", result["draft"])
        # Draft generation must not overwrite the stored narrative.
        view = gw.get_application(self.conn, OWNER, app_id)
        self.assertEqual(view["narrative"], "")
        actions = [a["action"] for a in gw.list_audit(self.conn, OWNER, app_id)]
        self.assertIn("draft_generated", actions)

    def test_generate_then_save_draft_via_update_narrative(self):
        _, app_id = self.make_application()
        result = gw.generate_draft(self.conn, OWNER, app_id)
        view = gw.get_application(self.conn, OWNER, app_id)
        saved = gw.update_narrative(
            self.conn,
            OWNER,
            {
                "application_id": app_id,
                "narrative": result["draft"],
                "expected_version": view["version"],
            },
        )
        self.assertEqual(saved["version"], view["version"] + 1)

    def test_anthropic_generator_fails_honestly_without_key(self):
        _, app_id = self.make_application()
        with self.assertRaises(gw.GrantwriterError) as ctx:
            gw.generate_draft(self.conn, OWNER, app_id, generator=gw.AnthropicGenerator())
        self.assertEqual(ctx.exception.code, "anthropic_not_configured")

    def test_openai_generator_fails_honestly_without_key(self):
        _, app_id = self.make_application()
        with self.assertRaises(gw.GrantwriterError) as ctx:
            gw.generate_draft(self.conn, OWNER, app_id, generator=gw.OpenAIGenerator())
        self.assertEqual(ctx.exception.code, "openai_not_configured")

    def test_anthropic_generator_with_key_but_no_model_fails_before_network(self):
        gen = gw.AnthropicGenerator(api_key="fake-key-for-test-only")
        with self.assertRaises(gw.GrantwriterError) as ctx:
            gen.generate("prompt", {})
        self.assertEqual(ctx.exception.code, "anthropic_model_not_configured")

    def test_google_docs_exporter_requires_client(self):
        exporter = gw.GoogleDocsExporter()
        with self.assertRaises(gw.GrantwriterError) as ctx:
            exporter.export("draft text", "Test title")
        self.assertEqual(ctx.exception.code, "google_docs_not_configured")

    def test_google_docs_exporter_with_fake_client(self):
        fake = FakeDocsClient()
        result = gw.GoogleDocsExporter().export("draft text", "Test title", docs_client=fake)
        self.assertEqual(result["documentId"], "fake-doc-1")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["title"], "Test title")
        self.assertEqual(fake.calls[0]["text"], "draft text")

    def test_build_draft_prompt_uses_only_supplied_facts(self):
        _, app_id = self.make_application()
        context = gw.get_application(self.conn, OWNER, app_id)
        prompt = gw.build_draft_prompt(context)
        self.assertIn("Community Health Grant", prompt)
        self.assertIn("[UNVERIFIED]", prompt)
        self.assertIn("ONLY the facts below", prompt)


class TestPersistenceAcrossConnections(GrantwriterTestBase):
    def test_data_survives_reconnect(self):
        _, app_id = self.make_application()
        self.conn.close()
        conn2 = gw.database()
        try:
            view = gw.get_application(conn2, OWNER, app_id)
            self.assertEqual(view["organization"], "Sanders Test Org")
        finally:
            conn2.close()


if __name__ == "__main__":
    unittest.main()
