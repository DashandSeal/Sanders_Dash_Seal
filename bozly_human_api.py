"""Bozly authenticated global human collaboration and WebRTC signaling API.

Media is direct encrypted WebRTC media between browsers, not handled by
this WSGI signaling server. TURN/STUN, consent, permissions and global reach
depend on live infrastructure configuration.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

import jwt
from cryptography.fernet import Fernet, InvalidToken
import bozly_operations as ops
import bozly_purchasing as purchasing
import bozly_global_transactions as global_finance

ISSUER = os.getenv("BOZLY_OIDC_ISSUER", "")
AUDIENCE = os.getenv("BOZLY_OIDC_AUDIENCE", "")
JWKS_PEM_FILE = os.getenv("BOZLY_OIDC_PUBLIC_KEY_FILE", "")
FERNET_KEY = os.getenv("BOZLY_SIGNAL_FERNET_KEY", "")
MAX_BODY = 131072
READONLY_ROLE = "bozly:view"
OPERATOR_ROLE = "bozly:operate"
ADMIN_ROLE = "bozly:manage"


def identity(environ):
    if not (ISSUER and AUDIENCE and JWKS_PEM_FILE):
        raise PermissionError("OIDC identity not configured")
    token = environ.get("HTTP_AUTHORIZATION", "")
    if not token.startswith("Bearer "):
        raise PermissionError("Bearer identity token required")
    with open(JWKS_PEM_FILE, "rb") as f:
        key = f.read(65537)
    if len(key) > 65536:
        raise PermissionError("OIDC key invalid")
    claims = jwt.decode(token[7:], key=key, algorithms=["RS256"],
                        issuer=ISSUER, audience=AUDIENCE,
                        options={"require":["exp","iat","sub","iss","aud"]},
                        leeway=30)
    subject = claims["sub"]
    if not isinstance(subject,str) or len(subject)<1 or len(subject)>256:
        raise PermissionError("Invalid subject")
    # Role and authorized-entity assertions are signed by the configured issuer.
    roles = claims.get("bozly_roles", [])
    entities = claims.get("bozly_entities", [])
    if not isinstance(roles,list) or not isinstance(entities,list):
        raise PermissionError("Invalid identity grants")
    return {"sub":subject,"roles":frozenset(x for x in roles if isinstance(x,str)),
            "entities":frozenset(x for x in entities if isinstance(x,str))}


def require_access(actor, entity, needed):
    if not entity or entity not in actor["entities"]:
        raise PermissionError("No access to legal entity")
    if needed == "view":
        ok = bool(actor["roles"] & {READONLY_ROLE, OPERATOR_ROLE, ADMIN_ROLE})
    elif needed == "operate":
        ok = bool(actor["roles"] & {OPERATOR_ROLE, ADMIN_ROLE})
    else:
        ok = ADMIN_ROLE in actor["roles"]
    if not ok:
        raise PermissionError("Role does not permit this action")


def _db():
    path = Path(os.getenv("BOZLY_CONTROL_DB", "/app/secure_ledgers/bozly_controls.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS call_rooms(
      room_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,
      host_subject TEXT NOT NULL,guest_subject TEXT NOT NULL,
      created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS call_signals(
      signal_id INTEGER PRIMARY KEY AUTOINCREMENT,room_id TEXT NOT NULL,
      sender TEXT NOT NULL,recipient TEXT NOT NULL,
      payload_ciphertext BLOB NOT NULL,created_at INTEGER NOT NULL,
      FOREIGN KEY(room_id) REFERENCES call_rooms(room_id)
    );
    """)
    return db


def _cipher():
    if not FERNET_KEY:
        raise RuntimeError("Encrypted signaling key not provisioned")
    return Fernet(FERNET_KEY.encode("ascii"))


def _room_access(db, room, actor, entity):
    row = db.execute(
        """SELECT host_subject,guest_subject,expires_at FROM call_rooms
           WHERE room_id=? AND entity_id=?""",(room,entity)).fetchone()
    if not row or row[2]<int(time.time()) or actor["sub"] not in row[:2]:
        raise PermissionError("Unknown, expired or unauthorized call room")
    return row


def _respond(start, code, obj):
    codes={200:"200 OK",201:"201 Created",400:"400 Bad Request",
           401:"401 Unauthorized",403:"403 Forbidden",404:"404 Not Found",
           413:"413 Content Too Large",503:"503 Service Unavailable"}
    data=json.dumps(obj,separators=(",",":")).encode()
    start(codes[code],[
        ("Content-Type","application/json"),
        ("Content-Length",str(len(data))),
        ("Cache-Control","no-store"),
        ("X-Content-Type-Options","nosniff"),
        ("Access-Control-Allow-Origin","null"),
    ])
    return [data]


