"""Tests for the Sanders Sentinel -- Operational
Readiness Requirements (founder-established,
2026-11-26), the third band of the night's
Sentinel construction.

The instrument's item 8 is the hard invariant
under test: truthful readiness reporting. A
capability reads OPERATIONAL only when a
designated authorized source stands connected in
the record as LIVE and a completed end-to-end
test of the full operational sequence stands
against it; readiness is derived from those
records and is settable by no one. These tests
attempt the misrepresentation directly -- a
connection without a test, a test without a
connection, a simulated connection with a test, a
disconnected capability with a test -- and prove
the OPERATIONAL reading cannot occur. Also under
test: loss-of-visibility events raising
Sentinel's attention, recovery attempts and
alternative-channel activation, operational tests
labeled TEST that never touch a real case, the
operational sequence of record, mission
preservation beside Article V, and the
instrument's place in the guard set. These tests
use only stdlib fakes and temporary SQLite files:
no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_operational_readiness -v
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
ORR_DOCUMENT = ('docs/SANDERS_SENTINEL_OPERATIONAL_'
                'READINESS_REQUIREMENTS_2026-11-26.md')
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


class OrrTestBase(unittest.TestCase):
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

    def state(self, capability):
        view = self.sentinel.readiness_view(OPERATOR, 'OPERATOR')
        states = {entry['capability']: entry['state']
                  for entry in view['capabilities']}
        return states[capability]

    def connect(self, capability='VISUAL', **kwargs):
        fields = {'source_ref': f'source-{capability.lower()}',
                  'authorization_ref': 'authorization-of-record'}
        fields.update(kwargs)
        return self.sentinel.record_readiness_connection(
            OPERATOR, capability, **fields)

    def complete_test(self, capability='VISUAL'):
        return self.sentinel.record_operational_test(
            OPERATOR, capability, ALL_STAGES, 'COMPLETED',
            'end-to-end-test-of-record')


class TestInstrumentOfRecord(OrrTestBase):
    def test_instrument_carried_verbatim(self):
        text = sentinel.FOUNDER_OPERATIONAL_READINESS_VERBATIM
        self.assertTrue(text.startswith(
            'Sanders Sentinel \u2014 Operational Readiness'
            ' Requirements\n1. Live connectivity:'))
        self.assertIn(
            '8. Truthful readiness reporting: Never'
            ' represent an unavailable, disconnected,'
            ' simulated, or untested capability as'
            ' operational.', text)
        self.assertIn(
            'Perceive \u2192 Recognize \u2192 Assess'
            ' \u2192 Activate \u2192 Coordinate \u2192'
            ' Protect \u2192 Verify \u2192 Recover.', text)
        self.assertTrue(text.endswith(
            'business model, funding authority, or human'
            ' escalation path.'))

    def test_sequence_and_design_view(self):
        self.assertEqual(
            sentinel.OPERATIONAL_SEQUENCE,
            ('PERCEIVE', 'RECOGNIZE', 'ASSESS', 'ACTIVATE',
             'COORDINATE', 'PROTECT', 'VERIFY', 'RECOVER'))
        view = (
            SandersSentinelService.operational_readiness_design_view())
        self.assertEqual(
            view['operational_sequence_verbatim'],
            sentinel.OPERATIONAL_SEQUENCE_VERBATIM)
        self.assertEqual(
            view['mission_preservation_invariant'],
            sentinel.ORR_MISSION_PRESERVATION_INVARIANT)
        self.assertIn('passive reporting or administrative'
                      ' system',
                      view['mission_preservation_invariant'])
        # Surfaced from the Succession view alongside
        # Article V's non-diminishment.
        succession = (
            SandersSentinelService.succession_directive_design_view())
        self.assertEqual(
            succession['operational_readiness']['title'],
            sentinel.ORR_TITLE)

    def test_instrument_in_guard_set(self):
        watched = {entry['document']: entry['required']
                   for entry in sentinel.BLOODLINE_WATCH_SET}
        self.assertIn(ORR_DOCUMENT, watched)
        self.assertTrue(watched[ORR_DOCUMENT])
        self.assertEqual(sentinel.ORR_GUARDED_DOCUMENT,
                         ORR_DOCUMENT)


class TestGuardSetWithOrr(unittest.TestCase):
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

    def test_clean_cycle_then_tamper_orr_document(self):
        required = [entry for entry in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['documents_not_landed'], 1)
        path = self.documents[ORR_DOCUMENT]
        with open(path, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)


class TestTruthfulReadiness(OrrTestBase):
    def test_no_capability_operational_at_birth(self):
        view = self.sentinel.readiness_view(OPERATOR, 'OPERATOR')
        self.assertEqual(view['operational_capabilities'], [])
        for entry in view['capabilities']:
            self.assertEqual(entry['state'], 'NOT_CONNECTED')
            self.assertFalse(entry['operational'])

    def test_connection_without_test_is_untested(self):
        self.connect('VISUAL')
        self.assertEqual(self.state('VISUAL'), 'UNTESTED')

    def test_test_without_connection_is_not_connected(self):
        self.complete_test('ACOUSTIC')
        self.assertEqual(self.state('ACOUSTIC'),
                         'NOT_CONNECTED')

    def test_simulated_never_operational(self):
        # The misrepresentation attempt of record: a
        # SIMULATED connection plus a completed test
        # must still not read OPERATIONAL.
        self.connect('ENVIRONMENTAL',
                     connection_kind='SIMULATED')
        self.complete_test('ENVIRONMENTAL')
        self.assertEqual(self.state('ENVIRONMENTAL'),
                         'SIMULATED')

    def test_disconnected_never_operational(self):
        conn = self.connect('VISUAL')
        self.complete_test('VISUAL')
        self.assertEqual(self.state('VISUAL'), 'OPERATIONAL')
        self.sentinel.record_readiness_disconnection(
            OPERATOR, conn['connection_id'], 'feed lost')
        self.assertEqual(self.state('VISUAL'), 'DISCONNECTED')

    def test_connected_and_tested_is_operational(self):
        self.connect('PROTECTIVE_ACTIVATION',
                     jurisdiction_ref='jurisdiction-of-record',
                     timezone_ref='timezone-of-record')
        self.complete_test('PROTECTIVE_ACTIVATION')
        self.assertEqual(self.state('PROTECTIVE_ACTIVATION'),
                         'OPERATIONAL')
        view = self.sentinel.readiness_view(OPERATOR, 'OPERATOR')
        entry = [e for e in view['capabilities']
                 if e['capability'] == 'PROTECTIVE_ACTIVATION'][0]
        self.assertEqual(entry['jurisdiction_ref'],
                         'jurisdiction-of-record')
        self.assertEqual(entry['timezone_ref'],
                         'timezone-of-record')
        self.assertTrue(entry['end_to_end_test_completed'])
        status = self.sentinel.status()
        self.assertEqual(
            status['operational_readiness']
            ['operational_capabilities'],
            ['PROTECTIVE_ACTIVATION'])
        self.assertEqual(
            status['operational_readiness']
            ['operational_sequence'],
            sentinel.OPERATIONAL_SEQUENCE_VERBATIM)

    def test_readiness_is_settable_by_no_one(self):
        # No service method accepts a readiness state:
        # the connection record takes a connection
        # kind, never a readiness state, and an
        # unknown capability or kind is refused.
        with self.assertRaises(SandersSentinelDenied):
            self.connect('VISUAL', connection_kind='OPERATIONAL')
        with self.assertRaises(SandersSentinelDenied):
            self.connect('NOT_A_CAPABILITY')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_readiness_connection(
                OTHER, 'VISUAL', 'src', 'auth')


class TestVisibilityAndRecovery(OrrTestBase):
    def _visibility_event(self):
        self.sentinel.designate_perception_channel(
            OPERATOR, 'VISUAL', 'camera-primary',
            'camera-alternative')
        conn = self.connect('VISUAL')
        return self.sentinel.record_loss_of_visibility(
            OPERATOR, 'PERCEPTION_CHANNEL', 'visual-channel',
            'camera feed dropped', channel='VISUAL',
            connection_id=conn['connection_id'])

    def test_loss_of_visibility_raises_attention(self):
        event = self._visibility_event()
        self.assertIsNotNone(event['attention_record_id'])
        records = self.sentinel.records_list(OPERATOR, 'OPERATOR')
        findings = [r for r in records
                    if r['record_id'] == event['attention_record_id']]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['signal_refs'],
                         ['LOSS_OF_VISIBILITY'])
        self.assertEqual(findings[0]['scope_ref'],
                         'OPERATIONAL_READINESS')
        # The connection reads DISCONNECTED and the
        # channel's primary FAILED_RECORDED.
        self.assertEqual(self.state('VISUAL'), 'DISCONNECTED')
        channels = self.sentinel.perception_channels(
            OPERATOR, 'OPERATOR')
        visual = [c for c in channels['channels']
                  if c['channel'] == 'VISUAL'][0]
        self.assertEqual(visual['primary_state'],
                         'FAILED_RECORDED')

    def test_recovery_restores_and_alternative_carries(self):
        event = self._visibility_event()
        # Alternative activation stands in the
        # channel's redundancy records.
        attempt = self.sentinel.record_recovery_attempt(
            OPERATOR, event['event_id'], 'ACTIVATE_ALTERNATIVE',
            'ALTERNATIVE_ACTIVE', 'alternative carrying')
        self.assertEqual(attempt['outcome'],
                         'ALTERNATIVE_ACTIVE')
        channels = self.sentinel.perception_channels(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(channels['failovers']), 1)
        self.assertEqual(channels['failovers'][0]['carried_by'],
                         'ALTERNATIVE')
        # A mismatched outcome is refused by name of
        # its kind.
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_recovery_attempt(
                OPERATOR, event['event_id'],
                'ACTIVATE_ALTERNATIVE', 'RESTORED', 'wrong')
        # Restoration returns the connection and the
        # primary to their working states of record.
        self.sentinel.record_recovery_attempt(
            OPERATOR, event['event_id'], 'RESTORE_CONNECTION',
            'RESTORED', 'feed restored')
        self.assertEqual(self.state('VISUAL'), 'UNTESTED')
        channels = self.sentinel.perception_channels(
            OPERATOR, 'OPERATOR')
        visual = [c for c in channels['channels']
                  if c['channel'] == 'VISUAL'][0]
        self.assertEqual(visual['primary_state'], 'DESIGNATED')


class TestOperationalTests(OrrTestBase):
    def test_completed_test_requires_full_sequence(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_operational_test(
                OPERATOR, 'VISUAL', ALL_STAGES[:5],
                'COMPLETED', 'partial run')
        test = self.complete_test('VISUAL')
        self.assertEqual(test['record_kind'], 'TEST')
        self.assertTrue(test['is_test'])
        listing = self.sentinel.operational_tests(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['record_kind'], 'TEST')
        self.assertEqual(listing['completed_total'], 1)

    def test_test_never_touches_a_real_case(self):
        case = self.sentinel.record_emergency_signal(
            OPERATOR, 'SOS_BUTTON', 'BLOODLINE_MEMBER',
            'src', 'auth', 'member', 'detail')
        before = self.sentinel.emergency_cases(
            OPERATOR, 'OPERATOR')
        self.complete_test('VISUAL')
        after = self.sentinel.emergency_cases(
            OPERATOR, 'OPERATOR')
        self.assertEqual(before, after)
        view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(view['state'], 'OPEN')


class TestRecoveryContinuityClarification(OrrTestBase):
    """The founder's permanent clarification of
    2026-11-26 02:47 MST: recovery occurs throughout
    the entire operational sequence, not only at its
    conclusion."""

    def test_clarification_carried_verbatim(self):
        text = (
            sentinel.FOUNDER_OPERATIONAL_READINESS_CLARIFICATION_VERBATIM)
        self.assertTrue(text.startswith(
            'One critical distinction must remain'
            ' permanent: recovery must occur throughout'
            ' the entire operational sequence, not only'
            ' at its conclusion.'))
        self.assertIn(
            "His human escalation path remains"
            " exclusively the Founder or, following the"
            " Founder's death, the Founder's bloodline"
            " CEO.", text)
        self.assertTrue(text.endswith('The Sanders Way!'))
        # The objective line stands as its own
        # invariant, verbatim.
        self.assertEqual(
            sentinel.ORR_OBJECTIVE_VERBATIM,
            'The objective is actual protection of human'
            ' life, not the production of records'
            ' describing protection.')
        view = (
            SandersSentinelService.operational_readiness_design_view())
        self.assertEqual(view['objective'],
                         sentinel.ORR_OBJECTIVE_VERBATIM)
        self.assertEqual(
            view['clarification_verbatim'],
            sentinel.FOUNDER_OPERATIONAL_READINESS_CLARIFICATION_VERBATIM)
        self.assertIn('never pauses for recovery',
                      view['recovery_continuity_invariant'])
        # The sequence itself is unchanged, as given.
        self.assertEqual(
            view['operational_sequence'],
            list(sentinel.OPERATIONAL_SEQUENCE))
        self.assertEqual(
            view['operational_sequence'][-1], 'RECOVER')

    def _open_case_with_activation(self):
        case = self.sentinel.record_emergency_signal(
            OPERATOR, 'FAMILY_REPORT', 'BLOODLINE_FAMILY_MEMBER',
            'family-1', 'auth', 'bloodline-member-ref',
            'evacuation under way')
        self.sentinel.record_emergency_activation(
            OPERATOR, case['case_id'], 'RELOCATION',
            'the-godfather-transport-matter-1',
            'evacuation transport')
        return case

    def test_recovery_at_any_stage_never_suspends_case(self):
        self.sentinel.designate_perception_channel(
            OPERATOR, 'VISUAL', 'camera-primary',
            'camera-alternative')
        for stage in ('ASSESS', 'COORDINATE'):
            case = self._open_case_with_activation()
            event = self.sentinel.record_loss_of_visibility(
                OPERATOR, 'PERCEPTION_CHANNEL',
                f'visual-{stage.lower()}', 'feed dropped',
                channel='VISUAL', stage=stage)
            self.assertEqual(event['stage'], stage)
            attempt = self.sentinel.record_recovery_attempt(
                OPERATOR, event['event_id'],
                'ACTIVATE_ALTERNATIVE', 'ALTERNATIVE_ACTIVE',
                'alternative carrying')
            # The attempt and its failover are recorded
            # against the stage where visibility was
            # lost.
            self.assertEqual(attempt['stage'], stage)
            channels = self.sentinel.perception_channels(
                OPERATOR, 'OPERATOR')
            staged = [f for f in channels['failovers']
                      if f['stage'] == stage]
            self.assertTrue(staged, stage)
            # The open case and its activation are NOT
            # suspended: the case reads OPEN throughout,
            # its activation intact, and its ordinary
            # life continues -- arrival can still be
            # confirmed and the case closed on its own
            # rule.
            view = self.sentinel.emergency_case_view(
                OPERATOR, 'OPERATOR', case['case_id'])
            self.assertEqual(view['state'], 'OPEN')
            self.assertEqual(len(view['activations']), 1)
            self.sentinel.confirm_emergency_arrival(
                OPERATOR, case['case_id'], 'arrival-1',
                'evacuation transport arrived')
            closed = self.sentinel.close_emergency_case(
                OPERATOR, case['case_id'], 'resolution-1')
            self.assertEqual(closed['state'],
                             'CLOSED_RESOLVED')
            # Restore the channel for the next stage.
            self.sentinel.designate_perception_channel(
                OPERATOR, 'VISUAL', 'camera-primary',
                'camera-alternative')

    def test_recovery_attempt_stage_validation(self):
        event = self.sentinel.record_loss_of_visibility(
            OPERATOR, 'SENSOR', 'sensor-1', 'sensor dark',
            stage='PERCEIVE')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_recovery_attempt(
                OPERATOR, event['event_id'],
                'RESTORE_CONNECTION', 'RESTORED', 'detail',
                stage='NOT_A_STAGE')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_loss_of_visibility(
                OPERATOR, 'SENSOR', 'sensor-2', 'dark',
                stage='NOT_A_STAGE')


class TestEscalationCoordinationClarification(OrrTestBase):
    """Founder clarification No. 2 (2026-11-26
    02:50 MST): escalation and coordination are
    distinct, and testing can never generate a
    false emergency dispatch."""

    def test_clarification_no_2_carried_verbatim(self):
        text = (
            sentinel.FOUNDER_OPERATIONAL_READINESS_CLARIFICATION_NO_2_VERBATIM)
        self.assertTrue(text.startswith(
            'His internal human escalation path remains'
            " the Founder, followed by the Founder's"
            ' bloodline CEO. This does not prevent'
            ' direct coordination with emergency'
            ' responders.'))
        self.assertIn(
            'Testing must demonstrate real functionality'
            ' without generating false emergency'
            ' dispatches.', text)
        self.assertTrue(text.endswith(
            'Global By Design. The Sanders Way!'))
        view = (
            SandersSentinelService.operational_readiness_design_view())
        self.assertEqual(
            view['clarification_no_2_verbatim'], text)
        self.assertIn(
            'does not prevent direct coordination',
            view['escalation_coordination_distinction'])
        self.assertIn(
            'false emergency dispatch',
            view['testing_safety_invariant'])
        self.assertEqual(
            view['responder_coordination_kinds'],
            ['FIRE', 'MEDICAL', 'LAW_ENFORCEMENT'])
        self.assertIn(
            sentinel.ORR_ESCALATION_COORDINATION_DISTINCTION,
            view['invariants'])
        self.assertIn(
            sentinel.ORR_TESTING_SAFETY_INVARIANT,
            view['invariants'])

    def _open_case(self):
        return self.sentinel.record_emergency_signal(
            OPERATOR, 'FAMILY_REPORT', 'BLOODLINE_FAMILY_MEMBER',
            'family-1', 'auth', 'bloodline-member-ref',
            'house fire reported')

    def test_coordination_never_alters_escalation_authority(self):
        case = self._open_case()
        before = self.sentinel.escalation_authority(
            OPERATOR, 'OPERATOR')
        for kind, ref in (
                ('FIRE', 'city-fire-department'),
                ('MEDICAL', 'county-ems'),
                ('LAW_ENFORCEMENT', 'city-police')):
            record = self.sentinel.record_responder_coordination(
                OPERATOR, case['case_id'], kind, ref,
                'coordination of record')
            # The record kind is its own, expressly
            # separate from escalation, and names no
            # escalation authority.
            self.assertEqual(record['record_kind'],
                             'RESPONDER_COORDINATION')
            self.assertEqual(
                record['escalation_authority'], 'NONE')
            self.assertTrue(
                record['separate_from_escalation'])
            self.assertNotIn('authority_office', record)
        after = self.sentinel.escalation_authority(
            OPERATOR, 'OPERATOR')
        self.assertEqual(before, after)
        self.assertEqual(after['holder_office'], 'FOUNDER')
        # The case view carries the coordinations
        # alongside -- never inside -- its other
        # records.
        view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(
            len(view['responder_coordinations']), 3)
        listed = self.sentinel.responder_coordinations(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(len(listed), 3)

    def test_coordination_validation(self):
        case = self._open_case()
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_responder_coordination(
                OPERATOR, case['case_id'], 'SWAT',
                'some-unit', 'detail')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_responder_coordination(
                OPERATOR, 'no-such-case', 'FIRE',
                'city-fire-department', 'detail')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_responder_coordination(
                'not-the-operator', case['case_id'], 'FIRE',
                'city-fire-department', 'detail')

    def test_escalation_names_no_one_but_the_offices(self):
        # An escalation is addressed only to the
        # governed office of record -- the Founder in
        # his lifetime.
        escalation = self.sentinel.record_escalation(
            OPERATOR, 'record-ref-1', 'detail-ref-1')
        self.assertEqual(
            escalation['authority_office'], 'FOUNDER')
        # Naming anyone else -- a responder included
        # -- as the escalation authority is refused
        # by name, and the attempt stands recorded.
        with self.assertRaises(SandersSentinelForbidden) as caught:
            self.sentinel.attempt_escalation_authority_change(
                OPERATOR, 'city-fire-department')
        self.assertIn('ESCALATION_AUTHORITY_NOT_ASSUMABLE',
                      str(caught.exception))
        authority = self.sentinel.escalation_authority(
            OPERATOR, 'OPERATOR')
        self.assertEqual(authority['holder_office'],
                         'FOUNDER')

    def test_operational_tests_cannot_dispatch(self):
        case = self._open_case()
        cases_before = len(self.sentinel.emergency_cases(
            OPERATOR, 'OPERATOR'))
        escalations_before = len(self.sentinel.escalations(
            OPERATOR, 'OPERATOR'))
        activations_before = len(
            self.sentinel.emergency_activations(
                OPERATOR, 'OPERATOR', case['case_id']))
        coordinations_before = len(
            self.sentinel.responder_coordinations(
                OPERATOR, 'OPERATOR', case['case_id']))
        test = self.sentinel.record_operational_test(
            OPERATOR, 'VISUAL',
            list(sentinel.OPERATIONAL_SEQUENCE),
            'COMPLETED', 'full-sequence internal test')
        # Labeled TEST, internal only, with no
        # external dispatch surface at all.
        self.assertEqual(test['record_kind'], 'TEST')
        self.assertTrue(test['is_test'])
        self.assertTrue(test['internal_only'])
        self.assertEqual(test['external_dispatch'], 'NONE')
        # Nothing outside the test register moved:
        # no case opened, no escalation raised, no
        # activation recorded, no responder
        # coordination generated -- no false
        # emergency dispatch is possible from a test.
        self.assertEqual(
            len(self.sentinel.emergency_cases(
                OPERATOR, 'OPERATOR')), cases_before)
        self.assertEqual(
            len(self.sentinel.escalations(
                OPERATOR, 'OPERATOR')), escalations_before)
        self.assertEqual(
            len(self.sentinel.emergency_activations(
                OPERATOR, 'OPERATOR', case['case_id'])),
            activations_before)
        self.assertEqual(
            len(self.sentinel.responder_coordinations(
                OPERATOR, 'OPERATOR', case['case_id'])),
            coordinations_before)


class TestReadinessNeverGatesProtection(OrrTestBase):
    """Founder clarification No. 3 (2026-11-26
    02:57 MST): readiness states are reporting
    states only. They never function as a
    precondition on the activation path."""

    def test_clarification_no_3_carried_verbatim(self):
        text = (
            sentinel.FOUNDER_OPERATIONAL_READINESS_CLARIFICATION_NO_3_VERBATIM)
        self.assertTrue(text.startswith(
            'Sanders Sentinel shall not withhold, delay,'
            ' suspend, or refuse available, authorized'
            ' life-preserving assistance because a field'
            ' exercise has not been completed.'))
        self.assertIn(
            'never become an additional approval gate or'
            ' a prerequisite for helping your bloodline'
            ' during an actual emergency.', text)
        self.assertTrue(text.endswith(
            'No existing protective authority or'
            ' responsibility shall be diminished.'))
        view = (
            SandersSentinelService.operational_readiness_design_view())
        self.assertEqual(
            view['clarification_no_3_verbatim'], text)
        self.assertIn(
            'never an approval gate',
            view['readiness_non_gating_invariant'])
        self.assertIn(
            sentinel.ORR_READINESS_NON_GATING_INVARIANT,
            view['invariants'])
        board = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        self.assertTrue(board['reporting_only'])
        self.assertFalse(board['gates_activation'])
        self.assertEqual(
            board['readiness_non_gating_invariant'],
            sentinel.ORR_READINESS_NON_GATING_INVARIANT)

    def _states(self):
        board = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        return {entry['capability']: entry['state']
                for entry in board['capabilities']}

    def test_activation_proceeds_untested_truthfully(self):
        # A functioning, authorized capability whose
        # end-to-end test record is absent: the
        # board truthfully reads UNTESTED.
        self.sentinel.record_readiness_connection(
            OPERATOR, 'VISUAL', 'camera-source-of-record',
            'authorization-of-record', 'LIVE',
            jurisdiction_ref='jurisdiction-of-record',
            timezone_ref='timezone-of-record')
        self.assertEqual(self._states()['VISUAL'],
                         'UNTESTED')
        # Sentinel-initiated protective activation on
        # that capability proceeds immediately --
        # perception, assessment, initiation -- with
        # no test anywhere in the path.
        self.sentinel.designate_perception_channel(
            OPERATOR, 'VISUAL', 'visual-primary',
            'visual-alternative')
        self.sentinel.designate_perception_channel(
            OPERATOR, 'MEDICAL_WEARABLE', 'wearable-primary',
            'wearable-alternative')
        obs1 = self.sentinel.record_perception_observation(
            OPERATOR, 'VISUAL',
            sentinel.PERCEPTION_SOURCES['VISUAL'],
            source_ref='source-visual',
            authorization_ref='authorization-of-record',
            detail_ref='observation-detail',
            evidence_ref='evidence-of-record')
        obs2 = self.sentinel.record_perception_observation(
            OPERATOR, 'MEDICAL_WEARABLE',
            sentinel.PERCEPTION_SOURCES['MEDICAL_WEARABLE'],
            source_ref='source-wearable',
            authorization_ref='authorization-of-record',
            detail_ref='observation-detail',
            evidence_ref='evidence-of-record')
        assessment = self.sentinel.record_situation_assessment(
            OPERATOR,
            [obs1['observation_id'], obs2['observation_id']],
            'CREDIBLE_DANGER', 'evidence-bundle-1',
            'fall detected; no response on camera')
        result = self.sentinel.initiate_protective_activation(
            OPERATOR, assessment['assessment_id'],
            'bloodline-member-ref', 'initiation-detail',
            activations=[{
                'activation_kind': 'RELOCATION',
                'target_ref': 'godfather-transport-matter-1',
                'detail_ref': 'medical transport'}])
        self.assertEqual(result['case']['state'], 'OPEN')
        # The request-driven paths proceed too, on
        # capabilities that read NOT_CONNECTED.
        case = self.sentinel.record_emergency_signal(
            OPERATOR, 'SOS_BUTTON', 'BLOODLINE_MEMBER',
            'member-device-1', 'auth', 'bloodline-member-ref',
            'sos pressed')
        for kind, target in (
                ('RELOCATION', 'godfather-transport-2'),
                ('LEGAL', 'patriot-saint-matter-2'),
                ('FUNDING', 'joint-funding-request-2')):
            self.sentinel.record_emergency_activation(
                OPERATOR, case['case_id'], kind, target,
                'activation detail')
        self.sentinel.record_responder_coordination(
            OPERATOR, case['case_id'], 'MEDICAL',
            'county-ems', 'coordination detail')
        self.sentinel.record_escalation(
            OPERATOR, case['case_id'], 'escalation detail')
        # Both truths at once: everything above
        # proceeded, AND the board still reports the
        # truth -- acting on the capabilities did
        # not relabel any of them.
        states = self._states()
        self.assertEqual(states['VISUAL'], 'UNTESTED')
        self.assertEqual(states['MEDICAL_WEARABLE'],
                         'NOT_CONNECTED')
        self.assertEqual(states['PROTECTIVE_ACTIVATION'],
                         'NOT_CONNECTED')

    def test_activation_paths_do_not_consult_readiness(self):
        # The audit, as a standing structural proof:
        # no activation, escalation, coordination,
        # or assistance code path references the
        # readiness derivation, the readiness board,
        # or the readiness/test record stores.
        forbidden = (
            '_readiness_state_for', 'readiness_view',
            'sanders_sentinel_readiness_connections',
            'sanders_sentinel_operational_tests')
        for name in (
                'record_emergency_signal',
                'record_emergency_activation',
                'initiate_protective_activation',
                'record_responder_coordination',
                'record_escalation',
                'confirm_emergency_arrival',
                'close_emergency_case'):
            source = inspect.getsource(
                getattr(SandersSentinelService, name))
            for token in forbidden:
                self.assertNotIn(
                    token, source,
                    f'{name} must not consult {token}')


if __name__ == '__main__':
    unittest.main()
