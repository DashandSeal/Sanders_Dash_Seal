"""First-boot observations use temporary logs and never configure the host."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from deploy.standardize import cloud_config


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'deploy/system_preflight_audit.sh'


class SystemAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / 'audit.log'

    def shell(self, text, **environment):
        return subprocess.run(['bash', '-c', 'source "$1"; ' + text, 'fixture', str(AUDIT)],
            env=os.environ | {'SDS_SYSTEM_AUDIT_LOG': str(self.log)} | environment,
            capture_output=True, text=True)

    def test_runtime_expansion_and_private_log(self):
        result = self.shell('system_audit_main')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.log.read_text()
        self.assertNotIn('$(date', text)
        self.assertNotIn('$binary', text)
        self.assertNotIn('${PROTECTED_PATHS', text)
        self.assertIn('git:', text)
        self.assertRegex(text, r'Timestamp: \d{4}-\d{2}-\d{2}')
        self.assertEqual(self.log.stat().st_mode & 0o777, 0o600)
        self.assertEqual(result.stdout, text)

    def test_missing_directory_is_an_observed_gap_without_creating_it(self):
        missing = self.root / 'missing'
        result = self.shell('collect_system_audit "$SDS_FIXTURE_PATH"', SDS_FIXTURE_PATH=str(missing))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OBSERVATION_COMPLETE_WITH_GAPS', result.stdout)
        self.assertIn(str(missing), result.stdout)
        self.assertFalse(missing.exists())

    def test_compose_failure_is_reported_without_false_daemon_readiness(self):
        binaries = self.root / 'bin'
        binaries.mkdir()
        docker = binaries / 'docker'
        docker.write_text('#!/bin/bash\nexit 23\n')
        docker.chmod(0o755)
        result = self.shell('collect_system_audit', PATH=str(binaries) + os.pathsep + os.environ['PATH'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('UNAVAILABLE_OR_TIMED_OUT', result.stdout)
        self.assertIn('OBSERVATION_COMPLETE_WITH_GAPS', result.stdout)

    def test_collection_failure_preserves_nonzero_status_and_partial_log(self):
        result = self.shell('uname() { return 17; }; system_audit_main')
        self.assertEqual(result.returncode, 17)
        self.assertNotIn('OBSERVATION_COMPLETE', result.stdout)
        self.assertTrue(self.log.exists())

    def test_symlink_log_is_rejected_without_overwriting_target(self):
        target = self.root / 'protected.txt'
        target.write_text('unchanged')
        self.log.symlink_to(target)
        result = self.shell('system_audit_main')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_log_replacement_is_bounded_and_private(self):
        self.log.write_text('prior' * 10000)
        self.log.chmod(0o644)
        result = self.shell('system_audit_main')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(self.log.stat().st_size, 10000)
        self.assertEqual(self.log.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(self.root.glob('audit.log.*')))

    def test_cloud_init_audit_precedes_bootstrap_outside_managed_source(self):
        data = cloud_config('a' * 40)
        config = json.loads(data.split('\n', 1)[1])
        self.assertEqual(len(config['runcmd']), 1)
        command = config['runcmd'][0]
        self.assertLess(command[2].index('sds-system-preflight-audit'), command[2].index('exec "$@"'))
        self.assertIn('SDS_BOOTSTRAP_COMMIT=' + 'a' * 40, command)
        paths = [item['path'] for item in config['write_files']]
        self.assertIn('/usr/local/sbin/sds-system-preflight-audit', paths)
        self.assertFalse(any(path.startswith('/opt/') for path in paths))
        audit = next(item for item in config['write_files'] if item['path'].endswith('sds-system-preflight-audit'))
        self.assertEqual(audit['content'], AUDIT.read_text())
        self.assertEqual(audit['permissions'], '0700')


if __name__ == '__main__':
    unittest.main()
