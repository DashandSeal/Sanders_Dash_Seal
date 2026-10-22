"""Static release-policy checks: deployment separate from privileged Twin-Gate."""
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

    def test_deployment_checks_without_privileged_twin_gate(self):
        self.assertNotIn('DENIED: independent production authorization not provisioned', self.workflow)
        self.assertIn('hashlib.sha256(path.read_bytes()).hexdigest()', self.workflow)
        self.assertIn("sys.exit('DENIED: paired manifest absent')", self.workflow)
        self.assertIn("sys.exit('DENIED: release evidence absent')", self.workflow)
        self.assertIn('no deployment performed', self.workflow)
        self.assertNotIn('kubectl apply', self.workflow)
        self.assertNotIn('docker push', self.workflow)
        self.assertNotIn('stripe trigger', self.workflow)

if __name__ == '__main__':
    unittest.main()
