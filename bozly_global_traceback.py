"""Bozly global confidential forensic traceback federation.

Unifies evidence from Bozly-owned deployments worldwide. Its own signed
telemetry, confidential storage, replay defense and cross-site correlation.
There is no covert intrusion into third-party systems, identity fabrication,
remote host surveillance, guaranteed invisibility or accusation from an IP.

The owner's Labyrinth Shield, Minotaur Sentinel and Quantum Armor sources
are not changed by this module. No commercial monitoring subscription.
"""
from __future__ import annotations
import base64
from cryptography.fernet import Fernet
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import ssl
import sys
import time
from urllib.parse import urlsplit
import urllib.request
import urllib.error

from bozly_purchasing import ENTITIES

DB_PATH = "/app/secure_ledgers/bozly_global_forensics.db"
STATE_PATH = "/app/secure_ledgers/security"
SERVICE_PATH = "/bozly/v1/security/global-evidence"
KEY_PATTERN = re.compile(r"^[a-zA-Z0-9._:@/-]{1,180}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
MAX_RECORD = None
MAX_CLOCK_SKEW = 300


def _config():
    sources = json.loads(os.environ.get("BOZLY_GLOBAL_SOURCE_KEYS_JSON", "{}"))
    if not isinstance(sources, dict):
        raise ValueError("Global source configuration must be an object")
    return sources


def _fernet():
    secret = os.environ.get("BOZLY_GLOBAL_FORENSIC_FERNET_KEY", "")
    if not secret:
        raise RuntimeError("Confidential global forensic storage key not configured")
    return Fernet(secret.encode("ascii"))


def _db():
    p = Path(os.environ.get("BOZLY_GLOBAL_FORENSIC_DB_PATH", DB_PATH))
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(str(p), isolation_level=None, timeout=20)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_global_evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_id TEXT NOT NULL,
      event_id TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      site_id TEXT NOT NULL,
      jurisdiction TEXT NOT NULL,
      observed_unix_ns INTEGER NOT NULL,
      received_unix_ns INTEGER NOT NULL,
      evidence_ciphertext BLOB NOT NULL,
      original_evidence_sha256 TEXT NOT NULL,
      request_body_sha256 TEXT NOT NULL,
      event_class TEXT NOT NULL,
      recorded_actor_claim TEXT,
      session_reference TEXT,
      transaction_reference TEXT,
      trace_reference TEXT,
      incident_reference TEXT,
      prior_entry_sha256 TEXT NOT NULL,
      entry_sha256 TEXT NOT NULL,
      UNIQUE(source_id,event_id)
    );
    CREATE INDEX IF NOT EXISTS bozly_global_by_incident
      ON bozly_global_evidence(entity_id,incident_reference,received_unix_ns);
    CREATE INDEX IF NOT EXISTS bozly_global_by_session
      ON bozly_global_evidence(entity_id,session_reference);
    CREATE INDEX IF NOT EXISTS bozly_global_by_transaction
      ON bozly_global_evidence(entity_id,transaction_reference);
    CREATE INDEX IF NOT EXISTS bozly_global_by_trace
      ON bozly_global_evidence(entity_id,trace_reference);
    """)
    return db


def _identifier(value, name, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not KEY_PATTERN.fullmatch(value):
        raise ValueError("Invalid " + name)
    return value


def _source(source_id):
    _identifier(source_id, "source identity")
    entry = _config().get(source_id)
    if not isinstance(entry, dict):
        raise PermissionError("Unrecognized global evidence sender")
    encoded = entry.get("key_b64", "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as e:
        raise PermissionError("Invalid source identity key") from e
    if len(key) < 32:
        raise PermissionError("Source identity key must be cryptographically strong")
    allowed = entry.get("entities", [])
    if not isinstance(allowed, list) or not allowed:
        raise PermissionError("Source requires an entity scope")
    return key, allowed


def _signature(key: bytes, timestamp: int, raw: bytes) -> str:
    msg = b"bozly-global-evidence-v1\n" + str(timestamp).encode() + b"\n" + raw
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _body(record):
    if not isinstance(record, dict):
        raise ValueError("Global evidence must be an object")
    data = json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()
    return data


def ingest_authenticated(raw: bytes, source_id: str, timestamp: int,
                         signature: str):
    """Ingest an authenticated origin observation; do not infer perpetrator."""
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("Invalid evidence body")
    if type(timestamp) is not int or abs(int(time.time()) - timestamp) > MAX_CLOCK_SKEW:
        raise PermissionError("Expired or future source message")
    if not isinstance(signature, str) or not HEX64.fullmatch(signature):
        raise PermissionError("Invalid signed message")
    key, allowed_entities = _source(source_id)
    if not hmac.compare_digest(_signature(key, timestamp, raw), signature):
        raise PermissionError("Invalid source authentication")
    event = json.loads(raw)
    if not isinstance(event, dict):
        raise ValueError("Evidence must be an object")
    entity_id = event.get("entity_id")
    if entity_id not in ENTITIES or entity_id not in allowed_entities:
        raise PermissionError("Source not authorized for this LLC")
    fields = ("event_id", "site_id", "jurisdiction", "event_class")
    for field in fields:
        _identifier(event.get(field), field)
    for field in ("actor_subject", "session_reference", "transaction_reference",
                  "trace_reference", "incident_reference"):
        _identifier(event.get(field), field, optional=True)
    original = event.get("original_evidence_sha256")
    if not isinstance(original, str) or not HEX64.fullmatch(original):
        raise ValueError("Source evidence digest required")
    observed = event.get("observed_unix_ns")
    if type(observed) is not int or observed <= 0 or observed > time.time_ns() + 120_000_000_000:
        raise ValueError("Invalid signed observation timestamp")
    # Confidential encryption is mandatory for globally collected records.
    encrypted = _fernet().encrypt(raw)
    received = time.time_ns()
    request_sha = hashlib.sha256(raw).hexdigest()
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("""SELECT request_body_sha256,entry_sha256
            FROM bozly_global_evidence WHERE source_id=? AND event_id=?""",
            (source_id, event["event_id"])).fetchone()
        if old is not None:
            if not hmac.compare_digest(old[0], request_sha):
                raise ValueError("Conflicting evidence with existing source event ID")
            db.commit()
            return {"ingested":True, "already_recorded":True,
                    "entry_sha256":old[1], "actor_identity_confirmed":False}
        previous = db.execute("""SELECT entry_sha256
            FROM bozly_global_evidence ORDER BY id DESC LIMIT 1""").fetchone()
        prior_hash = previous[0] if previous else "0"*64
        chain_body = json.dumps([prior_hash, source_id, event["event_id"],
                                 entity_id, received, request_sha],
                                separators=(",", ":")).encode()
        chain_hash = hashlib.sha256(chain_body).hexdigest()
        db.execute("""INSERT INTO bozly_global_evidence(
             source_id,event_id,entity_id,site_id,jurisdiction,
             observed_unix_ns,received_unix_ns,evidence_ciphertext,
             original_evidence_sha256,request_body_sha256,event_class,
             recorded_actor_claim,session_reference,transaction_reference,
             trace_reference,incident_reference,prior_entry_sha256,
             entry_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (source_id, event["event_id"], entity_id, event["site_id"],
              event["jurisdiction"], observed, received, encrypted, original,
              request_sha, event["event_class"], event.get("actor_subject"),
              event.get("session_reference"), event.get("transaction_reference"),
              event.get("trace_reference"), event.get("incident_reference"),
              prior_hash, chain_hash))
        db.commit()
    return {"ingested":True, "already_recorded":False,
            "entry_sha256":chain_hash, "actor_identity_confirmed":False,
            "attribution_status":"REQUIRES_CORROBORATING_RECORDS"}


