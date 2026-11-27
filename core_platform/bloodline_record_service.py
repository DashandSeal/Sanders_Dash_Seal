"""Bloodline Record Service — the authenticated descendant
record for the Sanders bloodline.

Built under the founder's order of 2026-11-26 ("get my
bloodline protected immediately"), under the Permanent
Bloodline Protection Directive (adopted 2026-11-25), whose
Supplemental Article III designates the founder's human
successors.

WHAT THIS MODULE IS: a governed, append-only record store
carrying one authenticated descendant record per designated
successor. Each record carries the successor's public name
(already published in docs/PERMANENT_BLOODLINE_PROTECTION_
DIRECTIVE.md), the designation and lineage bases stated in
the Directive, the authentication standard, and a registry
seal — the SHA-256 hash of that person's section of the
confidential Sanders Bloodline Registry. ONLY the hash is
ever stored or passed here: the registry itself, and every
vital-record detail, never enter this module, this store,
or the repository.

AUTHENTICATION HONESTY: records are established at
authentication level FOUNDER_DESIGNATED. Vital-record
tracing is still pending family documents; every vital
record field stands NOT_YET_TRACED until an operator
strengthens it toward a traced state with a record
reference. This module never claims a vital-record
authentication that does not exist.

APPEND-ONLY DISCIPLINE: there is no delete or remove
operation, by design. A record, once established, can only
be strengthened — a vital-records field may move from
NOT_YET_TRACED toward traced states and gain a record
reference, and may never move back. Duplicate establishment
with the identical registry seal is idempotent and returns
the existing record; establishment under a different seal
for the same person is refused.

RECORDS, NEVER OPERATIONS: this module holds records only.
It has no dispatch path, sends nothing, and takes no
protective action itself — it is the authenticated record
that protection stands on.

No record, no action: every state-changing operation
writes its Glass-Box receipt through the shared audit
adapter; the service refuses to exist without one.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
)


DESIGNATION_BASIS = (
    'Designated human successor \u2014 Supplemental Article III, '
    'Permanent Bloodline Protection Directive, adopted 2026-11-25')
LINEAGE_BASIS = (
    "Lineal descendant of the founder, per the founder's designation")
AUTHENTICATION_STANDARD = (
    'Authenticated by vital records traced to the Sanders '
    'Bloodline Registry \u2014 birth record first')
AUTHENTICATION_LEVEL = 'FOUNDER_DESIGNATED'
GENERATION = 1

VITAL_FIELDS = (
    'birth_record',
    'marriage_records',
    'death_record',
    'life_insurance',
    'health_insurance',
)

# Strength ordering for vital-records fields: a field may
# only ever move to a strictly higher rank. NOT_APPLICABLE_
# LIVING is terminal for a living person: it is a statement
# of fact (no death record exists), never a weakening.
STATUS_RANK = {
    'NOT_YET_TRACED': 0,
    'TRACED': 1,
    'VERIFIED': 2,
    'NOT_APPLICABLE_LIVING': 3,
}

INITIAL_VITAL_STATUS = {
    'birth_record': 'NOT_YET_TRACED',
    'marriage_records': 'NOT_YET_TRACED',
    'death_record': 'NOT_APPLICABLE_LIVING',
    'life_insurance': 'NOT_YET_TRACED',
    'health_insurance': 'NOT_YET_TRACED',
}

_SEAL_RE = re.compile(r'^[0-9a-f]{64}$')
_KEY_RE = re.compile(r'^[a-z0-9][a-z0-9\-]*$')

ESTABLISHED_EVENT = 'BLOODLINE_DESCENDANT_RECORD_ESTABLISHED'
STRENGTHENED_EVENT = 'BLOODLINE_DESCENDANT_RECORD_STRENGTHENED'


class BloodlineRecordDenied(Exception):
    """The requested bloodline record operation is not allowed."""


class BloodlineRecordForbidden(Exception):
    """The actor lacks authority for the requested operation."""


def _canonical_payload(fields: dict) -> str:
    return json.dumps(fields, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False)


def _payload_seal(fields: dict) -> str:
    return hashlib.sha256(
        _canonical_payload(fields).encode('utf-8')).hexdigest()


class BloodlineRecordService:
    """Authenticated descendant records for the Sanders bloodline:
    append-only, operator-written, Glass-Box receipted."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise BloodlineRecordDenied(
                'Bloodline records require a working Glass-Box '
                'audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.guard = AccessGuard(audit, 'bloodline_record', {
            'OPERATOR': {'BLOODLINE_RECORD'},
            'AUDITOR': {'BLOODLINE_RECORD'},
        })
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS bloodline_descendant_records (
                    person_key TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    designation_basis TEXT NOT NULL,
                    lineage_basis TEXT NOT NULL,
                    authentication_standard TEXT NOT NULL,
                    authentication_level TEXT NOT NULL,
                    vital_records_status TEXT NOT NULL,
                    record_refs TEXT NOT NULL,
                    registry_seal TEXT NOT NULL,
                    payload_seal TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    established_by TEXT NOT NULL,
                    established_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    # -- plumbing ---------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self._path, timeout=10,
                             isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def _now(self) -> float:
        return float(self._clock())

    def _check_actor(self, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise BloodlineRecordForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise BloodlineRecordForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'BLOODLINE_RECORD',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise BloodlineRecordForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise BloodlineRecordDenied(str(exc)) from exc

    # -- views --------------------------------------------------------

    @staticmethod
    def _payload_fields(row):
        return {
            'person_key': row['person_key'],
            'full_name': row['full_name'],
            'generation': row['generation'],
            'designation_basis': row['designation_basis'],
            'lineage_basis': row['lineage_basis'],
            'authentication_standard': row['authentication_standard'],
            'authentication_level': row['authentication_level'],
            'vital_records_status': json.loads(row['vital_records_status']),
            'record_refs': json.loads(row['record_refs']),
            'registry_seal': row['registry_seal'],
        }

    @classmethod
    def _record_view(cls, row):
        view = cls._payload_fields(row)
        view['payload_seal'] = row['payload_seal']
        view['receipt_id'] = row['receipt_id']
        view['established_by'] = row['established_by']
        view['established_at'] = row['established_at']
        view['updated_by'] = row['updated_by']
        view['updated_at'] = row['updated_at']
        return view

    def _fetch(self, db, person_key):
        return db.execute(
            'SELECT * FROM bloodline_descendant_records '
            'WHERE person_key = ?', (person_key,)).fetchone()

    # -- establishment ------------------------------------------------

    def establish_record(self, actor, person_key, full_name,
                         registry_seal, *, generation=GENERATION):
        """Establish one descendant record (operator only).

        ``registry_seal`` is the SHA-256 hex of the person's
        section of the confidential Sanders Bloodline Registry;
        only the hash is stored. Establishment with the
        identical seal for an existing person is idempotent and
        returns the existing record; a different seal is
        refused — the record is append-only.
        """
        self._require_operator(actor)
        if not isinstance(person_key, str) or not _KEY_RE.match(person_key):
            raise BloodlineRecordDenied(
                'person_key must be a lowercase slug')
        if not isinstance(full_name, str) or not full_name.strip():
            raise BloodlineRecordDenied('A full_name is required')
        if not isinstance(registry_seal, str) or not _SEAL_RE.match(
                registry_seal):
            raise BloodlineRecordDenied(
                'registry_seal must be a SHA-256 hex digest')
        if generation != GENERATION:
            raise BloodlineRecordDenied(
                'Only generation 1 designated successors are '
                'established by this record')
        with self._connect() as db:
            existing = self._fetch(db, person_key)
            if existing is not None:
                if existing['registry_seal'] == registry_seal:
                    view = self._record_view(existing)
                    view['already_current'] = True
                    return view
                raise BloodlineRecordDenied(
                    'A record already stands for this person under '
                    'a different registry seal; records are '
                    'append-only and are never overwritten')
            fields = {
                'person_key': person_key,
                'full_name': full_name.strip(),
                'generation': GENERATION,
                'designation_basis': DESIGNATION_BASIS,
                'lineage_basis': LINEAGE_BASIS,
                'authentication_standard': AUTHENTICATION_STANDARD,
                'authentication_level': AUTHENTICATION_LEVEL,
                'vital_records_status': dict(INITIAL_VITAL_STATUS),
                'record_refs': {},
                'registry_seal': registry_seal,
            }
            now = self._now()
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    ESTABLISHED_EVENT,
                    actor=actor, person_key=person_key,
                    full_name=fields['full_name'],
                    registry_seal=registry_seal,
                    authentication_level=AUTHENTICATION_LEVEL)
                db.execute(
                    'INSERT INTO bloodline_descendant_records '
                    '(person_key, full_name, generation, '
                    'designation_basis, lineage_basis, '
                    'authentication_standard, authentication_level, '
                    'vital_records_status, record_refs, registry_seal, '
                    'payload_seal, receipt_id, established_by, '
                    'established_at, updated_by, updated_at) VALUES '
                    '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (person_key, fields['full_name'], GENERATION,
                     DESIGNATION_BASIS, LINEAGE_BASIS,
                     AUTHENTICATION_STANDARD, AUTHENTICATION_LEVEL,
                     json.dumps(fields['vital_records_status']),
                     json.dumps(fields['record_refs']), registry_seal,
                     _payload_seal(fields), receipt_id, actor, now,
                     actor, now),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._fetch(db, person_key)
        view = self._record_view(row)
        view['already_current'] = False
        return view

    # -- strengthening (the only mutation) ----------------------------

    def strengthen_record(self, actor, person_key, field, new_status,
                          *, record_ref=None):
        """Strengthen one vital-records field (operator only).

        A field may only move to a strictly stronger state
        (NOT_YET_TRACED toward TRACED / VERIFIED) and may
        attach a record reference. Moving any field back, or
        changing a terminal fact, is refused. There is no
        other mutation and no removal.
        """
        self._require_operator(actor)
        if field not in VITAL_FIELDS:
            raise BloodlineRecordDenied(
                f'Unknown vital-records field: {field!r}')
        if new_status not in STATUS_RANK:
            raise BloodlineRecordDenied(
                f'Unknown vital-records status: {new_status!r}')
        if record_ref is not None and (
                not isinstance(record_ref, str) or not record_ref.strip()):
            raise BloodlineRecordDenied(
                'record_ref must be a non-empty reference')
        with self._connect() as db:
            row = self._fetch(db, person_key)
            if row is None:
                raise BloodlineRecordDenied(
                    f'No descendant record stands for {person_key!r}')
            fields = self._payload_fields(row)
            current = fields['vital_records_status'][field]
            if STATUS_RANK[new_status] <= STATUS_RANK[current]:
                raise BloodlineRecordDenied(
                    'Records only strengthen: '
                    f'{field} already stands {current} and cannot '
                    f'move to {new_status}')
            fields['vital_records_status'][field] = new_status
            if record_ref is not None:
                fields['record_refs'][field] = record_ref.strip()
            now = self._now()
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    STRENGTHENED_EVENT,
                    actor=actor, person_key=person_key, field=field,
                    from_status=current, to_status=new_status)
                db.execute(
                    'UPDATE bloodline_descendant_records SET '
                    'vital_records_status = ?, record_refs = ?, '
                    'payload_seal = ?, updated_by = ?, updated_at = ? '
                    'WHERE person_key = ?',
                    (json.dumps(fields['vital_records_status']),
                     json.dumps(fields['record_refs']),
                     _payload_seal(fields), actor, now, person_key),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._fetch(db, person_key)
        view = self._record_view(row)
        view['strengthen_receipt_id'] = receipt_id
        return view

    # -- reads and verification ---------------------------------------

    def descendant_records(self):
        """All established descendant records, in establishment order."""
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM bloodline_descendant_records '
                'ORDER BY established_at, person_key').fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, person_key):
        """One record, served only after a receipted guard access."""
        self._guard_access(actor, role, person_key,
                           'descendant record view')
        with self._connect() as db:
            row = self._fetch(db, person_key)
        if row is None:
            raise BloodlineRecordDenied(
                f'No descendant record stands for {person_key!r}')
        return self._record_view(row)

    def _establishing_receipt_in_chain(self, receipt_id):
        """Confirm the establishing receipt stands in the Glass-Box
        audit chain held by the audit adapter."""
        audit_path = getattr(self._audit, 'path', None)
        if audit_path is None:
            return False
        try:
            verify = getattr(self._audit, 'verify_audit', None)
            if callable(verify):
                verify()
            db = sqlite3.connect(f'file:{audit_path}?mode=ro', uri=True)
            try:
                row = db.execute(
                    'SELECT COUNT(*) FROM receipts WHERE hash = ?',
                    (receipt_id,)).fetchone()
            finally:
                db.close()
        except Exception:
            return False
        return bool(row and row[0] == 1)

    def verify_record(self, person_key):
        """Verify one record: recompute the payload seal over the
        stored canonical payload, and confirm the establishing
        Glass-Box receipt exists in the audit chain."""
        with self._connect() as db:
            row = self._fetch(db, person_key)
        if row is None:
            return {
                'person_key': person_key,
                'authenticated': False,
                'checks': {'record_exists': False},
            }
        fields = self._payload_fields(row)
        seal_ok = _payload_seal(fields) == row['payload_seal']
        registry_seal_ok = bool(
            _SEAL_RE.match(row['registry_seal'] or ''))
        receipt_ok = self._establishing_receipt_in_chain(row['receipt_id'])
        checks = {
            'record_exists': True,
            'payload_seal_recomputes': seal_ok,
            'registry_seal_well_formed': registry_seal_ok,
            'establishing_receipt_in_audit_chain': receipt_ok,
        }
        return {
            'person_key': person_key,
            'full_name': row['full_name'],
            'authentication_level': row['authentication_level'],
            'authenticated': all(checks.values()),
            'checks': checks,
        }
