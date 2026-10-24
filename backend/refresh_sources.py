"""Reproducibly snapshot existing source and binary assets into backend context."""
import base64
import hashlib
import json
from pathlib import Path


def snapshot(root):
    paths = [*root.glob('core_platform/*.py'), *root.glob('core_platform/*.py.pbd.json')]
    paths += [root / 'core_platform/oci_free_resources.json', root / 'core_platform/oci_free_resources.json.pbd.json']
    paths += [p for p in (root / 'web').rglob('*') if p.is_file()]
    paths += [root / p for p in ('requirements.txt', 'requirements-server.txt',
                                'deploy/gunicorn.conf.py', 'deploy/gunicorn.conf.py.pbd.json')]
    result = {}
    for path in sorted(paths):
        raw = path.read_bytes()
        item = {'sha256': hashlib.sha256(raw).hexdigest()}
        try:
            item['content'] = raw.decode('utf-8')
        except UnicodeDecodeError:
            item['content_base64'] = base64.b64encode(raw).decode('ascii')
        result[path.relative_to(root).as_posix()] = item
    return result


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'backend/platform-source.json').write_text(
        json.dumps(snapshot(root), indent=2, ensure_ascii=False) + '\n')
