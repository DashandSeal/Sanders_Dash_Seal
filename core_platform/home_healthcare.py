"""
Module: core_platform.home_healthcare
Architectural Layer: Sanders Home Healthcare & Caregivers RTSA —
public-facing healthcare platform core (Three Originals
Reconstruction Program, owner directive 2026-11-24 07:58 MST).

RECOVERED vs REBUILT inventory (the discipline is absolute):

* RECOVERED = records only. The registry / grid / schema records of
  this platform, and the verified fact that the company itself —
  Sanders Home Healthcare & Caregivers LLC — is operating. Company
  operations are not a platform build and are not claimed here.
* REBUILT = this entire module (2026-11-24): the public-facing
  healthcare platform core, rebuilt in the flagship's established
  patterns (rooms.py disciplines: a Glass-Box audit adapter is
  required at construction, every mutation runs under
  ``BEGIN IMMEDIATE`` with state re-validated inside the lock, and
  every receipt is written inside the critical section — a receipt
  failure rolls the mutation back: no record, no action).

This is a PLATFORM, distinct from the LLC of the same name (owner
ruling D-N12: the platform is the company, public-facing and
global). It is a sibling of Uncle Nickey / Mao, not merged with it:
the six service lines below are the services THIS platform offers;
Uncle Nickey / Mao bridges the same industry set under its own
identity.

HIPAA-BY-DESIGN, by construction: this platform stores REFERENCES
AND WORKFLOW STATE ONLY. ``client_ref`` and ``caregiver_ref`` are
opaque identifiers. There are NO fields for names, diagnoses, or
free-text health information anywhere in the schema. Minimum-
necessary is enforced by the foundation AccessGuard role scopes
plus a per-record ownership check, and EVERY read of an intake or
assignment record goes through the guard and is receipted before
the record is served (no record, no access).

NOT built here: the flagship's notary flows (they stay with Sanders
Dash & Seal — this module must not duplicate them), any real PHI
handling (none — references only), and billing.

Fail-closed throughout, on the platform's established disciplines:

* operator-only operations go through ``operator_verifier``; an
  absent verifier means denied;
* the geofence is a policy gate over declared jurisdiction values
  (foundation GeofencePolicy): ALLOW admits any actor, STEP_UP is
  operator-only, DENY admits nobody;
* assignment overlap for a caregiver fails closed, checked inside
  the transaction against the live rows.
"""

import secrets
import sqlite3
import time
from pathlib import Path

from .rtsa_foundation import (
    AccessGuard,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    latest_check_in as _foundation_latest_check_in,
    record_check_in as _foundation_record_check_in,
    validate_identity,
)

IDENTITY = validate_identity(PlatformIdentity(
    platform_id='sanders_home_healthcare',
    name='Sanders Home Healthcare & Caregivers',
    legal_entities=(
        'Sanders Home Healthcare & Caregivers LLC',
        'Sanders Senior Living LLC',
    ),
    naics_codes=('621610', '624120', '485991', '532283', '423450', '492110'),
    authorized_regions=('US-CO', 'US-WI'),
    status='RECONSTRUCTED',
))

# The six industries as OFFERED SERVICES of this platform (the same
# NAICS set Uncle Nickey / Mao bridges — the platforms are siblings,
# not merged; this module stands alone).
SERVICE_LINES = {
    '621610': 'Home Health Care Services',
    '624120': 'Personal Care Services',
    '485991': 'Non-Emergency Medical Transportation',
    '532283': 'Durable Medical Equipment Rental',
    '423450': 'Medical Supplies Distribution',
    '492110': 'Healthcare Courier Services',
}
# Healthcare courier operations that are strictly local fall under
# NAICS 492210 (Local Messengers and Local Delivery); an intake may
# declare 492210 for the courier service line and it is stored as
# declared.
COURIER_LOCAL_NAICS = '492210'
ACCEPTED_SERVICE_LINES = frozenset(SERVICE_LINES) | {COURIER_LOCAL_NAICS}

INTAKE_STATUSES = frozenset((
    'RECEIVED', 'REVIEWED', 'ACCEPTED', 'DECLINED', 'ACTIVE', 'CLOSED',
))
_INTAKE_TRANSITIONS = {
    'RECEIVED': frozenset(('REVIEWED', 'DECLINED')),
    'REVIEWED': frozenset(('ACCEPTED', 'DECLINED')),
    'ACCEPTED': frozenset(('ACTIVE',)),
    'ACTIVE': frozenset(('CLOSED',)),
    'DECLINED': frozenset(),
    'CLOSED': frozenset(),
}

