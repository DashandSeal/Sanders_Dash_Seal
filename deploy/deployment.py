"""
WSGI deployment boundary for the existing Sanders Dash & Seal application.

Default startup serves existing assets and diagnostics only. Trusted production
adapters are supplied by the administrator, behind an external verified bootstrap.
Neither environment configuration nor an HTTP request grants production authority.
"""

from dataclasses import dataclass, replace
import importlib
import json
import os
import re
from pathlib import Path

from app.customer_app import create_customer_app
from core_platform.free_resources import catalog as free_resource_catalog
from core_platform.pipeline_api import create_pipeline_app, TransactionStore
from core_platform.stream_api import create_stream_app

CANONICAL_HOST = 'sandersdashandseal.com'
ALIAS_HOSTS = {'www.sandersdashandseal.com', 'sanderslegalhelpersllc.com', 'www.sanderslegalhelpersllc.com'}
ORIGIN = 'https://' + CANONICAL_HOST
FACTORY = re.compile(r'([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))*(?::([A-Za-z_]\w*))?', re.ASCII)
WEB_ROOT = Path(__file__).resolve().parent.parent / 'web'

class DeploymentConfigurationError(ValueError):
    pass

@dataclass(frozen=True)
class RuntimeBindings:
    appointments: object = None
    payments: object = None
    authenticate: object = None
    auth_app: object = None
    release_verifier: object = None
    webhook_app: object = None
    transaction_processor: object = None
    transaction_store: object = None
    stream_verifier: object = None

def _response(start, status, payload, extra=None):
    body = json.dumps(payload, separators=(',', ':')).encode()
    start(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-store'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Referrer-Policy', 'no-referrer'),
        *(extra or ())
    ])
    return [body]

def _unavailable(env, start):
    return _response(start, '503 Service Unavailable', {'error': 'service_unavailable'})

def _denied():
    return False

# ---------------------------------------------------------------------------
# P2 (2026-11-13): AI-platform / voice / realtime / global wiring.
# Every optional module is imported lazily inside a helper and guarded:
# a missing or broken optional module degrades its own routes to an
# honest 503 and can never break the core app (/, /healthz, webhook).
# No live provider call is made by any route below without (a) the
# provider key present in the environment and (b) the matching owner
# approval gate APPROVED (all 9 gates are UNAPPROVED until the owner
# approves a specific gate by name).
# ---------------------------------------------------------------------------

_VOICE_APPS = {}  # process-local cache: {"voice": app, "daedalus": app}
_REALTIME_APP = {}  # process-local cache: {"app": app}


def _utcnow_iso():
    """UTC timestamp for responses (global_time; stdlib fallback)."""
    try:
        from core_platform.global_time import now_utc, serialize_utc
        return serialize_utc(now_utc())
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _negotiated_locale(env):
    """Best locale from Accept-Language (i18n; 'en' fallback)."""
    try:
        from core_platform.i18n import negotiate_locale
        return negotiate_locale(env.get("HTTP_ACCEPT_LANGUAGE"))
    except Exception:
        return "en"


def _is_approved(gate_id):
    """True only when the gate is APPROVED; any failure fails closed."""
    try:
        from core_platform.ai_platform_approval import is_approved
        return bool(is_approved(gate_id))
    except Exception:
        return False


def _approval_503(start, gate_id):
    try:
        from core_platform.ai_platform_approval import http_failure
        payload = http_failure(gate_id)
    except Exception:
        payload = {"status": 503, "error": "approval_required", "gate": gate_id}
    payload = {k: v for k, v in payload.items() if k != "status"}
    return _response(start, "503 Service Unavailable", payload)


class _OpenAIRealtimeTTSSynthesizer:
    """Minimal adapter for OpenAI Realtime TTS (mirrors the private
    adapter in core_platform.voice_api; that module remains the
    canonical provider-wiring module)."""

    name = "openai-realtime-tts"
    audio_format = "pcm"
    media_type = "audio/pcm"

    def __init__(self):
        from core_platform.openai_link import OpenAIRealtimeTTSSpeaker
        self._speaker = OpenAIRealtimeTTSSpeaker()

    def synthesize(self, text):
        return self._speaker.speak(text).audio


