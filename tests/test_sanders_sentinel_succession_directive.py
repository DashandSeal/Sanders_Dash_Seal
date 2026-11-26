"""Tests for the Sanders Sentinel — Permanent Global
Bloodline Protection and Succession Directive wiring
(founder-established, effective 2026-11-26), including
the founder's addition of 2026-11-26 01:56 MST.

The Directive supplements and strengthens the
Permanent Bloodline Protection Directive; it amends
nothing. It expands Sanders Sentinel's guard set to
all supplemental Founder-authorized directives, adds
escalation delivery verification and the governed
escalation-authority succession, holds emergency
protective actions ungated by escalation, and sets
the fulfillment-verification standard the three
platforms' coordinated assistance is confirmed
against: recorded is not delivered. The founder's
addition carries Sentinel's dual nature: his private
duties to the Sanders bloodline stand alongside his
public-facing business model, neither diminishing
the other. These tests use only stdlib fakes and
temporary SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_sentinel_succession_directive -v
(from the repo root).
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_patriot_saint_service as patriot
from core_platform import sanders_sentinel_service as sentinel
from core_platform import the_godfather_service as godfather
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintDenied,
    SandersPatriotSaintService,
)
from core_platform.sanders_sentinel_service import (
    SandersSentinelDenied,
    SandersSentinelForbidden,
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherDenied,
    TheGodfatherService,
)

OPERATOR = 'founder-operator'
OTHER = 'someone-else'

NEW_GUARDED_DOCUMENTS = (
    'docs/PERMANENT_GLOBAL_BLOODLINE_PROTECTION_DIRECTIVES_2026-11-26.md',
    'docs/FOUNDER_AMENDMENT_ARTICLE_III_PATRIOT_SAINT_2026-11-26.md',
    'docs/SANDERS_SENTINEL_PROTECTION_SUCCESSION_DIRECTIVE_2026-11-26.md',
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


class SuccessionTestBase(unittest.TestCase):
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


class TestDirectiveOfRecord(SuccessionTestBase):
    def test_directive_carried_verbatim(self):
        text = sentinel.FOUNDER_SUCCESSION_DIRECTIVE_VERBATIM
        self.assertIn(
            'Permanent Global Bloodline Protection and'
            ' Succession Directive', text)
        self.assertIn(
            'Article I \u2014 Human Authority and'
            ' Succession', text)
        self.assertIn(
            'Article VI \u2014 Global and Generational'
            ' Continuity', text)
        self.assertIn(
            'Verify the successful delivery of critical'
            ' alerts', text)
        self.assertIn(
            "Patriot Saint's Founder-authorized"
            ' financial disbursement authority shall'
            ' remain intact.', text)
        self.assertTrue(
            text.endswith('The Sanders Way!'))

    def test_operational_standard_verbatim(self):
        self.assertEqual(
            sentinel.OPERATIONAL_STANDARD_VERBATIM,
            'A transportation record is not'
            ' transportation.\n'
            'A financial reserve record is not money.\n'
            'A disbursement record is not a payment.\n'
            'An attorney request is not legal'
            ' representation.\n'
            'An escalation record is not a delivered'
            ' emergency alert.\n'
            'Sanders Sentinel must be capable of'
            ' coordinating actual protection, not merely'
            ' documenting the need for protection.')

    def test_articles_v_vi_invariants_present(self):
        joined = '\n'.join(
            sentinel.SUCCESSION_DIRECTIVE_INVARIANTS)
        self.assertIn('Permanent non-diminishment', joined)
        self.assertIn('seven continents', joined)
        self.assertIn('Emergency non-obstruction', joined)
        view = SandersSentinelService.succession_directive_design_view()
        self.assertEqual(
            view['directive_verbatim'],
            sentinel.FOUNDER_SUCCESSION_DIRECTIVE_VERBATIM)
        self.assertEqual(
            view['operational_standard'],
            sentinel.OPERATIONAL_STANDARD_VERBATIM)
        design = SandersSentinelService.bloodline_design_view()
        self.assertIn('sentinel_succession_directive', design)

    def test_founder_addition_and_dual_nature(self):
        # The founder's addition of 2026-11-26 01:56 MST,
        # carried verbatim with the Directive.
        self.assertEqual(
            sentinel.FOUNDER_SUCCESSION_DIRECTIVE_ADDITION_VERBATIM,
            'His private duties to the Sanders bloodline'
            ' \u2075While keeping it public facing'
            ' business model too')
        # The dual-nature invariant, in the style of
        # Patriot Saint's BLOODLINE_DUAL_NATURE_RULING:
        # Sentinel keeps his public-facing business model
        # alongside his private bloodline duties, and
        # neither purpose diminishes the other.
        self.assertEqual(
            sentinel.SUCCESSION_DUAL_NATURE_RULING,
            'Sanders Sentinel must remain both a'
            ' public-facing business and a permanent'
            ' protective resource for the Sanders'
            ' bloodline. Neither purpose should diminish'
            ' the other.')
        view = SandersSentinelService.succession_directive_design_view()
        self.assertEqual(
            view['dual_nature_ruling'],
            sentinel.SUCCESSION_DUAL_NATURE_RULING)
        self.assertEqual(
            view['founder_addition_verbatim'],
            sentinel.FOUNDER_SUCCESSION_DIRECTIVE_ADDITION_VERBATIM)


class TestGuardSetExpansion(unittest.TestCase):
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

    def test_watch_set_includes_supplemental_directives(self):
        watched = {entry['document']: entry['required']
                   for entry in sentinel.BLOODLINE_WATCH_SET}
        for document in NEW_GUARDED_DOCUMENTS:
            self.assertIn(document, watched)
            self.assertTrue(watched[document])
        # The registry stays optional, NOT_LANDED, and
        # confidential — unchanged by the expansion.
        self.assertFalse(
            watched['docs/SANDERS_BLOODLINE_REGISTRY.md'])

    def test_clean_cycle_then_tamper_each_new_document(self):
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['documents_sound'], 6)
        self.assertEqual(cycle['findings_raised'], 0)
        self.assertEqual(cycle['documents_not_landed'], 1)
        for document in NEW_GUARDED_DOCUMENTS:
            path = self.documents[document]
            original = path.read_bytes()
            with open(path, 'ab') as handle:
                handle.write(b'x')
            cycle = self.service.verify_bloodline_records(
                OPERATOR)
            self.assertEqual(cycle['findings_raised'], 1,
                             document)
            path.write_bytes(original)
        coverage = self.service.bloodline_coverage(
            OPERATOR, 'OPERATOR')
        self.assertEqual(coverage['findings_open'], 3)


class TestEscalationDelivery(SuccessionTestBase):
    def test_undelivered_stays_open_and_unclosable(self):
        esc = self.sentinel.record_escalation(
            OPERATOR, 'finding-ref-1', 'detail-1',
            critical=True)
        self.assertEqual(esc['delivery_state'], 'UNDELIVERED')
        self.assertFalse(esc['delivered'])
        self.assertEqual(esc['closure_state'], 'OPEN')
        with self.assertRaises(SandersSentinelDenied) as ctx:
            self.sentinel.close_escalation(
                OPERATOR, esc['escalation_id'], 'RESOLVED',
                'reason-1')
        self.assertIn(
            'ESCALATION_UNDELIVERED_MAY_NOT_BE_CLOSED',
            str(ctx.exception))
        listing = self.sentinel.escalations(OPERATOR, 'OPERATOR')
        self.assertEqual(
            listing['escalations'][0]['delivery_state'],
            'UNDELIVERED')
        status = self.sentinel.status()
        section = status['bloodline_succession_directive']
        self.assertEqual(section['undelivered_critical_open'], 1)

    def test_suppression_closure_refused_by_name(self):
        esc = self.sentinel.record_escalation(
            OPERATOR, 'finding-ref-2', 'detail-2',
            critical=True)
        self.sentinel.confirm_escalation_delivery(
            OPERATOR, esc['escalation_id'], 'ack-1')
        for decision in ('IGNORED', 'SUPPRESSED',
                         'CONCEALED', 'DELAYED'):
            with self.assertRaises(SandersSentinelDenied) as ctx:
                self.sentinel.close_escalation(
                    OPERATOR, esc['escalation_id'], decision,
                    'reason-2')
            self.assertIn('ESCALATION_MAY_NOT_BE_SUPPRESSED',
                          str(ctx.exception))

    def test_delivery_confirmation_then_closure(self):
        esc = self.sentinel.record_escalation(
            OPERATOR, 'finding-ref-3', 'detail-3')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.close_escalation(
                OPERATOR, esc['escalation_id'], 'RESOLVED', '')
        done = self.sentinel.confirm_escalation_delivery(
            OPERATOR, esc['escalation_id'], 'ack-ref-3')
        self.assertEqual(done['delivery_state'], 'DELIVERED')
        self.assertEqual(done['acknowledged_office'], 'FOUNDER')
        self.assertEqual(
            done['delivery_confirmation_ref'], 'ack-ref-3')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_escalation_delivery(
                OPERATOR, esc['escalation_id'], 'ack-again')
        closed = self.sentinel.close_escalation(
            OPERATOR, esc['escalation_id'], 'RESOLVED',
            'reason-3')
        self.assertEqual(closed['closure_state'], 'CLOSED')
        self.assertEqual(closed['closed_by'], OPERATOR)

    def test_escalation_writes_are_operator_only(self):
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_escalation(
                OTHER, 'finding-ref-4', 'detail-4')
        esc = self.sentinel.record_escalation(
            OPERATOR, 'finding-ref-4', 'detail-4')
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.confirm_escalation_delivery(
                OTHER, esc['escalation_id'], 'ack-4')


class TestEscalationAuthoritySuccession(SuccessionTestBase):
    def test_authority_held_by_founder_by_default(self):
        view = self.sentinel.escalation_authority(
            OPERATOR, 'OPERATOR')
        self.assertEqual(view['holder_office'], 'FOUNDER')
        self.assertEqual(view['state'], 'FOUNDER_LIFETIME')
        self.assertEqual(view['scope_ref'],
                         sentinel.SUCCESSION_SCOPE)

    def test_interception_refused_and_raised_as_finding(self):
        with self.assertRaises(SandersSentinelForbidden) as ctx:
            self.sentinel.attempt_escalation_authority_change(
                OTHER, 'claim-ref-1')
        self.assertIn('ESCALATION_AUTHORITY_NOT_ASSUMABLE',
                      str(ctx.exception))
        records = self.sentinel.records_list(OPERATOR, 'OPERATOR')
        attempts = [r for r in records
                    if 'ESCALATION_AUTHORITY_INTERCEPTION_ATTEMPT'
                    in r['signal_refs']]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]['scope_ref'],
                         sentinel.BLOODLINE_GOVERNANCE_SCOPE)
        self.assertEqual(attempts[0]['status'], 'REQUESTED')
        view = self.sentinel.escalation_authority(
            OPERATOR, 'OPERATOR')
        self.assertEqual(view['holder_office'], 'FOUNDER')

    def test_succession_event_recording(self):
        with self.assertRaises(SandersSentinelForbidden):
            self.sentinel.record_succession_event(
                OTHER, 'event-1', 'evidence-1')
        view = self.sentinel.record_succession_event(
            OPERATOR, 'event-1', 'evidence-1')
        # The successor is the OFFICE — never a named
        # person in this record.
        self.assertEqual(view['holder_office'], 'BLOODLINE_CEO')
        self.assertEqual(view['state'], 'SUCCESSION_RECORDED')
        self.assertEqual(view['succession_event_ref'], 'event-1')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_succession_event(
                OPERATOR, 'event-2', 'evidence-2')
        esc = self.sentinel.record_escalation(
            OPERATOR, 'finding-ref-5', 'detail-5', critical=True)
        self.assertEqual(esc['authority_office'], 'BLOODLINE_CEO')
        done = self.sentinel.confirm_escalation_delivery(
            OPERATOR, esc['escalation_id'], 'ack-5')
        self.assertEqual(done['acknowledged_office'],
                         'BLOODLINE_CEO')


class TestEmergencyNonObstruction(SuccessionTestBase):
    def test_emergency_action_ungated_by_escalation(self):
        esc = self.sentinel.record_escalation(
            OPERATOR, 'threat-1', 'detail-t1', critical=True,
            emergency=True)
        # The escalation stands UNDELIVERED; the
        # already-authorized emergency protective action
        # is recorded immediately regardless (Article IV).
        action = self.sentinel.record_emergency_protective_action(
            OPERATOR, 'evacuation-1', 'detail-a1',
            'founder-authorization-1',
            escalation_ref=esc['escalation_id'])
        self.assertFalse(action['gated_on_escalation_delivery'])
        self.assertEqual(action['escalation_ref'],
                         esc['escalation_id'])
        # Delivery verification still records after the
        # fact through the ordinary path.
        done = self.sentinel.confirm_escalation_delivery(
            OPERATOR, esc['escalation_id'], 'ack-after')
        self.assertEqual(done['delivery_state'], 'DELIVERED')


class TestFulfillmentRegister(SuccessionTestBase):
    def test_recorded_but_unconfirmed_raises_and_clears(self):
        exp = self.sentinel.record_fulfillment_expectation(
            OPERATOR, 'sanders_patriot_saint', 'matter-9',
            'DISBURSEMENT', 'terms-9', 1500.0)
        self.assertEqual(exp['state'], 'RECORDED_UNFULFILLED')
        # Terms not yet run: no finding.
        result = self.sentinel.verify_fulfillment(OPERATOR)
        self.assertEqual(result['findings_raised'], [])
        # Terms run with delivery unconfirmed: the
        # UNFULFILLED_ASSISTANCE finding is raised.
        self.now[0] = 2000.0
        result = self.sentinel.verify_fulfillment(OPERATOR)
        self.assertEqual(len(result['findings_raised']), 1)
        # Deduped on a second cycle.
        result = self.sentinel.verify_fulfillment(OPERATOR)
        self.assertEqual(result['findings_raised'], [])
        view = self.sentinel.fulfillment_view(OPERATOR, 'OPERATOR')
        self.assertEqual(view['unfulfilled_findings_open'], 1)
        self.assertEqual(view['overdue_unfulfilled'], 1)
        records = self.sentinel.records_list(OPERATOR, 'OPERATOR')
        findings = [r for r in records
                    if 'UNFULFILLED_ASSISTANCE' in r['signal_refs']]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['subject_ref'], 'matter-9')
        # A confirmed delivery clears the finding.
        done = self.sentinel.confirm_fulfillment(
            OPERATOR, exp['expectation_id'], 'delivery-9',
            'deposit posted to the member account')
        self.assertEqual(done['state'], 'FULFILLED')
        self.assertEqual(
            done['delivered_detail_ref'],
            'deposit posted to the member account')
        view = self.sentinel.fulfillment_view(OPERATOR, 'OPERATOR')
        self.assertEqual(view['unfulfilled_findings_open'], 0)
        self.assertEqual(view['by_state'], {'FULFILLED': 1})
        records = self.sentinel.records_list(OPERATOR, 'OPERATOR')
        findings = [r for r in records
                    if 'UNFULFILLED_ASSISTANCE' in r['signal_refs']]
        self.assertEqual(findings[0]['status'], 'OUTCOME_RECORDED')
        self.assertEqual(findings[0]['outcome'],
                         'FULFILLMENT_CONFIRMED')

    def test_confirmation_must_name_what_was_delivered(self):
        exp = self.sentinel.record_fulfillment_expectation(
            OPERATOR, 'the_godfather', 'matter-7',
            'TRANSPORTATION', 'terms-7', 1500.0)
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_fulfillment(
                OPERATOR, exp['expectation_id'], 'delivery-7', '')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_fulfillment_expectation(
                OPERATOR, 'not-a-platform', 'matter-8',
                'TRANSPORTATION', 'terms-8', 1500.0)
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_fulfillment_expectation(
                OPERATOR, 'the_godfather', 'matter-8',
                'NOT_A_KIND', 'terms-8', 1500.0)


class TestPlatformFulfillment(SuccessionTestBase):
    def test_patriot_matter_fulfillment(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'LEGAL_REPRESENTATION_COORDINATION',
            'member-2', 'detail-2')
        self.assertEqual(matter['fulfillment']['state'],
                         'RECORDED_UNFULFILLED')
        # Nothing recorded yet: nothing to fulfill.
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.confirm_matter_fulfillment(
                OPERATOR, matter['matter_id'], 'delivery-p')
        self.patriot.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.patriot.record_bloodline_coordination(
            OPERATOR, matter['matter_id'], 'counsel-located-1')
        done = self.patriot.confirm_matter_fulfillment(
            OPERATOR, matter['matter_id'], 'delivery-p')
        self.assertEqual(done['fulfillment']['state'],
                         'FULFILLED')
        remit = self.patriot.bloodline_remit(OPERATOR, 'OPERATOR')
        self.assertEqual(remit['matters_fulfilled'], 1)

    def test_patriot_disbursement_then_fulfillment(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'INCARCERATED_FUNDS_COORDINATION',
            'member-3', 'detail-3')
        self.patriot.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-req-1')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'the_godfather',
            'godfather-det-1')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'sanders_sentinel',
            'sentinel-det-1')
        disbursement = self.patriot.execute_disbursement(
            OPERATOR, matter['matter_id'],
            'INCARCERATED_MEMBER_ACCOUNT_DEPOSITS',
            'amount-1', 'payee-1')
        # Disbursement authority under the Amendment is
        # intact — and a disbursement record is not a
        # payment: fulfillment still stands unconfirmed.
        self.assertTrue(disbursement['funds_disbursed'])
        self.assertEqual(disbursement['fulfillment_state'],
                         'RECORDED_UNFULFILLED')
        done = self.patriot.confirm_matter_fulfillment(
            OPERATOR, matter['matter_id'], 'deposit-confirmed-1')
        self.assertEqual(done['fulfillment']['state'],
                         'FULFILLED')
        listing = self.patriot.bloodline_disbursements_list(
            OPERATOR, 'OPERATOR')
        self.assertEqual(listing[0]['fulfillment_state'],
                         'FULFILLED')

    def test_godfather_transport_and_reserve_fulfillment(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'MEDICAL_TRANSPORTATION', 'member-1',
            'detail-1')
        self.assertEqual(matter['fulfillment']['state'],
                         'RECORDED_UNFULFILLED')
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.confirm_transport_fulfillment(
                OPERATOR, matter['matter_id'], 'delivery-1')
        self.godfather.transport_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.godfather.record_transport_coordination(
            OPERATOR, matter['matter_id'], 'coord-1')
        done = self.godfather.confirm_transport_fulfillment(
            OPERATOR, matter['matter_id'], 'delivery-1')
        self.assertEqual(done['fulfillment']['state'],
                         'FULFILLED')
        reserve = self.godfather.designate_reserve(
            OPERATOR, 'desig-1', 'purpose-1')
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.confirm_reserve_fulfillment(
                OPERATOR, reserve['reserve_id'], 'delivery-r')
        self.godfather.reserve_action(
            OPERATOR, reserve['reserve_id'], 'approve')
        self.godfather.record_counterpart_reserve_approval(
            OPERATOR, reserve['reserve_id'], 'sentinel-approval-1')
        done = self.godfather.confirm_reserve_fulfillment(
            OPERATOR, reserve['reserve_id'], 'delivery-r')
        self.assertEqual(done['fulfillment']['state'],
                         'FULFILLED')
        self.assertFalse(done['funds_held'])
        remit = self.godfather.bloodline_remit(OPERATOR, 'OPERATOR')
        self.assertEqual(remit['transport_matters_fulfilled'], 1)
        self.assertEqual(remit['reserves_fulfilled'], 1)

    def test_sentinel_own_reserve_fulfillment(self):
        reserve = self.sentinel.designate_reserve(
            OPERATOR, 'desig-1', 'purpose-1')
        self.assertEqual(reserve['fulfillment']['state'],
                         'RECORDED_UNFULFILLED')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.confirm_reserve_fulfillment(
                OPERATOR, reserve['reserve_id'], 'delivery-r')
        self.sentinel.reserve_action(
            OPERATOR, reserve['reserve_id'], 'approve')
        self.sentinel.record_counterpart_reserve_approval(
            OPERATOR, reserve['reserve_id'], 'godfather-approval-1')
        done = self.sentinel.confirm_reserve_fulfillment(
            OPERATOR, reserve['reserve_id'], 'delivery-r')
        self.assertEqual(done['fulfillment']['state'],
                         'FULFILLED')
        self.assertFalse(done['funds_held'])
        view = self.sentinel.fulfillment_view(OPERATOR, 'OPERATOR')
        self.assertEqual(
            view['own_reserves'][0]['fulfillment']['state'],
            'FULFILLED')


if __name__ == '__main__':
    unittest.main()
