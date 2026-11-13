"""Bozly native forensic incident readout.

Read-only owner-scoped console data from native financial diversion and
forensic case records. Absence of entries never proves the entire system
has no intrusions. No spoofed 'system clear' health indicator.
"""
from __future__ import annotations
import os,sqlite3,time
from pathlib import Path
from .bozly_purchasing import ENTITIES
CONTROL="/app/secure_ledgers/bozly_controls.db"
def forensic_snapshot(entity_id,limit=100):
    if entity_id not in ENTITIES:raise ValueError("Unknown legal entity")
    if type(limit)!=int or not 1<=limit<=500:raise ValueError("Invalid limit")
    path=Path(os.environ.get("BOZLY_CONTROL_DB",CONTROL))
    if not path.is_file():
        return {"entity_id":entity_id,"status":"NO_CONTROL_LEDGER",
            "incidents":[],"incident_count_observed":None,
            "overall_security_health_verified":False}
    with sqlite3.connect(str(path)) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "bozly_diversion_incidents" not in tables:
            return {"entity_id":entity_id,"status":"NO_INCIDENT_TABLE",
                "incidents":[],"incident_count_observed":None,
                "overall_security_health_verified":False}
        rows=db.execute("""SELECT incident_id,category,subject_id,evidence_sha256,
            detected_at,severity FROM bozly_diversion_incidents
            WHERE entity_id=? ORDER BY detected_at DESC LIMIT ?""",
            (entity_id,limit)).fetchall()
        count=db.execute("""SELECT COUNT(*) FROM bozly_diversion_incidents
            WHERE entity_id=?""",(entity_id,)).fetchone()[0]
    return {"entity_id":entity_id,"status":"LEDGER_READ",
        "incident_count_observed":count,"incidents":[{
          "incident_id":a,"category":b,"subject_id":c,
          "evidence_sha256":d,"detected_unix":e,"severity":f}
          for a,b,c,d,e,f in rows],
        "overall_security_health_verified":False,"read_unix":int(time.time())}
