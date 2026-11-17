#!/usr/bin/env python3
"""The Sanders TwoStep v2 - Sanders Legal Helpers LLC (CO SOS ID: 20258029131)."""

import hashlib, hmac, json, os, secrets, shutil, sqlite3, time, zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BRAND = {
    "system": "The Sanders TwoStep v2",
    "headquarters": "Sanders Corporate Headquarters - The Sanders Companies (Est. 1996)",
    "operating_entity": "Sanders Legal Helpers LLC",
    "dba": "Sanders Dash & Seal",
    "colorado_sos_id": "20258029131",
    "entities": (
        "Sanders Home Healthcare & Caregivers LLC (SOS 20251946893)",
        "Sanders Senior Living LLC (SOS 20258000764)",
        "Sanders Legal Helpers LLC DBA Sanders Dash & Seal (SOS 20258029131)",
        "S & G Security Inc.",
    ),
}

TIERS = {
    "INTERNAL_ECOSYSTEM": {"monthly_usd": 0.0, "per_bundle_usd": 0.0},
    "B2B_SAAS_GATEWAY": {"monthly_usd": 199.0, "per_bundle_usd": 0.05},
    "ATTESTATION_CERTIFICATE": {"monthly_usd": 0.0, "per_bundle_usd": 5.0},
    "ENTERPRISE_WHITE_LABEL": {"monthly_usd": 1250.0, "per_bundle_usd": 0.0},
}


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fec_encode(data: bytes) -> tuple[bytes, bytes, bytes, int]:
    n = len(data)
    pad = data + (b"\x00" if n % 2 else b"")
    half = len(pad) // 2
    s0, s1 = pad[:half], pad[half:]
    parity = bytes(a ^ b for a, b in zip(s0, s1))
    return s0, s1, parity, n


def fec_heal(s0: bytes, parity: bytes, n: int) -> bytes:
    s1 = bytes(a ^ b for a, b in zip(s0, parity))
    return (s0 + s1)[:n]


class TwoStepEngine:
    def __init__(self, base_dir: Path) -> None:
        self.base = base_dir
        self.root = Path(__file__).resolve().parent
        self.assets = self.root / "assets"
        self.golden = self.base / "golden"
        self.base.mkdir(parents=True, exist_ok=True)
        self.assets.mkdir(parents=True, exist_ok=True)
        self.golden.mkdir(parents=True, exist_ok=True)
        self.db = self.base / "twostep.sqlite3"
        self.key = self._get_key()
        self._init_db()
        self.heal_assets()

    def _get_key(self) -> bytes:
        kf = self.base / ".hmac.key"
        if kf.exists():
            return bytes.fromhex(kf.read_text(encoding="utf-8").strip())
        k = secrets.token_bytes(32)
        kf.write_text(k.hex(), encoding="utf-8")
        os.chmod(kf, 0o600)
        return k

    def _init_db(self) -> None:
        with sqlite3.connect(self.db) as c:
            c.execute("CREATE TABLE IF NOT EXISTS bundles (id TEXT PRIMARY KEY, tier TEXT, sha TEXT, mac TEXT, receipt TEXT, healed INT, fee REAL, ts INT)")
            c.execute("CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts INT, event TEXT, hash TEXT)")

    def discover_seals(self) -> dict[str, Path]:
        found: dict[str, Path] = {}
        for folder in (self.root, self.assets, self.golden):
            if folder.is_dir():
                for fp in sorted(folder.glob("*.png")):
                    found.setdefault(fp.name, fp)
        return found

    def heal_assets(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for fn, src in self.discover_seals().items():
            gold = self.golden / fn
            if src.is_file() and not gold.is_file():
                shutil.copy2(src, gold)
            elif gold.is_file() and not src.is_file():
                shutil.copy2(gold, src)
            if src.is_file() and gold.is_file():
                if sha256_hex(src.read_bytes()) != sha256_hex(gold.read_bytes()):
                    shutil.copy2(gold, src)
                out[fn] = sha256_hex(src.read_bytes())
        return out

    def seal_and_dispatch(self, topic: str, payload: dict, tier: str = "INTERNAL_ECOSYSTEM") -> dict:
        comp = zlib.compress(json.dumps({"topic": topic, "payload": payload}, sort_keys=True).encode())
        s0, _s1, parity, n = fec_encode(comp)
        healed = fec_heal(s0, parity, n)
        digest = sha256_hex(healed)
        bid = f"ts2-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        mac = hmac.new(self.key, f"{bid}|{digest}".encode(), hashlib.sha256).hexdigest()
        receipt = sha256_hex(f"ATTESTED|{bid}|{digest}".encode())
        fee = float(TIERS.get(tier, TIERS["INTERNAL_ECOSYSTEM"])["per_bundle_usd"])
        now = int(time.time())
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO bundles VALUES (?, ?, ?, ?, ?, 1, ?, ?)", (bid, tier, digest, mac, receipt, fee, now))
            c.execute("INSERT INTO audit (ts, event, hash) VALUES (?, ?, ?)", (now, f"STEP2:{bid}", receipt))
        return {"bundle_id": bid, "state": "STEP2_ATTESTED", "fec_self_healed": True, "receipt": receipt, "fee_usd": fee}

    def status(self) -> dict:
        with sqlite3.connect(self.db) as c:
            (cnt,) = c.execute("SELECT COUNT(*) FROM bundles").fetchone()
            (rev,) = c.execute("SELECT COALESCE(SUM(fee), 0.0) FROM bundles").fetchone()
        return {"brand": BRAND, "tiers": TIERS, "bundles_attested": cnt, "accrued_revenue_usd": round(rev, 2), "seals": self.heal_assets()}


class Handler(BaseHTTPRequestHandler):
    eng: TwoStepEngine

    def log_message(self, *args) -> None:
        return

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/api/status"):
            self._send(200, json.dumps(self.eng.status(), indent=2).encode())
        elif self.path == "/healthz":
            self._send(200, json.dumps({"status": "HEALTHY", "owner": "Sanders Legal Helpers LLC", "sos_id": "20258029131"}).encode())
        elif self.path.startswith("/assets/"):
            fn = Path(self.path).name
            seals = self.eng.discover_seals()
            fp = seals.get(fn)
            if fp and fp.is_file():
                self._send(200, fp.read_bytes(), "image/png")
            else:
                self._send(404, b'{"error":"Seal not found"}')
        else:
            self._send(404, b'{"error":"Not found"}')


if __name__ == "__main__":
    engine = TwoStepEngine(Path.home() / ".local/share/sanders-twostep-v2")
    engine.seal_and_dispatch("sovereign.startup", {"sos_id": "20258029131"})
    Handler.eng = engine
    ThreadingHTTPServer(("127.0.0.1", 9400), Handler).serve_forever()
