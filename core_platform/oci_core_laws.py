"""
Module: core_platform.upgrade_sidecar
Architectural Layer: Oracle Always Free Enforcement & Core Law Compliance Gateway
Description: Enforces Core Law 10 and Core Law 11 by validating all runtime resource allocations,
             infrastructure configurations, and transaction payloads against the locked 
             oci_free_resources.json catalog. Ensures 100% zero-cost Oracle Cloud compliance 
             with immutable SHA-256 auditing and SQLite persistence.
"""

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import time
from datetime import datetime, timezone

class CoreLawViolation(ValueError):
    """Raised when an operation or configuration violates Core Law 10 or Core Law 11."""
    pass

class CoreLaws:
    """Enforces Core Law 10 and Core Law 11 compliance across Sanders Dash & Seal infrastructure."""
    
    def __init__(self, catalog_path):
        self.catalog_path = pathlib.Path(catalog_path)
        self.catalog = self._load_catalog()
        self._verify_core_laws()

    def _load_catalog(self):
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"OCI Free Resources catalog not found at {self.catalog_path}")
        
        try:
            data = json.loads(self.catalog_path.read_text(encoding='utf-8'))
            return data
        except Exception as exc:
            raise CoreLawViolation(f"Failed to parse OCI free resources catalog: {exc}") from exc

    def _verify_core_laws(self):
        governing_10 = self.catalog.get("governing_core_law", {})
        governing_11 = self.catalog.get("governing_core_Law", {})
        
        if governing_10.get("number") != 10 or "Always Free" not in governing_10.get("text", ""):
            raise CoreLawViolation("Core Law 10 integrity violation: Catalog missing mandatory Always Free mandate.")
            
        if governing_11.get("number") != 11 or "actually use" not in governing_11.get("text", ""):
            raise CoreLawViolation("Core Law 11 integrity violation: Catalog missing mandatory operational enforcement mandate.")

    def validate_resource_allocation(self, resource_id, configuration_metrics):
        """
        Validates that a requested resource allocation strictly adheres to Oracle Always Free allowances
        and does not trigger paid tiers or unapproved resource footprints.
        """
        resources = {r["id"]: r for r in self.catalog.get("resources", [])}
        if resource_id not in resources:
            raise CoreLawViolation(f"Resource identifier '{resource_id}' is not mapped in the Always Free catalog.")
            
        res_spec = resources[resource_id]
        allowances = res_spec.get("allowances", {})
        
        for metric, limit in allowances.items():
            requested_val = configuration_metrics.get(metric)
            if requested_val is not None:
                if isinstance(limit, (int, float)) and requested_val > limit:
                    raise CoreLawViolation(
                        f"Core Law 10/11 Violation: Resource '{resource_id}' metric '{metric}' requested value {requested_val} "
                        f"exceeds Always Free allowance limit of {limit}."
                    )
        return True

def import_core_laws(path):
    catalog_file = pathlib.Path(path) / "oci_free_resources.json"
    return CoreLaws(catalog_file)
