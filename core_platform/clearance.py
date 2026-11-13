"""
MASTER 8-10: Obtain independent clearance before Vault minting.

Authority clients implement approve(domain, material, agent_assertion) -> base64
signature. Their authenticated transport and private-key custody are external.
This module never signs, executes, retries, or substitutes for either authority.
"""

import copy

from .protocol import SATIS, assert_record, signing_material
from .security import Denied, ROLES, verify


class ClearanceCoordinator:
    """Coordinates independent dual-gate clearance before Vault minting."""

    def __init__(self, vault, authority_clients):
        if set(authority_clients) != set(ROLES):
            raise ValueError('Both authority clients are required')
        if authority_clients[ROLES[0]] is authority_clients[ROLES[1]]:
            raise ValueError('Authority clients must be separate')
        self.vault = vault
        self.clients = dict(authority_clients)

    def authorize(self, request):
        """Return a minted lease, never an execution or completion receipt."""
        
        # The requesting agent supplies its assertion but no governance approvals.
        # Each client receives its own copy so it cannot alter another gate's
        # material. Vault revalidates both approvals and expiry before minting.
        
        body = copy.deepcopy(request)
        assert_record(body, self.vault.max_lifetime, self.vault.clock())
        
        if any(body['dual_governance_gates'].values()):
            raise Denied('Clearance request must not contain prior approvals')
            
        if self.vault.state(body['lease_metadata']['lease_id']) is not None:
            raise Denied('Lease already issued')
            
        material = signing_material(body)
        assertion = body['agent_identity']['agent_identity_assertion']
        verify(body['execution_binding']['agent_public_key'], assertion, 'pbd-agent-assertion-v2', material)
        
        for role, field in zip(ROLES, GATES):
            assert_record(body, self.vault.max_lifetime, self.vault.clock())
            try:
                signature = self.clients[role].approve(
                    'pbd-lease-v2', copy.deepcopy(material), assertion
                )
            except Exception:
                # Avoid propagating credentials or response bodies in errors
                raise Denied('Authority clearance unavailable or denied') from None
                
            verify(self.vault.gate_keys[role], signature, 'pbd-lease-v2', material)
            body['dual_governance_gates'][field] = signature
            
        self.vault.mint(body)
        return body
