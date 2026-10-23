"""Immutable RON recording manifests for externally stored audiovisual media.

The recording engine must supply authenticated bytes and OCI object metadata.
This module validates manifest structure and digest evidence; it does not
capture media, prove continuity or attest OCI upload completion.
"""
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone

IDENT=re.compile(r'[A-Za-z0-9_.-]{1,128}\Z',re.ASCII)
HEX=re.compile(r'[a-f0-9]{64}\Z',re.ASCII)

class RecordingDenied(ValueError): pass

class NativeRecordingManifests:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS native_recording_manifests (
                session_id TEXT PRIMARY KEY, object_namespace TEXT NOT NULL,
                bucket TEXT NOT NULL, object_name TEXT NOT NULL,
                sha256 TEXT NOT NULL, bytes_count INTEGER NOT NULL,
                started_at INTEGER NOT NULL, ended_at INTEGER NOT NULL,
                retain_until INTEGER NOT NULL, created_at INTEGER NOT NULL)""")

    def register(self,session_id,namespace,bucket,object_name,sha256,bytes_count,started_at,ended_at):
        if not all(isinstance(x,str) and IDENT.fullmatch(x) for x in (session_id,namespace,bucket)):
            raise RecordingDenied('Invalid recording identifiers')
        if not isinstance(object_name,str) or not object_name or len(object_name)>512 or object_name.startswith('/'):
            raise RecordingDenied('Invalid OCI object name')
        if not isinstance(sha256,str) or not HEX.fullmatch(sha256):
            raise RecordingDenied('Invalid recording digest')
        if any(type(x) is not int for x in (bytes_count,started_at,ended_at)) or not (bytes_count>0 and 0<started_at<ended_at<=int(time.time())+60):
            raise RecordingDenied('Invalid recording timing or size')
        start=datetime.fromtimestamp(ended_at,timezone.utc)
        try:
            until=start.replace(year=start.year+10)
        except ValueError:
            until=start.replace(year=start.year+10,day=28)
        retain_until=int(until.timestamp())
        expected=(namespace,bucket,object_name,sha256,bytes_count,started_at,ended_at,retain_until)
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            session=db.execute('SELECT method,state FROM native_notarial_sessions WHERE session_id=?',(session_id,)).fetchone()
            room=db.execute('SELECT state,recording_digest FROM native_ron_rooms WHERE session_id=?',(session_id,)).fetchone()
            if session!=('RON','AWAITING_AUTHORITY') or room!=('RECORDING_INDEXED',sha256):
                raise RecordingDenied('RON session and recording evidence mismatch')
            existing=db.execute('SELECT object_namespace,bucket,object_name,sha256,bytes_count,started_at,ended_at,retain_until FROM native_recording_manifests WHERE session_id=?',(session_id,)).fetchone()
            if existing and existing!=expected:
                raise RecordingDenied('Conflicting immutable recording manifest')
            if not existing:
                db.execute('INSERT INTO native_recording_manifests VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (session_id,*expected,int(time.time())))
        return {'session_id':session_id,'sha256':sha256,'retain_until':retain_until,
                'object_name':object_name,'storage_upload_verified':False,'continuity_verified':False}
