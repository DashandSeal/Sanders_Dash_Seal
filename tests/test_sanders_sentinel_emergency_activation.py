"""Tests for the Sanders Sentinel -- Emergency
Activation duties (founder additions No. 2 and
No. 3 to the Permanent Global Bloodline Protection
and Succession Directive, 2026-11-26).

Addition No. 2 (02:29 MST) gave items 4-12 of the
Emergency Activation list with its closing line;
addition No. 3 (02:31 MST) gave the head of the
list -- its title and items 1-3 (its item 4
arrived truncated at "Authorized"; item 4's
complete text stands in addition No. 2). Together
they are the complete list, items 1-12: eight
authorized detection channels, three activations
run by reference into the Godfather's and Patriot
Saint's own segregated machinery and the
established joint funding authority, and
continuous response -- a case closes only when
the arrival of assistance stands verified and the
resolution of the immediate danger stands
recorded. These tests use only stdlib fakes and
temporary SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_emergency_activation -v
(from the repo root).
"""

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


class EmergencyTestBase(unittest.TestCase):
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

    def open_case(self, kind='SOS_BUTTON', **kwargs):
        source = sentinel.EMERGENCY_SIGNAL_SOURCES[kind]
        fields = {
            'source_ref': f'source-{kind.lower()}',
            'authorization_ref': 'authorization-of-record',
            'member_ref': 'bloodline-member-ref',
            'detail_ref': 'signal-detail-ref',
        }
        if kind == 'DISASTER_WARNING_EXPOSURE':
            fields['authorized_location_ref'] = (
                'authorized-location-of-record')
        fields.update(kwargs)
        return self.sentinel.record_emergency_signal(
            OPERATOR, kind, source, **fields)


class TestDutiesOfRecord(EmergencyTestBase):
    def test_addition_no_2_carried_verbatim(self):
        text = (
            sentinel.FOUNDER_EMERGENCY_ACTIVATION_ADDITION_NO_2_VERBATIM)
        self.assertTrue(text.startswith(
            '4. Medical emergency detection: Authorized'
            ' medical devices transmit emergency alerts.'))
        self.assertIn(
            "9. Emergency relocation: Sentinel activates"
            " the Godfather's transportation and"
            " evacuation capabilities.", text)
        self.assertIn(
            '12. Continuous emergency response: Sentinel'
            ' verifies whether assistance has arrived and'
            ' continues coordinating protection until the'
            ' immediate danger is resolved.', text)
        self.assertTrue(text.endswith(
            'While maintaining his public facing'
            ' business model'))

    def test_addition_no_3_carried_verbatim(self):
        text = (
            sentinel.FOUNDER_EMERGENCY_ACTIVATION_ADDITION_NO_3_VERBATIM)
        self.assertTrue(text.startswith(
            'Sanders Sentinel \u2014 Emergency Activation\n'
            '1. SOS button: A bloodline member requests'
            ' immediate emergency assistance.'))
        self.assertIn(
            '2. Voice activation: Sentinel receives a'
            ' spoken distress command.', text)
        self.assertIn(
            '3. Silent distress signal: Sentinel receives'
            ' an emergency request when speaking is'
            ' unsafe.', text)
        # Item 4 arrived truncated at "Authorized", as
        # given; its complete text stands in addition
        # No. 2 and is never completed here by invention.
        self.assertTrue(text.endswith(
            '4. Medical emergency detection: Authorized'))

    def test_design_view_surfaces_duties(self):
        view = (
            SandersSentinelService.emergency_activation_design_view())
        self.assertEqual(
            view['title'], 'Sanders Sentinel \u2014 Emergency Activation')
        self.assertEqual(
            view['addition_no_2_verbatim'],
            sentinel.FOUNDER_EMERGENCY_ACTIVATION_ADDITION_NO_2_VERBATIM)
        self.assertEqual(
            view['addition_no_3_verbatim'],
            sentinel.FOUNDER_EMERGENCY_ACTIVATION_ADDITION_NO_3_VERBATIM)
        self.assertEqual(len(view['signal_kinds']), 8)
        # The closing line's dual nature is referenced
        # from the standing ruling, never duplicated.
        self.assertEqual(
            view['dual_nature_ruling'],
            sentinel.SUCCESSION_DUAL_NATURE_RULING)
        succession = (
            SandersSentinelService.succession_directive_design_view())
        self.assertEqual(
            succession['emergency_activation']['title'],
            view['title'])
        joined = '\n'.join(view['invariants'])
        self.assertIn('never requires speech or sound', joined)
        self.assertIn('no live voice path', joined)
        self.assertIn('designated counterpart', joined)