ASSIGNMENT_STATUSES = frozenset((
    'SCHEDULED', 'CONFIRMED', 'COMPLETED', 'CANCELLED',
))
_ASSIGNMENT_TRANSITIONS = {
    'SCHEDULED': frozenset(('CONFIRMED', 'CANCELLED')),
    'CONFIRMED': frozenset(('COMPLETED', 'CANCELLED')),
    'COMPLETED': frozenset(),
    'CANCELLED': frozenset(),
}
# Assignment states that block an overlapping booking for the same
# caregiver.
_BLOCKING_ASSIGNMENT_STATUSES = ('SCHEDULED', 'CONFIRMED')
# Intake states on which assignments and consultation rooms may be
# bound.
_BINDABLE_INTAKE_STATUSES = ('ACCEPTED', 'ACTIVE')

_ROLE_SCOPES = {
    'OPERATOR': {'INTAKE', 'ASSIGNMENT'},
    'CAREGIVER': {'ASSIGNMENT'},
    'CLIENT': {'INTAKE'},
    'AUDITOR': {'INTAKE', 'ASSIGNMENT'},
}


class HomeHealthcareDenied(ValueError):
    """The requested home healthcare operation is invalid or cannot
    be evidenced, so it does not occur."""


class HomeHealthcareForbidden(ValueError):
    """The actor lacks authority for this home healthcare operation
    or record."""


