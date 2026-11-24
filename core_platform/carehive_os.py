"""
Module: core_platform.carehive_os
Architectural Layer: CareHive OS — Supervisory Sidecar (RECONSTRUCTED)
Description: A supervisory-sidecar service implementing the
DOCUMENTED CareHive OS architecture as local, honest mechanics:
supervised subjects with asserted claims, hash-chained cryptographic
evidence, independent challenge (a cycle verdict derived from the
evidence/postcondition record, never from the claim itself),
postcondition verification, and the evergreen
current/candidate/previous-known-good/recovery upgrade cycle.

RECOVERED vs REBUILT — the discipline is absolute:

* RECOVERED = the documentary record only: the platform identity
  below, the October 4, 2026 disclosure's architecture requirements
  at summary level (as recorded in
  docs/SANDERS_SYNTHETIC_AI_SIDECAR_ORIGINAL_ARCHITECTURE.md), the
  recorded dates, and the inventor/applicant context (inventor
  Roosevelt Sanders III; applicant context Sanders Home Healthcare
  & Caregivers LLC). This is documentary recovery only.
* REBUILT = every executable mechanism in this module, built
  2026-11-24 from those documented requirements. Nothing here is
  original CareHive OS code.
* NOT claimed: that this module is, or connects to, the original
  CareHive OS deployment. That deployment remains unauthenticated;
  the owner's Library inventory files
  (CAREHIVEOS-COMPLETE-INVENTORY.md and
  CAREHIVEOS-COMPLETE-INVENTORY(3).md) remain unlocated. No patent
  filing or grant is claimed: the October 2026 disclosure is a
  drafting package, not evidence of a patent filing or grant.

Name-form note: the October 2026 records use 'CareHiveOS' and
'CareHiveOS L15 Synthetic AI Sidecar'; the platform name
'CareHive OS' is the owner's (directive 2026-11-24).

Fail-closed throughout, on the rooms discipline: a Glass-Box audit
adapter is required at construction (no record, no action); every
mutation runs under BEGIN IMMEDIATE with state re-validated inside
the lock; every Glass-Box receipt is written inside the critical
section, before commit — a receipt failure rolls back and changes
nothing; operator-only operations check operator_verifier(actor),
and an absent verifier means denied.
"""

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .rtsa_foundation import (
    PlatformIdentity,
    ensure_checkin_schema,
    latest_check_in as _foundation_latest_check_in,
    record_check_in as _foundation_record_check_in,
    validate_identity,
)

# -- identity (RECOVERED documentary record) -------------------------

PLATFORM_ID = 'carehive_os'
PLATFORM_NAME = 'CareHive OS'
LEGAL_ENTITIES = (
    'Sanders Home Healthcare & Caregivers LLC',
    'Sanders Senior Living LLC',
)
# No NAICS codes are documented for CareHive OS itself. None are
# invented here.
NAICS_CODES = ()
AUTHORIZED_REGIONS = ('US-CO', 'US-WI')
PLATFORM_STATUS = 'RECONSTRUCTED'

IDENTITY = PlatformIdentity(
    platform_id=PLATFORM_ID,
    name=PLATFORM_NAME,
    legal_entities=LEGAL_ENTITIES,
    naics_codes=NAICS_CODES,
    authorized_regions=AUTHORIZED_REGIONS,
    status=PLATFORM_STATUS,
)

# -- documented architecture (RECOVERED, at summary level) -----------
#
# The nine elements below are the October 4, 2026 disclosure's
# architecture as recorded in the sidecar reconciliation document.
# Each is a design / invention-disclosure requirement. The source
# document's own bound, quoted verbatim: these are "design and
# invention-disclosure requirements, not proof of runtime
# implementation."

DOCUMENTED_ARCHITECTURE_BOUND = (
    'design and invention-disclosure requirements, not proof of '
    'runtime implementation'
)

