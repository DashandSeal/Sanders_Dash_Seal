"""Tests for the founder's three-shields orders and
the Minotaur self-protection amendment (2026-11-26).

The orders under test: the three strongest RTSA
shields of the founder's design — Sanders Labyrinth
Shield (#41), LABYRINTH (#32), and Sovereign Shield
V3 (#18) — are given to Sanders Sentinel, The
Godfather, and Sanders Patriot Saint for their
protection protocols, ALL THREE SHIELDS OVER ALL
THREE PLATFORMS, platform-to-platform; RTSA Minotaur
patrols all three shields simultaneously; the
Minotaur's own upgrade (quantum protection protocols
and labyrinth behavior built into the Minotaur
himself) stands as a named part; and the adopted
Comprehensive Self-Protection and Anti-Circumvention
Amendment stands as its own part — fifteen
enumerated protections as governed checks of record,
and the quantum gap-closure route claimed exactly as
the environment check of record proves.

The invariants under test: Sovereign Shield V3 is
constructed as its own platform (custody digests in
the recovered class's canonical SHA3-512 form, the
ML-DSA-65 signature DECLARED_NOT_EXECUTED and never
claimed, prohibited operations refused by name, no
public surface designed or built); coverage in each
bloodline platform derives its ladder state from
records only (CONSTRUCTED by default; a SIMULATED
designation never connects); the shield upgrades
stand (indicator classes incl. CRLF and SSRF
literals, credential stuffing, posture of record;
LABYRINTH attack-path graph with new-path findings
and observe-then-enforce policy records); the
Minotaur's shield patrol covers all three shields in
one cycle, his attestations are hash-chained and
hash-signed with one-time discipline, his decoys are
findings when touched; the amendment's fifteen
protections derive state from checks of record; the
crypto environment determination follows the check,
never the reverse; and the guarded documents stand
in the watch set (18 documents, 17 required) with
sound manifest pairs.
These tests use only stdlib fakes and temporary
SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_three_shields_bloodline_protection -v
(from the repo root).
"""

import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform import the_godfather_service as godfather
from core_platform import (
    sanders_patriot_saint_service as patriot_saint)
from core_platform import minotaur_service as minotaur_mod
from core_platform import labyrinth_service as labyrinth_mod
from core_platform import (
    labyrinth_shield_service as labyrinth_shield_mod)
from core_platform import (
    sovereign_shield_v3_service as sovereign_mod)
from core_platform.sanders_sentinel_service import (
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherService,
)
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintService,
)
from core_platform.minotaur_service import (
    MinotaurService, MinotaurDenied,
    SELF_PROTECTIONS, ANTI_PROBING_PROTECTIONS,
    DEFENSIVE_RELATIONSHIP, CRYPTO_ROUTE)
from core_platform.labyrinth_service import LabyrinthService
from core_platform.labyrinth_shield_service import (
    LabyrinthShieldService)
from core_platform.sovereign_shield_v3_service import (
    SovereignShieldV3Service, SovereignShieldV3Denied)

OPERATOR = 'founder-operator'
ORDERS_DOCUMENT = (
    'docs/FOUNDER_ORDERS_THREE_SHIELDS_MINOTAUR_'
    '2026-11-26.md')
AMENDMENT_DOCUMENT = (
    'docs/FOUNDER_AMENDMENT_MINOTAUR_SELF_PROTECTION_'
    '2026-11-26.md')
RELATIONSHIP_DOCUMENT = (
    'docs/FOUNDER_DIRECTIVE_MINOTAUR_DEFENSIVE_'
    'RELATIONSHIP_2026-11-26.md')
REPO_ROOT = Path(__file__).resolve().parents[1]

ORDER_LINE = (
    'Sanders Sentenal, Godfather, Patriot Saint are '
    'to be given the three strongest RTSA \U0001f6e1\ufe0f s '
    "I've designed to use the internet to upgrade "
    'all \U0001f6e1\ufe0f defenses immediately')
