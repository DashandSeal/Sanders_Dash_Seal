"""
Module: core_platform.rooms
Architectural Layer: Commercial Meeting Rooms Control Plane (MASTER
Section 22, draft expansion — Secure Virtual Meeting Rooms and
Conference Capabilities)
Description: The rooms service for ordinary commercial meetings:
durable room records with an explicit, checked lifecycle
(§22.3), scoped participant roles including a first-class
INTERPRETER role (§22.4), time-limited invitations (§22.5),
per-participant recording consent and a jurisdiction-aware retention
policy on the room record (§22.8), and a Glass-Box receipt for every
lifecycle transition, participant change and consent event (§22.11).

This is the CONTROL PLANE only. A room here is a governed corporate
object: who may be in it, in what role, under what consent, bound to
which commercial matter, retained how long. The media plane (actual
audio/video) stays behind the owner's ``voice_video_provider``
approval gate in the realtime module; this service mints no media
token, opens no media session, and answers nothing about media.

The regulated boundary is absolute: room types and participant roles
deliberately exclude every notarial concept. There is no notarial
room type and no notary role here; a room can never be represented
as, or converted into, a notarial session (§22.9 separation). Rooms
reference customer cases and the existing case/checkout flows; they
never duplicate or bypass them, and they never touch money movement
(§22.14: payment *status* belongs to the ledger, not the room).

Fail-closed throughout, on the platform's established disciplines:

* every mutation runs under ``BEGIN IMMEDIATE`` on the rooms store
  with the room row re-read and the operation re-validated under the
  lock (the concurrency-closure discipline: duplicate transitions
  serialize exactly once — the second caller observes the new state
  and is refused);
* every mutation writes its Glass-Box receipt inside the critical
  section, before the rooms transaction commits: a transition whose
  receipt cannot be written does not occur (no record, no action);
* identities are platform account identities only. A participant is
  bound to an account, or to a host-issued invitation recorded on the
  room that the invited account itself accepts. Nobody acts under a
  self-asserted identity, and nobody records consent for another
  participant.
* recording authorization exists only while the room is live
  (WAITING_ROOM or ACTIVE) and only on unanimous current consent
  recorded against the room's canonical consent notice version;
  leaving the live states, or any change to the consent or
  participant record the authorization rests on, revokes it in the
  same transaction (Phase B corrective fix — D-1, D-2).
"""

import re
import secrets
import sqlite3
import time
from pathlib import Path

from .cases import CaseDenied

IDENT = re.compile(r'^[A-Za-z0-9_-]{1,128}$', re.ASCII)
NOTICE_VERSION = re.compile(r'^[A-Za-z0-9_.-]{1,64}$', re.ASCII)

# Section 22.2 meeting types, commercial track. The notarial type
# (22.2 item 6) is deliberately absent: notarial sessions exist only
# on the regulated track, behind their own gates.
ROOM_TYPES = frozenset((
    'CONSULTATION',           # 22.2 items 1/8, 22.19 one-on-one consultations
    'COMMERCIAL_TRANSACTION',  # 22.2 item 4, 22.14 commercial transaction rooms
    'CONFERENCE',             # 22.2 items 2/9, multi-party and branch conferences
    'INTERNAL_COLLABORATION',  # 22.2 item 7, internal business conferences
))

# Section 22.4 participant roles, commercial subset. NOTARY is
# deliberately absent: an authorized notary's official authority is
# verified independently of platform role (22.4) on the regulated
# track; no commercial room confers or records it.
ROLES = frozenset((
    'HOST', 'PARTICIPANT', 'INTERPRETER', 'WITNESS', 'OBSERVER', 'SUPPORT',
))

# Section 22.8 recording policies: a policy may prohibit recording,
# permit it with consent, or require it. In the commercial track a
# REQUIRED policy still cannot override a participant's refusal:
# consent is never manufactured by policy (build decision, recorded
# in docs/SPEC_CONFORMANCE.md).
RECORDING_POLICIES = frozenset((
    'PROHIBITED', 'PERMITTED_WITH_CONSENT', 'REQUIRED',
))

CONSENT_DECISIONS = frozenset(('GRANTED', 'REFUSED', 'WITHDRAWN'))
CONSENT_SCOPE = 'RECORDING'

# The platform's current recording-consent notice version. Each room
# records a canonical consent notice version at creation (this
# default, or the version supplied at creation); a participant's
# consent counts toward recording authorization only when it was
# recorded against the room's canonical version (Phase B corrective
# fix, discrepancy D-2 — see docs/SPEC_CONFORMANCE.md).
DEFAULT_CONSENT_NOTICE_VERSION = 'v1'

