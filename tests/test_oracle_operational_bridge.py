import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from deploy.oracle.operational_bridge import record_cycle
from deploy.oracle.oracle_registry_probe import REGISTRY

class OperationalBridgeTests(unittest.TestCase):
    def test_fault_and_observed_recovery_persist(self):
        entries = json.loads(REGISTRY.read_text(encoding='utf-8'))['platforms']
        def samples(status):
            return [{'id': e['id'], 'name': e['name'], 'host': e['host'],
                     'port': e['port'], 'status': status, 'elapsed_ms': 1}
                    for e in entries]
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'operational.db'
            record_cycle(database, entries, samples('tcp_unreachable'), clock=lambda: 100.0)
            record_cycle(database, entries, samples('tcp_reachable'), clock=lambda: 101.0)
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM ai_canonical_endpoint_observations').fetchone()[0], 76)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ai_canonical_endpoint_incidents WHERE state='OBSERVED_RECOVERY'").fetchone()[0], 38)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ai_canonical_endpoint_incidents WHERE state='OPEN'").fetchone()[0], 0)

    def test_reject_partial_cycle(self):
        entries = json.loads(REGISTRY.read_text(encoding='utf-8'))['platforms']
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                record_cycle(Path(directory) / 'operational.db', entries, [])

if __name__ == '__main__':
    unittest.main()
