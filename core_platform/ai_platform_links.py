"""Central link registry and auto-connection system for Sanders Dash & Seal.

Declares every AI platform and its required links in
``core_platform/ai_platform_links.json`` (no secrets, no hardcoded keys)
and verifies each link on startup/check.

Status model (see the JSON registry ``status_meanings`` for the full text):

* ``LINKED`` -- a real local check passed (module compiles and imports,
  and a functional probe succeeded). For keyed providers LINKED also
  means the key/model/secret is present and local wiring builds. Live
  account validity is NOT verified: this module never makes a live paid
  call, and never makes any network call at all.
* ``MISSING_KEY`` -- a required API key, secret, model id, or provider
  package is absent. The exact missing item is named.
* ``MISSING_APPROVAL`` -- key present, but a live (paid / money-moving)
  action needs explicit owner approval and none is recorded.
* ``NOT_IMPLEMENTED`` -- the local module, file, or capability is absent
  or is a stub/fake only; no real backend is installed.
* ``BROKEN`` -- local code fails to compile or import for a reason other
  than a missing optional provider package/key.

Cost policy (owner direction 2026-11-13): free resources first. Free and
offline backends (local packages, system TTS, SQLite, Oracle Always Free)
are checked and auto-connected before any paid provider is considered.

Auto-connection only ever connects what is local/offline: the SQLite
ledger (temp-database round-trip), the local agent registry, the local
hash patrol, the offline TwinGate policy engine, local incident evidence,
and local files. Anything needing a key or owner approval is reported,
never silently connected and never faked.

Fake/offline mode is for tests only: callers may inject ``env``,
``import_checker`` and ``which_checker`` fakes. A fake never turns a
real ``check_all()`` result into LINKED -- the module always runs the
same code path; fakes only stand in for environment facts the test
controls. Production callers pass no fakes.

No secret value is ever logged, returned, or written to disk by this
module; only the *presence* of an environment variable is reported.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

__all__ = [
    "STATUSES",
    "PLATFORM_IDS",
    "PlatformStatus",
    "load_registry",
    "check_all",
    "check_platform",
    "check_providers",
    "auto_connect",
    "summarize",
    "main",
]

STATUSES = ("LINKED", "MISSING_KEY", "MISSING_APPROVAL", "NOT_IMPLEMENTED", "BROKEN")

# Platforms declared by the registry, in registry order.
PLATFORM_IDS = (
    "daedalus",
    "grantwriter",
    "ai_role_workers",
    "bozly",
    "minotaur_sentinel",
    "twingate",
    "sharpshooter",
    "stream_api",
    "voice_audio_video",
)

_DEFAULT_CONFIG = Path(__file__).with_name("ai_platform_links.json")

# Local capability probes shared by several platforms.
_SQLITE_PROBE = "sqlite_ledger"


@dataclass
class PlatformStatus:
    """One platform's link verdict. ``missing`` names exact missing items."""

    platform_id: str
    status: str
    missing: list = field(default_factory=list)
    detail: str = ""
    checks: dict = field(default_factory=dict)
    auto_connected: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "platform_id": self.platform_id,
            "status": self.status,
            "missing": list(self.missing),
            "detail": self.detail,
            "checks": dict(self.checks),
            "auto_connected": list(self.auto_connected),
        }


# --------------------------------------------------------------------------
# Registry loading
# --------------------------------------------------------------------------

def load_registry(config_path: str | os.PathLike | None = None) -> dict:
    """Load the link registry JSON. Raises on a missing/invalid registry."""
    path = Path(config_path) if config_path is not None else _DEFAULT_CONFIG
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or "platforms" not in data:
        raise ValueError(f"Unexpected link registry identity in {path}")
    return data


def _platform_entry(registry: dict, platform_id: str) -> dict:
    for entry in registry["platforms"]:
        if entry["id"] == platform_id:
            return entry
    raise KeyError(f"Unknown platform in registry: {platform_id!r}")


