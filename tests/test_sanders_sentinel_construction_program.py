"""Tests for the Sanders Sentinel -- Construction
Program (founder-adopted, 2026-11-26): emergency-
capability items 39-56 and the eight construction
priorities of the founder-presented assessment the
founder adopted as Sentinel's construction program.

The hard invariants under test: the truthful-
verification ladder is derived from records and
settable by no one (a SIMULATED designation never
connects; OPERATIONAL requires an ACTIVE LIVE
designation AND a completed end-to-end program
test); this construction connects nothing external
(item 52's satellite state stands NOT_CONNECTED
until designated); items 43 and 44 coordinate to
qualified human professionals only -- Sentinel
never treats; item 45 rests on an evidence
reference of record; a family notification is born
UNDELIVERED and is never represented as sent; a
deaf or hard-of-hearing notification refuses the
VOICE channel by name; recovery assistance belongs
only to a case closed CLOSED_RESOLVED; program
states gate nothing (an activation proceeds with
every item merely CONSTRUCTED); and the program
never touches the readiness board, the escalation
path, or any money authority. These tests use only
stdlib fakes and temporary SQLite files: no
network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_construction_program -v
(from the repo root).
"""

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform import the_godfather_service as godfather
from core_platform.sanders_sentinel_service import (
    SandersSentinelDenied,
    SandersSentinelForbidden,
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherService,
)
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintService,
)

OPERATOR = 'founder-operator'
OTHER = 'someone-else'
PROGRAM_DOCUMENT = ('docs/SANDERS_SENTINEL_'
                    'CONSTRUCTION_PROGRAM_2026-11-26.md')
ALL_STAGES = list(sentinel.OPERATIONAL_SEQUENCE)


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


class ProgramTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.audit = FakeAudit()
        self.now = [1000.0]
        self.sentinel = SandersSentinelService(
            self.root / 'sanders_sentinel.db',
            operator_verifier=_verifier, audit=self.audit,
            clock=lambda: self.now[0])
        self.godfather = TheGodfatherService(
            self.root / 'the_godfather.db',
            operator_verifier=_verifier, audit=self.audit,
            clock=lambda: self.now[0])
        self.patriot = SandersPatriotSaintService(
            self.root / 'sanders_patriot_saint.db',
            operator_verifier=_verifier, audit=self.audit,
            clock=lambda: self.now[0])

    def open_case(self, kind='SOS_BUTTON'):
        source = sentinel.EMERGENCY_SIGNAL_SOURCES[kind]
        return self.sentinel.record_emergency_signal(
            OPERATOR, kind, source, f'source-{kind.lower()}',
            'authorization-of-record', 'bloodline-member-ref',
            'signal-detail-ref')

    def close_case(self, case_id):
        self.sentinel.confirm_emergency_arrival(
            OPERATOR, case_id, 'arrival-ref',
            'assistance arrived and delivered')
        return self.sentinel.close_emergency_case(
            OPERATOR, case_id, 'resolution-ref')

    def item_state(self, item_no):
        view = self.sentinel.construction_program_view(
            OPERATOR, 'OPERATOR')
        return {entry['item']: entry
                for entry in view['items']}[item_no]


