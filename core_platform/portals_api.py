"""Portals API — the HTTP surface of the Sanders Companies' portals.

Mounted by the deployment router at ``/api/portals/`` (the
``/api/voice/`` pattern): a self-contained WSGI app over
``PortalsService``, wired with the application's own session
verifier. Enforcement lives here and in the service, so no router
path can bypass it:

- **Public submissions** (Wall of Valor, support, complaints,
  how-we're-doing, contractor interest, spotlight nomination) are
  accepted from the public — a person must be able to honor a
  veteran or file a complaint without an account — and land as
  cases AWAITING_HUMAN_REVIEW. A submission publishes nothing, ever.
- **Public reads** expose only what an operator's recorded decision
  made public: PUBLISHED tributes (and the photographs they carry),
  recorded spotlight selections, and figures sourced from the
  platform's own records.
- **Contractor surfaces** require the platform session (the same
  ``authenticate`` the customer app uses); a contractor sees only
  their own record.
- **Operator surfaces** require the session identity the house's
  operator verifier recognizes; the service re-checks authority on
  every action (fail-closed).
- POSTs are origin-checked against the site's own origins and
  JSON-only, in the customer app's discipline; bodies are capped —
  generously only where a tribute photograph rides along.

With no service wired (diagnostic startup) every route answers an
honest 503 ``portals_unavailable``.
"""

from __future__ import annotations

import json
import re

from .portals_service import (
    CONSENT_VERSION,
    PortalsDenied,
    PortalsForbidden,
    PortalsService,
)

SUBMIT_ROUTE = re.compile(r'^/api/portals/submissions/([a-z-]+)$')
CASE_ROUTE = re.compile(r'^/api/portals/cases/([A-Z]{3}-[0-9]{8}-[A-Z0-9]{10})$')
MEDIA_ROUTE = re.compile(r'^/api/portals/media/([a-f0-9]{64}\.(?:jpg|png|webp))$')
REVIEW_ROUTE = re.compile(
    r'^/api/portals/operator/cases/([A-Z]{3}-[0-9]{8}-[A-Z0-9]{10})/(review|resolve)$')

KIND_BY_SLUG = {
    'wall-of-valor': 'WALL_OF_VALOR',
    'support': 'SUPPORT',
    'complaints': 'COMPLAINT',
    'feedback': 'FEEDBACK',
    'contractor-interest': 'CONTRACTOR_INTEREST',
    'spotlight-nomination': 'SPOTLIGHT_NOMINATION',
}

MAX_BODY = 16 * 1024 * 1024
MAX_JSON_BODY = 64 * 1024

