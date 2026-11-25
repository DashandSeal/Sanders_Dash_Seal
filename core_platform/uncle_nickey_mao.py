"""
Module: core_platform.uncle_nickey_mao
Architectural Layer: Uncle Nickey / Mao — integrated RTSA bridge
across six healthcare service lines (one of the Three Originals).

RECOVERED vs REBUILT — the discipline of this module is absolute:
a rebuilt component is never described as recovered or original.

RECOVERED (the only recovered material used here — two record
artifacts from another platform's files in the main repo,
``rtsa_police_men/status.json`` and ``rtsa_police_men/index.html``):

* ``status.json`` records ``"guardian_nodes": ["Uncle Nickey / Mao"]``
  in the Police Men RTSA's topology record.
* ``index.html`` renders the dashboard line
  ``GUARDIAN RELAY: UNCLE NICKEY / MAO [SYNCED]``.

That recovered record is preserved verbatim in substance as
``GUARDIAN_RECORD`` below. In the recovered material nothing
executes behind this record; what the node guards, what the relay
relays, and what [SYNCED] syncs are stated nowhere in the examined
sources.

REBUILT (everything executable in this module): the platform
identity, the six-industry registry, the referral workflow, the
geofence gate, the record-access guard wiring, the check-in, and
the status surfaces are REBUILT from the founder-provided
specification of 2026-11-24 (the owner's record of the six bridged
healthcare service lines, Census-verified that morning; the
original record for 423450 and 492110 is pending on the owner's own
statement). The INDUSTRY_REGISTRY below is therefore a REBUILT
registry from founder-provided specification — the six lines are
the OWNER'S RECORD (2026-11-24, Census-verified), not recovered
code or recovered data structures.

NOT CLAIMED: no original bridge code was recovered, and none is
claimed here. The Guardian Watchdog code in the DeployPad repo is a
separate platform's material and is NOT used in this module
(identity protocols: named platforms are never merged or relabeled
into one another).

The bridge routes REFERENCES between industries. A referral's
``subject_ref`` is an OPAQUE REFERENCE ONLY: the bridge stores no
health records and no PHI — no clinical content, no patient data,
nothing but the reference string, the two industry codes, the
declared jurisdiction, and the referral's workflow state.

THE HOME HEALTHCARE CONNECTION (owner-approved 2026-11-24):
this bridge interoperates BY REFERENCE ONLY with its sibling
platform, Sanders Home Healthcare & Caregivers — the platforms
remain two platforms (separate identities, separate stores,
separate receipts; connection is not merger). When the Home
Healthcare platform is bound (see ``bind_home_healthcare``), the
bridge can: open a referral against a Home Healthcare person
identifier (the opaque ``person-…`` token as ``subject_ref`` —
never personal or health data), having first read the
identifier's activation state through Home Healthcare's own
service surface; serve every referral held for one subject
reference (the surface the Home Healthcare person page reads);
and read a person's six-workflow activation state so the
referral lifecycle works against live activations. Every
cross-platform event is receipted on BOTH sides or fails
closed: Home Healthcare receipts its state reads on its own
chain, this bridge receipts its side on its own chain, and a
failure on either side refuses the operation. Unbound, the
person-referral and activation-state surfaces refuse; the
bridge's own referral workflow is unaffected.

Fail-closed throughout, on the platform's established disciplines
(mirroring core_platform.rooms):

* a Glass-Box audit adapter is required at construction — no
  record, no action;
* every mutation runs under ``BEGIN IMMEDIATE`` with the referral
  row re-read and the operation re-validated inside the lock, so
  duplicate transitions serialize exactly once;
* every mutation writes its Glass-Box receipt inside the critical
  section, before the transaction commits: if the receipt write
  raises, the transaction rolls back and nothing changes;
* operator-only operations go through ``operator_verifier``; an
  absent verifier means operator operations are denied.
"""

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


class BridgeDenied(ValueError):
    """The requested bridge operation is invalid or not permitted."""


class BridgeForbidden(ValueError):
    """The actor lacks authority for this bridge operation."""


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='uncle_nickey_mao',
    name='Uncle Nickey / Mao',
    legal_entities=(
        'Sanders Home Healthcare & Caregivers LLC',
        'Sanders Senior Living LLC',
    ),
    naics_codes=('621610', '624120', '485991', '532283', '423450', '492110'),
    authorized_regions=('US-CO', 'US-WI'),
    status='RECONSTRUCTED',
))

