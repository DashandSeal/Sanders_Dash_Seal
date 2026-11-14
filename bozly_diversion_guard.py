"""Bozly CFO: non-suppressible suspected-diversion incident and officer fanout.

Owner directive: attempted diversion, concealment, or unauthorized redirection of
money, assets, holdings or subsidiary interests is a P0 incident. Record once
durably, queue delivery separately for CEO, acting CEO, every VP and human CFO.
Attempts are not executed by this component. Network delivery is best-effort;
status never falsely reports successful notification.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid

from bozly_operations import _db

REQUIRED_ROLES = ("ceo", "acting_ceo", "vp", "human_cfo")
CATEGORIES = frozenset({
    "unauthorized_money_diversion",
    "asset_diversion",
    "holdings_diversion",
    "subsidiary_interest_diversion",
    "secret_redirection",
    "suppressed_financial_notification",
    "payee_or_authorization_tampering",
    "suspected_financial_misappropriation",
})


class DiversionDenied(PermissionError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_diversion_incidents (
      incident_id TEXT PRIMARY KEY,
      entity_id TEXT NOT NULL,
      category TEXT NOT NULL,
      subject_id TEXT NOT NULL,
      request_actor TEXT NOT NULL,
      evidence_sha256 TEXT NOT NULL,
      detected_at INTEGER NOT NULL,
      severity TEXT NOT NULL DEFAULT 'P0'
    );
    CREATE TABLE IF NOT EXISTS bozly_diversion_deliveries (
      incident_id TEXT NOT NULL REFERENCES bozly_diversion_incidents(incident_id),
      role TEXT NOT NULL,
      recipient_id TEXT NOT NULL,
      status TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0,
      last_attempt_at INTEGER,
      delivered_at INTEGER,
      PRIMARY KEY (incident_id, role, recipient_id)
    );
    """)


def _recipient_config():
    """Owner-managed recipient directory; no invented officer identities."""
    try:
        config = json.loads(os.environ.get("BOZLY_FINANCIAL_ALERT_RECIPIENTS_JSON", "{}"))
    except ValueError:
        return {}
    if not isinstance(config, dict):
        return {}
    result = {}
    for role in REQUIRED_ROLES:
        raw = config.get(role, [])
        if not isinstance(raw, list):
            raw = []
        recipients = {}
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            rid = entry.get("id")
            endpoint = entry.get("url")
            token = entry.get("token")
            if not isinstance(rid, str) or not rid or len(rid) > 180:
                continue
            parsed = urlsplit(endpoint or "")
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.fragment or not isinstance(token, str)
                    or not token):
                continue
            recipients[rid] = {"url": endpoint, "token": token}
        result[role] = recipients
    return result


def _send_one(delivery):
    incident_id, role, recipient_id, endpoint, token, payload = delivery
    request = urllib.request.Request(
        endpoint, data=payload, method="POST", headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Idempotency-Key": incident_id + ":" + role + ":" + recipient_id,
        }
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirect(),
    )
    try:
        with opener.open(request, timeout=7) as response:
            if 200 <= response.status < 300:
                return (incident_id, role, recipient_id, True)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        pass
    return (incident_id, role, recipient_id, False)


