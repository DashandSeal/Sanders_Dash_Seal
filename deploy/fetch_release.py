"""Download the exact private release through OCI Instance Principals; verify before extraction."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time


def unpack(archive, destination, expected):
    archive, destination = Path(archive), Path(destination)
    if not re.fullmatch('[0-9a-f]{64}', expected) or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError('Release archive SHA mismatch')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Refusing to overwrite existing source')
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        if not members or len(members) > 5000 or sum(m.size for m in members) > 32 * 1024 * 1024:
            raise ValueError('Release archive exceeds limits')
        names = set()
        for member in members:
            path = Path(member.name)
            if (not member.isfile() or path.is_absolute() or '..' in path.parts
                    or member.name in names or '\\' in member.name):
                raise ValueError('Unsafe release archive member')
            names.add(member.name)
        destination.mkdir(mode=0o755, parents=True)
        for member in members:
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile(member).read())
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def fetch(config, *, runner=subprocess.run, pause=time.sleep):
    if not re.fullmatch('[0-9a-f]{40}', config['commit']):
        raise ValueError('Exact release commit required')
    with tempfile.TemporaryDirectory(prefix='sds-release-') as directory:
        archive = Path(directory) / 'application.tgz'
        for attempt in range(120):
            result = runner(['oci', 'os', 'object', 'get', '--namespace-name', config['namespace'],
                '--bucket-name', config['bucket'], '--name', config['object'], '--file', str(archive),
                '--auth', 'instance_principal', '--region', 'us-phoenix-1', '--no-retry',
                '--connection-timeout', '5', '--read-timeout', '10'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=30, check=False)
            if result.returncode == 0:
                unpack(archive, '/opt/sds-approved-source', config['sha256'])
                return
            if archive.exists(): archive.unlink()
            pause(15)
    raise ValueError('Private release unavailable after IAM propagation deadline')


if __name__ == '__main__':
    try:
        fetch(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        raise SystemExit('Release transfer failed; no application activation was reported.')
