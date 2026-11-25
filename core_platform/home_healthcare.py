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

THE SIX-INDUSTRY CONNECTIVE LAYER (restored 2026-11-24 — owner
design statement and go-ahead of 2026-11-24): this platform's
ORIGINAL design — the design of the owner's first platform
(Famous.ai, "Sanders Home Healthcare & Caregivers NAICS Code
Integrator", created 2025-11-15) — is six human-facing industry
workflows connected through one person: each of the six service
lines below is one industry's workflow, deliberately chosen; the
entry point is a doctor's appointment; and from ONE person
identifier every industry workflow stands online on the same
page in real time. This module restores that layer: person
identifiers (opaque reference tokens carrying NO personal or
health data), doctor-appointment records created under an
identifier, an activation record set that brings all six
workflows online together at the first appointment, and a
unified person page computed live from the current records, so
it reflects record changes as they happen. The six workflows
are THIS platform's own service lines; no connection to any
external industry system is made or claimed. The Famous.ai
face is preserved as the recovery record outside this module;
nothing of it is imported here, and its displayed code set —
a mutated generation carrying 532490 and 611699 in place of
532283 and 624120 — is NOT used: this module carries the
anchored original six codes exactly.

SEAL DESIGNATION (owner, 2026-11-24): under the dual-seal rule,
this platform's headquarters-seal slot is designated for the
headquarters seal bearing a purple heart — the variant of the
corporate headquarters seal with one purple heart in a gold
setting added at the bottom center, above "THE SANDERS
COMPANIES" banner, all original artwork, wording and colors
otherwise preserved — produced under the owner's instruction
and held in the owner's files at
~/workspace/seals/hq-seal-purple-heart.png, alongside this
platform's company seal per the dual-seal rule. This
purple-heart headquarters seal is EXCLUSIVE to this platform:
it is the only RTSA platform that carries it; every other
platform carries the standard blue-and-gold headquarters seal
under the dual-seal rule. The plain blue-and-gold headquarters
seal is NOT the designated seal for this platform and is not
substituted for it.

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
    'OPERATOR': {'INTAKE', 'ASSIGNMENT', 'APPOINTMENT', 'PERSON_PAGE'},
    'CAREGIVER': {'ASSIGNMENT'},
    'CLIENT': {'INTAKE', 'APPOINTMENT', 'PERSON_PAGE'},
    'AUDITOR': {'INTAKE', 'ASSIGNMENT', 'APPOINTMENT', 'PERSON_PAGE'},
}

# -- The six-industry connective layer --------------------------------
# One person identifier, a doctor-appointment entry point, and all
# six industry workflows online on the same page (owner design
# statement, 2026-11-24). Identifiers and appointments carry
# references and workflow state only — the no-PHI construction of
# this module is absolute: no name, diagnosis, or free-text health
# field exists on any of these tables either.
PERSON_IDENTIFIER_STATUSES = frozenset(('ACTIVE', 'REVOKED'))

APPOINTMENT_STATUSES = frozenset((
    'REQUESTED', 'SCHEDULED', 'COMPLETED', 'CANCELLED',
))
_APPOINTMENT_TRANSITIONS = {
    'REQUESTED': frozenset(('SCHEDULED', 'CANCELLED')),
    'SCHEDULED': frozenset(('COMPLETED', 'CANCELLED')),
    'COMPLETED': frozenset(),
    'CANCELLED': frozenset(),
}

# Per-workflow states on the unified person page: STANDBY before
# the person's industries are activated, ONLINE once an appointment
# has activated them, ENGAGED while a live (not DECLINED/CLOSED)
# intake stands on that workflow's service line.
WORKFLOW_STATES = frozenset(('STANDBY', 'ONLINE', 'ENGAGED'))


class HomeHealthcareDenied(ValueError):
    """The requested home healthcare operation is invalid or cannot
    be evidenced, so it does not occur."""


class HomeHealthcareForbidden(ValueError):
    """The actor lacks authority for this home healthcare operation
    or record."""


