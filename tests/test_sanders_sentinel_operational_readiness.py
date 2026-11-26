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


if __name__ == '__main__':
    unittest.main()
