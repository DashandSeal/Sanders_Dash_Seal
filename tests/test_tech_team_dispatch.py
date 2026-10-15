import tempfile
import unittest
from pathlib import Path
from core_platform.tech_team_dispatch import TechTeamDispatcher, DispatchDenied
from core_platform.upgrade_sidecar import CORE_LAWS

class Audit:
    def __init__(self): self.records=[]
    def preserve(self, item): self.records.append(item)

class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'dispatch.db'
        self.audit = Audit()
        self.dispatch = TechTeamDispatcher(self.path, CORE_LAWS, self.audit)

    def test_multi_capability_tasks(self):
        self.assertEqual(self.dispatch.submit('task-1','IT_AI_Manager_v15.0',
            'INFRASTRUCTURE_REPAIR','backend','MASTER-6',{}),'QUEUED')
        self.assertEqual(self.dispatch.submit('task-2','AI_Tech_Team',
            'FEATURE_DEVELOPMENT','frontend','MASTER-4',{}),'QUEUED')
        self.assertEqual(self.dispatch.inspect('task-2')['status'],'QUEUED')
        self.assertEqual(self.dispatch.complete_review('task-1',{'result':'tested'},
            {'passed':True}),'REVIEW_READY')
        self.assertEqual(TechTeamDispatcher(self.path, CORE_LAWS, self.audit).inspect('task-1')['status'],
                         'REVIEW_READY')

    def test_no_unverified_completion(self):
        self.dispatch.submit('task-1','AI_Tech_Team','HOT_SWAP_PLAN','frontend','MASTER-8',{})
        with self.assertRaises(DispatchDenied):
            self.dispatch.complete_review('task-1',{}, {'passed':False})
        self.assertEqual(self.dispatch.inspect('task-1')['status'],'QUEUED')

    def test_unknown_capability_and_missing_laws_denied(self):
        with self.assertRaises(DispatchDenied):
            self.dispatch.submit('task-1','AI_Tech_Team','UNRESTRICTED_SHELL','backend','MASTER-8',{})
        with self.assertRaises(Exception):
            TechTeamDispatcher(self.path, CORE_LAWS[:-1], self.audit)

if __name__ == '__main__':
    unittest.main()
