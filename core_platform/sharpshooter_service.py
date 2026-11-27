"""Sharpshooter — production RTSA platform (RTSA Build Program Q7).

RECOVERED / REBUILT, stated exactly:

RECOVERED (foundation, untouched): the ``sharpshooter/`` package —
``sharpshooter/core.py`` (provider-independent TLS diagnosis that
never bypasses certificate verification, the ``Incident`` record,
the integrity-hashed JSON ``evidence`` form, the ``Adapter``
contract — provider implementations must explicitly verify
credentials and resource ownership — and the ``Remediator`` with
its authorization-aware planner and execute-versus-plan
separation), ``sharpshooter/cli.py``, and ``sharpshooter/README.md``,
whose production-integration list this build executes: real
provider adapters, credential acquisition, a persistent event
store, and an API service. The foundation's diagnosis is
stateless: incidents live in process memory, evidence is printed,
no adapter is registered, no credential is ever acquired, and
nothing is queryable after the fact.

REBUILT (this module, 2026-11-24): the production Sharpshooter
platform on the shared RTSA foundation
(``core_platform/rtsa_foundation.py``) — the foundation package's
diagnosis and remediation semantics kept as durable, receipted
state in the platform's own store:

* a persistent event store: every diagnosis becomes an incident
  record carrying the recovered evidence hash, and every TLS
  observation feeds a certificate inventory (expiry, subject
  alternative names, TLS version) for the diagnosed hostname;
* a provider adapter registry implementing the recovered
  ``Adapter`` contract: adapters declare explicit capabilities;
  provider adapters acquire credentials from the environment by
  variable NAME only (presence is checked and recorded; a
  credential value is never read into a record, stored, or
  returned), and an adapter whose credential is absent executes
  nothing. The built-in TLS probe adapter is a real adapter: it
  performs the recovered diagnosis and the independent
  post-execution verification. No provider mutation occurs until
  an adapter with valid credentials is configured — the recovered
  README's rule, enforced here as state;
* remediation as checked records: a plan is recorded first
  (execute-versus-plan separation preserved), execution runs only
  a recorded plan through a capability-checked, credential-ready
  adapter, and an independent post-execution diagnosis verifies
  the result before the incident may be called resolved;
* rollback of an executed remediation restores the incident's
  pre-execution recorded state, receipted — record-level
  rollback, stated exactly;
* a durable job queue for diagnosis work with atomic claims, so
  concurrent callers enqueue rather than collide.

Diagnosis is performed by an injectable diagnoser whose
production binding is the recovered ``sharpshooter.core.diagnose``
— real DNS, TCP/443, and certificate-verified TLS with SNI,
against real hostnames. This platform diagnoses and remediates
operational infrastructure state; it holds no customer records
and no PHI.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541512,
541513, 541519, 518210, 561621, 541690 — ADOPTED_EXISTING
per the NACI six-code reconciliation of 2026-11-26. The
reconciled six govern the built identity from this lock-in
forward.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path

from sharpshooter.core import diagnose as _recovered_diagnose

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
    platform_id='sharpshooter',
    name='Sharpshooter',
    legal_entities=(),
    naics_codes=('541512', '541513', '541519', '518210', '561621', '541690'),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

PROBE_ADAPTER = 'tls-probe'
PROBE_CAPABILITIES = ('diagnose', 'verify')
INCIDENT_STATUSES = ('healthy', 'detected', 'resolved',
                     'verification_failed')
PLAN_OUTCOMES = ('planned', 'provider_action_required',
                 'authorization_required')
JOB_STATES = ('PENDING', 'CLAIMED', 'COMPLETED', 'FAILED')
JOB_TYPES = ('DIAGNOSE',)


class SharpshooterDenied(Exception):
    """The requested Sharpshooter operation is not allowed."""


class SharpshooterForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SharpshooterService:
    """Durable Sharpshooter diagnosis and remediation platform."""

    def __init__(self, database_path, operator_verifier, audit, *,
                 diagnoser=None, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SharpshooterDenied(
                'Sharpshooter requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._diagnoser = diagnoser or _recovered_diagnose
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sharpshooter', {
            'OPERATOR': {'INCIDENT', 'REMEDIATION', 'STATUS'},
            'AUDITOR': {'INCIDENT', 'REMEDIATION', 'STATUS'},
            'COORDINATOR': {'INCIDENT', 'STATUS'},
        })
        # Executors live outside the store: the registry records
        # what an adapter may do and whether its credential is
        # present; only adapters with a local executor can run.
        self._executors = {PROBE_ADAPTER: self._probe_execute}
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sharpshooter_incidents (
                    incident_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    detected_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    observations TEXT NOT NULL,
                    action TEXT NOT NULL DEFAULT 'none',
                    verification TEXT,
                    evidence_sha256 TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sharpshooter_remediations (
                    remediation_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    adapter TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    authorization TEXT,
                    pre_state TEXT,
                    detail TEXT,
                    rolled_back INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sharpshooter_jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    state TEXT NOT NULL,
                    incident_id TEXT,
                    detail TEXT,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sharpshooter_adapters (
                    name TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    credential_env TEXT,
                    credential_state TEXT NOT NULL,
                    registered_by TEXT NOT NULL,
                    registered_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sharpshooter_cert_inventory (
                    hostname TEXT PRIMARY KEY,
                    expires TEXT,
                    subject_alt_names TEXT NOT NULL,
                    tls_version TEXT,
                    last_seen REAL NOT NULL
                );
                """
            )
            db.execute(
                "INSERT OR IGNORE INTO sharpshooter_adapters"
                " (name, kind, capabilities, credential_env,"
                " credential_state, registered_by, registered_at)"
                " VALUES (?, 'BUILTIN', ?, NULL, 'NOT_REQUIRED',"
                " 'system', ?);",
                (PROBE_ADAPTER, json.dumps(list(PROBE_CAPABILITIES)),
                 float(self._clock())))

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
            raise SharpshooterForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SharpshooterForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    # -- adapters -----------------------------------------------------

    def _probe_execute(self, operation, hostname):
        """The built-in TLS probe adapter: a real execution of the
        recovered diagnosis. Success means a certificate-verified
        TLS handshake completed."""
        observation = self._diagnoser(hostname)
        return {'success': bool(observation.get('tls')),
                'observation': observation}

    def _adapter_row(self, db, name):
        return db.execute(
            'SELECT * FROM sharpshooter_adapters WHERE name = ?',
            (name,)).fetchone()

    @staticmethod
    def _adapter_view(row):
        return {
            'name': row['name'],
            'kind': row['kind'],
            'capabilities': json.loads(row['capabilities']),
            'credential_env': row['credential_env'],
            'credential_state': row['credential_state'],
            'registered_by': row['registered_by'],
            'registered_at': row['registered_at'],
        }

    def adapters(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sharpshooter_adapters ORDER BY name'
            ).fetchall()
        return [self._adapter_view(r) for r in rows]

    def register_provider_adapter(self, actor, name, capabilities,
                                  credential_env) -> dict:
        """Register a provider adapter under the recovered contract
        and acquire its credential: the credential is acquired from
        the environment by variable name — presence only is checked
        and recorded; the value is never read into a record."""
        self._require_operator(actor)
        if not isinstance(name, str) or not name.strip() \
                or name == PROBE_ADAPTER:
            raise SharpshooterDenied('A unique adapter name is required')
        if not isinstance(capabilities, (list, tuple)) \
                or not capabilities \
                or not all(isinstance(c, str) and c.strip()
                           for c in capabilities):
            raise SharpshooterDenied(
                'Capabilities must be a non-empty list of names')
        if not isinstance(credential_env, str) \
                or not credential_env.strip():
            raise SharpshooterDenied(
                'A credential environment variable name is required')
        state = 'PRESENT' if os.environ.get(credential_env) else 'ABSENT'
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                if self._adapter_row(db, name) is not None:
                    raise SharpshooterDenied(
                        f'Adapter already registered: {name!r}')
                db.execute(
                    "INSERT INTO sharpshooter_adapters (name, kind,"
                    " capabilities, credential_env, credential_state,"
                    " registered_by, registered_at) VALUES (?,"
                    " 'PROVIDER', ?, ?, ?, ?, ?);",
                    (name, json.dumps(sorted(set(capabilities))),
                     credential_env, state, actor, now))
                self._record('SHARPSHOOTER_ADAPTER_REGISTERED',
                             actor=actor, adapter=name,
                             credential_env=credential_env,
                             credential_state=state)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._adapter_view(self._adapter_row(db, name))

    def refresh_adapter_credential(self, actor, name) -> dict:
        """Re-run credential acquisition for a provider adapter
        (e.g. after the owner provisions the credential)."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = self._adapter_row(db, name)
                if row is None:
                    raise SharpshooterDenied(f'Unknown adapter: {name!r}')
                if row['kind'] != 'PROVIDER':
                    raise SharpshooterDenied(
                        'Only provider adapters acquire credentials')
                state = 'PRESENT' if os.environ.get(
                    row['credential_env']) else 'ABSENT'
                db.execute(
                    'UPDATE sharpshooter_adapters SET'
                    ' credential_state = ? WHERE name = ?;',
                    (state, name))
                self._record('SHARPSHOOTER_CREDENTIAL_ACQUIRED',
                             actor=actor, adapter=name,
                             credential_state=state)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._adapter_view(self._adapter_row(db, name))

    # -- diagnosis / incidents -----------------------------------------

    @staticmethod
    def _evidence_hash(incident_id, hostname, detected_at, status,
                       observations):
        payload = json.dumps({
            'id': incident_id, 'hostname': hostname,
            'detected_at': detected_at, 'status': status,
            'observations': observations,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _run_diagnosis(self, db, actor, hostname):
        """Run the diagnoser and persist the incident + certificate
        inventory inside the caller's transaction."""
        if not isinstance(hostname, str) or not hostname.strip() \
                or any(c in hostname for c in '/:@?# ') \
                or len(hostname) > 253:
            raise SharpshooterDenied('hostname must be a DNS name')
        observation = self._diagnoser(hostname)
        if not isinstance(observation, dict):
            raise SharpshooterDenied('Diagnoser returned no observation')
        now = self._now()
        incident_id = 'inc-' + secrets.token_urlsafe(12)
        status = 'healthy' if observation.get('tls') else 'detected'
        evidence = self._evidence_hash(incident_id, hostname, now,
                                       status, observation)
        db.execute(
            "INSERT INTO sharpshooter_incidents (incident_id,"
            " hostname, detected_at, status, observations, action,"
            " verification, evidence_sha256, created_by, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 'none', NULL, ?, ?, ?);",
            (incident_id, hostname, now, status,
             json.dumps(observation, sort_keys=True), evidence,
             actor, now))
        if observation.get('tls'):
            db.execute(
                "INSERT INTO sharpshooter_cert_inventory (hostname,"
                " expires, subject_alt_names, tls_version, last_seen)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(hostname) DO UPDATE SET"
                " expires = excluded.expires,"
                " subject_alt_names = excluded.subject_alt_names,"
                " tls_version = excluded.tls_version,"
                " last_seen = excluded.last_seen;",
                (hostname, observation.get('expires'),
                 json.dumps(observation.get('subject_alt_names', []),
                            sort_keys=True),
                 observation.get('tls_version'), now))
        self._record('SHARPSHOOTER_DIAGNOSIS_RECORDED', actor=actor,
                     incident_id=incident_id, hostname=hostname,
                     status=status, evidence_sha256=evidence)
        return incident_id

    def diagnose(self, actor, hostname) -> dict:
        self._check_actor(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                incident_id = self._run_diagnosis(db, actor, hostname)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._incident_row_view(
                self._incident_row(db, incident_id))

    @staticmethod
    def _incident_row_view(row):
        return {
            'incident_id': row['incident_id'],
            'hostname': row['hostname'],
            'detected_at': row['detected_at'],
            'status': row['status'],
            'observations': json.loads(row['observations']),
            'action': row['action'],
            'verification': (json.loads(row['verification'])
                             if row['verification'] else None),
            'evidence_sha256': row['evidence_sha256'],
            'created_by': row['created_by'],
            'updated_at': row['updated_at'],
        }

    def _incident_row(self, db, incident_id):
        row = db.execute(
            'SELECT * FROM sharpshooter_incidents'
            ' WHERE incident_id = ?', (incident_id,)).fetchone()
        if row is None:
            raise SharpshooterDenied(
                f'Unknown incident: {incident_id!r}')
        return row

    def incident_view(self, actor, role, incident_id) -> dict:
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'INCIDENT', incident_id,
                              purpose='incident view')
        except FoundationForbidden as exc:
            raise SharpshooterForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SharpshooterDenied(str(exc)) from exc
        with self._connect() as db:
            return self._incident_row_view(
                self._incident_row(db, incident_id))

    def cert_inventory(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sharpshooter_cert_inventory'
                ' ORDER BY hostname').fetchall()
        return [{
            'hostname': r['hostname'],
            'expires': r['expires'],
            'subject_alt_names': json.loads(r['subject_alt_names']),
            'tls_version': r['tls_version'],
            'last_seen': r['last_seen'],
        } for r in rows]

    # -- remediation ----------------------------------------------------

    @staticmethod
    def _remediation_view(row):
        return {
            'remediation_id': row['remediation_id'],
            'incident_id': row['incident_id'],
            'operation': row['operation'],
            'adapter': row['adapter'],
            'mode': row['mode'],
            'outcome': row['outcome'],
            'authorization': (json.loads(row['authorization'])
                              if row['authorization'] else None),
            'detail': row['detail'],
            'rolled_back': bool(row['rolled_back']),
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    def _remediation_row(self, db, remediation_id):
        row = db.execute(
            'SELECT * FROM sharpshooter_remediations'
            ' WHERE remediation_id = ?', (remediation_id,)).fetchone()
        if row is None:
            raise SharpshooterDenied(
                f'Unknown remediation: {remediation_id!r}')
        return row

    def plan_remediation(self, actor, incident_id, operation,
                         adapter_name) -> dict:
        """Record a remediation plan (execute-versus-plan
        separation). The operator's recorded act is the
        authorization the recovered Remediator requires: approved,
        and bound to this adapter. Capability and credential
        readiness decide the recorded outcome exactly as the
        recovered planner decided it."""
        self._require_operator(actor)
        if not isinstance(operation, str) or not operation.strip():
            raise SharpshooterDenied('An operation is required')
        now = self._now()
        remediation_id = 'rem-' + secrets.token_urlsafe(12)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                incident = self._incident_row(db, incident_id)
                if incident['status'] == 'healthy':
                    raise SharpshooterDenied(
                        'Incident is healthy: nothing to remediate')
                if incident['status'] == 'resolved':
                    raise SharpshooterDenied(
                        'Incident is already resolved')
                adapter = self._adapter_row(db, adapter_name)
                if adapter is None:
                    raise SharpshooterDenied(
                        f'Unknown adapter: {adapter_name!r}')
                capabilities = json.loads(adapter['capabilities'])
                if operation not in capabilities:
                    outcome = 'provider_action_required'
                    detail = 'unsupported_operation'
                elif adapter['credential_state'] == 'ABSENT':
                    outcome = 'authorization_required'
                    detail = 'adapter credential absent'
                else:
                    outcome = 'planned'
                    detail = None
                authorization = {
                    'approved': True, 'provider': adapter_name,
                    'approved_by': actor, 'approved_at': now,
                }
                pre_state = json.dumps({
                    'status': incident['status'],
                    'action': incident['action'],
                    'verification': (json.loads(incident['verification'])
                                     if incident['verification']
                                     else None),
                }, sort_keys=True)
                db.execute(
                    "INSERT INTO sharpshooter_remediations"
                    " (remediation_id, incident_id, operation, adapter,"
                    " mode, outcome, authorization, pre_state, detail,"
                    " rolled_back, created_by, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, 'PLANNED', ?, ?, ?, ?, 0,"
                    " ?, ?, ?);",
                    (remediation_id, incident_id, operation,
                     adapter_name, outcome,
                     json.dumps(authorization, sort_keys=True),
                     pre_state, detail, actor, now, now))
                self._record('SHARPSHOOTER_REMEDIATION_PLANNED',
                             actor=actor, remediation_id=remediation_id,
                             incident_id=incident_id,
                             operation=operation, adapter=adapter_name,
                             outcome=outcome)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._remediation_view(
                self._remediation_row(db, remediation_id))

    def execute_remediation(self, actor, remediation_id) -> dict:
        """Execute a recorded plan through its adapter, then verify
        independently: a fresh diagnosis decides resolved versus
        verification_failed, exactly as the recovered Remediator
        verified after execution."""
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                rem = self._remediation_row(db, remediation_id)
                if rem['mode'] != 'PLANNED' or rem['outcome'] != 'planned':
                    raise SharpshooterDenied(
                        'Only a planned remediation may execute')
                executor = self._executors.get(rem['adapter'])
                if executor is None:
                    raise SharpshooterDenied(
                        'Adapter has no local executor configured: '
                        'no provider mutation occurs until an adapter'
                        ' with valid credentials is configured')
                incident = self._incident_row(db, rem['incident_id'])
                outcome = executor(rem['operation'],
                                   incident['hostname'])
                verification = self._diagnoser(incident['hostname'])
                resolved = bool(outcome.get('success')) \
                    and bool(verification.get('tls'))
                new_status = 'resolved' if resolved \
                    else 'verification_failed'
                db.execute(
                    "UPDATE sharpshooter_incidents SET status = ?,"
                    " action = ?, verification = ?, updated_at = ?"
                    " WHERE incident_id = ?;",
                    (new_status, rem['operation'],
                     json.dumps(verification, sort_keys=True), now,
                     rem['incident_id']))
                if verification.get('tls'):
                    db.execute(
                        "INSERT INTO sharpshooter_cert_inventory"
                        " (hostname, expires, subject_alt_names,"
                        " tls_version, last_seen) VALUES (?, ?, ?, ?, ?)"
                        " ON CONFLICT(hostname) DO UPDATE SET"
                        " expires = excluded.expires,"
                        " subject_alt_names = excluded.subject_alt_names,"
                        " tls_version = excluded.tls_version,"
                        " last_seen = excluded.last_seen;",
                        (incident['hostname'], verification.get('expires'),
                         json.dumps(verification.get(
                             'subject_alt_names', []), sort_keys=True),
                         verification.get('tls_version'), now))
                db.execute(
                    "UPDATE sharpshooter_remediations SET"
                    " mode = 'EXECUTED', outcome = ?, updated_at = ?"
                    " WHERE remediation_id = ?;",
                    (new_status, now, remediation_id))
                self._record('SHARPSHOOTER_REMEDIATION_EXECUTED',
                             actor=actor, remediation_id=remediation_id,
                             incident_id=rem['incident_id'],
                             operation=rem['operation'],
                             result=new_status)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._remediation_view(
                self._remediation_row(db, remediation_id))

    def rollback_remediation(self, actor, remediation_id) -> dict:
        """Roll an executed remediation back to the incident's
        pre-execution recorded state. Record-level rollback: the
        recovered plan captured the prior state before execution,
        and that state is what is restored, receipted."""
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                rem = self._remediation_row(db, remediation_id)
                if rem['mode'] != 'EXECUTED':
                    raise SharpshooterDenied(
                        'Only an executed remediation may roll back')
                if rem['rolled_back']:
                    raise SharpshooterDenied(
                        'Remediation is already rolled back')
                pre = json.loads(rem['pre_state'])
                db.execute(
                    "UPDATE sharpshooter_incidents SET status = ?,"
                    " action = ?, verification = ?, updated_at = ?"
                    " WHERE incident_id = ?;",
                    (pre['status'], pre['action'],
                     (json.dumps(pre['verification'], sort_keys=True)
                      if pre['verification'] is not None else None),
                     now, rem['incident_id']))
                db.execute(
                    "UPDATE sharpshooter_remediations SET"
                    " rolled_back = 1, outcome = 'rolled_back',"
                    " updated_at = ? WHERE remediation_id = ?;",
                    (now, remediation_id))
                self._record('SHARPSHOOTER_REMEDIATION_ROLLED_BACK',
                             actor=actor, remediation_id=remediation_id,
                             incident_id=rem['incident_id'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._remediation_view(
                self._remediation_row(db, remediation_id))

    def remediation_view(self, actor, role, remediation_id) -> dict:
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'REMEDIATION',
                              remediation_id, purpose='remediation view')
        except FoundationForbidden as exc:
            raise SharpshooterForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SharpshooterDenied(str(exc)) from exc
        with self._connect() as db:
            return self._remediation_view(
                self._remediation_row(db, remediation_id))

    # -- job queue --------------------------------------------------------

    @staticmethod
    def _job_view(row):
        return {
            'job_id': row['job_id'],
            'job_type': row['job_type'],
            'hostname': row['hostname'],
            'state': row['state'],
            'incident_id': row['incident_id'],
            'detail': row['detail'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    def enqueue_job(self, actor, hostname, job_type='DIAGNOSE') -> dict:
        self._check_actor(actor)
        if job_type not in JOB_TYPES:
            raise SharpshooterDenied(f'Unknown job type: {job_type!r}')
        if not isinstance(hostname, str) or not hostname.strip() \
                or any(c in hostname for c in '/:@?# ') \
                or len(hostname) > 253:
            raise SharpshooterDenied('hostname must be a DNS name')
        now = self._now()
        job_id = 'job-' + secrets.token_urlsafe(12)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                db.execute(
                    "INSERT INTO sharpshooter_jobs (job_id, job_type,"
                    " hostname, state, incident_id, detail, created_by,"
                    " created_at, updated_at) VALUES (?, ?, ?,"
                    " 'PENDING', NULL, NULL, ?, ?, ?);",
                    (job_id, job_type, hostname, actor, now, now))
                self._record('SHARPSHOOTER_JOB_ENQUEUED', actor=actor,
                             job_id=job_id, hostname=hostname)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sharpshooter_jobs WHERE job_id = ?',
                (job_id,)).fetchone()
            return self._job_view(row)

    def jobs(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sharpshooter_jobs ORDER BY created_at,'
                ' job_id').fetchall()
        return [self._job_view(r) for r in rows]

    def process_next_job(self, actor) -> dict | None:
        """Claim the oldest pending job atomically and run it: the
        claim and the work land in one transaction, so two workers
        can never process the same job."""
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    "SELECT * FROM sharpshooter_jobs"
                    " WHERE state = 'PENDING' ORDER BY created_at,"
                    " job_id LIMIT 1;").fetchone()
                if row is None:
                    db.commit()
                    return None
                db.execute(
                    "UPDATE sharpshooter_jobs SET state = 'CLAIMED',"
                    " updated_at = ? WHERE job_id = ?;",
                    (now, row['job_id']))
                incident_id = self._run_diagnosis(
                    db, actor, row['hostname'])
                db.execute(
                    "UPDATE sharpshooter_jobs SET state = 'COMPLETED',"
                    " incident_id = ?, updated_at = ?"
                    " WHERE job_id = ?;",
                    (incident_id, self._now(), row['job_id']))
                self._record('SHARPSHOOTER_JOB_COMPLETED', actor=actor,
                             job_id=row['job_id'],
                             incident_id=incident_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM sharpshooter_jobs WHERE job_id = ?',
                (row['job_id'],)).fetchone()
            return self._job_view(row)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            incident_counts = {s: 0 for s in INCIDENT_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' sharpshooter_incidents GROUP BY status'):
                incident_counts[row['status']] = row['n']
            job_counts = {s: 0 for s in JOB_STATES}
            for row in db.execute(
                    'SELECT state, COUNT(*) AS n FROM sharpshooter_jobs'
                    ' GROUP BY state'):
                job_counts[row['state']] = row['n']
            adapters = db.execute(
                'SELECT COUNT(*) AS n FROM sharpshooter_adapters'
            ).fetchone()['n']
            certs = db.execute(
                'SELECT COUNT(*) AS n FROM sharpshooter_cert_inventory'
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'incident_counts': incident_counts,
            'job_counts': job_counts,
            'adapters_registered': adapters,
            'cert_inventory_entries': certs,
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
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
                    raise SharpshooterDenied(str(exc)) from exc
                self._record('SHARPSHOOTER_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