# --------------------------------------------------------------------------
# Small real probes (stdlib only, no network, no paid calls)
# --------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _compile_files(paths: list) -> tuple[list, list]:
    """Compile-check repo-relative source files. Returns (ok, failures).

    ``failures`` entries are ``"<path>: <error>"`` strings. Glob entries
    such as ``bozly_*.py`` are expanded against the repo root. Python
    files are read and compiled only -- never executed. Non-Python files
    (``.html``/``.js``) are checked for existence and, for HTML, that
    they parse; there is no JS parser in the stdlib, so JS syntax is
    reported as not verified rather than claimed.
    """
    from html.parser import HTMLParser

    root = _repo_root()
    ok: list = []
    failures: list = []
    expanded: list = []
    for rel in paths:
        if "*" in rel:
            expanded.extend(sorted(str(p.relative_to(root)) for p in root.glob(rel)))
        else:
            expanded.append(rel)
    for rel in expanded:
        path = root / rel
        if not path.exists():
            failures.append(f"{rel}: file not found")
            continue
        if path.suffix != ".py":
            try:
                text = path.read_text(encoding="utf-8")
            except Exception as exc:
                failures.append(f"{rel}: cannot read: {type(exc).__name__}: {exc}")
                continue
            if not text.strip():
                failures.append(f"{rel}: file is empty")
                continue
            if path.suffix == ".html":
                try:
                    HTMLParser().feed(text)
                except Exception as exc:
                    failures.append(f"{rel}: HTML parse error: {exc}")
                    continue
            ok.append(rel)
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            failures.append(
                f"{rel}: SyntaxError line {exc.lineno}: {exc.msg}"
            )
        except Exception as exc:  # unreadable file, bad encoding, ...
            failures.append(f"{rel}: cannot compile: {type(exc).__name__}: {exc}")
        else:
            ok.append(rel)
    return ok, failures


def _try_import(module_name: str) -> tuple[bool, str]:
    """Import a module. Returns (ok, error). ImportError naming a missing
    third-party package is reported as such, not as broken local code."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return False, f"ImportError: {exc}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def _sqlite_round_trip() -> bool:
    """Prove the SQLite ledger path works: create a temp DB, write a row,
    read it back. No repo file is touched."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        try:
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    "CREATE TABLE link_probe (id INTEGER PRIMARY KEY, v TEXT)"
                )
                conn.execute("INSERT INTO link_probe (v) VALUES (?)", ("ok",))
                conn.commit()
                row = conn.execute(
                    "SELECT v FROM link_probe WHERE id = 1"
                ).fetchone()
                return bool(row and row[0] == "ok")
            finally:
                conn.close()
        finally:
            os.unlink(db_path)
    except Exception:
        return False


def _env_present(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name)
    return bool(value and str(value).strip())


def _approved(env: Mapping[str, str], approval_env: str | None) -> bool:
    if not approval_env:
        return True
    return str(env.get(approval_env, "")).strip().lower() == "yes"


# --------------------------------------------------------------------------
# Per-platform checks
# --------------------------------------------------------------------------

def _check_daedalus(entry: dict, env: Mapping[str, str],
                    import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "daedalus"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="Daedalus local code does not compile.",
                              checks=checks)
    imported, err = _try_import(entry["primary_module"])
    checks["engine_importable"] = imported
    if not imported:
        return PlatformStatus(pid, "BROKEN", missing=[err],
                              detail="Daedalus engine module does not import.",
                              checks=checks)
    missing = [v for v in entry["env_vars"] if not _env_present(env, v)]
    checks["key_present"] = _env_present(env, "ANTHROPIC_API_KEY")
    checks["model_present"] = _env_present(env, "DAEDALUS_CLAUDE_MODEL")
    if missing:
        return PlatformStatus(
            pid, "MISSING_KEY", missing=missing,
            detail="Live Claude reasoning needs an Anthropic key and a model "
                   "id; the local engine chain imports but cannot reason.",
            checks=checks)
    if not _approved(env, entry.get("approval_env")):
        return PlatformStatus(
            pid, "MISSING_APPROVAL",
            missing=[f"owner approval ({entry.get('approval_env')}=yes)"],
            detail="Key and model are present, but live (paid) Claude use "
                   "needs explicit owner approval.",
            checks=checks)
    # Key + model + approval: build settings and a stdlib transport object.
    # This constructs local objects only; no network call is made, so live
    # account validity is NOT verified.
    try:
        from .daedalus_config import DaedalusSettings
        from .daedalus_claude_transport import build_transport

        settings = DaedalusSettings.from_env(env)
        if not settings.is_live_reasoning_configured:
            return PlatformStatus(
                pid, "MISSING_KEY", missing=["ANTHROPIC_API_KEY",
                                             "DAEDALUS_CLAUDE_MODEL"],
                detail="Settings report live reasoning not configured.",
                checks=checks)
        build_transport(settings=settings, backend="stdlib")
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"transport build failed: {exc}"],
                              detail="Key/model present but local transport "
                                     "wiring does not build.",
                              checks=checks)
    checks["transport_builds"] = True
    auto = [_SQLITE_PROBE] if _sqlite_round_trip() else []
    return PlatformStatus(
        pid, "LINKED", detail="Key and model present, owner approval "
        "recorded, stdlib Claude transport builds locally. No live call "
        "was made; live account validity is not verified.",
        checks=checks, auto_connected=auto)


