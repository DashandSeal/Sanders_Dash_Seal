"""Service intake spine — Track C (service development) of the
Commercial Ecosystem order, 2026-11-28.

The platforms' service engines exist (record-lifecycle and workflow
machinery, verified in the Track C census of 2026-11-28). What they
have never had is a customer door: a way for a member of the public
to become a client, name the priced service they are buying, and
have a case opened in the platform's own machinery. This module is
that door, built once as a reusable native spine that every priced
platform plugs into:

    public intake (a portal submission, born AWAITING_HUMAN_REVIEW)
      -> the operator's recorded APPROVE decision
      -> a client record (the client as its own record scope, its
         authorization the authority basis of record)
      -> an engagement binding client + chosen service + price of
         record to a case opened in the platform's own machinery.

Native by design: SQLite and the house Glass-Box audit only. No
outside product is any platform's mind, and no outside dependency
stands between a customer and a case.

Catalogs of record live here as data, written from each platform's
ruled price of record — never invented. Grantwriter's GRANT_SERVICES
catalog carries the founder's deliberation ruling of 2026-11-27
(Lane A: Readiness Review $49 one-time, Essential $99/mo; Lane B:
full federal proposal $15,000 flat, retainer $4,950/mo), which
superseded the figures in the 2026-11-26 deployment sheet; the
intake shape follows that sheet's section 3.

The percentage-of-award fee bar is structural at the spine, as it
is inside Grantwriter's own machinery: an engagement whose fee
structure is PERCENTAGE_OF_AWARD is refused by name, and no catalog
may carry one.
"""

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path


class ServiceIntakeDenied(ValueError):
    """An intake or engagement the record refuses on its merits."""


class ServiceIntakeForbidden(ValueError):
    """An action reserved to the operator, attempted by another."""


IDENT_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

FEE_BAR = {
    'refusal': 'SERVICE_INTAKE_PERCENTAGE_OF_AWARD_PRICING_REFUSED',
    'basis': 'Percentage-of-award pricing is barred (Grant '
             'Professionals Association Code of Ethics; AFP '
             'Standards; 2 CFR 200.442). Engagements stand on '
             'flat fees, subscriptions, and retainers of record.',
}

# Each entry: the service a customer can name, its price of record
# (display text and amount), its billing interval, and the fee
# structure recorded on the case the engagement opens.
GRANT_SERVICES = (
    {
        'key': 'READINESS_REVIEW',
        'label': 'Grant Readiness Review',
        'price_text': '$49 one-time',
        'amount_cents': 4900,
        'interval': 'ONE_TIME',
        'fee_structure': 'FLAT_FEE',
    },
    {
        'key': 'ESSENTIAL',
        'label': 'Grantwriter Essential',
        'price_text': '$99/month',
        'amount_cents': 9900,
        'interval': 'MONTH',
        'fee_structure': 'SUBSCRIPTION',
    },
    {
        'key': 'FULL_PROPOSAL',
        'label': 'Full Federal Proposal',
        'price_text': '$15,000 flat',
        'amount_cents': 1500000,
        'interval': 'ONE_TIME',
        'fee_structure': 'FLAT_FEE',
    },
    {
        'key': 'RETAINER',
        'label': 'Grantwriter Retainer',
        'price_text': '$4,950/month',
        'amount_cents': 495000,
        'interval': 'MONTH',
        'fee_structure': 'RETAINER',
    },
)

# Oikos's catalog of record (ruled 2026-11-27): institutions fund
# the necessities of human life across seven continents. Her
# served populations are never her payers — that principle is
# written into her structure, and the intake rule below enforces
# its shape: an Oikos client of record is an institution.
OIKOS_SERVICES = (
    {
        'key': 'CONTINENTAL_PROGRAM',
        'label': 'Continental Program',
        'price_text': 'from $250,000/year per continent program',
        'amount_cents': 25000000,
        'interval': 'YEAR',
        'fee_structure': 'PROGRAM_FEE',
    },
    {
        'key': 'GLOBAL_HUMANITY_PARTNERSHIP',
        'label': 'Global Humanity Partnership',
        'price_text': 'from $1,000,000/year',
        'amount_cents': 100000000,
        'interval': 'YEAR',
        'fee_structure': 'PARTNERSHIP_FEE',
    },
)

