"""
Module: core_platform.pbd_sentinel
Architectural Layer: Global PBD Sentinel — the MASTER §15
continuous deployed-state integrity monitoring platform (MASTER
§20: a separate platform; never merged with
PBDScriptValidationEngine, PBDManifestGenerator, the Vault, or
Glass-Box Audit).

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (records only, stated exactly): the platform's designed
purpose in the MASTER (Sanders_Dash_Seal_Actual_Build_Design_
MASTER_2026-10-11.md): §15 — a "persistent Global PBD Sentinel
layer that scans the governed environment continuously",
checking executable artifacts (.py, .js, .sh) against their
paired PBD manifests, with enforcement logic including detection
of missing PBD manifests, continuous payload-hash comparison,
tamper detection, forensic telemetry generation, critical
integrity alerts, and a continuous scanning loop; the intended
complete chain is Detect → Compare → Isolate → Alert → Preserve
→ Verify → Release or Rebuild. §16 names the forensic record's
fields: the relevant timestamp, source context, expected hash,
observed hash, affected object, attempted operation, responsible
identity/process where available, and containment action; and
its containment principle: a protected object that changes
outside its authorized cryptographic state "is treated as an
integrity event and prevented from becoming the accepted
operational state". §17's directory pairing names a
`pbd_global_sentinel.py` file. §20 lists the platform as
"continuous deployed-state integrity monitoring". No Sentinel
module existed in any examined source (the 143-identity
reconciliation, catalog row 25).

REBUILT (everything executable in this module): the Sentinel
service below, built 2026-11-24 under the owner's RTSA build
program on the shared foundation (core_platform.rtsa_foundation):
its own platform identity, a baseline store (the last accepted
observed state of every governed artifact), a cycle ledger, and
a finding ledger in its own store, Glass-Box receipts inside
each ledger transaction, receipted record access through the
foundation AccessGuard, and operator-only chain operations and
recall-pattern check-in.

HOW THE SENTINEL DIFFERS FROM THE VALIDATION ENGINE — stated
exactly (§20 separation): PBDScriptValidationEngine is the
pre-execution gate: it assesses a pair on request. The Sentinel
is deployed-state monitoring: it scans the whole governed tree
in cycles, compares every artifact against BOTH its paired
manifest's recorded hash AND the Sentinel's own accepted
baseline, and drives each discrepancy through the §15 chain as
a forensic finding. The pair assessment here is implemented
inside this module against the same §13 standard; the Sentinel
does not import, wrap, or replace the validation engine.

CHAIN SEMANTICS — stated exactly:

* A scan cycle Detects and Compares: every sound pair (verdict
  UNSIGNED or VALID under the §13 standard — a hash-matching
  pair; UNSIGNED is structurally sound, never authorization)
  advances the accepted baseline. Every unsound pair opens a
  finding in state COMPARED (Detect and Compare complete inside
  the cycle) — or is counted still-open when a non-terminal
  finding for the same artifact already exists, so drift is
  never duplicated and never silently dropped.
* TAMPER_DETECTED is the kind when a baseline exists and the
  artifact's observed hash has moved from the accepted baseline
  while no longer matching its manifest — the §16 case of an
  object changing outside its authorized cryptographic state.
  The baseline is NOT advanced for an unsound pair: the drift
  stays visible until the chain resolves it.
* Isolate records the containment action on the finding: the
  artifact is marked not-accepted-operational-state in the
  Sentinel's record. The Sentinel records containment state; it
  does not move, rename, or chmod files — enforcement on the
  record is by the systems that consult it, and this build does
  not claim otherwise.
* Alert writes the critical integrity alert to the Glass-Box
  chain with the full §16 forensic telemetry. Preserve binds an
  evidence digest over the finding's forensic record. Verify
  re-assesses the pair and passes only when the pair is sound
  again. Release (only from VERIFIED, with the pair still sound)
  advances the accepted baseline to the verified state and
  closes the finding. Rebuild marks the finding
  REBUILD_REQUIRED — the artifact must be rebuilt (for example
  through PBDManifestGenerator and re-validation) before it can
  return; the baseline is not advanced.
* Chain order is enforced: DETECTED → COMPARED → ISOLATED →
  ALERTED → PRESERVED → VERIFIED → RELEASED, with
  REBUILD_REQUIRED reachable from PRESERVED or VERIFIED. No
  transition skips a step, and terminal findings (RELEASED,
  REBUILD_REQUIRED) have no outgoing transitions.

Fail-closed throughout: a Glass-Box audit adapter is required
at construction — no record, no action. Artifact paths are
derived from the workspace walk only; the Sentinel reads inside
its configured workspace root. Python standard library only. No
secrets, no network, no external calls.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
561621, 518210, 541519, 541690, 541511 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
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


class PBDSentinelDenied(ValueError):
    """The requested Sentinel operation is invalid or cannot be
    evidenced, so it does not occur."""


class PBDSentinelForbidden(ValueError):
    """The actor lacks authority for this Sentinel operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='pbd_sentinel',
    name='Global PBD Sentinel',
    legal_entities=(),
    naics_codes=('541512', '561621', '518210', '541519', '541690', '541511'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

# The MASTER §15 intended complete chain this platform drives.
CHAIN = ('Detect', 'Compare', 'Isolate', 'Alert', 'Preserve',
         'Verify', 'Release or Rebuild')

# Executable artifact suffixes the §13 Dual-File Pair standard
# and the §15 Sentinel scope name.
EXECUTABLE_SUFFIXES = ('.py', '.js', '.sh')

# Directories never scanned: version-control internals and caches
# are not governed deployment artifacts.
SKIP_DIR_NAMES = frozenset(('.git', '__pycache__', 'node_modules'))

SOUND_VERDICTS = ('UNSIGNED', 'VALID')

FINDING_KINDS = (
    'MISSING_MANIFEST',
    'HASH_MISMATCH',
    'MALFORMED_MANIFEST',
    'ARTIFACT_MISMATCH',
    'MISSING_ARTIFACT',
    'TAMPER_DETECTED',
)

FINDING_STATES = (
    'DETECTED',
    'COMPARED',
    'ISOLATED',
    'ALERTED',
    'PRESERVED',
    'VERIFIED',
    'RELEASED',
    'REBUILD_REQUIRED',
)

TERMINAL_STATES = frozenset(('RELEASED', 'REBUILD_REQUIRED'))

# Checked chain transitions: current state -> reachable states.
_TRANSITIONS = {
    'DETECTED': frozenset(('COMPARED',)),
    'COMPARED': frozenset(('ISOLATED',)),
    'ISOLATED': frozenset(('ALERTED',)),
    'ALERTED': frozenset(('PRESERVED',)),
    'PRESERVED': frozenset(('VERIFIED', 'REBUILD_REQUIRED')),
    'VERIFIED': frozenset(('RELEASED', 'REBUILD_REQUIRED')),
    'RELEASED': frozenset(),
    'REBUILD_REQUIRED': frozenset(),
}


def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _assess_pair(workspace_root, artifact_rel):
    """The §13 Dual-File Pair assessment, implemented inside this
    module (the Sentinel does not import the validation engine —
    §20 separation). Pure: reads only the pair itself."""
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


class PBDSentinel:
    """The REBUILT Global PBD Sentinel service: scan cycles over
    the governed tree, an accepted-state baseline per artifact,
    and one forensic finding per discrepancy driven through the
    §15 chain — every cycle and every chain transition recorded
    in its own ledgers and receipted to the Glass-Box chain
    inside the ledger transaction."""

    def __init__(self, database, workspace_root,
                 operator_verifier=None, audit=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise PBDSentinelDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        root = Path(workspace_root).resolve()
        if not root.is_dir():
            raise PBDSentinelDenied(
                'workspace_root must be an existing directory')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.workspace_root = root
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'pbd_sentinel', {
            'OPERATOR': {'FINDING', 'STATUS'},
            'AUDITOR': {'FINDING', 'STATUS'},
            'COORDINATOR': {'FINDING', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS sentinel_baselines (
                artifact TEXT PRIMARY KEY,
                payload_hash_observed TEXT,
                verdict TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS sentinel_cycles (
                cycle_id TEXT PRIMARY KEY,
                actor TEXT NOT NULL,
                recorded_at INTEGER NOT NULL,
                artifacts_examined INTEGER NOT NULL,
                sound INTEGER NOT NULL,
                findings_opened INTEGER NOT NULL,
                still_open INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS sentinel_findings (
                finding_id TEXT PRIMARY KEY,
                artifact TEXT NOT NULL,
                manifest TEXT NOT NULL,
                kind TEXT NOT NULL,
                expected_hash TEXT,
                observed_hash TEXT,
                recorded_hash TEXT,
                state TEXT NOT NULL,
                telemetry TEXT NOT NULL DEFAULT '{}',
                cycle_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                closed_at INTEGER
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
            raise PBDSentinelDenied('Invalid actor identity')

    def _require_operator(self, actor, what):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDSentinelForbidden(f'{what} is an operator authority')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    @staticmethod
    def _finding_view(row):
        return {
            'finding_id': row['finding_id'],
            'artifact': row['artifact'],
            'manifest': row['manifest'],
            'kind': row['kind'],
            'expected_hash': row['expected_hash'],
            'observed_hash': row['observed_hash'],
            'recorded_hash': row['recorded_hash'],
            'state': row['state'],
            'telemetry': json.loads(row['telemetry']),
            'cycle_id': row['cycle_id'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'closed_at': row['closed_at'],
        }

    def _finding_row(self, db, finding_id):
        return db.execute(
            "SELECT * FROM sentinel_findings WHERE finding_id = ?;",
            (finding_id,)).fetchone()

    def _open_finding(self, db, artifact):
        return db.execute(
            "SELECT * FROM sentinel_findings WHERE artifact = ? "
            "AND state NOT IN ('RELEASED', 'REBUILD_REQUIRED') "
            "ORDER BY created_at DESC LIMIT 1;", (artifact,)).fetchone()

    # -- scan cycles (Detect → Compare) -------------------------------

    def _walk_artifacts(self):
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
        return artifacts

    def run_scan(self, actor):
        """Operator-only: one full Detect → Compare cycle over the
        governed tree. Sound pairs advance the accepted baseline;
        unsound pairs open findings (state COMPARED) or count as
        still-open against an existing non-terminal finding;
        baseline artifacts that have vanished open MISSING_ARTIFACT
        findings. The cycle row, the baseline updates, the
        findings, and the cycle's Glass-Box receipt are written
        inside one transaction."""
        self._require_operator(actor, 'Sentinel scan cycles')
        artifacts = self._walk_artifacts()
        assessments = {rel: _assess_pair(self.workspace_root, rel)
                       for rel in artifacts}
        cycle_id = 'cycle-' + secrets.token_urlsafe(12)
        now = int(time.time())
        sound = 0
        opened = 0
        still_open = 0
        kind_counts = {kind: 0 for kind in FINDING_KINDS}
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                baselines = {
                    row['artifact']: row for row in db.execute(
                        "SELECT * FROM sentinel_baselines;").fetchall()}
                candidates = []
                for rel in artifacts:
                    result = assessments[rel]
                    baseline = baselines.get(rel)
                    if result['verdict'] in SOUND_VERDICTS:
                        sound += 1
                        db.execute(
                            "INSERT INTO sentinel_baselines (artifact, "
                            "payload_hash_observed, verdict, cycle_id, "
                            "updated_at) VALUES (?, ?, ?, ?, ?) "
                            "ON CONFLICT(artifact) DO UPDATE SET "
                            "payload_hash_observed = excluded."
                            "payload_hash_observed, verdict = excluded."
                            "verdict, cycle_id = excluded.cycle_id, "
                            "updated_at = excluded.updated_at;",
                            (rel, result['payload_hash_observed'],
                             result['verdict'], cycle_id, now))
                        continue
                    kind = result['verdict']
                    if kind == 'HASH_MISMATCH' and baseline is not None \
                            and baseline['payload_hash_observed'] \
                            and result['payload_hash_observed'] \
                            and baseline['payload_hash_observed'] \
                            != result['payload_hash_observed']:
                        kind = 'TAMPER_DETECTED'
                    candidates.append((rel, result, kind, baseline))
                for rel, baseline in baselines.items():
                    if rel not in assessments:
                        result = {
                            'artifact': rel,
                            'manifest': rel + '.pbd.json',
                            'verdict': 'MISSING_ARTIFACT',
                            'payload_hash_observed': None,
                            'payload_hash_recorded': None,
                            'signature_status': None,
                        }
                        candidates.append(
                            (rel, result, 'MISSING_ARTIFACT', baseline))
                for rel, result, kind, baseline in candidates:
                    if self._open_finding(db, rel) is not None:
                        still_open += 1
                        continue
                    expected = result['payload_hash_recorded']
                    if baseline is not None and \
                            baseline['payload_hash_observed']:
                        expected = baseline['payload_hash_observed']
                    telemetry = {
                        'recorded_at': now,
                        'source_context': f'scan cycle {cycle_id}',
                        'expected_hash': expected,
                        'observed_hash': result['payload_hash_observed'],
                        'affected_object': rel,
                        'attempted_operation':
                            'deployed-state integrity scan',
                        'responsible_identity': actor,
                        'containment_action': 'NONE',
                        'verdict': result['verdict'],
                        'signature_status': result['signature_status'],
                    }
                    db.execute(
                        "INSERT INTO sentinel_findings (finding_id, "
                        "artifact, manifest, kind, expected_hash, "
                        "observed_hash, recorded_hash, state, "
                        "telemetry, cycle_id, created_at, updated_at, "
                        "closed_at) VALUES (?, ?, ?, ?, ?, ?, ?, "
                        "'COMPARED', ?, ?, ?, ?, NULL);",
                        ('find-' + secrets.token_urlsafe(12), rel,
                         result['manifest'], kind, expected,
                         result['payload_hash_observed'],
                         result['payload_hash_recorded'],
                         json.dumps(telemetry, sort_keys=True),
                         cycle_id, now, now))
                    kind_counts[kind] += 1
                    opened += 1
                db.execute(
                    "INSERT INTO sentinel_cycles (cycle_id, actor, "
                    "recorded_at, artifacts_examined, sound, "
                    "findings_opened, still_open) VALUES "
                    "(?, ?, ?, ?, ?, ?, ?);",
                    (cycle_id, actor, now, len(artifacts), sound,
                     opened, still_open))
                self._record('PBD_SENTINEL_SCAN_CYCLE', actor=actor,
                             cycle_id=cycle_id,
                             artifacts_examined=len(artifacts),
                             sound=sound, findings_opened=opened,
                             still_open=still_open,
                             kind_counts=kind_counts)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'cycle_id': cycle_id,
            'artifacts_examined': len(artifacts),
            'sound': sound,
            'findings_opened': opened,
            'still_open': still_open,
            'kind_counts': kind_counts,
        }

    # -- the chain beyond Compare --------------------------------------

    def _transition(self, actor, finding_id, target, stage,
                    what, mutate=None):
        """One checked chain transition, operator-only, with its
        receipt inside the transaction. ``mutate`` (optional) runs
        inside the transaction before the state update and may
        adjust the telemetry dict; it returns extra receipt
        fields."""
        self._require_operator(actor, what)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._finding_row(db, finding_id)
                if row is None:
                    raise PBDSentinelDenied('Unknown finding')
                current = row['state']
                if target not in _TRANSITIONS[current]:
                    raise PBDSentinelDenied(
                        f'Transition {current}->{target} is not '
                        'permitted by the §15 chain')
                telemetry = json.loads(row['telemetry'])
                extra = {}
                if mutate is not None:
                    extra = mutate(db, row, telemetry) or {}
                closed_at = now if target in TERMINAL_STATES else None
                db.execute(
                    "UPDATE sentinel_findings SET state = ?, "
                    "telemetry = ?, updated_at = ?, closed_at = ? "
                    "WHERE finding_id = ?;",
                    (target, json.dumps(telemetry, sort_keys=True),
                     now, closed_at, finding_id))
                self._record(stage, actor=actor, finding_id=finding_id,
                             artifact=row['artifact'],
                             from_state=current, to_state=target,
                             **extra)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._finding_view(self._finding_row(db, finding_id))

    def isolate(self, actor, finding_id):
        """Compare → Isolate: record the §16 containment action —
        the artifact is marked not-accepted-operational-state in
        the Sentinel's record (the record is the containment
        state; no file is moved)."""
        def mutate(db, row, telemetry):
            telemetry['containment_action'] = (
                'ISOLATED: marked not-accepted-operational-state')
            return {}
        return self._transition(actor, finding_id, 'ISOLATED',
                                'PBD_SENTINEL_ISOLATED',
                                'Finding isolation', mutate)

    def alert(self, actor, finding_id):
        """Isolate → Alert: issue the critical integrity alert —
        the full §16 forensic telemetry is written to the
        Glass-Box chain with this transition's receipt."""
        def mutate(db, row, telemetry):
            return {'kind': row['kind'],
                    'expected_hash': row['expected_hash'],
                    'observed_hash': row['observed_hash'],
                    'affected_object': row['artifact'],
                    'containment_action':
                        telemetry.get('containment_action')}
        return self._transition(actor, finding_id, 'ALERTED',
                                'PBD_SENTINEL_ALERT',
                                'Integrity alerts', mutate)

    def preserve(self, actor, finding_id):
        """Alert → Preserve: bind an evidence digest over the
        finding's forensic record (§16 tamper-proof audit
        tracking) into the finding's telemetry."""
        def mutate(db, row, telemetry):
            core = {
                'artifact': row['artifact'],
                'kind': row['kind'],
                'expected_hash': row['expected_hash'],
                'observed_hash': row['observed_hash'],
                'recorded_hash': row['recorded_hash'],
                'cycle_id': row['cycle_id'],
                'created_at': row['created_at'],
            }
            telemetry['evidence_digest'] = _sha256_hex(json.dumps(
                core, sort_keys=True, separators=(',', ':')
            ).encode('utf-8'))
            return {'evidence_digest': telemetry['evidence_digest']}
        return self._transition(actor, finding_id, 'PRESERVED',
                                'PBD_SENTINEL_PRESERVED',
                                'Evidence preservation', mutate)

    def verify(self, actor, finding_id):
        """Preserve → Verify: re-assess the pair now. The chain
        advances only when the pair is sound again (verdict
        UNSIGNED or VALID); otherwise the verification fails, the
        finding stays PRESERVED, and nothing is recorded."""
        self._require_operator(actor, 'Finding verification')
        with self._connect() as db:
            row = self._finding_row(db, finding_id)
        if row is None:
            raise PBDSentinelDenied('Unknown finding')
        if row['state'] != 'PRESERVED':
            raise PBDSentinelDenied(
                f"Transition {row['state']}->VERIFIED is not "
                'permitted by the §15 chain')
        result = _assess_pair(self.workspace_root, row['artifact'])
        if result['verdict'] not in SOUND_VERDICTS:
            raise PBDSentinelDenied(
                f"Verification failed: the pair is still "
                f"{result['verdict']}")
        def mutate(db, row, telemetry):
            telemetry['verification_verdict'] = result['verdict']
            telemetry['verification_observed_hash'] = \
                result['payload_hash_observed']
            return {'verification_verdict': result['verdict']}
        return self._transition(actor, finding_id, 'VERIFIED',
                                'PBD_SENTINEL_VERIFIED',
                                'Finding verification', mutate)

    def release(self, actor, finding_id):
        """Verify → Release: the pair is re-assessed once more and
        must still be sound; the accepted baseline advances to the
        verified state and the finding closes."""
        self._require_operator(actor, 'Finding release')
        with self._connect() as db:
            row = self._finding_row(db, finding_id)
        if row is None:
            raise PBDSentinelDenied('Unknown finding')
        if row['state'] != 'VERIFIED':
            raise PBDSentinelDenied(
                f"Transition {row['state']}->RELEASED is not "
                'permitted by the §15 chain')
        result = _assess_pair(self.workspace_root, row['artifact'])
        if result['verdict'] not in SOUND_VERDICTS:
            raise PBDSentinelDenied(
                f"Release refused: the pair is now "
                f"{result['verdict']}")
        def mutate(db, row, telemetry):
            db.execute(
                "INSERT INTO sentinel_baselines (artifact, "
                "payload_hash_observed, verdict, cycle_id, "
                "updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(artifact) DO UPDATE SET "
                "payload_hash_observed = excluded."
                "payload_hash_observed, verdict = excluded.verdict, "
                "cycle_id = excluded.cycle_id, updated_at = excluded."
                "updated_at;",
                (row['artifact'], result['payload_hash_observed'],
                 result['verdict'], row['cycle_id'],
                 int(time.time())))
            return {'released_verdict': result['verdict']}
        return self._transition(actor, finding_id, 'RELEASED',
                                'PBD_SENTINEL_RELEASED',
                                'Finding release', mutate)

    def mark_rebuild(self, actor, finding_id):
        """Preserve|Verify → Rebuild: the artifact must be rebuilt
        before it can return; the finding closes as
        REBUILD_REQUIRED and the baseline is not advanced."""
        return self._transition(actor, finding_id, 'REBUILD_REQUIRED',
                                'PBD_SENTINEL_REBUILD_REQUIRED',
                                'Rebuild marking')

    def finding_view(self, actor, role, finding_id):
        """Serve one finding under the access guard: access is
        authorized and receipted FIRST, and only then is the
        record fetched and served."""
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'FINDING', finding_id,
                              purpose='finding view')
        except FoundationForbidden as exc:
            raise PBDSentinelForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise PBDSentinelDenied(str(exc)) from exc
        with self._connect() as db:
            row = self._finding_row(db, finding_id)
            if row is None:
                raise PBDSentinelDenied('Unknown finding')
            return self._finding_view(row)

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to
        the platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise PBDSentinelForbidden(
                'Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise PBDSentinelDenied(str(exc)) from exc
                self._record('PBD_SENTINEL_CHECK_IN', actor=actor,
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
        """Platform status: identity, the §15 chain served, cycle
        count, baseline size, finding counts by state and kind,
        and the latest check-in."""
        with self._connect() as db:
            cycles = db.execute(
                "SELECT COUNT(*) AS n FROM sentinel_cycles;"
            ).fetchone()['n']
            baselines = db.execute(
                "SELECT COUNT(*) AS n FROM sentinel_baselines;"
            ).fetchone()['n']
            by_state = {state: 0 for state in FINDING_STATES}
            for row in db.execute(
                    "SELECT state, COUNT(*) AS n FROM "
                    "sentinel_findings GROUP BY state;").fetchall():
                if row['state'] in by_state:
                    by_state[row['state']] = row['n']
            by_kind = {kind: 0 for kind in FINDING_KINDS}
            for row in db.execute(
                    "SELECT kind, COUNT(*) AS n FROM "
                    "sentinel_findings GROUP BY kind;").fetchall():
                if row['kind'] in by_kind:
                    by_kind[row['kind']] = row['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'chain': list(CHAIN),
            'cycles_recorded': cycles,
            'baselines_tracked': baselines,
            'finding_counts_by_state': by_state,
            'finding_counts_by_kind': by_kind,
            'latest_check_in': latest,
        }
