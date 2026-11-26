"""Sovereign Shield V3 — the sovereign shield layer, built whole
as its own platform (RTSA Build Program Q19, constructed under
the founder's order of 2026-11-26).

Design of record. Sovereign Shield V3 is catalog #18. Its
recovered foundation is the ``SovereignShieldV3`` class at
``money_factory_legal_aid_v1_668/shield/sovereign_shield_v3.py``
— the shield class used inside Money Factory Legal Aid, left
untouched and in place by this build, exactly as the Labyrinth
Shield and Minotaur builds left their recovered foundations.
The fleet registry of record (``core_platform/ai_platform_
links.json``) records this platform as a local module with no
HTTP endpoint: no public surface and no API surface is designed
for it in any examined source, so this build constructs none —
the platform is reached platform-to-platform, never over HTTP.
The Police Men status of record names the shield layer
"Sovereign Shield V2/V3 Synthetic AI Defense", and the NACI
mapping of record describes this platform as the shield layer
of the Police Men containment envelope. The queue's Q19 entry
held this build on the founder's ruling on the V2 question
(D-N21): no V2 module exists in the repository, V3 is the
module of record, and the founder's order of 2026-11-26 — the
three strongest shields of his design given to Sanders
Sentinel, The Godfather, and Sanders Patriot Saint for their
protection protocols — carries this platform's construction as
its own platform.

What the recovered class does, and what this build carries.
The class's shield functions are chain-of-custody integrity: a
canonical custody record (engine, node, jurisdiction, the
7-continent sovereign baseline, an evidence SHA-256, atomic
timestamps) digested with SHA3-512, and an ML-DSA-65 (NIST
FIPS 204) lattice signature over that record. This service
carries those functions as durable, receipted records on the
shared RTSA foundation: custody records whose SHA3-512 record
digest is computed natively (Python standard library) over
exactly the foundation's canonical form. The ML-DSA-65
signature itself is NOT executed here: the recovered class
performs it through liboqs, a third-party library, and the
native-only law keeps third-party cryptography out of this
platform's path — the signature stands DECLARED in every
custody record, never claimed, until the founder designates
otherwise (the Daedalus precedent for declared-not-implemented
post-quantum scope). The class's remaining function — the
hard-locked retail pricing calculation — is Money Factory
Legal Aid's own pricing design, not a shield function: it
stays in Money Factory's module, untouched, and is not carried
into this platform.

The platform's governed work, beside the custody records:

- **Shield-layer determinations**: determinations over
  presented evidence, by reference — CONTAINMENT_ENVELOPE
  (the shield layer of the Police Men containment envelope)
  and SHIELD_POSTURE (this shield layer's own posture) — with
  the governed lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then a
  determination recorded against a presented evidence
  reference (DETERMINATION_RECORDED) with a closed verdict
  set (SOUND / FINDING / INCONCLUSIVE). A verdict binds only
  to the presented evidence and the scope the record names;
  it opens no other platform's store and changes no other
  platform's state.
- **Self-integrity**: a pin over the recovered foundation
  file and over this service module, so a changed foundation
  or a changed service is detected rather than silently
  trusted (the Labyrinth Shield's integrity discipline).
- **Contract discipline**: the platform's record operations
  are exposed as a view, and an operation check answers —
  fail-closed — whether a named operation is a record
  operation this platform may carry or one it refuses.

No record, no action: every state-changing operation writes
its Glass-Box receipt inside the same transaction, through
the shared foundation's audit adapter; the service refuses
to exist without one.
"""

from __future__ import annotations

import hashlib
import importlib.util
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
    platform_id='sovereign_shield_v3',
    name='Sovereign Shield V3',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The recovered foundation file this service builds out,
