"""Extract the reviewed source snapshot required by the ./backend build context."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def unpack(bundle_path, destination):
    destination = Path(destination).resolve()
    bundle = json.loads(Path(bundle_path).read_text())
    for name, item in bundle.items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts
                or not (name.startswith(('core_platform/', 'web/'))
                        or name in ('requirements.txt', 'requirements-server.txt',
                                    'deploy/gunicorn.conf.py', 'deploy/gunicorn.conf.py.pbd.json'))):
            raise ValueError('Unapproved bundle path')
        raw = item['content'].encode()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Snapshot hash mismatch')
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


if __name__ == '__main__':
    unpack('platform-source.json', '.')
