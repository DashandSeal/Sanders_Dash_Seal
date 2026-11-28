"""Tests for the service intake spine (Track C of the Commercial
Ecosystem order, 2026-11-28) and its first plug, Grantwriter's
GRANT_SERVICES intake.

The invariants under test: the catalog of record carries exactly
the founder's ruled prices of 2026-11-27 and no other figures; the
percentage-of-award fee bar refuses by name at the spine; a client
record is the client's own record scope standing on the client
authorization; an engagement binds client + service + price of
record to a case opened in the platform's own machinery; the full
public road runs — a GRANT_SERVICES portal submission is born
AWAITING_HUMAN_REVIEW, and the operator's APPROVE opens the client
and her PUBLIC_COMMERCIAL case at PREPARE, exactly once; a
platform with no opener takes RECORDED engagements the operator
works; and no intake moves without the operator's recorded
review — submission alone opens nothing.

These tests use only stdlib fakes and temporary SQLite files:
no network, no keys.
Run: python3 -m unittest tests.test_service_intake -v
(from the repo root).
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import grantwriter_mother
from core_platform.grantwriter_service import GrantwriterPlatform
from core_platform.portals_service import PortalsService
from core_platform.service_intake import (
    CATALOGS,
    GRANT_SERVICES,
    ServiceIntake,
    ServiceIntakeDenied,
    ServiceIntakeForbidden,
    catalog_for,
    grantwriter_opener,
    service_for,
)

OPERATOR = 'founder-operator'


class FakeAudit:
    def __init__(self):
        self.records = []

    def preserve(self, stage, **fields):
        self.records.append({'stage': stage, **fields})
        return 'receipt-' + stage


class SpineBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.audit = FakeAudit()
        self.intake = ServiceIntake(
            self.tmp / 'intake.db', self.audit,
            operator_verifier=lambda actor: actor == OPERATOR)

    def open_client(self, **kw):
        fields = {
            'organization': 'Milwaukee Food Alliance',
            'contact_name': 'Jordan Lee',
            'contact': 'jordan@example.org',
        }
        fields.update(kw)
        return self.intake.open_client(OPERATOR, 'grantwriter', **fields)


class TestCatalogOfRecord(SpineBase):
    def test_grantwriter_catalog_is_the_ruled_prices(self):
        by_key = {e['key']: e for e in GRANT_SERVICES}
        self.assertEqual(by_key['READINESS_REVIEW']['amount_cents'], 4900)
        self.assertEqual(by_key['READINESS_REVIEW']['interval'], 'ONE_TIME')
        self.assertEqual(by_key['ESSENTIAL']['amount_cents'], 9900)
        self.assertEqual(by_key['ESSENTIAL']['interval'], 'MONTH')
        self.assertEqual(by_key['FULL_PROPOSAL']['amount_cents'], 1500000)
        self.assertEqual(by_key['RETAINER']['amount_cents'], 495000)
        self.assertEqual(by_key['RETAINER']['interval'], 'MONTH')

    def test_no_catalog_carries_percentage_of_award(self):
        for platform_id, entries in CATALOGS.items():
            for entry in entries:
                self.assertNotEqual(
                    entry['fee_structure'], 'PERCENTAGE_OF_AWARD',
                    '%s/%s' % (platform_id, entry['key']))

    def test_unknown_platform_and_service_refused(self):
        with self.assertRaises(ServiceIntakeDenied):
            catalog_for('no_such_platform')
        with self.assertRaises(ServiceIntakeDenied):
            service_for('grantwriter', 'NO_SUCH_SERVICE')


class TestClientsAndEngagements(SpineBase):
    def test_client_record_stands_on_client_authorization(self):
        client = self.open_client()
        self.assertTrue(client['client_ref'].startswith('CLI-'))
        self.assertEqual(client['platform_id'], 'grantwriter')
        self.assertEqual(
            client['authorization_basis'], 'CLIENT_AUTHORIZATION')
        stages = [r['stage'] for r in self.audit.records]
        self.assertIn('service_intake.client_opened', stages)

    def test_engagement_without_opener_stands_recorded(self):
        client = self.open_client()
        engagement = self.intake.engage(
            OPERATOR, client['client_ref'], 'ESSENTIAL')
        self.assertEqual(engagement['status'], 'RECORDED')
        self.assertEqual(engagement['service_label'],
                         'Grantwriter Essential')
        self.assertEqual(engagement['price_text'], '$99/month')
        self.assertEqual(engagement['platform_case_ref'], '')

    def test_engagement_idempotent_on_portal_ref(self):
        client = self.open_client(portal_ref='GRS-20261128-AAAAAAAAAA')
        first = self.intake.engage(
            OPERATOR, client['client_ref'], 'ESSENTIAL',
            portal_ref='GRS-20261128-AAAAAAAAAA')
        second = self.intake.engage(
            OPERATOR, client['client_ref'], 'ESSENTIAL',
            portal_ref='GRS-20261128-AAAAAAAAAA')
        self.assertEqual(first['engagement_ref'], second['engagement_ref'])
        self.assertEqual(
            len(self.intake.engagements_for(client['client_ref'])), 1)

    def test_client_opening_idempotent_on_portal_ref(self):
        first = self.open_client(portal_ref='GRS-20261128-BBBBBBBBBB')
        second = self.open_client(portal_ref='GRS-20261128-BBBBBBBBBB')
        self.assertEqual(first['client_ref'], second['client_ref'])

    def test_non_operator_refused(self):
        with self.assertRaises(ServiceIntakeForbidden):
            self.intake.open_client(
                'mallory', 'grantwriter', organization='X Org',
                contact_name='Mal', contact='mal@example.org')


class GrantwriterPlugBase(SpineBase):
    def setUp(self):
        super().setUp()
        self._env = mock.patch.dict(
            os.environ,
            {'SANDERS_GRANTWRITER_DB': str(self.tmp / 'base.db')})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.grantwriter = GrantwriterPlatform(
            self.tmp / 'gw.db', grantwriter_mother.database(),
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=self.audit)
        self.intake.register_opener(
            'grantwriter', grantwriter_opener(self.grantwriter))


class TestGrantwriterPlug(GrantwriterPlugBase):
    def test_engagement_opens_case_at_prepare_in_client_scope(self):
        client = self.open_client()
        engagement = self.intake.engage(
            OPERATOR, client['client_ref'], 'READINESS_REVIEW')
        self.assertEqual(engagement['status'], 'OPEN')
        case = self.grantwriter.jurisdiction_case(
            OPERATOR, 'OPERATOR', engagement['platform_case_ref'],
            'PUBLIC_COMMERCIAL', client['client_ref'])
        self.assertEqual(case['stage'], 'PREPARE')
        self.assertEqual(case['branch'], 'PUBLIC_COMMERCIAL')
        self.assertEqual(case['scope_ref'], client['client_ref'])
        self.assertEqual(case['fee_structure'], 'FLAT_FEE')


class TestPortalRoad(GrantwriterPlugBase):
    def setUp(self):
        super().setUp()
        self.portals = PortalsService(
            self.tmp / 'portals.db', self.tmp / 'media',
            operator_verifier=lambda identity: identity == OPERATOR,
            audit=self.audit,
            approval_hook=self._hook)

    def _hook(self, identity, case):
        if case.get('kind') == 'GRANT_SERVICES':
            return self.intake.handle_portal_approval(identity, case)
        return None

    def _submit(self):
        body = json.dumps({
            'organization': 'Milwaukee Food Alliance',
            'contact_name': 'Jordan Lee',
            'contact': 'jordan@example.org',
            'seeking': 'Federal food-security funding',
            'service_key': 'READINESS_REVIEW',
        })
        return self.portals.submit(
            'GRANT_SERVICES', 'legal_helpers',
            name='Jordan Lee', contact='jordan@example.org',
            subject='READINESS_REVIEW', body=body)

    def test_submission_born_awaiting_review_opens_nothing(self):
        record = self._submit()
        self.assertTrue(record['ref'].startswith('GRS-'))
        self.assertEqual(record['status'], 'AWAITING_HUMAN_REVIEW')
        self.assertEqual(self.intake.status()['clients'], 0)

    def test_approval_opens_client_and_case_exactly_once(self):
        record = self._submit()
        result = self.portals.review(OPERATOR, record['ref'], 'APPROVE')
        self.assertEqual(result['status'], 'APPROVED')
        engagement = result['intake']
        self.assertEqual(engagement['status'], 'OPEN')
        self.assertEqual(engagement['service_key'], 'READINESS_REVIEW')
        client = self.intake.client_view(engagement['client_ref'])
        self.assertEqual(client['organization'],
                         'Milwaukee Food Alliance')
        case = self.grantwriter.jurisdiction_case(
            OPERATOR, 'OPERATOR', engagement['platform_case_ref'],
            'PUBLIC_COMMERCIAL', client['client_ref'])
        self.assertEqual(case['stage'], 'PREPARE')
        # A second handling of the same approval opens nothing new.
        again = self.intake.handle_portal_approval(
            OPERATOR, self.portals.get_case(record['ref']))
        self.assertEqual(again['engagement_ref'],
                         engagement['engagement_ref'])
        self.assertEqual(self.intake.status()['clients'], 1)

    def test_rejection_opens_nothing(self):
        record = self._submit()
        result = self.portals.review(OPERATOR, record['ref'], 'REJECT')
        self.assertEqual(result['status'], 'REJECTED')
        self.assertNotIn('intake', result)
        self.assertEqual(self.intake.status()['clients'], 0)


if __name__ == '__main__':
    unittest.main()
