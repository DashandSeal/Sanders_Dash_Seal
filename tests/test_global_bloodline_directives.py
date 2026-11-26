"""Tests for the Permanent Global Bloodline Protection
Directives wiring (founder-established, effective
2026-11-26) across Godfather, Sanders Sentinel, and
Sanders Patriot Saint.

The Directives supplement the Permanent Bloodline
Protection Directive; they do not amend it. Funding
approval is a recorded determination requiring BOTH
Godfather's and Sanders Sentinel's determinations;
Patriot Saint's matters read NOT FUNDED until both
determinations are recorded against them; Godfather
and Sanders Sentinel disburse and hold no funds, and
reserves are a register of designations and joint
approvals. Under the Founder's Amendment to Article
III (2026-11-26), Patriot Saint disburses for his
assigned private duties against the recorded joint
approval, through a governed disbursement record.
These tests use only stdlib fakes and temporary
SQLite files: no network, no keys.
Run: python3 -m unittest tests.test_global_bloodline_directives -v
(from the repo root).
"""

import hashlib
import json
import sqlite3
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
    SandersSentinelService,
)
from core_platform.the_godfather_service import (
    TheGodfatherDenied,
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


class DirectivesTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.audit = FakeAudit()
        self.godfather = TheGodfatherService(
            root / 'the_godfather.db',
            operator_verifier=_verifier, audit=self.audit)
        self.sentinel = SandersSentinelService(
            root / 'sanders_sentinel.db',
            operator_verifier=_verifier, audit=self.audit)
        self.patriot = SandersPatriotSaintService(
            root / 'sanders_patriot_saint.db',
            operator_verifier=_verifier, audit=self.audit)


class TestRulingsOfRecord(unittest.TestCase):
    def test_article_i_carried_verbatim_by_godfather(self):
        text = godfather.FOUNDER_DIRECTIVES_ARTICLE_I_VERBATIM
        self.assertIn('ARTICLE I \u2014 GODFATHER', text)
        self.assertIn(
            'Godfather shall maintain its own independent'
            ' public-facing commercial business model',
            text)
        for bullet in (
                'approve all funding necessary for Patriot'
                ' Saint to fulfill its private duties',
                'Acquiring ground, air, rail and water'
                ' transportation',
                'Providing emergency and medical'
                ' transportation',
                'Arranging emergency evacuations and'
                ' repatriation',
                'Securing transportation insurance,'
                ' maintenance, repairs and replacement',
                'Establishing and maintaining emergency'
                ' financial reserves alongside Sanders'
                ' Sentinel'):
            self.assertIn(bullet, text)
        self.assertIn('PERMANENT GLOBAL BLOODLINE'
                      ' PROTECTION DIRECTIVES',
                      ' '.join(godfather.__doc__.split()))
        self.assertIn('ARTICLE I assigns this platform',
                      ' '.join(godfather.__doc__.split()))

    def test_article_ii_carried_verbatim_by_sentinel(self):
        text = sentinel.FOUNDER_DIRECTIVES_ARTICLE_II_VERBATIM
        self.assertIn('ARTICLE II \u2014 SANDERS SENTINEL',
                      text)
        self.assertIn(
            'shall permanently retain all its original'
            ' responsibilities and protective duties',
            text)
        for bullet in (
                'Working alongside Godfather to approve all'
                ' funding necessary for Patriot Saint',
                'Establishing and maintaining emergency'
                ' financial reserves alongside Godfather',
                'Coordinating with Godfather and Patriot'
                ' Saint to ensure the continuous protection,'
                ' security and welfare of the Sanders'
                ' bloodline',
                'Preserving and carrying out all previously'
                ' assigned bloodline protection'
                ' responsibilities'):
            self.assertIn(bullet, text)

    def test_article_iii_carried_verbatim_by_patriot(self):
        text = patriot.FOUNDER_DIRECTIVES_ARTICLE_III_VERBATIM
        self.assertIn('ARTICLE III \u2014 PATRIOT SAINT', text)
        for bullet in (
                'Providing assistance whenever a Sanders'
                ' bloodline member encounters legal'
                ' difficulties',
                'Securing attorneys and arranging legal'
                ' representation',
                'Providing emergency legal assistance',
                'Providing bail and bond assistance',
                'Placing money on the accounts of'
                ' incarcerated Sanders bloodline members',
                'Paying tickets and fines',
                'Obtaining legal information, resources and'
                ' necessary assistance',
                'Coordinating with Godfather and Sanders'
                ' Sentinel to secure all funding necessary'):
            self.assertIn(bullet, text)
        # The 2026-11-25 rulings stand beside Article III,
        # unreplaced.
        self.assertIn('putting money on any of my bloodline',
                      patriot.FOUNDER_RULING_BLOODLINE_ROLE)
        self.assertEqual(len(patriot.BLOODLINE_DUTIES), 5)

    def test_articles_iv_vi_carried_by_all_three(self):
        for module in (godfather, sentinel, patriot):
            text = module.FOUNDER_DIRECTIVES_ARTICLES_IV_VI_VERBATIM
            self.assertIn('ARTICLE IV \u2014 GLOBAL BY DESIGN',
                          text)
            self.assertIn('across all seven continents', text)
            self.assertIn(
                'ARTICLE V \u2014 PERMANENT BLOODLINE'
                ' EXCLUSIVITY', text)
            self.assertIn(
                'ARTICLE VI \u2014 PRESERVATION OF ORIGINAL'
                ' AUTHORITY AND PURPOSE', text)
            self.assertIn('without merging', text)
            invariants = ' '.join(
                module.GLOBAL_DIRECTIVES_INVARIANTS)
            self.assertIn('Global By Design', invariants)
            self.assertIn('bloodline exclusivity', invariants)
            self.assertIn('disburse and hold no funds',
                          invariants)
            self.assertIn('Patriot Saint alone disburses',
                          invariants)
            self.assertEqual(module.DIRECTIVES_EFFECTIVE_DATE,
                             '2026-11-26')

    def test_design_views_carry_the_directives(self):
        g = TheGodfatherService.bloodline_design_view()
        self.assertIn('ARTICLE I \u2014 GODFATHER',
                      g['article_i_verbatim'])
        self.assertFalse(g['funds_disbursed'])
        self.assertFalse(g['funds_held'])
        self.assertTrue(g['segregated_store'])
        s = SandersSentinelService.directives_design_view()
        self.assertIn('ARTICLE II \u2014 SANDERS SENTINEL',
                      s['article_ii_verbatim'])
        p = SandersPatriotSaintService.directives_design_view()
        self.assertIn('ARTICLE III \u2014 PATRIOT SAINT',
                      p['article_iii_verbatim'])
        design = SandersPatriotSaintService.bloodline_design_view()
        self.assertIn('global_directives', design)


class TestGodfatherTransport(DirectivesTestBase):
    def test_matter_born_awaiting_human_review(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'TRANSPORTATION_ACQUISITION_AIR',
            'bloodline-member-ref-1', 'matter-detail-ref-1')
        self.assertEqual(matter['status'],
                         'AWAITING_HUMAN_REVIEW')
        self.assertEqual(matter['scope_ref'],
                         'GLOBAL_BLOODLINE_DIRECTIVES')
        self.assertTrue(matter['receipt_id'])

    def test_all_article_i_kinds_open(self):
        for kind in godfather.TRANSPORT_MATTER_KINDS:
            matter = self.godfather.open_transport_matter(
                OPERATOR, kind, 'member-ref', 'detail-ref')
            self.assertEqual(matter['matter_kind'], kind)

    def test_approve_then_coordination_recorded(self):
        matter = self.godfather.open_transport_matter(
            OPERATOR, 'EMERGENCY_EVACUATION_ARRANGEMENT',
            'member-ref', 'detail-ref')
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_transport_coordination(
                OPERATOR, matter['matter_id'], 'coord-ref')
        approved = self.godfather.transport_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.assertEqual(approved['status'], 'APPROVED')
        recorded = self.godfather.record_transport_coordination(
            OPERATOR, matter['matter_id'], 'coord-ref')
        self.assertEqual(recorded['status'],
                         'COORDINATION_RECORDED')

    def test_unknown_kind_and_non_operator_refused(self):
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.open_transport_matter(
                OPERATOR, 'BUY_A_PLANE', 'member', 'detail')
        with self.assertRaises(Exception):
            self.godfather.open_transport_matter(
                OTHER, 'MEDICAL_TRANSPORTATION',
                'member', 'detail')


class TestJointFundingApproval(DirectivesTestBase):
    def _godfather_approved(self):
        request = self.godfather.open_funding_request(
            OPERATOR, 'patriot-matter-ref-1', 'detail-ref-1')
        self.godfather.record_funding_determination(
            OPERATOR, request['request_id'], 'approve')
        return self.godfather.funding_request_view(
            OPERATOR, 'OPERATOR', request['request_id'])

    def _sentinel_approved(self):
        request = self.sentinel.open_funding_request(
            OPERATOR, 'patriot-matter-ref-1', 'detail-ref-1')
        self.sentinel.record_funding_determination(
            OPERATOR, request['request_id'], 'approve')
        return self.sentinel.funding_request_view(
            OPERATOR, 'OPERATOR', request['request_id'])

    def test_request_born_awaiting_human_review(self):
        request = self.godfather.open_funding_request(
            OPERATOR, 'matter-ref', 'detail-ref')
        self.assertEqual(request['status'],
                         'AWAITING_HUMAN_REVIEW')
        self.assertEqual(request['joint_state'],
                         'AWAITING_DETERMINATION')
        self.assertFalse(request['funding_approved'])
        self.assertTrue(request['counterpart_required'])
        self.assertEqual(request['counterpart_platform'],
                         'sanders_sentinel')

    def test_one_side_alone_never_reads_fully_approved(self):
        g = self._godfather_approved()
        self.assertEqual(g['joint_state'], 'AWAITING_COUNTERPART')
        self.assertFalse(g['funding_approved'])
        s = self._sentinel_approved()
        self.assertEqual(s['joint_state'], 'AWAITING_COUNTERPART')
        self.assertFalse(s['funding_approved'])
        self.assertEqual(s['counterpart_platform'],
                         'the_godfather')

    def test_joint_approval_completes_on_both_records(self):
        g = self._godfather_approved()
        s = self._sentinel_approved()
        g = self.godfather.record_counterpart_funding_determination(
            OPERATOR, g['request_id'], s['determination_ref'])
        self.assertEqual(g['joint_state'], 'JOINTLY_APPROVED')
        self.assertTrue(g['funding_approved'])
        s = self.sentinel.record_counterpart_funding_determination(
            OPERATOR, s['request_id'], g['determination_ref'])
        self.assertEqual(s['joint_state'], 'JOINTLY_APPROVED')
        self.assertTrue(s['funding_approved'])
        self.assertFalse(s['funds_disbursed'])

    def test_decline_reads_not_approved(self):
        request = self.sentinel.open_funding_request(
            OPERATOR, 'matter-ref', 'detail-ref')
        declined = self.sentinel.record_funding_determination(
            OPERATOR, request['request_id'], 'decline')
        self.assertEqual(declined['joint_state'], 'NOT_APPROVED')
        self.assertFalse(declined['funding_approved'])
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.record_counterpart_funding_determination(
                OPERATOR, request['request_id'], 'counterpart-ref')

    def test_counterpart_refused_before_own_approval(self):
        request = self.godfather.open_funding_request(
            OPERATOR, 'matter-ref', 'detail-ref')
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.record_counterpart_funding_determination(
                OPERATOR, request['request_id'], 'counterpart-ref')


class TestJointReservesRegister(DirectivesTestBase):
    def test_register_lifecycle_and_no_funds_held(self):
        reserve = self.godfather.designate_reserve(
            OPERATOR, 'designation-ref-1', 'purpose-ref-1')
        self.assertEqual(reserve['status'],
                         'AWAITING_HUMAN_REVIEW')
        self.assertFalse(reserve['funds_held'])
        self.assertFalse(reserve['jointly_approved'])
        reserve = self.godfather.reserve_action(
            OPERATOR, reserve['reserve_id'], 'approve')
        self.assertEqual(reserve['joint_state'],
                         'AWAITING_COUNTERPART')
        self.assertFalse(reserve['jointly_approved'])
        reserve = self.godfather.record_counterpart_reserve_approval(
            OPERATOR, reserve['reserve_id'], 'sentinel-approval-ref')
        self.assertTrue(reserve['jointly_approved'])
        self.assertFalse(reserve['funds_held'])
        with sqlite3.connect(self.godfather._bloodline_path) as db:
            rows = db.execute(
                'SELECT DISTINCT funds_held FROM'
                ' the_godfather_bloodline_reserves').fetchall()
        self.assertEqual(rows, [(0,)])

    def test_sentinel_side_register(self):
        reserve = self.sentinel.designate_reserve(
            OPERATOR, 'designation-ref-1', 'purpose-ref-1')
        reserve = self.sentinel.reserve_action(
            OPERATOR, reserve['reserve_id'], 'approve')
        reserve = self.sentinel.record_counterpart_reserve_approval(
            OPERATOR, reserve['reserve_id'], 'godfather-approval-ref')
        self.assertTrue(reserve['jointly_approved'])
        self.assertEqual(reserve['counterpart_platform'],
                         'the_godfather')


class TestPatriotFundingLink(DirectivesTestBase):
    def _funded_matter(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'BAIL_AND_BOND_ASSISTANCE',
            'bloodline-member-ref-1', 'matter-detail-ref-1')
        self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-ref-1')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'the_godfather',
            'godfather-determination-ref')
        return self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'sanders_sentinel',
            'sentinel-determination-ref')

    def test_matter_reads_not_funded_until_joint_approval(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'EMERGENCY_LEGAL_ASSISTANCE',
            'member-ref', 'detail-ref')
        self.assertEqual(matter['funding_state'], 'NOT_FUNDED')
        self.assertFalse(matter['funding_approved'])
        matter = self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-ref-1')
        self.assertEqual(matter['funding_state'],
                         'FUNDING_REQUESTED')
        self.assertFalse(matter['funding_approved'])
        matter = self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'the_godfather',
            'godfather-determination-ref')
        # One determination alone never funds the matter.
        self.assertEqual(matter['funding_state'],
                         'FUNDING_REQUESTED')
        self.assertFalse(matter['funding_approved'])
        matter = self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'sanders_sentinel',
            'sentinel-determination-ref')
        self.assertEqual(matter['funding_state'], 'FUNDED')
        self.assertTrue(matter['funding_approved'])
        self.assertFalse(matter['funds_disbursed'])

    def test_determination_refused_before_request(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'LEGAL_INFORMATION_RESOURCES',
            'member-ref', 'detail-ref')
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.record_matter_funding_determination(
                OPERATOR, matter['matter_id'], 'the_godfather',
                'determination-ref')

    def test_unknown_platform_and_duplicate_refused(self):
        matter = self._funded_matter()
        self.assertEqual(matter['funding_state'], 'FUNDED')
        fresh = self.patriot.open_bloodline_matter(
            OPERATOR, 'INCARCERATED_FUNDS_COORDINATION',
            'member-ref', 'detail-ref')
        self.patriot.request_matter_funding(
            OPERATOR, fresh['matter_id'], 'funding-ref-2')
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.record_matter_funding_determination(
                OPERATOR, fresh['matter_id'], 'patriot_saint',
                'self-determination-ref')
        self.patriot.record_matter_funding_determination(
            OPERATOR, fresh['matter_id'], 'the_godfather',
            'godfather-determination-ref')
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.record_matter_funding_determination(
                OPERATOR, fresh['matter_id'], 'the_godfather',
                'godfather-determination-ref-2')

    def test_article_iii_new_kinds_open(self):
        for kind in ('EMERGENCY_LEGAL_ASSISTANCE',
                     'BAIL_AND_BOND_ASSISTANCE',
                     'LEGAL_INFORMATION_RESOURCES'):
            matter = self.patriot.open_bloodline_matter(
                OPERATOR, kind, 'member-ref', 'detail-ref')
            self.assertEqual(matter['matter_kind'], kind)
            self.assertEqual(matter['funding_state'],
                             'NOT_FUNDED')


