"""Bozly native jurisdictional law-source registry and evidence cache.

A source monitor, not a legal opinion engine. It records official legal sources
by jurisdiction and topic, retrieves actual HTTPS responses with timestamps and
digests, and exposes freshness. No law or court outcome is invented.

International source registries are starting points; the authoritative statute,
tax authority, court and regulator for each affected country/state must be added.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

DB_PATH = "/app/secure_ledgers/bozly_legal_sources.db"
TOPICS = frozenset((
    "tax","banking","corporate","workers_compensation","employment",
    "payments","sanctions","lawsuits","privacy","healthcare","financial_reporting",
    "other",
))
SEED = (
    ("ILO NATLEX","GLOBAL","employment","https://natlex.ilo.org/dyn/natlex2/r/natlex/fe/about",
     "International Labour Organization"),
    ("EUR-Lex","EU","corporate","https://eur-lex.europa.eu/content/welcome/about.html?locale=en",
     "Publications Office of the European Union"),
    ("US IRS","US","tax","https://www.irs.gov/",
     "Internal Revenue Service"),
    ("US Treasury OFAC","US","sanctions","https://ofac.treasury.gov/sanctions-list-service",
     "U.S. Treasury, Office of Foreign Assets Control"),
    ("US DOL state workers compensation","US","workers_compensation",
     "https://www.dol.gov/agencies/owcp/wc","U.S. Department of Labor"),
    ("US federal courts PACER","US","lawsuits","https://pacer.uscourts.gov/",
     "Administrative Office of the U.S. Courts"),
    ("US FinCEN","US","banking","https://www.fincen.gov/",
     "U.S. Department of Treasury, Financial Crimes Enforcement Network"),
)


class LegalSourceUnavailable(RuntimeError):
    pass


def _db():
    path=Path(os.getenv("BOZLY_LEGAL_DB",DB_PATH))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path),timeout=15,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=15000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS legal_sources (
        source_id TEXT PRIMARY KEY,
        jurisdiction TEXT NOT NULL,
        topic TEXT NOT NULL,
        issuing_authority TEXT NOT NULL,
        url TEXT NOT NULL,
        last_checked INTEGER,
        last_success INTEGER,
        response_sha256 TEXT,
        http_status INTEGER,
        last_error TEXT,
        last_modified TEXT,
        content_type TEXT
    );
    CREATE TABLE IF NOT EXISTS legal_source_snapshots (
        source_id TEXT NOT NULL REFERENCES legal_sources(source_id),
        content_sha256 TEXT NOT NULL,
        fetched_at INTEGER NOT NULL,
        content_bytes INTEGER NOT NULL,
        PRIMARY KEY(source_id,content_sha256)
    );
    """)
    return db