DOCUMENTED_ARCHITECTURE = (
    {
        'element': 'independent_sidecar_identity',
        'requirement': 'The sidecar carries an independent identity.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'reasoning_verification_dimensions_15',
        'requirement': '15 reasoning/verification dimensions.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'live_state_causal_graph',
        'requirement': 'A live state/causal graph.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'bounded_autonomous_supervision',
        'requirement': 'Bounded autonomous supervision.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'simulation',
        'requirement': 'Simulation.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'independent_challenge',
        'requirement': 'Independent challenge.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'postcondition_verification',
        'requirement': 'Postcondition verification.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'cryptographic_evidence',
        'requirement': 'Cryptographic evidence.',
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
    {
        'element': 'evergreen_upgrade_cycle',
        'requirement': (
            'An evergreen current/candidate/previous-known-good/'
            'recovery upgrade cycle.'),
        'status': 'DESIGN_REQUIREMENT_NOT_RUNTIME_PROOF',
    },
)

DISCLOSURE_RECORD = {
    'subject_name_forms': ('CareHiveOS', 'CareHiveOS L15 Synthetic AI Sidecar'),
    'disclosure_date': '2026-10-04',
    'inventor': 'Roosevelt Sanders III',
    'applicant_context': 'Sanders Home Healthcare & Caregivers LLC',
    'nature': (
        'A drafting package, not evidence of a patent filing or '
        'grant. No patent filing or grant is claimed.'),
    'bound': DOCUMENTED_ARCHITECTURE_BOUND,
}

# -- interop interfaces (DOCUMENTED INTERFACE DEFINITIONS) -----------
#
# From the recovery dossier's derived-inventory record. Every entry's
# status is DOCUMENTED_INTERFACE_NOT_CONNECTED: no external system
# is connected; interface declarations do not establish active
# connections (the source inventory's own caveat). validate_envelope
# performs LOCAL shape validation of synthetic payloads only.

INTEROP_STATUS = 'DOCUMENTED_INTERFACE_NOT_CONNECTED'

INTEROP_INTERFACES = {
    'FHIR_R4': {
        'family': 'FHIR R4',
        'status': INTEROP_STATUS,
        'envelope': ('resourceType',),
    },
    'HL7_V2': {
        'family': 'HL7 v2',
        'status': INTEROP_STATUS,
        'envelope': ('message_type', 'segments'),
    },
    'X12_837P': {
        'family': 'X12 837P',
        'status': INTEROP_STATUS,
        'envelope': ('transaction', 'sender_id', 'receiver_id'),
        'transaction': '837P',
    },
    'X12_835': {
        'family': 'X12 835',
        'status': INTEROP_STATUS,
        'envelope': ('transaction', 'sender_id', 'receiver_id'),
        'transaction': '835',
    },
    'X12_270_271': {
        'family': 'X12 270/271',
        'status': INTEROP_STATUS,
        'envelope': ('transaction', 'sender_id', 'receiver_id'),
        'transactions': ('270', '271'),
    },
    'X12_276_277': {
        'family': 'X12 276/277',
        'status': INTEROP_STATUS,
        'envelope': ('transaction', 'sender_id', 'receiver_id'),
        'transactions': ('276', '277'),
    },
    'CDA_CCD': {
        'family': 'CDA/CCD',
        'status': INTEROP_STATUS,
        'envelope': ('document_type',),
        'document_types': ('CDA', 'CCD'),
    },
}

VERSION_STATES = frozenset((
    'CANDIDATE', 'CURRENT', 'PREVIOUS_KNOWN_GOOD', 'RECOVERY',
))

_GENESIS_HASH = '0' * 64


class CareHiveDenied(ValueError):
    """The requested CareHive OS operation is invalid or cannot be
    evidenced, so it does not occur."""


class CareHiveForbidden(ValueError):
    """The actor lacks authority for this CareHive OS operation."""


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False)


def _entry_hash(prev_hash, subject_id, kind, payload, created_at):
    canonical = _canonical({
        'subject_id': subject_id,
        'kind': kind,
        'payload': payload,
        'created_at': created_at,
    })
    return hashlib.sha256(
        (prev_hash + canonical).encode('utf-8')).hexdigest()


