"""NACI six-code lock-in (2026-11-26).

Under the founder's directives of 2026-11-26 (reconcile the
platforms that do not have with groups of six NACI industry
codes that would benefit humanity as a whole, not fragmented;
and "Give them purpose"), the NACI six-code reconciliation of
2026-11-26 assigned every platform a reconciled group of six.
This test pins the lock-in: each reconciled platform's built
identity record (PlatformIdentity.naics_codes) carries exactly
its reconciled six, and the ruled sets stand untouched \u2014
the anchored six on Uncle Nickey / Mao and Sanders Home
Healthcare & Caregivers, and JUGGERNAUT's ruled none.

The sixes are read from the module sources by AST so the pin
holds even where a module's own imports need packages the
test environment does not carry; the named platforms are
additionally verified through their live identity records.
"""

import ast
import importlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    'core_platform/ai_doctor_service.py': ('621111', '621511', '541715', '541618', '541690', '561621'),
    'core_platform/application_agent_service.py': ('541511', '541512', '518210', '541519', '541513', '541690'),
    'core_platform/archimedes_service.py': ('541511', '541512', '541513', '518210', '541519', '541330'),
    'core_platform/architect_service.py': ('541511', '541512', '541330', '541690', '518210', '541519'),
    'core_platform/baby_girl_service.py': ('541715', '541618', '621111', '621999', '541690', '561621'),
    'core_platform/backup_recovery_agent_service.py': ('518210', '541513', '541512', '541519', '561499', '541690'),
    'core_platform/bozly_service.py': ('541512', '541211', '541219', '518210', '541511', '541690'),
    'core_platform/cerberus_service.py': ('541512', '518210', '541211', '541690', '519190', '561499'),
    'core_platform/chorus_service.py': ('541511', '541512', '518210', '519130', '541519', '541690'),
    'core_platform/cobol_synthetic_ai_service.py': ('541511', '541512', '541513', '518210', '541519', '541690'),
    'core_platform/configuration_agent_service.py': ('541512', '541513', '541519', '518210', '541511', '541690'),
    'core_platform/database_agent_service.py': ('518210', '541512', '541519', '541513', '541511', '541690'),
    'core_platform/deployment_agent_service.py': ('541511', '541512', '541513', '518210', '541519', '541690'),
    'core_platform/fraud_rtsa_service.py': ('541512', '561611', '518210', '541519', '561621', '541690'),
    'core_platform/gia_mind_service.py': ('621330', '621112', '621999', '541618', '541512', '541690'),
    'core_platform/glass_box_audit_service.py': ('541211', '541512', '518210', '541690', '541219', '561499'),
    'core_platform/grantwriter_service.py': ('541611', '541612', '541618', '541512', '611430', '813211'),
    'core_platform/hydra_q_service.py': ('541512', '541715', '541519', '518210', '561621', '541690'),
    'core_platform/infrastructure_agent_service.py': ('541513', '518210', '541512', '541519', '541330', '541690'),
    'core_platform/integration_agent_service.py': ('541511', '541512', '518210', '541519', '541513', '541690'),
    'core_platform/it_ai_manager.py': ('541513', '541512', '541511', '518210', '541519', '541690'),
    'core_platform/it_support_agent_service.py': ('541513', '541512', '518210', '561499', '541519', '541690'),
    'core_platform/labyrinth_service.py': ('541512', '561621', '541519', '518210', '541690', '541511'),
    'core_platform/labyrinth_shield_service.py': ('541512', '561621', '541519', '518210', '541690', '541511'),
    'core_platform/lil_mama_service.py': ('541512', '541519', '561621', '518210', '541690', '519190'),
    'core_platform/minotaur_service.py': ('541512', '541519', '561621', '518210', '541511', '541690'),
    'core_platform/observability_agent_service.py': ('541512', '518210', '541519', '541513', '541511', '519190'),
    'core_platform/operations_rtsa_service.py': ('541611', '541512', '518210', '561110', '541690', '541614'),
    'core_platform/pbd_manifest_generator.py': ('541511', '541512', '518210', '541519', '541690', '519190'),
    'core_platform/pbd_sentinel.py': ('541512', '561621', '518210', '541519', '541690', '541511'),
    'core_platform/pbd_validation.py': ('541512', '541511', '518210', '541519', '541690', '561499'),
    'core_platform/performance_agent_service.py': ('541512', '541519', '518210', '541513', '541511', '541690'),
    'core_platform/promethean_service.py': ('541512', '561621', '541519', '541690', '518210', '541715'),
    'core_platform/quality_agent_service.py': ('541512', '541519', '541511', '518210', '541690', '561499'),
    'core_platform/sanders_agriculture_service.py': ('115114', '111998', '115115', '115116', '541611', '541618'),
    'core_platform/sanders_ai_psychiatrist_service.py': ('621330', '621112', '541715', '541618', '541690', '561621'),
    'core_platform/sanders_ai_research_service.py': ('541715', '541511', '541512', '541519', '541618', '541690'),
    'core_platform/sanders_analytics_service.py': ('518210', '541512', '541511', '541519', '541618', '541690'),
    'core_platform/sanders_banking_hub_service.py': ('522110', '522320', '541512', '522190', '523930', '541618'),
    'core_platform/sanders_cloud_services_service.py': ('518210', '541512', '541519', '541513', '541511', '541690'),
    'core_platform/sanders_communications_service.py': ('517311', '517312', '517410', '517919', '541810', '541820'),
    'core_platform/sanders_consulting_service.py': ('541611', '541612', '541613', '541614', '541618', '541690'),
    'core_platform/sanders_coordinator_service.py': ('561110', '561499', '541611', '541512', '541618', '561621'),
    'core_platform/sanders_customer_support_service.py': ('561421', '561422', '541512', '561499', '541519', '518210'),
    'core_platform/sanders_education_service.py': ('611710', '611699', '611430', '541618', '541512', '541513'),
    'core_platform/sanders_energy_service.py': ('221122', '221118', '221121', '541715', '541618', '541690'),
    'core_platform/sanders_entertainment_service.py': ('512110', '512120', '512191', '512199', '541810', '541820'),
    'core_platform/sanders_finance_service.py': ('522110', '522390', '523930', '524210', '541611', '541618'),
    'core_platform/sanders_freedom_revolution_service.py': ('813319', '813410', '813910', '813920', '541611', '541618'),
    'core_platform/sanders_global_freedom_service.py': ('813319', '813410', '541618', '541512', '541511', '541513'),
    'core_platform/sanders_global_relations_service.py': ('928120', '541820', '541611', '541618', '519190', '541690'),
    'core_platform/sanders_healthcare_service.py': ('621610', '621999', '541512', '621399', '541618', '624120'),
    'core_platform/sanders_hospitality_service.py': ('721110', '721120', '721191', '721199', '541611', '541618'),
    'core_platform/sanders_human_resources_service.py': ('541612', '561330', '541512', '541611', '561110', '541618'),
    'core_platform/sanders_infrastructure_service.py': ('541512', '518210', '237130', '541513', '541330', '541690'),
    'core_platform/sanders_innovation_lab_service.py': ('541715', '541511', '541512', '541519', '518210', '541690'),
    'core_platform/sanders_intelligence_service.py': ('541910', '561621', '541618', '541512', '541519', '541611'),
    'core_platform/sanders_legal_helpers_service.py': ('541110', '541199', '541611', '541613', '541618', '541690'),
    'core_platform/sanders_legal_services_service.py': ('541110', '541199', '541512', '541611', '518210', '519190'),
    'core_platform/sanders_logical_framework_service.py': ('541511', '541512', '541519', '541611', '541690', '518210'),
    'core_platform/sanders_logistics_service.py': ('484110', '484121', '484122', '488510', '493110', '541614'),
    'core_platform/sanders_manufacturing_service.py': ('332710', '332313', '332322', '332999', '541611', '541618'),
    'core_platform/sanders_marketing_service.py': ('541810', '541613', '541910', '541820', '541512', '519130'),
    'core_platform/sanders_omniconn_service.py': ('541512', '518210', '541511', '541513', '541519', '541618'),
    'core_platform/sanders_patriot_saint_service.py': ('541611', '541612', '541618', '541690', '541512', '541513'),
    'core_platform/sanders_real_estate_service.py': ('531390', '531210', '531311', '531312', '541611', '541618'),
    'core_platform/sanders_recon_service.py': ('541910', '541990', '541611', '541618', '561621', '561110'),
    'core_platform/sanders_research_service.py': ('541715', '541720', '541714', '541618', '541690', '541511'),
    'core_platform/sanders_retail_service.py': ('454110', '445120', '454210', '454390', '541810', '541820'),
    'core_platform/sanders_sales_service.py': ('541613', '561421', '541512', '541618', '541810', '518210'),
    'core_platform/sanders_security_ops_service.py': ('561621', '541512', '541519', '561612', '541618', '518210'),
    'core_platform/sanders_security_service.py': ('561612', '561621', '541512', '541519', '541618', '541690'),
    'core_platform/sanders_senior_living_service.py': ('623110', '623311', '623312', '624120', '621610', '541611'),
    'core_platform/sanders_sentinel_service.py': ('541512', '541519', '541611', '541618', '541690', '561621'),
    'core_platform/sanders_sports_service.py': ('711211', '711212', '711219', '711310', '711320', '541611'),
    'core_platform/sanders_steward_sentinel_service.py': ('541512', '541513', '541519', '561621', '518210', '541690'),
    'core_platform/sanders_strategy_hub_service.py': ('541611', '541618', '541612', '541613', '541614', '541690'),
    'core_platform/sanders_strategy_intel_service.py': ('541611', '541910', '541512', '541618', '541519', '518210'),
    'core_platform/sanders_supply_chain_service.py': ('541614', '493110', '488510', '484110', '541618', '518210'),
    'core_platform/sanders_technology_service.py': ('541511', '541512', '518210', '541519', '541513', '541690'),
    'core_platform/sanders_transportation_service.py': ('484110', '484121', '484122', '485991', '488510', '492110'),
    'core_platform/sanders_wellness_service.py': ('621399', '621498', '621999', '624120', '713940', '541611'),
    'core_platform/sharpshooter_service.py': ('541512', '541513', '541519', '518210', '561621', '541690'),
    'core_platform/showtime_service.py': ('512110', '512120', '512191', '512199', '541810', '541820'),
    'core_platform/sovereign_shield_v3_service.py': ('541512', '561621', '541519', '518210', '541690', '541511'),
    'core_platform/surn_service.py': ('624230', '541512', '518210', '517919', '541690', '922190'),
    'core_platform/the_godfather_service.py': ('541611', '541618', '541512', '541614', '561110', '624230'),
    'core_platform/twin_gate_service.py': ('541512', '541519', '518210', '561621', '541690', '561110'),
    'core_platform/uptime_agent_service.py': ('541513', '541512', '518210', '541519', '561499', '541690'),
    'core_platform/vault.py': ('541512', '518210', '541519', '561621', '541511', '541690'),
}

