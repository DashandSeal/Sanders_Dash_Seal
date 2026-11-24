"""
Module: core_platform.authority_verifiers
Architectural Layer: Independent Verifier Adapters for Human Authority Review
Description: The three verifier adapters core_platform.authority_review
requires before it will record a REVIEW_VERIFIED decision. Each adapter
verifies only from evidence the platform itself holds, and each returns
False when it cannot verify; none of them manufactures evidence.

- Identity: the platform's own account records (SessionAuth). The
  reviewer must hold an OPERATOR account and the notary identity must
  be a registered OPERATOR account: in this platform the notary is
  staff, and an identity the platform has never issued is not verified.
- Notarial authority: the fail-closed commission verification contract
  in backend/commission_sync.py, fed with the notary's recorded
  commission (state, commission id, legal name). That contract returns
  False until a registry_adapter validated against an official source
  is injected. No such adapter exists in this repository: the official
  Colorado Secretary of State (CO_SOS) and Wisconsin Department of
  Financial Institutions (WI_DFI) commission sources must be confirmed
  and supplied by the owner, as recorded in docs/SPEC_CONFORMANCE.md.
  Until then this adapter verifies nothing, by design.
- Provider: the provider clients the owner has configured (the same
  client set deploy/production_bindings.py builds from the owner's
  keys). A mapped provider with no configured client is not verified.
  Navu has no client anywhere in this repository, so MOBILE_NOTARY
  provider verification cannot pass until a Navu integration exists.
  A service mapped to no provider (AUTHORIZED_DOCUMENT_SERVICE) has
  no external dependency to verify and passes this check on that
  basis alone; the identity and authority checks still apply.
"""

try:
    from backend.commission_sync import verify_notary_commission
except Exception:  # pragma: no cover - import context without repo root
    verify_notary_commission = None

from .authority_review import AuthorityReview

PROVIDER_CLIENT_KEYS = {
    'Signwell': 'signwell',
    'BlueNotary': 'bluenotary',
    'Navu': None,
}


class SessionIdentityVerifier:
    """Identity verification against the platform's own account records."""

    def __init__(self, auth):
        self.auth = auth

    def __call__(self, reviewer, notary_identity):
        try:
            return (self.auth.operator_verifier(reviewer) is True
                    and self.auth.operator_verifier(notary_identity) is True)
        except Exception:
            return False


class CommissionAuthorityVerifier:
    """Notarial-authority verification through backend/commission_sync.

    ``commission_records`` maps a notary identity to the commission on
    record for it: {'state', 'commission_id', 'legal_name'}. The
    record's state must equal the case's jurisdiction. Verification
    itself is delegated to the fail-closed contract; without an
    injected official-source ``registry_adapter`` it returns False.
    """

    def __init__(self, commission_records=None, registry_adapter=None):
        self.commission_records = dict(commission_records or {})
        self.registry_adapter = registry_adapter

    def __call__(self, case, notary_identity):
        if verify_notary_commission is None:
            return False
        try:
            record = self.commission_records.get(notary_identity)
            if not isinstance(record, dict):
                return False
            state = str(case.get('jurisdiction', '')).upper().strip()
            if str(record.get('state', '')).upper().strip() != state:
                return False
            return verify_notary_commission(
                state, record.get('commission_id'),
                record.get('legal_name'),
                registry_adapter=self.registry_adapter) is True
        except Exception:
            return False


class ConfiguredProviderVerifier:
    """Provider verification from the owner's configured client set."""

    def __init__(self, clients=None):
        self.clients = dict(clients or {})

    def __call__(self, case, provider):
        if provider is None:
            return True
        if provider not in PROVIDER_CLIENT_KEYS:
            return False
        key = PROVIDER_CLIENT_KEYS[provider]
        if key is None:
            return False
        return self.clients.get(key) is not None


def create_authority_review(db_path, cases, auth, audit, *,
                            commission_records=None, registry_adapter=None,
                            provider_clients=None, core_laws=None):
    """Compose AuthorityReview with the platform's own verifier adapters."""
    return AuthorityReview(
        db_path, cases,
        SessionIdentityVerifier(auth),
        CommissionAuthorityVerifier(commission_records, registry_adapter),
        ConfiguredProviderVerifier(provider_clients),
        audit, core_laws)
