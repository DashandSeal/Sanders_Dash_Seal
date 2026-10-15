import copy
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core_platform.clearance import ClearanceCoordinator
from core_platform.protocol import GATES, signing_material
from core_platform.security import Denied, ROLES, TwinGate, Vault, digest, public_hex, sign


class Client:
    def __init__(self, callback):
        self.callback = callback

    def approve(self, domain, material, assertion):
        return self.callback(domain, material, assertion)


class ClearanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 1000
        self.keys = {r: Ed25519PrivateKey.generate() for r in ROLES}
        gate = TwinGate({r: public_hex(k.public_key()) for r, k in self.keys.items()})
        self.vault = Vault(Path(self.tmp.name) / 'vault.db', gate,
                           {'STANDARD': 60}, lambda: self.now)
        self.agent = Ed25519PrivateKey.generate()
        self.body = self.vault.request(public_hex(self.agent.public_key()),
            {'endpoint': 'https://service.internal/status', 'allowed_verbs': ['GET'],
             'network_jail_ips': ['10.0.0.1'], 'operation': 'READ_STATUS'},
            b'{}', 60, 'STANDARD', 'IntegrationAgent', digest(b'worker'))
        self.body['agent_identity']['agent_identity_assertion'] = sign(
            self.agent, 'pbd-agent-assertion-v2', signing_material(self.body))
        self.calls = []
        def signer(role):
            def approve(domain, material, assertion):
                self.calls.append(role)
                return sign(self.keys[role], domain, material)
            return Client(approve)
        self.clients = {r: signer(r) for r in ROLES}

    def authorize(self):
        return ClearanceCoordinator(self.vault, self.clients).authorize(self.body)

    def assert_unissued(self):
        self.assertIsNone(self.vault.state(self.body['lease_metadata']['lease_id']))

    def test_two_verified_approvals_mint_without_mutating_request(self):
        original = copy.deepcopy(self.body)
        lease = self.authorize()
        self.assertEqual(self.calls, list(ROLES))
        self.assertEqual(self.body, original)
        self.assertEqual(self.vault.state(lease['lease_metadata']['lease_id']), 'READY')
        self.assertTrue(all(lease['dual_governance_gates'].values()))

    def test_bad_agent_assertion_never_contacts_authorities(self):
        self.body['agent_identity']['agent_identity_assertion'] = ''
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.calls, [])
        self.assert_unissued()

    def test_manager_denial_stops_before_minotaur(self):
        self.clients[ROLES[0]] = Client(lambda *args: '')
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.calls, [])
        self.assert_unissued()

    def test_minotaur_denial_never_mints(self):
        self.clients[ROLES[1]] = Client(lambda *args: '')
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.calls, [ROLES[0]])
        self.assert_unissued()

    def test_outage_is_not_retried_and_error_is_sanitized(self):
        calls = []
        def fail(*args):
            calls.append(1)
            raise TimeoutError('secret transport data')
        self.clients[ROLES[1]] = Client(fail)
        with self.assertRaises(Denied) as caught: self.authorize()
        self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(calls, [1])
        self.assert_unissued()

    def test_modified_scope_signature_is_rejected(self):
        def changed(domain, material, assertion):
            material['operational_bounds']['allowed_verbs'].append('DELETE')
            return sign(self.keys[ROLES[0]], domain, material)
        self.clients[ROLES[0]] = Client(changed)
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.body['operational_bounds']['allowed_verbs'], ['GET'])
        self.assert_unissued()

    def test_expiry_during_clearance_never_mints(self):
        def delayed(domain, material, assertion):
            self.now += 60
            return sign(self.keys[ROLES[1]], domain, material)
        self.clients[ROLES[1]] = Client(delayed)
        with self.assertRaises(Denied): self.authorize()
        self.assert_unissued()

    def test_wrong_authority_key_is_rejected(self):
        self.clients[ROLES[1]] = Client(lambda domain, material, assertion:
            sign(self.keys[ROLES[0]], domain, material))
        with self.assertRaises(Denied): self.authorize()
        self.assert_unissued()

    def test_duplicate_lease_never_requests_more_approvals(self):
        self.authorize()
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.calls, list(ROLES))

    def test_prefilled_approvals_rejected(self):
        self.body['dual_governance_gates'][GATES[0]] = 'prior'
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.calls, [])

    def test_shared_client_rejected(self):
        same = self.clients[ROLES[0]]
        with self.assertRaises(ValueError):
            ClearanceCoordinator(self.vault, {r: same for r in ROLES})
