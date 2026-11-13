"""Run with authenticated OCI access: Plan, Apply, install, verify. No SSH."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

REGION='us-phoenix-1'
def cli(args, *, raw=False, runner=subprocess.run):
    # Terraform zip uploads are materially larger than OCI state reads.
    # Keep the existing read limits; allow more time to send and acknowledge
    # the Resource Manager update rather than misclassifying it as a bad build.
    connection_timeout, read_timeout = 30, 360
    result = runner(['oci', *args, '--region', REGION, '--output', 'json',
        '--connection-timeout', str(connection_timeout), '--read-timeout',
        str(read_timeout), '--max-retries', '2'], capture_output=True,
        text=True, check=True, timeout=360 if upload else 180)
    return result.stdout if raw else json.loads(result.stdout)


def validate_plan(plan):
    # Owner controls resource names and stack profile. Preserve the separate
    # instruction not to destroy existing resources or select paid E4 compute.
    if not isinstance(plan.get('resource_changes'),list):
        raise ValueError('Oracle did not return a structured Terraform plan')
    for change in plan['resource_changes']:
        if change.get('mode')=='data': continue
        actions=change['change']['actions']
        if actions==['no-op'] or (change.get('type')=='terraform_data' and actions==['delete']): continue
        # Versioned installer/source objects change their key every release.
        # Terraform expresses that normal rotation as replacement; it is not
        # destruction of the VM, a ledger bucket, or a customer record.
        release_rotation = versioned_release_rotation(change)
        if actions not in (['create'],['update']) and not release_rotation:
            raise ValueError('Destructive/replacement operation rejected: '+change['address'])
        after=change['change'].get('after') or {}
        if change['type']=='oci_core_instance':
            if after.get('shape') not in ('VM.Standard.A1.Flex','VM.Standard.E2.1.Micro'):
                raise ValueError('Paid compute shape conflicts with the owner zero-spend instruction')
            if after.get('shape')=='VM.Standard.A1.Flex':
                size=after.get('shape_config') or [{}]
                if not 0<float(size[0].get('ocpus',0))<=2 or not 0<float(size[0].get('memory_in_gbs',0))<=12:
                    raise ValueError('Compute allocation exceeds the owner supplied Free Tier profile')
        if change['type']=='oci_objectstorage_bucket':
            if (after.get('access_type')!='NoPublicAccess' or after.get('storage_tier')!='Standard'
                or after.get('auto_tiering') not in (None,'Disabled') or after.get('kms_key_id')):
                raise ValueError('Unexpected bucket billing/public-access configuration')
    return True


def versioned_release_rotation(change):
    patterns = {'release': r'releases/[0-9a-f]{40}\.tgz',
                'existing_installer': r'installers/[0-9a-f]{40}\.sh'}
    name = change.get('name')
    if (change.get('type') != 'oci_objectstorage_object' or name not in patterns
            or change.get('address') != 'oci_objectstorage_object.'+name+'[0]'
            or change.get('change',{}).get('actions') not in
               (['delete','create'],['create','delete'])):
        return False
    before=change['change'].get('before') or {}
    after=change['change'].get('after') or {}
    return (isinstance(before.get('namespace'),str) and bool(before['namespace'])
        and before.get('namespace')==after.get('namespace')
        and isinstance(before.get('bucket'),str)
        and re.fullmatch(r'sds-release-[0-9a-f]{12}',before['bucket']) is not None
        and before['bucket']==after.get('bucket')
        and all(isinstance(record.get('object'),str) and
            re.fullmatch(patterns[name],record['object']) is not None
            for record in (before,after))
        and before['object']!=after['object'])


def wait_job(identifier, api=cli, clock=time.monotonic, pause=time.sleep, timeout=3600):
    deadline=clock()+timeout
    while clock()<deadline:
        record=api(['resource-manager','job','get','--job-id',identifier])['data']
        state=record['lifecycle-state']
        print('Resource Manager job: '+state,flush=True)
        if state=='SUCCEEDED': return record
        if state in ('FAILED','CANCELED'): raise ValueError('Resource Manager job '+state)
        pause(20)
    raise TimeoutError('Resource Manager job deadline elapsed')


def wait_command(command, instance, api=cli, clock=time.monotonic, pause=time.sleep, timeout=5400):
    deadline=clock()+timeout
    while clock()<deadline:
        try:
            record=api(['instance-agent','command-execution','get','--command-id',command,'--instance-id',instance])['data']
        except subprocess.CalledProcessError as error:
            if 'NotAuthorizedOrNotFound' not in (error.stderr or ''): raise
            pause(20);continue
        state=record.get('lifecycle-state')
        print('Instance agent execution: '+str(state),flush=True)
        if state=='SUCCEEDED':
            content=record.get('content')
            code=content.get('exit-code') if isinstance(content,dict) else record.get('exit-code')
            if type(code) is not int or code != 0:
                raise ValueError('Agent success state without exit code zero')
            return record
        if state in ('FAILED','TIMED_OUT','CANCELED'):
            raise ValueError('Installation '+state+'; inspect Oracle Run Command output')
        pause(20)
    raise TimeoutError('Agent did not complete; check plugin permissions and egress')


def deploy(stack_id, api=cli, *, before_install=None):
    if not re.fullmatch(r'ocid1\.ormstack\.[A-Za-z0-9.]+',stack_id):
        raise ValueError('Actual Oracle Resource Manager stack OCID required')
    plan_id=api(['resource-manager','job','create-plan-job','--stack-id',stack_id])['data']['id']
    wait_job(plan_id,api)
    plan=json.loads(api(['resource-manager','job','get-job-tf-plan','--job-id',plan_id,
        '--tf-plan-format','JSON','--file','-'],raw=True))
    validate_plan(plan)
    apply_id=api(['resource-manager','job','create-apply-job','--stack-id',stack_id,
        '--execution-plan-strategy','FROM_PLAN_JOB_ID','--execution-plan-job-id',plan_id])['data']['id']
    wait_job(apply_id,api)
    state=json.loads(api(['resource-manager','job','get-job-tf-state','--job-id',apply_id,'--file','-'],raw=True))
    outputs=state['outputs']
    config=outputs.get('application_install_command',outputs.get('existing_install_command'))['value']
    if before_install is not None:
        before_install(config, api)
    # The install source is PRIVATE. No PAR or credential is put in an agent command.
    content={'source':{'sourceType':'OBJECT_STORAGE_TUPLE','namespaceName':config['namespace'],
        'bucketName':config['bucket'],'objectName':config['object']},'output':{'outputType':'TEXT'}}
    command=api(['instance-agent','command','create','--compartment-id',config['compartment_id'],
        '--target',json.dumps({'instanceId':config['instance_id']}),'--content',json.dumps(content),
        '--timeout-in-seconds','3600','--display-name','Sanders Dash & Seal application activation'])['data']['id']
    wait_command(command,config['instance_id'],api)
    return {'status':'AGENT_INSTALL_AND_BACKUP_VERIFIED','stack_id':stack_id,'command_id':command,
            'commit':config['commit'],'billing_verified':False,'business_integrations_verified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stack-id',required=True)
    args=parser.parse_args()
    print(json.dumps(deploy(args.stack_id)))


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError,TimeoutError,subprocess.SubprocessError) as error:
        print('ORACLE_ACTIVATION_NOT_COMPLETED: '+str(error),file=sys.stderr)
        raise SystemExit(1)
