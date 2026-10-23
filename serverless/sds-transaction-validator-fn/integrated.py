"""Connector Hub function task: signed events -> durable core -> archive receipts.

The owner's original func.py is retained unchanged. This integrated entrypoint
uses no local authoritative database, credentials or background polling loops.
"""
import base64
import binascii
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


MAX_BODY = 1048576
MAX_RECORDS = 128


class BatchRejected(ValueError):
    pass


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise BatchRejected('Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise BatchRejected('Nonfinite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BatchRejected('Backend redirect rejected')


def dispatch(event, endpoint, timeout):
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path != '/api/stream/transactions'):
        raise BatchRejected('Configured HTTPS stream endpoint required')
    request = urllib.request.Request(endpoint,
        data=json.dumps(event, separators=(',', ':'), allow_nan=False).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        if response.status != 200:
            raise BatchRejected('Backend rejected event')
        raw = response.read(131073)
        if len(raw) > 131072:
            raise BatchRejected('Backend response too large')
        receipt = strict_json(raw)
    if (not isinstance(receipt, dict) or receipt.get('status') != 'COMMITTED'
            or receipt.get('transaction_id') != event['transaction_id']
            or not isinstance(receipt.get('receipt'), dict)
            or receipt['receipt'].get('request_id') != event['transaction_id']):
        raise BatchRejected('Committed matching receipt required')
    return receipt


def process_batch(raw, endpoint, *, send=dispatch, clock=time.monotonic):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BODY:
        raise BatchRejected('Batch size rejected')
    body = strict_json(raw)
    if not isinstance(body, list) or not 0 < len(body) <= MAX_RECORDS:
        raise BatchRejected('Nonempty bounded Connector Hub list required')
    # Validate the entire transport envelope before committing any event.
    events = []
    for record in body:
        if not isinstance(record, dict) or not isinstance(record.get('value'), str):
            raise BatchRejected('Encoded stream value required')
        try:
            value = base64.b64decode(record['value'], validate=True)
            if not 0 < len(value) <= 262144:
                raise BatchRejected('Event size rejected')
            event = strict_json(value)
        except (binascii.Error, UnicodeError, ValueError) as error:
            raise BatchRejected('Invalid stream value') from error
        if (not isinstance(event, dict)
                or set(event) != {'actor', 'transaction_id', 'transaction', 'signature'}
                or not isinstance(event['transaction_id'], str)
                or not isinstance(event['transaction'], dict)
                or event['transaction'].get('request_id') != event['transaction_id']):
            raise BatchRejected('Signed transaction envelope required')
        events.append(event)
    deadline = clock() + 24
    receipts = []
    for event in events:
        remaining = deadline - clock()
        if remaining < 1:
            raise BatchRejected('Batch deadline reached; retry safely')
        receipts.append(send(event, endpoint, min(3, remaining)))
    return receipts


def handler(ctx, data=None):
    from fdk import response
    try:
        if data is None:
            raise BatchRejected('Batch required')
        receipts = process_batch(data.read(MAX_BODY + 1), os.environ.get('SDS_STREAM_BACKEND_URL', ''))
        # Use Connector Hub's supported JSON-list output for the storage sink.
        return response.Response(ctx, response_data=json.dumps(receipts, separators=(',', ':')),
            headers={'Content-Type': 'application/json'}, status_code=200)
    except Exception:
        # No payloads, credentials, internal exception details or false SUCCESS.
        return response.Response(ctx, response_data='{"error":"stream_batch_not_committed"}',
            headers={'Content-Type': 'application/json'}, status_code=503)
