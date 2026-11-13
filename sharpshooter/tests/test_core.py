import unittest
from sharpshooter.core import Adapter, Remediator, new_incident, evidence, diagnose

class DemoAdapter(Adapter):
    name = "demo"
    def capabilities(self): return {"renew_certificate"}
    def execute(self, operation, hostname, *, authorization):
        return {"success": True}

class Tests(unittest.TestCase):
    def test_no_authorization(self):
        incident = new_incident("example.org", {"tls": False})
        result = Remediator(DemoAdapter()).repair(incident, "renew_certificate", {})
        self.assertEqual(result.status, "authorization_required")
    def test_plan_does_not_execute(self):
        incident = new_incident("example.org", {"tls": False})
        result = Remediator(DemoAdapter()).repair(incident, "renew_certificate", {"approved": True, "provider": "demo"})
        self.assertEqual(result.status, "planned")
    def test_unsupported(self):
        incident = new_incident("example.org", {"tls": False})
        result = Remediator(DemoAdapter()).repair(incident, "change_dns", {})
        self.assertEqual(result.status, "provider_action_required")
    def test_evidence(self):
        self.assertIn("sha256", evidence(new_incident("example.org", {"tls": False})))
    def test_hostname_validation(self):
        with self.assertRaises(ValueError):
            diagnose("https://example.org/path")
if __name__ == "__main__":
    unittest.main()