ANCHORED_SIX = ('621610', '624120', '485991', '532283',
                '423450', '492110')


def identity_naics_codes(relative_path):
    tree = ast.parse(
        (REPO_ROOT / relative_path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(
                node.func, 'id', None) == 'PlatformIdentity':
            for keyword in node.keywords:
                if keyword.arg == 'naics_codes':
                    return tuple(
                        elt.value for elt in keyword.value.elts)
    raise AssertionError('no PlatformIdentity in ' + relative_path)


class TestNaciSixCodeLockIn(unittest.TestCase):

    def test_reconciled_sixes_carried(self):
        for relative_path, codes in EXPECTED.items():
            self.assertEqual(
                identity_naics_codes(relative_path), codes,
                relative_path)

    def test_every_reconciled_six_is_six_distinct_codes(self):
        for relative_path, codes in EXPECTED.items():
            self.assertEqual(len(codes), 6, relative_path)
            self.assertEqual(len(set(codes)), 6, relative_path)

    def test_grantwriter_composed_six(self):
        module = importlib.import_module(
            'core_platform.grantwriter_service')
        self.assertEqual(
            tuple(module.IDENTITY.naics_codes),
            ('541611', '541612', '541618', '541512',
             '611430', '813211'))

    def test_ruled_sets_untouched(self):
        home_healthcare = importlib.import_module(
            'core_platform.home_healthcare')
        self.assertEqual(
            tuple(home_healthcare.IDENTITY.naics_codes),
            ANCHORED_SIX)
        uncle_nickey_mao = importlib.import_module(
            'core_platform.uncle_nickey_mao')
        self.assertEqual(
            tuple(uncle_nickey_mao.IDENTITY.naics_codes),
            ANCHORED_SIX)
        juggernaut = importlib.import_module(
            'core_platform.juggernaut_service')
        self.assertEqual(
            tuple(juggernaut.IDENTITY.naics_codes), ())

    def test_watchdog_disclosure_carried(self):
        for module_name in ('core_platform.lil_mama_service',
                            'core_platform.baby_girl_service'):
            module = importlib.import_module(module_name)
            self.assertIn('watchdogs with no codes',
                          module.__doc__)


if __name__ == '__main__':
    unittest.main()
