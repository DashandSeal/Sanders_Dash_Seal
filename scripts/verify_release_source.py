"""Verify Git or packaged source integrity, without inventing release authority."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def verify(root, commit=None):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Regular source directory required')
    if (root / '.git').is_dir():
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
        actual = git('rev-parse', 'HEAD')
        if git('status', '--porcelain', '--untracked-files=all'):
            raise ValueError('Source checkout has drift')
        names = git('ls-files').splitlines()
    else:
        manifest = root / '.sds-source.json'
        if manifest.is_symlink():
            raise ValueError('Regular source manifest required')
        record = json.loads(manifest.read_text())
        actual, expected = record['source_commit'], record['files']
        names = sorted(expected)
        observed = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
        if observed != set(names) | {'.sds-source.json'}:
            raise ValueError('Packaged source inventory changed')
        for name, digest in expected.items():
            path = root / name
            if (Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink()
                    or not re.fullmatch('[0-9a-f]{64}', digest)
                    or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
                raise ValueError('Packaged source hash mismatch')
    if not re.fullmatch('[0-9a-f]{40}', actual) or (commit and commit != actual):
        raise ValueError('Exact source commit mismatch')
    for name in names:
        path = root / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid source file')
    return actual, names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('commit', nargs='?')
    parser.add_argument('--copy-to', type=Path)
    args = parser.parse_args()
    try:
        commit, names = verify(args.source, args.commit)
        if args.copy_to:
            for name in names:
                target = args.copy_to / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(args.source / name, target)
        print('SOURCE_INTEGRITY_VERIFIED ' + commit + ' (not a privileged-operation grant)')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        parser.exit(1, 'Source verification failed: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
