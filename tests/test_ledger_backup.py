"""Backups against live WAL databases and simulated OCI/Docker boundaries."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from deploy.ledger_backup import backup, preflight, readonly, snapshot, verify_snapshot


class LedgerBackupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'live.db'
        self.connection = sqlite3.connect(self.source)
        self.addCleanup(self.connection.close)
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('CREATE TABLE ledger(id INTEGER PRIMARY KEY, payload TEXT)')
        self.connection.execute("INSERT INTO ledger(payload) VALUES ('committed transaction')")
        self.connection.commit()
        self.config = dict(namespace='fixture', region='us-phoenix-1', bucket='sds-ledger-backups',
                           budget_bytes=1000000, max_snapshot_bytes=100000)
        self.temp = self.root / 'temporary'
        self.temp.mkdir()
        self.uploaded = None
        self.calls = []
        self.bucket = {'public-access-type': 'NoPublicAccess', 'storage-tier': 'Standard',
                       'versioning': 'Disabled', 'auto-tiering': 'Disabled'}

    def runner(self, command, **kwargs):
        self.calls.append(command)
        if command[0] == 'docker':
            destination = self.root / 'captured.db'
            snapshot(self.source, destination, 100000)
            kwargs['stdout'].write(destination.read_bytes())
            return subprocess.CompletedProcess(command, 0)
        self.assertIn('instance_principal', command)
        if command[2:4] == ['bucket', 'get']:
            data = {'data': self.bucket}
        elif command[2:4] == ['object', 'list']:
            self.assertIn('--all', command)
            data = {'data': []}
        elif command[2:4] == ['object', 'put']:
            path = Path(command[command.index('--file') + 1])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn('--verify-checksum', command)
            self.assertIn('--no-overwrite', command)
            self.assertIn('--no-multipart', command)
            self.uploaded = path.read_bytes()
            data = {}
        elif command[2:4] == ['object', 'get']:
            Path(command[command.index('--file') + 1]).write_bytes(self.uploaded)
            data = {}
        else:
            self.fail('Unexpected command')
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(data))

    def test_live_wal_snapshot_can_restore_committed_rows(self):
        self.assertTrue(Path(str(self.source) + '-wal').exists())
        target = self.root / 'snapshot.db'
        snapshot(self.source, target, 100000)
        with closing(readonly(target)) as connection:
            self.assertEqual(connection.execute('SELECT payload FROM ledger').fetchall(),
                             [('committed transaction',)])
        self.assertEqual(verify_snapshot(target, 100000), hashlib.sha256(target.read_bytes()).digest())

    def test_missing_source_does_not_create_empty_database(self):
        source = self.root / 'absent.db'
        with self.assertRaises(sqlite3.OperationalError):
            snapshot(source, self.root / 'bad.db', 100000)
        self.assertFalse(source.exists())

    def test_uncommitted_rows_are_not_backed_up(self):
        self.connection.execute("INSERT INTO ledger(payload) VALUES ('not committed')")
        target = self.root / 'committed.db'
        snapshot(self.source, target, 100000)
        with closing(readonly(target)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM ledger').fetchone(), (1,))

    def test_snapshot_limit_rejects_before_copy(self):
        with self.assertRaises(ValueError):
            snapshot(self.source, self.root / 'too-big.db', 1)

    def test_success_uploads_restores_and_cleans_temporary_files(self):
        backup(self.config, runner=self.runner, temp_root=self.temp)
        self.assertIsNotNone(self.uploaded)
        self.assertEqual(list(self.temp.iterdir()), [])
        docker = next(call for call in self.calls if call[0] == 'docker')
        self.assertIn('/app/data/sds_production.db', docker)
        self.assertIn('wsgi-backend', docker)

    def test_upload_failure_cleans_temporary_files(self):
        def fail(command, **kwargs):
            if command[2:4] == ['object', 'put']:
                raise subprocess.CalledProcessError(1, command)
            return self.runner(command, **kwargs)
        with self.assertRaises(subprocess.CalledProcessError):
            backup(self.config, runner=fail, temp_root=self.temp)
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_standalone_container_helper_streams_a_valid_snapshot(self):
        helper = Path(__file__).resolve().parents[1] / 'deploy/ledger_backup.py'
        result = subprocess.run([sys.executable, str(helper), '--stream', str(self.source),
            '--max-bytes', '100000'], capture_output=True, check=True)
        target = self.root / 'streamed.db'
        target.write_bytes(result.stdout)
        verify_snapshot(target, 100000)
        self.assertTrue(result.stdout.startswith(b'SQLite format 3'))

    def test_docker_failure_cleans_up_without_upload(self):
        def fail(command, **kwargs):
            if command[0] == 'docker':
                raise subprocess.CalledProcessError(1, command)
            return self.runner(command, **kwargs)
        with self.assertRaises(subprocess.CalledProcessError):
            backup(self.config, runner=fail, temp_root=self.temp)
        self.assertEqual(list(self.temp.iterdir()), [])
        self.assertIsNone(self.uploaded)

    def test_iam_failure_precedes_database_access(self):
        def deny(command, **kwargs):
            self.assertEqual(command[0], 'oci')
            raise subprocess.CalledProcessError(1, command)
        with self.assertRaises(subprocess.CalledProcessError):
            backup(self.config, runner=deny, temp_root=self.temp)
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_private_bucket_and_versioning_preflight(self):
        for field, value in [('public-access-type', 'ObjectRead'), ('versioning', 'Enabled'),
                             ('storage-tier', 'Archive'), ('auto-tiering', 'InfrequentAccess')]:
            previous = self.bucket[field]
            self.bucket[field] = value
            with self.assertRaises(ValueError):
                preflight(self.config, runner=self.runner)
            self.bucket[field] = previous
        self.assertFalse(any(call[0] == 'docker' for call in self.calls))

    def test_exhausted_budget_never_uploads_or_deletes(self):
        self.config['budget_bytes'] = 1
        with self.assertRaises(ValueError):
            backup(self.config, runner=self.runner, temp_root=self.temp)
        self.assertFalse(any('put' in call or 'delete' in call for call in self.calls))

    def test_corrupt_restored_database_fails_and_cleans_up(self):
        def corrupt(command, **kwargs):
            result = self.runner(command, **kwargs)
            if command[2:4] == ['object', 'get']:
                Path(command[command.index('--file') + 1]).write_bytes(b'corrupt')
            return result
        with self.assertRaises(sqlite3.DatabaseError):
            backup(self.config, runner=corrupt, temp_root=self.temp)
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_different_valid_restore_fails_digest(self):
        def alter(command, **kwargs):
            result = self.runner(command, **kwargs)
            if command[2:4] == ['object', 'get']:
                with closing(sqlite3.connect(command[command.index('--file') + 1])) as connection:
                    connection.execute("UPDATE ledger SET payload='different'")
                    connection.commit()
            return result
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            backup(self.config, runner=alter, temp_root=self.temp)
        self.assertEqual(list(self.temp.iterdir()), [])