class HomeHealthcarePlatform:
    """Sanders Home Healthcare & Caregivers RTSA core: client
    intakes, caregiver assignments, consultation-room binding,
    platform check-ins, and the six-industry connective layer
    (person identifiers, doctor appointments, industry activation
    and the unified person page) — references and workflow state
    only."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS person_identifiers (
                person_ref TEXT PRIMARY KEY,
                jurisdiction TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS person_appointments (
                appointment_id TEXT PRIMARY KEY,
                person_ref TEXT NOT NULL,
                provider_ref TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                starts_at INTEGER NOT NULL,
                ends_at INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS industry_activations (
                person_ref TEXT NOT NULL,
                service_line TEXT NOT NULL,
                appointment_id TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (person_ref, service_line)
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

    @staticmethod
    def _person_view(row):
        return {
            'person_ref': row['person_ref'],
            'jurisdiction': row['jurisdiction'],
            'status': row['status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    @staticmethod
    def _appointment_view(row):
        return {
            'appointment_id': row['appointment_id'],
            'person_ref': row['person_ref'],
            'provider_ref': row['provider_ref'],
            'jurisdiction': row['jurisdiction'],
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

    def _person_row(self, db, person_ref):
        return db.execute(
            "SELECT * FROM person_identifiers WHERE person_ref = ?;",
            (person_ref,)).fetchone()

    def _appointment_row(self, db, appointment_id):
        return db.execute(
            "SELECT * FROM person_appointments WHERE appointment_id = ?;",
            (appointment_id,)).fetchone()

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

    # -- six-industry connective layer ---------------------------------
    # One identifier, a doctor-appointment entry point, and all six
    # industry workflows online on the same page (owner design
    # statement, 2026-11-24). The six workflows are this platform's
    # own six service lines above — no external industry system is
    # connected or claimed.

    def issue_person_identifier(self, actor, jurisdiction):
        """Issue ONE person identifier (operator-only): an opaque
        reference token that carries no personal or health data and
        keys the person's unified page. Geofence: DENY refuses;
        STEP_UP is operator-only (the issuer is an operator by the
        check above). The issuance is receipted in the same
        transaction — no record, no identifier."""
        self._check_actor(actor)
        decision = self.geofence.evaluate(jurisdiction)
        if decision == 'DENY':
            raise HomeHealthcareDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        person_ref = 'person-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                db.execute(
                    "INSERT INTO person_identifiers (person_ref, "
                    "jurisdiction, status, created_by, created_at, "
                    "updated_at) VALUES (?, ?, 'ACTIVE', ?, ?, ?);",
                    (person_ref, jurisdiction, actor, now, now))
                self._record('HOME_HEALTHCARE_PERSON_IDENTIFIER_ISSUED',
                             person_ref=person_ref, actor=actor,
                             jurisdiction=jurisdiction)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._person_view(self._person_row(db, person_ref))

    def revoke_person_identifier(self, actor, person_ref):
        """Revoke a person identifier (operator-only). A revoked
        identifier admits no new appointments and its unified page
        refuses every role; its records remain as evidence. Only an
        ACTIVE identifier can be revoked."""
        self._check_actor(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                row = self._person_row(db, person_ref)
                if row is None:
                    raise HomeHealthcareDenied('Unknown person identifier')
                if row['status'] != 'ACTIVE':
                    raise HomeHealthcareDenied(
                        'Only an ACTIVE identifier can be revoked; '
                        f"this identifier is {row['status']}")
                db.execute(
                    "UPDATE person_identifiers SET status = 'REVOKED', "
                    "updated_at = ? WHERE person_ref = ?;",
                    (now, person_ref))
                self._record('HOME_HEALTHCARE_PERSON_IDENTIFIER_REVOKED',
                             person_ref=person_ref, actor=actor)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._person_view(self._person_row(db, person_ref))

    def create_appointment(self, actor, person_ref, provider_ref,
                           jurisdiction, starts_at, ends_at):
        """The entry point of the original design: a doctor
        appointment created under ONE person identifier. The actor
        is an operator or the person themselves (actor ==
        person_ref). The identifier must exist and be ACTIVE, the
        window must be well-formed, and the geofence applies to the
        appointment's jurisdiction (DENY refuses; STEP_UP is
        operator-only). provider_ref is an opaque reference to the
        doctor/practice — no name or health data is stored.

        ACTIVATION: inside the same transaction, when this is the
        person's first appointment, one activation row per service
        line brings all six industry workflows ONLINE together,
        bound to this appointment, and the activation is receipted
        with the six anchored codes. Returns
        {'appointment': ..., 'activation': ... or None}."""
        self._check_actor(actor)
        self._check_ref('person_ref', person_ref)
        self._check_ref('provider_ref', provider_ref)
        for label, value in (('starts_at', starts_at), ('ends_at', ends_at)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise HomeHealthcareDenied(f'Invalid {label}')
        if ends_at <= starts_at:
            raise HomeHealthcareDenied('ends_at must follow starts_at')
        decision = self.geofence.evaluate(jurisdiction)
        if decision == 'DENY':
            raise HomeHealthcareDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        if decision == 'STEP_UP' and not self._is_operator(actor):
            raise HomeHealthcareDenied(
                'Jurisdiction requires operator step-up: '
                f'{jurisdiction!r}')
        appointment_id = 'appt-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                person = self._person_row(db, person_ref)
                if person is None:
                    raise HomeHealthcareDenied('Unknown person identifier')
                if person['status'] != 'ACTIVE':
                    raise HomeHealthcareDenied(
                        'Appointments require an ACTIVE identifier; '
                        f"this identifier is {person['status']}")
                if actor != person_ref and not self._is_operator(actor):
                    raise HomeHealthcareForbidden(
                        'Appointments are created by an operator or by '
                        'the person under their own identifier')
                db.execute(
                    "INSERT INTO person_appointments (appointment_id, "
                    "person_ref, provider_ref, jurisdiction, starts_at, "
                    "ends_at, status, created_by, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'REQUESTED', ?, ?, ?);",
                    (appointment_id, person_ref, provider_ref,
                     jurisdiction, starts_at, ends_at, actor, now, now))
                self._record('HOME_HEALTHCARE_APPOINTMENT_CREATED',
                             appointment_id=appointment_id, actor=actor,
                             person_ref=person_ref,
                             provider_ref=provider_ref,
                             jurisdiction=jurisdiction,
                             starts_at=starts_at, ends_at=ends_at)
                activation = None
                existing = db.execute(
                    "SELECT COUNT(*) AS n FROM industry_activations "
                    "WHERE person_ref = ?;", (person_ref,)).fetchone()
                if existing['n'] == 0:
                    for code in SERVICE_LINES:
                        db.execute(
                            "INSERT INTO industry_activations (person_ref, "
                            "service_line, appointment_id, state, "
                            "created_at, updated_at) VALUES (?, ?, ?, "
                            "'ONLINE', ?, ?);",
                            (person_ref, code, appointment_id, now, now))
                    self._record(
                        'HOME_HEALTHCARE_INDUSTRIES_ACTIVATED',
                        person_ref=person_ref, actor=actor,
                        appointment_id=appointment_id,
                        service_lines=list(SERVICE_LINES))
                    activation = {
                        'person_ref': person_ref,
                        'appointment_id': appointment_id,
                        'activated_at': now,
                        'service_lines': list(SERVICE_LINES),
                    }
                db.commit()
            except Exception:
                db.rollback()
                raise
            return {
                'appointment': self._appointment_view(
                    self._appointment_row(db, appointment_id)),
                'activation': activation,
            }

    def transition_appointment(self, actor, appointment_id, target):
        """One checked appointment lifecycle transition
        (operator-only, exactly as intake transitions). An invalid
        transition refuses and changes nothing."""
        self._check_actor(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_operator(actor)
                row = self._appointment_row(db, appointment_id)
                if row is None:
                    raise HomeHealthcareDenied('Unknown appointment')
                state = row['status']
                if target not in _APPOINTMENT_TRANSITIONS.get(
                        state, frozenset()):
                    raise HomeHealthcareDenied(
                        f'Appointment transition {state} -> {target} '
                        'is not permitted')
                db.execute(
                    "UPDATE person_appointments SET status = ?, "
                    "updated_at = ? WHERE appointment_id = ?;",
                    (target, now, appointment_id))
                self._record('HOME_HEALTHCARE_APPOINTMENT_TRANSITION',
                             appointment_id=appointment_id, actor=actor,
                             from_state=state, to_state=target)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._appointment_view(
                self._appointment_row(db, appointment_id))

    def appointment_view(self, actor, role, appointment_id):
        """Serve one appointment record through the AccessGuard
        (the access receipt precedes the record). A CLIENT may view
        only appointments under their own identifier."""
        self.guard.access(actor, role, 'APPOINTMENT', appointment_id,
                          purpose='appointment_view')
        with self._connect() as db:
            row = self._appointment_row(db, appointment_id)
            if row is None:
                raise HomeHealthcareDenied('Unknown appointment')
            if role == 'CLIENT' and row['person_ref'] != actor:
                raise HomeHealthcareForbidden(
                    'A client may view only their own appointments')
            return self._appointment_view(row)

    @staticmethod
    def _workflow_lines(code):
        """The stored service_line values belonging to one workflow:
        the courier workflow (492110) also carries intakes declared
        under the strictly-local 492210."""
        if code == '492110':
            return ('492110', COURIER_LOCAL_NAICS)
        return (code,)

    def person_page(self, actor, role, person_ref):
        """The unified page of the original design: ONE identifier,
        every industry workflow online on the same page. Served
        through the AccessGuard under the PERSON_PAGE category (the
        access receipt precedes any record). A CLIENT may view only
        their own page. A REVOKED identifier's page refuses every
        role — revocation takes the page offline; the records
        remain as evidence.

        The page is computed LIVE from the current records at read
        time: the identifier, its activation (if any), all its
        appointments (newest first), and one workflow entry per
        anchored service line — STANDBY before activation, ONLINE
        once activated, ENGAGED while a live intake stands on that
        line — with the line's intake records by reference. State
        changes in the underlying records are reflected on the
        next read: that is the real-time property this design
        carries, and no more is claimed."""
        self.guard.access(actor, role, 'PERSON_PAGE', person_ref,
                          purpose='person_page')
        with self._connect() as db:
            person = self._person_row(db, person_ref)
            if person is None:
                raise HomeHealthcareDenied('Unknown person identifier')
            if person['status'] == 'REVOKED':
                raise HomeHealthcareForbidden(
                    'Person identifier is revoked; its page is offline')
            if role == 'CLIENT' and person_ref != actor:
                raise HomeHealthcareForbidden(
                    'A client may view only their own page')
            activation_rows = db.execute(
                "SELECT * FROM industry_activations WHERE person_ref = ? "
                "ORDER BY created_at LIMIT 1;", (person_ref,)).fetchone()
            activation = None
            if activation_rows is not None:
                activation = {
                    'appointment_id': activation_rows['appointment_id'],
                    'activated_at': activation_rows['created_at'],
                }
            appointments = [
                self._appointment_view(row) for row in db.execute(
                    "SELECT * FROM person_appointments "
                    "WHERE person_ref = ? ORDER BY created_at DESC, "
                    "appointment_id;", (person_ref,)).fetchall()
            ]
            workflows = []
            for code, label in SERVICE_LINES.items():
                lines = self._workflow_lines(code)
                marks = ','.join('?' * len(lines))
                intakes = [
                    self._intake_view(row) for row in db.execute(
                        f"SELECT * FROM client_intakes "
                        f"WHERE client_ref = ? AND service_line IN "
                        f"({marks}) ORDER BY created_at, intake_id;",
                        (person_ref, *lines)).fetchall()
                ]
                if activation is None:
                    state = 'STANDBY'
                elif any(i['status'] not in ('DECLINED', 'CLOSED')
                         for i in intakes):
                    state = 'ENGAGED'
                else:
                    state = 'ONLINE'
                workflows.append({
                    'naics': code,
                    'service_line': label,
                    'state': state,
                    'intakes': intakes,
                })
        return {
            'person_ref': person_ref,
            'identifier': self._person_view(person),
            'activation': activation,
            'appointments': appointments,
            'workflows': workflows,
        }

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
        """Platform status: identity, service lines, intake,
        assignment, identifier and appointment counts by status,
        the number of persons whose industries stand activated,
        and the latest check-in."""
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
            identifier_counts = {status: 0 for status in
                                 sorted(PERSON_IDENTIFIER_STATUSES)}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM "
                    "person_identifiers GROUP BY status;").fetchall():
                identifier_counts[row['status']] = row['n']
            appointment_counts = {status: 0 for status in
                                  sorted(APPOINTMENT_STATUSES)}
            for row in db.execute(
                    "SELECT status, COUNT(*) AS n FROM "
                    "person_appointments GROUP BY status;").fetchall():
                appointment_counts[row['status']] = row['n']
            activations = db.execute(
                "SELECT COUNT(DISTINCT person_ref) AS n FROM "
                "industry_activations;").fetchone()['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'identity_digest': IDENTITY.integrity_digest(),
            'service_lines': dict(SERVICE_LINES),
            'courier_local_naics': COURIER_LOCAL_NAICS,
            'intakes_by_status': intake_counts,
            'assignments_by_status': assignment_counts,
            'identifiers_by_status': identifier_counts,
            'appointments_by_status': appointment_counts,
            'industry_activations': activations,
            'latest_check_in': latest,
        }
