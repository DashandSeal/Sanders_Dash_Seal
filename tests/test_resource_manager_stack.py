"""Resource Manager packaging tests never plan/apply or create cloud resources."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.package_resource_manager import build, contents


ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


class ResourceManagerStackTests(unittest.TestCase):
    def test_zip_has_flat_terraform_layout_and_reproducible_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ('one.zip', 'two.zip'))
            result = build(first, SHA)
            build(second, SHA)
            self.assertFalse(result['provisioned'])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIn('main.tf', archive.namelist())
                self.assertIn('cloud-init-audit.yaml', archive.namelist())
                self.assertTrue(all('/' not in name for name in archive.namelist()))
                self.assertEqual(archive.testzip(), None)

    def test_invalid_commit_and_existing_output_rejected(self):
        with self.assertRaises(ValueError):
            contents('PR-3-CLEAN-CANDIDATE')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'stack.zip'
            build(output, SHA)
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                build(output, SHA)
            self.assertEqual(original, output.read_bytes())

    def test_audit_profile_does_not_clone_or_activate_application(self):
        config = json.loads(contents(SHA)['cloud-init-audit.yaml'].split('\n', 1)[1])
        self.assertEqual(config['runcmd'], [['bash', '/usr/local/sbin/sds-system-preflight-audit']])
        self.assertEqual(len(config['write_files']), 1)
        text = json.dumps(config)
        self.assertNotIn('git clone', text)
        self.assertNotIn('compose up', text)

    def test_stage_template_escapes_shell_and_pins_only_release_slot(self):
        files = contents(SHA)
        text = files['cloud-init-stage.yaml.tftpl']
        self.assertIn('SDS_BOOTSTRAP_COMMIT=${approved_commit}', text)
        self.assertIn('$${SDS_SOURCE_DIR', text)
        restored = text.replace('${approved_commit}', SHA).replace('$${', '${').replace('%%{', '%{')
        config = json.loads(restored.split('\n', 1)[1])
        self.assertEqual(len(config['runcmd']), 1)
        self.assertIn('SDS_BOOTSTRAP_MODE=stage', config['runcmd'][0])
        self.assertIn(SHA, files['release.tf'])

    def test_all_package_pairs_and_inventory_hashes_match(self):
        files = contents(SHA)
        manifest = json.loads(files['package_manifest.json'])
        for name, expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256(files[name].encode()).hexdigest(), expected)
        for name, raw in files.items():
            if name.endswith('.pbd.json'):
                paired = json.loads(raw)
                artifact = paired['body']['artifact']
                self.assertEqual(paired['body']['payload_hash'], hashlib.sha256(files[artifact].encode()).hexdigest())
                self.assertFalse(paired['signatures'])

    def test_default_resources_and_shape_respect_existing_instance_boundary(self):
        files = contents(SHA)
        self.assertIn('shape = "VM.Standard.A1.Flex"', files['main.tf'])
        self.assertNotIn('VM.Standard.E4.Flex', files['main.tf'])
        self.assertIn('prevent_destroy = true', files['main.tf'])
        self.assertNotIn('InstancePrincipal', files['versions.tf'])
        self.assertNotIn('remote-exec', files['main.tf'])
        self.assertNotIn('private_key', files['main.tf'])
        self.assertIn('default = false', files['variables.tf'])
        self.assertIn('NOT_VERIFIED', files['outputs.tf'])

    def test_new_network_has_default_route_and_explicit_web_ports(self):
        main = contents(SHA)['main.tf']
        self.assertIn('resource "oci_core_internet_gateway"', main)
        self.assertIn('destination = "0.0.0.0/0"', main)
        self.assertIn('{ http = 80, https = 443 }', main)
        self.assertNotIn('source_port_range', main)
        self.assertNotIn('= 22', main)

    def test_generated_cloud_metadata_stays_under_budget(self):
        files = contents(SHA)
        text = files['cloud-init-stage.yaml.tftpl'].replace('${approved_commit}', SHA).replace('$${', '${').replace('%%{', '%{')
        import base64
        self.assertLess(len(base64.b64encode(text.encode())), 30000)


if __name__ == '__main__':
    unittest.main()