class CareHiveSidecar:
    """Supervisory sidecar for CareHive OS (REBUILT mechanics over
    the RECOVERED documented architecture)."""

    def __init__(self, database, operator_verifier=None, audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise CareHiveDenied(
                'A Glass-Box audit adapter is required: no record, no action')
        validate_identity(IDENTITY)
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.identity = IDENTITY
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS supervised_subjects (
                subject_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status_claim TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS evidence_entries (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS supervision_cycles (
                cycle_id TEXT PRIMARY KEY,
                run_by TEXT NOT NULL,
                started_at INTEGER NOT NULL,
                finished_at INTEGER,
                summary TEXT
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS postconditions (
                subject_id TEXT NOT NULL,
                postcondition TEXT NOT NULL,
                observed_state TEXT NOT NULL,
                result TEXT NOT NULL,
                verified_by TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS versions (
                version_label TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
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

    @staticmethod
    def _check_actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise CareHiveDenied('A non-empty actor is required')

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise CareHiveForbidden('Operator authority required')

    @staticmethod
    def _check_text(value, label):
        if not isinstance(value, str) or not value.strip():
            raise CareHiveDenied(f'A non-empty {label} is required')
        return value.strip()

    def _record(self, stage, **fields):
        """Write one Glass-Box receipt. Called only inside a critical
        section, before commit: if this raises, the caller rolls
        back and nothing changes."""
        try:
            return self.audit.preserve(stage, **fields)
        except Exception as exc:
            raise CareHiveDenied(
                f'Glass-Box receipt {stage} could not be preserved: '
                'no record, no action') from exc

    def _subject_row(self, db, subject_id):
        return db.execute(
            "SELECT * FROM supervised_subjects WHERE subject_id = ?;",
            (subject_id,)).fetchone()

    # -- subjects ------------------------------------------------------

    def register_subject(self, actor, subject_id, kind, status_claim):
        """Register a supervised subject (operator-only). The
        status_claim is the subject's asserted state; a duplicate
        subject_id is denied."""
        self._require_operator(actor)
        subject_id = self._check_text(subject_id, 'subject_id')
        kind = self._check_text(kind, 'kind')
        status_claim = self._check_text(status_claim, 'status_claim')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                if self._subject_row(db, subject_id) is not None:
                    raise CareHiveDenied(
                        f'Subject already registered: {subject_id}')
                db.execute(
                    "INSERT INTO supervised_subjects (subject_id, kind, "
                    "status_claim, created_by, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (subject_id, kind, status_claim, actor, now, now))
                self._record('CAREHIVE_SUBJECT_REGISTERED', actor=actor,
                             subject_id=subject_id, kind=kind,
                             status_claim=status_claim)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'subject_id': subject_id, 'kind': kind,
                'status_claim': status_claim, 'created_by': actor,
                'created_at': now, 'updated_at': now}

    def update_claim(self, actor, subject_id, status_claim):
        """Update a subject's asserted claim (operator-only). The
        sidecar never edits a claim during a supervision cycle —
        challenge is independent of the claim."""
        self._require_operator(actor)
        subject_id = self._check_text(subject_id, 'subject_id')
        status_claim = self._check_text(status_claim, 'status_claim')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                if self._subject_row(db, subject_id) is None:
                    raise CareHiveDenied(f'Unknown subject: {subject_id}')
                db.execute(
                    "UPDATE supervised_subjects SET status_claim = ?, "
                    "updated_at = ? WHERE subject_id = ?;",
                    (status_claim, now, subject_id))
                self._record('CAREHIVE_CLAIM_UPDATED', actor=actor,
                             subject_id=subject_id,
                             status_claim=status_claim)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'subject_id': subject_id, 'status_claim': status_claim,
                'updated_at': now}

    def get_subject(self, subject_id):
        with self._connect() as db:
            row = self._subject_row(db, subject_id)
            if row is None:
                return None
            return {key: row[key] for key in row.keys()}

    # -- evidence ------------------------------------------------------

    def append_evidence(self, actor, subject_id, kind, payload):
        """Append one hash-chained evidence entry for a subject (any
        non-empty actor). The chained entry AND its Glass-Box
        receipt CAREHIVE_EVIDENCE_APPENDED are written inside the
        critical section: a receipt failure rolls back and nothing
        is appended."""
        self._check_actor(actor)
        subject_id = self._check_text(subject_id, 'subject_id')
        kind = self._check_text(kind, 'kind')
        if payload is None:
            raise CareHiveDenied('An evidence payload is required')
        payload_text = payload if isinstance(payload, str) else _canonical(payload)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                if self._subject_row(db, subject_id) is None:
                    raise CareHiveDenied(f'Unknown subject: {subject_id}')
                last = db.execute(
                    "SELECT hash FROM evidence_entries "
                    "ORDER BY seq DESC LIMIT 1;").fetchone()
                prev_hash = last['hash'] if last is not None else _GENESIS_HASH
                entry_hash = _entry_hash(
                    prev_hash, subject_id, kind, payload_text, now)
                cursor = db.execute(
                    "INSERT INTO evidence_entries (subject_id, kind, "
                    "payload, prev_hash, hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (subject_id, kind, payload_text, prev_hash,
                     entry_hash, now))
                seq = cursor.lastrowid
                self._record('CAREHIVE_EVIDENCE_APPENDED', actor=actor,
                             subject_id=subject_id, kind=kind, seq=seq,
                             hash=entry_hash)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'seq': seq, 'subject_id': subject_id, 'kind': kind,
                'payload': payload_text, 'prev_hash': prev_hash,
                'hash': entry_hash, 'created_at': now}

    def verify_evidence_chain(self):
        """Recompute the full hash chain; True only if every link
        and every entry hash recomputes exactly."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM evidence_entries ORDER BY seq ASC;"
            ).fetchall()
        prev_hash = _GENESIS_HASH
        for row in rows:
            if row['prev_hash'] != prev_hash:
                return False
            if _entry_hash(row['prev_hash'], row['subject_id'],
                           row['kind'], row['payload'],
                           row['created_at']) != row['hash']:
                return False
            prev_hash = row['hash']
        return True

    # -- postconditions --------------------------------------------------

    def verify_postcondition(self, actor, subject_id, postcondition,
                             observed_state):
        """Verify one postcondition (operator-only): result is
        'PASS' iff observed_state == postcondition, else 'FAIL'.
        Recorded, with receipt CAREHIVE_POSTCONDITION."""
        self._require_operator(actor)
        subject_id = self._check_text(subject_id, 'subject_id')
        postcondition = self._check_text(postcondition, 'postcondition')
        observed_state = self._check_text(observed_state, 'observed_state')
        result = 'PASS' if observed_state == postcondition else 'FAIL'
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                if self._subject_row(db, subject_id) is None:
                    raise CareHiveDenied(f'Unknown subject: {subject_id}')
                db.execute(
                    "INSERT INTO postconditions (subject_id, "
                    "postcondition, observed_state, result, verified_by, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?);",
                    (subject_id, postcondition, observed_state, result,
                     actor, now))
                self._record('CAREHIVE_POSTCONDITION', actor=actor,
                             subject_id=subject_id,
                             postcondition=postcondition,
                             observed_state=observed_state, result=result)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'subject_id': subject_id, 'postcondition': postcondition,
                'observed_state': observed_state, 'result': result,
                'verified_by': actor, 'created_at': now}

    def _latest_postcondition(self, db, subject_id):
        return db.execute(
            "SELECT * FROM postconditions WHERE subject_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1;",
            (subject_id,)).fetchone()

    # -- supervision cycle ------------------------------------------------

    def run_cycle(self, actor):
        """Run one bounded supervision cycle (operator-only).

        For every subject, bounded supervision reads the claim; the
        INDEPENDENT CHALLENGE re-derives the subject's state from
        its own evidence record: the verdict is 'AGREES' iff the
        subject's status_claim equals the observed_state of its
        LATEST postcondition record AND that postcondition's result
        is 'PASS'; 'DISAGREES' otherwise — including no postcondition
        on record (an unverified claim never agrees). The challenge
        is computed from the evidence/postcondition tables, never
        from the claim itself. One receipt, CAREHIVE_CYCLE_RUN,
        carries the verdict map."""
        self._require_operator(actor)
        started = int(time.time())
        cycle_id = 'cycle-' + secrets.token_urlsafe(12)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                subjects = db.execute(
                    "SELECT * FROM supervised_subjects "
                    "ORDER BY subject_id;").fetchall()
                verdicts = {}
                for subject in subjects:
                    latest = self._latest_postcondition(
                        db, subject['subject_id'])
                    if (latest is not None
                            and latest['result'] == 'PASS'
                            and subject['status_claim']
                            == latest['observed_state']):
                        verdicts[subject['subject_id']] = 'AGREES'
                    else:
                        verdicts[subject['subject_id']] = 'DISAGREES'
                finished = int(time.time())
                summary = {
                    'cycle_id': cycle_id,
                    'run_by': actor,
                    'started_at': started,
                    'finished_at': finished,
                    'subject_count': len(subjects),
                    'verdicts': verdicts,
                }
                db.execute(
                    "INSERT INTO supervision_cycles (cycle_id, run_by, "
                    "started_at, finished_at, summary) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (cycle_id, actor, started, finished,
                     _canonical(summary)))
                self._record('CAREHIVE_CYCLE_RUN', actor=actor,
                             cycle_id=cycle_id, verdicts=verdicts,
                             subject_count=len(subjects))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return summary

    # -- evergreen upgrade cycle -------------------------------------------

    def propose_version(self, actor, version_label):
        """Propose a version as CANDIDATE (operator-only). A
        duplicate label is denied, and a second live CANDIDATE is
        denied — one candidate at a time, bounded."""
        self._require_operator(actor)
        version_label = self._check_text(version_label, 'version_label')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                existing = db.execute(
                    "SELECT * FROM versions WHERE version_label = ?;",
                    (version_label,)).fetchone()
                if existing is not None:
                    raise CareHiveDenied(
                        f'Version already exists: {version_label}')
                live = db.execute(
                    "SELECT version_label FROM versions "
                    "WHERE state = 'CANDIDATE';").fetchone()
                if live is not None:
                    raise CareHiveDenied(
                        'A candidate is already live: '
                        f"{live['version_label']}")
                db.execute(
                    "INSERT INTO versions (version_label, state, "
                    "created_at, updated_at) VALUES (?, 'CANDIDATE', ?, ?);",
                    (version_label, now, now))
                self._record('CAREHIVE_VERSION_PROPOSED', actor=actor,
                             version_label=version_label)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'version_label': version_label, 'state': 'CANDIDATE',
                'created_at': now, 'updated_at': now}

    def promote_version(self, actor, version_label):
        """Promote a CANDIDATE to CURRENT (operator-only). Requires
        state CANDIDATE and a PASS postcondition whose subject_id ==
        version_label (the candidate verified as a subject). On
        promote: the existing CURRENT (if any) becomes
        PREVIOUS_KNOWN_GOOD, and any prior PREVIOUS_KNOWN_GOOD
        becomes RECOVERY. Receipt CAREHIVE_VERSION_PROMOTED."""
        self._require_operator(actor)
        version_label = self._check_text(version_label, 'version_label')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = db.execute(
                    "SELECT * FROM versions WHERE version_label = ?;",
                    (version_label,)).fetchone()
                if row is None:
                    raise CareHiveDenied(
                        f'Unknown version: {version_label}')
                if row['state'] != 'CANDIDATE':
                    raise CareHiveDenied(
                        f"Version {version_label} is {row['state']}, "
                        'not CANDIDATE')
                passed = db.execute(
                    "SELECT 1 FROM postconditions WHERE subject_id = ? "
                    "AND result = 'PASS' LIMIT 1;",
                    (version_label,)).fetchone()
                if passed is None:
                    raise CareHiveDenied(
                        f'Version {version_label} has no PASS '
                        'postcondition on record')
                db.execute(
                    "UPDATE versions SET state = 'RECOVERY', "
                    "updated_at = ? WHERE state = 'PREVIOUS_KNOWN_GOOD';",
                    (now,))
                db.execute(
                    "UPDATE versions SET state = 'PREVIOUS_KNOWN_GOOD', "
                    "updated_at = ? WHERE state = 'CURRENT';", (now,))
                db.execute(
                    "UPDATE versions SET state = 'CURRENT', "
                    "updated_at = ? WHERE version_label = ?;",
                    (now, version_label))
                self._record('CAREHIVE_VERSION_PROMOTED', actor=actor,
                             version_label=version_label)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'version_label': version_label, 'state': 'CURRENT',
                'updated_at': now}

    def rollback_version(self, actor):
        """Roll back (operator-only): the PREVIOUS_KNOWN_GOOD becomes
        CURRENT and the displaced CURRENT becomes RECOVERY. Requires
        a PREVIOUS_KNOWN_GOOD. Receipt CAREHIVE_VERSION_ROLLED_BACK."""
        self._require_operator(actor)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                pkg = db.execute(
                    "SELECT * FROM versions "
                    "WHERE state = 'PREVIOUS_KNOWN_GOOD';").fetchone()
                if pkg is None:
                    raise CareHiveDenied(
                        'No PREVIOUS_KNOWN_GOOD version to roll back to')
                current = db.execute(
                    "SELECT * FROM versions WHERE state = 'CURRENT';"
                ).fetchone()
                if current is not None:
                    db.execute(
                        "UPDATE versions SET state = 'RECOVERY', "
                        "updated_at = ? WHERE version_label = ?;",
                        (now, current['version_label']))
                db.execute(
                    "UPDATE versions SET state = 'CURRENT', "
                    "updated_at = ? WHERE version_label = ?;",
                    (now, pkg['version_label']))
                self._record(
                    'CAREHIVE_VERSION_ROLLED_BACK', actor=actor,
                    restored_version=pkg['version_label'],
                    displaced_version=(
                        current['version_label'] if current else None))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'restored_version': pkg['version_label'],
                'displaced_version': (
                    current['version_label'] if current else None),
                'state': 'CURRENT', 'updated_at': now}

    def version_states(self):
        with self._connect() as db:
            rows = db.execute(
                "SELECT version_label, state FROM versions "
                "ORDER BY version_label;").fetchall()
        return {row['version_label']: row['state'] for row in rows}

    # -- interop envelope validation (local, synthetic only) ----------------

    def validate_envelope(self, interface_id, payload):
        """LOCAL shape validation of a synthetic payload against a
        DOCUMENTED INTERFACE DEFINITION. No external system is
        connected; interface declarations do not establish active
        connections. Unknown interface -> CareHiveDenied."""
        if interface_id not in INTEROP_INTERFACES:
            raise CareHiveDenied(f'Unknown interface: {interface_id!r}')
        if not isinstance(payload, dict):
            return {'valid': False,
                    'errors': ['payload must be an object']}
        errors = []

        def need(field):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{field} must be a non-empty string')

        if interface_id == 'FHIR_R4':
            need('resourceType')
        elif interface_id == 'HL7_V2':
            need('message_type')
            segments = payload.get('segments')
            if (not isinstance(segments, list) or not segments
                    or any(not isinstance(s, str) or not s.strip()
                           for s in segments)):
                errors.append(
                    'segments must be a non-empty list of strings')
        elif interface_id in ('X12_837P', 'X12_835'):
            expected = INTEROP_INTERFACES[interface_id]['transaction']
            if payload.get('transaction') != expected:
                errors.append(f"transaction must be '{expected}'")
            need('sender_id')
            need('receiver_id')
        elif interface_id in ('X12_270_271', 'X12_276_277'):
            allowed = INTEROP_INTERFACES[interface_id]['transactions']
            if payload.get('transaction') not in allowed:
                errors.append(
                    f'transaction must be one of {list(allowed)}')
            need('sender_id')
            need('receiver_id')
        elif interface_id == 'CDA_CCD':
            if payload.get('document_type') not in ('CDA', 'CCD'):
                errors.append("document_type must be 'CDA' or 'CCD'")
        return {'valid': not errors, 'errors': errors}

    # -- check-in and status -------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), via the
        shared foundation helper, with receipt CAREHIVE_CHECK_IN
        inside the critical section."""
        self._require_operator(actor)
        deployment_location = self._check_text(
            deployment_location, 'deployment_location')
        operational_status = self._check_text(
            operational_status, 'operational_status')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                record = _foundation_record_check_in(
                    db, IDENTITY, deployment_location, operational_status)
                self._record('CAREHIVE_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except CareHiveDenied:
                db.rollback()
                raise
            except Exception as exc:
                db.rollback()
                raise CareHiveDenied(str(exc)) from exc
        return record

    def latest_check_in(self):
        with self._connect() as db:
            return _foundation_latest_check_in(db, PLATFORM_ID)

    def status(self):
        with self._connect() as db:
            subject_count = db.execute(
                "SELECT COUNT(*) AS n FROM supervised_subjects;"
            ).fetchone()['n']
            last_cycle = db.execute(
                "SELECT summary FROM supervision_cycles "
                "ORDER BY started_at DESC, rowid DESC LIMIT 1;"
            ).fetchone()
            versions = {row['version_label']: row['state'] for row in
                        db.execute(
                            "SELECT version_label, state FROM versions "
                            "ORDER BY version_label;").fetchall()}
        return {
            'identity': IDENTITY.to_dict(),
            'identity_digest': IDENTITY.integrity_digest(),
            'status': PLATFORM_STATUS,
            'subject_count': subject_count,
            'last_cycle': (json.loads(last_cycle['summary'])
                           if last_cycle is not None else None),
            'evidence_chain_valid': self.verify_evidence_chain(),
            'versions': versions,
            'interop_interfaces': [
                {'interface_id': interface_id,
                 'family': spec['family'],
                 'status': spec['status']}
                for interface_id, spec in INTEROP_INTERFACES.items()
            ],
            'documented_architecture': list(DOCUMENTED_ARCHITECTURE),
            'disclosure': dict(DISCLOSURE_RECORD),
        }
