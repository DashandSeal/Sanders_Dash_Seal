"""
Module: core_platform.grantwriter_service
Architectural Layer: Grantwriter — platform service layer (fourth
workstream, Three Originals Reconstruction Program; owner directive
2026-11-24 08:02 MST: Grantwriter must be deployed too, and must be
upgraded to its maximum level).

"Maximum level" for this build — stated exactly, invented nowhere
beyond the record: Set B (sanders-global-platforms
database_schema.sql) records Grantwriter at logic_level 12, the
maximum of that schema's 1-12 CHECK range, tier_category
'professional'. Set C places Grantwriter in Tier 4 (Financial &
Legal). Maximum level here therefore means: the complete designed
scope implemented at that recorded top level — the full
data/draft/export scope of the existing modules PLUS the
designed-but-absent scope (submission workflow; portfolio
management; the grant-compliance evaluation named in Set C; the
public surface is the surface pass's job, not this module's) PLUS
all five shared ecosystem requirements (Glass-Box receipts,
session/platform identity via the shared foundation, jurisdiction
geofence, check-in records, and the access guard).

RECOVERED vs REBUILT — the discipline of this module is absolute:

RECOVERED (pre-existing base, used as-is, not edited by this
build):
* The existing Grantwriter data module in ``app/`` (its
  filename is a pre-existing repo fact, not used as a name
  anywhere in this module's surface) and
  ``core_platform/grantwriter_llm.py`` — the existing Grantwriter
  data/draft modules. Their own record labels them
  REBUILT-NOT-RESTORED (2026-11-13): they are the pre-existing
  base this service composes, NOT originals, and they are not
  claimed as recovered originals here.
* The registry entry for id 'grantwriter' in
  ``core_platform/ai_platform_links.json`` ("Grantwriter: grant
  opportunity and application management backed by local
  SQLite", endpoint local://sqlite). That entry names no legal
  entity, so this platform's legal_entities is ().
* The Set B level record above and the Set C tier record above.

REBUILT (this build, 2026-11-24): this service layer
(``GrantwriterPlatform``), the application submission workflow,
the portfolio view, the local grant-compliance evaluation (the
Set C record's 'grant-compliance' edge function itself is NOT
recovered — this is a local implementation of the evaluation it
names), and the shared-requirements integration (identity,
geofence, access guard, Glass-Box receipts, check-in).

Pricing: the records conflict — Set B records a final price of
$4,000,000 and Set C records $396,000,000/yr. That conflict is
UNRESOLVED, is the owner's to settle, and this module carries NO
price.

Gates untouched: the ``grantwriter_purpose`` approval gate in
``core_platform/ai_platform_approval.py`` /
``ai_platform_approvals.json`` is UNAPPROVED at this build. Live
draft generation is refused until that gate is approved; nothing
in this module flips, bypasses, or re-reads around any gate.

Cross-store atomicity — the documented Phase B residual class,
named, not hidden: the base Grantwriter store and this service's
own workflow store are two separate SQLite stores. A base-layer
create commits in the base store BEFORE this service writes its
Glass-Box receipt (and, for applications, its workflow row) in
its own transaction. If that receipt write fails, the operation
raises and the workflow row rolls back, but the already-committed
base row is NOT rolled back — cross-store atomicity is not
claimed. Within this service's own store, every mutation runs
under BEGIN IMMEDIATE with its receipt inside the critical
section, following the core_platform.rooms discipline.

``record_submission`` is a RECORDED state only: it records an
operator-supplied external reference for an application. This
service transmits NOTHING anywhere — no submission to any funder
or external system is made, claimed, or implied.

Base-layer API adaptation (read from the real module): the base
data layer has no store class. It is a module of functions taking
a SQLite connection ``c`` (from its ``database()`` factory, which
reads the SANDERS_GRANTWRITER_DB environment variable) plus an
``owner`` string, plus a body dict. Accordingly ``base_store``
here is that connection, constructed by the CALLER the real way,
and the service passes the acting actor as the base layer's
``owner`` for owner-scoped operations. Base function mapping:
create_opportunity -> create_opportunity(c, owner, body);
create_application -> create_application(c, owner, body);
add_budget_line -> add_budget_line(c, owner, body);
attach_evidence -> add_evidence(c, owner, body) (the base name is
add_evidence); reads -> list_opportunities / list_applications /
get_application(c, owner, ...); drafts -> generate_draft(c,
owner, application_id, generator=...).
"""

import sqlite3
import time
from pathlib import Path

from app import grantwriter_mother

