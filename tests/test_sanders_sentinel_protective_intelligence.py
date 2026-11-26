"""Tests for the Sanders Sentinel -- Real-Time
Protective Intelligence instrument
(founder-established, 2026-11-26), the second band
of the night's Sentinel construction.

The instrument extends Sentinel from receiving
requests to real-time perception, detection,
assessment, and protective response: perception
intake over five authorized channels, multisensor
assessment on evidence of record, predictive
hazard flags, protective initiation of the
Emergency Activation machinery on a recorded
credible-danger determination, continuous
situational assessment across an open case, and
operational redundancy of record. Honest limit,
asserted in these tests: no camera, sensor,
wearable, or warning feed is connected by this
construction -- live sources connect later as
designated authorized counterparts, and nothing
is represented as connected that is not. These
tests use only stdlib fakes and temporary SQLite
files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_protective_intelligence -v
(from the repo root).
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_sentinel_service as sentinel
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintService,
)
from core_platform.sanders_sentinel_service import (
    SandersSentinelDenied,
    SandersSentinelForbidden,
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherService,
)

OPERATOR = 'founder-operator'
OTHER = 'someone-else'
RTPI_DOCUMENT = ('docs/SANDERS_SENTINEL_REAL_TIME_'
                 'PROTECTIVE_INTELLIGENCE_2026-11-26.md')


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


class RtpiTestBase(unittest.TestCase):
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

    def designate(self, channel='VISUAL'):
        return self.sentinel.designate_perception_channel(
            OPERATOR, channel, f'{channel.lower()}-primary',
            f'{channel.lower()}-alternative')

    def observe(self, channel='VISUAL', **kwargs):
        fields = {
            'source_ref': f'source-{channel.lower()}',
            'authorization_ref': 'authorization-of-record',
            'detail_ref': 'observation-detail',
            'evidence_ref': 'evidence-of-record',
        }
        fields.update(kwargs)
        return self.sentinel.record_perception_observation(
            OPERATOR, channel,
            sentinel.PERCEPTION_SOURCES[channel], **fields)


class TestInstrumentOfRecord(RtpiTestBase):
    def test_instrument_carried_verbatim(self):
        text = sentinel.FOUNDER_PROTECTIVE_INTELLIGENCE_VERBATIM
        self.assertTrue(text.startswith(
            'Sanders Sentinel \u2014 Real-Time Protective'
            ' Intelligence\nHis architecture must support:'))
        self.assertIn(
            '1. Live visual perception: Analyze authorized'
            ' security camera feeds and voluntarily shared'
            ' live video', text)
        self.assertIn(
            '8. Immediate protective activation: Initiate'
            ' appropriate emergency assistance upon'
            ' detecting credible danger, without depending'
            ' exclusively on a person requesting help.',
            text)
        self.assertIn(
            '10. Operational redundancy: Maintain'
            ' alternative detection and communication'
            ' channels when primary systems fail.', text)
        self.assertTrue(text.endswith(
            'not simply the ability to receive requests.'))

    def test_design_view_and_honest_limit(self):
        view = (
            SandersSentinelService.protective_intelligence_design_view())
        self.assertEqual(
            view['instrument_verbatim'],
            sentinel.FOUNDER_PROTECTIVE_INTELLIGENCE_VERBATIM)
        self.assertEqual(len(view['perception_channels']), 5)
        # The honest limit, in the record itself: no
        # feed is connected by this construction.
        self.assertFalse(view['feeds_connected'])
        joined = '\n'.join(view['invariants'])
        self.assertIn('No camera, sensor, wearable, or'
                      ' warning feed is connected', joined)
        status = self.sentinel.status()
        section = status['real_time_protective_intelligence']
        self.assertFalse(section['feeds_connected'])
        # Surfaced from the Emergency Activation view too.
        emergency = (
            SandersSentinelService.emergency_activation_design_view())
        self.assertEqual(
            emergency['protective_intelligence']['title'],
            sentinel.RTPI_TITLE)

    def test_instrument_in_guard_set(self):
        watched = {entry['document']: entry['required']
                   for entry in sentinel.BLOODLINE_WATCH_SET}
        self.assertIn(RTPI_DOCUMENT, watched)
        self.assertTrue(watched[RTPI_DOCUMENT])
        self.assertEqual(
            sentinel.RTPI_GUARDED_DOCUMENT, RTPI_DOCUMENT)


class TestGuardSetWithRtpi(unittest.TestCase):
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

    def test_clean_cycle_then_tamper_rtpi_document(self):
        required = [entry for entry in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['documents_not_landed'], 1)
        path = self.documents[RTPI_DOCUMENT]
        with open(path, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)


class TestPerceptionIntake(RtpiTestBase):
    def test_designate_then_observe_all_channels(self):
        for channel in sentinel.PERCEPTION_CHANNELS:
            self.designate(channel)
            obs = self.observe(channel)
            self.assertEqual(obs['channel'], channel)
            self.assertEqual(obs['channel_path'], 'PRIMARY')
            self.assertEqual(
                obs['source_kind'],
                sentinel.PERCEPTION_SOURCES[channel])
        listing = self.sentinel.perception_observations(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['total'], 5)
        self.assertEqual(
            set(listing['by_channel']),
            set(sentinel.PERCEPTION_CHANNELS))

    def test_observation_requires_designated_channel(self):
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.observe('VISUAL')
        self.assertIn('PERCEPTION_CHANNEL_NOT_DESIGNATED',
                      str(ctx.exception))
        channels = self.sentinel.perception_channels(
            OPERATOR, 'OPERATOR')
        visual = [c for c in channels['channels']
                  if c['channel'] == 'VISUAL'][0]
        self.assertEqual(visual['designation_state'],
                         'NOT_DESIGNATED')
        self.assertFalse(channels['feeds_connected'])

    def test_unauthorized_source_refused_by_name(self):
        self.designate('ACOUSTIC')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_perception_observation(
                OPERATOR, 'ACOUSTIC', 'CONNECTED_SENSOR',
                'src', 'auth', 'detail', 'evidence')
        self.assertIn('PERCEPTION_SOURCE_NOT_AUTHORIZED',
                      str(ctx.exception))
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_perception_observation(
                OTHER, 'ACOUSTIC',
                sentinel.PERCEPTION_SOURCES['ACOUSTIC'],
                'src', 'auth', 'detail', 'evidence')

    def test_primary_failure_moves_to_alternative(self):
        self.designate('ENVIRONMENTAL')
        failover = (
            self.sentinel.record_perception_channel_failure(
                OPERATOR, 'ENVIRONMENTAL', 'sensor-bus-fault',
                'primary sensor bus fault of record'))
        self.assertEqual(failover['carried_by'], 'ALTERNATIVE')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.observe('ENVIRONMENTAL')
        self.assertIn('PERCEPTION_CHANNEL_PRIMARY_FAILED',
                      str(ctx.exception))
        obs = self.observe('ENVIRONMENTAL',
                           channel_path='ALTERNATIVE')
        self.assertEqual(obs['channel_path'], 'ALTERNATIVE')
        channels = self.sentinel.perception_channels(
            OPERATOR, 'OPERATOR')
        env = [c for c in channels['channels']
               if c['channel'] == 'ENVIRONMENTAL'][0]
        self.assertEqual(env['primary_state'],
                         'FAILED_RECORDED')
        self.assertEqual(len(channels['failovers']), 1)
        # A fresh designation of record restores the
        # primary.
        self.designate('ENVIRONMENTAL')
        obs = self.observe('ENVIRONMENTAL')
        self.assertEqual(obs['channel_path'], 'PRIMARY')


class TestAssessmentAndFlags(RtpiTestBase):
    def setUp(self):
        super().setUp()
        self.designate('VISUAL')
        self.designate('ACOUSTIC')
        self.obs_visual = self.observe('VISUAL')
        self.obs_acoustic = self.observe('ACOUSTIC')

    def test_multisensor_assessment_on_evidence(self):
        assessment = self.sentinel.record_situation_assessment(
            OPERATOR,
            [self.obs_visual['observation_id'],
             self.obs_acoustic['observation_id']],
            'CREDIBLE_DANGER', 'evidence-bundle-1',
            'smoke visible; alarm sounding')
        self.assertEqual(assessment['observation_count'], 2)
        self.assertTrue(assessment['credible_danger'])
        listing = self.sentinel.situation_assessments(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing['credible_danger_total'], 1)

    def test_assessment_never_on_invented_data(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_situation_assessment(
                OPERATOR, ['sentinel-observation-missing'],
                'CREDIBLE_DANGER', 'evidence', 'detail')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_situation_assessment(
                OPERATOR, [], 'CREDIBLE_DANGER',
                'evidence', 'detail')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_situation_assessment(
                OPERATOR, [self.obs_visual['observation_id']],
                'MAYBE_DANGER', 'evidence', 'detail')

    def test_hazard_flag_rests_on_accumulation(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.raise_hazard_flag(
                OPERATOR, 'pattern-1',
                [self.obs_visual['observation_id']], 'detail')
        flag = self.sentinel.raise_hazard_flag(
            OPERATOR, 'repeated-smoke-pattern',
            [self.obs_visual['observation_id'],
             self.obs_acoustic['observation_id']],
            'developing pattern of record')
        self.assertEqual(flag['observation_count'], 2)
        self.assertEqual(flag['state'], 'OPEN')
        flags = self.sentinel.hazard_flags(OPERATOR, 'OPERATOR')
        self.assertEqual(flags['open_total'], 1)


class TestProtectiveInitiation(RtpiTestBase):
    def setUp(self):
        super().setUp()
        self.designate('VISUAL')
        self.designate('MEDICAL_WEARABLE')
        obs1 = self.observe('VISUAL')
        obs2 = self.observe('MEDICAL_WEARABLE')
        self.assessment = (
            self.sentinel.record_situation_assessment(
                OPERATOR,
                [obs1['observation_id'], obs2['observation_id']],
                'CREDIBLE_DANGER', 'evidence-bundle-9',
                'fall detected; no response on camera'))

    def test_initiation_opens_case_and_activates(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'MEDICAL_TRANSPORTATION',
            'bloodline-member-ref', 'medical-transport')
        result = self.sentinel.initiate_protective_activation(
            OPERATOR, self.assessment['assessment_id'],
            'bloodline-member-ref', 'initiation-detail',
            activations=[{
                'activation_kind': 'RELOCATION',
                'target_ref': matter['matter_id'],
                'detail_ref': 'medical-transport'}])
        case = result['case']
        self.assertEqual(case['state'], 'OPEN')
        self.assertEqual(case['signal_kind'],
                         'RTSA_PLATFORM_SIGNAL')
        self.assertEqual(case['source_ref'],
                         self.assessment['assessment_id'])
        self.assertEqual(len(result['activations']), 1)
        self.assertFalse(
            result['initiation']['gated_on_escalation_delivery'])
        # The initiated case closes under the same rule
        # as any emergency case: verified arrival plus a
        # recorded resolution.
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.close_emergency_case(
                OPERATOR, case['case_id'], 'resolution-1')
        self.sentinel.confirm_emergency_arrival(
            OPERATOR, case['case_id'], 'arrival-1',
            'medical transport arrived')
        closed = self.sentinel.close_emergency_case(
            OPERATOR, case['case_id'], 'resolution-1')
        self.assertEqual(closed['state'], 'CLOSED_RESOLVED')

    def test_initiation_requires_credible_danger(self):
        obs = self.observe('VISUAL')
        calm = self.sentinel.record_situation_assessment(
            OPERATOR, [obs['observation_id']],
            'NO_CREDIBLE_DANGER', 'evidence', 'all quiet')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.initiate_protective_activation(
                OPERATOR, calm['assessment_id'],
                'bloodline-member-ref', 'detail')
        self.assertIn(
            'PROTECTIVE_ACTIVATION_REQUIRES_CREDIBLE_DANGER',
            str(ctx.exception))
        # And one initiation per assessment.
        self.sentinel.initiate_protective_activation(
            OPERATOR, self.assessment['assessment_id'],
            'bloodline-member-ref', 'detail')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.initiate_protective_activation(
                OPERATOR, self.assessment['assessment_id'],
                'bloodline-member-ref', 'detail')
        self.assertIn('PROTECTIVE_INITIATION_ALREADY_RECORDED',
                      str(ctx.exception))

    def test_continuous_assessment_across_open_case(self):
        result = self.sentinel.initiate_protective_activation(
            OPERATOR, self.assessment['assessment_id'],
            'bloodline-member-ref', 'detail')
        case_id = result['case']['case_id']
        obs = self.observe('VISUAL')
        follow = self.sentinel.record_situation_assessment(
            OPERATOR, [obs['observation_id']],
            'CREDIBLE_DANGER', 'evidence-bundle-10',
            'conditions worsening', case_id=case_id,
            adaptation_ref='assistance-adapted-ref')
        self.assertEqual(follow['case_id'], case_id)
        self.assertEqual(follow['adaptation_ref'],
                         'assistance-adapted-ref')
        listing = self.sentinel.situation_assessments(
            OPERATOR, 'OPERATOR', case_id=case_id)
        self.assertEqual(listing['total'], 1)
        # No assessment records against a closed case.
        self.sentinel.confirm_emergency_arrival(
            OPERATOR, case_id, 'arrival-1', 'assistance in')
        self.sentinel.close_emergency_case(
            OPERATOR, case_id, 'resolution-1')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_situation_assessment(
                OPERATOR, [obs['observation_id']],
                'NO_CREDIBLE_DANGER', 'evidence', 'detail',
                case_id=case_id)


if __name__ == '__main__':
    unittest.main()
