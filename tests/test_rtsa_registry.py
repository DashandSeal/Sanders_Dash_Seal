"""Canonical 14-RTSA architecture boundary tests."""
import unittest
from core_platform.rtsa_registry import RTSA_ROLES, RTSAStatus, get_rtsa, authorize_rtsa, RTSAAuthorizationError

class RTSATests(unittest.TestCase):
    def test_all_fourteen_are_distinct(self):
        self.assertEqual(len(RTSA_ROLES), 14)
        self.assertEqual(len({role.slug for role in RTSA_ROLES.values()}), 14)
        self.assertIn("HYDRA-Q", RTSA_ROLES)
        self.assertIn("LABYRINTH", RTSA_ROLES)
        self.assertIn("MINOTAUR", RTSA_ROLES)
        self.assertIn("Sanders Labyrinth Shield 🛡️", RTSA_ROLES)

    def test_all_are_fail_closed(self):
        for name, role in RTSA_ROLES.items():
            with self.subTest(name=name):
                self.assertEqual(role.status, RTSAStatus.SPECIFIED)
                self.assertFalse(role.enabled)
                self.assertTrue(role.requires_twin_gate)
                self.assertTrue(role.requires_human_approval)
                with self.assertRaises(RTSAAuthorizationError):
                    authorize_rtsa(name, "external_execution")

    def test_unknown_identity_rejected(self):
        with self.assertRaises(RTSAAuthorizationError):
            get_rtsa("MICHAEL ANGELO")

    def test_it_agents_not_rtsa(self):
        with self.assertRaises(RTSAAuthorizationError):
            get_rtsa("Uptime Agent")

if __name__ == "__main__":
    unittest.main()
