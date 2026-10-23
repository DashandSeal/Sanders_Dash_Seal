"""Build a reproducible Resource Manager ZIP; never contacts OCI or creates resources."""
import argparse
import gzip
import io
import subprocess
import tarfile
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy.standardize import cloud_config


def pair(name, content):
    return json.dumps({'body': {'schema': 1, 'platform': 'Sanders Dash & Seal',
        'artifact': name, 'payload_hash': hashlib.sha256(content.encode()).hexdigest(),
        'scope': {'endpoint': 'local://development', 'method': 'TEST', 'ip': '127.0.0.1',
                  'operation': 'DEVELOPMENT_VALIDATION'}}, 'signatures': {},
        'status': 'UNSIGNED_SOURCE_MANIFEST'}, indent=2) + '\n'


def application_bundle(commit, root=ROOT, source_names=None):
    if source_names is None:
        source_names = subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True).splitlines()
    names = sorted(set(source_names))
    manifest = {'source_commit': commit, 'files': {}}
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as bundle:
            for name in names:
                path = root / name
                if (Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink()
                        or not path.is_file() or any(part in ('.git', 'node_modules', '.venv') for part in Path(name).parts)
                        or name.endswith(('.env', '.env.secrets'))):
                    raise ValueError('Only clean repository source files may be packaged')
                raw = path.read_bytes()
                manifest['files'][name] = hashlib.sha256(raw).hexdigest()
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(raw), 0o644
                bundle.addfile(item, io.BytesIO(raw))
            raw = (json.dumps(manifest, sort_keys=True) + '\n').encode()
            item = tarfile.TarInfo('.sds-source.json')
            item.size, item.mode = len(raw), 0o644
            bundle.addfile(item, io.BytesIO(raw))
    if not all(name in names for name in ('docker-compose.yml', 'backend/platform-source.json',
            'worker/package-lock.json', 'deploy/install_application.sh', 'scripts/verify_release_source.py')):
        raise ValueError('The complete committed application source is required')
    if len(output.getvalue()) > 8 * 1024 * 1024:
        raise ValueError('Application archive exceeds Resource Manager upload budget')
    return output.getvalue()


def contents(commit, *, root=ROOT, source_names=None, direct=False):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('A full source commit SHA is required')
    folder = root / 'infrastructure/resource-manager'
    files = {name: (folder / name).read_text() for name in
             ('versions.tf', 'variables.tf', 'main.tf', 'free-platform.tf', 'outputs.tf', 'schema.yaml', 'README.md')}
    if direct:
        # Apply alone boots a fresh A1 using the same bundled application installer.
        files['variables.tf'] = files['variables.tf'].replace(
            'variable "create_instance" {\n  type = bool\n  default = false',
            'variable "create_instance" {\n  type = bool\n  default = true').replace(
            'variable "deploy_existing_instance" {\n  type = bool\n  default = true',
            'variable "deploy_existing_instance" {\n  type = bool\n  default = false')
        files['schema.yaml'] = files['schema.yaml'].replace('title: Sanders Dash & Seal application deployment',
            'title: Sanders Dash & Seal direct A1 installation')
        files['README.md'] = (root / 'infrastructure/resource-manager/DIRECT_INSTALL.md').read_text()
    files['release.tf'] = 'locals {\n  approved_commit = "' + commit + '"\n}\n'
    files['application.tgz'] = application_bundle(commit, root, source_names)
    files['wait_application.py'] = (root / 'deploy/wait_application.py').read_text()
    install = (root / 'deploy/install_application.sh').read_text()
    fetch = (root / 'deploy/fetch_release.py').read_text()
    config = {'ssh_deletekeys': True, 'write_files': [
        {'path': '/usr/local/sbin/sds-install-application', 'owner': 'root:root',
         'permissions': '0700', 'content': install},
        {'path': '/usr/local/sbin/sds-fetch-release', 'owner': 'root:root',
         'permissions': '0700', 'content': fetch},
        {'path': '/etc/sanders-dash-seal/release.json', 'owner': 'root:root',
         'permissions': '0600', 'content': 'SDS_RELEASE_CONFIG_SLOT'}],
        'runcmd': [['bash', '/usr/local/sbin/sds-install-application']]}
    template = ('#cloud-config\n' + json.dumps(config, indent=2) + '\n').replace('${', '$${').replace('%{', '%%{')
    files['cloud-init-application.yaml.tftpl'] = template.replace('"SDS_RELEASE_CONFIG_SLOT"', '${jsonencode(release_config)}')
    import base64
    # Oracle Run Command can fetch a script larger than 4 KB from private Object Storage.
    # A root invocation is required by the OS; this does not invent a release authorizer.
    existing = """#!/bin/bash
set -Eeuo pipefail
if [[ \"$EUID\" != 0 ]]; then exec sudo -n /usr/local/sbin/sanders-install-from-bucket SDS_INSTALL_COMMIT; fi
install -d -m 0700 /etc/sanders-dash-seal
"""
    existing = existing.replace('SDS_INSTALL_COMMIT', commit)
    for destination, raw in [('/usr/local/sbin/sds-install-application', install),
                             ('/usr/local/sbin/sds-fetch-release', fetch)]:
        existing += "printf '%s' '" + base64.b64encode(raw.encode()).decode() + "' | base64 -d > " + destination + "\nchmod 0700 " + destination + "\n"
    existing += "printf '%s' '${release_config_base64}' | base64 -d > /etc/sanders-dash-seal/release.json\nchmod 0600 /etc/sanders-dash-seal/release.json\nexec /bin/bash /usr/local/sbin/sds-install-application\n"
    files['install-existing.sh.tftpl'] = existing
    for name, raw in list(files.items()):
        if name != 'README.md' and isinstance(raw, str):
            files[name + '.pbd.json'] = pair(name, raw)
    files['package_manifest.json'] = json.dumps({'schema': 1, 'source_commit': commit,
        'files': {name: hashlib.sha256(raw.encode() if isinstance(raw, str) else raw).hexdigest() for name, raw in sorted(files.items())},
        'production_signatures_verified': False, 'cloud_resources_created': False}, indent=2) + '\n'
    return files


def build(output, commit, *, root=ROOT, source_names=None, direct=False):
    files = contents(commit, root=root, source_names=source_names, direct=direct)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted(files.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
    return {'file': str(output), 'source_commit': commit, 'members': len(files),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'provisioned': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source-list', type=Path)
    parser.add_argument('--direct', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output, args.commit, source_names=json.loads(args.source_list.read_text()) if args.source_list else None, direct=args.direct)))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
