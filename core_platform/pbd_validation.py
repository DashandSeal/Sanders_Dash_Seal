"""
Module: core_platform.pbd_validation
Architectural Layer: PBDScriptValidationEngine — the MASTER §13
pre-execution Dual-File Pair validation gate (MASTER §20: a
separate platform; never merged with PBDManifestGenerator, the
Global PBD Sentinel, the Vault, or Glass-Box Audit).

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (records only, stated exactly): the platform's designed
purpose in the MASTER (Sanders_Dash_Seal_Actual_Build_Design_
MASTER_2026-10-11.md): §13 names this engine the validation
enforcement point — "No valid `.pbd.json` Twin-Gated manifest = no
execution" — and §20 lists it as the "pre-execution Dual-File Pair
validation gate". Also recovered: this module's own orphaned
manifest, `core_platform/pbd_validation.py.pbd.json`, which
survived in the repo while the module itself was MISSING (the
143-identity reconciliation, catalog row 23, records the negative
finding). The orphaned manifest's recorded payload hash cannot
correspond to any file at the head it was found at — the artifact
did not exist — and is superseded by this build's manifest update,
recorded in docs/SPEC_CONFORMANCE.md. No validation-engine code
was recovered from any examined source.

REBUILT (everything executable in this module): the validation
service below, built 2026-11-24 under the owner's RTSA build
program on the shared foundation (core_platform.rtsa_foundation):
its own platform identity, a validation ledger in its own store,
Glass-Box receipts for every recorded validation, receipted
record access through the foundation AccessGuard, jurisdiction
geofence policy over declared jurisdictions, and operator-only
recall-pattern check-in.

WHAT VALIDATION MEANS HERE — stated exactly, never overstated:

* The engine assesses a Dual-File Pair (an executable artifact and
  its paired `.pbd.json` manifest) and returns one verdict:
  VALID, UNSIGNED, HASH_MISMATCH, ARTIFACT_MISMATCH,
  MALFORMED_MANIFEST, MISSING_MANIFEST, or MISSING_ARTIFACT.
* A pair is VALID only when the manifest parses, names this
  artifact, its recorded payload hash equals the SHA-256 of the
  artifact's exact bytes, AND the manifest carries Twin-Gate
  signatures. Every manifest in this repository today is an
  UNSIGNED_SOURCE_MANIFEST, so a hash-matching pair is reported
  UNSIGNED — structurally sound, but NOT authorization: per the
  repository's standing rule, an unsigned pair is not
  authorization for privileged application operations. The engine
  never upgrades an unsigned pair to VALID and never fabricates a
  signature.
* The engine is an assessment and recording service. It does not
  itself execute or block execution of other code; the §13 law's
  enforcement in running systems is by the systems that consult a
  validation verdict, and wiring such consultation into the
  flagship's startup is NOT part of this build and is not claimed.

Fail-closed throughout, on the platform's established disciplines:

* a Glass-Box audit adapter is required at construction — no
  record, no action;
* artifact paths must be relative and resolve inside the
  configured workspace root — absolute paths and traversal are
  refused before any file is read;
* every recorded validation writes its Glass-Box receipt inside
  the ledger transaction: if the receipt write raises, the
  transaction rolls back and nothing is recorded;
* operator-only operations (tree scans, check-in) go through
  ``operator_verifier``; an absent verifier means they are denied.

Python standard library only. No secrets, no network, no external
calls.
"""

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    latest_check_in as _foundation_latest_check_in,
    record_check_in as _foundation_record_check_in,
    validate_identity,
)


class PBDValidationDenied(ValueError):
    """The requested validation operation is invalid or cannot be
    evidenced, so it does not occur."""


