"""Durable appointment requests; a requested time is never a confirmed booking.

Case and appointment writes share a transaction. Human review, payment and
notarial execution remain separate. No documents or identity evidence collected.
"""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from .cases import CaseDenied


class AppointmentDenied(Exception):
    pass


IDENT = re.compile(r'[A-Za-z0-9_.-]{1,128}')


class AppointmentStore:
    def __init__(self, cases, audit, *, clock=time.time):
        self.cases, self.path, self.clock = cases, cases.db_path, clock
        self.audit = audit
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS appointments (
                case_id TEXT PRIMARY KEY REFERENCES cases(case_id),
                requester TEXT NOT NULL, request_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, requested_start TEXT NOT NULL,
                meeting_area TEXT NOT NULL, consent_at INTEGER NOT NULL,
                UNIQUE(requester, request_id))''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def request(self, requester, request_id, jurisdiction, service,
                requested_start, meeting_area, consent):
        if (not all(isinstance(v, str) and IDENT.fullmatch(v)
                    for v in (requester, request_id))
                or jurisdiction not in ('CO', 'WI')
                or service not in ('MOBILE_NOTARY', 'AUTHORIZED_DOCUMENT_SERVICE')
                or consent is not True
                or not isinstance(meeting_area, str)
                or not 2 <= len(meeting_area.strip()) <= 160
                or any(ord(c) < 32 for c in meeting_area)
                or not isinstance(requested_start, str)):
            raise AppointmentDenied('Invalid appointment request')
        try:
            start = datetime.fromisoformat(requested_start.replace('Z', '+00:00'))
            if start.tzinfo is None:
                raise ValueError('Timezone required')
            timestamp = start.timestamp()
        except (ValueError, OverflowError) as exc:
            raise AppointmentDenied('Invalid requested time') from exc
        normalized = start.astimezone(timezone.utc).isoformat()
        fields = (jurisdiction, service, normalized, meeting_area.strip(), True)
        fingerprint = hashlib.sha256(json.dumps(fields).encode()).hexdigest()
        self.audit.preserve({'stage': 'APPOINTMENT_REQUEST_INTENT', 'request_id': request_id})
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT case_id,fingerprint FROM appointments '
                'WHERE requester=? AND request_id=?', (requester, request_id)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise AppointmentDenied('Request ID reused with different details')
                case_id = previous['case_id']
            else:
                if not self.clock() < timestamp <= self.clock() + 365 * 86400:
                    raise AppointmentDenied('Requested time must be in the next year')
                case_id = 'appointment-' + uuid.uuid4().hex
                self.cases.create(case_id, jurisdiction, service, requester, connection=db)
                db.execute('INSERT INTO appointments VALUES (?,?,?,?,?,?,?)',
                    (case_id, requester, request_id, fingerprint, normalized,
                     meeting_area.strip(), int(self.clock())))
        self.audit.preserve({'stage': 'APPOINTMENT_REQUEST_RECORDED', 'case_id': case_id})
        return self.get(case_id, requester)

    def get(self, case_id, requester):
        with self.connect() as db:
            row = db.execute('''SELECT a.case_id,c.jurisdiction,c.service,c.status,
                a.requested_start,a.meeting_area FROM appointments a
                JOIN cases c ON c.case_id=a.case_id
                WHERE a.case_id=? AND a.requester=?''', (case_id, requester)).fetchone()
        if row is None:
            raise AppointmentDenied('Unknown appointment')
        return dict(row)

    def list_owned(self, requester):
        with self.connect() as db:
            rows = db.execute('SELECT case_id FROM appointments WHERE requester=? '
                              'ORDER BY consent_at DESC, rowid DESC LIMIT 50',
                              (requester,)).fetchall()
        return [self.get(row['case_id'], requester) for row in rows]

    def list_for_operator(self):
        """Trusted internal operation; HTTP caller must verify operator authority first."""
        with self.connect() as db:
            rows = db.execute('SELECT case_id,requester FROM appointments '
                              'ORDER BY consent_at DESC,rowid DESC LIMIT 100').fetchall()
        return [self.get(row['case_id'], row['requester']) for row in rows]
