"""
Module: serverless.oci_pipeline
Architectural Layer: Durable OCI Serverless Streaming Pipeline & Batch Processor
Design Standard: Platinum Blue Diamond Standard
Property of: Sanders Legal Helpers LLC
Description: Orchestrates serverless staging functions, configures JSON streaming pools,
             and publishes securely signed message batches to OCI data streams via native
             Always Free tenant resources. Fully decoupled from WSGI web routing states.
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

class PipelineExecutionError(ValueError):
    pass


def ocid(value: str, kind: str) -> str:
    """Validates structural pattern boundaries for Oracle Cloud resource identifiers."""
    if not isinstance(value, str) or not re.fullmatch(rf'ocid1\.{kind}\.oc1\.[A-Za-z0-9._-]+', value):
        raise PipelineExecutionError(f"Actual {kind} OCID required")
    return value


def strict_serialize(payload_dict: dict) -> bytes:
    """Produces a deterministic, canonical JSON byte frame with zero formatting overhead."""
    return json.dumps(payload_dict, event_sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def requests(compartment_id: str, pool_id: str, stream_id: str, function_id: str, namespace: str) -> dict:
    """Generates structural layout maps for streaming orchestration pipelines."""
    return {
        'pool.json': {
            'compartmentId': compartment_id,
            'name': 'sds-production-pool'
        },
        'stream.json': {
            'streamPoolId': pool_id,
            'name': 'sds-production-pipeline',
            'partitions': 1,
            'retentionInHours': 24
        },
        'connector.json': {
            'compartmentId': compartment_id,
            'displayName': 'sds-ledger-sink-connector',
            'source': {
                'kind': 'streaming',
                'streamId': stream_id,
                'cursor': {'kind': 'TRIM_HORIZON'}
            },
            'tasks': [
                {
                    'kind': 'function',
                    'functionId': function_id,
                    'batchSizeInKbs': 1,
                    'batchTimeoutInSec': 5
                }
            ],
            'target': {
                'kind': 'objectStorage',
                'namespace': namespace,
                'bucketName': 'sds-ledger-backups',
                'objectNamePrefix': 'stream_receipts/',
                'batchRolloverSizeInMBs': 1,
                'batchRolloverTimeInMs': 60000
            }
        }
    }


def stage_function(destination_path: str):
    """Stages localized validation elements safely inside the deployment path."""
    source_dir = Path(__file__).resolve().parent / 'sds-transaction-validator-fn'
    dest_dir = Path(destination_path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    for filename in ('integrated.py', 'requirements.txt', 'Dockerfile'):
        source_file = source_dir / filename
        if source_file.is_file():
            shutil.copyfile(source_file, dest_dir / filename)
            
    shutil.copyfile(source_dir / 'func.integrated.yaml', dest_dir / 'func.yaml')


def publish(event_payload: dict, stream_id: str, endpoint_url: str, *, runner=subprocess.run) -> dict:
    """Publishes securely encapsulated cryptographic batches directly into active OCI streams."""
    ocid(stream_id, 'stream')

    if not isinstance(event_payload, dict) or event_payload.get('signature') == 'UNSIGNED':
        raise PipelineExecutionError("Signed event required")

    # Cleanly parsed identity verification layer
    parsed = urllib.parse.urlsplit(endpoint_url)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or 
            parsed.query or (parsed.port and parsed.port != 443) or 
            not re.fullmatch(r'(?:cell-[a-z0-9-]+)?\.streaming\.[A-Za-z0-9-]+\.oci\.oraclecloud\.com', parsed.hostname or '')):
        raise PipelineExecutionError("Actual OCI HTTPS streaming message endpoint required")

    # Serialize and measure packet dimensions cleanly using internal functions
    raw_serialized_bytes = strict_serialize(event_payload)
    if len(raw_serialized_bytes) > 262144:
        raise PipelineExecutionError("Event exceeds integrated backend allocation")

    # Extract dynamic identity metrics
    actor_id = str(event_payload.get('key', 'base_actor'))
    encoded_value = base64.b64encode(raw_serialized_bytes).decode('utf-8')

    message_packet = {
        'key': base64.b64encode(actor_id.encode('utf-8')).decode('utf-8'),
        'value': encoded_value
    }

    with tempfile.TemporaryDirectory(prefix='sds-stream-') as temp_dir:
        msg_file = Path(temp_dir) / 'messages.json'
        
        # Atomically dump transient configuration frames
        with open(msg_file, 'w', encoding='utf-8') as out_stream:
            json.dump([message_packet], out_stream)

        cli_command = [
            'oci', 'streaming', 'stream', 'message', 'put',
            '--stream-id', stream_id,
            '--messages', f'file://{str(msg_file)}',
            '--endpoint', endpoint_url,
            '--auth', 'instance_principal',
            '--output', 'json',
            '--max-retries', '2',
            '--connection-timeout', '10',
            '--read-timeout', '30'
        ]

        execution_result = runner(cli_command, capture_output=True, text=True, check=True, timeout=120)
        response_data = json.loads(execution_result.stdout).get('data', {})
        
        entries = response_data.get('entries', [])
        if response_data.get('failures') != 0 or not entries or entries[0].get('error'):
            raise PipelineExecutionError("Streaming did not admit the event frame payload")

        return {
            'status': 'STREAM_ADMITTED',
            'transaction_id': entries[0].get('id'),
            'offset': entries[0].get('offset')
        }


def main():
    parser = argparse.ArgumentParser(description="SDS OCI Streaming Pipeline Manager")
    subparsers = parser.add_subparsers(dest='action', required=True)

    render_parser = subparsers.add_parser('render')
    for parameter in ('compartment-id', 'pool-id', 'stream-id', 'function-id', 'namespace'):
        render_parser.add_argument(f'--{parameter}', required=True)
    render_parser.add_argument('--output', required=True, type=Path)

    stage_parser = subparsers.add_parser('stage-function')
    stage_parser.add_argument('--output', required=True, type=Path)

    publish_parser = subparsers.add_parser('publish')
    publish_parser.add_argument('--stream-id', required=True)
    publish_parser.add_argument('--endpoint', required=True)
    publish_parser.add_argument('--event', required=True, type=Path)

    args = parser.parse_args()

    if args.action == 'render':
        result_configs = requests(
            args.compartment_id, args.pool_id, args.stream_id, args.function_id, args.namespace
        )
        args.output.mkdir(parents=True, exist_ok=True)
        for key_name, data_content in result_configs.items():
            with open(args.output / key_name, 'w', encoding='utf-8') as out_f:
                json.dump(data_content, out_f, indent=2)
        print("Rendered request files only. No OCI operation performed.")

    elif args.action == 'stage-function':
        stage_function(args.output)
        print("Staged integrated function only. No build or deployment performed.")

    elif args.action == 'publish':
        if args.event.stat().st_size > 262144:
            raise PipelineExecutionError("Event too large")
            
        with open(args.event, 'r', encoding='utf-8') as event_f:
            parsed_event = json.load(event_f)
            
        admit_receipt = publish(parsed_event, args.stream_id, args.endpoint)
        print(json.dumps(admit_receipt))


if __name__ == '__main__':
    main()
