"""
Native RON room lifecycle and recording-evidence binding.

This coordinates room state and consent, actual audiovisual transport,
recording storage, identity proofing and legal completion are separate services.
"""

import re
import sqlite3
import time

ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$', re.ASCII)

class RoomDenied(ValueError):
    pass

class NativeRonRoom:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_ron_rooms (
                session_id TEXT PRIMARY KEY, room_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL, consent_digest TEXT,
                recording_digest TEXT, created_at INTEGER NOT NULL
            );""")

    def create(self, session_id, room_id):
        if not all(isinstance(x, str) and ID.fullmatch(x) for x in (session_id, room_id)):
            raise RoomDenied("Invalid room identity")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE;")
            session = db.execute("SELECT method, state FROM native_notarial_sessions WHERE session_id = ?;", (session_id,)).fetchone()
            if not session or session[0] != 'RON' or session[1] != 'AWAITING_AUTHORITY':
                raise RoomDenied("RON session unavailable")
            try:
                db.execute("INSERT INTO native_ron_rooms (session_id, room_id, state, consent_digest, recording_digest, created_at) VALUES (?, ?, 'AWAITING_CONSENT', NULL, NULL, ?);",
                           (session_id, room_id, int(time.time())))
                db.commit()
            except sqlite3.IntegrityError as exc:
                raise RoomDenied("Duplicate room") from exc
        return session_id

    def get(self, session_id):
        if not isinstance(session_id, str) or not ID.fullmatch(session_id):
            raise RoomDenied("Invalid session token")
        with sqlite3.connect(self.path, timeout=10) as db:
            row = db.execute("SELECT session_id, room_id, state, consent_digest, recording_digest FROM native_ron_rooms WHERE session_id = ?;", (session_id,)).fetchone()
            if not row:
                raise RoomDenied("Unknown room")
            return dict(zip(('session_id', 'room_id', 'state', 'consent_digest', 'recording_digest'), row))

    def consent(self, session_id, digest):
        if not isinstance(digest, str) or not re.fullmatch(r'^[a-f0-9]{64}$', digest):
            raise RoomDenied("Invalid consent digest")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE;")
            result = db.execute("UPDATE native_ron_rooms SET state = 'CONSENT_RECORDED', consent_digest = ? WHERE session_id = ?;", (digest, session_id))
            if result.rowcount != 1:
                raise RoomDenied("Room not awaiting consent")
            db.commit()
        return self.get(session_id)

    def recording(self, session_id, digest):
        if not isinstance(digest, str) or not re.fullmatch(r'^[a-f0-9]{64}$', digest):
            raise RoomDenied("Invalid recording digest")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE;")
            result = db.execute("UPDATE native_ron_rooms SET state = 'RECORDING_INDEXED', recording_digest = ? WHERE session_id = ?;", (digest, session_id))
            if result.rowcount != 1:
                raise RoomDenied("Consent required before recording evidence")
            db.commit()
        return self.get(session_id)
