"""P1 livemode tests: Stripe defaults to TEST mode; live mode requires
BOTH livemode and explicit live verification.

Fake providers only: fake webhook secret, local HMAC signatures, temp
SQLite files. No live keys, no live Stripe calls, no network.

Run from the repo root with the venv that has stripe:

    ~/workspace/.venv-simultaneous/bin/python -m unittest discover -s tests -v
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from test_p1_wsgi import FAKE_SECRET, FakeLedger, call, make_event_table, signed_event


def make_app(ledger, **kwargs):
    from core_platform.stream_api import import_make_app

    return import_make_app(
        ledger_engine=ledger,
        webhook_secret=FAKE_SECRET,
        enabled=True,
        **kwargs,
    )


def post_event(app, event_id, event_type, livemode=True):
    payload, header = signed_event(event_id, event_type, livemode=livemode)
    return call(
        app,
        "POST",
        "/v1/payments/stripe/webhook",
        payload,
        {"HTTP_STRIPE_SIGNATURE": header},
    )


class TestLivemodeDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "ledger.db")
        make_event_table(self.db_path)
        self.ledger = FakeLedger(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_is_test_mode(self):
        """No expected_livemode passed: test events settle, live events 400."""
        app = make_app(self.ledger)
        code, body = post_event(app, "evt_test_1", "checkout.session.completed",
                                livemode=False)
        self.assertTrue(code.startswith("200"), (code, body))
        self.assertIn(b"LEDGER_SETTLED", body)
        code, body = post_event(app, "evt_live_1", "checkout.session.completed",
                                livemode=True)
        self.assertTrue(code.startswith("400"), (code, body))
        self.assertIn(b"environment_livemode_mismatch", body)

    def test_live_without_verification_raises_at_startup(self):
        from core_platform.stream_api import WebhookConfigurationError

        with self.assertRaises(WebhookConfigurationError):
            make_app(self.ledger, expected_livemode=True)
        with self.assertRaises(WebhookConfigurationError):
            make_app(self.ledger, expected_livemode=True, live_verified=False)

    def test_live_with_verification_settles_live_events(self):
        app = make_app(self.ledger, expected_livemode=True, live_verified=True)
        code, body = post_event(app, "evt_live_2", "checkout.session.completed",
                                livemode=True)
        self.assertTrue(code.startswith("200"), (code, body))
        self.assertIn(b"LEDGER_SETTLED", body)
        code, body = post_event(app, "evt_test_2", "checkout.session.completed",
                                livemode=False)
        self.assertTrue(code.startswith("400"), (code, body))

    def test_provider_validate_defaults_to_test_mode(self):
        """A Vault bundle without stripe_livemode must validate test keys,
        not live keys (free-first / test-first default)."""
        from deploy.refresh_provider_secrets import validate

        data = validate({"stripe_api_key": "sk_test_0123456789abcdef"})
        self.assertEqual(data.get("stripe_livemode", False), False)
        with self.assertRaises(ValueError):
            validate({"stripe_api_key": "sk_live_0123456789abcdef"})

    def test_init_runtime_defaults_to_test_mode(self):
        from deploy.init_runtime import initialize

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "runtime"
            initialize(folder, chown=lambda *a: None)
            settings = __import__("json").loads((folder / "runtime.json").read_text())
            self.assertIs(settings.get("stripe_livemode"), False)


class TestWsgiLivemodeEnvGate(unittest.TestCase):
    """wsgi.create_native_application() reads STRIPE_LIVEMODE /
    STRIPE_LIVE_VERIFIED from the environment. The wsgi module builds its
    app at import time, so these run in a subprocess to isolate the env."""

    _SCRIPT = (
        "import os, sys; sys.path.insert(0, os.getcwd())\n"
        "from core_platform.stream_api import WebhookConfigurationError\n"
        "try:\n"
        "    import wsgi\n"
        "    print('BUILT')\n"
        "except WebhookConfigurationError:\n"
        "    print('RAISED')\n"
    )

    def setUp(self):
        self._data_dir = REPO_ROOT / "data"
        self._data_existed = self._data_dir.exists()

    def tearDown(self):
        # create_native_application() creates data/; remove it only if this
        # test created it, so a pre-existing ledger is never touched.
        if not self._data_existed and self._data_dir.exists():
            shutil.rmtree(self._data_dir, ignore_errors=True)

    def _run(self, extra_env):
        env = dict(os.environ)
        env["STRIPE_WEBHOOK_SECRET"] = FAKE_SECRET
        env.pop("STRIPE_LIVEMODE", None)
        env.pop("STRIPE_LIVE_VERIFIED", None)
        env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, "-c", self._SCRIPT],
            cwd=str(REPO_ROOT), env=env,
            capture_output=True, text=True, timeout=60,
        )
        return proc.stdout.strip(), proc.stderr.strip()

    def test_no_env_builds_in_test_mode(self):
        out, err = self._run({})
        self.assertEqual(out, "BUILT", err)

    def test_livemode_without_verification_refuses_to_build(self):
        out, err = self._run({"STRIPE_LIVEMODE": "1"})
        self.assertEqual(out, "RAISED", err)

    def test_livemode_with_verification_builds(self):
        out, err = self._run({"STRIPE_LIVEMODE": "1", "STRIPE_LIVE_VERIFIED": "1"})
        self.assertEqual(out, "BUILT", err)


if __name__ == "__main__":
    unittest.main()
