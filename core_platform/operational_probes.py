"""
Actual local probes for the operational observation cycle; no repair executor.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import time
from contextlib import closing
from urllib.request import Request, ProxyHandler, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

from operational_runtime import import_observation, readonly_database
from upgrade_sidecar import CORE_LAWS

class Noredirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def http_probe(url, *, opener=None, clock=time.monotonic):
    # URLs are fixed by this module. Never taken from HTTP requests or model output.
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    start = clock()
    try:
        with opener.open(Request(url, headers={'Host': 'sandersdashandseal.com'}), timeout=3) as response:
            code = response.status
            raw = response.read(8192)
        if len(raw) == 8192:
            return observation("UNKNOWN", "INVALID_HEALTH_RESPONSE")
        value = json.loads(raw)
        expected = "service_ready" if url.endswith("/readyz") else "process_alive"
        if code == 200 and isinstance(value, dict) and value.get(expected) is True:
            return observation("HEALTHY", "HTTP_VERIFIED", latency_ms=max(0, (clock()-start)*1000))
        return observation("FAULT", "HTTP_UNHEALTHY", http_status=code)
    except HTTPError as error:
        code = error.code
        error.close()
        return observation("FAULT", "HTTP_UNHEALTHY", http_status=code)
    except (OSError, ValueError):
        return observation("FAULT", "HTTP_UNAVAILABLE")

def database_probe(path):
    try:
        with closing(readonly_database(path)) as db:
            result = db.execute("PRAGMA quick_check;").fetchall()
        return observation("HEALTHY", "DATABASE_CHECKED") if result == [('ok',)] else observation("FAULT", "DATABASE_CORRUPT")
    except sqlite3.Error:
        return observation("FAULT", "DATABASE_UNAVAILABLE")

def source_probe(root):
    files = list((Path(root)/'core_platform').glob('*.py'))
    if not files:
        return observation("UNKNOWN", "SOURCE_NOT_OBSERVED")
    try:
        for path in files:
            manifest = Path(str(path)+'.pbd.json')
            if path.is_symlink() or manifest.is_symlink():
                return observation("FAULT", "SOURCE_INTEGRITY_MISMATCH")
            pair = json.loads(manifest.read_text())
            if (pair['body']['artifact'] != path.relative_to(root).as_posix()
                or pair['body']['payload_hash'] != hashlib.sha256(path.read_bytes()).hexdigest()):
                return observation("FAULT", "SOURCE_INTEGRITY_MISMATCH")
        return observation("HEALTHY", "SOURCE_HASHES_MATCH", files_checked=len(files))
    except (OSError, ValueError, KeyError, TypeError):
        return observation("FAULT", "SOURCE_PAIR_INVALID")

def integration_probe(path):
    with closing(readonly_database(path)) as db:
        rows = db.execute("SELECT state, COUNT(*) FROM provider_requests GROUP BY state;").fetchall()
    # Only report uncertain operations. Stored successful requests do not prove
    # credentials or external providers are currently connected.
    uncertain = sum(count for state, count in rows if state == 'UNCERTAIN')
    return observation("FAULT" if uncertain else "UNKNOWN",
                       "PROVIDER_RECONCILIATION_REQUIRED" if uncertain else "LIVE_PROVIDER_NOT_PROBED",
                       uncertain_requests=uncertain)

def backup_probe(path, clock=time.monotonic):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return observation("UNKNOWN", "BACKUP_NOT_OBSERVED")
    value = json.loads(path.read_text())
    if (value.get("status") != "BACKUP_RESTORE_VERIFIED"
        or type(value.get("verified_at")) not in (int, float)
        or not math.isfinite(value["verified_at"]) or value["verified_at"] < 0
        or value["verified_at"] > clock() or value.get("databases_verified") != 2):
        return observation("UNKNOWN", "BACKUP_EVIDENCE_INVALID")
    return observation("HEALTHY", "BACKUP_RESTORE_OBSERVED", age_seconds=clock()-value["verified_at"])

def configured_probes(path, audit, *, root=None, backup_status="/run/sds/backup-status.json"):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def audit_probe():
        try:
            audit.verify_audit()
            return observation("HEALTHY", "LOCAL_AUDIT_CHAIN_CHECKED")
        except Exception:
            return observation("FAULT", "AUDIT_CHAIN_UNAVAILABLE")

    def config_probe():
        catalog = json.loads((root/'core_platform/oci_free_resources.json').read_text())
        correct = item(CORE_LAWS) == catalog['governing_core_law']['number'] == 10
        return observation("HEALTHY" if correct else "FAULT", "TEN_LAWS_MATCH" if correct else "LAW_CONFIGURATION_MISMATCH")

    def disk_probe():
        usage = shutil.disk_usage(Path(path).parent)
        return observation("HEALTHY" if usage.free > 0 else "FAULT",
                           "DISK_SPACE_OBSERVED" if usage.free > 0 else "DISK_FULL", free_bytes=usage.free, total_bytes=usage.total)

    def support_probe():
        with closing(readonly_database(path)) as db:
            count = db.execute("SELECT COUNT(*) FROM ai_operational_incidents WHERE state='OPEN';").fetchone()[0]
        return observation("HEALTHY", "INCIDENT_INVENTORY_READ", open_incidents=count)

    def quality_probe():
        # This is a separate observation, never a signed Quality attestation.
        with closing(readonly_database(path)) as db:
            count = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('ai_observation_cycles');").fetchone()[0]
        return observation("HEALTHY" if count == 1 else "FAULT", "SUPERVISION_SCHEMA_CHECKED", tables=count)

    return {
        "uptime": lambda: http_probe("http://127.0.0.1:8000/healthz"),
        "application": lambda: http_probe("http://127.0.0.1:8000/readyz"),
        "database": lambda: database_probe(path),
        "deployment": lambda: source_probe(root),
        "infrastructure": disk_probe,
        "integration": lambda: integration_probe(path),
        "performance": lambda: http_probe("http://127.0.0.1:8000/healthz"),
        "backup": lambda: backup_probe(backup_status),
        "observability": audit_probe,
        "quality": quality_probe,
        "configuration": config_probe,
        "support": support_probe
    }
