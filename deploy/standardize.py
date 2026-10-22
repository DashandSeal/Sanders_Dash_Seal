"""Render OCI standardization requests locally; never provisions cloud resources."""
import argparse
import base64
import ipaddress
import json
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[1]


def ocid(value, kind):
    kinds = '(?:compartment|tenancy)' if kind == 'compartment' else re.escape(kind)
    if not re.fullmatch(r'ocid1\.' + kinds + r'\.oc1\.[a-z0-9-]*\.[a-z0-9]{20,}', value):
        raise ValueError('A complete OCI ' + kind + ' identifier is required')
    if any(marker in value.lower() for marker in ('placeholder', 'your_', 'example')):
        raise ValueError('Placeholder resource identity rejected')
    return value


def public_key(value):
    parts = value.strip().split()
    if len(parts) < 2 or parts[0] not in ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256'):
        raise ValueError('An OpenSSH public key is required; never supply a private key')
    try:
        raw = base64.b64decode(parts[1], validate=True)
        size = struct.unpack('>I', raw[:4])[0]
        if raw[4:4 + size].decode() != parts[0] or len(raw) <= 4 + size:
            raise ValueError('Invalid public key payload')
    except (ValueError, UnicodeError, struct.error) as error:
        raise ValueError('Invalid OpenSSH public key') from error
    # Exclude comments from instance metadata.
    return ' '.join(parts[:2])


def cloud_config(commit, *, mode='stage', tune_kernel=False, public_ipv4=None):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('An immutable full commit SHA is required')
    if mode not in ('stage', 'activate'):
        raise ValueError('Unknown bootstrap mode')
    if mode == 'activate' and not public_ipv4:
        raise ValueError('Activation requires this individual node\'s public IPv4')
    if public_ipv4:
        address = ipaddress.IPv4Address(public_ipv4)
        if not address.is_global:
            raise ValueError('A public IPv4 address is required')
    command = ['env', 'SDS_BOOTSTRAP_COMMIT=' + commit,
               'SDS_BOOTSTRAP_MODE=' + mode, 'SDS_TUNE_KERNEL=' + str(int(tune_kernel))]
    if public_ipv4:
        command.append('SDS_PUBLIC_IPV4=' + public_ipv4)
    command.extend(['bash', '/usr/local/sbin/sds-bootstrap'])
    config = {'ssh_deletekeys': True, 'write_files': [{
        'path': '/usr/local/sbin/sds-bootstrap', 'owner': 'root:root',
        'permissions': '0700', 'content': (ROOT / 'deploy/sds-bootstrap.sh').read_text()}, {
        'path': '/usr/local/sbin/sds-system-preflight-audit', 'owner': 'root:root',
        'permissions': '0700', 'content': (ROOT / 'deploy/system_preflight_audit.sh').read_text()}],
        'runcmd': [['bash', '-c', 'set -Eeuo pipefail\nbash /usr/local/sbin/sds-system-preflight-audit\nexec "$@"',
                   'sds-cloud-init', *command]]}
    # JSON is a YAML subset accepted after the cloud-config header.
    return '#cloud-config\n' + json.dumps(config, indent=2) + '\n'


def render(*, commit, compartment_id, image_id, subnet_id, nsg_id,
           availability_domain, ssh_public_key, assign_public_ip=False,
           mode='stage', tune_kernel=False, public_ipv4=None, builder_instance_id=None):
    compartment_id = ocid(compartment_id, 'compartment')
    if not availability_domain or len(availability_domain) > 255 or any(
            character in availability_domain for character in '\r\n'):
        raise ValueError('An actual availability domain name is required')
    if mode == 'activate' and not assign_public_ip:
        raise ValueError('Public edge activation requires explicit public-IP assignment')
    user_data = cloud_config(commit, mode=mode, tune_kernel=tune_kernel, public_ipv4=public_ipv4)
    metadata = {'user_data': base64.b64encode(user_data.encode()).decode(),
                'ssh_authorized_keys': public_key(ssh_public_key)}
    if len(json.dumps(metadata).encode()) > 32000:
        raise ValueError('Instance metadata exceeds the conservative 32 KB limit')
    details = {'instanceType': 'compute', 'launchDetails': {
        'compartmentId': compartment_id, 'availabilityDomain': availability_domain,
        'shape': 'VM.Standard.A1.Flex', 'shapeConfig': {'ocpus': 1, 'memoryInGBs': 6},
        'sourceDetails': {'sourceType': 'image', 'imageId': ocid(image_id, 'image'),
                          'bootVolumeSizeInGBs': 50},
        'createVnicDetails': {'subnetId': ocid(subnet_id, 'subnet'),
                              'nsgIds': [ocid(nsg_id, 'networksecuritygroup')],
                              'assignPublicIp': assign_public_ip},
        'instanceOptions': {'areLegacyImdsEndpointsDisabled': True}, 'metadata': metadata}}
    files = {'cloud-init.yaml': user_data, 'instance-configuration.json': json.dumps({
        'compartmentId': compartment_id, 'displayName': 'SDS-Standard-Production-Template',
        'instanceDetails': details}, indent=2) + '\n'}
    if builder_instance_id:
        files['custom-image-request.json'] = json.dumps({
            'compartmentId': compartment_id, 'displayName': 'SDS-Platinum-Golden-Image',
            'instanceId': ocid(builder_instance_id, 'instance')}, indent=2) + '\n'
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('commit', 'compartment-id', 'image-id', 'subnet-id', 'nsg-id', 'availability-domain'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--ssh-public-key-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assign-public-ip', action='store_true')
    parser.add_argument('--mode', choices=['stage', 'activate'], default='stage')
    parser.add_argument('--tune-kernel', action='store_true')
    parser.add_argument('--public-ipv4')
    parser.add_argument('--sanitized-builder-instance-id', dest='builder_instance_id')
    args = vars(parser.parse_args())
    output = args.pop('output')
    try:
        args['ssh_public_key'] = args.pop('ssh_public_key_file').read_text()
        files = render(**args)
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        for name, content in files.items():
            path = output / name
            path.write_text(content)
            path.chmod(0o600)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('Rendered local review files only. No OCI resource was created or launched.')


if __name__ == '__main__':
    main()
