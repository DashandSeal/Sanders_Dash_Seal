"""Tests for the Bloodline Record Service.

Fixture seals only: every registry seal in this file is the
SHA-256 of a fixture string invented for these tests. No real
registry content, and no real registry seal, appears here.
"""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core_platform.bloodline_record_service import (
    BloodlineRecordDenied,
    BloodlineRecordForbidden,
    BloodlineRecordService,
)
from core_platform.glass_box_audit import GlassBoxAudit


OPERATOR = 'RooseveltSanders'


def _fixture_seal(label):
    return hashlib.sha256(
        ('fixture registry section: ' + label).encode('utf-8')
    ).hexdigest()


SEAL_ONE = _fixture_seal('descendant one')
SEAL_TWO = _fixture_seal('descendant two')


class BloodlineRecordServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.audit_path = tmp / 'audit.db'
        self.db_path = tmp / 'bloodline_records.db'
        audit = GlassBoxAudit(self.audit_path)
        self.service = BloodlineRecordService(
            self.db_path,
            operator_verifier=lambda actor: actor == OPERATOR,
            audit=audit)

    def _establish(self):
        return self.service.establish_record(
            OPERATOR, 'descendant-one', 'Descendant One', SEAL_ONE)

    def test_operator_can_establish(self):
        view = self._establish()
        self.assertEqual(view['person_key'], 'descendant-one')
        self.assertEqual(view['full_name'], 'Descendant One')
        self.assertEqual(view['generation'], 1)
        self.assertEqual(view['authentication_level'], 'FOUNDER_DESIGNATED')
        self.assertEqual(view['registry_seal'], SEAL_ONE)
        self.assertFalse(view['already_current'])
        status = view['vital_records_status']
        self.assertEqual(status['birth_record'], 'NOT_YET_TRACED')
        self.assertEqual(status['death_record'], 'NOT_APPLICABLE_LIVING')
        records = self.service.descendant_records()
        self.assertEqual([r['person_key'] for r in records],
                         ['descendant-one'])

    def test_non_operator_denied(self):
        with self.assertRaises(BloodlineRecordForbidden):
            self.service.establish_record(
                'Mallory', 'descendant-one', 'Descendant One', SEAL_ONE)
        self.assertEqual(self.service.descendant_records(), [])

    def test_verify_record_authenticated_after_establishment(self):
        self._establish()
        result = self.service.verify_record('descendant-one')
        self.assertTrue(result['authenticated'])
        self.assertTrue(result['checks']['record_exists'])
        self.assertTrue(result['checks']['payload_seal_recomputes'])
        self.assertTrue(
            result['checks']['establishing_receipt_in_audit_chain'])

    def test_verify_unknown_person_not_authenticated(self):
        result = self.service.verify_record('nobody')
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['checks']['record_exists'])

    def test_tampered_payload_fails_verification(self):
        self._establish()
        db = sqlite3.connect(self.db_path)
        db.execute(
            "UPDATE bloodline_descendant_records "
            "SET full_name = 'Forged Name' "
            "WHERE person_key = 'descendant-one'")
        db.commit()
        db.close()
        result = self.service.verify_record('descendant-one')
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['checks']['payload_seal_recomputes'])

    def test_no_removal_api_exists(self):
        names = {name.lower() for name in dir(BloodlineRecordService)}
        self.assertFalse(
            any('delete' in name or 'remove' in name for name in names))

    def test_strengthen_only_moves_forward(self):
        self._establish()
        view = self.service.strengthen_record(
            OPERATOR, 'descendant-one', 'birth_record', 'TRACED',
            record_ref='fixture-birth-record-ref')
        self.assertEqual(
            view['vital_records_status']['birth_record'], 'TRACED')
        self.assertEqual(
            view['record_refs']['birth_record'], 'fixture-birth-record-ref')
        self.assertTrue(
            self.service.verify_record('descendant-one')['authenticated'])
        with self.assertRaises(BloodlineRecordDenied):
            self.service.strengthen_record(
                OPERATOR, 'descendant-one', 'birth_record', 'NOT_YET_TRACED')
        with self.assertRaises(BloodlineRecordDenied):
            self.service.strengthen_record(
                OPERATOR, 'descendant-one', 'birth_record', 'TRACED')
        with self.assertRaises(BloodlineRecordDenied):
            self.service.strengthen_record(
                OPERATOR, 'descendant-one', 'death_record', 'TRACED')

    def test_strengthen_requires_operator(self):
        self._establish()
        with self.assertRaises(BloodlineRecordForbidden):
            self.service.strengthen_record(
                'Mallory', 'descendant-one', 'birth_record', 'TRACED')

    def test_duplicate_establishment_idempotent(self):
        first = self._establish()
        second = self._establish()
        self.assertTrue(second['already_current'])
        self.assertEqual(second['receipt_id'], first['receipt_id'])
        self.assertEqual(len(self.service.descendant_records()), 1)
        with self.assertRaises(BloodlineRecordDenied):
            self.service.establish_record(
                OPERATOR, 'descendant-one', 'Descendant One', SEAL_TWO)
        self.assertEqual(len(self.service.descendant_records()), 1)

    def test_audit_receipt_written(self):
        view = self._establish()
        db = sqlite3.connect(self.audit_path)
        rows = db.execute(
            'SELECT body, hash FROM receipts WHERE hash = ?',
            (view['receipt_id'],)).fetchall()
        db.close()
        self.assertEqual(len(rows), 1)
        body = json.loads(rows[0][0])
        self.assertEqual(
            body['event'], 'BLOODLINE_DESCENDANT_RECORD_ESTABLISHED')
        self.assertEqual(body['context']['person_key'], 'descendant-one')
        # No registry content rides in the receipt: only the seal hash.
        self.assertEqual(body['context']['registry_seal'], SEAL_ONE)


if __name__ == '__main__':
    unittest.main()
