"""Tests for the Sanders Sentinel -- Human Life
Protection By Design architecture (founder-adopted,
2026-11-26): the architecture statement of record,
the expanded threat scope, the prevention layer,
the clinical handover, the voice/telephony
extension architecture, the six-industry resource
base, and per-part ladder reporting.

The hard invariants under test: the operational
sequence remains the established eight stages and
prevention is a SUPPORTING layer, never a ninth
stage and never a gate (a prevention record
conditions nothing; protective paths proceed with
every part merely CONSTRUCTED and never consult a
part state); the truthful-verification ladder is
derived from records and settable by no one (a
SIMULATED designation never connects; OPERATIONAL
requires an ACTIVE LIVE designation AND a
completed end-to-end test); this construction
connects nothing external; across the threat scope
Sentinel coordinates and never treats, and a
psychological record coordinates only to qualified
human professionals; a handover carries authorized
information by reference only, holds no medical
information, and claims no interoperability; the
telephony components stand NOT_INSTALLED,
NOT_CONFIGURED, and NOT_CONNECTED with live_call
False; the six industries are referenced by name
and anchored NAICS code, with emergency ambulance
transportation distinct from non-emergency medical
transportation; and the architecture never touches
the escalation path, the readiness board, the
construction program, or any money authority.
These tests use only stdlib fakes and temporary
SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_human_life_protection -v
(from the repo root).
"""

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform.sanders_sentinel_service import (
    SandersSentinelDenied,
    SandersSentinelForbidden,
    SandersSentinelService,
)

OPERATOR = 'founder-operator'
OTHER = 'someone-else'
HLP_DOCUMENT = ('docs/SANDERS_SENTINEL_HUMAN_LIFE_'
                'PROTECTION_2026-11-26.md')
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


class HlpTestBase(unittest.TestCase):
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

    def open_case(self, kind='SOS_BUTTON'):
        source = sentinel.EMERGENCY_SIGNAL_SOURCES[kind]
        return self.sentinel.record_emergency_signal(
            OPERATOR, kind, source, f'source-{kind.lower()}',
            'authorization-of-record', 'bloodline-member-ref',
            'signal-detail-ref')

    def part_state(self, part_key):
        view = self.sentinel.human_life_protection_view(
            OPERATOR, 'OPERATOR')
        return {entry['part']: entry
                for entry in view['parts']}[part_key]


