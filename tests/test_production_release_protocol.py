"""Static fail-closed checks for the production release entrypoint."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ProductionReleaseProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (ROOT / '.github/workflows/production-release.yml').read_text()

    def test_manual_only_and_read_only(self):
        self.assertIn('workflow_dispatch:', self.workflow)
        self.assertNotIn('push:', self.workflow)
        self.assertIn('contents: read', self.workflow)
        self.assertIn('environment: production', self.workflow)

    def test_no_unguarded_deployment(self):
        self.assertIn('DENIED: independent production authorization not provisioned', self.workflow)
        self.assertIn('hashlib.sha256(path.read_bytes()).hexdigest()', self.workflow)
        self.assertNotIn('kubectl apply', self.workflow)
        self.assertNotIn('docker push', self.workflow)
        self.assertNotIn('stripe trigger', self.workflow)

if __name__ == '__main__':
    unittest.main()
