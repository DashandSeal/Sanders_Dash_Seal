"""Extract and verify text and binary source snapshot entries."""
import base64
import binascii
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
        if ('content' in item) == ('content_base64' in item):
            raise ValueError('Snapshot entry must have exactly one content encoding')
        if 'content_base64' in item:
            try:
                raw = base64.b64decode(item['content_base64'], validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError('Invalid base64 snapshot content') from error
        else:
            raw = item['content'].encode('utf-8')
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Snapshot hash mismatch')
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


if __name__ == '__main__':
    unpack('platform-source.json', '.')