class TestDisbursementRefusals(DirectivesTestBase):
    def test_disburse_funds_refused_by_name_everywhere(self):
        with self.assertRaises(TheGodfatherDenied) as ctx:
            self.godfather.disburse_funds(OPERATOR)
        self.assertIn('GODFATHER_COORDINATION_ONLY',
                      str(ctx.exception))
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.disburse_funds(OPERATOR)
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'TICKET_PAYMENT_COORDINATION',
            'member-ref', 'detail-ref')
        with self.assertRaises(SandersPatriotSaintDenied) as ctx:
            self.patriot.disburse_funds(
                OPERATOR, matter['matter_id'])
        self.assertIn(
            'PATRIOT_SAINT_DISBURSEMENT_GOVERNED_PATH_ONLY',
            str(ctx.exception))

    def test_operation_checks_refuse_execution_by_name(self):
        with self.assertRaises(TheGodfatherDenied) as ctx:
            self.godfather.operation_check(
                OPERATOR, 'OPERATOR', 'purchase_transportation')
        self.assertIn('GODFATHER_COORDINATION_ONLY',
                      str(ctx.exception))
        with self.assertRaises(TheGodfatherDenied):
            self.godfather.operation_check(
                OPERATOR, 'OPERATOR', 'hold_funds')
        with self.assertRaises(SandersSentinelDenied):
            self.sentinel.operation_check(
                OPERATOR, 'OPERATOR', 'disburse_funds')
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.operation_check(
                OPERATOR, 'OPERATOR', 'transfer_funds')

    def test_funds_flags_false_in_status_views(self):
        self.assertFalse(
            self.godfather.status()['bloodline_directives']
            ['funds_disbursed'])
        self.assertFalse(
            self.sentinel.status()['bloodline_directives']
            ['funds_held'])
        self.assertFalse(
            self.patriot.status()['bloodline_funds_disbursed'])


