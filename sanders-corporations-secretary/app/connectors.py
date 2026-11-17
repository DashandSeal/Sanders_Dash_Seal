"""Public-data connector that never sends company records to GitHub."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from . import db, intelligence

GITHUB_REPO='DashandSeal/Sanders_Dash_Seal'
GITHUB_COMMITS='https://api.github.com/repos/'+GITHUB_REPO+'/commits?per_page=1'

def read_github_head(fetcher=None)->dict:
    # Only a fixed public URL; not a user-defined arbitrary URL, so no SSRF input.
    def default_fetch():
        req=Request(GITHUB_COMMITS,headers={'User-Agent':'Sanders-Corporations-Secretary/0.2','Accept':'application/vnd.github+json'})
        with urlopen(req,timeout=8) as response:return json.load(response)
    payload=fetcher() if fetcher else default_fetch()
    if not isinstance(payload,list) or not payload:raise ValueError('GitHub returned no commit')
    data=payload[0]; sha=data['sha'];url=data['html_url']
    if not re.fullmatch('[a-f0-9]{40}',sha) or not url.startswith('https://github.com/'+GITHUB_REPO+'/commit/'):
        raise ValueError('Unexpected GitHub commit identity')
    return {'sha':sha,'url':url,'message':str(data['commit']['message']).split('\n')[0][:180],'retrieved_at':db.utc_now(),'source':'GitHub public REST API'}

def sync_public_github(fetcher=None)->dict:
    commit=read_github_head(fetcher)
    with db.connect() as cx:
        previous=cx.execute("SELECT latest_ref FROM connector_sync WHERE connector='github_public'").fetchone()
        changed=not previous or previous['latest_ref']!=commit['sha']
        cx.execute("INSERT INTO connector_sync(connector,latest_ref,last_synced_at,last_status,source_url) VALUES('github_public',?,?,?,?) ON CONFLICT(connector) DO UPDATE SET latest_ref=excluded.latest_ref,last_synced_at=excluded.last_synced_at,last_status=excluded.last_status,source_url=excluded.source_url",(commit['sha'],commit['retrieved_at'],'success',commit['url']))
        if changed:
            summary='Public repository change: '+commit['message']
            cursor=cx.execute("INSERT INTO events(company_id,kind,summary,payload,created_at) VALUES(?,?,?,?,?)",('headquarters','general.notice',summary,json.dumps({'sha':commit['sha'],'source_url':commit['url'],'fetched_at':commit['retrieved_at']}),db.utc_now()))
            eid=cursor.lastrowid
            db.audit_insert(cx,'connector:github_public','event.ingest',f'event:{eid}',{'sha':commit['sha'],'source_url':commit['url']})
    return {**commit,'changed':changed,'scope':'public_repository_metadata_only'}

def status()->list[dict]:
    with db.connect() as cx:return [dict(x) for x in cx.execute('SELECT * FROM connector_sync ORDER BY connector')]