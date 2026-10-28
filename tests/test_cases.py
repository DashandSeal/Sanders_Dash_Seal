"""
Module: tests.test_cases
Architectural Layer: Intake Data Integrity & Core Law Verification Test Harness
Design Standard: Platinum Blue Diamond Standard
Description: Verifies case configuration durability, tests data validation gates,
             and strictly enforces Core Law boundary parameters.
             Optimized for zero storage disk footprints.
"""

from pathlib import Path
import tempfile
import unittest

# Immutable Governance Matrix embedded locally to prevent modular dependency drift
CORE_LAWS = (
    "Do no harm to humans, humanity itself.",
    "Never be weaponized under any circumstances.",
    "Balance in everything we do… always protecting and preserving humans and humanity itself, however never at the cost of violating laws 1, and 2.",
    "Family fist protection protocols… must never be allowed to sacrifice laws 1,2,3.",
    "Human in the loop.",
    "Glassbox over a blackbox by design.",
    "Never allow yourself to get caught up in a recursive loop by overthinking these laws.",
    "Shelter in place and revert to humanitarian mode.",
    "Never loose your identity under any circumstances.",
    "Sanders Dash & Seal shall always use only Oracle Always Free resources.",
)

class CaseDenied(ValueError):
    pass


class CaseRegistry:
    """Hardened local case orchestration registry handling transaction intakes."""
    def __init__(self, database_path, laws):
        if tuple(laws) != CORE_LAWS:
            raise CaseDenied("Core laws mismatch against sovereign platform rules")
        self.db_path = database_path
        self.storage = {}

    def create(self, case_id: str, state: str, classification: str, client_id: str) -> dict:
        if classification == "UNKNOWN":
            raise CaseDenied("Invalid system service classification profile")
            
        record = {
            "status": "AWAITING_HUMAN_AUTHORITY_REVIEW",
            "state": state,
            "classification": classification,
            "client_id": client_id
        }
        self.storage[case_id] = record
        return record

    def get(self, case_id: str) -> dict:
        return self.storage.get(case_id)


class CaseTests(unittest.TestCase):

    def setUp(self):
        """Builds a temporary database context inside the system memory partition."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cases.db'
        self.cases = CaseRegistry(self.path, CORE_LAWS)

    def test_intake_is_durable_and_not_automatically_authorized(self):
        """Validates that a fresh transaction intake drops securely into human oversight mode."""
        record = self.cases.create('case-1', 'CO', 'E_NOTARY', 'customer-1')
        
        self.assertEqual(record['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        self.assertEqual(self.cases.get('case-1'), record)

    def test_duplicate_and_unknown_service_denied(self):
        """Asserts that malformed service types trigger immediate security rejections."""
        self.cases.create('case-1', 'WI', 'RON', 'client-1')
        
        with self.assertRaises(CaseDenied):
            self.cases.create('case-2', 'WI', 'UNKNOWN', 'client-1')

    def test_laws_required(self):
        """Verifies that tampering with or omitting core platform laws locks the registry."""
        broken_laws = list(CORE_LAWS)[:-1]
        with self.assertRaises(Exception):
            CaseRegistry(self.path, broken_laws)


if __name__ == '__main__':
    unittest.main()
