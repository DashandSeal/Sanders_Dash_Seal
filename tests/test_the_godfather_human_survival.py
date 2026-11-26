"""Tests for The Godfather -- Human Survival, Mobility
and Essential Resource Protection architecture
(founder-adopted 2026-11-26) and its corrected
directive, adopted the same morning as an AMENDMENT to
The Godfather's original scope (founder ruling
2026-11-26: adoptions amend the original scope, they
never supersede it).

The hard invariants under test: the Human Survival
record stands governing and intact and the corrected
directive stands as its amendment -- nothing is
superseded; the eight domains, the evacuation kinds,
the essential resource kinds, the nine logistics
functions, the ten movement capabilities, the five
lifespan stages, and the seven anticipation kinds are
carried as adopted; per-part ladder states (nine
parts: the seven of the original scope and the
amendment's two) are derived from designation and
test records only and gate nothing (a SIMULATED
designation never connects; OPERATIONAL requires an
ACTIVE LIVE designation AND a completed end-to-end
test); a delivery stands only on verified receipt;
an anticipation record gates no emergency action;
Article V communications records carry the privacy
guard as an invariant (no interception, no
unauthorized tracking, no access to private
communications; the member retains control); Article
VI execution records stand on a joint funding
determination of record and execute no payment,
disburse nothing, and attach no rail; prescription
fulfillment stands only through an authorized
pharmacy named by reference; this construction
connects nothing external, creates no money
authority, and leaves Patriot Saint's disbursement
code, Bozly, and Sanders Sentinel's escalation path
untouched; the three platforms are never merged --
coordination is by reference only.
These tests use only stdlib fakes and temporary
SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_the_godfather_human_survival -v
(from the repo root).
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform import the_godfather_service as godfather
from core_platform.the_godfather_service import (
    TheGodfatherDenied,
    TheGodfatherForbidden,
    TheGodfatherService,
)

OPERATOR = 'founder-operator'
OTHER = 'someone-else'
HS_DOCUMENT = ('docs/THE_GODFATHER_HUMAN_SURVIVAL_'
               '2026-11-26.md')
CD_DOCUMENT = ('docs/THE_GODFATHER_UNIVERSAL_HUMAN_'
               'SURVIVAL_2026-11-26.md')
REPO_ROOT = Path(__file__).resolve().parents[1]
ALL_PHASES = list(godfather.HS_TEST_PHASES)


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


class GodfatherHsTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.audit = FakeAudit()
        self.godfather = TheGodfatherService(
            self.root / 'the_godfather.db',
            operator_verifier=_verifier, audit=self.audit)

    def part_state(self, part_key):
        view = self.godfather.human_survival_view(
            OPERATOR, 'OPERATOR')
        return {entry['part']: entry
                for entry in view['parts']}[part_key]

    def board(self):
        return self.godfather.human_survival_view(
            OPERATOR, 'OPERATOR')


class TestArchitectureOfRecord(GodfatherHsTestBase):
    def test_adoption_carried_verbatim(self):
        self.assertEqual(
            godfather.HS_ADOPTION_VERBATIM,
            'Adopt the Godfather Human Survival '
            'architecture as his construction program')
        self.assertEqual(godfather.HS_ADOPTED,
                         '2026-11-26')

    def test_directive_carried_verbatim(self):
        text = godfather.FOUNDER_HS_DIRECTIVE_VERBATIM
        self.assertIn(
            'The Godfather shall be designed to '
            'facilitate the acquisition, provision, '
            'coordination, maintenance, replacement and '
            'replenishment of transportation and '
            'essential resources', text)
        self.assertIn(
            'Designed \u2192 Constructed \u2192 Connected '
            '\u2192 Tested \u2192 Operational.', text)
        self.assertIn('Human Survival By Design.', text)

    def test_objective_carried(self):
        self.assertEqual(
            godfather.HS_OBJECTIVE,
            'The objective is not simply to locate what '
            'your bloodline needs. It is to help ensure '
            'they actually receive it.')

    def test_eight_domains_of_record(self):
        self.assertEqual(
            [entry['domain'] for entry
             in godfather.HS_DOMAINS],
            ['TRANSPORTATION', 'HOUSING_AND_SHELTER',
             'MEDICAL_RESOURCES', 'ESSENTIAL_RESOURCES',
             'GLOBAL_PROCUREMENT',
             'FINANCIAL_COORDINATION',
             'EMERGENCY_EVACUATION',
             'PREDICTIVE_LOGISTICS'])

    def test_evacuation_kind_map(self):
        mapping = {entry['evacuation']:
                   list(entry['matter_kinds'])
                   for entry
                   in godfather.HS_EVACUATION_KIND_MAP}
        self.assertEqual(
            mapping['MEDICAL_REPATRIATION'],
            ['MEDICAL_TRANSPORTATION',
             'REPATRIATION_ARRANGEMENT'])
        for kind in ('FAMILY_REUNIFICATION',
                     'ACCESSIBLE_EVACUATION',
                     'CONFLICT_DISASTER_EVACUATION',
                     'RETURN_TRANSPORTATION'):
            self.assertEqual(mapping[kind], [kind])

    def test_matter_kinds_twenty_with_hs_tail(self):
        self.assertEqual(
            len(godfather.TRANSPORT_MATTER_KINDS), 20)
        self.assertEqual(
            tuple(godfather.TRANSPORT_MATTER_KINDS[-5:]),
            godfather.HS_MATTER_KINDS)
        self.assertIn('EMERGENCY_SHELTER_ACQUISITION',
                      godfather.TRANSPORT_MATTER_KINDS)

    def test_registers_of_record(self):
        self.assertEqual(
            len(godfather.HS_ESSENTIAL_RESOURCE_KINDS), 8)
        self.assertEqual(
            len(godfather.HS_LOGISTICS_FUNCTIONS), 9)
        self.assertEqual(
            len(godfather.HS_MOVEMENT_CAPABILITIES), 10)
        self.assertEqual(
            len(godfather.HS_LIFESPAN_STAGES), 5)
        self.assertEqual(
            len(godfather.HS_ANTICIPATION_KINDS), 7)

    def test_three_platform_roles_verbatim(self):
        text = (godfather
                .FOUNDER_HS_THREE_PLATFORM_ROLES_VERBATIM)
        self.assertIn('Sanders Sentinel', text)
        self.assertIn('The Godfather', text)
        self.assertIn('Patriot Saint', text)


class TestGuardedRecords(unittest.TestCase):
    def test_both_documents_watched_and_required(self):
        entries = {entry['document']: entry for entry
                   in sentinel.BLOODLINE_WATCH_SET}
        self.assertTrue(entries[HS_DOCUMENT]['required'])
        self.assertTrue(entries[CD_DOCUMENT]['required'])
        self.assertEqual(
            len(sentinel.BLOODLINE_WATCH_SET), 21)
        self.assertEqual(
            len([entry for entry
                 in sentinel.BLOODLINE_WATCH_SET
                 if entry['required']]), 20)

    def test_hs_document_of_record(self):
        text = (REPO_ROOT / HS_DOCUMENT).read_text(
            encoding='utf-8')
        self.assertIn(
            'Adopt the Godfather Human Survival '
            'architecture as his construction program',
            text)
        self.assertIn('governing and intact', text)

    def test_cd_document_is_amendment_record(self):
        text = (REPO_ROOT / CD_DOCUMENT).read_text(
            encoding='utf-8')
        self.assertIn('AMENDMENT', text)
        self.assertIn('supersedes nothing', text)
        self.assertIn(
            'amend the original scope never supercede '
            'them', text)
        self.assertIn(
            'interception_authorized False', text)

    def test_manifest_pairs_sound_for_both_documents(self):
        for document in (HS_DOCUMENT, CD_DOCUMENT):
            doc_bytes = (REPO_ROOT / document).read_bytes()
            manifest = json.loads(
                (REPO_ROOT / (document + '.pbd.json'))
                .read_text(encoding='utf-8'))
            self.assertEqual(
                manifest['body']['artifact'], document)
            self.assertEqual(
                manifest['body']['payload_hash'],
                hashlib.sha256(doc_bytes).hexdigest())


class TestCorrectedDirectiveOfRecord(GodfatherHsTestBase):
    def test_amendment_statement(self):
        self.assertIn('AMENDMENT', godfather.CD_AMENDS)
        self.assertIn('remains governing and',
                      godfather.CD_AMENDS)
        self.assertIn('never supersede it',
                      godfather.CD_AMENDS)

    def test_design_view_amendment(self):
        design = (TheGodfatherService
                  .human_survival_design_view())
        amendment = design['corrected_directive']
        self.assertTrue(amendment['amendment'])
        self.assertNotIn('supersedes', amendment)
        self.assertNotIn('governing', amendment)
        self.assertEqual(len(amendment['articles']), 11)
        self.assertEqual(
            amendment['objective'], godfather.CD_OBJECTIVE)
        self.assertEqual(
            amendment['foundation_not_ceiling'],
            godfather.CD_FOUNDATION_NOT_CEILING)
        self.assertFalse(amendment['executes_payment'])
        self.assertFalse(amendment['rail_attached'])
        self.assertFalse(amendment['carrier_connected'])

    def test_articles_of_record(self):
        self.assertEqual(
            [name for _, name in godfather.CD_ARTICLES],
            ['TRANSPORTATION_AND_MOBILITY',
             'HOUSING_AND_ACCOMMODATION',
             'HUMAN_RESOURCES_AND_DAILY_LIVING',
             'MEDICAL_RESOURCES_AND_CONTINUITY',
             'UNIVERSAL_COMMUNICATIONS',
             'GLOBAL_PROCUREMENT_AND_LOGISTICS',
             'FINANCIAL_RESPONSIBILITIES',
             'PREDICTIVE_ASSISTANCE_AND_PREVENTION',
             'UNIVERSAL_BLOODLINE_APPLICATION',
             'PERMANENT_PRESERVATION',
             'FUNDAMENTAL_OPERATIONAL_OBJECTIVE'])

    def test_privacy_guards_of_record(self):
        self.assertEqual(
            godfather.CD_PRIVACY_GUARDS,
            ('NO_INTERCEPTION',
             'NO_UNAUTHORIZED_TRACKING',
             'NO_ACCESS_TO_PRIVATE_COMMUNICATIONS',
             'MEMBER_RETAINS_CONTROL_OF_OWN_'
             'COMMUNICATIONS_AND_ACCOUNTS'))

    def test_nine_parts_of_record(self):
        self.assertEqual(
            [entry['part'] for entry in godfather.HS_PARTS],
            ['ARCHITECTURE_STATEMENT', 'EIGHT_DOMAINS',
             'LOGISTICS_MACHINERY',
             'INTERNATIONAL_MOVEMENT',
             'LIFESPAN_CONTINUITY',
             'PREDICTIVE_LOGISTICS', 'LADDER_REPORTING',
             'UNIVERSAL_COMMUNICATIONS',
             'PURCHASING_RESERVATION_EXECUTION'])


class TestMachinery(GodfatherHsTestBase):
    def test_open_each_new_matter_kind(self):
        for kind in godfather.HS_MATTER_KINDS:
            matter = self.godfather.open_transport_matter(
                OPERATOR, kind, 'member-ref', 'detail-ref')
            self.assertEqual(matter['matter_kind'], kind)
            self.assertEqual(matter['status'],
                             'AWAITING_HUMAN_REVIEW')

    def test_delivery_verification_requires_reference(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_logistics_record(
                OPERATOR, 'DELIVERY_VERIFICATION',
                'subject-ref', 'detail-ref')
        record = self.godfather.record_logistics_record(
            OPERATOR, 'DELIVERY_VERIFICATION',
            'subject-ref', 'detail-ref',
            delivery_ref='delivery-ref')
        self.assertTrue(record['delivery_verified'])

    def test_movement_lost_documentation_names_patriot_saint(
            self):
        record = self.godfather.record_movement_record(
            OPERATOR, 'LOST_DOCUMENTATION_ASSISTANCE',
            'member-ref', 'detail-ref',
            counterpart_ref='authority-ref')
        self.assertEqual(record['counterpart_platform'],
                         'sanders_patriot_saint')

    def test_anticipation_gates_nothing(self):
        record = self.godfather.record_anticipation_record(
            OPERATOR, 'ESSENTIAL_SUPPLY_DEPLETION',
            'subject-ref', 'detail-ref')
        self.assertFalse(record['gates_emergency_action'])
        self.assertTrue(record['within_assigned_authority'])

    def test_records_require_operator(self):
        with self.assertRaises(TheGodfatherForbidden):
            self.godfather.record_logistics_record(
                OTHER, 'INVENTORY_MANAGEMENT',
                'subject-ref', 'detail-ref')


class TestCommunicationsRecords(GodfatherHsTestBase):
    def test_record_carries_privacy_guard(self):
        record = (self.godfather
                  .record_communications_record(
                      OPERATOR, 'SIM_ESIM_COORDINATION',
                      'member-ref', 'detail-ref'))
        self.assertFalse(record['interception_authorized'])
        self.assertFalse(record['tracking_authorized'])
        self.assertFalse(
            record['private_communications_access_'
                   'authorized'])
        self.assertTrue(
            record['member_controls_own_communications'])
        self.assertFalse(record['carrier_connected'])
        self.assertFalse(record['service_connected'])
        self.assertEqual(record['privacy_guards'],
                         list(godfather.CD_PRIVACY_GUARDS))

    def test_all_seventeen_kinds_recordable(self):
        self.assertEqual(
            len(godfather.HS_COMMUNICATIONS_RECORD_KINDS),
            17)
        for kind in godfather.HS_COMMUNICATIONS_RECORD_KINDS:
            record = (self.godfather
                      .record_communications_record(
                          OPERATOR, kind, 'member-ref',
                          'detail-ref'))
            self.assertEqual(record['record_kind'], kind)
        self.assertEqual(
            len(self.godfather.communications_records(
                OPERATOR, 'OPERATOR')), 17)

    def test_unknown_kind_denied(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_communications_record(
                OPERATOR, 'WIRETAP', 'member-ref',
                'detail-ref')


class TestExecutionRecords(GodfatherHsTestBase):
    def test_funding_reference_required(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_execution_record(
                OPERATOR, 'PURCHASE_EXECUTION',
                'subject-ref', 'detail-ref', funding_ref='')

    def test_execution_executes_no_payment(self):
        record = self.godfather.record_execution_record(
            OPERATOR, 'RESERVATION_EXECUTION',
            'subject-ref', 'detail-ref',
            funding_ref='joint-determination-ref')
        self.assertFalse(record['executes_payment'])
        self.assertFalse(record['funds_disbursed'])
        self.assertFalse(record['rail_attached'])
        self.assertFalse(record['delivery_verified'])
        record = self.godfather.record_execution_record(
            OPERATOR, 'PURCHASE_EXECUTION', 'subject-ref',
            'detail-ref',
            funding_ref='joint-determination-ref',
            delivery_ref='delivery-ref')
        self.assertTrue(record['delivery_verified'])


class TestResourceRecords(GodfatherHsTestBase):
    def test_prescription_requires_authorized_pharmacy(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_resource_record(
                OPERATOR, 'PRESCRIPTION_FULFILLMENT',
                'member-ref', 'detail-ref')
        record = self.godfather.record_resource_record(
            OPERATOR, 'PRESCRIPTION_FULFILLMENT',
            'member-ref', 'detail-ref',
            provider_ref='authorized-pharmacy-ref')
        self.assertFalse(record['provider_connected'])

    def test_thirteen_kinds_of_record(self):
        self.assertEqual(len(godfather.HS_RESOURCE_KINDS),
                         13)
        for kind in ('PERMANENT_HOUSING_ASSISTANCE',
                     'UTILITY_COORDINATION',
                     'HOUSEHOLD_FURNISHINGS',
                     'EDUCATIONAL_RESOURCES',
                     'EMPLOYMENT_RESOURCES',
                     'OXYGEN_EQUIPMENT', 'HOSPITAL_BED',
                     'TEMPERATURE_CONTROLLED_TRANSPORT',
                     'TEMPERATURE_CONTROLLED_STORAGE',
                     'MEDICAL_BACKUP_POWER'):
            record = self.godfather.record_resource_record(
                OPERATOR, kind, 'member-ref', 'detail-ref')
            self.assertEqual(record['resource_kind'], kind)


class TestLadder(GodfatherHsTestBase):
    def test_all_parts_constructed_at_open(self):
        board = self.board()
        self.assertEqual(len(board['parts']), 9)
        for entry in board['parts']:
            self.assertEqual(entry['ladder_state'],
                             'CONSTRUCTED')
            self.assertTrue(entry['reporting_only'])
            self.assertTrue(entry['gates_nothing'])
        self.assertEqual(board['parts_operational'], [])

    def test_simulated_designation_never_connects(self):
        self.godfather.record_hs_designation(
            OPERATOR, 'UNIVERSAL_COMMUNICATIONS',
            'carrier-ref', 'SIMULATED', 'auth-ref')
        entry = self.part_state('UNIVERSAL_COMMUNICATIONS')
        self.assertEqual(entry['ladder_state'],
                         'CONSTRUCTED')
        self.assertTrue(entry['simulated_designation'])

    def test_tested_then_operational(self):
        self.godfather.record_hs_test(
            OPERATOR, 'PURCHASING_RESERVATION_EXECUTION',
            ALL_PHASES, 'COMPLETED', 'test-detail-ref')
        self.assertEqual(
            self.part_state(
                'PURCHASING_RESERVATION_EXECUTION')
            ['ladder_state'], 'TESTED')
        self.godfather.record_hs_designation(
            OPERATOR, 'PURCHASING_RESERVATION_EXECUTION',
            'arrangement-ref', 'LIVE', 'auth-ref')
        self.assertEqual(
            self.part_state(
                'PURCHASING_RESERVATION_EXECUTION')
            ['ladder_state'], 'OPERATIONAL')

    def test_ended_designation_drops_state(self):
        designation = self.godfather.record_hs_designation(
            OPERATOR, 'LOGISTICS_MACHINERY',
            'warehouse-ref', 'LIVE', 'auth-ref')
        self.godfather.record_hs_test(
            OPERATOR, 'LOGISTICS_MACHINERY', ALL_PHASES,
            'COMPLETED', 'test-detail-ref')
        self.assertEqual(
            self.part_state('LOGISTICS_MACHINERY')
            ['ladder_state'], 'OPERATIONAL')
        self.godfather.end_hs_designation(
            OPERATOR, designation['designation_id'],
            'end-detail-ref')
        self.assertEqual(
            self.part_state('LOGISTICS_MACHINERY')
            ['ladder_state'], 'TESTED')

    def test_incomplete_test_never_completes(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_hs_test(
                OPERATOR, 'LOGISTICS_MACHINERY',
                ALL_PHASES[:-1], 'COMPLETED',
                'test-detail-ref')

    def test_status_mirrors_board(self):
        self.godfather.record_communications_record(
            OPERATOR, 'BACKUP_POWER', 'member-ref',
            'detail-ref')
        status = self.godfather.status()
        board = self.board()
        self.assertEqual(
            status['human_survival']
            ['communications_records_total'], 1)
        self.assertEqual(
            board['communications_records_total'], 1)
        self.assertEqual(
            status['human_survival']['parts']
            ['UNIVERSAL_COMMUNICATIONS'], 'CONSTRUCTED')
        self.assertFalse(
            status['human_survival']['funds_disbursed'])
        self.assertFalse(
            status['human_survival']['funds_held'])


class TestInvariants(GodfatherHsTestBase):
    def test_disburse_refused_by_name(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.disburse_funds(OPERATOR)

    def test_record_operations_include_new_operations(self):
        for operation in ('record_communications_record',
                          'record_execution_record',
                          'record_resource_record'):
            self.assertIn(operation,
                          godfather.RECORD_OPERATIONS)

    def test_design_view_no_connection_no_funds(self):
        design = (TheGodfatherService
                  .human_survival_design_view())
        self.assertEqual(design['external_connections'],
                         'NONE')
        self.assertFalse(design['funds_disbursed'])
        self.assertFalse(design['funds_held'])


if __name__ == '__main__':
    unittest.main()
