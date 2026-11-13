"""P1 secrets tests: no literal webhook secret in code or compose files, and
the app fails honestly when STRIPE_WEBHOOK_SECRET is missing.

All secrets used here are FAKE test values (whsec_test_...) — no live keys,
no live Stripe calls. Run from the repo root with the venv that has stripe:

    ~/workspace/sds-p0-work/venv/bin/python -m unittest discover -s tests -v
"""

import hashlib
import hmac
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAKE_SECRET = "whsec_test_p1_fake_secret_0123456789abcdef"

# A line is a literal secret if it contains whsec_ followed by value
# characters, except for: the startswith() validation checks, ${...}
# compose interpolation, and regex character classes in validators.
_LITERAL = re.compile(r"whsec_[A-Za-z0-9_]{4,}")
_EXCUSED = ("startswith", "${STRIPE_WEBHOOK_SECRET", "whsec_[A-Za-z0-9_]")


class TestNoLiteralSecrets(unittest.TestCase):
    FILES = [
        "wsgi.py",
        "deploy/sovereign_reconciliation.py",
        "docker-compose.yml",
        "Sanders_Dash_Seal",
        "compose.yaml",
        "deploy/refresh_provider_secrets.py",
        "deploy/install_application.sh",
    ]

    def test_no_literal_webhook_secret(self):
        for rel in self.FILES:
            text = (REPO_ROOT / rel).read_text()
            for lineno, line in enumerate(text.splitlines(), 1):
                if _LITERAL.search(line) and not any(e in line for e in _EXCUSED):
                    self.fail(f"{rel}:{lineno} contains a literal webhook secret value")

    def test_compose_files_use_interpolation(self):
        for rel in ("docker-compose.yml", "Sanders_Dash_Seal"):
            text = (REPO_ROOT / rel).read_text()
            self.assertIn(
                "${STRIPE_WEBHOOK_SECRET:?STRIPE_WEBHOOK_SECRET must be set",
                text,
                f"{rel} must fail fast when the secret is not provided",
            )
        compose = (REPO_ROOT / "compose.yaml").read_text()
        self.assertIn("STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}", compose)

    def test_sovereign_reconciliation_sets_no_secret(self):
        text = (REPO_ROOT / "deploy/sovereign_reconciliation.py").read_text()
        self.assertNotIn('setdefault("STRIPE_WEBHOOK_SECRET"', text)
        self.assertNotIn("setdefault('STRIPE_WEBHOOK_SECRET'", text)


class TestWebhookSecretRequired(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        self._data_dir = REPO_ROOT / "data"

    def tearDown(self):
        if self._saved is not None:
            os.environ["STRIPE_WEBHOOK_SECRET"] = self._saved
        else:
            os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        # create_native_application() creates data/ before it reads the
        # secret; remove the empty dir again so the test leaves no trace.
        try:
            self._data_dir.rmdir()
        except OSError:
            pass

    def test_missing_secret_raises(self):
        import wsgi
        from core_platform.stream_api import WebhookConfigurationError

        with self.assertRaises(WebhookConfigurationError):
            wsgi.create_native_application()

    def test_fake_secret_builds_callable_app(self):
        os.environ["STRIPE_WEBHOOK_SECRET"] = FAKE_SECRET
        import wsgi

        app = wsgi.create_native_application()
        self.assertTrue(callable(app))
        # Webhook GET must answer 405 post_required, not crash.
        status = {}

        def start_response(code, headers):
            status["code"] = code

        body = b"".join(
            app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/v1/payments/stripe/webhook",
                    "wsgi.input": __import__("io").BytesIO(b""),
                    "CONTENT_LENGTH": "0",
                },
                start_response,
            )
        )
        self.assertTrue(status["code"].startswith("405"), status)
        self.assertIn(b"post_required", body)


class TestRuntimeEnvWriter(unittest.TestCase):
    def test_writes_0600_env_file_from_provider(self):
        from deploy.refresh_provider_secrets import write_runtime_env

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "runtime.env"
            wrote = write_runtime_env(
                {"stripe_webhook_secret": FAKE_SECRET}, env_path
            )
            self.assertTrue(wrote)
            self.assertEqual(
                env_path.read_text(), f"STRIPE_WEBHOOK_SECRET={FAKE_SECRET}\n"
            )
            self.assertEqual(env_path.stat().st_mode & 0o777, 0o600)

    def test_provider_without_secret_leaves_file_untouched(self):
        from deploy.refresh_provider_secrets import write_runtime_env

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "runtime.env"
            self.assertFalse(write_runtime_env({}, env_path))
            self.assertFalse(env_path.exists())

    def test_unwritable_secret_value_raises(self):
        from deploy.refresh_provider_secrets import write_runtime_env

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_runtime_env(
                    {"stripe_webhook_secret": "whsec_bad value with spaces"},
                    Path(tmp) / "runtime.env",
                )

    def test_refresh_writes_env_file_from_vault_provider(self):
        """End-to-end refresh() with a stubbed OCI API: runtime.json is
        updated AND runtime.env is written from the same validated provider
        data, including on the UNCHANGED second run."""
        import base64
        import json

        from deploy.refresh_provider_secrets import refresh

        provider = {
            "stripe_webhook_secret": FAKE_SECRET,
            "stripe_livemode": True,
        }
        bundle = base64.b64encode(json.dumps(provider).encode()).decode()

        def fake_api(args, **kwargs):
            if args[0] == "vault":
                return {
                    "data": [
                        {
                            "secret-name": "sds-runtime-provider-config",
                            "lifecycle-state": "ACTIVE",
                            "id": "ocid1.vaultsecret.test",
                        }
                    ]
                }
            return {
                "data": {
                    "secret-bundle-content": {
                        "content-type": "BASE64",
                        "content": bundle,
                    }
                }
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release.json"
            release.write_text(json.dumps({"compartment_id": "ocid1.compartment.test"}))
            settings = root / "runtime.json"
            settings.write_text("{}")
            env_path = root / "runtime.env"
            result = refresh(
                release, settings, env_path, api=fake_api, restart=False
            )
            self.assertEqual(result, "PROVIDER_SECRET_REFRESHED")
            self.assertEqual(
                env_path.read_text(), f"STRIPE_WEBHOOK_SECRET={FAKE_SECRET}\n"
            )
            self.assertEqual(
                json.loads(settings.read_text())["stripe_webhook_secret"],
                FAKE_SECRET,
            )
            # Second run: unchanged, but the env file must still be there.
            result = refresh(
                release, settings, env_path, api=fake_api, restart=False
            )
            self.assertEqual(result, "PROVIDER_SECRET_UNCHANGED")
            self.assertEqual(
                env_path.read_text(), f"STRIPE_WEBHOOK_SECRET={FAKE_SECRET}\n"
            )

    def test_refresh_without_provider_leaves_env_untouched(self):
        import json

        from deploy.refresh_provider_secrets import refresh

        def empty_api(args, **kwargs):
            return {"data": []}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release.json"
            release.write_text(json.dumps({"compartment_id": "ocid1.compartment.test"}))
            settings = root / "runtime.json"
            settings.write_text("{}")
            env_path = root / "runtime.env"
            result = refresh(
                release, settings, env_path, api=empty_api, restart=False
            )
            self.assertEqual(result, "PROVIDER_SECRET_NOT_CONFIGURED")
            self.assertFalse(env_path.exists())


if __name__ == "__main__":
    unittest.main()
