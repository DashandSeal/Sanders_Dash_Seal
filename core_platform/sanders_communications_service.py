"""Sanders Communications — the secure
communications platform.

The production build-out of the Sanders
Communications design (canonical catalog row
#113, Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q82).

NAME — verified before building, per the name
law: the canonical catalog (row #113), Set B,
and Set C Tier 7 all name this platform
**Sanders Communications** — the queue-note
reading matched the source name exactly. Set A
carries no entry for this platform.

PERSONA FORMS — RECORDED, NEITHER ADOPTED: Set
B's persona column names "Signal"; Set C's
nickname is "Connect" (its embedded registry
record pairs the platform as "Sanders
Communications / Connect"). The two forms
differ; both are recorded exactly as found, and
neither is adopted as the platform's persona,
name, or identifier. ("Signal" is also the name
of the separate Sanders Signal platform, catalog
#12 — recorded as found, never harmonized.)

Set C's purpose text for this name — "Secure
communications, global networks, emergency
comms, encrypted messaging mastery" — is
recorded verbatim as found and is NOT the built
scope beyond governed communications records:
no message is transmitted, no network is
operated, no traffic is encrypted, and no
emergency is broadcast by this build. The
designed hostname communications.sandersglobal.com
(Set C registry record) sits under the unowned
parent sandersglobal.com, so it is recorded and
nothing is served there.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — secure communications,
global networks, and emergency communications
(canonical catalog row #113; Set C Tier 7; the
Set B schema seed carries the platform at the
professional tier). No Sanders Communications
module existed in any examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders
Communications platform's own identity and
store, carrying communications records:

- **Communications records**: a subject
  reference (a communications program, network
  arrangement, or messaging service under
  service, by reference), a declared set of
  channel references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The channel discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set
  (COMMUNICATIONS_POSITION_CONFIRMED /
  CHANNEL_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no channels stands
  NO_CHANNELS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no channels were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never transmission**: determinations
  are records placed before human operators. The
  platform transmits no message, operates no
  network, encrypts no traffic, and broadcasts
  no emergency — transmit_message,
  operate_network, encrypt_traffic,
  broadcast_emergency, and external_execution
  are refused by name under
  COMMUNICATIONS_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  channels are carried by reference only; the
  platform holds no message content, no
  encryption keys, no network credentials, and
  no live-system state — references and workflow
  state only, as across the ecosystem. No public
  or customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: Set B attests a single code
  (517810). No owner ruling assigns a set, and
  the canonical catalog row carries none — NO
  NAICS set is carried into the platform's built
  identity; the attested code stands recorded as
  found and unruled.
- **Separation**: the Sanders Communications
  platform is its own platform. It is not
  Sanders Signal (catalog #12 — the social
  distribution hub), not Voice / Audio / Video
  (catalog #11), not Emergency Global
  Communication (catalog #140 — a
  domain-registration record with no designed
  purpose), and not Sanders Technology (catalog
  #123) — identities are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    validate_identity,
)
from .rtsa_foundation import (
    latest_check_in as _foundation_latest_check_in,
)
from .rtsa_foundation import (
    record_check_in as _foundation_record_check_in,
)


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='sanders_communications',
    name='Sanders Communications',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Secure communications, global networks, emergency comms'
DISCIPLINE = 'COMMUNICATIONS_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_communications', 'approve_communications', 'record_outcome',
    'view_communications', 'view_design')
EXECUTION_OPERATIONS = ('transmit_message', 'operate_network',
    'encrypt_traffic', 'broadcast_emergency',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('COMMUNICATIONS_POSITION_CONFIRMED', 'CHANNEL_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('COMMUNICATIONS_POSITION_CONFIRMED', 'CHANNEL_ACTION_REQUIRED')
MAX_REFS = 100


class SandersCommunicationsDenied(Exception):
    """The requested Sanders Communications operation is not
    allowed."""


class SandersCommunicationsForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersCommunicationsService:
    """Sanders Communications: governed communications records under the communications records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersCommunicationsDenied(
                'Sanders Communications requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_communications', {
            'OPERATOR': {'SANDERS_COMMUNICATIONS'},
            'AUDITOR': {'SANDERS_COMMUNICATIONS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_communications_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    channel_refs TEXT NOT NULL,
                    channel_count INTEGER NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    evidence_ref TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
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
            raise SandersCommunicationsForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersCommunicationsForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersCommunicationsForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_COMMUNICATIONS',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersCommunicationsForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersCommunicationsDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #113', 'Set B schema seed row (read directly)', 'Set C Tier 7 catalog entry (read directly); Set A carries no entry', 'decisions.md: no ruling names this platform; the Sanders Signal identity (catalog #12) stays separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Communications is the secure communications platform: it carries governed communications records over communications programs, network arrangements, and messaging services and declared channel sets presented by reference only. Set C’s purpose text for this name — Secure communications, global networks, emergency comms, encrypted messaging mastery — is recorded verbatim as found and is NOT the built scope: no message is transmitted, no network is operated, no traffic is encrypted, and no emergency is broadcast by this build. The platform transmits no message, operates no network, encrypts no traffic, and broadcasts no emergency: transmit_message, operate_network, encrypt_traffic, broadcast_emergency, and external_execution are refused by name under COMMUNICATIONS_RECORDS_ONLY, and determinations are records for human operators, never transmission. A record declared with no channels stands NO_CHANNELS_SUBMITTED and no determination can be recorded on it. PERSONA FORMS — RECORDED, NEITHER ADOPTED: Set B’s persona Signal and Set C’s nickname Connect differ; both are recorded exactly as found and neither is adopted as the platform’s persona, name, or identifier. Set A carries no entry for this platform. The designed hostname communications.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its attested NAICS code (Set B, 517810) is recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no message content, no encryption keys, no network credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Communications is distinct from Sanders Signal (catalog 12), Voice / Audio / Video (catalog 11), Emergency Global Communication (catalog 140), and Sanders Technology (catalog 123) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the communications records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersCommunicationsDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Communications platform'
                ' carries communications records'
                ' only \u2014 it transmits no message,'
                ' operates no network, encrypts'
                ' no traffic, and broadcasts no'
                ' emergency itself'
                ' (COMMUNICATIONS_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersCommunicationsDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'discipline': DISCIPLINE,
            'designed_role': DESIGNED_ROLE,
        }

    # -- records ------------------------------------------------------

    @staticmethod
    def _record_view(row):
        operations = json.loads(row['channel_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'channel_refs': operations,
            'channel_count': row['channel_count'],
            'channel_state': ('NO_CHANNELS_SUBMITTED'
                             if row['channel_count'] == 0
                             else 'CHANNELS_SUBMITTED'),
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_record(self, actor, subject_ref, channel_refs,
                      scope_ref, *, region=None):
        """Record one communications record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_CHANNELS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record transmits no
        message, operates no network, and
        encrypts no traffic."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersCommunicationsDenied(
                    f'A {label} is required')
        if not isinstance(channel_refs, (list, tuple)):
            raise SandersCommunicationsDenied(
                'channel_refs must be a list of references')
        if len(channel_refs) > MAX_REFS:
            raise SandersCommunicationsDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in channel_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersCommunicationsDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-communications-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_COMMUNICATIONS_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    channel_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_communications_records'
                    ' (record_id, subject_ref, channel_refs,'
                    ' channel_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(operations), len(operations),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_communications_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_communications_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_communications_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersCommunicationsDenied(
                'Communications record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested communications record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersCommunicationsDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_communications_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersCommunicationsDenied(
                        'Communications record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersCommunicationsDenied(
                        f"Cannot {action} a communications record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_COMMUNICATIONS_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_communications_records SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    (new_status, actor, now, receipt_id,
                     record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM sanders_communications_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (COMMUNICATIONS_POSITION_CONFIRMED or CHANNEL_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_CHANNELS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersCommunicationsDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersCommunicationsDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_communications_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersCommunicationsDenied(
                        'Communications record not found')
                if row['status'] != 'APPROVED':
                    raise SandersCommunicationsDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" communications records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['channel_count'] == 0:
                    raise SandersCommunicationsDenied(
                        'NO_CHANNELS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_COMMUNICATIONS_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_communications_records SET status = ?,'
                    ' outcome = ?, evidence_ref = ?, updated_by'
                    ' = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE record_id = ?',
                    ('OUTCOME_RECORDED', outcome,
                     evidence_ref.strip(), actor, now, receipt_id,
                     record_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM sanders_communications_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_communications_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_communications_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_communications_records'
                ' WHERE channel_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(channel_count), 0) AS n'
                ' FROM sanders_communications_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_channels_submitted': no_refs,
            'channels_declared_total': refs_total,
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to
        the platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise SandersCommunicationsDenied(str(exc)) from exc
                self._record('SANDERS_COMMUNICATIONS_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
