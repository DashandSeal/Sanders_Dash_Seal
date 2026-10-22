"""Owner-directed OCI free-resource incorporation, without provisioning or spending.

The catalog describes documented allowances. Inventory counts are not billing
meters. This module never adds a deployment gate or grants business authority.
"""
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path


CATALOG = Path(__file__).with_name('oci_free_resources.json')


def catalog():
    value = json.loads(CATALOG.read_text())
    if value.get('platform') != 'Sanders Dash & Seal' or value.get('schema') != 1:
        raise ValueError('Unexpected resource catalog identity')
    return value


def inventory_mapping(report):
    counts = Counter()
    for item in report.get('resources', []):
        if isinstance(item, dict) and isinstance(item.get('resource_type'), str):
            counts[item['resource_type'].casefold()] += 1
    return {'catalog_date': catalog()['catalog_date'],
        'scope': 'PERMISSION_FILTERED_METADATA',
        'scan_complete': report.get('scan_complete') is True,
        'metered_usage_verified': False, 'free_balance_verified': False,
        'cloud_changes_performed': False,
        'resources': [{'id': item['id'], 'related_observations': sum(
            counts[name.casefold()] for name in item['inventory_types']),
            'observation_status': ('RELATED_METADATA_OBSERVED' if any(
                counts[name.casefold()] for name in item['inventory_types']) else 'NOT_OBSERVED'),
            'usage_status': 'NOT_METERED_BY_RESOURCE_SEARCH'} for item in catalog()['resources']]}


def allowance_comparison(resource_id, requested, usage=None, *, account_state='free_only'):
    """Advisory arithmetic over explicit comparable units, never a deployment gate.

    usage must contain every requested metric; absent observation stays unknown.
    Unknown/non-numeric/conditional metrics are rejected instead of treated as zero.
    A comparison is not evidence of actual account eligibility or zero billing.
    """
    entries = {item['id']: item for item in catalog()['resources']}
    if resource_id not in entries or not isinstance(requested, dict) or not requested:
        raise ValueError('Documented resource and named metrics required')
    limits = entries[resource_id]['allowances']
    for key, value in requested.items():
        limit = limits.get(key)
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or type(limit) not in (int, float) or not math.isfinite(limit)
                or key.startswith(('paid_or_trial_', 'groups_minimum_', 'groups_maximum_'))):
            raise ValueError('Explicit comparable documented metrics required')
    result = {'resource_id': resource_id, 'status': 'USAGE_UNKNOWN',
        'billing_verified': False, 'deployment_authorized': False,
        'cloud_changes_performed': False, 'comparisons': {}}
    if account_state != 'free_only':
        result['status'] = 'ACCOUNT_STATE_REQUIRES_SEPARATE_PROFILE'
        return result
    if not isinstance(usage, dict) or any(key not in usage for key in requested):
        return result
    for key, amount in requested.items():
        used = usage[key]
        if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
            raise ValueError('Explicit nonnegative metered usage required')
        result['comparisons'][key] = {'observed_usage': used, 'requested_addition': amount,
            'projected_usage': used + amount, 'documented_allowance': limits[key],
            'within_documented_amount': used + amount <= limits[key]}
    result['status'] = ('WITHIN_DOCUMENTED_AMOUNTS' if all(
        item['within_documented_amount'] for item in result['comparisons'].values())
        else 'EXCEEDS_DOCUMENTED_AMOUNTS')
    return result


def report():
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'catalog': catalog(),
            'live_usage': 'NOT_QUERIED', 'cloud_changes_performed': False}


if __name__ == '__main__':
    print(json.dumps(report(), indent=2))
