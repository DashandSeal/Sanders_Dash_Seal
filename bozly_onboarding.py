"""Bozly native client onboarding and hashed API license management.

Owner-defined plans, no imposed subscriptions, throttling tiers, mock keys,
public unauthenticated registration or raw secret storage. Existing CFO
identity may provision keys; client entitlements are scoped by legal entity.
"""
from __future__ import annotations
import hashlib,hmac,os,re,secrets,sqlite3,time
from pathlib import Path
from bozly_purchasing import ENTITIES
DEFAULT_DB="/app/secure_ledgers/bozly_financial_core.db"
_NAME=re.compile(r"^[a-zA-Z0-9_.:-]{1,100}$")
def _db():
    p=Path(os.environ.get("BOZLY_DB_PATH",DEFAULT_DB));p.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(p),timeout=15,isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""CREATE TABLE IF NOT EXISTS bozly_client_licenses(
       client_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,contact_reference TEXT NOT NULL,
       license_name TEXT NOT NULL,api_key_hash TEXT UNIQUE NOT NULL,
       status TEXT NOT NULL,created_at INTEGER NOT NULL,expires_at INTEGER,
       created_by TEXT NOT NULL,revoked_at INTEGER,revoked_by TEXT);
       CREATE INDEX IF NOT EXISTS bozly_license_scope
       ON bozly_client_licenses(entity_id,status);""")
    return c
class BozlyOnboardingEngine:
    def compute_file_hash(self):
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    def provision_new_client(self,*,entity_id,contact_reference,license_name,actor,
                             expires_at=None):
        if entity_id not in ENTITIES:raise ValueError("Unrecognized legal entity")
        if not all(isinstance(x,str) and x.strip() and len(x)<=250
                   for x in (contact_reference,actor)):
            raise ValueError("Contact and actor required")
        if not isinstance(license_name,str) or not _NAME.fullmatch(license_name):
            raise ValueError("Valid owner-defined license name required")
        now=int(time.time())
        if expires_at is not None and (type(expires_at)!=int or expires_at<=now):
            raise ValueError("Expiry must be future unix time or omitted")
        client_id="cli_"+secrets.token_hex(16)
        raw_key="bz_"+secrets.token_urlsafe(48)
        key_hash=hashlib.sha256(raw_key.encode()).hexdigest()
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO bozly_client_licenses(
             client_id,entity_id,contact_reference,license_name,api_key_hash,
             status,created_at,expires_at,created_by) VALUES(?,?,?,?,?,'ACTIVE',?,?,?)""",
             (client_id,entity_id,contact_reference,license_name,key_hash,now,
              expires_at,actor))
            db.commit()
        return {"client_id":client_id,"entity_id":entity_id,"license_name":license_name,
            "status":"ACTIVE","secret_api_key_once":raw_key,
            "raw_key_stored":False,"client_account_created":True,
            "subscription_charge_started":False}
    def authenticate(self,raw_key,entity_id):
        if entity_id not in ENTITIES or not isinstance(raw_key,str) or not raw_key.startswith("bz_"):
            raise PermissionError("Invalid client credentials")
        digest=hashlib.sha256(raw_key.encode()).hexdigest()
        with _db() as db:
            row=db.execute("""SELECT client_id,license_name,status,expires_at
               FROM bozly_client_licenses
               WHERE api_key_hash=? AND entity_id=?""",(digest,entity_id)).fetchone()
        if row is None or row[2]!="ACTIVE" or (row[3] is not None and row[3]<=int(time.time())):
            raise PermissionError("Inactive or unrecognized client credential")
        return {"authenticated":True,"client_id":row[0],"license_name":row[1],
                "entity_id":entity_id}
    def revoke(self,*,entity_id,client_id,actor):
        if entity_id not in ENTITIES or not isinstance(actor,str) or not actor:
            raise PermissionError("Invalid owner identity or legal entity")
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            updated=db.execute("""UPDATE bozly_client_licenses SET status='REVOKED',
               revoked_at=?,revoked_by=? WHERE client_id=? AND entity_id=?
               AND status='ACTIVE'""",(int(time.time()),actor,client_id,entity_id)).rowcount
            db.commit()
        return {"client_id":client_id,"revoked":bool(updated)}
