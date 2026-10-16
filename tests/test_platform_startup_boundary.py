"""Regression tests: startup must not silently bypass existing security."""
import unittest
from contextlib import contextmanager


@contextmanager
def denied():
    with unittest.TestCase().assertRaises(DeploymentBoundaryDenied):
        yield
from core_platform.platform_startup_boundary import (
    StartupReadiness, DeploymentBoundaryDenied, require_operation,
)


def test_diagnostics_work_without_twin_gate():
    state = StartupReadiness(True, True, True, False, False, False).report()
    assert state["diagnostics_available"] is True
    assert state["consequential_operations_ready"] is False
    assert state["production_ready"] is False


def test_sensitive_operations_fail_closed():
    for action in ["repair", "upgrade", "deploy", "execute_agent"]:
        with denied():
            require_operation(action, owner_halt=False, twin_gate_authorization=False,
                              existing_policy_authorization=True,
                              runtime_protections_verified=True)

def test_owner_halt_prevents_sensitive_operation():
    with denied():
        require_operation("deploy", owner_halt=True, twin_gate_authorization=True,
                          existing_policy_authorization=True,
                          runtime_protections_verified=True)


def test_unknown_operations_are_denied():
    with denied():
        require_operation("unreviewed_action", owner_halt=False,
                          twin_gate_authorization=True,
                          existing_policy_authorization=True,
                          runtime_protections_verified=True)


def test_fully_authorized_operation_passes_boundary():
    assert require_operation("upgrade", owner_halt=False,
                             twin_gate_authorization=True,
                             existing_policy_authorization=True,
                             runtime_protections_verified=True)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value)
        for name, value in globals().items() if name.startswith("test_"))
