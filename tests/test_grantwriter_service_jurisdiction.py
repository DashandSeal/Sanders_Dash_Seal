"""Tests for the Grantwriter Complete Service Jurisdiction
(founder-presented 2026-11-26 12:57 MST; adopted 2026-11-26
13:03 MST as an AMENDMENT to her original purpose).

The invariants under test: the jurisdiction lands as a guarded
document in the watch set (24 documents, 23 required) with a
sound manifest pair, its statement carried verbatim in
Grantwriter's module and surfaced in her design view with the
amendment relationship named and the amend-never-supersede
ruling quoted on its face; the three service branches function
independently with cross-branch access refused by name; the
property objectives register stands exactly as assigned with
no use restrictions added; the seven-stage duty cycle runs as
a checked case lifecycle; submissions stand on an AUTHORITY
BASIS \u2014 the standing Founder grant, or the client
authorization of record \u2014 with NO per-case founder
authorization gate anywhere in the machinery (founder
correction 2026-11-26 13:12 MST); JustGrants roles stand as
facts of record per entity, never as a system reservation;
the seeded JustGrants case A-547904 stands at its truthful
stage; the founder's two further Grants.gov workspaces of
record stand seeded at PREPARE in the same branch, the
Justice System Research workspace carrying its unestablished
submission status on its face; and every adopted operating rule holds as a structural
property proven by a test \u2014 functioning duties never
suspend, an incomplete profile never blocks an otherwise
eligible case (only a funder's own named mandatory
requirement may), all opportunity kinds are pursuable, no
discard without an alternative-structures check of record,
and the percentage-of-award fee bar refuses by name.

These tests use only stdlib fakes and temporary SQLite files:
no network, no keys.
Run: python3 -m unittest tests.test_grantwriter_service_jurisdiction -v
(from the repo root).
"""

