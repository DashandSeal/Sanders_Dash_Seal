"""Fail-closed state commission registry verification.

Registry URLs and schema adapters must be validated against official sources.
Unknown or unavailable state endpoints never establish authority.
"""
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class CommissionVerificationDenied(ValueError): pass

SUPPORTED={'CO','WI'}
ID=re.compile(r'[A-Za-z0-9-]{1,80}\Z',re.ASCII)

def verify_notary_commission(state_code, commission_id, user_identity, *, registry_adapter=None):
    if not isinstance(state_code,str) or state_code.upper().strip() not in SUPPORTED:
        return False
    state=state_code.upper().strip()
    if not isinstance(commission_id,str) or not ID.fullmatch(commission_id):
        return False
    if not isinstance(user_identity,str) or not user_identity.strip():
        return False
    # No undocumented or speculative government API endpoint is treated as authoritative.
    if registry_adapter is None:
        return False
    try:
        evidence=registry_adapter(state,commission_id,user_identity)
        if not isinstance(evidence,dict) or set(evidence)!={
            'source','state','commission_id','name','status','verified_at','expires_at'}:
            return False
        return (evidence['source'] in ('CO_SOS','WI_DFI')
            and evidence['source']==('CO_SOS' if state=='CO' else 'WI_DFI')
            and evidence['state']==state and evidence['commission_id']==commission_id
            and evidence['name'].casefold().strip()==user_identity.casefold().strip()
            and evidence['status']=='ACTIVE'
            and type(evidence['verified_at']) is int and type(evidence['expires_at']) is int
            and evidence['verified_at']<=evidence['expires_at'])
    except (ValueError,TypeError,KeyError,TimeoutError,OSError):
        return False
