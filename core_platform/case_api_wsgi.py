"""
Module: core_platform.case_api_wsgi
Architectural Layer: Authenticated Fail-Closed Case Intake HTTP API Gateway
Description: Authenticated development WSGI case intake interface. Confirms external identities
             independently via caller-supplied token vectors.
"""

import json
import re
from cases import CaseDenied

MAX_BODY = 8192
CASE_COLLECTION_PATH = '/v1/cases'
CASE_RESOURCE_RE = re.compile(r'^/v1/cases/([A-Za-z0-9_-]{1,128})$')

class APIConfigurationError(Exception):
    pass

def create_app(registry, authenticate):
    if not callable(authenticate):
        raise APIConfigurationError('Independent authentication adapter required')

    def respond(start_response, status, payload):
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        start_response(status, [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff')
        ])
        return [body]

    def app(environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')

        if not isinstance(path, str) or not isinstance(method, str):
            return respond(start_response, '400 Bad Request', {'error': 'invalid_environ'})

        # Route 1: Case Collection Endpoint (/v1/cases)
        if path == CASE_COLLECTION_PATH:
            if method != 'POST':
                return respond(start_response, '405 Method Not Allowed', {'error': 'method_not_allowed'})
                
            try:
                identity = authenticate(environ)
            except Exception:
                identity = None

            if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identity):
                return respond(start_response, '401 Unauthorized', {'error': 'unauthorized'})

            try:
                length_str = environ.get('CONTENT_LENGTH', '')
                if not length_str.isdigit() or int(length_str) > MAX_BODY:
                    return respond(start_response, '413 Content Too Large', {'error': 'payload_too_large'})
                if environ.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
                    return respond(start_response, '415 Unsupported Media Type', {'error': 'json_required'})

                length = int(length_str)
                raw = environ['wsgi.input'].read(length)
                if len(raw) != length:
                    raise ValueError('short body')

                data = json.loads(raw)
                if not isinstance(data, dict) or set(data.keys()) != {'case_id', 'jurisdiction', 'service'}:
                    raise ValueError('unexpected fields')

                record = registry.create(data['case_id'], data['jurisdiction'], data['service'], identity)
                return respond(start_response, '201 Created', {'case': record})
            except (ValueError, TypeError, KeyError, json.JSONDecodeError, CaseDenied) as err:
                return respond(start_response, '400 Bad Request', {'error': f'invalid_payload: {str(err)}'})

        # Route 2: Individual Case Resource Endpoint (/v1/cases/<id>)
        match = CASE_RESOURCE_RE.fullmatch(path)
        if match:
            if method != 'GET':
                return respond(start_response, '405 Method Not Allowed', {'error': 'method_not_allowed'})
                
            try:
                identity = authenticate(environ)
            except Exception:
                identity = None

            if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identity):
                return respond(start_response, '401 Unauthorized', {'error': 'unauthorized'})

            try:
                case_id = match.group(1)
                record = registry.get(case_id)
                if not record or record.get('requester') != identity:
                    return respond(start_response, '404 Not Found', {'error': 'case_not_found'})
                return respond(start_response, '200 OK', {'case': record})
            except CaseDenied:
                return respond(start_response, '404 Not Found', {'error': 'case_not_found'})

        # Default Catch-all: Route Not Found
        return respond(start_response, '404 Not Found', {'error': 'not_found'})

    return app
