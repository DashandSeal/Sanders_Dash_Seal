"""Provider API connections for Sanders Dash & Seal.

Secrets must be injected by the deployment secret manager; never log tokens.
WriteProviderClient adds the documented document/session creation operations.
"""
import json
import urllib.error
import urllib.parse
import urllib.request


class ProviderConnectionError(RuntimeError):
    pass


class ReadOnlyProviderClient:
    def __init__(self, provider, api_key, *, timeout=10, opener=None):
        if provider not in ('signwell', 'bluenotary'):
            raise ValueError('unsupported provider')
        if (not isinstance(api_key, str) or not 8 <= len(api_key) <= 4096
                or any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
            raise ValueError('API credential required')
        if not 1 <= timeout <= 30:
            raise ValueError('timeout outside allowed range')
        self.provider = provider
        self._api_key = api_key
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener(NoRedirect()).open

    def _get(self, url):
        header = ('X-Api-Key', self._api_key) if self.provider == 'signwell' else ('Authorization', 'Bearer ' + self._api_key)
        req = urllib.request.Request(url, headers={header[0]: header[1], 'Accept': 'application/json'}, method='GET')
        try:
            with self._opener(req, timeout=self.timeout) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Provider response too large')
                return json.loads(raw)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, OSError) as exc:
            # Do not expose response bodies, URL query parameters, or credentials.
            raise ProviderConnectionError(self.provider + ' read-only request failed') from None

    def get_document(self, document_id):
        if self.provider != 'signwell':
            raise ValueError('SignWell operation only')
        return self._get('https://www.signwell.com/api/v1/documents/' + _safe_id(document_id))

    def get_session(self, session_id):
        if self.provider != 'bluenotary':
            raise ValueError('BlueNotary operation only')
        return self._get('https://app.bluenotary.us/api/integrationsv2/sessions/' + _safe_id(session_id))


def _safe_id(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError('invalid resource identifier')
    if not all(c.isascii() and (c.isalnum() or c in '-_') for c in value):
        raise ValueError('invalid resource identifier')
    return urllib.parse.quote(value, safe='')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API credential to a redirected host.
        return None


class WriteProviderClient(ReadOnlyProviderClient):
    def create_request(self, payload):
        url = ('https://www.signwell.com/api/v1/document_templates/documents/' if self.provider == 'signwell'
               else 'https://app.bluenotary.us/api/integrationsv2/sessions/')
        header = ('X-Api-Key', self._api_key) if self.provider == 'signwell' else ('Authorization', 'Bearer ' + self._api_key)
        req = urllib.request.Request(url, data=json.dumps(payload, allow_nan=False).encode(),
            headers={header[0]: header[1], 'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
        try:
            with self._opener(req, timeout=self.timeout) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Provider response too large')
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError('Provider object required')
                return result
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, OSError):
            raise ProviderConnectionError(self.provider + ' request outcome unavailable') from None
