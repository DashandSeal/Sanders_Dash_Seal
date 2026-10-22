"""Read-only validation of actual OCI identity mappings; never provisions resources."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse


REQUIRED = ('OCI_REGION', 'OCI_TENANCY_OCID', 'OCI_COMPARTMENT_OCID',
    'OCI_STREAM_POOL_OCID', 'OCI_STREAM_OCID', 'OCI_STREAM_ENDPOINT',
    'OCI_STREAM_TOPIC_NAME', 'OCI_FUNCTION_OCID', 'OCI_OBJECT_STORAGE_NAMESPACE',
    'OCI_BACKUP_BUCKET')


def load_env(path):
    info = path.stat()
    if path.is_symlink() or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Use an owner-controlled private 0600 configuration file')
    if info.st_size > 65536:
        raise ValueError('Configuration too large')
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or key not in REQUIRED or key in result:
            raise ValueError('Unexpected, duplicate or malformed configuration key')
        # This is data parsing, never shell sourcing/interpolation.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    validate(result)
    return result


def validate(config):
    for key in REQUIRED:
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError('Missing actual configuration: ' + key)
    if config['OCI_REGION'] != 'us-phoenix-1':
        raise ValueError('Existing deployment region is us-phoenix-1')
    for key, kind in (('OCI_TENANCY_OCID', 'tenancy'),
                      ('OCI_COMPARTMENT_OCID', '(?:compartment|tenancy)'),
                      ('OCI_STREAM_POOL_OCID', 'streampool'),
                      ('OCI_STREAM_OCID', 'stream'), ('OCI_FUNCTION_OCID', 'fnfunc')):
        value = config[key]
        if not re.fullmatch(r'ocid1\.' + kind + r'\.oc1\.[a-z0-9-]*\.[A-Za-z0-9]{40,}', value):
            raise ValueError('Real OCID required: ' + key)
        if any(word in value.lower() for word in ('your_', 'example', 'rooseveltsanders', 'nearzero')):
            raise ValueError('Placeholder OCID rejected: ' + key)
    if (config['OCI_COMPARTMENT_OCID'].startswith('ocid1.tenancy.')
            and config['OCI_COMPARTMENT_OCID'] != config['OCI_TENANCY_OCID']):
        raise ValueError('Root compartment must use this tenancy OCID')
    endpoint = urllib.parse.urlsplit(config['OCI_STREAM_ENDPOINT'])
    if (endpoint.scheme != 'https' or endpoint.username or endpoint.password
            or endpoint.query or endpoint.fragment or endpoint.path not in ('', '/')
            or endpoint.port not in (None, 443) or not re.fullmatch(
                r'(?:cell-[a-z0-9-]+\.)?streaming\.us-phoenix-1\.oci\.oraclecloud\.com',
                endpoint.hostname or '')):
        raise ValueError('Actual Phoenix HTTPS stream message endpoint required')
    if config['OCI_STREAM_TOPIC_NAME'] != 'sds-production-pipeline':
        raise ValueError('Unexpected production stream name')
    if config['OCI_BACKUP_BUCKET'] != 'sds-ledger-backups':
        raise ValueError('Unexpected backup bucket name')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', config['OCI_OBJECT_STORAGE_NAMESPACE']):
        raise ValueError('Actual Object Storage namespace required')


def verify_resources(config, *, runner=subprocess.run):
    validate(config)
    def get(arguments):
        command = ['oci', *arguments, '--region', config['OCI_REGION'],
                   '--auth', 'instance_principal', '--output', 'json',
                   '--connection-timeout', '10', '--read-timeout', '30', '--max-retries', '2']
        result = runner(command, capture_output=True, text=True, check=True, timeout=120)
        return json.loads(result.stdout)['data']
    def require(condition):
        if not condition:
            raise ValueError('OCI resource mapping mismatch; no deployment performed')
    tenancy = get(['iam', 'tenancy', 'get', '--tenancy-id', config['OCI_TENANCY_OCID']])
    require(tenancy['id'] == config['OCI_TENANCY_OCID'])
    compartment = config['OCI_COMPARTMENT_OCID']
    if compartment != config['OCI_TENANCY_OCID']:
        # Follow nested compartment parents to the configured tenancy.
        parent, visited = compartment, set()
        while parent != config['OCI_TENANCY_OCID']:
            require(parent not in visited and len(visited) < 32)
            visited.add(parent)
            details = get(['iam', 'compartment', 'get', '--compartment-id', parent])
            require(details['id'] == parent and details['lifecycle-state'] == 'ACTIVE')
            parent = details['compartment-id']
    pool = get(['streaming', 'admin', 'stream-pool', 'get',
                '--stream-pool-id', config['OCI_STREAM_POOL_OCID']])
    require(pool['id'] == config['OCI_STREAM_POOL_OCID'] and
            pool['compartment-id'] == compartment and pool['lifecycle-state'] == 'ACTIVE')
    stream = get(['streaming', 'admin', 'stream', 'get', '--stream-id', config['OCI_STREAM_OCID']])
    require(stream['id'] == config['OCI_STREAM_OCID'] and stream['compartment-id'] == compartment
            and stream['stream-pool-id'] == config['OCI_STREAM_POOL_OCID']
            and stream['name'] == config['OCI_STREAM_TOPIC_NAME'] and stream['lifecycle-state'] == 'ACTIVE'
            and stream['messages-endpoint'].rstrip('/') == config['OCI_STREAM_ENDPOINT'].rstrip('/'))
    function = get(['fn', 'function', 'get', '--function-id', config['OCI_FUNCTION_OCID']])
    require(function['id'] == config['OCI_FUNCTION_OCID'] and
            function['compartment-id'] == compartment and function['lifecycle-state'] == 'ACTIVE')
    namespace = get(['os', 'ns', 'get'])
    require(namespace == config['OCI_OBJECT_STORAGE_NAMESPACE'])
    bucket = get(['os', 'bucket', 'get', '--namespace-name', namespace,
                  '--bucket-name', config['OCI_BACKUP_BUCKET']])
    require(bucket['name'] == config['OCI_BACKUP_BUCKET'] and bucket['compartment-id'] == compartment
            and bucket['namespace'] == namespace and bucket['public-access-type'] == 'NoPublicAccess'
            and bucket['storage-tier'] == 'Standard')
    return {'status': 'RESOURCE_IDENTITIES_VERIFIED', 'production_ready': False,
            'routing_verified': False, 'transaction_verified': False, 'backup_verified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--verify-live', action='store_true', help='Perform read-only OCI API checks')
    args = parser.parse_args()
    config = load_env(args.config)
    if args.verify_live:
        print(json.dumps(verify_resources(config)))
    else:
        print('Configuration syntax accepted; OCI identities remain unverified. No OCI calls performed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise SystemExit('OCI preflight failed: ' + str(error))
