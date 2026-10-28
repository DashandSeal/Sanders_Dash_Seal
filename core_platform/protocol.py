"""MASTER section 9 field structure and canonical signing material.

The signed execution binding supplies the concrete bytes/key/operation referenced
by the MASTER's symbolic signature expressions. It is not a substitute schema.
"""
import copy
import ipaddress
import re
from datetime import datetime, timezone
from .security import Denied, digest

GATES = ('it_manager_operational_necessity_signoff',
         'minotaur_labyrinth_shield_clearance_hash')


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def timestamp(value):
    try:
        if not isinstance(value, str) or not value.endswith('Z'):
            raise ValueError()
        return datetime.fromisoformat(value[:-1] + '+00:00').timestamp()
    except (ValueError, TypeError, OverflowError) as exc:
        raise Denied('UTC timestamp required') from exc


def signing_material(record):
    value = copy.deepcopy(record)
    value['agent_identity']['agent_identity_assertion'] = ''
    value['dual_governance_gates'] = {name: '' for name in GATES}
    return value


def assert_record(record, max_lifetime, now):
    try:
        if set(record) != {'lease_metadata', 'agent_identity', 'operational_bounds',
                           'dual_governance_gates', 'execution_binding'}:
            raise ValueError()
        meta, agent, bounds = (record[k] for k in ('lease_metadata', 'agent_identity', 'operational_bounds'))
        binding = record['execution_binding']
        if set(meta) != {'lease_id', 'timestamp_utc', 'expires_at_utc', 'nonce'}:
            raise ValueError()
        if set(agent) != {'requesting_agent', 'agent_identity_assertion', 'commanding_authority'}:
            raise ValueError()
        if set(bounds) != {'target_endpoint', 'allowed_verbs', 'network_jail_ips', 'max_execution_limit'}:
            raise ValueError()
        if set(binding) != {'agent_public_key', 'payload_hash', 'operation', 'token_class', 'artifact_hash'}:
            raise ValueError()
        if set(record['dual_governance_gates']) != set(GATES):
            raise ValueError()
        if agent['commanding_authority'] != 'IT_AI_Manager_v15.0':
            raise ValueError()
        for value in (meta['lease_id'], meta['nonce'], agent['requesting_agent'],
                      bounds['target_endpoint'], binding['operation']):
            if not isinstance(value, str) or not value or '*' in value:
                raise ValueError()
        if not all(re.fullmatch('[0-9a-f]{64}', binding[k]) for k in ('payload_hash', 'artifact_hash')):
            raise ValueError()
        if not re.fullmatch('[0-9a-f]{64}', binding['agent_public_key']):
            raise ValueError()
        for field in ('allowed_verbs', 'network_jail_ips'):
            values = bounds[field]
            if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
                raise ValueError()
            if len(values) != len(set(values)):
                raise ValueError()
        if any(v not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS') for v in bounds['allowed_verbs']):
            raise ValueError()
        for ip in bounds['network_jail_ips']:
            ipaddress.ip_address(ip)
        if type(bounds['max_execution_limit']) is not int or bounds['max_execution_limit'] != 1:
            raise ValueError()
        issued, expires = timestamp(meta['timestamp_utc']), timestamp(meta['expires_at_utc'])
        limit = max_lifetime[binding['token_class']]
        if not issued <= now < expires or not 0 < expires - issued <= limit:
            raise ValueError()
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise Denied('Invalid lease structure, scope, or lifetime policy') from exc


def check_operation(record, scope, payload):
    bounds, binding = record['operational_bounds'], record['execution_binding']
    if (set(scope) != {'endpoint', 'method', 'ip', 'operation'}
        or scope['endpoint'] != bounds['target_endpoint']
        or scope['method'] not in bounds['allowed_verbs']
        or scope['ip'] not in bounds['network_jail_ips']
        or scope['operation'] != binding['operation']
        or digest(payload) != binding['payload_hash']):
        raise Denied('Operation outside signed scope')