# REBUILT registry from founder-provided specification. Provenance:
# the six lines are the OWNER'S RECORD (2026-11-24, Census-verified);
# the original record for 423450/492110 is pending.
INDUSTRY_REGISTRY = [
    {'naics': '621610',
     'title': 'Home Health Care Services',
     'service_line': 'home healthcare'},
    {'naics': '624120',
     'title': 'Services for the Elderly and Persons with Disabilities',
     'service_line': 'personal care services'},
    {'naics': '485991',
     'title': 'Special Needs Transportation',
     'service_line': 'non-emergency medical transportation'},
    {'naics': '532283',
     'title': 'Home Health Equipment Rental',
     'service_line': 'durable medical equipment rental'},
    {'naics': '423450',
     'title': 'Medical, Dental, and Hospital Equipment and Supplies '
              'Merchant Wholesalers',
     'service_line': 'medical supplies distribution'},
    {'naics': '492110',
     'codes': ('492110', '492210'),
     'title': 'Couriers and Express Delivery Services',
     'service_line': 'healthcare courier services',
     'note': '492210 applies when operations are strictly local.'},
]


def _industry_codes(entry):
    codes = entry.get('codes')
    if codes:
        return tuple(codes)
    return (entry['naics'],)


VALID_INDUSTRY_CODES = frozenset(
    code for entry in INDUSTRY_REGISTRY for code in _industry_codes(entry))

# RECOVERED record only — verbatim substance from the recovery
# dossier (~/workspace/reconciliation-143/uncle-nickey-mao-recovery.md),
# sourced from the two Police Men artifacts named in 'source'.
GUARDIAN_RECORD = {
    'source': 'rtsa_police_men/status.json and rtsa_police_men/index.html, '
              'main repo',
    'guardian_nodes': ['Uncle Nickey / Mao'],
    'dashboard_marker': 'GUARDIAN RELAY: UNCLE NICKEY / MAO [SYNCED]',
    'note': 'RECOVERED record only — in the recovered material nothing '
            'executes behind this record; what the node guards, what the '
            'relay relays, and what [SYNCED] syncs are stated nowhere in '
            'the examined sources.',
}

REFERRAL_STATUSES = ('OPEN', 'ROUTED', 'ACCEPTED', 'COMPLETED', 'CANCELLED')

# Checked referral lifecycle. COMPLETED and CANCELLED are terminal.
_TRANSITIONS = {
    'OPEN': frozenset(('ROUTED', 'CANCELLED')),
    'ROUTED': frozenset(('ACCEPTED', 'CANCELLED')),
    'ACCEPTED': frozenset(('COMPLETED',)),
    'COMPLETED': frozenset(),
    'CANCELLED': frozenset(),
}