CATALOGS = {
    'grantwriter': GRANT_SERVICES,
    'oikos': OIKOS_SERVICES,
}

# Portal submission kinds that are commercial service intakes, and
# the platform each one engages. The portals machinery owns the
# submission and its review; the spine owns what approval opens.
KIND_PLATFORM = {
    'GRANT_SERVICES': 'grantwriter',
    'OIKOS_PROGRAMS': 'oikos',
}


def _oikos_intake_rule(fields):
    """Oikos's structural rule, enforced at intake: her clients
    of record are institutions — the populations she serves are
    never her payers."""
    if str(fields.get('client_kind', '')).strip().upper() != 'INSTITUTION':
        raise ServiceIntakeDenied(
            'OIKOS_PAYER_MUST_BE_AN_INSTITUTION: Oikos is funded '
            'by institutions; her served populations are never '
            'her payers.')


# Per-platform intake rules, checked on the submitted fields
# before a client record opens.
INTAKE_RULES = {
    'oikos': _oikos_intake_rule,
}


def _text(value, field, limit, *, required=True, minimum=1):
    if not isinstance(value, str):
        raise ServiceIntakeDenied('%s must be text.' % field)
    value = value.strip()
    if required and len(value) < minimum:
        raise ServiceIntakeDenied('%s is required.' % field)
    if len(value) > limit:
        raise ServiceIntakeDenied('%s is too long.' % field)
    return value


def catalog_for(platform_id):
    """The platform's service catalog of record (a copy)."""
    entries = CATALOGS.get(platform_id)
    if entries is None:
        raise ServiceIntakeDenied(
            'No service catalog of record for platform: %r'
            % (platform_id,))
    return [dict(entry) for entry in entries]


def service_for(platform_id, service_key):
    """One catalog entry by key, or a refusal naming the fact."""
    for entry in catalog_for(platform_id):
        if entry['key'] == service_key:
            return entry
    raise ServiceIntakeDenied(
        'No service of record %r for platform %r'
        % (service_key, platform_id))


