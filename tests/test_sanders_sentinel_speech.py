"""Tests for Sanders Sentinel's speech and voice
(founder ruling "Every single platform must have
the ability to speak", 2026-11-26 03:06 MST;
specification 03:09 MST; implementation principle
03:11 MST) -- band four of the night's Sentinel
construction.

Under test: the ruling, specification, and
principle carried verbatim; the ruling's place in
the guard set; speech records on escalations and
emergency cases, born UNDELIVERED under the same
delivery-verification discipline as escalations;
the native-path lock (Sentinel speaks only through
the flagship's Daedalus system-TTS path; a provider
path is refused by name); the engine/voice
distinction (shared sovereign engine, Sentinel's
own voice identity on every record); two-way voice
conversation records with language as a recorded
field and live_call False throughout; voice never
a precondition for protective action (structural
audit plus a live exercise); voice-channel failure
flowing into the standing loss-of-visibility and
recovery records; and the VOICE_CALLING readiness
capability reading NOT_CONNECTED with nothing of
record. These tests use only stdlib fakes and
temporary SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_speech -v
(from the repo root).
"""

import inspect
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
SPEAK_DOCUMENT = ('docs/FOUNDER_RULING_EVERY_PLATFORM_'
                  'MUST_SPEAK_2026-11-26.md')


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


class SpeechTestBase(unittest.TestCase):
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

    def escalation(self):
        return self.sentinel.record_escalation(
            OPERATOR, 'record-ref-1', 'detail-ref-1',
            emergency=True)

    def case(self):
        return self.sentinel.record_emergency_signal(
            OPERATOR, 'FAMILY_REPORT',
            'BLOODLINE_FAMILY_MEMBER', 'family-1', 'auth',
            'bloodline-member-ref', 'emergency of record')


class TestRulingOfRecord(SpeechTestBase):
    def test_ruling_specification_principle_verbatim(self):
        self.assertEqual(
            sentinel.FOUNDER_RULING_EVERY_PLATFORM_MUST_SPEAK_VERBATIM,
            'Every single platform must have the ability'
            ' to speak')
        spec = sentinel.FOUNDER_SPEAK_SPECIFICATION_VERBATIM
        self.assertTrue(spec.startswith(
            'Real-time conversation \u2014 natural,'
            ' interactive, two-way verbal communication.'))
        self.assertIn(
            'Voice shall be an additional operational'
            ' capability, never a replacement for existing'
            ' capabilities or a prerequisite for'
            ' protective action.', spec)
        self.assertTrue(spec.endswith(
            'Distinct identities. Native voices. Two-way'
            ' communication. Global By Design'))
        principle = (
            sentinel.FOUNDER_SPEAK_IMPLEMENTATION_PRINCIPLE_VERBATIM)
        self.assertIn(
            'a shared sovereign voice engine may serve'
            ' all 140 platforms without merging their'
            ' identities, personalities, responsibilities,'
            ' or operational authority', principle)
        self.assertIn(
            'Live calling remains a required capability,'
            ' not a verified operational capability.',
            principle)

    def test_ruling_in_guard_set(self):
        entries = {entry['document']: entry
                   for entry in sentinel.BLOODLINE_WATCH_SET}
        self.assertIn(SPEAK_DOCUMENT, entries)
        self.assertTrue(entries[SPEAK_DOCUMENT]['required'])
        view = SandersSentinelService.bloodline_design_view()
        watched = {entry['document']
                   for entry in view['watch_set']}
        self.assertIn(SPEAK_DOCUMENT, watched)
        self.assertIn('sentinel_speech', view)

    def test_design_view_engine_shared_voice_his(self):
        view = SandersSentinelService.speech_design_view()
        self.assertEqual(
            view['ruling_verbatim'],
            'Every single platform must have the ability'
            ' to speak')
        self.assertTrue(view['engine_shared'])
        self.assertEqual(view['engine'],
                         sentinel.SENTINEL_SPEECH_NATIVE_PATH)
        self.assertEqual(view['voice_identity'],
                         'SANDERS_SENTINEL')
        self.assertIn('Engine shared, voice his',
                      view['voice_distinction'])
        self.assertFalse(view['voice_calling_live'])
        self.assertEqual(
            view['voice_calling_status'],
            'REQUIRED CAPABILITY \u2014 NOT A VERIFIED'
            ' OPERATIONAL CAPABILITY')
        limits = view['honest_limits']
        self.assertFalse(limits['live_voice_calling'])
        self.assertEqual(limits['speak_endpoint'],
                         'POST /api/voice/speak')
        self.assertIn('SystemTTSSynthesizer',
                      limits['synthesizer_of_record'])
        self.assertTrue(
            limits['translation'].startswith('NOT_BUILT'))