def dispatch_pending(incident_id: str | None = None) -> dict:
    """Attempt a concurrent broadcast to every configured officer.

    Returns each recipient's recorded status; no claim of simultaneity or
    receipt when network providers cannot confirm delivery.
    """
    config = _recipient_config()
    with _db() as db:
        _setup(db)
        if incident_id:
            rows = db.execute(
                """SELECT d.incident_id,d.role,d.recipient_id,i.entity_id,
                          i.category,i.subject_id,i.evidence_sha256,i.detected_at
                   FROM bozly_diversion_deliveries d JOIN bozly_diversion_incidents i
                   ON i.incident_id=d.incident_id
                   WHERE d.incident_id=? AND d.status IN ('PENDING','RETRY','UNCONFIGURED')""",
                (incident_id,)
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT d.incident_id,d.role,d.recipient_id,i.entity_id,
                          i.category,i.subject_id,i.evidence_sha256,i.detected_at
                   FROM bozly_diversion_deliveries d JOIN bozly_diversion_incidents i
                   ON i.incident_id=d.incident_id
                   WHERE d.status IN ('PENDING','RETRY','UNCONFIGURED')
                   ORDER BY i.detected_at LIMIT 250"""
            ).fetchall()
    scheduled = []
    for iid, role, rid, entity, category, subject, digest, detected in rows:
        target = config.get(role, {}).get(rid)
        if not target:
            continue
        payload = json.dumps({
            "event": "BOZLY_P0_SUSPECTED_DIVERSION",
            "severity": "P0",
            "incident_id": iid,
            "entity_id": entity,
            "category": category,
            "subject_id": subject,
            "evidence_sha256": digest,
            "detected_at_utc": datetime.fromtimestamp(
                detected, timezone.utc).isoformat(),
            "requires_immediate_attention": True,
        }, separators=(",", ":")).encode()
        scheduled.append((iid, role, rid, target["url"], target["token"], payload))
    results = []
    if scheduled:
        with ThreadPoolExecutor(max_workers=min(len(scheduled), 16)) as pool:
            futures = [pool.submit(_send_one, item) for item in scheduled]
            for future in as_completed(futures):
                results.append(future.result())
    now = int(time.time())
    with _db() as db:
        _setup(db)
        db.execute("BEGIN IMMEDIATE")
        for iid, role, rid, delivered in results:
            db.execute(
                """UPDATE bozly_diversion_deliveries
                SET status=?,attempts=attempts+1,last_attempt_at=?,
                    delivered_at=CASE WHEN ? THEN ? ELSE delivered_at END
                WHERE incident_id=? AND role=? AND recipient_id=?
                AND status!='DELIVERED'""",
                ("DELIVERED" if delivered else "RETRY",now,1 if delivered else 0,
                 now,iid,role,rid)
            )
        db.commit()
        if incident_id:
            report=db.execute(
                """SELECT role,recipient_id,status FROM bozly_diversion_deliveries
                WHERE incident_id=? ORDER BY role,recipient_id""",
                (incident_id,)
            ).fetchall()
        else:
            report=[]
    return {
        "incident_id":incident_id,
        "delivery_status":[
            {"role":r,"recipient_id":rid,"status":status}
            for r,rid,status in report
        ],
        "all_recipients_notified":bool(report) and all(s=="DELIVERED" for _,_,s in report),
        "required_roles":list(REQUIRED_ROLES),
    }


def report_diversion_attempt(*, entity_id: str, category: str, subject_id: str,
                             request_actor: str, evidence_sha256: str,
                             incident_id: str | None = None) -> dict:
    """Record suspected misconduct and fan out P0 to ALL required officer roles.

    A missing officer endpoint remains visibly UNCONFIGURED; it is never
    interpreted as an authorization to proceed quietly. The caller must
    independently prevent the unauthorized asset movement.
    """
    if category not in CATEGORIES:
        raise ValueError("Unsupported suspected-diversion category")
    if not all(isinstance(v, str) and 0 < len(v) <= 256
               for v in (entity_id, subject_id, request_actor)):
        raise ValueError("Entity, subject and request identity required")
    if (not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64
            or any(c not in "0123456789abcdef" for c in evidence_sha256)):
        raise ValueError("SHA-256 digest of original evidence required")
    incident_id = incident_id or ("div_" + uuid.uuid4().hex)
    config = _recipient_config()
    now = int(time.time())
    with _db() as db:
        _setup(db)
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT entity_id,category,evidence_sha256 FROM bozly_diversion_incidents WHERE incident_id=?",
            (incident_id,)
        ).fetchone()
        if existing and existing != (entity_id,category,evidence_sha256):
            raise ValueError("Conflicting incident identity")
        if not existing:
            db.execute(
                """INSERT INTO bozly_diversion_incidents
                (incident_id,entity_id,category,subject_id,request_actor,evidence_sha256,detected_at)
                VALUES(?,?,?,?,?,?,?)""",
                (incident_id,entity_id,category,subject_id,request_actor,evidence_sha256,now)
            )
        for role in REQUIRED_ROLES:
            recipients = config.get(role, {})
            if recipients:
                db.execute(
                    """DELETE FROM bozly_diversion_deliveries WHERE
                    incident_id=? AND role=? AND recipient_id='__unconfigured__'
                    AND status='UNCONFIGURED'""",(incident_id,role)
                )
                for rid in recipients:
                    db.execute(
                        """INSERT OR IGNORE INTO bozly_diversion_deliveries
                        (incident_id,role,recipient_id,status)
                        VALUES(?,?,?,'PENDING')""",(incident_id,role,rid)
                    )
            else:
                db.execute(
                    """INSERT OR IGNORE INTO bozly_diversion_deliveries
                    (incident_id,role,recipient_id,status)
                    VALUES(?,?,'__unconfigured__','UNCONFIGURED')""",
                    (incident_id,role)
                )
        db.commit()
    return dispatch_pending(incident_id)


def block_and_alert(*, entity_id: str, category: str, subject_id: str,
                    request_actor: str, evidence: bytes):
    """Raise an incident, then deny a suspected diversion irrespective of delivery."""
    report = report_diversion_attempt(
        entity_id=entity_id,category=category,subject_id=subject_id,
        request_actor=request_actor,
        evidence_sha256=hashlib.sha256(evidence).hexdigest()
    )
    raise DiversionDenied(
        "Suspected unauthorized financial diversion blocked; incident " +
        report["incident_id"]
    )
