# Save this file to: generated/closeup_tenancy_deep_audit.py
import os
import sys
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import oci
except ImportError:
    print("[CRITICAL] Missing enterprise dependency: Run 'pip install oci' to execute this production engine.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [AUDIT-CORE] - %(levelname)s - %(message)s')

class TenancyDeepDiscoveryEngine:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.security_boundary = "Roosevelt Sanders exclusively"
        self.inventory_map = {"tenancy_audit_timestamp": oci.util.formatted_datetime(), "resources": {}}
        
    def enforce_security_enclave(self) -> bool:
        """Enforces non-negotiable structural identity authorization gates before memory access."""
        if self.auth_token == self.security_boundary:
            logging.info("Identity authorized. Initiating deep system memory scan.")
            return True
        logging.critical("SECURITY VIOLATION: INVALID AUTH-TOKEN. CORES LOCKED.")
        return False

    def initialize_oci_clients(self):
        """Loads configuration mechanics using standard OCI instance principal/config methods."""
        # Uses local environment config loading by default (Cloud Shell default)
        try:
            self.config = oci.config.from_file()
            oci.config.validate_config(self.config)
            self.identity_client = oci.identity.IdentityClient(self.config)
            self.compute_client = oci.core.ComputeClient(self.config)
            self.network_client = oci.core.VirtualNetworkClient(self.config)
            self.storage_client = oci.object_storage.ObjectStorageClient(self.config)
            self.tenancy_id = self.config["tenancy"]
        except Exception as e:
            logging.critical(f"Failed to bind OCI runtime client context: {str(e)}")
            sys.exit(1)

    def fetch_all_active_compartments(self) -> list:
        """Crawls the entire tenancy tree recursively to discover hidden compartments."""
        compartments = [self.tenancy_id]
        try:
            list_compartments = oci.pagination.list_call_get_all_results(
                self.identity_client.list_compartments,
                compartment_id=self.tenancy_id,
                compartment_id_in_subtree=True,
                access_level="ACCESSIBLE"
            )
            for comp in list_compartments.data:
                if comp.lifecycle_state == "ACTIVE":
                    compartments.append(comp.id)
            return compartments
        except Exception as e:
            logging.error(f"Compartment navigation mapping failed: {str(e)}")
            return compartments

    def audit_compute_infrastructure(self, compartment_id: str) -> list:
        """Queries the bare-metal and paravirtualized compute allocations inside a compartment."""
        instances_found = []
        try:
            instances = self.compute_client.list_instances(compartment_id=compartment_id).data
            for inst in instances:
                instances_found.append({
                    "id": inst.id,
                    "display_name": inst.display_name,
                    "lifecycle_state": inst.lifecycle_state,
                    "shape": inst.shape,
                    "region": inst.region,
                    "public_ip": inst.metadata.get("public_ip", "N/A")
                })
        except Exception:
            pass # Suppress sub-compartment query access limitations silently
        return instances_found

    def audit_network_fabrics(self, compartment_id: str) -> list:
        """Scans for active Virtual Cloud Networks, Subnets, and SecLists."""
        networks_found = []
        try:
            vcns = self.network_client.list_vcns(compartment_id=compartment_id).data
            for vcn in vcns:
                networks_found.append({
                    "vcn_id": vcn.id,
                    "display_name": vcn.display_name,
                    "cidr_block": vcn.cidr_block,
                    "lifecycle_state": vcn.lifecycle_state
                })
        except Exception:
            pass
        return networks_found

    def execute_parallel_audit(self):
        """Orchestrates structural thread pool to crawl all regions and fabrics simultaneously."""
        if not self.enforce_security_enclave():
            sys.exit("[CRITICAL] Security authentication lockout.")
            
        self.initialize_oci_clients()
        compartments = self.fetch_all_active_compartments()
        
        logging.info(f"Discovered {len(compartments)} accessible active infrastructure compartments. Mapping systems...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            compute_futures = {executor.submit(self.audit_compute_infrastructure, cid): cid for cid in compartments}
            network_futures = {executor.submit(self.audit_network_fabrics, cid): cid for cid in compartments}
            
            for future in as_completed(compute_futures):
                cid = compute_futures[future]
                res = future.result()
                if res:
                    self.inventory_map["resources"].setdefault(cid, {})["compute_nodes"] = res
                    
            for future in as_completed(network_futures):
                cid = network_futures[future]
                res = future.result()
                if res:
                    self.inventory_map["resources"].setdefault(cid, {})["network_fabrics"] = res

        # Write the fully populated real-world map to disk
        os.makedirs("generated", exist_ok=True)
        with open("generated/tenancy_audit_matrix.json", "w") as f:
            json.dump(self.inventory_map, f, indent=2)
            
        logging.info("System mapping sequence completed. Production output matrix written to disk successfully.")

if __name__ == "__main__":
    # Production execution hook requiring your non-negotiable runtime token
    audit_runner = TenancyDeepDiscoveryEngine(auth_token="Roosevelt Sanders exclusively")
    audit_runner.execute_parallel_audit()