class TestSpeechRecords(SpeechTestBase):
    def test_speech_on_escalation_delivery_discipline(self):
        escalation = self.escalation()
        record = self.sentinel.record_speech(
            OPERATOR, 'ESCALATION',
            escalation['escalation_id'],
            'Emergency escalation. Assistance is on its'
            ' way.')
        # Born UNDELIVERED, on the native path, in
        # Sentinel's own voice.
        self.assertEqual(record['delivery_state'],
                         'UNDELIVERED')
        self.assertFalse(record['delivered'])
        self.assertIsNone(record['delivered_at'])
        self.assertEqual(record['native_path'],
                         'DAEDALUS_SYSTEM_TTS')
        self.assertEqual(record['voice_identity'],
                         'SANDERS_SENTINEL')
        # Only the recorded acknowledgment by
        # reference, naming the office of record,
        # delivers it.
        delivered = self.sentinel.confirm_speech_delivery(
            OPERATOR, record['speech_id'], 'ack-ref-1')
        self.assertEqual(delivered['delivery_state'],
                         'DELIVERED')
        self.assertEqual(delivered['acknowledged_office'],
                         'FOUNDER')
        self.assertEqual(
            delivered['delivery_confirmation_ref'],
            'ack-ref-1')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_speech_delivery(
                OPERATOR, record['speech_id'], 'ack-ref-2')
        # The escalation's own view carries its speech.
        view = self.sentinel.escalation_view(
            OPERATOR, 'OPERATOR', escalation['escalation_id'])
        self.assertEqual(len(view['speech_records']), 1)

    def test_speech_on_emergency_case(self):
        case = self.case()
        record = self.sentinel.record_speech(
            OPERATOR, 'EMERGENCY_CASE', case['case_id'],
            'Evacuation transport has been activated.')
        listed = self.sentinel.speech_records(
            OPERATOR, 'OPERATOR',
            subject_kind='EMERGENCY_CASE',
            subject_ref=case['case_id'])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['speech_id'],
                         record['speech_id'])
        view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(len(view['speech_records']), 1)

    def test_native_path_lock_and_validation(self):
        escalation = self.escalation()
        # A provider path is refused by name: Sentinel
        # speaks only through the native engine.
        with self.assertRaises(SandersSentinelDenied) as caught:
            self.sentinel.record_speech(
                OPERATOR, 'ESCALATION',
                escalation['escalation_id'], 'text',
                native_path='ELEVENLABS')
        self.assertIn('SPEECH_NATIVE_PATH_ONLY',
                      str(caught.exception))
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_speech(
                OPERATOR, 'ESCALATION', 'no-such-escalation',
                'text')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_speech(
                OPERATOR, 'ESCALATION',
                escalation['escalation_id'], 'x' * 5001)
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_speech(
                'not-the-operator', 'ESCALATION',
                escalation['escalation_id'], 'text')