class TestProgramOfRecord(ProgramTestBase):
    def test_items_carried_verbatim(self):
        text = (sentinel
                .FOUNDER_CONSTRUCTION_PROGRAM_ITEMS_VERBATIM)
        lines = text.split('\n')
        self.assertEqual(len(lines), 18)
        self.assertEqual(
            lines[0], '39 Emergency shelter acquisition')
        self.assertEqual(
            lines[4],
            '43 Mental health crisis intervention through '
            'qualified professionals')
        self.assertEqual(
            lines[17],
            '56 Post-emergency recovery assistance')
        for number, line in zip(range(39, 57), lines):
            self.assertTrue(line.startswith(f'{number} '))

    def test_priorities_carried_verbatim(self):
        text = (sentinel
                .FOUNDER_CONSTRUCTION_PROGRAM_PRIORITIES_VERBATIM)
        lines = text.split('\n')
        self.assertEqual(len(lines), 8)
        self.assertTrue(lines[0].startswith(
            'Live perception connections'))
        self.assertIn('Receive genuine emergency signals',
                      lines[0])
        self.assertTrue(lines[7].startswith(
            'Operational verification'))
        self.assertIn('genuinely requested, received and '
                      'delivered', lines[7])

    def test_adoption_carried_verbatim(self):
        self.assertEqual(
            sentinel
            .FOUNDER_CONSTRUCTION_PROGRAM_ADOPTION_VERBATIM,
            'Adopt items 39\u201356 and the eight priorities '
            'as Sentinel\u2019s construction program')

    def test_register_matches_the_adopted_items(self):
        design = (SandersSentinelService
                  .construction_program_design_view())
        self.assertEqual(len(design['items']), 18)
        self.assertEqual(len(design['priorities']), 8)
        verbatim_titles = [
            line.split(' ', 1)[1] for line in sentinel
            .FOUNDER_CONSTRUCTION_PROGRAM_ITEMS_VERBATIM
            .split('\n')]
        self.assertEqual(
            [entry['title'] for entry in design['items']],
            verbatim_titles)
        self.assertEqual(
            design['ladder'],
            ['DESIGNED', 'CONSTRUCTED', 'CONNECTED',
             'TESTED', 'OPERATIONAL'])
        self.assertIn('connects nothing external',
                      design['no_connection_invariant'])
        self.assertFalse(design['funds_disbursed'])
        self.assertFalse(design['funds_held'])

    def test_program_in_bloodline_design_view(self):
        design = (SandersSentinelService
                  .bloodline_design_view())
        self.assertIn('sentinel_construction_program',
                      design)
        program = design['sentinel_construction_program']
        self.assertEqual(len(program['items']), 18)


class TestGuardSetWithProgram(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.repo = root / 'repo'
        self.documents = {}
        for entry in sentinel.BLOODLINE_WATCH_SET:
            if not entry['required']:
                continue
            path = self.repo / entry['document']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"Guarded record: {entry['title']}\n",
                encoding='utf-8')
            digest = hashlib.sha256(
                path.read_bytes()).hexdigest()
            manifest = {'body': {
                'schema': 1,
                'platform': 'Sanders Dash & Seal',
                'artifact': entry['document'],
                'payload_hash': digest,
                'scope': 'source-manifest',
                'signatures': {},
                'status': 'UNSIGNED_SOURCE_MANIFEST'}}
            Path(str(path) + '.pbd.json').write_text(
                json.dumps(manifest), encoding='utf-8')
            self.documents[entry['document']] = path
        self.service = SandersSentinelService(
            root / 'sanders_sentinel.db',
            operator_verifier=_verifier, audit=FakeAudit(),
            repo_root=self.repo)

    def test_program_document_watched_and_required(self):
        entry = {e['document']: e
                 for e in sentinel.BLOODLINE_WATCH_SET}[
                     PROGRAM_DOCUMENT]
        self.assertTrue(entry['required'])
        self.assertEqual(len(sentinel.BLOODLINE_WATCH_SET),
                         15)

    def test_clean_cycle_then_tamper_program_document(self):
        required = [entry for entry
                    in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        self.assertEqual(len(required), 14)
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['documents_not_landed'], 1)
        path = self.documents[PROGRAM_DOCUMENT]
        with open(path, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)