def _voice_backends():
    """Free-first voice backends (transcriber faster-whisper -> Deepgram
    -> OpenAI gpt-transcribe; synthesizer system TTS -> Google ->
    ElevenLabs -> OpenAI Realtime). Provider adapters are constructed
    ONLY when the voice_video_provider approval gate is APPROVED;
    otherwise only local/offline backends are attempted. A backend
    whose key or package is missing is skipped; nothing here makes a
    live call. FasterWhisperTranscriber constructs its model eagerly
    (one ~75 MB download on first use when faster-whisper is installed
    but the model is not cached), so backends are built lazily on the
    first /api/voice request, never at startup."""
    from core_platform.daedalus_voice import (
        DeepgramTranscriber,
        ElevenLabsSynthesizer,
        FasterWhisperTranscriber,
        GoogleTTSSynthesizer,
        OpenAITranscriber,
        SystemTTSSynthesizer,
    )
    approved = _is_approved("voice_video_provider")
    transcriber = None
    builds = [lambda: FasterWhisperTranscriber("tiny")]
    if approved:
        builds += [DeepgramTranscriber, OpenAITranscriber]
    for build in builds:
        try:
            transcriber = build()
            break
        except Exception:
            continue
    synthesizer = None
    builds = [SystemTTSSynthesizer]
    if approved:
        builds += [GoogleTTSSynthesizer, ElevenLabsSynthesizer,
                   _OpenAIRealtimeTTSSynthesizer]
    for build in builds:
        try:
            synthesizer = build()
            break
        except Exception:
            continue
    return transcriber, synthesizer


def _voice_apps():
    """(plain voice app, Daedalus voice-turn app), built once per process.
    The turn app has runtime=None: no Daedalus signing key, durable
    evidence store, or daedalus_live approval is wired in this pass, so
    POST /api/voice/turn honestly answers 503
    daedalus_runtime_not_configured."""
    if "voice" not in _VOICE_APPS:
        from core_platform.voice_api import (
            create_daedalus_voice_app,
            create_voice_app,
        )
        transcriber, synthesizer = _voice_backends()
        _VOICE_APPS["voice"] = create_voice_app(transcriber, synthesizer)
        _VOICE_APPS["daedalus"] = create_daedalus_voice_app(
            runtime=None, transcriber=transcriber, synthesizer=synthesizer)
    return _VOICE_APPS["voice"], _VOICE_APPS["daedalus"]


def _realtime_app():
    """Realtime/video app (env-wired LiveKit/Daily clients, no transport:
    room/token answer honest 503s until a provider is configured)."""
    if "app" not in _REALTIME_APP:
        from core_platform.realtime_api import create_realtime_app
        _REALTIME_APP["app"] = create_realtime_app()
    return _REALTIME_APP["app"]


