"""Signed Streaming events committed by the existing durable Python authority."""
from collections.abc import Mapping
import json

from .pipeline_api import IDENT, TransactionRejected, TransactionStore
from .receipt_verification import ReceiptSignatureVerifier, verify_and_log_receipt


def stream_signing_payload(event):
    """Exclude the signature itself; bind the independently registered actor."""
    if (not isinstance(event, dict)
            or set(event) != {'actor', 'transaction_id', 'transaction', 'signature'}
            or not isinstance(event['actor'], str) or not IDENT.fullmatch(event['actor'])
            or not isinstance(event['transaction_id'], str)
            or not IDENT.fullmatch(event['transaction_id'])
            or not isinstance(event['transaction'], dict)
            or event['transaction'].get('request_id') != event['transaction_id']
            or not isinstance(event['signature'], str) or len(event['signature']) > 256):
        raise TransactionRejected('Invalid signed event')
    return json.dumps({'actor': event['actor'], 'transaction': event['transaction']},
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def create_stream_app(processor=None, release_verifier=None, store=None, verifiers=None):
    """Keys and business processor come from the trusted runtime factory only."""
    def app(env, start):
        def respond(status, payload):
            raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
            start(status, [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'),
                          ('Content-Length', str(len(raw)))])
            return [raw]
        try:
            ready = (callable(processor) and callable(release_verifier)
                     and release_verifier() is True and isinstance(store, TransactionStore)
                     and isinstance(verifiers, Mapping) and bool(verifiers))
        except Exception:
            ready = False
        if not ready:
            return respond('503 Service Unavailable', {'error': 'stream_authority_unavailable'})
        if env.get('REQUEST_METHOD') != 'POST':
            return respond('405 Method Not Allowed', {'error': 'post_required'})
        if env.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
            return respond('415 Unsupported Media Type', {'error': 'json_required'})
        try:
            length = int(env.get('CONTENT_LENGTH', '0'))
            if not 0 < length <= 262144:
                raise ValueError('Size')
            raw = env['wsgi.input'].read(length)
            if len(raw) != length:
                raise ValueError('Short body')
            event = strict_json(raw)
            payload = stream_signing_payload(event)
        except (KeyError, ValueError, TypeError, UnicodeError, RecursionError):
            return respond('400 Bad Request', {'error': 'invalid_stream_event'})
        try:
            verifier = verifiers.get(event['actor'])
            # Verify before deduplication as well: invalid signatures never get a
            # receipt just because someone previously committed the same ID.
            if (not isinstance(verifier, ReceiptSignatureVerifier)
                    or not verifier.verify(event['transaction_id'], payload, event['signature'])):
                return respond('401 Unauthorized', {'error': 'invalid_stream_signature'})

            def committed_processor(transaction, namespaced_actor, db):
                if not verify_and_log_receipt(None, event['transaction_id'], payload,
                        event['signature'], verifier=verifier, connection=db):
                    raise TransactionRejected('Signed receipt rejected')
                # Existing processor retains business validation, human authority
                # and audit duties, sharing this exact SQLite transaction.
                return processor(transaction, event['actor'], db)

            receipt = store.process(event['transaction'], 'stream:' + event['actor'], committed_processor)
            return respond('200 OK', {'transaction_id': event['transaction_id'],
                'status': 'COMMITTED', 'receipt': receipt})
        except (TransactionRejected, ValueError, TypeError):
            return respond('409 Conflict', {'error': 'stream_transaction_rejected'})
        except Exception:
            return respond('503 Service Unavailable', {'error': 'stream_commit_unavailable'})
    return app
