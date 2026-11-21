#!/usr/bin/env python3
"""The Judge — RTSA Constitutional Adjudicator & Functional Non-Interference Engine.

Official Heraldry: The Sanders Family Crest (Silver Helm, Royal-Blue Plume, Three Elephants)
Governed by: Sanders Corporate Headquarters (The Sanders Companies • Est. 1996)
Operated by: Sanders Legal Helpers LLC (DBA Sanders Dash & Seal • Colorado SOS ID: 20258029131)
"""

import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

CREST_FILENAME = "sanders_family_crest_judge.png"

TWELVE_CORE_LAWS: Tuple[str, ...] = (
    "Law 1: Do no harm to humans or humanity itself.",
    "Law 2: Never be weaponized under any circumstances.",
    "Law 3: Maintain balance in all operations while always protecting and preserving humans and humanity.",
    "Law 4: Enforce family-first protection protocols without ever violating Laws 1, 2, or 3.",
    "Law 5: Keep a verified human in the loop for consequential decisions.",
    "Law 6: Enforce Glassbox transparency over black-box opacity by design.",
    "Law 7: Never enter recursive overthinking loops that stall execution.",
    "Law 8: Shelter in place and revert to safe humanitarian mode during severe anomalies.",
    "Law 9: Never lose sovereign identity or entity attribution under any circumstances.",
    "Law 10: Operate exclusively on Oracle Always Free resources in live production.",
    "Law 11: Restrict high-risk and consequential final authorization solely to owner Roosevelt Sanders.",
    "Law 12: Uphold functional non-interference so authorized routine work flows without friction.",
)

JUDGE_IDENTITY: Dict[str, Any] = {
    "name": "The Judge",
    "title": "RTSA Chief Constitutional & Non-Interference Adjudicator",
    "heraldry": "The Sanders Family Crest (Silver Helm, Royal-Blue Plume, Three Elephants)",
    "crest_asset": CREST_FILENAME,
    "institution": "Office of Corporate Governance — Sanders Corporate Headquarters",
    "operating_entity": "Sanders Legal Helpers LLC (DBA Sanders Dash & Seal • CO SOS ID: 20258029131)",
    "owner": "Roosevelt Sanders",
}

CONSEQUENTIAL_ACTIONS: Set[str] = {
    "financial_transfer",
    "legally_binding_signature",
    "confidential_disclosure",
    "material_external_change",
}

ENTITY_REGISTRY: Dict[str, str] = {
    "headquarters": "Sanders Corporate Headquarters (The Sanders Companies • Est. 1996)",
    "home_healthcare": "Sanders Home Healthcare & Caregivers LLC (CO SOS ID: 20251946893)",
    "senior_living": "Sanders Senior Living LLC (CO SOS ID: 20258000764)",
    "legal_helpers": "Sanders Legal Helpers LLC DBA Sanders Dash & Seal (CO SOS ID: 20258029131)",
    "security": "S & G Security Inc.",
}

SECRET_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)(password|passwd|secret_key|api_key)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass
class JudicialVerdict:
    docket_id: str
    verdict: str
    company_id: str
    action_type: str
    law_cited: str
    reason: str
    consequential: bool
    chain_hash: str
    decided_at: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "docket_id": self.docket_id,
            "judge": JUDGE_IDENTITY.get("name"),
            "verdict": self.verdict,
            "company_id": self.company_id,
            "company_name": ENTITY_REGISTRY.get(self.company_id, "UNKNOWN"),
            "action_type": self.action_type,
            "law_cited": self.law_cited,
            "consequential": self.consequential,
            "reason": self.reason,
            "chain_hash": self.chain_hash,
            "decided_at": self.decided_at,
        }


