"""Short-lived, room-scoped WebRTC signaling authorization ledger.

Issuance is a privileged operation: callers must authenticate and authorize
the user/room before invoking issue_webrtc_access_token.
"""
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path

def _db_path():
    return Path(os.environ.get("SQLITE_DB_PATH", "/app/data/sds_production.db"))

def bootstrap_auth_schema():
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS sds_authorized_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            assigned_session_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            revoked_at INTEGER
        )""")

def issue_webrtc_access_token(user_id, session_id, ttl_minutes=60):
    """Issue only after the calling service independently verifies room membership."""
    if not all(isinstance(x, str) and 0 < len(x) <= 128 for x in (user_id, session_id)):
        raise ValueError("Invalid identity or room")
    if not isinstance(ttl_minutes, int) or not 1 <= ttl_minutes <= 60:
        raise ValueError("Invalid token lifetime")
    bootstrap_auth_schema()
    token = secrets.token_hex(32)
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    with sqlite3.connect(_db_path()) as db:
        db.execute("INSERT INTO sds_authorized_sessions VALUES (?,?,?,?,NULL)",
                   (digest, user_id, session_id, int(time.time()) + ttl_minutes * 60))
    return token

def validate_worker_token_request(token_string):
    if not isinstance(token_string, str) or len(token_string) != 64:
        return {"isValid": False, "reason": "Invalid token"}
    try:
        bytes.fromhex(token_string)
    except ValueError:
        return {"isValid": False, "reason": "Invalid token"}
    bootstrap_auth_schema()
    digest = hashlib.sha256(token_string.encode("ascii")).hexdigest()
    with sqlite3.connect(_db_path()) as db:
        row = db.execute(
            "SELECT user_id, assigned_session_id FROM sds_authorized_sessions "
            "WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?",
            (digest, int(time.time()))).fetchone()
    if not row:
        return {"isValid": False, "reason": "Unknown or expired token"}
    return {"isValid": True, "session": {
        "user_id": row[0], "assigned_session_id": row[1],
        "notary_session_ids": [row[1]]}}

def revoke_webrtc_access_token(token_string):
    if not isinstance(token_string, str) or len(token_string) != 64:
        return False
    bootstrap_auth_schema()
    with sqlite3.connect(_db_path()) as db:
        cursor = db.execute("UPDATE sds_authorized_sessions SET revoked_at=? "
                            "WHERE token_hash=? AND revoked_at IS NULL",
                            (int(time.time()), hashlib.sha256(token_string.encode()).hexdigest()))
        return cursor.rowcount == 1
