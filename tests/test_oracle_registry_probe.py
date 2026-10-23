import importlib.util
import json
from pathlib import Path
import socket
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "deploy" / "oracle" / "oracle_registry_probe.py"
spec = importlib.util.spec_from_file_location("oracle_registry_probe", MODULE)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)

class CanonicalObserverTests(unittest.TestCase):
    def test_complete_registry(self):
        data = json.loads(observer.REGISTRY.read_text(encoding="utf-8"))
        entries = observer.validate(data["platforms"])
        self.assertEqual(len(entries), 38)
        self.assertEqual(entries[0]["name"], "Sanders Sentinel")
        self.assertEqual(entries[-1]["name"], "Sanders Biotech")
        self.assertEqual([e["host"] for e in entries[:12]], ["34.133.172.131"] * 12)
        self.assertEqual([e["host"] for e in entries[12:23]], ["35.238.209.6"] * 11)
        self.assertEqual([e["host"] for e in entries[23:]], ["34.27.79.1"] * 15)

    def test_actual_local_socket_connectivity(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            result = observer.probe({"id": 1, "name": "local", "host": "127.0.0.1", "port": listener.getsockname()[1]}, 1)
            self.assertEqual(result["status"], "tcp_reachable")

    def test_registry_rejects_missing_entry(self):
        entries = json.loads(observer.REGISTRY.read_text(encoding="utf-8"))["platforms"]
        with self.assertRaises(ValueError):
            observer.validate(entries[:-1])

if __name__ == "__main__":
    unittest.main()