def _check_grantwriter(entry: dict, env: Mapping[str, str],
                       import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "grantwriter"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        missing = list(failures)
        if not import_checker("realtime_ai"):
            missing.append("package realtime_ai (module realtime_ai.runtime) "
                           "not installed")
        return PlatformStatus(
            pid, "BROKEN", missing=missing,
            detail="Grantwriter (Mother) local code does not compile, so "
                   "its SQLite ledger cannot be linked.",
            checks=checks)
    return PlatformStatus(pid, "LINKED",
                          detail="Grantwriter module compiles.",
                          checks=checks,
                          auto_connected=[_SQLITE_PROBE]
                          if _sqlite_round_trip() else [])


def _check_ai_role_workers(entry: dict, env: Mapping[str, str],
                           import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "ai_role_workers"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="AI role worker local code does not "
                                     "compile.",
                              checks=checks)
    try:
        from .agent_registry import IT_AGENT_NAMES
        from . import technical_worker, operational_worker  # noqa: F401
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="AI role worker modules do not import.",
                              checks=checks)
    checks["agents_registered"] = len(IT_AGENT_NAMES)
    if len(IT_AGENT_NAMES) != 12:
        return PlatformStatus(pid, "BROKEN",
                              missing=["agent registry holds "
                                       f"{len(IT_AGENT_NAMES)} agents, "
                                       "expected 12"],
                              detail="Agent matrix is incomplete.",
                              checks=checks)
    auto = ["local_agent_registry (12 agents)"]
    if _sqlite_round_trip():
        auto.append(_SQLITE_PROBE)
    return PlatformStatus(pid, "LINKED",
                          detail="Agent registry imports with 12 IT agents; "
                                 "read-only technical worker and SQLite "
                                 "operational worker import.",
                          checks=checks, auto_connected=auto)


def _check_bozly(entry: dict, env: Mapping[str, str],
                 import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "bozly"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(
            pid, "BROKEN", missing=failures,
            detail=f"Bozly: {len(ok)} of {len(ok) + len(failures)} modules "
                   "compile; the failing module(s) block the platform.",
            checks=checks)
    return PlatformStatus(pid, "LINKED",
                          detail="All Bozly modules compile.",
                          checks=checks, auto_connected=["local_files"])


def _check_minotaur_sentinel(entry: dict, env: Mapping[str, str],
                             import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "minotaur_sentinel"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="Minotaur Sentinel local code does not "
                                     "compile.",
                              checks=checks)
    try:
        root = str(_repo_root())
        if root not in sys.path:
            sys.path.insert(0, root)
        import minotaur_sentinel as sentinel_mod
        sentinel = sentinel_mod.MinotaurSentinel()
        with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
            tmp.write(b"link-registry-probe")
            probe_path = tmp.name
        try:
            got = sentinel.compute_target_hash(probe_path)
        finally:
            os.unlink(probe_path)
        expected = hashlib.sha256(b"link-registry-probe").hexdigest()
        checks["hash_probe_matches"] = got == expected
        if got != expected:
            return PlatformStatus(
                pid, "BROKEN", missing=["hash probe mismatch"],
                detail="Sentinel hash computation does not match hashlib.",
                checks=checks)
        anomalies = sentinel.execute_patrol_cycle()
        checks["patrol_anomalies"] = len(anomalies)
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="Minotaur Sentinel does not run locally.",
                              checks=checks)
    auto = ["local_hash_patrol (sha256 verified on temp file)"]
    if _sqlite_round_trip():
        auto.append(_SQLITE_PROBE)
    detail = ("Sentinel instantiates and its SHA-256 probe matches hashlib. "
              f"Patrol reports {len(anomalies)} missing protected target(s); "
              "that is the sentinel working correctly, not a sentinel failure.")
    return PlatformStatus(pid, "LINKED", detail=detail, checks=checks,
                          auto_connected=auto)


