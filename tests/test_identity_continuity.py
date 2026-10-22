import unittest
from copy import deepcopy
from unittest.mock import Mock
from core_platform.identity_continuity import (
    IdentityPreservingExecutor, IdentityContinuityDenied, require_continuity)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.baseline = dict(identity_id="sidecar", role="supervision",
            authority_boundary="owner-scoped", capabilities=["diagnosis"],
            protections=["Twin-Gate", "owner-halt"])
        self.executor = Mock()

    def test_preserves_executor_checks_and_recovery(self):
        candidate = deepcopy(self.baseline)
        candidate['capabilities'].append('translation')
        verifier = Mock(return_value=candidate)
        guard = IdentityPreservingExecutor(self.executor, {'sidecar': self.baseline}, verifier)
        record = {'component': 'sidecar', 'artifact_hash': 'a' * 64}
        guard.stage(record, 'artifact')
        verifier.assert_called_once_with(record, 'artifact')
        self.executor.stage.assert_called_once_with(record, 'artifact')
        guard.verify(record)
        guard.rollback(record)
        self.executor.verify.assert_called_once_with(record)
        self.executor.rollback.assert_called_once_with(record)

    def test_rejects_each_identity_change_and_regression(self):
        for field in self.baseline:
            with self.subTest(field=field):
                candidate = deepcopy(self.baseline)
                candidate[field] = [] if isinstance(candidate[field], list) else 'other'
                guard = IdentityPreservingExecutor(self.executor, {'sidecar': self.baseline},
                                                    lambda *args: candidate)
                with self.assertRaises(IdentityContinuityDenied):
                    guard.stage({'component': 'sidecar'}, 'artifact')
        self.executor.stage.assert_not_called()

    def test_duplicate_identity_denied(self):
        with self.assertRaises(IdentityContinuityDenied):
            IdentityPreservingExecutor(self.executor,
                {'platform': self.baseline, 'sidecar': self.baseline}, lambda *args: None)

    def test_missing_attestation_and_unknown_component_denied(self):
        guard = IdentityPreservingExecutor(self.executor, {'sidecar': self.baseline},
                                          lambda *args: None)
        for component in ('sidecar', 'unknown'):
            with self.assertRaises(IdentityContinuityDenied):
                guard.stage({'component': component}, 'artifact')
        self.executor.stage.assert_not_called()

    def test_baseline_copied_and_verifier_cannot_rewrite_request(self):
        expected = deepcopy(self.baseline)
        def verifier(record, path):
            record['component'] = 'other'
            return expected
        guard = IdentityPreservingExecutor(self.executor, {'sidecar': self.baseline}, verifier)
        self.baseline['identity_id'] = 'changed'
        guard.stage({'component': 'sidecar'}, 'artifact')
        self.executor.stage.assert_called_once_with({'component': 'sidecar'}, 'artifact')

    def test_underlying_denial_propagates(self):
        self.executor.stage.side_effect = RuntimeError('owner halt')
        guard = IdentityPreservingExecutor(self.executor, {'sidecar': self.baseline},
                                          lambda *args: self.baseline)
        with self.assertRaises(RuntimeError):
            guard.stage({'component': 'sidecar'}, 'artifact')
