"""Reproducibly snapshot existing source into the owner's ./backend context.

Only listed platform source/assets are copied; no credentials, records or keys.
Run from any directory after changing a packaged source or paired manifest.
"""
import hashlib
import json
from pathlib import Path


def snapshot(root):
    paths = [*root.glob('core_platform/*.py'), *root.glob('core_platform/*.py.pbd.json')]
    paths += [p for p in (root / 'web').rglob('*') if p.is_file()]
    paths += [root / p for p in ('requirements.txt', 'requirements-server.txt',
                                'deploy/gunicorn.conf.py', 'deploy/gunicorn.conf.py.pbd.json')]
    return {p.relative_to(root).as_posix(): {'content': p.read_text(),
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'backend/platform-source.json').write_text(
        json.dumps(snapshot(root), indent=2, ensure_ascii=False) + '\n')