# resolved from this module's own location (repository root),
# never from a caller-supplied path. A second copy of the
# class exists inside the Money Factory package directory;
# the fleet registry names this path as the module of record,
# and this path is the one pinned.
FOUNDATION_FILE = (
    Path(__file__).resolve().parent.parent
    / 'money_factory_legal_aid_v1_668' / 'shield'
    / 'sovereign_shield_v3.py')
SERVICE_FILE = Path(__file__).resolve()

# The recovered class's own constants, mirrored so the custody
# records this service keeps speak the foundation's language;
# integrity_status reports whether the loaded foundation's
# constants still match these.
FOUNDATION_ENGINE = 'Money Factory Legal Aid v1.668'
JURISDICTION_BASELINE = '7-CONTINENT_300PLUS_SOVEREIGN_BASELINE'
PQC_ALGORITHM = 'ML-DSA-65'
PQC_STANDARD = 'NIST FIPS 204'
PQC_SIGNATURE_STATE = 'DECLARED_NOT_EXECUTED'

RECORD_OPERATIONS = (
    'record_custody', 'record_determination_request',
    'approve_determination', 'reject_determination',
    'record_determination', 'view_custody',
    'view_determination', 'view_contract', 'pin_integrity',
    'view_integrity',
)
PROHIBITED_OPERATIONS = (
    'external_execution', 'credential_access', 'notarization',
    'legal_filing', 'financial_transfer',
    'production_deployment',
)
DETERMINATION_KINDS = ('CONTAINMENT_ENVELOPE', 'SHIELD_POSTURE')
DETERMINATION_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                          'DETERMINATION_RECORDED')
DETERMINATION_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
DETERMINATION_VERDICTS = ('SOUND', 'FINDING', 'INCONCLUSIVE')


class SovereignShieldV3Denied(Exception):
    """The requested Sovereign Shield V3 operation is not
    allowed."""


class SovereignShieldV3Forbidden(Exception):
    """The actor lacks authority for the requested operation."""


