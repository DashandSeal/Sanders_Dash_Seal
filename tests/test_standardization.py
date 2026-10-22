"""Standardization tests never launch an instance or change host kernel settings."""
import base64
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import types
import unittest

from deploy import kernel_profile, standardize


ROOT = Path(__file__).resolve().parents[1]


class StandardizationTests(unittest.TestCase):
    def options(self):
        key = b'ssh-ed25519'
        raw = struct.pack('>I', len(key)) + key + struct.pack('>I', 32) + b'x' * 32
        identity = lambda kind: 'ocid1.' + kind + '.oc1.phx.' + 'a' * 40
        return dict(commit='a' * 40, compartment_id=identity('compartment'),
                    image_id=identity('image'), subnet_id=identity('subnet'),
                    nsg_id=identity('networksecuritygroup'), availability_domain='test:PHX-AD-1',
                    ssh_public_key='ssh-ed25519 ' + base64.b64encode(raw).decode())

    def test_template_pins_commit_and_defaults_to_private_staging(self):
        files = standardize.render(**self.options())
        request = json.loads(files['instance-configuration.json'])
        launch = request['instanceDetails']['launchDetails']
        self.assertFalse(launch['createVnicDetails']['assignPublicIp'])
        self.assertEqual(launch['shapeConfig'], {'ocpus': 1, 'memoryInGBs': 6})
        cloud = base64.b64decode(launch['metadata']['user_data']).decode()
        self.assertEqual(cloud, files['cloud-init.yaml'])
        config = json.loads(cloud.split('\n', 1)[1])
        self.assertEqual(len(config['runcmd']), 1)
        self.assertIn('SDS_BOOTSTRAP_MODE=stage', config['runcmd'][0])
        self.assertIn('SDS_BOOTSTRAP_COMMIT=' + 'a' * 40, config['runcmd'][0])
        self.assertEqual(config['write_files'][0]['permissions'], '0700')
        self.assertNotIn('SDS_PUBLIC_IPV4=', ' '.join(config['runcmd'][0]))
        self.assertNotIn('PRIVATE KEY', cloud)

    def test_bad_commit_identity_key_and_activation_are_rejected(self):
        changes = ({'commit': 'main'}, {'image_id': 'ocid1.image.oc1.phx.placeholder'},
                   {'ssh_public_key': '-----BEGIN PRIVATE KEY-----'}, {'mode': 'activate'},
                   {'mode': 'activate', 'assign_public_ip': True, 'public_ipv4': '10.0.0.2'})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                standardize.render(**(self.options() | change))

    def test_image_request_is_optional_and_never_an_automatic_launch(self):
        files = standardize.render(**(self.options() | {
            'builder_instance_id': 'ocid1.instance.oc1.phx.' + 'b' * 40}))
        self.assertEqual(json.loads(files['custom-image-request.json'])['displayName'],
                         'SDS-Platinum-Golden-Image')
        self.assertNotIn('launch-request.json', files)

    def test_cli_refuses_overwriting_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / 'public.pub'
            options = self.options()
            key.write_text(options.pop('ssh_public_key'))
            command = ['python3', str(ROOT / 'deploy/standardize.py'),
                       '--ssh-public-key-file', str(key), '--output', str(root)]
            for field, value in options.items():
                command.extend(['--' + field.replace('_', '-'), value])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'cloud-init.yaml').exists())

    def shell(self, commands):
        return subprocess.run(['bash', '-c', 'source "$1"; ' + commands,
                               'fixture', str(ROOT / 'deploy/sds-bootstrap.sh')],
                              capture_output=True, text=True)

    def test_stage_authorization_failure_stops_before_mutation_or_success(self):
        result = self.shell('''
check_source() { echo source; }; check_host() { echo host; }
authorize_release() { echo denied; return 7; }
install_engine() { echo MUTATION; }; configure_firewall() { echo MUTATION; }
SDS_BOOTSTRAP_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
stage_node
''')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn('MUTATION', result.stdout)
        self.assertNotIn('STAGED:', result.stdout)

    def test_stage_refuses_existing_containers(self):
        result = self.shell('''
check_source() { :; }; check_host() { :; }; authorize_release() { :; }
docker() { echo existing_container; }
install_engine() { echo MUTATION; }
SDS_BOOTSTRAP_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
SDS_PROJECT_DIR=/opt/sanders-dash-seal
SDS_STATE_DIR=/var/lib/sanders-dash-seal
stage_node
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('MUTATION', result.stdout)
        self.assertNotIn('STAGED:', result.stdout)

    def test_successful_stage_builds_but_does_not_start_application(self):
        result = self.shell('''
check_source() { :; }; check_host() { :; }; authorize_release() { echo authorized; }
docker() { :; }; install_engine() { echo engine; }; configure_firewall() { echo firewall; }
stage_authorized_source() { echo source_staged; }
compose() { echo "compose $*"; }
apply_kernel_profile() { :; }; install_integrity_monitor() { echo monitored; }
SDS_BOOTSTRAP_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
SDS_PROJECT_DIR=/opt/sanders-dash-seal
SDS_STATE_DIR=/var/lib/sanders-dash-seal
SDS_RUNTIME_ENV_FILE=/unused
stage_node
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stdout.index('authorized'), result.stdout.index('engine'))
        self.assertIn('compose build pipeline-worker wsgi-backend', result.stdout)
        self.assertNotIn('compose up', result.stdout)
        self.assertIn('STAGED:', result.stdout)

    def test_failed_build_never_reports_staged(self):
        result = self.shell('''
check_source() { :; }; check_host() { :; }; authorize_release() { :; }
docker() { :; }; install_engine() { :; }; configure_firewall() { :; }
stage_authorized_source() { :; }
compose() { [[ "$1" != build ]]; }
install_integrity_monitor() { echo BASELINE; }
SDS_BOOTSTRAP_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
SDS_PROJECT_DIR=/opt/sanders-dash-seal
SDS_STATE_DIR=/var/lib/sanders-dash-seal
SDS_RUNTIME_ENV_FILE=/unused
stage_node
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('STAGED:', result.stdout)
        self.assertNotIn('BASELINE', result.stdout)

    def test_activation_without_new_host_ip_stops_before_checkout(self):
        result = self.shell('''
SDS_BOOTSTRAP_MODE=activate
unset SDS_PUBLIC_IPV4
prepare_checkout() { echo CHECKOUT; }
bootstrap_main
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('CHECKOUT', result.stdout)

    def test_repository_source_is_not_loaded_before_independent_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'deploy.sh').write_text('echo REPOSITORY_CODE_EXECUTED\n')
            result = self.shell('''
SDS_BOOTSTRAP_MODE=stage
SDS_SOURCE_DIR="$2"
prepare_checkout() { :; }
verify_bootstrap_source() { echo DENIED; return 9; }
bootstrap_main
'''.replace('"$2"', "'" + directory + "'"))
            self.assertEqual(result.returncode, 9)
            self.assertNotIn('REPOSITORY_CODE_EXECUTED', result.stdout)

    def profile_runner(self, *, fail=False):
        values = {key: '0' for key in kernel_profile.PROFILE}
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if command[1] == '-n':
                return types.SimpleNamespace(stdout=values[command[2]])
            if command[1] == '-p':
                values.update(kernel_profile.PROFILE)
                if fail:
                    raise subprocess.CalledProcessError(1, command)
            if command[1] == '-w':
                key, value = command[2].split('=', 1)
                values[key] = value
            return types.SimpleNamespace(stdout='')
        return run, values, calls

    def test_kernel_profile_persists_only_requested_values(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'sds.conf'
            runner, values, _ = self.profile_runner()
            result = kernel_profile.apply_profile(target, runner=runner)
            self.assertFalse(result['measured_throughput'])
            self.assertEqual(values, kernel_profile.PROFILE)
            self.assertIn('net.ipv4.tcp_tw_reuse=1', target.read_text())
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_kernel_failure_restores_prior_file_and_all_values(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'sds.conf'
            target.write_text('original\n')
            target.chmod(0o600)
            runner, values, _ = self.profile_runner(fail=True)
            with self.assertRaises(subprocess.CalledProcessError):
                kernel_profile.apply_profile(target, runner=runner)
            self.assertEqual(target.read_text(), 'original\n')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(set(values.values()), {'0'})
            self.assertFalse(list(Path(directory).glob('.sds-sysctl-*')))

    def test_kernel_target_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'sds.conf'
            target.symlink_to(Path(directory) / 'other')
            with self.assertRaises(ValueError):
                kernel_profile.apply_profile(target, runner=lambda *a, **k: self.fail('host call'))


if __name__ == '__main__':
    unittest.main()