def correlate(*,entity_id,incident_reference,maximum=500):
    """Cross-border correlation of exact records from authenticated sources.

    Returns sourced actor identity claims; not accusations, verified people,
    external network traceback, or unsupported attribution confidence scores.
    """
    if entity_id not in ENTITIES:
        raise ValueError("Unknown LLC")
    _identifier(incident_reference, "incident reference")
    if type(maximum) is not int or maximum < 1:
        raise ValueError("Invalid result count")
    with _db() as db:
        seeds = db.execute("""SELECT event_id,session_reference,
            transaction_reference,trace_reference FROM bozly_global_evidence
            WHERE entity_id=? AND incident_reference=?""",
            (entity_id, incident_reference)).fetchall()
        if not seeds:
            return {"entity_id":entity_id,
                    "incident_reference":incident_reference,
                    "status":"NO_AUTHENTICATED_EVIDENCE",
                    "records":[], "identified_responsible_parties":[]}
        tokens = set()
        for _,session,transaction,trace in seeds:
            for kind, value in (("session_reference",session),
                                ("transaction_reference",transaction),
                                ("trace_reference",trace)):
                if value:
                    tokens.add((kind,value))
        rows = db.execute("""SELECT source_id,event_id,site_id,jurisdiction,
            observed_unix_ns,event_class,recorded_actor_claim,
            session_reference,transaction_reference,trace_reference,
            incident_reference,original_evidence_sha256,entry_sha256
            FROM bozly_global_evidence
            WHERE entity_id=? ORDER BY received_unix_ns DESC""",
            (entity_id,)).fetchall()
    linked=[]
    for row in rows:
        source,event,site,juris,observed,kind,actor,session,transaction,trace,incident,evidence_sha,chain_sha=row
        if incident != incident_reference and not any(
            (key,value) in tokens for key,value in (
                ("session_reference",session),
                ("transaction_reference",transaction),
                ("trace_reference",trace)
            ) if value
        ):
            continue
        linked.append({
            "source_id":source, "event_id":event,
            "site_id":site,"jurisdiction":juris,
            "observed_unix_ns":observed,"event_class":kind,
            "actor_subject_claim":actor,
            "session_reference":session,
            "transaction_reference":transaction,
            "trace_reference":trace,
            "source_evidence_sha256":evidence_sha,
            "global_chain_sha256":chain_sha,
        })
        if len(linked)>=maximum:
            break
    claimed = sorted({item["actor_subject_claim"]
                      for item in linked if item["actor_subject_claim"]})
    return {"entity_id":entity_id,"incident_reference":incident_reference,
        "status":"CORRELATED_AUTHENTICATED_SOURCE_OBSERVATIONS",
        "records":linked,"jurisdictions":sorted({x["jurisdiction"] for x in linked}),
        "observed_sites":sorted({x["site_id"] for x in linked}),
        "source_asserted_actor_subjects":claimed,
        "identified_responsible_parties":[],
        "identity_attribution_proven":False,
        "confidential_internal_forensic_report":True}


