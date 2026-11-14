"""Bozly CFO event-driven financial observation and reconciliation engine.

This module never initiates a charge, changes Stripe account settings, or infers
a bank payout from a webhook. Verified Stripe events are recorded under a
server-configured legal entity; financial observations are reconciled in SQLite.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Mapping

ENGINE_ID = "BOZLY-CFO-v2.5.0-ROBUST-35"
DEFAULT_DB = "/app/secure_ledgers/bozly_financial_core.db"
PAYMENT_EVENTS = frozenset({
    "invoice.paid",
    "payment_intent.succeeded",
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
})
SUBSCRIPTION_EVENTS = frozenset({
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
})


class BozlyLedgerError(RuntimeError):
    pass


def event_observation(event: Mapping) -> tuple[str, int | None, str | None, str | None]:
    """Return evidence classification, amount in minor units, currency and ref.

    Net payout is intentionally not estimated: Stripe fees, taxes and refunds
    must come from the processor's actual settlement/balance transactions.
    """
    typ = event["type"]
    obj = event["data"]["object"]
    state = "OBSERVED"
    amount = None
    currency = None
    ref = None
    if typ in PAYMENT_EVENTS:
        field = "amount_received" if typ == "payment_intent.succeeded" else (
            "amount_total" if typ.startswith("checkout.session.") else "amount_paid"
        )
        candidate = obj.get(field)
        currency = obj.get("currency")
        paid = typ != "checkout.session.completed" or obj.get("payment_status") == "paid"
        if typ == "checkout.session.async_payment_succeeded":
            paid = obj.get("payment_status") == "paid"
        if paid and type(candidate) is int and candidate >= 0 and (
            isinstance(currency, str) and len(currency) == 3 and currency.isalpha()
        ):
            amount = candidate
            currency = currency.lower()
            ref_value = obj.get("payment_intent")
            if isinstance(ref_value, dict):
                ref_value = ref_value.get("id")
            if not isinstance(ref_value, str) or not ref_value:
                ref_value = obj.get("id")
            if isinstance(ref_value, str) and ref_value:
                ref = ref_value
                state = "PAID_EVENT_OBSERVED"
    elif typ in SUBSCRIPTION_EVENTS:
        ref = obj.get("id") if isinstance(obj.get("id"), str) else None
        state = "SUBSCRIPTION_EVENT_OBSERVED"
    return state, amount, currency, ref


class BozlyCFOCore:
    def __init__(self, db_path: str | None = None):
        self.system_id = ENGINE_ID
        self.db_path = Path(db_path or os.environ.get("BOZLY_DB_PATH", DEFAULT_DB))
        self.db_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS stripe_inbox (
                    event_id TEXT PRIMARY KEY,
                    route_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at INTEGER,
                    body_sha256 TEXT NOT NULL,
                    observation TEXT NOT NULL,
                    amount_minor INTEGER,
                    currency TEXT,
                    payment_ref TEXT,
                    received_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reconcile_queue (
                    event_id TEXT PRIMARY KEY
                        REFERENCES stripe_inbox(event_id),
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS financial_observations (
                    entity_id TEXT NOT NULL,
                    payment_ref TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    first_event_id TEXT NOT NULL,
                    PRIMARY KEY (entity_id, payment_ref)
                );
                CREATE TABLE IF NOT EXISTS subscription_observations (
                    entity_id TEXT NOT NULL,
                    subscription_id TEXT NOT NULL,
                    status TEXT,
                    provider_created_at INTEGER NOT NULL,
                    last_event_id TEXT NOT NULL,
                    PRIMARY KEY (entity_id, subscription_id)
                );
                CREATE TABLE IF NOT EXISTS audit_chain (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    previous_sha256 TEXT NOT NULL,
                    entry_sha256 TEXT NOT NULL,
                    recorded_at INTEGER NOT NULL
                );
            """)

    def _connect(self):
        db = sqlite3.connect(str(self.db_path), timeout=20, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=20000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def reconcile_transaction(
        self, event: Mapping, *,
        route_id: str, entity_id: str, jurisdiction: str, body_sha256: str
    ) -> dict:
        """Atomically persist a previously signature-verified Stripe event.

        Never use Stripe metadata supplied in an event to select legal entity.
        The WSGI receiver supplies entity/jurisdiction from its server-owned route.
        """
        event_id, event_type = event.get("id"), event.get("type")
        data = event.get("data")
        if not (isinstance(event_id, str) and event_id.startswith("evt_")
                and isinstance(event_type, str) and event_type
                and isinstance(data, dict) and isinstance(data.get("object"), dict)):
            raise ValueError("Invalid Stripe event envelope")
        if not all(isinstance(x, str) and x for x in (route_id, entity_id, jurisdiction)):
            raise ValueError("Explicit server-controlled financial route required")
        if len(body_sha256) != 64:
            raise ValueError("SHA-256 request digest required")
        state, amount, currency, ref = event_observation(event)
        received = int(time.time())
        created = event.get("created")
        if type(created) is not int:
            created = None
        started = time.monotonic()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT entity_id, body_sha256 FROM stripe_inbox WHERE event_id=?",
                (event_id,)
            ).fetchone()
            if previous is not None:
                if previous != (entity_id, body_sha256):
                    raise BozlyLedgerError("Conflicting event identity")
                return {
                    "engine_id": self.system_id, "transaction_status": "DUPLICATE",
                    "event_id": event_id, "allocation": {"entity_id": entity_id},
                }
            db.execute(
                """INSERT INTO stripe_inbox
                (event_id,route_id,entity_id,jurisdiction,event_type,created_at,
                 body_sha256,observation,amount_minor,currency,payment_ref,received_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id,route_id,entity_id,jurisdiction,event_type,created,
                 body_sha256,state,amount,currency,ref,received)
            )
            db.execute(
                "INSERT INTO reconcile_queue(event_id,status,updated_at) VALUES (?,?,?)",
                (event_id,"PENDING",received)
            )
            prev = db.execute(
                "SELECT entry_sha256 FROM audit_chain ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_digest = prev[0] if prev else "0" * 64
            digest = hashlib.sha256(
                (prev_digest + ":" + event_id + ":" + body_sha256 +
                 ":" + entity_id).encode("utf-8")
            ).hexdigest()
            db.execute(
                """INSERT INTO audit_chain
                (event_id,previous_sha256,entry_sha256,recorded_at)
                VALUES (?,?,?,?)""",
                (event_id,prev_digest,digest,received)
            )
            db.commit()
        return {
            "engine_id": self.system_id,
            "transaction_status": "RECORDED",
            "event_id": event_id,
            "observation": state,
            "allocation": {"entity_id": entity_id, "jurisdiction": jurisdiction},
            "telemetry": {
                "execution_time_ms": round((time.monotonic() - started) * 1000, 3),
                "resource_footprint": "not_measured",
            },
        }

    def process_pending(self, batch_size: int = 64) -> int:
        """Reconcile only recorded facts; no external financial operations."""
        changed = 0
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT q.event_id, e.entity_id, e.event_type, e.observation,
                   e.amount_minor, e.currency, e.payment_ref, e.created_at
                   FROM reconcile_queue q JOIN stripe_inbox e USING(event_id)
                   WHERE q.status='PENDING' ORDER BY e.received_at LIMIT ?""",
                (batch_size,)
            ).fetchall()
            for event_id, entity, typ, observation, amount, currency, ref, created in rows:
                status = "OBSERVED"
                if observation == "PAID_EVENT_OBSERVED" and ref is not None:
                    existing = db.execute(
                        """SELECT amount_minor,currency FROM financial_observations
                           WHERE entity_id=? AND payment_ref=?""",
                        (entity,ref)
                    ).fetchone()
                    if existing and existing != (amount,currency):
                        status = "CONFLICT"
                    else:
                        db.execute(
                            """INSERT OR IGNORE INTO financial_observations
                               VALUES (?,?,?,?,?)""",
                            (entity,ref,amount,currency,event_id)
                        )
                        status = "RECONCILED_OBSERVATION"
                elif typ in SUBSCRIPTION_EVENTS and ref is not None:
                    if type(created) is not int:
                        created = 0
                    db.execute(
                        """INSERT INTO subscription_observations
                        (entity_id,subscription_id,status,provider_created_at,last_event_id)
                        VALUES (?,?,?,?,?)
                        ON CONFLICT(entity_id,subscription_id) DO UPDATE SET
                        status=excluded.status,
                        provider_created_at=excluded.provider_created_at,
                        last_event_id=excluded.last_event_id
                        WHERE excluded.provider_created_at>=subscription_observations.provider_created_at""",
                        (entity,ref,typ,created,event_id)
                    )
                    status = "SUBSCRIPTION_OBSERVED"
                db.execute(
                    "UPDATE reconcile_queue SET status=?,updated_at=? WHERE event_id=?",
                    (status,int(time.time()),event_id)
                )
                changed += 1
            db.commit()
        return changed


def run_worker() -> None:
    core = BozlyCFOCore()
    poll = float(os.environ.get("BOZLY_POLL_SECONDS", "2"))
    if not 0.1 <= poll <= 300:
        raise ValueError("Invalid polling interval")
    while True:
        core.process_pending()
        # P0 officer notifications are retried independently of an API request.
        # Delivery attempts are non-transactional; failures do not stop the CFO.
        try:
            from bozly_diversion_guard import dispatch_pending
            dispatch_pending()
        except Exception:
            # Keep the worker available; undelivered incidents remain durable.
            import logging
            logging.getLogger("bozly").error("P0 diversion alert retry unavailable")
        time.sleep(poll)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "worker":
        run_worker()
    else:
        raise SystemExit("Usage: python bozly_cfo.py worker")
