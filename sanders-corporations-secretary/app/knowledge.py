"""Source-anchored retrieval. Company scoping is enforced before ranking."""
from __future__ import annotations
import hashlib
import math
import re
from collections import Counter
from . import db
from .registry import COMPANY_BY_ID

STOP={"and","the","for","with","from","into","this","that","what","when","where","have","does","are","was","your","about","show","tell","find","which","will","should","their","company","corporate","sand ers","sanders"}

def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+",text.lower()) if len(w)>2 and w not in STOP]

def add_knowledge(company_id: str,title: str, body: str, source_type: str,source_ref:str,classification:str="internal") -> dict:
    if company_id not in COMPANY_BY_ID: raise ValueError("unknown company")
    digest=hashlib.sha256(body.encode("utf-8")).hexdigest()
    with db.connect() as cx:
        cx.execute("INSERT OR IGNORE INTO knowledge(company_id,title,body,source_type,source_ref,classification,content_sha256,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (company_id,title,body,source_type,source_ref,classification,digest,db.utc_now()))
        row=cx.execute("SELECT id FROM knowledge WHERE company_id=? AND source_ref=? AND content_sha256=?",(company_id,source_ref,digest)).fetchone()
        db.audit_insert(cx,'owner','knowledge.index',f'knowledge:{row["id"]}',{"company_id":company_id,"digest":digest,"source_ref":source_ref})
    return {"id":row["id"],"company_id":company_id,"content_sha256":digest,"source_ref":source_ref}

def search(query:str,company_id:str|None=None,limit:int=6,include_internal:bool=True)->list[dict]:
    if company_id and company_id not in COMPANY_BY_ID:raise ValueError("unknown company")
    sql="SELECT id,company_id,title,body,source_type,source_ref,classification,content_sha256 FROM knowledge WHERE 1=1"
    args=[]
    if company_id:sql+=" AND company_id=?";args.append(company_id)
    if not include_internal:sql+=" AND classification='public'"
    sql+=" ORDER BY id DESC LIMIT 5000"
    with db.connect() as cx: docs=[dict(x) for x in cx.execute(sql,args)]
    q=Counter(terms(query));
    if not q:return []
    corpus=[Counter(terms(f'{x["title"]} {x["body"]}')) for x in docs]
    df=Counter(k for c in corpus for k in c)
    scores=[]
    for d,c in zip(docs,corpus):
        score=sum((1+math.log(1+c[t]))*(math.log((len(docs)+1)/(df[t]+1))+1)*q[t] for t in q if c[t])
        if score<=0:continue
        text=d.pop("body")
        d["excerpt"]=text[:380]+("…" if len(text)>380 else "")
        d["score"]=round(score,3)
        scores.append(d)
    scores.sort(key=lambda d:(-d["score"],-d["id"]))
    return scores[:limit]