def _respond(start, status, payload):
    data=json.dumps(payload, separators=(",", ":")).encode()
    start(status,[("Content-Type","application/json"),
                  ("Content-Length",str(len(data))),
                  ("Cache-Control","no-store"),
                  ("X-Content-Type-Options","nosniff")])
    return [data]


def application(environ, start_response):
    """Single ingestion entrypoint behind owner-managed HTTPS reverse proxy."""
    if environ.get("PATH_INFO") != SERVICE_PATH or environ.get("REQUEST_METHOD")!="POST":
        return _respond(start_response,"404 Not Found",{"error":"UNKNOWN_PATH"})
    try:
        size=int(environ.get("CONTENT_LENGTH","0") or "0")
        if size <= 0:
            return _respond(start_response,"413 Content Too Large",{"error":"BODY_SIZE"})
        raw=environ["wsgi.input"].read(size)
        if len(raw)!=size:
            return _respond(start_response,"400 Bad Request",{"error":"BODY_INCOMPLETE"})
        source_id=environ.get("HTTP_X_BOZLY_SOURCE","")
        timestamp=int(environ.get("HTTP_X_BOZLY_TIMESTAMP","0"))
        signature=environ.get("HTTP_X_BOZLY_SIGNATURE","")
        result=ingest_authenticated(raw,source_id,timestamp,signature)
        return _respond(start_response,"201 Created",result)
    except PermissionError:
        return _respond(start_response,"403 Forbidden",{"error":"SOURCE_NOT_AUTHORIZED"})
    except (ValueError,TypeError,KeyError,json.JSONDecodeError):
        return _respond(start_response,"400 Bad Request",{"error":"INVALID_EVIDENCE"})
    except (OSError,RuntimeError,sqlite3.Error):
        return _respond(start_response,"503 Service Unavailable",
                        {"error":"FORENSIC_STORAGE_UNAVAILABLE"})


