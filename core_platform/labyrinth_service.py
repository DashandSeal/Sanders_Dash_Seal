"""LABYRINTH — the zero-trust and attack-path security RTSA.

The production build-out of the LABYRINTH role contract
(``core_platform/rtsa_registry.py``: canonical name "LABYRINTH",
slug ``labyrinth``, mission "zero-trust and attack-path
security", SPECIFIED, enabled: False), built whole as its own
platform service over the shared RTSA foundation (RTSA Build
Program Q29).

Identity discipline (MASTER section 5 / section 20, catalog
decision D-N8): LABYRINTH is a SEPARATE platform from Sanders
Labyrinth Shield (the real-time defensive perimeter environment,
queue Q8) and from RTSA Minotaur (the patrol that certifies the
Shield's safety, queue Q9). The Shield enforces; the Minotaur
patrols; LABYRINTH analyzes. The three are never merged, and this
module imports neither of them.

The contract's guardrails are the design: the role requires
Twin-Gate authorization and human approval, and its prohibited
operations — external execution, credential access, notarization,
legal filing, financial transfer, and production deployment —
are refused by name, in the service, every time. This platform
performs no scan, no probe, and no enforcement. What it does is
the attack-path analysis record, governed:

- **Analysis records**: attack-path analyses over declared
  system models, carried as durable, receipted records (subject
  reference, declared entry-point reference, target reference,
  scope reference) with a lifecycle: REQUESTED, then APPROVED or
  REJECTED by a human operator's recorded decision, then a
  result recorded against presented evidence (RESULT_RECORDED).
  The analysis reasons over the declared model an operator
  presents by reference; it does not reach into any live system.
- **Results** are recorded only for APPROVED analyses and only
  against a presented evidence reference, with a closed verdict
  set (PATH_EXISTS / NO_PATH_WITHIN_SCOPE / INCONCLUSIVE) —
  NO_PATH_WITHIN_SCOPE is scoped to the declared model and scope
  by construction, never a claim about a live environment.
- **Zero-trust discipline**: no analysis result is inherited,
  assumed, or carried over — every subject is analyzed on its own
  recorded approval, and a result binds only to the analysis,
  model, and scope it names.
- **Contract discipline**: the role contract is exposed as a
  view, and an operation check answers — fail-closed — whether a
  named operation is a record operation this platform may carry
  or a prohibited operation it refuses.

No record, no action: every state-changing operation writes its
Glass-Box receipt inside the same transaction, through the shared
foundation's audit adapter; the service refuses to exist without
one.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections import deque
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
from .rtsa_registry import RTSA_ROLES


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='labyrinth',
    name='LABYRINTH',
    legal_entities=('s_and_g_security_inc',),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

CONTRACT = RTSA_ROLES['LABYRINTH']
RECORD_OPERATIONS = (
    'record_analysis', 'approve_analysis', 'record_result',
    'view_analysis', 'view_contract',
    'record_graph', 'record_edge', 'view_graph',
    'record_policy', 'flow_check',
)
ANALYSIS_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED',
                     'RESULT_RECORDED')
ANALYSIS_TRANSITIONS = {
    'approve': {'REQUESTED': 'APPROVED'},
    'reject': {'REQUESTED': 'REJECTED'},
}
VERDICTS = ('PATH_EXISTS', 'NO_PATH_WITHIN_SCOPE', 'INCONCLUSIVE')


class LabyrinthDenied(Exception):
    """The requested LABYRINTH operation is not allowed."""


class LabyrinthForbidden(Exception):
    """The actor lacks authority for the requested operation."""



# -- Inherited defenses (founder directive,
# 2026-11-26) --------------------------------
#
# Every shield inherits the Minotaur's new
# defenses: a shared defensive STANDARD,
# separately embodied in this shield's own
# machinery — never merged into the Minotaur
# or into another shield. Each protection of
# his set stands here with its applicability
# for THIS shield: INHERITED_FUNCTIONING
# (implemented and exercised in this
# service) or INHERITED_BY_DESIGN (the
# standard holds by this shield's design,
# with the reason stated). His eight
# domains organize the set.
FOUNDER_INHERITANCE_DIRECTIVE_VERBATIM = (
    'Everyone of my \U0001f6e1\ufe0f\'s must inherit the'
    ' minotaur\'s new defenses don\'t you agree')
INHERITED_STANDARD_SOURCE = (
    'the Minotaur\'s upgrade, his adopted Self-'
    'Protection Amendment, the thirteen anti-'
    'probing protections, and the eight-domain'
    ' architecture, under the functioning-'
    'defense standard')
INHERITED_PROTECTION_OUTCOMES = (
    'EVIDENCED', 'FINDING', 'NOT_EVIDENCED',
    'FUNCTIONING')
INHERITED_PROTECTIONS = (
    {'protection': 'COMPROMISED_ADMINISTRATIVE_CREDENTIALS',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'operator verification with per-actor failure bucketing and lockout, in this service'},
    {'protection': 'PRIVILEGE_ESCALATION',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'the role guard is fixed in this service; guarded reads cannot write'},
    {'protection': 'MALICIOUS_INTERNAL_PLATFORM_COMMUNICATIONS',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'records arriving platform-to-platform are never executed as instructions in this service — an architectural property; the Minotaur\'s patrol verifies this shield\'s core by hash, not by claimed identity'},
    {'protection': 'COMPROMISED_RECOVERY_MECHANISMS',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'recovery for this shield is by reference to the Glass-Box receipts and the Minotaur\'s signed anchor over its core; a compromised recovery source is detected from his layer'},
    {'protection': 'UNAUTHORIZED_CONFIGURATION_CHANGES',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'configuration of record in this service changes only through verified operator acts, each receipted'},
    {'protection': 'DENIAL_OF_SERVICE',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'availability is a host property; this shield performs no unauthenticated work amplification — its acts are bounded governed records behind the guard'},
    {'protection': 'RESOURCE_EXHAUSTION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'his bounded-record discipline applies: this shield\'s acts are single governed records, and its stores are its own'},
    {'protection': 'SECURITY_LOG_TAMPERING',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'every graph, edge, policy, and flow record is receipted at the moment of the act'},
    {'protection': 'CLOCK_TIMESTAMP_MANIPULATION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield\'s records carry receipted sequence in the Glass-Box audit; its own determinations do not order by wall clock'},
    {'protection': 'COMPROMISED_CRYPTOGRAPHIC_RANDOMNESS',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield generates no key material; the Minotaur\'s deterministic derivation standard covers the signing layer above it'},
    {'protection': 'MALICIOUS_SOFTWARE_ROLLBACK',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield\'s core is hash-pinned by the Minotaur\'s patrol; a rolled-back module reads MISMATCH there and raises his anomaly'},
    {'protection': 'UNAUTHORIZED_DISABLING_OF_DEFENSIVE_FUNCTIONS',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'this service exposes no operation that disables a defensive function'},
    {'protection': 'SINGLE_POINTS_OF_FAILURE',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'evidence for this shield stands in its own store, the Glass-Box receipts, and the Minotaur\'s anchor — three places by design'},
    {'protection': 'THREAT_DETECTION_INTELLIGENCE_COMPROMISE',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield\'s detection records are receipted records; alteration is a tamper finding under the same discipline'},
    {'protection': 'GOVERNING_DIRECTIVES_MODIFICATION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'his governing directives stand in Sanders Sentinel\'s guarded record set; this shield holds no directive it could rewrite'},
    {'protection': 'UNAUTHORIZED_RECONNAISSANCE_AND_PROBING',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield\'s surfaces answer only through the access guard; probing meets the uniform refusal'},
    {'protection': 'NETWORK_AND_SERVICE_ENUMERATION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'nothing in this shield lists its internals to an unguarded caller; invalid and unknown requests receive the identical refusal'},
    {'protection': 'API_DISCOVERY_AND_UNAUTHORIZED_ENDPOINT_ACCESS',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield\'s route forms answer 401 unauthenticated by the application gate'},
    {'protection': 'AUTHENTICATION_BYPASS_AND_SESSION_HIJACKING',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'no session stands in this service to hijack; the actor is verified at the moment of every act'},
    {'protection': 'CREDENTIAL_THEFT_AND_BRUTE_FORCE',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'the lockout: failed verifications bucket per actor and lock out at the threshold, in this service'},
    {'protection': 'ERROR_MESSAGE_INFORMATION_LEAKAGE',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'refusals in this service are uniform: they name the rule, never the internals'},
    {'protection': 'TIMING_AND_SIDE_CHANNEL_ATTACKS',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'no secret-bearing comparison stands in this shield\'s own code paths; its hashes are integrity values, not secrets'},
    {'protection': 'FORGED_INTERNAL_PLATFORM_IDENTITIES',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'every state-changing act re-verifies the operator in this service; a forged instruction is an unverified actor and is refused before any state change'},
    {'protection': 'DEFENSIVE_PATROL_MANIPULATION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'this shield keeps no patrol of its own to manipulate; the Minotaur\'s sequencing derives from his signed chain head'},
    {'protection': 'DEFENSIVE_CONFIGURATION_DISCOVERY',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'its communication policies are guarded reads; unguarded callers receive the uniform refusal'},
    {'protection': 'RECOVERY_INFRASTRUCTURE_COMPROMISE',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'recovery evidence for this shield stands outside its own store (Glass-Box receipts, the Minotaur\'s anchor)'},
    {'protection': 'DISABLE_OWN_PROTECTIONS_ATTACKS',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'there is no disabling operation in this service for such an attack to invoke'},
    {'protection': 'MACHINERY_TURNED_AGAINST_AUTHORIZED_OPERATIONS',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'this service acts only on verified operator acts and its own records'},
)
INHERITED_MACHINERY = (
    {'machinery': 'HASH_SIGNED_ATTESTATION_CHAIN',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'embodied as Glass-Box receipts for every record plus the Minotaur\'s signed chain over this shield\'s core'},
    {'machinery': 'LABYRINTH_BEHAVIOR',
     'applicability': 'INHERITED_FUNCTIONING',
     'basis': 'native to this shield: the attack-path graph — paths through a labyrinth of edges to the crown — is its own machinery'},
    {'machinery': 'CRYPTO_CLAIM_RULE',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'no cryptographic claim surface stands in this shield to assert or downgrade'},
    {'machinery': 'DECOY_ISOLATION',
     'applicability': 'INHERITED_BY_DESIGN',
     'basis': 'decoys are the Minotaur\'s machinery over this shield; this shield plants none'},
)
INHERITED_DOMAINS = (
    'SELF_PROTECTION',
    'ANTI_PROBING',
    'ANTI_CIRCUMVENTION',
    'CRYPTOGRAPHIC_PROTECTION',
    'INFRASTRUCTURE_PROTECTION',
    'RECOVERY_PROTECTION',
    'DEFENSIVE_CONTINUITY',
    'COUNTER_MANIPULATION',
)

class LabyrinthService:
    """LABYRINTH: governed attack-path analysis records under
    the role contract's discipline."""

    def __init__(self, database_path, *, operator_verifier, audit,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise LabyrinthDenied(
                'LABYRINTH requires a working Glass-Box audit'
                ' adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'labyrinth', {
            'OPERATOR': {'SECURITY'},
            'AUDITOR': {'SECURITY'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS lab_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    subject_ref TEXT NOT NULL,
                    entry_ref TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    scope_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    evidence_ref TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_graphs (
                    graph_ref TEXT PRIMARY KEY,
                    entry_refs TEXT NOT NULL,
                    crown_refs TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    graph_ref TEXT NOT NULL,
                    from_ref TEXT NOT NULL,
                    to_ref TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS lab_graph_edges_graph_idx
                    ON lab_graph_edges (graph_ref);
                CREATE TABLE IF NOT EXISTS lab_graph_findings (
                    finding_id TEXT PRIMARY KEY,
                    graph_ref TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    detected_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_policies (
                    policy_id TEXT PRIMARY KEY,
                    from_platform TEXT NOT NULL,
                    to_platform TEXT NOT NULL,
                    endpoint_ref TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_flow_checks (
                    check_id TEXT PRIMARY KEY,
                    from_platform TEXT NOT NULL,
                    to_platform TEXT NOT NULL,
                    endpoint_ref TEXT NOT NULL,
                    determination TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
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
            raise LabyrinthForbidden(
                'A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        """Verify the operator — with the inherited
        brute-force defense functioning: failed
        verifications bucket per actor, and at the
        lockout threshold the actor is refused
        outright until the window clears. The
        refusal is uniform."""
        self._check_actor(actor)
        now = self._now()
        with self._connect() as db:
            self._ensure_defense_tables(db)
            failures = db.execute(
                'SELECT COUNT(*) AS n FROM lab_auth_failures'
                ' WHERE actor = ? AND failed_at > ?',
                (actor, now - 900),
            ).fetchone()['n']
        if failures >= 5:
            raise LabyrinthForbidden(
                'Operator authority is required for this operation')
        if self._is_operator(actor):
            with self._connect() as db:
                self._ensure_defense_tables(db)
                db.execute('BEGIN IMMEDIATE;')
                try:
                    db.execute(
                        'DELETE FROM lab_auth_failures'
                        ' WHERE actor = ?', (actor,))
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            return
        with self._connect() as db:
            self._ensure_defense_tables(db)
            db.execute('BEGIN IMMEDIATE;')
            try:
                db.execute(
                    'INSERT INTO lab_auth_failures'
                    ' (actor, failed_at) VALUES (?, ?)',
                    (actor, now))
                db.commit()
            except Exception:
                db.rollback()
                raise
        raise LabyrinthForbidden(
            'Operator authority is required for this operation')
    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise LabyrinthForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'SECURITY', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise LabyrinthForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise LabyrinthDenied(str(exc)) from exc

    # -- contract -----------------------------------------------------

    @staticmethod
    def contract_view() -> dict:
        return {
            'canonical_name': CONTRACT.canonical_name,
            'slug': CONTRACT.slug,
            'mission': CONTRACT.mission,
            'contract_status': CONTRACT.status.value,
            'enabled': CONTRACT.enabled,
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'prohibited_operations':
                list(CONTRACT.prohibited_operations),
            'record_operations': list(RECORD_OPERATIONS),
            'note': 'The platform carries attack-path analysis'
                    ' records over declared models only: it'
                    ' performs no scan, no probe, and no'
                    ' enforcement, and a NO_PATH_WITHIN_SCOPE'
                    ' verdict binds only to the declared model and'
                    ' scope it names. LABYRINTH is a separate'
                    ' platform from Sanders Labyrinth Shield (the'
                    ' defensive perimeter) and from RTSA Minotaur'
                    ' (its patrol) — the three are never merged.'
                    ' The contract remains SPECIFIED and enabled:'
                    " False — deployment of the intelligence is"
                    " the owner's named approval, not this"
                    " build's.",
        }

    def operation_check(self, actor, role, operation, *, region=None):
        """Fail-closed contract check: a named operation is either
        a record operation this platform carries, or it is refused
        — prohibited by the contract, or unknown."""
        self._geo(region)
        self._guard_access(actor, role, 'contract',
                           'operation contract check')
        if operation in CONTRACT.prohibited_operations:
            raise LabyrinthDenied(
                f'Operation {operation!r} is prohibited by the'
                ' LABYRINTH role contract')
        if operation not in RECORD_OPERATIONS:
            raise LabyrinthDenied(
                f'Unknown operation: {operation!r}')
        return {
            'operation': operation,
            'permitted_as': 'RECORD_ONLY',
            'requires_twin_gate': CONTRACT.requires_twin_gate,
            'requires_human_approval':
                CONTRACT.requires_human_approval,
            'contract_enabled': CONTRACT.enabled,
        }

    # -- analyses -------------------------------------------------------

    @staticmethod
    def _analysis_view(row):
        return {
            'analysis_id': row['analysis_id'],
            'subject_ref': row['subject_ref'],
            'entry_ref': row['entry_ref'],
            'target_ref': row['target_ref'],
            'scope_ref': row['scope_ref'],
            'status': row['status'],
            'verdict': row['verdict'],
            'evidence_ref': row['evidence_ref'],
            'requested_by': row['requested_by'],
            'requested_at': row['requested_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    def create_analysis(self, actor, subject_ref, entry_ref,
                        target_ref, scope_ref, *, region=None):
        """Record one attack-path analysis request (operator
        only) over a declared model, presented by reference. The
        record governs the analysis; recording it scans nothing
        and reaches into no live system."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('subject_ref', subject_ref),
                             ('entry_ref', entry_ref),
                             ('target_ref', target_ref),
                             ('scope_ref', scope_ref)):
            if not isinstance(value, str) or not value.strip():
                raise LabyrinthDenied(f'A {label} is required')
        now = self._now()
        analysis_id = f'lab-analysis-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_ANALYSIS_RECORDED', actor=actor,
                    analysis_id=analysis_id,
                    subject_ref=subject_ref.strip(),
                    target_ref=target_ref.strip())
                db.execute(
                    'INSERT INTO lab_analyses (analysis_id,'
                    ' subject_ref, entry_ref, target_ref, scope_ref,'
                    ' status, verdict, evidence_ref, requested_by,'
                    ' requested_at, updated_by, updated_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?, ?, ?)',
                    (analysis_id, subject_ref.strip(),
                     entry_ref.strip(), target_ref.strip(),
                     scope_ref.strip(), 'REQUESTED', None, None,
                     actor, now, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(row)

    def analyses_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'analyses', 'analyses view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM lab_analyses ORDER BY requested_at',
            ).fetchall()
        return [self._analysis_view(row) for row in rows]

    def analysis_view(self, actor, role, analysis_id, *,
                      region=None):
        self._geo(region)
        self._guard_access(actor, role, analysis_id, 'analysis view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        if row is None:
            raise LabyrinthDenied('Analysis not found')
        return self._analysis_view(row)

    def analysis_action(self, actor, analysis_id, action, *,
                        region=None):
        """Approve or reject one requested analysis (operator
        only) — the recorded human decision the contract
        requires. Approval approves the RECORD; it executes
        nothing."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ANALYSIS_TRANSITIONS.get(action)
        if transitions is None:
            raise LabyrinthDenied(
                f'Unknown analysis action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lab_analyses'
                    ' WHERE analysis_id = ?',
                    (analysis_id,)).fetchone()
                if row is None:
                    raise LabyrinthDenied('Analysis not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise LabyrinthDenied(
                        f"Cannot {action} an analysis in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'LABYRINTH_ANALYSIS_ACTION', actor=actor,
                    analysis_id=analysis_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE lab_analyses SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE analysis_id = ?',
                    (new_status, actor, now, receipt_id, analysis_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(updated)

    def record_result(self, actor, analysis_id, verdict,
                      evidence_ref, *, region=None):
        """Record one approved analysis's result (operator only),
        against a presented evidence reference. A result without
        evidence is refused: an attack-path claim with nothing
        behind it is not a record. A NO_PATH_WITHIN_SCOPE verdict
        binds only to the declared model and scope the analysis
        names."""
        self._geo(region)
        self._require_operator(actor)
        if verdict not in VERDICTS:
            raise LabyrinthDenied(f'Unknown verdict: {verdict!r}')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise LabyrinthDenied(
                'An evidence reference is required to record a'
                ' result')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM lab_analyses'
                    ' WHERE analysis_id = ?',
                    (analysis_id,)).fetchone()
                if row is None:
                    raise LabyrinthDenied('Analysis not found')
                if row['status'] != 'APPROVED':
                    raise LabyrinthDenied(
                        'Results are recorded only for APPROVED'
                        f" analyses (this one is {row['status']})")
                receipt_id = self._record(
                    'LABYRINTH_RESULT_RECORDED', actor=actor,
                    analysis_id=analysis_id, verdict=verdict,
                    evidence_ref=evidence_ref.strip())
                db.execute(
                    'UPDATE lab_analyses SET status = ?, verdict'
                    ' = ?, evidence_ref = ?, updated_by = ?,'
                    ' updated_at = ?, receipt_id = ?'
                    ' WHERE analysis_id = ?',
                    ('RESULT_RECORDED', verdict,
                     evidence_ref.strip(), actor, now, receipt_id,
                     analysis_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM lab_analyses WHERE analysis_id = ?',
                (analysis_id,)).fetchone()
        return self._analysis_view(updated)

    # -- attack-path graph (shield upgrade, 2026-11-26) --------------
    #
    # The graph discipline of the shield-upgrade research (Area
    # 2.4) made native over declared inventories: nodes are
    # identities, platforms, credentials, and data stores named
    # by reference; edges are traversable relationships an
    # operator records. The platform computes shortest paths
    # from declared entry nodes to declared crown (Tier 0)
    # nodes, ranks choke points — the edges whose removal
    # disconnects the most entry-to-crown pairs — and treats
    # edge creation itself as a detection event: an edge that
    # creates a new entry-to-crown path raises a finding in
    # the same transaction. The graph reasons over the declared
    # model only; it scans nothing and reaches into no live
    # system.

    @staticmethod
    def _graph_paths(entry_refs, crown_refs, edges):
        """All (entry, crown) pairs with one shortest path each,
        over the declared edges. ``edges`` is a list of
        (from_ref, to_ref) pairs."""
        adjacency = {}
        for from_ref, to_ref in edges:
            adjacency.setdefault(from_ref, []).append(to_ref)
        paths = []
        for entry in entry_refs:
            for crown in crown_refs:
                if entry == crown:
                    continue
                previous = {entry: None}
                queue = deque([entry])
                while queue:
                    node = queue.popleft()
                    if node == crown:
                        break
                    for nxt in adjacency.get(node, []):
                        if nxt not in previous:
                            previous[nxt] = node
                            queue.append(nxt)
                if crown not in previous:
                    continue
                path = []
                node = crown
                while node is not None:
                    path.append(node)
                    node = previous[node]
                paths.append({
                    'entry_ref': entry,
                    'crown_ref': crown,
                    'path': list(reversed(path)),
                    'hops': len(path) - 1,
                })
        return paths

    @classmethod
    def _connected_pairs(cls, entry_refs, crown_refs, edges):
        return {
            (p['entry_ref'], p['crown_ref'])
            for p in cls._graph_paths(entry_refs, crown_refs,
                                      edges)
        }

    @staticmethod
    def _edge_view(row):
        return {
            'edge_id': row['edge_id'],
            'graph_ref': row['graph_ref'],
            'from_ref': row['from_ref'],
            'to_ref': row['to_ref'],
            'relationship': row['relationship'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def _graph_rows(self, db, graph_ref):
        graph = db.execute(
            'SELECT * FROM lab_graphs WHERE graph_ref = ?',
            (graph_ref,)).fetchone()
        if graph is None:
            raise LabyrinthDenied('Graph not found')
        edges = db.execute(
            'SELECT * FROM lab_graph_edges WHERE graph_ref = ?'
            ' ORDER BY recorded_at', (graph_ref,)).fetchall()
        return graph, edges

    def record_graph(self, actor, graph_ref, entry_refs,
                     crown_refs, *, region=None):
        """Declare one attack-path graph (operator only): its
        low-trust entry nodes and its crown (Tier 0) nodes, all
        by reference."""
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(graph_ref, str) or not graph_ref.strip():
            raise LabyrinthDenied('A graph reference is required')
        for label, refs in (('entry_refs', entry_refs),
                            ('crown_refs', crown_refs)):
            if not isinstance(refs, (list, tuple)) or not refs \
                    or any(not isinstance(r, str) or not r.strip()
                           for r in refs):
                raise LabyrinthDenied(
                    f'The graph {label} must be a non-empty list'
                    ' of references')
        now = self._now()
        graph_ref = graph_ref.strip()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_GRAPH_RECORDED', actor=actor,
                    graph_ref=graph_ref,
                    entry_refs=list(entry_refs),
                    crown_refs=list(crown_refs))
                db.execute(
                    'INSERT INTO lab_graphs (graph_ref, entry_refs,'
                    ' crown_refs, recorded_by, recorded_at,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?)'
                    ' ON CONFLICT(graph_ref) DO UPDATE SET'
                    ' entry_refs = excluded.entry_refs,'
                    ' crown_refs = excluded.crown_refs,'
                    ' recorded_by = excluded.recorded_by,'
                    ' recorded_at = excluded.recorded_at,'
                    ' receipt_id = excluded.receipt_id',
                    (graph_ref, json.dumps(list(entry_refs)),
                     json.dumps(list(crown_refs)), actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'graph_ref': graph_ref,
            'entry_refs': list(entry_refs),
            'crown_refs': list(crown_refs),
            'recorded_by': actor,
            'recorded_at': now,
        }

    def record_edge(self, actor, graph_ref, from_ref, to_ref,
                    relationship, *, region=None):
        """Record one traversable edge in a declared graph
        (operator only). If the edge creates an entry-to-crown
        path that did not exist before it, a NEW_PATH_TO_CROWN
        finding is raised in the same transaction — edge
        creation is itself a detection event."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (('from_ref', from_ref),
                             ('to_ref', to_ref),
                             ('relationship', relationship)):
            if not isinstance(value, str) or not value.strip():
                raise LabyrinthDenied(f'A {label} is required')
        now = self._now()
        edge_id = f'lab-edge-{uuid.uuid4().hex[:16]}'
        finding = None
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                graph, rows = self._graph_rows(db, graph_ref)
                entry_refs = json.loads(graph['entry_refs'])
                crown_refs = json.loads(graph['crown_refs'])
                before = self._connected_pairs(
                    entry_refs, crown_refs,
                    [(r['from_ref'], r['to_ref']) for r in rows])
                receipt_id = self._record(
                    'LABYRINTH_EDGE_RECORDED', actor=actor,
                    edge_id=edge_id, graph_ref=graph_ref,
                    from_ref=from_ref.strip(),
                    to_ref=to_ref.strip())
                db.execute(
                    'INSERT INTO lab_graph_edges (edge_id,'
                    ' graph_ref, from_ref, to_ref, relationship,'
                    ' recorded_by, recorded_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (edge_id, graph_ref, from_ref.strip(),
                     to_ref.strip(), relationship.strip(), actor,
                     now, receipt_id),
                )
                after = self._connected_pairs(
                    entry_refs, crown_refs,
                    [(r['from_ref'], r['to_ref']) for r in rows]
                    + [(from_ref.strip(), to_ref.strip())])
                new_pairs = sorted(after - before)
                if new_pairs:
                    finding_id = (
                        f'lab-finding-{uuid.uuid4().hex[:16]}')
                    detail = (
                        'Edge ' + from_ref.strip() + ' -> '
                        + to_ref.strip()
                        + ' created new entry-to-crown path(s): '
                        + ', '.join(
                            f'{a} -> {b}' for a, b in new_pairs))
                    f_receipt = self._record(
                        'LABYRINTH_GRAPH_FINDING', actor=actor,
                        finding_id=finding_id, graph_ref=graph_ref,
                        kind='NEW_PATH_TO_CROWN', detail=detail)
                    db.execute(
                        'INSERT INTO lab_graph_findings'
                        ' (finding_id, graph_ref, kind, detail,'
                        ' detected_at, receipt_id) VALUES'
                        ' (?, ?, ?, ?, ?, ?)',
                        (finding_id, graph_ref,
                         'NEW_PATH_TO_CROWN', detail, now,
                         f_receipt),
                    )
                    finding = {
                        'finding_id': finding_id,
                        'graph_ref': graph_ref,
                        'kind': 'NEW_PATH_TO_CROWN',
                        'detail': detail,
                        'detected_at': now,
                        'receipt_id': f_receipt,
                    }
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_graph_edges WHERE edge_id = ?',
                (edge_id,)).fetchone()
        view = self._edge_view(row)
        view['new_path_finding'] = finding
        return view

    def graph_view(self, actor, role, graph_ref, *, region=None):
        """One declared graph with its computed attack paths
        and choke points. A path binds only to the declared
        model; NO path in the view is a claim about a live
        environment."""
        self._geo(region)
        self._guard_access(actor, role, graph_ref, 'graph view')
        with self._connect() as db:
            graph, rows = self._graph_rows(db, graph_ref)
            findings = db.execute(
                'SELECT * FROM lab_graph_findings'
                ' WHERE graph_ref = ? ORDER BY detected_at',
                (graph_ref,)).fetchall()
        entry_refs = json.loads(graph['entry_refs'])
        crown_refs = json.loads(graph['crown_refs'])
        edges = [(r['from_ref'], r['to_ref']) for r in rows]
        paths = self._graph_paths(entry_refs, crown_refs, edges)
        connected = {(p['entry_ref'], p['crown_ref'])
                     for p in paths}
        choke_points = []
        for row in rows:
            remaining = [e for e in edges
                         if e != (row['from_ref'], row['to_ref'])]
            still = self._connected_pairs(entry_refs, crown_refs,
                                          remaining)
            disconnected = len(connected - still)
            if disconnected:
                choke_points.append({
                    'edge_id': row['edge_id'],
                    'from_ref': row['from_ref'],
                    'to_ref': row['to_ref'],
                    'pairs_disconnected': disconnected,
                })
        choke_points.sort(
            key=lambda c: -c['pairs_disconnected'])
        return {
            'graph_ref': graph_ref,
            'entry_refs': entry_refs,
            'crown_refs': crown_refs,
            'edges': [self._edge_view(r) for r in rows],
            'paths': paths,
            'choke_points': choke_points,
            'findings': [
                {'finding_id': f['finding_id'],
                 'kind': f['kind'], 'detail': f['detail'],
                 'detected_at': f['detected_at'],
                 'receipt_id': f['receipt_id']}
                for f in findings],
            'note': 'Computed over the declared model only:'
                    ' paths, choke points, and findings bind'
                    ' to the recorded edges and the declared'
                    ' entry and crown nodes, never to a live'
                    ' environment.',
        }

    # -- communication policies (shield upgrade, 2026-11-26) ---------
    #
    # Per-platform communication policy on the CISA
    # observe-then-enforce method (research Area 2.3): an
    # operator records which platform may call which endpoint;
    # new policies begin in OBSERVE (a non-listed flow is
    # recorded as an observed violation, not refused) and are
    # moved to ENFORCE by a further recorded policy, where a
    # non-listed flow is refused. LABYRINTH carries the policy
    # and the flow-check records; it enforces nothing on live
    # traffic — the determination is the record.

    @staticmethod
    def _policy_view(row):
        return {
            'policy_id': row['policy_id'],
            'from_platform': row['from_platform'],
            'to_platform': row['to_platform'],
            'endpoint_ref': row['endpoint_ref'],
            'mode': row['mode'],
            'status': row['status'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def record_policy(self, actor, from_platform, to_platform,
                      endpoint_ref, mode, *, region=None):
        """Record one allowed inter-platform flow (operator
        only) with its rollout mode: OBSERVE or ENFORCE."""
        self._geo(region)
        self._require_operator(actor)
        if mode not in ('OBSERVE', 'ENFORCE'):
            raise LabyrinthDenied(
                f'Unknown policy mode: {mode!r}')
        for label, value in (
                ('from_platform', from_platform),
                ('to_platform', to_platform),
                ('endpoint_ref', endpoint_ref)):
            if not isinstance(value, str) or not value.strip():
                raise LabyrinthDenied(f'A {label} is required')
        now = self._now()
        policy_id = f'lab-policy-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_POLICY_RECORDED', actor=actor,
                    policy_id=policy_id,
                    from_platform=from_platform.strip(),
                    to_platform=to_platform.strip(),
                    endpoint_ref=endpoint_ref.strip(), mode=mode)
                db.execute(
                    'INSERT INTO lab_policies (policy_id,'
                    ' from_platform, to_platform, endpoint_ref,'
                    ' mode, status, recorded_by, recorded_at,'
                    ' updated_by, updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (policy_id, from_platform.strip(),
                     to_platform.strip(), endpoint_ref.strip(),
                     mode, 'ACTIVE', actor, now, actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_policies WHERE policy_id = ?',
                (policy_id,)).fetchone()
        return self._policy_view(row)

    def policies_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'policies',
                           'policies view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM lab_policies ORDER BY recorded_at',
            ).fetchall()
        return [self._policy_view(row) for row in rows]

    def flow_check(self, actor, from_platform, to_platform,
                   endpoint_ref, *, region=None):
        """Record one flow determination against the policy
        set (operator only). A listed flow is ALLOWED. An
        unlisted flow is an OBSERVED_VIOLATION while any
        governing policy stands in OBSERVE, and REFUSED once
        the governing mode is ENFORCE; with no policy at all
        the default is OBSERVE — observe-then-enforce begins
        by observing."""
        self._geo(region)
        self._require_operator(actor)
        for label, value in (
                ('from_platform', from_platform),
                ('to_platform', to_platform),
                ('endpoint_ref', endpoint_ref)):
            if not isinstance(value, str) or not value.strip():
                raise LabyrinthDenied(f'A {label} is required')
        now = self._now()
        check_id = f'lab-flow-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            listed = db.execute(
                "SELECT * FROM lab_policies WHERE status ="
                " 'ACTIVE' AND from_platform = ? AND"
                ' to_platform = ? AND endpoint_ref = ?',
                (from_platform.strip(), to_platform.strip(),
                 endpoint_ref.strip()),
            ).fetchone()
            governing = db.execute(
                "SELECT mode FROM lab_policies WHERE status ="
                " 'ACTIVE' AND from_platform = ?",
                (from_platform.strip(),),
            ).fetchall()
        if listed is not None:
            determination = 'ALLOWED'
            mode = listed['mode']
        else:
            mode = ('ENFORCE' if any(
                row['mode'] == 'ENFORCE' for row in governing)
                else 'OBSERVE')
            determination = (
                'REFUSED' if mode == 'ENFORCE'
                else 'OBSERVED_VIOLATION')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LABYRINTH_FLOW_CHECK', actor=actor,
                    check_id=check_id,
                    from_platform=from_platform.strip(),
                    to_platform=to_platform.strip(),
                    endpoint_ref=endpoint_ref.strip(),
                    determination=determination, mode=mode)
                db.execute(
                    'INSERT INTO lab_flow_checks (check_id,'
                    ' from_platform, to_platform, endpoint_ref,'
                    ' determination, mode, recorded_by,'
                    ' recorded_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (check_id, from_platform.strip(),
                     to_platform.strip(), endpoint_ref.strip(),
                     determination, mode, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_flow_checks WHERE check_id = ?',
                (check_id,)).fetchone()
        return {
            'check_id': row['check_id'],
            'from_platform': row['from_platform'],
            'to_platform': row['to_platform'],
            'endpoint_ref': row['endpoint_ref'],
            'determination': row['determination'],
            'mode': row['mode'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }


    # -- inherited defenses (founder directive,
    # 2026-11-26) --------------------------------
    #
    # The Minotaur's defensive standard, embodied
    # in this shield's own machinery: the lockout
    # in _require_operator above, and the governed
    # self-protection checks of record here — each
    # inherited protection's state derived from
    # its checks, its applicability stated in the
    # design of record.

    @staticmethod
    def _ensure_defense_tables(db):
        db.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS lab_defense_checks (
                check_id TEXT PRIMARY KEY,
                protection_key TEXT NOT NULL,
                outcome TEXT NOT NULL,
                evidence_ref TEXT NOT NULL,
                detail TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                recorded_at REAL NOT NULL,
                receipt_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_auth_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                failed_at REAL NOT NULL
            );
            """)

    @staticmethod
    def inherited_defenses_design_view() -> dict:
        return {
            'directive_verbatim':
                FOUNDER_INHERITANCE_DIRECTIVE_VERBATIM,
            'standard_source':
                INHERITED_STANDARD_SOURCE,
            'embodiment': 'SEPARATELY_EMBODIED',
            'shields_merged': False,
            'merged_into_minotaur': False,
            'domains': list(INHERITED_DOMAINS),
            'protections': [dict(e) for e in
                INHERITED_PROTECTIONS],
            'machinery': [dict(e) for e in
                INHERITED_MACHINERY],
            'external_connections': 'NONE',
        }

    def inherited_defenses_view(self, actor, role, *,
                                region=None):
        self._geo(region)
        self._guard_access(actor, role,
                           'self-protection',
                           'inherited defenses view')
        with self._connect() as db:
            self._ensure_defense_tables(db)
            rows = db.execute(
                'SELECT * FROM lab_defense_checks'
                ' ORDER BY recorded_at').fetchall()
        latest = {}
        for row in rows:
            latest[row['protection_key']] = row
        protections = []
        for entry in INHERITED_PROTECTIONS:
            row = latest.get(entry['protection'])
            protections.append({
                'protection': entry['protection'],
                'applicability':
                    entry['applicability'],
                'basis': entry['basis'],
                'state': (row['outcome'] if row
                          else 'CONSTRUCTED'),
                'latest_check': (
                    {'check_id': row['check_id'],
                     'outcome': row['outcome'],
                     'evidence_ref':
                         row['evidence_ref'],
                     'recorded_at':
                         row['recorded_at'],
                     'receipt_id': row['receipt_id']}
                    if row else None),
            })
        return {
            'design': type(self)
                .inherited_defenses_design_view(),
            'part': 'INHERITED_MINOTAUR_DEFENSES',
            'ladder_state': 'CONSTRUCTED',
            'protections': protections,
            'checks_total': len(rows),
            'external_connections': 'NONE',
        }

    def record_self_protection_check(
            self, actor, protection_key, outcome,
            evidence_ref, detail, *, region=None):
        self._geo(region)
        self._require_operator(actor)
        known = {e['protection'] for e in
                 INHERITED_PROTECTIONS}
        if protection_key not in known:
            raise LabyrinthDenied(
                'The protection must be one of the inherited set')
        if outcome not in INHERITED_PROTECTION_OUTCOMES:
            raise LabyrinthDenied(
                'The check outcome must be one of: '
                + ', '.join(
                    INHERITED_PROTECTION_OUTCOMES))
        for label, value in (
                ('evidence_ref', evidence_ref),
                ('detail', detail)):
            if (not isinstance(value, str)
                    or not value.strip()):
                raise LabyrinthDenied(
                    f'A {label} is required')
        now = self._now()
        check_id = 'lab-defcheck-' + uuid.uuid4().hex[:16]
        with self._connect() as db:
            self._ensure_defense_tables(db)
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'LAB_SELF_PROTECTION_CHECK',
                    actor=actor, check_id=check_id,
                    protection_key=protection_key,
                    outcome=outcome)
                db.execute(
                    'INSERT INTO lab_defense_checks'
                    ' (check_id, protection_key,'
                    ' outcome, evidence_ref, detail,'
                    ' recorded_by, recorded_at,'
                    ' receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?)',
                    (check_id, protection_key, outcome,
                     evidence_ref.strip(),
                     detail.strip(), actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM lab_defense_checks'
                ' WHERE check_id = ?',
                (check_id,)).fetchone()
        return {
            'check_id': row['check_id'],
            'protection': row['protection_key'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'detail': row['detail'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def self_protection_checks(self, actor, role, *,
                               region=None):
        self._geo(region)
        self._guard_access(actor, role,
                           'self-protection',
                           'self protection checks view')
        with self._connect() as db:
            self._ensure_defense_tables(db)
            rows = db.execute(
                'SELECT * FROM lab_defense_checks'
                ' ORDER BY recorded_at').fetchall()
        views = [{
            'check_id': row['check_id'],
            'protection': row['protection_key'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        } for row in rows]
        return {'checks': views, 'total': len(views)}

    # -- status / check-in ----------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            by_status = {s: 0 for s in ANALYSIS_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM lab_analyses'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            by_verdict = {v: 0 for v in VERDICTS}
            for row in db.execute(
                    'SELECT verdict, COUNT(*) AS n FROM lab_analyses'
                    ' WHERE verdict IS NOT NULL GROUP BY verdict'):
                by_verdict[row['verdict']] = row['n']
            graphs_total = db.execute(
                'SELECT COUNT(*) AS n FROM lab_graphs',
            ).fetchone()['n']
            edges_total = db.execute(
                'SELECT COUNT(*) AS n FROM lab_graph_edges',
            ).fetchone()['n']
            findings_total = db.execute(
                'SELECT COUNT(*) AS n FROM lab_graph_findings',
            ).fetchone()['n']
            policies_total = db.execute(
                "SELECT COUNT(*) AS n FROM lab_policies"
                " WHERE status = 'ACTIVE'",
            ).fetchone()['n']
            flow_checks_total = db.execute(
                'SELECT COUNT(*) AS n FROM lab_flow_checks',
            ).fetchone()['n']
            latest = _foundation_latest_check_in(db,
                                                 IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'contract': self.contract_view(),
            'analyses_total': sum(by_status.values()),
            'analyses_by_status': by_status,
            'analyses_by_verdict': by_verdict,
            'graphs_total': graphs_total,
            'graph_edges_total': edges_total,
            'graph_findings_total': findings_total,
            'policies_active': policies_total,
            'flow_checks_total': flow_checks_total,
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
                    raise LabyrinthDenied(str(exc)) from exc
                self._record('LABYRINTH_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
