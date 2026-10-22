"""Initializer integration with a disposable bootstrap; never changes a host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


class InstanceInitializerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copyfile(ROOT / 'instance_init.sh', self.root / 'instance_init.sh')
        (self.root / 'deploy').mkdir()
        self.log = self.root / 'bootstrap.json'
        # Mock only the downstream boundary to observe handoff, not real authority.
        (self.root / 'deploy/sds-bootstrap.sh').write_text('''#!/bin/bash
python3 - <<'PYCODE'
import json,os
from pathlib import Path
Path(os.environ['FIXTURE_LOG']).write_text(json.dumps({key:os.getenv(key) for key in (
 'SDS_BOOTSTRAP_COMMIT','SDS_BOOTSTRAP_MODE','SDS_TUNE_KERNEL','SDS_PUBLIC_IPV4')}))
PYCODE
exit "${FIXTURE_EXIT:-0}"
''')

    def run_initializer(self, *args, **environment):
        env = os.environ | {'FIXTURE_LOG': str(self.log)} | environment
        return subprocess.run(['bash', str(self.root / 'instance_init.sh'), *args],
                              capture_output=True, text=True, env=env)

    def test_default_stage_hands_off_exact_commit_without_inherited_public_ip(self):
        result = self.run_initializer('--commit', SHA, SDS_PUBLIC_IPV4='129.146.111.166')
        self.assertEqual(result.returncode, 0, result.stderr)
        handoff = json.loads(self.log.read_text())
        self.assertEqual(handoff['SDS_BOOTSTRAP_MODE'], 'stage')
        self.assertEqual(handoff['SDS_BOOTSTRAP_COMMIT'], SHA)
        self.assertIsNone(handoff['SDS_PUBLIC_IPV4'])

    def test_activation_passes_only_explicit_node_address_and_requested_tuning(self):
        result = self.run_initializer('--activate', '--commit', SHA,
            '--public-ipv4', '129.146.111.166', '--tune-kernel', SDS_PUBLIC_IPV4='8.8.8.8')
        self.assertEqual(result.returncode, 0, result.stderr)
        handoff = json.loads(self.log.read_text())
        self.assertEqual(handoff['SDS_BOOTSTRAP_MODE'], 'activate')
        self.assertEqual(handoff['SDS_PUBLIC_IPV4'], '129.146.111.166')
        self.assertEqual(handoff['SDS_TUNE_KERNEL'], '1')

    def test_placeholder_commit_never_reaches_bootstrap(self):
        result = self.run_initializer('--commit', 'PR-3-CLEAN-CANDIDATE')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_activation_cannot_use_inherited_ip(self):
        result = self.run_initializer('--activate', '--commit', SHA, SDS_PUBLIC_IPV4='129.146.111.166')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_private_address_is_rejected_before_bootstrap(self):
        result = self.run_initializer('--activate', '--commit', SHA, '--public-ipv4', '10.0.0.175')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_invalid_modes_duplicate_or_missing_arguments_stop_before_bootstrap(self):
        for arguments in (('--activate', '--stage', '--commit', SHA),
                          ('--commit',), ('--commit', SHA, '--commit', SHA),
                          ('--unknown',), ('--stage', '--commit', SHA, '--public-ipv4', '8.8.8.8')):
            with self.subTest(arguments=arguments):
                result = self.run_initializer(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists())

    def test_downstream_failure_preserves_exit_status_without_activation_success(self):
        result = self.run_initializer('--stage', '--commit', SHA, FIXTURE_EXIT='9')
        self.assertEqual(result.returncode, 9)
        self.assertIn('Initializer failed', result.stderr)
        self.assertNotIn('Passed', result.stdout)
        self.assertNotIn('Activating', result.stdout)

    def test_shell_syntax_and_help_make_no_deployment_call(self):
        result = subprocess.run(['bash', '-n', str(ROOT / 'instance_init.sh')], capture_output=True)
        self.assertEqual(result.returncode, 0)
        result = self.run_initializer('--help')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()
