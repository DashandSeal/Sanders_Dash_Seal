"""Internal readiness reporting; verdicts are not credentials or execution grants.

Call only with results from trusted policy adapters. This module neither executes
operations nor replaces cryptographic verification in the actual executor.
"""
from dataclasses import dataclass


class DeploymentBoundaryDenied(ValueError):
    pass


@dataclass(frozen=True)
class StartupReadiness:
    configuration_valid: bool
    identity_inventory_valid: bool
    diagnostics_healthy: bool
    twin_gate_verified: bool
    runtime_protections_verified: bool
    production_connections_verified: bool

    def report(self):
        diagnostics = all(value is True for value in (
            self.configuration_valid, self.identity_inventory_valid,
            self.diagnostics_healthy))
        consequential = diagnostics and all(value is True for value in (
            self.twin_gate_verified, self.runtime_protections_verified))
        return {"diagnostics_available": diagnostics,
                "consequential_operations_ready": consequential,
                "production_ready": consequential and
                self.production_connections_verified is True}


def require_operation(action, *, owner_halt, twin_gate_authorization,
                      existing_policy_authorization, runtime_protections_verified):
    """Combine trusted internal verdicts, never accept these flags from an API."""
    if action not in ("repair", "upgrade", "deploy", "execute_agent"):
        raise DeploymentBoundaryDenied("Unknown consequential operation")
    if owner_halt is not False or not all(value is True for value in (
        twin_gate_authorization, existing_policy_authorization,
        runtime_protections_verified
    )):
        raise DeploymentBoundaryDenied("Consequential operation not authorized")
    return True
