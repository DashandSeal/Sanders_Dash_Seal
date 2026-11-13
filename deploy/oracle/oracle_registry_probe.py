"""
Module: deploy.oracle.oracle_registry_probe
Architectural Layer: Read-Only Concurrent Canonical Endpoint Observer
Property of: Sanders Legal Helpers LLC
Developed by: Roosevelt Sanders
Description: Observes the owner's canonical endpoint inventory without executing
             mutations or deployment alterations. Validates system port sequence integrity
             and isolates network state tracking cleanly under Always Free tier allocations.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time

REGISTRY = Path(__file__).parent / "sanders_master_grid.json"

class ProbeValidationDenied(ValueError):
    pass


def validate(entries: list) -> list:
    """Validates structural properties and port integrity constraints of the master grid registry."""
    if not isinstance(entries, list):
        raise ProbeValidationDenied("Platforms registry payload must be an array list structure")

    if len(entries) != 38:
        raise ProbeValidationDenied("Expected all 38 canonical entries inside the infrastructure registry matrix")

    extracted_ports = []
    seen_names = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ProbeValidationDenied(f"Malformed structure detected at element slot index {index}")

        # Strict parameter visibility guards
        required_keys = ("id", "name", "host", "port", "naics")
        if not all(k in entry for k in required_keys):
            raise ProbeValidationDenied(f"Missing mandatory platform attributes at element slot index {index}")

        extracted_ports.append(entry["port"])
        seen_names.add(entry["name"])

        # Validate NAICS data structure properties
        naics_data = entry["naics"]
        if isinstance(naics_data, list):
            if any(not isinstance(code, str) or len(code) != 6 for code in naics_data):
                raise ProbeValidationDenied(f"Invalid NAICS identifier structure at slot index {index}")
        elif isinstance(naics_data, str):
            if len(naics_data) != 6:
                raise ProbeValidationDenied(f"Invalid single NAICS identifier width at slot index {index}")
        else:
            raise ProbeValidationDenied(f"Unsupported NAICS sequence data format type at slot index {index}")

    if extracted_ports != list(range(3001, 3039)):
        raise ProbeValidationDenied("Canonical network port assignment sequence mismatch")

    if len(seen_names) != 38:
        raise ProbeValidationDenied("Duplicate platform names identified across registry configurations")

    return entries


def probe(entry: dict, timeout: float) -> dict:
    """Probes the network surface of an individual canonical node using ephemeral socket boundaries."""
    start_time = time.monotonic()
    target_host = str(entry["host"])
    target_port = int(entry["port"])

    try:
        # Use short dual-stack socket connections to minimize block times
        with socket.create_connection((target_host, target_port), timeout=timeout):
            status, detail = "tcp_reachable", None
    except OSError as exc:
        status, detail = "tcp_unreachable", f"{type(exc).__name__}: {str(exc)[:240]}"

    elapsed_ms = round((time.monotonic() - start_time) * 1000)

    return {
        "id": entry["id"],
        "name": entry["name"],
        "host": target_host,
        "port": target_port,
        "status": status,
        "detail": detail,
        "elapsed_ms": elapsed_ms
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, default=Path("oracle_probe_results.json"))
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    if not 0.1 <= args.timeout <= 30.0 or not 1 <= args.workers <= 64:
        parser.error("Network timeout parameter constraints must fall between 0.1..30 and workers 1..64")

    if not args.registry.is_file():
        parser.error(f"Specified master infrastructure registry grid not found at path destination: {args.registry}")

    try:
        raw_payload = json.loads(args.registry.read_text(encoding="utf-8"))
        platform_entries = raw_payload.get("platforms", [])
        validated_entries = validate(platform_entries)
    except Exception as read_error:
        parser.error(f"Failed to process master grid configurations: {str(read_error)}")

    # Map connection states concurrently across pooled threads
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda e: probe(e, args.timeout), validated_entries))

    report = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "measurement": "TCP connectivity only; not application readiness or AI functionality",
        "results": results
    }

    # Ensure targeted data tree branches are present before writing outcomes
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary_telemetry = {
        "total": len(results),
        "reachable": sum(r["status"] == "tcp_reachable" for r in results),
        "output_path": str(args.output)
    }
    print(json.dumps(summary_telemetry))


if __name__ == "__main__":
    main()
