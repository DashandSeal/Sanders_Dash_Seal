"""Application upload packages and archive failure paths; never creates OCI resources."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

from scripts.package_resource_manager import build, contents, application_bundle
from scripts.verify_release_source import verify
from deploy.fetch_release import unpack
from deploy.wait_application import wait

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40
NAMES = sorted(set(json.loads((ROOT / 'backend/platform-source.json').read_text())) |
    {'docker-compose.yml', 'backend/platform-source.json', 'worker/package-lock.json',
     'deploy/install_application.sh', 'scripts/verify_release_source.py'})


def packaged():
    return contents(SHA, source_names=NAMES)


class ResourceManagerStackTests(unittest.TestCase):
    def test_zip_contains_complete_application_and_reproducible_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ('one.zip', 'two.zip'))
            build(first, SHA, source_names=NAMES)
            build(second, SHA, source_names=NAMES)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIn('application.tgz', archive.namelist())
                self.assertEqual(archive.testzip(), None)
                blob = archive.read('application.tgz')
            bundle = tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz')
            self.assertIn('core_platform/security.py', bundle.getnames())
            self.assertIn('worker/package-lock.json', bundle.getnames())
            self.assertIn('backend/platform-source.json', bundle.getnames())

    def test_invalid_commit_and_existing_output_rejected(self):
        with self.assertRaises(ValueError): contents('PR-3-CLEAN-CANDIDATE')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stack.zip'
            build(path, SHA, source_names=NAMES)
            with self.assertRaises(FileExistsError): build(path, SHA, source_names=NAMES)

    def test_payload_integrity_is_verified_without_custom_authorizer(self):
        raw = application_bundle(SHA, ROOT, NAMES)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'release.tgz'
            archive.write_bytes(raw)
            source = Path(directory) / 'source'
            unpack(archive, source, hashlib.sha256(raw).hexdigest())
            self.assertEqual(verify(source, SHA)[0], SHA)
            (source / 'worker/package.json').write_text('tampered')
            with self.assertRaises(ValueError): verify(source, SHA)
            with self.assertRaises(ValueError): unpack(archive, Path(directory) / 'wrong', '0' * 64)

    def test_archive_traversal_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'bad.tgz'
            with tarfile.open(archive, 'w:gz') as bundle:
                entry = tarfile.TarInfo('../escape')
                entry.size = 1
                bundle.addfile(entry, io.BytesIO(b'x'))
            with self.assertRaises(ValueError): unpack(archive, Path(directory) / 'source', hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertFalse((Path(directory) / 'escape').exists())

    def test_first_boot_installs_application_instead_of_audit_only(self):
        files = packaged()
        text = files['cloud-init-application.yaml.tftpl'].replace('${jsonencode(release_config)}', json.dumps(json.dumps({'commit': SHA}))).replace('$${','${').replace('%%{','%{')
        config = json.loads(text.split('\n',1)[1])
        self.assertEqual(config['runcmd'], [['bash', '/usr/local/sbin/sds-install-application']])
        installer = config['write_files'][0]['content']
        self.assertIn('compose up -d pipeline-worker wsgi-backend reverse-proxy', installer)
        self.assertNotIn('SANDERS_RUNTIME_FACTORY', text)
        self.assertNotIn('authorize-release', text)

    def test_private_artifact_and_exact_instance_iam_scope(self):
        main = packaged()['main.tf']
        self.assertIn('access_type = "NoPublicAccess"', main)
        self.assertIn("instance.id = '${oci_core_instance.sds_automated[0].id}'", main)
        self.assertIn("request.permission='OBJECT_READ'", main)
        self.assertNotIn('preauthenticated', main)
        self.assertIn('VM.Standard.A1.Flex', main)
        self.assertNotIn('VM.Standard.E4.Flex', main)

    def test_readiness_deadline_does_not_turn_failure_into_success(self):
        now = [0]
        def pause(seconds): now[0] += seconds
        self.assertEqual(wait('129.146.111.166', SHA, timeout=2,
            check=lambda *args: False, clock=lambda: now[0], pause=pause), 1)
        self.assertEqual(wait('129.146.111.166', SHA, check=lambda *args: True), 0)

    def test_package_hashes_and_metadata_budget(self):
        files = packaged()
        manifest = json.loads(files['package_manifest.json'])
        for name, digest in manifest['files'].items():
            raw = files[name]
            self.assertEqual(hashlib.sha256(raw.encode() if isinstance(raw,str) else raw).hexdigest(), digest)
        self.assertLess(len(files['cloud-init-application.yaml.tftpl'].encode()) * 4 / 3, 30000)


if __name__ == '__main__': unittest.main()
