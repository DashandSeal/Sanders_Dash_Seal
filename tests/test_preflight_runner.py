"""Disposable preflight orchestration tests; fake Docker never contacts a daemon."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PreflightRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        shutil.copyfile(ROOT / 'run_preflight_checks.sh', self.repo / 'run_preflight_checks.sh')
        (self.repo / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/verify_release_source.py', self.repo / 'scripts/verify_release_source.py')
        (self.repo / 'deploy').mkdir()
        shutil.copyfile(ROOT / 'deploy/compose.preflight.yml', self.repo / 'deploy/compose.preflight.yml')
        for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=Fixture', '-c',
                     'user.email=fixture@localhost', 'commit', '-qm', 'Fixture source']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True)
        self.sha = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
        self.log = self.root / 'docker.log'
        binaries = self.root / 'bin'
        binaries.mkdir()
        docker = binaries / 'docker'
        docker.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$FIXTURE_DOCKER_LOG"
if [[ "$*" == *"run --rm --no-deps ${FIXTURE_FAIL:-never}"* ]]; then exit 23; fi
exit 0
''')
        docker.chmod(0o755)
        self.environment = os.environ | {'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
            'FIXTURE_DOCKER_LOG': str(self.log), 'SDS_SOURCE_DIR': str(self.repo), 'TMPDIR': str(self.root)}

    def run_preflight(self, *args, fail=None):
        env = self.environment.copy()
        if fail:
            env['FIXTURE_FAIL'] = fail
        return subprocess.run(['bash', str(self.repo / 'run_preflight_checks.sh'), *args],
                              capture_output=True, text=True, env=env)

    def test_runs_both_engines_in_disposable_project_and_cleans_it(self):
        result = self.run_preflight('--commit', self.sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn('run --rm --no-deps node-tests', log)
        self.assertIn('run --rm --no-deps python-tests', log)
        self.assertIn('down --rmi local', log)
        self.assertIn('-p sds-preflight-', log)
        self.assertNotIn('up -d', log)
        self.assertNotIn('wsgi-backend', log)
        self.assertFalse(list(self.root.glob('sds-preflight.*')))
        self.assertIn('LOCAL_REGRESSION_PASSED', result.stdout)

    def test_node_failure_stops_python_and_preserves_status_after_cleanup(self):
        result = self.run_preflight('--commit', self.sha, fail='node-tests')
        self.assertEqual(result.returncode, 23)
        log = self.log.read_text()
        self.assertNotIn('run --rm --no-deps python-tests', log)
        self.assertIn('down --rmi local', log)
        self.assertNotIn('LOCAL_REGRESSION_PASSED', result.stdout)

    def test_python_failure_does_not_report_success(self):
        result = self.run_preflight('--commit', self.sha, fail='python-tests')
        self.assertEqual(result.returncode, 23)
        self.assertNotIn('LOCAL_REGRESSION_PASSED', result.stdout)

    def test_wrong_commit_and_dirty_checkout_never_call_docker(self):
        result = self.run_preflight('--commit', 'f' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        (self.repo / 'unexpected.txt').write_text('drift')
        result = self.run_preflight('--commit', self.sha)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_invalid_commit_and_help_do_not_build(self):
        result = self.run_preflight('--commit', 'PR-3')
        self.assertNotEqual(result.returncode, 0)
        result = self.run_preflight('--help')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_isolation_configuration_has_no_production_mounts_or_ports(self):
        text = (ROOT / 'deploy/compose.preflight.yml').read_text()
        self.assertNotIn('volumes:', text)
        self.assertNotIn('ports:', text)
        self.assertNotIn('env_file:', text)
        self.assertEqual(text.count('network_mode: none'), 2)
        self.assertEqual(text.count('read_only: true'), 2)

    def test_activation_cannot_run_after_a_failed_regression(self):
        (self.root / 'deploy.sh').write_text('check_host() { :; }; install_engine() { :; }; main() { echo ACTIVATED; }\n')
        result = subprocess.run(['bash', '-c', '''
source "$1/deploy/sds-bootstrap.sh"
require_bootstrap_root() { :; }; prepare_checkout() { :; }; verify_bootstrap_source() { :; }
verify_instance_context() { echo metadata; }; validate_candidate() { return 29; }
SDS_SOURCE_DIR="$2"; SDS_BOOTSTRAP_MODE=activate; SDS_PUBLIC_IPV4=129.146.111.166
bootstrap_main
''', 'fixture', str(ROOT), str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 29)
        self.assertNotIn('ACTIVATED', result.stdout)


if __name__ == '__main__':
    unittest.main()
