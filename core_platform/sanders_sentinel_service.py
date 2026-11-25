"""Sanders Sentinel — the global watchdog platform.

The production build-out of the Sanders Sentinel design
(canonical catalog row #54, Band 2D), built whole as its
own platform service over the shared RTSA foundation
(RTSA Build Program Q48).

NAME — verified before building, per the name law: the
canonical catalog (row #54), the master grid
(deploy/oracle/sanders_master_grid.json id 1), and the
owner's recorded rulings (canonical-catalog decisions
D-N6 and the Group 3 watchdog roster) name this platform
**Sanders Sentinel**. D-N6 rules expressly: "Not Alpha.
His name is Sanders Sentinel." The Police Men status
record (rtsa_police_men/status.json) names a watchdog
"Alpha (WD-03)" as an enforcer, and the catalog merged
that watchdog record into this row on the strength of the
shared grid nickname — that source designation is recorded
here exactly as found and is NOT adopted as a name: the
owner's ruled watchdog roster is Lil Mama, Baby Girl,
Alph, Bata, and no document the owner has ruled renames
this platform. The CareHiveOS inventory the owner supplied
2026-11-24 likewise uses "Alpha"/"Beta" watchdog
designations that conflict with his ruled roster; his
rulings govern, and nothing here is harmonized to that
document.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — "Global watchdog, critical infrastructure"
(canonical catalog row #54; master grid id 1) — and the
Police Men status record naming the third watchdog as an
enforcer alongside Lil Mama. The grid endpoint the
records carry (a Google Cloud host, :3001) is a file
claim, not a verified live check, and the grid file is
truncated at id 28; no Sentinel module existed in any
examined source.

REBUILT (everything executable in this module): the
governed platform below — Sanders Sentinel's own identity
and store, carrying global-watch records over subjects
and detection signals presented by reference:

- **Watch records**: a subject reference (the system,
  service, or infrastructure under watch, by reference), a
  declared set of detection-signal references, and a scope
  reference, carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by a
  human operator's recorded decision, then an outcome
  recorded against presented evidence (OUTCOME_RECORDED).
- **The signal discipline**: outcomes are recorded only
  for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (ESCALATION_RECORDED / NO_ESCALATION_REQUIRED /
  INCONCLUSIVE). A record declared with no detection
  signals stands NO_SIGNALS_SUBMITTED in every view and in
  the status tallies, and both determinations are refused
  on it — no signals were presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **The watchdog law, enforced**: a watchdog detects and
  escalates only. It holds no corporate decision
  authority, takes no enforcement action against any
  person, company, or platform, and decides nothing: an
  ESCALATION_RECORDED outcome is a record placed before a
  human decision-maker, never an act. Execution operations
  are refused by name with the watchdog signal,
  WATCHDOG_DETECT_AND_ESCALATE_ONLY. This platform
  contains nothing, blocks nothing, suspends nothing, and
  watches no live system — detection enters the ecosystem
  only as records presented to it by reference.
- **Reference-only discipline**: subjects and signals are
  carried by reference only; the platform holds no
  telemetry, no traffic, and no live-system state. (Its
  own record store is its own — it is not a window into
  any operational system.)
- **Separation**: Sanders Sentinel is its own platform.
  It is not Global PBD Sentinel (Q4 — the MASTER §15
  deployed-state integrity monitor; the shared word
  "Sentinel" merges nothing), not Steward Sentinel
  (catalog #84), not Sanders Labyrinth Shield (Q8), not
  RTSA Minotaur (Q9), not the Police Men layer, and not
  any of the four roster watchdogs — Lil Mama, Baby Girl,
  Alph, and Bata are their own platforms.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.

FOUNDER'S RULING 2026-11-25 — BLOODLINE PROTECTION (a
ruled extension of this platform's remit, recorded as a
ruling, not as recovered design): the founder ruled,
verbatim: "Sanders Sentinel is to do more than watch codes
it's role is to protect my bloodline" (Founder's Rulings
on the Bloodline Protection Open Items, addendum
2026-11-25 11:37 MST). Under that ruling this platform
carries BLOODLINE GOVERNANCE COVERAGE: a governed watch
over the bloodline governance records — the Permanent
Bloodline Protection Directive, the Founder's Rulings
record, and the Bloodline Governance Directive in docs/,
each paired with its `.pbd.json` manifest, and the
Sanders Bloodline Registry at its designated docs/ path
when it lands in the repository. A verification cycle
assesses each watched document against its manifest's
recorded payload hash (the MASTER §13 pair assessment,
shared with — never merged into — the §13 validation
engine and the §15 Global PBD Sentinel, whose code-file
scope is unchanged by this coverage). Every assessment is
a durable, receipted check record in this platform's own
store. A document that does not assess sound — a hash
mismatch, a missing or malformed manifest, a missing
required document — raises a FINDING: a watch record
under the bloodline governance scope, placed before a
human operator exactly as every escalation this platform
makes. The coverage verifies and escalates only: it
amends nothing, restores nothing, repairs nothing, and
decides nothing, and no finding is an act against any
person or document. The registry entry is watched as
NOT_LANDED — an informational state, never a finding —
until the registry record itself lands in the repository.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from .pbd_validation import assess_pair
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
    platform_id='sanders_sentinel',
    name='Sanders Sentinel',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Global watchdog, critical infrastructure'
WATCHDOG_DISCIPLINE = 'DETECT_AND_ESCALATE_ONLY'
RECORD_OPERATIONS = (
    'record_watch', 'approve_watch', 'record_outcome',
    'view_watch', 'view_design',
    'verify_bloodline_records', 'view_bloodline_coverage',
)
EXECUTION_OPERATIONS = (
    'enforce_containment', 'block_subject', 'suspend_platform',
    'take_action', 'external_execution',
)
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('ESCALATION_RECORDED', 'NO_ESCALATION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('ESCALATION_RECORDED', 'NO_ESCALATION_REQUIRED')
MAX_SIGNAL_REFS = 100

# -- Bloodline governance coverage (founder's ruling,
# 2026-11-25) ------------------------------------------------
FOUNDER_RULING_BLOODLINE_PROTECTION = (
    "Sanders Sentinel is to do more than watch codes it's"
    ' role is to protect my bloodline')
FOUNDER_RULING_BLOODLINE_DATE = '2026-11-25'
BLOODLINE_GOVERNANCE_SCOPE = 'BLOODLINE_GOVERNANCE'
# The governed watch set: the bloodline governance records,
# each verified against its paired `.pbd.json` manifest.
# A required document that is missing or does not assess
# sound raises a finding; a not-yet-landed optional document
# stands NOT_LANDED and raises nothing.
BLOODLINE_WATCH_SET = (
    {'document': 'docs/PERMANENT_BLOODLINE_PROTECTION_DIRECTIVE.md',
     'title': 'Permanent Bloodline Protection Directive',
     'required': True},
    {'document': 'docs/FOUNDER_RULINGS_BLOODLINE_PROTECTION_2026-11-25.md',
     'title': "Founder's Rulings — Bloodline Protection"
              ' (2026-11-25)',
     'required': True},
    {'document': 'docs/SANDERS_EXECUTIVE_BLOODLINE_GOVERNANCE.md',
     'title': 'Bloodline Governance Directive',
     'required': True},
    {'document': 'docs/SANDERS_BLOODLINE_REGISTRY.md',
     'title': 'Sanders Bloodline Registry',
     'required': False},
)
# Pair verdicts that assess sound: the manifest's recorded
# payload hash equals the document's SHA-256. UNSIGNED is
# the repository's standing state for source manifests —
# structurally sound, never authorization.
BLOODLINE_SOUND_VERDICTS = ('VALID', 'UNSIGNED')
BLOODLINE_CHECK_STATES = ('SOUND', 'FINDING', 'NOT_LANDED')


class SandersSentinelDenied(Exception):
    """The requested Sanders Sentinel operation is not
    allowed."""


class SandersSentinelForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersSentinelService:
    """Sanders Sentinel: governed global-watch records
    under the watchdog detect-and-escalate discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 repo_root=None, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersSentinelDenied(
                'Sanders Sentinel requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._repo_root = (Path(repo_root)
                           if repo_root is not None else None)
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_sentinel', {
            'OPERATOR': {'SENTINEL'},
            'AUDITOR': {'SENTINEL'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_sentinel_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    signal_refs TEXT NOT NULL,
                    signal_count INTEGER NOT NULL,
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
                CREATE TABLE IF NOT EXISTS sanders_sentinel_bloodline_checks (
                    check_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    document_ref TEXT NOT NULL,
                    manifest_ref TEXT,
                    required INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    verdict TEXT,
                    payload_hash_observed TEXT,
                    payload_hash_recorded TEXT,
                    finding_record_id TEXT,
                    checked_by TEXT NOT NULL,
                    checked_at REAL NOT NULL,
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
            raise SandersSentinelForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersSentinelForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersSentinelForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SENTINEL',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersSentinelForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersSentinelDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def bloodline_design_view() -> dict:
        return {
            'founder_ruling': FOUNDER_RULING_BLOODLINE_PROTECTION,
            'ruling_date': FOUNDER_RULING_BLOODLINE_DATE,
            'ruling_source': "Founder's Rulings on the Bloodline"
                             ' Protection Open Items, addendum'
                             ' 2026-11-25 11:37 MST',
            'scope_ref': BLOODLINE_GOVERNANCE_SCOPE,
            'watch_set': [
                {'document': entry['document'],
                 'manifest': entry['document'] + '.pbd.json',
                 'title': entry['title'],
                 'required': entry['required']}
                for entry in BLOODLINE_WATCH_SET],
            'mechanism': 'A verification cycle assesses each'
                         ' watched document against its paired'
                         ' `.pbd.json` manifest payload hash (the'
                         ' MASTER §13 pair assessment). Sound'
                         ' verdicts: VALID and UNSIGNED. Any'
                         ' other verdict on a required document'
                         ' raises a finding — a watch record'
                         ' under the bloodline governance scope,'
                         ' placed before a human operator. An'
                         ' optional document that has not landed'
                         ' in the repository stands NOT_LANDED'
                         ' and raises nothing.',
            'note': 'Bloodline governance coverage is Sanders'
                    ' Sentinel\u2019s ruled remit under the'
                    ' founder\u2019s 2026-11-25 ruling: its role'
                    ' is to protect the bloodline, and the'
                    ' governance records are what it protects'
                    ' here. The coverage detects and escalates'
                    ' only — it amends nothing, restores'
                    ' nothing, and decides nothing. It is'
                    ' carried by this platform, not by the'
                    ' Global PBD Sentinel: that platform\u2019s'
                    ' MASTER §15 scope over executable files is'
                    ' unchanged, and the shared §13 assessment'
                    ' merges no identities.',
        }

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #54',
                'deploy/oracle/sanders_master_grid.json id 1',
                'rtsa_police_men/status.json (watchdog enforcer'
                ' record)',
                'owner rulings D-N6 and the Group 3 watchdog'
                ' roster (canonical-catalog decisions)',
            ],
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'bloodline_protection':
                SandersSentinelService.bloodline_design_view(),
            'note': 'Sanders Sentinel is the global watchdog'
                    ' platform: it carries watch records over'
                    ' subjects and detection signals presented by'
                    ' reference only. A watchdog detects and'
                    ' escalates only — it holds no corporate'
                    ' decision authority, takes no enforcement'
                    ' action, and decides nothing; an escalation'
                    ' is a record placed before a human'
                    ' decision-maker. Execution operations are'
                    ' refused by name with the watchdog signal'
                    ' WATCHDOG_DETECT_AND_ESCALATE_ONLY. A record'
                    ' declared with no detection signals stands'
                    ' NO_SIGNALS_SUBMITTED and no determination'
                    ' can be recorded on it. The name is Sanders'
                    ' Sentinel per owner ruling D-N6 ("Not Alpha");'
                    ' the status record\u2019s "Alpha" designation'
                    ' is recorded as found and is not adopted as'
                    ' a name. Sanders Sentinel is distinct from'
                    ' Global PBD Sentinel, from Steward Sentinel,'
                    ' from Sanders Labyrinth Shield, from RTSA'
                    ' Minotaur, from the Police Men layer, and'
                    ' from the roster watchdogs Lil Mama, Baby'
                    ' Girl, Alph, and Bata — identities are never'
                    ' merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — an execution operation the watchdog discipline
        does not authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersSentinelDenied(
                f'Operation {operation!r} is an execution'
                ' operation: a watchdog detects and escalates'
                ' only and holds no authority to act'
                ' (WATCHDOG_DETECT_AND_ESCALATE_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersSentinelDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'watchdog_discipline': WATCHDOG_DISCIPLINE,
            'designed_role': DESIGNED_ROLE,
        }

    # -- records ------------------------------------------------------

    @staticmethod
    def _record_view(row):
        signals = json.loads(row['signal_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'signal_refs': signals,
            'signal_count': row['signal_count'],
            'signal_state': ('NO_SIGNALS_SUBMITTED'
                             if row['signal_count'] == 0
                             else 'SIGNALS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, signal_refs,
                      scope_ref, *, region=None):
        """Record one global-watch record (operator only) over
        a subject and a declared set of detection-signal
        references, presented by reference. The signal set may
        be empty — the record then stands NO_SIGNALS_SUBMITTED,
        exactly as the signal discipline holds, and no
        determination can be recorded on it. Recording the
        record watches nothing live and acts on nothing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersSentinelDenied(
                    f'A {label} is required')
        if not isinstance(signal_refs, (list, tuple)):
            raise SandersSentinelDenied(
                'signal_refs must be a list of references')
        if len(signal_refs) > MAX_SIGNAL_REFS:
            raise SandersSentinelDenied(
                f'At most {MAX_SIGNAL_REFS} signal'
                ' references per record')
        signals = []
        for ref in signal_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersSentinelDenied(
                    'Every signal reference must be a'
                    ' non-empty string')
            signals.append(ref.strip())
        now = self._now()
        record_id = f'sentinel-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_SENTINEL_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    signal_count=len(signals))
                db.execute(
                    'INSERT INTO sanders_sentinel_records'
                    ' (record_id, subject_ref, signal_refs,'
                    ' signal_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(),
                     json.dumps(signals), len(signals),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sanders_sentinel_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_sentinel_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_sentinel_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersSentinelDenied(
                'Watch record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested watch record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersSentinelDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_sentinel_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSentinelDenied(
                        'Watch record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersSentinelDenied(
                        f"Cannot {action} a watch record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_SENTINEL_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_sentinel_records SET status = ?,'
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
                'SELECT * FROM sanders_sentinel_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (ESCALATION_RECORDED or NO_ESCALATION_REQUIRED) on a
        record declared with no signals is refused —
        NO_SIGNALS_SUBMITTED: no signals were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersSentinelDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersSentinelDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_sentinel_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersSentinelDenied(
                        'Watch record not found')
                if row['status'] != 'APPROVED':
                    raise SandersSentinelDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" watch records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['signal_count'] == 0:
                    raise SandersSentinelDenied(
                        'NO_SIGNALS_SUBMITTED: a record'
                        ' declared with no signals cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_SENTINEL_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_sentinel_records SET status = ?,'
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
                'SELECT * FROM sanders_sentinel_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- bloodline governance coverage ----------------------------

    @staticmethod
    def _bloodline_check_view(row):
        return {
            'check_id': row['check_id'],
            'cycle_id': row['cycle_id'],
            'document_ref': row['document_ref'],
            'manifest_ref': row['manifest_ref'],
            'required': bool(row['required']),
            'state': row['state'],
            'verdict': row['verdict'],
            'payload_hash_observed': row['payload_hash_observed'],
            'payload_hash_recorded': row['payload_hash_recorded'],
            'finding_record_id': row['finding_record_id'],
            'checked_by': row['checked_by'],
            'checked_at': row['checked_at'],
            'receipt_id': row['receipt_id'],
        }

    def _open_bloodline_finding(self, db, document_ref, verdict):
        """The id of the still-open finding watch record for a
        document and verdict signal, if one already stands — a
        standing finding is linked, never duplicated."""
        signal = f'BLOODLINE_GOVERNANCE_ASSESSMENT:{verdict}'
        rows = db.execute(
            'SELECT record_id, signal_refs FROM'
            ' sanders_sentinel_records WHERE scope_ref = ?'
            ' AND subject_ref = ? AND status IN'
            " ('REQUESTED', 'APPROVED')",
            (BLOODLINE_GOVERNANCE_SCOPE, document_ref)).fetchall()
        for row in rows:
            if signal in json.loads(row['signal_refs']):
                return row['record_id']
        return None

    def verify_bloodline_records(self, actor, *, region=None):
        """Run one bloodline governance verification cycle
        (operator only): assess every watched document against
        its paired `.pbd.json` manifest, record each
        assessment as a durable receipted check, and raise a
        finding watch record for every required document that
        does not assess sound. Detect and escalate only: the
        cycle amends, restores, and repairs nothing, and a
        finding is a record placed before a human operator."""
        self._geo(region)
        self._require_operator(actor)
        if self._repo_root is None:
            raise SandersSentinelDenied(
                'Bloodline governance coverage is not bound to'
                ' a repository root')
        assessments = []
        for entry in BLOODLINE_WATCH_SET:
            document = entry['document']
            if not entry['required'] and not (
                    self._repo_root / document).is_file():
                assessments.append({
                    'entry': entry, 'verdict': None,
                    'state': 'NOT_LANDED',
                    'payload_hash_observed': None,
                    'payload_hash_recorded': None,
                    'manifest': document + '.pbd.json'})
                continue
            result = assess_pair(self._repo_root, document)
            assessments.append({
                'entry': entry, 'verdict': result['verdict'],
                'state': ('SOUND' if result['verdict']
                          in BLOODLINE_SOUND_VERDICTS
                          else 'FINDING'),
                'payload_hash_observed':
                    result['payload_hash_observed'],
                'payload_hash_recorded':
                    result['payload_hash_recorded'],
                'manifest': result['manifest']})
        now = self._now()
        cycle_id = f'bloodline-cycle-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                for item in assessments:
                    entry = item['entry']
                    finding_record_id = None
                    if item['state'] == 'FINDING':
                        finding_record_id = \
                            self._open_bloodline_finding(
                                db, entry['document'],
                                item['verdict'])
                        if finding_record_id is None:
                            finding_record_id = (
                                'sentinel-record-'
                                f"{uuid.uuid4().hex[:16]}")
                            signals = [
                                'BLOODLINE_GOVERNANCE_ASSESSMENT:'
                                f"{item['verdict']}"]
                            receipt_id = self._record(
                                'SANDERS_SENTINEL_BLOODLINE_FINDING',
                                actor=actor, cycle_id=cycle_id,
                                record_id=finding_record_id,
                                document_ref=entry['document'],
                                verdict=item['verdict'])
                            db.execute(
                                'INSERT INTO'
                                ' sanders_sentinel_records'
                                ' (record_id, subject_ref,'
                                ' signal_refs, signal_count,'
                                ' scope_ref, status, outcome,'
                                ' evidence_ref, requested_by,'
                                ' requested_at, updated_by,'
                                ' updated_at, receipt_id) VALUES'
                                ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,'
                                ' ?, ?, ?)',
                                (finding_record_id,
                                 entry['document'],
                                 json.dumps(signals), len(signals),
                                 BLOODLINE_GOVERNANCE_SCOPE,
                                 'REQUESTED', None, None, actor,
                                 now, actor, now, receipt_id))
                    check_id = ('bloodline-check-'
                                f"{uuid.uuid4().hex[:16]}")
                    receipt_id = self._record(
                        'SANDERS_SENTINEL_BLOODLINE_CHECK',
                        actor=actor, cycle_id=cycle_id,
                        check_id=check_id,
                        document_ref=entry['document'],
                        state=item['state'],
                        verdict=item['verdict'])
                    db.execute(
                        'INSERT INTO'
                        ' sanders_sentinel_bloodline_checks'
                        ' (check_id, cycle_id, document_ref,'
                        ' manifest_ref, required, state, verdict,'
                        ' payload_hash_observed,'
                        ' payload_hash_recorded,'
                        ' finding_record_id, checked_by,'
                        ' checked_at, receipt_id) VALUES'
                        ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (check_id, cycle_id, entry['document'],
                         item['manifest'],
                         1 if entry['required'] else 0,
                         item['state'], item['verdict'],
                         item['payload_hash_observed'],
                         item['payload_hash_recorded'],
                         finding_record_id, actor, now,
                         receipt_id))
                db.commit()
            except Exception:
                db.rollback()
                raise
            rows = db.execute(
                'SELECT * FROM sanders_sentinel_bloodline_checks'
                ' WHERE cycle_id = ? ORDER BY document_ref',
                (cycle_id,)).fetchall()
        checks = [self._bloodline_check_view(row) for row in rows]
        return {
            'cycle_id': cycle_id,
            'checked_at': now,
            'checked_by': actor,
            'scope_ref': BLOODLINE_GOVERNANCE_SCOPE,
            'checks': checks,
            'documents_sound': sum(
                1 for c in checks if c['state'] == 'SOUND'),
            'findings_raised': sum(
                1 for c in checks if c['state'] == 'FINDING'),
            'documents_not_landed': sum(
                1 for c in checks if c['state'] == 'NOT_LANDED'),
        }

    def bloodline_coverage(self, actor, role, *, region=None):
        """The current bloodline governance coverage view: the
        latest recorded check for every watched document, and
        the findings still standing open before a human."""
        self._geo(region)
        self._guard_access(actor, role, 'bloodline-coverage',
                           'bloodline coverage view')
        with self._connect() as db:
            latest = []
            for entry in BLOODLINE_WATCH_SET:
                row = db.execute(
                    'SELECT * FROM'
                    ' sanders_sentinel_bloodline_checks'
                    ' WHERE document_ref = ? ORDER BY'
                    ' checked_at DESC, rowid DESC LIMIT 1',
                    (entry['document'],)).fetchone()
                if row is None:
                    latest.append({
                        'document_ref': entry['document'],
                        'manifest_ref':
                            entry['document'] + '.pbd.json',
                        'title': entry['title'],
                        'required': entry['required'],
                        'state': ('NOT_LANDED'
                                  if not entry['required']
                                  else 'NEVER_CHECKED'),
                        'verdict': None, 'checked_at': None,
                        'finding_record_id': None})
                else:
                    view = self._bloodline_check_view(row)
                    view['title'] = entry['title']
                    latest.append(view)
            checks_total = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' sanders_sentinel_bloodline_checks'
            ).fetchone()['n']
            cycles_total = db.execute(
                'SELECT COUNT(DISTINCT cycle_id) AS n FROM'
                ' sanders_sentinel_bloodline_checks'
            ).fetchone()['n']
            findings_open = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' sanders_sentinel_records WHERE scope_ref = ?'
                " AND status IN ('REQUESTED', 'APPROVED')",
                (BLOODLINE_GOVERNANCE_SCOPE,)).fetchone()['n']
        return {
            'design': self.bloodline_design_view(),
            'bound_to_repository_root':
                self._repo_root is not None,
            'latest_checks': latest,
            'checks_total': checks_total,
            'cycles_total': cycles_total,
            'findings_open': findings_open,
        }

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_sentinel_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_sentinel_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_sentinel_records'
                ' WHERE signal_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(signal_count), 0) AS n'
                ' FROM sanders_sentinel_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
            bloodline_checks_total = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' sanders_sentinel_bloodline_checks'
            ).fetchone()['n']
            bloodline_latest_states = {}
            for entry in BLOODLINE_WATCH_SET:
                row = db.execute(
                    'SELECT state FROM'
                    ' sanders_sentinel_bloodline_checks'
                    ' WHERE document_ref = ? ORDER BY'
                    ' checked_at DESC, rowid DESC LIMIT 1',
                    (entry['document'],)).fetchone()
                bloodline_latest_states[entry['document']] = (
                    row['state'] if row is not None
                    else ('NOT_LANDED' if not entry['required']
                          else 'NEVER_CHECKED'))
            bloodline_findings_open = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' sanders_sentinel_records WHERE scope_ref = ?'
                " AND status IN ('REQUESTED', 'APPROVED')",
                (BLOODLINE_GOVERNANCE_SCOPE,)).fetchone()['n']
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'bloodline_coverage': {
                'founder_ruling':
                    FOUNDER_RULING_BLOODLINE_PROTECTION,
                'bound_to_repository_root':
                    self._repo_root is not None,
                'documents_watched': len(BLOODLINE_WATCH_SET),
                'checks_total': bloodline_checks_total,
                'latest_states': bloodline_latest_states,
                'findings_open': bloodline_findings_open,
            },
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_signals_submitted': no_signals,
            'signals_declared_total': signals_total,
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
                    raise SandersSentinelDenied(str(exc)) from exc
                self._record('SANDERS_SENTINEL_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