_MEDIA_TYPES = {'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}


def create_portals_app(service, authenticate=None,
                       allowed_origins=frozenset()):
    """Build the portals WSGI app around a PortalsService (or None)."""

    def respond(start, status, data, content_type='application/json',
                cache='no-store'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        start(status, [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body))),
            ('Cache-Control', cache),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy',
             "default-src 'none'; script-src 'self'; style-src 'self'; "
             "connect-src 'self'; img-src 'self' data:; base-uri none; "
             "form-action 'self'; frame-ancestors 'none'"),
            ('X-Content-Type-Options', 'nosniff'),
        ])
        return [body]

    def identity_of(env):
        if not callable(authenticate):
            return None
        try:
            identity = authenticate(env)
        except Exception:
            return None
        return identity if isinstance(identity, str) and identity else None

    def read_json(env, cap):
        if env.get('HTTP_ORIGIN') not in allowed_origins:
            raise _HttpError('403 Forbidden', 'origin_denied')
        content_type = env.get('CONTENT_TYPE', '').split(';')[0].strip().lower()
        if content_type != 'application/json':
            raise _HttpError('415 Unsupported Media Type', 'json_required')
        length = env.get('CONTENT_LENGTH', '')
        if not isinstance(length, str) or not length.isdigit() \
                or not 0 < int(length) <= cap:
            raise _HttpError('400 Bad Request', 'invalid_request')
        raw = env['wsgi.input'].read(int(length))
        if len(raw) != int(length):
            raise _HttpError('400 Bad Request', 'invalid_request')
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise _HttpError('400 Bad Request', 'invalid_request')
        if not isinstance(data, dict):
            raise _HttpError('400 Bad Request', 'invalid_request')
        return data

    class _HttpError(Exception):
        def __init__(self, status, error):
            super().__init__(error)
            self.status = status
            self.error = error

    def app(env, start):
        path = env.get('PATH_INFO', '')
        method = env.get('REQUEST_METHOD', '')
        if service is None:
            return respond(start, '503 Service Unavailable',
                           {'error': 'portals_unavailable'})
        submit_match = SUBMIT_ROUTE.fullmatch(path)
        case_match = CASE_ROUTE.fullmatch(path)
        media_match = MEDIA_ROUTE.fullmatch(path)
        review_match = REVIEW_ROUTE.fullmatch(path)
        try:
            # -- public reads --------------------------------------
            if method == 'GET' and path == '/api/portals/status':
                return respond(start, '200 OK', {'status': service.status()})
            if method == 'GET' and path == '/api/portals/wall':
                return respond(start, '200 OK', {'wall': service.wall()})
            if method == 'GET' and path == '/api/portals/spotlights':
                return respond(start, '200 OK',
                               {'spotlights': service.spotlights()})
            if method == 'GET' and path == '/api/portals/how-were-doing':
                return respond(start, '200 OK', service.metrics())
            if method == 'GET' and media_match:
                target = service.media_path(media_match.group(1))
                ext = target.suffix.lstrip('.')
                return respond(start, '200 OK', target.read_bytes(),
                               _MEDIA_TYPES[ext])
            if method == 'GET' and case_match:
                return respond(start, '200 OK',
                               {'case': service.case_status(case_match.group(1))})

            # -- public submissions --------------------------------
            if method == 'POST' and submit_match:
                kind = KIND_BY_SLUG.get(submit_match.group(1))
                if kind is None:
                    return respond(start, '404 Not Found', {'error': 'not_found'})
                cap = MAX_BODY if kind == 'WALL_OF_VALOR' else MAX_JSON_BODY
                data = read_json(env, cap)
                fields = {'company', 'name', 'contact', 'subject', 'body',
                          'honoree', 'relationship', 'consent',
                          'consent_version', 'photo_b64'}
                if not set(data) <= fields:
                    raise _HttpError('400 Bad Request', 'invalid_request')
                record = service.submit(
                    kind, data.get('company'),
                    name=data.get('name'), contact=data.get('contact'),
                    subject=data.get('subject', ''), body=data.get('body'),
                    honoree=data.get('honoree', ''),
                    relationship=data.get('relationship', ''),
                    consent=data.get('consent', False),
                    consent_version=data.get('consent_version', ''),
                    photo_b64=data.get('photo_b64'),
                    identity=identity_of(env) or '')
                return respond(start, '201 Created', {'case': record})

            # -- contractor surfaces (session required) ------------
            if path == '/api/portals/contractor/me':
                identity = identity_of(env)
                if identity is None:
                    return respond(start, '401 Unauthorized',
                                   {'error': 'sign_in_required'})
                if method == 'GET':
                    return respond(start, '200 OK',
                                   {'contractor': service.contractor_home(identity)})
                if method == 'POST':
                    read_json(env, MAX_JSON_BODY)
                    return respond(
                        start, '201 Created',
                        {'acknowledgment': service.acknowledge_handbook(identity)})
                return respond(start, '405 Method Not Allowed',
                               {'error': 'method_not_allowed'})

            # -- operator surfaces (operator authority required) ---
            if method == 'GET' and path == '/api/portals/operator/queue':
                identity = identity_of(env)
                if identity is None:
                    return respond(start, '401 Unauthorized',
                                   {'error': 'sign_in_required'})
                return respond(start, '200 OK',
                               {'queue': service.review_queue(identity)})
            if method == 'POST' and path == '/api/portals/operator/spotlights':
                identity = identity_of(env)
                if identity is None:
                    return respond(start, '401 Unauthorized',
                                   {'error': 'sign_in_required'})
                data = read_json(env, MAX_JSON_BODY)
                if set(data) != {'contractor_name', 'period_type',
                                 'period_label', 'citation', 'company'}:
                    raise _HttpError('400 Bad Request', 'invalid_request')
                record = service.record_spotlight(identity, **data)
                return respond(start, '201 Created', {'spotlight': record})
            if method == 'POST' and review_match:
                identity = identity_of(env)
                if identity is None:
                    return respond(start, '401 Unauthorized',
                                   {'error': 'sign_in_required'})
                data = read_json(env, MAX_JSON_BODY)
                ref, action = review_match.group(1), review_match.group(2)
                if action == 'review':
                    if set(data) != {'decision', 'note'} and set(data) != {'decision'}:
                        raise _HttpError('400 Bad Request', 'invalid_request')
                    record = service.review(
                        identity, ref, data['decision'], data.get('note', ''))
                else:
                    if set(data) != {'note'} and set(data) != set():
                        raise _HttpError('400 Bad Request', 'invalid_request')
                    record = service.resolve(identity, ref, data.get('note', ''))
                return respond(start, '200 OK', {'case': record})

            return respond(start, '404 Not Found', {'error': 'not_found'})
        except _HttpError as exc:
            return respond(start, exc.status, {'error': exc.error})
        except PortalsForbidden:
            return respond(start, '403 Forbidden',
                           {'error': 'portals_forbidden'})
        except PortalsDenied as exc:
            return respond(start, '400 Bad Request',
                           {'error': 'portals_denied', 'detail': str(exc)})
        except Exception:
            return respond(start, '500 Internal Server Error',
                           {'error': 'portals_error'})

    return app
