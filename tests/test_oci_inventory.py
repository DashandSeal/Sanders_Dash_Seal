"""OCI inventory uses fake API responses; no cloud changes or network requests."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import types
import unittest

from deploy.oci_inventory import ReadOnlyOCI, collect, compare, inventory_status, load_config, run_inventory, validate_config


def identity(kind, letter='a'):
    return 'ocid1.' + kind + '.oc1..' + letter * 50


def configuration():
    return {'schema': 1, 'tenancy_id': identity('tenancy'), 'compartment_id': identity('tenancy'),
            'home_region': 'us-phoenix-1', 'expected': [{'identifier': identity('instance'),
            'resource_type': 'Instance', 'region': 'us-phoenix-1',
            'compartment_id': identity('tenancy'), 'allowed_states': ['RUNNING']}]}


def resource(identifier=None, compartment=None, state='RUNNING'):
    return {'identifier': identifier or identity('instance'), 'resource-type': 'Instance',
            'compartment-id': compartment or identity('tenancy'), 'lifecycle-state': state,
            'display-name': 'sanders-dash-seal', 'freeform-tags': {'secret': 'DO_NOT_RETAIN'}}


class FakeOCI:
    def __init__(self, *, fail_region=None, repeated_cursor=False, compartments=None, pages=None):
        self.calls = []
        self.fail_region = fail_region
        self.repeated_cursor = repeated_cursor
        self.compartments = compartments or []
        self.pages = pages

    def get(self, args, region):
        self.calls.append((args, region))
        if args[:3] == ['iam', 'region-subscription', 'list']:
            return {'data': [{'region-name': r, 'status': 'READY'}
                             for r in ('us-phoenix-1', 'us-ashburn-1')]}
        if args[:3] == ['iam', 'compartment', 'list']:
            return {'data': self.compartments}
        if region == self.fail_region:
            raise subprocess.TimeoutExpired('oci', 10)
        if self.repeated_cursor:
            return {'data': {'items': []}, 'opc-next-page': 'same'}
        compartment = args[args.index('--query-text') + 1].split("'")[1]
        if self.pages and region == 'us-phoenix-1':
            if '--page' not in args:
                return {'data': {'items': []}, 'opc-next-page': 'next'}
            return {'data': {'items': [resource(compartment=compartment)]}}
        return {'data': {'items': [resource(compartment=compartment)] if region == 'us-phoenix-1' else []}}


class OCIInventoryTests(unittest.TestCase):
    def test_scans_all_subscribed_regions_and_explicit_pagination(self):
        api = FakeOCI(pages=True)
        report = collect(configuration(), api=api)
        self.assertEqual(report['status'], 'EXPECTED_RESOURCES_VISIBLE')
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['full_tenancy_visibility_verified'])
        self.assertEqual(set(report['regions']), {'us-ashburn-1', 'us-phoenix-1'})
        self.assertTrue(any('--page' in args for args, _ in api.calls))
        self.assertNotIn('DO_NOT_RETAIN', json.dumps(report))

    def test_child_scope_excludes_siblings_and_includes_grandchildren(self):
        child, grandchild, sibling = (identity('compartment', c) for c in 'bcd')
        config = configuration()
        config['compartment_id'] = child
        config['expected'][0]['compartment_id'] = grandchild
        compartments = [{'id': child, 'compartment-id': config['tenancy_id'], 'lifecycle-state': 'ACTIVE'},
            {'id': grandchild, 'compartment-id': child, 'lifecycle-state': 'ACTIVE'},
            {'id': sibling, 'compartment-id': config['tenancy_id'], 'lifecycle-state': 'ACTIVE'}]
        # Distinct resources in each compartment; duplicate identities are invalid.
        api = FakeOCI(compartments=compartments)
        original = api.get
        def get(args, region):
            response = original(args, region)
            if args[0] == 'search':
                for item in response['data']['items']:
                    if item['compartment-id'] == child:
                        item['identifier'] = identity('instance', 'b')
            return response
        api.get = get
        report = collect(config, api=api)
        self.assertEqual(report['compartments'], sorted([child, grandchild]))
        self.assertNotIn(sibling, json.dumps(api.calls))
        self.assertEqual(report['status'], 'EXPECTED_RESOURCES_VISIBLE')

    def test_timeout_is_incomplete_and_does_not_claim_deleted_resources(self):
        report = collect(configuration(), api=FakeOCI(fail_region='us-phoenix-1'))
        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['expected_checks'][0]['status'], 'NOT_OBSERVED')
        self.assertFalse(report['scan_complete'])

    def test_repeated_page_cursor_stops_and_records_failure(self):
        api = FakeOCI(repeated_cursor=True)
        report = collect(configuration(), api=api)
        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertLess(len(api.calls), 10)

    def test_state_mismatch_and_unobserved_identity_require_attention(self):
        config = configuration()
        config['expected'][0]['allowed_states'] = ['STOPPED']
        report = collect(config, api=FakeOCI())
        self.assertEqual(report['status'], 'ATTENTION_REQUIRED')
        self.assertEqual(report['expected_checks'][0]['status'], 'MISMATCH')
        config['expected'][0]['identifier'] = identity('instance', 'z')
        report = collect(config, api=FakeOCI())
        self.assertEqual(report['expected_checks'][0]['status'], 'NOT_OBSERVED')

    def test_placeholder_empty_expectations_and_query_injection_rejected(self):
        for changes in ({'tenancy_id': 'placeholder'}, {'expected': []},
                        {'compartment_id': identity('tenancy') + "' or 1=1"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_config(configuration() | changes)

    def test_diff_detects_added_changed_and_no_longer_observed(self):
        old = collect(configuration(), api=FakeOCI())
        new = json.loads(json.dumps(old))
        new['resources'][0]['lifecycle_state'] = 'STOPPED'
        self.assertTrue(compare(old, new)['changed'])
        new['resources'][0]['identifier'] = identity('instance', 'b')
        result = compare(old, new)
        self.assertTrue(result['added'])
        self.assertTrue(result['no_longer_observed'])
        new['scope_sha256'] = 'changed'
        self.assertEqual(compare(old, new)['status'], 'NO_COMPARABLE_PREVIOUS_OBSERVATION')

    def test_complete_observation_preserved_after_failed_query_and_invalid_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'inventory.json'
            path.write_text(json.dumps(configuration()))
            path.chmod(0o600)
            state = root / 'state'
            report = run_inventory(path, state, api=FakeOCI())
            self.assertEqual(report['status'], 'EXPECTED_RESOURCES_VISIBLE')
            saved = (state / 'previous-complete.json').read_bytes()
            report = run_inventory(path, state, api=FakeOCI(fail_region='us-phoenix-1'))
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual(report['changes']['status'], 'WITHHELD_INCOMPLETE_SCAN')
            self.assertEqual(saved, (state / 'previous-complete.json').read_bytes())
            path.chmod(0o644)
            report = run_inventory(path, state, api=FakeOCI())
            self.assertEqual(report['errors'][0]['phase'], 'CONFIGURATION')
            self.assertEqual(saved, (state / 'previous-complete.json').read_bytes())
            self.assertEqual((state / 'latest.json').stat().st_mode & 0o777, 0o600)

    def test_config_and_report_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'actual.json'
            source.write_text(json.dumps(configuration()))
            source.chmod(0o600)
            link = root / 'link.json'
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                load_config(link)
            state = root / 'state'
            state.mkdir(mode=0o700)
            (state / 'latest.json').symlink_to(source)
            with self.assertRaises(ValueError):
                run_inventory(source, state, api=FakeOCI())
            self.assertEqual(json.loads(source.read_text()), configuration())

    def test_platform_status_rejects_stale_failed_missing_and_future_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(inventory_status(root)['inventory_current'])
            now = datetime.now(timezone.utc)
            report = {'status': 'EXPECTED_RESOURCES_VISIBLE', 'scan_complete': True,
                      'observed_at': now.isoformat()}
            path = root / 'latest.json'
            path.write_text(json.dumps(report))
            self.assertTrue(inventory_status(root, now=now)['inventory_current'])
            self.assertEqual(inventory_status(root, now=now + timedelta(hours=8))['status'], 'STALE')
            self.assertFalse(inventory_status(root, now=now - timedelta(hours=1))['inventory_current'])
            report['status'] = 'INCOMPLETE'
            path.write_text(json.dumps(report))
            self.assertFalse(inventory_status(root, now=now)['inventory_current'])

    def test_cli_uses_instance_principals_fixed_read_operations_and_timeouts(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return types.SimpleNamespace(stdout='{"data": []}')
        api = ReadOnlyOCI(runner)
        api.get(['iam', 'region-subscription', 'list', '--all'], 'us-phoenix-1')
        command, kwargs = calls[0]
        self.assertIn('instance_principal', command)
        self.assertNotIn('shell', kwargs)
        self.assertLessEqual(kwargs['timeout'], 45)
        api.calls = 200
        with self.assertRaises(ValueError):
            api.get(['iam', 'region-subscription', 'list'], 'us-phoenix-1')

    def test_authorized_bootstrap_installs_and_enables_inventory_timer(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['bash', '-c', '''
source "$1/deploy.sh"
SDS_PROJECT_DIR="$1"
install() { echo "install $*"; }
systemctl() { echo "systemctl $*"; }
install_inventory_monitor
''', 'fixture', str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sanders-oci-inventory.service', result.stdout)
        self.assertIn('enable --now sanders-oci-inventory.timer', result.stdout)
        self.assertNotIn('enable --now sanders-oci-inventory.service', result.stdout)


if __name__ == '__main__':
    unittest.main()