class UncleNickeyMaoBridge:
    """The REBUILT Uncle Nickey / Mao bridge service: a referral
    workflow routing opaque references between the six bridged
    healthcare industries, behind a jurisdiction geofence, a
    HIPAA-by-design record-access guard, and Glass-Box receipts for
    every mutation and every granted record access."""

    def __init__(self, database, operator_verifier=None, audit=None,
                 home_healthcare=None):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise BridgeDenied(
                'A Glass-Box audit adapter is required: '
                'no record, no action')
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self.audit = audit
        self.home_healthcare = home_healthcare
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'uncle_nickey_mao', {
            'OPERATOR': {'REFERRAL', 'STATUS'},
            'COORDINATOR': {'REFERRAL'},
            'AUDITOR': {'REFERRAL', 'STATUS'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS bridge_referrals (
                referral_id TEXT PRIMARY KEY,
                from_industry TEXT NOT NULL,
                to_industry TEXT NOT NULL,
                subject_ref TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
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
            raise BridgeDenied('Invalid actor identity')

    def _record(self, stage, **fields):
        self.audit.preserve(stage, **fields)

    @staticmethod
    def _referral_view(row):
        return {
            'referral_id': row['referral_id'],
            'from_industry': row['from_industry'],
            'to_industry': row['to_industry'],
            'subject_ref': row['subject_ref'],
            'jurisdiction': row['jurisdiction'],
            'status': row['status'],
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    def _referral_row(self, db, referral_id):
        return db.execute(
            "SELECT * FROM bridge_referrals WHERE referral_id = ?;",
            (referral_id,)).fetchone()

    def _counts(self, db):
        counts = {status: 0 for status in REFERRAL_STATUSES}
        for row in db.execute(
                "SELECT status, COUNT(*) AS n FROM bridge_referrals "
                "GROUP BY status;").fetchall():
            if row['status'] in counts:
                counts[row['status']] = row['n']
        return counts

    # -- referrals -----------------------------------------------------

    def create_referral(self, actor, from_industry, to_industry,
                        subject_ref, jurisdiction):
        """Create a referral in OPEN, routing an opaque subject
        reference from one bridged industry to another.

        ``subject_ref`` is an OPAQUE REFERENCE ONLY — the bridge
        routes references between industries and stores no health
        records and no PHI.

        Geofence (over the declared jurisdiction): 'ALLOW' admits
        any actor; 'STEP_UP' is operator-only; 'DENY' refuses.
        """
        self._check_actor(actor)
        if from_industry not in VALID_INDUSTRY_CODES:
            raise BridgeDenied(
                f'Unknown from_industry: {from_industry!r}')
        if to_industry not in VALID_INDUSTRY_CODES:
            raise BridgeDenied(f'Unknown to_industry: {to_industry!r}')
        if from_industry == to_industry:
            raise BridgeDenied(
                'from_industry and to_industry must be different')
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise BridgeDenied('A non-empty subject_ref is required')
        verdict = self.geofence.evaluate(jurisdiction)
        if verdict == 'DENY':
            raise BridgeDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        if verdict == 'STEP_UP' and not self._is_operator(actor):
            raise BridgeForbidden(
                'Jurisdiction requires operator step-up verification')
        referral_id = 'ref-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO bridge_referrals (referral_id, "
                    "from_industry, to_industry, subject_ref, "
                    "jurisdiction, status, created_by, created_at, "
                    "updated_at) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?);",
                    (referral_id, from_industry, to_industry, subject_ref,
                     jurisdiction, actor, now, now))
                self._record('UNCLE_NICKEY_REFERRAL_CREATED',
                             referral_id=referral_id, actor=actor,
                             from_industry=from_industry,
                             to_industry=to_industry,
                             jurisdiction=jurisdiction)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._referral_view(
                self._referral_row(db, referral_id))

    def transition_referral(self, actor, referral_id, target):
        """One checked lifecycle transition:
        OPEN->ROUTED, ROUTED->ACCEPTED, ACCEPTED->COMPLETED,
        OPEN|ROUTED->CANCELLED. ROUTED/ACCEPTED/COMPLETED are
        operator-or-creator; CANCELLED is operator-only. The row is
        re-read and the transition re-validated inside the lock, so
        a duplicate transition is refused exactly once serialized.
        """
        self._check_actor(actor)
        if target not in REFERRAL_STATUSES:
            raise BridgeDenied(f'Unknown target status: {target!r}')
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                row = self._referral_row(db, referral_id)
                if row is None:
                    raise BridgeDenied('Unknown referral')
                current = row['status']
                if target not in _TRANSITIONS[current]:
                    raise BridgeDenied(
                        f'Transition {current}->{target} is not permitted')
                if target == 'CANCELLED':
                    if not self._is_operator(actor):
                        raise BridgeForbidden(
                            'Cancellation is an operator authority')
                elif (not self._is_operator(actor)
                        and row['created_by'] != actor):
                    raise BridgeForbidden(
                        'Operator or referral creator authority required')
                db.execute(
                    "UPDATE bridge_referrals SET status = ?, "
                    "updated_at = ? WHERE referral_id = ?;",
                    (target, now, referral_id))
                self._record('UNCLE_NICKEY_REFERRAL_TRANSITION',
                             referral_id=referral_id, actor=actor,
                             from_status=current, to_status=target)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._referral_view(
                self._referral_row(db, referral_id))

    def referral_view(self, actor, role, referral_id):
        """Serve one referral under the HIPAA-by-design access
        guard: access is authorized and receipted FIRST, and only
        then is the record fetched and served."""
        self._check_actor(actor)
        # HIPAA posture: authorize + receipt BEFORE the fetch. An
        # unknown id is therefore still receipted as an access
        # attempt (the access receipt names the ref) — the audit
        # record of who asked for what exists whether or not the
        # record does.
        try:
            self.guard.access(actor, role, 'REFERRAL', referral_id,
                              purpose='referral view')
        except FoundationForbidden as exc:
            raise BridgeForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise BridgeDenied(str(exc)) from exc
        with self._connect() as db:
            row = self._referral_row(db, referral_id)
            if row is None:
                raise BridgeDenied('Unknown referral')
            return self._referral_view(row)

    # -- the Home Healthcare connection (by reference only) -----------

    def bind_home_healthcare(self, home_healthcare):
        """Bind the sibling Home Healthcare platform's service
        surface for by-reference interoperation. The peer is
        duck-typed: it must expose ``activation_state``. Binding
        wires no shared store and merges nothing — each platform
        keeps its own database and its own receipts."""
        if home_healthcare is None or not callable(
                getattr(home_healthcare, 'activation_state', None)):
            raise BridgeDenied(
                'A home healthcare surface exposing activation_state '
                'is required to bind')
        self.home_healthcare = home_healthcare

    def _home_healthcare_peer(self):
        peer = self.home_healthcare
        if peer is None:
            raise BridgeDenied(
                'Home Healthcare platform is not bound to this bridge')
        return peer

    def _read_activation_state(self, person_ref, actor):
        """Read a person's activation state through Home
        Healthcare's own service surface. Home Healthcare receipts
        the read on its own chain; any refusal or failure there
        fails this read closed."""
        peer = self._home_healthcare_peer()
        try:
            return peer.activation_state(
                person_ref, reader_platform='uncle_nickey_mao',
                reader_actor=actor)
        except Exception as exc:
            raise BridgeDenied(
                'Home Healthcare did not answer the activation-state '
                f'read: {exc}') from exc

    def create_person_referral(self, actor, person_ref, from_industry,
                               to_industry, jurisdiction):
        """Open a referral against a Home Healthcare person
        identifier: the referral's ``subject_ref`` is the person's
        opaque ``person-…`` token — a reference only; neither
        platform stores personal or health data for it.

        Before anything is written here, the identifier's
        activation state is read through Home Healthcare's own
        surface (receipted on Home Healthcare's chain): the
        identifier must exist, stand ACTIVE, and have its
        industries activated, with both the from- and to-industry
        workflows ONLINE or ENGAGED — the referral lifecycle works
        against live activations or not at all. The referral is
        then created under this bridge's own disciplines (the
        anchored industry codes; the geofence: 'ALLOW' admits any
        actor, 'STEP_UP' is operator-only, 'DENY' refuses), with
        both receipts inside the transaction."""
        self._check_actor(actor)
        if not isinstance(person_ref, str) or not person_ref.strip():
            raise BridgeDenied('A non-empty person_ref is required')
        if from_industry not in VALID_INDUSTRY_CODES:
            raise BridgeDenied(
                f'Unknown from_industry: {from_industry!r}')
        if to_industry not in VALID_INDUSTRY_CODES:
            raise BridgeDenied(f'Unknown to_industry: {to_industry!r}')
        if from_industry == to_industry:
            raise BridgeDenied(
                'from_industry and to_industry must be different')
        state = self._read_activation_state(person_ref, actor)
        if state['identifier_status'] != 'ACTIVE':
            raise BridgeDenied(
                'Person referrals require an ACTIVE identifier; this '
                f"identifier is {state['identifier_status']}")
        if state['activation'] is None:
            raise BridgeDenied(
                'Person referrals require activated industries; this '
                'identifier has no activation yet')
        workflow_states = {w['naics']: w['state']
                           for w in state['workflows']}
        for code in (from_industry, to_industry):
            # The courier workflow also stands under its
            # strictly-local declaration 492210.
            key = '492110' if code == '492210' else code
            if workflow_states.get(key) not in ('ONLINE', 'ENGAGED'):
                raise BridgeDenied(
                    f'Industry workflow {code} is not online for this '
                    'identifier')
        verdict = self.geofence.evaluate(jurisdiction)
        if verdict == 'DENY':
            raise BridgeDenied(
                f'Jurisdiction denied: {jurisdiction!r}')
        if verdict == 'STEP_UP' and not self._is_operator(actor):
            raise BridgeForbidden(
                'Jurisdiction requires operator step-up verification')
        referral_id = 'ref-' + secrets.token_urlsafe(12)
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                db.execute(
                    "INSERT INTO bridge_referrals (referral_id, "
                    "from_industry, to_industry, subject_ref, "
                    "jurisdiction, status, created_by, created_at, "
                    "updated_at) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?);",
                    (referral_id, from_industry, to_industry, person_ref,
                     jurisdiction, actor, now, now))
                self._record('UNCLE_NICKEY_REFERRAL_CREATED',
                             referral_id=referral_id, actor=actor,
                             from_industry=from_industry,
                             to_industry=to_industry,
                             jurisdiction=jurisdiction)
                self._record('UNCLE_NICKEY_PERSON_REFERRAL_CREATED',
                             referral_id=referral_id, actor=actor,
                             person_ref=person_ref,
                             activation_appointment_id=(
                                 state['activation']['appointment_id']))
                db.commit()
            except Exception:
                db.rollback()
                raise
            return self._referral_view(
                self._referral_row(db, referral_id))

    def referrals_for_subject(self, actor, role, subject_ref):
        """Serve every referral held for one subject reference,
        oldest first. This is the surface the Home Healthcare
        person page reads: the person's bridge referral state for
        the same six codes. Access discipline mirrors the
        platforms' ownership rules: the subject themselves (actor
        == subject_ref) reads their own referrals; any other
        reader goes through this bridge's access guard under the
        REFERRAL category (OPERATOR / COORDINATOR / AUDITOR).
        Every granted read is receipted BEFORE the records are
        served — on this bridge's chain; the reading platform
        receipts its own side on its own chain."""
        self._check_actor(actor)
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise BridgeDenied('A non-empty subject_ref is required')
        if actor == subject_ref:
            self._record('UNCLE_NICKEY_SUBJECT_REFERRALS_READ',
                         actor=actor, subject_ref=subject_ref,
                         access='subject')
        else:
            try:
                self.guard.access(actor, role, 'REFERRAL', subject_ref,
                                  purpose='subject referrals')
            except FoundationForbidden as exc:
                raise BridgeForbidden(str(exc)) from exc
            except FoundationDenied as exc:
                raise BridgeDenied(str(exc)) from exc
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM bridge_referrals WHERE subject_ref = ? "
                "ORDER BY created_at, referral_id;",
                (subject_ref,)).fetchall()
        return [self._referral_view(row) for row in rows]

    def person_activation_state(self, actor, role, person_ref):
        """Read one person's six-workflow activation state from
        Home Healthcare, through its own service surface, so this
        bridge's referral lifecycle works against live
        activations. The state is Home Healthcare's record, served
        by Home Healthcare and receipted on its chain; this bridge
        receipts the read on its own chain before serving it — a
        failure on either side fails the read closed. Access: the
        person themselves (actor == person_ref), or a reader the
        guard authorizes under the STATUS category (OPERATOR /
        AUDITOR)."""
        self._check_actor(actor)
        if not isinstance(person_ref, str) or not person_ref.strip():
            raise BridgeDenied('A non-empty person_ref is required')
        if actor != person_ref:
            try:
                self.guard.access(actor, role, 'STATUS', person_ref,
                                  purpose='person activation state')
            except FoundationForbidden as exc:
                raise BridgeForbidden(str(exc)) from exc
            except FoundationDenied as exc:
                raise BridgeDenied(str(exc)) from exc
        state = self._read_activation_state(person_ref, actor)
        self._record('UNCLE_NICKEY_ACTIVATION_STATE_READ',
                     actor=actor, person_ref=person_ref,
                     identifier_status=state['identifier_status'],
                     activated=state['activation'] is not None)
        return state

    # -- check-in ------------------------------------------------------

    def record_check_in(self, actor, deployment_location,
                        operational_status):
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._check_actor(actor)
        if not self._is_operator(actor):
            raise BridgeForbidden('Check-in is an operator authority')
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise BridgeDenied(str(exc)) from exc
                self._record('UNCLE_NICKEY_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record

    # -- status --------------------------------------------------------

    def guardian_relay_status(self):
        """The RECOVERED guardian record and the REBUILT bridge's
        live state, clearly separated and labeled: the recovered
        half is a record, the live half is measured from this
        service's own store. Neither stands in for the other."""
        with self._connect() as db:
            counts = self._counts(db)
        return {
            'recovered_record': dict(GUARDIAN_RECORD),
            'live_bridge_state': {'referral_counts': counts},
        }

    def status(self):
        """Platform status: identity, the industry registry,
        referral counts by status, the latest check-in, and the
        guardian record's source line."""
        with self._connect() as db:
            counts = self._counts(db)
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'industries': [dict(entry) for entry in INDUSTRY_REGISTRY],
            'referral_counts': counts,
            'latest_check_in': latest,
            'guardian_record_source': GUARDIAN_RECORD['source'],
            'home_healthcare_bound': self.home_healthcare is not None,
        }
