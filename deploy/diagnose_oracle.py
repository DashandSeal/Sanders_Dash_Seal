"""Read-only retrieval of the selected stack host's recent agent executions."""
import json
import os
import re

from .activate_on_oracle import cli
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


def diagnose(stack_id,api=cli):
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
        command=record.get('command-id')
        if not command:continue
        actual=api(['instance-agent','command-execution','get',
                    '--command-id',command,'--instance-id',config['instance_id']])['data']
        content=actual.get('content') or {}
        results.append({'command_id':command,'state':actual.get('lifecycle-state'),
            'exit_code':content.get('exit-code'),'output':safe_lines(content.get('text')),
            'message':safe_lines(content.get('message'))})
    return {'cloud_changes_performed':False,'executions':results}


def main():
    with credentials():
        result=diagnose(os.environ.get('OCI_STACK_OCID',''))
    print(json.dumps(result))


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('ORACLE_READ_ONLY_DIAGNOSIS_FAILED')
