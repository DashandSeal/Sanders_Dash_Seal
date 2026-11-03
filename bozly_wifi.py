"""Bozly native Linux Wi-Fi connectivity agent.

Uses the host's NetworkManager and an actual wireless interface. Can detect
Wi-Fi state and activate an existing saved Wi-Fi profile by UUID; it never
requests, logs, exports or stores Wi-Fi passwords.

Run on a Wi-Fi-capable host with NetworkManager permissions, not in the
isolated Docker container. No claim of existing hardware or connectivity.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class WiFiUnavailable(RuntimeError):
    pass


def _nmcli(*args: str, timeout: int = 12) -> str:
    binary=shutil.which("nmcli")
    if not binary:
        raise WiFiUnavailable("NetworkManager nmcli is not installed on this host")
    try:
        result=subprocess.run(
            [binary, *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "LC_ALL":"C"}
        )
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise WiFiUnavailable("Host network manager is unavailable") from exc
    if result.returncode:
        # Never echo arbitrary NetworkManager stderr: it may expose credentials.
        raise WiFiUnavailable("NetworkManager could not complete requested operation")
    return result.stdout


def _device_rows() -> list[dict]:
    raw=_nmcli("-t","-f","DEVICE,TYPE,STATE,CONNECTION","device","status")
    rows=[]
    for line in raw.splitlines():
        # nmcli escapes ':' inside profile names. Keep only known state fields
        # and never depend on the human-readable connection-name field.
        fields=line.split(":",3)
        if len(fields)<3:
            continue
        dev,typ,state=fields[:3]
        if dev and typ:
            rows.append({"device":dev,"type":typ,"state":state})
    return rows


def status() -> dict:
    devices=_device_rows()
    radios=_nmcli("radio","wifi").strip().lower()
    wifi=[d for d in devices if d["type"]=="wifi"]
    connected=[d["device"] for d in wifi if d["state"]=="connected"]
    wired=[d["device"] for d in devices if d["type"]=="ethernet" and d["state"]=="connected"]
    cellular=[d["device"] for d in devices if d["type"] in ("gsm","cdma","wwan") and d["state"]=="connected"]
    return {
        "component":"BOZLY_WIFI",
        "wifi_radio_enabled":radios=="enabled",
        "wifi_hardware_detected":bool(wifi),
        "wifi_connected":bool(connected),
        "wifi_interfaces_connected":connected,
        "wired_interfaces_connected":wired,
        "mobile_broadband_interfaces_connected":cellular,
        "any_detected_link_connected":bool(connected or wired or cellular),
        "internet_reachability":"not_measured",
        "observed_at_unix":int(time.time()),
    }


def available_saved_wifi() -> list[str]:
    """Profile UUIDs only; hide SSIDs and secrets in logs and reports."""
    raw=_nmcli("-t","-f","UUID,TYPE","connection","show")
    uuids=[]
    for line in raw.splitlines():
        parts=line.split(":",1)
        if len(parts)==2 and parts[1].strip() in ("802-11-wireless","wifi"):
            value=parts[0].strip()
            if UUID_PATTERN.fullmatch(value):
                uuids.append(value.lower())
    return uuids


def connect_saved_wifi(uuid: str) -> dict:
    """Activate an existing Wi-Fi connection profile; do not invent credentials."""
    if not isinstance(uuid,str) or not UUID_PATTERN.fullmatch(uuid):
        raise ValueError("Expected saved NetworkManager Wi-Fi connection UUID")
    if uuid.lower() not in available_saved_wifi():
        raise WiFiUnavailable("That UUID is not a saved Wi-Fi connection profile")
    result=_nmcli("--wait","25","connection","up","uuid",uuid,timeout=33)
    observed=status()
    return {
        "component":"BOZLY_WIFI",
        "requested_profile_uuid":uuid.lower(),
        "activation_command_accepted":bool(result.strip()) or observed["wifi_connected"],
        "wifi_connected_now":observed["wifi_connected"],
        "actual_host_observation":observed,
    }


def maintain_connectivity(*, retry_seconds: int=30):
    """Restore owner-configured saved Wi-Fi when wireless connectivity drops.

    Never disconnect an active wired, cellular or wireless link, and never
    join a new/unknown hotspot. Leave fallback routing to NetworkManager.
    """
    if type(retry_seconds) is not int or not 5<=retry_seconds<=600:
        raise ValueError("Retry interval must be 5..600 seconds")
    raw=os.environ.get("BOZLY_WIFI_SAVED_PROFILE_UUIDS","")
    preferred=[u.strip().lower() for u in raw.split(",") if u.strip()]
    if any(not UUID_PATTERN.fullmatch(u) for u in preferred):
        raise ValueError("Invalid owner-configured Wi-Fi profile UUID")
    while True:
        try:
            observed=status()
            if preferred and observed["wifi_hardware_detected"] and not observed["wifi_connected"]:
                known=set(available_saved_wifi())
                for uuid in preferred:
                    if uuid not in known:
                        continue
                    try:
                        updated=connect_saved_wifi(uuid)
                        if updated["wifi_connected_now"]:
                            break
                    except WiFiUnavailable:
                        continue
        except WiFiUnavailable:
            # The host may be booting; loop and recover on the next iteration.
            pass
        time.sleep(retry_seconds)


def main():
    parser=argparse.ArgumentParser(description="Bozly native host Wi-Fi operations")
    parser.add_argument("command",choices=("status","connect","maintain"))
    parser.add_argument("--uuid",default="")
    args=parser.parse_args()
    if args.command=="status":
        print(json.dumps(status(),sort_keys=True))
    elif args.command=="connect":
        print(json.dumps(connect_saved_wifi(args.uuid),sort_keys=True))
    else:
        maintain_connectivity()


if __name__=="__main__":
    main()
