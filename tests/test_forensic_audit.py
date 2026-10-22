"""Tripwire regressions in isolated Git repositories; no SMTP delivery."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.forensic_audit import audit


class ForensicAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / 'repo'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Local Test Fixture')
        (self.root / 'security').mkdir()
        (self.root / 'security/forensic-policy.json').write_text(json.dumps({
            'schema': 1, 'allowed_duplicate_groups': [['compose.yaml', 'docker-compose.yml']]}))
        (self.root / '.github').mkdir()
        (self.root / '.github/tracked.txt').write_text('include hidden tracked directories')
        self.source('example.py', 'print("fixture")\n')
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def source(self, name, content):
        path = self.root / name
        path.write_text(content)
        Path(str(path) + '.pbd.json').write_text(json.dumps({'body': {
            'artifact': name, 'payload_hash': hashlib.sha256(path.read_bytes()).hexdigest()},
            'signatures': {}}))

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Disposable fixture baseline')

    def reasons(self):
        return {issue['reason'] for issue in audit(self.root)['issues']}

    def test_clean_repository_includes_dot_directories(self):
        result = audit(self.root)
        self.assertTrue(result['integrity_passed'])
        self.assertIn('.github/tracked.txt', [item['path'] for item in result['inventory']])
        self.assertFalse(result['production_signatures_verified'])

    def test_source_modification_and_committed_pair_mismatch_detected(self):
        (self.root / 'example.py').write_text('print("changed")\n')
        self.assertIn('missing_or_mismatched_pair', self.reasons())
        self.assertIn('uncommitted_or_untracked_drift', self.reasons())
        self.commit()
        self.assertIn('missing_or_mismatched_pair', self.reasons())

    def test_permissions_detected_even_when_git_ignores_filemode(self):
        self.git('config', 'core.filemode', 'false')
        (self.root / 'example.py').chmod(0o600)
        self.assertIn('permission_mismatch', self.reasons())

    def test_untracked_and_duplicate_additions_detected(self):
        (self.root / 'unexpected.txt').write_text('new file')
        self.assertIn('uncommitted_or_untracked_drift', self.reasons())
        self.source('copy.py', 'print("fixture")\n')
        self.commit()
        self.assertIn('unexpected_exact_duplicate', self.reasons())

    def test_explicit_owner_duplicate_group_is_allowed(self):
        for name in ('compose.yaml', 'docker-compose.yml'):
            self.source(name, 'services: {}\n')
        self.commit()
        self.assertTrue(audit(self.root)['integrity_passed'])

    def test_report_generation_does_not_create_its_own_drift(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/forensic_audit.py'
        output = self.directory / 'reports'
        result = subprocess.run([sys.executable, str(script), '--root', str(self.root),
                                 '--output', str(output)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / 'forensic_manifest.sha256').exists())
        self.assertTrue(audit(self.root)['integrity_passed'])

    def test_output_inside_checkout_is_rejected(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/forensic_audit.py'
        result = subprocess.run([sys.executable, str(script), '--root', str(self.root),
            '--output', str(self.root / 'report')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'report').exists())

    def test_symlink_is_not_a_trusted_source_file(self):
        (self.root / 'link.py').symlink_to('example.py')
        self.commit()
        self.assertIn('unsupported_git_entry', self.reasons())
