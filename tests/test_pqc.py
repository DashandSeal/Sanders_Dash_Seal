"""Post-quantum cryptography tests: ML-KEM-768 key exchange and ML-DSA-65
signatures (NIST FIPS 203 / 204) via the ``cryptography`` library, plus
the Bozly CFO ledger-entry signing layer and the PaymentLedger PQC
signature layer.

Real PQC operations only — no stubs, no fake "quantum-safe" claims.
Tests that need a working PQC backend are skipped with a clear reason
when the runtime cannot perform PQC (e.g. cryptography 47.0.0 on
OpenSSL 3.0); the fail-closed tests run in every runtime. No live keys,
no network, temp SQLite files only.
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core_platform import pqc
from core_platform.bozly import pqc_ledger
from core_platform.stripe_payments import PaymentDenied, PaymentLedger


def _pqc_or_skip(test):
    if not pqc.available():
        test.skipTest("PQC unavailable in this runtime: " + str(pqc.status().get("reason")))


class TestPQCStatus(unittest.TestCase):
    def test_status_shape_is_honest(self):
        report = pqc.status()
        self.assertIn("available", report)
        self.assertIn("kem_algorithm", report)
        self.assertIn("signature_algorithm", report)
        self.assertIn("min_verified_library_version", report)
        if report["available"]:
            self.assertEqual(report["kem_algorithm"], "ML-KEM-768")
            self.assertEqual(report["signature_algorithm"], "ML-DSA-65")
            self.assertIsNone(report["reason"])
        else:
            self.assertIsNone(report["kem_algorithm"])
            self.assertIsNone(report["signature_algorithm"])
            self.assertIsNotNone(report["reason"])

    def test_unavailable_backend_raises_fail_closed(self):
        # Simulate a runtime whose backend cannot do PQC.
        original = pqc._BACKEND
        try:
            pqc._BACKEND = pqc._Backend.__new__(pqc._Backend)
            pqc._BACKEND.available = False
            pqc._BACKEND.library_version = None
            pqc._BACKEND.reason = "simulated: pqc_not_supported_by_backend"
            self.assertFalse(pqc.available())
            with self.assertRaises(pqc.PQCUnavailableError):
                pqc.generate_kem_keypair()
            with self.assertRaises(pqc.PQCUnavailableError):
                pqc.generate_signing_keypair()
            self.assertFalse(pqc.status()["available"])
        finally:
            pqc._BACKEND = original


class TestMLKEM(unittest.TestCase):
    def test_kem_roundtrip_shared_secret_matches(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_kem_keypair()
        shared_secret, ciphertext = pqc.kem_encapsulate(public_der)
        self.assertEqual(len(shared_secret), 32)
        self.assertEqual(len(ciphertext), 1088)
        self.assertEqual(pqc.kem_decapsulate(private_der, ciphertext), shared_secret)

    def test_kem_wrong_private_key_gives_different_secret(self):
        _pqc_or_skip(self)
        _, public_der = pqc.generate_kem_keypair()
        other_private, _ = pqc.generate_kem_keypair()
        shared_secret, ciphertext = pqc.kem_encapsulate(public_der)
        self.assertNotEqual(
            pqc.kem_decapsulate(other_private, ciphertext), shared_secret
        )

    def test_kem_bad_ciphertext_rejected(self):
        # ML-KEM uses implicit rejection: a tampered (but well-formed)
        # ciphertext decapsulates to an unrelated secret instead of
        # raising, so the peer's key will not match. A structurally
        # invalid ciphertext (wrong length) raises ValueError.
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_kem_keypair()
        shared_secret, ciphertext = pqc.kem_encapsulate(public_der)
        tampered = bytes([ciphertext[0] ^ 0xFF]) + ciphertext[1:]
        self.assertNotEqual(pqc.kem_decapsulate(private_der, tampered), shared_secret)
        with self.assertRaises(ValueError):
            pqc.kem_decapsulate(private_der, ciphertext[:10])

    def test_derive_session_key_binds_to_context(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_kem_keypair()
        shared_secret, ciphertext = pqc.kem_encapsulate(public_der)
        key_a = pqc.derive_session_key(shared_secret, b"session-1")
        key_b = pqc.derive_session_key(shared_secret, b"session-2")
        self.assertEqual(len(key_a), 32)
        self.assertNotEqual(key_a, key_b)
        self.assertEqual(
            key_a, pqc.derive_session_key(shared_secret, b"session-1")
        )


class TestMLDSA(unittest.TestCase):
    def test_sign_and_verify_roundtrip(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_signing_keypair()
        signature = pqc.sign(private_der, b"ledger-entry-1")
        self.assertTrue(pqc.verify(public_der, b"ledger-entry-1", signature))

    def test_tampered_message_fails(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_signing_keypair()
        signature = pqc.sign(private_der, b"amount=100")
        self.assertFalse(pqc.verify(public_der, b"amount=101", signature))

    def test_tampered_signature_fails(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_signing_keypair()
        signature = pqc.sign(private_der, b"amount=100")
        tampered = bytes([signature[0] ^ 0x01]) + signature[1:]
        self.assertFalse(pqc.verify(public_der, b"amount=100", tampered))

    def test_wrong_public_key_fails(self):
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_signing_keypair()
        _, other_public = pqc.generate_signing_keypair()
        signature = pqc.sign(private_der, b"amount=100")
        self.assertFalse(pqc.verify(other_public, b"amount=100", signature))

    def test_malformed_public_key_fails_not_raises(self):
        _pqc_or_skip(self)
        private_der, _ = pqc.generate_signing_keypair()
        signature = pqc.sign(private_der, b"amount=100")
        self.assertFalse(pqc.verify(b"not-a-key", b"amount=100", signature))

    def test_canonical_bytes_deterministic(self):
        record = {"b": 2, "a": [1, {"z": 3, "y": 4}]}
        self.assertEqual(pqc.canonical_bytes(record), pqc.canonical_bytes(record))
        self.assertEqual(
            pqc.canonical_bytes(record), b'{"a":[1,{"y":4,"z":3}],"b":2}'
        )


class TestBozlyLedgerSigning(unittest.TestCase):
    def test_sign_and_verify_ledger_entry(self):
        _pqc_or_skip(self)
        private_der, _ = pqc_ledger.generate_ledger_signing_keypair()
        entry = {
            "event_id": "evt_test_1",
            "event_type": "checkout.session.completed",
            "amount": 1000,
            "currency": "usd",
            "state": "PAID_EVENT_OBSERVED",
        }
        signed = pqc_ledger.sign_ledger_entry(private_der, entry)
        self.assertEqual(signed["pqc_algorithm"], "ML-DSA-65")
        self.assertEqual(signed["event_id"], "evt_test_1")
        self.assertTrue(pqc_ledger.verify_ledger_entry(signed))

    def test_tampered_ledger_entry_fails(self):
        _pqc_or_skip(self)
        private_der, _ = pqc_ledger.generate_ledger_signing_keypair()
        signed = pqc_ledger.sign_ledger_entry(
            private_der, {"event_id": "evt_test_2", "amount": 1000}
        )
        signed["amount"] = 1001
        self.assertFalse(pqc_ledger.verify_ledger_entry(signed))

    def test_unsigned_entry_fails(self):
        self.assertFalse(
            pqc_ledger.verify_ledger_entry({"event_id": "evt_x", "amount": 1})
        )

    def test_double_sign_refused(self):
        _pqc_or_skip(self)
        private_der, _ = pqc_ledger.generate_ledger_signing_keypair()
        signed = pqc_ledger.sign_ledger_entry(
            private_der, {"event_id": "evt_test_3", "amount": 5}
        )
        with self.assertRaises(ValueError):
            pqc_ledger.sign_ledger_entry(private_der, signed)


class TestPaymentLedgerPQC(unittest.TestCase):
    def _recorded_ledger(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        ledger = PaymentLedger(tmp.name)
        event = {
            "id": "evt_pqc_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "client_reference_id": "case_1",
                    "payment_intent": "pi_test_1",
                    "amount_total": 1000,
                    "currency": "usd",
                    "payment_status": "paid",
                }
            },
        }
        ledger.register_checkout("case_1", "cs_test_1", 1000, "usd")
        self.assertEqual(ledger.record_event(event), "RECORDED")
        return ledger

    def test_sign_and_verify_recorded_event(self):
        _pqc_or_skip(self)
        ledger = self._recorded_ledger()
        private_der, _ = pqc.generate_signing_keypair()
        result = ledger.sign_recorded_event("evt_pqc_1", private_der)
        self.assertEqual(result["algorithm"], "ML-DSA-65")
        self.assertTrue(ledger.verify_recorded_event("evt_pqc_1"))

    def test_unsigned_recorded_event_fails_verification(self):
        ledger = self._recorded_ledger()
        self.assertFalse(ledger.verify_recorded_event("evt_pqc_1"))

    def test_unknown_event_cannot_be_signed(self):
        _pqc_or_skip(self)
        ledger = self._recorded_ledger()
        private_der, _ = pqc.generate_signing_keypair()
        with self.assertRaises(PaymentDenied):
            ledger.sign_recorded_event("evt_nope", private_der)

    def test_tampered_record_fails_verification(self):
        _pqc_or_skip(self)
        ledger = self._recorded_ledger()
        private_der, _ = pqc.generate_signing_keypair()
        ledger.sign_recorded_event("evt_pqc_1", private_der)
        import sqlite3

        with sqlite3.connect(ledger.self_path) as db:
            db.execute(
                "UPDATE stripe_events SET event_type = ? WHERE event_id = ?;",
                ("charge.refunded", "evt_pqc_1"),
            )
            db.commit()
        self.assertFalse(ledger.verify_recorded_event("evt_pqc_1"))


class TestPQCRealTime(unittest.TestCase):
    def test_operations_complete_in_real_time(self):
        """Every PQC operation must finish in well under 1 second.

        Real-time bound is generous on purpose: measured medians on
        this host are a few milliseconds. Anything over 1s is a
        failure, not a slow pass.
        """
        _pqc_or_skip(self)
        private_der, public_der = pqc.generate_signing_keypair()
        kem_private, kem_public = pqc.generate_kem_keypair()
        message = b"real-time check"
        for name, fn in (
            ("kem_encapsulate", lambda: pqc.kem_encapsulate(kem_public)),
            ("kem_decapsulate", lambda: pqc.kem_decapsulate(
                kem_private, pqc.kem_encapsulate(kem_public)[1])),
            ("sign", lambda: pqc.sign(private_der, message)),
            ("verify", lambda: pqc.verify(
                public_der, message, pqc.sign(private_der, message))),
        ):
            samples = [time.perf_counter()]
            for _ in range(5):
                fn()
                samples.append(time.perf_counter())
            elapsed = max(b - a for a, b in zip(samples, samples[1:]))
            self.assertLess(
                elapsed, 1.0, f"{name} took {elapsed:.3f}s, over the 1s real-time bound"
            )


if __name__ == "__main__":
    unittest.main()