from .ai_platform_approval import (  # noqa: E402
    ApprovalRequiredError,
    guarded_grantwriter_generation,
)
from .rtsa_foundation import (  # noqa: E402
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


class GrantwriterPlatformDenied(ValueError):
    """The requested Grantwriter operation is invalid or not permitted."""


class GrantwriterPlatformForbidden(ValueError):
    """The actor lacks authority for this Grantwriter operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='grantwriter',
    name='Grantwriter',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='UPGRADED',
))

DESIGNED_LEVEL = {
    'logic_level': 12,
    'scale': '1-12',
    'source': 'Set B database_schema.sql seed (sanders-global-platforms)',
    'tier_category': 'professional',
    'set_c_tier': 'Tier 4 — Financial & Legal',
}

WORKFLOW_STAGES = (
    'DRAFT', 'IN_REVIEW', 'READY', 'SUBMITTED',
    'AWARDED', 'DECLINED', 'CLOSED',
)

# Checked workflow lifecycle. SUBMITTED is entered only via
# record_submission (a recorded external reference), never via a
# bare stage transition. AWARDED / DECLINED / CLOSED are terminal.
_TRANSITIONS = {
    'DRAFT': frozenset(('IN_REVIEW',)),
    'IN_REVIEW': frozenset(('READY',)),
    'READY': frozenset(('IN_REVIEW', 'SUBMITTED', 'AWARDED', 'DECLINED', 'CLOSED')),
    'SUBMITTED': frozenset(('AWARDED', 'DECLINED', 'CLOSED')),
    'AWARDED': frozenset(),
    'DECLINED': frozenset(),
    'CLOSED': frozenset(),
}


class GrantwriterPlatform:
    """Grantwriter at its recorded maximum level: a platform
    service layer composing the pre-existing Grantwriter data and
    draft modules with a submission workflow, a portfolio view, a
    local grant-compliance evaluation, and the shared ecosystem
    requirements (identity, geofence, access guard, Glass-Box
    receipts, check-in)."""

    def __init__(self, database, base_store, operator_verifier=None,
                 audit=None, approval_checker=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise GrantwriterPlatformDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        if base_store is None:
            raise GrantwriterPlatformDenied(
                'A base Grantwriter store is required: the caller '
                'constructs it from the existing data layer')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        # base_store: the existing data layer's SQLite connection,
        # constructed by the caller via its database() factory.
        self.base = base_store
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.approval_checker = approval_checker
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'grantwriter', {
            'OPERATOR': {'OPPORTUNITY', 'APPLICATION', 'PORTFOLIO',
                         'COMPLIANCE'},
            'AUDITOR': {'OPPORTUNITY', 'APPLICATION', 'PORTFOLIO',
                        'COMPLIANCE'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS application_workflow (
                application_id TEXT PRIMARY KEY,
                jurisdiction TEXT NOT NULL,
                stage TEXT NOT NULL,
                external_ref TEXT,
                updated_by TEXT NOT NULL,
                updated_at INTEGER NOT NULL
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
            raise GrantwriterPlatformDenied('Invalid actor identity')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    def _geofence(self, actor, jurisdiction):
        """ALLOW any actor; STEP_UP operator-only; DENY -> denied."""
        verdict = self.geofence.evaluate(jurisdiction)
        if verdict == 'DENY':
            raise GrantwriterPlatformDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        if verdict == 'STEP_UP' and not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Jurisdiction requires operator step-up verification')
        return verdict

    def _guard_access(self, actor, role, category, record_ref, purpose):
        try:
            return self.guard.access(actor, role, category, record_ref,
                                     purpose=purpose)
        except FoundationForbidden as exc:
            raise GrantwriterPlatformForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise GrantwriterPlatformDenied(str(exc)) from exc

    def _workflow_row(self, db, application_id):
        return db.execute(
            "SELECT * FROM application_workflow "
            "WHERE application_id = ?;", (application_id,)).fetchone()

    @staticmethod
    def _workflow_view(row):
        if row is None:
            return None
        return {
            'application_id': row['application_id'],
            'jurisdiction': row['jurisdiction'],
            'stage': row['stage'],
            'external_ref': row['external_ref'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
        }

    # -- base-layer operations ----------------------------------------

    def create_opportunity(self, actor, jurisdiction, **fields):
        """Create a grant opportunity through the base layer, behind
        the geofence, with a GRANTWRITER_OPPORTUNITY_CREATED
        receipt. Cross-store bound: see the module docstring."""
        self._check_actor(actor)
        self._geofence(actor, jurisdiction)
        result = grantwriter_mother.create_opportunity(
            self.base, actor, dict(fields))
        self._record('GRANTWRITER_OPPORTUNITY_CREATED', actor=actor,
                     opportunity_id=result['id'],
                     jurisdiction=jurisdiction)
        return result

    def create_application(self, actor, jurisdiction, **fields):
        """Create a draft application through the base layer, behind
        the geofence, plus a workflow row at DRAFT in this service's
        store and a GRANTWRITER_APPLICATION_CREATED receipt, inside
        the same operation. Cross-store bound: see docstring."""
        self._check_actor(actor)
        self._geofence(actor, jurisdiction)
        result = grantwriter_mother.create_application(
            self.base, actor, dict(fields))
        application_id = result['id']
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO application_workflow (application_id, "
                    "jurisdiction, stage, external_ref, updated_by, "
                    "updated_at) VALUES (?, ?, 'DRAFT', NULL, ?, ?);",
                    (application_id, jurisdiction, actor, now))
                self._record('GRANTWRITER_APPLICATION_CREATED',
                             actor=actor, application_id=application_id,
                             jurisdiction=jurisdiction)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return result

    def add_budget_line(self, actor, application_id, **fields):
        """Add a budget line via the base layer's add_budget_line,
        with a GRANTWRITER_BUDGET_LINE_ADDED receipt."""
        self._check_actor(actor)
        body = {'application_id': application_id, **fields}
        result = grantwriter_mother.add_budget_line(self.base, actor, body)
        self._record('GRANTWRITER_BUDGET_LINE_ADDED', actor=actor,
                     application_id=application_id,
                     budget_line_id=result['id'])
        return result

    def attach_evidence(self, actor, application_id, **fields):
        """Attach evidence via the base layer's add_evidence (the
        base name for this operation), with a
        GRANTWRITER_EVIDENCE_ATTACHED receipt."""
        self._check_actor(actor)
        body = {'application_id': application_id, **fields}
        result = grantwriter_mother.add_evidence(self.base, actor, body)
        self._record('GRANTWRITER_EVIDENCE_ATTACHED', actor=actor,
                     application_id=application_id,
                     evidence_id=result['id'])
        return result

    # -- workflow ------------------------------------------------------

    def stage_for(self, application_id):
        """The recorded workflow stage for an application, or None."""
        with self._connect() as db:
            row = self._workflow_row(db, application_id)
            return row['stage'] if row is not None else None

    def workflow_for(self, application_id):
        """The full workflow record for an application, or None."""
        with self._connect() as db:
            return self._workflow_view(self._workflow_row(db, application_id))

    def _transition_locked(self, db, actor, application_id, target,
                           external_ref=None):
        row = self._workflow_row(db, application_id)
        if row is None:
            raise GrantwriterPlatformDenied('Unknown application workflow')
        current = row['stage']
        if target not in _TRANSITIONS[current]:
            raise GrantwriterPlatformDenied(
                f'Transition {current}->{target} is not permitted')
        now = int(time.time())
        if external_ref is not None:
            db.execute(
                "UPDATE application_workflow SET stage = ?, "
                "external_ref = ?, updated_by = ?, updated_at = ? "
                "WHERE application_id = ?;",
                (target, external_ref, actor, now, application_id))
        else:
            db.execute(
                "UPDATE application_workflow SET stage = ?, "
                "updated_by = ?, updated_at = ? "
                "WHERE application_id = ?;",
                (target, actor, now, application_id))
        self._record('GRANTWRITER_STAGE_TRANSITION', actor=actor,
                     application_id=application_id,
                     from_stage=current, to_stage=target,
                     external_ref=external_ref)
        return self._workflow_view(self._workflow_row(db, application_id))

    def transition_stage(self, actor, application_id, target_stage):
        """One checked workflow stage transition (operator-only,
        fail-closed, receipt GRANTWRITER_STAGE_TRANSITION).
        SUBMITTED is not a bare transition: use record_submission."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Stage transitions are an operator authority')
        if target_stage not in WORKFLOW_STAGES:
            raise GrantwriterPlatformDenied(
                f'Unknown target stage: {target_stage!r}')
        if target_stage == 'SUBMITTED':
            raise GrantwriterPlatformDenied(
                'SUBMITTED is recorded only via record_submission '
                'with an external reference')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                view = self._transition_locked(
                    db, actor, application_id, target_stage)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return view

    def record_submission(self, actor, application_id, external_ref):
        """Record a submission: stage -> SUBMITTED with an
        operator-supplied external reference. RECORDED state only —
        this service transmits NOTHING anywhere; no submission to
        any funder or external system is made or implied.
        Operator-only, receipt GRANTWRITER_STAGE_TRANSITION."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Recording a submission is an operator authority')
        if not isinstance(external_ref, str) or not external_ref.strip():
            raise GrantwriterPlatformDenied(
                'A non-empty external reference is required')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._workflow_row(db, application_id)
                if row is None:
                    raise GrantwriterPlatformDenied(
                        'Unknown application workflow')
                if row['stage'] != 'READY':
                    raise GrantwriterPlatformDenied(
                        f"Submission may be recorded only from READY, "
                        f"not {row['stage']}")
                view = self._transition_locked(
                    db, actor, application_id, 'SUBMITTED',
                    external_ref=external_ref.strip())
                db.commit()
            except Exception:
                db.rollback()
                raise
            return view

    # -- draft generation (gate discipline is absolute) -----------------

    def generate_draft(self, actor, application_id, **kw):
        """Generate a draft for an application.

        mode='offline' (the default): the base module's designed
        offline default (FakeGenerator, or a caller-supplied
        offline generator via ``generator=``); the result is
        labeled mode='offline' and receipted as such.

        mode='live': live generation ONLY through the approval
        gate. When an approval_checker is bound, it must return
        True for 'grantwriter_purpose'; when none is bound, the
        existing guarded path in ai_platform_approval
        (guarded_grantwriter_generation, reading the real gate
        state — UNAPPROVED) decides. Either way, an unapproved
        gate raises GrantwriterPlatformDenied('grantwriter_purpose
        approval required') and NO live provider adapter is ever
        called without that check passing.
        """
        self._check_actor(actor)
        mode = kw.get('mode', 'offline')
        if mode == 'offline':
            generator = kw.get('generator') or grantwriter_mother.FakeGenerator()
            result = grantwriter_mother.generate_draft(
                self.base, actor, application_id, generator=generator)
            out = dict(result)
            out['mode'] = 'offline'
            self._record('GRANTWRITER_DRAFT_GENERATED', actor=actor,
                         application_id=application_id, mode='offline',
                         generator=out.get('generator'))
            return out
        if mode != 'live':
            raise GrantwriterPlatformDenied(f'Unknown draft mode: {mode!r}')
        # Live mode: gate check first, before any generator exists
        # in a callable path.
        if self.approval_checker is not None:
            try:
                approved = self.approval_checker('grantwriter_purpose') is True
            except Exception:
                approved = False
            if not approved:
                raise GrantwriterPlatformDenied(
                    'grantwriter_purpose approval required')
            live_generator = kw.get('generator') or kw.get('live_generator')
            if live_generator is None:
                raise GrantwriterPlatformDenied(
                    'Live draft generation is approved but no live '
                    'generator was supplied; no live call was made')
            result = grantwriter_mother.generate_draft(
                self.base, actor, application_id, generator=live_generator)
        else:
            live_generator = kw.get('generator') or kw.get('live_generator')
            if live_generator is None:
                # Still route through the guarded path so the gate
                # refusal is the real one; with no generator the
                # guarded callable is never reached while unapproved.
                def _no_live_generator():
                    raise GrantwriterPlatformDenied(
                        'Live draft generation is approved but no live '
                        'generator was supplied; no live call was made')
                try:
                    guarded_grantwriter_generation(_no_live_generator)
                except ApprovalRequiredError as exc:
                    raise GrantwriterPlatformDenied(
                        'grantwriter_purpose approval required') from exc
                raise GrantwriterPlatformDenied(
                    'Live generator was not supplied')  # pragma: no cover
            def _run():
                return grantwriter_mother.generate_draft(
                    self.base, actor, application_id,
                    generator=live_generator)
            try:
                result = guarded_grantwriter_generation(_run)
            except ApprovalRequiredError as exc:
                raise GrantwriterPlatformDenied(
                    'grantwriter_purpose approval required') from exc
        out = dict(result)
        out['mode'] = 'live'
        self._record('GRANTWRITER_DRAFT_GENERATED', actor=actor,
                     application_id=application_id, mode='live',
                     generator=out.get('generator'))
        return out

    # -- portfolio (Set C portfolio management, REBUILT) ----------------

    def portfolio_view(self, actor, role):
        """Portfolio aggregates computed from the base store's real
        read API (list_opportunities / list_applications /
        get_application), behind the PORTFOLIO access guard. No
        figure is invented: every number is counted or summed from
        stored rows for the acting owner."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'PORTFOLIO', 'portfolio',
                           purpose='portfolio view')
        opportunities = grantwriter_mother.list_opportunities(self.base, actor)
        applications = grantwriter_mother.list_applications(self.base, actor)
        by_status = {}
        total_cents = 0
        for app in applications:
            by_status[app['status']] = by_status.get(app['status'], 0) + 1
            full = grantwriter_mother.get_application(
                self.base, actor, app['id'])
            total_cents += sum(
                line.get('amount_cents', 0)
                for line in full.get('budget_lines', []))
        return {
            'platform_id': IDENTITY.platform_id,
            'opportunities': {
                'total': len(opportunities),
                'total_ceiling_cents': sum(
                    o.get('ceiling_cents', 0) for o in opportunities),
            },
            'applications': {
                'total': len(applications),
                'by_status': by_status,
            },
            'total_application_amount_cents': total_cents,
        }

    # -- compliance evaluation (Set C 'grant-compliance', REBUILT local) --

    def compliance_evaluate(self, actor, role, application_id):
        """Local grant-compliance evaluation for one application,
        behind the COMPLIANCE access guard. Checks are computed
        from the base store: the application exists; it has at
        least one budget line; at least one evidence item; a
        narrative is present; its total budget is > 0 cents; and a
        workflow stage is recorded in this service's store.
        Receipt GRANTWRITER_COMPLIANCE_EVALUATED."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'COMPLIANCE', application_id,
                           purpose='grant-compliance evaluation')
        try:
            full = grantwriter_mother.get_application(
                self.base, actor, application_id)
        except ValueError:
            full = None
        if full is None:
            checks = {
                'application_exists': False,
                'has_budget_line': False,
                'has_evidence': False,
                'narrative_present': False,
                'total_budget_positive': False,
                'workflow_stage_recorded': False,
            }
        else:
            total_cents = sum(
                line.get('amount_cents', 0)
                for line in full.get('budget_lines', []))
            checks = {
                'application_exists': True,
                'has_budget_line': len(full.get('budget_lines', [])) >= 1,
                'has_evidence': len(full.get('evidence', [])) >= 1,
                'narrative_present': bool(
                    str(full.get('narrative') or '').strip()),
                'total_budget_positive': total_cents > 0,
                'workflow_stage_recorded':
                    self.stage_for(application_id) is not None,
            }
        result = {
            'application_id': application_id,
            'checks': checks,
            'passed': all(checks.values()),
        }
        self._record('GRANTWRITER_COMPLIANCE_EVALUATED', actor=actor,
                     application_id=application_id,
                     passed=result['passed'])
        return result

    # -- check-in --------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with receipt GRANTWRITER_CHECK_IN inside the
        transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise GrantwriterPlatformDenied(str(exc)) from exc
                self._record('GRANTWRITER_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    # -- status ------------------------------------------------------------

    def _base_counts(self):
        counts = {'opportunities': 0, 'applications': 0}
        try:
            for table in counts:
                row = self.base.execute(
                    f"SELECT COUNT(*) FROM {table};").fetchone()  # noqa: S608
                counts[table] = int(row[0])
        except Exception:
            return counts
        return counts

    def _gate_state(self):
        if self.approval_checker is None:
            return 'UNAPPROVED (no checker bound)'
        try:
            approved = self.approval_checker('grantwriter_purpose') is True
        except Exception:
            approved = False
        return 'APPROVED' if approved else 'UNAPPROVED'

    def status(self):
        """Platform status: identity, the designed level record,
        workflow stage counts, base-store counts, the generation
        gate state, and the latest check-in."""
        stage_counts = {stage: 0 for stage in WORKFLOW_STAGES}
        with self._connect() as db:
            for row in db.execute(
                    "SELECT stage, COUNT(*) AS n FROM "
                    "application_workflow GROUP BY stage;").fetchall():
                if row['stage'] in stage_counts:
                    stage_counts[row['stage']] = row['n']
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'designed_level': dict(DESIGNED_LEVEL),
            'workflow_stage_counts': stage_counts,
            'base_counts': self._base_counts(),
            'generation_gate': {
                'grantwriter_purpose': self._gate_state(),
            },
            'latest_check_in': latest,
        }


__all__ = [
    'DESIGNED_LEVEL',
    'IDENTITY',
    'WORKFLOW_STAGES',
    'GrantwriterPlatform',
    'GrantwriterPlatformDenied',
    'GrantwriterPlatformForbidden',
]