class PBDValidationForbidden(ValueError):
    """The actor lacks authority for this validation operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='pbd_validation',
    name='PBDScriptValidationEngine',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The MASTER §13 permanent deployment law this platform serves.
ENFORCEMENT_LAW = (
    'No valid .pbd.json Twin-Gated manifest = no execution.')

VERDICTS = (
    'VALID',
    'UNSIGNED',
    'HASH_MISMATCH',
    'ARTIFACT_MISMATCH',
    'MALFORMED_MANIFEST',
    'MISSING_MANIFEST',
    'MISSING_ARTIFACT',
)

# Executable artifact suffixes the §13 Dual-File Pair standard and
# the §15 Sentinel scope name.
EXECUTABLE_SUFFIXES = ('.py', '.js', '.sh')

# Directories never scanned: version-control internals and caches
# are not governed deployment artifacts.
SKIP_DIR_NAMES = frozenset(('.git', '__pycache__', 'node_modules'))


def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def assess_pair(workspace_root, artifact_rel):
    """Pure Dual-File Pair assessment (no store, no audit, no I/O
    beyond reading the pair itself).

    ``artifact_rel`` must already be a normalized relative path
    inside ``workspace_root`` (see PBDValidationEngine._resolve).
    Returns the verdict dict the engine records: artifact, manifest
    path, verdict, the observed and recorded payload hashes (when
    readable), and the manifest's signature status (when readable).
    """
    root = Path(workspace_root)
    artifact_path = root / artifact_rel
    manifest_rel = artifact_rel + '.pbd.json'
    manifest_path = root / manifest_rel
    result = {
        'artifact': artifact_rel,
        'manifest': manifest_rel,
        'verdict': None,
        'payload_hash_observed': None,
        'payload_hash_recorded': None,
        'signature_status': None,
    }
    if not artifact_path.is_file():
        result['verdict'] = 'MISSING_ARTIFACT'
        return result
    observed = _sha256_hex(artifact_path.read_bytes())
    result['payload_hash_observed'] = observed
    if not manifest_path.is_file():
        result['verdict'] = 'MISSING_MANIFEST'
        return result
    try:
        manifest = json.loads(manifest_path.read_bytes().decode('utf-8'))
        body = manifest['body']
        recorded = body['payload_hash']
        if not isinstance(recorded, str) or not isinstance(body, dict):
            raise ValueError('manifest body is malformed')
    except Exception:
        result['verdict'] = 'MALFORMED_MANIFEST'
        return result
    result['payload_hash_recorded'] = recorded
    result['signature_status'] = body.get('status')
    if body.get('artifact') != artifact_rel:
        result['verdict'] = 'ARTIFACT_MISMATCH'
        return result
    if recorded != observed:
        result['verdict'] = 'HASH_MISMATCH'
        return result
    signatures = body.get('signatures')
    if not isinstance(signatures, dict) or not signatures:
        result['verdict'] = 'UNSIGNED'
        return result
    result['verdict'] = 'VALID'
    return result


class PBDValidationEngine:
    """The REBUILT PBDScriptValidationEngine service: Dual-File
    Pair assessments recorded in its own validation ledger, every
    recorded validation receipted to the Glass-Box chain inside the
    ledger transaction, record access receipted through the
    foundation AccessGuard, and operator-only tree scans and
    check-in."""

    def __init__(self, database, workspace_root,
                 operator_verifier=None, audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise PBDValidationDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        root = Path(workspace_root).resolve()
        if not root.is_dir():
            raise PBDValidationDenied(
                'workspace_root must be an existing directory')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.workspace_root = root
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'pbd_validation', {
            'OPERATOR': {'VALIDATION', 'STATUS'},
            'AUDITOR': {'VALIDATION', 'STATUS'},
            'COORDINATOR': {'VALIDATION', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS pbd_validations (
                validation_id TEXT PRIMARY KEY,
                artifact TEXT NOT NULL,
                manifest TEXT NOT NULL,
                verdict TEXT NOT NULL,
                payload_hash_observed TEXT,
                payload_hash_recorded TEXT,
                signature_status TEXT,
                actor TEXT NOT NULL,
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
        if not isinstance(actor, str) or not actor.strip():
            raise PBDValidationDenied('Invalid actor identity')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    def _resolve(self, artifact):
        """Normalize a caller-supplied artifact path to a relative
        path inside the workspace root. Fail-closed: non-strings,
        absolute paths, and anything resolving outside the root are
        refused before any file is read."""
        if not isinstance(artifact, str) or not artifact.strip():
            raise PBDValidationDenied('A non-empty artifact path is required')
        candidate = Path(artifact)
        if candidate.is_absolute():
            raise PBDValidationDenied(
                'Artifact paths must be relative to the workspace root')
        resolved = (self.workspace_root / candidate).resolve()
        if resolved != self.workspace_root and \
                self.workspace_root not in resolved.parents:
            raise PBDValidationDenied(
                'Artifact path escapes the workspace root')
        return resolved.relative_to(self.workspace_root).as_posix()

    @staticmethod
    def _validation_view(row):
        return {
            'validation_id': row['validation_id'],
            'artifact': row['artifact'],
            'manifest': row['manifest'],
            'verdict': row['verdict'],
            'payload_hash_observed': row['payload_hash_observed'],
            'payload_hash_recorded': row['payload_hash_recorded'],
            'signature_status': row['signature_status'],
            'actor': row['actor'],
            'recorded_at': row['recorded_at'],
        }

    def _counts(self, db):
        counts = {verdict: 0 for verdict in VERDICTS}
        for row in db.execute(
                "SELECT verdict, COUNT(*) AS n FROM pbd_validations "
                "GROUP BY verdict;").fetchall():
            if row['verdict'] in counts:
                counts[row['verdict']] = row['n']
        return counts

    # -- validation ----------------------------------------------------

    def validate_pair(self, actor, artifact):
        """Assess one Dual-File Pair and record the assessment.

        The verdict is computed from the pair's exact bytes, then
        the ledger row and its Glass-Box receipt are written inside
        one transaction: if the receipt cannot be written, nothing
        is recorded and the assessment is not served.
        """
        self._check_actor(actor)
        artifact_rel = self._resolve(artifact)
        result = assess_pair(self.workspace_root, artifact_rel)
        validation_id = 'val-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO pbd_validations (validation_id, "
                    "artifact, manifest, verdict, "
                    "payload_hash_observed, payload_hash_recorded, "
                    "signature_status, actor, recorded_at) VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?);",
                    (validation_id, result['artifact'], result['manifest'],
                     result['verdict'], result['payload_hash_observed'],
                     result['payload_hash_recorded'],
                     result['signature_status'], actor, now))
                self._record('PBD_VALIDATION_RECORDED',
                             validation_id=validation_id, actor=actor,
                             artifact=result['artifact'],
                             verdict=result['verdict'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM pbd_validations WHERE validation_id = ?;",
                (validation_id,)).fetchone()
            return self._validation_view(row)

    def scan(self, actor):
        """Operator-only: assess every executable artifact under
        the workspace root and record one ledger row per pair, with
        one summary receipt for the scan. Returns verdict counts
        for this scan. Version-control internals and caches are
        skipped (SKIP_DIR_NAMES) — they are not governed deployment
        artifacts."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDValidationForbidden(
                'Tree scans are an operator authority')
        artifacts = []
        for path in sorted(self.workspace_root.rglob('*')):
            if not path.is_file():
                continue
            if path.suffix not in EXECUTABLE_SUFFIXES:
                continue
            rel = path.relative_to(self.workspace_root)
            if any(part in SKIP_DIR_NAMES for part in rel.parts):
                continue
            if path.name.endswith('.pbd.json'):
                continue
            artifacts.append(rel.as_posix())
        counts = {verdict: 0 for verdict in VERDICTS}
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                for artifact_rel in artifacts:
                    result = assess_pair(self.workspace_root, artifact_rel)
                    counts[result['verdict']] += 1
                    db.execute(
                        "INSERT INTO pbd_validations (validation_id, "
                        "artifact, manifest, verdict, "
                        "payload_hash_observed, payload_hash_recorded, "
                        "signature_status, actor, recorded_at) VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?);",
                        ('val-' + secrets.token_urlsafe(12),
                         result['artifact'], result['manifest'],
                         result['verdict'], result['payload_hash_observed'],
                         result['payload_hash_recorded'],
                         result['signature_status'], actor, now))
                self._record('PBD_VALIDATION_SCAN', actor=actor,
                             artifacts_examined=len(artifacts),
                             counts=counts)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'artifacts_examined': len(artifacts), 'counts': counts}

    def validation_view(self, actor, role, validation_id):
        """Serve one recorded validation under the access guard:
        access is authorized and receipted FIRST, and only then is
        the record fetched and served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'VALIDATION', validation_id,
                              purpose='validation view')
        except FoundationForbidden as exc:
            raise PBDValidationForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise PBDValidationDenied(str(exc)) from exc
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM pbd_validations WHERE validation_id = ?;",
                (validation_id,)).fetchone()
            if row is None:
                raise PBDValidationDenied('Unknown validation')
            return self._validation_view(row)

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDValidationForbidden(
                'Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise PBDValidationDenied(str(exc)) from exc
                self._record('PBD_VALIDATION_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    # -- status --------------------------------------------------------

    def status(self):
        """Platform status: identity, the enforcement law served,
        recorded-validation counts by verdict, and the latest
        check-in."""
        with self._connect() as db:
            counts = self._counts(db)
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'enforcement_law': ENFORCEMENT_LAW,
            'workspace_root': str(self.workspace_root),
            'validation_counts': counts,
            'latest_check_in': latest,
        }