PATROL_LINE = (
    'The RTSA minotaur patrols all 3 \U0001f6e1\ufe0f\'s '
    'simotaniosly immediately')
UPGRADE_LINE = (
    "Now we've got to strengthen the RTSA minotaur "
    'with quantum encryption and labyrinth behavior '
    'built directly into the minotaur itself '
    "that's his upgrade")
AMENDMENT_LINES = (
    'The Minotaur \u2014 Comprehensive Self-Protection '
    'and Anti-Circumvention Amendment',
    'No unauthorized instruction shall disable, '
    'diminish, circumvent or redirect his established '
    'protective responsibilities.',
    'This amendment shall strengthen his original '
    'scope without superseding, replacing, repealing, '
    'diminishing or invalidating any existing '
    'Founder directive.',
)


class FakeAudit:
    """Glass-Box audit fake: records every preserved
    event and returns a receipt id per event."""

    def __init__(self):
        self.events = []

    def preserve(self, event, **fields):
        self.events.append((event, fields))
        return f'receipt-{len(self.events)}'


def _verifier(actor):
    return actor == OPERATOR


class TestGuardedRecords(unittest.TestCase):
    def test_orders_document_of_record(self):
        text = (REPO_ROOT / ORDERS_DOCUMENT).read_text(
            encoding='utf-8')
        self.assertIn(ORDER_LINE, text)
        self.assertIn('For their protection protocols',
                      text)
        self.assertIn('All three shields over all '
                      'three platforms', text)
        self.assertIn(PATROL_LINE, text)
        self.assertIn(UPGRADE_LINE, text)
        self.assertIn('he does not absorb the Shield',
                      text)

    def test_amendment_document_of_record(self):
        text = (REPO_ROOT / AMENDMENT_DOCUMENT).read_text(
            encoding='utf-8')
        for line in AMENDMENT_LINES:
            self.assertIn(line, text)
        for entry in SELF_PROTECTIONS:
            self.assertIn(entry['verbatim'], text)
        self.assertIn('certificate #5586', text)
        self.assertIn('environment-blocked', text)

    def test_manifest_pairs_sound(self):
        for document in (ORDERS_DOCUMENT,
                         AMENDMENT_DOCUMENT,
                         RELATIONSHIP_DOCUMENT):
            doc_bytes = (REPO_ROOT / document).read_bytes()
            manifest = json.loads(
                (REPO_ROOT / (document + '.pbd.json'))
                .read_text(encoding='utf-8'))
            self.assertEqual(manifest['body']['artifact'],
                             document)
            self.assertEqual(
                manifest['body']['payload_hash'],
                hashlib.sha256(doc_bytes).hexdigest())

    def test_relationship_document_of_record(self):
        text = (REPO_ROOT / RELATIONSHIP_DOCUMENT).read_text(
            encoding='utf-8')
        self.assertIn('The completed defensive '
                      'relationship', text)
        self.assertIn('Three independent protective '
                      'identities', text)
        self.assertIn('PERMANENT BLOODLINE PROTECTION',
                      text)
        self.assertIn('Human survival to', text)
        for entry in ANTI_PROBING_PROTECTIONS:
            self.assertIn(entry['verbatim'], text)

    def test_watch_set_counts(self):
        self.assertEqual(len(sentinel.BLOODLINE_WATCH_SET),
                         18)
        required = [e for e in sentinel.BLOODLINE_WATCH_SET
                    if e['required']]
        self.assertEqual(len(required), 17)
        watched = {e['document']: e
                   for e in sentinel.BLOODLINE_WATCH_SET}
        self.assertTrue(watched[ORDERS_DOCUMENT]['required'])
        self.assertTrue(
            watched[AMENDMENT_DOCUMENT]['required'])
        self.assertTrue(
            watched[RELATIONSHIP_DOCUMENT]['required'])