def _load_foundation():
    """Load the recovered foundation module by path, or None.

    The foundation lives outside the ``core_platform`` package;
    loading by path reads its real code without moving or
    copying it. A foundation that cannot be loaded is reported
    by the integrity views, never silently trusted.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            'sovereign_shield_v3_foundation', FOUNDATION_FILE)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


class SovereignShieldV3Service:
    """Sovereign Shield V3: governed custody records and
    shield-layer determinations over the recovered shield
    class, on the shared RTSA foundation."""

    def __init__(self, database_path, *, operator_verifier,
                 audit, clock=time.time):
        if audit is None or not callable(
                getattr(audit, 'preserve', None)):
            raise SovereignShieldV3Denied(
                'Sovereign Shield V3 requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sovereign_shield_v3', {
            'OPERATOR': {'SHIELD'},
            'AUDITOR': {'SHIELD'},
        })
        self._foundation = _load_foundation()
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS ssv3_custody (
                    custody_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    jurisdiction_code TEXT NOT NULL,
                    naics_code TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    payload_ref TEXT NOT NULL,
                    record_sha3_512 TEXT NOT NULL,
                    pqc_algorithm TEXT NOT NULL,
                    pqc_signature_state TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS
                ssv3_determinations (
                    determination_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    evidence_ref TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ssv3_integrity (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    foundation_hash TEXT NOT NULL,
                    service_hash TEXT NOT NULL,
                    pinned_by TEXT NOT NULL,
                    pinned_at REAL NOT NULL,
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
            raise SovereignShieldV3Forbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SovereignShieldV3Forbidden(
                'Operator authority is required for this'
                ' operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SovereignShieldV3Forbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SHIELD', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise SovereignShieldV3Forbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SovereignShieldV3Denied(str(exc)) from exc

    # -- contract -----------------------------------------------------

    @staticmethod
    def contract_view() -> dict:
        return {
            'platform': 'Sovereign Shield V3',
            'catalog_number': 18,
            'build_program_ref': 'Q19',
            'mission': (
                'The sovereign shield layer: chain-of-custody'
                ' integrity records in the recovered shield'
                ' class\u2019s canonical form, and governed'
                ' shield-layer determinations over presented'
                ' evidence \u2014 including the shield layer of'
                ' the Police Men containment envelope.'),
            'foundation': (
                'money_factory_legal_aid_v1_668/shield/'
                'sovereign_shield_v3.py (recovered, untouched)'),
            'jurisdiction_baseline': JURISDICTION_BASELINE,
            'pqc_algorithm': PQC_ALGORITHM,
            'pqc_standard': PQC_STANDARD,
            'pqc_signature_state': PQC_SIGNATURE_STATE,
            'record_operations': list(RECORD_OPERATIONS),
            'prohibited_operations':
                list(PROHIBITED_OPERATIONS),
            'public_surface': None,
            'note': (
                'No HTTP endpoint and no public surface is'
                ' designed for this platform in any examined'
                ' source, and none is built: the platform is'
                ' reached platform-to-platform only. The'
                ' ML-DSA-65 lattice signature of the recovered'
                ' class is performed there through liboqs, a'
                ' third-party library; this service computes'
                ' the custody record\u2019s SHA3-512 digest'
                ' natively and carries the signature as'
                ' DECLARED_NOT_EXECUTED \u2014 declared, never'
                ' claimed. The recovered class\u2019s'
                ' hard-locked pricing calculation is Money'
                ' Factory Legal Aid\u2019s own pricing design,'
                ' not a shield function; it remains in Money'
                ' Factory\u2019s module and is not carried'
                ' here. Sovereign Shield V3 is a separate'
                ' platform from Sanders Labyrinth Shield and'
                ' from LABYRINTH \u2014 the three shields are'
                ' never merged.'),
        }

    def operation_check(self, actor, role, operation, *,
                        region=None):
        """Fail-closed contract check: a named operation is
        either a record operation this platform carries, or it
        is refused — prohibited, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in PROHIBITED_OPERATIONS:
            raise SovereignShieldV3Denied(
                f'Operation {operation!r} is prohibited for'
                ' Sovereign Shield V3')
        if operation not in RECORD_OPERATIONS:
            raise SovereignShieldV3Denied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
        }

    # -- chain-of-custody records -------------------------------------

    @staticmethod
    def _custody_view(row):
        return {
            'custody_id': row['custody_id'],
            'node_id': row['node_id'],
            'jurisdiction_code': row['jurisdiction_code'],
            'jurisdiction_baseline': JURISDICTION_BASELINE,
            'naics_code': row['naics_code'],
            'evidence_sha256': row['evidence_sha256'],
            'payload_ref': row['payload_ref'],
            'record_sha3_512': row['record_sha3_512'],
            'pqc_algorithm': row['pqc_algorithm'],
            'pqc_signature_state': row['pqc_signature_state'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def record_custody(self, actor, node_id, jurisdiction_code,
                       naics_code, evidence_sha256, payload_ref,
                       *, region=None):
        """Record one chain-of-custody entry (operator only).

        The record digest is SHA3-512 over the canonical form
        of the custody record, exactly as the recovered class
        computes it \u2014 the payload itself is carried by
        reference only, never stored. The ML-DSA-65 signature
        is recorded as DECLARED_NOT_EXECUTED: this platform
        does not perform third-party lattice signing.
        """
        self._geo(region)
        self._require_operator(actor)
        for label, value in (
                ('node_id', node_id),
                ('jurisdiction_code', jurisdiction_code),
                ('naics_code', naics_code),
                ('payload_ref', payload_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SovereignShieldV3Denied(
                    f'A {label} is required')
        if not isinstance(evidence_sha256, str) \
                or len(evidence_sha256) != 64 \
                or any(c not in '0123456789abcdef'
                       for c in evidence_sha256.lower()):
            raise SovereignShieldV3Denied(
                'evidence_sha256 must be a valid 64-character'
                ' hex SHA-256 digest')
        evidence_sha256 = evidence_sha256.lower()
        now = self._now()
        canonical_record = {
            'engine': FOUNDATION_ENGINE,
            'node_id': node_id.strip(),
            'jurisdiction_code': jurisdiction_code.strip(),
            'jurisdiction_baseline': JURISDICTION_BASELINE,
            'naics_code': naics_code.strip(),
            'evidence_sha256': evidence_sha256,
            'atomic_timestamp_ns': time.time_ns(),
            'payload_ref': payload_ref.strip(),
        }
        canonical_bytes = json.dumps(
            canonical_record, sort_keys=True,
            separators=(',', ':')).encode('utf-8')
        record_digest = hashlib.sha3_512(
            canonical_bytes).hexdigest()
        custody_id = f'ssv3-coc-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SSV3_CUSTODY_RECORDED', actor=actor,
                    custody_id=custody_id,
                    evidence_sha256=evidence_sha256,
                    record_sha3_512=record_digest)
                db.execute(
                    'INSERT INTO ssv3_custody (custody_id,'
                    ' node_id, jurisdiction_code, naics_code,'
                    ' evidence_sha256, payload_ref,'
                    ' record_sha3_512, pqc_algorithm,'
                    ' pqc_signature_state, recorded_by,'
                    ' recorded_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (custody_id, node_id.strip(),
                     jurisdiction_code.strip(),
                     naics_code.strip(), evidence_sha256,
                     payload_ref.strip(), record_digest,
                     PQC_ALGORITHM, PQC_SIGNATURE_STATE,
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM ssv3_custody WHERE custody_id = ?',
                (custody_id,)).fetchone()
        return self._custody_view(row)

    def custody_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'custody',
                           'custody view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM ssv3_custody'
                ' ORDER BY recorded_at').fetchall()
        return [self._custody_view(row) for row in rows]

    def custody_view(self, actor, role, custody_id, *,
                     region=None):
        self._geo(region)
        self._guard_access(actor, role, custody_id,
                           'custody view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM ssv3_custody WHERE custody_id = ?',
                (custody_id,)).fetchone()
        if row is None:
            raise SovereignShieldV3Denied('Custody record not'
                                          ' found')
        return self._custody_view(row)

    # -- shield-layer determinations -----------------------------------

    @staticmethod
    def _determination_view(row):
        return {
            'determination_id': row['determination_id'],
            'kind': row['kind'],
            'subject_ref': row['subject_ref'],
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_determination(self, actor, kind, subject_ref,
                             scope_ref, *, region=None):
        """Record one shield-layer determination request
        (operator only), over a subject presented by
        reference. Recording it inspects nothing and reaches
        into no live system."""
        self._geo(region)
        self._require_operator(actor)
        if kind not in DETERMINATION_KINDS:
            raise SovereignShieldV3Denied(
                f'Unknown determination kind: {kind!r}')
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SovereignShieldV3Denied(
                    f'A {label} is required')
        now = self._now()
        determination_id = f'ssv3-det-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SSV3_DETERMINATION_RECORDED', actor=actor,
                    determination_id=determination_id, kind=kind,
                    subject_ref=subject_ref.strip())
                db.execute(
                    'INSERT INTO ssv3_determinations'
                    ' (determination_id, kind, subject_ref,'
                    ' scope_ref, status, verdict, evidence_ref,'
                    ' requested_by, requested_at, updated_by,'
                    ' updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (determination_id, kind, subject_ref.strip(),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM ssv3_determinations'
                ' WHERE determination_id = ?',
                (determination_id,)).fetchone()
        return self._determination_view(row)

    def determinations_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'determinations',
                           'determinations view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM ssv3_determinations'
                ' ORDER BY requested_at').fetchall()
        return [self._determination_view(row) for row in rows]

    def determination_view(self, actor, role, determination_id,
                           *, region=None):
        self._geo(region)
        self._guard_access(actor, role, determination_id,
                           'determination view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM ssv3_determinations'
                ' WHERE determination_id = ?',
                (determination_id,)).fetchone()
        if row is None:
            raise SovereignShieldV3Denied(
                'Determination not found')
        return self._determination_view(row)

    def determination_action(self, actor, determination_id,
                             action, *, region=None):
        """Approve or reject one requested determination
        (operator only) \u2014 the recorded human decision.
        Approval approves the RECORD; it executes nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = DETERMINATION_TRANSITIONS.get(action)
        if transitions is None:
            raise SovereignShieldV3Denied(
                f'Unknown determination action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM ssv3_determinations'
                    ' WHERE determination_id = ?',
                    (determination_id,)).fetchone()
                if row is None:
                    raise SovereignShieldV3Denied(
                        'Determination not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SovereignShieldV3Denied(
                        f"Cannot {action} a determination in"
                        f" status {row['status']}")
                receipt_id = self._record(
                    'SSV3_DETERMINATION_ACTION', actor=actor,
                    determination_id=determination_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE ssv3_determinations SET status = ?,'
                    ' updated_by = ?, updated_at = ?,'
                    ' receipt_id = ? WHERE determination_id = ?',
                    (new_status, actor, now, receipt_id,
                     determination_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM ssv3_determinations'
                ' WHERE determination_id = ?',
                (determination_id,)).fetchone()
        return self._determination_view(updated)

    def record_determination(self, actor, determination_id,
                             verdict, evidence_ref, *,
                             region=None):
        """Record one approved determination's verdict
        (operator only), against a presented evidence
        reference. A verdict without evidence is refused:
        a shield claim with nothing behind it is not a
        record. The verdict binds only to the presented
        evidence and the scope the record names."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in DETERMINATION_VERDICTS:
            raise SovereignShieldV3Denied(
                f'Unknown verdict: {verdict!r}')
        if not isinstance(evidence_ref, str) \
                or not evidence_ref.strip():
            raise SovereignShieldV3Denied(
                'An evidence reference is required to record'
                ' a determination')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM ssv3_determinations'
                    ' WHERE determination_id = ?',
                    (determination_id,)).fetchone()
                if row is None:
                    raise SovereignShieldV3Denied(
                        'Determination not found')
                if row['status'] != 'APPROVED':
                    raise SovereignShieldV3Denied(
                        'Determinations are recorded only for'
                        ' APPROVED requests (this one is'
                        f" {row['status']})")
                receipt_id = self._record(
                    'SSV3_DETERMINATION_RESULT', actor=actor,
                    determination_id=determination_id,
                    verdict=verdict,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE ssv3_determinations SET status = ?,'
                    ' verdict = ?, evidence_ref = ?,'
                    ' updated_by = ?, updated_at = ?,'
                    ' receipt_id = ? WHERE determination_id = ?',
                    ('DETERMINATION_RECORDED', verdict,
                     evidence_ref.strip(), actor, now, receipt_id,
                     determination_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM ssv3_determinations'
                ' WHERE determination_id = ?',
                (determination_id,)).fetchone()
        return self._determination_view(updated)

    # -- self-integrity -------------------------------------------------

    @staticmethod
    def _file_hash(path) -> str:
        try:
            digest = hashlib.sha256()
            with open(path, 'rb') as handle:
                while chunk := handle.read(8192):
                    digest.update(chunk)
            return digest.hexdigest()
        except OSError:
            return 'FILE_MISSING'

    def _foundation_state(self) -> dict:
        module = self._foundation
        if module is None:
            return {'loaded': False, 'constants_match': False}
        cls = getattr(module, 'SovereignShieldV3', None)
        return {
            'loaded': cls is not None,
            'constants_match': bool(
                cls is not None
                and getattr(cls, 'JURISDICTION_BASELINE', None)
                == JURISDICTION_BASELINE
                and getattr(cls, 'PQC_ALGORITHM', None)
                == PQC_ALGORITHM),
        }

    def integrity_status(self, actor, role, *, region=None):
        """Compare the foundation file and this service module
        against their pin, and report the foundation's load
        state."""
        self._geo(region)
        self._guard_access(actor, role, 'integrity',
                           'integrity view')
        foundation_current = self._file_hash(FOUNDATION_FILE)
        service_current = self._file_hash(SERVICE_FILE)
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM ssv3_integrity WHERE id = 1',
            ).fetchone()
        if row is None:
            state = 'UNPINNED'
            pinned = None
        else:
            pinned = {
                'foundation_hash': row['foundation_hash'],
                'service_hash': row['service_hash'],
                'pinned_by': row['pinned_by'],
                'pinned_at': row['pinned_at'],
            }
            state = (
                'MATCH'
                if pinned['foundation_hash'] == foundation_current
                and pinned['service_hash'] == service_current
                else 'MISMATCH')
        return {
            'foundation_file': (
                'money_factory_legal_aid_v1_668/shield/'
                'sovereign_shield_v3.py'),
            'service_file': 'core_platform/'
                            'sovereign_shield_v3_service.py',
            'state': state,
            'pinned': pinned,
            'foundation_current_hash': foundation_current,
            'service_current_hash': service_current,
            'foundation': self._foundation_state(),
        }

    def integrity_pin(self, actor, *, region=None):
        """Pin the current foundation and service hashes
        (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        foundation_current = self._file_hash(FOUNDATION_FILE)
        service_current = self._file_hash(SERVICE_FILE)
        if foundation_current == 'FILE_MISSING':
            raise SovereignShieldV3Denied(
                'Cannot pin a missing foundation file')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SSV3_INTEGRITY_PIN', actor=actor,
                    foundation_hash=foundation_current,
                    service_hash=service_current)
                db.execute(
                    'INSERT INTO ssv3_integrity (id,'
                    ' foundation_hash, service_hash, pinned_by,'
                    ' pinned_at, receipt_id) VALUES'
                    ' (1, ?, ?, ?, ?, ?)'
                    ' ON CONFLICT(id) DO UPDATE SET'
                    ' foundation_hash ='
                    ' excluded.foundation_hash,'
                    ' service_hash = excluded.service_hash,'
                    ' pinned_by = excluded.pinned_by,'
                    ' pinned_at = excluded.pinned_at,'
                    ' receipt_id = excluded.receipt_id',
                    (foundation_current, service_current, actor,
                     now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.integrity_status(actor, 'OPERATOR',
                                     region=region)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            custody_total = db.execute(
                'SELECT COUNT(*) AS n FROM ssv3_custody',
            ).fetchone()['n']
            by_status = {s: 0 for s in DETERMINATION_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' ssv3_determinations GROUP BY status'):
                by_status[row['status']] = row['n']
            pin = db.execute(
                'SELECT foundation_hash, service_hash FROM'
                ' ssv3_integrity WHERE id = 1',
            ).fetchone()
            latest = _foundation_latest_check_in(
                db, IDENTITY.platform_id)
        if pin is None:
            integrity_state = 'UNPINNED'
        else:
            integrity_state = (
                'MATCH'
                if pin['foundation_hash']
                == self._file_hash(FOUNDATION_FILE)
                and pin['service_hash']
                == self._file_hash(SERVICE_FILE)
                else 'MISMATCH')
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'custody_records_total': custody_total,
            'determinations_total': sum(by_status.values()),
            'determinations_by_status': by_status,
            'integrity_state': integrity_state,
            'foundation': self._foundation_state(),
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound
        to the platform identity's integrity digest via the
        shared foundation, with its receipt inside the
        transaction."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise SovereignShieldV3Denied(str(exc)) from exc
                self._record('SSV3_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