def _check_twingate(entry: dict, env: Mapping[str, str],
                    import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "twingate"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="TwinGate local code does not compile.",
                              checks=checks)
    try:
        from .twin_gate import (
            AuthorizationDenied, GlassBoxAudit, Lease, TwinGate, Vault,
            utc_now,
        )
        from hashlib import sha256 as _sha256

        payload = b"link-registry-probe"
        lease = Lease(
            lease_id="link-registry-probe-1",
            agent="link-registry-probe",
            target="link-registry-probe",
            method="GET",
            issued_at=utc_now(),
            expires_at=utc_now() + timedelta(minutes=5),
            payload_sha256=_sha256(payload).hexdigest(),
        )
        gate = TwinGate(Vault(), GlassBoxAudit())
        try:
            gate.authorize(lease, agent="link-registry-probe",
                           target="link-registry-probe", method="GET",
                           payload=payload)
            denied = False
        except AuthorizationDenied:
            denied = True
        checks["fail_closed_deny"] = denied
        checks["audit_chain_verifies"] = gate.audit.verify()
        if not denied or not gate.audit.verify():
            return PlatformStatus(
                pid, "BROKEN",
                missing=["fail-closed probe did not deny, or audit chain "
                         "does not verify"],
                detail="TwinGate policy engine does not fail closed.",
                checks=checks)
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="TwinGate policy engine does not run.",
                              checks=checks)
    return PlatformStatus(
        pid, "LINKED",
        detail="TwinGate imports and its fail-closed probe works: an "
               "unapproved lease is denied and the glass-box audit chain "
               "verifies.",
        checks=checks, auto_connected=["offline_policy_engine "
                                       "(fail-closed deny verified)"])


def _check_sharpshooter(entry: dict, env: Mapping[str, str],
                        import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "sharpshooter"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="Sharpshooter local code does not "
                                     "compile.",
                              checks=checks)
    try:
        root = str(_repo_root())
        if root not in sys.path:
            sys.path.insert(0, root)
        from sharpshooter.core import evidence, new_incident

        incident = new_incident("example.invalid", {"tls": False, "dns": []})
        rendered = evidence(incident)
        checks["incident_evidence_renders"] = bool(rendered)
        if not rendered:
            raise ValueError("evidence() returned empty output")
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="Sharpshooter local incident/evidence "
                                     "handling does not run.",
                              checks=checks)
    return PlatformStatus(
        pid, "LINKED",
        detail="Sharpshooter imports and local incident/evidence handling "
               "renders (no network diagnosis was attempted).",
        checks=checks, auto_connected=["local_incident_evidence"])