class TestArchitectureOfRecord(HlpTestBase):
    def test_statement_carried_verbatim(self):
        text = sentinel.FOUNDER_HLP_STATEMENT_VERBATIM
        self.assertIn(
            'Sanders Sentinel shall be architected '
            'with the preservation and protection of '
            'human life as a fundamental design '
            'objective', text)
        self.assertIn(sentinel.HLP_MEASURE, text)
        self.assertIn(
            'The objective is actual protection of '
            'human life, not the production of '
            'records describing protection.', text)
        self.assertIn(
            'Perceive \u2192 Recognize \u2192 Assess \u2192 '
            'Activate \u2192 Coordinate \u2192 Protect \u2192 '
            'Verify \u2192 Recover.', text)

    def test_adoption_carried_verbatim(self):
        self.assertEqual(
            sentinel.FOUNDER_HLP_ADOPTION_VERBATIM,
            'Adopt the Human Life Protection '
            'architecture as Sentinel\'s next '
            'construction program')

    def test_threat_scope_carried_verbatim(self):
        lines = (sentinel
                 .FOUNDER_HLP_THREAT_SCOPE_VERBATIM
                 .split('\n'))
        self.assertEqual(len(lines), 10)
        self.assertTrue(lines[0].startswith(
            'Disability protection'))
        self.assertTrue(lines[-1].startswith(
            'International protection'))

    def test_prevention_carried_verbatim(self):
        lines = (sentinel.FOUNDER_HLP_PREVENTION_VERBATIM
                 .split('\n'))
        self.assertEqual(len(lines), 8)
        self.assertTrue(lines[0].startswith(
            'Forecast dangerous heat'))
        self.assertTrue(lines[-1].startswith(
            'Communications degradation'))

    def test_handover_fields_carried_verbatim(self):
        lines = (sentinel
                 .FOUNDER_HLP_HANDOVER_FIELDS_VERBATIM
                 .split('\n'))
        self.assertEqual(len(lines), 8)
        self.assertEqual(
            lines[0],
            'Known medical conditions and allergies.')
        self.assertEqual(lines[-1],
                         'Applicable medical directives.')

    def test_components_carried_verbatim(self):
        lines = (sentinel
                 .FOUNDER_HLP_TELEPHONY_COMPONENTS_VERBATIM
                 .split('\n'))
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[0].startswith('Sherpa-ONNX'))
        self.assertTrue(lines[-1].startswith(
            'IETF RFC 6881'))

    def test_industries_carried_verbatim(self):
        lines = (sentinel.FOUNDER_HLP_INDUSTRIES_VERBATIM
                 .split('\n'))
        self.assertEqual(len(lines), 6)
        self.assertTrue(lines[0].startswith(
            'Home healthcare'))
        self.assertTrue(lines[-1].startswith(
            'Healthcare courier services'))

    def test_design_view_shape(self):
        design = (SandersSentinelService
                  .hlp_design_view())
        self.assertEqual(len(design['parts']), 7)
        self.assertEqual(
            len(design['threat_categories']), 10)
        self.assertEqual(
            len(design['prevention_kinds']), 8)
        self.assertEqual(
            len(design['handover_fields']), 8)
        self.assertEqual(
            len(design['telephony_components']), 5)
        self.assertEqual(
            len(design['industry_resource_base']), 6)
        self.assertEqual(
            design['prevention_layer'], 'SUPPORTING')
        self.assertEqual(
            design['external_connections'], 'NONE')
        self.assertFalse(design['live_call'])
        self.assertEqual(
            design['telephony_connection_state'],
            'NOT_CONNECTED')

    def test_sequence_remains_eight_stages(self):
        design = (SandersSentinelService
                  .hlp_design_view())
        self.assertEqual(design['operational_sequence'],
                         ALL_STAGES)
        self.assertEqual(len(ALL_STAGES), 8)
        self.assertNotIn('PREVENT', ALL_STAGES)
        self.assertNotIn('PREVENTION', ALL_STAGES)

    def test_industry_codes_are_the_anchored_six(self):
        codes = [entry['naics'] for entry in (
            SandersSentinelService.hlp_design_view()
            ['industry_resource_base'])]
        self.assertEqual(
            codes, ['621610', '624120', '485991',
                    '532283', '423450', '492110'])

    def test_ambulance_distinction_carried(self):
        design = (SandersSentinelService
                  .hlp_design_view())
        self.assertIn(
            'distinct',
            design['ambulance_distinction_invariant'])
        self.assertIn(
            '485991',
            design['ambulance_distinction_invariant'])

    def test_bloodline_design_view_includes_hlp(self):
        view = (SandersSentinelService
                .bloodline_design_view())
        self.assertIn('sentinel_human_life_protection',
                      view)
        self.assertEqual(
            view['sentinel_human_life_protection']
            ['title'], sentinel.HLP_TITLE)


