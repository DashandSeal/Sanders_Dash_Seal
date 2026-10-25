"""Source snapshot consistency for the owner's separate backend build context."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from backend.unpack import unpack


class OwnerStackPackagingTests(unittest.TestCase):
    def test_backend_build_uses_canonical_sources_without_duplicate_snapshot(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / 'backend/Dockerfile').read_text()
        compose = (root / 'docker-compose.yml').read_text()
        self.assertIn('COPY core_platform/ ./core_platform/', dockerfile)
        self.assertIn('COPY web/ ./web/', dockerfile)
        self.assertNotIn('platform-source.json', dockerfile)
        self.assertIn('context: .\n      dockerfile: backend/Dockerfile', compose)
        for image in ('sds-founder.png', 'IMG_20261024_141659486_HDR.jpg',
                      'IMG_20261024_141701319_HDR.jpg'):
            self.assertTrue((root / 'web' / image).is_file())

    def test_unpack_denies_path_escape_and_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle.json'
            for bad in ({'../escape.py': {'content': 'x', 'sha256': ''}},
                        {'core_platform/x.py': {'content': 'changed', 'sha256': ''}}):
                bundle.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    unpack(bundle, root / 'output')

    def test_binary_portrait_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'web'
            source.mkdir()
            raw = b'\\x89PNG\\r\\n\\x1a\\n' + bytes(range(256))
            (source / 'sds-founder.png').write_bytes(raw)
            item = {'content_base64': base64.b64encode(raw).decode('ascii'),
                    'sha256': hashlib.sha256(raw).hexdigest()}
            bundle = root / 'bundle.json'
            bundle.write_text(json.dumps({'web/sds-founder.png': item}))
            unpack(bundle, root / 'output')
            self.assertEqual((root / 'output/web/sds-founder.png').read_bytes(), raw)
            item['sha256'] = '0' * 64
            bundle.write_text(json.dumps({'web/sds-founder.png': item}))
            with self.assertRaises(ValueError):
                unpack(bundle, root / 'tampered')

    def test_default_compose_and_named_compose_are_identical(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / 'compose.yaml').read_bytes(),
                         (root / 'docker-compose.yml').read_bytes())
