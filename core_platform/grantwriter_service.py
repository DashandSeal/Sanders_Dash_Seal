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

AMENDMENT — COMPLETE SERVICE JURISDICTION (founder-presented
2026-11-26 12:57 MST; adopted 2026-11-26 13:03 MST as an
AMENDMENT to her original purpose): the guarded record is
docs/GRANTWRITER_COMPLETE_SERVICE_JURISDICTION_2026-11-26.md.
Her original purpose (the grantwriter_purpose gate, APPROVED by
the founder 2026-11-25; statement of record in
ai_platform_approvals.json) stands governing and intact —
this amendment expands her jurisdiction and supersedes nothing
(founder ruling 2026-11-26 09:31 MST: adoptions amend the
original scope, never supersede it). The amendment adds: three
independent, concurrent service branches (public commercial;
private corporate for the four companies; platform funding);
a property acquisition objectives register exactly as the
founder assigned it; the seven-stage duty cycle as a case
lifecycle (PREPARE -> VALIDATE -> SUBMIT -> VERIFY_RECEIPT ->
CORRECT -> MANAGE_AWARDS -> CLOSE_OUT_RENEW); and the adopted
operating rules as structural properties of the machinery.

Authority (founder correction 2026-11-26 13:12 MST): there is
NO per-case founder authorization gate. Grantwriter executes
submissions within her existing Founder-granted authority
— the adopted jurisdiction and her original purpose are
the standing grant — plus applicable client
authorizations for public work. Submission records carry an
AUTHORITY BASIS (the standing Founder grant of record, or the
client authorization of record), never a per-application
founder approval. JustGrants roles (Entity Administrator /
Application Submitter / Authorized Representative) are modeled
as facts of record per entity, never as a system reservation:
for the seeded case of record the founder currently holds the
Application Submitter role — a changeable role-assignment
fact, not a restriction on her authority.

The legacy application workflow in this module is unchanged:
its record_submission remains a RECORDED state only and
transmits nothing. The jurisdiction case lifecycle is the
amendment's own machinery, in this service's own store,
beside it.

MOTHER UPGRADE (founder direction 2026-11-26 16:42 MST:
"give Grantwriter everything she truly needs to perform her
duties \u2014 upgrade everything"): three additions, all
records in this service's own store beside the jurisdiction
machinery. (1) TARGETING PARAMETERS OF RECORD \u2014 the
founder's pursuit floor (2026-11-26 16:29 MST: discovery and
pursuit target opportunities of $10,000,000 and up; the floor
steers new hunts and cancels no case of record), his
partnership rule as corrected and clarified the same
afternoon (16:31\u201316:33 MST: joint and collaborative
applications are made only among the four Sanders companies
\u2014 those are the joint partners; an external co-applicant
is refused by name in her machinery), and his global-by-design
key principle (16:12 MST: her submission access is a global
register, every jurisdiction's system keyed the same way
\u2014 the founder's authority or her own seat, plus her
records). (2) THE ACCESS REGISTER \u2014 her keys as platform
records, one entry per system, in truthful laddered states
verified 2026-11-26 (JustGrants key of record active through
the founder's activated Entity Administrator authority, her
own-name seat pending the 2026-11-27 session of record;
SAM.gov and Grants.gov verified; eRA Commons, HRSA EHBs and
FEMA GO not started; GrantSolutions, PMS and ASAP stand
AT_AWARD \u2014 provisioned at award or invitation, recorded
as their state, not as a gap). The register holds NO
credentials and NO passwords, ever. (3) DISCOVERY \u2014 a
native client for the Grants.gov public opportunities API,
carried as a LABELED, detachable input tool: a data source,
never her decision-making. Discovery results record as
records under her targeting (the floor applied where the
source exposes amounts); a discovery record never auto-creates
a pursuit case \u2014 a case is born only through her duty
cycle. The connection state is reported truthfully: it reads
CONNECTED only when a discovery run has actually been
answered by the source, and NOT_CONNECTED otherwise.

