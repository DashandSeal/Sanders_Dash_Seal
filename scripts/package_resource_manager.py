"""Build a reproducible Resource Manager ZIP; never contacts OCI or creates resources."""
import argparse
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
        'status': 'UNSIGNED_DEPLOYMENT_BLOCKED'}, indent=2) + '\n'


def contents(commit, *, root=ROOT):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('A full source commit SHA is required')
    folder = root / 'infrastructure/resource-manager'
    files = {name: (folder / name).read_text() for name in
             ('versions.tf', 'variables.tf', 'main.tf', 'outputs.tf', 'schema.yaml', 'README.md')}
    files['release.tf'] = 'locals {\n  approved_commit = "' + commit + '"\n}\n'
    # Escape Terraform interpolation inside embedded shell; only the release slot
    # is a Terraform substitution. No credentials or source archives enter metadata.
    stage = cloud_config(commit)
    stage_config = json.loads(stage.split('\n', 1)[1])
    audit = next(item for item in stage_config['write_files'] if item['path'].endswith('sds-system-preflight-audit'))
    files['cloud-init-audit.yaml'] = '#cloud-config\n' + json.dumps({
        'ssh_deletekeys': True, 'write_files': [audit],
        'runcmd': [['bash', '/usr/local/sbin/sds-system-preflight-audit']]}, indent=2) + '\n'
    stage = stage.replace('${', '$${').replace('%{', '%%{')
    files['cloud-init-stage.yaml.tftpl'] = stage.replace('SDS_BOOTSTRAP_COMMIT=' + commit,
                                                    'SDS_BOOTSTRAP_COMMIT=${approved_commit}')
    if len(stage.encode()) > 22000:
        raise ValueError('Bootstrap template exceeds the conservative metadata budget')
    for name, raw in list(files.items()):
        if name != 'README.md':
            files[name + '.pbd.json'] = pair(name, raw)
    files['package_manifest.json'] = json.dumps({'schema': 1, 'source_commit': commit,
        'files': {name: hashlib.sha256(raw.encode()).hexdigest() for name, raw in sorted(files.items())},
        'production_signatures_verified': False, 'cloud_resources_created': False}, indent=2) + '\n'
    return files


def build(output, commit):
    files = contents(commit)
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
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output, args.commit)))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
