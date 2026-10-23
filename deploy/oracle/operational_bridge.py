"""Persist canonical endpoint observations in the existing Sanders operational SQLite database.

Separate endpoint identities remain visible; no endpoint is promoted to an AI agent.
TCP connectivity is not application readiness. This module never performs repairs.
"""
import json
import sqlite3
import time
from pathlib import Path

from deploy.oracle.oracle_registry_probe import probe, validate

SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_canonical_endpoint_observations (
  observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  system_id INTEGER NOT NULL,
  observed_at REAL NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('tcp_reachable','tcp_unreachable')),
  elapsed_ms INTEGER NOT NULL,
  UNIQUE(system_id,observed_at)
);
CREATE TABLE IF NOT EXISTS ai_canonical_endpoint_incidents (
  incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
  system_id INTEGER NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('OPEN','OBSERVED_RECOVERY')),
  opened_observation INTEGER NOT NULL,
  closed_observation INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS ai_canonical_endpoint_one_open
ON ai_canonical_endpoint_incidents(system_id) WHERE state='OPEN';
"""

def record_cycle(database, entries, results, *, clock=time.time):
    entries = validate(entries)
    if len(results) != len(entries):
        raise ValueError('Incomplete endpoint observation cycle')
    expected = {(e['id'], e['host'], e['port'], e['name']) for e in entries}
    received = {(r['id'], r['host'], r['port'], r['name']) for r in results}
    if expected != received or len(received) != len(results):
        raise ValueError('Endpoint identity mismatch')
    observed = clock()
    with sqlite3.connect(str(database), timeout=10) as db:
        db.executescript(SCHEMA)
        db.execute('BEGIN IMMEDIATE')
        for r in results:
            if r['status'] not in ('tcp_reachable','tcp_unreachable'):
                raise ValueError('Invalid endpoint status')
            cursor = db.execute(
                'INSERT INTO ai_canonical_endpoint_observations(system_id,observed_at,status,elapsed_ms) VALUES(?,?,?,?)',
                (r['id'], observed, r['status'], r['elapsed_ms']))
            active = db.execute(
                "SELECT incident_id FROM ai_canonical_endpoint_incidents WHERE system_id=? AND state='OPEN'",
                (r['id'],)).fetchone()
            if r['status'] == 'tcp_unreachable' and active is None:
                db.execute('INSERT INTO ai_canonical_endpoint_incidents(system_id,state,opened_observation) VALUES(?,?,?)',
                           (r['id'], 'OPEN', cursor.lastrowid))
            elif r['status'] == 'tcp_reachable' and active:
                db.execute("UPDATE ai_canonical_endpoint_incidents SET state='OBSERVED_RECOVERY',closed_observation=? WHERE incident_id=?",
                           (cursor.lastrowid, active[0]))
    return {'observed_at': observed, 'systems': len(results)}

def run(database, registry, *, timeout=1.5, workers=12):
    from concurrent.futures import ThreadPoolExecutor
    entries = validate(json.loads(Path(registry).read_text(encoding='utf-8'))['platforms'])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda e: probe(e, timeout), entries))
    return record_cycle(database, entries, results)