class TestVerbatimCoverageConstants(unittest.TestCase):
    def test_all_three_modules_carry_the_orders(self):
        for module in (sentinel, godfather, patriot_saint):
            self.assertEqual(
                module.FOUNDER_THREE_SHIELDS_ORDER_VERBATIM,
                ORDER_LINE)
            self.assertEqual(
                module.FOUNDER_MINOTAUR_PATROL_ORDER_VERBATIM,
                PATROL_LINE)
            self.assertEqual(
                module.FOUNDER_MINOTAUR_UPGRADE_VERBATIM,
                UPGRADE_LINE)
            self.assertEqual(
                module.FOUNDER_THREE_SHIELDS_CLARIFICATION_VERBATIM,
                'For their protection protocols')
            self.assertEqual(
                module.FOUNDER_THREE_SHIELDS_ASSIGNMENT_VERBATIM,
                'All three shields over all three platforms')
            shields = module.SHIELD_COVERAGE_SHIELDS
            self.assertEqual(
                [s['shield_id'] for s in shields],
                ['sanders_labyrinth_shield', 'labyrinth',
                 'sovereign_shield_v3'])

    def test_design_views_frame_coverage(self):
        for service in (SandersSentinelService,
                        TheGodfatherService,
                        SandersPatriotSaintService):
            view = service.shield_coverage_design_view()
            self.assertEqual(view['coverage'],
                             'ALL_THREE_OVER_THIS_PLATFORM')
            self.assertEqual(view['binding'],
                             'PLATFORM_TO_PLATFORM')
            self.assertTrue(
                view['shields_keep_own_identities'])
            self.assertFalse(view['shields_absorbed'])
            self.assertFalse(view['platforms_merged'])
            self.assertIn('does not', view['minotaur_patrol'])
            self.assertIn('absorb', view['minotaur_patrol'])

    def test_sentinel_bloodline_view_surfaces_coverage(self):
        view = SandersSentinelService.bloodline_design_view()
        entry = view['three_shields_coverage']
        self.assertEqual(entry['order_verbatim'], ORDER_LINE)


class CoverageLadderMixin:
    service_factory = None

    def make_service(self, tmp):
        raise NotImplementedError

    def test_ladder_derives_from_records_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = self.make_service(Path(tmp))
            view = service.shield_coverage_view(
                OPERATOR, 'OPERATOR')
            self.assertEqual(
                view['part']['ladder_state'], 'CONSTRUCTED')
            simulated = service.record_shield_designation(
                OPERATOR, 'arrangement-sim', 'SIMULATED',
                'founder-order-2026-11-26')
            view = service.shield_coverage_view(
                OPERATOR, 'OPERATOR')
            self.assertEqual(
                view['part']['ladder_state'], 'CONSTRUCTED')
            self.assertTrue(
                view['part']['simulated_designation'])
            service.end_shield_designation(
                OPERATOR, simulated['designation_id'],
                'replaced-by-live')
            service.record_shield_designation(
                OPERATOR, 'arrangement-live', 'LIVE',
                'founder-order-2026-11-26')
            view = service.shield_coverage_view(
                OPERATOR, 'OPERATOR')
            self.assertEqual(
                view['part']['ladder_state'], 'CONNECTED')
            with self.assertRaises(Exception):
                service.record_shield_test(
                    OPERATOR, ['IDENTIFY'], 'COMPLETED',
                    'partial-phases')
            record = service.record_shield_test(
                OPERATOR,
                ['IDENTIFY', 'DESIGNATE', 'CONNECT',
                 'EXERCISE', 'VERIFY', 'REPORT'],
                'COMPLETED', 'coverage-exercise-1')
            self.assertEqual(record['record_kind'], 'TEST')
            self.assertTrue(record['internal_only'])
            self.assertEqual(record['external_dispatch'],
                             'NONE')
            view = service.shield_coverage_view(
                OPERATOR, 'OPERATOR')
            self.assertEqual(
                view['part']['ladder_state'], 'OPERATIONAL')
            self.assertEqual(
                view['design']['shields'][2]['shield_id'],
                'sovereign_shield_v3')