class HomeHealthcarePlatform:
    """Sanders Home Healthcare & Caregivers RTSA core: client
    intakes, caregiver assignments, consultation-room binding and
    platform check-ins — references and workflow state only."""

    def __init__(self, database, operator_verifier=None, audit=None,
                 rooms=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise HomeHealthcareDenied(
                'A Glass-Box audit adapter is required: no record, no action')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.rooms = rooms
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, IDENTITY.platform_id, _ROLE_SCOPES)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS client_intakes (
                intake_id TEXT PRIMARY KEY,
                client_ref TEXT NOT NULL,
                service_line TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS caregiver_assignments (
                assignment_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                caregiver_ref TEXT NOT NULL,
                starts_at INTEGER NOT NULL,
                ends_at INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS consultation_links (
                intake_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")
            ensure_checkin_schema(db)

    # -- plumbing ----------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA busy_timeout=10000;")
        db.row_factory = sqlite3.Row
        return db

    def _is_operator(self, actor):
        if self.operator_verifier is None:
            return False
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        if not self._is_operator(actor):
            raise HomeHealthcareForbidden('Operator authority required')

    @staticmethod
    def _check_actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise HomeHealthcareDenied('A non-empty actor is required')

    @staticmethod
    def _check_ref(label, value):
        if not isinstance(value, str) or not value.strip():
            raise HomeHealthcareDenied(f'A non-empty {label} is required')
        return value

    def _record(self, stage, **fields):
        self.audit.preserve({'stage': stage, **fields})

    # -- presentation --------------------------------------------------

    @staticmethod
    def _intake_view(row):
        return {
            'intake_id': row['intake_id'],
            'client_ref': row['client_ref'],
            'service_line': row['service_line'],
            'jurisdiction': row['jurisdiction'],
            'status': row['status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    @staticmethod
    def _assignment_view(row):
        return {
            'assignment_id': row['assignment_id'],
            'intake_id': row['intake_id'],
            'caregiver_ref': row['caregiver_ref'],
            'starts_at': row['starts_at'],
            'ends_at': row['ends_at'],
            'status': row['status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    def _intake_row(self, db, intake_id):
        return db.execute(
            "SELECT * FROM client_intakes WHERE intake_id = ?;",
            (intake_id,)).fetchone()

    def _assignment_row(self, db, assignment_id):
        return db.execute(
            "SELECT * FROM caregiver_assignments WHERE assignment_id = ?;",
            (assignment_id,)).fetchone()

    # -- intakes ---------------------------------------------------------

    def create_intake(self, actor, client_ref, service_line, jurisdiction):
        """Open a client intake in RECEIVED. The service line must be
        one of the six offered NAICS codes (courier also accepts the
        strictly-local 492210). Geofence: ALLOW admits any actor,
        STEP_UP is operator-only, DENY admits nobody."""
        self._check_actor(actor)
        self._check_ref('client_ref', client_ref)
        if service_line not in ACCEPTED_SERVICE_LINES:
            raise HomeHealthcareDenied(
                f'Unsupported service line: {service_line!r}')
        decision = self.geofence.evaluate(jurisdiction)
        if decision == 'DENY':
            raise HomeHealthcareDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        if decision == 'STEP_UP' and not self._is_operator(actor):
            raise HomeHealthcareDenied(
                'Jurisdiction requires operator step-up: '
                f'{jurisdiction!r}')
        intake_id = 'intake-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO client_intakes (intake_id, client_ref, "
                    "service_line, jurisdiction, status, created_by, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, "
                    "'RECEIVED', ?, ?, ?);",
                    (intake_id, client_ref, service_line, jurisdiction,
                     actor, now, now))
                self._record('HOME_HEALTHCARE_INTAKE_CREATED',
                             intake_id=intake_id, actor=actor,
                             client_ref=client_ref,
                             service_line=service_line,
                             jurisdiction=jurisdiction)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._intake_view(self._intake_row(db, intake_id))

    def transition_intake(self, actor, intake_id, target):
        """One checked intake lifecycle transition. ALL intake
        transitions are operator-only; an invalid transition refuses
        and changes nothing."""
        self._check_actor(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                row = self._intake_row(db, intake_id)
                if row is None:
                    raise HomeHealthcareDenied('Unknown intake')
                state = row['status']
                if target not in _INTAKE_TRANSITIONS.get(state, frozenset()):
                    raise HomeHealthcareDenied(
                        f'Intake transition {state} -> {target} '
                        'is not permitted')
                db.execute(
                    "UPDATE client_intakes SET status = ?, updated_at = ? "
                    "WHERE intake_id = ?;", (target, now, intake_id))
                self._record('HOME_HEALTHCARE_INTAKE_TRANSITION',
                             intake_id=intake_id, actor=actor,
                             from_state=state, to_state=target)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._intake_view(self._intake_row(db, intake_id))

    def intake_view(self, actor, role, intake_id):
        """Serve one intake record through the AccessGuard: the
        access receipt is written BEFORE the record is read (no
        record, no access). A CLIENT may view only their own intake
        (client_ref == actor)."""
        # Guard first: a refused role/category raises before any
        # record is touched and writes no receipt; a granted access
        # is receipted even when the ownership check below then
        # refuses — attempted accesses are evidence.
        self.guard.access(actor, role, 'INTAKE', intake_id,
                          purpose='intake_view')
        with self._connect() as db:
            row = self._intake_row(db, intake_id)
            if row is None:
                raise HomeHealthcareDenied('Unknown intake')
            if role == 'CLIENT' and row['client_ref'] != actor:
                raise HomeHealthcareForbidden(
                    'A client may view only their own intake')
            return self._intake_view(row)

    # -- assignments -----------------------------------------------------

    def create_assignment(self, actor, intake_id, caregiver_ref,
                          starts_at, ends_at):
        """Schedule a caregiver assignment (operator-only). The
        intake must exist and be ACCEPTED or ACTIVE, the window must
        be well-formed, and no other SCHEDULED/CONFIRMED assignment
        for the same caregiver may overlap [starts_at, ends_at) —
        checked inside the transaction, fail closed."""
        self._check_actor(actor)
        self._check_ref('caregiver_ref', caregiver_ref)
        for label, value in (('starts_at', starts_at), ('ends_at', ends_at)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise HomeHealthcareDenied(f'Invalid {label}')
        if ends_at <= starts_at:
            raise HomeHealthcareDenied('ends_at must follow starts_at')
        assignment_id = 'asgn-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                intake = self._intake_row(db, intake_id)
                if intake is None:
                    raise HomeHealthcareDenied('Unknown intake')
                if intake['status'] not in _BINDABLE_INTAKE_STATUSES:
                    raise HomeHealthcareDenied(
                        'Assignments require an ACCEPTED or ACTIVE intake; '
                        f"this intake is {intake['status']}")
                overlap = db.execute(
                    "SELECT 1 FROM caregiver_assignments "
                    "WHERE caregiver_ref = ? AND status IN (?, ?) "
                    "AND starts_at < ? AND ? < ends_at LIMIT 1;",
                    (caregiver_ref, *_BLOCKING_ASSIGNMENT_STATUSES,
                     ends_at, starts_at)).fetchone()
                if overlap is not None:
                    raise HomeHealthcareDenied(
                        'Caregiver already has an overlapping assignment')
                db.execute(
                    "INSERT INTO caregiver_assignments (assignment_id, "
                    "intake_id, caregiver_ref, starts_at, ends_at, status, "
                    "created_by, created_at, updated_at) VALUES (?, ?, ?, "
                    "?, ?, 'SCHEDULED', ?, ?, ?);",
                    (assignment_id, intake_id, caregiver_ref, starts_at,
                     ends_at, actor, now, now))
                self._record('HOME_HEALTHCARE_ASSIGNMENT_CREATED',
                             assignment_id=assignment_id, actor=actor,
                             intake_id=intake_id, caregiver_ref=caregiver_ref,
                             starts_at=starts_at, ends_at=ends_at)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._assignment_view(
                self._assignment_row(db, assignment_id))

    def transition_assignment(self, actor, assignment_id, target):
        """One checked assignment lifecycle transition. CONFIRMED and
        CANCELLED are operator-only; COMPLETED may be recorded by an
        operator OR by the assigned caregiver (actor ==
        caregiver_ref). An invalid transition refuses and changes
        nothing."""
        self._check_actor(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._assignment_row(db, assignment_id)
                if row is None:
                    raise HomeHealthcareDenied('Unknown assignment')
                state = row['status']
                if target not in _ASSIGNMENT_TRANSITIONS.get(
                        state, frozenset()):
                    raise HomeHealthcareDenied(
                        f'Assignment transition {state} -> {target} '
                        'is not permitted')
                if target == 'COMPLETED' and actor == row['caregiver_ref']:
                    pass  # the assigned caregiver closes their own visit
                else:
                    self._require_operator(actor)
                db.execute(
                    "UPDATE caregiver_assignments SET status = ?, "
                    "updated_at = ? WHERE assignment_id = ?;",
                    (target, now, assignment_id))
                self._record('HOME_HEALTHCARE_ASSIGNMENT_TRANSITION',
                             assignment_id=assignment_id, actor=actor,
                             from_state=state, to_state=target)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._assignment_view(
                self._assignment_row(db, assignment_id))

    def assignment_view(self, actor, role, assignment_id):
        """Serve one assignment record through the AccessGuard (the
        access receipt precedes the record). A CAREGIVER may view
        only their own assignments (caregiver_ref == actor)."""
        # Guard first, exactly as intake_view: granted accesses are
        # receipted even when the ownership check below then refuses
        # — attempted accesses are evidence.
        self.guard.access(actor, role, 'ASSIGNMENT', assignment_id,
                          purpose='assignment_view')
        with self._connect() as db:
            row = self._assignment_row(db, assignment_id)
            if row is None:
                raise HomeHealthcareDenied('Unknown assignment')
            if role == 'CAREGIVER' and row['caregiver_ref'] != actor:
                raise HomeHealthcareForbidden(
                    'A caregiver may view only their own assignments')
            return self._assignment_view(row)

    # -- consultation binding (bind, don't rebuild) -----------------------

    def create_consultation_room(self, actor, intake_id):
        """Bind a consultation room to an ACCEPTED or ACTIVE intake
        through the bound RoomService — the rooms service is not
        rebuilt here. Intakes are not cases, so the room is created
        with case_id=None and a purpose naming the intake reference.
        Any failure in the rooms service propagates as
        HomeHealthcareDenied with NO link recorded."""
        self._check_actor(actor)
        if self.rooms is None:
            raise HomeHealthcareDenied('rooms service not bound')
        with self._connect() as db:
            intake = self._intake_row(db, intake_id)
            if intake is None:
                raise HomeHealthcareDenied('Unknown intake')
            if intake['status'] not in _BINDABLE_INTAKE_STATUSES:
                raise HomeHealthcareDenied(
                    'Consultation rooms require an ACCEPTED or ACTIVE '
                    f"intake; this intake is {intake['status']}")
            jurisdiction = intake['jurisdiction']
        purpose = f'Home healthcare consultation for intake {intake_id}'
        try:
            room = self.rooms.create_room(
                actor, room_type='CONSULTATION', purpose=purpose,
                case_id=None, jurisdiction=jurisdiction)
        except Exception as exc:
            raise HomeHealthcareDenied(
                f'Rooms service refused the consultation room: {exc}'
            ) from exc
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO consultation_links (intake_id, room_id, "
                    "created_by, created_at) VALUES (?, ?, ?, ?);",
                    (intake_id, room['room_id'], actor, now))
                self._record('HOME_HEALTHCARE_CONSULTATION_LINKED',
                             intake_id=intake_id, actor=actor,
                             room_id=room['room_id'])
                db.commit()
            except Exception:
                db.rollback()
                raise
        return room

    # -- check-in and status ----------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record one platform check-in (operator-only) through the
        foundation check-in helper, receipted in the same
        transaction."""
        self._check_actor(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                record = _foundation_record_check_in(
                    db, IDENTITY, deployment_location, operational_status)
                self._record('HOME_HEALTHCARE_CHECK_IN', actor=actor,
                             platform_id=IDENTITY.platform_id,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             recorded_at=now)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    def status(self):
        """Platform status: identity, service lines, intake and
        assignment counts by status, and the latest check-in."""
        with self._connect() as db:
            intake_counts = {status: 0 for status in
                             sorted(INTAKE_STATUSES)}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM client_intakes "
                    "GROUP BY status;").fetchall():
                intake_counts[row['status']] = row['n']
            assignment_counts = {status: 0 for status in
                                 sorted(ASSIGNMENT_STATUSES)}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM "
                    "caregiver_assignments GROUP BY status;").fetchall():
                assignment_counts[row['status']] = row['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'identity_digest': IDENTITY.integrity_digest(),
            'service_lines': dict(SERVICE_LINES),
            'courier_local_naics': COURIER_LOCAL_NAICS,
            'intakes_by_status': intake_counts,
            'assignments_by_status': assignment_counts,
            'latest_check_in': latest,
        }
