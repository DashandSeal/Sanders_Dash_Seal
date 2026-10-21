"""Host-local authorized-source baseline. No automatic repair or rebasing on drift."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


def inventory(root):
    root = Path(root).resolve()
    records = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '.git' in relative.parts:
            continue
        if path.is_symlink():
            raise ValueError('Symlink in deployed source')
        if path.is_file():
            metadata = path.stat()
            records[relative.as_posix()] = {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'mode': stat.S_IMODE(metadata.st_mode), 'uid': metadata.st_uid}
    return records


def check(root, baseline):
    saved = json.loads(Path(baseline).read_text())
    current = inventory(root)
    return {'passed': saved['files'] == current,
        'missing': sorted(set(saved['files']) - set(current)),
        'unexpected': sorted(set(current) - set(saved['files'])),
        'changed': sorted(name for name in set(current) & set(saved['files'])
                          if current[name] != saved['files'][name])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['baseline', 'check', 'validate-stage'])
    parser.add_argument('root')
    parser.add_argument('baseline')
    args = parser.parse_args()
    if args.operation == 'validate-stage':
        unknown = set(inventory(args.baseline)) - set(inventory(args.root))
        if unknown:
            print(json.dumps({'unexpected_existing_files': sorted(unknown)}))
            return 1
        return 0
    baseline = Path(args.baseline)
    if args.operation == 'baseline':
        if os.geteuid() != 0 or baseline.is_symlink() or baseline.parent.is_symlink():
            parser.error('Baseline requires root and a protected, nonsymlink state path')
        if baseline.parent.stat().st_uid != 0 or stat.S_IMODE(baseline.parent.stat().st_mode) & 0o077:
            parser.error('Baseline directory must be root-owned and private')
        baseline.write_text(json.dumps({'schema': 1, 'files': inventory(args.root)}, indent=2) + '\n')
        baseline.chmod(0o600)
        print('Authorized-source integrity baseline installed; not a digital signature.')
        return 0
    result = check(args.root, baseline)
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