def application(environ,start_response):
    try:
        actor=identity(environ)
    except (PermissionError,jwt.PyJWTError,OSError,ValueError):
        return _respond(start_response,401,{"error":"IDENTITY_UNAVAILABLE"})
    if environ.get("CONTENT_TYPE","").split(";")[0].strip() not in (
        "application/json","") and environ.get("REQUEST_METHOD")=="POST":
        return _respond(start_response,400,{"error":"JSON_REQUIRED"})
    method=environ.get("REQUEST_METHOD","")
    path=environ.get("PATH_INFO","")
    if not path.startswith("/bozly/v1/"):
        return _respond(start_response,404,{"error":"UNKNOWN_PATH"})
    if method not in {"POST","GET"}:
        return _respond(start_response,404,{"error":"UNSUPPORTED_METHOD"})
    length=int(environ.get("CONTENT_LENGTH","0") or "0")
    if length<0 or length>MAX_BODY:
        return _respond(start_response,413,{"error":"INVALID_SIZE"})
    if method=="POST" and not (0 < length <= MAX_BODY):
        return _respond(start_response,400,{"error":"BODY_REQUIRED"})
    try:
        data=json.loads(environ["wsgi.input"].read(length)) if method=="POST" else {}
        if not isinstance(data,dict):
            raise ValueError()
        entity=data.get("entity_id") if method=="POST" else environ.get("QUERY_STRING","").removeprefix("entity_id=")
        if not isinstance(entity,str) or len(entity)>180:
            raise ValueError()
        action=path.removeprefix("/bozly/v1/")
        if method=="POST" and action=="global-transaction-quote":
            require_access(actor,entity,"operate")
            if data.get("paying_entity")!=entity:
                raise PermissionError("Paying LLC must match authorized entity")
            result=global_finance.prepare_global_transaction(
                transaction_id=data["transaction_id"],
                paying_entity=entity,
                recipient_reference=data["recipient_reference"],
                recipient_country=data["recipient_country"],
                purpose=data["purpose"],
                necessity_evidence=data["necessity_evidence"],
                source_currency=data["source_currency"],
                source_minor=data["source_minor"],
                source_exponent=data["source_exponent"],
                destination_currency=data["destination_currency"],
                destination_minor=data["destination_minor"],
                destination_exponent=data["destination_exponent"],
                fx_rate_decimal=data["fx_rate_decimal"],
                fx_quote_reference=data["fx_quote_reference"],
                fx_provider_reference=data["fx_provider_reference"],
                quote_expires_utc=data["quote_expires_utc"],
                quoted_fees_source_minor=data["quoted_fees_source_minor"],
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="global-transaction-authorize":
            require_access(actor,entity,"manage")
            ceo=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo or actor["sub"]!=ceo:
                raise PermissionError("CEO authorization required")
            with global_finance._open() as financial_db:
                found=financial_db.execute(
                    "SELECT paying_entity FROM bozly_global_transactions WHERE transaction_id=?",
                    (data["transaction_id"],)
                ).fetchone()
            if not found or found[0]!=entity:
                raise PermissionError("Global transaction belongs to another entity")
            result=global_finance.authorize_global_transaction(
                transaction_id=data["transaction_id"],
                ceo_subject=actor["sub"],
                transaction_digest=data["transaction_digest"],
            )
            return _respond(start_response,200,result)
        if method=="POST" and action=="global-transaction-summary":
            require_access(actor,entity,"view")
            return _respond(start_response,200,{
                "entity_id":entity,
                "transactions":global_finance.global_transaction_summary(entity),
                "status":"recorded_transactions_only_not_live_bank_settlement",
            })
        if method=="POST" and action=="purchase":
            require_access(actor,entity,"operate")
            if data.get("paying_entity")!=entity:
                raise PermissionError("Paying entity must match authenticated entity scope")
            result=purchasing.create_purchase(
                order_id=data["order_id"],
                paying_entity=entity,
                merchant_id=data["merchant_id"],
                merchant_invoice=data["merchant_invoice"],
                description=data["description"],
                category=data["category"],
                necessity_reason=data["necessity_reason"],
                evidence_reference=data["evidence_reference"],
                amount_minor=data["amount_minor"],
                currency=data["currency"],
                destination_token=data["destination_token"],
                line_items=data["line_items"],
                beneficiary_allocations_minor=data["beneficiary_allocations_minor"],
                creator_subject=actor["sub"],
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="purchase-ceo-authorize":
            require_access(actor,entity,"manage")
            ceo_id=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo_id or actor["sub"]!=ceo_id:
                raise PermissionError("CEO identity required for purchasing authorization")
            order_id=data["order_id"]
            with purchasing._db() as order_db:
                existing=purchasing._order_row(order_db,order_id)
            if existing[0]!=entity:
                raise PermissionError("Purchase belongs to another legal entity")
            result=purchasing.ceo_authorize_purchase(
                order_id=order_id,ceo_subject=actor["sub"],
                authorized_purchase_digest=data["authorized_purchase_digest"],
            )
            return _respond(start_response,200,result)
        if method=="POST" and action=="purchase-submit":
            require_access(actor,entity,"manage")
            ceo_id=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo_id or actor["sub"]!=ceo_id:
                raise PermissionError("CEO identity required for purchase submission")
            order_id=data["order_id"]
            with purchasing._db() as order_db:
                existing=purchasing._order_row(order_db,order_id)
            if existing[0]!=entity:
                raise PermissionError("Purchase belongs to another legal entity")
            result=purchasing.submit_authorized_purchase(order_id)
            return _respond(start_response,200,result)
        if method=="POST" and action=="purchase-monthly-review":
            require_access(actor,entity,"view")
            return _respond(start_response,200,
                purchasing.monthly_purchases(paying_entity=entity,month=data["month"]))
        if method=="POST" and action=="workflows":
            require_access(actor,entity,"operate")
            result=ops.new_workflow(entity,data["title"],data["category"],actor["sub"])
            return _respond(start_response,201,result)
        if method=="POST" and action=="workflow-transition":
            require_access(actor,entity,"operate")
            result=ops.advance_workflow(entity,data["workflow_id"],data["state"],
                                        actor["sub"],int(data["revision"]))
            return _respond(start_response,200,result)
        if method=="POST" and action=="alert":
            require_access(actor,entity,"operate")
            result=ops.priority_alert(entity,data["priority"],data["category"],
                                      data["description"],data["dedupe_key"])
            return _respond(start_response,201,result)
        if method=="POST" and action=="alert-ack":
            require_access(actor,entity,"operate")
            done=ops.acknowledge_alert(entity,data["alert_id"],actor["sub"])
            return _respond(start_response,200,{"acknowledged":done})
        if method=="POST" and action=="fraud-signal":
            require_access(actor,entity,"operate")
            result=ops.record_risk_signal(
                entity,data["source_id"],data["signal_type"],data["evidence_digest"]
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="learning-feedback":
            require_access(actor,entity,"operate")
            result=ops.record_learning_feedback(entity,data["signal_id"],
                        data["disposition"],actor["sub"],data.get("model_version"))
            return _respond(start_response,201,{"feedback_id":result})
        if method=="POST" and action=="call-rooms":
            require_access(actor,entity,"operate")
            guest=data["guest_subject"]
            if not isinstance(guest,str) or not guest or guest==actor["sub"] or len(guest)>256:
                raise ValueError()
            rid="room_"+uuid.uuid4().hex
            now=int(time.time())
            with _db() as db:
                db.execute("INSERT INTO call_rooms VALUES(?,?,?,?,?,?)",
                           (rid,entity,actor["sub"],guest,now,now+3600))
            return _respond(start_response,201,{"room_id":rid,"expires_at":now+3600})
        if method=="POST" and action=="call-signals":
            require_access(actor,entity,"view")
            room=data["room_id"]
            kind=data["kind"]
            if kind not in {"offer","answer","ice-candidate","hangup"}:
                raise ValueError()
            payload=data["payload"]
            if not isinstance(payload,dict):
                raise ValueError()
            encoded=json.dumps({"kind":kind,"payload":payload},separators=(",",":")).encode()
            if len(encoded)>64000:
                raise ValueError()
            with _db() as db:
                host,guest,_=_room_access(db,room,actor,entity)
                recipient=guest if actor["sub"]==host else host
                cipher=_cipher().encrypt(encoded)
                cursor=db.execute("""INSERT INTO call_signals
                  (room_id,sender,recipient,payload_ciphertext,created_at)
                  VALUES(?,?,?,?,?)""",(room,actor["sub"],recipient,cipher,int(time.time())))
            return _respond(start_response,201,{"signal_id":cursor.lastrowid})
        if method=="POST" and action=="call-inbox":
            require_access(actor,entity,"view")
            room=data["room_id"]
            after=max(0,int(data.get("after",0)))
            with _db() as db:
                _room_access(db,room,actor,entity)
                rows=db.execute("""SELECT signal_id,sender,payload_ciphertext FROM call_signals
                   WHERE room_id=? AND recipient=? AND signal_id>? ORDER BY signal_id LIMIT 100""",
                   (room,actor["sub"],after)).fetchall()
            out=[]
            for ident,sender,ciphertext in rows:
                out.append({"id":ident,"sender":sender,
                            **json.loads(_cipher().decrypt(ciphertext))})
            return _respond(start_response,200,{"signals":out})
        return _respond(start_response,404,{"error":"UNKNOWN_ACTION"})
    except PermissionError:
        return _respond(start_response,403,{"error":"ACCESS_DENIED"})
    except (KeyError,ValueError,TypeError,OverflowError,InvalidToken):
        return _respond(start_response,400,{"error":"INVALID_REQUEST"})
    except Exception:
        return _respond(start_response,503,{"error":"SERVICE_UNAVAILABLE"})
