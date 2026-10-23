import unittest
from core_platform.hotswap import Workload, UpgradePlan, GovernedHotSwap, HotSwapDenied
from core_platform.upgrade_sidecar import CORE_LAWS

IMAGE_A = 'repo/frontend@sha256:' + 'a' * 64
IMAGE_B = 'repo/frontend@sha256:' + 'b' * 64

class FakeDeployment:
    def __init__(self, unhealthy=None):
        self.started = []
        self.stopped = []
        self.unhealthy = unhealthy
    def start_candidate(self, w): self.started.append(w.name)
    def healthy(self, w): return w.name != self.unhealthy
    def stop_candidate(self, w): self.stopped.append(w.name)

class FakeRouting:
    def __init__(self): self.switched=[]; self.rolled=[]
    def cutover(self, w): self.switched.append(w.name)
    def verified(self, w): return True
    def rollback(self, w): self.rolled.append(w.name)

class FakeAudit:
    def __init__(self): self.events=[]
    def preserve(self, record): self.events.append(record)

class HotSwapTests(unittest.TestCase):
    def plan(self):
        frontend = Workload('frontend', 'frontend', IMAGE_A, IMAGE_B, ('backend',))
        backend = Workload('backend', 'backend', IMAGE_A, IMAGE_B)
        return UpgradePlan('release-1', (frontend, backend),
                           {'inventor':'Roosevelt Sanders',
                            'intended_owner':'Sanders Legal Helpers LLC',
                            'confidentiality':'restricted',
                            'source_commit':'commit-reference',
                            'design_reference':'MASTER-2026-10-11'})

    def test_dependency_order_and_fingerprint(self):
        self.assertEqual([w.name for w in self.plan().ordered()], ['backend','frontend'])
        self.assertEqual(self.plan().fingerprint(), self.plan().fingerprint())

    def test_successful_cutover(self):
        deploy, route, audit = FakeDeployment(), FakeRouting(), FakeAudit()
        engine = GovernedHotSwap(deploy, route, audit, lambda p, h: True, CORE_LAWS)
        self.assertEqual(engine.run(self.plan()), 'LIVE_VERIFIED')
        self.assertEqual(route.switched, ['backend','frontend'])
        self.assertEqual(audit.events[-1]['stage'], 'UPGRADE_VERIFIED')

    def test_failed_frontend_health_rolls_back_backend(self):
        deploy, route, audit = FakeDeployment('frontend'), FakeRouting(), FakeAudit()
        engine = GovernedHotSwap(deploy, route, audit, lambda p, h: True, CORE_LAWS)
        with self.assertRaises(HotSwapDenied):
            engine.run(self.plan())
        self.assertEqual(route.rolled, ['backend'])
        self.assertEqual(deploy.stopped, ['frontend','backend'])
        self.assertEqual(audit.events[-1]['stage'], 'UPGRADE_SHELTER')

    def test_authority_denial_no_execution(self):
        deploy, route, audit = FakeDeployment(), FakeRouting(), FakeAudit()
        engine = GovernedHotSwap(deploy, route, audit, lambda p, h: False, CORE_LAWS)
        with self.assertRaises(HotSwapDenied):
            engine.run(self.plan())
        self.assertEqual(deploy.started, [])

    def test_cycle_and_missing_provenance_rejected(self):
        p = self.plan()
        with self.assertRaises(HotSwapDenied):
            UpgradePlan('r', (Workload('a','backend',IMAGE_A,IMAGE_B,('b',)),
                              Workload('b','frontend',IMAGE_A,IMAGE_B,('a',))), p.invention_record).ordered()
        with self.assertRaises(HotSwapDenied):
            UpgradePlan('r', p.workloads, {}).ordered()

if __name__ == '__main__':
    unittest.main()
