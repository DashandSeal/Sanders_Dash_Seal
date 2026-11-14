"""BOZLY native market-news intake and evidence-grounded headline telemetry.

Fetches explicitly configured public RSS or Atom sources via stdlib HTTPS.
No purchased market feed, no fake offline bullish fallback, and no claims of
real-time exchange prices or successful retrieval when sources are unavailable.
"""
from __future__ import annotations
import hashlib, json, os, re, sqlite3, ssl, time, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

DEFAULT_DB="/app/secure_ledgers/bozly_financial_core.db"
UP={"gain","growth","rally","rise","rises","surge","record","strong","beats","rebound","recover"}
DOWN={"decline","drop","drops","fall","falls","crash","weak","misses","loss","slump","plunge"}
ATOM="{http://www.w3.org/2005/Atom}"
def _db():
    file=Path(os.environ.get("BOZLY_DB_PATH",DEFAULT_DB));file.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(file),timeout=15,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""CREATE TABLE IF NOT EXISTS bozly_market_articles(
      entity_id TEXT NOT NULL,feed_name TEXT NOT NULL,article_hash TEXT NOT NULL,
      title TEXT NOT NULL,source_url TEXT NOT NULL,headline_score INTEGER NOT NULL,
      signal TEXT NOT NULL,fetched_unix INTEGER NOT NULL,PRIMARY KEY(entity_id,feed_name,article_hash));
    CREATE TABLE IF NOT EXISTS bozly_market_fetches(
      request_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,feed_name TEXT NOT NULL,
      fetched_unix INTEGER NOT NULL,success INTEGER NOT NULL,article_count INTEGER NOT NULL,
      error_code TEXT);""")
    return db
def _sources():
    obj=json.loads(os.environ.get("BOZLY_PUBLIC_MARKET_FEEDS_JSON","{}"))
    if not isinstance(obj,dict):raise ValueError("Feed registry must be an object")
    return obj
def _fetch(uri):
    p=urlsplit(uri)
    if p.scheme!="https" or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("HTTPS public feed URL required")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),NoRedirect())
    req=urllib.request.Request(uri,headers={"User-Agent":"BozlyNativeMarketNews/1.0",
        "Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with opener.open(req,timeout=12) as response:
        if response.status!=200:raise ValueError("Feed did not return HTTP 200")
        data=response.read(1_000_001)
        if len(data)>1_000_000:raise ValueError("Oversized market feed")
        return data
def _parse(raw):
    root=ET.fromstring(raw)
    entries=root.findall(".//item") if root.tag.lower().endswith("rss") or root.find("channel") is not None else root.findall(".//"+ATOM+"entry")
    result=[]
    for item in entries[:50]:
        title=item.findtext("title") or item.findtext(ATOM+"title") or ""
        link=item.findtext("link") or ""
        if not link:
            n=item.find(ATOM+"link")
            if n is not None:link=n.get("href","")
        if not title.strip() or not urlsplit(link).scheme in ("http","https"):continue
        tokens=set(re.findall(r"[a-z]+",title.lower()))
        score=len(tokens&UP)-len(tokens&DOWN)
        result.append({"title":title[:450],"link":link[:1300],
            "telemetry_metrics":{"raw_score":score,
                "signal_direction":"BULLISH" if score>0 else "BEARISH" if score<0 else "NEUTRAL",
                "method":"headline_keyword_heuristic_not_price_or_investment_advice"}})
    return result
class BozlyMarketIngestor:
    engine_id="BOZLY-NATIVE-MARKET-INGESTOR"
    def compute_integrity_seal(self):
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    def fetch_and_analyze_feed(self,segment,entity_id):
        from bozly_purchasing import ENTITIES
        if entity_id not in ENTITIES:raise ValueError("Unknown Sanders legal entity")
        sources=_sources();url=sources.get(segment)
        if not isinstance(url,str) or not url:
            return {"status":"NOT_CONFIGURED","articles":[],"feed_name":segment}
        stamp=int(time.time());request_id=hashlib.sha256(
            (entity_id+":"+segment+":"+str(time.time_ns())).encode()).hexdigest()
        try:
            rows=_parse(_fetch(url))
        except (ValueError,urllib.error.URLError,TimeoutError,OSError,ET.ParseError) as e:
            with _db() as db:
                db.execute("INSERT INTO bozly_market_fetches VALUES(?,?,?,?,?,?,?)",
                    (request_id,entity_id,segment,stamp,0,0,type(e).__name__))
            return {"status":"UNAVAILABLE","feed_name":segment,"articles":[],
                "retrieval_succeeded":False,"error_type":type(e).__name__}
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            for a in rows:
                h=hashlib.sha256((a["link"]+a["title"]).encode()).hexdigest()
                db.execute("""INSERT OR IGNORE INTO bozly_market_articles
                 VALUES(?,?,?,?,?,?,?,?)""",(entity_id,segment,h,a["title"],a["link"],
                    a["telemetry_metrics"]["raw_score"],
                    a["telemetry_metrics"]["signal_direction"],stamp))
            db.execute("INSERT INTO bozly_market_fetches VALUES(?,?,?,?,?,?,?)",
                (request_id,entity_id,segment,stamp,1,len(rows),None))
            db.commit()
        return {"status":"FETCHED","feed_name":segment,"articles":rows,
            "fetched_unix":stamp,"retrieval_succeeded":True,
            "exchange_price_data":False}
    def generate_saas_public_payload(self,client_token,segment="NASDAQ_MARKET_NEWS",entity_id=None):
        # Public market information is not restricted by the assistant-added
        # authenticated-dictionary token requirement. The client_token
        # argument is retained for compatibility with the owner's interface.
        # The Sanders Dash & Seal storefront is operated by the legal-helpers LLC.
        target_entity = entity_id if entity_id is not None else "sanders_legal_helpers"
        response=self.fetch_and_analyze_feed(segment,target_entity)
        return json.dumps({"service_provider":"Sanders Dash and Seal",
            "engine":self.engine_id,"client_auth_status":"PUBLIC_MARKET_DATA",
            "execution_timestamp":int(time.time()),
            "market_intelligence_payload":response},separators=(",",":"))
