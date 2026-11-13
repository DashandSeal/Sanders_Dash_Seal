"""Tests for core_platform.global_compliance and global_connectivity.

Fakes only. Stdlib unittest. No network, no keys, no live calls.
Run from the worktree root:
    python3 -m unittest tests.test_global_compliance -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_platform.global_compliance import (  # noqa: E402
    APPROVED_RON_JURISDICTIONS,
    AccessibilityChecklist,
    ConsentStore,
    DataSubjectRequestHandler,
    InMemoryRecordStore,
    NotApprovedInJurisdiction,
    check_html_accessibility,
    gate_ron,
    jurisdiction_status,
)
from core_platform.global_connectivity import (  # noqa: E402
    backoff_seconds,
    fallback_for,
    policy_for,
)


class TestConsent(unittest.TestCase):
    def setUp(self):
        self.store = ConsentStore()

    def test_grant_records_granted_with_utc_timestamp(self):
        rec = self.store.grant("subject-1", "appointment_contact")
        self.assertTrue(rec.granted)
        self.assertEqual(rec.subject_id, "subject-1")
        self.assertEqual(rec.scope, "appointment_contact")
        self.assertIsNotNone(rec.granted_at_utc)
        self.assertIn("T", rec.granted_at_utc)  # ISO-8601
        self.assertTrue(rec.granted_at_utc.endswith("+00:00"))
        self.assertIsNone(rec.withdrawn_at_utc)
        self.assertTrue(self.store.is_granted("subject-1", "appointment_contact"))

    def test_withdraw_after_grant(self):
        granted = self.store.grant("subject-1", "av_recording")
        withdrawn = self.store.withdraw("subject-1", "av_recording")
        self.assertFalse(withdrawn.granted)
        self.assertEqual(withdrawn.granted_at_utc, granted.granted_at_utc)
        self.assertIsNotNone(withdrawn.withdrawn_at_utc)
        self.assertFalse(self.store.is_granted("subject-1", "av_recording"))

    def test_withdraw_without_prior_grant_is_recorded_not_granted(self):
        rec = self.store.withdraw("subject-1", "av_recording")
        self.assertFalse(rec.granted)
        self.assertIsNone(rec.granted_at_utc)
        self.assertIsNotNone(rec.withdrawn_at_utc)

    def test_unknown_subject_scope_is_not_granted(self):
        self.assertIsNone(self.store.status("nobody", "av_recording"))
        self.assertFalse(self.store.is_granted("nobody", "av_recording"))

    def test_scopes_are_independent(self):
        self.store.grant("subject-1", "appointment_contact")
        self.assertFalse(self.store.is_granted("subject-1", "av_recording"))

    def test_all_for_subject_lists_only_that_subject(self):
        self.store.grant("subject-1", "a")
        self.store.grant("subject-2", "a")
        rows = self.store.all_for_subject("subject-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subject_id"], "subject-1")


class TestExportDelete(unittest.TestCase):
    def setUp(self):
        self.cases = InMemoryRecordStore("cases")
        self.cases.add({"subject_id": "subject-1", "case_id": "C-1", "service": "RON"})
        self.cases.add({"subject_id": "subject-2", "case_id": "C-2", "service": "RON"})
        self.cases.add({"subject_id": "subject-1", "case_id": "C-3", "service": "MOBILE_NOTARY"})
        self.handler = DataSubjectRequestHandler([self.cases])

    def test_export_shape_and_only_own_records(self):
        out = self.handler.export_subject_data("subject-1")
        self.assertEqual(out["subject_id"], "subject-1")
        self.assertIn("exported_at_utc", out)
        self.assertIn("cases", out["stores"])
        self.assertEqual(out["stores"]["cases"]["status"], "EXPORTED")
        records = out["stores"]["cases"]["records"]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r["subject_id"] == "subject-1" for r in records))
        self.assertEqual({r["case_id"] for r in records}, {"C-1", "C-3"})

    def test_export_json_is_valid_json(self):
        parsed = json.loads(self.handler.export_json("subject-2"))
        self.assertEqual(parsed["subject_id"], "subject-2")
        self.assertEqual(len(parsed["stores"]["cases"]["records"]), 1)

    def test_delete_request_recorded_and_deletes_from_real_store(self):
        out = self.handler.request_deletion("subject-1")
        self.assertEqual(out["status"], "RECORDED")
        self.assertTrue(out["request_id"])
        self.assertEqual(out["subject_id"], "subject-1")
        self.assertIn("requested_at_utc", out)
        self.assertEqual(out["per_store"]["cases"]["status"], "DELETED")
        self.assertEqual(out["per_store"]["cases"]["deleted_count"], 2)
        # Only subject-1's records are gone.
        self.assertEqual(len(self.cases.export_for("subject-1")), 0)
        self.assertEqual(len(self.cases.export_for("subject-2")), 1)
        # The request itself is on the recorded-requests log.
        self.assertEqual(self.handler.recorded_requests()[-1]["request_id"], out["request_id"])

    def test_delete_store_without_delete_is_honestly_not_implemented(self):
        class ExportOnlyStore:
            name = "legacy_ledger"

            def export_for(self, subject_id):
                return [{"subject_id": subject_id, "note": "legacy"}]

        handler = DataSubjectRequestHandler([ExportOnlyStore()])
        out = handler.request_deletion("subject-1")
        self.assertEqual(out["status"], "RECORDED")
        self.assertEqual(out["per_store"]["legacy_ledger"]["status"], "NOT_IMPLEMENTED")
        self.assertEqual(out["per_store"]["legacy_ledger"]["deleted_count"], 0)

    def test_export_rejects_empty_subject(self):
        with self.assertRaises(ValueError):
            self.handler.export_subject_data("   ")


class TestRonGating(unittest.TestCase):
    def test_no_jurisdiction_approved_by_default(self):
        self.assertEqual(len(APPROVED_RON_JURISDICTIONS), 0)

    def test_gate_fails_closed_for_unapproved_jurisdiction(self):
        for code in ("CO", "WI", "FL", "WY", "US", "EEA"):
            with self.assertRaises(NotApprovedInJurisdiction) as ctx:
                gate_ron(code)
            self.assertEqual(ctx.exception.code, "NOT_APPROVED_IN_JURISDICTION")

    def test_gate_fails_closed_for_no_jurisdiction(self):
        for bad in ("", "   ", None, 123):
            with self.assertRaises(NotApprovedInJurisdiction) as ctx:
                gate_ron(bad)
            self.assertEqual(ctx.exception.code, "NOT_APPROVED_IN_JURISDICTION")

    def test_gate_allows_only_explicitly_approved_jurisdiction(self):
        result = gate_ron("CO", approved={"CO"})
        self.assertEqual(result, {"ok": True, "jurisdiction": "CO"})
        # Approval is case-insensitive, but must be explicit.
        self.assertEqual(gate_ron("co", approved={"CO"})["jurisdiction"], "CO")
        with self.assertRaises(NotApprovedInJurisdiction):
            gate_ron("WI", approved={"CO"})

    def test_registry_marks_every_jurisdiction_ron_not_approved(self):
        for code in ("CO", "WI", "WY", "FL", "US", "EEA", "UK", "CA"):
            rule = jurisdiction_status(code)
            self.assertIsNotNone(rule)
            self.assertEqual(rule.ron_status, "needs_owner_approval")

    def test_unknown_jurisdiction_has_no_registry_entry(self):
        self.assertIsNone(jurisdiction_status("XX"))


class TestAccessibility(unittest.TestCase):
    GOOD_HTML = """<html lang="en"><head><title>t</title></head><body>
      <a href="#main">Skip to main content</a>
      <img src="/a.png" alt="Founder portrait">
      <label for="name">Name</label><input id="name" type="text">
      <button type="submit">Submit</button>
      <div role="status" aria-live="polite"></div>
      </body></html>"""

    BAD_HTML = """<html><head><title>t</title></head><body>
      <img src="/a.png">
      <input id="name" type="text">
      <button type="submit"></button>
      </body></html>"""

    def test_checklist_passes_good_html(self):
        report = check_html_accessibility(self.GOOD_HTML)
        by_id = {i["id"]: i for i in report["items"]}
        self.assertEqual(by_id["a11y-lang"]["result"], "pass")
        self.assertEqual(by_id["a11y-alt"]["result"], "pass")
        self.assertEqual(by_id["a11y-labels"]["result"], "pass")
        self.assertEqual(by_id["a11y-buttons"]["result"], "pass")
        self.assertEqual(by_id["a11y-live"]["result"], "pass")
        self.assertEqual(report["failed"], 0)

    def test_checklist_fails_bad_html_honestly(self):
        report = check_html_accessibility(self.BAD_HTML)
        by_id = {i["id"]: i for i in report["items"]}
        self.assertEqual(by_id["a11y-lang"]["result"], "fail")
        self.assertEqual(by_id["a11y-alt"]["result"], "fail")
        self.assertEqual(by_id["a11y-labels"]["result"], "fail")
        self.assertEqual(by_id["a11y-buttons"]["result"], "fail")
        self.assertGreaterEqual(report["failed"], 4)
        self.assertIn("a11y-lang", report["summary"])

    def test_unmeasurable_items_are_not_checked_not_passed(self):
        report = check_html_accessibility(self.GOOD_HTML)
        by_id = {i["id"]: i for i in report["items"]}
        for item_id in ("a11y-keyboard", "a11y-focus", "a11y-contrast", "a11y-target"):
            self.assertEqual(by_id[item_id]["result"], "not_checked")

    def test_evidence_checklist_reports_missing_evidence(self):
        report = AccessibilityChecklist.check_page({})
        self.assertEqual(report["passed"], 0)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["not_checked"], len(report["items"]))
        report2 = AccessibilityChecklist.check_page(
            {"a11y-lang": True, "a11y-alt": False})
        by_id = {i["id"]: i for i in report2["items"]}
        self.assertEqual(by_id["a11y-lang"]["result"], "pass")
        self.assertEqual(by_id["a11y-alt"]["result"], "fail")
        self.assertEqual(by_id["a11y-labels"]["result"], "not_checked")

    def test_real_repo_index_page_passes_static_items(self):
        # The repo's own web/index.html is the evidence; the checklist
        # must report on it honestly rather than assume anything.
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "web", "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        report = check_html_accessibility(html)
        by_id = {i["id"]: i for i in report["items"]}
        self.assertEqual(by_id["a11y-lang"]["result"], "pass")
        self.assertEqual(by_id["a11y-labels"]["result"], "pass")
        # Unmeasurable items stay not_checked even for a real page.
        self.assertEqual(by_id["a11y-contrast"]["result"], "not_checked")


class TestConnectivityPolicy(unittest.TestCase):
    def test_policy_for_known_platforms(self):
        for platform in ("daedalus", "openai", "livekit", "deepgram", "elevenlabs", "google"):
            p = policy_for(platform, "us")
            self.assertGreater(p.timeout_seconds, 0)
            self.assertGreaterEqual(p.max_retries, 0)
            self.assertGreater(p.backoff_base_seconds, 0)
            self.assertGreaterEqual(p.backoff_max_seconds, p.backoff_base_seconds)
            self.assertTrue(p.offline_fallback)

    def test_daedalus_timeout_matches_in_repo_precedent(self):
        # daedalus_claude_transport.py defaults to 45 s per request.
        self.assertEqual(policy_for("daedalus", "us").timeout_seconds, 45.0)

    def test_unknown_platform_or_region_raises(self):
        with self.assertRaises(ValueError):
            policy_for("not-a-platform", "us")
        with self.assertRaises(ValueError):
            policy_for("daedalus", "moon")

    def test_free_first_fallback_declared_for_every_platform(self):
        self.assertIn("faster-whisper", fallback_for("openai", "us"))
        self.assertIn("faster-whisper", fallback_for("deepgram", "us"))
        self.assertIn("System TTS", fallback_for("elevenlabs", "us"))
        self.assertIn("Self-hosted LiveKit", fallback_for("livekit", "us"))
        self.assertIn("Oracle Always Free", fallback_for("livekit", "us"))

    def test_backoff_is_exponential_and_capped(self):
        self.assertEqual(backoff_seconds(1, base=1.0, cap=8.0), 1.0)
        self.assertEqual(backoff_seconds(2, base=1.0, cap=8.0), 2.0)
        self.assertEqual(backoff_seconds(3, base=1.0, cap=8.0), 4.0)
        self.assertEqual(backoff_seconds(4, base=1.0, cap=8.0), 8.0)
        self.assertEqual(backoff_seconds(10, base=1.0, cap=8.0), 8.0)
        # Monotonic for the policy's own parameters.
        delays = [backoff_seconds(n, base=0.5, cap=4.0) for n in range(1, 7)]
        self.assertEqual(delays, sorted(delays))

    def test_backoff_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            backoff_seconds(0)
        with self.assertRaises(ValueError):
            backoff_seconds(1, base=0)


if __name__ == "__main__":
    unittest.main()
