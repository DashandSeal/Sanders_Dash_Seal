"""The Godfather — the Godfather platform.

The production build-out of The Godfather
design (canonical catalog row #143, Band 2D),
built whole as its own platform service over
the shared RTSA foundation (RTSA Build Program
Q101).

NAME — verified before building, per the name
law: the owner's own correction of 2026-11-23
(decisions.md) establishes **The Godfather** as
a platform in its own right — "the Godfather
gets his own row (catalog count 142 → 143)" —
and the program queue carries it as catalog
#143; the queue-note reading matched the
owner's record exactly. The canonical
catalog's printed table ends at row #142; row
#143 stands on the owner's correction, carried
in decisions.md and the queue. No Set A, Set
B, or Set C entry names this platform in its
own right (verified by direct read of all
three), and the MASTER names it nowhere
(verified).

SEPARATION — the owner's correction of
2026-11-23 governs: **The Godfather and
Sanders Patriot Saint are TWO SEPARATE
PLATFORMS.** Set B's schema row pairs Patriot
Saint with the persona "Godfather", and Set C
gives Sanders Patriot Saint the nickname
"Godfather" (its Tier 1 entry, its summary
table, and its embedded registry record
"Sanders Patriot Saint / Godfather") — all of
those are PATRIOT SAINT'S records, recorded
exactly as found on catalog #85's build
(tranche 20); under the owner's correction the
pairing does NOT merge the two platforms. This
build carries only The Godfather identity
(#143): it claims none of Patriot Saint's
scope, purpose text, price, NAICS set, or
hostname, and merges nothing in either
direction.

DESIGNED PURPOSE — the owner's words
(2026-11-23): the Godfather and Patriot Saint
"are businesses for the public, and protection
for his bloodline" — a dual purpose, like the
watchdogs' dual roles. That owner record is
this platform's entire design record, recorded
exactly as found. The built scope is governed
records only: the platform records matters
presented by reference; it provides no
protection, transacts no business, issues no
directive, and enforces no decision itself.

RECOVERED vs REBUILT — the discipline of this
module is absolute: a rebuilt component is
never described as recovered or original.

RECOVERED (records only, stated exactly): the
owner's design record — a business for the
public, and protection for his bloodline
(decisions.md, owner correction 2026-11-23;
canonical catalog row #143 by that
correction). No Godfather module existed in
any examined source; no Set A/B/C entry, no
price, no NAICS set, no hostname, and no
classification is attested for this platform
in its own right in any examined source.

REBUILT (everything executable in this module):
the governed platform below — The Godfather
platform's own identity and store, carrying
governed matter records:

- **Matter records**: a subject reference (a
  public-business matter or a
  bloodline-protection matter under service, by
  reference), a declared set of matter
  references, and a scope reference, carried
  as durable, receipted records with a
  lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded
  decision, then an outcome recorded against
  presented evidence (OUTCOME_RECORDED).
- **The matter discipline**: outcomes are
  recorded only for APPROVED records and only
  against a presented evidence reference, with
  a closed outcome set
  (GODFATHER_POSITION_CONFIRMED /
  MATTER_ACTION_REQUIRED / INCONCLUSIVE). A
  record declared with no matters stands
  NO_MATTERS_SUBMITTED in every view and in
  the status tallies, and both determinations
  are refused on it — no matters were
  presented to determine from; INCONCLUSIVE,
  which asserts nothing, records against
  evidence.
- **Records, never action**: determinations
  are records placed before human operators.
  The platform provides no protection,
  transacts no business, issues no directive,
  and enforces no decision — provide_protection,
  transact_business, issue_directive,
  enforce_decision, and external_execution are
  refused by name under GODFATHER_RECORDS_ONLY.
- **Reference-only discipline**: subjects and
  matters are carried by reference only; the
  platform holds no business records content,
  no family data, no financial state, and no
  credentials — references and workflow state
  only, as across the ecosystem. No public or
  customer surface is designed for this
  platform in any examined source, so none was
  built; no security internals are exposed.
- **NAICS**: no NAICS set is attested for this
  platform in any examined source. The NAICS
  set on Set B's Patriot Saint row (541512,
  561621) belongs to catalog #85's record and
  is NOT carried into this platform's built
  identity; none is invented.
- **Separation**: The Godfather platform is
  its own platform. It is not Sanders Patriot
  Saint (catalog #85 — a separate platform
  under the owner's 2026-11-23 correction),
  not Sanders Steward Sentinel (catalog #84),
  and not Sanders Strategy Hub (catalog #94) —
  identities are never merged.

No record, no action: every state-changing
operation writes its Glass-Box receipt inside
the same transaction, through the shared
foundation's audit adapter; the service refuses
to exist without one.

FOUNDER'S PERMANENT GLOBAL BLOODLINE PROTECTION
DIRECTIVES (established by the founder, effective
2026-11-26; a ruled extension of this platform's
remit, recorded as a ruling, not as recovered
design): the Directives form an integral part of
the Permanent Bloodline Protection Directive
adopted 2026-11-25 and supplement it; they do not
amend it. ARTICLE I assigns this platform private
responsibilities exclusively for the Sanders
bloodline, carried here beside its independent
public-facing commercial business model: working
alongside Sanders Sentinel to approve all funding
necessary for Patriot Saint to fulfill its private
duties; transportation coordination for the
bloodline (acquisition of ground, air, rail, and
water transportation; domestic and international
provision; emergency and medical transportation;
evacuation and repatriation arrangement;
insurance, maintenance, repairs, and
replacement); and establishing and maintaining
emergency financial reserves alongside Sanders
Sentinel. Under the reconciliation of record,
funding approval is a RECORDED DETERMINATION
inside the system: a funding request reads as
approved only when both this platform's and
Sanders Sentinel's determinations stand recorded
against it — one side alone never reads as fully
approved. No platform disburses or holds funds:
the reserves are a register of designations and
joint approvals, not platform-held money, and
transportation acquisition is coordination and
records — purchase and title execution remain
with the companies and humans. Every matter,
request, and designation is a tracked record born
AWAITING_HUMAN_REVIEW, kept in a segregated store
the commercial operations never read, under
Articles IV–VI: Global By Design, permanent
bloodline exclusivity, and preservation of each
platform's original identity and purpose —
coordination without merging.
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
    platform_id='the_godfather',
    name='The Godfather',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

DESIGNED_ROLE = 'A business for the public, and protection for his bloodline (owner record)'
DISCIPLINE = 'GODFATHER_RECORDS_ONLY'
RECORD_OPERATIONS = ('record_godfather', 'approve_godfather', 'record_outcome',
    'view_godfather', 'view_design',
    'open_bloodline_transport_matter',
    'act_on_bloodline_transport_matter',
    'record_bloodline_transport_coordination',
    'open_bloodline_funding_request',
    'record_bloodline_funding_determination',
    'record_counterpart_funding_determination',
    'designate_bloodline_reserve',
    'act_on_bloodline_reserve',
    'record_counterpart_reserve_approval',
    'view_bloodline_remit')
EXECUTION_OPERATIONS = ('provide_protection', 'transact_business',
    'issue_directive', 'enforce_decision',
    'external_execution')
RECORD_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                   'OUTCOME_RECORDED')
RECORD_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
OUTCOMES = ('GODFATHER_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED',
            'INCONCLUSIVE')
DETERMINATIONS = ('GODFATHER_POSITION_CONFIRMED', 'MATTER_ACTION_REQUIRED')
MAX_REFS = 100

# -- Permanent Global Bloodline Protection
# Directives (founder-established, effective
# 2026-11-26) ---------------------------------------
DIRECTIVES_TITLE = ('Permanent Global Bloodline'
                    ' Protection Directives')
DIRECTIVES_ESTABLISHED_BY = ('Roosevelt Sanders'
                             ' \u2014 Founder')
DIRECTIVES_EFFECTIVE_DATE = '2026-11-26'
DIRECTIVES_DESIGNATION = 'Permanent | Global By Design'
DIRECTIVES_SOURCE = ('Founder record:'
                     ' founder-permanent-global-bloodline'
                     '-protection-directives-2026-11-26')
BLOODLINE_DIRECTIVES_SCOPE = 'GLOBAL_BLOODLINE_DIRECTIVES'
BLOODLINE_DISCIPLINE = 'GODFATHER_COORDINATION_ONLY'
# Article I assigns the funding approval for Patriot
# Saint's private duties jointly to this platform and
# Sanders Sentinel: neither side's determination
# reads as fully approved on its own.
FUNDING_COUNTERPART_PLATFORM = 'sanders_sentinel'
FUNDING_COUNTERPART_NAME = 'Sanders Sentinel'
RESERVE_COUNTERPART_PLATFORM = 'sanders_sentinel'
RESERVE_COUNTERPART_NAME = 'Sanders Sentinel'
FOUNDER_DIRECTIVES_ARTICLE_I_VERBATIM = (
    'ARTICLE I \u2014 GODFATHER\n'
    '\n'
    'Godfather shall maintain its own independent'
    ' public-facing commercial business model while'
    ' permanently carrying out its private'
    ' responsibilities exclusively for the Sanders'
    ' bloodline.\n'
    '\n'
    'Its private responsibilities shall include:\n'
    '\n'
    '- Working alongside Sanders Sentinel to approve'
    ' all funding necessary for Patriot Saint to'
    ' fulfill its private duties.\n'
    '- Acquiring whatever type of transportation the'
    ' Sanders bloodline requires.\n'
    '- Acquiring ground, air, rail and water'
    ' transportation.\n'
    '- Providing domestic and international'
    ' transportation.\n'
    '- Providing emergency and medical'
    ' transportation.\n'
    '- Arranging emergency evacuations and'
    ' repatriation.\n'
    '- Securing transportation insurance, maintenance,'
    ' repairs and replacement.\n'
    '- Establishing and maintaining emergency'
    ' financial reserves alongside Sanders Sentinel'
    ' for the protection of the Sanders bloodline.')
FOUNDER_DIRECTIVES_ARTICLES_IV_VI_VERBATIM = (
    'ARTICLE IV \u2014 GLOBAL BY DESIGN\n'
    '\n'
    'All responsibilities established within these'
    ' directives are Global By Design from their'
    ' inception.\n'
    '\n'
    'The protection, assistance, transportation,'
    ' funding and legal support provided to the'
    ' Sanders bloodline shall extend worldwide,'
    ' across all seven continents.\n'
    '\n'
    'Geographical location, national borders,'
    ' residency, relocation or international travel'
    ' shall not extinguish, diminish or terminate'
    ' these assigned responsibilities.\n'
    '\n'
    'ARTICLE V \u2014 PERMANENT BLOODLINE EXCLUSIVITY\n'
    '\n'
    'The private responsibilities established herein'
    ' are exclusively dedicated to the Sanders'
    ' bloodline and its present and future bloodline'
    ' descendants.\n'
    '\n'
    'These responsibilities shall remain permanent'
    ' and shall not be diluted, reassigned, abandoned,'
    ' redirected or subordinated to public-facing'
    ' commercial interests.\n'
    '\n'
    'The separate public-facing business models shall'
    ' remain intact without interfering with the'
    ' fulfillment of these private responsibilities.\n'
    '\n'
    'ARTICLE VI \u2014 PRESERVATION OF ORIGINAL'
    ' AUTHORITY AND PURPOSE\n'
    '\n'
    'Godfather, Sanders Sentinel and Patriot Saint'
    ' shall retain their respective identities,'
    ' original functions, established responsibilities'
    ' and independent purposes.\n'
    '\n'
    'Their coordinated responsibilities shall'
    ' strengthen one another without merging,'
    ' replacing or diminishing any platform\u2019s'
    ' original assignment.\n'
    '\n'
    'No unauthorized alteration, reinterpretation,'
    ' restriction or modification shall weaken the'
    ' responsibilities established by the Founder for'
    ' the protection of the Sanders bloodline.\n'
    '\n'
    'These directives shall operate in conjunction'
    ' with the Permanent Bloodline Protection'
    ' Directive throughout the Sanders Sovereign RTSA'
    ' Ecosystem.')
# Articles IV–VI as governing invariants of this
# module, with the reconciliation of record: stated
# here so no future upgrade of this module can
# silently drop them.
GLOBAL_DIRECTIVES_INVARIANTS = (
    'Global By Design: the responsibilities'
    ' established by the Permanent Global Bloodline'
    ' Protection Directives extend worldwide, across'
    ' all seven continents; geographical location,'
    ' national borders, residency, relocation, or'
    ' international travel shall not extinguish,'
    ' diminish, or terminate them.',
    'Permanent bloodline exclusivity: the private'
    ' responsibilities are exclusively dedicated to'
    ' the Sanders bloodline and its present and future'
    ' bloodline descendants; they shall not be'
    ' diluted, reassigned, abandoned, redirected, or'
    ' subordinated to public-facing commercial'
    ' interests.',
    'Preservation of original authority and purpose:'
    ' Godfather, Sanders Sentinel, and Patriot Saint'
    ' retain their respective identities, original'
    ' functions, established responsibilities, and'
    ' independent purposes; their coordinated'
    ' responsibilities strengthen one another without'
    ' merging, replacing, or diminishing any'
    " platform's original assignment.",
    'Funding approval under these Directives is a'
    ' recorded determination requiring both'
    " Godfather's and Sanders Sentinel's"
    ' determinations; the emergency reserves are a'
    ' register of designations and joint approvals,'
    ' not platform-held money. Godfather and Sanders'
    ' Sentinel disburse and hold no funds. Under the'
    " Founder's Amendment to Article III (2026-11-26),"
    ' Patriot Saint alone disburses — for his'
    ' assigned private responsibilities only, against'
    ' the recorded joint approval, as a platform'
    ' record with no payment rail attached or'
    ' represented.',
)
# The transportation coordination matter kinds of
# Article I: acquisition by mode, provision by
# reach, emergency and medical transportation,
# evacuation and repatriation arrangement, and
# insurance, maintenance, repairs, and replacement
# — each as coordination and records only.
TRANSPORT_MATTER_KINDS = (
    'TRANSPORTATION_ACQUISITION_GROUND',
    'TRANSPORTATION_ACQUISITION_AIR',
    'TRANSPORTATION_ACQUISITION_RAIL',
    'TRANSPORTATION_ACQUISITION_WATER',
    'TRANSPORTATION_PROVISION_DOMESTIC',
    'TRANSPORTATION_PROVISION_INTERNATIONAL',
    'EMERGENCY_TRANSPORTATION',
    'MEDICAL_TRANSPORTATION',
    'EMERGENCY_EVACUATION_ARRANGEMENT',
    'REPATRIATION_ARRANGEMENT',
    'TRANSPORTATION_INSURANCE',
    'TRANSPORTATION_MAINTENANCE',
    'TRANSPORTATION_REPAIRS',
    'TRANSPORTATION_REPLACEMENT',
)
TRANSPORT_MATTER_STATUSES = ('AWAITING_HUMAN_REVIEW',
                             'APPROVED', 'REJECTED',
                             'COORDINATION_RECORDED')
TRANSPORT_MATTER_TRANSITIONS = {
    'approve': {'AWAITING_HUMAN_REVIEW': 'APPROVED'},
    'reject': {'AWAITING_HUMAN_REVIEW': 'REJECTED'},
}
TRANSPORT_OPEN_STATUSES = ('AWAITING_HUMAN_REVIEW',
                           'APPROVED')
FUNDING_REQUEST_STATUSES = ('AWAITING_HUMAN_REVIEW',
                            'APPROVED', 'DECLINED')
FUNDING_REQUEST_TRANSITIONS = {
    'approve': {'AWAITING_HUMAN_REVIEW': 'APPROVED'},
    'decline': {'AWAITING_HUMAN_REVIEW': 'DECLINED'},
}
RESERVE_STATUSES = ('AWAITING_HUMAN_REVIEW',
                    'APPROVED', 'DECLINED')
RESERVE_TRANSITIONS = {
    'approve': {'AWAITING_HUMAN_REVIEW': 'APPROVED'},
    'decline': {'AWAITING_HUMAN_REVIEW': 'DECLINED'},
}
JOINT_STATES = ('AWAITING_DETERMINATION',
                'AWAITING_COUNTERPART',
                'JOINTLY_APPROVED', 'NOT_APPROVED')
# Operations the bloodline remit refuses by name:
# the platform coordinates and records — it moves
# no money, holds no funds, and executes no purchase
# or title transfer. Refused under
# GODFATHER_COORDINATION_ONLY.
BLOODLINE_EXECUTION_OPERATIONS = (
    'disburse_funds', 'disburse', 'pay_ticket',
    'pay_tickets', 'transfer_funds', 'move_money',
    'release_funds', 'send_money', 'hold_funds',
    'purchase_transportation', 'buy_vehicle',
    'acquire_title', 'take_title', 'execute_purchase',
)


class TheGodfatherDenied(Exception):
    """The requested The Godfather operation is not
    allowed."""


class TheGodfatherForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class TheGodfatherService:
    """The Godfather: governed records under the Godfather records discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise TheGodfatherDenied(
                'The Godfather requires a working'
                ' Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'the_godfather', {
            'OPERATOR': {'THE_GODFATHER'},
            'AUDITOR': {'THE_GODFATHER'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS the_godfather_records (
                    record_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    matter_refs TEXT NOT NULL,
                    matter_count INTEGER NOT NULL,
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
        # The bloodline remit under the Permanent
        # Global Bloodline Protection Directives
        # keeps its matters, funding requests, and
        # reserve designations in a SEGREGATED STORE:
        # a separate database file beside the
        # commercial store. The commercial operations
        # never open it, and the bloodline remit never
        # opens the commercial store.
        self._bloodline_path = self._path.with_name(
            self._path.stem + '_bloodline' + self._path.suffix)
        with self._bloodline_connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS the_godfather_bloodline_transport_matters (
                    matter_id TEXT PRIMARY KEY,
                    matter_kind TEXT NOT NULL,
                    member_ref TEXT NOT NULL,
                    detail_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coordination_ref TEXT,
                    opened_by TEXT NOT NULL,
                    opened_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS the_godfather_bloodline_funding_requests (
                    request_id TEXT PRIMARY KEY,
                    matter_ref TEXT NOT NULL,
                    detail_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    counterpart_platform TEXT NOT NULL,
                    counterpart_determination_ref TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS the_godfather_bloodline_reserves (
                    reserve_id TEXT PRIMARY KEY,
                    designation_ref TEXT NOT NULL,
                    purpose_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    counterpart_platform TEXT NOT NULL,
                    counterpart_approval_ref TEXT,
                    funds_held INTEGER NOT NULL DEFAULT 0,
                    designated_by TEXT NOT NULL,
                    designated_at REAL NOT NULL,
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
            raise TheGodfatherForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise TheGodfatherForbidden(
                'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise TheGodfatherForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'THE_GODFATHER',
                              record_ref, purpose=purpose)
        except FoundationForbidden as exc:
            raise TheGodfatherForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise TheGodfatherDenied(str(exc)) from exc

    # -- design -----------------------------------------------------

    @staticmethod
    def design_view() -> dict:
        return {
            'name': IDENTITY.name,
            'designed_role': DESIGNED_ROLE,
            'design_sources': ['decisions.md — owner correction 2026-11-23: The Godfather and Patriot Saint are TWO SEPARATE PLATFORMS; the Godfather gets his own row (catalog #143); dual purpose in the owner’s words', 'canonical catalog row #85 (the paired record as found: Set B persona "Godfather"; Set C nickname "Godfather") — Patriot Saint’s records, expressly NOT claimed for this platform', 'Set B (read directly): no row for The Godfather in its own right — "Godfather" appears only as Patriot Saint’s persona in its schema row; Set A carries no entry (platform registry read directly); the MASTER names it nowhere (verified)', 'Set C (read directly): no entry for The Godfather in its own right — "Godfather" appears only as Sanders Patriot Saint’s nickname in its Tier 1 entry, summary table, and embedded registry record'],
            'discipline': DISCIPLINE,
            'record_operations': list(RECORD_OPERATIONS),
            'bloodline_directives':
                TheGodfatherService.bloodline_design_view(),
            'note': 'The Godfather is its own platform (catalog 143, by the owner’s 2026-11-23 correction): it carries governed matter records over public-business matters and bloodline-protection matters and declared matter sets presented by reference only. Its entire design record is the owner’s words — the Godfather is a business for the public, and protection for his bloodline (a dual purpose, like the watchdogs’ dual roles) — recorded exactly as found. The built scope is records only: the platform provides no protection, transacts no business, issues no directive, and enforces no decision: provide_protection, transact_business, issue_directive, enforce_decision, and external_execution are refused by name under GODFATHER_RECORDS_ONLY, and determinations are records for human operators, never action. A record declared with no matters stands NO_MATTERS_SUBMITTED and no determination can be recorded on it. SEPARATION — TWO SEPARATE PLATFORMS (owner correction 2026-11-23): Set B’s schema row pairs Patriot Saint with the persona Godfather and Set C gives Sanders Patriot Saint the nickname Godfather — those are Patriot Saint’s records (catalog 85), recorded as found on that platform’s build; the pairing does not merge the platforms, and this build claims none of Patriot Saint’s scope, purpose text, price, NAICS set, or hostname, in either direction. No Set A, Set B, or Set C entry names The Godfather in its own right (verified by direct read of all three), and the MASTER names it nowhere. No designed price is attested for The Godfather in any examined source — the figures on the paired records stand on Patriot Saint’s row and are NOT carried. No NAICS set is attested for this platform (Patriot Saint’s Set B set is not carried), no designed hostname is recorded for it, and no classification is attested. The platform holds references and workflow state only — no business records content, no family data, no financial state, no credentials. No public or customer surface is designed for this platform in any examined source, so none was built and no security internals are exposed. The Godfather is distinct from Sanders Patriot Saint (catalog 85), Sanders Steward Sentinel (catalog 84), and Sanders Strategy Hub (catalog 94) — identities are never merged.',
        }



    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed design check: a named operation is either
        a record operation this platform carries, or it is
        refused — a sales operation or an execution operation
        the Godfather records discipline does not
        authorize, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'design',
                           'operation design check')
        if operation in BLOODLINE_EXECUTION_OPERATIONS:
            raise TheGodfatherDenied(
                f'Operation {operation!r} is refused: the'
                ' Godfather platform coordinates and'
                ' records under the Permanent Global'
                ' Bloodline Protection Directives \u2014 it'
                ' disburses no funds, holds no funds, and'
                ' executes no purchase or title transfer'
                ' (GODFATHER_COORDINATION_ONLY)')
        if operation in EXECUTION_OPERATIONS:
            raise TheGodfatherDenied(
                f'Operation {operation!r} is refused: the'
                ' Godfather platform carries'
                ' governed records only \u2014 it'
                ' provides no protection, transacts'
                ' no business, issues no directive,'
                ' and enforces no decision itself'
                ' (GODFATHER_RECORDS_ONLY)')
        if operation not in RECORD_OPERATIONS:
            raise TheGodfatherDenied(
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
        operations = json.loads(row['matter_refs'])
        return {
            'record_id': row['record_id'],
            'subject_ref': row['subject_ref'],
            'matter_refs': operations,
            'matter_count': row['matter_count'],
            'matter_state': ('NO_MATTERS_SUBMITTED'
                             if row['matter_count'] == 0
                             else 'MATTERS_SUBMITTED'),
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

    def create_record(self, actor, subject_ref, matter_refs,
                      scope_ref, *, region=None):
        """Record one Godfather record (operator only) over
        a subject and a declared set of operation
        references, presented by reference. The operation set
        may be empty — the record then stands
        NO_MATTERS_SUBMITTED, exactly as the operation
        discipline holds, and no determination can be recorded
        on it. Recording the record provides no protection,
        transacts no business, and issues
        no directive."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise TheGodfatherDenied(
                    f'A {label} is required')
        if not isinstance(matter_refs, (list, tuple)):
            raise TheGodfatherDenied(
                'matter_refs must be a list of references')
        if len(matter_refs) > MAX_REFS:
            raise TheGodfatherDenied(
                f'At most {MAX_REFS} operation'
                ' references per record')
        operations = []
        for ref in matter_refs:
            if not isinstance(ref, str) or not ref.strip():
                raise TheGodfatherDenied(
                    'Every operation reference must be a'
                    ' non-empty string')
            operations.append(ref.strip())
        now = self._now()
        record_id = f'the-godfather-record-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'THE_GODFATHER_RECORD_RECORDED',
                    actor=actor, record_id=record_id,
                    subject_ref=subject_ref.strip(),
                    matter_count=len(operations))
                db.execute(
                    'INSERT INTO the_godfather_records'
                    ' (record_id, subject_ref, matter_refs,'
                    ' matter_count, scope_ref, status, outcome,'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(row)

    def records_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'records', 'records view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM the_godfather_records'
                ' ORDER BY requested_at',
            ).fetchall()
        return [self._record_view(row) for row in rows]

    def record_view(self, actor, role, record_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, record_id, 'record view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        if row is None:
            raise TheGodfatherDenied(
                'Godfather record not found')
        return self._record_view(row)

    def record_action(self, actor, record_id, action, *,
                      region=None):
        """Approve or reject one requested Godfather record
        (operator only) — the recorded human decision the
        record lifecycle requires. Approval approves the
        RECORD; it authorizes no action against any subject."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RECORD_TRANSITIONS.get(action)
        if transitions is None:
            raise TheGodfatherDenied(
                f'Unknown record action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM the_godfather_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Godfather record not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise TheGodfatherDenied(
                        f"Cannot {action} a Godfather record"
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'THE_GODFATHER_RECORD_ACTION',
                    actor=actor, record_id=record_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE the_godfather_records SET status = ?,'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    def record_outcome(self, actor, record_id, outcome,
                       evidence_ref, *, region=None):
        """Record one approved record's outcome (operator
        only), against a presented evidence reference. An
        outcome without evidence is refused. A determination
        (GODFATHER_POSITION_CONFIRMED or MATTER_ACTION_REQUIRED) on a
        record declared with no operations is refused —
        NO_MATTERS_SUBMITTED: no operations were presented to
        determine from. An escalation outcome is a record for
        a human decision; it dispatches and enforces
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        if outcome not in OUTCOMES:
            raise TheGodfatherDenied(
                f'Unknown outcome: {outcome!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise TheGodfatherDenied(
                'An evidence reference is required to record an'
                ' outcome')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM the_godfather_records'
                    ' WHERE record_id = ?',
                    (record_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Godfather record not found')
                if row['status'] != 'APPROVED':
                    raise TheGodfatherDenied(
                        'Outcomes are recorded only for APPROVED'
                        f" Godfather records (this one is"
                        f" {row['status']})")
                if outcome in DETERMINATIONS \
                        and row['matter_count'] == 0:
                    raise TheGodfatherDenied(
                        'NO_MATTERS_SUBMITTED: a record'
                        ' declared with no operations cannot be'
                        f' determined {outcome}')
                receipt_id = self._record(
                    'THE_GODFATHER_OUTCOME_RECORDED',
                    actor=actor, record_id=record_id,
                    outcome=outcome,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE the_godfather_records SET status = ?,'
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
                'SELECT * FROM the_godfather_records'
                ' WHERE record_id = ?',
                (record_id,)).fetchone()
        return self._record_view(updated)

    # -- bloodline remit (Permanent Global Bloodline
    # Protection Directives, 2026-11-26) --------------

    @staticmethod
    def bloodline_design_view() -> dict:
        return {
            'directives_title': DIRECTIVES_TITLE,
            'established_by': DIRECTIVES_ESTABLISHED_BY,
            'effective_date': DIRECTIVES_EFFECTIVE_DATE,
            'designation': DIRECTIVES_DESIGNATION,
            'source': DIRECTIVES_SOURCE,
            'article_i_verbatim':
                FOUNDER_DIRECTIVES_ARTICLE_I_VERBATIM,
            'articles_iv_vi_verbatim':
                FOUNDER_DIRECTIVES_ARTICLES_IV_VI_VERBATIM,
            'scope_ref': BLOODLINE_DIRECTIVES_SCOPE,
            'discipline': BLOODLINE_DISCIPLINE,
            'invariants':
                list(GLOBAL_DIRECTIVES_INVARIANTS),
            'transport_matter_kinds':
                list(TRANSPORT_MATTER_KINDS),
            'funding_counterpart_platform':
                FUNDING_COUNTERPART_PLATFORM,
            'funding_counterpart_name':
                FUNDING_COUNTERPART_NAME,
            'reserve_counterpart_platform':
                RESERVE_COUNTERPART_PLATFORM,
            'funds_disbursed': False,
            'funds_held': False,
            'segregated_store': True,
            'note': (
                'Under the founder\u2019s Permanent Global'
                ' Bloodline Protection Directives'
                ' (effective 2026-11-26), supplementing the'
                ' Permanent Bloodline Protection Directive'
                ' without amending it, Godfather carries'
                ' private responsibilities exclusively for'
                ' the Sanders bloodline beside its own'
                ' independent public-facing commercial'
                ' business model (Article I): joint funding'
                ' approval with Sanders Sentinel for'
                ' Patriot Saint\u2019s private duties,'
                ' transportation coordination, and'
                ' emergency financial reserves held jointly'
                ' with Sanders Sentinel. Funding approval'
                ' is a recorded determination: a funding'
                ' request reads as approved only when both'
                ' this platform\u2019s and Sanders'
                ' Sentinel\u2019s determinations stand'
                ' recorded against it \u2014 one side alone'
                ' never reads as fully approved. The'
                ' platform disburses nothing and holds no'
                ' funds: reserves are a register of'
                ' designations and joint approvals, not'
                ' platform-held money, and transportation'
                ' acquisition is coordination and records'
                ' \u2014 purchase and title execution remain'
                ' with the companies and humans. Every'
                ' matter, request, and designation is born'
                ' AWAITING_HUMAN_REVIEW and is kept in a'
                ' segregated store the commercial'
                ' operations never read. Articles IV\u2013VI'
                ' govern: Global By Design, permanent'
                ' bloodline exclusivity, and preservation'
                ' of each platform\u2019s original identity'
                ' and purpose \u2014 coordination without'
                ' merging.'),
        }

    @staticmethod
    def _joint_state(status, counterpart_ref):
        """The joint state of a two-platform approval: a
        determination on one side alone never reads as
        fully approved."""
        if status == 'AWAITING_HUMAN_REVIEW':
            return 'AWAITING_DETERMINATION'
        if status == 'DECLINED':
            return 'NOT_APPROVED'
        if counterpart_ref:
            return 'JOINTLY_APPROVED'
        return 'AWAITING_COUNTERPART'

    # -- transportation coordination matters -----------

    @staticmethod
    def _transport_matter_view(row):
        return {
            'matter_id': row['matter_id'],
            'matter_kind': row['matter_kind'],
            'member_ref': row['member_ref'],
            'detail_ref': row['detail_ref'],
            'status': row['status'],
            'coordination_ref': row['coordination_ref'],
            'scope_ref': BLOODLINE_DIRECTIVES_SCOPE,
            'segregated_store': True,
            'opened_by': row['opened_by'],
            'opened_at': row['opened_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def open_transport_matter(self, actor, matter_kind,
                              member_ref, detail_ref, *,
                              region=None):
        """Open one transportation coordination matter
        (operator only) in the segregated bloodline
        store. A matter is a coordination record, by
        reference only: the kind of transportation
        responsibility under Article I (acquisition by
        mode, provision by reach, emergency or medical
        transportation, evacuation or repatriation
        arrangement, insurance, maintenance, repairs,
        or replacement), the bloodline member by
        reference, and the matter's detail by
        reference. It is born AWAITING_HUMAN_REVIEW
        and moves only on a human operator's recorded
        decision. Opening a matter acquires nothing
        and moves no money — the platform coordinates;
        humans and the companies execute."""
        self._geo(region)
        self._require_operator(actor)
        if matter_kind not in TRANSPORT_MATTER_KINDS:
            raise TheGodfatherDenied(
                f'Unknown transportation matter kind:'
                f' {matter_kind!r}')
        for label, value in (('member_ref', member_ref),
                             ('detail_ref', detail_ref)):
            if not isinstance(value, str) or not value.strip():
                raise TheGodfatherDenied(
                    f'A {label} is required')
        now = self._now()
        matter_id = (f'the-godfather-transport-matter-'
                     f'{uuid.uuid4().hex[:16]}')
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'THE_GODFATHER_TRANSPORT_MATTER_OPENED',
                    actor=actor, matter_id=matter_id,
                    matter_kind=matter_kind,
                    scope_ref=BLOODLINE_DIRECTIVES_SCOPE)
                db.execute(
                    'INSERT INTO'
                    ' the_godfather_bloodline_transport_matters'
                    ' (matter_id, matter_kind, member_ref,'
                    ' detail_ref, status, coordination_ref,'
                    ' opened_by, opened_at, updated_by,'
                    ' updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (matter_id, matter_kind,
                     member_ref.strip(), detail_ref.strip(),
                     'AWAITING_HUMAN_REVIEW', None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_transport_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._transport_matter_view(row)

    def transport_matters_list(self, actor, role, *,
                               region=None):
        self._geo(region)
        self._guard_access(actor, role, 'transport-matters',
                           'transport matters view')
        with self._bloodline_connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_transport_matters'
                ' ORDER BY opened_at').fetchall()
        return [self._transport_matter_view(row) for row in rows]

    def transport_matter_view(self, actor, role, matter_id, *,
                              region=None):
        self._geo(region)
        self._guard_access(actor, role, matter_id,
                           'transport matter view')
        with self._bloodline_connect() as db:
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_transport_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        if row is None:
            raise TheGodfatherDenied(
                'Transportation matter not found')
        return self._transport_matter_view(row)

    def transport_matter_action(self, actor, matter_id,
                                action, *, region=None):
        """Approve or reject one transportation matter
        awaiting human review (operator only) — the
        recorded human decision the remit requires.
        Approval approves the coordination matter; it
        executes no purchase and transfers no title."""
        self._geo(region)
        self._require_operator(actor)
        transitions = TRANSPORT_MATTER_TRANSITIONS.get(action)
        if transitions is None:
            raise TheGodfatherDenied(
                f'Unknown transportation matter action:'
                f' {action!r}')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_transport_matters'
                    ' WHERE matter_id = ?',
                    (matter_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Transportation matter not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise TheGodfatherDenied(
                        f'Cannot {action} a transportation'
                        f" matter in status {row['status']}")
                receipt_id = self._record(
                    'THE_GODFATHER_TRANSPORT_MATTER_ACTION',
                    actor=actor, matter_id=matter_id,
                    action=action, from_status=row['status'],
                    to_status=new_status)
                db.execute(
                    'UPDATE'
                    ' the_godfather_bloodline_transport_matters'
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
                ' the_godfather_bloodline_transport_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._transport_matter_view(updated)

    def record_transport_coordination(self, actor, matter_id,
                                      coordination_ref, *,
                                      region=None):
        """Record, against an APPROVED transportation
        matter, the coordination a human arranged
        (operator only), by reference: a vehicle or
        passage located, a carrier engaged by the
        companies, an evacuation arranged. The platform
        records the coordination — it performs none of
        it, acquires nothing, and moves no money."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(coordination_ref, str) \
                or not coordination_ref.strip():
            raise TheGodfatherDenied(
                'A coordination reference is required to'
                ' record coordination')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_transport_matters'
                    ' WHERE matter_id = ?',
                    (matter_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Transportation matter not found')
                if row['status'] != 'APPROVED':
                    raise TheGodfatherDenied(
                        'Coordination is recorded only for'
                        ' APPROVED transportation matters'
                        f" (this one is {row['status']})")
                receipt_id = self._record(
                    'THE_GODFATHER_TRANSPORT_COORDINATION_RECORDED',
                    actor=actor, matter_id=matter_id,
                    coordination_ref=coordination_ref.strip())
                db.execute(
                    'UPDATE'
                    ' the_godfather_bloodline_transport_matters'
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
                ' the_godfather_bloodline_transport_matters'
                ' WHERE matter_id = ?',
                (matter_id,)).fetchone()
        return self._transport_matter_view(updated)

    # -- joint funding approval (Article I, with
    # Sanders Sentinel) --------------------------------

    @staticmethod
    def _funding_request_view(row):
        joint_state = TheGodfatherService._joint_state(
            row['status'],
            row['counterpart_determination_ref'])
        return {
            'request_id': row['request_id'],
            'matter_ref': row['matter_ref'],
            'detail_ref': row['detail_ref'],
            'status': row['status'],
            'determination': (
                row['status'] if row['status']
                in ('APPROVED', 'DECLINED') else None),
            'determination_ref': (
                row['request_id'] if row['status']
                == 'APPROVED' else None),
            'counterpart_platform':
                row['counterpart_platform'],
            'counterpart_name': FUNDING_COUNTERPART_NAME,
            'counterpart_required': True,
            'counterpart_determination_ref':
                row['counterpart_determination_ref'],
            'joint_state': joint_state,
            # One side alone never reads as fully
            # approved: this is True only when both
            # determinations stand recorded.
            'funding_approved':
                joint_state == 'JOINTLY_APPROVED',
            'funds_disbursed': False,
            'funds_held': False,
            'scope_ref': BLOODLINE_DIRECTIVES_SCOPE,
            'segregated_store': True,
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def open_funding_request(self, actor, matter_ref,
                             detail_ref, *, region=None):
        """Open one funding request (operator only) in
        the segregated bloodline store: a request, by
        reference, for funding necessary for Patriot
        Saint to fulfill its private duties (the
        Patriot Saint matter it serves, by reference,
        and the request's detail, by reference). It is
        born AWAITING_HUMAN_REVIEW; this platform's
        determination is recorded against it by a human
        operator, and Sanders Sentinel's determination
        is required alongside it — neither side alone
        approves funding. Opening a request moves no
        money and holds no funds."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('matter_ref', matter_ref),
                             ('detail_ref', detail_ref)):
            if not isinstance(value, str) or not value.strip():
                raise TheGodfatherDenied(
                    f'A {label} is required')
        now = self._now()
        request_id = (f'the-godfather-funding-request-'
                      f'{uuid.uuid4().hex[:16]}')
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'THE_GODFATHER_FUNDING_REQUEST_OPENED',
                    actor=actor, request_id=request_id,
                    matter_ref=matter_ref.strip(),
                    counterpart_platform=
                    FUNDING_COUNTERPART_PLATFORM,
                    scope_ref=BLOODLINE_DIRECTIVES_SCOPE)
                db.execute(
                    'INSERT INTO'
                    ' the_godfather_bloodline_funding_requests'
                    ' (request_id, matter_ref, detail_ref,'
                    ' status, counterpart_platform,'
                    ' counterpart_determination_ref,'
                    ' requested_by, requested_at, updated_by,'
                    ' updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (request_id, matter_ref.strip(),
                     detail_ref.strip(),
                     'AWAITING_HUMAN_REVIEW',
                     FUNDING_COUNTERPART_PLATFORM, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' WHERE request_id = ?',
                (request_id,)).fetchone()
        return self._funding_request_view(row)

    def funding_requests_list(self, actor, role, *,
                              region=None):
        self._geo(region)
        self._guard_access(actor, role, 'funding-requests',
                           'funding requests view')
        with self._bloodline_connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' ORDER BY requested_at').fetchall()
        return [self._funding_request_view(row) for row in rows]

    def funding_request_view(self, actor, role, request_id, *,
                             region=None):
        self._geo(region)
        self._guard_access(actor, role, request_id,
                           'funding request view')
        with self._bloodline_connect() as db:
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' WHERE request_id = ?',
                (request_id,)).fetchone()
        if row is None:
            raise TheGodfatherDenied(
                'Funding request not found')
        return self._funding_request_view(row)

    def record_funding_determination(self, actor, request_id,
                                     action, *, region=None):
        """Record this platform's funding determination
        (operator only): approve or decline a funding
        request awaiting human review. The determination
        is a recorded decision inside the system — it
        disburses nothing. Even approved, the request
        does not read as fully approved until Sanders
        Sentinel's determination is also recorded
        against it."""
        self._geo(region)
        self._require_operator(actor)
        transitions = FUNDING_REQUEST_TRANSITIONS.get(action)
        if transitions is None:
            raise TheGodfatherDenied(
                f'Unknown funding determination action:'
                f' {action!r}')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_funding_requests'
                    ' WHERE request_id = ?',
                    (request_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Funding request not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise TheGodfatherDenied(
                        f'Cannot {action} a funding request'
                        f" in status {row['status']}")
                receipt_id = self._record(
                    'THE_GODFATHER_FUNDING_DETERMINATION',
                    actor=actor, request_id=request_id,
                    action=action, from_status=row['status'],
                    to_status=new_status,
                    funds_disbursed=False)
                db.execute(
                    'UPDATE'
                    ' the_godfather_bloodline_funding_requests'
                    ' SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE request_id = ?',
                    (new_status, actor, now, receipt_id,
                     request_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' WHERE request_id = ?',
                (request_id,)).fetchone()
        return self._funding_request_view(updated)

    def record_counterpart_funding_determination(
            self, actor, request_id,
            counterpart_determination_ref, *, region=None):
        """Record, against this platform's APPROVED
        funding request, Sanders Sentinel's
        determination, by reference (operator only).
        Only with both determinations recorded does the
        request read JOINTLY_APPROVED — fully approved.
        Recording the counterpart reference moves no
        money; execution of any payment remains a
        human act outside the platforms."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(counterpart_determination_ref, str) \
                or not counterpart_determination_ref.strip():
            raise TheGodfatherDenied(
                'A counterpart determination reference is'
                ' required')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_funding_requests'
                    ' WHERE request_id = ?',
                    (request_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Funding request not found')
                if row['status'] != 'APPROVED':
                    raise TheGodfatherDenied(
                        'A counterpart determination is'
                        ' recorded only against this'
                        " platform's APPROVED determination"
                        f" (this request is {row['status']})")
                if row['counterpart_determination_ref']:
                    raise TheGodfatherDenied(
                        'The counterpart determination is'
                        ' already recorded for this request')
                receipt_id = self._record(
                    'THE_GODFATHER_COUNTERPART_FUNDING_DETERMINATION',
                    actor=actor, request_id=request_id,
                    counterpart_platform=
                    FUNDING_COUNTERPART_PLATFORM,
                    counterpart_determination_ref=
                    counterpart_determination_ref.strip(),
                    joint_state='JOINTLY_APPROVED',
                    funds_disbursed=False)
                db.execute(
                    'UPDATE'
                    ' the_godfather_bloodline_funding_requests'
                    ' SET counterpart_determination_ref = ?,'
                    ' updated_by = ?, updated_at = ?,'
                    ' receipt_id = ? WHERE request_id = ?',
                    (counterpart_determination_ref.strip(),
                     actor, now, receipt_id, request_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' WHERE request_id = ?',
                (request_id,)).fetchone()
        return self._funding_request_view(updated)

    # -- emergency reserves register (Article I, held
    # jointly with Sanders Sentinel) -------------------

    @staticmethod
    def _reserve_view(row):
        joint_state = TheGodfatherService._joint_state(
            row['status'], row['counterpart_approval_ref'])
        return {
            'reserve_id': row['reserve_id'],
            'designation_ref': row['designation_ref'],
            'purpose_ref': row['purpose_ref'],
            'status': row['status'],
            'approval_ref': (
                row['reserve_id'] if row['status']
                == 'APPROVED' else None),
            'counterpart_platform':
                row['counterpart_platform'],
            'counterpart_name': RESERVE_COUNTERPART_NAME,
            'counterpart_required': True,
            'counterpart_approval_ref':
                row['counterpart_approval_ref'],
            'joint_state': joint_state,
            'jointly_approved':
                joint_state == 'JOINTLY_APPROVED',
            # A register of designations and joint
            # approvals — never platform-held money.
            'funds_held': False,
            'funds_disbursed': False,
            'scope_ref': BLOODLINE_DIRECTIVES_SCOPE,
            'segregated_store': True,
            'designated_by': row['designated_by'],
            'designated_at': row['designated_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def designate_reserve(self, actor, designation_ref,
                          purpose_ref, *, region=None):
        """Designate one emergency reserve (operator
        only) in the segregated bloodline store: a
        register entry, by reference — what the reserve
        is designated for, and its purpose for the
        protection of the bloodline. It is born
        AWAITING_HUMAN_REVIEW; this platform's approval
        and Sanders Sentinel's approval are both
        required for the designation to read jointly
        approved. A designation holds no funds: the
        register records designations and approvals,
        never money."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('designation_ref', designation_ref),
                             ('purpose_ref', purpose_ref)):
            if not isinstance(value, str) or not value.strip():
                raise TheGodfatherDenied(
                    f'A {label} is required')
        now = self._now()
        reserve_id = (f'the-godfather-reserve-'
                      f'{uuid.uuid4().hex[:16]}')
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'THE_GODFATHER_RESERVE_DESIGNATED',
                    actor=actor, reserve_id=reserve_id,
                    designation_ref=designation_ref.strip(),
                    counterpart_platform=
                    RESERVE_COUNTERPART_PLATFORM,
                    funds_held=False,
                    scope_ref=BLOODLINE_DIRECTIVES_SCOPE)
                db.execute(
                    'INSERT INTO'
                    ' the_godfather_bloodline_reserves'
                    ' (reserve_id, designation_ref,'
                    ' purpose_ref, status,'
                    ' counterpart_platform,'
                    ' counterpart_approval_ref, funds_held,'
                    ' designated_by, designated_at,'
                    ' updated_by, updated_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?)',
                    (reserve_id, designation_ref.strip(),
                     purpose_ref.strip(), 'AWAITING_HUMAN_REVIEW',
                     RESERVE_COUNTERPART_PLATFORM, None, 0,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' WHERE reserve_id = ?',
                (reserve_id,)).fetchone()
        return self._reserve_view(row)

    def reserves_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'reserves',
                           'reserves register view')
        with self._bloodline_connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' ORDER BY designated_at').fetchall()
        return [self._reserve_view(row) for row in rows]

    def reserve_view(self, actor, role, reserve_id, *,
                     region=None):
        self._geo(region)
        self._guard_access(actor, role, reserve_id,
                           'reserve view')
        with self._bloodline_connect() as db:
            row = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' WHERE reserve_id = ?',
                (reserve_id,)).fetchone()
        if row is None:
            raise TheGodfatherDenied('Reserve not found')
        return self._reserve_view(row)

    def reserve_action(self, actor, reserve_id, action, *,
                       region=None):
        """Record this platform's decision on one
        reserve designation awaiting human review
        (operator only): approve or decline. The
        decision is a register record — it holds no
        funds and moves no money."""
        self._geo(region)
        self._require_operator(actor)
        transitions = RESERVE_TRANSITIONS.get(action)
        if transitions is None:
            raise TheGodfatherDenied(
                f'Unknown reserve action: {action!r}')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_reserves'
                    ' WHERE reserve_id = ?',
                    (reserve_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Reserve not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise TheGodfatherDenied(
                        f'Cannot {action} a reserve'
                        f" designation in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'THE_GODFATHER_RESERVE_ACTION',
                    actor=actor, reserve_id=reserve_id,
                    action=action, from_status=row['status'],
                    to_status=new_status, funds_held=False)
                db.execute(
                    'UPDATE the_godfather_bloodline_reserves'
                    ' SET status = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE reserve_id = ?',
                    (new_status, actor, now, receipt_id,
                     reserve_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' WHERE reserve_id = ?',
                (reserve_id,)).fetchone()
        return self._reserve_view(updated)

    def record_counterpart_reserve_approval(
            self, actor, reserve_id, counterpart_approval_ref,
            *, region=None):
        """Record, against this platform's APPROVED
        reserve designation, Sanders Sentinel's
        approval, by reference (operator only). Only
        with both approvals recorded does the
        designation read JOINTLY_APPROVED. The register
        holds no funds at any point."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(counterpart_approval_ref, str) \
                or not counterpart_approval_ref.strip():
            raise TheGodfatherDenied(
                'A counterpart approval reference is'
                ' required')
        now = self._now()
        with self._bloodline_connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM'
                    ' the_godfather_bloodline_reserves'
                    ' WHERE reserve_id = ?',
                    (reserve_id,)).fetchone()
                if row is None:
                    raise TheGodfatherDenied(
                        'Reserve not found')
                if row['status'] != 'APPROVED':
                    raise TheGodfatherDenied(
                        'A counterpart approval is recorded'
                        " only against this platform's"
                        ' APPROVED designation (this reserve'
                        f" is {row['status']})")
                if row['counterpart_approval_ref']:
                    raise TheGodfatherDenied(
                        'The counterpart approval is already'
                        ' recorded for this reserve')
                receipt_id = self._record(
                    'THE_GODFATHER_COUNTERPART_RESERVE_APPROVAL',
                    actor=actor, reserve_id=reserve_id,
                    counterpart_platform=
                    RESERVE_COUNTERPART_PLATFORM,
                    counterpart_approval_ref=
                    counterpart_approval_ref.strip(),
                    joint_state='JOINTLY_APPROVED',
                    funds_held=False)
                db.execute(
                    'UPDATE the_godfather_bloodline_reserves'
                    ' SET counterpart_approval_ref = ?,'
                    ' updated_by = ?, updated_at = ?,'
                    ' receipt_id = ? WHERE reserve_id = ?',
                    (counterpart_approval_ref.strip(),
                     actor, now, receipt_id, reserve_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' WHERE reserve_id = ?',
                (reserve_id,)).fetchone()
        return self._reserve_view(updated)

    def disburse_funds(self, actor, *args, **kwargs):
        """Refused by name, unconditionally. Under the
        Permanent Global Bloodline Protection
        Directives and the reconciliation of record,
        no platform disburses or holds funds: funding
        approval is a recorded determination, and
        execution of any payment remains a human act.
        No argument, actor, or state changes that."""
        raise TheGodfatherDenied(
            'disburse_funds is refused: the Godfather'
            ' platform coordinates and records under the'
            ' Permanent Global Bloodline Protection'
            ' Directives \u2014 it disburses no funds and'
            ' holds no funds (GODFATHER_COORDINATION_ONLY)')

    def bloodline_remit(self, actor, role, *, region=None):
        """The bloodline remit read surface under the
        Directives: Article I of record, the
        invariants, and the remit's open records —
        transportation matters, funding requests, and
        reserve designations — with tallies over all.
        Guarded exactly as this platform's other record
        views; the commercial records are never read
        here, and this remit is never read by the
        commercial views."""
        self._geo(region)
        self._guard_access(actor, role, 'bloodline-remit',
                           'bloodline remit view')
        with self._bloodline_connect() as db:
            transport_by_status = {
                s: 0 for s in TRANSPORT_MATTER_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' the_godfather_bloodline_transport_matters'
                    ' GROUP BY status'):
                transport_by_status[row['status']] = row['n']
            transport_by_kind = {
                k: 0 for k in TRANSPORT_MATTER_KINDS}
            for row in db.execute(
                    'SELECT matter_kind, COUNT(*) AS n FROM'
                    ' the_godfather_bloodline_transport_matters'
                    ' GROUP BY matter_kind'):
                transport_by_kind[row['matter_kind']] = row['n']
            open_transport = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_transport_matters'
                ' WHERE status IN (?, ?) ORDER BY opened_at',
                TRANSPORT_OPEN_STATUSES).fetchall()
            funding_rows = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_funding_requests'
                ' ORDER BY requested_at').fetchall()
            reserve_rows = db.execute(
                'SELECT * FROM'
                ' the_godfather_bloodline_reserves'
                ' ORDER BY designated_at').fetchall()
        funding = [self._funding_request_view(row)
                   for row in funding_rows]
        reserves = [self._reserve_view(row)
                    for row in reserve_rows]
        view = self.bloodline_design_view()
        view['transport_matters_total'] = sum(
            transport_by_status.values())
        view['transport_matters_by_status'] = \
            transport_by_status
        view['transport_matters_by_kind'] = transport_by_kind
        view['open_transport_matters'] = [
            self._transport_matter_view(row)
            for row in open_transport]
        view['funding_requests'] = funding
        view['funding_jointly_approved'] = sum(
            1 for f in funding if f['funding_approved'])
        view['reserves'] = reserves
        view['reserves_jointly_approved'] = sum(
            1 for r in reserves if r['jointly_approved'])
        return view

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in RECORD_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n'
                    ' FROM the_godfather_records'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_outcome = {o: 0 for o in OUTCOMES}
            for row in db.execute(
                    'SELECT outcome, COUNT(*) AS n'
                    ' FROM the_godfather_records'
                    ' WHERE outcome IS NOT NULL GROUP BY outcome'):
                by_outcome[row['outcome']] = row['n']
            no_refs = db.execute(
                'SELECT COUNT(*) AS n FROM the_godfather_records'
                ' WHERE matter_count = 0').fetchone()['n']
            refs_total = db.execute(
                'SELECT COALESCE(SUM(matter_count), 0) AS n'
                ' FROM the_godfather_records').fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        with self._bloodline_connect() as db:
            transport_by_status = {
                s: 0 for s in TRANSPORT_MATTER_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM'
                    ' the_godfather_bloodline_transport_matters'
                    ' GROUP BY status'):
                transport_by_status[row['status']] = row['n']
            funding_jointly_approved = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' the_godfather_bloodline_funding_requests'
                " WHERE status = 'APPROVED' AND"
                ' counterpart_determination_ref IS NOT NULL'
            ).fetchone()['n']
            funding_total = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' the_godfather_bloodline_funding_requests'
            ).fetchone()['n']
            reserves_jointly_approved = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' the_godfather_bloodline_reserves'
                " WHERE status = 'APPROVED' AND"
                ' counterpart_approval_ref IS NOT NULL'
            ).fetchone()['n']
            reserves_total = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' the_godfather_bloodline_reserves'
            ).fetchone()['n']
        return {
            'identity': IDENTITY.to_dict(),
            'design': self.design_view(),
            'bloodline_directives': {
                'article': 'ARTICLE I \u2014 GODFATHER',
                'effective_date': DIRECTIVES_EFFECTIVE_DATE,
                'transport_matters_total':
                    sum(transport_by_status.values()),
                'transport_matters_by_status':
                    transport_by_status,
                'funding_requests_total': funding_total,
                'funding_jointly_approved':
                    funding_jointly_approved,
                'reserves_total': reserves_total,
                'reserves_jointly_approved':
                    reserves_jointly_approved,
                'funds_disbursed': False,
                'funds_held': False,
            },
            'records_total': sum(by_status.values()),
            'records_by_status': by_status,
            'records_by_outcome': by_outcome,
            'records_no_matters_submitted': no_refs,
            'matters_declared_total': refs_total,
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
                    raise TheGodfatherDenied(str(exc)) from exc
                self._record('THE_GODFATHER_CHECK_IN',
                             actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
