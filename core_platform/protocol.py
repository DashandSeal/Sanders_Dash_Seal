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
    value['agent_identity']['identity_assertion'] = ''
    value['dual_governance_gates'] = {name: '' for name in GATES}
    return value

def assert_record(record, max_lifetime=86400, now=None):
    try:
        if not isinstance(record, dict):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        if set(record.keys()) != {
            'lease_metadata', 'agent_identity', 'operational_bounds',
            'dual_governance_gates', 'execution_binding'
        }:
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        meta, agent, bounds, binding = (record[k] for k in (
            'lease_metadata', 'agent_identity', 'operational_bounds', 'execution_binding'
        ))

        if set(meta.keys()) != {'lease_id', 'timestamp_utc', 'expires_at_utc', 'nonce'}:
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if set(agent.keys()) != {'requesting_agent', 'agent_identity_assertion', 'commanding_authority'}:
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if set(bounds.keys()) != {'target_endpoint', 'allowed_verbs', 'network_jail_ip', 'max_memory_mb'}:
            raise ValueError('Lease structure out of compliance with master protocol specifications')
        if set(binding.keys()) != {'agent_public_key', 'payload_hash', 'operation', 'train_gate_profile'}:
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        if set(record['dual_governance_gates'].keys()) != set(GATES):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        if agent['commanding_authority'] != 'IT_AI_Manager_v15.0':
            raise ValueError('Lease structure out of compliance with master protocol specifications')

        for value in [
            meta['lease_id'], meta['nonce'], agent['requesting_agent'],
            bounds['target_endpoint'], binding['operation']
        ]:
            if not isinstance(value, str) or not value or '*' in value:
                raise ValueError('Lease structure out of compliance with master protocol specifications')

        if not HEX_64_RE.fullmatch(binding['payload_hash']) or not HEX_64_RE.fullmatch(binding['agent_public_key']):
            raise ValueError('Lease structure out of compliance with master protocol specifications')

    except Exception as exc:
        if isinstance(exc, ValueError) and 'master protocol specifications' in str(exc):
            raise
        raise ValueError('Lease structure out of compliance with master protocol specifications') from exc

    # Robust IP tracking engine integration Layer verification
    try:
        ipaddress.ip_address(bounds['network_jail_ip'])
    except Exception as exc:
        raise ValueError('Lease structure out of compliance with master protocol specifications') from exc