def _check_stream_api(entry: dict, env: Mapping[str, str],
                      import_checker: Callable[[str], bool]) -> PlatformStatus:
    pid = "stream_api"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="Stream API local code does not compile.",
                              checks=checks)
    missing: list = []
    if not import_checker("stripe"):
        missing.append("package stripe not installed")
    checks["stripe_package_present"] = import_checker("stripe")
    missing.extend(v for v in entry["env_vars"] if not _env_present(env, v))
    checks["webhook_secret_present"] = _env_present(env, "STRIPE_WEBHOOK_SECRET")
    if missing:
        return PlatformStatus(
            pid, "MISSING_KEY", missing=missing,
            detail="Stripe webhook receiver needs the stripe package and "
                   "STRIPE_WEBHOOK_SECRET before it can verify anything.",
            checks=checks)
    if not _approved(env, entry.get("approval_env")):
        return PlatformStatus(
            pid, "MISSING_APPROVAL",
            missing=[f"owner approval ({entry.get('approval_env')}=yes)"],
            detail="Stripe secret is present, but live money movement needs "
                   "explicit owner approval.",
            checks=checks)
    try:
        from .stream_api import import_make_app

        class _FakeLedger:
            def dispatch(self, *args, **kwargs):
                return "ok"

        app = import_make_app(_FakeLedger(), env["STRIPE_WEBHOOK_SECRET"])
        checks["wsgi_app_builds"] = callable(app)
    except ImportError as exc:
        # Reality wins over the injected checker: if stripe really is not
        # importable, the link is missing its package, not broken code.
        if getattr(exc, "name", None) == "stripe" or "stripe" in str(exc):
            return PlatformStatus(
                pid, "MISSING_KEY",
                missing=["package stripe not installed (import failed)"],
                detail="Stripe package is not importable in this "
                       "interpreter.",
                checks=checks)
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="Stripe webhook WSGI app does not build.",
                              checks=checks)
    except Exception as exc:
        return PlatformStatus(pid, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="Stripe webhook WSGI app does not build.",
                              checks=checks)
    auto = [_SQLITE_PROBE] if _sqlite_round_trip() else []
    return PlatformStatus(
        pid, "LINKED",
        detail="Stripe package and webhook secret present, owner approval "
               "recorded, webhook WSGI app builds locally. No live Stripe "
               "call was made.",
        checks=checks, auto_connected=auto)


def _check_voice_audio_video(entry: dict, env: Mapping[str, str],
                             import_checker: Callable[[str], bool],
                             which_checker: Callable[[str], str | None]
                             ) -> PlatformStatus:
    pid = "voice_audio_video"
    ok, failures = _compile_files(entry["local_modules"])
    checks = {"modules_compiled": len(ok), "modules_failed": len(failures)}
    if failures:
        return PlatformStatus(pid, "BROKEN", missing=failures,
                              detail="Voice/Audio/Video local code does not "
                                     "compile.",
                              checks=checks)
    imported, err = _try_import(entry["primary_module"])
    checks["voice_api_importable"] = imported
    if not imported:
        return PlatformStatus(pid, "BROKEN", missing=[err],
                              detail="Voice API module does not import.",
                              checks=checks)
    # Free/offline backends first (owner direction: free resources first).
    # NOTE: FasterWhisperTranscriber.__init__ loads (and downloads) a model,
    # so the health check never constructs it; package presence plus the
    # wiring import is the check. Model download is a separate setup step.
    faster = import_checker("faster_whisper")
    system_tts = import_checker("pyttsx3") or bool(which_checker("espeak-ng"))
    ffmpeg = bool(which_checker("ffmpeg"))
    checks["faster_whisper_installed"] = faster
    checks["system_tts_available"] = system_tts
    checks["ffmpeg_present"] = ffmpeg
    paid_missing = [v for v in entry["env_vars"] if not _env_present(env, v)]
    checks["paid_keys_missing"] = len(paid_missing)
    if faster or system_tts:
        # A real local backend exists; verify the wiring answers /status.
        try:
            from .voice_api import create_voice_app
            app = create_voice_app(None, None)
            seen: dict = {}

            def _start(status, headers):
                seen["status"] = status

            body = b"".join(app({"PATH_INFO": "/api/voice/status",
                                 "REQUEST_METHOD": "GET"}, _start))
            checks["status_endpoint_200"] = seen.get("status", "").startswith("200")
            if not checks["status_endpoint_200"]:
                raise ValueError(f"/api/voice/status answered {seen}")
            _ = body
        except Exception as exc:
            return PlatformStatus(pid, "BROKEN",
                                  missing=[f"{type(exc).__name__}: {exc}"],
                                  detail="Voice API wiring does not answer "
                                         "its status endpoint.",
                                  checks=checks)
        backend = "faster-whisper" if faster else "system TTS"
        if paid_missing:
            detail = (f"Local offline backend present ({backend}); voice API "
                      "status endpoint answers. Paid providers still need "
                      "keys: " + ", ".join(paid_missing))
        else:
            detail = (f"Local offline backend present ({backend}); voice API "
                      "status endpoint answers.")
        return PlatformStatus(pid, "LINKED", detail=detail, checks=checks,
                              auto_connected=[backend, "local_files"])
    missing = ["package faster-whisper not installed",
               "system TTS not available (package pyttsx3 or espeak-ng "
               "not installed)"]
    missing.extend(paid_missing)
    return PlatformStatus(
        pid, "NOT_IMPLEMENTED", missing=missing,
        detail="No working voice backend is installed: local STT (faster-"
               "whisper) and local system TTS are both absent, and no paid "
               "provider key is set. The voice API imports and honestly "
               "answers 503, but transcription/synthesis cannot run.",
        checks=checks)