class TestLadderDerivation(ProgramTestBase):
    def test_every_item_constructed_at_birth(self):
        view = self.sentinel.construction_program_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(view['items']), 18)
        for entry in view['items']:
            self.assertEqual(entry['ladder_state'],
                             'CONSTRUCTED')
            self.assertTrue(entry['reporting_only'])
            self.assertFalse(entry['gates_activation'])
        self.assertEqual(view['items_operational'], [])
        self.assertEqual(view['external_connections'],
                         'NONE')

    def test_satellite_not_connected_until_designated(self):
        state = self.item_state(52)
        self.assertEqual(state['satellite_state'],
                         'NOT_CONNECTED')
        self.assertIn('satellite',
                      state['designation_required'])

    def test_simulated_designation_never_connects(self):
        self.sentinel.record_program_designation(
            OPERATOR, 52, 'satellite-service-ref',
            'SIMULATED', 'authorization-ref')
        state = self.item_state(52)
        self.assertEqual(state['ladder_state'],
                         'CONSTRUCTED')
        self.assertTrue(state['simulated_designation'])
        self.assertEqual(state['satellite_state'],
                         'NOT_CONNECTED')

    def test_live_designation_connects(self):
        record = self.sentinel.record_program_designation(
            OPERATOR, 54, 'dispatch-channel-ref', 'LIVE',
            'authorization-ref')
        self.assertEqual(record['state'], 'ACTIVE')
        state = self.item_state(54)
        self.assertEqual(state['ladder_state'],
                         'CONNECTED')
        self.assertEqual(state['designation_kind'],
                         'LIVE')

    def test_test_alone_reads_tested(self):
        self.sentinel.record_program_test(
            OPERATOR, 49, ALL_STAGES, 'COMPLETED',
            'test-detail-ref')
        state = self.item_state(49)
        self.assertEqual(state['ladder_state'], 'TESTED')
        self.assertTrue(
            state['end_to_end_test_completed'])

    def test_operational_requires_connection_and_test(self):
        self.sentinel.record_program_designation(
            OPERATOR, 53, 'channel-ref', 'LIVE',
            'authorization-ref')
        self.assertEqual(self.item_state(53)['ladder_state'],
                         'CONNECTED')
        self.sentinel.record_program_test(
            OPERATOR, 53, ALL_STAGES, 'COMPLETED',
            'test-detail-ref')
        self.assertEqual(self.item_state(53)['ladder_state'],
                         'OPERATIONAL')
        view = self.sentinel.construction_program_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(view['items_operational'], [53])

    def test_ending_designation_rederives_state(self):
        designation = self.sentinel.record_program_designation(
            OPERATOR, 53, 'channel-ref', 'LIVE',
            'authorization-ref')
        self.sentinel.record_program_test(
            OPERATOR, 53, ALL_STAGES, 'COMPLETED',
            'test-detail-ref')
        self.assertEqual(self.item_state(53)['ladder_state'],
                         'OPERATIONAL')
        ended = self.sentinel.end_program_designation(
            OPERATOR, designation['designation_id'],
            'designation-withdrawn-ref')
        self.assertEqual(ended['state'], 'ENDED')
        self.assertEqual(self.item_state(53)['ladder_state'],
                         'TESTED')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.end_program_designation(
                OPERATOR, designation['designation_id'],
                'again')

    def test_designation_validation(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_program_designation(
                OPERATOR, 38, 'ref', 'LIVE', 'auth')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_program_designation(
                OPERATOR, 57, 'ref', 'LIVE', 'auth')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_program_designation(
                OPERATOR, 52, 'ref', 'PARTIAL', 'auth')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_program_designation(
                OPERATOR, 52, '', 'LIVE', 'auth')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_program_designation(
                OTHER, 52, 'ref', 'LIVE', 'auth')

    def test_completed_test_requires_full_sequence(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_program_test(
                OPERATOR, 52, ['PERCEIVE'], 'COMPLETED',
                'detail')
        record = self.sentinel.record_program_test(
            OPERATOR, 52, ['PERCEIVE'], 'FAILED',
            'detail')
        self.assertEqual(record['outcome'], 'FAILED')
        self.assertEqual(record['record_kind'], 'TEST')
        self.assertTrue(record['internal_only'])
        self.assertEqual(record['external_dispatch'],
                         'NONE')
        self.assertEqual(self.item_state(52)['ladder_state'],
                         'CONSTRUCTED')

    def test_program_tests_labeled_and_listed(self):
        self.sentinel.record_program_test(
            OPERATOR, 55, ALL_STAGES, 'COMPLETED',
            'detail')
        tests = self.sentinel.program_tests(
            OPERATOR, 'OPERATOR')
        self.assertEqual(tests['record_kind'], 'TEST')
        self.assertEqual(tests['total'], 1)
        self.assertEqual(tests['completed_total'], 1)
        self.assertEqual(tests['tests'][0]['item'], 55)

    def test_program_never_touches_readiness_board(self):
        self.sentinel.record_program_designation(
            OPERATOR, 52, 'ref', 'LIVE', 'auth')
        self.sentinel.record_program_test(
            OPERATOR, 52, ALL_STAGES, 'COMPLETED',
            'detail')
        board = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(
            [entry['capability']
             for entry in board['capabilities']],
            list(sentinel.READINESS_CAPABILITIES))
        self.assertEqual(board['operational_capabilities'],
                         [])
        # The readiness path itself refuses a program
        # capability by name.
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_operational_test(
                OPERATOR, 'PROGRAM_ITEM_52', ALL_STAGES,
                'COMPLETED', 'detail')

    def test_priority_one_carries_channel_states(self):
        view = self.sentinel.construction_program_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(view['priorities']), 8)
        first = view['priorities'][0]
        self.assertEqual(first['title'],
                         'Live perception connections')
        self.assertEqual(
            set(first['perception_channel_states']),
            set(sentinel.PERCEPTION_CHANNELS))
        self.assertEqual(
            set(first['perception_channel_states']
                .values()),
            {'NOT_CONNECTED'})


class TestAssistanceCoordination(ProgramTestBase):
    def test_mental_health_coordination_only(self):
        case = self.open_case()
        record = self.sentinel.record_assistance_coordination(
            OPERATOR, 43,
            'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL',
            'professional-of-record-ref', 'detail-ref',
            case_id=case['case_id'])
        self.assertEqual(record['sentinel_role'],
                         'COORDINATION_ONLY')
        self.assertEqual(record['intervention_by'],
                         'QUALIFIED_HUMAN_PROFESSIONAL')
        self.assertFalse(record['treatment_by_sentinel'])
        self.assertTrue(record['receipt_id'])

    def test_counseling_coordination(self):
        record = self.sentinel.record_assistance_coordination(
            OPERATOR, 44, 'TRAINED_CRISIS_COUNSELOR',
            'counselor-of-record-ref', 'detail-ref')
        self.assertEqual(record['item'], 44)
        self.assertFalse(record['treatment_by_sentinel'])

    def test_wrong_kind_for_item_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_assistance_coordination(
                OPERATOR, 44,
                'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL',
                'ref', 'detail')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_assistance_coordination(
                OPERATOR, 46,
                'ADULT_PROTECTIVE_SERVICES', 'ref',
                'detail')

    def test_items_outside_43_to_46_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_assistance_coordination(
                OPERATOR, 47,
                'VICTIM_ASSISTANCE_ORGANIZATION', 'ref',
                'detail')

    def test_exploitation_requires_evidence_of_record(self):
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_assistance_coordination(
                OPERATOR, 45, 'ADULT_PROTECTIVE_SERVICES',
                'aps-ref', 'detail')
        self.assertIn('evidence', str(ctx.exception))
        record = self.sentinel.record_assistance_coordination(
            OPERATOR, 45,
            'FINANCIAL_INSTITUTION_FRAUD_DEPARTMENT',
            'fraud-department-ref', 'detail',
            evidence_ref='transaction-evidence-ref',
            language='ENGLISH')
        self.assertEqual(record['evidence_ref'],
                         'transaction-evidence-ref')
        self.assertEqual(record['language'], 'ENGLISH')

    def test_identity_theft_coordination(self):
        record = self.sentinel.record_assistance_coordination(
            OPERATOR, 46,
            'VICTIM_ASSISTANCE_ORGANIZATION',
            'victim-assistance-ref', 'detail')
        self.assertEqual(record['item'], 46)

    def test_crisis_coordination_needs_open_case(self):
        case = self.open_case()
        self.close_case(case['case_id'])
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_assistance_coordination(
                OPERATOR, 43,
                'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL',
                'ref', 'detail', case_id=case['case_id'])
        self.assertIn('EMERGENCY_CASE_NOT_OPEN',
                      str(ctx.exception))
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_assistance_coordination(
                OPERATOR, 43,
                'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL',
                'ref', 'detail', case_id='no-such-case')

    def test_coordination_listing(self):
        self.sentinel.record_assistance_coordination(
            OPERATOR, 46,
            'FINANCIAL_INSTITUTION_FRAUD_DEPARTMENT',
            'ref', 'detail')
        listing = self.sentinel.assistance_coordinations(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 1)
        self.assertFalse(listing['treatment_by_sentinel'])
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_assistance_coordination(
                OTHER, 46,
                'FINANCIAL_INSTITUTION_FRAUD_DEPARTMENT',
                'ref', 'detail')


class TestFamilyNotifications(ProgramTestBase):
    def test_notification_born_undelivered(self):
        case = self.open_case()
        record = self.sentinel.record_family_notification(
            OPERATOR, case['case_id'], 'family-ref',
            'TEXT', 'detail-ref')
        self.assertEqual(record['delivery_state'],
                         'UNDELIVERED')
        self.assertIsNone(
            record['delivery_confirmation_ref'])
        delivered = (self.sentinel
                     .confirm_family_notification_delivery(
                         OPERATOR,
                         record['notification_id'],
                         'delivery-confirmation-ref'))
        self.assertEqual(delivered['delivery_state'],
                         'DELIVERED')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_family_notification_delivery(
                OPERATOR, record['notification_id'],
                'again')

    def test_notification_needs_open_case(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_family_notification(
                OPERATOR, 'no-such-case', 'family-ref',
                'TEXT', 'detail')
        case = self.open_case()
        self.close_case(case['case_id'])
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_family_notification(
                OPERATOR, case['case_id'], 'family-ref',
                'TEXT', 'detail')
        self.assertIn('EMERGENCY_CASE_NOT_OPEN',
                      str(ctx.exception))

    def test_deaf_hard_of_hearing_refuses_voice(self):
        case = self.open_case()
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_family_notification(
                OPERATOR, case['case_id'], 'family-ref',
                'VOICE', 'detail',
                accessibility='DEAF_OR_HARD_OF_HEARING')
        self.assertIn('ACCESSIBLE_CHANNEL_REQUIRED',
                      str(ctx.exception))
        for channel in ('TEXT', 'VISUAL', 'SILENT'):
            record = self.sentinel.record_family_notification(
                OPERATOR, case['case_id'], 'family-ref',
                channel, 'detail',
                accessibility='DEAF_OR_HARD_OF_HEARING')
            self.assertEqual(record['channel'], channel)
            self.assertEqual(record['accessibility'],
                             'DEAF_OR_HARD_OF_HEARING')

    def test_language_is_a_recorded_field(self):
        case = self.open_case()
        record = self.sentinel.record_family_notification(
            OPERATOR, case['case_id'], 'family-ref',
            'VOICE', 'detail', language='SPANISH')
        self.assertEqual(record['language'], 'SPANISH')
        self.assertIn(
            'No translation capability',
            sentinel
            .CONSTRUCTION_PROGRAM_LANGUAGE_INVARIANT)

    def test_notification_listing_counts_undelivered(self):
        case = self.open_case()
        self.sentinel.record_family_notification(
            OPERATOR, case['case_id'], 'family-ref',
            'SILENT', 'detail')
        listing = self.sentinel.family_notifications(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 1)
        self.assertEqual(listing['undelivered_total'], 1)
        filtered = self.sentinel.family_notifications(
            OPERATOR, 'OPERATOR', case_id=case['case_id'])
        self.assertEqual(filtered['total'], 1)


class TestRecoveryAssistance(ProgramTestBase):
    def test_recovery_belongs_to_closed_cases(self):
        case = self.open_case()
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_recovery_assistance(
                OPERATOR, case['case_id'],
                'FOLLOW_UP_ASSISTANCE', 'target-ref',
                'detail')
        self.assertIn('CLOSED_RESOLVED',
                      str(ctx.exception))
        self.close_case(case['case_id'])
        record = self.sentinel.record_recovery_assistance(
            OPERATOR, case['case_id'],
            'FOLLOW_UP_ASSISTANCE', 'target-ref',
            'detail', target_platform='the_godfather')
        self.assertEqual(record['state'], 'RECORDED')
        completed = self.sentinel.complete_recovery_assistance(
            OPERATOR, record['assistance_id'],
            'completion-detail-ref')
        self.assertEqual(completed['state'], 'COMPLETED')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.complete_recovery_assistance(
                OPERATOR, record['assistance_id'],
                'again')

    def test_recovery_validation(self):
        case = self.open_case()
        self.close_case(case['case_id'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_recovery_assistance(
                OPERATOR, case['case_id'], 'NEW_KIND',
                'target', 'detail')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_recovery_assistance(
                OPERATOR, case['case_id'],
                'FOLLOW_UP_ASSISTANCE', 'target',
                'detail', target_platform='unknown')
        listing = self.sentinel.recovery_assistance_records(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 0)


class TestCarriedItems(ProgramTestBase):
    def test_shelter_matter_kind_of_record(self):
        self.assertIn('EMERGENCY_SHELTER_ACQUISITION',
                      godfather.TRANSPORT_MATTER_KINDS)
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'EMERGENCY_SHELTER_ACQUISITION',
            'bloodline-member-ref', 'shelter-detail')
        self.assertEqual(matter['status'],
                         'AWAITING_HUMAN_REVIEW')

    def test_relocation_activation_reaches_shelter(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'EMERGENCY_SHELTER_ACQUISITION',
            'bloodline-member-ref', 'shelter-detail')
        case = self.open_case()
        activation = (self.sentinel
                      .record_emergency_activation(
                          OPERATOR, case['case_id'],
                          'RELOCATION',
                          matter['matter_id'],
                          'shelter-detail'))
        self.assertEqual(activation['target_platform'],
                         'the_godfather')
        self.assertEqual(activation['target_ref'],
                         matter['matter_id'])

    def test_relocation_and_legal_kinds_of_record(self):
        for kind in (
                'TRANSPORTATION_PROVISION_DOMESTIC',
                'EMERGENCY_TRANSPORTATION',
                'TRANSPORTATION_PROVISION_INTERNATIONAL',
                'EMERGENCY_EVACUATION_ARRANGEMENT',
                'MEDICAL_TRANSPORTATION',
                'REPATRIATION_ARRANGEMENT'):
            self.assertIn(kind,
                          godfather.TRANSPORT_MATTER_KINDS)
        from core_platform import (
            sanders_patriot_saint_service as patriot)
        for kind in (
                'LEGAL_REPRESENTATION_COORDINATION',
                'EMERGENCY_LEGAL_ASSISTANCE'):
            self.assertIn(kind,
                          patriot.BLOODLINE_MATTER_KINDS)


class TestProgramGatesNothing(ProgramTestBase):
    def test_activation_proceeds_with_all_constructed(self):
        # No designations, no program tests: every item
        # stands CONSTRUCTED, and the emergency paths
        # proceed exactly as before (clarification
        # No. 3, carried into this program).
        case = self.open_case()
        activation = (self.sentinel
                      .record_emergency_activation(
                          OPERATOR, case['case_id'],
                          'RELOCATION', 'matter-ref',
                          'detail'))
        self.assertEqual(activation['activation_kind'],
                         'RELOCATION')
        coordination = (self.sentinel
                        .record_responder_coordination(
                            OPERATOR, case['case_id'],
                            'MEDICAL', 'responder-ref',
                            'detail'))
        self.assertEqual(
            coordination['escalation_authority'], 'NONE')

    def test_protective_paths_never_consult_program(self):
        for name in ('record_emergency_signal',
                     'record_emergency_activation',
                     'record_responder_coordination',
                     'close_emergency_case',
                     'record_emergency_protective_action'):
            source = inspect.getsource(
                getattr(SandersSentinelService, name))
            self.assertNotIn('_program_item_state',
                             source, name)
            self.assertNotIn('CONSTRUCTION_PROGRAM',
                             source, name)

    def test_no_new_money_authority(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.disburse_funds(OPERATOR)
        status = self.sentinel.status()
        program = status['construction_program']
        self.assertFalse(program['funds_disbursed'])
        self.assertFalse(program['funds_held'])
        self.assertEqual(
            program['external_connections'], 'NONE')


class TestStatusSummary(ProgramTestBase):
    def test_status_carries_program_summary(self):
        status = self.sentinel.status()
        program = status['construction_program']
        self.assertEqual(
            len(program['items_by_ladder_state']), 18)
        self.assertEqual(
            set(program['items_by_ladder_state']
                .values()),
            {'CONSTRUCTED'})
        self.assertEqual(program['designations_active'],
                         0)
        self.sentinel.record_program_designation(
            OPERATOR, 52, 'ref', 'LIVE', 'auth')
        self.sentinel.record_program_test(
            OPERATOR, 52, ALL_STAGES, 'COMPLETED',
            'detail')
        status = self.sentinel.status()
        program = status['construction_program']
        self.assertEqual(
            program['items_by_ladder_state'][52],
            'OPERATIONAL')
        self.assertEqual(program['items_operational'],
                         [52])
        self.assertEqual(program['designations_active'],
                         1)
        self.assertEqual(
            status['bloodline_coverage']
            ['documents_watched'], 15)


if __name__ == '__main__':
    unittest.main()
