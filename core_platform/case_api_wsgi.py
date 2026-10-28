"""Authenticated development WSGI case intake; not a notarial authorization endpoint.

The authentication adapter must independently validate an external identity token.
No trust is placed in caller-supplied user headers, role labels or payment status.
"""
import json
import re
from .cases import CaseDenied

MAX_BODY = 8192
CASE_PATH = re.compile(r'^/v1/cases/([A-Za-z0-9_.-]{1,128})$')

class APIConfigurationError(Exception):
    pass

def create_app(registry, authenticate):
    if not callable(authenticate):
        raise APIConfigurationError('Independent authentication adapter required')

    def respond(start_response, status, payload):
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        start_response(status, [('Content-Type','application/json'),
                                ('Content-Length',str(len(body))),
                                ('Cache-Control','no-store'),
                                ('X-Content-Type-Options','nosniff')])
        return [body]

    def app(environ, start_response):
        path = environ.get('PATH_INFO','')
        method = environ.get('REQUEST_METHOD','')
        if not isinstance(path,str) or not isinstance(method,str):
            return respond(start_response,'400 Bad Request',{'error':'invalid_request'})
        if path != '/v1/cases' and not CASE_PATH.fullmatch(path):
            return respond(start_response,'404 Not Found',{'error':'not_found'})
        if (path == '/v1/cases' and method != 'POST') or (path != '/v1/cases' and method != 'GET'):
            return respond(start_response,'405 Method Not Allowed',{'error':'method_not_allowed'})
        try:
            identity = authenticate(environ)
        except Exception:
            identity = None
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',identity):
            return respond(start_response,'401 Unauthorized',{'error':'unauthorized'})
        if method == 'POST':
            length = environ.get('CONTENT_LENGTH','')
            if not isinstance(length,str) or not length.isdigit() or not 0 < int(length) <= MAX_BODY:
                return respond(start_response,'413 Content Too Large',{'error':'invalid_length'})
            if environ.get('CONTENT_TYPE','').split(';')[0].strip().lower() != 'application/json':
                return respond(start_response,'415 Unsupported Media Type',{'error':'json_required'})
            try:
                raw = environ['wsgi.input'].read(int(length))
                if len(raw) != int(length):
                    raise ValueError('short body')
                data = json.loads(raw)
                if not isinstance(data,dict) or set(data) != {'case_id','jurisdiction','service'}:
                    raise ValueError('unexpected fields')
                record = registry.create(data['case_id'],data['jurisdiction'],data['service'],identity)
            except (ValueError,TypeError,KeyError,UnicodeError,CaseDenied):
                return respond(start_response,'400 Bad Request',{'error':'case_denied'})
            return respond(start_response,'201 Created',{'case':record})
        match = CASE_PATH.fullmatch(path)
        try:
            record = registry.get(match.group(1))
        except (ValueError,TypeError,CaseDenied):
            return respond(start_response,'404 Not Found',{'error':'not_found'})
        if not record or record.get('requester') != identity:
            return respond(start_response,'404 Not Found',{'error':'not_found'})
        return respond(start_response,'200 OK',{'case':record})
    return app
