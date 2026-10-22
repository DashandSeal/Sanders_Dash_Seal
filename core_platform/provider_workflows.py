"""Human-directed, case-bound provider requests; never a notarial execution grant.

Only fingerprints and provider references are persisted. An uncertain POST is
never retried automatically: neither provider documents an idempotency guarantee.
"""
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime
from .provider_connections import ProviderConnectionError


class ProviderUnavailable(Exception):
    pass


class ProviderRequestConflict(Exception):
    pass


def text(value, maximum=160):
    if (not isinstance(value, str) or not 1 <= len(value) <= maximum
            or value != value.strip() or any(ord(c) < 32 for c in value)):
        raise ValueError('Invalid provider request field')
    return value


def identifier(value):
    value = text(value, 128)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid provider resource identifier')
    return value


def email(value):
    value = text(value, 254)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Invalid recipient email')
    return value


def prepare(provider, data, case_id, *, signwell_test_mode=False):
    if not isinstance(data, dict):
        raise ValueError('Request object required')
    request_id = identifier(data.get('request_id'))
    if provider == 'signwell':
        if set(data) != {'request_id', 'template_id', 'name', 'recipients'}:
            raise ValueError('Invalid SignWell fields')
        recipients = data['recipients']
        if not isinstance(recipients, list) or not 1 <= len(recipients) <= 20:
            raise ValueError('Recipients required')
        normalized = []
        for recipient in recipients:
            if not isinstance(recipient, dict) or set(recipient) != {'id', 'placeholder_name', 'name', 'email'}:
                raise ValueError('Invalid SignWell recipient')
            normalized.append({'id': identifier(recipient['id']),
                'placeholder_name': text(recipient['placeholder_name']),
                'name': text(recipient['name']), 'email': email(recipient['email'])})
        if len({r['id'] for r in normalized}) != len(normalized):
            raise ValueError('Duplicate recipient identifier')
        if len({r['placeholder_name'] for r in normalized}) != len(normalized):
            raise ValueError('Duplicate template placeholder')
        payload = {'template_id': identifier(data['template_id']), 'name': text(data['name']),
            'recipients': normalized, 'draft': False, 'test_mode': signwell_test_mode,
            'metadata': {'sds_case_id': case_id, 'sds_request_id': request_id}}
    elif provider == 'bluenotary':
        required = {'request_id', 'document_templates', 'all_signers', 'session_notary_email',
                    'notarization_timing_type'}
        if set(data) not in (required, required | {'session_timing'}):
            raise ValueError('Invalid BlueNotary fields')
        templates = data['document_templates']; signers = data['all_signers']
        if not isinstance(templates, list) or not 1 <= len(templates) <= 20:
            raise ValueError('Provider templates required')
        if not isinstance(signers, list) or not 1 <= len(signers) <= 20:
            raise ValueError('Signers required')
        normalized = []
        for signer in signers:
            if not isinstance(signer, dict) or set(signer) != {'first_name', 'last_name', 'email'}:
                raise ValueError('Invalid BlueNotary signer')
            normalized.append({'first_name': text(signer['first_name'], 50),
                'last_name': text(signer['last_name'], 50), 'email': email(signer['email'])})
        timing = data['notarization_timing_type']
        if timing not in ('notarize_now', 'notarize_later'):
            raise ValueError('Invalid session timing')
        payload = {'signing_type': 'ron', 'session_type': 'gnw',
            'notarization_id': hashlib.sha256((case_id + ':' + request_id).encode()).hexdigest(),
            'document_templates': [identifier(t) for t in templates], 'all_signers': normalized,
            'session_notary_email': email(data['session_notary_email']),
            'notarization_timing_type': timing}
        if timing == 'notarize_later':
            scheduled = text(data.get('session_timing'), 50)
            parsed = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
            if parsed.tzinfo is None or parsed.timestamp() <= time.time():
                raise ValueError('Future timezone-aware session time required')
            payload['session_timing'] = scheduled
        elif 'session_timing' in data:
            raise ValueError('Unexpected session time')
    else:
        raise ValueError('Unsupported provider')
    return request_id, payload


class ProviderWorkflows:
    def __init__(self, path, cases, operator, audit, clients, *, signwell_test_mode=False):
        self.path, self.cases, self.operator, self.audit, self.clients = str(path), cases, operator, audit, clients
        self.signwell_test_mode = signwell_test_mode
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS provider_requests (
                case_id TEXT NOT NULL, provider TEXT NOT NULL, request_id TEXT NOT NULL,
                actor TEXT NOT NULL, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
                resource_id TEXT, created_at INTEGER NOT NULL,
                PRIMARY KEY(case_id,provider,request_id))''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10); db.row_factory = sqlite3.Row
        return db

    def authorize(self, case_id, actor):
        if self.operator(actor) is not True:
            raise PermissionError('Operator required')
        self.cases.get(case_id)

    def records(self, case_id, actor):
        self.authorize(case_id, actor)
        with self.connect() as db:
            return [dict(row) for row in db.execute('''SELECT provider,request_id,state,resource_id
                FROM provider_requests WHERE case_id=? ORDER BY created_at DESC,rowid DESC LIMIT 100''', (case_id,))]

    def submit(self, case_id, actor, provider, data):
        self.authorize(case_id, actor)
        request_id, payload = prepare(provider, data, case_id, signwell_test_mode=self.signwell_test_mode)
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                               allow_nan=False).encode()).hexdigest()
        client = self.clients.get(provider)
        if client is None:
            raise ProviderUnavailable(provider + '_credentials_not_configured')
        key = (case_id, provider, request_id)
        self.audit.preserve({'stage': 'HUMAN_PROVIDER_REQUEST', 'case_id': case_id,
            'provider': provider, 'request_id': request_id, 'actor': actor, 'sha256': fingerprint})
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM provider_requests WHERE case_id=? AND provider=? AND request_id=?', key).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint or previous['state'] != 'CREATED':
                    raise ProviderRequestConflict('Request reused or outcome requires provider reconciliation')
                return self.receipt(previous)
            db.execute('INSERT INTO provider_requests VALUES (?,?,?,?,?,?,?,?)',
                       (*key, actor, fingerprint, 'SUBMITTING', None, int(time.time())))
        try:
            result = client.create_request(payload)
            resource = identifier(result.get('id') if provider == 'signwell' else result.get('bn_session_id'))
            if provider == 'bluenotary' and result.get('response') != 'Pass':
                raise ProviderConnectionError('Provider did not accept session')
        except Exception:
            with self.connect() as db:
                db.execute('UPDATE provider_requests SET state=? WHERE case_id=? AND provider=? AND request_id=?',
                           ('OUTCOME_UNKNOWN', *key))
            self.audit.preserve({'stage': 'PROVIDER_OUTCOME_UNKNOWN', 'case_id': case_id,
                                 'provider': provider, 'request_id': request_id})
            raise ProviderUnavailable('Provider outcome unknown; inspect provider before creating another request') from None
        with self.connect() as db:
            db.execute('UPDATE provider_requests SET state=?,resource_id=? WHERE case_id=? AND provider=? AND request_id=?',
                       ('CREATED', resource, *key))
        self.audit.preserve({'stage': 'PROVIDER_REQUEST_CREATED', 'case_id': case_id,
            'provider': provider, 'request_id': request_id, 'resource_id': resource})
        return self.receipt({'provider': provider, 'request_id': request_id, 'state': 'CREATED', 'resource_id': resource})

    @staticmethod
    def receipt(record):
        return {**{k: record[k] for k in ('provider', 'request_id', 'state', 'resource_id')},
                'notarial_act_executed': False}
