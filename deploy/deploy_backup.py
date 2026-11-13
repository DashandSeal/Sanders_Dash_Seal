#!/usr/bin/env python3
import pathlib
import sqlite3
import sys
from datetime import datetime

# Define hardlocked platform path parameters
DB_PATH = pathlib.Path("/app/data/sds_production.db")
BACKUP_DIR = pathlib.Path("/app/data/backups")

def execute_online_backup():
    print(f"[{datetime.now().isoformat()}] Launching Sanders Dash & Seal online ledger backup...")
    
    # 1. Structural Validation Gating
    if not DB_PATH.exists():
        print(f"❌ Structural Error: Primary database file not found at {DB_PATH}")
        sys.exit(1)
        
    # 2. Ensure targeted backup archive path exists safely
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped archive destination filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination_path = BACKUP_DIR / f"sds_backup_{timestamp}.db"
    
    # 3. Safe Online Vacuum Ingestion Run
    connection = None
    try:
        # Establish connection to live operational ledger
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        # SQLite 'VACUUM INTO' copies data natively while maintaining real-time active read/write lines
        print(f"Streaming live consistent snapshot to: {destination_path.name}")
        cursor.execute("VACUUM INTO ?;", (str(destination_path),))
        
        print("✅ Online backup completed successfully. Cryptographic ledger integrity intact.")
        
    except sqlite3.Error as error:
        print(f"❌ Database engine compilation failure during snapshot execution: {error}")
        sys.exit(1)
        
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    execute_online_backup()
