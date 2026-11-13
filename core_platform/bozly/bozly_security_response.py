"""Platinum Blue Diamond: native Minotaur integrity response and forensic chain.

This is the operating response for the owner's existing minotaur_sentinel.py.
It does not modify the owner's Sentinel or Labyrinth Shield source.
Monitoring is confined to local, authorized Bozly files and service metadata.
No remote host interrogation, counterattack, secret scanning or attribution claims.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import time
import uuid

from minotaur_sentinel import MinotaurSentinel, PROTECTED_TARGETS

ROOT = Path(os.environ.get("BOZLY_SECURITY_ROOT", "/app")).resolve()
STATE = Path(os.environ.get("BOZLY_SECURITY_STATE_DIR",
                            "/app/secure_ledgers/security")).resolve()
INTERVAL = float(os.environ.get("BOZLY_SECURITY_SCAN_SECONDS", "10"))


def _within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _private_dir():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)


def _digest_file(path: Path) -> str:
    if not path.is_file():
        return "FILE_MISSING"
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _targets() -> list[str]:
    # The owner's original target list is retained, plus the remaining
    # native Bozly engines and security runtime assets already present.
    # Bozly modules live in core_platform/bozly/ (WSGI entrypoints in
    # web/); names are paths relative to the security root.
    names = set(PROTECTED_TARGETS)
    for pattern in ("bozly_*.py", "core_platform/bozly/bozly_*.py",
                    "web/bozly_*.py"):
        names.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern)
                     if p.is_file())
    names.update(("minotaur_sentinel.py",
                  "core_platform/bozly/bozly_security_response.py",
                  "web/bozly_shield_wsgi.py"))
    return sorted(names)


def _file_observation(name: str) -> dict:
    path = (ROOT / name).resolve()
    if not _within(path, ROOT):
        raise ValueError("Target path escaped security root")
    try:
        info = path.stat()
        return {
            "path": name,
            "sha256": _digest_file(path),
            "size_bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns,
            "owner_uid": info.st_uid,
            "owner_gid": info.st_gid,
        }
    except FileNotFoundError:
        return {"path": name, "sha256": "FILE_MISSING"}


def _event(event_type: str, evidence: dict, severity: str) -> dict:
    """Append evidence to a private host-local SHA-256-chained forensic ledger."""
    _private_dir()
    logfile = STATE / "forensic_breach_manifest.pbd.json"
    record = {
        "incident_id": "bzsec_" + uuid.uuid4().hex,
        "event": event_type,
        "severity": severity,
        "observed_at_unix_ns": time.time_ns(),
        "host": socket.gethostname(),
        "observing_process_id": os.getpid(),
        "evidence": evidence,
        "responsible_person_identified": False,
        "identity_attribution": "UNDETERMINED",
    }
    fd = os.open(str(logfile), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(os.dup(fd), "r", encoding="utf-8") as previous_log:
            lines = previous_log.readlines()
        last = json.loads(lines[-1]) if lines else None
        record["previous_entry_sha256"] = (last.get("entry_sha256")
                                          if last else "0" * 64)
        body = json.dumps(record, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False).encode()
        record["entry_sha256"] = hashlib.sha256(body).hexdigest()
        os.lseek(fd, 0, os.SEEK_END)
        os.write(fd, (json.dumps(record, sort_keys=True,
                                 separators=(",", ":")) + "\n").encode())
        os.fsync(fd)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    return {"incident_id": record["incident_id"],
            "evidence_sha256": record["entry_sha256"],
            "event": event_type}


def record_request_rejection(*,remote_address: str,path: str,reason: str,
                             request_sha256: str):
    # Defensive telemetry from Bozly's own inbound request only.
    return _event("SHIELD_REQUEST_REJECTED", {
        "remote_address": str(remote_address)[:150],
        "request_path": str(path)[:250],
        "reason": str(reason)[:120],
        "request_body_sha256": request_sha256,
    }, "P1")


def _baseline_file() -> Path:
    return STATE / "minotaur_approved_baseline.json"


def _baseline():
    """One persistent first-start snapshot; do not silently reset on restart."""
    _private_dir()
    baseline = _baseline_file()
    if baseline.exists():
        with baseline.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise ValueError("Unrecognized persisted Sentinel baseline")
        return data["targets"]
    observations = {name: _file_observation(name) for name in _targets()}
    fd = None
    try:
        fd = os.open(str(baseline), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        data = {"schema": 1, "established_at_unix": int(time.time()),
                "targets": observations}
        os.write(fd, json.dumps(data, sort_keys=True).encode())
        os.fsync(fd)
    except FileExistsError:
        with baseline.open("r", encoding="utf-8") as file:
            return json.load(file)["targets"]
    finally:
        if fd is not None:
            os.close(fd)
    _event("MINOTAUR_BASELINE_ESTABLISHED", {
        "tracked_targets": sorted(observations),
        "initially_missing": sorted(
            name for name, obj in observations.items()
            if obj["sha256"] == "FILE_MISSING"
        ),
    }, "INFO")
    return observations


def isolation_state() -> dict:
    path = STATE / "minotaur_isolation.json"
    if not path.exists():
        return {"isolated": False}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return {"isolated": bool(data["isolated"]),
                "incident_id": data.get("incident_id"),
                "detected_at_unix": data.get("detected_at_unix")}
    except (OSError, ValueError, KeyError):
        # Missing/unreadable trustworthy state cannot be misreported as clear.
        return {"isolated": True, "state_read_error": True}


def _isolate(event: dict, target: str):
    """Persist isolation readable by every Bozly web-worker process.

    Records the affected target for the owner's forensic response.
    This does not impose an assistant-designed global shutdown on Bozly.
    """
    _private_dir()
    destination = STATE / "minotaur_isolation.json"
    tmp = STATE / (".isolation-" + uuid.uuid4().hex)
    data = {"isolated": True, "incident_id": event["incident_id"],
            "target": target, "detected_at_unix": int(time.time())}
    with tmp.open("x", encoding="utf-8") as out:
        json.dump(data, out, sort_keys=True)
        out.flush()
        os.fsync(out.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, destination)


def patrol_once(sentinel: MinotaurSentinel, approved: dict) -> list[dict]:
    # Runs the user's actual Sentinel algorithm; durable baseline protects
    # against unobserved changes between daemon restarts.
    raw = sentinel.execute_patrol_cycle()
    observed = {name: _file_observation(name)
                for name in sorted(set(approved) | set(_targets()))}
    anomalies = []
    for name, initial in approved.items():
        current = observed[name]
        if current["sha256"] != initial["sha256"]:
            anomalies.append({
                "target": name,
                "expected_sha256": initial["sha256"],
                "observed": current,
                "sentinel_cycle_anomalies": raw[:100],
            })
    # Protect against silent addition of security-relevant executable modules.
    for name in observed.keys() - approved.keys():
        if observed[name]["sha256"] != "FILE_MISSING":
            anomalies.append({"target": name, "expected_sha256": "NOT_IN_BASELINE",
                              "observed": observed[name],
                              "sentinel_cycle_anomalies": raw[:100]})
    # Stable dedupe: persist changes only on new anomaly signatures.
    dedupe = STATE / "minotaur_last_anomaly_sha256"
    fingerprint = hashlib.sha256(json.dumps(anomalies, sort_keys=True).encode()).hexdigest()
    prior = dedupe.read_text().strip() if dedupe.exists() else ""
    if anomalies and fingerprint != prior:
        record = _event("MINOTAUR_FILE_INTEGRITY_ALERT", {
            "anomalies": anomalies, "detection_source": "LOCAL_FILE_INTEGRITY",
            "traceback_scope": "LOCAL_EVIDENCE_AVAILABLE_FOR_GLOBAL_CORRELATION",
            "no_actor_attribution_without_additional_CORROBORATION": True,
        }, "P0")
        _isolate(record, anomalies[0]["target"])
        dedupe.write_text(fingerprint, encoding="ascii")
        os.chmod(dedupe, 0o600)
    return anomalies


def daemon():
    if INTERVAL <= 0:
        raise ValueError("Scan interval must be positive")
    os.chdir(ROOT)
    sentinel = MinotaurSentinel()
    approved = _baseline()
    while True:
        try:
            patrol_once(sentinel, approved)
        except Exception as error:
            record = _event("MINOTAUR_PATROL_FAILED", {
                "error_type": type(error).__name__,
                "details": "PATROL_FAILED"}, "P0")
            _isolate(record, "minotaur_patrol")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    daemon()
