"""Source snapshot consistency for the owner's separate backend build context."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from backend.refresh_sources import snapshot
from backend.unpack import unpack


class OwnerStackPackagingTests(unittest.TestCase):
    def test_backend_snapshot_matches_existing_platform_sources(self):
        root = Path(__file__).resolve().parents[1]
        saved = json.loads((root / 'backend/platform-source.json').read_text())
        self.assertEqual(saved, snapshot(root))

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