class TestVoiceConversations(SpeechTestBase):
    def test_two_way_conversation_records(self):
        case = self.case()
        conversation = self.sentinel.open_voice_conversation(
            OPERATOR, 'EMERGENCY_CASE', case['case_id'], 'en')
        self.assertEqual(conversation['state'], 'OPEN')
        self.assertEqual(conversation['language'], 'en')
        self.assertEqual(conversation['voice_identity'],
                         'SANDERS_SENTINEL')
        self.assertEqual(conversation['native_path'],
                         'DAEDALUS_SYSTEM_TTS')
        # A conversation record is not a live call,
        # and never reads as one.
        self.assertFalse(conversation['live_call'])
        self.sentinel.record_voice_turn(
            OPERATOR, conversation['conversation_id'],
            'INBOUND', 'I need help leaving the house.')
        self.sentinel.record_voice_turn(
            OPERATOR, conversation['conversation_id'],
            'OUTBOUND', 'Transport is activated. Stay on'
            ' the line with me.')
        view = self.sentinel.voice_conversation_view(
            OPERATOR, 'OPERATOR',
            conversation['conversation_id'])
        self.assertEqual(
            [turn['direction'] for turn in view['turns']],
            ['INBOUND', 'OUTBOUND'])
        closed = self.sentinel.close_voice_conversation(
            OPERATOR, conversation['conversation_id'],
            'conversation-complete')
        self.assertEqual(closed['state'], 'CLOSED')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_voice_turn(
                OPERATOR, conversation['conversation_id'],
                'INBOUND', 'after closure')
        # The case view carries the conversation.
        case_view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(
            len(case_view['voice_conversations']), 1)

    def test_conversation_validation(self):
        case = self.case()
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.open_voice_conversation(
                OPERATOR, 'EMERGENCY_CASE', case['case_id'],
                'en', native_path='GOOGLE_TTS')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.open_voice_conversation(
                OPERATOR, 'EMERGENCY_CASE', 'no-such-case',
                'en')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.open_voice_conversation(
                'not-the-operator', 'EMERGENCY_CASE',
                case['case_id'], 'en')


class TestVoiceNeverGatesAndRecovery(SpeechTestBase):
    def test_voice_calling_readiness_not_connected(self):
        board = self.sentinel.readiness_view(
            OPERATOR, 'OPERATOR')
        states = {entry['capability']: entry['state']
                  for entry in board['capabilities']}
        self.assertEqual(states['VOICE_CALLING'],
                         'NOT_CONNECTED')

    def test_protective_action_never_consults_voice(self):
        # With no speech, no conversation, and voice
        # calling NOT_CONNECTED, the full protective
        # path proceeds immediately.
        case = self.case()
        self.sentinel.record_emergency_activation(
            OPERATOR, case['case_id'], 'RELOCATION',
            'godfather-transport-1', 'evacuation')
        self.sentinel.record_responder_coordination(
            OPERATOR, case['case_id'], 'FIRE',
            'city-fire-department', 'coordination')
        self.sentinel.record_escalation(
            OPERATOR, case['case_id'], 'escalation detail')
        view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(view['state'], 'OPEN')
        # The structural audit stands beside the
        # exercise: no assistance path references the
        # speech or conversation machinery.
        forbidden = ('record_speech', 'speech_records',
                     'voice_conversation',
                     'sanders_sentinel_speech_records',
                     'sanders_sentinel_voice_conversations')
        for name in ('record_emergency_signal',
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

    def test_voice_channel_failure_recovers_in_place(self):
        case = self.case()
        conversation = self.sentinel.open_voice_conversation(
            OPERATOR, 'EMERGENCY_CASE', case['case_id'], 'en')
        # An interrupted voice channel is a loss of
        # visibility on a communication channel,
        # recorded against the stage, and recovery is
        # attempted under the standing cross-cutting
        # rule -- while the case and its protective
        # action continue untouched.
        event = self.sentinel.record_loss_of_visibility(
            OPERATOR, 'COMMUNICATION_CHANNEL',
            conversation['conversation_id'],
            'voice channel interrupted', stage='COORDINATE')
        self.assertEqual(event['stage'], 'COORDINATE')
        attempt = self.sentinel.record_recovery_attempt(
            OPERATOR, event['event_id'],
            'RESTORE_CONNECTION', 'RESTORED',
            'voice channel restored; text and silent'
            ' channels stood available throughout')
        self.assertEqual(attempt['stage'], 'COORDINATE')
        view = self.sentinel.emergency_case_view(
            OPERATOR, 'OPERATOR', case['case_id'])
        self.assertEqual(view['state'], 'OPEN')
        conv = self.sentinel.voice_conversation_view(
            OPERATOR, 'OPERATOR',
            conversation['conversation_id'])
        self.assertEqual(conv['state'], 'OPEN')


if __name__ == '__main__':
    unittest.main()
