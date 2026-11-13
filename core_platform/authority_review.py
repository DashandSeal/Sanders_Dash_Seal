"""
Module: core_platform.authority_review
Architectural Layer: Human Notarial Authority Review Bridge
Description: Records verified human review decisions. Never infers consent
from automated payment triggers, AI suggestions, or proxies.
"""

import json
import re
import sqlite3
import time
from .upgrade_sidecar import require_core_laws

class AuthorityDenied(Exception):
    """Custom exception raised when human authority review or verification fails."""
    pass

IDENT = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

SERVICE_PROVIDER = {
    "MOBILE_NOTARY": "Navu",
    "E_NOTARY": "Signwell",
    "RON": "BlueNotary",
    "AUTHORIZED_DOCUMENT_SERVICE": None
}

class AuthorityReview:
    """Human notarial authority review bridge for Sanders Dash & Seal."""

    def __init__(self, db_path, cases, identity_verifier, authority_verifier, provider_verifier, audit, core_laws=None):
        if core_laws is not None:
            require_core_laws(core_laws)
        if not all(callable(x) for x in (identity_verifier, authority_verifier, provider_verifier, audit.preserve)):
            raise AuthorityDenied('Independent verification adapters required')

        self.db_path = str(db_path)
        self.cases = cases
        self.identity_verifier = identity_verifier
        self.authority_verifier = authority_verifier
        self.provider_verifier = provider_verifier
        self.audit = audit

        with sqlite3.connect(self.db_path, timeout=10) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS human_authority_reviews (
                case_id TEXT PRIMARY KEY,
                reviewer TEXT NOT NULL,
                notary_identity TEXT NOT NULL,
                evidence TEXT NOT NULL,
                decision TEXT NOT NULL,
                reviewed_at INTEGER NOT NULL
            );""")

    def review(self, case_id, reviewer, notary_identity, evidence):
        if not all(isinstance(v, str) and IDENT.fullmatch(v) for v in (case_id, reviewer, notary_identity)):
            raise AuthorityDenied('Structured human authority evidence identifiers required')
        if not isinstance(evidence, dict):
            raise AuthorityDenied('Structured human authority evidence dictionary required')

        case = self.cases.get(case_id)
        if case['status'] != 'AWAITING_HUMAN_REVIEW':
            raise AuthorityDenied('Case state does not permit review')

        try:
            valid_identity = self.identity_verifier(reviewer, notary_identity)
            valid_authority = self.authority_verifier(case, notary_identity)
            
            # Case-insensitive provider mapping lookup protection
            service_target = str(case.get('service', '')).upper()
            provider_string = SERVICE_PROVIDER.get(service_target)
            
            valid_provider = self.provider_verifier(case, provider_string)
        except Exception as exc:
            raise AuthorityDenied('External authority verification unavailable') from exc

        if not (valid_identity and valid_authority and valid_provider):
            raise AuthorityDenied('Independent notarial authority checks failed')

        self.audit.preserve({
            'event': 'HUMAN_AUTHORITY_REVIEW',
            'case_id': case_id,
            'reviewer': reviewer,
            'notary_identity': notary_identity,
            'evidence': evidence,
            'decision': 'REVIEW_VERIFIED'
        })

        with sqlite3.connect(self.db_path, timeout=10) as db:
            try:
                db.execute(
                    """INSERT INTO human_authority_reviews (case_id, reviewer, notary_identity, evidence, decision, reviewed_at)
                       VALUES (?, ?, ?, ?, 'REVIEW_VERIFIED', ?);""",
                    (case_id, reviewer, notary_identity, json.dumps(evidence, sort_keys=True), int(time.time()))
                )
            except sqlite3.IntegrityError as exc:
                raise AuthorityDenied('Case authority already reviewed') from exc
            db.commit()

        return {'case_id': case_id, 'status': 'REVIEW_VERIFIED'}
