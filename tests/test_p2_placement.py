"""P2 placement tests: files moved by the placement map are importable at
their new locations, the integrity patrols point at the new paths, and the
old root locations are gone.

Run from the repo root with the venv that has stripe:
    ~/workspace/sds-p0-work/venv/bin/python -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BOZLY_PACKAGE = [
    "bozly_auth_gate",
    "bozly_cfo",
    "bozly_claim_integrity",
    "bozly_diversion_guard",
    "bozly_financial_ethics",
    "bozly_forensic_accounting",
    "bozly_forensic_dashboard",
    "bozly_global_presence",
    "bozly_global_traceback",
    "bozly_global_transactions",
    "bozly_human_api",
    "bozly_identity_and_conduct",
    "bozly_legal_intelligence",
    "bozly_market_ingestor",
    "bozly_multimodal_integrity",
    "bozly_native_backup",
    "bozly_native_broker",
    "bozly_native_cfo",
    "bozly_native_investment_intelligence",
    "bozly_onboarding",
    "bozly_operations",
    "bozly_pq_identity",
    "bozly_purchasing",
    "bozly_quantum_armor",
    "bozly_security_response",
    "bozly_synthetic_guard",
    "bozly_uplink",
    "bozly_wifi",
    "bozly_wizardry_engine",
]


class TestBozlyPackageImports(unittest.TestCase):
    def test_all_bozly_modules_import_at_new_paths(self):
        import importlib

        for name in BOZLY_PACKAGE:
            with self.subTest(module=name):
                module = importlib.import_module(
                    f"core_platform.bozly.{name}")
                self.assertIsNotNone(module)
        for name in ("bozly_shield_wsgi", "bozly_stripe_webhook_wsgi"):
            with self.subTest(module=name):
                module = importlib.import_module(f"web.{name}")
                self.assertIsNotNone(module)

    def test_shield_wsgi_exposes_shielded_applications(self):
        from web import bozly_shield_wsgi

        self.assertTrue(callable(bozly_shield_wsgi.human_application_shielded))
        self.assertTrue(callable(bozly_shield_wsgi.webhook_application_shielded))

    def test_stripe_webhook_wsgi_exposes_application(self):
        from web import bozly_stripe_webhook_wsgi

        self.assertTrue(callable(bozly_stripe_webhook_wsgi.application))


class TestPatrolListsPointAtMovedFiles(unittest.TestCase):
    def test_no_patrol_target_is_a_bare_root_bozly_name(self):
        from core_platform.bozly import bozly_synthetic_guard
        import minotaur_sentinel

        for name, targets in (
            ("minotaur_sentinel.PROTECTED_TARGETS",
             minotaur_sentinel.PROTECTED_TARGETS),
            ("bozly_synthetic_guard.PROTECTED_MANIFEST",
             bozly_synthetic_guard.PROTECTED_MANIFEST),
        ):
            for target in targets:
                self.assertFalse(
                    target.startswith("bozly_") and "/" not in target,
                    f"{name} still lists root-level {target}",
                )
                self.assertTrue(
                    (REPO_ROOT / target).exists(),
                    f"{name} lists {target}, which does not exist",
                )


class TestSecurityResponseTargets(unittest.TestCase):
    def test_targets_all_exist_under_new_layout(self):
        from core_platform.bozly import bozly_security_response as sr

        sr.ROOT = REPO_ROOT
        targets = sr._targets()
        self.assertIn("core_platform/bozly/bozly_cfo.py", targets)
        self.assertIn("web/bozly_shield_wsgi.py", targets)
        self.assertIn("worker/src/server.js", targets)
        for target in targets:
            self.assertTrue(
                (REPO_ROOT / target).exists(),
                f"_targets() lists {target}, which does not exist",
            )

    def test_file_observation_works_for_package_paths(self):
        from core_platform.bozly import bozly_security_response as sr

        sr.ROOT = REPO_ROOT
        for target in ("core_platform/bozly/bozly_cfo.py",
                       "web/bozly_shield_wsgi.py",
                       "worker/src/server.js"):
            observed = sr._file_observation(target)
            self.assertEqual(observed["path"], target)
            self.assertNotEqual(observed["sha256"], "FILE_MISSING")

    def test_file_observation_rejects_escape(self):
        from core_platform.bozly import bozly_security_response as sr

        sr.ROOT = REPO_ROOT
        with self.assertRaises(ValueError):
            sr._file_observation("../outside.py")


class TestFreeResourceCatalogRename(unittest.TestCase):
    def test_typo_name_is_gone_and_canonical_catalog_exists(self):
        self.assertFalse((REPO_ROOT / "oci_free_resouseces.json").exists())
        self.assertTrue((REPO_ROOT / "oci_free_resources.json").exists())
        self.assertFalse(
            (REPO_ROOT / "core_platform/oci_free_resources.json").exists())
        self.assertTrue(
            (REPO_ROOT / "core_platform/oci_core_laws.py").exists())

    def test_free_resources_catalog_loads_real_catalog(self):
        from core_platform.free_resources import catalog

        data = catalog()
        self.assertEqual(data["platform"], "Sanders Dash & Seal")
        self.assertEqual(data["schema"], 1)
        self.assertEqual(len(data["resources"]), 6)

    def test_core_laws_module_accepts_catalog_with_mandates(self):
        # P2: the catalog is the 6-resource free-first rebuild, which
        # carries governing_core_law 10 ("Always Free") and
        # governing_core_Law 11 ("actually use"), so import_core_laws
        # now loads instead of raising (the P2-chain test asserting the
        # raise was written against the 2-resource catalog without them).
        from core_platform.oci_core_laws import import_core_laws

        laws = import_core_laws(REPO_ROOT)
        self.assertTrue(laws.validate_resource_allocation(
            "oracle-a1-compute", {"ocpu": 2}))
        with self.assertRaises(Exception):
            laws.validate_resource_allocation("oracle-a1-compute", {"ocpu": 3})


class TestPlacementLayout(unittest.TestCase):
    def test_no_bozly_modules_remain_at_root(self):
        self.assertEqual(list(REPO_ROOT.glob("bozly_*.py")), [])

    def test_moved_files_exist_at_new_locations(self):
        expected = [
            "core_platform/bozly/bozly_cfo.py",
            "web/bozly_shield_wsgi.py",
            "web/bozly_stripe_webhook_wsgi.py",
            "worker/src/server.js",
            "deploy/deployment.py",
            "app/customer_app.py",
            "app/case_api_wsgi.py",
            "web/dashboard.html",
            "core_platform/synthetic_localization.py",
            "core_platform/synthetic_operations.py",
            "deploy/sovereign_reconciliation.py",
            "deploy/speedracer_remediator.py",
            "deploy/deploy_backup.py",
            "deploy/instance_init.sh",
            "deploy/run_preflight_checks.sh",
        ]
        for rel in expected:
            with self.subTest(path=rel):
                self.assertTrue((REPO_ROOT / rel).exists(), rel)

    def test_root_deploy_sh_still_present(self):
        # The root deploy.sh move is BLOCKED (deploy/deploy.sh collision);
        # it must still be at the root.
        self.assertTrue((REPO_ROOT / "deploy.sh").exists())


if __name__ == "__main__":
    unittest.main()
