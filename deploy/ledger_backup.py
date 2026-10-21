"""Consistent ledger snapshots and private OCI uploads; no provisioning or deletion."""
import argparse
import base64
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid


def readonly(path):
    # mode=ro is essential: a missing source must never become an empty database.
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', timeout=10, uri=True)


def snapshot(source, destination, max_bytes):
    started = time.monotonic()
    with closing(readonly(source)) as src:
        pages = src.execute('PRAGMA page_count').fetchone()[0]
        page_size = src.execute('PRAGMA page_size').fetchone()[0]
        if pages == 0 or pages * page_size > max_bytes:
            raise ValueError('Source database is empty or exceeds snapshot allocation')
        with closing(sqlite3.connect(destination)) as dst:
            def progress(status, remaining, total):
                if total * page_size > max_bytes or time.monotonic() - started > 120:
                    raise ValueError('Snapshot allocation or time limit exceeded')
            src.backup(dst, pages=256, progress=progress, sleep=0.05)
            if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Snapshot integrity check failed')
    os.chmod(destination, 0o600)


def stream_snapshot(source, max_bytes):
    # Executed inside the existing Python container as its non-root app user.
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='sds-ledger-') as directory:
        target = Path(directory) / 'snapshot.db'
        snapshot(source, target, max_bytes)
        with target.open('rb') as handle:
            while chunk := handle.read(1024 * 1024):
                sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()


def verify_snapshot(path, max_bytes):
    if not 0 < path.stat().st_size <= max_bytes:
        raise ValueError('Invalid snapshot size')
    with closing(readonly(path)) as connection:
        if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Downloaded snapshot failed integrity check')
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.digest()


def load_config(path):
    info = path.stat()
    if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError('Backup configuration must be root-owned and private (0600)')
    config = json.loads(path.read_text())
    for field in ('namespace', 'region', 'bucket'):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError('Missing backup configuration: ' + field)
    budget = config.get('budget_bytes')
    maximum = config.get('max_snapshot_bytes')
    if (type(budget) is not int or type(maximum) is not int
            or not 0 < maximum <= 1_000_000_000
            or not maximum <= budget <= 20_000_000_000):
        raise ValueError('Explicit remaining free allocation and snapshot limit required')
    return config


def oci(config, arguments, *, runner=subprocess.run):
    command = ['oci', 'os', *arguments, '--namespace-name', config['namespace'],
               '--region', config['region'], '--auth', 'instance_principal',
               '--connection-timeout', '10', '--read-timeout', '120',
               '--max-retries', '2', '--output', 'json']
    result = runner(command, check=True, capture_output=True, text=True, timeout=600)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def preflight(config, *, runner=subprocess.run):
    bucket = oci(config, ['bucket', 'get', '--bucket-name', config['bucket'], '--fields', 'autoTiering'], runner=runner)['data']
    if (bucket.get('public-access-type') != 'NoPublicAccess'
            or bucket.get('storage-tier') != 'Standard'
            or bucket.get('versioning') != 'Disabled'
            or bucket.get('auto-tiering') != 'Disabled'):
        raise ValueError('Require a private Standard bucket with versioning and auto-tiering disabled')
    # Account-wide free headroom is an operator prerequisite, not a billing cap.
    objects = oci(config, ['object', 'list', '--bucket-name', config['bucket'], '--all'], runner=runner)['data']
    sizes = [item['size'] for item in objects]
    if any(type(size) is not int or size < 0 for size in sizes):
        raise ValueError('Invalid bucket inventory')
    used = sum(sizes)
    if len(objects) >= 10000 or used + config['max_snapshot_bytes'] > config['budget_bytes']:
        raise ValueError('Backup allocation exhausted; no upload or automatic deletion performed')
    return used


def backup(config, *, runner=subprocess.run, temp_root=None):
    used = preflight(config, runner=runner)
    with tempfile.TemporaryDirectory(prefix='sds-backup-', dir=temp_root) as directory:
        local = Path(directory) / 'ledger.db'
        # Send only this helper into the running backend: no dependency install or restart.
        helper = Path(__file__).read_text()
        command = ['docker', 'compose', '-p', 'sanders-dash-seal',
                   '-f', '/opt/sanders-dash-seal/docker-compose.yml',
                   '-f', '/opt/sanders-dash-seal/deploy/compose.production.yml',
                   'exec', '-T', 'wsgi-backend', 'python', '-c', helper,
                   '--stream', '/app/data/sds_production.db',
                   '--max-bytes', str(config['max_snapshot_bytes'])]
        with local.open('xb') as output:
            os.chmod(local, 0o600)
            runner(command, stdout=output, check=True, timeout=180)
        digest = verify_snapshot(local, config['max_snapshot_bytes'])
        if used + local.stat().st_size > config['budget_bytes']:
            raise ValueError('Backup allocation exhausted')
        name = ('ledger_snapshots/sds_production_' +
                datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + uuid.uuid4().hex + '.db')
        oci(config, ['object', 'put', '--bucket-name', config['bucket'], '--file', str(local),
            '--name', name, '--no-overwrite', '--no-multipart', '--verify-checksum',
            '--opc-checksum-algorithm', 'SHA256', '--opc-content-sha256',
            base64.b64encode(digest).decode('ascii'), '--metadata',
            json.dumps({'sha256': digest.hex(), 'format': 'sqlite-online-backup-v1'})], runner=runner)
        # Prove the uploaded object can be restored, rather than trusting an upload message.
        restored = Path(directory) / 'restore.db'
        oci(config, ['object', 'get', '--bucket-name', config['bucket'],
            '--name', name, '--file', str(restored)], runner=runner)
        if verify_snapshot(restored, config['max_snapshot_bytes']) != digest:
            raise ValueError('Restore digest mismatch; remote object retained for investigation')
        print(json.dumps({'status': 'BACKUP_RESTORE_VERIFIED', 'object': name,
                          'sha256': digest.hex(), 'bytes': local.stat().st_size}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path('/etc/sanders-dash-seal/backup.json'))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--stream', type=Path)
    parser.add_argument('--max-bytes', type=int)
    args = parser.parse_args()
    os.umask(0o077)
    if args.stream:
        if args.max_bytes is None or args.max_bytes <= 0:
            parser.error('--stream requires a positive --max-bytes')
        stream_snapshot(args.stream, args.max_bytes)
        return
    if os.geteuid() != 0:
        parser.error('Host backup requires root access to the existing Docker volume')
    config = load_config(args.config)
    with open('/run/lock/sanders-ledger-backup.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.check:
            preflight(config)
            print('Private bucket access and configured allocation verified; no backup performed')
        else:
            backup(config)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        print('Ledger backup failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
