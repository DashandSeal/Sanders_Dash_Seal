"""Regression tests — Daedalus baseline drift and deliberate re-pin.

The 2026-11-26/27 incident these tests pin down: Daedalus's
Minotaur patrol baselines were pinned at 2026-11-26T00:23:42Z
against the then-deployed tree. A routine deploy later that day
changed one patrolled file (``core_platform/ai_platform_links.json``).
From that moment ``DaedalusProtection.require_intact()`` raised
``DaedalusTamperError`` on every call, and the five
protection-gated capabilities (live_native_reasoning,
live_source_provenance, glass_box_audit, request_correlation,
real_time_learning) read "unavailable" — silently, for a day.

The protection layer behaved exactly as designed (fail closed).
What was missing was (a) a loud drift signal at deploy time and
(b) a deliberate operator re-pin path. The deploy-time signal is
``deploy/daedalus_drift_check.py`` (run by the master-deploy
workflow after every deploy); the re-pin path is the
workflow_dispatch "Daedalus baseline re-pin (operator, deliberate)"
workflow. These tests prove the mechanics both rely on:

* drift of a patrolled target surfaces as a NAMED tamper state —
  the patrol report's ``tamper_detected`` status naming the file in
  ``altered``, and ``require_intact()`` raising
  ``DaedalusTamperError`` naming the file — never as five
  unexplained unavailable capabilities at this layer;
* a protection-gated capability (the native core's ``generate()``)
  refuses while drifted and works again after a deliberate
  ``pin_baselines()`` re-pin;
* the drift-check script patrols exactly PATROL_TARGETS and its
  verdicts agree with the protection layer's state.

Nothing here touches the seed, the 32-leaf epoch, the 300 s patrol
cadence, or the patrol target set.
"""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from core_platform.daedalus_knowledge_store import DaedalusKnowledgeStore
from core_platform.daedalus_native_core import DaedalusNativeCore
from core_platform.daedalus_protection import (
    PATROL_TARGETS,
    DaedalusProtection,
    DaedalusTamperError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# The file whose deploy-time change caused the 2026-11-26 drift.
DRIFTED_TARGET = "core_platform/ai_platform_links.json"


def load_drift_check():
    """Load deploy/daedalus_drift_check.py by path (it is a deploy
    tool, not a package module)."""
    spec = importlib.util.spec_from_file_location(
        "daedalus_drift_check",
        REPO_ROOT / "deploy" / "daedalus_drift_check.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DaedalusBaselineDriftTest(unittest.TestCase):
    """Sandbox shape follows the engine's own integrity-patrol
    probe: a scratch repo holding exactly the patrol set, with the
    protection state in a scratch directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.sandbox = tmp / "repo"
        for rel in set(PATROL_TARGETS):
            dest = self.sandbox / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, dest)
        self.state_dir = tmp / "state"
        self.protection = DaedalusProtection(
            repo_root=self.sandbox, state_dir=self.state_dir
        )
        clean = self.protection.patrol()
        self.assertEqual(clean["status"], "clean")

    def tearDown(self):
        self._tmp.cleanup()

    def drift(self):
        target = self.sandbox / DRIFTED_TARGET
        data = bytearray(target.read_bytes())
        data[10] ^= 0x01
        target.write_bytes(bytes(data))

    def test_drift_surfaces_named_tamper_state(self):
        self.drift()
        report = self.protection.patrol()
        self.assertEqual(report["status"], "tamper_detected")
        self.assertIn(DRIFTED_TARGET, report["altered"])
        with self.assertRaises(DaedalusTamperError) as caught:
            self.protection.require_intact()
        self.assertIn(DRIFTED_TARGET, str(caught.exception))

    def test_repin_restores_gated_capabilities(self):
        core = DaedalusNativeCore(
            knowledge_store=DaedalusKnowledgeStore(
                Path(self._tmp.name) / "kb.db"
            ),
            protection=self.protection,
        )
        admitted = core.generate(
            system="drift-test", user_message="What is Bozly?"
        )
        self.assertTrue(admitted.text.strip())

        self.drift()
        with self.assertRaises(DaedalusTamperError):
            core.generate(
                system="drift-test", user_message="What is Bozly?"
            )

        # The deliberate operator act: re-pin against the current
        # tree. The gate reopens and the capability works again.
        self.protection.pin_baselines()
        intact = self.protection.require_intact()
        self.assertEqual(intact["status"], "intact")
        restored = core.generate(
            system="drift-test", user_message="What is Bozly?"
        )
        self.assertTrue(restored.text.strip())
        self.assertEqual(self.protection.patrol()["status"], "clean")

    def test_drift_check_script_matches_patrol_set_and_verdicts(self):
        module = load_drift_check()
        self.assertEqual(tuple(module.TARGETS), tuple(PATROL_TARGETS))
        state_path = self.state_dir / "daedalus_protection_state.json"

        code, _lines = module.check(self.sandbox, state_path)
        self.assertEqual(code, 0)

        self.drift()
        code, lines = module.check(self.sandbox, state_path)
        self.assertEqual(code, 1)
        self.assertTrue(
            any(
                DRIFTED_TARGET in line and "DIFF" in line
                for line in lines
            )
        )
        self.assertTrue(
            any("DAEDALUS BASELINE DRIFT DETECTED" in line for line in lines)
        )


if __name__ == "__main__":
    unittest.main()