class TestSignalIntake(EmergencyTestBase):
    def test_all_eight_channels_open_cases(self):
        for kind in sentinel.EMERGENCY_SIGNAL_KINDS:
            case = self.open_case(kind)
            self.assertEqual(case['signal_kind'], kind)
            self.assertEqual(case['state'], 'OPEN')
            self.assertTrue(case['open'])
            self.assertFalse(case['arrival_verified'])
            self.assertEqual(
                case['source_kind'],
                sentinel.EMERGENCY_SIGNAL_SOURCES[kind])
        listing = self.sentinel.emergency_cases(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(listing['cases']), 8)
        self.assertEqual(listing['open_total'], 8)
        self.assertEqual(
            set(listing['by_signal_kind']),
            set(sentinel.EMERGENCY_SIGNAL_KINDS))

    def test_unauthorized_source_refused_by_name(self):
        for kind, source in (
                sentinel.EMERGENCY_SIGNAL_SOURCES.items()):
            wrong = ('PUBLIC_EMERGENCY_WARNING'
                     if source != 'PUBLIC_EMERGENCY_WARNING'
                     else 'BLOODLINE_MEMBER')
            with self.assertRaises(
                    SandersSentinelDenied) as ctx:
                self.sentinel.record_emergency_signal(
                    OPERATOR, kind, wrong, 'src', 'auth',
                    'member', 'detail',
                    authorized_location_ref='loc-ref')
            self.assertIn(
                'EMERGENCY_SIGNAL_SOURCE_NOT_AUTHORIZED',
                str(ctx.exception), kind)

    def test_unknown_kind_and_non_operator_refused(self):
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_emergency_signal(
                OPERATOR, 'SMOKE_SIGNAL', 'BLOODLINE_MEMBER',
                'src', 'auth', 'member', 'detail')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_emergency_signal(
                OTHER, 'SOS_BUTTON', 'BLOODLINE_MEMBER',
                'src', 'auth', 'member', 'detail')

    def test_silent_distress_needs_no_speech(self):
        # Item 3: the silent channel is complete as
        # received, in silence -- no spoken content,
        # transcript, or sound is recorded or required.
        case = self.open_case('SILENT_DISTRESS_SIGNAL')
        self.assertEqual(case['signal_kind'],
                         'SILENT_DISTRESS_SIGNAL')
        events = [fields for event, fields in self.audit.events
                  if event.endswith('EMERGENCY_SIGNAL_RECORDED')]
        self.assertTrue(events)
        for fields in events:
            self.assertNotIn('transcript', fields)
            self.assertNotIn('audio', fields)
            self.assertNotIn('spoken_text', fields)

    def test_disaster_exposure_needs_authorized_location(self):
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_emergency_signal(
                OPERATOR, 'DISASTER_WARNING_EXPOSURE',
                'PUBLIC_EMERGENCY_WARNING', 'warning-1',
                'auth', 'member', 'detail')
        self.assertIn(
            'AUTHORIZED_LOCATION_INFORMATION_REQUIRED',
            str(ctx.exception))
        case = self.open_case('DISASTER_WARNING_EXPOSURE')
        self.assertEqual(case['authorized_location_ref'],
                         'authorized-location-of-record')
        # Only the reference of record is held -- no
        # coordinates, no tracking data.
        self.assertNotIn('latitude', case)
        self.assertNotIn('longitude', case)
        self.assertIn(
            'without unauthorized personal tracking',
            sentinel.EMERGENCY_NO_TRACKING_INVARIANT)


