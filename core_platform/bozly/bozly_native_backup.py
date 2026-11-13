"""Bozly native online SQLite database backup with SHA-256 manifests.

Uses Python sqlite3 backup API for WAL-safe consistent snapshots; no external
backup SaaS. Backups are separate from recovery guarantees. The owner schedules
deployment according to the existing Oracle Always Free architecture.
"""
from __future__ import annotations
import hashlib,json,os,sqlite3,time
from pathlib import Path
def _hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as file:
        while True:
            chunk=file.read(1024*1024)
            if not chunk:break
            h.update(chunk)
    return h.hexdigest()
def snapshot(*,source_db=None,target_directory=None):
    source=Path(source_db or os.environ.get("BOZLY_DB_PATH",
        "/app/secure_ledgers/bozly_financial_core.db")).resolve()
    out=Path(target_directory or os.environ.get("BOZLY_BACKUP_DIR",
        "/app/secure_ledgers/backups")).resolve()
    if not source.is_file() or source.stat().st_size==0:
        raise FileNotFoundError("Native source ledger not present")
    if not source.name.endswith((".db",".sqlite",".sqlite3")):
        raise ValueError("Expected SQLite database file")
    if source==out or source in out.parents:
        raise ValueError("Unsafe backup destination")
    out.mkdir(parents=True,exist_ok=True,mode=0o700)
    stamp=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())
    name=source.stem+"_"+stamp+"_"+os.urandom(6).hex()
    temp=out/(name+".partial")
    dest=out/(name+".db")
    try:
        src=sqlite3.connect(f"file:{source}?mode=ro",uri=True,timeout=30)
        try:
            dst=sqlite3.connect(str(temp),timeout=30)
            try:
                src.backup(dst,pages=256,sleep=0.05)
            finally:dst.close()
        finally:src.close()
        os.chmod(temp,0o600)
        digest=_hash(temp)
        size=temp.stat().st_size
        os.replace(temp,dest)
        manifest={"file":dest.name,"source":source.name,"sha256":digest,
            "size_bytes":size,"snapshot_unix":int(time.time()),
            "source_ledger_independently_audited":False}
        mf=out/(name+".json")
        with open(mf,"x",encoding="utf-8") as f:
            json.dump(manifest,f,sort_keys=True,separators=(",",":"))
        os.chmod(mf,0o600)
        return {"status":"SNAPSHOT_WRITTEN","destination":str(dest),
            "manifest":str(mf),"sha256":digest,"size_bytes":size,
            "off_host_redundancy_confirmed":False}
    finally:
        if temp.exists():temp.unlink()