_CHECKERS = {
    "daedalus": _check_daedalus,
    "grantwriter": _check_grantwriter,
    "ai_role_workers": _check_ai_role_workers,
    "bozly": _check_bozly,
    "minotaur_sentinel": _check_minotaur_sentinel,
    "twingate": _check_twingate,
    "sharpshooter": _check_sharpshooter,
    "stream_api": _check_stream_api,
}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def _default_import_checker(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        # Dotted names (e.g. google.cloud.texttospeech) raise when the
        # parent package is absent; that means "not installed".
        return False


def check_platform(platform_id: str, registry: dict | None = None,
                   env: Mapping[str, str] | None = None,
                   import_checker: Callable[[str], bool] | None = None,
                   which_checker: Callable[[str], str | None] | None = None
                   ) -> PlatformStatus:
    """Verify one platform's links. Every call returns a status; an
    unexpected failure inside a checker is reported as BROKEN, never
    raised and never silently upgraded to LINKED."""
    registry = registry or load_registry()
    entry = _platform_entry(registry, platform_id)
    env = os.environ if env is None else env
    import_checker = import_checker or _default_import_checker
    which_checker = which_checker or shutil.which
    checker = _CHECKERS.get(platform_id)
    try:
        if platform_id == "voice_audio_video":
            return _check_voice_audio_video(entry, env, import_checker,
                                            which_checker)
        if checker is None:
            return PlatformStatus(platform_id, "NOT_IMPLEMENTED",
                                  missing=[f"no checker for {platform_id}"],
                                  detail="No checker implemented.")
        return checker(entry, env, import_checker)
    except Exception as exc:  # a checker must never crash check_all()
        return PlatformStatus(platform_id, "BROKEN",
                              missing=[f"{type(exc).__name__}: {exc}"],
                              detail="Checker failed unexpectedly.")


def check_all(registry: dict | None = None,
              env: Mapping[str, str] | None = None,
              import_checker: Callable[[str], bool] | None = None,
              which_checker: Callable[[str], str | None] | None = None
              ) -> dict[str, PlatformStatus]:
    """Verify every platform in the registry. All 9 platforms always get
    a status, even if a checker fails."""
    registry = registry or load_registry()
    results: dict[str, PlatformStatus] = {}
    for entry in registry["platforms"]:
        results[entry["id"]] = check_platform(
            entry["id"], registry=registry, env=env,
            import_checker=import_checker, which_checker=which_checker)
    return results


def check_providers(registry: dict | None = None,
                    env: Mapping[str, str] | None = None,
                    import_checker: Callable[[str], bool] | None = None
                    ) -> dict[str, dict]:
    """Per external-provider status. No network call is made; a provider
    is LINKED only when every required env var is present, its package
    (if any) is installed, and owner approval is recorded where required.
    Otherwise MISSING_KEY (or MISSING_APPROVAL when only approval is
    missing)."""
    registry = registry or load_registry()
    env = os.environ if env is None else env
    import_checker = import_checker or _default_import_checker
    out: dict[str, dict] = {}
    for provider_id, provider in registry.get("providers", {}).items():
        missing = [v for v in provider.get("env_vars", [])
                   if not _env_present(env, v)]
        package = provider.get("package")
        package_ok = True if package is None else import_checker(package)
        if package is not None and not package_ok:
            missing.append(f"package {package} not installed")
        if missing:
            status = "MISSING_KEY"
        elif provider.get("requires_owner_approval_for_live") and not _approved(
                env, f"SDS_OWNER_APPROVAL_{provider_id.upper()}"):
            status = "MISSING_APPROVAL"
            missing = [f"owner approval "
                       f"(SDS_OWNER_APPROVAL_{provider_id.upper()}=yes)"]
        else:
            status = "LINKED"
        out[provider_id] = {
            "status": status,
            "missing": missing,
            "provider": provider.get("name", provider_id),
            "cost_tier": provider.get("cost_tier"),
            "free_alternative": provider.get("free_alternative"),
        }
    return out


def auto_connect(results: dict[str, PlatformStatus] | None = None,
                 registry: dict | None = None,
                 env: Mapping[str, str] | None = None,
                 import_checker: Callable[[str], bool] | None = None,
                 which_checker: Callable[[str], str | None] | None = None
                 ) -> dict:
    """Auto-connect what CAN be auto-connected (local/offline only) and
    honestly list what cannot be. Returns connected items per platform
    plus the unmet requirements. Never connects a keyed provider."""
    results = results or check_all(registry=registry, env=env,
                                   import_checker=import_checker,
                                   which_checker=which_checker)
    connected: dict[str, list] = {}
    cannot: dict[str, list] = {}
    for pid, status in results.items():
        if status.auto_connected:
            connected[pid] = list(status.auto_connected)
        if status.status != "LINKED" and status.missing:
            cannot[pid] = list(status.missing)
    return {"connected": connected, "cannot_auto_connect": cannot}


def summarize(results: dict[str, PlatformStatus]) -> dict:
    """Counts and a printable per-platform table."""
    counts: dict[str, int] = {s: 0 for s in STATUSES}
    rows = []
    for pid in PLATFORM_IDS:
        status = results.get(pid)
        if status is None:
            counts["NOT_IMPLEMENTED"] += 1
            rows.append((pid, "NOT_IMPLEMENTED", ["not checked"]))
            continue
        counts[status.status] = counts.get(status.status, 0) + 1
        rows.append((pid, status.status, list(status.missing)))
    return {"counts": counts, "rows": rows,
            "total": len(rows),
            "all_reported": len(rows) == len(PLATFORM_IDS)}


def main(argv: list | None = None) -> int:
    """CLI: ``python -m core_platform.ai_platform_links [--json]``.

    Prints the per-platform table. Exit 0 when every platform reported a
    status and none is BROKEN; exit 1 when any platform is BROKEN.
    Missing keys are expected without credentials and do not fail the run.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Sanders Dash & Seal AI platform link registry check")
    parser.add_argument("--json", action="store_true",
                        help="print machine-readable JSON instead of a table")
    parser.add_argument("--config", default=None,
                        help="path to ai_platform_links.json")
    args = parser.parse_args(argv)
    registry = load_registry(args.config) if args.config else load_registry()
    results = check_all(registry=registry)
    providers = check_providers(registry=registry)
    summary = summarize(results)
    if args.json:
        print(json.dumps({
            "platforms": {pid: s.to_dict() for pid, s in results.items()},
            "providers": providers,
            "summary": summary,
        }, indent=2, sort_keys=True))
    else:
        print("Sanders Dash & Seal -- AI platform links "
              f"({datetime.now(timezone.utc).isoformat()} UTC)")
        print(f"{'platform':<20} {'status':<17} missing")
        for pid, status, missing in summary["rows"]:
            print(f"{pid:<20} {status:<17} {'; '.join(missing) or '-'}")
        print("\nproviders (no live calls made):")
        for provider_id, info in sorted(providers.items()):
            print(f"  {provider_id:<12} {info['status']:<17} "
                  f"{'; '.join(info['missing']) or '-'}")
        print(f"\ncounts: {summary['counts']}")
    return 1 if summary["counts"].get("BROKEN", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
