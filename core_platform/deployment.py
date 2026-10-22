"""WSGI deployment boundary for the existing Sanders Dash & Seal application.

Default startup serves existing assets and diagnostics only. Trusted production
adapters are supplied by the administrator, behind an external verified bootstrap.
Neither environment configuration nor an HTTP request grants production authority.
"""
from dataclasses import dataclass, replace
import importlib
import json
import re

from .customer_app import create_customer_app
from .free_resources import catalog as free_resource_catalog
from .pipeline_api import create_pipeline_app, TransactionStore
from .stream_api import create_stream_app


CANONICAL_HOST = 'sandersdashandseal.com'
ALIAS_HOSTS = ('www.sandersdashandseal.com', 'sanderslegalhelpersllc.com',
               'www.sanderslegalhelpersllc.com')
ORIGIN = 'https://' + CANONICAL_HOST
FACTORY = re.compile(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*', re.ASCII)


class DeploymentConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeBindings:
    appointments: object
    payments: object
    authenticate: object
    auth_app: object
    release_verifier: object
    webhook_app: object = None
    transaction_processor: object = None
    transaction_store: object = None
    stream_verifiers: object = None


def _response(start, status, payload, extra=()):
    body = json.dumps(payload, separators=(',', ':')).encode()
    start(status, [('Content-Type', 'application/json'),
                   ('Content-Length', str(len(body))),
                   ('Cache-Control', 'no-store'),
                   ('X-Content-Type-Options', 'nosniff'),
                   ('Referrer-Policy', 'no-referrer'), *extra])
    return [body]


def _unavailable(env, start):
    return _response(start, '503 Service Unavailable', {'error': 'service_unavailable'})


def _denied():
    return False


def create_application(bindings=None):
    """Compose existing components; no bindings means diagnostic-only startup."""
    if bindings is not None:
        if (not isinstance(bindings, RuntimeBindings)
                or bindings.appointments is None or bindings.payments is None
                or getattr(bindings.payments, 'appointments', None) is not bindings.appointments
                or getattr(bindings.payments, 'origin', None) != ORIGIN
                or not all(callable(x) for x in (bindings.authenticate,
                    bindings.auth_app, bindings.release_verifier))
                or (bindings.webhook_app is not None and not callable(bindings.webhook_app))):
            raise DeploymentConfigurationError('Independent runtime bindings required')
        verifier = bindings.release_verifier
        if bindings.transaction_processor is not None and not callable(bindings.transaction_processor):
            raise DeploymentConfigurationError('Trusted transaction processor required')
        customer = create_customer_app(bindings.appointments, bindings.authenticate,
            bindings.payments, bindings.auth_app, ORIGIN, release_verifier=verifier)
    else:
        verifier = _denied
        customer = create_customer_app(None, lambda env: None, None,
            _unavailable, ORIGIN, release_verifier=verifier)

    pipeline = create_pipeline_app(bindings.authenticate if bindings else None,
        bindings.transaction_processor if bindings else None, verifier,
        bindings.transaction_store if bindings else None)
    stream = create_stream_app(bindings.transaction_processor if bindings else None,
        verifier, bindings.transaction_store if bindings else None,
        bindings.stream_verifiers if bindings else None)

    def ready():
        try:
            return verifier() is True
        except Exception:
            return False

    def application(env, start):
        # HTTP_HOST is the actual virtual-host authority. Forwarded headers never
        # extend the allowlist; the TLS frontend must also enforce this boundary.
        host = env.get('HTTP_HOST', '')
        if not isinstance(host, str):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
        host = host.lower()
        path = env.get('PATH_INFO', '')
        if host == 'wsgi-backend:8000' and path == '/api/stream/transactions':
            return stream(env, start)
        if host == 'wsgi-backend:8000' and path in ('/api/auth/verify', '/api/transactions/process'):
            return pipeline(env, start)
        if host.endswith(':443'):
            host = host[:-4]
        if host not in (CANONICAL_HOST, *ALIAS_HOSTS):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if host != CANONICAL_HOST:
            if method not in ('GET', 'HEAD'):
                return _response(start, '421 Misdirected Request',
                    {'error': 'canonical_origin_required'})
            # Preserve no untrusted request target in a Location header. Users
            # arrive at the canonical platform home and authenticate there.
            start('308 Permanent Redirect', [('Location', ORIGIN + '/'),
                ('Content-Length', '0'), ('Cache-Control', 'no-store')])
            return [b'']
        if path == '/api/platform/free-resources':
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            return _response(start, '200 OK', free_resource_catalog())
        if path in ('/healthz', '/readyz'):
            if method != 'GET':
                return _response(start, '405 Method Not Allowed',
                    {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            if path == '/healthz':
                return _response(start, '200 OK',
                    {'platform': 'Sanders Dash & Seal', 'process_alive': True})
            available = ready()
            return _response(start, '200 OK' if available else '503 Service Unavailable',
                {'service_ready': available})
        if path == '/stripe/webhook':
            if bindings is None or bindings.webhook_app is None or not ready():
                return _unavailable(env, start)
            return bindings.webhook_app(env, start)
        if path in ('/api/auth/verify', '/api/transactions/process'):
            return pipeline(env, start)
        if path == '/api/stream/transactions':
            return stream(env, start)
        return customer(env, start)
    return application


def load_application(factory_reference=None, *, transaction_db=None):
    """Load a trusted, administrator-installed adapter factory, not HTTP input.

    Do not set this value from a request or an untrusted configuration file.
    Source/dependency authorization remains the external bootstrap's obligation.
    Invalid explicit configuration fails startup instead of silently downgrading.
    """
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
