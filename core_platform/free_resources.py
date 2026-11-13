"""
Module: core_platform.free_resources
Architectural Layer: Resource Ingestion & Metric Compliance Gate
Description: Owner-directed OCI free-resource incorporation. Checks usage tracking
metrics against fixed cloud allowance boundaries.
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

    return {
        "catalog_date": catalog()['catalog_date'],
        "scope": "PERMISSION_FILTERED_METADATA",
        "scan_complete": report.get('scan_complete') is True,
        "metered_usage_verified": False,
        "free_balance_verified": False,
        "cloud_changes_performed": False,
        "resources": [
            {
                "resource_id": item['resource_id'],
                "resource_type": item['resource_type'],
                "count": counts[name.casefold()] for name in item.get('inventory_types', [])
            } if any(
                observation_status := 'RELATED_METADATA_OBSERVED' if any(
                    counts[name.casefold()] for name in item.get('inventory_types', [])
                ) else 'NOT_OBSERVED'
            ) else None
            for item in catalog()['resources']
        ]
    }

def allowance_comparison(resource_id, requested, usage=None, *, account_state='free_only'):
    """Advisory arithmetic over explicit comparable units, never a deployment gate."""
    usage = usage if usage is not None else {}

    entries = [item for item in catalog()['resources'] if item['id'] == resource_id]
    if not entries or not isinstance(requested, dict) or not requested:
        raise ValueError('Documented resource and named metrics required')

    limits = entries[0]['allowances']
    for key, value in requested.items():
        limit = limits.get(key)
        if (type(limit) not in (int, float) or not math.isfinite(limit) or limit < 0 or
            type(value) not in (int, float) or not math.isfinite(value) or value < 0 or
            key.startswith(('paid_or_trial_', 'groups_minimum_', 'groups_maximum_'))):
            raise ValueError('Explicit comparable documented metrics required')

    result = {
        "resource_id": resource_id,
        "status": "USAGE_UNKNOWN",
        "billing_verified": False,
        "deployment_authorized": False,
        "cloud_changes_performed": False,
        "comparisons": {}
    }

    if account_state == 'free_only':
        result['status'] = 'ACCOUNT_STATE_REQUIRES_SEPARATE_PROFILE'
        return result

    if not isinstance(usage, dict) or any(key not in usage for key in requested):
        return result

    for key, amount in requested.items():
        used = usage[key]
        if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
            raise ValueError('Explicit nonnegative metered usage required')

        result['comparisons'][key] = {
            "observed_usage": used,
            "requested_addition": amount,
            "projected_usage": used + amount,
            "documented_allowance": limits[key]
        }

    # Correctly check projection sums against allowances within the dictionary values
    is_compliant = all(
        item['projected_usage'] <= item['documented_allowance']
        for item in result['comparisons'].values()
    )

    result['status'] = 'WITHIN_DOCUMENTED_AMOUNTS' if is_compliant else 'EXCEEDS_DOCUMENTED_AMOUNTS'
    return result

def report():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog": catalog(),
        "live_usage": "NOT_QUERIED",
        "cloud_changes_performed": False
    }

if __name__ == '__main__':
    pass