def _serve_web_file(start, filename, media_type):
    """Serve one file from web/; returns None when it does not exist."""
    try:
        body = (WEB_ROOT / filename).read_bytes()
    except OSError:
        return None
    start("200 OK", [
        ("Content-Type", media_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    ])
    return [body]


def _combined_platform_status(env):
    """Combined per-platform status: link registry + approval gates +
    service links + platform services + global (region/locale/currency)
    + voice backends + free-first ordering. Read-only; no live call,
    no secret value is ever returned. Each section is guarded so one
    broken module degrades its own section instead of the endpoint."""
    locale = _negotiated_locale(env)
    payload = {
        "platform": "Sanders Dash & Seal",
        "generated_at_utc": _utcnow_iso(),
        "locale": locale,
    }
    try:
        from core_platform.i18n import text_direction, translate
        payload["text_direction"] = text_direction(locale)
        payload["title"] = translate("app.title", locale)
    except Exception as exc:
        payload["title_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.ai_platform_links import (
            check_all,
            check_providers,
            summarize,
        )
        results = check_all()
        payload["platform_links"] = {
            pid: status.to_dict() for pid, status in results.items()}
        payload["platform_link_summary"] = summarize(results)
        payload["providers"] = check_providers()
    except Exception as exc:
        payload["platform_links_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.ai_platform_approval import approval_checklist
        payload["approvals"] = approval_checklist()
    except Exception as exc:
        payload["approvals_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.service_linking import linking_table
        rows = linking_table()
        payload["service_links"] = {
            "rows": len(rows),
            "by_live_status": {
                s: sum(1 for r in rows if r.get("live_status") == s)
                for s in sorted({r.get("live_status") for r in rows})},
        }
    except Exception as exc:
        payload["service_links_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.platform_services import platform_status
        payload["services"] = platform_status()
    except Exception as exc:
        payload["services_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.global_regions import GlobalRegionsConfig
        payload["regions"] = GlobalRegionsConfig.from_env().summary()
    except Exception as exc:
        payload["regions_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # P3 (2026-11-13): global_connectivity now has a real caller.
        # Policy table only (no live calls, no network): per-platform
        # timeout/retry/offline-fallback for the primary region ("us",
        # us-phoenix-1). eu/apac policies are declared only -- no
        # deployment exists there.
        from core_platform.global_connectivity import all_policies
        payload["connectivity"] = {
            "region": "us",
            "policies": {
                p.platform: {
                    "timeout_seconds": p.timeout_seconds,
                    "max_retries": p.max_retries,
                    "offline_fallback": p.offline_fallback,
                }
                for p in all_policies()
                if p.region == "us"
            },
            "note": ("Policy table only, not measured latency. "
                     "eu/apac policies are declared only; no deployment there."),
        }
    except Exception as exc:
        payload["connectivity_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # P3 (2026-11-13): global_compliance now has a real caller.
        # RON gate state, read-only: the owner-approved set is EMPTY by
        # default and gating is fail-closed, so no jurisdiction is
        # approved until the owner approves one by name.
        from core_platform.global_compliance import APPROVED_RON_JURISDICTIONS
        payload["ron"] = {
            "gate": "fail_closed",
            "approved_jurisdictions": sorted(APPROVED_RON_JURISDICTIONS),
            "check": "GET /api/compliance/ron?jurisdiction=XX",
        }
    except Exception as exc:
        payload["ron_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.global_payments import live_gate, resolve_currency
        livemode = (os.environ.get("STRIPE_LIVEMODE") or "").strip().lower() in (
            "1", "true", "yes")
        live_verified = (os.environ.get("STRIPE_LIVE_VERIFIED") or "").strip().lower() in (
            "1", "true", "yes")
        payments = {"live_gate": live_gate(
            livemode=livemode, live_verified=live_verified)}
        try:
            currency, source = resolve_currency(
                accept_language=env.get("HTTP_ACCEPT_LANGUAGE"))
            payments["currency"] = currency
            payments["currency_source"] = source
        except Exception as exc:
            payments["currency"] = None
            payments["currency_source"] = None
            payments["currency_note"] = (
                f"unresolvable from request: {type(exc).__name__}; "
                "pass an explicit currency")
        payload["payments"] = payments
    except Exception as exc:
        payload["payments_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.voice_api import describe_voice_backends
        payload["voice_backends"] = describe_voice_backends()
    except Exception as exc:
        payload["voice_backends_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.free_first import free_first_status
        payload["free_first"] = free_first_status()
    except Exception as exc:
        payload["free_first_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # PQC (2026-11-13): post-quantum cryptography status, read-only.
        # Reports honestly whether this runtime can perform ML-KEM-768 /
        # ML-DSA-65. No keys are ever returned. If the runtime cannot do
        # PQC, "available" is False and nothing claims otherwise.
        from core_platform.pqc import status as pqc_status
        payload["pqc"] = pqc_status()
    except Exception as exc:
        payload["pqc_error"] = f"{type(exc).__name__}: {exc}"
    return payload

def create_application(bindings=None):
    """Expose existing components; no bindings means diagnostic-only startup."""
    if bindings is not None:
        if not isinstance(bindings, RuntimeBindings) or bindings.appointments is None or bindings.payments is None or getattr(bindings.payments, 'origin', None) is not ORIGIN or not all(callable(v) for v in (bindings.authenticate, bindings.auth_app, bindings.release_verifier)) or (bindings.webhook_app is not None and not callable(bindings.webhook_app)):
            raise DeploymentConfigurationError('Independent runtime bindings required')
        verifier = bindings.release_verifier
        if bindings.transaction_processor is not None and not callable(bindings.transaction_processor):
            raise DeploymentConfigurationError('Trusted transaction processor required')
        customer = create_customer_app(
            bindings.appointments, bindings.authenticate,
            bindings.payments, bindings.auth_app, ORIGIN, release_verifier=verifier
        )
    else:
        verifier = _denied
        customer = create_customer_app(
            None, lambda env: None,
            _unavailable, _unavailable, ORIGIN, release_verifier=verifier
        )

    pipeline = create_pipeline_app(
        authenticate=bindings.authenticate if bindings else None,
        processor=bindings.transaction_processor if bindings else None,
        release_verifier=verifier,
        store=bindings.transaction_store if bindings else None)

    stream = create_stream_app(
        processor=bindings.transaction_processor if bindings else None,
        release_verifier=verifier,
        store=bindings.transaction_store if bindings else None,
        stream_verifier=bindings.stream_verifier if bindings else None)

    def ready():
        try:
            return verifier() is True
        except Exception:
            return False

    # Hosts that reach this process without going through the public proxy:
    # the legacy internal name, the compose service name the worker calls
    # (worker/src/index.js uses http://wsgi-backend:8000), and loopback,
    # which the installer health checks and the worker test fixture use.
    # These hosts may only reach diagnostics and the authenticated API
    # routes, never the customer pages; the API routes still enforce their
    # own authentication / release-verifier gates.
    INTERNAL_HOSTS = ('magi-backend:8000', 'wsgi-backend:8000')
    LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')

    def _is_internal(hostname):
        if hostname in INTERNAL_HOSTS:
            return True
        return hostname.split(':')[0] in LOOPBACK_HOSTS

    def _api_route(env, start):
        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if path == '/':
            # Portal home. Internal/loopback and canonical hosts get the
            # real web/index.html. Alias hosts fall through (return None)
            # to the customer app, which serves jade-landing.html at '/'.
            # Previously the canonical host 308-redirected '/' to itself.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            host = env.get('HTTP_HOST', '')
            if not isinstance(host, str):
                return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
            host = host.lower()
            if host.endswith(':443'):
                host = host[:-4]
            if host in ALIAS_HOSTS:
                return None
            try:
                body = (WEB_ROOT / 'index.html').read_bytes()
            except OSError:
                return _response(start, '503 Service Unavailable', {'error': 'home_unavailable'})
            start('200 OK', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(body))),
                ('Cache-Control', 'no-store'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Referrer-Policy', 'no-referrer'),
                ('Content-Language', _negotiated_locale(env)),
            ])
            return [body]
        if path in ('/voice.html', '/video.html',
                    '/daedalus_voice.js', '/video.js'):
            # Voice/video pages + their scripts, served from web/.
            # /voice.html needs camera/mic for getUserMedia; nginx only
            # relaxes Permissions-Policy for that one path (see nginx.conf).
            media_type = ('text/html; charset=utf-8' if path.endswith('.html')
                          else 'text/javascript; charset=utf-8')
            served = _serve_web_file(start, path.lstrip('/'), media_type)
            if served is not None:
                return served
            if path == '/voice.html':
                return _response(start, '503 Service Unavailable',
                                 {'error': 'voice_unavailable',
                                  'reason': 'web/voice.html is missing from this checkout'})
            return _response(start, '404 Not Found', {'error': 'not_found'})
        if path == '/api/voice' or path.startswith('/api/voice/'):
            # Real voice adapters (free-first, approval-gated for live
            # providers). No backends are configured when no key/package
            # is present, so transcribe/speak answer honest 503s; the
            # turn route answers 503 daedalus_runtime_not_configured
            # until a Daedalus runtime is wired (signing key + durable
            # evidence store + daedalus_live approval).
            try:
                voice_app, daedalus_app = _voice_apps()
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'voice_unavailable',
                                  'reason': f'voice module failed to load: {type(exc).__name__}: {exc}'})
            if path in ('/api/voice/turn', '/api/voice/daedalus/status'):
                return daedalus_app(env, start)
            return voice_app(env, start)
        if path == '/api/daedalus/describe':
            # Real Daedalus capability report (pure, no key, no live call).
            # fully_active is false until a live engine is built.
            try:
                from core_platform.daedalus_engine import describe as daedalus_describe
                payload = daedalus_describe()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'daedalus_unavailable',
                                  'reason': f'Daedalus engine failed to load: {type(exc).__name__}: {exc}'})
        if path == '/api/realtime/status' or path == '/api/video/status' or path.startswith('/api/realtime/'):
            # LiveKit/Daily realtime + video signalling (env-wired, no
            # transport). Room/token POSTs need a configured provider;
            # when one IS configured they additionally need the
            # voice_video_provider approval gate, else honest 503.
            if path in ('/api/realtime/room', '/api/realtime/token') and method == 'POST':
                try:
                    from core_platform.livekit_realtime import RealtimeConfig
                    provider = RealtimeConfig.from_env().provider()
                except Exception:
                    provider = 'none'
                if provider != 'none' and not _is_approved('voice_video_provider'):
                    return _approval_503(start, 'voice_video_provider')
            try:
                return _realtime_app()(env, start)
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'realtime_unavailable',
                                  'reason': f'realtime module failed to load: {type(exc).__name__}: {exc}'})
        if path == '/api/compliance/ron':
            # P3 (2026-11-13): RON / notarial gating on a live route.
            # Fail-closed via global_compliance.gate_ron: the approved
            # set is EMPTY by default, so every jurisdiction is denied
            # with NOT_APPROVED_IN_JURISDICTION until the owner approves
            # one by name. The request cannot supply its own approved
            # list; only an owner code change to
            # APPROVED_RON_JURISDICTIONS can approve a jurisdiction.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from urllib.parse import parse_qs
                from core_platform.global_compliance import (
                    APPROVED_RON_JURISDICTIONS,
                    NotApprovedInJurisdiction,
                    gate_ron,
                )
                query = parse_qs(env.get('QUERY_STRING') or '')
                jurisdiction = (query.get('jurisdiction') or [None])[0]
                try:
                    result = gate_ron(jurisdiction)
                except NotApprovedInJurisdiction as exc:
                    return _response(start, '403 Forbidden', {
                        'error': 'NOT_APPROVED_IN_JURISDICTION',
                        'jurisdiction': jurisdiction,
                        'approved_jurisdictions': sorted(APPROVED_RON_JURISDICTIONS),
                        'detail': str(exc)})
                return _response(start, '200 OK', {
                    'ok': True, 'jurisdiction': result['jurisdiction'],
                    'generated_at_utc': _utcnow_iso()})
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'ron_gate_unavailable',
                                  'reason': f'{type(exc).__name__}: {exc}'})
        if path == '/api/platform/status':
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            return _response(start, '200 OK', _combined_platform_status(env))
        if path == '/api/payments/currency':
            # Read-only currency resolution for payments (global_payments):
            # explicit ?currency= takes priority, then Accept-Language,
            # then nothing is silently assumed (USD is never a default).
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from urllib.parse import parse_qs
                from core_platform.global_payments import CurrencyError, resolve_currency
                query = parse_qs(env.get('QUERY_STRING') or '')
                explicit = (query.get('currency') or [None])[0]
                currency, source = resolve_currency(
                    explicit, accept_language=env.get('HTTP_ACCEPT_LANGUAGE'))
                return _response(start, '200 OK', {
                    'currency': currency, 'source': source,
                    'generated_at_utc': _utcnow_iso()})
            except Exception as exc:
                status = ('400 Bad Request' if exc.__class__.__name__ == 'CurrencyError'
                          else '503 Service Unavailable')
                error = ('currency_unresolvable' if exc.__class__.__name__ == 'CurrencyError'
                         else 'currency_service_unavailable')
                return _response(start, status, {'error': error, 'detail': str(exc)})
        if path == '/api/platform/free-resources':
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                payload = free_resource_catalog()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'resource_catalog_unavailable'})
        if path == '/api/pqc/status':
            # Post-quantum cryptography status (ML-KEM-768 / ML-DSA-65),
            # read-only and key-free. Reports honestly whether this
            # runtime can perform PQC; 200 with available:false when it
            # cannot — never a fake claim of quantum safety.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from core_platform.pqc import status as pqc_status
                payload = pqc_status()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'pqc_status_unavailable'})
        if path in ('/healthz', '/readyz'):
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            if path == '/healthz':
                return _response(start, '200 OK',
                                 {'platform': 'Sanders Dash & Seal', 'process_alive': True,
                                  'generated_at_utc': _utcnow_iso()})
            available = ready()
            return _response(start, '200 OK' if available else '503 Service Unavailable',
                             {'service_ready': available,
                              'generated_at_utc': _utcnow_iso()})
        if path == '/stripe/webhook':
            if bindings is None or bindings.webhook_app is None or not ready():
                return _unavailable(env, start)
            return bindings.webhook_app(env, start)
        if path in ('/api/auth/verify', '/api/transactions/process'):
            return pipeline(env, start)
        if path == '/api/stream/transactions':
            return stream(env, start)
        return None

    def _is_customer_api(path):
        # Paths served by app/customer_app.py (session + appointment APIs).
        # They were reachable only on alias hosts: on the canonical host
        # the 308 below swallowed them (GET /api/session 308-redirected
        # with no JSON body), so the worker's session check -- which always
        # sends Host: sandersdashandseal.com -- could never succeed, and
        # the worker python-integration test failed at WebSocket upgrade
        # with 503. Only these API paths are delegated; customer static
        # pages stay alias-only. customer() itself still enforces the
        # release verifier (503) and authentication (401).
        return (path == '/api/session'
                or path == '/api/appointments'
                or path.startswith('/api/appointments/')
                or path == '/api/operator/appointments'
                or path.startswith('/api/operator/appointments/'))

    def application(env, start):
        host = env.get('HTTP_HOST', '')
        if not isinstance(host, str):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
        host = host.lower()
        if host.endswith(':443'):
            host = host[:-4]

        # Internal / loopback hosts: diagnostics and API only. The API
        # routes were previously unreachable here (only 'magi-backend:8000'
        # was recognised, while the worker calls 'wsgi-backend:8000' and
        # the fixture calls 127.0.0.1), and the canonical redirect below
        # used to swallow /healthz and every API call on the public host.
        if _is_internal(host):
            routed = _api_route(env, start)
            if routed is not None:
                return routed
            if _is_customer_api(env.get('PATH_INFO', '')):
                return customer(env, start)
            return _response(start, '404 Not Found', {'error': 'not_found'})

        if host not in (CANONICAL_HOST, *ALIAS_HOSTS):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})

        # Public hosts: serve diagnostics and API routes before the
        # canonical-host redirect, so /healthz, /readyz and the /api/
        # routes are reachable through nginx instead of 308-redirecting
        # (and, for POSTs, 421-ing) every one of them.
        routed = _api_route(env, start)
        if routed is not None:
            return routed

        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if host == CANONICAL_HOST:
            if _is_customer_api(path):
                return customer(env, start)
            if method not in ('GET', 'HEAD'):
                return _response(start, '421 Misdirected Request',
                                 {'error': 'canonical_origin_required'})
            start('308 Permanent Redirect', [('Location', ORIGIN + '/'),
                                               ('Content-Length', '0'), ('Cache-Control', 'no-store')])
            return [b'']

        return customer(env, start)

    return application

def load_application(factory_reference=None, *, transaction_db=None):
    """Load a trusted, administrator-installed adapter factory, not HTTP input."""
    if factory_reference is None:
        return create_application()
    if not isinstance(factory_reference, str) or not FACTORY.fullmatch(factory_reference):
        raise DeploymentConfigurationError('Expected trusted module:factory')
    module, name = factory_reference.split(':')
    factory = getattr(importlib.import_module(module), name)
    if not callable(factory):
        raise DeploymentConfigurationError('Runtime factory must be callable')
    bindings = factory()
    if not isinstance(bindings, RuntimeBindings):
        raise DeploymentConfigurationError('Configured factory must return runtime bindings')
    if (transaction_db is not None and bindings.transaction_processor is not None
        and bindings.transaction_store is None):
        bindings = replace(bindings, transaction_store=TransactionStore(transaction_db))
    return create_application(bindings)