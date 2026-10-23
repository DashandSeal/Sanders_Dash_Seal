#!/usr/bin/env python3
"""Observe the owner's canonical endpoint inventory; no deployment or mutation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time

REGISTRY = Path(__file__).with_name("sanders_master_grid.json")

def validate(entries):
    if len(entries) != 38:
        raise ValueError("Expected all 38 canonical entries")
    if [e["port"] for e in entries] != list(range(3001, 3039)):
        raise ValueError("Canonical port sequence mismatch")
    if len({e["name"] for e in entries}) != 38:
        raise ValueError("Duplicate platform names")
    if any(len(e["naics"]) != 6 for e in entries):
        raise ValueError("Every entry requires six industry codes")
    return entries

def probe(entry, timeout):
    start = time.monotonic()
    try:
        with socket.create_connection((entry["host"], entry["port"]), timeout=timeout):
            status, detail = "tcp_reachable", None
    except OSError as exc:
        status, detail = "tcp_unreachable", f"{type(exc).__name__}: {exc}"[:240]
    return {
        "id": entry["id"], "name": entry["name"],
        "host": entry["host"], "port": entry["port"],
        "status": status, "detail": detail,
        "elapsed_ms": round((time.monotonic() - start) * 1000),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, default=Path("oracle_probe_results.json"))
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if not 0 < args.timeout <= 30 or not 1 <= args.workers <= 64:
        parser.error("timeout must be 0..30 and workers must be 1..64")
    entries = validate(json.loads(args.registry.read_text(encoding="utf-8"))["platforms"])
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda entry: probe(entry, args.timeout), entries))
    report = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "measurement": "TCP connectivity only; not application readiness or AI functionality",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(results), "reachable": sum(r["status"] == "tcp_reachable" for r in results), "output": str(args.output)}))

if __name__ == "__main__":
    main()
