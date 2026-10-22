"""Local OCI request rendering, function staging and explicit signed publishing.

Rendering/staging never executes OCI commands. Publishing is a separate action
against an existing stream and validates per-message admission, not business commit.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.parse

def ocid(value, kind):
    if not isinstance(value, str) or not re.fullmatch(r'ocid1\.' + kind + r'\.[A-Za-z0-9._:-]+', value):
        raise ValueError('Actual ' + kind + ' OCID required')
    return value


def requests(compartment_id, pool_id, stream_id, function_id, namespace):
    if not isinstance(namespace, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', namespace):
        raise ValueError('Actual Object Storage namespace required')
    ocid(compartment_id, '(?:compartment|tenancy)')
    ocid(pool_id, 'streampool')
    ocid(stream_id, 'stream')
    ocid(function_id, 'fnfunc')
    return {
        'pool.json': {'compartmentId': compartment_id, 'name': 'sds-production-pool'},
        'stream.json': {'streamPoolId': pool_id, 'name': 'sds-production-pipeline',
                        'partitions': 1, 'retentionInHours': 24},
        'connector.json': {'compartmentId': compartment_id,
            'displayName': 'sds-ledger-sink-connector',
            'source': {'kind': 'streaming', 'streamId': stream_id,
                       'cursor': {'kind': 'TRIM_HORIZON'}},
            'tasks': [{'kind': 'function', 'functionId': function_id,
                       'batchSizeInKbs': 1, 'batchTimeInSec': 5}],
            'target': {'kind': 'objectStorage', 'namespace': namespace,
                       'bucketName': 'sds-ledger-backups',
                       'objectNamePrefix': 'stream_receipts/',
                       'batchRolloverSizeInMBs': 1, 'batchRolloverTimeInMs': 60000}}
    }


def stage_function(destination):
    # Never overwrite an existing review/build directory or select original func.py
    # accidentally through Fn's default manifest lookup.
    source = Path(__file__).resolve().parent / 'sds-transaction-validator-fn'
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('integrated.py', 'requirements.txt', 'Dockerfile'):
        shutil.copyfile(source / name, destination / name)
    shutil.copyfile(source / 'func.integrated.yaml', destination / 'func.yaml')


def publish(event, stream_id, endpoint, *, runner=subprocess.run):
    from core_platform.stream_api import stream_signing_payload, strict_json
    ocid(stream_id, 'stream')
    stream_signing_payload(event)
    if not event['signature'] or event['signature'] == 'UNSIGNED':
        raise ValueError('Signed event required')
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in ('', '/') or parsed.port not in (None, 443)
            or not re.fullmatch(r'(?:cell-[a-z0-9-]+\.)?streaming\.[a-z0-9-]+\.oci\.oraclecloud\.com',
                                parsed.hostname or '')):
        raise ValueError('Actual OCI HTTPS streaming message endpoint required')
    value = json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(value) > 262144:
        raise ValueError('Event exceeds integrated backend allocation')
    message = {'key': base64.b64encode(event['actor'].encode()).decode(),
               'value': base64.b64encode(value).decode()}
    with tempfile.TemporaryDirectory(prefix='sds-producer-') as directory:
        path = Path(directory) / 'messages.json'
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            json.dump([message], handle)
        command = ['oci', 'streaming', 'stream', 'message', 'put', '--stream-id', stream_id,
            '--messages', 'file://' + str(path), '--endpoint', endpoint,
            '--auth', 'instance_principal', '--output', 'json', '--max-retries', '2',
            '--connection-timeout', '10', '--read-timeout', '30']
        response = runner(command, capture_output=True, text=True, check=True, timeout=120)
        data = strict_json(response.stdout)['data']
        entries = data.get('entries')
        if (data.get('failures') != 0 or not isinstance(entries, list) or len(entries) != 1
                or entries[0].get('error') or entries[0].get('offset') is None):
            raise ValueError('Streaming did not admit the event')
        return {'status': 'STREAM_ADMITTED', 'transaction_id': event['transaction_id'],
                'offset': entries[0]['offset']}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    render = sub.add_parser('render')
    for name in ('compartment-id', 'pool-id', 'stream-id', 'function-id', 'namespace'):
        render.add_argument('--' + name, required=True)
    render.add_argument('--output', required=True, type=Path)
    stage = sub.add_parser('stage-function')
    stage.add_argument('--output', required=True, type=Path)
    producer = sub.add_parser('publish')
    producer.add_argument('--stream-id', required=True)
    producer.add_argument('--endpoint', required=True)
    producer.add_argument('--event', required=True, type=Path)
    args = parser.parse_args()
    if args.action == 'render':
        result = requests(args.compartment_id, args.pool_id, args.stream_id, args.function_id, args.namespace)
        args.output.mkdir(parents=True, exist_ok=False)
        for name, body in result.items():
            (args.output / name).write_text(json.dumps(body, indent=2) + '\n')
        print('Rendered request files only. No OCI operation performed.')
    elif args.action == 'stage-function':
        stage_function(args.output)
        print('Staged integrated function only. No build or deployment performed.')
    else:
        from core_platform.stream_api import strict_json
        raw = args.event.read_bytes()
        if len(raw) > 262144:
            raise ValueError('Event too large')
        print(json.dumps(publish(strict_json(raw), args.stream_id, args.endpoint)))


if __name__ == '__main__':
    main()
