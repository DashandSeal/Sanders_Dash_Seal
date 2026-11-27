"""Showtime — the media platform.

The production build-out of the Showtime design
(canonical catalog rows #112 + #125, Band 2D),
built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q93).

NAME AND UNIFICATION — verified before
building, per the name law: this platform
exists by the owner's own ruling **D-N10**
(decisions.md): "Sanders Media is Showtime.
Sanders Media and Sanders Media Hub are
combined into one platform, called Showtime."
The queue-note reading "Showtime" matched the
ruled name exactly. The ruling joins exactly
two source identities and nothing more:
canonical catalog row #112, **Sanders Media**
(Set B — its design record is its schema row:
persona "Voice", professional tier, and
nothing beyond the row), and canonical
catalog row #125, **Sanders Media Hub** (Set C
Tier 7 — nickname "Broadcast"). No other media
identity is joined: Sanders Entertainment
(catalog #79) and Voice / Audio / Video
(catalog #11) are separate platforms and stay
separate. Set B carries NO entry under
"Sanders Media Hub", "Showtime", "Sanders
Marketing", or "Sanders Sales" (verified by
direct read of the schema and the tier pricing
file); Set C carries no entry under the name
"Showtime" (verified by direct read); Set A
carries no entry for any of the three names
(platform registry read directly); the MASTER
names none of them.

PERSONA AND NICKNAME — RECORDED, NOT ADOPTED:
Set B's persona for Sanders Media is "Voice"
and Set C's nickname for Sanders Media Hub is
"Broadcast". Both forms are recorded exactly
as found; neither is adopted as the platform's
persona, name, or identifier — the platform's
name is Showtime, per D-N10.

Set C's purpose text for Sanders Media Hub —
"Media production, broadcasting supremacy,
content distribution, internal
communications" — is recorded verbatim as
found and is NOT the built scope beyond
governed media records: no media is produced,
nothing is broadcast, no content is
distributed, and nothing is syndicated by this
build; the "supremacy" wording is
design-record language, not a claim. Set B's
Sanders Media record carries no purpose text
beyond its schema row.

DESIGNED ADDRESSES — RECORDED, NOT ACTIVATED:
the platform's reserved home is
showtime.sandersdashandseal.com (owner
reservation, 2026-11-24: the Showtime home is
reserved on the flagship domain and activates
when the platform is built whole). This build
records the reservation as designed and takes
NO action on it: no DNS record is created, no
certificate coverage is issued, and nothing is
served on that subdomain — activation is an
owner-side Cloudflare step plus the owner's
named certificate-issuance approval, both
outside this build. Set C's registry record
also carries the designed hostname
media-hub.sandersglobal.com for Sanders Media
Hub; it sits under the unowned parent
sandersglobal.com, so it is recorded and
nothing is served there. The platform's route
family is wired on the flagship hosts per the
program's standard pattern, like every
platform in this program.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
two source identities and the owner's D-N10
unification ruling (decisions.md); Set B's
Sanders Media schema row (persona "Voice",
professional tier) and Set C's Sanders Media
Hub tier entry (Tier 7, nickname "Broadcast",
purpose text above). No Showtime, Sanders
Media, or Sanders Media Hub module existed in
any examined source.

REBUILT (everything executable in this module):
the governed platform below — Showtime's own
identity and store, carrying media records:

- **Media records**: a subject reference (a
  media program, channel, or content line under
  service, by reference), a declared set of
  program references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The program discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (SHOWTIME_POSITION_CONFIRMED /
  PROGRAM_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no programs stands
  NO_PROGRAMS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no programs were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never production**: determinations
  are records placed before human operators.
  The platform produces no media, broadcasts
  nothing, distributes no content, and
  syndicates nothing — produce_media,
  broadcast_media, distribute_content,
  syndicate_content, and external_execution
  are refused by name under
  SHOWTIME_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  programs are carried by reference only; the
  platform holds no media content, no
  broadcast state, no rights or licensing
  state, and no credentials — references and
  workflow state only, as across the ecosystem.
  No public or customer surface is designed
  for this platform in any examined source, so
  none was built; no security internals are
  exposed.
- **NAICS**: Set B's schema row attests a
  single code for Sanders Media (519130) —
  recorded exactly as found. No owner ruling
  assigns a NAICS set to Showtime, so NO NAICS
  set is carried into the platform's built
  identity and none is invented.
- **Separation**: Showtime is its own
  platform — the one platform the owner's
  D-N10 ruling forms from Sanders Media and
  Sanders Media Hub. It is not Sanders
  Entertainment (catalog #79 — a separate
  platform, built whole at Q70, whose own
  record already holds this separation), not
  Sanders Communications (catalog #113), and
  not Voice / Audio / Video (catalog #11) —
  no identity beyond the two the ruling joins
  is merged into it, and it is merged into
  none.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 512110,
512120, 512191, 512199, 541810, 541820 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
attested sets recorded above stand as found; the
reconciled six govern the built identity from this lock-in
forward.
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
    platform_id='showtime',
    name='Showtime',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=('512110', '512120', '512191', '512199', '541810', '541820'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Media production, broadcasting, content distribution, internal communications'
DISCIPLINE = 'SHOWTIME_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_showtime', 'approve_showtime', 'record_outcome',
    'view_showtime', 'view_design')
EXECUTION_OPERATIONS = ('produce_media', 'broadcast_media',
    'distribute_content', 'syndicate_content',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SHOWTIME_POSITION_CONFIRMED', 'PROGRAM_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SHOWTIME_POSITION_CONFIRMED', 'PROGRAM_ACTION_REQUIRED')
MAX_REFS = 100


class ShowtimeDenied(Exception):
    """The requested Showtime operation is not
    allowed."""


class ShowtimeForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class ShowtimeService:
    """Showtime: governed media records under the media records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ShowtimeDenied(
                'Showtime requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'showtime', {
            'OPERATOR': {'SHOWTIME'},
            'AUDITOR': {'SHOWTIME'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS showtime_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    program_refs TEXT NOT NULL,
                    program_count INTEGER NOT NULL,
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
            raise ShowtimeForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise ShowtimeForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise ShowtimeForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SHOWTIME',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise ShowtimeForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise ShowtimeDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['decisions.md D-N10 — the owner’s ruling: Sanders Media and Sanders Media Hub are combined into one platform, called Showtime', 'canonical catalog rows #112 (Sanders Media, Set B) and #125 (Sanders Media Hub, Set C Tier 7)', 'Set B database_schema.sql row for Sanders Media (persona Voice, professional, $4,000,000, NAICS 519130) and tier_pricing_global.py (read directly) — no entry under Sanders Media Hub, Showtime, Sanders Marketing, or Sanders Sales', 'Set C branch README (read directly): Sanders Media Hub Tier 7 entry (nickname Broadcast, $252,000,000/yr, purpose text) and its embedded registry record (media-hub.sandersglobal.com) — no entry under the name Showtime', 'Set A carries no entry for any of the three names (platform registry read directly); the MASTER names none of them', 'owner reservation 2026-11-24: showtime.sandersdashandseal.com is Showtime’s reserved home — recorded as designed, not activated by this build'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Showtime is the media platform — the one platform formed by the owner’s D-N10 ruling, which combines Sanders Media (canonical catalog row 112, Set B) and Sanders Media Hub (canonical catalog row 125, Set C Tier 7) into one platform called Showtime; the ruling joins exactly those two identities and nothing more. It carries governed media records over media programs, channels, and content lines and declared program sets presented by reference only. Set C’s purpose text for Sanders Media Hub — Media production, broadcasting supremacy, content distribution, internal communications — is recorded verbatim as found and is NOT the built scope: no media is produced, nothing is broadcast, no content is distributed, and nothing is syndicated by this build; the supremacy wording is design-record language, not a claim. Set B’s Sanders Media record is name-only beyond its schema row. The platform produces no media, broadcasts nothing, distributes no content, and syndicates nothing: produce_media, broadcast_media, distribute_content, syndicate_content, and external_execution are refused by name under SHOWTIME_RECORDS_ONLY, and determinations are records for human operators, never production. A record declared with no programs stands NO_PROGRAMS_SUBMITTED and no determination can be recorded on it. PERSONA AND NICKNAME — RECORDED, NOT ADOPTED: Set B’s persona Voice (Sanders Media) and Set C’s nickname Broadcast (Sanders Media Hub) are recorded exactly as found; neither is adopted as the platform’s persona, name, or identifier. DESIGNED ADDRESSES — RECORDED, NOT ACTIVATED: the reserved home showtime.sandersdashandseal.com (owner reservation, 2026-11-24) is recorded as designed; this build creates no DNS record, issues no certificate coverage, and serves nothing on that subdomain — activation is an owner-side Cloudflare step plus the owner’s named certificate-issuance approval. The designed hostname media-hub.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. NAICS: Set B attests a single code for Sanders Media (519130), recorded as found; no NAICS set is carried into the built identity and none is invented. The platform holds references and workflow state only — no media content, no broadcast state, no rights or licensing state, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Showtime is distinct from Sanders Entertainment (catalog 79), Sanders Communications (catalog 113), and Voice / Audio / Video (catalog 11) — identities are never merged beyond the two the D-N10 ruling joins.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the media records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise ShowtimeDenied(
                f'Operation {operation!r} is refused: the'
                ' Showtime platform'
                ' carries media records'
                ' only \u2014 it produces no'
                ' media, broadcasts nothing,'
                ' distributes no content, and'
                ' syndicates nothing itself'
                ' (SHOWTIME_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise ShowtimeDenied(
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
        operations = json.loads(row['program_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'program_refs': operations,
            'program_count': row['program_count'],
            'program_state': ('NO_PROGRAMS_SUBMITTED'
                             if row['program_count'] == 0
                             else 'PROGRAMS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, program_refs,
                      scope_ref, *, region=None):
        """Record one media record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_PROGRAMS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record produces no
        media, broadcasts nothing, and
        distributes no content."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ShowtimeDenied(
                    f'A {label} is required')
        if not isinstance(program_refs, (list, tuple)):
            raise ShowtimeDenied(
                'program_refs must be a list of references')
        if len(program_refs) > MAX_REFS:
            raise ShowtimeDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in program_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise ShowtimeDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'showtime-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SHOWTIME_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    program_count=len(operations))
                db.execute(
                    'INSERT INTO showtime_records'
                    ' (record_id, subject_ref, program_refs,'
                    ' program_count, scope_ref, status, outcome,'
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
                'SELECT * FROM showtime_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM showtime_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM showtime_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise ShowtimeDenied(
                'Showtime record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested media record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise ShowtimeDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM showtime_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ShowtimeDenied(
                        'Showtime record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise ShowtimeDenied(
                        f"Cannot {action} a media record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SHOWTIME_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE showtime_records SET status = ?,'
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
                'SELECT * FROM showtime_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SHOWTIME_POSITION_CONFIRMED or PROGRAM_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_PROGRAMS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise ShowtimeDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ShowtimeDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM showtime_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise ShowtimeDenied(
                        'Showtime record not found')
                if row['status'] != 'APPROVED':
                    raise ShowtimeDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" media records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['program_count'] == 0:
                    raise ShowtimeDenied(
                        'NO_PROGRAMS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SHOWTIME_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE showtime_records SET status = ?,'
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
                'SELECT * FROM showtime_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM showtime_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM showtime_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM showtime_records'
                ' WHERE program_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(program_count), 0) AS n'
                ' FROM showtime_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_programs_submitted': no_refs,
            'programs_declared_total': refs_total,
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
                    raise ShowtimeDenied(str(exc)) from exc
                self._record('SHOWTIME_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
