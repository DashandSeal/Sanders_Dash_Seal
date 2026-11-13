"""P3 polish pins (2026-11-13): .gitignore, compose reconciliation, EXIF GPS,
docs corrections C1-C18.

Every assertion here is checkable from the checkout alone: no network, no
secrets, no deployment. The two JPG assertions need Pillow; they skip (rather
than fail) if Pillow is absent, and the EXIF strip itself was verified
separately with before/after hashes in the P3 report.
"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from PIL import Image as _PILImage
except Exception:  # pragma: no cover - environment without Pillow
    _PILImage = None


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def git_check_ignored(rel_path):
    """True if git would ignore this path (uses the real .gitignore)."""
    proc = subprocess.run(
        ["git", "check-ignore", "--quiet", rel_path],
        cwd=ROOT, capture_output=True, text=True,
    )
    return proc.returncode == 0


class TestGitignore(unittest.TestCase):
    def test_gitignore_is_patterns_not_shell_commands(self):
        lines = read(".gitignore").splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            self.assertFalse(
                stripped.startswith("git "),
                f".gitignore still contains a shell command: {line!r}",
            )

    def test_gitignore_covers_expected_junk(self):
        text = read(".gitignore")
        for pattern in ("__pycache__/", "*.py[cod]", "node_modules/",
                        ".env", "*.pem", "*.key"):
            self.assertIn(pattern, text, f"missing pattern {pattern}")

    def test_gitignore_does_not_ignore_pbd_pairs(self):
        # Only real patterns count: the explanatory comment mentions
        # *.pbd.json, so check non-comment lines.
        patterns = [ln.strip() for ln in read(".gitignore").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")]
        self.assertNotIn("*.pbd.json", patterns,
                         ".pbd.json must stay tracked, never ignored")

    def test_tracked_files_not_ignored(self):
        for rel in ("wsgi.py", "docker-compose.yml", "compose.yaml",
                    "worker/package-lock.json",
                    "tests/test_p1_secrets.py.pbd.json"):
            self.assertFalse(git_check_ignored(rel),
                             f"tracked file {rel} is now ignored")

    def test_untracked_junk_is_ignored(self):
        for rel in ("foo.pyc", "node_modules/x", ".env",
                    "__pycache__/a.pyc"):
            self.assertTrue(git_check_ignored(rel),
                            f"{rel} should be ignored")


class TestComposeReconciliation(unittest.TestCase):
    def test_three_variants_exist_and_differ(self):
        a = (ROOT / "docker-compose.yml").read_bytes()
        b = (ROOT / "compose.yaml").read_bytes()
        c = (ROOT / "Sanders_Dash_Seal").read_bytes()
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)

    def test_each_file_names_its_own_network_and_services(self):
        dc = read("docker-compose.yml")
        cy = read("compose.yaml")
        ss = read("Sanders_Dash_Seal")
        self.assertIn("sds-secure-bridge", dc)
        self.assertIn("sds_production_network", cy)
        self.assertIn("pipeline-worker", dc)
        self.assertIn("pipeline-worker", cy)
        self.assertIn("nginx-edge", ss)
        self.assertNotIn("pipeline-worker", ss)

    def test_no_live_compose_file_hardcodes_a_webhook_secret(self):
        # Both live files must reference the secret from the environment,
        # never a literal value (checked as: no 'whsec_' literal anywhere).
        for rel in ("docker-compose.yml", "compose.yaml", "Sanders_Dash_Seal"):
            self.assertNotIn("whsec_", read(rel), rel)

    def test_reconciliation_doc_exists_and_names_canonical_paths(self):
        doc = read("docs/COMPOSE_RECONCILIATION.md")
        self.assertIn("compose.yaml", doc)
        self.assertIn("docker-compose.yml", doc)
        self.assertIn("Installer / bootstrap", doc)
        self.assertIn("Legacy services / backup", doc)
        self.assertIn("NOT CONVERGED", doc)


@unittest.skipIf(_PILImage is None, "Pillow not installed")
class TestExifGps(unittest.TestCase):
    def test_jpgs_carry_no_gps_ifd(self):
        for rel in ("web/IMG_20261024_141659486_HDR.jpg",
                    "web/IMG_20261024_141701319_HDR.jpg"):
            with _PILImage.open(ROOT / rel) as im:
                gps = im.getexif().get_ifd(0x8825)
                self.assertFalse(bool(gps), f"{rel} still has a GPS IFD")

    def test_jpgs_keep_non_location_exif(self):
        # Only the GPS IFD was stripped; ordinary tags (dimensions, make,
        # date) must still be present.
        for rel in ("web/IMG_20261024_141659486_HDR.jpg",
                    "web/IMG_20261024_141701319_HDR.jpg"):
            with _PILImage.open(ROOT / rel) as im:
                ex = im.getexif()
                self.assertIn(271, ex, f"{rel} lost its Make tag")
                self.assertIn(306, ex, f"{rel} lost its DateTime tag")
                self.assertIn(34665, ex, f"{rel} lost its Exif sub-IFD")


class TestDocsCorrections(unittest.TestCase):
    def test_gitops_and_forensic_marked_not_active(self):
        self.assertIn("NOT ACTIVE", read("docs/OCI_GITOPS.md"))
        self.assertIn("does not exist", read("docs/OCI_GITOPS.md"))
        self.assertIn("PROPOSED, NOT ACTIVE",
                      read("docs/FORENSIC_SECURITY.md"))

    def test_progressive_policy_marked_workflow_missing(self):
        self.assertIn("does not exist",
                      read("docs/PROGRESSIVE_PRODUCTION_RELEASE_POLICY.md"))

    def test_governance_manifest_rule_scoped_to_privileged_ops(self):
        self.assertIn("privileged application operation",
                      read("docs/GOVERNANCE.md"))

    def test_live_verification_retitled(self):
        self.assertIn("Live verification procedures (not yet executed)",
                      read("docs/LIVE_VERIFICATION.md"))

    def test_catalog_no_longer_claims_complete(self):
        text = read("docs/OCI_FREE_RESOURCE_MAPPING.md")
        self.assertIn("partial catalog", text)
        self.assertNotIn("# Complete Oracle free-resource incorporation", text)

    def test_identical_compose_claims_removed(self):
        self.assertNotIn("compose.yaml is identical",
                         read("docs/INGESTION_WORKER.md"))
        self.assertNotIn("compose.yaml now matches",
                         read("docs/OWNER_STACK_STATUS.md"))
        self.assertNotIn("owner-approved identical compose.yaml",
                         read("docs/FORENSIC_SECURITY.md"))

    def test_ledger_backup_names_real_files(self):
        text = read("docs/LEDGER_BACKUPS.md")
        self.assertIn("deploy/deploy_backup.py", text)
        self.assertIn("deploy/ledger_backup.py", text)
        self.assertNotIn("sudo bash deploy_backup.sh", text)

    def test_source_mapping_marks_missing_files(self):
        text = read("docs/SOURCE_MAPPING.md")
        self.assertIn("File not present in this repository", text)

    def test_archive_banners_present(self):
        self.assertIn("ARCHIVED 2026-11-13",
                      read("docs/AI_RUNTIME_VERIFICATION_2026-10-23.md"))
        self.assertIn("ARCHIVED 2026-11-13",
                      read("docs/AI_TASKS_VERIFICATION_2026-10-23.md"))
        self.assertIn("DATED SNAPSHOT",
                      read("docs/MOBILE_SERVICE_READINESS.md"))

    def test_corrections_log_covers_undefined_c12_c16(self):
        text = read("docs/P3_CORRECTIONS_2026-11-13.md")
        for marker in ("C12", "C16", "C13", "UNRESOLVABLE"):
            self.assertIn(marker, text, f"corrections log missing {marker}")

    def test_jade_still_required_items_marked_done(self):
        text = read("docs/JADE_STOREFRONT_INTEGRATION.md")
        self.assertIn("now done", text)
        self.assertIn("web/sds-founder.png", text)


if __name__ == "__main__":
    unittest.main()