def register_source(source_id, jurisdiction, topic, url, issuing_authority):
    """Register known issuing authority; do not accept HTTP or embedded creds."""
    if (not isinstance(source_id,str) or not source_id.strip()
            or len(source_id)>180 or not isinstance(jurisdiction,str)
            or not 2<=len(jurisdiction)<=100
            or not isinstance(issuing_authority,str)
            or not issuing_authority.strip()):
        raise ValueError("Source, jurisdiction and issuing authority required")
    if topic not in TOPICS:
        raise ValueError("Unknown legal topic")
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.fragment
            or len(url)>2048):
        raise ValueError("Official HTTPS source URL required")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO legal_sources
            (source_id,jurisdiction,topic,issuing_authority,url)
            VALUES(?,?,?,?,?)
            ON CONFLICT(source_id) DO UPDATE SET
               jurisdiction=excluded.jurisdiction,topic=excluded.topic,
               issuing_authority=excluded.issuing_authority,url=excluded.url,
               last_checked=CASE WHEN legal_sources.url=excluded.url
                   THEN legal_sources.last_checked ELSE NULL END,
               last_success=CASE WHEN legal_sources.url=excluded.url
                   THEN legal_sources.last_success ELSE NULL END,
               response_sha256=CASE WHEN legal_sources.url=excluded.url
                   THEN legal_sources.response_sha256 ELSE NULL END""",
            (source_id,jurisdiction.upper(),topic,issuing_authority,url))
        db.commit()
    return {"source_id":source_id,"registered":True,"authoritative_text_verified":False}


def seed_authorities():
    count=0
    for source,region,topic,url,authority in SEED:
        register_source(source,region,topic,url,authority)
        count+=1
    return count


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def refresh_source(source_id):
    """Observe actual source availability and content digest with local UTC clock.

    Never mistake a retrieved landing page for a complete legal rule.
    Restricts retrieval to the registered host's official HTTPS endpoint.
    """
    with _db() as db:
        row=db.execute("SELECT url FROM legal_sources WHERE source_id=?",
                       (source_id,)).fetchone()
    if not row:
        raise KeyError("Unknown legal source")
    url=row[0]
    opener=urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirect(),
    )
    req=urllib.request.Request(url,headers={
        "Accept":"text/html,application/xhtml+xml,application/xml,text/plain,application/pdf",
        "User-Agent":"Bozly-Source-Observer/1.0",
    })
    when=int(time.time())
    try:
        with opener.open(req,timeout=12) as response:
            body=response.read(1024*1024+1)
            if len(body)>1024*1024:
                raise LegalSourceUnavailable("Response larger than safe snapshot limit")
            if not 200<=response.status<300:
                raise LegalSourceUnavailable("Official legal source HTTP response unsuccessful")
            mime=response.headers.get("Content-Type","")[:150]
            modified=response.headers.get("Last-Modified","")[:128]
            digest=hashlib.sha256(body).hexdigest()
            status=response.status
    except (urllib.error.URLError,OSError,TimeoutError,ValueError,
            LegalSourceUnavailable) as exc:
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""UPDATE legal_sources SET last_checked=?,last_error=?
                       WHERE source_id=?""",(when,type(exc).__name__,source_id))
            db.commit()
        return {"source_id":source_id,"source_reachable":False,
                "checked_at":when,"current_law_verified":False}
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""UPDATE legal_sources SET last_checked=?,last_success=?,
                   response_sha256=?,http_status=?,last_modified=?,
                   content_type=?,last_error=NULL WHERE source_id=?""",
                   (when,when,digest,status,modified,mime,source_id))
        db.execute("""INSERT OR IGNORE INTO legal_source_snapshots
            (source_id,content_sha256,fetched_at,content_bytes)
            VALUES(?,?,?,?)""",(source_id,digest,when,len(body)))
        db.commit()
    return {
        "source_id":source_id,"source_reachable":True,
        "checked_at":when,"content_sha256":digest,
        "content_bytes":len(body),"last_modified_claim":modified,
        "current_law_verified":False,
        "note":"This is a retrieval record, not a legal analysis or completeness guarantee.",
    }


def source_status(jurisdiction=None,topic=None):
    if topic is not None and topic not in TOPICS:
        raise ValueError("Unknown legal topic")
    sql="""SELECT source_id,jurisdiction,topic,issuing_authority,url,
           last_checked,last_success,response_sha256,last_error,
           last_modified FROM legal_sources WHERE 1=1"""
    args=[]
    if jurisdiction:
        sql+=" AND (jurisdiction=? OR jurisdiction='GLOBAL')"
        args.append(jurisdiction.upper())
    if topic:
        sql+=" AND topic=?"
        args.append(topic)
    sql+=" ORDER BY jurisdiction,topic,source_id"
    with _db() as db:
        rows=db.execute(sql,args).fetchall()
    return [{
        "source_id":sid,"jurisdiction":region,"topic":subject,
        "authority":authority,"url":url,"last_checked_unix":checked,
        "last_success_unix":last_success,"content_sha256":digest,
        "last_error":error,"publisher_last_modified":modified,
        "law_application_verified":False,
    } for sid,region,subject,authority,url,checked,last_success,digest,
          error,modified in rows]