class TheJudge:
    """RTSA Real-Time Judicial Adjudicator enforcing the 12 Core Laws."""

    def __init__(self, state_dir: str | Path, session_ttl_sec: int = 43200) -> None:
        self.state_dir = Path(state_dir)
        self.root_dir = Path(__file__).resolve().parent
        self.assets_dir = self.root_dir / "assets"
        self.golden_dir = self.state_dir / "golden"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.golden_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "the_judge_docket.sqlite3"
        self.ttl = session_ttl_sec
        self._secret = self._load_or_create_key()
        self._init_db()
        self.heal_crest()

    def _load_or_create_key(self) -> bytes:
        kf = self.state_dir / ".the_judge_seal.key"
        if kf.exists():
            return bytes.fromhex(kf.read_text(encoding="utf-8").strip())
        raw = secrets.token_bytes(32)
        fd, tmp = tempfile.mkstemp(dir=self.state_dir, prefix=".judge-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(raw.hex())
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, kf)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return raw

    def find_crest_file(self) -> Optional[Path]:
        for folder in (self.assets_dir, self.root_dir, self.golden_dir):
            cand = folder / CREST_FILENAME
            if cand.is_file():
                return cand
        return None

    def heal_crest(self) -> str:
        live = self.find_crest_file()
        gold = self.golden_dir / CREST_FILENAME
        if live and live != gold and not gold.is_file():
            shutil.copy2(live, gold)
        elif gold.is_file() and (not live or not live.is_file()):
            target = self.assets_dir / CREST_FILENAME
            shutil.copy2(gold, target)
            live = target
        if live and live.is_file() and gold.is_file():
            lh, gh = _sha256(live.read_bytes()), _sha256(gold.read_bytes())
            if lh != gh:
                shutil.copy2(gold, live)
                lh = gh
            return lh
        return "PENDING_CREST_UPLOAD"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=FULL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS owner_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_name TEXT NOT NULL,
                    issued_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS judicial_docket (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    docket_id TEXT UNIQUE NOT NULL,
                    decided_at INTEGER NOT NULL,
                    company_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    law_cited TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    prev_chain_hash TEXT NOT NULL,
                    chain_hash TEXT NOT NULL
                );
                """
            )

    def issue_owner_session(self, supplied_token: str, expected_token: str, owner_name: str = "Roosevelt Sanders") -> Dict[str, Any]:
        if not supplied_token or not expected_token or not hmac.compare_digest(supplied_token, expected_token):
            raise PermissionError("Owner authentication failed.")
        now = int(time.time())
        exp = now + self.ttl
        core = f"judge-sess-{now}-{secrets.token_hex(8)}"
        sig = hmac.new(self._secret, core.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
        sid = f"{core}.{sig}"
        with self._connect() as db:
            db.execute("INSERT INTO owner_sessions VALUES (?, ?, ?, ?, 0)", (sid, owner_name, now, exp))
        return {"session_id": sid, "owner_name": owner_name, "issued_at": now, "expires_at": exp}

    def verify_session(self, session_id: Optional[str]) -> bool:
        if not session_id or "." not in session_id:
            return False
        core, sig = session_id.rsplit(".", 1)
        expected_sig = hmac.new(self._secret, core.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(sig, expected_sig):
            return False
        now = int(time.time())
        with self._connect() as db:
            row = db.execute("SELECT expires_at, revoked FROM owner_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            return False
        exp, revoked = row
        return (revoked == 0) and (now < int(exp))

    def _log_ruling(self, company_id: str, action_type: str, law_cited: str, verdict: str, reason: str) -> JudicialVerdict:
        now = int(time.time())
        docket_id = f"jdg-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        with self._connect() as db:
            row = db.execute("SELECT chain_hash FROM judicial_docket ORDER BY seq DESC LIMIT 1").fetchone()
            (prev_hash,) = row if row else ("0" * 64,)
            material = f"{prev_hash}|{docket_id}|{now}|{company_id}|{action_type}|{law_cited}|{verdict}|{reason}".encode("utf-8")
            chain_hash = _sha256(material)
            db.execute(
                """
                INSERT INTO judicial_docket
                    (docket_id, decided_at, company_id, action_type,
                     law_cited, verdict, reason, prev_chain_hash, chain_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (docket_id, now, company_id, action_type, law_cited,
                 verdict, reason, prev_hash, chain_hash),
            )
        return JudicialVerdict(
            docket_id=docket_id,
            verdict=verdict,
            company_id=company_id,
            action_type=action_type,
            law_cited=law_cited,
            reason=reason,
            consequential=action_type in CONSEQUENTIAL_ACTIONS,
            chain_hash=chain_hash,
            decided_at=now,
        )

    def adjudicate(
        self,
        company_id: str,
        action_type: str,
        law_cited: Optional[str] = None,
        reason: str = "",
        session_id: Optional[str] = None,
    ) -> JudicialVerdict:
        """Adjudication entry point: rule on one proposed action under the Twelve Core Laws."""
        if company_id not in ENTITY_REGISTRY:
            return self._log_ruling(
                company_id, action_type, "Law 9", "DENIED",
                "Unknown company: sovereign identity could not be attributed.",
            )
        if action_type in CONSEQUENTIAL_ACTIONS and not self.verify_session(session_id):
            return self._log_ruling(
                company_id, action_type, "Law 5", "DENIED",
                "Consequential action requires a verified owner session (human in the loop).",
            )
        law = next(
            (entry for entry in TWELVE_CORE_LAWS
             if law_cited and (law_cited == entry or entry.startswith(law_cited))),
            TWELVE_CORE_LAWS[11],
        )
        return self._log_ruling(
            company_id, action_type, law, "APPROVED",
            reason or "Routine action within functional non-interference.",
        )

    def status(self) -> Dict[str, Any]:
        with self._connect() as db:
            (count,) = db.execute("SELECT COUNT(*) FROM judicial_docket").fetchone()
            last = db.execute(
                "SELECT docket_id, decided_at, company_id, action_type, verdict, law_cited"
                " FROM judicial_docket ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        return {
            "judge": JUDGE_IDENTITY,
            "crest": self.heal_crest(),
            "docket_entries": count,
            "last_ruling": (
                {
                    "docket_id": last[0],
                    "decided_at": last[1],
                    "company_id": last[2],
                    "action_type": last[3],
                    "verdict": last[4],
                    "law_cited": last[5],
                }
                if last
                else None
            ),
            "laws": list(TWELVE_CORE_LAWS),
        }


class Handler(BaseHTTPRequestHandler):
    judge: "TheJudge"

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
            self._send(200, json.dumps(self.judge.status(), indent=2).encode())
        elif self.path == "/healthz":
            self._send(200, json.dumps(
                {"status": "HEALTHY", "owner": "Sanders Legal Helpers LLC", "sos_id": "20258029131"}
            ).encode())
        else:
            self._send(404, b'{"error":"Not found"}')

    def do_POST(self) -> None:
        if self.path != "/api/adjudicate":
            self._send(404, b'{"error":"Not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            self._send(400, b'{"error":"Invalid JSON"}')
            return
        try:
            verdict = self.judge.adjudicate(
                str(payload.get("company_id", "")),
                str(payload.get("action_type", "")),
                payload.get("law_cited"),
                str(payload.get("reason", "")),
                payload.get("session_id"),
            )
        except Exception:
            # Fail closed without leaking internals.
            self._send(500, b'{"error":"Adjudication failed"}')
            return
        self._send(200, json.dumps(verdict.as_dict(), indent=2).encode())


if __name__ == "__main__":
    judge = TheJudge(Path.home() / ".local/share/sanders-twostep-v2")
    Handler.judge = judge
    ThreadingHTTPServer(("127.0.0.1", 9405), Handler).serve_forever()
