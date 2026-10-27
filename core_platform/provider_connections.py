"""
Module: core_platform.provider_connections
Architectural Layer: Remote Remote Online Notarization (RON) API Gateway Adapter
Description: Secure connection handlers for SignWell and BlueNotary platform endpoints.
             Enforces explicit payload boundaries, non-redirecting transport bounds,
             and robust timeout gates to prevent internal thread-locking.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

class ProviderConnectionError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Fail-closed redirect fence: forces immediate halts instead of credentials forward leaking."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API credential payload to a redirected remote host destination
        return None

class ReadOnlyProviderClient:
    """Bounded query manager enforcing absolute input validation fences over external APIs."""

    def __init__(self, provider, api_key, *, timeout=10, opener=None):
        if provider not in ('signwell', 'bluenotary'):
            raise ValueError('Unsupported provider platform allocation specified')
        if not isinstance(api_key, str) or not 8 <= len(api_key) <= 400 or any(
            ord(c) < 33 or ord(c) > 126 for c in api_key
        ):
            raise ValueError('API credential configuration out of safe boundaries')
        if not 1 <= timeout <= 30:
            raise ValueError('Timeout parameter outside allowed range matrix')
            
        self.provider = provider
        self._api_key = api_key
        self.timeout = timeout
        
        # Configure a secure non-redirecting transport pool natively
        self._opener = opener if opener is not None else urllib.request.build_opener(NoRedirect())

    def _get_auth_headers(self):
        """Constructs safe explicit authentication dictionary matrices uniformly."""
        if self.provider == 'signwell':
            return {'X-Api-Key': self._api_key}
        elif self.provider == 'bluenotary':
            return {'X-Authorization-Token': self._api_key}
        return {}

    def _get(self, url):
        headers = self._get_auth_headers()
        headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Sanders Dash & Seal Platform Sync Gateway v1.0'
        })
        
        try:
            req = urllib.request.Request(url, headers=headers, method='GET')
            with self._opener.open(req, timeout=self.timeout) as response:
                raw_response = response.read(1024 * 1024 + 1)
                if len(raw_response) > 1024 * 1024:
                    raise ValueError('Provider transmission response size threshold exceeded')
                return json.loads(raw_response.decode('utf-8'))
        except (urllib.error.URLError, ValueError, KeyError) as error:
            raise ProviderConnectionError(f"External platform network lookup failure ({self.provider}): {str(error)}") from error

    def get_document(self, document_id):
        if self.provider != 'signwell':
            raise ProviderConnectionError('SignWell operation track only')
        safe_id = self._safe_id(document_id)
        return self._get(f'https://signwell.com{safe_id}/')

    def get_session(self, session_id):
        if self.provider != 'bluenotary':
            raise ProviderConnectionError('BlueNotary operation track only')
        safe_id = self._safe_id(session_id)
        return self._get(f'https://bluenotary.us{safe_id}')

    def _safe_id(self, value):
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError('Invalid resource layout identification handle')
        if not all(c.isalnum() or c in '-_' for c in value):
            raise ValueError('Invalid resource identification character matrix')
        return urllib.parse.quote(value, safe='')

class WriteProviderClient(ReadOnlyProviderClient):
    """Transaction publisher pushing validated case payloads cleanly over remote sessions."""

    def create_request(self, url, payload):
        if not isinstance(payload, dict):
            raise ValueError('Structured dictionary request layout body required')
            
        headers = self._get_auth_headers()
        serialized_payload = json.dumps(payload, allow_nan=False).encode('utf-8')
        
        headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'Content-Length': str(len(serialized_payload)),
            'Accept': 'application/json',
            'User-Agent': 'Sanders Dash & Seal Platform Sync Gateway v1.0'
        })

        try:
            req = urllib.request.Request(url, data=serialized_payload, headers=headers, method='POST')
            with self._opener.open(req, timeout=self.timeout) as response:
                raw_response = response.read(1024 * 1024 + 1)
                if len(raw_response) > 1024 * 1024:
                    raise ValueError('Provider transmission response size threshold exceeded')
                
                result = json.loads(raw_response.decode('utf-8'))
                if not isinstance(result, dict):
                    raise ValueError('Unexpected remote data format returned')
                return result
        except (urllib.error.URLError, ValueError, KeyError) as error:
            raise ProviderConnectionError(f"External platform push execution failure ({self.provider}): {str(error)}") from error
