import tempfile
import unittest
from pathlib import Path
from core_platform.upgrade_sidecar import UpgradeSidecar, UpgradeDenied

class UpgradeSidecarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'upgrades.db'
        self.sidecar = UpgradeSidecar(self.path, ['payments', 'notarial', 'security'])
        self.digest = 'a' * 64

    def test_durable_proposal_and_review(self):
        self.assertEqual(self.sidecar.propose('req-1','payments','2.0',self.digest,{'source':'review'}),'PROPOSED')
        self.assertEqual(self.sidecar.evaluate('req-1',{'tests':'pending'}),'EVALUATED')
        reopened = UpgradeSidecar(self.path, ['payments','notarial','security'])
        self.assertEqual(reopened.get('req-1')['state'],'EVALUATED')
        self.assertEqual(reopened.get('req-1')['evidence']['review']['tests'],'pending')

    def test_unknown_component_and_duplicate_rejected(self):
        with self.assertRaises(UpgradeDenied):
            self.sidecar.propose('req-1','unknown','2.0',self.digest,{})
        self.sidecar.propose('req-1','security','2.0',self.digest,{})
        with self.assertRaises(UpgradeDenied):
            self.sidecar.propose('req-1','security','2.0',self.digest,{})

    def test_no_unapproved_execution(self):
        self.sidecar.propose('req-1','notarial','2.0',self.digest,{})
        with self.assertRaises(UpgradeDenied):
            self.sidecar.apply_upgrade('req-1')
        with self.assertRaises(UpgradeDenied):
            self.sidecar.approve_or_deploy('req-1')
        self.assertEqual(self.sidecar.get('req-1')['state'],'PROPOSED')

    def test_block_and_no_evaluation_after_block(self):
        self.sidecar.propose('req-1','security','2.0',self.digest,{})
        self.assertEqual(self.sidecar.block('req-1','unverified source'),'BLOCKED')
        with self.assertRaises(UpgradeDenied):
            self.sidecar.evaluate('req-1',{'tests':'pass'})

if __name__ == '__main__':
    unittest.main()
