"""Independent RTSA handler tests; offline and non-executing."""
import unittest
from core_platform.rtsa_registry import RTSA_ROLES
from core_platform.rtsa_assessments import assess, AssessmentRejected

class AssessmentTests(unittest.TestCase):
    def test_all_fourteen_have_distinct_handlers(self):
        for name in RTSA_ROLES:
            with self.subTest(name=name):
                result = assess(name, {})
                self.assertEqual(result.rtsa, name)
                self.assertEqual(result.outcome, "ADVISORY_ONLY")
                self.assertFalse(result.execution_allowed)
                self.assertTrue(result.findings)
                self.assertEqual(len(result.input_digest), 64)

    def test_canonical_digest_independent_of_key_order(self):
        a = assess("ARCHITECT", {"components": 1, "interfaces": 2})
        b = assess("ARCHITECT", {"interfaces": 2, "components": 1})
        self.assertEqual(a.input_digest, b.input_digest)

    def test_role_specific_results(self):
        self.assertIn("SHIELD_CLEARANCE_DENIED", assess("MINOTAUR", {}).findings)
        self.assertIn("ISOLATION_REQUIRED", assess("Sanders Labyrinth Shield 🛡️",
                                                   {"threat_detected": True}).findings)
        self.assertIn("FRAUD_REVIEW_REQUIRED", assess("Fraud RTSA 🚨",
                                                     {"suspicious_signals": [1]}).findings)

    def test_invalid_input_denied(self):
        with self.assertRaises(AssessmentRejected):
            assess("ARCHITECT", [])
        with self.assertRaises(AssessmentRejected):
            assess("ARCHITECT", {"bad": object()})
        with self.assertRaises(AssessmentRejected):
            assess("PROMETHEAN", {"threat_cases": "invalid"})

if __name__ == "__main__":
    unittest.main()
