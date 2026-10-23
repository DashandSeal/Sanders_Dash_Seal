"""Read-only retrieval of the selected stack host's recent agent executions."""
import json
import os
import re
import sys

from .activate_on_oracle import cli,wait_command
from .gitops_deploy import credentials


def safe_lines(text):
    if not isinstance(text,str):return []
    text=re.sub(r'-----BEGIN[^\n]*-----.*?(?:-----END[^\n]*-----|\Z)',
                '[private key omitted]',text,flags=re.S)
    lines=[]
    for line in text.splitlines()[-60:]:
        if re.search(r'password|secret|token|private.?key|authorization|cookie|credential|api.?key|fingerprint',line,re.I):
            continue
        if re.fullmatch(r'\s*[A-Za-z0-9+/=]{40,}\s*',line):continue
        line=re.sub(r'https?://\S+','[URL]',line)
        line=''.join(c for c in line if c.isprintable())[:500]
        if line.strip():lines.append(line)
    return lines[-30:]


def diagnose(stack_id,api=cli,*,probe_host=False):
    if not re.fullmatch(r'ocid1\.ormstack\.[A-Za-z0-9.]+',stack_id):
        raise ValueError('Actual stack identifier required')
    state=json.loads(api(['resource-manager','stack','get-stack-tf-state',
                         '--stack-id',stack_id,'--file','-'],raw=True))
    outputs=state['outputs']
    config=outputs.get('application_install_command',outputs.get('existing_install_command'))['value']
    records=api(['instance-agent','command-execution','list',
        '--compartment-id',config['compartment_id'],'--instance-id',config['instance_id'],
        '--sort-by','TIMECREATED','--sort-order','DESC','--limit','5'])['data']
    results=[]
    for record in records:
        command=record.get('instance-agent-command-id')
        if not isinstance(command,str) or not command:
            raise ValueError('Oracle execution summary lacks its documented command identifier')
        actual=api(['instance-agent','command-execution','get',
                    '--command-id',command,'--instance-id',config['instance_id']])['data']
        content=actual.get('content') or {}
        results.append({'command_id':command,'state':actual.get('lifecycle-state'),
            'exit_code':content.get('exit-code'),'output':safe_lines(content.get('text')),
            'message':safe_lines(content.get('message'))})
    result={'cloud_changes_performed':False,'executions':results,
            'status':'EXECUTIONS_OBSERVED' if results else 'NO_EXECUTIONS_OBSERVED'}
    if probe_host:
        # Fixed read-only OS queries. No customer files, settings, keys, source
        # changes, privilege changes, service restarts or package installation.
        script='''#!/bin/bash
exec 2>&1
echo SDS_HOST_CHECK_BEGIN
id -un
id -u
if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    echo "OS_ID=$ID OS_VERSION=$VERSION_ID"
fi
sudo -n /usr/bin/id -u
echo "SUDO_ID_EXIT=$?"
sudo -n -l /bin/bash
echo "SUDO_BASH_CHECK_EXIT=$?"
echo SDS_HOST_CHECK_END
exit 0
'''
        content={'source':{'sourceType':'TEXT','text':script},'output':{'outputType':'TEXT'}}
        command=api(['instance-agent','command','create','--compartment-id',config['compartment_id'],
            '--target',json.dumps({'instanceId':config['instance_id']}),'--content',json.dumps(content),
            '--timeout-in-seconds','60','--display-name','Sanders Dash & Seal read-only host inspection'])['data']['id']
        record=wait_command(command,config['instance_id'],api,timeout=180)
        result['host_probe']={'command_id':command,'output':safe_lines((record.get('content') or {}).get('text'))}
        result['cloud_changes_performed']=True
        result['change_scope']='CREATED_READ_ONLY_INSPECTION_COMMAND_RECORD'
        result['infrastructure_changes_performed']=False
    return result


def main():
    with credentials():
        result=diagnose(os.environ.get('OCI_STACK_OCID',''),probe_host='--probe-host' in sys.argv[1:])
    print(json.dumps(result))


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('ORACLE_READ_ONLY_DIAGNOSIS_FAILED')
