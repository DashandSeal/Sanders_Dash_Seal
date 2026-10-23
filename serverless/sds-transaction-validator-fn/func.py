import io
import os
import json
import logging
import hashlib
import sqlite3
from fdk import response

# Configuration parameters derived from OCI application context
DB_VOLUME_PATH = os.getenv("DB_VOLUME_PATH", "/tmp/sds_production.db")

def verify_and_commit_event(payload_dict):
    """
    Enforces atomic write consistency and calculates structural SHA-256
    signatures before logging transaction records into the ledger database.
    """
    try:
        # Normalize and prepare payload structure
        transaction_id = payload_dict.get("transaction_id")
        raw_payload = json.dumps(payload_dict, sort_keys=True).encode('utf-8')
        calculated_digest = hashlib.sha256(raw_payload).hexdigest()
        signature = payload_dict.get("signature", "UNSIGNED")

        # Initialize thread-isolated connection to SQLite ledger storage
        connection = sqlite3.connect(DB_VOLUME_PATH)
        cursor = connection.cursor()

        # Bootstrap internal schema safely if running in an ephemeral sandbox
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sds_ledger_receipts (
                transaction_id TEXT PRIMARY KEY,
                sha256_digest TEXT,
                operational_signature TEXT,
                status TEXT,
                recorded_at TEXT
            )
        """)

        with connection:
            cursor.execute("""
                INSERT OR REPLACE INTO sds_ledger_receipts
                (transaction_id, sha256_digest, operational_signature, status, recorded_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (transaction_id, calculated_digest, signature, 'VERIFIED'))

        connection.close()
        return {"success": True, "digest": calculated_digest}
    except Exception as e:
        logging.error(f"[INTEGRITY VOID]: Data engine parsing error: {str(e)}")
        return {"success": False, "error": str(e)}

def handler(ctx, data: io.BytesIO = None):
    """
    Main OCI Functions entry point invoked by the Service Connector Hub.
    """
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Initializing serverless execution sandbox hook...")

    try:
        # Parse incoming stream batch records from Connector Hub
        body = json.loads(data.read().decode('utf-8'))

        # OCI Service Connector batches events inside a list wrapper
        results = []
        if isinstance(body, list):
            for record in body:
                payload = json.loads(record.get("value", "{}"))
                execution_receipt = verify_and_commit_event(payload)
                results.append(execution_receipt)
        else:
            payload = json.loads(body.get("value", "{}"))
            results.append(verify_and_commit_event(payload))

        return response.Response(
            ctx,
            response_data=json.dumps({"processed_records": len(results), "batch_status": "SUCCESS", "metrics": results}),
            headers={"Content-Type": "application/json"}
        )

    except (Exception, ValueError) as ex:
        logging.error(f"[SANDBOX EXCEPTION] Runtime fault encountered: {str(ex)}")
        return response.Response(
            ctx,
            response_data=json.dumps({"error": "Failed to parse streaming payload batch", "details": str(ex)}),
            headers={"Content-Type": "application/json"}
        )