class TestPatriotSaintDisbursement(DirectivesTestBase):
    """The Founder's Amendment to Article III
    (2026-11-26): Patriot Saint disburses for his
    assigned private duties — only against the recorded
    joint Godfather + Sanders Sentinel funding approval,
    only through a governed disbursement record in the
    segregated bloodline store."""

    def _funded_matter(self, approve=True):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'BAIL_AND_BOND_ASSISTANCE',
            'bloodline-member-ref-1', 'matter-detail-ref-1')
        if approve:
            self.patriot.bloodline_matter_action(
                OPERATOR, matter['matter_id'], 'approve')
        self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-ref-1')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'the_godfather',
            'godfather-determination-ref')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'sanders_sentinel',
            'sentinel-determination-ref')
        return matter['matter_id']

    def test_amendment_carried_verbatim_with_supersession(self):
        text = patriot.FOUNDER_AMENDMENT_ARTICLE_III_VERBATIM
        self.assertIn('hereby amend Article III', text)
        self.assertIn('the necessary controls have been'
                      ' put in place', text)
        self.assertIn('hereby superseded as it applies to'
                      " Patriot Saint's assigned private"
                      ' responsibilities', text)
        self.assertIn('Godfather and Sanders Sentinel'
                      ' shall retain their established'
                      ' funding approval responsibilities',
                      text)
        view = SandersPatriotSaintService.amendment_design_view()
        self.assertEqual(view['effective_date'], '2026-11-26')
        self.assertFalse(view['payment_rail_attached'])
        self.assertEqual(view['disbursement_discipline'],
                         'PATRIOT_SAINT_PRIVATE_DUTY_DISBURSEMENT')
        self.assertEqual(len(patriot.DISBURSEMENT_PURPOSES), 6)
        design = SandersPatriotSaintService.bloodline_design_view()
        self.assertIn('amendment', design)
        directives = SandersPatriotSaintService.directives_design_view()
        self.assertIn('amendment', directives)

    def test_disbursement_executes_against_joint_approval(self):
        matter_id = self._funded_matter()
        record = self.patriot.execute_disbursement(
            OPERATOR, matter_id, 'BAIL_AND_BOND_PAYMENTS',
            'amount-ref-1', 'payee-ref-1')
        self.assertTrue(record['funds_disbursed'])
        self.assertTrue(record['receipt_id'].startswith('receipt-'))
        self.assertFalse(record['payment_rail_attached'])
        self.assertEqual(record['godfather_determination_ref'],
                         'godfather-determination-ref')
        self.assertEqual(record['sentinel_determination_ref'],
                         'sentinel-determination-ref')
        events = [name for name, _ in self.audit.events]
        self.assertIn(
            'SANDERS_PATRIOT_SAINT_BLOODLINE_DISBURSEMENT_EXECUTED',
            events)
        view = self.patriot.bloodline_matter_view(
            OPERATOR, 'OPERATOR', matter_id)
        self.assertTrue(view['funds_disbursed'])
        self.assertTrue(view['funding']['funds_disbursed'])
        status = self.patriot.status()
        self.assertTrue(status['bloodline_funds_disbursed'])
        self.assertEqual(status['bloodline_disbursements_total'], 1)
        with sqlite3.connect(self.patriot._bloodline_path) as db:
            row = db.execute(
                'SELECT funds_disbursed FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?', (matter_id,)).fetchone()
        self.assertEqual(row[0], 1)
        remit = self.patriot.bloodline_remit(OPERATOR, 'OPERATOR')
        self.assertTrue(remit['funds_disbursed'])
        self.assertEqual(remit['disbursements_total'], 1)
        listed = self.patriot.bloodline_disbursements_list(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['purpose'],
                         'BAIL_AND_BOND_PAYMENTS')

    def test_disbursement_refused_without_joint_approval(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'EMERGENCY_LEGAL_ASSISTANCE',
            'member-ref', 'detail-ref')
        self.patriot.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        with self.assertRaises(SandersPatriotSaintDenied) as ctx:
            self.patriot.execute_disbursement(
                OPERATOR, matter['matter_id'],
                'EMERGENCY_LEGAL_ASSISTANCE',
                'amount-ref', 'payee-ref')
        self.assertIn('REQUIRES_JOINT_APPROVAL',
                      str(ctx.exception))
        self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-ref')
        self.patriot.record_matter_funding_determination(
            OPERATOR, matter['matter_id'], 'the_godfather',
            'godfather-determination-ref')
        # One determination alone never authorizes a
        # disbursement.
        with self.assertRaises(SandersPatriotSaintDenied) as ctx:
            self.patriot.execute_disbursement(
                OPERATOR, matter['matter_id'],
                'EMERGENCY_LEGAL_ASSISTANCE',
                'amount-ref', 'payee-ref')
        self.assertIn('REQUIRES_JOINT_APPROVAL',
                      str(ctx.exception))

    def test_disbursement_refused_outside_private_duties(self):
        matter_id = self._funded_matter()
        with self.assertRaises(SandersPatriotSaintDenied) as ctx:
            self.patriot.execute_disbursement(
                OPERATOR, matter_id,
                'COMMERCIAL_VENDOR_PAYMENT',
                'amount-ref', 'payee-ref')
        self.assertIn('PRIVATE_DUTIES_ONLY', str(ctx.exception))
        view = self.patriot.bloodline_matter_view(
            OPERATOR, 'OPERATOR', matter_id)
        self.assertFalse(view['funds_disbursed'])

    def test_disbursement_refused_before_matter_approval(self):
        matter_id = self._funded_matter(approve=False)
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.execute_disbursement(
                OPERATOR, matter_id, 'BAIL_AND_BOND_PAYMENTS',
                'amount-ref', 'payee-ref')

    def test_disbursement_records_segregated(self):
        matter_id = self._funded_matter()
        self.patriot.execute_disbursement(
            OPERATOR, matter_id,
            'ATTORNEY_FEES_AND_LEGAL_REPRESENTATION',
            'amount-ref', 'payee-ref')
        with sqlite3.connect(self.patriot._path) as db:
            commercial = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='table'")}
        with sqlite3.connect(self.patriot._bloodline_path) as db:
            bloodline = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='table'")}
        self.assertNotIn(
            'sanders_patriot_saint_bloodline_disbursements',
            commercial)
        self.assertIn(
            'sanders_patriot_saint_bloodline_disbursements',
            bloodline)
        # The governed operation is a carried operation;
        # the ungoverned ones stay refused by name.
        self.patriot.operation_check(
            OPERATOR, 'OPERATOR', 'execute_bloodline_disbursement')
        with self.assertRaises(SandersPatriotSaintDenied):
            self.patriot.operation_check(
                OPERATOR, 'OPERATOR', 'disburse_funds')
        # The commercial side carries no disbursement:
        # its records are untouched by the execution.
        self.assertEqual(
            self.patriot.records_list(OPERATOR, 'OPERATOR'), [])


