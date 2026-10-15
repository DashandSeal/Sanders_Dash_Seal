"""Read-only provider API connections for Sanders Dash & Seal.

Secrets must be injected by the deployment secret manager; never log tokens.
This module cannot initiate a signing or notarization session.
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
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError('API credential required')
        if not 1 <= timeout <= 30:
            raise ValueError('timeout outside allowed range')
        self.provider = provider
        self._api_key = api_key
        self.timeout = timeout
        self._opener = opener or urllib.request.urlopen

    def _get(self, url):
        header = ('X-Api-Key', self._api_key) if self.provider == 'signwell' else ('Authorization', 'Bearer ' + self._api_key)
        req = urllib.request.Request(url, headers={header[0]: header[1], 'Accept': 'application/json'}, method='GET')
        try:
            with self._opener(req, timeout=self.timeout) as response:
                return json.loads(response.read(1024 * 1024))
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
