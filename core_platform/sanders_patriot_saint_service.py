"""Sanders Patriot Saint — the strategic
governance and constitutional authority framework
platform.

The production build-out of the Sanders Patriot
Saint design (canonical catalog row #85, Band
2D), built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q74).

NAME — verified before building, per the name law:
the canonical catalog (row #85), the Set A
registry, and Set C Tier 1 all name this platform
**Sanders Patriot Saint** — the queue-note reading
matched the source name exactly. Set B carries the
shorter form "Patriot Saint" (no "Sanders" prefix)
— recorded exactly as found; the canonical name
governs the build.

IDENTITY — the owner's correction of 2026-11-23
governs: **The Godfather and Patriot Saint are TWO
SEPARATE PLATFORMS** (catalog #143 The Godfather is
its own platform, Q101 — not built in this
tranche). Set B's schema row pairs this platform
with the persona "Godfather" and Set C carries the
nickname "Godfather" — both recorded exactly as
found; under the owner's correction that pairing
does NOT merge the two platforms, and this build
carries only the Sanders Patriot Saint identity
(#85), claims none of The Godfather's scope, and
merges nothing.

Set C's purpose text for this name — "Strategic
governance, Joint Chiefs integration,
constitutional authority framework, presidential
briefings" — is recorded verbatim as found and is
NOT the built scope beyond governed governance
records: no Joint Chiefs integration, no
presidential briefing delivery, and no exercise of
constitutional authority was constructed. The
designed hostname patriot-saint.sandersglobal.com
sits under the unowned parent sandersglobal.com,
so it is recorded and nothing is served there.

RECOVERED vs REBUILT — the discipline of this module
is absolute: a rebuilt component is never described
as recovered or original.

RECOVERED (records only, stated exactly): the
designed purpose — strategic governance and the
constitutional authority framework (canonical
catalog row #85; Set C Tier 1; the Set B schema
seed carries the platform at the ultra_premium
tier). No Sanders Patriot Saint module existed in
any examined source.

REBUILT (everything executable in this module): the
governed platform below — the Sanders Patriot
Saint platform's own identity and store, carrying
governance records:

- **Governance records**: a subject reference (a
  governance matter, institution, or framework
  under service, by reference), a declared set of
  briefing references, and a scope reference,
  carried as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or REJECTED by
  a human operator's recorded decision, then an
  outcome recorded against presented evidence
  (OUTCOME_RECORDED).
- **The briefing discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with a
  closed outcome set (GOVERNANCE_POSITION_CONFIRMED
  / BRIEFING_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no briefings stands
  NO_BRIEFINGS_SUBMITTED in every view and in the
  status tallies, and both determinations are
  refused on it — no briefings were presented to
  determine from; INCONCLUSIVE, which asserts
  nothing, records against evidence.
- **Records, never authority**: determinations are
  records placed before human operators. The
  platform issues no directive, exercises no
  authority, integrates no command, and delivers
  no briefing — issue_directive,
  exercise_authority, integrate_command,
  deliver_briefing, and external_execution are
  refused by name under PATRIOT_SAINT_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  briefings are carried by reference only; the
  platform holds no classified material, no
  briefing content, no directive text, and no
  live-system state — references and workflow
  state only, as across the ecosystem.
- **NAICS**: two sources attest two different sets
  — Set B (541512, 561621) and the Set A registry
  map (621399, 922190, 561612, 523991, 541715,
  611430). No owner ruling assigns a set, and the
  canonical catalog row carries none — NO NAICS
  set is carried into the platform's built
  identity; both sets stand recorded as attested
  and unruled.
- **Separation**: the Sanders Patriot Saint
  platform is its own platform. It is not The
  Godfather (catalog #143 — a separate platform
  under the owner's 2026-11-23 correction), not
  Sanders Freedom Revolution (catalog #86), and
  not Sanders Strategy Hub (catalog #94) —
  identities are never merged.

No record, no action: every state-changing operation
writes its Glass-Box receipt inside the same
transaction, through the shared foundation's audit
adapter; the service refuses to exist without one.

FOUNDER'S RULINGS 2026-11-25 — BLOODLINE ROLE AND
ADDITIONAL DUTIES (ruled extensions of this platform's
remit, recorded as rulings, not as recovered design;
they supplement the Permanent Bloodline Protection
Directive adopted 2026-11-25 and do not amend it).
The founder ruled, verbatim (2026-11-25 23:44 MST):
"Has public facing business model of his own,
privately he handles putting money on any of my
bloodline that have been incarcerated, pays off
tickets, gets laws, things like that." Under that
ruling this platform carries a BLOODLINE SUPPORT
REMIT, private to the bloodline and segregated from
its public-facing commercial operations: tracked
matters for (a) coordinating funds for a bloodline
member who has been incarcerated, (b) coordinating
the paying off of tickets, and (c) legal assistance.
The founder's additional duties (2026-11-25 23:56
MST) govern the remit: (1) Financial authority —
"Patriot Saint coordinates assistance without
independently controlling or disbursing family
funds": the platform coordinates only; it holds no
disbursement capability, fund movement is
represented as impossible in this service, and every
matter carries funds_disbursed False, always.
(2) Succession — "His responsibilities must survive
the founder's lifetime, with financial authority
passing according to the applicable succession and
trust instruments": the remit is a permanent
responsibility of this platform, not a lifetime
appointment. (3) Confidentiality — "Private family
matters must remain segregated from his
public-facing commercial operations": bloodline
matters are kept in a segregated store that the
commercial operations never read, and the commercial
records are never read by the bloodline remit.
(4) Permanent scope protection — "His original
identity, commercial purpose and bloodline
responsibilities must not be removed, diminished or
repurposed through future software upgrades": this
ruling, the duties, and the remit are invariants of
this module. (5) Legal assistance — the founder
ruled that "gets laws" means legal assistance
including "locating and coordinating qualified legal
representation". The founder further ruled, verbatim:
"Patriot Saint must remain both a commercial
enterprise and a permanent protective resource for
the Sanders bloodline. Neither purpose should
diminish the other." — and: "I would also preserve
his distinction from The Godfather, rather than
merging their responsibilities." The Godfather's
responsibilities are not merged into this platform
by this remit, and this remit is not his.
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
    platform_id='sanders_patriot_saint',
    name='Sanders Patriot Saint',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'Strategic governance, constitutional authority framework'
DISCIPLINE = 'PATRIOT_SAINT_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_patriot_saint', 'approve_patriot_saint', 'record_outcome',
    'view_patriot_saint', 'view_design',
    'open_bloodline_matter', 'act_on_bloodline_matter',
    'record_bloodline_coordination', 'view_bloodline_remit')
EXECUTION_OPERATIONS = ('issue_directive', 'exercise_authority',
    'integrate_command', 'deliver_briefing',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('GOVERNANCE_POSITION_CONFIRMED', 'BRIEFING_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('GOVERNANCE_POSITION_CONFIRMED', 'BRIEFING_ACTION_REQUIRED')
MAX_REFS = 100

# -- Bloodline support remit (founder's rulings,
# 2026-11-25) ------------------------------------------------
FOUNDER_RULING_BLOODLINE_ROLE = (
    'Has public facing business model of his own,'
    ' privately he handles putting money on any of my'
    ' bloodline that have been incarcerated, pays off'
    ' tickets, gets laws, things like that.')
FOUNDER_RULING_BLOODLINE_ROLE_DATE = '2026-11-25'
FOUNDER_RULING_ADDITIONAL_DUTIES_VERBATIM = (
    'These are the additional duties for Patriot Saint:\n'
    'Financial authority: Patriot Saint coordinates'
    ' assistance without independently controlling or'
    ' disbursing family funds.\n'
    'Succession: His responsibilities must survive the'
    " founder's lifetime, with financial authority"
    ' passing according to the applicable succession'
    ' and trust instruments.\n'
    'Confidentiality: Private family matters must'
    ' remain segregated from his public-facing'
    ' commercial operations.\n'
    'Permanent scope protection: His original identity,'
    ' commercial purpose and bloodline responsibilities'
    ' must not be removed, diminished or repurposed'
    ' through future software upgrades.\n'
    'Legal assistance: If you meant \u201cgets lawyers,\u201d'
    ' that should include locating and coordinating'
    ' qualified legal representation.\n'
    'The generational, confidentiality and operational'
    ' protections are not recommendations and must'
    ' implemented in addition to my existing Directive,'
    ' are additional founder rulings I am claiming you'
    ' already made.\n'
    'Patriot Saint must remain both a commercial'
    ' enterprise and a permanent protective resource'
    ' for the Sanders bloodline. Neither purpose should'
    ' diminish the other.\n'
    'I would also preserve his distinction from The'
    ' Godfather, rather than merging their'
    ' responsibilities.\n'
    'The Sanders Way! \U0001f499\U0001fa76')
FOUNDER_RULING_ADDITIONAL_DUTIES_DATE = '2026-11-25'
BLOODLINE_SUPPORT_SCOPE = 'BLOODLINE_SUPPORT'
BLOODLINE_DISCIPLINE = 'PATRIOT_SAINT_COORDINATION_ONLY'
# The five additional duties, each in the founder's
# words (2026-11-25 23:56 MST).
BLOODLINE_DUTIES = (
    {'duty': 'FINANCIAL_AUTHORITY',
     'ruling': 'Patriot Saint coordinates assistance'
               ' without independently controlling or'
               ' disbursing family funds.'},
    {'duty': 'SUCCESSION',
     'ruling': 'His responsibilities must survive the'
               " founder's lifetime, with financial"
               ' authority passing according to the'
               ' applicable succession and trust'
               ' instruments.'},
    {'duty': 'CONFIDENTIALITY',
     'ruling': 'Private family matters must remain'
               ' segregated from his public-facing'
               ' commercial operations.'},
    {'duty': 'PERMANENT_SCOPE_PROTECTION',
     'ruling': 'His original identity, commercial'
               ' purpose and bloodline responsibilities'
               ' must not be removed, diminished or'
               ' repurposed through future software'
               ' upgrades.'},
    {'duty': 'LEGAL_ASSISTANCE',
     'ruling': 'Legal assistance includes locating and'
               ' coordinating qualified legal'
               ' representation.'},
)
BLOODLINE_DUAL_NATURE_RULING = (
    'Patriot Saint must remain both a commercial'
    ' enterprise and a permanent protective resource'
    ' for the Sanders bloodline. Neither purpose should'
    ' diminish the other.')
BLOODLINE_GODFATHER_DISTINCTION_RULING = (
    'I would also preserve his distinction from The'
    ' Godfather, rather than merging their'
    ' responsibilities.')
# Invariants of record under the succession and
# permanent-scope-protection duties: stated here so no
# future upgrade of this module can silently drop them.
BLOODLINE_INVARIANTS = (
    'The bloodline support remit survives the'
    " founder's lifetime; financial authority passes"
    ' according to the applicable succession and trust'
    ' instruments.',
    "This platform's original identity, commercial"
    ' purpose, and bloodline responsibilities must not'
    ' be removed, diminished, or repurposed through'
    ' future software upgrades.',
    'The platform coordinates assistance only: it'
    ' never independently controls or disburses family'
    ' funds, and funds_disbursed is False on every'
    ' bloodline matter, always.',
    'Bloodline matters are segregated from the'
    ' public-facing commercial operations in a separate'
    ' store; neither store is read by the other'
    " remit.",
    'Patriot Saint remains both a commercial enterprise'
    ' and a permanent protective resource for the'
    ' Sanders bloodline; neither purpose diminishes the'
    ' other.',
    "The Godfather's responsibilities are not merged"
    ' into this platform, and this remit is not his.',
)
# The tracked matter kinds of the remit, from the
# founder's role statement: funds for an incarcerated
# bloodline member, tickets, and legal assistance —
# each as coordination only.
BLOODLINE_MATTER_KINDS = (
    'INCARCERATED_FUNDS_COORDINATION',
    'TICKET_PAYMENT_COORDINATION',
    'LEGAL_REPRESENTATION_COORDINATION',
)
BLOODLINE_MATTER_STATUSES = ('AWAITING_HUMAN_REVIEW',
                             'APPROVED', 'REJECTED',
                             'COORDINATION_RECORDED')
BLOODLINE_MATTER_TRANSITIONS = {
    'approve': {'AWAITING_HUMAN_REVIEW': 'APPROVED'},
    'reject': {'AWAITING_HUMAN_REVIEW': 'REJECTED'},
}
BLOODLINE_OPEN_STATUSES = ('AWAITING_HUMAN_REVIEW',
                           'APPROVED')
# Operations the bloodline remit refuses by name: the
# platform coordinates assistance — it does not move
# money. Any disbursement operation is refused under
# PATRIOT_SAINT_COORDINATION_ONLY.
BLOODLINE_EXECUTION_OPERATIONS = (
    'disburse_funds', 'disburse', 'pay_ticket',
    'pay_tickets', 'transfer_funds', 'move_money',
    'release_funds', 'send_money',
)


class SandersPatriotSaintDenied(Exception):
    """The requested Sanders Patriot Saint operation is not
    allowed."""


class SandersPatriotSaintForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class SandersPatriotSaintService:
    """Sanders Patriot Saint: governed governance records under the patriot saint records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise SandersPatriotSaintDenied(
                'Sanders Patriot Saint requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'sanders_patriot_saint', {
            'OPERATOR': {'SANDERS_PATRIOT_SAINT'},
            'AUDITOR': {'SANDERS_PATRIOT_SAINT'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_patriot_saint_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    briefing_refs TEXT NOT NULL,
                    briefing_count INTEGER NOT NULL,
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
        # The bloodline support remit keeps its matters
        # in a SEGREGATED STORE (founder's confidentiality
        # duty, 2026-11-25): a separate database file
        # beside the commercial store. The commercial
        # operations never open it, and the bloodline
        # remit never opens the commercial store.
        self._bloodline_path = self._path.with_name(
            self._path.stem + '_bloodline' + self._path.suffix)
        with self._bloodline_connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanders_patriot_saint_bloodline_matters (
                    matter_id TEXT PRIMARY KEY,
                    matter_kind TEXT NOT NULL,
                    member_ref TEXT NOT NULL,
                    detail_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coordination_ref TEXT,
                    funds_disbursed INTEGER NOT NULL DEFAULT 0,
                    opened_by TEXT NOT NULL,
                    opened_at REAL NOT NULL,
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

    def _bloodline_connect(self):
        db = sqlite3.connect(self._bloodline_path, timeout=10,
                             isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def _now(self) -> float:
        return float(self._clock())

    def _check_actor(self, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise SandersPatriotSaintForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise SandersPatriotSaintForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise SandersPatriotSaintForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SANDERS_PATRIOT_SAINT',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise SandersPatriotSaintForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise SandersPatriotSaintDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['canonical catalog row #85', 'Set A platform registry (name, hostname, NAICS map)', 'Set B schema seed row (read directly)', 'Set C Tier 1 catalog entry (read directly)', 'owner correction 2026-11-23 (decisions.md): Godfather and Patriot Saint are two separate platforms'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'bloodline_support':
                SandersPatriotSaintService.bloodline_design_view(),
            'note': 'Sanders Patriot Saint is the strategic governance and constitutional authority framework platform: it carries governed governance records over governance matters, institutions, and frameworks and declared briefing sets presented by reference only. Set C’s purpose text for this name — Strategic governance, Joint Chiefs integration, constitutional authority framework, presidential briefings — is recorded verbatim as found and is NOT the built scope: no Joint Chiefs integration, no presidential briefing delivery, and no exercise of constitutional authority was constructed. The platform issues no directive, exercises no authority, integrates no command, and delivers no briefing: issue_directive, exercise_authority, integrate_command, deliver_briefing, and external_execution are refused by name under PATRIOT_SAINT_RECORDS_ONLY, and determinations are records for human operators, never acts of authority. A record declared with no briefings stands NO_BRIEFINGS_SUBMITTED and no determination can be recorded on it. IDENTITY: under the owner’s 2026-11-23 correction, The Godfather and Patriot Saint are TWO SEPARATE PLATFORMS — Set B’s persona pairing Godfather and Set C’s nickname Godfather are recorded as found, but this build carries only the Sanders Patriot Saint identity (catalog 85), claims none of The Godfather’s scope (catalog 143), and merges nothing. Set B carries the shorter name form Patriot Saint (no Sanders prefix) — recorded as found; the canonical name Sanders Patriot Saint governs. The designed hostname patriot-saint.sandersglobal.com sits under the unowned parent sandersglobal.com; it is recorded and nothing is served there. Its two attested NAICS sets are recorded as found, and no NAICS set is carried into its identity. The platform holds references and workflow state only — no classified material, no briefing content, no directive text. Sanders Patriot Saint is distinct from The Godfather (catalog 143), Sanders Freedom Revolution (catalog 86), and Sanders Strategy Hub (catalog 94) — identities are never merged.',
        }



    @staticmethod
    def bloodline_design_view() -> dict:
        return {
            'founder_ruling': FOUNDER_RULING_BLOODLINE_ROLE,
            'ruling_date': FOUNDER_RULING_BLOODLINE_ROLE_DATE,
            'additional_duties_verbatim':
                FOUNDER_RULING_ADDITIONAL_DUTIES_VERBATIM,
            'additional_duties_date':
                FOUNDER_RULING_ADDITIONAL_DUTIES_DATE,
            'scope_ref': BLOODLINE_SUPPORT_SCOPE,
            'discipline': BLOODLINE_DISCIPLINE,
            'duties': [dict(duty) for duty in BLOODLINE_DUTIES],
            'invariants': list(BLOODLINE_INVARIANTS),
            'dual_nature_ruling': BLOODLINE_DUAL_NATURE_RULING,
            'godfather_distinction_ruling':
                BLOODLINE_GODFATHER_DISTINCTION_RULING,
            'matter_kinds': list(BLOODLINE_MATTER_KINDS),
            'matter_statuses': list(BLOODLINE_MATTER_STATUSES),
            'funds_disbursed': False,
            'segregated_store': True,
            'note': (
                "Under the founder's rulings of 2026-11-25"
                ' (23:44 and 23:56 MST), supplementing the'
                ' Permanent Bloodline Protection Directive'
                ' without amending it, Sanders Patriot Saint'
                ' carries a private BLOODLINE SUPPORT remit'
                ' beside his public-facing business model of'
                ' his own: tracked matters coordinating'
                ' funds for a bloodline member who has been'
                ' incarcerated, coordinating the paying off'
                ' of tickets, and legal assistance —'
                ' locating and coordinating qualified legal'
                ' representation. The platform COORDINATES'
                ' assistance only: it never independently'
                ' controls or disburses family funds, fund'
                ' movement is represented as impossible in'
                ' this service, disbursement operations are'
                ' refused by name under'
                ' PATRIOT_SAINT_COORDINATION_ONLY, and every'
                ' matter carries funds_disbursed False,'
                ' always. Every matter is born'
                ' AWAITING_HUMAN_REVIEW and moves only on a'
                " human operator's recorded decision."
                ' Bloodline matters are kept in a segregated'
                ' store the commercial operations never'
                ' read, and the remit never reads the'
                ' commercial store. The remit, the duties,'
                " and this platform's identity are"
                ' invariants: they survive the founder\u2019s'
                ' lifetime and must not be removed,'
                ' diminished, or repurposed through future'
                ' software upgrades. The Godfather\u2019s'
                ' responsibilities are not merged into this'
                ' platform, and this remit is not his.'),
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the patriot saint records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in BLOODLINE_EXECUTION_OPERATIONS:
            raise SandersPatriotSaintDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Patriot Saint platform coordinates'
                ' bloodline assistance only — it never'
                ' independently controls or disburses family'
                ' funds (PATRIOT_SAINT_COORDINATION_ONLY;'
                " founder's financial-authority duty,"
                ' 2026-11-25)')
        if operation in EXECUTION_OPERATIONS:
            raise SandersPatriotSaintDenied(
                f'Operation {operation!r} is refused: the'
                ' Sanders Patriot Saint platform'
                ' carries patriot saint records only'
                ' \u2014 it issues no directive, exercises'
                ' no authority, integrates no command,'
                ' and delivers no briefing itself'
                ' (PATRIOT_SAINT_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise SandersPatriotSaintDenied(
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
        operations = json.loads(row['briefing_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'briefing_refs': operations,
            'briefing_count': row['briefing_count'],
            'briefing_state': ('NO_BRIEFINGS_SUBMITTED'
                             if row['briefing_count'] == 0
                             else 'BRIEFINGS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, briefing_refs,
                      scope_ref, *, region=None):
        """Record one patriot saint record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_BRIEFINGS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record issues no directive,
        exercises no authority, and delivers
        no briefing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersPatriotSaintDenied(
                    f'A {label} is required')
        if not isinstance(briefing_refs, (list, tuple)):
            raise SandersPatriotSaintDenied(
                'briefing_refs must be a list of references')
        if len(briefing_refs) > MAX_REFS:
            raise SandersPatriotSaintDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in briefing_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise SandersPatriotSaintDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'sanders-patriot-saint-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    briefing_count=len(operations))
                db.execute(
                    'INSERT INTO sanders_patriot_saint_records'
                    ' (record_id, subject_ref, briefing_refs,'
                    ' briefing_count, scope_ref, status, outcome,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM sanders_patriot_saint_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise SandersPatriotSaintDenied(
                'Patriot Saint record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested patriot saint record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersPatriotSaintDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_patriot_saint_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Patriot Saint record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersPatriotSaintDenied(
                        f"Cannot {action} a patriot saint record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE sanders_patriot_saint_records SET status = ?,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (GOVERNANCE_POSITION_CONFIRMED or BRIEFING_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_BRIEFINGS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise SandersPatriotSaintDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SandersPatriotSaintDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM sanders_patriot_saint_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Patriot Saint record not found')
                if row['status'] != 'APPROVED':
                    raise SandersPatriotSaintDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" patriot saint records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['briefing_count'] == 0:
                    raise SandersPatriotSaintDenied(
                        'NO_BRIEFINGS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE sanders_patriot_saint_records SET status = ?,'
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
                'SELECT * FROM sanders_patriot_saint_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- bloodline support remit (founder's rulings,
    # 2026-11-25) ------------------------------------------------

    @staticmethod
    def _bloodline_matter_view(row):
        return {
            'matter_id': row['matter_id'],
            'matter_kind': row['matter_kind'],
            'member_ref': row['member_ref'],
            'detail_ref': row['detail_ref'],
            'status': row['status'],
            'coordination_ref': row['coordination_ref'],
            # The founder's financial-authority duty, in
            # code: the platform coordinates assistance
            # and disburses nothing — always False.
            'funds_disbursed': False,
            'scope_ref': BLOODLINE_SUPPORT_SCOPE,
            'segregated_store': True,
            'opened_by': row['opened_by'],
            'opened_at': row['opened_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def open_bloodline_matter(self, actor, matter_kind,
                              member_ref, detail_ref, *,
                              region=None):
        """Open one bloodline support matter (operator
        only) in the segregated bloodline store. A matter
        is a coordination record, by reference only: the
        kind of assistance (funds for an incarcerated
        bloodline member, a ticket, or legal
        representation), the bloodline member by
        reference, and the matter's detail by reference.
        It is born AWAITING_HUMAN_REVIEW and moves only
        on a human operator's recorded decision. Opening
        a matter moves no money and engages no counsel —
        the platform coordinates; humans act."""
        self._geo(region)
        self._require_operator(actor)
        if matter_kind not in BLOODLINE_MATTER_KINDS:
            raise SandersPatriotSaintDenied(
                f'Unknown bloodline matter kind:'
                f' {matter_kind!r}')
        for label, value in (('member_ref', member_ref),
                             ('detail_ref', detail_ref)):
            if not isinstance(value, str) or not value.strip():
                raise SandersPatriotSaintDenied(
                    f'A {label} is required')
        now = self._now()
        matter_id = (f'sanders-patriot-saint-bloodline-matter-'
                     f'{uuid.uuid4().hex[:16]}')
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_BLOODLINE_MATTER_OPENED',
                    actor=actor, matter_id=matter_id,
                    matter_kind=matter_kind,
                    scope_ref=BLOODLINE_SUPPORT_SCOPE)
                db.execute(
                    'INSERT INTO'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' (matter_id, matter_kind, member_ref,'
                    ' detail_ref, status, coordination_ref,'
                    ' funds_disbursed, opened_by, opened_at,'
                    ' updated_by, updated_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?)',
                    (matter_id, matter_kind,
                     member_ref.strip(), detail_ref.strip(),
                     'AWAITING_HUMAN_REVIEW', None, 0,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._bloodline_matter_view(row)

    def bloodline_matters_list(self, actor, role, *,
                               region=None):
        self._geo(region)
        self._guard_access(actor, role, 'bloodline-matters',
                           'bloodline matters view')
        with self._bloodline_connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' ORDER BY opened_at').fetchall()
        return [self._bloodline_matter_view(row) for row in rows]

    def bloodline_matter_view(self, actor, role, matter_id, *,
                              region=None):
        self._geo(region)
        self._guard_access(actor, role, matter_id,
                           'bloodline matter view')
        with self._bloodline_connect() as db:
            row = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        if row is None:
            raise SandersPatriotSaintDenied(
                'Bloodline matter not found')
        return self._bloodline_matter_view(row)

    def bloodline_matter_action(self, actor, matter_id,
                                action, *, region=None):
        """Approve or reject one bloodline matter awaiting
        human review (operator only) — the recorded human
        decision the remit requires. Approval approves the
        coordination matter; it disburses nothing and
        authorizes no payment by the platform."""
        self._geo(region)
        self._require_operator(actor)
        transitions = BLOODLINE_MATTER_TRANSITIONS.get(action)
        if transitions is None:
            raise SandersPatriotSaintDenied(
                f'Unknown bloodline matter action: {action!r}')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' WHERE matter_id = ?',
                    (matter_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Bloodline matter not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise SandersPatriotSaintDenied(
                        f'Cannot {action} a bloodline matter'
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_BLOODLINE_MATTER_ACTION',
                    actor=actor, matter_id=matter_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE matter_id = ?',
                    (new_status, actor, now, receipt_id,
                     matter_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._bloodline_matter_view(updated)

    def record_bloodline_coordination(self, actor, matter_id,
                                      coordination_ref, *,
                                      region=None):
        """Record, against an APPROVED bloodline matter,
        the coordination a human arranged (operator
        only), by reference: counsel located, a facility
        contact made, a payment arranged by the founder
        or another human. The platform records the
        coordination — it performs none of it, and it
        disburses nothing: the recorded matter keeps
        funds_disbursed False."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(coordination_ref, str) \
                or not coordination_ref.strip():
            raise SandersPatriotSaintDenied(
                'A coordination reference is required to'
                ' record coordination')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' WHERE matter_id = ?',
                    (matter_id,)).fetchone()
                if row is None:
                    raise SandersPatriotSaintDenied(
                        'Bloodline matter not found')
                if row['status'] != 'APPROVED':
                    raise SandersPatriotSaintDenied(
                        'Coordination is recorded only for'
                        ' APPROVED bloodline matters (this'
                        f" one is {row['status']})")
                receipt_id = self._record(
                    'SANDERS_PATRIOT_SAINT_BLOODLINE_COORDINATION_RECORDED',
                    actor=actor, matter_id=matter_id,
                    coordination_ref=coordination_ref.strip(),
                    funds_disbursed=False)
                db.execute(
                    'UPDATE'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' SET status = ?, coordination_ref = ?,'
                    ' updated_by = ?, updated_at = ?,'
                    ' receipt_id = ? WHERE matter_id = ?',
                    ('COORDINATION_RECORDED',
                     coordination_ref.strip(), actor, now,
                     receipt_id, matter_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._bloodline_matter_view(updated)

    def disburse_funds(self, actor, matter_id, *args, **kwargs):
        """Refused by name, unconditionally. Under the
        founder's financial-authority duty (2026-11-25),
        Patriot Saint coordinates assistance without
        independently controlling or disbursing family
        funds: fund movement is represented as impossible
        in this service, and no argument, actor, or state
        changes that."""
        raise SandersPatriotSaintDenied(
            'disburse_funds is refused: the Sanders Patriot'
            ' Saint platform coordinates bloodline'
            ' assistance only — it never independently'
            ' controls or disburses family funds'
            ' (PATRIOT_SAINT_COORDINATION_ONLY)')

    def bloodline_remit(self, actor, role, *, region=None):
        """The bloodline support remit read surface: the
        founder's ruling and duties of record, the
        invariants, and the remit's matters — open
        matters in full, tallies over all. Guarded
        exactly as this platform's other record views;
        the commercial records are never read here, and
        this remit is never read by the commercial
        views (the founder's confidentiality duty)."""
        self._geo(region)
        self._guard_access(actor, role, 'bloodline-remit',
                           'bloodline remit view')
        with self._bloodline_connect() as db:
            by_status = {s: 0 for s in BLOODLINE_MATTER_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_kind = {k: 0 for k in BLOODLINE_MATTER_KINDS}
            for row in db.execute(
                    'SELECT matter_kind, COUNT(*) AS n FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' GROUP BY matter_kind'):
                by_kind[row['matter_kind']] = row['n']
            open_rows = db.execute(
                'SELECT * FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE status IN (?, ?) ORDER BY opened_at',
                BLOODLINE_OPEN_STATUSES).fetchall()
        view = self.bloodline_design_view()
        view['matters_total'] = sum(by_status.values())
        view['matters_by_status'] = by_status
        view['matters_by_kind'] = by_kind
        view['open_matters'] = [
            self._bloodline_matter_view(row) for row in open_rows]
        return view

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM sanders_patriot_saint_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM sanders_patriot_saint_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM sanders_patriot_saint_records'
                ' WHERE briefing_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(briefing_count), 0) AS n'
                ' FROM sanders_patriot_saint_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        with self._bloodline_connect() as db:
            matters_by_status = {
                s: 0 for s in BLOODLINE_MATTER_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' GROUP BY status'):
                matters_by_status[row['status']] = row['n']
            matters_by_kind = {
                k: 0 for k in BLOODLINE_MATTER_KINDS}
            for row in db.execute(
                    'SELECT matter_kind, COUNT(*) AS n FROM'
                    ' sanders_patriot_saint_bloodline_matters'
                    ' GROUP BY matter_kind'):
                matters_by_kind[row['matter_kind']] = row['n']
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'bloodline_matters_total':
                sum(matters_by_status.values()),
            'bloodline_matters_by_status': matters_by_status,
            'bloodline_matters_by_kind': matters_by_kind,
            'bloodline_funds_disbursed': False,
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_briefings_submitted': no_refs,
            'briefings_declared_total': refs_total,
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
                    raise SandersPatriotSaintDenied(str(exc)) from exc
                self._record('SANDERS_PATRIOT_SAINT_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