# The one record category this phase produces (22.8: retention is per
# record category and jurisdiction; no universal rule is presumed).
RETENTION_CATEGORY = 'COMMERCIAL_MEETING_RECORD'
# Platform policy default — a build decision recorded in
# docs/SPEC_CONFORMANCE.md, NOT a statutory period. The 10-year
# period in the RON readiness record governs regulated-track
# recordings and is deliberately not imported here: commercial rooms
# carry no notarial function. A host may set a per-room value, and
# the room's jurisdiction is recorded so a future jurisdiction
# schedule can supersede the default.
DEFAULT_RETENTION_DAYS = 365
MAX_RETENTION_DAYS = 3650

DEFAULT_INVITE_TTL_SECONDS = 72 * 3600
MAX_INVITE_TTL_SECONDS = 7 * 24 * 3600

STATES = frozenset((
    'DRAFT', 'SCHEDULED', 'WAITING_ROOM', 'ACTIVE', 'ENDED',
    'ARCHIVED', 'CANCELLED', 'LOCKED', 'SUSPENDED', 'EVIDENCE_HOLD',
))
TERMINAL_STATES = frozenset(('ARCHIVED', 'CANCELLED'))
# States in which the participant set may still change (22.5).
PARTICIPANT_CHANGE_STATES = frozenset((
    'DRAFT', 'SCHEDULED', 'WAITING_ROOM', 'ACTIVE', 'LOCKED', 'SUSPENDED',
))
# States in which consent may be recorded or changed.
CONSENT_STATES = STATES - TERMINAL_STATES
# States in which recording may be authorized: the room is live or
# about to be (22.8: consent precedes any recording state).
RECORDING_AUTHORIZABLE_STATES = frozenset(('WAITING_ROOM', 'ACTIVE'))

# Checked lifecycle transitions (22.3). LOCKED and EVIDENCE_HOLD
# return to the state recorded when they were entered.
_TRANSITIONS = {
    'schedule': {'DRAFT': 'SCHEDULED'},
    'open': {'DRAFT': 'WAITING_ROOM', 'SCHEDULED': 'WAITING_ROOM'},
    'activate': {'WAITING_ROOM': 'ACTIVE'},
    'lock': {'WAITING_ROOM': 'LOCKED', 'ACTIVE': 'LOCKED'},
    'suspend': {'WAITING_ROOM': 'SUSPENDED', 'ACTIVE': 'SUSPENDED'},
    # Resumption lands in WAITING_ROOM, never directly in ACTIVE:
    # resumption requires a fresh authorization pass (22.3).
    'resume': {'SUSPENDED': 'WAITING_ROOM'},
    'end': {'WAITING_ROOM': 'ENDED', 'ACTIVE': 'ENDED',
            'LOCKED': 'ENDED', 'SUSPENDED': 'ENDED'},
    'archive': {'ENDED': 'ARCHIVED'},
    'cancel': {'DRAFT': 'CANCELLED', 'SCHEDULED': 'CANCELLED',
               'WAITING_ROOM': 'CANCELLED'},
}
_OPERATOR_ONLY_ACTIONS = frozenset(('hold', 'release_hold'))


class RoomDenied(ValueError):
    """The requested room operation is invalid or not permitted."""


class RoomNotFound(LookupError):
    """The room does not exist, or is not visible to this actor.

    The two cases are deliberately indistinguishable (participant
    isolation, 22.13): an actor who is not the host, an operator, or
    a participant learns nothing about a room's existence.
    """


class RoomForbidden(PermissionError):
    """The actor can see the room but lacks authority for this action."""


