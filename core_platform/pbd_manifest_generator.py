"""
Module: core_platform.pbd_manifest_generator
Architectural Layer: PBDManifestGenerator — the MASTER §14
manifest generation and payload/scope binding platform (MASTER
§20: a separate platform; never merged with
PBDScriptValidationEngine, the Global PBD Sentinel, the Vault, or
Glass-Box Audit).

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (records only, stated exactly): the platform's designed
purpose in the MASTER (Sanders_Dash_Seal_Actual_Build_Design_
MASTER_2026-10-11.md): §14, the PBD Manifest Generation Standard —
the generator "converts an executable script into a governed
deployment artifact" by reading the exact script payload,
calculating the payload hash, binding the script to its intended
operational scope, binding the target endpoint, identifying the
IT AI Manager version, recording required authorization metadata,
and generating the paired `.pbd.json` manifest; §20 lists it as
"manifest generation and payload/scope binding". Also recovered:
the manifest format every governed artifact in this repository
carries today — a JSON object whose `body` holds schema, platform,
artifact, payload_hash, scope, signatures, and status. No
generator module existed in any examined source (the 143-identity
reconciliation, catalog row 24: manifests were maintained by hand
and tooling).

REBUILT (everything executable in this module): the generation
service below, built 2026-11-24 under the owner's RTSA build
program on the shared foundation (core_platform.rtsa_foundation):
its own platform identity, a generation ledger in its own store,
Glass-Box receipts for every generation action, receipted record
access through the foundation AccessGuard, and operator-only
generation and recall-pattern check-in.

WHAT GENERATION MEANS HERE — stated exactly, never overstated:

* Generation is an operator authority. The generator writes the
  paired manifest for an executable artifact inside the workspace
  root, binding the artifact's exact SHA-256 payload hash, its
  operational scope, an optional target endpoint, the commanding
  IT AI Manager version (IT_AI_Manager_v15.0, the MASTER §9
  authority), and authorization metadata naming the requesting
  operator.
* The generator NEVER signs. A generated manifest carries an
  empty `signatures` object and the status
  UNSIGNED_SOURCE_MANIFEST: per the repository's standing rule,
  an unsigned pair is not authorization for privileged
  application operations. Twin-Gate signatures are the IT AI
  Manager's and MINOTAUR's to give, through their own processes —
  this platform prepares the governed artifact; it does not
  authorize it.
* When a manifest already exists for the artifact, the generator
  preserves its structure exactly (the repository's manifest
  rule): if its recorded payload hash already equals the
  artifact's current hash, nothing is written (action EXISTING);
  if the hash is stale, ONLY the payload_hash field is updated
  (action REGENERATED). The full §14 field set is written when a
  manifest is first created (action GENERATED).

RESIDUAL, stated plainly: the manifest file write is not
transactional with this service's store. Generation writes the
file, re-reads and verifies it against the computed hash, and
only then records the ledger row and its Glass-Box receipt inside
a transaction; if the receipt cannot be written, the action
raises and is not recorded, but the written manifest file remains
on disk (the Phase B cross-store residual class, recorded in
docs/SPEC_CONFORMANCE.md).

Fail-closed throughout: a Glass-Box audit adapter is required at
construction — no record, no action; artifact paths must be
relative and resolve inside the workspace root; only executable
suffixes (.py, .js, .sh) are governed artifacts.

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


class PBDGeneratorDenied(ValueError):
    """The requested generation operation is invalid or cannot be
    evidenced, so it does not occur."""


class PBDGeneratorForbidden(ValueError):
    """The actor lacks authority for this generation operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='pbd_manifest_generator',
    name='PBDManifestGenerator',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The MASTER §9 commanding authority recorded in every generated
# manifest's bindings.
MANAGER_VERSION = 'IT_AI_Manager_v15.0'

# The platform name every manifest in this repository carries.
MANIFEST_PLATFORM = 'Sanders Dash & Seal'