class ServiceIntake:
    """Client records and engagements binding customers to cases.

    An opener is a callable (actor, client, service) -> case ref
    that opens the engagement's case in one platform's own
    machinery. A platform with no registered opener still takes
    engagements: they stand RECORDED in the spine, worked by the
    operator, until the platform's opener is plugged in.
    """

    def __init__(self, db_path, audit, operator_verifier=None,
                 openers=None, clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise ServiceIntakeDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self.operator_verifier = operator_verifier
        self.openers = dict(openers or {})
        self.clock = clock
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS intake_clients (
                client_ref TEXT PRIMARY KEY,
                platform_id TEXT NOT NULL,
                organization TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                authorization_basis TEXT NOT NULL,
                portal_ref TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                receipt_hash TEXT NOT NULL DEFAULT ''
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS intake_engagements (
                engagement_ref TEXT PRIMARY KEY,
                client_ref TEXT NOT NULL,
                platform_id TEXT NOT NULL,
                service_key TEXT NOT NULL,
                service_label TEXT NOT NULL,
                price_text TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                interval TEXT NOT NULL,
                fee_structure TEXT NOT NULL,
                seeking TEXT NOT NULL DEFAULT '',
                platform_case_ref TEXT NOT NULL DEFAULT '',
                portal_ref TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                receipt_hash TEXT NOT NULL DEFAULT ''
            );""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                idx_intake_engagements_portal_ref
                ON intake_engagements (portal_ref)
                WHERE portal_ref != '';""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                idx_intake_clients_portal_ref
                ON intake_clients (platform_id, portal_ref)
                WHERE portal_ref != '';""")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _receipt(self, event, **context):
        return self.audit.preserve(event, **context) or ''

    def _require_operator(self, actor):
        if self.operator_verifier is None:
            return
        if not isinstance(actor, str) or not IDENT_RE.fullmatch(actor):
            raise ServiceIntakeForbidden('Operator sign-in required.')
        try:
            verified = self.operator_verifier(actor) is True
        except Exception:
            verified = False
        if not verified:
            raise ServiceIntakeForbidden('Operator authority required.')

    def register_opener(self, platform_id, opener):
        if not callable(opener):
            raise ServiceIntakeDenied('An opener must be callable.')
        self.openers[platform_id] = opener

    # -- clients ---------------------------------------------------

    def open_client(self, actor, platform_id, *, organization,
                    contact_name, contact,
                    authorization_basis='CLIENT_AUTHORIZATION',
                    portal_ref=''):
        """Open a client record: the client as its own record
        scope, its authorization the authority basis of record.
        Idempotent on (platform_id, portal_ref): re-approving the
        same intake never opens a second client."""
        self._require_operator(actor)
        catalog_for(platform_id)  # refuses a platform with no catalog
        organization = _text(organization, 'organization', 200)
        contact_name = _text(contact_name, 'contact_name', 200)
        contact = _text(contact, 'contact', 200)
        authorization_basis = _text(
            authorization_basis, 'authorization_basis', 100)
        portal_ref = _text(portal_ref, 'portal_ref', 200,
                            required=False, minimum=0)
        with self._connect() as db:
            if portal_ref:
                row = db.execute(
                    "SELECT * FROM intake_clients WHERE platform_id = ?"
                    " AND portal_ref = ?;",
                    (platform_id, portal_ref)).fetchone()
                if row is not None:
                    return dict(row)
            client_ref = 'CLI-' + uuid.uuid4().hex[:12].upper()
            now = int(self.clock())
            receipt = self._receipt(
                'service_intake.client_opened', actor=actor,
                client_ref=client_ref, platform_id=platform_id,
                organization=organization, portal_ref=portal_ref)
            db.execute(
                "INSERT INTO intake_clients (client_ref, platform_id,"
                " organization, contact_name, contact,"
                " authorization_basis, portal_ref, created_by,"
                " created_at, receipt_hash) VALUES (?, ?, ?, ?, ?,"
                " ?, ?, ?, ?, ?);",
                (client_ref, platform_id, organization, contact_name,
                 contact, authorization_basis, portal_ref, actor, now,
                 receipt))
            return dict(db.execute(
                "SELECT * FROM intake_clients WHERE client_ref = ?;",
                (client_ref,)).fetchone())

    def client_view(self, client_ref):
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM intake_clients WHERE client_ref = ?;",
                (client_ref,)).fetchone()
        if row is None:
            raise ServiceIntakeDenied(
                'No client of record: %r' % (client_ref,))
        return dict(row)

    # -- engagements -------------------------------------------------

    def engage(self, actor, client_ref, service_key, *,
               seeking='', portal_ref=''):
        """Bind a client to one service of record. When the
        platform's opener is registered, the engagement's case is
        opened in the platform's own machinery and the engagement
        stands OPEN with the case ref; otherwise it stands
        RECORDED in the spine. Idempotent on portal_ref."""
        self._require_operator(actor)
        seeking = _text(seeking, 'seeking', 2000,
                        required=False, minimum=0)
        portal_ref = _text(portal_ref, 'portal_ref', 200,
                           required=False, minimum=0)
        with self._connect() as db:
            if portal_ref:
                row = db.execute(
                    "SELECT * FROM intake_engagements"
                    " WHERE portal_ref = ?;", (portal_ref,)).fetchone()
                if row is not None:
                    return dict(row)
        client = self.client_view(client_ref)
        platform_id = client['platform_id']
        service = service_for(platform_id, service_key)
        if str(service['fee_structure']).strip().upper() == \
                'PERCENTAGE_OF_AWARD':
            raise ServiceIntakeDenied(
                FEE_BAR['refusal'] + ': ' + FEE_BAR['basis'])
        case_ref = ''
        status = 'RECORDED'
        opener = self.openers.get(platform_id)
        if opener is not None:
            case_ref = opener(actor, client, service) or ''
            status = 'OPEN'
        engagement_ref = 'ENG-' + uuid.uuid4().hex[:12].upper()
        now = int(self.clock())
        receipt = self._receipt(
            'service_intake.engagement_opened', actor=actor,
            engagement_ref=engagement_ref, client_ref=client_ref,
            platform_id=platform_id, service_key=service_key,
            platform_case_ref=case_ref, portal_ref=portal_ref)
        with self._connect() as db:
            db.execute(
                "INSERT INTO intake_engagements (engagement_ref,"
                " client_ref, platform_id, service_key, service_label,"
                " price_text, amount_cents, interval, fee_structure,"
                " seeking, platform_case_ref, portal_ref, status,"
                " created_by, created_at, receipt_hash) VALUES"
                " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (engagement_ref, client_ref, platform_id, service_key,
                 service['label'], service['price_text'],
                 service['amount_cents'], service['interval'],
                 service['fee_structure'], seeking, case_ref,
                 portal_ref, status, actor, now, receipt))
            return dict(db.execute(
                "SELECT * FROM intake_engagements"
                " WHERE engagement_ref = ?;",
                (engagement_ref,)).fetchone())

    def engagements_for(self, client_ref):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM intake_engagements WHERE client_ref = ?"
                " ORDER BY created_at ASC;", (client_ref,)).fetchall()
        return [dict(row) for row in rows]

    # -- the portal bridge -------------------------------------------

    def handle_portal_approval(self, actor, case):
        """What an operator's APPROVE opens, for a commercial
        service intake case from the portals machinery: the client
        record and the engagement, exactly once per portal case.
        The case body carries the intake fields as JSON:
        organization, contact_name, contact, seeking, service_key
        (the subject may name the service key instead)."""
        if not isinstance(case, dict):
            raise ServiceIntakeDenied('A portal case record is required.')
        kind = case.get('kind', '')
        platform_id = KIND_PLATFORM.get(kind)
        if platform_id is None:
            raise ServiceIntakeDenied(
                'Not a service intake kind: %r' % (kind,))
        fields = {}
        body = case.get('body') or ''
        if isinstance(body, str) and body.strip().startswith('{'):
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                fields = parsed
        rule = INTAKE_RULES.get(platform_id)
        if rule is not None:
            rule(fields)
        service_key = fields.get('service_key') or case.get('subject', '')
        service_key = str(service_key).strip().upper()
        service_for(platform_id, service_key)  # refuses an unnamed service
        client = self.open_client(
            actor, platform_id,
            organization=fields.get('organization')
            or case.get('submitter_name', ''),
            contact_name=fields.get('contact_name')
            or case.get('submitter_name', ''),
            contact=fields.get('contact')
            or case.get('submitter_contact', ''),
            portal_ref=case.get('ref', ''))
        return self.engage(
            actor, client['client_ref'], service_key,
            seeking=fields.get('seeking', ''),
            portal_ref=case.get('ref', ''))

    # -- status -------------------------------------------------------

    def status(self):
        with self._connect() as db:
            clients = db.execute(
                "SELECT COUNT(*) AS n FROM intake_clients;").fetchone()['n']
            engagements = db.execute(
                "SELECT status, COUNT(*) AS n FROM intake_engagements"
                " GROUP BY status;").fetchall()
        return {
            'clients': clients,
            'engagements_by_status': {
                row['status']: row['n'] for row in engagements},
            'catalogs': {pid: len(entries)
                         for pid, entries in CATALOGS.items()},
        }


def grantwriter_opener(grantwriter):
    """The Grantwriter plug: an engagement opens her jurisdiction
    case under PUBLIC_COMMERCIAL in the client's own record scope,
    born at PREPARE, on the client authorization of record, with
    the catalog's fee structure of record on the case."""
    def opener(actor, client, service):
        view = grantwriter.create_jurisdiction_case(
            actor, 'PUBLIC_COMMERCIAL', client['client_ref'],
            '%s: %s' % (service['label'], client['organization']),
            fee_structure=service['fee_structure'])
        return view['case_id']
    return opener
