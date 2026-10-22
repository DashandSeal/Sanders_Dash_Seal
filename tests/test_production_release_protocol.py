"""Legacy entrypoint delegates to real deployment without extra approval inputs."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ProductionReleaseProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (ROOT / '.github/workflows/production-release.yml').read_text()

    def test_legacy_entrypoint_has_no_manual_authority_gate(self):
        self.assertIn('workflow_dispatch:', self.workflow)
        self.assertNotIn('push:', self.workflow)
        self.assertIn('contents: read', self.workflow)
        self.assertNotIn('environment:', self.workflow)
        self.assertNotIn('release_evidence', self.workflow)
        self.assertNotIn('artifact_path', self.workflow)

    def test_deployment_checks_without_privileged_twin_gate(self):
        self.assertNotIn('DENIED: independent production authorization not provisioned', self.workflow)
        self.assertIn('uses: ./.github/workflows/oci-gitops-deploy.yml', self.workflow)
        self.assertIn('secrets: inherit', self.workflow)
        self.assertNotIn('DENIED:', self.workflow)
        self.assertNotIn('kubectl apply', self.workflow)
        self.assertNotIn('docker push', self.workflow)
        self.assertNotIn('stripe trigger', self.workflow)

if __name__ == '__main__':
    unittest.main()
