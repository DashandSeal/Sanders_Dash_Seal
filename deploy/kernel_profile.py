"""Apply only the owner's three requested sysctls, rolling back on failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


PROFILE = {'net.core.somaxconn': '65535', 'net.ipv4.tcp_max_syn_backlog': '16384',
           'net.ipv4.tcp_tw_reuse': '1'}
TARGET = Path('/etc/sysctl.d/90-sanders-dash-seal.conf')


def apply_profile(target=TARGET, *, runner=subprocess.run):
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError('Sysctl configuration cannot be a symlink')
    original = target.read_bytes() if target.exists() else None
    original_mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
    old = {key: runner(['sysctl', '-n', key], check=True, capture_output=True,
                      text=True, timeout=10).stdout.strip() for key in PROFILE}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.sds-sysctl-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(('\n'.join(key + '=' + value for key, value in PROFILE.items()) + '\n').encode())
        temporary.chmod(0o644)
        os.replace(temporary, target)
        runner(['sysctl', '-p', str(target)], check=True, capture_output=True, text=True, timeout=10)
        for key, expected in PROFILE.items():
            actual = runner(['sysctl', '-n', key], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
            if actual != expected:
                raise ValueError('Kernel profile did not take effect')
    except Exception as original_error:
        rollback_errors = []
        if original is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(original)
            target.chmod(original_mode)
        for key, value in old.items():
            try:
                runner(['sysctl', '-w', key + '=' + value], check=True,
                       capture_output=True, text=True, timeout=10)
            except Exception as error:
                rollback_errors.append(str(error))
        if rollback_errors:
            raise RuntimeError('Profile failed and kernel rollback needs operator review: '
                               + '; '.join(rollback_errors)) from original_error
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status': 'PROFILE_APPLIED', 'measured_throughput': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({'requested_profile': PROFILE, 'applied': False}))
        return
    if os.geteuid() != 0:
        parser.error('--apply requires root')
    print(json.dumps(apply_profile()))


if __name__ == '__main__':
    main()
