import unittest
from core_platform.autonomous_development import AutonomousDevelopment, DevelopmentDenied, FeatureRequest
from core_platform.upgrade_sidecar import CORE_LAWS

class Generator:
    def generate(self, request, inventory):
        return {'core_platform/new_feature.py': 'VALUE = 1\n'}

class Verifier:
    def __init__(self, passed=True): self.passed = passed
    def verify(self, request, candidate, hashes):
        return {'passed': self.passed, 'tests': 'independent'}

class Publisher:
    def __init__(self): self.calls = 0
    def open_review(self, request, candidate, hashes, evidence):
        self.calls += 1
        return {'review_id': 'draft-review', 'merged': False}

class Audit:
    def __init__(self): self.events = []
    def preserve(self, event): self.events.append(event)

class AutonomousTests(unittest.TestCase):
    def setUp(self):
        self.publisher, self.audit = Publisher(), Audit()
        self.request = FeatureRequest('feature-1', 'frontend', 'MASTER-3', 'Accessible intake')

    def test_review_not_deployment(self):
        engine = AutonomousDevelopment(Generator(), Verifier(), self.publisher, self.audit, CORE_LAWS)
        self.assertFalse(engine.prepare(self.request, {'frontend': 'v1'})['merged'])
        self.assertEqual(self.publisher.calls, 1)

    def test_failed_verification_denies_publish(self):
        engine = AutonomousDevelopment(Generator(), Verifier(False), self.publisher, self.audit, CORE_LAWS)
        with self.assertRaises(DevelopmentDenied):
            engine.prepare(self.request, {'frontend': 'v1'})
        self.assertEqual(self.publisher.calls, 0)

    def test_unknown_component_denied(self):
        engine = AutonomousDevelopment(Generator(), Verifier(), self.publisher, self.audit, CORE_LAWS)
        with self.assertRaises(DevelopmentDenied):
            engine.prepare(self.request, {})

if __name__ == '__main__':
    unittest.main()