def _no_redirect():
    class Handler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):
            return None
    return Handler()


def sender():
    """Forward locally collected Minotaur incidents to the owner's global node.

    Process state is private, durable; network errors never delete unsent rows.
    No customer SaaS broker or external surveillance mechanisms required.
    """
    endpoint=os.environ["BOZLY_GLOBAL_TRACEBACK_ENDPOINT"]
    address=urlsplit(endpoint)
    if address.scheme!="https" or not address.hostname or address.fragment:
        raise ValueError("Owner-operated global endpoint must use HTTPS")
    source_id=_identifier(os.environ["BOZLY_GLOBAL_SOURCE_ID"],"source ID")
    entity_id=os.environ["BOZLY_GLOBAL_ENTITY_ID"]
    if entity_id not in ENTITIES:raise ValueError("Invalid source LLC")
    site_id=_identifier(os.environ["BOZLY_GLOBAL_SITE_ID"],"site ID")
    jurisdiction=_identifier(os.environ["BOZLY_GLOBAL_JURISDICTION"],"jurisdiction")
    key_b64=os.environ["BOZLY_GLOBAL_SOURCE_KEY_B64"]
    key=base64.b64decode(key_b64,validate=True)
    if len(key)<32:raise ValueError("Source signing key must have at least 32 bytes")
    forensic_file=Path(os.environ.get("BOZLY_SECURITY_STATE_DIR",STATE_PATH))/"forensic_breach_manifest.pbd.json"
    position_file=Path(os.environ.get("BOZLY_GLOBAL_SENDER_CURSOR_FILE",
                                     STATE_PATH+"/global_forensic_sender.cursor"))
    position_file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    opener=urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _no_redirect())
    while True:
        if forensic_file.exists():
            offset=int(position_file.read_text().strip()) if position_file.exists() else 0
            with forensic_file.open("rb") as file:
                file.seek(offset)
                while True:
                    entry_start=file.tell()
                    line=file.readline()
                    if not line or not line.endswith(b"\n"):
                        break
                    original=json.loads(line)
                    incident_id=original.get("incident_id")
                    if not isinstance(incident_id,str) or not incident_id:
                        raise ValueError("Local incident without source event ID")
                    event = {
                        "event_id":incident_id,
                        "entity_id":entity_id,
                        "site_id":site_id,
                        "jurisdiction":jurisdiction,
                        "event_class":_identifier(original.get("event"),"local event"),
                        "observed_unix_ns":original.get("observed_at_unix_ns"),
                        "original_evidence_sha256":hashlib.sha256(line).hexdigest(),
                        "incident_reference":incident_id,
                    }
                    # Other correlations must come from actual authenticated
                    # local records; never invent a person, session or trace.
                    body=_body(event)
                    timestamp=int(time.time())
                    req=urllib.request.Request(endpoint,data=body,method="POST",headers={
                        "Content-Type":"application/json",
                        "X-Bozly-Source":source_id,
                        "X-Bozly-Timestamp":str(timestamp),
                        "X-Bozly-Signature":_signature(key,timestamp,body),
                    })
                    try:
                        with opener.open(req,timeout=10) as response:
                            if response.status not in (200,201,202):
                                raise OSError("Global forensic collector rejected entry")
                    except (urllib.error.URLError,TimeoutError,OSError):
                        file.seek(entry_start)
                        break
                    offset=file.tell()
                    tmp=position_file.with_name(position_file.name+".partial")
                    with tmp.open("w",encoding="ascii") as cursor:
                        cursor.write(str(offset))
                        cursor.flush()
                        os.fsync(cursor.fileno())
                    os.chmod(tmp,0o600)
                    os.replace(tmp,position_file)
        time.sleep(10)


if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="send":
        sender()
    else:
        raise SystemExit("Use 'send' for owner-authorized global evidence forwarding")
