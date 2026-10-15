"""Human notarial authority review bridge for Sanders Dash & Seal.

Records verified human review decisions. Never infers commission authority from
Stripe payment, AI recommendations, provider selection or requester statements.
Production identity, commission and provider verification are external adapters.
"""
import json
import re
import sqlite3
import time
from .upgrade_sidecar import require_core_laws

class AuthorityDenied(Exception):
    pass

IDENT = re.compile(r'^[A-Za-z0-9_.-]{1,128}$')
SERVICE_PROVIDER = {'E_NOTARY':'SignWell', 'RON':'BlueNotary',
                    'AUTHORIZED_DOCUMENT_SERVICE':None}

class AuthorityReview:
    def __init__(self, db_path, cases, identity_verifier, authority_verifier,
                 provider_verifier, audit, core_laws):
        require_core_laws(core_laws)
        if not all(callable(x) for x in
                   (identity_verifier,authority_verifier,provider_verifier)):
            raise AuthorityDenied('Independent verification adapters required')
        self.db_path=str(db_path)
        self.cases=cases
        self.identity_verifier=identity_verifier
        self.authority_verifier=authority_verifier
        self.provider_verifier=provider_verifier
        self.audit=audit
        with sqlite3.connect(self.db_path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS human_authority_reviews (
                case_id TEXT PRIMARY KEY, reviewer TEXT NOT NULL,
                notary_identity TEXT NOT NULL, evidence TEXT NOT NULL,
                decision TEXT NOT NULL, reviewed_at INTEGER NOT NULL)''')

    def review(self, case_id, reviewer, notary_identity, evidence):
        if (not all(isinstance(v,str) and IDENT.fullmatch(v)
                    for v in (case_id,reviewer,notary_identity))
                or not isinstance(evidence,dict) or not evidence):
            raise AuthorityDenied('Structured human authority evidence required')
        case=self.cases.get(case_id)
        if case['status']!='AWAITING_HUMAN_AUTHORITY_REVIEW':
            raise AuthorityDenied('Case state does not permit review')
        # Each adapter must independently return the literal True.
        # Provider selection alone never constitutes provider authorization.
        try:
            valid_identity=self.identity_verifier(reviewer,notary_identity,evidence) is True
            valid_authority=self.authority_verifier(case,notary_identity,evidence) is True
            valid_provider=self.provider_verifier(case,SERVICE_PROVIDER[case['service']],evidence) is True
        except Exception as exc:
            raise AuthorityDenied('External authority verification unavailable') from exc
        if not (valid_identity and valid_authority and valid_provider):
            raise AuthorityDenied('Independent notarial authority checks denied')
        self.audit.preserve({'event':'HUMAN_AUTHORITY_REVIEW','case_id':case_id,
                             'reviewer':reviewer,'notary_identity':notary_identity,
                             'evidence':evidence,'decision':'REVIEW_VERIFIED'})
        with sqlite3.connect(self.db_path) as db:
            try:
                db.execute('INSERT INTO human_authority_reviews VALUES (?,?,?,?,?,?)',
                           (case_id,reviewer,notary_identity,json.dumps(evidence,sort_keys=True),
                            'REVIEW_VERIFIED',int(time.time())))
            except sqlite3.IntegrityError as exc:
                raise AuthorityDenied('Case authority already reviewed') from exc
        # Review is evidence of a human decision, not execution of a notarial act.
        return {'case_id':case_id,'status':'REVIEW_VERIFIED','notarial_act_executed':False}