NAICS LOCK-IN — 2026-11-26: under the founder's directive
of 2026-11-26 (reconcile the platforms that do not have
with groups of six NACI industry codes that would benefit
humanity as a whole, not fragmented), this platform's
identity record carries the reconciled six: 541611,
541612, 541618, 541512, 611430, 813211 — COMPOSED per the
NACI six-code reconciliation of 2026-11-26. The reconciled
six govern the built identity from this lock-in forward.
"""

import json
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
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
    naics_codes=('541611', '541612', '541618', '541512', '611430', '813211'),
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

# -- Complete Service Jurisdiction (amendment, adopted 2026-11-26) ---

JURISDICTION_GUARDED_DOCUMENT = (
    'docs/GRANTWRITER_COMPLETE_SERVICE_JURISDICTION_2026-11-26.md')
JURISDICTION_TITLE = 'Grantwriter \u2014 Complete Service Jurisdiction'
JURISDICTION_ADOPTED = '2026-11-26'
JURISDICTION_AMENDS = (
    "Her original purpose of record \u2014 the founder's statement "
    'approved 2026-11-25 under the grantwriter_purpose gate: '
    'publicly a grant-services business; privately serving every '
    'platform and S & G Security Inc, Sanders Home Healthcare '
    '& Caregivers LLC, Sanders Senior Living LLC, Sanders Legal '
    'Helpers LLC; the property closing line as corrected by the '
    'founder (two upscale office buildings, upscale houses, two '
    'warehouses)')
AMEND_NEVER_SUPERSEDE_RULING = (
    'Nothing is adopted if it supercede the original directives '
    'those are to be immediately changed to amend the original '
    'scope never supercede them')
AMEND_NEVER_SUPERSEDE_RULING_SOURCE = (
    "The founder's ruling of 2026-11-26 09:31 MST, quoted "
    'verbatim (his spelling carried as given): an adoption '
    'amends the original scope, it never supersedes it')

JURISDICTION_STATEMENT = (
    'Complete service jurisdiction\n'
    'GRANTWRITER\n'
    'Global funding acquisition and grant management\n'
    'Public\n'
    'Commercial grant services\n'
    '4 companies\n'
    'Private corporate funding\n'
    '140+ RTSA\n'
    'Platform-specific funding\n'
    'Property acquisition objectives\n'
    '2\n'
    'Upscale office buildings\n'
    'Multiple\n'
    'Upscale houses\n'
    '2\n'
    'Warehouses\n'
    'All three service branches must function independently and concurrently, without merging company identities, platform scopes, client records or financial accounts.\n'
    'Prepare — Develop complete narratives, budgets, supporting documents and applications.\n'
    'Validate — Check accuracy against original funding requirements.\n'
    'Submit — Execute actual submissions through authorized interfaces.\n'
    'Verify receipt — Obtain official tracking numbers and agency acceptance confirmations.\n'
    'Correct — Resolve errors, rejected submissions and requests for additional information.\n'
    'Manage awards — Track decisions, award conditions, funding and reporting.\n'
    'Close out and renew — Complete reporting, identify continuation funding and maintain permanent records.\n'
    'Grantwriter must continue performing every functioning duty while additional capabilities are developed.\n'
    'No incomplete platform profile shall unnecessarily prevent an otherwise eligible application.\n'
    'She must pursue individual, joint, collaborative and ecosystem-wide funding opportunities wherever permitted.\n'
    'She must support every legitimate submission method, not exclusively API-based submissions.\n'
    'She must execute actual authorized submissions without unnecessary internal approval gates.\n'
    'She must explore alternative eligible funding structures rather than prematurely discard opportunities.\n'
    'Her property acquisition objectives must remain exactly as you assigned them, without my imposing additional use restrictions.\n'
    'Testing must strengthen her operations, not unnecessarily suspend them.\n'
    'What must remain fully intact\n'
    "Grantwriter's authority and capabilities must encompass:\n"
    'Her independent public-facing commercial business.\n'
    'The complete family of four companies.\n'
    'The entire 140+ RTSA ecosystem.\n'
    'Two upscale office buildings.\n'
    'Upscale houses.\n'
    'Two warehouses.\n'
    'Global funding discovery, preparation, submission, acquisition and administration.\n'
    'Expand her capabilities, not her restrictions. Amend the original directives, never supersede them.\n'
    'Global By Design. The Sanders Way! 💙🩶')

JURISDICTION_BRANCHES = (
    {'branch': 'PUBLIC_COMMERCIAL',
     'name': 'Public \u2014 commercial grant services',
     'scope': 'Her independent public-facing commercial '
              'business. Each client is its own record scope; '
              'authority for public work is the client '
              'authorization of record.'},
    {'branch': 'PRIVATE_CORPORATE',
     'name': 'Private \u2014 corporate funding',
     'scope': 'The complete family of four companies, a '
              'separate record scope per company; authority '
              'is the standing Founder grant of record.'},
    {'branch': 'PLATFORM_FUNDING',
     'name': 'Platform-specific funding',
     'scope': "The entire ecosystem of the statement's "
              "'140+ RTSA' (canonical count of record: 140 "
              'platforms), a separate record scope per '
              'platform; authority is the standing Founder '
              'grant of record.'},
)
JURISDICTION_BRANCH_IDS = tuple(
    entry['branch'] for entry in JURISDICTION_BRANCHES)

JURISDICTION_COMPANIES = (
    'S & G Security Inc.',
    'Sanders Home Healthcare & Caregivers LLC',
    'Sanders Senior Living LLC',
    'Sanders Legal Helpers LLC',
)

DUTY_CYCLE_STAGES = (
    'PREPARE', 'VALIDATE', 'SUBMIT', 'VERIFY_RECEIPT',
    'CORRECT', 'MANAGE_AWARDS', 'CLOSE_OUT_RENEW',
)
DUTY_CYCLE_STAGE_MEANINGS = {
    'PREPARE': 'Develop complete narratives, budgets, '
               'supporting documents and applications',
    'VALIDATE': 'Check accuracy against original funding '
                'requirements',
    'SUBMIT': 'Execute actual submissions through authorized '
              'interfaces',
    'VERIFY_RECEIPT': 'Obtain official tracking numbers and '
                      'agency acceptance confirmations',
    'CORRECT': 'Resolve errors, rejected submissions and '
               'requests for additional information',
    'MANAGE_AWARDS': 'Track decisions, award conditions, '
                     'funding and reporting',
    'CLOSE_OUT_RENEW': 'Complete reporting, identify '
                       'continuation funding and maintain '
                       'permanent records',
}
# The adopted duty cycle as a checked lifecycle. CORRECT is
# reached from VERIFY_RECEIPT and returns to SUBMIT (a corrected
# resubmission runs the cycle again). DISCARDED is not a cycle
# stage: it is reachable only through discard_jurisdiction_case,
# which requires an alternative-structures check of record.
_DUTY_CYCLE_TRANSITIONS = {
    'PREPARE': frozenset(('VALIDATE',)),
    'VALIDATE': frozenset(('SUBMIT',)),
    'SUBMIT': frozenset(('VERIFY_RECEIPT',)),
    'VERIFY_RECEIPT': frozenset(('CORRECT', 'MANAGE_AWARDS')),
    'CORRECT': frozenset(('SUBMIT',)),
    'MANAGE_AWARDS': frozenset(('CLOSE_OUT_RENEW',)),
    'CLOSE_OUT_RENEW': frozenset(),
    'DISCARDED': frozenset(),
}

SUBMISSION_METHODS = ('PORTAL', 'API', 'MAIL', 'EMAIL', 'IN_PERSON')

# Authority basis (founder correction 2026-11-26 13:12 MST):
# there is NO per-case founder authorization gate. Grantwriter
# executes submissions within her existing Founder-granted
# authority \u2014 the adopted jurisdiction and her original
# purpose are the standing grant \u2014 plus applicable client
# authorizations for public work. A submission record carries
# the basis it stands on, never a per-application approval.
AUTHORITY_BASES = ('FOUNDER_STANDING_GRANT', 'CLIENT_AUTHORIZATION')
_BRANCH_AUTHORITY_BASIS = {
    'PUBLIC_COMMERCIAL': 'CLIENT_AUTHORIZATION',
    'PRIVATE_CORPORATE': 'FOUNDER_STANDING_GRANT',
    'PLATFORM_FUNDING': 'FOUNDER_STANDING_GRANT',
}

OPPORTUNITY_KINDS = (
    'INDIVIDUAL', 'JOINT', 'COLLABORATIVE', 'ECOSYSTEM_WIDE')

# Her property acquisition objectives, exactly as the founder
# assigned them. Objectives of record: the platform adds NO use
# restrictions to them.
PROPERTY_OBJECTIVES = (
    {'objective': 'Upscale office buildings',
     'quantity_of_record': '2'},
    {'objective': 'Upscale houses',
     'quantity_of_record': 'Multiple'},
    {'objective': 'Warehouses',
     'quantity_of_record': '2'},
)

FEE_BAR = {
    'refused_structure': 'PERCENTAGE_OF_AWARD',
    'refusal': 'GRANTWRITER_PERCENTAGE_OF_AWARD_PRICING_REFUSED',
    'basis': 'Percentage-of-award grant pricing is barred '
             '(GPA Ethics; AFP; 2 CFR 200.442) \u2014 law of '
             'record, untouched by the amendment',
}

OPERATING_RULES = (
    {'rule': 'FUNCTIONING_DUTIES_NEVER_SUSPEND',
     'statement': 'Grantwriter continues performing every '
                  'functioning duty while additional '
                  'capabilities are developed. Testing '
                  'strengthens her operations, not '
                  'unnecessarily suspends them. This service '
                  'exposes no disable or suspend switch.'},
    {'rule': 'INCOMPLETE_PROFILE_DOES_NOT_BLOCK',
     'statement': 'No incomplete platform profile '
                  'unnecessarily prevents an otherwise '
                  'eligible application: profile gaps record '
                  'as gaps on the case. Only a funder\u2019s '
                  'own mandatory requirement may block a '
                  'submission, and the record names it as the '
                  'funder\u2019s.'},
    {'rule': 'ALL_OPPORTUNITY_KINDS_PURSUABLE',
     'statement': 'She pursues individual, joint, '
                  'collaborative and ecosystem-wide funding '
                  'opportunities wherever permitted.'},
    {'rule': 'EVERY_LEGITIMATE_SUBMISSION_METHOD',
     'statement': 'She supports every legitimate submission '
                  'method \u2014 portal, API, mail, email, '
                  'in-person \u2014 not exclusively API-based '
                  'submissions.'},
    {'rule': 'NO_PER_CASE_FOUNDER_AUTHORIZATION_GATE',
     'statement': 'She executes submissions within her '
                  'existing Founder-granted authority (the '
                  'standing grant of record) plus applicable '
                  'client authorizations. She never '
                  're-requests permission for responsibilities '
                  'already assigned to her; no per-case '
                  'founder approval object exists in her '
                  'machinery.'},
    {'rule': 'ALTERNATIVE_STRUCTURES_BEFORE_DISCARD',
     'statement': 'She explores alternative eligible funding '
                  'structures rather than prematurely '
                  'discarding opportunities: a case may be '
                  'discarded only after an alternative-'
                  'structures check of record.'},
    {'rule': 'PROPERTY_OBJECTIVES_EXACTLY_AS_ASSIGNED',
     'statement': 'Her property acquisition objectives remain '
                  'exactly as the founder assigned them; the '
                  'platform imposes no additional use '
                  'restrictions.'},
    {'rule': 'BRANCHES_NEVER_MERGE',
     'statement': 'All three service branches function '
                  'independently and concurrently, without '
                  'merging company identities, platform '
                  'scopes, client records or financial '
                  'accounts. Cross-branch access to a case is '
                  'refused by name.'},
)

# JustGrants roles (founder correction 2026-11-26 13:12 MST):
# three DISTINCT roles, modeled as facts of record per entity
# \u2014 never as a system reservation. Submission is not
# reserved to the Entity Administrator; JustGrants expressly
# accommodates grant writers serving multiple entities.
JUSTGRANTS_ROLES = (
    'ENTITY_ADMINISTRATOR', 'APPLICATION_SUBMITTER',
    'AUTHORIZED_REPRESENTATIVE')
JUSTGRANTS_ROLE_MEANINGS = {
    'ENTITY_ADMINISTRATOR': 'Assigns and manages authorized '
                            'users',
    'APPLICATION_SUBMITTER': 'Completes and submits '
                             'applications',
    'AUTHORIZED_REPRESENTATIVE': 'Representative and '
                                 'award-acceptance '
                                 'responsibilities',
}
_ROLE_SYSTEMS = {'JUSTGRANTS': JUSTGRANTS_ROLES}

# The seeded case of record: the live JustGrants application.
# Stage history is recorded at its factual positions (epoch
# seconds, UTC): submitted 2026-11-21, Grants.gov validation
# passed 2026-11-22, agency retrieval confirmed 2026-11-25.
SEEDED_JUSTGRANTS_CASE_ID = 'A-547904'
_SEED_ROLE_ASSIGNMENTS = (
    ('JUSTGRANTS', 'Sanders Home Healthcare & Caregivers LLC',
     'ENTITY_ADMINISTRATOR', 'Roosevelt Sanders'),
    ('JUSTGRANTS', 'Sanders Home Healthcare & Caregivers LLC',
     'APPLICATION_SUBMITTER', 'Roosevelt Sanders'),
    ('JUSTGRANTS', 'Sanders Home Healthcare & Caregivers LLC',
     'AUTHORIZED_REPRESENTATIVE', 'Roosevelt Sanders'),
)
_SEED_CASE_STAGES = (
    {'stage': 'PREPARE', 'recorded_at': 1763683200,
     'recorded_by': 'RooseveltSanders',
     'note': 'Step 1 package prepared for the NIJ FY26 Elder '
             'Abuse opportunity (GRANT14829509)'},
    {'stage': 'SUBMIT', 'recorded_at': 1763683200,
     'recorded_by': 'RooseveltSanders',
     'submission_method': 'PORTAL',
     'authority_basis': 'FOUNDER_STANDING_GRANT',
     'note': 'Submitted 2026-11-21 through the Grants.gov / '
             'JustGrants portal under the standing Founder '
             'grant. Application Submitter of record: '
             'Roosevelt Sanders \u2014 a role-assignment fact '
             'of record, not a restriction on '
             'Grantwriter\u2019s authority'},
    {'stage': 'VALIDATE', 'recorded_at': 1763769600,
     'recorded_by': 'GRANTWRITER_RECORD',
     'note': 'Validation of record: Grants.gov validation '
             'passed 2026-11-22 \u2014 the receiving '
             'system\u2019s validation of the submitted '
             'package, recorded at its factual position '
             'after submission'},
    {'stage': 'VERIFY_RECEIPT', 'recorded_at': 1764028800,
     'recorded_by': 'GRANTWRITER_RECORD',
     'tracking_ref': 'A-547904',
     'note': 'Agency retrieval confirmed 2026-11-25; official '
             'application number A-547904. Step 2 in '
             'preparation \u2014 due 2026-12-07 8:59 PM EST'},
)

# The founder's further Grants.gov workspaces of record
# (founder's own Grants.gov Applicant Dashboard, 2026-11-26,
# cross-checked by an independent in-account read the same
# hour): both stand in preparation — Grants.gov "In
# Progress" — for Sanders Home Healthcare & Caregivers LLC
# as applicant, so both seed at PREPARE in the
# PRIVATE_CORPORATE branch, identified by their workspace
# IDs. No Grants.gov tracking numbers are of record for
# either workspace, and none are invented. Stage positions
# use the register's epoch convention of the A-547904 seed.
SEEDED_WORKSPACE_CASE_IDS = ('WS01787570', 'WS01783365')
_SEED_WORKSPACE_CASES = (
    {'case_id': 'WS01787570',
     'scope_ref': 'Sanders Home Healthcare & Caregivers LLC',
     'title': 'SHHC LLC - National Dislocated Worker '
              'Grant - 2026',
     'funder': 'U.S. Department of Labor, Employment and '
               'Training Administration (ETA)',
     'external_ref': 'ETA-TEGL-09-24-CH1',
     'recorded_at': 1763769600,
     'note': 'Workspace of record in Grants.gov (founder\u2019s '
             'Applicant Dashboard, 2026-11-26): SHHC LLC - '
             'National Dislocated Worker Grant - 2026, '
             'opportunity ETA-TEGL-09-24-CH1 (National '
             'Dislocated Worker Grants). In preparation '
             '\u2014 last activity 2026-11-22. Closing date '
             '2026-12-31'},
    {'case_id': 'WS01783365',
     'scope_ref': 'Sanders Home Healthcare & Caregivers LLC',
     'title': 'SHHC \u2013 NIJ Justice System Research \u2013 2026',
     'funder': 'National Institute of Justice (NIJ)',
     'external_ref': 'O-NIJ-2026-172800',
     'recorded_at': 1763164800,
     'note': 'Workspace of record in Grants.gov (founder\u2019s '
             'Applicant Dashboard, 2026-11-26): SHHC \u2013 NIJ '
             'Justice System Research \u2013 2026, opportunity '
             'O-NIJ-2026-172800. In preparation \u2014 last '
             'activity 2026-11-15. Its closing date '
             '2026-11-16 has passed with the workspace still '
             'showing In Progress: submission status NOT '
             'ESTABLISHED \u2014 whether it was submitted '
             'another way or set aside awaits the '
             'founder\u2019s word. Recorded at PREPARE on the '
             'evidence of record; not marked submitted, '
             'closed or awarded'},
)



# -- Mother upgrade (founder direction 2026-11-26) -------------------
# Targeting parameters of record, the access register, and the
# labeled discovery connection. Founder documents of record:
# the pursuit-floor direction of 2026-11-26 (16:29 MST) as
# corrected 16:31 MST and clarified 16:33 MST, and the
# global-by-design key direction of 2026-11-26 16:12 MST.

PURSUIT_FLOOR_USD = 10_000_000

EXTERNAL_PARTNER_REFUSAL = 'GRANTWRITER_EXTERNAL_PARTNER_REFUSED'

TARGETING_PARAMETERS = {
    'pursuit_floor_usd': PURSUIT_FLOOR_USD,
    'pursuit_floor_of_record': '$10,000,000 and up',
    'pursuit_floor_scope': (
        'Discovery and pursuit target opportunities of '
        '$10,000,000 and up. The floor steers what she hunts '
        'going forward; it cancels no case of record \u2014 '
        'cases already of record and in motion continue on '
        'their own footing'),
    'pursuit_floor_source': (
        'Founder direction 2026-11-26 16:29 MST: \u201cWe have '
        'go after grants $10 million dollars and up to make a '
        'real world difference\u201d'),
    'partnership_rule': 'JOINT_PARTNERS_ARE_THE_FOUR_COMPANIES_ONLY',
    'joint_partners': JURISDICTION_COMPANIES,
    'external_co_applicants': 'REFUSED_BY_NAME',
    'external_partner_refusal': EXTERNAL_PARTNER_REFUSAL,
    'partnership_rule_source': (
        'Founder correction 2026-11-26 16:31 MST (\u201cNo '
        'joint appreciation only our companies\u201d \u2014 '
        'appreciation carried as given; operative word: '
        'application), clarified 16:33 MST: \u201cThose are '
        'our joint partners\u201d \u2014 the four Sanders '
        'companies are each other\u2019s joint partners; joint '
        'and collaborative applications run inside the Sanders '
        'house, never with outside parties'),
    'access_principle': 'GLOBAL_BY_DESIGN_KEY_REGISTER',
    'access_principle_statement': (
        'Her submission access is a global register: every '
        'jurisdiction\u2019s system keyed the same way \u2014 '
        'the founder\u2019s authority or her own seat, plus her '
        'platform records of them'),
    'access_principle_source': (
        'Founder direction 2026-11-26 16:12 MST: '
        '\u201cshe\u2019s got to be able to submit grants '
        'globally by design\u201d'),
}

# The access register: her keys as platform records, one entry
# per system, in truthful laddered states. Facts verified
# 2026-11-26 and 2026-11-27 and stated exactly as verified; nothing here is a
# credential \u2014 the register never holds a password.
ACCESS_STATES = (
    'KEY_OF_RECORD_ACTIVE', 'VERIFIED', 'SUBMITTED',
    'PENDING', 'NOT_STARTED', 'AT_AWARD')
ACCESS_REGISTER_SEED = (
    {'system': 'JUSTGRANTS',
     'state': 'KEY_OF_RECORD_ACTIVE',
     'basis': 'Her key of record runs through the founder’s '
              'activated Entity Administrator authority (his DOJ '
              'account was activated 2026-11-26), and her own-name '
              'Application Submitter seat now stands completed and '
              'verified (2026-11-27)',
     'detail': 'Own-name seat COMPLETE + VERIFIED 2026-11-27: invite '
               'sent from the founder’s DIAMD Entity Administrator '
               'session to daddydik323@gmail.com and activated the '
               'same day. From the seat’s own JustGrants session, '
               'Applications – SANDERS HOME HEALTHCARE & CAREGIVERS '
               'LLC lists GRANT14829509 (NIJ FY 2026 Research on the '
               'Abuse, Neglect, and Exploitation of Elderly '
               'Individuals; application A-547904) with Application '
               'Submitter: ROOSEVELT SANDERS, Status New; the Step 2 '
               'task "10d Verify & Confirm (Initiate)" stands '
               'assigned to the seat; package due December 7, 2026 '
               '8:59:00 PM EST. Participants of record on A-547904: '
               'ROOSEVELT SANDERS — Entity Administrator and '
               'ROOSEVELT SANDERS — Application Submitter. '
               'Authorized Representative remains the founder',
     'verified_on': '2026-11-27'},
    {'system': 'SAM.GOV',
     'state': 'VERIFIED',
     'basis': 'Founder is Administrator (verified in SAM.gov '
              '2026-11-26); her access runs through his '
              'entity administration',
     'detail': 'Sanders Home Healthcare & Caregivers LLC: '
               'Active Registration, expires 2027-11-11 '
               '(UEI QW8BRKNCF573, CAGE 27KB6). Sanders '
               'Senior Living LLC (UEI FJAZARX3NJA6): '
               'registration Work In Progress. Sanders Legal '
               'Helpers LLC (UEI J9FUQW4EXQ17): registration '
               'Work In Progress. S & G Security Inc.: no '
               'registration of record',
     'verified_on': '2026-11-26'},
    {'system': 'GRANTS.GOV',
     'state': 'VERIFIED',
     'basis': 'Submission under the founder\u2019s active '
              'Expanded AOR; her workspace participation '
              'attaches per application',
     'detail': 'Sanders Home Healthcare & Caregivers LLC '
               'linked (UEI QW8BRKNCF573); founder is EBiz '
               'POC with APPROVED / ACTIVE roles: Expanded '
               'AOR, Standard AOR, Workspace Manager '
               '(verified in Grants.gov 2026-11-26)',
     'verified_on': '2026-11-26'},
    {'system': 'ERA_COMMONS',
     'state': 'NOT_STARTED',
     'basis': 'Organization registration with the founder as '
              'Signing Official; the SAM.gov registration it '
              'requires stands Active',
     'detail': 'Not started \u2014 Tier 2, create ahead of '
               'need (NIH / eRA Commons)',
     'verified_on': '2026-11-26'},
    {'system': 'HRSA_EHBS',
     'state': 'VERIFIED',
     'basis': 'Her HRSA key is HELD for SANDERS HOME HEALTHCARE & '
              'CAREGIVERS LLC: the founder’s EHBs profile was '
              'created 2026-11-27 and the organization stands '
              'registered from its SAM.gov record — UEI '
              'QW8BRKNCF573 imported from SAM',
     'detail': 'HRSA Electronic Handbooks (EHBs): profile of record '
               'created 2026-11-27 (Roosevelt Sanders, '
               'rooseveltsanders381@gmail.com); SANDERS HOME '
               'HEALTHCARE & CAREGIVERS LLC registered in EHBs on '
               'its Active SAM.gov registration (UEI QW8BRKNCF573). '
               'EHBs associations for Sanders Senior Living LLC and '
               'Sanders Legal Helpers LLC await their SAM.gov '
               'registrations completing (Work In Progress of '
               'record). The register holds no credential',
     'verified_on': '2026-11-27'},
    {'system': 'FEMA_GO',
     'state': 'VERIFIED',
     'basis': 'Her FEMA GO key is HELD: the founder’s FEMA GO '
              'account was created via Login.gov 2026-11-27 and '
              'SANDERS HOME HEALTHCARE & CAREGIVERS LLC stands '
              'auto-attached from its SAM.gov record',
     'detail': 'FEMA GO (go.fema.gov): account of record created '
               '2026-11-27 via Login.gov; the organization attached '
               'automatically from SAM.gov — Active, SAM expiration '
               '11/10/2027; the Team list of record shows Roosevelt '
               'Sanders — Authorized Organization Representative, '
               'All Programs. The register holds no credential',
     'verified_on': '2026-11-27'},
    {'system': 'NSF_RESEARCH_GOV',
     'state': 'VERIFIED',
     'basis': 'Her NSF key is HELD for SANDERS HOME HEALTHCARE & '
              'CAREGIVERS LLC: the founder’s NSF Research.gov '
              'account stands registered and activated (NSF ID '
              '0000AB29V) and his Administrator role for the '
              'organization stands GRANTED and ACTIVE',
     'detail': 'NSF Research.gov (research.gov): account of record '
               'created and activated 2026-11-27 (Roosevelt Sanders, '
               'rooseveltsanders381@gmail.com; NSF ID 0000AB29V). '
               'The organization was found by UEI QW8BRKNCF573 '
               '\u2014 NSF displays SANDERS HOME HEALTHCARE & '
               'CAREGIVERS LLC; it was not previously registered '
               'with NSF, and as the SAM point of contact the founder '
               'was required to obtain the Administrator role through '
               'this process. Organization record: short name '
               '"Sanders Home Healthcare & Caregivers", type Small '
               'Business, time zone America/Denver, phone '
               '414-502-3325, email rooseveltsanders381@gmail.com, no '
               'fax. View My Roles of record: Administrator (Admin) '
               'under Active Role(s) \u2014 the role includes '
               'Sponsored Projects Officer (SPO) and View Only; '
               'granted on submission, no Requested Roles pending; '
               'NSF displays Date Added 11/28/2026 (UTC) for the grant '
               'made the evening of November 27, 2026 MST. Authorized '
               'Organizational Representative is not a separate '
               'selectable role in this flow; further roles may be '
               'requested now that Administrator is held. The '
               'register holds no credential',
     'verified_on': '2026-11-27'},
    {'system': 'AMERICORPS_EGRANTS',
     'state': 'VERIFIED',
     'basis': 'Her AmeriCorps eGrants key is HELD for SANDERS HOME '
              'HEALTHCARE & CAREGIVERS LLC: the organization stands '
              'registered in AmeriCorps eGrants and the founder\u2019s '
              'access stands confirmed \u2014 \u201cThank You \u2014 '
              'You now have access to eGrants\u201d',
     'detail': 'AmeriCorps eGrants (egrants.cns.gov): registration '
               'of record completed 2026-11-27 (username '
               'RooseveltSanders, rooseveltsanders381@gmail.com); '
               'the signed-in homepage of record reads \u201cWelcome '
               'Roosevelt / Welcome to eGrants!\u201d. Organization '
               'profile: legal name SANDERS HOME HEALTHCARE & '
               'CAREGIVERS LLC (SAM-exact), entered under the '
               'organization\u2019s EIN as 9 digits, UEI '
               'QW8BRKNCF573, organization type For Profit '
               'Organization, address 8267 Sedgewick Dr, Colorado '
               'Springs, CO 80925-9418 (portal-validated ZIP+4), '
               'phone 414-502-3325; Rules of Behavior accepted; '
               'Indirect Cost Rate Record \u201cNo\u201d. The portal '
               'issued no account or confirmation number. No grant '
               'application was started. The register holds no '
               'credential',
     'verified_on': '2026-11-27'},
    {'system': 'GRANTSOLUTIONS',
     'state': 'AT_AWARD',
     'basis': 'Provisioned at award or by agency invitation',
     'detail': 'Cannot be created standalone \u2014 AT_AWARD '
               'is its state of record, not a gap',
     'verified_on': '2026-11-26'},
    {'system': 'PMS',
     'state': 'AT_AWARD',
     'basis': 'Provisioned at award (HHS Payment Management '
              'Services)',
     'detail': 'Cannot be created standalone \u2014 AT_AWARD '
               'is its state of record, not a gap',
     'verified_on': '2026-11-26'},
    {'system': 'ASAP',
     'state': 'AT_AWARD',
     'basis': 'Provisioned at award (Automated Standard '
              'Application for Payments)',
     'detail': 'Cannot be created standalone \u2014 AT_AWARD '
               'is its state of record, not a gap',
     'verified_on': '2026-11-26'},
    {'system': 'EU_FUNDING_TENDERS_PORTAL',
     'state': 'VERIFIED',
     'basis': 'Her first global key: the founder\u2019s EU '
              'Login account is held '
              '(rooseveltsanders381@gmail.com) and SANDERS '
              'HOME HEALTHCARE & CAREGIVERS LLC stands '
              'registered in the Participant Register \u2014 '
              'registration completed 2026-11-26; PIC '
              '859635244; the founder is the authorised user '
              'on the registration',
     'detail': 'EU Funding & Tenders Portal, Participant '
               'Register: organisation registration of record '
               'under Colorado Secretary of State registration '
               'number 20251946893; the portal confirmed '
               '\u201cRegistration completed / Registration '
               'submitted successfully\u201d (the founder '
               'submitted himself, 2026-11-26). The EU Login '
               'credential is held by the founder alone and '
               'is never recorded here; Validation Services '
               'may request documents at application time',
     'verified_on': '2026-11-26'},
    {'system': 'UNGM',
     'state': 'VERIFIED',
     'basis': 'Her second global key: the founder\u2019s '
              'UNGM supplier account is held and activated '
              '(rooseveltsanders381@gmail.com) and SANDERS '
              'HOME HEALTHCARE & CAREGIVERS LLC stands '
              'registered \u2014 Basic Registration submitted '
              '2026-11-26; UNGM number 1312370; supplier '
              'profile registered with 25 UN Organizations; '
              'the founder made the Declaration of '
              'Eligibility himself',
     'detail': 'UN Global Marketplace (ungm.org): Basic '
               'Registration of record \u2014 year '
               'established 2025; employees 0 (independent '
               'contractors, owner-operated); scope '
               'International; UNSPSC 85101508, 85101600, '
               '91111600, 91111900; the site confirmed '
               '\u201cCongratulations! The registration at '
               'Basic level has been submitted. Your '
               'supplier profile is registered with 25 '
               'Organizations.\u201d No tax ID or document '
               'upload was requested or supplied; the UNGM '
               'credential is held by the founder alone and '
               'is never recorded here',
     'verified_on': '2026-11-26'},
    {'system': 'UNRWA',
     'state': 'VERIFIED',
     'basis': 'Her UNRWA door stands ACCEPTED: the founder’s UNGM '
              'supplier application for the United Nations Relief '
              'and Works Agency for Palestine Refugees in the Near '
              'East (UNRWA) was accepted 2026-11-27, notified '
              'through the In-Tend e-tendering portal',
     'detail': 'UNRWA e-Tendering via In-Tend, reached through the '
               'UNGM registration of record (UNGM number 1312370): '
               'acceptance of record 2026-11-27 — SANDERS HOME '
               'HEALTHCARE & CAREGIVERS LLC may participate in UNRWA '
               'tender opportunities published under UNGM Tender '
               'Notices; invitations arrive by email. The register '
               'holds no credential',
     'verified_on': '2026-11-27'},
    {'system': 'FAO',
     'state': 'VERIFIED',
     'basis': 'Her FAO door stands REGISTERED: the company details '
              'of SANDERS HOME HEALTHCARE & CAREGIVERS LLC were '
              'registered with the Food and Agriculture '
              'Organization of the United Nations (FAO) electronic '
              'tendering site via In-Tend 2026-11-27',
     'detail': 'FAO electronic tendering via In-Tend, reached '
               'through the UNGM registration of record (UNGM number '
               '1312370): registration of record 2026-11-27 — UNGM '
               'portal tender opportunities for FAO are accessible '
               'to the company. The register holds no credential',
     'verified_on': '2026-11-27'},
    {'system': 'WORLD_BANK_VMP',
     'state': 'SUBMITTED',
     'basis': 'Her third global key: the founder\u2019s '
              'World Bank Vendor Management Portal account '
              'is held (rooseveltsanders381@gmail.com, '
              'signed in via Google \u2014 no credential of '
              'its own was created) and the vendor '
              'application of SANDERS HOME HEALTHCARE & '
              'CAREGIVERS LLC stands SUBMITTED 2026-11-26; '
              'Application Number VMP0016761; submitted, '
              'not yet approved \u2014 the World Bank '
              'reviews; the founder made the '
              'conflict-of-interest attestation and the '
              'submission himself',
     'detail': 'World Bank Vendor Management Portal '
               '(vmp-ext.worldbank.org): vendor application '
               'of record \u2014 establishment date '
               '08/27/2025 (founder-confirmed); categories '
               'MEDICAL: SERVICES and CONTRACT '
               'CONSULTANTS: CONSULTING: FIRMS FOR '
               'OPERATIONAL PROJECTS; company, contact and '
               'questionnaire fully filled and saved before '
               'submission; both WBG conflict questions '
               'answered No; no demographic ownership '
               'categories claimed; no tax ID was requested '
               'or entered at any step; the account is the '
               'founder\u2019s Google sign-in and no '
               'credential is recorded here',
     'verified_on': '2026-11-26'},
)
ACCESS_SYSTEMS = tuple(e['system'] for e in ACCESS_REGISTER_SEED)

# Discovery: the Grants.gov public opportunities API as a
# LABELED, detachable input tool \u2014 a data source, never
# her decision-making (native-only labeling discipline).
DISCOVERY_SOURCE = {
    'name': 'Grants.gov public opportunities API',
    'kind': 'LABELED_DETACHABLE_INPUT_TOOL',
    'role': 'DATA_SOURCE_ONLY_NOT_DECISION_MAKING',
    'search_endpoint': 'https://api.grants.gov/v1/api/search2',
    'detail_endpoint':
        'https://api.grants.gov/v1/api/fetchOpportunity',
    'auto_creates_cases': False,
}
# The NAICS facet set her record currently carries (the set
# carried in her base platform record). The founder's NAICS
# ruling is still open, so the set is labeled exactly that:
# carried, not ruled. The source API exposes CFDA / agency
# facets rather than NAICS parameters, so the carried set is
# recorded as the targeting facet of record on every run; it
# is never represented as an API parameter the source accepts.
DISCOVERY_NAICS_CODES = (
    '541611', '541612', '541613', '541614', '541618', '541690')
DISCOVERY_NAICS_STATUS = 'CARRIED_NOT_RULED'


def _default_discovery_fetch(url, payload):
    """The native discovery transport: one JSON POST via the
    standard library. Raises on any failure; the caller records
    the connection state honestly."""
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def _amount_of_record(value):
    """Parse a source amount to an int of USD, or None when
    the source exposes none."""
    if value is None:
        return None
    try:
        return int(float(str(value).replace(',', '').strip()))
    except (TypeError, ValueError):
        return None


class GrantwriterPlatform:
    """Grantwriter at its recorded maximum level: a platform
    service layer composing the pre-existing Grantwriter data and
    draft modules with a submission workflow, a portfolio view, a
    local grant-compliance evaluation, and the shared ecosystem
    requirements (identity, geofence, access guard, Glass-Box
    receipts, check-in)."""

    def __init__(self, database, base_store, operator_verifier=None,
                 audit=None, approval_checker=None,
                 discovery_fetcher=None):
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
        self._discovery_fetch = discovery_fetcher or \
            _default_discovery_fetch
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'grantwriter', {
            'OPERATOR': {'OPPORTUNITY', 'APPLICATION', 'PORTFOLIO',
                         'COMPLIANCE', 'JURISDICTION'},
            'AUDITOR': {'OPPORTUNITY', 'APPLICATION', 'PORTFOLIO',
                        'COMPLIANCE', 'JURISDICTION'},
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
            db.execute("""CREATE TABLE IF NOT EXISTS jurisdiction_cases (
                case_id TEXT PRIMARY KEY,
                branch TEXT NOT NULL,
                scope_ref TEXT NOT NULL,
                title TEXT NOT NULL,
                funder TEXT,
                external_ref TEXT,
                opportunity_kind TEXT NOT NULL,
                fee_structure TEXT,
                profile_complete INTEGER NOT NULL DEFAULT 1,
                profile_gaps TEXT,
                funder_block TEXT,
                stage TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS jurisdiction_case_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                submission_method TEXT,
                authority_basis TEXT,
                tracking_ref TEXT,
                note TEXT,
                recorded_by TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS jurisdiction_alternative_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                structures_considered TEXT NOT NULL,
                note TEXT,
                recorded_by TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS jurisdiction_role_assignments (
                system TEXT NOT NULL,
                entity TEXT NOT NULL,
                role TEXT NOT NULL,
                holder TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (system, entity, role)
            );""")
            case_columns = [row[1] for row in db.execute(
                "PRAGMA table_info(jurisdiction_cases);").fetchall()]
            if 'partners' not in case_columns:
                db.execute(
                    "ALTER TABLE jurisdiction_cases "
                    "ADD COLUMN partners TEXT;")
            db.execute("""CREATE TABLE IF NOT EXISTS grantwriter_access_register (
                system TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                basis TEXT,
                detail TEXT,
                verified_on TEXT,
                updated_by TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS grantwriter_discovery_runs (
                run_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                keyword TEXT,
                state TEXT NOT NULL,
                hits_returned INTEGER NOT NULL DEFAULT 0,
                records_written INTEGER NOT NULL DEFAULT 0,
                below_floor_filtered INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                recorded_by TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS grantwriter_discovery_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source_opp_id TEXT,
                opp_number TEXT,
                title TEXT,
                agency TEXT,
                open_date TEXT,
                close_date TEXT,
                opp_status TEXT,
                cfda_list TEXT,
                award_ceiling INTEGER,
                estimated_total_funding INTEGER,
                floor_verdict TEXT NOT NULL,
                recorded_at INTEGER NOT NULL
            );""")
            self._seed_jurisdiction(db)
            self._seed_access_register(db)

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


    # -- Complete Service Jurisdiction (amendment machinery) -----------

    def _seed_jurisdiction(self, db):
        """Seed the records of fact the amendment names: the
        JustGrants role assignments for Sanders Home Healthcare
        & Caregivers LLC and the live JustGrants case A-547904
        at its truthful stage. Idempotent: existing records are
        never overwritten (INSERT OR IGNORE / existence check),
        so a later role-assignment change of record survives
        restarts. Also seeds the founder's further Grants.gov
        workspaces of record (dashboard of 2026-11-26) at
        PREPARE, under the same discipline."""
        for system, entity, role, holder in _SEED_ROLE_ASSIGNMENTS:
            db.execute(
                "INSERT OR IGNORE INTO jurisdiction_role_assignments "
                "(system, entity, role, holder, updated_by, updated_at) "
                "VALUES (?, ?, ?, ?, 'FOUNDER_RECORD', 1764028800);",
                (system, entity, role, holder))
        existing = db.execute(
            "SELECT case_id FROM jurisdiction_cases WHERE case_id = ?;",
            (SEEDED_JUSTGRANTS_CASE_ID,)).fetchone()
        if existing is None:
            self._seed_justgrants_case(db)
        self._seed_workspace_cases(db)

    def _seed_justgrants_case(self, db):
        """Insert the seeded JustGrants case A-547904 and
        its stage history (called only when the case is
        absent)."""
        db.execute(
            "INSERT INTO jurisdiction_cases (case_id, branch, "
            "scope_ref, title, funder, external_ref, "
            "opportunity_kind, fee_structure, profile_complete, "
            "profile_gaps, funder_block, stage, created_by, "
            "created_at, updated_by, updated_at) VALUES (?, "
            "'PRIVATE_CORPORATE', ?, ?, ?, ?, 'INDIVIDUAL', NULL, "
            "1, NULL, NULL, 'VERIFY_RECEIPT', 'RooseveltSanders', "
            "1763683200, 'RooseveltSanders', 1764028800);",
            (SEEDED_JUSTGRANTS_CASE_ID,
             'Sanders Home Healthcare & Caregivers LLC',
             'SHHC \u2013 Elder Abuse \u2014 NIJ FY26 Elder Abuse',
             'National Institute of Justice (NIJ)',
             'GRANT14829509'))
        for entry in _SEED_CASE_STAGES:
            db.execute(
                "INSERT INTO jurisdiction_case_stages (case_id, "
                "stage, submission_method, authority_basis, "
                "tracking_ref, note, recorded_by, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (SEEDED_JUSTGRANTS_CASE_ID, entry['stage'],
                 entry.get('submission_method'),
                 entry.get('authority_basis'),
                 entry.get('tracking_ref'), entry.get('note'),
                 entry['recorded_by'], entry['recorded_at']))

    def _seed_workspace_cases(self, db):
        """Seed the founder's further Grants.gov workspaces
        of record at PREPARE. Idempotent, under the same
        discipline as the JustGrants seed: existing
        records are never overwritten, so a later change
        of record survives restarts."""
        for case in _SEED_WORKSPACE_CASES:
            existing = db.execute(
                "SELECT case_id FROM jurisdiction_cases "
                "WHERE case_id = ?;",
                (case['case_id'],)).fetchone()
            if existing is not None:
                continue
            db.execute(
                "INSERT INTO jurisdiction_cases (case_id, "
                "branch, scope_ref, title, funder, "
                "external_ref, opportunity_kind, "
                "fee_structure, profile_complete, "
                "profile_gaps, funder_block, stage, "
                "created_by, created_at, updated_by, "
                "updated_at) VALUES (?, "
                "'PRIVATE_CORPORATE', ?, ?, ?, ?, "
                "'INDIVIDUAL', NULL, 1, NULL, NULL, "
                "'PREPARE', 'RooseveltSanders', ?, "
                "'RooseveltSanders', ?);",
                (case['case_id'], case['scope_ref'],
                 case['title'], case['funder'],
                 case['external_ref'],
                 case['recorded_at'], case['recorded_at']))
            db.execute(
                "INSERT INTO jurisdiction_case_stages "
                "(case_id, stage, submission_method, "
                "authority_basis, tracking_ref, note, "
                "recorded_by, recorded_at) VALUES (?, "
                "'PREPARE', NULL, NULL, NULL, ?, "
                "'GRANTWRITER_RECORD', ?);",
                (case['case_id'], case['note'],
                 case['recorded_at']))

    @staticmethod
    def _jurisdiction_case_view(db, row):
        stages = db.execute(
            "SELECT * FROM jurisdiction_case_stages "
            "WHERE case_id = ? ORDER BY id;", (row['case_id'],)).fetchall()
        checks = db.execute(
            "SELECT COUNT(*) AS n FROM "
            "jurisdiction_alternative_checks WHERE case_id = ?;",
            (row['case_id'],)).fetchone()['n']
        return {
            'case_id': row['case_id'],
            'branch': row['branch'],
            'scope_ref': row['scope_ref'],
            'title': row['title'],
            'funder': row['funder'],
            'external_ref': row['external_ref'],
            'opportunity_kind': row['opportunity_kind'],
            'partners': json.loads(row['partners'])
            if row['partners'] else [],
            'fee_structure': row['fee_structure'],
            'profile_complete': bool(row['profile_complete']),
            'profile_gaps': row['profile_gaps'],
            'funder_block': row['funder_block'],
            'stage': row['stage'],
            'alternative_structures_checks': checks,
            'stage_history': [
                {'stage': s['stage'],
                 'submission_method': s['submission_method'],
                 'authority_basis': s['authority_basis'],
                 'tracking_ref': s['tracking_ref'],
                 'note': s['note'],
                 'recorded_by': s['recorded_by'],
                 'recorded_at': s['recorded_at']}
                for s in stages],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
        }

    def _jurisdiction_case_row(self, db, case_id):
        return db.execute(
            "SELECT * FROM jurisdiction_cases WHERE case_id = ?;",
            (case_id,)).fetchone()

    def _require_case_scope(self, db, case_id, branch, scope_ref):
        """Fetch a case enforcing its branch + scope binding.
        A case answers only inside its own branch and scope:
        cross-branch or cross-scope access is refused by name
        \u2014 the branches never merge identities, scopes,
        client records, or financial accounts."""
        row = self._jurisdiction_case_row(db, case_id)
        if row is None:
            raise GrantwriterPlatformDenied('Unknown jurisdiction case')
        if row['branch'] != branch or row['scope_ref'] != scope_ref:
            raise GrantwriterPlatformForbidden(
                'GRANTWRITER_CROSS_BRANCH_ACCESS_REFUSED: case '
                f"{case_id} belongs to branch {row['branch']} "
                f"scope {row['scope_ref']!r}; access from branch "
                f"{branch} scope {scope_ref!r} is refused \u2014 "
                'the service branches never merge identities, '
                'scopes, client records, or financial accounts')
        return row

    @staticmethod
    def _validate_case_partners(opportunity_kind, partners):
        """The founder's partnership rule (2026-11-26, corrected
        16:31 MST and clarified 16:33 MST): joint and
        collaborative applications are made only among the four
        Sanders companies \u2014 those are the joint partners.
        A named partner outside the four is refused by name.
        Returns the partners of record as a tuple."""
        if partners is None:
            return ()
        if isinstance(partners, str) or \
                not isinstance(partners, (list, tuple)):
            raise GrantwriterPlatformDenied(
                'Partners must be named as a list of entities')
        named = []
        for partner in partners:
            if not isinstance(partner, str) or not partner.strip():
                raise GrantwriterPlatformDenied(
                    'Every partner must be named')
            named.append(partner.strip())
        external = [name for name in named
                    if name not in JURISDICTION_COMPANIES]
        if external:
            raise GrantwriterPlatformForbidden(
                EXTERNAL_PARTNER_REFUSAL + ': joint and '
                'collaborative applications are made only among '
                'the four Sanders companies \u2014 '
                + '; '.join(JURISDICTION_COMPANIES)
                + ' \u2014 the joint partners of record. '
                'External co-applicant refused: '
                + '; '.join(external))
        if opportunity_kind == 'INDIVIDUAL' and named:
            raise GrantwriterPlatformDenied(
                'An INDIVIDUAL case names no partners; a case '
                'with partners of record is JOINT, COLLABORATIVE '
                'or ECOSYSTEM_WIDE')
        return tuple(named)

    @staticmethod
    def _validate_branch_scope(branch, scope_ref):
        if branch not in JURISDICTION_BRANCH_IDS:
            raise GrantwriterPlatformDenied(
                f'Unknown service branch: {branch!r}')
        if not isinstance(scope_ref, str) or not scope_ref.strip():
            raise GrantwriterPlatformDenied(
                'A non-empty record scope is required')
        scope_ref = scope_ref.strip()
        if branch == 'PRIVATE_CORPORATE' and \
                scope_ref not in JURISDICTION_COMPANIES:
            raise GrantwriterPlatformDenied(
                'The PRIVATE_CORPORATE branch serves exactly the '
                'four companies of record: '
                + '; '.join(JURISDICTION_COMPANIES))
        return scope_ref

    def create_jurisdiction_case(self, actor, branch, scope_ref, title,
                                 opportunity_kind='INDIVIDUAL',
                                 funder=None, external_ref=None,
                                 fee_structure=None,
                                 profile_complete=True,
                                 profile_gaps=None, case_id=None,
                                 partners=None):
        """Open a jurisdiction case at PREPARE in one branch and
        one record scope. The standing fee bar is structural: a
        percentage-of-award fee structure is refused by name.
        An incomplete profile records as gaps on the case and
        never blocks it. Receipt
        GRANTWRITER_JURISDICTION_CASE_CREATED."""
        self._check_actor(actor)
        scope_ref = self._validate_branch_scope(branch, scope_ref)
        if opportunity_kind not in OPPORTUNITY_KINDS:
            raise GrantwriterPlatformDenied(
                f'Unknown opportunity kind: {opportunity_kind!r}')
        if not isinstance(title, str) or not title.strip():
            raise GrantwriterPlatformDenied('A case title is required')
        if fee_structure is not None and \
                str(fee_structure).strip().upper() == 'PERCENTAGE_OF_AWARD':
            raise GrantwriterPlatformDenied(
                FEE_BAR['refusal'] + ': ' + FEE_BAR['basis'])
        partners = self._validate_case_partners(
            opportunity_kind, partners)
        if case_id is None:
            case_id = 'GWJ-' + uuid.uuid4().hex[:12].upper()
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                if self._jurisdiction_case_row(db, case_id) is not None:
                    raise GrantwriterPlatformDenied(
                        f'Jurisdiction case already exists: {case_id}')
                db.execute(
                    "INSERT INTO jurisdiction_cases (case_id, branch, "
                    "scope_ref, title, funder, external_ref, "
                    "opportunity_kind, fee_structure, profile_complete, "
                    "profile_gaps, funder_block, stage, created_by, "
                    "created_at, updated_by, updated_at, partners) "
                    "VALUES (?, ?, "
                    "?, ?, ?, ?, ?, ?, ?, ?, NULL, 'PREPARE', ?, ?, "
                    "?, ?, ?);",
                    (case_id, branch, scope_ref, title.strip(), funder,
                     external_ref, opportunity_kind, fee_structure,
                     1 if profile_complete else 0, profile_gaps,
                     actor, now, actor, now,
                     json.dumps(list(partners)) if partners else None))
                db.execute(
                    "INSERT INTO jurisdiction_case_stages (case_id, "
                    "stage, submission_method, authority_basis, "
                    "tracking_ref, note, recorded_by, recorded_at) "
                    "VALUES (?, 'PREPARE', NULL, NULL, NULL, NULL, ?, "
                    "?);", (case_id, actor, now))
                self._record('GRANTWRITER_JURISDICTION_CASE_CREATED',
                             actor=actor, case_id=case_id, branch=branch,
                             scope_ref=scope_ref,
                             opportunity_kind=opportunity_kind)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._jurisdiction_case_view(
                db, self._jurisdiction_case_row(db, case_id))

    def jurisdiction_case(self, actor, role, case_id, branch, scope_ref):
        """One case, read inside its own branch + scope only,
        behind the JURISDICTION access guard."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'JURISDICTION', case_id,
                           purpose='jurisdiction case view')
        with self._connect() as db:
            row = self._require_case_scope(db, case_id, branch, scope_ref)
            return self._jurisdiction_case_view(db, row)

    def advance_jurisdiction_case(self, actor, case_id, branch, scope_ref,
                                  target_stage, note=None,
                                  submission_method=None,
                                  authority_basis=None,
                                  tracking_ref=None):
        """One checked duty-cycle stage transition (operator-only,
        receipt GRANTWRITER_JURISDICTION_STAGE_RECORDED). SUBMIT
        records the submission method and the authority basis it
        stands on \u2014 the standing Founder grant for the
        companies and the ecosystem, the client authorization of
        record for public work. There is no per-case founder
        approval object and none is consulted. VERIFY_RECEIPT
        requires the official tracking reference."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Duty-cycle stage transitions are an operator authority')
        if target_stage == 'DISCARDED':
            raise GrantwriterPlatformDenied(
                'DISCARDED is reached only via '
                'discard_jurisdiction_case, which requires an '
                'alternative-structures check of record')
        if target_stage not in DUTY_CYCLE_STAGES:
            raise GrantwriterPlatformDenied(
                f'Unknown duty-cycle stage: {target_stage!r}')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._require_case_scope(
                    db, case_id, branch, scope_ref)
                current = row['stage']
                if target_stage not in _DUTY_CYCLE_TRANSITIONS[current]:
                    raise GrantwriterPlatformDenied(
                        f'Duty-cycle transition {current}->{target_stage} '
                        'is not permitted')
                if target_stage == 'SUBMIT':
                    if row['funder_block']:
                        raise GrantwriterPlatformDenied(
                            'GRANTWRITER_FUNDER_REQUIREMENT_BLOCKS_'
                            'SUBMISSION: ' + row['funder_block']
                            + ' \u2014 the funder\u2019s own '
                            'mandatory requirement, named as the '
                            'funder\u2019s; not an internal gate')
                    if submission_method not in SUBMISSION_METHODS:
                        raise GrantwriterPlatformDenied(
                            'A submission method is required and must '
                            'be one of: ' + ', '.join(SUBMISSION_METHODS))
                    expected = _BRANCH_AUTHORITY_BASIS[row['branch']]
                    if authority_basis != expected:
                        raise GrantwriterPlatformDenied(
                            'GRANTWRITER_AUTHORITY_BASIS_MISMATCH: '
                            f"branch {row['branch']} submits on "
                            f'{expected}; the standing grant and the '
                            'client authorization of record are the '
                            'only bases \u2014 no per-case founder '
                            'approval exists or is required')
                if target_stage == 'VERIFY_RECEIPT':
                    if not isinstance(tracking_ref, str) or \
                            not tracking_ref.strip():
                        raise GrantwriterPlatformDenied(
                            'VERIFY_RECEIPT requires the official '
                            'tracking number or agency acceptance '
                            'confirmation reference')
                    tracking_ref = tracking_ref.strip()
                now = int(time.time())
                db.execute(
                    "UPDATE jurisdiction_cases SET stage = ?, "
                    "updated_by = ?, updated_at = ? WHERE case_id = ?;",
                    (target_stage, actor, now, case_id))
                db.execute(
                    "INSERT INTO jurisdiction_case_stages (case_id, "
                    "stage, submission_method, authority_basis, "
                    "tracking_ref, note, recorded_by, recorded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    (case_id, target_stage,
                     submission_method if target_stage == 'SUBMIT' else None,
                     authority_basis if target_stage == 'SUBMIT' else None,
                     tracking_ref if target_stage == 'VERIFY_RECEIPT'
                     else None,
                     note, actor, now))
                self._record('GRANTWRITER_JURISDICTION_STAGE_RECORDED',
                             actor=actor, case_id=case_id,
                             from_stage=current, to_stage=target_stage,
                             submission_method=submission_method
                             if target_stage == 'SUBMIT' else None,
                             authority_basis=authority_basis
                             if target_stage == 'SUBMIT' else None,
                             tracking_ref=tracking_ref
                             if target_stage == 'VERIFY_RECEIPT' else None)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._jurisdiction_case_view(
                db, self._jurisdiction_case_row(db, case_id))

    def record_funder_requirement(self, actor, case_id, branch, scope_ref,
                                  requirement, met=False):
        """Record a funder's own mandatory requirement against a
        case (operator-only). An unmet funder requirement is the
        ONLY block on an otherwise eligible submission, and the
        record names it as the funder's. Recording it met clears
        the block. Receipt
        GRANTWRITER_JURISDICTION_FUNDER_REQUIREMENT."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Funder requirement records are an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_case_scope(db, case_id, branch, scope_ref)
                if met:
                    block = None
                else:
                    if not isinstance(requirement, str) or \
                            not requirement.strip():
                        raise GrantwriterPlatformDenied(
                            'An unmet funder requirement must be named')
                    block = requirement.strip()
                now = int(time.time())
                db.execute(
                    "UPDATE jurisdiction_cases SET funder_block = ?, "
                    "updated_by = ?, updated_at = ? WHERE case_id = ?;",
                    (block, actor, now, case_id))
                self._record(
                    'GRANTWRITER_JURISDICTION_FUNDER_REQUIREMENT',
                    actor=actor, case_id=case_id, requirement=requirement,
                    met=bool(met))
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._jurisdiction_case_view(
                db, self._jurisdiction_case_row(db, case_id))

    def record_alternative_structures_check(self, actor, case_id, branch,
                                            scope_ref,
                                            structures_considered,
                                            note=None):
        """Record that alternative eligible funding structures
        were explored for a case (operator-only, receipt
        GRANTWRITER_JURISDICTION_ALTERNATIVES_CHECKED). A case
        may not be discarded without this check of record."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Alternative-structures checks are an operator authority')
        if not isinstance(structures_considered, str) or \
                not structures_considered.strip():
            raise GrantwriterPlatformDenied(
                'The alternative structures considered must be named')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                self._require_case_scope(db, case_id, branch, scope_ref)
                now = int(time.time())
                db.execute(
                    "INSERT INTO jurisdiction_alternative_checks "
                    "(case_id, structures_considered, note, recorded_by, "
                    "recorded_at) VALUES (?, ?, ?, ?, ?);",
                    (case_id, structures_considered.strip(), note,
                     actor, now))
                self._record(
                    'GRANTWRITER_JURISDICTION_ALTERNATIVES_CHECKED',
                    actor=actor, case_id=case_id,
                    structures_considered=structures_considered.strip())
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._jurisdiction_case_view(
                db, self._jurisdiction_case_row(db, case_id))

    def discard_jurisdiction_case(self, actor, case_id, branch, scope_ref,
                                  note=None):
        """Discard a case (operator-only, receipt
        GRANTWRITER_JURISDICTION_CASE_DISCARDED) \u2014 only from
        PREPARE or VALIDATE, and only after an alternative-
        structures check of record: opportunities are never
        discarded prematurely."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Discarding a case is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._require_case_scope(
                    db, case_id, branch, scope_ref)
                if row['stage'] not in ('PREPARE', 'VALIDATE'):
                    raise GrantwriterPlatformDenied(
                        'Only a case at PREPARE or VALIDATE may be '
                        f"discarded, not {row['stage']}")
                checks = db.execute(
                    "SELECT COUNT(*) AS n FROM "
                    "jurisdiction_alternative_checks WHERE case_id = ?;",
                    (case_id,)).fetchone()['n']
                if checks < 1:
                    raise GrantwriterPlatformDenied(
                        'GRANTWRITER_DISCARD_REQUIRES_ALTERNATIVE_'
                        'STRUCTURES_CHECK: an opportunity may not be '
                        'discarded without an alternative-structures '
                        'check of record')
                now = int(time.time())
                db.execute(
                    "UPDATE jurisdiction_cases SET stage = 'DISCARDED', "
                    "updated_by = ?, updated_at = ? WHERE case_id = ?;",
                    (actor, now, case_id))
                db.execute(
                    "INSERT INTO jurisdiction_case_stages (case_id, "
                    "stage, submission_method, authority_basis, "
                    "tracking_ref, note, recorded_by, recorded_at) "
                    "VALUES (?, 'DISCARDED', NULL, NULL, NULL, ?, ?, "
                    "?);", (case_id, note, actor, now))
                self._record('GRANTWRITER_JURISDICTION_CASE_DISCARDED',
                             actor=actor, case_id=case_id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._jurisdiction_case_view(
                db, self._jurisdiction_case_row(db, case_id))

    def record_role_assignment(self, actor, system, entity, role, holder):
        """Record who holds a role for an entity in an external
        system (operator-only, receipt
        GRANTWRITER_ROLE_ASSIGNMENT_RECORDED). Role assignments
        are FACTS OF RECORD \u2014 changeable facts, never a
        system reservation and never a restriction on
        Grantwriter's authority."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Role assignment records are an operator authority')
        if system in _ROLE_SYSTEMS and role not in _ROLE_SYSTEMS[system]:
            raise GrantwriterPlatformDenied(
                f'Unknown {system} role: {role!r} \u2014 the roles '
                'of record are ' + ', '.join(_ROLE_SYSTEMS[system]))
        for value, label in ((entity, 'entity'), (role, 'role'),
                             (holder, 'holder')):
            if not isinstance(value, str) or not value.strip():
                raise GrantwriterPlatformDenied(
                    f'A non-empty {label} is required')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO jurisdiction_role_assignments (system, "
                    "entity, role, holder, updated_by, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(system, "
                    "entity, role) DO UPDATE SET holder = "
                    "excluded.holder, updated_by = excluded.updated_by, "
                    "updated_at = excluded.updated_at;",
                    (system, entity.strip(), role.strip(),
                     holder.strip(), actor, now))
                self._record('GRANTWRITER_ROLE_ASSIGNMENT_RECORDED',
                             actor=actor, system=system,
                             entity=entity.strip(), role=role.strip(),
                             holder=holder.strip())
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'system': system, 'entity': entity.strip(),
                'role': role.strip(), 'holder': holder.strip(),
                'updated_by': actor, 'updated_at': now}

    def role_assignments(self, system=None, entity=None):
        """The role assignments of record, optionally filtered."""
        query = "SELECT * FROM jurisdiction_role_assignments"
        clauses, params = [], []
        if system is not None:
            clauses.append("system = ?")
            params.append(system)
        if entity is not None:
            clauses.append("entity = ?")
            params.append(entity)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY system, entity, role;"
        with self._connect() as db:
            return [
                {'system': r['system'], 'entity': r['entity'],
                 'role': r['role'], 'holder': r['holder'],
                 'updated_by': r['updated_by'],
                 'updated_at': r['updated_at']}
                for r in db.execute(query, params).fetchall()]

    # -- Mother upgrade: targeting, access register, discovery ------

    @staticmethod
    def targeting_view() -> dict:
        """The targeting parameters of record (founder directions
        of 2026-11-26): the $10,000,000 pursuit floor, the
        partnership rule, and the global-by-design key
        principle."""
        view = dict(TARGETING_PARAMETERS)
        view['joint_partners'] = list(TARGETING_PARAMETERS[
            'joint_partners'])
        return view

    def _seed_access_register(self, db):
        """Seed her keys of record, one entry per system, in the
        truthful states verified 2026-11-26. Idempotent: existing
        entries are never overwritten, so a later state of record
        survives restarts. The register holds no credentials."""
        for entry in ACCESS_REGISTER_SEED:
            db.execute(
                "INSERT OR IGNORE INTO grantwriter_access_register "
                "(system, state, basis, detail, verified_on, "
                "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, "
                "'FOUNDER_RECORD', 1764115200);",
                (entry['system'], entry['state'], entry['basis'],
                 entry['detail'], entry['verified_on']))

    @staticmethod
    def _access_entry_view(row):
        return {'system': row['system'], 'state': row['state'],
                'basis': row['basis'], 'detail': row['detail'],
                'verified_on': row['verified_on'],
                'updated_by': row['updated_by'],
                'updated_at': row['updated_at']}

    def access_register(self):
        """Her keys of record, in register order."""
        with self._connect() as db:
            return [self._access_entry_view(r) for r in db.execute(
                "SELECT * FROM grantwriter_access_register "
                "ORDER BY rowid;").fetchall()]

    def record_access_state(self, actor, system, state, basis=None,
                            detail=None, verified_on=None):
        """Record a key's state (operator-only, receipt
        GRANTWRITER_ACCESS_STATE_RECORDED). States are the
        laddered states of record; a new jurisdiction's system
        may be added \u2014 the register is global by design.
        No credential is ever recorded: this surface refuses
        password-shaped input by name."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Access register records are an operator authority')
        if not isinstance(system, str) or not system.strip():
            raise GrantwriterPlatformDenied('A system must be named')
        system = system.strip().upper()
        if state not in ACCESS_STATES:
            raise GrantwriterPlatformDenied(
                f'Unknown access state: {state!r} \u2014 the states '
                'of record are ' + ', '.join(ACCESS_STATES))
        for value in (basis, detail):
            if value is not None and 'password' in str(value).lower():
                raise GrantwriterPlatformDenied(
                    'GRANTWRITER_ACCESS_REGISTER_HOLDS_NO_CREDENTIALS: '
                    'the register records keys as states and bases '
                    'only \u2014 never a password or credential')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO grantwriter_access_register (system, "
                    "state, basis, detail, verified_on, updated_by, "
                    "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(system) DO UPDATE SET state = "
                    "excluded.state, basis = excluded.basis, detail = "
                    "excluded.detail, verified_on = "
                    "excluded.verified_on, updated_by = "
                    "excluded.updated_by, updated_at = "
                    "excluded.updated_at;",
                    (system, state, basis, detail, verified_on,
                     actor, now))
                self._record('GRANTWRITER_ACCESS_STATE_RECORDED',
                             actor=actor, system=system, state=state)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM grantwriter_access_register "
                "WHERE system = ?;", (system,)).fetchone()
            return self._access_entry_view(row)

    def access_register_board(self, actor, role):
        """The access register board, behind the JURISDICTION
        guard: her keys as records under the global-by-design
        principle. Credentials held: none, ever."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'JURISDICTION',
                           'access-register',
                           purpose='grantwriter access register')
        return {
            'principle': TARGETING_PARAMETERS['access_principle'],
            'principle_statement': TARGETING_PARAMETERS[
                'access_principle_statement'],
            'credentials_held': False,
            'passwords_held': False,
            'entries': self.access_register(),
        }

    def _discovery_run_view(self, db, row):
        records = db.execute(
            "SELECT * FROM grantwriter_discovery_records "
            "WHERE run_id = ? ORDER BY id;", (row['run_id'],)).fetchall()
        return {
            'run_id': row['run_id'],
            'source': row['source'],
            'keyword': row['keyword'],
            'state': row['state'],
            'hits_returned': row['hits_returned'],
            'records_written': row['records_written'],
            'below_floor_filtered': row['below_floor_filtered'],
            'error': row['error'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'records': [self._discovery_record_view(r)
                        for r in records],
        }

    @staticmethod
    def _discovery_record_view(row):
        return {
            'source_opp_id': row['source_opp_id'],
            'opp_number': row['opp_number'],
            'title': row['title'],
            'agency': row['agency'],
            'open_date': row['open_date'],
            'close_date': row['close_date'],
            'opp_status': row['opp_status'],
            'cfda_list': json.loads(row['cfda_list'])
            if row['cfda_list'] else [],
            'award_ceiling': row['award_ceiling'],
            'estimated_total_funding':
                row['estimated_total_funding'],
            'floor_verdict': row['floor_verdict'],
            'recorded_at': row['recorded_at'],
        }

    def discovery_connection_state(self):
        """The truthful connection state of the labeled discovery
        source: CONNECTED only when a discovery run has actually
        been answered by the source; NOT_CONNECTED otherwise
        \u2014 never claimed from configuration alone."""
        with self._connect() as db:
            row = db.execute(
                "SELECT state FROM grantwriter_discovery_runs "
                "ORDER BY recorded_at DESC, rowid DESC LIMIT 1;"
            ).fetchone()
        if row is not None and row['state'] == 'CONNECTED':
            return 'CONNECTED'
        return 'NOT_CONNECTED'

    def run_discovery_search(self, actor, keyword=None, rows=25):
        """Run one discovery search against the labeled Grants.gov
        public opportunities API (operator-only, receipt
        GRANTWRITER_DISCOVERY_SEARCH_RECORDED). Results record as
        discovery records under her targeting: where the source
        exposes an amount (estimated total program funding or
        award ceiling), an opportunity below the $10,000,000
        floor is filtered out and counted, never recorded; where
        the source exposes no amount, the record carries
        AMOUNT_NOT_EXPOSED and stands. A discovery record never
        auto-creates a pursuit case. When the source does not
        answer, the run records NOT_CONNECTED with the failure
        named \u2014 no results are fabricated."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise GrantwriterPlatformForbidden(
                'Discovery searches are an operator authority')
        try:
            rows = max(1, min(int(rows), 100))
        except (TypeError, ValueError):
            raise GrantwriterPlatformDenied(
                'rows must be a whole number') from None
        run_id = 'GWD-' + uuid.uuid4().hex[:12].upper()
        now = int(time.time())
        payload = {'oppStatuses': 'posted', 'rows': rows}
        if isinstance(keyword, str) and keyword.strip():
            payload['keyword'] = keyword.strip()
        state = 'CONNECTED'
        error = None
        hits = []
        try:
            response = self._discovery_fetch(
                DISCOVERY_SOURCE['search_endpoint'], payload)
            hits = ((response or {}).get('data') or {}).get(
                'oppHits') or []
        except Exception as exc:  # the source did not answer
            state = 'NOT_CONNECTED'
            error = f'{type(exc).__name__}: {exc}'[:300]
            hits = []
        records = []
        below_floor = 0
        if state == 'CONNECTED':
            for hit in hits:
                ceiling = None
                estimated = None
                opp_id = hit.get('id')
                if opp_id is not None:
                    try:
                        detail = self._discovery_fetch(
                            DISCOVERY_SOURCE['detail_endpoint'],
                            {'oppId': int(opp_id)
                             if str(opp_id).isdigit() else opp_id})
                        synopsis = ((detail or {}).get('data')
                                    or {}).get('synopsis') or {}
                        ceiling = _amount_of_record(
                            synopsis.get('awardCeiling'))
                        estimated = _amount_of_record(
                            synopsis.get(
                                'estimatedTotalProgramFunding'))
                    except Exception:
                        ceiling = None
                        estimated = None
                amounts = [a for a in (estimated, ceiling)
                           if a is not None]
                if not amounts:
                    verdict = 'AMOUNT_NOT_EXPOSED'
                elif max(amounts) >= PURSUIT_FLOOR_USD:
                    verdict = 'MEETS_FLOOR'
                else:
                    verdict = 'BELOW_FLOOR'
                if verdict == 'BELOW_FLOOR':
                    below_floor += 1
                    continue
                records.append({
                    'source_opp_id': str(opp_id)
                    if opp_id is not None else None,
                    'opp_number': hit.get('number'),
                    'title': hit.get('title'),
                    'agency': hit.get('agency'),
                    'open_date': hit.get('openDate'),
                    'close_date': hit.get('closeDate'),
                    'opp_status': hit.get('oppStatus'),
                    'cfda_list': hit.get('cfdaList') or [],
                    'award_ceiling': ceiling,
                    'estimated_total_funding': estimated,
                    'floor_verdict': verdict,
                    'recorded_at': now,
                })
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO grantwriter_discovery_runs (run_id, "
                    "source, keyword, state, hits_returned, "
                    "records_written, below_floor_filtered, error, "
                    "recorded_by, recorded_at) VALUES (?, ?, ?, ?, "
                    "?, ?, ?, ?, ?, ?);",
                    (run_id, DISCOVERY_SOURCE['name'],
                     payload.get('keyword'), state, len(hits),
                     len(records), below_floor, error, actor, now))
                for record in records:
                    db.execute(
                        "INSERT INTO grantwriter_discovery_records "
                        "(run_id, source_opp_id, opp_number, title, "
                        "agency, open_date, close_date, opp_status, "
                        "cfda_list, award_ceiling, "
                        "estimated_total_funding, floor_verdict, "
                        "recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, "
                        "?, ?, ?, ?, ?, ?);",
                        (run_id, record['source_opp_id'],
                         record['opp_number'], record['title'],
                         record['agency'], record['open_date'],
                         record['close_date'], record['opp_status'],
                         json.dumps(record['cfda_list']),
                         record['award_ceiling'],
                         record['estimated_total_funding'],
                         record['floor_verdict'],
                         record['recorded_at']))
                self._record(
                    'GRANTWRITER_DISCOVERY_SEARCH_RECORDED',
                    actor=actor, run_id=run_id, state=state,
                    hits_returned=len(hits),
                    records_written=len(records),
                    below_floor_filtered=below_floor)
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                "SELECT * FROM grantwriter_discovery_runs "
                "WHERE run_id = ?;", (run_id,)).fetchone()
            return self._discovery_run_view(db, row)

    def discovery_board(self, actor, role):
        """The discovery board, behind the JURISDICTION guard:
        the labeled source, its truthful connection state, the
        carried NAICS facet set (CARRIED_NOT_RULED), and every
        discovery run and record of record."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'JURISDICTION', 'discovery',
                           purpose='grantwriter discovery board')
        with self._connect() as db:
            runs = [self._discovery_run_view(db, r) for r in
                    db.execute(
                        "SELECT * FROM grantwriter_discovery_runs "
                        "ORDER BY recorded_at, rowid;").fetchall()]
        return {
            'source': dict(DISCOVERY_SOURCE),
            'connection_state': self.discovery_connection_state(),
            'pursuit_floor_usd': PURSUIT_FLOOR_USD,
            'naics_codes_carried': list(DISCOVERY_NAICS_CODES),
            'naics_status': DISCOVERY_NAICS_STATUS,
            'auto_creates_cases': False,
            'runs': runs,
        }

    @staticmethod
    def jurisdiction_design_view() -> dict:
        """The Complete Service Jurisdiction as adopted
        2026-11-26: an AMENDMENT to her original purpose, which
        stands governing and intact. Her authority is the
        standing grant; her capabilities expand, her
        restrictions do not."""
        return {
            'title': JURISDICTION_TITLE,
            'adopted': JURISDICTION_ADOPTED,
            'amendment': True,
            'amends': JURISDICTION_AMENDS,
            'original_purpose_governing_and_intact': True,
            'amend_never_supersede_ruling': AMEND_NEVER_SUPERSEDE_RULING,
            'amend_never_supersede_ruling_source':
                AMEND_NEVER_SUPERSEDE_RULING_SOURCE,
            'guarded_document': JURISDICTION_GUARDED_DOCUMENT,
            'jurisdiction': 'Global funding acquisition and '
                            'grant management',
            'branches': [dict(entry) for entry in JURISDICTION_BRANCHES],
            'branches_function': 'INDEPENDENT_AND_CONCURRENT',
            'companies': list(JURISDICTION_COMPANIES),
            'duty_cycle': [
                {'stage': stage,
                 'meaning': DUTY_CYCLE_STAGE_MEANINGS[stage]}
                for stage in DUTY_CYCLE_STAGES],
            'submission_methods': list(SUBMISSION_METHODS),
            'authority_bases': list(AUTHORITY_BASES),
            'per_case_founder_authorization_gate': False,
            'opportunity_kinds': list(OPPORTUNITY_KINDS),
            'property_objectives': {
                'objectives': [dict(o) for o in PROPERTY_OBJECTIVES],
                'use_restrictions_added_by_platform': False,
            },
            'fee_bar': dict(FEE_BAR),
            'operating_rules': [dict(r) for r in OPERATING_RULES],
            'justgrants_roles': [
                {'role': role, 'meaning': JUSTGRANTS_ROLE_MEANINGS[role]}
                for role in JUSTGRANTS_ROLES],
            'roles_model': 'FACTS_OF_RECORD_PER_ENTITY',
            'targeting': GrantwriterPlatform.targeting_view(),
            'access_register': {
                'principle': TARGETING_PARAMETERS[
                    'access_principle'],
                'states': list(ACCESS_STATES),
                'systems': list(ACCESS_SYSTEMS),
                'credentials_held': False,
            },
            'discovery': {
                'source': dict(DISCOVERY_SOURCE),
                'naics_codes_carried': list(DISCOVERY_NAICS_CODES),
                'naics_status': DISCOVERY_NAICS_STATUS,
                'connection_state': 'REPORTED_ON_THE_DISCOVERY_'
                                    'BOARD_TRUTHFULLY',
            },
            'external_connections': 'ONE_LABELED_DETACHABLE_'
                                    'INPUT_TOOL: the Grants.gov '
                                    'public opportunities API '
                                    'as a discovery data source '
                                    'only; no submission '
                                    'connection',
            'funds_held': False,
            'funds_disbursed': False,
        }

    def jurisdiction_board(self, actor, role):
        """The jurisdiction board: the design view, case counts
        by branch and duty-cycle stage, the property objectives
        register, the role assignments of record, and the
        seeded JustGrants case \u2014 computed from this
        service's own store, behind the JURISDICTION guard."""
        self._check_actor(actor)
        self._guard_access(actor, role, 'JURISDICTION', 'jurisdiction',
                           purpose='jurisdiction board')
        with self._connect() as db:
            by_branch = {branch: 0 for branch in JURISDICTION_BRANCH_IDS}
            for row in db.execute(
                    "SELECT branch, COUNT(*) AS n FROM "
                    "jurisdiction_cases GROUP BY branch;").fetchall():
                if row['branch'] in by_branch:
                    by_branch[row['branch']] = row['n']
            by_stage = {stage: 0 for stage in
                        DUTY_CYCLE_STAGES + ('DISCARDED',)}
            for row in db.execute(
                    "SELECT stage, COUNT(*) AS n FROM "
                    "jurisdiction_cases GROUP BY stage;").fetchall():
                if row['stage'] in by_stage:
                    by_stage[row['stage']] = row['n']
            seeded_row = self._jurisdiction_case_row(
                db, SEEDED_JUSTGRANTS_CASE_ID)
            seeded = (self._jurisdiction_case_view(db, seeded_row)
                      if seeded_row is not None else None)
        return {
            'platform_id': IDENTITY.platform_id,
            'design': type(self).jurisdiction_design_view(),
            'cases': {'total': sum(by_branch.values()),
                      'by_branch': by_branch,
                      'by_stage': by_stage},
            'role_assignments': self.role_assignments(),
            'seeded_case': seeded,
            'targeting': type(self).targeting_view(),
            'access_register': self.access_register_board(
                actor, role),
            'discovery': self.discovery_board(actor, role),
        }

    def _jurisdiction_status_summary(self):
        with self._connect() as db:
            total = db.execute(
                "SELECT COUNT(*) AS n FROM jurisdiction_cases;"
            ).fetchone()['n']
            seeded = self._jurisdiction_case_row(
                db, SEEDED_JUSTGRANTS_CASE_ID)
            access_entries = db.execute(
                "SELECT COUNT(*) AS n FROM "
                "grantwriter_access_register;").fetchone()['n']
        return {
            'guarded_document': JURISDICTION_GUARDED_DOCUMENT,
            'amendment': True,
            'branches': list(JURISDICTION_BRANCH_IDS),
            'cases_total': total,
            'seeded_case': (
                {'case_id': SEEDED_JUSTGRANTS_CASE_ID,
                 'stage': seeded['stage']} if seeded is not None
                else None),
            'mother_upgrade': {
                'pursuit_floor_usd': PURSUIT_FLOOR_USD,
                'access_register_entries': access_entries,
                'discovery_connection':
                    self.discovery_connection_state(),
            },
        }

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
            'service_jurisdiction': self._jurisdiction_status_summary(),
        }


