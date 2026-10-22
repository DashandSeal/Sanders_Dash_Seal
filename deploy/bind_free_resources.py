"""Bind provisioned OCI resources to real host backup and metric operations."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def cli(args, runner=subprocess.run):
    result = runner(['oci', *args, '--region', 'us-phoenix-1', '--auth', 'instance_principal',
        '--output', 'json', '--connection-timeout', '10', '--read-timeout', '30', '--max-retries', '2'],
        capture_output=True, text=True, check=True, timeout=120)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def validate(config):
    required = {'schema', 'instance_id', 'compartment_id', 'namespace', 'region', 'bucket',
                'topic_id', 'metric_namespace', 'budget_bytes', 'max_snapshot_bytes'}
    if set(config) != required or config['schema'] != 1 or config['region'] != 'us-phoenix-1':
        raise ValueError('Invalid provisioned resource binding')
    for key, prefix in [('instance_id','ocid1.instance.'), ('compartment_id','ocid1.'),
                        ('topic_id','ocid1.onstopic.')]:
        if not isinstance(config[key], str) or not config[key].startswith(prefix):
            raise ValueError('Invalid resource identity: ' + key)
    if (not isinstance(config['bucket'],str) or not config['bucket'].startswith('sds-ledger-backups-')
        or not isinstance(config['namespace'],str) or not config['namespace']):
        raise ValueError('Invalid private backup target')
    if config['metric_namespace'] != 'sds_platform':
        raise ValueError('Unexpected metric namespace')
    if (type(config['budget_bytes']) is not int or type(config['max_snapshot_bytes']) is not int
        or not 0 < config['max_snapshot_bytes'] <= 1000000000
        or not config['max_snapshot_bytes'] <= config['budget_bytes'] <= 20000000000):
        raise ValueError('Invalid backup allocation')
    return config


def private_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        os.chmod(temporary, 0o600)
        json.dump(value, output)
        output.write('\n')
    os.replace(temporary, path)


def verify(config, api=cli):
    validate(config)
    bucket = api(['os','bucket','get','--namespace-name',config['namespace'],
                  '--bucket-name',config['bucket']])['data']
    if (bucket.get('public-access-type') != 'NoPublicAccess' or bucket.get('storage-tier') != 'Standard'
        or bucket.get('compartment-id') != config['compartment_id']):
        raise ValueError('Backup bucket is not the selected private Standard resource')
    topic = api(['ons','topic','get','--topic-id',config['topic_id']])['data']
    if topic.get('lifecycle-state') != 'ACTIVE' or topic.get('compartment-id') != config['compartment_id']:
        raise ValueError('Monitoring topic is not active in selected compartment')
    return {'private_backup_bucket_verified': True, 'notification_topic_verified': True,
            'billing_verified': False, 'other_catalog_services_provisioned': False}


def metric(config, name, value, api=cli):
    data = [{'compartmentId':config['compartment_id'], 'namespace':'sds_platform', 'name':name,
        'dimensions':{'resourceId':config['instance_id']},
        'datapoints':[{'timestamp':datetime.now(timezone.utc).isoformat(), 'value':value, 'count':1}]}]
    api(['monitoring','metric-data','post','--metric-data',json.dumps(data)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('/etc/sanders-dash-seal/resources.json'))
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--backup', action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0: raise ValueError('Host resource binding requires root')
    config=validate(json.loads(args.config.read_text()))
    result=verify(config)
    if args.install:
        private_json('/etc/sanders-dash-seal/backup.json', {key:config[key] for key in
            ('namespace','region','bucket','budget_bytes','max_snapshot_bytes')})
        root=Path(__file__).resolve().parents[1]
        for name in ('sanders-resource-check.service','sanders-resource-check.timer'):
            subprocess.run(['install','-m','0644',str(root/'deploy/systemd'/name),'/etc/systemd/system/'],check=True)
        subprocess.run(['systemctl','daemon-reload'],check=True)
        subprocess.run(['systemctl','enable','--now','sanders-resource-check.timer','sanders-ledger-backup.timer'],check=True)
    if args.backup:
        try:
            subprocess.run(['/bin/bash','/opt/sanders-dash-seal/deploy_backup.sh'],check=True,timeout=1800)
        except (subprocess.SubprocessError,OSError):
            metric(config,'BackupVerified',0)
            raise
        metric(config,'BackupVerified',1)
        result['backup_restore_verified']=True
    metric(config,'PlatformHeartbeat',1)
    private_json('/var/lib/sanders-dash-seal/resource-status.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print('RESOURCE_ACTIVATION_FAILED: '+str(error),file=sys.stderr)
        raise SystemExit(1)
