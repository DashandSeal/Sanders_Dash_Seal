"""Complete resource mapping is read-only and never invents usage or spending authority."""
import io
import json
from pathlib import Path
import tempfile
import unittest

from core_platform.free_resources import catalog, inventory_mapping, allowance_comparison
from core_platform.deployment import create_application
from deploy.oci_inventory import run_inventory


class FreeResourcesTests(unittest.TestCase):
    def test_all_documented_categories_and_three_sources_are_incorporated(self):
        value = catalog()
        self.assertEqual({source['id'] for source in value['sources']},
                         {'infoq_capacity', 'always_free', 'tenancy_explorer'})
        expected = {'certificates','a1_compute','micro_compute','block_storage','object_storage',
            'vault','resource_manager','autonomous_database','nosql','mysql','placement_groups',
            'flex_load_balancer','network_load_balancer','vcn','flow_logs','site_to_site_vpn',
            'apm','connector_hub','dashboards','email_delivery','fleet_management','monitoring',
            'notifications','outbound_transfer','logging','bastion'}
        self.assertEqual({item['id'] for item in value['resources']}, expected)
        self.assertEqual(value['currency_budget_usd'], 0)
        self.assertEqual(value['spending_authority'], 'Roosevelt Sanders')
        self.assertFalse(value['automatic_provisioning'])
        self.assertTrue(all(item['automatic_provisioning'] is False for item in value['resources']))

    def test_shared_pools_and_account_states_are_not_summed_as_extra_capacity(self):
        entries = {item['id']:item for item in catalog()['resources']}
        self.assertEqual(entries['logging']['shared_pool'], entries['flow_logs']['shared_pool'])
        self.assertEqual(entries['object_storage']['allowances']['free_only_combined_storage_gb'], 20)
        self.assertEqual(entries['a1_compute']['allowances']['continuous_ocpus_total'], 2)
        self.assertEqual(allowance_comparison('object_storage', {'free_only_combined_storage_gb':1},
            {'free_only_combined_storage_gb':0}, account_state='trial')['status'],
            'ACCOUNT_STATE_REQUIRES_SEPARATE_PROFILE')
        with self.assertRaises(ValueError):
            allowance_comparison('object_storage', {'paid_or_trial_standard_gb':1}, {'paid_or_trial_standard_gb':0})

    def test_inventory_type_support_never_establishes_free_entitlement(self):
        report={'scan_complete':True,'resources':[{'resource_type':'Instance'}, {'resource_type':'Streaming'},
                                                 {'resource_type':'NetworkFirewall'}]}
        result=inventory_mapping(report)
        self.assertFalse(result['metered_usage_verified'])
        self.assertFalse(result['free_balance_verified'])
        entries={item['id']:item for item in result['resources']}
        self.assertEqual(entries['a1_compute']['related_observations'], 1)
        self.assertEqual(entries['a1_compute']['usage_status'], 'NOT_METERED_BY_RESOURCE_SEARCH')
        self.assertNotIn('streaming', entries)
        self.assertFalse(catalog()['inventory_semantics']['supported_type_means_free'])

    def test_missing_usage_stays_unknown_and_additions_are_counted(self):
        request={'continuous_ocpus_total':1,'continuous_memory_gb_total':6}
        self.assertEqual(allowance_comparison('a1_compute',request)['status'],'USAGE_UNKNOWN')
        self.assertEqual(allowance_comparison('a1_compute',request,{'continuous_ocpus_total':0})['status'],'USAGE_UNKNOWN')
        first=allowance_comparison('a1_compute',request,{'continuous_ocpus_total':1,'continuous_memory_gb_total':6})
        self.assertEqual(first['status'],'WITHIN_DOCUMENTED_AMOUNTS')
        self.assertFalse(first['billing_verified'])
        self.assertFalse(first['deployment_authorized'])
        second=allowance_comparison('a1_compute',request,{'continuous_ocpus_total':2,'continuous_memory_gb_total':12})
        self.assertEqual(second['status'],'EXCEEDS_DOCUMENTED_AMOUNTS')

    def test_invalid_and_undocumented_inputs_are_not_free_capacity(self):
        for resource, requested, usage in (
            ('streaming',{'partitions':1},{'partitions':0}),
            ('a1_compute',{'continuous_ocpus_total':True},{'continuous_ocpus_total':0}),
            ('a1_compute',{'continuous_ocpus_total':1},{'continuous_ocpus_total':-1}),
            ('a1_compute',{'continuous_ocpus_total':float('nan')},None),
            ('placement_groups',{'groups_maximum_documented':50},{'groups_maximum_documented':0})):
            with self.subTest(resource=resource,requested=requested), self.assertRaises(ValueError):
                allowance_comparison(resource,requested,usage)

    def request(self,path,method='GET',host='sandersdashandseal.com'):
        result={}
        def start(status,headers): result.update(status=status,headers=dict(headers))
        result['body']=b''.join(create_application()({'HTTP_HOST':host,'PATH_INFO':path,
            'REQUEST_METHOD':method,'wsgi.input':io.BytesIO(b'')},start))
        return result

    def test_application_catalog_works_without_business_adapters_and_exposes_no_account_ids(self):
        response=self.request('/api/platform/free-resources')
        self.assertEqual(response['status'],'200 OK')
        value=json.loads(response['body'])
        self.assertEqual(len(value['sources']),3)
        self.assertNotIn(b'ocid1.',response['body'])
        self.assertNotIn(b'129.146.111.166',response['body'])
        self.assertEqual(self.request('/resources')['status'],'200 OK')
        self.assertEqual(self.request('/api/platform/free-resources','POST')['status'],'405 Method Not Allowed')
        self.assertEqual(self.request('/api/platform/free-resources',host='untrusted.example')['status'],'421 Misdirected Request')
        self.assertEqual(self.request('/readyz')['status'],'503 Service Unavailable')

    def test_failed_inventory_keeps_coverage_and_usage_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=run_inventory(root/'missing-config',root/'state')
            self.assertFalse(result['scan_complete'])
            self.assertFalse(result['free_resource_mapping']['scan_complete'])
            self.assertEqual(len(result['free_resource_mapping']['resources']),26)
            self.assertFalse(result['free_resource_mapping']['free_balance_verified'])


if __name__=='__main__': unittest.main()
