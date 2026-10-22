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
    result=runner(['oci',*args,'--region',REGION,'--output','json','--connection-timeout','10',
        '--read-timeout','60','--max-retries','2'],capture_output=True,text=True,check=True,timeout=180)
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
        if actions not in (['create'],['update']):
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
            if record.get('exit-code') != 0:
                raise ValueError('Agent success state without exit code zero')
            return record
        if state in ('FAILED','TIMED_OUT','CANCELED'):
            raise ValueError('Installation '+state+'; inspect Oracle Run Command output')
        pause(20)
    raise TimeoutError('Agent did not complete; check plugin permissions and egress')


def deploy(stack_id, api=cli):
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
