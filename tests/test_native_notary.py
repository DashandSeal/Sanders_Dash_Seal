import tempfile
import unittest
import time
import json
from pathlib import Path

from core_platform.native_notary import NativeNotarySessions, NativeNotaryDenied
from core_platform.native_authority import NativeAuthority
from core_platform.native_evidence import NativeEvidenceIndex
from core_platform.native_ron_rooms import NativeRonRooms


class NativeNotaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "native.db"
        self.sessions = NativeNotarySessions(self.path)

    def test_enotary_persists_and_cancels(self):
        created = self.sessions.create("session-1", "case-1", "E_NOTARY", "CO")
        self.assertEqual(created["state"], "AWAITING_AUTHORITY")
        restored = NativeNotarySessions(self.path).get("session-1")
        self.assertEqual(restored["case_id"], "case-1")
        self.assertEqual(self.sessions.cancel("session-1")["state"], "CANCELLED")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.cancel("session-1")

    def test_ron_is_separate_and_duplicate_denied(self):
        self.sessions.create("session-2", "case-2", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-2", "case-3", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-3", "case-3", "MOBILE_NOTARY", "WI")

    def test_no_unverified_completion(self):
        self.sessions.create("session-4", "case-4", "RON", "WI")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete("session-4", human_attestation=True,
                                   authority_evidence=True, identity_evidence=True,
                                   act_evidence=True)
        self.assertEqual(self.sessions.get("session-4")["state"], "AWAITING_AUTHORITY")

    def register_authorities(self, session_id, *, ron=False):
        authority = NativeAuthority(self.path)
        kinds = ('IDENTITY','COMMISSION','JURISDICTION','METHOD','HUMAN_ATTESTATION','ACT_EXECUTION')
        if ron:
            kinds += ('RON_PROVIDER_AUTHORIZATION',)
        now = int(time.time())
        for kind in kinds:
            authority.register(session_id,kind,'proof-'+kind,'trusted-verifier',now,now+3600,
                               trusted_verifier=lambda *arguments: True)
        return {
            'human_attestation': {'verified':True,'evidence_id':'proof-HUMAN_ATTESTATION'},
            'authority_evidence': {'verified':True,'evidence_id':'proof-COMMISSION'},
            'identity_evidence': {'verified':True,'evidence_id':'proof-IDENTITY'},
            'act_evidence': {'verified':True,'evidence_id':'proof-ACT_EXECUTION'}
        }

    def test_unregistered_verified_flags_cannot_complete(self):
        self.sessions.create('session-asserted','case-asserted','E_NOTARY','CO')
        claimed = {key:{'verified':True,'evidence_id':'claimed'} for key in
                   ('human_attestation','authority_evidence','identity_evidence','act_evidence')}
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('session-asserted',**claimed)
        self.assertEqual(self.sessions.get('session-asserted')['state'],'AWAITING_AUTHORITY')

    def test_enotary_completion_is_bound_to_independent_authority_evidence(self):
        self.sessions.create('enotary-complete','case-complete','E_NOTARY','CO')
        claimed=self.register_authorities('enotary-complete')
        wrong=dict(claimed, identity_evidence={'verified':True,'evidence_id':'other-session'})
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('enotary-complete',**wrong)
        self.assertEqual(self.sessions.get('enotary-complete')['state'],'AWAITING_AUTHORITY')
        completed=self.sessions.complete('enotary-complete',**claimed)
        self.assertEqual(completed['state'],'COMPLETED')
        self.assertEqual(json.loads(completed['evidence_json'])['act_evidence'],claimed['act_evidence'])
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('enotary-complete',**claimed)

    def test_ron_completion_requires_room_consent_recording_and_matching_index(self):
        self.sessions.create('ron-complete','ron-case','RON','WI')
        claimed=self.register_authorities('ron-complete',ron=True)
        evidence=NativeEvidenceIndex(self.path)
        rooms=NativeRonRooms(self.path)
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('ron-complete',**claimed)
        rooms.create('ron-complete','room-complete')
        rooms.consent('ron-complete','a'*64)
        rooms.recording('ron-complete','b'*64)
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('ron-complete',**claimed)
        evidence.register('ron-complete','consent-1','CONSENT','a'*64)
        evidence.register('ron-complete','recording-wrong','AV_RECORDING','c'*64)
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.complete('ron-complete',**claimed)
        evidence.register('ron-complete','recording-1','AV_RECORDING','b'*64)
        self.assertEqual(self.sessions.complete('ron-complete',**claimed)['state'],'COMPLETED')

    def test_case_registry_binding_when_shared_database(self):
        from core_platform.cases import CaseRegistry
        from core_platform.upgrade_sidecar import CORE_LAWS
        cases = CaseRegistry(self.path, CORE_LAWS)
        cases.create("case-6", "CO", "E_NOTARY", "requester-6")
        self.sessions.create("session-6", "case-6", "E_NOTARY", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-7", "case-6", "RON", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-8", "missing-case", "E_NOTARY", "CO")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("session-9", "case-6", "E_NOTARY", "WI")

    def test_unknown_session_and_invalid_identity_denied(self):
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.get("missing")
        with self.assertRaises(NativeNotaryDenied):
            self.sessions.create("", "case-5", "RON", "WI")


if __name__ == "__main__":
    unittest.main()
