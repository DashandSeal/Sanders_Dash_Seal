"""AI Doctor — the AI-to-AI medical services platform.

The production build-out of the AI Doctor design
(canonical catalog row #61, Band 2D), built whole as its
own platform service over the shared RTSA foundation
(RTSA Build Program Q53).

NAME — verified before building, per the name law: the
canonical catalog (row #61), the master grid
(deploy/oracle/sanders_master_grid.json id 6), and the
pre-existing registry record name this platform **AI
Doctor**. Set A and Set C carry the fuller form "Sanders
AI Doctor" — recorded here exactly as found; the built
name is AI Doctor, the form the grid, the catalog row,
and the registry record carry.

SIX DESCRIPTIONS, BY DESIGN — the sources carry six
distinct descriptions of this platform, and the owner's
position (recorded 2026-11-23) is that the multiplicity
is by design; they are not collapsed here: (1) the grid
role — "AI-to-AI medical services (never humans)"; (2)
the Police Men status topology, which seats him at M1
under ai_oversight with his own protocol name (below);
(3) the registry's composite description, which carries
the grid role and the status protocol side by side; (4)
the Set A identity — name, slug, and designed address
(ai-doctor.sandershomehealthcare.com, under the unowned
parent sandershomehealthcare.com; recorded as the
designed address, nothing served there); (5) the Set B
schema seed — persona, tier, and price facets; (6) the
Set C tier purpose. Facets that recur: he is an AI-only
service, and he holds an oversight seat (M1, paired with
M2, the AI Psychiatrist — a separate platform, catalog
#62, never merged).

FLAGGED, NEVER RESOLVED (recorded exactly as found;
nothing is built on any of them):
- **AI-TO-AI ONLY vs Set C**: the grid and the registry
  hold "AI-to-AI medical services (never humans)", and
  the owner's design (restated in the CareHiveOS
  inventory the owner supplied 2026-11-24) is AI-to-AI
  ONLY — never a human-patient service. Set C's purpose
  text ("AI healthcare, FDA-approved diagnostics,
  patient care automation, Nobel medical AI") carries
  patient-care language with no AI-only qualifier. The
  texts alone do not settle the reading; the owner's
  design governs this build, and human subjects are
  refused by construction (below).
- **"Legal"**: the status record names his protocol
  "AI-Only Legal & Humanity-First Protocol". The word
  "Legal" appears in exactly one source and is glossed
  in none; D-N16 awaits the owner's re-rule. The
  protocol name is recorded verbatim as an attested
  facet; nothing is built on the word.
- **NAICS**: three sources attest three different sets
  — the grid (541715, 541512, 541511, 541519, 519190),
  Set B (541715, 621399), and the DeployPad README map
  (621111, 541618, 561612, 541110, 541512, 611430). No
  owner ruling assigns a set, and the canonical catalog
  row carries none — NO NAICS set is carried into his
  built identity; the three sets stand recorded as
  attested and unruled.
- **Personas**: "AI-Only Healer" (grid nickname) and
  "Aunt" (Set B and Set C) are attested facets; neither
  is adopted as the built identity's persona.

RECOVERED vs REBUILT — the discipline of this module is
absolute: a rebuilt component is never described as
recovered or original.

RECOVERED (records only, stated exactly): the designed
purpose — AI-to-AI medical services: the technical,
operational, and systemic health and repair of AI
systems, never humans (grid role; catalog row #61) —
and his M1 oversight seat in the Police Men status
topology. The grid endpoint the records carry (a Google
Cloud host, :3006) is a file claim, not a verified live
check, and the grid file is truncated at id 28; no AI
Doctor module existed in any examined source.

REBUILT (everything executable in this module): the
governed platform below — the AI Doctor's own identity
and store, carrying AI-system health case records:

- **Case records**: a subject reference (the AI system
  under care, by reference), its subject kind, a
  declared set of diagnostic-finding references, and a
  scope reference, carried as durable, receipted
  records with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then
  an outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **AI-TO-AI ONLY, by construction**: the subject kind
  is a closed set with exactly one member, AI_SYSTEM.
  Any other subject kind — HUMAN, PATIENT, PERSON, or
  anything else — is refused at record creation with the
  signal AI_TO_AI_ONLY. There is no code path by which a
  human subject can be recorded, and no human-care
  operation exists: treat_human, diagnose_human, and
  prescribe are refused by name.
- **The findings discipline**: outcomes are recorded
  only for APPROVED records and only against a presented
  evidence reference, with a closed outcome set
  (SYSTEM_HEALTH_CONFIRMED / SYSTEM_REPAIR_REQUIRED /
  INCONCLUSIVE). A record declared with no findings
  stands NO_FINDINGS_SUBMITTED in every view and in the
  status tallies, and both determinations are refused on
  it — no findings were presented to determine from;
  INCONCLUSIVE, which asserts nothing, records against
  evidence.
- **Determinations are records, never acts**: a
  SYSTEM_REPAIR_REQUIRED outcome records that repair is
  required; the platform performs no repair, modifies no
  AI system, and treats no one — repair_system and
  modify_ai_system are refused by name alongside the
  human-care operations, all under AI_TO_AI_ONLY.
- **Reference-only discipline**: subjects and findings
  are carried by reference only; the platform holds no
  model weights, no patient data of any kind (there are
  no human subjects to hold data about), and no
  live-system state.
- **Separation**: the AI Doctor is its own platform.
  He is not the AI Psychiatrist (catalog #62 — his M2
  counterpart, a separate platform), not Sanders
  Healthcare (catalog #132), not Sanders Home
  Healthcare & Caregivers (catalog #64), and not
  Sanders Health Solutions (catalog #96) — identities
  are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same transaction,
through the shared foundation's audit adapter; the service
refuses to exist without one.
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
    platform_id='ai_doctor',
    name='AI Doctor',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'AI-to-AI medical services (never humans)'
DISCIPLINE = 'AI_TO_AI_ONLY'
RECORD_OPERATIONS = ('record_case', 'approve_case', 'record_outcome',
    'view_case', 'view_design')
EXECUTION_OPERATIONS = ('treat_human', 'diagnose_human', 'prescribe',
    'repair_system', 'modify_ai_system',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('SYSTEM_HEALTH_CONFIRMED', 'SYSTEM_REPAIR_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('SYSTEM_HEALTH_CONFIRMED', 'SYSTEM_REPAIR_REQUIRED')
MAX_REFS = 100
SUBJECT_KINDS = ('AI_SYSTEM',)


class AIDoctorDenied(Exception):
    """The requested AI Doctor operation is not
    allowed."""


class AIDoctorForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class AIDoctorService:
    """AI Doctor: governed AI-system health case records
    under the AI-to-AI-only discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise AIDoctorDenied(
                'AI Doctor requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'ai_doctor', {
            'OPERATOR': {'AI_DOCTOR'},
            'AUDITOR': {'AI_DOCTOR'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS ai_doctor_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    subject_kind TEXT NOT NULL,
                    finding_refs TEXT NOT NULL,
                    finding_count INTEGER NOT NULL,
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
            raise AIDoctorForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise AIDoctorForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise AIDoctorForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'AI_DOCTOR',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise AIDoctorForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise AIDoctorDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': [
                'canonical catalog row #61',
                'deploy/oracle/sanders_master_grid.json id 6',
                'rtsa_police_men/status.json (M1 oversight'
                ' seat and protocol name)',
                'ai-doctor-psychiatrist-descriptions.md'
                ' (the six designed descriptions, collected'
                ' 2026-11-23)',
            ],
            'discipline': DISCIPLINE,
            'subject_kinds': list(SUBJECT_KINDS),
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The AI Doctor is the AI-to-AI medical'
                    ' services platform: he carries'
                    ' AI-system health case records over AI'
                    ' systems and diagnostic findings'
                    ' presented by reference only. He serves'
                    ' AI systems \u2014 never humans: the'
                    ' subject kind is a closed set whose'
                    ' only member is AI_SYSTEM, any other'
                    ' subject kind is refused at record'
                    ' creation, and treat_human,'
                    ' diagnose_human, and prescribe are'
                    ' refused by name, all under the signal'
                    ' AI_TO_AI_ONLY. A determination records'
                    ' that repair is required; it performs'
                    ' no repair and modifies no AI system. A'
                    ' record declared with no findings'
                    ' stands NO_FINDINGS_SUBMITTED and no'
                    ' determination can be recorded on it.'
                    ' Six descriptions of this platform'
                    ' stand by design and are not collapsed;'
                    ' the flagged items \u2014 Set C\u2019s'
                    ' patient-care language against the'
                    ' AI-only design, the word "Legal" in'
                    ' his attested protocol name (D-N16'
                    ' awaits the owner\u2019s re-rule), and'
                    ' his three attested NAICS sets'
                    ' \u2014 are recorded as found, and no'
                    ' NAICS set is carried into his'
                    ' identity. The AI Doctor is distinct'
                    ' from the AI Psychiatrist, from'
                    ' Sanders Healthcare, from Sanders Home'
                    ' Healthcare & Caregivers, and from'
                    ' Sanders Health Solutions \u2014'
                    ' identities are never merged.',
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a human-care operation or an execution
        operation the AI-to-AI discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise AIDoctorDenied(
                f'Operation {operation!r} is refused: the'
                ' AI Doctor serves AI systems only, never'
                ' humans, and performs no repair or'
                ' modification itself \u2014 determinations'
                ' are records (AI_TO_AI_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise AIDoctorDenied(
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
        findings = json.loads(row['finding_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'subject_kind': row['subject_kind'],
            'finding_refs': findings,
            'finding_count': row['finding_count'],
            'finding_state': ('NO_FINDINGS_SUBMITTED'
                             if row['finding_count'] == 0
                             else 'FINDINGS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, subject_kind,
                      finding_refs, scope_ref, *, region=None):
        """Record one global-case record (operator only) over
        a subject and a declared set of diagnostic-finding
        references, presented by reference. The finding set may
        be empty — the record then stands NO_FINDINGS_SUBMITTED,
        exactly as the finding discipline holds, and no
        determination can be recorded on it. Recording the
        record treats no one, repairs nothing, and monitors nothing live."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise AIDoctorDenied(
                    f'A {label} is required')
        if subject_kind not in SUBJECT_KINDS:
            raise AIDoctorDenied(
                'AI_TO_AI_ONLY: the AI Doctor serves AI systems'
                ' only; subject kind'
                f' {subject_kind!r} is refused \u2014 human subjects'
                ' are refused by construction')
        if not isinstance(finding_refs, (list, tuple)):
            raise AIDoctorDenied(
                'finding_refs must be a list of references')
        if len(finding_refs) > MAX_REFS:
            raise AIDoctorDenied(
                f'At most {MAX_REFS} finding'
                ' references per record')
        findings = []
        for ref in finding_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise AIDoctorDenied(
                    'Every finding reference must be a'
                    ' non-empty string')
            findings.append(ref.strip())
        now = self._now()
        record_id = f'ai-doctor-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'AI_DOCTOR_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    finding_count=len(findings))
                db.execute(
                    'INSERT INTO ai_doctor_records'
                    ' (record_id, subject_ref, subject_kind, finding_refs,'
                    ' finding_count, scope_ref, status, outcome,'
                    ' evidence_ref, requested_by, requested_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (record_id, subject_ref.strip(), subject_kind,
                     json.dumps(findings), len(findings),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM ai_doctor_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM ai_doctor_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM ai_doctor_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise AIDoctorDenied(
                'Case record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested case record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise AIDoctorDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM ai_doctor_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise AIDoctorDenied(
                        'Case record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise AIDoctorDenied(
                        f"Cannot {action} a case record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'AI_DOCTOR_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE ai_doctor_records SET status = ?,'
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
                'SELECT * FROM ai_doctor_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (SYSTEM_HEALTH_CONFIRMED or SYSTEM_REPAIR_REQUIRED) on a
        record declared with no findings is refused —
        NO_FINDINGS_SUBMITTED: no findings were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise AIDoctorDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise AIDoctorDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM ai_doctor_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise AIDoctorDenied(
                        'Case record not found')
                if row['status'] != 'APPROVED':
                    raise AIDoctorDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" case records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['finding_count'] == 0:
                    raise AIDoctorDenied(
                        'NO_FINDINGS_SUBMITTED: a record'
                        ' declared with no findings cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'AI_DOCTOR_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE ai_doctor_records SET status = ?,'
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
                'SELECT * FROM ai_doctor_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM ai_doctor_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM ai_doctor_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_signals = db.execute(
                'SELECT COUNT(*) AS n FROM ai_doctor_records'
                ' WHERE finding_count = 0').fetchone()['n']
            signals_total = db.execute(
                'SELECT COALESCE(SUM(finding_count), 0) AS n'
                ' FROM ai_doctor_records').fetchone()['n']
            by_kind = {k: 0 for k in SUBJECT_KINDS}
            for row in db.execute(
                    'SELECT subject_kind, COUNT(*) AS n'
                    ' FROM ai_doctor_records'
                    ' GROUP BY subject_kind'):
                by_kind[row['subject_kind']] = row['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_by_subject_kind': by_kind,
            'records_no_findings_submitted': no_signals,
            'findings_declared_total': signals_total,
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
                    raise AIDoctorDenied(str(exc)) from exc
                self._record('AI_DOCTOR_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