class TestActivations(EmergencyTestBase):
    def test_relocation_activates_godfather_matter(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'EMERGENCY_EVACUATION_ARRANGEMENT',
            'bloodline-member-ref', 'evacuation-detail')
        case = self.open_case('MEDICAL_DEVICE_ALERT')
        activation = self.sentinel.record_emergency_activation(
            OPERATOR, case['case_id'], 'RELOCATION',
            matter['matter_id'], 'evacuation-detail')
        self.assertEqual(activation['target_platform'],
                         'the_godfather')
        self.assertEqual(activation['target_ref'],
                         matter['matter_id'])
        self.assertFalse(
            activation['gated_on_escalation_delivery'])

    def test_legal_activates_patriot_saint_matter(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'EMERGENCY_LEGAL_ASSISTANCE',
            'bloodline-member-ref', 'legal-detail')
        case = self.open_case('FAMILY_REPORT')
        activation = self.sentinel.record_emergency_activation(
            OPERATOR, case['case_id'], 'LEGAL',
            matter['matter_id'], 'legal-detail')
        self.assertEqual(activation['target_platform'],
                         'sanders_patriot_saint')
        self.assertEqual(activation['target_ref'],
                         matter['matter_id'])

    def test_funding_exercises_joint_authority(self):
        request = self.sentinel.open_funding_request(
            OPERATOR, 'emergency-matter-ref',
            'emergency-funding-detail')
        self.sentinel.record_funding_determination(
            OPERATOR, request['request_id'], 'approve')
        case = self.open_case('MISSED_CHECK_IN')
        activation = self.sentinel.record_emergency_activation(
            OPERATOR, case['case_id'], 'FUNDING',
            request['request_id'], 'emergency-funding-detail')
        self.assertEqual(activation['activation_kind'],
                         'FUNDING')
        self.assertEqual(activation['target_ref'],
                         request['request_id'])
        # No new money authority: Sentinel still
        # disburses nothing, and the case records hold
        # no funds.
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.disburse_funds(OPERATOR)
        status = self.sentinel.status()
        self.assertFalse(
            status['emergency_activation']['funds_disbursed'])

    def test_activation_requires_open_case(self):
        case = self.open_case()
        self.sentinel.confirm_emergency_arrival(
            OPERATOR, case['case_id'], 'arrival-1',
            'assistance on scene')
        self.sentinel.close_emergency_case(
            OPERATOR, case['case_id'], 'resolution-1')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.record_emergency_activation(
                OPERATOR, case['case_id'], 'LEGAL',
                'matter-ref', 'detail')
        self.assertIn('EMERGENCY_CASE_NOT_OPEN',
                      str(ctx.exception))


class TestContinuousResponse(EmergencyTestBase):
    def test_case_closes_only_on_verified_arrival(self):
        case = self.open_case()
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.close_emergency_case(
                OPERATOR, case['case_id'], 'resolution-1')
        self.assertIn(
            'EMERGENCY_ARRIVAL_UNVERIFIED_MAY_NOT_BE_CLOSED',
            str(ctx.exception))
        arrived = self.sentinel.confirm_emergency_arrival(
            OPERATOR, case['case_id'], 'arrival-ref-1',
            'ambulance arrived; member transported')
        self.assertTrue(arrived['arrival_verified'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_emergency_arrival(
                OPERATOR, case['case_id'], 'arrival-again',
                'duplicate')
        closed = self.sentinel.close_emergency_case(
            OPERATOR, case['case_id'], 'resolution-ref-1')
        self.assertEqual(closed['state'], 'CLOSED_RESOLVED')
        self.assertFalse(closed['open'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.close_emergency_case(
                OPERATOR, case['case_id'], 'resolution-2')

    def test_unverified_past_terms_raises_finding(self):
        case = self.open_case(assistance_due_at=1500.0)
        self.now[0] = 1600.0
        cycle = self.sentinel.verify_emergency_cases(OPERATOR)
        self.assertEqual(len(cycle['findings_raised']), 1)
        self.assertEqual(cycle['overdue_unverified'], 1)
        # Deduped per case on a second cycle.
        cycle = self.sentinel.verify_emergency_cases(OPERATOR)
        self.assertEqual(cycle['findings_raised'], [])
        # The finding is a fulfillment-scope watch
        # record carrying the UNFULFILLED_ASSISTANCE
        # signal -- the same discipline as the
        # fulfillment register.
        records = self.sentinel.records_list(
            OPERATOR, 'OPERATOR')
        findings = [r for r in records
                    if r['scope_ref'] == 'FULFILLMENT_VERIFICATION']
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['subject_ref'],
                         case['case_id'])
        # A confirmed arrival decides the finding.
        self.sentinel.confirm_emergency_arrival(
            OPERATOR, case['case_id'], 'arrival-late',
            'assistance arrived late but arrived')
        records = self.sentinel.records_list(
            OPERATOR, 'OPERATOR')
        decided = [r for r in records
                   if r['record_id'] == findings[0]['record_id']]
        self.assertEqual(decided[0]['status'],
                         'OUTCOME_RECORDED')
        self.assertEqual(decided[0]['outcome'],
                         'EMERGENCY_ASSISTANCE_ARRIVED')

    def test_status_counts_emergency_activation(self):
        self.open_case('SOS_BUTTON')
        self.open_case('RTSA_PLATFORM_SIGNAL')
        status = self.sentinel.status()
        section = status['emergency_activation']
        self.assertEqual(section['cases_total'], 2)
        self.assertEqual(section['cases_open'], 2)
        self.assertEqual(
            section['cases_by_signal_kind']['SOS_BUTTON'], 1)
        self.assertEqual(
            section['cases_by_signal_kind']
            ['RTSA_PLATFORM_SIGNAL'], 1)
        self.assertEqual(section['activations_total'], 0)
        self.assertFalse(section['funds_held'])


if __name__ == '__main__':
    unittest.main()