class TestSegregation(DirectivesTestBase):
    def test_godfather_bloodline_store_is_separate(self):
        self.assertNotEqual(self.godfather._path,
                            self.godfather._bloodline_path)
        self.godfather.open_transport_matter(
            OPERATOR, 'MEDICAL_TRANSPORTATION',
            'member-ref', 'detail-ref')
        self.godfather.create_record(
            OPERATOR, 'subject-ref-1', [], 'scope-ref-1')
        with sqlite3.connect(self.godfather._path) as db:
            commercial = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='table'")}
        with sqlite3.connect(self.godfather._bloodline_path) as db:
            bloodline = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='table'")}
        self.assertIn('the_godfather_records', commercial)
        self.assertNotIn(
            'the_godfather_bloodline_transport_matters',
            commercial)
        self.assertIn(
            'the_godfather_bloodline_transport_matters',
            bloodline)
        self.assertIn('the_godfather_bloodline_reserves',
                      bloodline)
        records = self.godfather.records_list(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(records), 1)
        remit = self.godfather.bloodline_remit(
            OPERATOR, 'OPERATOR')
        self.assertEqual(remit['transport_matters_total'], 1)

    def test_patriot_funding_lives_in_bloodline_store(self):
        matter = self.patriot.open_bloodline_matter(
            OPERATOR, 'BAIL_AND_BOND_ASSISTANCE',
            'member-ref', 'detail-ref')
        self.patriot.request_matter_funding(
            OPERATOR, matter['matter_id'], 'funding-ref')
        with sqlite3.connect(self.patriot._bloodline_path) as db:
            row = db.execute(
                'SELECT funding_state FROM'
                ' sanders_patriot_saint_bloodline_matters'
                ' WHERE matter_id = ?',
                (matter['matter_id'],)).fetchone()
        self.assertEqual(row[0], 'FUNDING_REQUESTED')
        remit = self.patriot.bloodline_remit(
            OPERATOR, 'OPERATOR')
        self.assertEqual(
            remit['matters_by_funding_state']
            ['FUNDING_REQUESTED'], 1)


