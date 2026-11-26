"""Tests for the Sanders Patriot Saint bloodline support
remit (founder's rulings, 2026-11-25 23:44 and 23:56 MST).

The remit is coordination-centered, under the founder's
five additional duties: bloodline matters live in a
segregated store the commercial operations never read,
and every matter is born AWAITING_HUMAN_REVIEW.
Disbursement is governed by the Founder's Amendment to
Article III (2026-11-26): the platform disburses for
its assigned private duties only through a governed
disbursement record against the recorded joint
Godfather + Sanders Sentinel funding approval, and
ungoverned disbursement is refused by name. These
tests use only stdlib fakes and temporary SQLite
files: no network, no keys.
Run: python3 -m unittest tests.test_sanders_patriot_saint_bloodline -v
(from the repo root).
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from core_platform import sanders_patriot_saint_service as patriot
from core_platform.sanders_patriot_saint_service import (
    SandersPatriotSaintDenied,
    SandersPatriotSaintForbidden,
    SandersPatriotSaintService,
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


class PatriotSaintBloodlineTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / 'sanders_patriot_saint.db'
        self.audit = FakeAudit()
        self.service = SandersPatriotSaintService(
            self.db_path,
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=self.audit)

    def open_matter(self, kind='INCARCERATED_FUNDS_COORDINATION'):
        return self.service.open_bloodline_matter(
            OPERATOR, kind, 'bloodline-member-ref-1',
            'matter-detail-ref-1')


class TestRulingOfRecord(unittest.TestCase):
    def test_role_statement_carried_verbatim(self):
        self.assertEqual(
            patriot.FOUNDER_RULING_BLOODLINE_ROLE,
            'Has public facing business model of his own, '
            'privately he handles putting money on any of my '
            'bloodline that have been incarcerated, pays off '
            'tickets, gets laws, things like that.')
        self.assertIn('putting money on any of my bloodline',
                      ' '.join(patriot.__doc__.split()))

    def test_five_additional_duties_carried(self):
        duties = {d['duty']: d['ruling']
                  for d in patriot.BLOODLINE_DUTIES}
        self.assertEqual(set(duties), {
            'FINANCIAL_AUTHORITY', 'SUCCESSION',
            'CONFIDENTIALITY', 'PERMANENT_SCOPE_PROTECTION',
            'LEGAL_ASSISTANCE'})
        self.assertIn('without independently controlling or '
                      'disbursing family funds',
                      duties['FINANCIAL_AUTHORITY'])
        self.assertIn('survive the founder', duties['SUCCESSION'])
        self.assertIn('segregated', duties['CONFIDENTIALITY'])
        self.assertIn('must not be removed, diminished or '
                      'repurposed', duties['PERMANENT_SCOPE_PROTECTION'])
        self.assertIn('locating and coordinating qualified '
                      'legal representation',
                      duties['LEGAL_ASSISTANCE'])
        verbatim = patriot.FOUNDER_RULING_ADDITIONAL_DUTIES_VERBATIM
        self.assertIn('Neither purpose should diminish the '
                      'other', verbatim)
        self.assertIn('preserve his distinction from The '
                      'Godfather', verbatim)

    def test_design_view_carries_the_remit(self):
        view = SandersPatriotSaintService.bloodline_design_view()
        self.assertEqual(view['founder_ruling'],
                         patriot.FOUNDER_RULING_BLOODLINE_ROLE)
        self.assertEqual(view['discipline'],
                         'PATRIOT_SAINT_COORDINATION_ONLY')
        self.assertEqual(view['disbursement_discipline'],
                         'PATRIOT_SAINT_PRIVATE_DUTY_DISBURSEMENT')
        self.assertTrue(
            view['funds_disbursed_recorded_per_matter'])
        self.assertIn('hereby superseded',
                      view['amendment']['amendment_verbatim'])
        self.assertTrue(view['segregated_store'])
        design = SandersPatriotSaintService.design_view()
        self.assertIn('bloodline_support', design)


class TestMatterLifecycle(PatriotSaintBloodlineTestBase):
    def test_matter_born_awaiting_human_review(self):
        matter = self.open_matter()
        self.assertEqual(matter['status'], 'AWAITING_HUMAN_REVIEW')
        self.assertFalse(matter['funds_disbursed'])
        self.assertEqual(matter['scope_ref'], 'BLOODLINE_SUPPORT')
        self.assertTrue(matter['receipt_id'])

    def test_approve_then_coordination_recorded(self):
        matter = self.open_matter('TICKET_PAYMENT_COORDINATION')
        approved = self.service.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.assertEqual(approved['status'], 'APPROVED')
        recorded = self.service.record_bloodline_coordination(
            OPERATOR, matter['matter_id'], 'coordination-ref-1')
        self.assertEqual(recorded['status'], 'COORDINATION_RECORDED')
        self.assertEqual(recorded['coordination_ref'],
                         'coordination-ref-1')
        self.assertFalse(recorded['funds_disbursed'])

    def test_reject_path(self):
        matter = self.open_matter('LEGAL_REPRESENTATION_COORDINATION')
        rejected = self.service.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'reject')
        self.assertEqual(rejected['status'], 'REJECTED')

    def test_coordination_refused_before_approval(self):
        matter = self.open_matter()
        with self.assertRaises(SandersPatriotSaintDenied):
            self.service.record_bloodline_coordination(
                OPERATOR, matter['matter_id'], 'coordination-ref-1')

    def test_unknown_kind_refused(self):
        with self.assertRaises(SandersPatriotSaintDenied):
            self.service.open_bloodline_matter(
                OPERATOR, 'WIRE_TRANSFER', 'member', 'detail')

    def test_non_operator_cannot_open_or_act(self):
        with self.assertRaises(SandersPatriotSaintForbidden):
            self.service.open_bloodline_matter(
                OTHER, 'TICKET_PAYMENT_COORDINATION',
                'member', 'detail')
        matter = self.open_matter()
        with self.assertRaises(SandersPatriotSaintForbidden):
            self.service.bloodline_matter_action(
                OTHER, matter['matter_id'], 'approve')

    def test_receipts_written_for_state_changes(self):
        matter = self.open_matter()
        self.service.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.service.record_bloodline_coordination(
            OPERATOR, matter['matter_id'], 'coordination-ref-1')
        events = [event for event, _ in self.audit.events]
        self.assertIn(
            'SANDERS_PATRIOT_SAINT_BLOODLINE_MATTER_OPENED', events)
        self.assertIn(
            'SANDERS_PATRIOT_SAINT_BLOODLINE_MATTER_ACTION', events)
        self.assertIn(
            'SANDERS_PATRIOT_SAINT_BLOODLINE_COORDINATION_RECORDED',
            events)
        view = self.service.bloodline_matter_view(
            OPERATOR, 'OPERATOR', matter['matter_id'])
        self.assertTrue(view['receipt_id'].startswith('receipt-'))


class TestDisbursementDiscipline(PatriotSaintBloodlineTestBase):
    def test_disburse_funds_refused_by_name(self):
        matter = self.open_matter()
        with self.assertRaises(SandersPatriotSaintDenied) as ctx:
            self.service.disburse_funds(OPERATOR, matter['matter_id'])
        self.assertIn(
            'PATRIOT_SAINT_DISBURSEMENT_GOVERNED_PATH_ONLY',
            str(ctx.exception))

    def test_operation_check_refuses_disbursement_by_name(self):
        for operation in ('disburse_funds', 'pay_ticket',
                          'transfer_funds'):
            with self.assertRaises(SandersPatriotSaintDenied) as ctx:
                self.service.operation_check(
                    OPERATOR, 'OPERATOR', operation)
            self.assertIn(
                'PATRIOT_SAINT_DISBURSEMENT_GOVERNED_PATH_ONLY',
                str(ctx.exception))

    def test_funds_disbursed_false_absent_disbursement(self):
        matter = self.open_matter()
        self.service.bloodline_matter_action(
            OPERATOR, matter['matter_id'], 'approve')
        self.service.record_bloodline_coordination(
            OPERATOR, matter['matter_id'], 'coordination-ref-1')
        remit = self.service.bloodline_remit(OPERATOR, 'OPERATOR')
        self.assertFalse(remit['funds_disbursed'])
        status = self.service.status()
        self.assertFalse(status['bloodline_funds_disbursed'])
        with sqlite3.connect(self.service._bloodline_path) as db:
            rows = db.execute(
                'SELECT DISTINCT funds_disbursed FROM'
                ' sanders_patriot_saint_bloodline_matters').fetchall()
        self.assertEqual(rows, [(0,)])


class TestSegregation(PatriotSaintBloodlineTestBase):
    def test_stores_are_separate_files_with_separate_tables(self):
        self.assertNotEqual(self.service._path,
                            self.service._bloodline_path)
        self.open_matter()
        self.service.create_record(OPERATOR, 'subject-ref-1', [],
                                   'scope-ref-1')
        with sqlite3.connect(self.service._path) as db:
            commercial_tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        with sqlite3.connect(self.service._bloodline_path) as db:
            bloodline_tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn('sanders_patriot_saint_records',
                      commercial_tables)
        self.assertNotIn('sanders_patriot_saint_bloodline_matters',
                         commercial_tables)
        self.assertEqual(
            bloodline_tables,
            {'sanders_patriot_saint_bloodline_matters',
             'sanders_patriot_saint_bloodline_disbursements',
             'sanders_patriot_saint_shield_coverage_designations',
             'sanders_patriot_saint_shield_coverage_tests'})

    def test_commercial_views_never_show_bloodline_matters(self):
        matter = self.open_matter()
        self.service.create_record(OPERATOR, 'subject-ref-1', [],
                                   'scope-ref-1')
        records = self.service.records_list(OPERATOR, 'OPERATOR')
        self.assertEqual(len(records), 1)
        self.assertNotIn(matter['matter_id'],
                         [r['record_id'] for r in records])
        matters = self.service.bloodline_matters_list(
            OPERATOR, 'OPERATOR')
        self.assertEqual([m['matter_id'] for m in matters],
                         [matter['matter_id']])

    def test_remit_read_surface(self):
        matter = self.open_matter()
        remit = self.service.bloodline_remit(OPERATOR, 'OPERATOR')
        self.assertEqual(remit['matters_total'], 1)
        self.assertEqual(
            remit['matters_by_status']['AWAITING_HUMAN_REVIEW'], 1)
        self.assertEqual(
            [m['matter_id'] for m in remit['open_matters']],
            [matter['matter_id']])
        self.assertEqual(len(remit['duties']), 5)
        self.assertTrue(remit['invariants'])


if __name__ == '__main__':
    unittest.main()
