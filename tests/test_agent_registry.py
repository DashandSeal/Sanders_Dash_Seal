"""Registry tests: all 12 source-defined agents must fail closed."""
import unittest
from core_platform.agent_registry import AGENTS, IT_AGENT_NAMES, require_registered_agent, require_executable_agent

class RegistryTests(unittest.TestCase):
    def test_exact_source_matrix(self):
        self.assertEqual(len(IT_AGENT_NAMES), 12)
        self.assertEqual(set(AGENTS), set(IT_AGENT_NAMES))
    def test_no_unapproved_execution(self):
        for name in IT_AGENT_NAMES:
            with self.subTest(name=name):
                self.assertEqual(require_registered_agent(name).implementation_status, "INTERFACE_ONLY")
                with self.assertRaises(PermissionError):
                    require_executable_agent(name)
    def test_unknown_agent_denied(self):
        with self.assertRaises(PermissionError):
            require_registered_agent("Unknown Agent")

if __name__ == "__main__":
    unittest.main()
