"""Cross-component MASTER integration regression tests."""
import tempfile
import unittest
from pathlib import Path
from core_platform.platform_integration import SandersDashSealIntegration, IntegrationDenied
from core_platform.upgrade_sidecar import CORE_LAWS, UpgradeSidecar
from core_platform.cases import CaseRegistry
from core_platform.tech_team_dispatch import TechTeamDispatcher


class Audit:
    def __init__(self):
        self.events = []

    def preserve(self, record):
        self.events.append(record)


class Authority:
    def __init__(self, cases, audit):
        self.cases, self.audit = cases, audit

    def review(self, case_id, reviewer, notary_identity, evidence):
        return {'case_id': case_id, 'status': 'REVIEW_VERIFIED',
                'notarial_act_executed': False}


class PlatformIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.audit = Audit()
        self.cases = CaseRegistry(root / 'cases.db', CORE_LAWS)
        self.authority = Authority(self.cases, self.audit)
        self.dispatch = TechTeamDispatcher(root / 'tasks.db', CORE_LAWS, self.audit)
        self.sidecar = UpgradeSidecar(root / 'upgrades.db', ['core_platform'], CORE_LAWS)
        self.platform = SandersDashSealIntegration(
            self.cases, self.authority, self.dispatch, self.sidecar,
            self.audit, CORE_LAWS)

    def tearDown(self):
        self.temp.cleanup()

    def test_connected_intake_and_human_review(self):
        case = self.platform.intake('case-1', 'CO', 'E_NOTARY', 'requester-1')
        self.assertEqual(case['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')
        result = self.platform.human_review('case-1', 'reviewer', 'notary', {'proof': True})
        self.assertFalse(result['notarial_act_executed'])
        self.assertEqual(self.cases.get('case-1')['status'], 'AWAITING_HUMAN_AUTHORITY_REVIEW')

    def test_technical_and_sidecar_connection(self):
        self.assertEqual(self.platform.request_technical_work(
            'task-1', 'IT_AI_Manager_v15.0', 'INTEGRATION_TEST',
            'core_platform', 'MASTER 8', {}), 'QUEUED')
        self.assertEqual(self.platform.propose_upgrade(
            'upgrade-1', 'core_platform', '1', 'a' * 64,
            {'master_section': 'MASTER 13'}), 'PROPOSED')
        self.assertEqual(self.sidecar.get('upgrade-1')['state'], 'PROPOSED')

    def test_no_self_authorized_execution(self):
        with self.assertRaises(IntegrationDenied):
            self.platform.deploy()
        with self.assertRaises(IntegrationDenied):
            self.platform.execute_notarial_act()
        with self.assertRaises(IntegrationDenied):
            self.platform.request_technical_work(
                'task-2', 'IT_AI_Manager_v15.0', 'INTEGRATION_TEST',
                'core_platform', 'unverified', {})
        with self.assertRaises(IntegrationDenied):
            self.platform.propose_upgrade('upgrade-2', 'core_platform', '1', 'a' * 64, {})

    def test_independent_boundaries(self):
        with self.assertRaises(IntegrationDenied):
            SandersDashSealIntegration(self.cases, self.authority, self.dispatch,
                                       self.sidecar, self.cases, CORE_LAWS)
        with self.assertRaises(IntegrationDenied):
            SandersDashSealIntegration(self.cases, Authority(object(), self.audit),
                                       self.dispatch, self.sidecar, self.audit, CORE_LAWS)


if __name__ == '__main__':
    unittest.main()
