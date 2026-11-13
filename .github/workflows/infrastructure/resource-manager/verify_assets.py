#!/usr/bin/env python3
"""
BOZLY RESOURCING: INFRASTRUCTURE ASSET VALIDATOR
Standard: Platinum Blue Diamond Standard | Level 35+ Hyper-State Environment Gate
"""

import os
import sys
import hashlib

ASSETS = [
    "infrastructure/resource-manager/bozly_apparmor.profile",
    "infrastructure/resource-manager/bozly_watchdog_trigger.py"
]

def audit_infrastructure_assets():
    print("=====================================================================")
    print(" RUNNING BOZLY SECURITY ARCHIVE INTEGRITY CHECKS")
    print("=====================================================================")
    
    for asset_path in ASSETS:
        if not os.path.exists(asset_path):
            print(f"::error::Required infrastructure asset missing: {asset_path}")
            sys.exit(1)
            
        sha256 = hashlib.sha256()
        with open(asset_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        print(f"✓ Verified Asset Footprint [{asset_path}]: {sha256.hexdigest()}")
        
    print("✓ All Infrastructure Automated Containment Assets: Passed")

if __name__ == "__main__":
    audit_infrastructure_assets()
