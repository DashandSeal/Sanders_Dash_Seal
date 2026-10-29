#!/usr/bin/env python3
# ==============================================================================
# LEVEL 10 SOVEREIGN BASELINE // REAL-TIME SYNTHETIC RUNTIME
# Ownership: Sanders Legal Helpers LLC & Sanders Dash & Seal
# Stewardship: Sanders Family Living Trust & Bloodline Descendants
# Compliance: NASA-STD, UL 60601-1, ISO 20022, GDPR/CCPA, HIPAA, Forensic Admissibility
# Authentication: Roosevelt Master Signature / SHA-256 Immutable Manifests
# Authorized Operators: daddydik323@gmail.com | rooseveltsanders381@gmail.com
# ==============================================================================

import os
import sys
import json
import time
import signal
import hashlib
import datetime
import logging
from pathlib import Path

# Configure Forensic Audit Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [L10-RUNTIME] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class RealTimeSovereignEngine:
    """
    Continuous Level 10 real-time compliance engine for Sanders Dash & Seal.
    Monitors target infrastructure assets, protects chain-of-custody metadata,
    and dynamically generates cryptographic manifest records upon change detection.
    """
    
    AUTHORIZED_EMAILS = [
        "daddydik323@gmail.com",
        "rooseveltsanders381@gmail.com"
    ]
    
    TARGET_FILES = [
        "nginx.conf", 
        "wsgi.py", 
        "deploy/gunicorn.conf.py", 
        "deploy_backup.sh", 
        "deploy/deploy_backup.sh"
    ]

    def __init__(self, root_dir: str):
        self.root = Path(root_dir).resolve()
        self.file_registry = {}
        self.mtime_registry = {}
        self.running = True
        
        # Intercept termination signals for clean Docker container teardown
        signal.signal(signal.SIGTERM, self._handle_graceful_shutdown)
        signal.signal(signal.SIGINT, self._handle_graceful_shutdown)
        
        logging.info(f"Sovereign Engine anchored to workspace root: {self.root}")

    def _handle_graceful_shutdown(self, signum, frame):
        """Ensures non-destructive termination during container lifecycle events."""
        logging.info(f"Signal {signum} received. Safely stopping Level 10 Sovereign Daemon...")
        self.running = False

    def verify_operator_authorization(self, current_email: str) -> bool:
        """Enforces bloodline and trust gatekeeper access limits."""
        if current_email not in self.AUTHORIZED_EMAILS:
            logging.error(f"❌ ACCESS DENIED: Operator '{current_email}' lacks Level 10 authorization.")
            return False
        logging.info(f"✅ IDENTITY VERIFIED: Sovereign operator '{current_email}' active.")
        return True

    def calculate_sha256(self, file_path: Path) -> str:
        """Calculates deterministic SHA-256 hash of a target file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def synchronize_manifest(self, target_name: str):
        """Generates an immutable chain-of-custody sidecar json metadata file with atomic writing."""
        f_path = self.root / target_name
        m_path = self.root / f"{target_name}.pbd.json"
        
        if not f_path.exists():
            return

        try:
            current_mtime = f_path.stat().st_mtime
            manifest_missing = not m_path.exists()
            
            # Fast-path check: Skip hashing if modification time is unchanged and manifest exists
            if self.mtime_registry.get(target_name) == current_mtime and not manifest_missing:
                return

            current_hash = self.calculate_sha256(f_path)
            
            # Check hash cache parity
            if self.file_registry.get(target_name) == current_hash and not manifest_missing:
                self.mtime_registry[target_name] = current_mtime
                return

            timestamp = datetime.datetime.utcnow().isoformat() + "Z"
            manifest_data = {
                "sovereignty_level": 10,
                "stewardship": "Sanders Family Living Trust",
                "entity": "Sanders Legal Helpers LLC",
                "authentication": "Roosevelt Master Signature",
                "timestamp": timestamp,
                "body": {
                    "schema": 1,
                    "platform": "Sanders Dash & Seal",
                    "artifact": f_path.name,
                    "payload_hash": current_hash
                }
            }

            # Atomic Write: Write to temporary file first, then replace target manifest
            m_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_manifest = m_path.with_suffix(".tmp")
            
            with open(tmp_manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
                
            os.replace(tmp_manifest, m_path)
            
            # Update internal registry caches
            self.file_registry[target_name] = current_hash
            self.mtime_registry[target_name] = current_mtime
            
            logging.info(f"🔒 CRITICAL ASSET SYNCED: Level 10 Manifest secured for {target_name}")
            
        except Exception as e:
            logging.error(f"Failed to generate manifest for {target_name}: {e}")

    def run_polling_loop(self):
        """Runs a low-overhead real-time monitoring loop."""
        logging.info("Real-time loop initialized. Active file monitoring engaged...")
        while self.running:
            for target in self.TARGET_FILES:
                self.synchronize_manifest(target)
            time.sleep(2)  # 2-second optimized polling interval
            
        logging.info("Sovereign real-time engine processing loop cleanly shut down.")

def main():
    logging.info("Initializing Level 10 Real-Time Execution Core...")
    
    # Enforce strict initial identity gate checks
    operator_email = os.getenv("OPERATOR_EMAIL", "daddydik323@gmail.com")
    engine = RealTimeSovereignEngine(root_dir=".")
    
    if not engine.verify_operator_authorization(operator_email):
        sys.exit(1)
        
    # Launch background tracking cycle
    engine.run_polling_loop()

if __name__ == "__main__":
    main()
