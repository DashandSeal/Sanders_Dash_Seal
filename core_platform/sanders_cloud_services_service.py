"""Sanders Cloud Services — the cloud
services platform.

The production build-out of the Sanders Cloud
Services design (canonical catalog row #124,
Band 2D), built whole as its own platform
service over the shared RTSA foundation (RTSA
Build Program Q92).

NAME — verified before building, per the name
law: the canonical catalog (row #124) and Set C
Tier 7 name this platform **Sanders Cloud
Services** — the queue-note reading matched the
source name exactly. Set B carries NO entry
under this name (verified by direct read of the
schema and the tier pricing file), and Set A
carries no entry for this platform (verified by
direct read of the platform registry); the
MASTER names it nowhere. Set C's tier catalog
entry is the platform's only design record.
Set C classifies the entry "Secret" —
recorded exactly as found; the build exposes no
security internals and no public surface
regardless.

NICKNAME — RECORDED, NOT ADOPTED: Set C's
nickname for this platform is "Sky". It is
recorded exactly as found and is not adopted as
the platform's persona, name, or identifier.

Set C's purpose text for this name — "Cloud
infrastructure, AWS/Azure/Google replacement,
FedRAMP authorized, multi-cloud mastery" — is
recorded verbatim as found and is NOT the built
scope beyond governed cloud-services records:
no cloud is provisioned, nothing is deployed to
any cloud, no workload is migrated, and no
cloud account is held or modified by this
build. The "replacement" and "mastery" wording
is design-record language, not a claim.
FedRAMP authorization is a real United States
federal authorization: this platform holds no
FedRAMP authorization and claims none — the
design text is recorded as found, nothing more.

CORE LAW 10 TENSION — RECORDED AS FOUND, NEVER
HARMONIZED: Set C's purpose text speaks of
replacing AWS, Azure, and Google and of
multi-cloud mastery. The ecosystem's build and
deploy law — Core Law 10 (Oracle Always Free
only) and Core Law 11, and the owner's ruling
of 2026-11-24 ("we aren't moving from Oracle
that was never part of the plan") — makes
Oracle Always Free the permanent home. The
tension between the design text and the law
stands in this record exactly as found; the
build follows the law: this platform creates
no dependency on any paid cloud service,
integrates with no AWS, Azure, or Google
account, and runs on the ecosystem's Oracle
Always Free posture like every platform in
this program. The designed hostname
cloud.sandersglobal.com (Set C registry
record) sits under the unowned parent
sandersglobal.com, so it is recorded and
nothing is served there.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is never
described as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — cloud infrastructure and
multi-cloud services (canonical catalog row
#124; Set C Tier 7 — the platform's only design
record; Set B carries no row). No Sanders Cloud
Services module existed in any examined source.

REBUILT (everything executable in this module):
the governed platform below — the Sanders Cloud
Services platform's own identity and store,
carrying cloud-services records:

- **Cloud-services records**: a subject
  reference (a cloud service estate, hosting
  arrangement, or migration program under
  service, by reference), a declared set of
  service references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED
  by a human operator's recorded decision, then
  an outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The service discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set
  (CLOUD_SERVICES_POSITION_CONFIRMED /
  CLOUD_SERVICE_ACTION_REQUIRED / INCONCLUSIVE).
  A record declared with no services stands
  NO_SERVICES_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no services were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never provisioning**: determinations
  are records placed before human operators. The
  platform provisions no cloud, deploys to no
  cloud, migrates no workload, and modifies no
  cloud account — provision_cloud,
  deploy_to_cloud, migrate_workload,
  modify_cloud_account, and external_execution
  are refused by name under
  CLOUD_SERVICES_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  services are carried by reference only; the
  platform holds no cloud credentials, no
  provider account state, no workload content,
  and no live-system state — references and
  workflow state only, as across the ecosystem.
  No public or customer surface is designed for
  this platform in any examined source, so none
  was built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source (no Set B row;
  no Set A entry; no Set C registry NAICS map
  entry) — NO NAICS set is carried into the
  platform's built identity and none is invented.
- **Separation**: the Sanders Cloud Services
  platform is its own platform. It is not
  Sanders Infrastructure (catalog #122), not
  Sanders Technology (catalog #123), not the
  Infrastructure Agent (catalog #46), and not
  the Vault (catalog #22 — TwinGate's internal
  token vault, not a cloud service); it is not
  Oracle Cloud either — it provisions nothing
  and administers no tenancy. Identities are
  never merged.

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
    platform_id='sanders_cloud_services',
    name='Sanders Cloud Services',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Cloud infrastructure services'
DISCIPLINE = 'CLOUD_SERVICES_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_cloud_services', 'approve_cloud_services', 'record_outcome',
    'view_cloud_services', 'view_design')
EXECUTION_OPERATIONS = ('provision_cloud', 'deploy_to_cloud',
    'migrate_workload', 'modify_cloud_account',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('CLOUD_SERVICES_POSITION_CONFIRMED', 'CLOUD_SERVICE_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('CLOUD_SERVICES_POSITION_CONFIRMED', 'CLOUD_SERVICE_ACTION_REQUIRED')
MAX_REFS = 100


class SandersCloudServicesDenied(Exception):
    """The requested Sanders Cloud Services operation is not
    allowed."""


class SandersCloudServicesForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersCloudServicesService:
    """Sanders Cloud Services: governed cloud-services records under the cloud services records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersCloudServicesDenied(
                'Sanders Cloud Services requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_cloud_services', {
            'OPERATOR': {'SANDERS_CLOUD_SERVICES'},
            'AUDITOR': {'SANDERS_CLOUD_SERVICES'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_cloud_services_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    service_refs TEXT NOT NULL,
                    service_count INTEGER NOT NULL,
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
            raise SandersCloudServicesForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersCloudServicesForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersCloudServicesForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_CLOUD_SERVICES',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersCloudServicesForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersCloudServicesDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #124', 'Set C Tier 7 catalog entry (read directly) — the platform’s only design record', 'Set B: no entry under this name (verified by direct read); Set A carries no entry (platform registry read directly); the MASTER names it nowhere', 'Core Law 10 and Core Law 11 (repo AGENTS.md) and the owner’s 2026-11-24 ruling — Oracle Always Free is the permanent home; Set C’s multi-cloud purpose text is recorded as found, never harmonized', 'decisions.md: no ruling names this platform; the Sanders Infrastructure (catalog #122) and Vault (catalog #22) identities stay separate'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'Sanders Cloud Services is the cloud services platform: it carries governed cloud-services records over cloud service estates, hosting arrangements, and migration programs and declared service sets presented by reference only. Set C’s purpose text for this name — Cloud infrastructure, AWS/Azure/Google replacement, FedRAMP authorized, multi-cloud mastery — is recorded verbatim as found and is NOT the built scope: no cloud is provisioned, nothing is deployed to any cloud, no workload is migrated, and no cloud account is held or modified by this build; the replacement and mastery wording is design-record language, not a claim, and this platform holds no FedRAMP authorization and claims none. CORE LAW 10 TENSION — RECORDED AS FOUND, NEVER HARMONIZED: the design text’s multi-cloud and replacement language stands against Core Law 10 and Core Law 11 (Oracle Always Free is the permanent home; the owner’s 2026-11-24 ruling: we aren’t moving from Oracle); the build follows the law — no dependency on any paid cloud service is created and no AWS, Azure, or Google account is integrated. The platform provisions no cloud, deploys to no cloud, migrates no workload, and modifies no cloud account: provision_cloud, deploy_to_cloud, migrate_workload, modify_cloud_account, and external_execution are refused by name under CLOUD_SERVICES_RECORDS_ONLY, and determinations are records for human operators, never provisioning. A record declared with no services stands NO_SERVICES_SUBMITTED and no determination can be recorded on it. NICKNAME — RECORDED, NOT ADOPTED: Set C’s nickname Sky is recorded exactly as found; it is not adopted as the platform’s persona, name, or identifier. Set C classifies the entry Secret — recorded as found. Set B carries NO entry under this name (verified by direct read), and Set A carries no entry for this platform. The designed hostname cloud.sandersglobal.com (Set C registry record) sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. No NAICS set is attested for this platform in any examined source, and none is carried or invented. The platform holds references and workflow state only — no cloud credentials, no provider account state, no workload content. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. Sanders Cloud Services is distinct from Sanders Infrastructure (catalog 122), Sanders Technology (catalog 123), the Infrastructure Agent (catalog 46), and the Vault (catalog 22) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the cloud services records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in EXECUTION_OPERATIONS:
            raise SandersCloudServicesDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Cloud Services platform'
                ' carries cloud services records'
                ' only \u2014 it provisions no'
                ' cloud, deploys to no cloud,'
                ' migrates no workload, and'
                ' modifies no cloud account itself'
                ' (CLOUD_SERVICES_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersCloudServicesDenied(
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
        operations = json.loads(row['service_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'service_refs': operations,
            'service_count': row['service_count'],
            'service_state': ('NO_SERVICES_SUBMITTED'
                             if row['service_count'] == 0
                             else 'SERVICES_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, service_refs,
                      scope_ref, *, region=None):
        """Record one cloud services record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_SERVICES_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record provisions no
        cloud, deploys nothing, and migrates
        no workload."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersCloudServicesDenied(
                    f'A {label} is required')
        if not isinstance(service_refs, (list, tuple)):
            raise SandersCloudServicesDenied(
                'service_refs must be a list of references')
        if len(service_refs) > MAX_REFS:
            raise SandersCloudServicesDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in service_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersCloudServicesDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-cloud-services-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_CLOUD_SERVICES_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    service_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_cloud_services_records'
                    ' (record_id, subject_ref, service_refs,'
                    ' service_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_cloud_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_cloud_services_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_cloud_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersCloudServicesDenied(
                'Cloud Services record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested cloud services record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersCloudServicesDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_cloud_services_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersCloudServicesDenied(
                        'Cloud Services record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersCloudServicesDenied(
                        f"Cannot {action} a cloud services record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_CLOUD_SERVICES_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_cloud_services_records SET status = ?,'
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
                'SELECT * FROM sanders_cloud_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (CLOUD_SERVICES_POSITION_CONFIRMED or CLOUD_SERVICE_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_SERVICES_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersCloudServicesDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersCloudServicesDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_cloud_services_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersCloudServicesDenied(
                        'Cloud Services record not found')
                if row['status'] != 'APPROVED':
                    raise SandersCloudServicesDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" cloud services records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['service_count'] == 0:
                    raise SandersCloudServicesDenied(
                        'NO_SERVICES_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_CLOUD_SERVICES_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_cloud_services_records SET status = ?,'
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
                'SELECT * FROM sanders_cloud_services_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_cloud_services_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_cloud_services_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_cloud_services_records'
                ' WHERE service_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(service_count), 0) AS n'
                ' FROM sanders_cloud_services_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_services_submitted': no_refs,
            'services_declared_total': refs_total,
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
                    raise SandersCloudServicesDenied(str(exc)) from exc
                self._record('SANDERS_CLOUD_SERVICES_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
