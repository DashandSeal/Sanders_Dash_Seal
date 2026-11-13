"""Load only the owner's designated provider configuration from OCI Vault."""
import base64
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

NAME='sds-runtime-provider-config'
FIELDS={'stripe_api_key','stripe_webhook_secret','stripe_livemode',
        'signwell_api_key','signwell_test_mode','bluenotary_api_key'}


def command(args,runner=subprocess.run):
    result=runner(['oci',*args,'--region','us-phoenix-1','--auth','instance_principal',
        '--output','json','--connection-timeout','5','--read-timeout','15','--max-retries','1'],
        check=True,capture_output=True,text=True,timeout=60)
    return json.loads(result.stdout)


def retrieve(compartment,api=command):
    secrets=api(['vault','secret','list','--compartment-id',compartment,'--all'])['data']
    matches=[item for item in secrets if item.get('secret-name')==NAME and item.get('lifecycle-state')=='ACTIVE']
    if not matches:return None
    if len(matches)!=1:raise ValueError('Ambiguous designated provider configuration')
    record=api(['secrets','secret-bundle','get','--secret-id',matches[0]['id'],'--stage','CURRENT'])['data']
    content=record['secret-bundle-content']
    if content.get('content-type')!='BASE64':raise ValueError('Unexpected secret encoding')
    raw=base64.b64decode(content['content'],validate=True)
    if len(raw)>8192:raise ValueError('Provider configuration is too large')
    return validate(json.loads(raw))


def validate(data):
    if not isinstance(data,dict) or set(data)-FIELDS:raise ValueError('Invalid provider configuration fields')
    if any(type(data.get(k,default)) is not bool for k,default in
           (('stripe_livemode',False),('signwell_test_mode',False))):raise ValueError('Invalid provider environment')
    for name in ('stripe_api_key','stripe_webhook_secret','signwell_api_key','bluenotary_api_key'):
        if name in data and (not isinstance(data[name],str) or not 8<=len(data[name])<=4096
                or any(ord(c)<33 or ord(c)>126 for c in data[name])):
            raise ValueError('Invalid credential value')
    key=data.get('stripe_api_key')
    prefix=('rk_live_','sk_live_') if data.get('stripe_livemode',False) else ('rk_test_','sk_test_')
    if key is not None and not key.startswith(prefix):raise ValueError('Provider key environment mismatch')
    signing=data.get('stripe_webhook_secret')
    if signing is not None and not signing.startswith('whsec_'):raise ValueError('Invalid webhook secret')
    return data


def write_runtime_env(provider, env_path):
    """Write the systemd EnvironmentFile from validated Vault provider data.

    Only STRIPE_WEBHOOK_SECRET is exported: it is the one secret the
    wsgi-backend container needs from the host environment (see compose.yaml
    and deploy/sanders_manager.service). The file is root-owned, mode 0600,
    written atomically; no value is ever logged. A provider without a webhook
    secret leaves any existing file untouched. A secret that cannot be written
    as a plain KEY=value line raises instead of writing a broken file.
    """
    secret = provider.get('stripe_webhook_secret')
    if not secret:
        return False
    if not re.fullmatch(r'whsec_[A-Za-z0-9_]+', secret):
        raise ValueError('Invalid webhook secret for env file')
    env_path = Path(env_path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=env_path.parent, delete=False) as output:
        temporary = Path(output.name)
        os.chown(temporary, 0, 0)
        os.chmod(temporary, 0o600)
        output.write('STRIPE_WEBHOOK_SECRET=' + secret + '\n')
    os.replace(temporary, env_path)
    return True


def refresh(release_path=Path('/etc/sanders-dash-seal/release.json'),
            settings_path=Path('/etc/sanders-dash-seal/runtime/runtime.json'),
            env_path=Path('/etc/sanders-dash-seal/runtime.env'),*,api=command,restart=False):
    config=json.loads(release_path.read_text())
    provider=retrieve(config['compartment_id'],api)
    if provider is None:return 'PROVIDER_SECRET_NOT_CONFIGURED'
    write_runtime_env(provider, env_path)
    settings=json.loads(settings_path.read_text())
    previous={key:settings[key] for key in FIELDS if key in settings}
    if previous==provider:return 'PROVIDER_SECRET_UNCHANGED'
    for key in FIELDS:settings.pop(key,None)
    settings.update(provider)
    with tempfile.NamedTemporaryFile(mode='w',dir=settings_path.parent,delete=False) as output:
        temporary=Path(output.name);os.chown(temporary,0,10001);os.chmod(temporary,0o640)
        json.dump(settings,output);output.write('\n')
    os.replace(temporary,settings_path)
    if restart:
        # compose.yaml is the file the stack runs under (see deploy.sh);
        # `up -d` recreates wsgi-backend when its environment changed, so a
        # rotated secret takes effect. Plain `restart` would keep the old
        # container and its old environment.
        subprocess.run(['docker','compose','-p','sanders-dash-seal',
            '--project-directory','/opt/sanders-dash-seal',
            '-f','/opt/sanders-dash-seal/compose.yaml',
            '-f','/opt/sanders-dash-seal/deploy/compose.production.yml',
            'up','-d','wsgi-backend'],check=True,timeout=90,capture_output=True)
    return 'PROVIDER_SECRET_REFRESHED'


if __name__=='__main__':
    import sys
    if os.geteuid()!=0:raise SystemExit('Host secret refresh requires root')
    try:print(refresh(restart='--restart' in sys.argv))
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        # Never expose CLI stderr, secret bundle, key value or exception payload.
        print('PROVIDER_SECRET_REFRESH_FAILED',file=sys.stderr);raise SystemExit(1)