GENERATION_ACTIONS = ('GENERATED', 'REGENERATED', 'EXISTING')

# Executable artifact suffixes the §13/§14 standards govern.
EXECUTABLE_SUFFIXES = ('.py', '.js', '.sh')


class PBDManifestGenerator:
    """The REBUILT PBDManifestGenerator service: operator-only
    Dual-File Pair manifest generation and regeneration inside a
    workspace root, every action recorded in its own generation
    ledger and receipted to the Glass-Box chain."""

    def __init__(self, database, workspace_root,
                 operator_verifier=None, audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise PBDGeneratorDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        root = Path(workspace_root).resolve()
        if not root.is_dir():
            raise PBDGeneratorDenied(
                'workspace_root must be an existing directory')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.workspace_root = root
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'pbd_manifest_generator', {
            'OPERATOR': {'GENERATION', 'STATUS'},
            'AUDITOR': {'GENERATION', 'STATUS'},
            'COORDINATOR': {'GENERATION', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS pbd_generations (
                generation_id TEXT PRIMARY KEY,
                artifact TEXT NOT NULL,
                manifest TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                scope TEXT NOT NULL,
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
            raise PBDGeneratorDenied('Invalid actor identity')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    def _resolve(self, artifact):
        """Normalize a caller-supplied artifact path to a relative
        path inside the workspace root. Fail-closed: non-strings,
        absolute paths, and anything resolving outside the root are
        refused before any file is read or written."""
        if not isinstance(artifact, str) or not artifact.strip():
            raise PBDGeneratorDenied(
                'A non-empty artifact path is required')
        candidate = Path(artifact)
        if candidate.is_absolute():
            raise PBDGeneratorDenied(
                'Artifact paths must be relative to the workspace root')
        resolved = (self.workspace_root / candidate).resolve()
        if resolved != self.workspace_root and \
                self.workspace_root not in resolved.parents:
            raise PBDGeneratorDenied(
                'Artifact path escapes the workspace root')
        return resolved.relative_to(self.workspace_root).as_posix()

    @staticmethod
    def _generation_view(row):
        return {
            'generation_id': row['generation_id'],
            'artifact': row['artifact'],
            'manifest': row['manifest'],
            'action': row['action'],
            'payload_hash': row['payload_hash'],
            'scope': row['scope'],
            'actor': row['actor'],
            'recorded_at': row['recorded_at'],
        }

    def _counts(self, db):
        counts = {action: 0 for action in GENERATION_ACTIONS}
        for row in db.execute(
                "SELECT action, COUNT(*) AS n FROM pbd_generations "
                "GROUP BY action;").fetchall():
            if row['action'] in counts:
                counts[row['action']] = row['n']
        return counts

    # -- generation ----------------------------------------------------

    def generate(self, actor, artifact, scope='source-manifest',
                 endpoint=None):
        """Generate (or refresh) the paired `.pbd.json` manifest
        for one executable artifact. Operator-only.

        Follows MASTER §14 for a first creation and the
        repository's manifest rule for an existing manifest
        (structure preserved; only the payload hash changes). The
        written manifest is re-read and verified against the
        computed hash before the action is recorded and receipted.
        Returns the recorded generation view plus the manifest
        body written.
        """
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDGeneratorForbidden(
                'Manifest generation is an operator authority')
        artifact_rel = self._resolve(artifact)
        if Path(artifact_rel).suffix not in EXECUTABLE_SUFFIXES:
            raise PBDGeneratorDenied(
                'Only executable artifacts (.py, .js, .sh) are '
                'governed by the Dual-File Pair standard')
        if not isinstance(scope, str) or not scope.strip():
            raise PBDGeneratorDenied('A non-empty scope is required')
        if endpoint is not None and (
                not isinstance(endpoint, str) or not endpoint.strip()):
            raise PBDGeneratorDenied(
                'endpoint must be a non-empty string when given')
        artifact_path = self.workspace_root / artifact_rel
        if not artifact_path.is_file():
            raise PBDGeneratorDenied(
                f'Artifact does not exist: {artifact_rel}')
        payload_hash = hashlib.sha256(
            artifact_path.read_bytes()).hexdigest()
        manifest_rel = artifact_rel + '.pbd.json'
        manifest_path = self.workspace_root / manifest_rel

        existing = None
        if manifest_path.is_file():
            try:
                existing = json.loads(
                    manifest_path.read_bytes().decode('utf-8'))
                if not isinstance(existing.get('body'), dict):
                    raise ValueError('manifest body is malformed')
            except Exception as exc:
                raise PBDGeneratorDenied(
                    'Existing manifest is malformed; refusing to '
                    'overwrite it') from exc

        if existing is not None and \
                existing['body'].get('payload_hash') == payload_hash:
            action = 'EXISTING'
            body = existing['body']
        elif existing is not None:
            action = 'REGENERATED'
            existing['body']['payload_hash'] = payload_hash
            manifest_path.write_bytes(
                json.dumps(existing, indent=4).encode('utf-8'))
            body = existing['body']
        else:
            action = 'GENERATED'
            body = {
                'schema': 1,
                'platform': MANIFEST_PLATFORM,
                'artifact': artifact_rel,
                'payload_hash': payload_hash,
                'scope': scope,
                'endpoint': endpoint,
                'manager_version': MANAGER_VERSION,
                'authorization': {
                    'requested_by': actor,
                    'signatures_required': [
                        'IT_AI_Manager', 'MINOTAUR'],
                },
                'signatures': {},
                'status': 'UNSIGNED_SOURCE_MANIFEST',
            }
            manifest_path.write_bytes(
                json.dumps({'body': body}, indent=4).encode('utf-8'))

        # Re-read and verify whatever is now on disk before the
        # action is recorded: a manifest whose recorded hash does
        # not equal the artifact's hash is never receipted as a
        # generation.
        try:
            on_disk = json.loads(
                manifest_path.read_bytes().decode('utf-8'))
            verified = on_disk['body']['payload_hash'] == payload_hash
        except Exception:
            verified = False
        if not verified:
            raise PBDGeneratorDenied(
                'Written manifest failed verification against the '
                'artifact payload hash')

        generation_id = 'gen-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO pbd_generations (generation_id, "
                    "artifact, manifest, action, payload_hash, scope, "
                    "actor, recorded_at) VALUES (?, ?, ?, ?, ?, ?, "
                    "?, ?);",
                    (generation_id, artifact_rel, manifest_rel, action,
                     payload_hash, scope, actor, now))
                self._record('PBD_MANIFEST_GENERATION', actor=actor,
                             generation_id=generation_id,
                             artifact=artifact_rel, action=action,
                             payload_hash=payload_hash)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM pbd_generations WHERE generation_id = ?;",
                (generation_id,)).fetchone()
            view = self._generation_view(row)
        view['manifest_body'] = body
        return view

    def generation_view(self, actor, role, generation_id):
        """Serve one recorded generation under the access guard:
        access is authorized and receipted FIRST, and only then is
        the record fetched and served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'GENERATION', generation_id,
                              purpose='generation view')
        except FoundationForbidden as exc:
            raise PBDGeneratorForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise PBDGeneratorDenied(str(exc)) from exc
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM pbd_generations WHERE generation_id = ?;",
                (generation_id,)).fetchone()
            if row is None:
                raise PBDGeneratorDenied('Unknown generation')
            return self._generation_view(row)

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDGeneratorForbidden(
                'Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise PBDGeneratorDenied(str(exc)) from exc
                self._record('PBD_GENERATOR_CHECK_IN', actor=actor,
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
        """Platform status: identity, the manager version recorded
        in generated bindings, generation counts by action, and the
        latest check-in."""
        with self._connect() as db:
            counts = self._counts(db)
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'manager_version': MANAGER_VERSION,
            'generation_counts': counts,
            'latest_check_in': latest,
        }
