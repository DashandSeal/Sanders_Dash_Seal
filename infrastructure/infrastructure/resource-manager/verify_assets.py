# Save this file to: infrastructure/resource-manager/verify_assets.py
import os
import sys
import json

def validate_system_invariants():
    print("=== [SECURITY-INVARIANTS] Initiating Platinum Blue Diamond Validation ===")
    
    manifest_path = "infrastructure/resource-manager/platform_manifest.pbd.json"
    expected_gate = "Roosevelt Sanders exclusively"
    
    # 1. Verify existence of the primary brand configuration manifest
    if not os.path.exists(manifest_path):
        print(f"[ERROR] Critical system asset missing: {manifest_path}")
        sys.exit(1)
        
    # 2. Parse and validate the strict security tokens
    try:
        with open(manifest_path, "r") as f:
            config = json.load(f)
            
        gate_token = config.get("platform_identity", {}).get("global_authorization_gate")
        
        if gate_token != expected_gate:
            print(f"[SECURITY ALERT] Unauthorized access token detected: '{gate_token}'")
            sys.exit(2)
            
        print(f"[SUCCESS] Global security gate verified: '{gate_token}'")
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to parse infrastructure manifest: {str(e)}")
        sys.exit(1)

    print("=== [SECURITY-INVARIANTS] All validation checks passed successfully ===")
    sys.exit(0)

if __name__ == "__main__":
    validate_system_invariants()