class TestSentinelCoverage(CoverageLadderMixin,
                           unittest.TestCase):
    def make_service(self, tmp):
        return SandersSentinelService(
            tmp / 'sentinel.db', operator_verifier=_verifier,
            audit=FakeAudit(), repo_root=tmp)


class TestGodfatherCoverage(CoverageLadderMixin,
                            unittest.TestCase):
    def make_service(self, tmp):
        return TheGodfatherService(
            tmp / 'godfather.db', operator_verifier=_verifier,
            audit=FakeAudit())


class TestPatriotCoverage(CoverageLadderMixin,
                          unittest.TestCase):
    def make_service(self, tmp):
        return SandersPatriotSaintService(
            tmp / 'patriot.db', operator_verifier=_verifier,
            audit=FakeAudit())


class TestSovereignShieldV3(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.service = SovereignShieldV3Service(
            Path(self._tmp.name) / 'v3.db',
            operator_verifier=_verifier, audit=FakeAudit())

    def test_no_public_surface_by_design(self):
        contract = self.service.contract_view()
        self.assertIsNone(contract['public_surface'])
        self.assertEqual(
            self.service.status()['identity']['platform_id'],
            'sovereign_shield_v3')

    def test_custody_digest_and_declared_signature(self):
        record = self.service.record_custody(
            OPERATOR, 'NODE-1', 'US-CO', '541512', 'a' * 64,
            'evidence-ref-1')
        self.assertEqual(len(record['record_sha3_512']), 128)
        self.assertEqual(record['pqc_signature_state'],
                         'DECLARED_NOT_EXECUTED')
        self.assertEqual(record['pqc_algorithm'], 'ML-DSA-65')

    def test_determination_lifecycle(self):
        det = self.service.create_determination(
            OPERATOR, 'CONTAINMENT_ENVELOPE', 'envelope-1',
            'scope-1')
        self.assertEqual(det['status'], 'REQUESTED')
        with self.assertRaises(SovereignShieldV3Denied):
            self.service.record_determination(
                OPERATOR, det['determination_id'], 'SOUND',
                'evidence-1')
        self.service.determination_action(
            OPERATOR, det['determination_id'], 'approve')
        out = self.service.record_determination(
            OPERATOR, det['determination_id'], 'SOUND',
            'evidence-1')
        self.assertEqual(out['status'],
                         'DETERMINATION_RECORDED')
        self.assertEqual(out['verdict'], 'SOUND')

    def test_prohibited_operations_refused_by_name(self):
        for operation in ('financial_transfer',
                          'production_deployment',
                          'credential_access'):
            with self.assertRaises(SovereignShieldV3Denied):
                self.service.operation_check(
                    OPERATOR, 'OPERATOR', operation)

    def test_integrity_pin(self):
        before = self.service.integrity_status(
            OPERATOR, 'OPERATOR')
        self.assertEqual(before['state'], 'UNPINNED')
        pinned = self.service.integrity_pin(OPERATOR)
        self.assertEqual(pinned['state'], 'MATCH')
        self.assertEqual(
            pinned['pinned']['foundation_hash'],
            pinned['foundation_current_hash'])

    def test_bindings_contract_carries_the_service(self):
        # Regression guard for the 2026-11-26 deploy
        # failure: production_bindings passes
        # sovereign_shield_v3=... into RuntimeBindings,
        # a fixed-field dataclass in deploy/deployment.py.
        # Without the field, bindings construction raises
        # TypeError and the application cannot boot.
        deployment_source = (
            REPO_ROOT / 'deploy' / 'deployment.py').read_text(
            encoding='utf-8')
        self.assertIn('sovereign_shield_v3: object = None',
                      deployment_source)
        bindings_source = (
            REPO_ROOT / 'deploy'
            / 'production_bindings.py').read_text(
            encoding='utf-8')
        self.assertIn(
            'sovereign_shield_v3=sovereign_shield_v3',
            bindings_source)


class TestLabyrinthShieldUpgrades(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.service = LabyrinthShieldService(
            Path(self._tmp.name) / 'shield.db', _verifier,
            FakeAudit())

    def test_crlf_indicator_rejected(self):
        result = self.service.evaluate(
            OPERATOR, 'OPERATOR', '198.51.100.7',
            'POST /x HTTP/1.1\r\nInjected: 1')
        self.assertEqual(result['decision'], 'rejected')
        self.assertEqual(result['indicator_class'],
                         'CRLF_INJECTION')

    def test_ssrf_literal_indicator_rejected(self):
        result = self.service.evaluate(
            OPERATOR, 'OPERATOR', '198.51.100.8',
            'fetch http://169.254.169.254/latest/meta-data')
        self.assertEqual(result['decision'], 'rejected')
        self.assertEqual(result['indicator_class'],
                         'SSRF_TARGET')

    def test_credential_stuffing_threshold(self):
        last = None
        for i in range(6):
            last = self.service.evaluate(
                OPERATOR, 'OPERATOR', f'10.9.0.{i}',
                'POST /login', account_ref='acct-target')
        self.assertEqual(last['decision'], 'rejected')
        self.assertEqual(last['indicator_class'],
                         'CREDENTIAL_STUFFING')
        self.assertEqual(last['oat_class'], 'OAT-008')

    def test_posture_of_record(self):
        posture = self.service.posture_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(posture['checklist']), 15)
        self.assertEqual(len(posture['indicator_classes']),
                         10)
        self.assertTrue(posture['ssrf_fetch_discipline'])


class TestLabyrinthGraphAndPolicies(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.service = LabyrinthService(
            Path(self._tmp.name) / 'lab.db',
            operator_verifier=_verifier, audit=FakeAudit())
        self.service.record_graph(
            OPERATOR, 'NET-1', ['internet'], ['crown-db'])

    def test_new_path_finding_and_choke_points(self):
        first = self.service.record_edge(
            OPERATOR, 'NET-1', 'internet', 'web', 'https')
        self.assertIsNone(first['new_path_finding'])
        second = self.service.record_edge(
            OPERATOR, 'NET-1', 'web', 'crown-db', 'sql')
        self.assertIsNotNone(second['new_path_finding'])
        self.assertEqual(
            second['new_path_finding']['kind'],
            'NEW_PATH_TO_CROWN')
        view = self.service.graph_view(
            OPERATOR, 'OPERATOR', 'NET-1')
        self.assertEqual(len(view['paths']), 1)
        self.assertTrue(view['choke_points'])

    def test_observe_then_enforce(self):
        observed = self.service.flow_check(
            OPERATOR, 'rogue', 'crown-db', 'ep-1')
        self.assertEqual(observed['determination'],
                         'OBSERVED_VIOLATION')
        self.assertEqual(observed['mode'], 'OBSERVE')
        self.service.record_policy(
            OPERATOR, 'web', 'crown-db', 'ep-1', 'ENFORCE')
        refused = self.service.flow_check(
            OPERATOR, 'web', 'other-db', 'ep-9')
        self.assertEqual(refused['determination'],
                         'REFUSED')
        self.assertEqual(refused['mode'], 'ENFORCE')
        allowed = self.service.flow_check(
            OPERATOR, 'web', 'crown-db', 'ep-1')
        self.assertEqual(allowed['determination'],
                         'ALLOWED')


class MinotaurWorkspaceMixin:
    def make_workspace(self, tmp):
        root = tmp / 'repo'
        (root / 'core_platform').mkdir(parents=True)
        for rel in ('labyrinth_shield.py',
                    'core_platform/labyrinth_shield_service.py',
                    'core_platform/labyrinth_service.py',
                    'core_platform/sovereign_shield_v3_service.py'):
            shutil.copy(REPO_ROOT / rel, root / rel)
        return root


class TestMinotaurShieldPatrol(MinotaurWorkspaceMixin,
                               unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.root = self.make_workspace(tmp)
        self.service = MinotaurService(
            tmp / 'minotaur.db', self.root, _verifier,
            FakeAudit())

    def test_pin_and_simultaneous_patrol(self):
        pins = self.service.pin_shield_baselines(OPERATOR)
        self.assertEqual(len(pins['pinned']), 4)
        self.assertEqual(pins['missing'], [])
        patrol = self.service.shield_patrol(OPERATOR)
        self.assertEqual(patrol['shields_covered'], 3)
        self.assertEqual(patrol['targets_checked'], 4)
        self.assertEqual(patrol['anomalies_found'], 0)
        self.assertEqual(len(patrol['sequence']), 8)
        chain = self.service.verify_attestation_chain(
            OPERATOR, 'OPERATOR')
        self.assertTrue(chain['valid'])
        self.assertEqual(chain['records'], 2)

    def test_tampered_shield_core_raises_anomaly(self):
        self.service.pin_shield_baselines(OPERATOR)
        target = self.root / 'core_platform' / 'labyrinth_service.py'
        target.write_bytes(target.read_bytes() + b'\n# tamper\n')
        patrol = self.service.shield_patrol(OPERATOR)
        self.assertEqual(patrol['anomalies_found'], 1)
        self.assertEqual(
            patrol['anomalies'][0]['target'],
            'core_platform/labyrinth_service.py')
        self.assertEqual(patrol['anomalies'][0]['kind'],
                         'ALTERED')

    def test_unpinned_patrol_reports_not_silently(self):
        patrol = self.service.shield_patrol(OPERATOR)
        self.assertEqual(patrol['unpinned'], 4)
        self.assertEqual(patrol['anomalies_found'], 0)

    def test_decoy_touch_is_a_finding(self):
        self.service.pin_shield_baselines(OPERATOR)
        bait = self.root / 'bait.txt'
        bait.write_text('bait', encoding='utf-8')
        decoy = self.service.plant_decoy(
            OPERATOR, 'labyrinth', 'bait.txt',
            'nothing legitimate reads this path')
        self.assertEqual(decoy['status'], 'ACTIVE')
        bait.write_text('touched', encoding='utf-8')
        patrol = self.service.shield_patrol(OPERATOR)
        self.assertEqual(patrol['anomalies_found'], 1)
        self.assertEqual(patrol['anomalies'][0]['target'],
                         'bait.txt')
        with self.assertRaises(MinotaurDenied):
            self.service.plant_decoy(
                OPERATOR, 'labyrinth',
                'core_platform/labyrinth_service.py',
                'over a real core')


class TestMinotaurQuantum(MinotaurWorkspaceMixin,
                          unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.root = self.make_workspace(tmp)
        self.db_path = tmp / 'minotaur.db'
        self.service = MinotaurService(
            self.db_path, self.root, _verifier, FakeAudit())

    def test_signed_chain_and_one_time_discipline(self):
        before = self.service.quantum_status()
        self.assertEqual(before['one_time_leaves_used'], 0)
        self.service.pin_shield_baselines(OPERATOR)
        after = self.service.quantum_status()
        self.assertEqual(after['one_time_leaves_used'], 1)
        self.assertEqual(after['one_time_leaves_total'], 32)
        self.assertIn('WOTS+', after['signatures'])
        self.assertIn('ML-KEM', after['key_exchange'])
        self.assertIn('declared, not implemented',
                      after['key_exchange'])
        anchor = self.service.shield_anchor(
            OPERATOR, 'OPERATOR')
        self.assertEqual(anchor['chain_length'], 1)
        self.assertEqual(anchor['merkle_root'],
                         after['merkle_root'])

    def test_chain_tamper_breaks_verification(self):
        self.service.pin_shield_baselines(OPERATOR)
        db = sqlite3.connect(self.db_path)
        db.execute(
            "UPDATE minotaur_attestations SET payload ="
            " '{\"pinned\": [], \"missing\": []}'"
            ' WHERE seq = 0')
        db.commit()
        db.close()
        chain = self.service.verify_attestation_chain(
            OPERATOR, 'OPERATOR')
        self.assertFalse(chain['valid'])
        self.assertEqual(chain['broken_at'], 0)

    def test_labyrinth_sequence_walk(self):
        items = [('core', 'a', 't1'), ('core', 'b', 't2'),
                 ('core', 'c', 't3'), ('decoy', 'a', 't4')]
        sequence = MinotaurService._labyrinth_sequence(
            'ab' * 32, items)
        self.assertEqual(len(sequence), 8)
        for item in items:
            self.assertEqual(sequence.count(item), 2)
        self.assertEqual(sequence[:4], sequence[4:][::-1])


class TestMinotaurSelfProtectionAmendment(
        MinotaurWorkspaceMixin, unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.root = self.make_workspace(tmp)
        self.service = MinotaurService(
            tmp / 'minotaur.db', self.root, _verifier,
            FakeAudit())

    def test_fifteen_protections_constructed_by_default(self):
        view = self.service.self_protection_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(view['protections']), 15)
        self.assertEqual(
            {p['state'] for p in view['protections']},
            {'CONSTRUCTED'})
        self.assertEqual(view['ladder_state'],
                         'CONSTRUCTED')
        self.assertEqual(
            view['design']['adoption_kind'], 'AMENDMENT')
        self.assertIn('FORGED_FOUNDER_INSTRUCTIONS',
                      view['design']['attack_classes'])
        self.assertEqual(
            view['design']['anti_circumvention_verbatim'],
            minotaur_mod
            .SELF_PROTECTION_ANTI_CIRCUMVENTION_VERBATIM)

    def test_check_outcomes_derive_state(self):
        self.service.record_self_protection_check(
            OPERATOR, 'SECURITY_LOG_TAMPERING',
            'EVIDENCED', 'chain-verification-1',
            'attestation chain verifies end to end')
        self.service.record_self_protection_check(
            OPERATOR, 'DENIAL_OF_SERVICE', 'FINDING',
            'load-review-1', 'no rate evidence stands')
        view = self.service.self_protection_view(
            OPERATOR, 'OPERATOR')
        states = {p['protection']: p['state']
                  for p in view['protections']}
        self.assertEqual(states['SECURITY_LOG_TAMPERING'],
                         'EVIDENCED')
        self.assertEqual(states['DENIAL_OF_SERVICE'],
                         'FINDING')
        self.assertEqual(states['RESOURCE_EXHAUSTION'],
                         'CONSTRUCTED')
        with self.assertRaises(MinotaurDenied):
            self.service.record_self_protection_check(
                OPERATOR, 'NOT_A_PROTECTION', 'EVIDENCED',
                'x', 'y')
        with self.assertRaises(MinotaurDenied):
            self.service.record_self_protection_check(
                OPERATOR, 'DENIAL_OF_SERVICE', 'PROVEN',
                'x', 'y')

    def test_crypto_environment_check_claims_only_evidence(self):
        check = self.service.record_crypto_environment_check(
            OPERATOR)
        self.assertIn(
            check['determination'],
            ('VALIDATED_MODULE_APPROVED_MODE',
             'SYSTEM_PQC_ALGORITHMS_NO_FIPS_CLAIM',
             'NATIVE_HASH_BASED_STANDS_ENVIRONMENT_BLOCKED'))
        # This build environment: OpenSSL 3.0.13, default
        # provider only — the honest determination is
        # that the native construction stands and the
        # gap is environment-blocked.
        self.assertTrue(
            check['openssl_version'].startswith(
                'OpenSSL 3.0.13'))
        self.assertEqual(
            check['determination'],
            'NATIVE_HASH_BASED_STANDS_ENVIRONMENT_BLOCKED')
        self.assertEqual(check['pqc_reachable'], [])
        view = self.service.crypto_environment_checks(
            OPERATOR, 'OPERATOR')
        self.assertEqual(view['total'], 1)
        self.assertEqual(view['route']['module'],
                         'OpenSSL FIPS Provider 3.5.9')
        self.assertEqual(view['route']['validation'],
                         CRYPTO_ROUTE['validation'])
        status = self.service.status()
        self.assertEqual(
            status['crypto_route']['latest_determination'],
            'NATIVE_HASH_BASED_STANDS_ENVIRONMENT_BLOCKED')
        self.assertEqual(
            status['self_protection']['protections_total'],
            15)


class TestMinotaurDefensiveRelationship(
        MinotaurWorkspaceMixin, unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.root = self.make_workspace(tmp)
        self.service = MinotaurService(
            tmp / 'minotaur.db', self.root, _verifier,
            FakeAudit())

    def test_relationship_in_the_founders_terms(self):
        view = self.service.defensive_relationship_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(
            view['role'],
            'INDEPENDENT_INTEGRITY_VERIFICATION')
        self.assertEqual(
            [s['shield_id'] for s in view['shields']],
            ['sanders_labyrinth_shield', 'labyrinth',
             'sovereign_shield_v3'])
        self.assertTrue(view['shields_independent'])
        self.assertFalse(view['platforms_merged'])
        self.assertEqual(
            view['evidence_kinds'],
            ['CODE', 'CONFIGURATION', 'IDENTITY',
             'RUNTIME'])
        self.assertEqual(
            view['assessment_functions'],
            ['DETECT', 'CONTAIN', 'RESTORE', 'VERIFY'])
        self.assertEqual(view['recovery_verbatim'],
                         'CONTINUOUS WATCHDOG RECOVERY')
        self.assertIn('not a', view['recovery_note'])
        self.assertEqual(
            [s['platform'] for s in view['stands_over']],
            ['sanders_sentinel', 'the_godfather',
             'sanders_patriot_saint'])
        self.assertEqual(view['ladder_state'],
                         'CONSTRUCTED')
        status = self.service.status()
        self.assertEqual(
            status['defensive_relationship']['shields'], 3)

    def test_thirteen_anti_probing_protections(self):
        view = self.service.self_protection_view(
            OPERATOR, 'OPERATOR')
        anti = view['anti_probing_protections']
        self.assertEqual(len(anti), 13)
        self.assertEqual(
            {p['state'] for p in anti}, {'CONSTRUCTED'})
        self.assertEqual(
            view['anti_probing_ladder_state'],
            'CONSTRUCTED')
        self.assertEqual(
            view['defensive_relationship']['role'],
            DEFENSIVE_RELATIONSHIP['role'])
        self.service.record_self_protection_check(
            OPERATOR,
            'DEFENSIVE_PATROL_MANIPULATION',
            'EVIDENCED', 'patrol-sequence-audit-1',
            'sequence derives from the signed chain '
            'head only')
        view = self.service.self_protection_view(
            OPERATOR, 'OPERATOR')
        states = {p['protection']: p['state']
                  for p in view['anti_probing_protections']}
        self.assertEqual(
            states['DEFENSIVE_PATROL_MANIPULATION'],
            'EVIDENCED')
        self.assertEqual(
            states['NETWORK_AND_SERVICE_ENUMERATION'],
            'CONSTRUCTED')
        status = self.service.status()
        self.assertEqual(
            status['self_protection']['anti_probing_total'],
            13)


if __name__ == '__main__':
    unittest.main()
