"""Transfer supplied Actions secrets to the designated existing OCI Vault secret.

Secret bytes are outside Terraform, Object Storage and agent command text. This
module creates no account, key, vault or service and prints no secret values.
"""
import base64
import json
import os
from pathlib import Path
import tempfile
from deploy.refresh_provider_secrets import NAME, retrieve, validate


ENV_FIELDS = {'STRIPE_SECRET_KEY': 'stripe_api_key', 'STRIPE_API_KEY': 'stripe_api_key',
              'STRIPE_WEBHOOK_SECRET': 'stripe_webhook_secret',
              'SIGNWELL_API_KEY': 'signwell_api_key', 'BLUENOTARY_API_KEY': 'bluenotary_api_key'}


def environment_values(environment):
    values = {}
    for source, target in ENV_FIELDS.items():
        value = environment.get(source, '')
        if value:
            if target in values and values[target] != value:
                raise ValueError('Conflicting Stripe credential fields')
            values[target] = value
    for source, target in [('STRIPE_LIVEMODE', 'stripe_livemode'), ('SIGNWELL_TEST_MODE', 'signwell_test_mode')]:
        value = environment.get(source, '')
        if value:
            if value not in ('true', 'false'):
                raise ValueError('Provider environment must be true or false')
            values[target] = value == 'true'
    return values


def publish(compartment, supplied, api):
    if not supplied:
        return 'PROVIDER_CONFIGURATION_PRESERVED'
    records = api(['vault', 'secret', 'list', '--compartment-id', compartment, '--all'])['data']
    selected = [r for r in records if r.get('secret-name') == NAME and r.get('lifecycle-state') == 'ACTIVE']
    if len(selected) != 1:
        raise ValueError('Provider credential destination requires one existing ACTIVE sds-runtime-provider-config Vault secret')
    secret_id = selected[0]['id']
    # Read metadata before the current version so a concurrent write cannot be overwritten.
    metadata = api(['vault', 'secret', 'get', '--secret-id', secret_id])
    etag = metadata.get('etag')
    if not isinstance(etag, str) or not etag:
        raise ValueError('Provider credential destination did not supply a concurrency etag')
    previous = retrieve(compartment, api)
    if previous is None:
        raise ValueError('Provider credential destination changed during refresh')
    merged = dict(previous); merged.update(supplied); validate(merged)
    raw = json.dumps(merged, sort_keys=True, separators=(',', ':')).encode()
    if len(raw) > 8192:
        raise ValueError('Provider configuration is too large')
    if merged == previous:
        return 'PROVIDER_SECRET_UNCHANGED'
    with tempfile.TemporaryDirectory(prefix='sds-provider-custody-') as folder:
        path = Path(folder) / 'vault-update.json'
        path.touch(mode=0o600)
        path.write_text(json.dumps({'secretContentContent': base64.b64encode(raw).decode(),
                                   'secretContentStage': 'CURRENT'}))
        api(['vault', 'secret', 'update-base64', '--secret-id', secret_id, '--if-match', etag,
             '--from-json', 'file://' + str(path), '--force', '--wait-for-state', 'ACTIVE',
             '--max-wait-seconds', '120'])
    # Verify the actual CURRENT bundle, not merely an HTTP/API submission acknowledgement.
    if retrieve(compartment, api) != merged:
        raise ValueError('Provider credential transfer did not produce the expected CURRENT configuration')
    return 'PROVIDER_SECRET_TRANSFERRED'
