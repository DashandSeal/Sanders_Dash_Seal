"""Local model transport for diagnosis; generated text never grants authority.

Uses the chat-completions protocol supported by a self-hosted llama.cpp server.
No provider credentials, remote paid endpoints, redirects, shell tools or model
downloads are used. A configured inference service must actually respond before
a result is labeled model-assisted.
"""
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from .operational_probes import NoRedirect
from .upgrade_sidecar import CORE_LAWS


class InferenceUnavailable(RuntimeError):pass


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def constant(value):raise ValueError('Nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


class LocalInferenceClient:
    def __init__(self,endpoint,model,*,timeout=30):
        if not isinstance(endpoint,str):raise ValueError('Local endpoint must be text')
        target=urlsplit(endpoint)
        if (target.scheme!='http' or target.hostname not in ('127.0.0.1','localhost','::1')
                or target.username or target.password or target.query or target.fragment
                or target.path!='/v1/chat/completions' or target.port is None
                or not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}',model)
                or type(timeout) not in (int,float) or not 0<timeout<=120):
            raise ValueError('Explicit local model endpoint and identity required')
        self.endpoint,self.model,self.timeout=endpoint,model,timeout
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def diagnose(self,grounded):
        system=('You are the Sanders Dash & Seal diagnostic reasoning component. '
            'Return only a JSON object with hypotheses (an array of objects with '
            'statement and evidence_sha256) and counterevidence (an array of strings). '
            'Hypotheses are unproven. Do not claim a repair, authority, signatures, '
            'verified cause or successful execution. No tools or commands. '
            'Use only the supplied measured evidence. Governing laws:\n'+
            '\n'.join(str(n)+'. '+law for n,law in enumerate(CORE_LAWS,1)))
        request={'model':self.model,'stream':False,'temperature':0,'max_tokens':1024,
            'response_format':{'type':'json_object'},'messages':[
                {'role':'system','content':system},
                {'role':'user','content':json.dumps(grounded,sort_keys=True,allow_nan=False)}]}
        raw=json.dumps(request,allow_nan=False).encode()
        if len(raw)>16384:raise InferenceUnavailable('DIAGNOSTIC_INPUT_TOO_LARGE')
        try:
            with self.opener.open(Request(self.endpoint,data=raw,
                    headers={'Content-Type':'application/json'},method='POST'),timeout=self.timeout) as response:
                if response.status!=200:raise ValueError('Inference failed')
                payload=response.read(65537)
            if len(payload)>65536:raise ValueError('Oversized inference response')
            answer=strict_json(payload)
            choices=answer['choices']
            if not isinstance(choices,list) or len(choices)!=1:raise ValueError('Ambiguous response')
            choice=choices[0];message=choice['message']
            if (choice.get('finish_reason')!='stop' or message.get('role')!='assistant'
                    or message.get('tool_calls') or message.get('function_call')
                    or not isinstance(message.get('content'),str)):
                raise ValueError('Incomplete or executable model response')
            result=strict_json(message['content'])
            if not isinstance(result,dict) or set(result)!={'hypotheses','counterevidence'}:
                raise ValueError('Invalid diagnostic result')
            hypotheses=result['hypotheses'];counter=result['counterevidence']
            if not isinstance(hypotheses,list) or not 1<=len(hypotheses)<=8:
                raise ValueError('Missing bounded hypotheses')
            for hypothesis in hypotheses:
                if (not isinstance(hypothesis,dict) or set(hypothesis)!={'statement','evidence_sha256'}
                        or not isinstance(hypothesis['statement'],str)
                        or not 1<=len(hypothesis['statement'])<=1000
                        or hypothesis['evidence_sha256']!=grounded['evidence']['sha256']):
                    raise ValueError('Model cited unsupported evidence')
            if (not isinstance(counter,list) or len(counter)>8
                    or any(not isinstance(text,str) or len(text)>1000 for text in counter)):
                raise ValueError('Invalid counterevidence')
            return result
        except Exception:
            # Do not expose arbitrary service responses, private prompts or URLs.
            raise InferenceUnavailable('LOCAL_INFERENCE_NOT_CONFIRMED') from None


def configured_client(path=Path('/run/sds/ai-model.json')):
    path=Path(path)
    if not path.exists():return None
    info=path.stat()
    if path.is_symlink() or info.st_uid!=0 or info.st_mode & 0o027 or info.st_size>4096:
        raise ValueError('Protected local inference configuration required')
    config=strict_json(path.read_text())
    if not isinstance(config,dict) or set(config)!={'endpoint','model'}:
        raise ValueError('Invalid inference configuration')
    return LocalInferenceClient(config['endpoint'],config['model'])
