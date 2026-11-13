"""CI smoke tests for the SOTA CI baseline (2026-11-13).

Stdlib-only (unittest). Guards:
  1. This file's own .pbd.json pair is a valid Shape A manifest whose
     payload_hash is the real sha256 of this file.
  2. The upgraded workflows pin the current action majors (checkout v7,
     setup-python v7) and the new ci-sota.yml workflow exists.
  3. The Architectural Integrity Gateway workflow was NOT edited by this
     branch: it still contains its push step. Its fix is a proposed diff
     only (see docs/ci-platform-modernization-20261113.md); update this
     test when the owner approves and applies that fix.
"""

import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestCiSmoke(unittest.TestCase):
    def test_own_pbd_pair_matches_sha256(self):
        pair = REPO_ROOT / "sharpshooter/tests/test_ci_smoke.py.pbd.json"
        self.assertTrue(pair.is_file(), "missing .pbd.json pair for test_ci_smoke.py")
        data = json.loads(pair.read_text())
        body = data["body"]
        self.assertEqual(body["schema"], 1)
        self.assertEqual(body["platform"], "Sanders Dash & Seal")
        self.assertEqual(body["artifact"], "sharpshooter/tests/test_ci_smoke.py")
        self.assertEqual(data.get("status"), "UNSIGNED_SOURCE_MANIFEST")
        digest = hashlib.sha256(
            (REPO_ROOT / "sharpshooter/tests/test_ci_smoke.py").read_bytes()
        ).hexdigest()
        self.assertEqual(body["payload_hash"], digest)

    def test_upgraded_workflows_pin_current_majors(self):
        for name in (
            "closeup_vmax_pipeline.yml",
            "verify-bozly-integrity.yml",
            "ci-sota.yml",
        ):
            text = (REPO_ROOT / ".github/workflows" / name).read_text()
            self.assertIn("actions/checkout@v7", text, name)
            self.assertIn("actions/setup-python@v7", text, name)
            self.assertNotIn("actions/checkout@v4", text, name)
            self.assertNotIn("actions/setup-python@v5", text, name)
        closeup = (
            REPO_ROOT / ".github/workflows/closeup_vmax_pipeline.yml"
        ).read_text()
        # Python 3.10 reached end of life 2026-10-01; it must not come back.
        self.assertNotIn("'3.10'", closeup)

    def test_gateway_workflow_still_has_push_step_marker(self):
        text = (
            REPO_ROOT / ".github/workflows/parallel-build-verification.yml"
        ).read_text()
        self.assertIn("Securely Push Verified Manifest Assets", text)


if __name__ == "__main__":
    unittest.main()
