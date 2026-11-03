"""Bozly store-and-forward satellite/terrestrial gateway adapter.

Requires an actual HTTPS gateway, carrier connectivity, satellite terminal,
billing arrangement and credentials. There is no simulated satellite uplink.
Messages are already ciphertext envelopes, never plain financial information.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from bozly_operations import _db


def configuration():
    endpoint=os.environ.get("BOZLY_UPLINK_GATEWAY_URL","")
    token=os.environ.get("BOZLY_UPLINK_BEARER_TOKEN","")
    parsed=urlparse(endpoint)
    if not endpoint or parsed.scheme!="https" or not parsed.hostname or not token:
        raise RuntimeError("Real HTTPS satellite gateway and credential required")
    if parsed.username or parsed.password or parsed.fragment:
        raise RuntimeError("Gateway URL must not contain credentials or fragments")
    return endpoint,token


def deliver_pending(max_batch=32):
    endpoint,token=configuration()
    sent=0
    with _db() as db:
        messages=db.execute(
            """SELECT message_id,entity_id,priority,payload_ciphertext,attempts
               FROM uplink_outbox WHERE status IN ('PENDING','RETRY')
               AND attempts<20 ORDER BY
               CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1
                 WHEN 'P2' THEN 2 ELSE 3 END,created_at LIMIT ?""",
            (max_batch,)
        ).fetchall()
    for message_id,entity,priority,cipher,attempts in messages:
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            claimed=db.execute(
                """UPDATE uplink_outbox SET status='SENDING',attempts=attempts+1,
                    updated_at=? WHERE message_id=? AND status IN ('PENDING','RETRY')""",
                (int(time.time()),message_id)).rowcount
            db.commit()
        if not claimed:
            continue
        payload=json.dumps({
            "message_id":message_id,"entity_id":entity,
            "priority":priority,"encrypted_envelope":json.loads(cipher)
        },separators=(",",":")).encode()
        req=urllib.request.Request(endpoint,data=payload,method="POST",headers={
            "Authorization":"Bearer "+token,
            "Content-Type":"application/json",
            "Idempotency-Key":message_id,
        })
        delivered=False
        try:
            opener=urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPRedirectHandler(),
            )
            with opener.open(req,timeout=20) as response:
                delivered=200<=response.status<300
        except (urllib.error.URLError,TimeoutError,OSError,ValueError):
            pass
        with _db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE uplink_outbox SET status=?,updated_at=? WHERE message_id=?",
                ("DELIVERED_TO_GATEWAY" if delivered else "RETRY",
                 int(time.time()),message_id)
            )
            db.commit()
        if delivered:
            sent+=1
    return sent


def run():
    configuration()
    while True:
        deliver_pending()
        time.sleep(5)


if __name__=="__main__":
    run()