import hashlib
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import grantwriter_mother
from core_platform import grantwriter_service as gwsvc
from core_platform import sanders_sentinel_service as sentinel
from core_platform.grantwriter_service import (
    GrantwriterPlatform,
    GrantwriterPlatformDenied,
    GrantwriterPlatformForbidden,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR = 'founder-operator'
COMPANY = 'Sanders Home Healthcare & Caregivers LLC'
OTHER_COMPANY = 'Sanders Senior Living LLC'
JURISDICTION_DOCUMENT = (
    'docs/GRANTWRITER_COMPLETE_SERVICE_JURISDICTION_2026-11-26.md')


class FakeAudit:
    def __init__(self):
        self.records = []

    def preserve(self, stage, **fields):
        self.records.append({'stage': stage, **fields})


class GrantwriterJurisdictionBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self._env = mock.patch.dict(
            os.environ,
            {'SANDERS_GRANTWRITER_DB': str(tmp / 'base.db')})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.audit = FakeAudit()
        self.service = GrantwriterPlatform(
            tmp / 'svc.db', grantwriter_mother.database(),
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=self.audit)

    def make_case(self, branch='PRIVATE_CORPORATE', scope=COMPANY,
                  **kw):
        return self.service.create_jurisdiction_case(
            OPERATOR, branch, scope, kw.pop('title', 'Test case'),
            **kw)

    def advance(self, case, target, **kw):
        return self.service.advance_jurisdiction_case(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'], target, **kw)

    def walk_to_submit(self, case, method='PORTAL',
                       basis='FOUNDER_STANDING_GRANT'):
        self.advance(case, 'VALIDATE')
        return self.advance(case, 'SUBMIT', submission_method=method,
                            authority_basis=basis)


class TestGuardedRecord(GrantwriterJurisdictionBase):
    def test_document_landed_with_sound_manifest_pair(self):
        doc_path = REPO_ROOT / JURISDICTION_DOCUMENT
        self.assertTrue(doc_path.exists())
        manifest = json.loads(
            (REPO_ROOT / (JURISDICTION_DOCUMENT + '.pbd.json'))
            .read_text(encoding='utf-8'))
        digest = hashlib.sha256(doc_path.read_bytes()).hexdigest()
        self.assertEqual(manifest['body']['payload_hash'], digest)
        self.assertEqual(manifest['body']['artifact'],
                         JURISDICTION_DOCUMENT)

    def test_document_carries_statement_verbatim_and_amendment(self):
        text = (REPO_ROOT / JURISDICTION_DOCUMENT).read_text(
            encoding='utf-8')
        self.assertIn(gwsvc.JURISDICTION_STATEMENT, text)
        self.assertIn('stands as an AMENDMENT to '
                      "Grantwriter's original purpose", text)
        self.assertIn(gwsvc.AMEND_NEVER_SUPERSEDE_RULING, text)
        self.assertIn('standing grant', text)
        self.assertNotIn('SUBMISSION_BY_FOUNDER_ROLE', text)

    def test_document_in_watch_set_required(self):
        entries = {e['document']: e
                   for e in sentinel.BLOODLINE_WATCH_SET}
        self.assertIn(JURISDICTION_DOCUMENT, entries)
        self.assertTrue(entries[JURISDICTION_DOCUMENT]['required'])
        self.assertEqual(len(sentinel.BLOODLINE_WATCH_SET), 24)
        self.assertEqual(
            len([e for e in sentinel.BLOODLINE_WATCH_SET
                 if e['required']]), 23)

    def test_design_view_surfaces_jurisdiction_and_amendment(self):
        view = GrantwriterPlatform.jurisdiction_design_view()
        self.assertTrue(view['amendment'])
        self.assertTrue(
            view['original_purpose_governing_and_intact'])
        self.assertIn('grantwriter_purpose', view['amends'])
        self.assertEqual(view['guarded_document'],
                         JURISDICTION_DOCUMENT)
        self.assertEqual(view['amend_never_supersede_ruling'],
                         gwsvc.AMEND_NEVER_SUPERSEDE_RULING)
        self.assertEqual(
            [b['branch'] for b in view['branches']],
            ['PUBLIC_COMMERCIAL', 'PRIVATE_CORPORATE',
             'PLATFORM_FUNDING'])
        self.assertEqual(view['companies'],
                         list(gwsvc.JURISDICTION_COMPANIES))
        self.assertEqual(
            [s['stage'] for s in view['duty_cycle']],
            list(gwsvc.DUTY_CYCLE_STAGES))
        self.assertFalse(
            view['per_case_founder_authorization_gate'])
        self.assertEqual(view['roles_model'],
                         'FACTS_OF_RECORD_PER_ENTITY')

    def test_property_objectives_exactly_as_assigned(self):
        view = GrantwriterPlatform.jurisdiction_design_view()
        objectives = view['property_objectives']
        self.assertEqual(
            [(o['objective'], o['quantity_of_record'])
             for o in objectives['objectives']],
            [('Upscale office buildings', '2'),
             ('Upscale houses', 'Multiple'),
             ('Warehouses', '2')])
        self.assertFalse(
            objectives['use_restrictions_added_by_platform'])


class TestBranches(GrantwriterJurisdictionBase):
    def test_case_in_each_branch(self):
        for branch, scope in (
                ('PUBLIC_COMMERCIAL', 'Client A'),
                ('PRIVATE_CORPORATE', COMPANY),
                ('PLATFORM_FUNDING', 'sanders-sentinel')):
            case = self.make_case(branch, scope)
            self.assertEqual(case['branch'], branch)
            self.assertEqual(case['stage'], 'PREPARE')
            self.assertEqual(case['stage_history'][0]['stage'],
                             'PREPARE')

    def test_private_corporate_scope_is_the_four_companies(self):
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.make_case('PRIVATE_CORPORATE', 'Some Other LLC')
        self.assertIn('four companies', str(ctx.exception))
        for company in gwsvc.JURISDICTION_COMPANIES:
            self.assertEqual(
                self.make_case('PRIVATE_CORPORATE',
                               company)['scope_ref'], company)

    def test_branch_is_required_and_validated(self):
        with self.assertRaises(GrantwriterPlatformDenied):
            self.make_case('NO_SUCH_BRANCH', COMPANY)

    def test_cross_branch_access_refused_by_name(self):
        case = self.make_case('PRIVATE_CORPORATE', COMPANY)
        with self.assertRaises(GrantwriterPlatformForbidden) as ctx:
            self.service.jurisdiction_case(
                OPERATOR, 'OPERATOR', case['case_id'],
                'PUBLIC_COMMERCIAL', COMPANY)
        self.assertIn('GRANTWRITER_CROSS_BRANCH_ACCESS_REFUSED',
                      str(ctx.exception))

    def test_cross_scope_access_refused_by_name(self):
        case = self.make_case('PRIVATE_CORPORATE', COMPANY)
        with self.assertRaises(GrantwriterPlatformForbidden) as ctx:
            self.service.advance_jurisdiction_case(
                OPERATOR, case['case_id'], 'PRIVATE_CORPORATE',
                OTHER_COMPANY, 'VALIDATE')
        self.assertIn('GRANTWRITER_CROSS_BRANCH_ACCESS_REFUSED',
                      str(ctx.exception))


class TestDutyCycle(GrantwriterJurisdictionBase):
    def test_full_cycle_walk_with_stage_records(self):
        case = self.make_case()
        case = self.advance(case, 'VALIDATE')
        case = self.advance(
            case, 'SUBMIT', submission_method='PORTAL',
            authority_basis='FOUNDER_STANDING_GRANT')
        case = self.advance(case, 'VERIFY_RECEIPT',
                            tracking_ref='TRK-123')
        case = self.advance(case, 'MANAGE_AWARDS')
        case = self.advance(case, 'CLOSE_OUT_RENEW')
        self.assertEqual(case['stage'], 'CLOSE_OUT_RENEW')
        self.assertEqual(
            [s['stage'] for s in case['stage_history']],
            ['PREPARE', 'VALIDATE', 'SUBMIT', 'VERIFY_RECEIPT',
             'MANAGE_AWARDS', 'CLOSE_OUT_RENEW'])
        submit = case['stage_history'][2]
        self.assertEqual(submit['submission_method'], 'PORTAL')
        self.assertEqual(submit['authority_basis'],
                         'FOUNDER_STANDING_GRANT')
        self.assertEqual(case['stage_history'][3]['tracking_ref'],
                         'TRK-123')

    def test_illegal_transition_refused(self):
        case = self.make_case()
        with self.assertRaises(GrantwriterPlatformDenied):
            self.advance(case, 'SUBMIT',
                         submission_method='PORTAL',
                         authority_basis='FOUNDER_STANDING_GRANT')

    def test_submit_on_standing_grant_alone_no_per_case_approval(self):
        # The service is constructed with approval_checker=None:
        # no approval object exists anywhere, and none is asked
        # for. The case still reaches SUBMIT on the standing
        # grant alone (founder correction 2026-11-26 13:12 MST).
        self.assertIsNone(self.service.approval_checker)
        case = self.walk_to_submit(self.make_case())
        self.assertEqual(case['stage'], 'SUBMIT')
        self.assertNotIn('founder_authorization_ref', case)
        self.assertNotIn('founder_approval', case)

    def test_no_per_case_gate_encoding_in_module_source(self):
        source = (REPO_ROOT / 'core_platform'
                  / 'grantwriter_service.py').read_text(
                      encoding='utf-8')
        self.assertNotIn('SUBMISSION_BY_FOUNDER_ROLE', source)
        self.assertNotIn('founder_authorization_ref', source)

    def test_public_branch_submits_on_client_authorization(self):
        case = self.make_case('PUBLIC_COMMERCIAL', 'Client A')
        self.advance(case, 'VALIDATE')
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.advance(case, 'SUBMIT', submission_method='EMAIL',
                         authority_basis='FOUNDER_STANDING_GRANT')
        self.assertIn('GRANTWRITER_AUTHORITY_BASIS_MISMATCH',
                      str(ctx.exception))
        case = self.advance(case, 'SUBMIT',
                            submission_method='EMAIL',
                            authority_basis='CLIENT_AUTHORIZATION')
        self.assertEqual(case['stage'], 'SUBMIT')

    def test_every_submission_method_accepted(self):
        for method in gwsvc.SUBMISSION_METHODS:
            case = self.walk_to_submit(self.make_case(),
                                       method=method)
            self.assertEqual(case['stage'], 'SUBMIT')
            self.assertEqual(
                case['stage_history'][-1]['submission_method'],
                method)

    def test_submit_requires_a_method(self):
        case = self.make_case()
        self.advance(case, 'VALIDATE')
        with self.assertRaises(GrantwriterPlatformDenied):
            self.advance(case, 'SUBMIT',
                         authority_basis='FOUNDER_STANDING_GRANT')

    def test_verify_receipt_requires_tracking_reference(self):
        case = self.walk_to_submit(self.make_case())
        with self.assertRaises(GrantwriterPlatformDenied):
            self.advance(case, 'VERIFY_RECEIPT')
        case = self.advance(case, 'VERIFY_RECEIPT',
                            tracking_ref='A-000001')
        self.assertEqual(
            case['stage_history'][-1]['tracking_ref'], 'A-000001')

    def test_correct_loop_resubmits(self):
        case = self.walk_to_submit(self.make_case())
        case = self.advance(case, 'VERIFY_RECEIPT',
                            tracking_ref='REJ-1')
        case = self.advance(case, 'CORRECT',
                            note='Agency requested more information')
        case = self.advance(case, 'SUBMIT',
                            submission_method='PORTAL',
                            authority_basis='FOUNDER_STANDING_GRANT')
        case = self.advance(case, 'VERIFY_RECEIPT',
                            tracking_ref='A-000002')
        self.assertEqual(case['stage'], 'VERIFY_RECEIPT')
        submits = [s for s in case['stage_history']
                   if s['stage'] == 'SUBMIT']
        self.assertEqual(len(submits), 2)

    def test_advance_is_operator_only(self):
        case = self.make_case()
        with self.assertRaises(GrantwriterPlatformForbidden):
            self.service.advance_jurisdiction_case(
                'not-the-operator', case['case_id'],
                case['branch'], case['scope_ref'], 'VALIDATE')


class TestOperatingRules(GrantwriterJurisdictionBase):
    def test_no_disable_or_suspend_switch_exists(self):
        for name in dir(GrantwriterPlatform):
            self.assertNotIn('disable', name.lower())
            self.assertNotIn('suspend', name.lower())

    def test_duties_continue_while_other_cases_develop(self):
        developing = self.make_case(title='Still in development')
        other = self.walk_to_submit(self.make_case(title='Live'))
        self.assertEqual(developing['stage'], 'PREPARE')
        self.assertEqual(other['stage'], 'SUBMIT')
        # The developing case still advances afterwards.
        self.assertEqual(self.advance(developing, 'VALIDATE')
                         ['stage'], 'VALIDATE')

    def test_incomplete_profile_never_blocks(self):
        case = self.make_case(profile_complete=False,
                              profile_gaps='EIN letter not yet '
                                           'of record')
        case = self.walk_to_submit(case)
        self.assertEqual(case['stage'], 'SUBMIT')
        self.assertFalse(case['profile_complete'])
        self.assertIn('EIN letter', case['profile_gaps'])

    def test_only_a_funders_own_requirement_blocks(self):
        case = self.make_case()
        self.advance(case, 'VALIDATE')
        case = self.service.record_funder_requirement(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'],
            'Funder requires a current SAM.gov registration '
            'screenshot in the package')
        self.assertIsNotNone(case['funder_block'])
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.advance(case, 'SUBMIT', submission_method='PORTAL',
                         authority_basis='FOUNDER_STANDING_GRANT')
        self.assertIn(
            'GRANTWRITER_FUNDER_REQUIREMENT_BLOCKS_SUBMISSION',
            str(ctx.exception))
        self.assertIn('SAM.gov', str(ctx.exception))
        case = self.service.record_funder_requirement(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'], 'SAM.gov registration', met=True)
        self.assertIsNone(case['funder_block'])
        case = self.advance(case, 'SUBMIT',
                            submission_method='PORTAL',
                            authority_basis='FOUNDER_STANDING_GRANT')
        self.assertEqual(case['stage'], 'SUBMIT')

    def test_all_opportunity_kinds_pursuable(self):
        for kind in gwsvc.OPPORTUNITY_KINDS:
            case = self.make_case(opportunity_kind=kind)
            self.assertEqual(case['opportunity_kind'], kind)

    def test_discard_requires_alternative_structures_check(self):
        case = self.make_case()
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.service.discard_jurisdiction_case(
                OPERATOR, case['case_id'], case['branch'],
                case['scope_ref'])
        self.assertIn(
            'GRANTWRITER_DISCARD_REQUIRES_ALTERNATIVE_'
            'STRUCTURES_CHECK', str(ctx.exception))
        self.service.record_alternative_structures_check(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'],
            'Individual award; joint application with a '
            'partner platform; ecosystem-wide consortium')
        case = self.service.discard_jurisdiction_case(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'], note='Funder program discontinued')
        self.assertEqual(case['stage'], 'DISCARDED')
        self.assertEqual(case['alternative_structures_checks'], 1)

    def test_discard_from_submit_refused(self):
        case = self.walk_to_submit(self.make_case())
        self.service.record_alternative_structures_check(
            OPERATOR, case['case_id'], case['branch'],
            case['scope_ref'], 'Flat-fee resubmission next cycle')
        with self.assertRaises(GrantwriterPlatformDenied):
            self.service.discard_jurisdiction_case(
                OPERATOR, case['case_id'], case['branch'],
                case['scope_ref'])

    def test_fee_bar_refuses_percentage_of_award_by_name(self):
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.make_case('PUBLIC_COMMERCIAL', 'Client A',
                           fee_structure='PERCENTAGE_OF_AWARD')
        self.assertIn(
            'GRANTWRITER_PERCENTAGE_OF_AWARD_PRICING_REFUSED',
            str(ctx.exception))
        self.assertIn('2 CFR 200.442', str(ctx.exception))
        case = self.make_case('PUBLIC_COMMERCIAL', 'Client A',
                              fee_structure='FLAT_FEE')
        self.assertEqual(case['fee_structure'], 'FLAT_FEE')


class TestRolesAndSeededCase(GrantwriterJurisdictionBase):
    def test_seeded_role_assignments_are_facts_of_record(self):
        assignments = self.service.role_assignments(
            system='JUSTGRANTS', entity=COMPANY)
        by_role = {a['role']: a['holder'] for a in assignments}
        self.assertEqual(
            by_role['APPLICATION_SUBMITTER'], 'Roosevelt Sanders')
        self.assertEqual(
            by_role['ENTITY_ADMINISTRATOR'], 'Roosevelt Sanders')
        self.assertEqual(
            by_role['AUTHORIZED_REPRESENTATIVE'],
            'Roosevelt Sanders')

    def test_role_assignment_is_a_changeable_fact(self):
        self.service.record_role_assignment(
            OPERATOR, 'JUSTGRANTS', COMPANY,
            'APPLICATION_SUBMITTER', 'A. Grantwriter Designee')
        assignments = self.service.role_assignments(
            system='JUSTGRANTS', entity=COMPANY)
        by_role = {a['role']: a['holder'] for a in assignments}
        self.assertEqual(by_role['APPLICATION_SUBMITTER'],
                         'A. Grantwriter Designee')
        with self.assertRaises(GrantwriterPlatformDenied):
            self.service.record_role_assignment(
                OPERATOR, 'JUSTGRANTS', COMPANY,
                'SUBMISSION_RESERVED_TO_ADMIN', 'Nobody')

    def test_seeded_case_at_truthful_stage(self):
        board = self.service.jurisdiction_board(OPERATOR, 'OPERATOR')
        case = board['seeded_case']
        self.assertEqual(case['case_id'], 'A-547904')
        self.assertEqual(case['branch'], 'PRIVATE_CORPORATE')
        self.assertEqual(case['scope_ref'], COMPANY)
        self.assertEqual(case['external_ref'], 'GRANT14829509')
        self.assertEqual(case['stage'], 'VERIFY_RECEIPT')
        self.assertEqual(
            [s['stage'] for s in case['stage_history']],
            ['PREPARE', 'SUBMIT', 'VALIDATE', 'VERIFY_RECEIPT'])
        submit = case['stage_history'][1]
        self.assertEqual(submit['submission_method'], 'PORTAL')
        self.assertEqual(submit['authority_basis'],
                         'FOUNDER_STANDING_GRANT')
        self.assertEqual(case['stage_history'][3]['tracking_ref'],
                         'A-547904')

    def test_seeded_workspace_case_dislocated_worker(self):
        case = self.service.jurisdiction_case(
            OPERATOR, 'OPERATOR', 'WS01787570',
            'PRIVATE_CORPORATE', COMPANY)
        self.assertEqual(case['branch'], 'PRIVATE_CORPORATE')
        self.assertEqual(case['scope_ref'], COMPANY)
        self.assertEqual(case['external_ref'], 'ETA-TEGL-09-24-CH1')
        self.assertIn('Department of Labor', case['funder'])
        self.assertEqual(case['stage'], 'PREPARE')
        self.assertEqual(
            [s['stage'] for s in case['stage_history']], ['PREPARE'])
        entry = case['stage_history'][0]
        self.assertIsNone(entry['tracking_ref'])
        self.assertIsNone(entry['authority_basis'])
        self.assertIn('2026-11-22', entry['note'])
        self.assertIn('2026-12-31', entry['note'])
        self.assertNotIn('founder_authorization_ref',
                         json.dumps(case))

    def test_seeded_workspace_case_justice_research_honest(self):
        case = self.service.jurisdiction_case(
            OPERATOR, 'OPERATOR', 'WS01783365',
            'PRIVATE_CORPORATE', COMPANY)
        self.assertEqual(case['branch'], 'PRIVATE_CORPORATE')
        self.assertEqual(case['scope_ref'], COMPANY)
        self.assertEqual(case['external_ref'], 'O-NIJ-2026-172800')
        self.assertIn('National Institute of Justice',
                      case['funder'])
        # Honesty state: in preparation on the evidence of
        # record — never marked submitted, closed or awarded,
        # with the open question carried on the case itself.
        self.assertEqual(case['stage'], 'PREPARE')
        self.assertEqual(
            [s['stage'] for s in case['stage_history']], ['PREPARE'])
        note = case['stage_history'][0]['note']
        self.assertIn('NOT ESTABLISHED', note)
        self.assertIn('2026-11-15', note)
        self.assertIn('2026-11-16', note)
        self.assertNotIn('founder_authorization_ref',
                         json.dumps(case))

    def test_workspace_seeding_is_idempotent(self):
        tmp = Path(self._tmp.name)
        again = GrantwriterPlatform(
            tmp / 'svc.db', grantwriter_mother.database(),
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=FakeAudit())
        board = again.jurisdiction_board(OPERATOR, 'OPERATOR')
        self.assertEqual(board['cases']['by_branch']
                         ['PRIVATE_CORPORATE'], 3)
        self.assertEqual(board['cases']['by_stage']['PREPARE'], 2)

    def test_seeding_is_idempotent(self):
        tmp = Path(self._tmp.name)
        again = GrantwriterPlatform(
            tmp / 'svc.db', grantwriter_mother.database(),
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=FakeAudit())
        board = again.jurisdiction_board(OPERATOR, 'OPERATOR')
        self.assertEqual(
            len(board['seeded_case']['stage_history']), 4)
        self.assertEqual(board['cases']['by_branch']
                         ['PRIVATE_CORPORATE'], 3)

    def test_status_surfaces_jurisdiction_summary(self):
        status = self.service.status()
        summary = status['service_jurisdiction']
        self.assertTrue(summary['amendment'])
        self.assertEqual(summary['guarded_document'],
                         JURISDICTION_DOCUMENT)
        self.assertEqual(summary['seeded_case']['stage'],
                         'VERIFY_RECEIPT')


class TestRoutes(unittest.TestCase):
    """Route shapes, checked against the dispatcher source
    itself (the full app module imports optional crypto
    dependencies not present in every test environment; the
    patterns are compiled from the exact source text)."""

    def _route(self, name):
        source = (REPO_ROOT / 'app' / 'customer_app.py').read_text(
            encoding='utf-8')
        marker = name + " = re.compile(r'"
        start = source.index(marker) + len(marker)
        pattern = source[start:source.index("'", start)]
        return re.compile(pattern)

    def test_jurisdiction_route_shapes(self):
        self.assertIsNotNone(
            self._route('GW_JURISDICTION_CASE_ROUTE').fullmatch(
                '/api/grantwriter/jurisdiction/cases/A-547904'))
        self.assertIsNotNone(
            self._route('GW_JURISDICTION_CASE_STAGE_ROUTE')
            .fullmatch(
                '/api/grantwriter/jurisdiction/cases/A-547904/stage'))
        self.assertIsNotNone(
            self._route('GW_JURISDICTION_CASE_DISCARD_ROUTE')
            .fullmatch(
                '/api/grantwriter/jurisdiction/cases/A-547904'
                '/discard'))
        self.assertIsNotNone(
            self._route('GW_JURISDICTION_CASE_ALTERNATIVES_ROUTE')
            .fullmatch(
                '/api/grantwriter/jurisdiction/cases/A-547904'
                '/alternative-structures'))
        source = (REPO_ROOT / 'app' / 'customer_app.py').read_text(
            encoding='utf-8')
        self.assertIn("'/api/grantwriter/jurisdiction'", source)


if __name__ == '__main__':
    unittest.main()


# -- Mother upgrade (founder direction 2026-11-26) -------------------


def _fake_discovery_fetch(url, payload):
    """A labeled fake of the Grants.gov public API: three search
    hits; detail amounts for two of them (one above the floor,
    one below); the third's detail answers with no synopsis, so
    no amount is exposed."""
    if url.endswith('search2'):
        return {'data': {'oppHits': [
            {'id': '101', 'number': 'TEST-BIG-1',
             'title': 'Big Health Program',
             'agency': 'Department of Health and Human Services',
             'agencyCode': 'HHS', 'openDate': '11/01/2026',
             'closeDate': '03/01/2027', 'oppStatus': 'posted',
             'cfdaList': ['93.000']},
            {'id': '102', 'number': 'TEST-SMALL-1',
             'title': 'Small Local Grant', 'agency': 'Agency',
             'agencyCode': 'AG', 'openDate': '11/01/2026',
             'closeDate': '01/01/2027', 'oppStatus': 'posted',
             'cfdaList': []},
            {'id': '103', 'number': 'TEST-NOAMT-1',
             'title': 'Amount Not Published', 'agency': 'Agency',
             'agencyCode': 'AG', 'openDate': '11/01/2026',
             'closeDate': '02/01/2027', 'oppStatus': 'posted',
             'cfdaList': []},
        ]}}
    if url.endswith('fetchOpportunity'):
        amounts = {
            101: {'estimatedTotalProgramFunding': '25000000',
                  'awardCeiling': '12000000'},
            102: {'estimatedTotalProgramFunding': '400000',
                  'awardCeiling': '500000'},
        }
        return {'data': {'synopsis': amounts.get(payload['oppId'], {})}}
    raise AssertionError(f'unexpected url {url}')


class TestMotherUpgrade(GrantwriterJurisdictionBase):
    def make_service(self, fetcher=None):
        tmp = Path(self._tmp.name)
        return GrantwriterPlatform(
            tmp / 'svc2.db', grantwriter_mother.database(),
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=FakeAudit(), discovery_fetcher=fetcher)

    def test_pursuit_floor_recorded_and_cancels_nothing(self):
        view = GrantwriterPlatform.jurisdiction_design_view()
        targeting = view['targeting']
        self.assertEqual(targeting['pursuit_floor_usd'], 10_000_000)
        self.assertEqual(gwsvc.PURSUIT_FLOOR_USD, 10_000_000)
        self.assertIn('cancels no case of record',
                      targeting['pursuit_floor_scope'])
        board = self.service.jurisdiction_board(OPERATOR, 'OPERATOR')
        self.assertEqual(board['targeting']['pursuit_floor_usd'],
                         10_000_000)
        # The floor steers new hunts; the cases of record stand.
        self.assertEqual(board['cases']['by_branch']
                         ['PRIVATE_CORPORATE'], 3)
        self.assertEqual(board['seeded_case']['case_id'], 'A-547904')
        self.assertEqual(board['seeded_case']['stage'],
                         'VERIFY_RECEIPT')

    def test_external_partner_refused_by_name(self):
        with self.assertRaises(GrantwriterPlatformForbidden) as ctx:
            self.make_case(opportunity_kind='JOINT',
                           partners=[COMPANY, 'Outside Org Inc.'])
        self.assertIn('GRANTWRITER_EXTERNAL_PARTNER_REFUSED',
                      str(ctx.exception))
        with self.assertRaises(GrantwriterPlatformForbidden):
            self.make_case(branch='PLATFORM_FUNDING',
                           scope='grantwriter',
                           opportunity_kind='COLLABORATIVE',
                           partners=['Some Foundation'])

    def test_internal_joint_case_accepted(self):
        case = self.make_case(
            opportunity_kind='JOINT',
            partners=[COMPANY, OTHER_COMPANY,
                      'Sanders Legal Helpers LLC',
                      'S & G Security Inc.'])
        self.assertEqual(case['opportunity_kind'], 'JOINT')
        self.assertEqual(case['partners'],
                         [COMPANY, OTHER_COMPANY,
                          'Sanders Legal Helpers LLC',
                          'S & G Security Inc.'])
        solo = self.make_case()
        self.assertEqual(solo['partners'], [])

    def test_access_register_states_exact(self):
        entries = {e['system']: e
                   for e in self.service.access_register()}
        self.assertEqual(
            {system: e['state'] for system, e in entries.items()},
            {'JUSTGRANTS': 'KEY_OF_RECORD_ACTIVE',
             'SAM.GOV': 'VERIFIED',
             'GRANTS.GOV': 'VERIFIED',
             'ERA_COMMONS': 'NOT_STARTED',
             'HRSA_EHBS': 'VERIFIED',
             'FEMA_GO': 'VERIFIED',
             'NSF_RESEARCH_GOV': 'VERIFIED',
             'AMERICORPS_EGRANTS': 'VERIFIED',
             'GRANTSOLUTIONS': 'AT_AWARD',
             'PMS': 'AT_AWARD',
             'ASAP': 'AT_AWARD',
             'EU_FUNDING_TENDERS_PORTAL': 'VERIFIED',
             'UNGM': 'VERIFIED',
             'UNRWA': 'VERIFIED',
             'FAO': 'VERIFIED',
             'UNOPS_ESOURCING': 'VERIFIED',
             'WORLD_BANK_VMP': 'SUBMITTED'})
        eu = entries['EU_FUNDING_TENDERS_PORTAL']
        self.assertIn('859635244', eu['basis'])
        self.assertIn('EU Login', eu['basis'])
        self.assertIn('20251946893', eu['detail'])
        self.assertIn('Participant Register', eu['detail'])
        ungm = entries['UNGM']
        self.assertIn('1312370', ungm['basis'])
        self.assertIn('Declaration of Eligibility', ungm['basis'])
        self.assertIn('25 Organizations', ungm['detail'])
        self.assertIn('85101508', ungm['detail'])
        wbvmp = entries['WORLD_BANK_VMP']
        self.assertIn('VMP0016761', wbvmp['basis'])
        self.assertIn('SUBMITTED 2026-11-26', wbvmp['basis'])
        self.assertIn('08/27/2025', wbvmp['detail'])
        self.assertIn('MEDICAL: SERVICES', wbvmp['detail'])
        justgrants = entries['JUSTGRANTS']
        self.assertIn('Entity Administrator', justgrants['basis'])
        self.assertIn('A-547904', justgrants['detail'])
        self.assertIn('daddydik323@gmail.com', justgrants['detail'])
        self.assertIn('Application Submitter', justgrants['detail'])
        hrsa = entries['HRSA_EHBS']
        self.assertIn('QW8BRKNCF573', hrsa['detail'])
        fema = entries['FEMA_GO']
        self.assertIn('Authorized Organization Representative',
                      fema['detail'])
        nsf = entries['NSF_RESEARCH_GOV']
        self.assertIn('0000AB29V', nsf['basis'])
        self.assertIn('QW8BRKNCF573', nsf['detail'])
        self.assertIn('Administrator', nsf['detail'])
        americorps = entries['AMERICORPS_EGRANTS']
        self.assertIn('You now have access to eGrants',
                      americorps['basis'])
        self.assertIn('QW8BRKNCF573', americorps['detail'])
        self.assertIn('RooseveltSanders', americorps['detail'])
        unrwa = entries['UNRWA']
        self.assertIn('accepted 2026-11-27', unrwa['basis'])
        fao = entries['FAO']
        self.assertIn('Food and Agriculture Organization',
                      fao['basis'])
        unops = entries['UNOPS_ESOURCING']
        self.assertIn('United Nations Office for Project '
                      'Services', unops['basis'])
        self.assertIn('1312370', unops['detail'])
        self.assertIn('esourcing.unops.org', unops['detail'])
        sam = entries['SAM.GOV']
        self.assertIn('QW8BRKNCF573', sam['detail'])
        self.assertIn('27KB6', sam['detail'])
        self.assertIn('FJAZARX3NJA6', sam['detail'])
        self.assertIn('J9FUQW4EXQ17', sam['detail'])
        grants = entries['GRANTS.GOV']
        self.assertIn('Expanded AOR', grants['detail'])
        self.assertIn('Workspace Manager', grants['detail'])
        for entry in entries.values():
            self.assertNotIn('password',
                             (entry['basis'] + entry['detail']).lower())
        board = self.service.access_register_board(
            OPERATOR, 'OPERATOR')
        self.assertFalse(board['credentials_held'])
        self.assertEqual(board['principle'],
                         'GLOBAL_BY_DESIGN_KEY_REGISTER')

    def test_access_state_recording_and_credential_refusal(self):
        updated = self.service.record_access_state(
            OPERATOR, 'ERA_COMMONS', 'PENDING',
            basis='Organization registration submitted',
            verified_on='2026-11-27')
        self.assertEqual(updated['state'], 'PENDING')
        entries = {e['system']: e
                   for e in self.service.access_register()}
        self.assertEqual(entries['ERA_COMMONS']['state'], 'PENDING')
        with self.assertRaises(GrantwriterPlatformForbidden):
            self.service.record_access_state(
                'not-the-operator', 'ERA_COMMONS', 'VERIFIED')
        with self.assertRaises(GrantwriterPlatformDenied) as ctx:
            self.service.record_access_state(
                OPERATOR, 'ERA_COMMONS', 'PENDING',
                detail='the password is hunter2')
        self.assertIn('HOLDS_NO_CREDENTIALS', str(ctx.exception))
        with self.assertRaises(GrantwriterPlatformDenied):
            self.service.record_access_state(
                OPERATOR, 'ERA_COMMONS', 'SOMEWHERE')

    def test_discovery_floor_filtering_and_records(self):
        service = self.make_service(_fake_discovery_fetch)
        before = service.jurisdiction_board(
            OPERATOR, 'OPERATOR')['cases']['total']
        run = service.run_discovery_search(OPERATOR, keyword='health')
        self.assertEqual(run['state'], 'CONNECTED')
        self.assertEqual(run['hits_returned'], 3)
        self.assertEqual(run['records_written'], 2)
        self.assertEqual(run['below_floor_filtered'], 1)
        by_number = {r['opp_number']: r for r in run['records']}
        self.assertEqual(by_number['TEST-BIG-1']['floor_verdict'],
                         'MEETS_FLOOR')
        self.assertEqual(
            by_number['TEST-BIG-1']['estimated_total_funding'],
            25_000_000)
        self.assertEqual(by_number['TEST-BIG-1']['award_ceiling'],
                         12_000_000)
        self.assertEqual(by_number['TEST-NOAMT-1']['floor_verdict'],
                         'AMOUNT_NOT_EXPOSED')
        self.assertNotIn('TEST-SMALL-1', by_number)
        board = service.discovery_board(OPERATOR, 'OPERATOR')
        self.assertEqual(board['connection_state'], 'CONNECTED')
        self.assertEqual(board['naics_status'], 'CARRIED_NOT_RULED')
        self.assertEqual(board['naics_codes_carried'],
                         ['541611', '541612', '541613', '541614',
                          '541618', '541690'])
        self.assertFalse(board['auto_creates_cases'])
        self.assertEqual(board['source']['kind'],
                         'LABELED_DETACHABLE_INPUT_TOOL')
        after = service.jurisdiction_board(
            OPERATOR, 'OPERATOR')['cases']['total']
        self.assertEqual(before, after)

    def test_discovery_not_connected_honesty(self):
        def failing_fetch(url, payload):
            raise OSError('network unreachable')

        service = self.make_service(failing_fetch)
        self.assertEqual(service.discovery_connection_state(),
                         'NOT_CONNECTED')
        run = service.run_discovery_search(OPERATOR)
        self.assertEqual(run['state'], 'NOT_CONNECTED')
        self.assertEqual(run['records'], [])
        self.assertEqual(run['records_written'], 0)
        self.assertIn('network unreachable', run['error'])
        board = service.discovery_board(OPERATOR, 'OPERATOR')
        self.assertEqual(board['connection_state'], 'NOT_CONNECTED')
        with self.assertRaises(GrantwriterPlatformForbidden):
            service.run_discovery_search('not-the-operator')
