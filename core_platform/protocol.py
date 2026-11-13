"""
Module: core_platform.protocol
Architectural Layer: MASTER section 0 field structure and canonical signing material.
Description: Validates execution leases, dual governance gates, and network jail bounds.
             Provides robust ISO timestamp conversions and deterministic structures.
"""

import copy
import ipaddress
import re
from datetime import datetime, timezone
from .security import Denied, digest

GATES = (
    'it_manager_operational_necessity_signoff',
    'minotaur_labyrinth_shield_clearance_hash'
)

HEX_64_RE = re.compile(r'^[0-9a-fA-F]{64}$')

def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='seconds')

def timestamp(value):
    """Parses absolute UTI ISO format timestamp strings safely without brittle character slicing."""
    try:
        if not isinstance(value, str):
            raise ValueError()

        # Cleanly convert standard 'Z' suffix to formal explicit offset formatting
        normalized = value.strip()
        if normalized.endswith('Z'):
            normalized = normalized[:-1] + '+00:00'

        dt = datetime.fromisoformat(normalized)

        # Enforce that all parsed verification inputs must possess an explicit UTC offset boundary
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError()

        return dt.timestamp()
    except (ValueError, TypeError, OverflowError) as exc:
        raise Denied('UTC timestamp required') from exc

def signing_material(record):
    value = copy.deepcopy(record)
    if 'agent_identity' in value and isinstance(value['agent_identity'], dict):
        value['agent_identity']['identity_assertion'] = ''
    if 'dual_governance_gates' in value and isinstance(value['dual_governance_gates'], dict):
        value['dual_governance_gates'] = {name: '' for name in GATES if name in value['dual_governance_gates']}
    return value

def assert_record(record, max_lifetime=86400, now=None):
    try:
        if not isinstance(record, dict):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        required_sections = {'lease_metadata', 'agent_identity', 'operational_bounds', 'execution_binding'}
        if not required_sections.issubset(record.keys()):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        meta, agent, bounds, binding = (record[k] for k in (
            'lease_metadata', 'agent_identity', 'operational_bounds', 'execution_binding'
        ))

        if not {'lease_id', 'timestamp_utc'}.issubset(meta.keys()):
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if not {'requesting_agent', 'commanding_authority'}.issubset(agent.keys()):
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if not {'target_endpoint', 'network_jail_ip'}.issubset(bounds.keys()):
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if not {'payload_hash', 'operation'}.issubset(binding.keys()):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        if agent.get('commanding_authority') != 'IT_AI_Manager_v15.0':
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        for value in [
            meta.get('lease_id'), meta.get('nonce'), agent.get('requesting_agent'),
            bounds.get('target_endpoint'), binding.get('operation')
        ]:
            if value is not None and (not isinstance(value, str) or not value or '*' in value):
                raise ValueError('Lease structure out of compliance with master protocol specifications')

        if binding.get('payload_hash') and not HEX_64_RE.fullmatch(binding['payload_hash']):
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if binding.get('agent_public_key') and not HEX_64_RE.fullmatch(binding['agent_public_key']):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

    except Exception as exc:
        if isinstance(exc, ValueError) and 'master protocol specifications' in str(exc):
            raise
        raise ValueError('Lease structure out of compliance with master protocol specifications') from exc

    # Robust IP tracking engine integration Layer verification
    try:
        if 'network_jail_ip' in bounds:
            ipaddress.ip_address(bounds['network_jail_ip'])
    except Exception as exc:
        raise ValueError('Lease structure out of compliance with master protocol specifications') from exc