class TestSentinelCoveragePreserved(unittest.TestCase):
    """Article II retains ALL original responsibilities:
    the 2026-11-25 bloodline governance coverage still
    verifies sound documents and raises findings on
    tampered ones."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.repo = root / 'repo'
        docs = self.repo / 'docs'
        docs.mkdir(parents=True)
        self.documents = {}
        for entry in sentinel.BLOODLINE_WATCH_SET:
            if not entry['required']:
                continue
            path = self.repo / entry['document']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"# {entry['title']}\n\ngoverned text\n",
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
        self.audit = FakeAudit()
        self.service = SandersSentinelService(
            root / 'sanders_sentinel.db',
            operator_verifier=_verifier, audit=self.audit,
            repo_root=self.repo)

    def test_clean_cycle_sound_then_tamper_finding(self):
        cycle = self.service.verify_bloodline_records(OPERATOR)
        # Every required watched document assesses sound:
        # the original three records plus the supplemental
        # Founder-authorized directives the 2026-11-26
        # Sentinel Directive added to the guard set.
        required = [entry for entry in sentinel.BLOODLINE_WATCH_SET
                    if entry['required']]
        self.assertEqual(cycle['documents_sound'],
                         len(required))
        self.assertEqual(cycle['findings_raised'], 0)
        target = self.documents[
            'docs/PERMANENT_BLOODLINE_PROTECTION_DIRECTIVE.md']
        with open(target, 'ab') as handle:
            handle.write(b'x')
        cycle = self.service.verify_bloodline_records(OPERATOR)
        self.assertEqual(cycle['findings_raised'], 1)
        coverage = self.service.bloodline_coverage(
            OPERATOR, 'OPERATOR')
        self.assertEqual(coverage['findings_open'], 1)
        # The coordination surface carries the same
        # coverage alongside the Article II records.
        surface = self.service.bloodline_coordination(
            OPERATOR, 'OPERATOR')
        self.assertEqual(
            surface['governance_coverage']['findings_open'], 1)
        self.assertIn('article_ii_verbatim', surface)

    def test_coordination_records(self):
        record = self.service.record_bloodline_coordination(
            OPERATOR, 'protection-subject-ref',
            'coordination-detail-ref')
        self.assertEqual(record['participants'],
                         ['the_godfather',
                          'sanders_patriot_saint'])
        surface = self.service.bloodline_coordination(
            OPERATOR, 'OPERATOR')
        self.assertEqual(len(surface['coordination_records']), 1)


if __name__ == '__main__':
    unittest.main()
