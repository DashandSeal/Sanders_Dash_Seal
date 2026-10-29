"""
Customer interface over existing case, appointment and payment components.

Authentication is an injected independent session verifier, never a user header.
Production startup must be externally verified, default API behavior is denial.
The auth application owns OIDC/session cookies, login CSRF and logout behavior.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from .appointments import AppointmentDenied, IDENT
from .cases import CaseDenied
from .stripe_payments import PaymentDenied

ASSETS = {
    '/auth/login': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/register': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/setup': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/logout': ('auth.html', 'text/html; charset=utf-8'),
    '/assets/auth.js': ('auth.js', 'application/javascript; charset=utf-8'),
    '/resources.js': ('resources.js', 'application/javascript; charset=utf-8'),
    '/landing': ('jade-landing.html', 'text/html; charset=utf-8'),
    '/assets/jade-landing.css': ('jade-landing.css', 'text/css; charset=utf-8'),
    '/assets/jade-landing.js': ('jade-landing.js', 'application/javascript; charset=utf-8'),
    '/assets/sds-founder.png': ('sds-founder.png', 'image/png'),
    '/assets/wall-of-valor-primary.jpg': ('IMG_20261024_141701319_HDR.jpg', 'image/jpeg'),
    '/assets/wall-of-valor-secondary.jpg': ('IMG_20261024_141659486_HDR.jpg', 'image/jpeg'),
    '/': ('jade-landing.html', 'text/html; charset=utf-8'),
    '/appointments': ('index.html', 'text/html; charset=utf-8'),
    '/operator': ('index.html', 'text/html; charset=utf-8'),
    '/assets/operator.js': ('operator.js', 'application/javascript; charset=utf-8'),
    '/assets/booking.css': ('booking.css', 'text/css; charset=utf-8'),
    '/assets/booking.js': ('booking.js', 'application/javascript; charset=utf-8'),
}

CASE_ROUTE = re.compile(r'^/api/appointments/([A-Za-z0-9_-]{1,128})/checkout$')
OPERATOR_ROUTE = re.compile(r'^/api/operator/appointments/([A-Za-z0-9_-]{1,128})/quote$')

def create_customer_app(appointments, authenticate, payments, auth_app, site_origin, *, release_verifier=lambda: False):
    origin = urlparse(site_origin)
    if (origin.scheme != 'https' or not origin.netloc or origin.path
        or origin.query or origin.fragment or origin.username
        or not all(callable(v) for v in (authenticate, auth_app, release_verifier))):
        raise ValueError('Trusted origin and independent authentication adapters required')
        
    root = Path(__file__).resolve().parent.parent / 'web'

    def respond(start_status, data, content_type='application/json'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        start_status(str(status) if 'status' in locals() else '200 OK', [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; "
                                        "connect-src 'self'; img-src 'self' data:; base-uri none; form-action 'self'; frame-ancestors 'none'"),
            ('X-Content-Type-Options', 'nosniff')
        ])
        return [body]

    def app(env, start):
        path, method = env.get('PATH_INFO', ''), env.get('REQUEST_METHOD', '')
        if method == 'GET' and path in ASSETS:
            filename, mime = ASSETS[path]
            return respond(start, '200 OK', (root / filename).read_bytes(), mime)
            
        try:
            if release_verifier() is not True:
                return respond(start, '503 Service Unavailable', {'error': 'appointments_unavailable'})
        except Exception:
            return respond(start, '503 Service Unavailable', {'error': 'appointments_unavailable'})

        if path.startswith('/auth/'):
            return auth_app(env, start)

        case_match = CASE_ROUTE.fullmatch(path)
        operator_match = OPERATOR_ROUTE.fullmatch(path)
        is_operator_route = path == '/api/operator/appointments' or operator_match is not None

        if path not in ('/api/session', '/api/appointments') and not case_match and not is_operator_route:
            return respond(start, '404 Not Found', {'error': 'not_found'})

        allowed = ('GET', 'POST') if path == '/api/appointments' else (
            ('POST',) if operator_match or (case_match and case_match.group(2)) else ('GET',)
        )
        if method not in allowed:
            return respond(start, '405 Method Not Allowed', {'error': 'method_not_allowed'})

        try:
            identity = authenticate(env)
        except Exception:
            identity = None

        if not isinstance(identity, str) or not IDENT.fullmatch(identity):
            return respond(start, '401 Unauthorized', {'error': 'sign_in_required'})

        if is_operator_route:
            try:
                authorized = payments.operator_verifier(identity) is True
            except Exception:
                authorized = False
            if not authorized:
                return respond(start, '403 Forbidden', {'error': 'operator_required'})

        data = None
        if method == 'POST':
            if env.get('HTTP_ORIGIN') != site_origin:
                return respond(start, '403 Forbidden', {'error': 'origin_denied'})
            if env.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
                return respond(start, '415 Unsupported Media Type', {'error': 'json_required'})
            try:
                length = env.get('CONTENT_LENGTH', '')
                if not isinstance(length, str) or not length.isdigit() or not 0 < int(length) <= 4096:
                    raise ValueError('length')
                row = env['wsgi.input'].read(int(length))
                if len(row) != int(length):
                    raise ValueError('short body')
                data = json.loads(row)
                if not isinstance(data, dict):
                    raise ValueError('object required')
            except (ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError):
                return respond(start, '400 Bad Request', {'error': 'invalid_request'})

        try:
            if path == '/api/operator/appointments':
                return respond(start, '200 OK', {'appointments': appointments.list_for_operator()})
            if operator_match:
                if set(data) != {'items', 'expires_at'}:
                    raise ValueError('unexpected fields')
                quote = payments.approve_quote(operator_match.group(1), identity, **data)
                return respond(start, '201 Created', {'quote': quote})
            if path == '/api/session':
                return respond(start, '200 OK', {'authenticated': True})
            if path == '/api/appointments':
                if method == 'GET':
                    return respond(start, '200 OK', {'appointments': appointments.list_owned(identity)})
                expected = {'request_id', 'jurisdiction', 'service', 'requested_start', 'meeting_area', 'consent'}
                if set(data) != expected:
                    raise ValueError('unexpected fields')
                record = appointments.request(identity, **data)
                return respond(start, '201 Created', {'appointment': record})

            case_id = case_match.group(1)
            record = appointments.get(case_id, identity)
            
            if method == 'GET':
                return respond(start, '200 OK', {
                    'appointment': record,
                    'quote': payments.quote_for_case_id(identity),
                    'payment': payments.ledger.status(case_id)
                })

            if set(data) != {'quote_id', 'accept_quote'}:
                raise ValueError('unexpected fields')
            result = payments.checkout(case_id, identity, **data)
            return respond(start, '200 OK', result)

        except AppointmentDenied:
            return respond(start, '400 Bad Request' if path == '/api/appointments' else '404 Not Found', {'error': 'appointment_unavailable'})
        except (ValueError, TypeError, KeyError, CaseDenied):
            return respond(start, '400 Bad Request', {'error': 'invalid_request'})
        except PaymentDenied:
            return respond(start, '409 Conflict', {'error': 'checkout_unavailable'})
        except Exception:
            return respond(start, '503 Service Unavailable', {'error': 'temporarily_unavailable'})

    return app