__all__ = [
    'AUTHORITY_BASES',
    'DESIGNED_LEVEL',
    'DUTY_CYCLE_STAGES',
    'FEE_BAR',
    'IDENTITY',
    'JURISDICTION_BRANCHES',
    'JURISDICTION_COMPANIES',
    'JURISDICTION_GUARDED_DOCUMENT',
    'JURISDICTION_STATEMENT',
    'JUSTGRANTS_ROLES',
    'OPERATING_RULES',
    'OPPORTUNITY_KINDS',
    'ACCESS_REGISTER_SEED',
    'ACCESS_STATES',
    'ACCESS_SYSTEMS',
    'DISCOVERY_NAICS_CODES',
    'DISCOVERY_NAICS_STATUS',
    'DISCOVERY_SOURCE',
    'EXTERNAL_PARTNER_REFUSAL',
    'PURSUIT_FLOOR_USD',
    'TARGETING_PARAMETERS',
    'PROPERTY_OBJECTIVES',
    'SEEDED_JUSTGRANTS_CASE_ID',
    'SEEDED_WORKSPACE_CASE_IDS',
    'SUBMISSION_METHODS',
    'WORKFLOW_STAGES',
    'GrantwriterPlatform',
    'GrantwriterPlatformDenied',
    'GrantwriterPlatformForbidden',
]
