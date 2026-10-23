import unittest
from backend.commission_sync import verify_notary_commission

class CommissionSyncTests(unittest.TestCase):
    def test_unconfigured_registry_denied(self):
        self.assertFalse(verify_notary_commission('CO','123','Example Notary'))
        self.assertFalse(verify_notary_commission('WI','123','Example Notary'))
        self.assertFalse(verify_notary_commission('XX','123','Example Notary'))

    def test_structured_verified_registry_evidence(self):
        def adapter(state,commission_id,name):
            return {'source':'CO_SOS','state':state,'commission_id':commission_id,
                'name':name,'status':'ACTIVE','verified_at':100,'expires_at':200}
        self.assertTrue(verify_notary_commission('CO','123','Example Notary',registry_adapter=adapter))
        self.assertFalse(verify_notary_commission('WI','123','Example Notary',registry_adapter=adapter))

    def test_inactive_and_missing_evidence_denied(self):
        self.assertFalse(verify_notary_commission('CO','123','Example Notary',
            registry_adapter=lambda *args:{'status':'ACTIVE'}))
        self.assertFalse(verify_notary_commission('CO','123','Example Notary',
            registry_adapter=lambda *args: (_ for _ in ()).throw(OSError('offline'))))
