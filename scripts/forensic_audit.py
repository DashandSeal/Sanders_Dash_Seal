"""Repository tripwire: compare expected hashes, permissions and worktree state.

Checksums detect inconsistency; independent signatures and protected workflows
are required to authenticate who authorized a coordinated source/manifest edit.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess


def git(root, *arguments):
    return subprocess.run(['git', '-C', str(root), *arguments], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def audit(root):
    root = Path(root).resolve()
    policy = json.loads((root / 'security/forensic-policy.json').read_text())
    if policy.get('schema') != 1:
        raise ValueError('Unknown forensic policy')
    approved_duplicates = [set(group) for group in policy['allowed_duplicate_groups']]
    issues, inventory, unsigned = [], [], []
    duplicates = defaultdict(list)
    for entry in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not entry:
            continue
        metadata, encoded_name = entry.split(b'\t', 1)
        mode, object_id, stage = metadata.decode().split()
        name = encoded_name.decode('utf8')
        source = root / name
        if stage != '0' or mode not in ('100644', '100755'):
            issues.append({'path': name, 'reason': 'unsupported_git_entry'})
            continue
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
            issues.append({'path': name, 'reason': 'missing_or_unsafe_file'})
            continue
        permissions = stat.S_IMODE(source.stat().st_mode)
        expected = 0o755 if mode == '100755' else 0o644
        if permissions != expected:
            issues.append({'path': name, 'reason': 'permission_mismatch'})
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        inventory.append({'path': name, 'sha256': digest, 'mode': mode})
        if raw.strip():
            duplicates[digest].append(name)
        requires_pair = (source.suffix in ('.py', '.js', '.sh') or source.name == 'Dockerfile'
                         or name in ('compose.yaml', 'docker-compose.yml', 'nginx.conf'))
        pair = Path(str(source) + '.pbd.json')
        if requires_pair or pair.exists():
            try:
                manifest = json.loads(pair.read_text())
                if (manifest['body']['artifact'] != name
                        or manifest['body']['payload_hash'] != digest):
                    raise ValueError('Pair mismatch')
                if not manifest.get('signatures'):
                    unsigned.append(name)
            except (OSError, ValueError, KeyError, TypeError):
                issues.append({'path': name, 'reason': 'missing_or_mismatched_pair'})
    for digest, names in duplicates.items():
        if len(names) > 1 and set(names) not in approved_duplicates:
            issues.append({'paths': sorted(names), 'reason': 'unexpected_exact_duplicate'})
    if git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all'):
        issues.append({'reason': 'uncommitted_or_untracked_drift'})
    return {'platform': 'Sanders Dash & Seal', 'schema': 1,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'commit': git(root, 'rev-parse', 'HEAD').decode().strip(),
        'integrity_passed': not issues, 'issues': issues,
        'inventory': sorted(inventory, key=lambda item: item['path']),
        'unsigned_pairs': unsigned, 'production_signatures_verified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    root, output = Path(arguments.root).resolve(), Path(arguments.output).resolve()
    if output.is_relative_to(root):
        parser.error('Audit output must be outside the checkout')
    output.mkdir(parents=True, exist_ok=True)
    report = audit(root)
    (output / 'forensic-report.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = []
    for item in report['inventory']:
        name = item['path']
        escaped = name.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
        prefix = '\\' if escaped != name else ''
        lines.append(f"{prefix}{item['sha256']}  {escaped}\n")
    (output / 'forensic_manifest.sha256').write_text(''.join(lines))
    print(json.dumps({'integrity_passed': report['integrity_passed'],
        'issues': len(report['issues']), 'files': len(report['inventory']),
        'production_signatures_verified': False}))
    return 0 if report['integrity_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