class RoomService:
    """Durable commercial meeting rooms: lifecycle, participants,
    invitations, consent, retention and Glass-Box evidence."""

    def __init__(self, database, cases=None, operator_verifier=None,
                 audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise RoomDenied(
                'A Glass-Box audit adapter is required: no record, no action')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.cases = cases
        self.operator_verifier = operator_verifier
        self.audit = audit
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT NOT NULL,
                purpose TEXT NOT NULL,
                state TEXT NOT NULL,
                host TEXT NOT NULL,
                case_id TEXT,
                jurisdiction TEXT,
                scheduled_start INTEGER,
                scheduled_end INTEGER,
                recording_policy TEXT NOT NULL,
                recording_state TEXT NOT NULL,
                consent_notice_version TEXT,
                retention_category TEXT NOT NULL,
                retention_days INTEGER NOT NULL,
                retention_basis TEXT NOT NULL,
                locked_from TEXT,
                hold_from TEXT,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                state_changed_at INTEGER NOT NULL
            );""")
            columns = {row[1] for row in db.execute(
                "PRAGMA table_info(rooms);").fetchall()}
            if 'consent_notice_version' not in columns:
                # A store created before the D-2 corrective fix has no
                # canonical consent notice version. Its rooms fail
                # closed on recording authorization: no recorded
                # consent can match a NULL canonical version.
                db.execute(
                    "ALTER TABLE rooms ADD COLUMN "
                    "consent_notice_version TEXT;")
            db.execute("""CREATE TABLE IF NOT EXISTS room_participants (
                room_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                via TEXT NOT NULL,
                added_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (room_id, identity)
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS room_invites (
                invite_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                invitee TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                issued_by TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS room_consents (
                consent_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                identity TEXT NOT NULL,
                scope TEXT NOT NULL,
                decision TEXT NOT NULL,
                notice_version TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")

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

    @staticmethod
    def _check_actor(actor):
        if not isinstance(actor, str) or not IDENT.fullmatch(actor):
            raise RoomDenied('Invalid actor identity')

    @staticmethod
    def _check_room_id(room_id):
        if not isinstance(room_id, str) or not IDENT.fullmatch(room_id):
            raise RoomNotFound('Unknown room')

    def _room_row(self, db, room_id):
        row = db.execute(
            "SELECT * FROM rooms WHERE room_id = ?;", (room_id,)).fetchone()
        if row is None:
            raise RoomNotFound('Unknown room')
        return row

    def _participant(self, db, room_id, identity):
        return db.execute(
            "SELECT * FROM room_participants WHERE room_id = ? "
            "AND identity = ?;", (room_id, identity)).fetchone()

    def _visibility(self, db, row, actor):
        """'host' | 'operator' | 'participant' | None for this actor."""
        if row['host'] == actor:
            return 'host'
        if self._is_operator(actor):
            return 'operator'
        participant = self._participant(db, row['room_id'], actor)
        if participant is not None and participant['status'] != 'REMOVED':
            return 'participant'
        return None

    def _visible_row(self, db, room_id, actor):
        row = self._room_row(db, room_id)
        if self._visibility(db, row, actor) is None:
            raise RoomNotFound('Unknown room')
        return row

    def _manage_row(self, db, room_id, actor):
        """Room row when the actor may manage it (host or operator)."""
        row = self._visible_row(db, room_id, actor)
        if row['host'] != actor and not self._is_operator(actor):
            raise RoomForbidden('Host or operator authority required')
        return row

    def _record(self, stage, **fields):
        self.audit.preserve({'stage': stage, **fields})

    def _current_consent_record(self, db, room_id, identity):
        return db.execute(
            "SELECT decision, notice_version FROM room_consents "
            "WHERE room_id = ? AND identity = ? AND scope = ? "
            "ORDER BY recorded_at DESC, rowid DESC LIMIT 1;",
            (room_id, identity, CONSENT_SCOPE)).fetchone()

    def _current_consent(self, db, room_id, identity):
        row = self._current_consent_record(db, room_id, identity)
        return row['decision'] if row is not None else None

    @staticmethod
    def _consent_counts(record, canonical_version):
        """Whether a participant's current consent record counts
        toward recording authorization: it must be a GRANTED decision
        recorded against the room's canonical consent notice version.
        A consent recorded against any other version stays on the
        append-only record but does not satisfy authorization (D-2)."""
        return (record is not None
                and record['decision'] == 'GRANTED'
                and record['notice_version'] == canonical_version)

    def _admitted(self, db, room_id):
        return db.execute(
            "SELECT * FROM room_participants WHERE room_id = ? "
            "AND status = 'ADMITTED' ORDER BY created_at, identity;",
            (room_id,)).fetchall()

    def _revoke_recording_locked(self, db, row, reason):
        """Revert an AUTHORIZED recording state inside the caller's
        transaction; the caller has already validated the change that
        makes the authorization stale (consent changed, participant
        set changed, room left its live states)."""
        if row['recording_state'] != 'AUTHORIZED':
            return
        db.execute(
            "UPDATE rooms SET recording_state = 'NOT_AUTHORIZED', "
            "updated_at = ? WHERE room_id = ?;",
            (int(time.time()), row['room_id']))
        self._record('ROOM_RECORDING_REVOKED', room_id=row['room_id'],
                     reason=reason)

    # -- presentation --------------------------------------------------

    def _retention_view(self, row):
        eligible_at = None
        if row['state'] == 'ARCHIVED':
            eligible_at = (row['state_changed_at']
                           + row['retention_days'] * 86400)
        return {
            'category': row['retention_category'],
            'days': row['retention_days'],
            'basis': row['retention_basis'],
            'deletion_eligible_at': eligible_at,
            'on_hold': row['state'] == 'EVIDENCE_HOLD',
        }

    def _room_view(self, db, row, viewer):
        view = {
            'room_id': row['room_id'],
            'room_type': row['room_type'],
            'purpose': row['purpose'],
            'state': row['state'],
            'host': row['host'],
            'case_id': row['case_id'],
            'jurisdiction': row['jurisdiction'],
            'scheduled_start': row['scheduled_start'],
            'scheduled_end': row['scheduled_end'],
            'recording_policy': row['recording_policy'],
            'recording_state': row['recording_state'],
            'consent_notice_version': row['consent_notice_version'],
            'retention': self._retention_view(row),
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'state_changed_at': row['state_changed_at'],
        }
        if viewer is None:
            return view
        privileged = viewer in ('host', 'operator')
        participants = []
        rows = db.execute(
            "SELECT * FROM room_participants WHERE room_id = ? "
            "ORDER BY created_at, identity;", (row['room_id'],)).fetchall()
        for participant in rows:
            entry = {
                'identity': participant['identity'],
                'role': participant['role'],
                'status': participant['status'],
                'via': participant['via'],
                'added_by': participant['added_by'],
            }
            if privileged or participant['identity'] == viewer:
                entry['consent'] = self._current_consent(
                    db, row['room_id'], participant['identity'])
            participants.append(entry)
        view['participants'] = participants
        invites = []
        invite_rows = db.execute(
            "SELECT * FROM room_invites WHERE room_id = ? "
            "ORDER BY created_at, invite_id;", (row['room_id'],)).fetchall()
        for invite in invite_rows:
            if not privileged and invite['invitee'] != viewer:
                continue
            invites.append({
                'invite_id': invite['invite_id'],
                'invitee': invite['invitee'],
                'role': invite['role'],
                'status': invite['status'],
                'issued_by': invite['issued_by'],
                'expires_at': invite['expires_at'],
            })
        view['invites'] = invites
        return view

    # -- rooms ---------------------------------------------------------

    def create_room(self, actor, *, room_type, purpose, case_id=None,
                    jurisdiction=None, scheduled_start=None,
                    scheduled_end=None, recording_policy=None,
                    retention_days=None, consent_notice_version=None):
        """Create a room in DRAFT; the creator is its host and first
        participant. A case binding is validated against the case
        registry: a customer binds only their own case. The room
        records a canonical consent notice version (the create input,
        or the platform default): only consent recorded against that
        version counts toward recording authorization (D-2)."""
        self._check_actor(actor)
        if room_type not in ROOM_TYPES:
            raise RoomDenied('Unsupported room type')
        if not isinstance(purpose, str) or not 1 <= len(purpose.strip()) <= 200:
            raise RoomDenied('A room purpose of 1-200 characters is required')
        purpose = purpose.strip()
        if recording_policy is None:
            recording_policy = 'PERMITTED_WITH_CONSENT'
        if recording_policy not in RECORDING_POLICIES:
            raise RoomDenied('Unsupported recording policy')
        if consent_notice_version is None:
            consent_notice_version = DEFAULT_CONSENT_NOTICE_VERSION
        if (not isinstance(consent_notice_version, str)
                or not NOTICE_VERSION.fullmatch(consent_notice_version)):
            raise RoomDenied('Invalid consent notice version')
        if retention_days is None:
            retention_days = DEFAULT_RETENTION_DAYS
            retention_basis = 'PLATFORM_DEFAULT'
        else:
            retention_basis = 'HOST_POLICY'
        if (not isinstance(retention_days, int)
                or isinstance(retention_days, bool)
                or not 1 <= retention_days <= MAX_RETENTION_DAYS):
            raise RoomDenied('Invalid retention period')
        for label, value in (('scheduled_start', scheduled_start),
                             ('scheduled_end', scheduled_end)):
            if value is not None and (
                    not isinstance(value, int) or isinstance(value, bool)
                    or value <= 0):
                raise RoomDenied(f'Invalid {label}')
        if (scheduled_start is not None and scheduled_end is not None
                and scheduled_end <= scheduled_start):
            raise RoomDenied('scheduled_end must follow scheduled_start')
        if jurisdiction is not None and (
                not isinstance(jurisdiction, str)
                or not IDENT.fullmatch(jurisdiction)):
            raise RoomDenied('Invalid jurisdiction')
        if case_id is not None:
            if not isinstance(case_id, str) or not IDENT.fullmatch(case_id):
                raise RoomDenied('Invalid case identity')
            if self.cases is None:
                raise RoomDenied('Case binding is not wired in this runtime')
            try:
                case = self.cases.get(case_id)
            except CaseDenied:
                case = None
            if (case is None or (not self._is_operator(actor)
                    and case.get('requester') != actor)):
                # One caller-facing denial for both failures: a case
                # that does not exist and a case this actor may not
                # bind answer identically, so room creation cannot be
                # used to enumerate which case identities exist — the
                # same isolation discipline this service applies to
                # room visibility (D-3).
                raise RoomDenied('Case cannot be bound')
            if jurisdiction is None:
                jurisdiction = case.get('jurisdiction')
        room_id = 'room-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO rooms (room_id, room_type, purpose, state, "
                    "host, case_id, jurisdiction, scheduled_start, "
                    "scheduled_end, recording_policy, recording_state, "
                    "consent_notice_version, retention_category, "
                    "retention_days, retention_basis, "
                    "created_by, created_at, updated_at, state_changed_at) "
                    "VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, ?, "
                    "'NOT_AUTHORIZED', ?, ?, ?, ?, ?, ?, ?, ?);",
                    (room_id, room_type, purpose, actor, case_id,
                     jurisdiction, scheduled_start, scheduled_end,
                     recording_policy, consent_notice_version,
                     RETENTION_CATEGORY, retention_days,
                     retention_basis, actor, now, now, now))
                db.execute(
                    "INSERT INTO room_participants (room_id, identity, role, "
                    "status, via, added_by, created_at, updated_at) "
                    "VALUES (?, ?, 'HOST', 'ADMITTED', 'HOST_SELF', ?, ?, ?);",
                    (room_id, actor, actor, now, now))
                self._record('ROOM_CREATED', room_id=room_id, actor=actor,
                             room_type=room_type, case_id=case_id,
                             jurisdiction=jurisdiction,
                             recording_policy=recording_policy,
                             consent_notice_version=consent_notice_version,
                             retention_days=retention_days,
                             retention_basis=retention_basis)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, 'host')

    def get_room(self, room_id, actor):
        """Full room view for the host, an operator, or a participant."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        with self._connect() as db:
            row = self._visible_row(db, room_id, actor)
            viewer = self._visibility(db, row, actor)
            return self._room_view(db, row, viewer)

    def list_for_actor(self, actor):
        """Rooms the actor hosts or participates in; operators see all."""
        self._check_actor(actor)
        operator = self._is_operator(actor)
        with self._connect() as db:
            if operator:
                rows = db.execute(
                    "SELECT * FROM rooms ORDER BY updated_at DESC "
                    "LIMIT 200;").fetchall()
            else:
                rows = db.execute(
                    "SELECT r.* FROM rooms r WHERE r.host = ? OR EXISTS ("
                    "SELECT 1 FROM room_participants p WHERE "
                    "p.room_id = r.room_id AND p.identity = ? "
                    "AND p.status != 'REMOVED') "
                    "ORDER BY r.updated_at DESC LIMIT 200;",
                    (actor, actor)).fetchall()
            result = []
            for row in rows:
                view = self._room_view(db, row, None)
                view['participant_count'] = db.execute(
                    "SELECT COUNT(*) AS n FROM room_participants "
                    "WHERE room_id = ? AND status = 'ADMITTED';",
                    (row['room_id'],)).fetchone()['n']
                result.append(view)
            return result

    def transition(self, room_id, actor, action, *, scheduled_start=None,
                   scheduled_end=None):
        """One checked lifecycle transition (22.3). Host or operator;
        hold/release_hold are operator-only (owner-controlled
        administrative authority). Invalid transitions refuse and
        change nothing."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if action in _OPERATOR_ONLY_ACTIONS or action == 'unlock':
            pass
        elif action not in _TRANSITIONS:
            raise RoomDenied('Unknown transition')
        if action == 'schedule':
            for label, value in (('scheduled_start', scheduled_start),
                                 ('scheduled_end', scheduled_end)):
                if value is not None and (
                        not isinstance(value, int) or isinstance(value, bool)
                        or value <= 0):
                    raise RoomDenied(f'Invalid {label}')
            if (scheduled_start is not None and scheduled_end is not None
                    and scheduled_end <= scheduled_start):
                raise RoomDenied('scheduled_end must follow scheduled_start')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._manage_row(db, room_id, actor)
                state = row['state']
                if action in _OPERATOR_ONLY_ACTIONS:
                    if not self._is_operator(actor):
                        raise RoomForbidden(
                            'Evidence hold is an operator authority')
                    if action == 'hold':
                        if state in TERMINAL_STATES or state == 'EVIDENCE_HOLD':
                            raise RoomDenied(
                                f'Room in state {state} cannot be held')
                        target = 'EVIDENCE_HOLD'
                        db.execute(
                            "UPDATE rooms SET hold_from = ? WHERE room_id = ?;",
                            (state, room_id))
                    else:
                        if state != 'EVIDENCE_HOLD':
                            raise RoomDenied('Room is not on evidence hold')
                        target = row['hold_from'] or 'DRAFT'
                        db.execute(
                            "UPDATE rooms SET hold_from = NULL "
                            "WHERE room_id = ?;", (room_id,))
                elif action == 'unlock':
                    if state != 'LOCKED':
                        raise RoomDenied(
                            f'Transition unlock is not permitted '
                            f'from state {state}')
                    target = row['locked_from'] or 'WAITING_ROOM'
                    db.execute(
                        "UPDATE rooms SET locked_from = NULL "
                        "WHERE room_id = ?;", (room_id,))
                else:
                    if state == 'EVIDENCE_HOLD':
                        raise RoomDenied(
                            'Room is on evidence hold; transitions are frozen')
                    target = _TRANSITIONS[action].get(state)
                    if target is None:
                        raise RoomDenied(
                            f'Transition {action} is not permitted '
                            f'from state {state}')
                    if action == 'schedule':
                        start = (scheduled_start
                                 if scheduled_start is not None
                                 else row['scheduled_start'])
                        end = (scheduled_end
                               if scheduled_end is not None
                               else row['scheduled_end'])
                        if start is None:
                            raise RoomDenied(
                                'schedule requires a scheduled_start')
                        if end is not None and end <= start:
                            raise RoomDenied(
                                'scheduled_end must follow scheduled_start')
                        db.execute(
                            "UPDATE rooms SET scheduled_start = ?, "
                            "scheduled_end = ? WHERE room_id = ?;",
                            (start, end, room_id))
                    if action == 'lock':
                        db.execute(
                            "UPDATE rooms SET locked_from = ? "
                            "WHERE room_id = ?;", (state, room_id))
                db.execute(
                    "UPDATE rooms SET state = ?, state_changed_at = ?, "
                    "updated_at = ? WHERE room_id = ?;",
                    (target, now, now, room_id))
                if target not in RECORDING_AUTHORIZABLE_STATES:
                    # Recording authorization may exist only while the
                    # room is in WAITING_ROOM or ACTIVE. Any transition
                    # landing anywhere else — lock, suspend, end,
                    # cancel, archive, hold, schedule — revokes it in
                    # this same transaction (D-1): an authorization
                    # describes a live, continuously authorized room,
                    # and a room that unlocks or resumes re-earns it
                    # through a fresh authorization pass.
                    fresh = self._room_row(db, room_id)
                    self._revoke_recording_locked(
                        db, fresh, f'room_{target.lower()}')
                self._record('ROOM_TRANSITION', room_id=room_id, actor=actor,
                             action=action, from_state=state,
                             to_state=target)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            viewer = self._visibility(db, row, actor)
            return self._room_view(db, row, viewer)

    # -- participants and invitations -----------------------------------

    def _require_participant_change_state(self, row):
        if row['state'] not in PARTICIPANT_CHANGE_STATES:
            raise RoomDenied(
                f"Participants cannot change while the room is "
                f"{row['state']}")

    def add_participant(self, room_id, actor, identity, role):
        """Directly admit an account as a participant (host/operator).
        The account acts only as itself; admission asserts nothing
        about the person beyond the account identity (22.4)."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if not isinstance(identity, str) or not IDENT.fullmatch(identity):
            raise RoomDenied('Invalid participant identity')
        if role not in ROLES or role == 'HOST':
            raise RoomDenied('Unsupported participant role')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._manage_row(db, room_id, actor)
                self._require_participant_change_state(row)
                existing = self._participant(db, room_id, identity)
                if existing is not None and existing['status'] == 'ADMITTED':
                    raise RoomDenied('Already a participant')
                if existing is not None:
                    db.execute(
                        "UPDATE room_participants SET role = ?, "
                        "status = 'ADMITTED', via = 'HOST_ADD', "
                        "added_by = ?, updated_at = ? WHERE room_id = ? "
                        "AND identity = ?;",
                        (role, actor, now, room_id, identity))
                else:
                    db.execute(
                        "INSERT INTO room_participants (room_id, identity, "
                        "role, status, via, added_by, created_at, "
                        "updated_at) VALUES (?, ?, ?, 'ADMITTED', 'HOST_ADD', "
                        "?, ?, ?);",
                        (room_id, identity, role, actor, now, now))
                self._revoke_recording_locked(
                    db, self._room_row(db, room_id), 'participant_changed')
                self._record('ROOM_PARTICIPANT_ADDED', room_id=room_id,
                             actor=actor, identity=identity, role=role,
                             via='HOST_ADD')
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, self._visibility(db, row, actor))

    def remove_participant(self, room_id, actor, identity):
        """Remove a participant (host/operator), or leave (the
        participant themself). The host cannot be removed."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if not isinstance(identity, str) or not IDENT.fullmatch(identity):
            raise RoomDenied('Invalid participant identity')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._visible_row(db, room_id, actor)
                self._require_participant_change_state(row)
                if identity == row['host']:
                    raise RoomDenied('The host cannot be removed')
                if (actor != identity and row['host'] != actor
                        and not self._is_operator(actor)):
                    raise RoomForbidden(
                        'Host or operator authority required')
                existing = self._participant(db, room_id, identity)
                if existing is None or existing['status'] == 'REMOVED':
                    raise RoomDenied('Not a participant')
                db.execute(
                    "UPDATE room_participants SET status = 'REMOVED', "
                    "updated_at = ? WHERE room_id = ? AND identity = ?;",
                    (now, room_id, identity))
                self._revoke_recording_locked(
                    db, self._room_row(db, room_id), 'participant_changed')
                self._record('ROOM_PARTICIPANT_REMOVED', room_id=room_id,
                             actor=actor, identity=identity)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, self._visibility(db, row, actor))

    def issue_invite(self, room_id, actor, invitee, role, ttl_seconds=None):
        """Issue a time-limited invitation to an account (22.5). The
        invitation is recorded on the room; only the invited account
        can accept it, and only as itself."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if not isinstance(invitee, str) or not IDENT.fullmatch(invitee):
            raise RoomDenied('Invalid invitee identity')
        if role not in ROLES or role == 'HOST':
            raise RoomDenied('Unsupported participant role')
        if ttl_seconds is None:
            ttl_seconds = DEFAULT_INVITE_TTL_SECONDS
        if (not isinstance(ttl_seconds, int)
                or isinstance(ttl_seconds, bool)
                or not 60 <= ttl_seconds <= MAX_INVITE_TTL_SECONDS):
            raise RoomDenied('Invalid invitation lifetime')
        now = int(time.time())
        invite_id = 'inv-' + secrets.token_urlsafe(12)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._manage_row(db, room_id, actor)
                self._require_participant_change_state(row)
                existing = self._participant(db, room_id, invitee)
                if existing is not None and existing['status'] == 'ADMITTED':
                    raise RoomDenied('Already a participant')
                db.execute(
                    "INSERT INTO room_invites (invite_id, room_id, "
                    "invitee, role, status, issued_by, expires_at, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, "
                    "'PENDING', ?, ?, ?, ?);",
                    (invite_id, room_id, invitee, role, actor,
                     now + ttl_seconds, now, now))
                self._record('ROOM_INVITE_ISSUED', room_id=room_id,
                             actor=actor, invite_id=invite_id,
                             invitee=invitee, role=role,
                             expires_at=now + ttl_seconds)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'invite_id': invite_id, 'room_id': room_id,
                'invitee': invitee, 'role': role, 'status': 'PENDING',
                'issued_by': actor, 'expires_at': now + ttl_seconds}

    def accept_invite(self, room_id, actor, invite_id):
        """Accept an invitation: the invited account, acting as
        itself, becomes an admitted participant. Expired invitations
        are rejected (22.13)."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if not isinstance(invite_id, str) or not IDENT.fullmatch(invite_id):
            raise RoomDenied('Invalid invitation identity')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                invite = db.execute(
                    "SELECT * FROM room_invites WHERE invite_id = ? "
                    "AND room_id = ?;", (invite_id, room_id)).fetchone()
                if invite is None:
                    raise RoomNotFound('Unknown invitation')
                if invite['invitee'] != actor:
                    raise RoomForbidden(
                        'Only the invited account may accept this invitation')
                row = self._room_row(db, room_id)
                self._require_participant_change_state(row)
                if invite['status'] != 'PENDING':
                    raise RoomDenied('Invitation is no longer pending')
                if invite['expires_at'] <= now:
                    db.execute(
                        "UPDATE room_invites SET status = 'EXPIRED', "
                        "updated_at = ? WHERE invite_id = ?;",
                        (now, invite_id))
                    self._record('ROOM_INVITE_EXPIRED', room_id=room_id,
                                 actor=actor, invite_id=invite_id)
                    db.commit()
                    raise RoomDenied('Invitation has expired')
                existing = self._participant(db, room_id, actor)
                if existing is not None and existing['status'] == 'ADMITTED':
                    raise RoomDenied('Already a participant')
                if existing is not None:
                    db.execute(
                        "UPDATE room_participants SET role = ?, "
                        "status = 'ADMITTED', via = 'INVITE', "
                        "added_by = ?, updated_at = ? WHERE room_id = ? "
                        "AND identity = ?;",
                        (invite['role'], invite['issued_by'], now,
                         room_id, actor))
                else:
                    db.execute(
                        "INSERT INTO room_participants (room_id, identity, "
                        "role, status, via, added_by, created_at, "
                        "updated_at) VALUES (?, ?, ?, 'ADMITTED', 'INVITE', "
                        "?, ?, ?);",
                        (room_id, actor, invite['role'],
                         invite['issued_by'], now, now))
                db.execute(
                    "UPDATE room_invites SET status = 'ACCEPTED', "
                    "updated_at = ? WHERE invite_id = ?;", (now, invite_id))
                self._revoke_recording_locked(
                    db, self._room_row(db, room_id), 'participant_changed')
                self._record('ROOM_INVITE_ACCEPTED', room_id=room_id,
                             actor=actor, invite_id=invite_id,
                             role=invite['role'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, self._visibility(db, row, actor))

    def revoke_invite(self, room_id, actor, invite_id):
        """Revoke a pending invitation (host/operator)."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if not isinstance(invite_id, str) or not IDENT.fullmatch(invite_id):
            raise RoomDenied('Invalid invitation identity')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._manage_row(db, room_id, actor)
                invite = db.execute(
                    "SELECT * FROM room_invites WHERE invite_id = ? "
                    "AND room_id = ?;", (invite_id, room_id)).fetchone()
                if invite is None:
                    raise RoomNotFound('Unknown invitation')
                if invite['status'] != 'PENDING':
                    raise RoomDenied('Invitation is no longer pending')
                db.execute(
                    "UPDATE room_invites SET status = 'REVOKED', "
                    "updated_at = ? WHERE invite_id = ?;", (now, invite_id))
                self._record('ROOM_INVITE_REVOKED', room_id=room_id,
                             actor=actor, invite_id=invite_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'invite_id': invite_id, 'room_id': room_id,
                'status': 'REVOKED'}

    # -- consent and recording authorization ----------------------------

    def record_consent(self, room_id, actor, *, decision, notice_version):
        """Record the actor's OWN recording consent (22.8). Consent
        is bound to the participant, the consent scope, the notice
        version presented, and the time — and to nobody else: a host
        or operator cannot consent on a participant's behalf.
        Decisions are append-only; the current decision is the
        latest. A refusal or withdrawal while recording is authorized
        revokes the authorization in the same transaction, as does a
        grant recorded against a notice version other than the room's
        canonical version: such a grant is preserved on the record
        but no longer counts toward authorization, so the standing
        authorization no longer describes the consent on record
        (D-2)."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        if decision not in CONSENT_DECISIONS:
            raise RoomDenied('Unsupported consent decision')
        if (not isinstance(notice_version, str)
                or not NOTICE_VERSION.fullmatch(notice_version)):
            raise RoomDenied('Invalid consent notice version')
        now = int(time.time())
        consent_id = 'consent-' + secrets.token_urlsafe(12)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._visible_row(db, room_id, actor)
                if row['state'] not in CONSENT_STATES:
                    raise RoomDenied(
                        f"Consent cannot change while the room is "
                        f"{row['state']}")
                participant = self._participant(db, room_id, actor)
                if participant is None or participant['status'] != 'ADMITTED':
                    raise RoomForbidden(
                        'Only an admitted participant records consent')
                if decision == 'WITHDRAWN' and self._current_consent(
                        db, room_id, actor) != 'GRANTED':
                    raise RoomDenied('No granted consent to withdraw')
                db.execute(
                    "INSERT INTO room_consents (consent_id, room_id, "
                    "identity, scope, decision, notice_version, "
                    "recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (consent_id, room_id, actor, CONSENT_SCOPE, decision,
                     notice_version, now))
                self._record('ROOM_CONSENT_RECORDED', room_id=room_id,
                             actor=actor, identity=actor,
                             scope=CONSENT_SCOPE, decision=decision,
                             notice_version=notice_version)
                if (decision != 'GRANTED'
                        or notice_version
                        != row['consent_notice_version']):
                    self._revoke_recording_locked(
                        db, self._room_row(db, room_id), 'consent_changed')
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'consent_id': consent_id, 'room_id': room_id,
                'identity': actor, 'scope': CONSENT_SCOPE,
                'decision': decision, 'notice_version': notice_version,
                'recorded_at': now}

    def authorize_recording(self, room_id, actor):
        """Authorize the recording state (host/operator). Recording
        itself is executed by the gated media plane; this is the
        consent gate in front of it (22.8): the room must be live or
        in its waiting state, the room's policy must not prohibit
        recording, and EVERY admitted participant — host included —
        must hold a current GRANTED consent recorded against the
        room's canonical consent notice version. A consent recorded
        against any other version remains on the append-only record
        but does not count (D-2). Anything less refuses and changes
        nothing."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._manage_row(db, room_id, actor)
                if row['state'] not in RECORDING_AUTHORIZABLE_STATES:
                    raise RoomDenied(
                        f"Recording cannot be authorized while the room "
                        f"is {row['state']}")
                if row['recording_policy'] == 'PROHIBITED':
                    raise RoomDenied(
                        'The room recording policy prohibits recording')
                if row['recording_state'] == 'AUTHORIZED':
                    raise RoomDenied('Recording is already authorized')
                admitted = self._admitted(db, room_id)
                canonical = row['consent_notice_version']
                missing = [p['identity'] for p in admitted
                           if not self._consent_counts(
                               self._current_consent_record(
                                   db, room_id, p['identity']), canonical)]
                if missing:
                    raise RoomDenied(
                        'Recording consent is missing for '
                        f'{len(missing)} participant(s)')
                db.execute(
                    "UPDATE rooms SET recording_state = 'AUTHORIZED', "
                    "updated_at = ? WHERE room_id = ?;", (now, room_id))
                self._record('ROOM_RECORDING_AUTHORIZED', room_id=room_id,
                             actor=actor,
                             notice_version=canonical,
                             participants=len(admitted))
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, self._visibility(db, row, actor))

    def revoke_recording(self, room_id, actor):
        """Revoke a recording authorization (host/operator)."""
        self._check_actor(actor)
        self._check_room_id(room_id)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._manage_row(db, room_id, actor)
                if row['recording_state'] != 'AUTHORIZED':
                    raise RoomDenied('Recording is not authorized')
                db.execute(
                    "UPDATE rooms SET recording_state = 'NOT_AUTHORIZED', "
                    "updated_at = ? WHERE room_id = ?;", (now, room_id))
                self._record('ROOM_RECORDING_REVOKED', room_id=room_id,
                             actor=actor, reason='host_revoked')
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = self._room_row(db, room_id)
            return self._room_view(db, row, self._visibility(db, row, actor))