class TestGuardSetWithHlp(unittest.TestCase):
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

    def test_hlp_document_watched_and_required(self):
        entry = {e['document']: e
                 for e in sentinel.BLOODLINE_WATCH_SET}[
                     HLP_DOCUMENT]
        self.assertTrue(entry['required'])
        self.assertEqual(len(sentinel.BLOODLINE_WATCH_SET),
                         20)

    def test_clean_cycle_then_tamper_hlp_document(self):
        required = [entry for entry
                    in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        self.assertEqual(len(required), 19)
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['documents_not_landed'], 1)
        path = self.documents[HLP_DOCUMENT]
        with open(path, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(
            OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)


class TestLadderDerivation(HlpTestBase):
    def test_every_part_constructed_at_birth(self):
        view = self.sentinel.human_life_protection_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(view['parts']), 7)
        for entry in view['parts']:
            self.assertEqual(entry['ladder_state'],
                             'CONSTRUCTED')
            self.assertTrue(entry['reporting_only'])
            self.assertFalse(entry['gates_activation'])
        self.assertEqual(view['parts_operational'], [])
        self.assertEqual(view['external_connections'],
                         'NONE')
        self.assertFalse(view['live_call'])

    def test_simulated_designation_never_connects(self):
        self.sentinel.record_hlp_designation(
            OPERATOR, 'PREVENTION_LAYER', 'feed-ref',
            'SIMULATED', 'authorization-ref')
        state = self.part_state('PREVENTION_LAYER')
        self.assertEqual(state['ladder_state'],
                         'CONSTRUCTED')
        self.assertTrue(state['simulated_designation'])

    def test_live_designation_connects(self):
        self.sentinel.record_hlp_designation(
            OPERATOR, 'PREVENTION_LAYER', 'feed-ref',
            'LIVE', 'authorization-ref')
        state = self.part_state('PREVENTION_LAYER')
        self.assertEqual(state['ladder_state'],
                         'CONNECTED')

    def test_test_alone_reads_tested(self):
        self.sentinel.record_hlp_test(
            OPERATOR, 'CLINICAL_HANDOVER', ALL_STAGES,
            'COMPLETED', 'test-detail-ref')
        state = self.part_state('CLINICAL_HANDOVER')
        self.assertEqual(state['ladder_state'], 'TESTED')

    def test_operational_requires_both(self):
        self.sentinel.record_hlp_designation(
            OPERATOR, 'CLINICAL_HANDOVER', 'service-ref',
            'LIVE', 'authorization-ref')
        self.sentinel.record_hlp_test(
            OPERATOR, 'CLINICAL_HANDOVER', ALL_STAGES,
            'COMPLETED', 'test-detail-ref')
        state = self.part_state('CLINICAL_HANDOVER')
        self.assertEqual(state['ladder_state'],
                         'OPERATIONAL')

    def test_ending_designation_rederives(self):
        designation = self.sentinel.record_hlp_designation(
            OPERATOR, 'PREVENTION_LAYER', 'feed-ref',
            'LIVE', 'authorization-ref')
        self.sentinel.end_hlp_designation(
            OPERATOR, designation['designation_id'],
            'ended-detail-ref')
        state = self.part_state('PREVENTION_LAYER')
        self.assertEqual(state['ladder_state'],
                         'CONSTRUCTED')

    def test_unknown_part_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_hlp_designation(
                OPERATOR, 'NOT_A_PART', 'ref', 'LIVE',
                'authorization-ref')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_hlp_test(
                OPERATOR, 'NOT_A_PART', ALL_STAGES,
                'COMPLETED', 'detail-ref')

    def test_completed_test_requires_all_stages(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_hlp_test(
                OPERATOR, 'PREVENTION_LAYER',
                ALL_STAGES[:4], 'COMPLETED',
                'detail-ref')

    def test_hlp_records_do_not_touch_program_or_readiness(
            self):
        before_program = (
            self.sentinel.construction_program_view(
                OPERATOR, 'OPERATOR'))
        before_readiness = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        self.sentinel.record_hlp_designation(
            OPERATOR, 'PREVENTION_LAYER', 'feed-ref',
            'LIVE', 'authorization-ref')
        self.sentinel.record_hlp_test(
            OPERATOR, 'PREVENTION_LAYER', ALL_STAGES,
            'COMPLETED', 'test-detail-ref')
        after_program = (
            self.sentinel.construction_program_view(
                OPERATOR, 'OPERATOR'))
        after_readiness = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        self.assertEqual(
            [e['ladder_state']
             for e in before_program['items']],
            [e['ladder_state']
             for e in after_program['items']])
        self.assertEqual(before_readiness, after_readiness)
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_operational_test(
                OPERATOR, 'HLP_PART_PREVENTION_LAYER',
                ALL_STAGES, 'COMPLETED', 'detail-ref')


class TestThreatRecords(HlpTestBase):
    def test_record_each_category(self):
        for entry in sentinel.HLP_THREAT_CATEGORIES:
            record = self.sentinel.record_threat_record(
                OPERATOR, entry['category'], 'member-ref',
                'evidence-ref', 'detail-ref')
            self.assertEqual(record['category'],
                             entry['category'])
            self.assertFalse(
                record['treatment_by_sentinel'])
            self.assertEqual(record['sentinel_role'],
                             'COORDINATION_ONLY')
        listing = self.sentinel.threat_records(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 10)
        self.assertFalse(listing['treatment_by_sentinel'])

    def test_unknown_category_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'NOT_A_CATEGORY', 'member-ref',
                'evidence-ref', 'detail-ref')

    def test_evidence_required(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'ENVIRONMENTAL', 'member-ref',
                '', 'detail-ref')

    def test_psychological_qualified_professionals_only(
            self):
        record = self.sentinel.record_threat_record(
            OPERATOR, 'PSYCHOLOGICAL', 'member-ref',
            'evidence-ref', 'detail-ref',
            coordination_kind=(
                'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL'),
            counterpart_ref='crisis-service-ref')
        self.assertEqual(
            record['coordination_kind'],
            'QUALIFIED_MENTAL_HEALTH_PROFESSIONAL')
        record = self.sentinel.record_threat_record(
            OPERATOR, 'PSYCHOLOGICAL', 'member-ref',
            'evidence-ref', 'detail-ref',
            coordination_kind='TRAINED_CRISIS_COUNSELOR',
            counterpart_ref='counselor-ref')
        self.assertEqual(record['coordination_kind'],
                         'TRAINED_CRISIS_COUNSELOR')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'PSYCHOLOGICAL', 'member-ref',
                'evidence-ref', 'detail-ref',
                coordination_kind=(
                    'EMERGENCY_RESPONDER_SERVICE'),
                counterpart_ref='responder-ref')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'PSYCHOLOGICAL', 'member-ref',
                'evidence-ref', 'detail-ref',
                coordination_kind=(
                    'ASSISTANCE_ORGANIZATION'),
                counterpart_ref='org-ref')

    def test_coordination_kind_and_counterpart_pair(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'WATER_SAFETY', 'member-ref',
                'evidence-ref', 'detail-ref',
                coordination_kind=(
                    'EMERGENCY_RESPONDER_SERVICE'))
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'WATER_SAFETY', 'member-ref',
                'evidence-ref', 'detail-ref',
                counterpart_ref='responder-ref')

    def test_case_must_exist(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_threat_record(
                OPERATOR, 'ENVIRONMENTAL', 'member-ref',
                'evidence-ref', 'detail-ref',
                case_id='no-such-case')
        case = self.open_case()
        record = self.sentinel.record_threat_record(
            OPERATOR, 'ENVIRONMENTAL', 'member-ref',
            'evidence-ref', 'detail-ref',
            case_id=case['case_id'])
        self.assertEqual(record['case_id'],
                         case['case_id'])

    def test_non_operator_refused(self):
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_threat_record(
                OTHER, 'ENVIRONMENTAL', 'member-ref',
                'evidence-ref', 'detail-ref')


class TestPreventionRecords(HlpTestBase):
    def test_record_each_kind(self):
        for entry in sentinel.HLP_PREVENTION_KINDS:
            record = (self.sentinel
                      .record_prevention_record(
                          OPERATOR, entry['kind'],
                          'member-ref', 'detail-ref'))
            self.assertEqual(record['anticipation_kind'],
                             entry['kind'])
            self.assertEqual(record['prevention_layer'],
                             'SUPPORTING')
            self.assertFalse(record['gates_activation'])
            self.assertFalse(record['delays_activation'])
        listing = self.sentinel.prevention_records(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 8)
        self.assertFalse(listing['gates_activation'])

    def test_link_machinery_discipline_per_kind(self):
        record = (self.sentinel
                  .record_prevention_record(
                      OPERATOR, 'SEVERE_WEATHER_WARNING',
                      'member-ref', 'detail-ref',
                      linked_machinery_kind='GODFATHER_MATTER',
                      linked_record_ref='matter-ref'))
        self.assertEqual(record['linked_machinery_kind'],
                         'GODFATHER_MATTER')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_prevention_record(
                OPERATOR, 'TRANSPORTATION_DISRUPTION',
                'member-ref', 'detail-ref',
                linked_machinery_kind='FAMILY_NOTIFICATION',
                linked_record_ref='notification-ref')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_prevention_record(
                OPERATOR, 'ELEVATED_FALL_RISK',
                'member-ref', 'detail-ref',
                linked_machinery_kind='FAMILY_NOTIFICATION')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_prevention_record(
                OPERATOR, 'ELEVATED_FALL_RISK',
                'member-ref', 'detail-ref',
                linked_record_ref='notification-ref')

    def test_prevention_never_gates_activation(self):
        # No prevention records at all: the emergency
        # paths proceed (clarification No. 3).
        case = self.open_case()
        activation = (self.sentinel
                      .record_emergency_activation(
                          OPERATOR, case['case_id'],
                          'RELOCATION', 'matter-ref',
                          'detail'))
        self.assertEqual(activation['activation_kind'],
                         'RELOCATION')
        # And with prevention records standing, the
        # same paths proceed unchanged.
        self.sentinel.record_prevention_record(
            OPERATOR, 'FORECAST_DANGEROUS_HEAT',
            'member-ref', 'detail-ref')
        case = self.open_case()
        activation = (self.sentinel
                      .record_emergency_activation(
                          OPERATOR, case['case_id'],
                          'RELOCATION', 'matter-ref',
                          'detail'))
        self.assertEqual(activation['activation_kind'],
                         'RELOCATION')

    def test_protective_paths_never_consult_hlp(self):
        for name in ('record_emergency_signal',
                     'record_emergency_activation',
                     'record_responder_coordination',
                     'close_emergency_case',
                     'record_emergency_protective_action'):
            source = inspect.getsource(
                getattr(SandersSentinelService, name))
            self.assertNotIn('_hlp_part_state', source,
                             name)
            self.assertNotIn('HLP_', source, name)
            self.assertNotIn('prevention_records', source,
                             name)


class TestHandoverRecords(HlpTestBase):
    def coordinate(self, case_id):
        return (self.sentinel
                .record_responder_coordination(
                    OPERATOR, case_id, 'MEDICAL',
                    'responder-ref', 'detail'))

    def test_handover_attaches_to_coordination(self):
        case = self.open_case()
        coordination = self.coordinate(case['case_id'])
        record = self.sentinel.record_handover_record(
            OPERATOR, case['case_id'],
            coordination['coordination_id'],
            'jurisdiction-ref', 'detail-ref',
            conditions_allergies_ref='conditions-ref',
            medications_ref='medications-ref',
            accessibility_ref='accessibility-ref')
        self.assertTrue(
            record['authorized_information_only'])
        self.assertFalse(
            record['holds_medical_information'])
        self.assertFalse(
            record['interoperability_claimed'])
        self.assertEqual(record['privacy'],
                         'JURISDICTION_AWARE')
        self.assertEqual(
            record['fields_by_reference']
            ['conditions_allergies'], 'conditions-ref')
        self.assertIsNone(
            record['fields_by_reference']['equipment'])
        self.assertIn('HL7 FHIR',
                      record['standards_informing'])

    def test_handover_requires_a_field(self):
        case = self.open_case()
        coordination = self.coordinate(case['case_id'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_handover_record(
                OPERATOR, case['case_id'],
                coordination['coordination_id'],
                'jurisdiction-ref', 'detail-ref')

    def test_handover_unknown_coordination_refused(self):
        case = self.open_case()
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_handover_record(
                OPERATOR, case['case_id'],
                'no-such-coordination',
                'jurisdiction-ref', 'detail-ref',
                medications_ref='medications-ref')

    def test_handover_case_must_match_coordination(self):
        case = self.open_case()
        other = self.open_case()
        coordination = self.coordinate(case['case_id'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_handover_record(
                OPERATOR, other['case_id'],
                coordination['coordination_id'],
                'jurisdiction-ref', 'detail-ref',
                medications_ref='medications-ref')

    def test_handover_jurisdiction_required(self):
        case = self.open_case()
        coordination = self.coordinate(case['case_id'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_handover_record(
                OPERATOR, case['case_id'],
                coordination['coordination_id'],
                '', 'detail-ref',
                medications_ref='medications-ref')


class TestTelephonyComponents(HlpTestBase):
    def test_record_each_component(self):
        for entry in sentinel.HLP_TELEPHONY_COMPONENTS:
            record = (self.sentinel
                      .record_telephony_component(
                          OPERATOR, entry['component'],
                          'architecture-ref', 'detail-ref'))
            self.assertEqual(record['component'],
                             entry['component'])
            self.assertEqual(
                record['installation_state'],
                'NOT_INSTALLED')
            self.assertEqual(
                record['configuration_state'],
                'NOT_CONFIGURED')
            self.assertEqual(record['connection_state'],
                             'NOT_CONNECTED')
            self.assertFalse(record['live_call'])
            self.assertEqual(
                record['native_voice_path'],
                'DAEDALUS_SYSTEM_TTS')
            self.assertEqual(
                record['extension_of'],
                'DAEDALUS_SOVEREIGN_VOICE_ENGINE')
        listing = self.sentinel.telephony_components(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 5)
        self.assertEqual(listing['connection_state'],
                         'NOT_CONNECTED')
        self.assertFalse(listing['live_call'])

    def test_unknown_component_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_telephony_component(
                OPERATOR, 'NOT_A_COMPONENT', 'ref',
                'detail-ref')

    def test_voice_calling_readiness_unchanged(self):
        self.sentinel.record_telephony_component(
            OPERATOR, 'ASTERISK', 'architecture-ref',
            'detail-ref')
        readiness = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        voice = {entry['capability']: entry for entry
                 in readiness['capabilities']}[
                     'VOICE_CALLING']
        self.assertEqual(voice['state'], 'NOT_CONNECTED')


class TestStatusAndNonGating(HlpTestBase):
    def test_status_includes_hlp_section(self):
        self.sentinel.record_threat_record(
            OPERATOR, 'ENVIRONMENTAL', 'member-ref',
            'evidence-ref', 'detail-ref')
        self.sentinel.record_prevention_record(
            OPERATOR, 'CAREGIVER_ABSENCE', 'member-ref',
            'detail-ref')
        status = self.sentinel.status()
        section = status['human_life_protection']
        self.assertEqual(section['title'],
                         sentinel.HLP_TITLE)
        self.assertEqual(
            section['threat_records_total'], 1)
        self.assertEqual(
            section['prevention_records_total'], 1)
        self.assertEqual(
            section['telephony_connection_state'],
            'NOT_CONNECTED')
        self.assertFalse(section['live_call'])
        self.assertEqual(section['parts_operational'],
                         [])
        self.assertEqual(
            set(section['parts_by_ladder_state']
                .values()), {'CONSTRUCTED'})

    def test_no_new_money_authority(self):
        with self.assertRaises(Exception):
            self.sentinel.disburse_funds(OPERATOR)
        view = self.sentinel.human_life_protection_view(
            OPERATOR, 'OPERATOR')
        self.assertFalse(view['funds_disbursed'])
        self.assertFalse(view['funds_held'])


if __name__ == '__main__':
    unittest.main()
