"""Scheduled, read-only OCI Search inventory for Sanders Dash & Seal."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core_platform.free_resources import inventory_mapping


CONFIG = Path('/etc/sanders-dash-seal/inventory.json')
STATE = Path('/var/lib/sanders-dash-seal/oci-inventory')
REGION = re.compile(r'[a-z]{2,}-[a-z0-9-]+-[0-9]+')
IDENTITY = re.compile(r'ocid1\.[a-z0-9]+\.oc1\.[a-z0-9-]*\.[A-Za-z0-9]{40,}')


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {
            'schema', 'tenancy_id', 'compartment_id', 'home_region', 'expected'} or config['schema'] != 1:
        raise ValueError('Invalid inventory configuration schema')
    for key in ('tenancy_id', 'compartment_id'):
        value = config[key]
        if not isinstance(value, str) or not IDENTITY.fullmatch(value):
            raise ValueError('Actual OCI identities required')
        kind = value.split('.')[1]
        if kind not in (('tenancy',) if key == 'tenancy_id' else ('tenancy', 'compartment')):
            raise ValueError('Unexpected identity type')
    if config['compartment_id'].startswith('ocid1.tenancy.') and config['compartment_id'] != config['tenancy_id']:
        raise ValueError('Root scope must match tenancy')
    if not isinstance(config['home_region'], str) or not REGION.fullmatch(config['home_region']):
        raise ValueError('Actual home region required')
    if not isinstance(config['expected'], list) or not 1 <= len(config['expected']) <= 200:
        raise ValueError('Configure between one and 200 expected resource identities')
    seen = set()
    for item in config['expected']:
        if not isinstance(item, dict) or set(item) != {'identifier', 'resource_type', 'region', 'compartment_id', 'allowed_states'}:
            raise ValueError('Invalid expected-resource schema')
        for field in ('identifier', 'compartment_id'):
            if not isinstance(item[field], str) or not IDENTITY.fullmatch(item[field]):
                raise ValueError('Expected-resource identity is incomplete')
        if not isinstance(item['resource_type'], str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,99}', item['resource_type']):
            raise ValueError('Invalid resource type')
        if not isinstance(item['region'], str) or not REGION.fullmatch(item['region']):
            raise ValueError('Invalid resource region')
        states = item['allowed_states']
        if not isinstance(states, list) or not states or not all(isinstance(s, str) and re.fullmatch('[A-Z_]{1,40}', s) for s in states):
            raise ValueError('Explicit expected lifecycle states required')
        key = (item['region'], item['identifier'])
        if key in seen:
            raise ValueError('Duplicate expected identity')
        seen.add(key)
    return config


def load_config(path):
    info = path.stat()
    if path.is_symlink() or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_size > 262144:
        raise ValueError('Inventory configuration must be owner-controlled, private and bounded')
    return validate_config(json.loads(path.read_text()))


class ReadOnlyOCI:
    """Fixed command families; no supplied shell, endpoint, profile or write action."""
    def __init__(self, runner=subprocess.run):
        self.runner = runner
        self.deadline = time.monotonic() + 300
        self.calls = 0

    def get(self, args, region):
        remaining = self.deadline - time.monotonic()
        if remaining < 1 or self.calls >= 200:
            raise ValueError('Inventory request/time budget exceeded')
        self.calls += 1
        command = ['oci', *args, '--region', region, '--auth', 'instance_principal',
                   '--output', 'json', '--connection-timeout', '5', '--read-timeout', '20', '--max-retries', '1']
        response = self.runner(command, capture_output=True, text=True, check=True, timeout=min(45, remaining))
        if len(response.stdout) > 8 * 1024 * 1024:
            raise ValueError('OCI response too large')
        body = json.loads(response.stdout)
        if not isinstance(body, dict) or 'data' not in body:
            raise ValueError('Malformed OCI response')
        return body


def data_list(response):
    value = response['data']
    if not isinstance(value, list) or len(value) > 20000 or not all(isinstance(item, dict) for item in value):
        raise ValueError('Malformed OCI list')
    return value


def normalize(item, region, compartment):
    result = {'region': region, 'identifier': item['identifier'],
              'compartment_id': item['compartment-id'], 'resource_type': item['resource-type'],
              'display_name': item.get('display-name'), 'lifecycle_state': item.get('lifecycle-state'),
              'availability_domain': item.get('availability-domain')}
    if not isinstance(result['identifier'], str) or not IDENTITY.fullmatch(result['identifier']):
        raise ValueError('Malformed discovered resource identifier')
    if result['compartment_id'] != compartment:
        raise ValueError('OCI query returned an out-of-scope resource')
    if not isinstance(result['resource_type'], str):
        raise ValueError('Malformed discovered resource type')
    # No tags, payloads, credentials or service-specific private fields are retained.
    if any(value is not None and (not isinstance(value, str) or len(value) > 2048) for value in result.values()):
        raise ValueError('Malformed resource metadata')
    return result


def collect(config, *, api=None):
    validate_config(config)
    api = api or ReadOnlyOCI()
    report = {'schema': 1, 'platform': 'Sanders Dash & Seal',
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'scope_sha256': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
              'visibility': 'PERMISSION_FILTERED_SEARCH_INDEX', 'full_tenancy_visibility_verified': False,
              'production_ready': False, 'billing_verified': False,
              'scan_complete': False, 'regions': [], 'compartments': [], 'resources': [], 'errors': []}
    home = config['home_region']
    def error(phase, region=None, compartment=None):
        report['errors'].append({'phase': phase, 'region': region, 'compartment_id': compartment,
                                 'reason': 'QUERY_FAILED_OR_INVALID_RESPONSE'})
    try:
        subscriptions = data_list(api.get(['iam', 'region-subscription', 'list',
            '--tenancy-id', config['tenancy_id'], '--all'], home))
        if not subscriptions or any(item.get('status') != 'READY' for item in subscriptions):
            raise ValueError('Region subscription not ready')
        regions = sorted({item['region-name'] for item in subscriptions})
        if len(regions) > 50 or not all(isinstance(r, str) and REGION.fullmatch(r) for r in regions):
            raise ValueError('Invalid subscribed regions')
        if home not in regions:
            raise ValueError('Configured home region not subscribed')
        report['regions'] = regions
        children = data_list(api.get(['iam', 'compartment', 'list', '--compartment-id', config['tenancy_id'],
            '--compartment-id-in-subtree', 'true', '--access-level', 'ANY', '--all'], home))
        parents = {item['id']: item['compartment-id'] for item in children if item.get('lifecycle-state') == 'ACTIVE'}
        if any(not IDENTITY.fullmatch(k) or not IDENTITY.fullmatch(v) for k, v in parents.items()):
            raise ValueError('Invalid compartment hierarchy')
        scope = config['compartment_id']
        if scope != config['tenancy_id'] and scope not in parents:
            raise ValueError('Selected compartment not observable')
        compartments = {scope}
        for identifier in parents:
            current, visited = identifier, set()
            while current != config['tenancy_id']:
                if current in visited or current not in parents:
                    raise ValueError('Incomplete or cyclic compartment hierarchy')
                visited.add(current)
                if current == scope:
                    compartments.add(identifier)
                current = parents[current]
            if scope == config['tenancy_id']:
                compartments.add(identifier)
        if len(compartments) > 500:
            raise ValueError('Compartment scan bound exceeded')
        report['compartments'] = sorted(compartments)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        error('DISCOVERY')
        return evaluate(report, config)
    resources = {}
    for region in regions:
        for compartment in sorted(compartments):
            try:
                token, seen = None, set()
                for page in range(100):
                    args = ['search', 'resource', 'structured-search', '--query-text',
                            "query all resources where compartmentId = '" + compartment + "'", '--limit', '1000']
                    if token:
                        args.extend(['--page', token])
                    response = api.get(args, region)
                    items = response['data']['items']
                    if not isinstance(items, list) or len(items) > 1000:
                        raise ValueError('Invalid Search page')
                    for item in items:
                        resource = normalize(item, region, compartment)
                        key = (region, resource['identifier'])
                        if key in resources and resources[key] != resource:
                            raise ValueError('Conflicting resource observations')
                        resources[key] = resource
                    token = response.get('opc-next-page')
                    if not token:
                        break
                    if not isinstance(token, str) or len(token) > 4096 or token in seen:
                        raise ValueError('Repeated or invalid pagination cursor')
                    seen.add(token)
                else:
                    raise ValueError('Search pagination bound exceeded')
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                error('SEARCH', region, compartment)
    report['resources'] = sorted(resources.values(), key=lambda item: (item['region'], item['identifier']))
    report['scan_complete'] = not report['errors']
    return evaluate(report, config)


def evaluate(report, config):
    observed = {(item['region'], item['identifier']): item for item in report['resources']}
    checks = []
    for expected in config['expected']:
        item = observed.get((expected['region'], expected['identifier']))
        status = 'NOT_OBSERVED'
        if item:
            status = 'MATCHED_VISIBLE' if (item['compartment_id'] == expected['compartment_id']
                and item['resource_type'].lower() == expected['resource_type'].lower()
                and item['lifecycle_state'] in expected['allowed_states']) else 'MISMATCH'
        checks.append({'identifier': expected['identifier'], 'region': expected['region'], 'status': status})
    report['expected_checks'] = checks
    report['status'] = ('INCOMPLETE' if not report['scan_complete'] else
                        'EXPECTED_RESOURCES_VISIBLE' if all(c['status'] == 'MATCHED_VISIBLE' for c in checks)
                        else 'ATTENTION_REQUIRED')
    return report


def compare(previous, current):
    if not previous or previous.get('scope_sha256') != current['scope_sha256']:
        return {'status': 'NO_COMPARABLE_PREVIOUS_OBSERVATION'}
    old = {(r['region'], r['identifier']): r for r in previous['resources']}
    new = {(r['region'], r['identifier']): r for r in current['resources']}
    return {'status': 'COMPARED', 'previous_observed_at': previous['observed_at'],
            'added': sorted([list(key) for key in new.keys() - old.keys()]),
            'no_longer_observed': sorted([list(key) for key in old.keys() - new.keys()]),
            'changed': sorted([list(key) for key in new.keys() & old.keys() if new[key] != old[key]])}


def inventory_status(state=STATE, *, now=None, max_age_seconds=7 * 3600):
    """Operator/audit consumer: stale or failed evidence can never mean current."""
    try:
        path = state / 'latest.json'
        if path.is_symlink():
            raise ValueError('Report symlink')
        report = json.loads(path.read_text())
        observed = datetime.fromisoformat(report['observed_at'])
        current = now or datetime.now(timezone.utc)
        age = (current - observed).total_seconds()
        if age < -60 or age > max_age_seconds:
            return {'status': 'STALE', 'inventory_current': False, 'observed_at': report['observed_at']}
        return {'status': report['status'],
                'inventory_current': report['status'] == 'EXPECTED_RESOURCES_VISIBLE' and report['scan_complete'] is True,
                'observed_at': report['observed_at']}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status': 'UNAVAILABLE', 'inventory_current': False}


def atomic_json(path, value):
    if path.is_symlink():
        raise ValueError('State files cannot be symlinks')
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.inventory-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write((json.dumps(value, indent=2) + '\n').encode())
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def run_inventory(config_path=CONFIG, state=STATE, *, api=None):
    if state.is_symlink() or state.parent.is_symlink():
        raise ValueError('Private state directory required')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = state.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('State directory must be owner-controlled and private')
    lock_path = state / 'inventory.lock'
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous_path = state / 'previous-complete.json'
        if previous_path.is_symlink():
            raise ValueError('Previous observation cannot be a symlink')
        previous = json.loads(previous_path.read_text()) if previous_path.exists() else None
        try:
            config = load_config(config_path)
            report = collect(config, api=api)
            report['changes'] = (compare(previous, report) if report['scan_complete'] else
                                 {'status': 'WITHHELD_INCOMPLETE_SCAN'})
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
            report = {'schema': 1, 'status': 'INCOMPLETE', 'scan_complete': False,
                      'observed_at': datetime.now(timezone.utc).isoformat(),
                      'errors': [{'phase': 'CONFIGURATION', 'reason': 'INVALID_OR_UNAVAILABLE'}],
                      'production_ready': False, 'changes': {'status': 'WITHHELD_INCOMPLETE_SCAN'}}
        report['previous_complete_observed_at'] = previous.get('observed_at') if previous else None
        report['free_resource_mapping'] = inventory_mapping(report)
        atomic_json(state / 'latest.json', report)
        if report['scan_complete']:
            atomic_json(previous_path, report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--state', type=Path, default=STATE)
    args = parser.parse_args()
    report = run_inventory(args.config, args.state)
    print(json.dumps({'status': report['status'], 'observed_at': report['observed_at'],
                      'report': str(args.state / 'latest.json')}))
    return 0 if report['status'] == 'EXPECTED_RESOURCES_VISIBLE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
