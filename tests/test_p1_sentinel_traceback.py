"""P1 sentinel / traceback tests: the integrity patrols no longer chase a
file that never existed, the truncated traceback module is restored from
git history, and the corrupt grantwriter module is rebuilt (not restored).
"""

import os
import py_compile
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TestSentinelTargetsExist(unittest.TestCase):
    def test_no_protected_target_is_missing(self):
        from core_platform.bozly import bozly_synthetic_guard
        import minotaur_sentinel

        for name, targets in (
            ("minotaur_sentinel.PROTECTED_TARGETS", minotaur_sentinel.PROTECTED_TARGETS),
            ("bozly_synthetic_guard.PROTECTED_MANIFEST", bozly_synthetic_guard.PROTECTED_MANIFEST),
        ):
            self.assertNotIn("bozly_global_cfo.py", targets, name)
            for target in targets:
                self.assertTrue(
                    (REPO_ROOT / target).exists(),
                    f"{name} lists {target}, which does not exist",
                )

    def test_patrol_reports_no_missing_files(self):
        import minotaur_sentinel

        cwd = os.getcwd()
        try:
            os.chdir(REPO_ROOT)
            sentinel = minotaur_sentinel.MinotaurSentinel()
            anomalies = sentinel.execute_patrol_cycle()
        finally:
            os.chdir(cwd)
        missing = [a for a in anomalies if a.endswith(":MISSING")]
        self.assertEqual(missing, [], f"patrol still reports missing files: {anomalies}")
        self.assertEqual(anomalies, [], f"patrol reports anomalies: {anomalies}")


class TestTracebackRestoredAndGrantwriterRebuilt(unittest.TestCase):
    def test_traceback_compiles_and_imports(self):
        path = REPO_ROOT / "core_platform/bozly/bozly_global_traceback.py"
        self.assertTrue(path.exists())
        py_compile.compile(str(path), doraise=True)
        from core_platform.bozly import bozly_global_traceback

        self.assertTrue(callable(bozly_global_traceback.correlate))

    def test_grantwriter_is_rebuilt_not_deleted(self):
        """Decision (P1, 2026-11-13): REBUILT, not deleted.

        The P1 chain deleted app/grantwriter_mother.py because the only
        version in history was truncated at birth (132 lines, no compiling
        version, no callers). The link/grantwriter-repair-20261113 branch
        rebuilt it honestly instead (34 KB, REBUILT_NOT_RESTORED, fake
        offline generator by default, real adapters fail honestly without
        a key, no invented approval gates). Deletion would remove a named
        platform the owner wants working; the rebuild restores the
        capability without claiming to be the lost original. The old
        test asserting deletion is replaced by this one.
        """
        path = REPO_ROOT / "app/grantwriter_mother.py"
        self.assertTrue(path.exists())
        self.assertTrue((REPO_ROOT / "app/grantwriter_mother.py.pbd.json").exists())
        py_compile.compile(str(path), doraise=True)
        text = path.read_text()
        self.assertNotIn("from realtime_ai", text)
        self.assertNotIn("import realtime_ai", text)
        from app import grantwriter_mother

        self.assertTrue(grantwriter_mother.REBUILT_NOT_RESTORED)
        self.assertEqual(grantwriter_mother.PLATFORM.name, "Grantwriter")
        self.assertEqual(grantwriter_mother.PLATFORM.nickname, "Mother")
        self.assertTrue(callable(grantwriter_mother.generate_draft))


if __name__ == "__main__":
    unittest.main()
