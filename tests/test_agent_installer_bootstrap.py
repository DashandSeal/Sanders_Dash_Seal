import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import mock_open, patch

from deploy.bootstrap_agent_installer import HELPER, SUDOERS, bootstrap, render_helper


class AgentInstallerTests(unittest.TestCase):
    def execute(self, args, *, uid=0, download_fails=False):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            def run(command, **kwargs):
                calls.append((command, kwargs))
                if command[0] == '/usr/bin/oci':
                    if download_fails:
                        raise subprocess.CalledProcessError(1, command)
                    Path(command[command.index('--file') + 1]).write_text('#!/bin/bash\nexit 0\n')
            with patch('sys.argv', [HELPER] + args), patch('os.geteuid', return_value=uid), \
                    patch('os.umask'), patch('fcntl.flock'), patch('pathlib.Path.mkdir'), \
                    patch('pathlib.Path.stat', return_value=type('Stat', (), {'st_uid':0, 'st_mode':0o40700, 'st_size':24})()), \
                    patch('pathlib.Path.is_symlink', return_value=False), \
                    patch('pathlib.Path.is_file', return_value=True), \
                    patch('builtins.open', mock_open()), \
                    patch('tempfile.TemporaryDirectory') as temporary, \
                    patch('subprocess.run', side_effect=run):
                temporary.return_value.__enter__.return_value = directory
                exec(compile(render_helper('namespace', 'sds-release-123456abcdef'), HELPER, 'exec'), {})
        return calls

    def test_fixed_bucket_commit_and_environment(self):
        calls = self.execute(['a' * 40])
        self.assertEqual(len(calls), 2)
        command, kwargs = calls[0]
        self.assertIn('installers/' + 'a' * 40 + '.sh', command)
        self.assertEqual(command[command.index('--bucket-name') + 1], 'sds-release-123456abcdef')
        self.assertEqual(kwargs['env']['HOME'], '/root')
        self.assertEqual(set(kwargs['env']), {'HOME', 'PATH', 'LANG'})
        self.assertEqual(calls[1][0][0], '/bin/bash')
        self.assertEqual(SUDOERS, 'ocarun ALL=(root) NOPASSWD: NOSETENV: ' + HELPER + '\n')
        self.assertNotIn('/bin/bash', SUDOERS)

    def test_reject_untrusted_arguments_and_unprivileged_execution(self):
        for args in ([], ['../bad'], ['a' * 40, '/tmp/script'], ['A' * 40], ['--help']):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.execute(args)
        with self.assertRaises(SystemExit):
            self.execute(['a' * 40], uid=988)

    def test_failed_download_never_executes(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.execute(['a' * 40], download_fails=True)

    def test_bootstrap_requires_administrator_before_any_host_changes(self):
        with patch('os.geteuid', return_value=988), patch('subprocess.run') as run:
            with self.assertRaises(PermissionError):
                bootstrap('namespace', 'sds-release-123456abcdef')
            run.assert_not_called()

    def test_bindings_are_data_and_bucket_is_expected(self):
        for namespace, bucket in [('bad/namespace', 'sds-release-123456abcdef'),
                                  ('namespace', 'other-bucket'), ("';evil", 'sds-release-123456abcdef')]:
            with self.assertRaises(ValueError):
                render_helper(namespace, bucket)
        compile(render_helper('BUCKET', 'sds-release-123456abcdef'), HELPER, 'exec')


if __name__ == '__main__':
    unittest.main()
