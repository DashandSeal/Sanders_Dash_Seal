"""Administrator bootstrap for the OCI agent's fixed private-bucket installer."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


HELPER = '/usr/local/sbin/sanders-install-from-bucket'
SUDOERS = 'ocarun ALL=(root) NOPASSWD: NOSETENV: ' + HELPER + '\n'


def render_helper(namespace, bucket):
    if (not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', namespace)
            or not re.fullmatch(r'sds-release-[0-9a-f]{12}', bucket)):
        raise ValueError('Expected the existing Sanders private release bucket')
    template = '''#!/usr/bin/python3
import fcntl, os, re, subprocess, sys, tempfile
from pathlib import Path
if os.geteuid() != 0 or len(sys.argv) != 2 or not re.fullmatch('[0-9a-f]{40}', sys.argv[1]):
    raise SystemExit('A full release commit and administrator execution are required')
os.umask(0o077)
env = {'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'}
work = Path('/run/sanders-agent-installer')
work.mkdir(mode=0o700, exist_ok=True)
info = work.stat()
if work.is_symlink() or info.st_uid != 0 or info.st_mode & 0o077:
    raise SystemExit('Invalid administrator working directory')
with open(work / 'install.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    with tempfile.TemporaryDirectory(prefix='sds-install-', dir=work) as directory:
        target = Path(directory) / 'install.sh'
        subprocess.run(['/usr/bin/oci','os','object','get',
            '--namespace-name',NAMESPACE,'--bucket-name',BUCKET,
            '--name','installers/' + sys.argv[1] + '.sh','--file',str(target),
            '--auth','instance_principal','--region','us-phoenix-1',
            '--connection-timeout','5','--read-timeout','30'],
            check=True, timeout=120, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not target.is_file() or not 0 < target.stat().st_size <= 1048576:
            raise SystemExit('Invalid private installer size')
        subprocess.run(['/bin/bash',str(target)], check=True, env=env,
                       stdin=subprocess.DEVNULL)
'''
    bindings = {'NAMESPACE': repr(namespace), 'BUCKET': repr(bucket)}
    return re.sub(r'\b(NAMESPACE|BUCKET)\b', lambda match: bindings[match[0]], template)


def bootstrap(namespace, bucket):
    helper = render_helper(namespace, bucket)
    if os.geteuid() != 0:
        raise PermissionError('Run this one-time bootstrap from an administrator session')
    if not Path('/usr/bin/oci').is_file():
        subprocess.run(['/usr/bin/dnf', 'install', '-y',
                        'oraclelinux-developer-release-el9'], check=True)
        subprocess.run(['/usr/bin/dnf', 'install', '-y', 'python39-oci-cli'], check=True)
    # All destinations are fixed and under administrator-owned directories.
    for directory in (Path(HELPER).parent, Path('/etc/sudoers.d')):
        info = directory.stat()
        if directory.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise PermissionError('Installer directory must be administrator-owned')
    work_dir = Path('/run/sanders-agent-installer')
    work_dir.mkdir(mode=0o700, exist_ok=True)
    info = work_dir.stat()
    if work_dir.is_symlink() or info.st_uid != 0 or info.st_mode & 0o077:
        raise PermissionError('Administrator working directory must be private')
    with tempfile.TemporaryDirectory(prefix='sds-agent-bootstrap-', dir='/run') as work:
        candidate = Path(work) / 'sudoers'
        candidate.write_text(SUDOERS)
        candidate.chmod(0o440)
        subprocess.run(['/usr/sbin/visudo', '-cf', str(candidate)], check=True)
        for destination, content, mode in ((Path(HELPER), helper, 0o700),
                (Path('/etc/sudoers.d/sanders-agent-installer'), SUDOERS, 0o440)):
            if destination.is_symlink():
                raise PermissionError('Refusing a symlink destination')
            # Replace atomically; never follow an existing target during writes.
            fd, temporary = tempfile.mkstemp(prefix='.sds-', dir=destination.parent)
            try:
                with os.fdopen(fd, 'w') as handle:
                    handle.write(content)
                    os.fchmod(handle.fileno(), mode)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-config')
    parser.add_argument('--namespace')
    parser.add_argument('--bucket')
    args = parser.parse_args()
    if args.release_config:
        if args.namespace or args.bucket:
            parser.error('Use release-config or namespace/bucket, not both')
        config = json.loads(Path(args.release_config).read_text())
        bootstrap(config['namespace'], config['bucket'])
    elif args.namespace and args.bucket:
        bootstrap(args.namespace, args.bucket)
    else:
        parser.error('Supply release-config or both namespace and bucket')
