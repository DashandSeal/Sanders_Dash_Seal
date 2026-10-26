"""
Module: core_platform.stream_api
Architectural Layer: Secure Durable Stream Processing Matrix
Description: Validates incoming signed transaction frames. Enforces strict JSON keys,
             signature non-repudiation, and transactional deduplication states.
"""

from collections.abc import Mapping
import json
from .pipeline_api import IDENT, TransactionRejected, TransactionStore

class StreamConfigurationError(Exception):
    pass

def stream_signing_payload(event):
    """Excludes the signature itself; binds the independently registered actor and context."""
    if not isinstance(event, dict):
        raise TransactionRejected('Invalid signed event structure')
        
    required_keys = {'actor', 'transaction_id', 'transaction', 'signature'}
    if set(event.keys()) != required_keys:
        raise TransactionRejected('Invalid signed event structure: fields mismatch')
        
    if not isinstance(event['actor'], str) or not IDENT.fullmatch(event['actor']):
        raise TransactionRejected('Invalid signed event: actor signature invalid')
    if not isinstance(event['transaction_id'], str) or not IDENT.fullmatch(event['transaction_id']):
        raise TransactionRejected('Invalid signed event: transactional identity mismatch')
    if not isinstance(event['transaction'], dict):
        raise TransactionRejected('Invalid signed event structure')
        
    if event['transaction'].get('request_id') != event['transaction_id']:
        raise TransactionRejected('Invalid signed event footprint boundary')
    if not isinstance(event['signature'], str) or len(event['signature']) < 32:
        raise TransactionRejected('Invalid signed event: signature token empty')
        
    return json.dumps({
        'actor': event['actor'],
        'transaction': event['transaction']
    }, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def strict_json(raw):
    """Parses raw text payloads while strictly forbidding duplicate keys or invalid structures."""
    def pairs_hook(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key string detected')
            result[key] = value
        return result

    def constant_hook(value):
        raise ValueError(f'Nonfinite JSON constant value forbidden: {value}')

    try:
        decoded_str = raw.decode('utf-8')
        return json.loads(decoded_str, object_pairs_hook=pairs_hook, parse_constant=constant_hook)
    except Exception as error:
        raise ValueError(f'Malformed stream body format: {str(error)}') from error

def create_stream_app(processor=None, release_verifier=None, store=None, verifiers=None):
    """Factory builder initializing verified processing blocks and signature keys maps."""
    if verifiers is None:
        verifiers = {}
    if not isinstance(verifiers, Mapping):
        raise StreamConfigurationError('Valid verifiers mapping configuration required')

    def app(env, start):
        def respond(status, payload):
            raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            start(status, [
                ('Content-Type', 'application/json'),
                ('Content-Length', str(len(raw_body))),
                ('Cache-Control', 'no-store'),
                ('X-Content-Type-Options', 'nosniff')
            ])
            return [raw_body]

        # 1. Structural Gateway Checks
        try:
            ready = (callable(processor) and callable(release_verifier) and
                     release_verifier() is True and isinstance(store, TransactionStore))
        except Exception:
            ready = False

        if not ready:
            return respond('503 Service Unavailable', {'error': 'stream_authority_offline'})

        if env.get('REQUEST_METHOD') != 'POST':
            return respond('405 Method Not Allowed', {'error': 'post_required'})
            
        content_type = env.get('CONTENT_TYPE', '').split(';')[0].strip().lower()
        if content_type != 'application/json':
            return respond('415 Unsupported Media Type', {'error': 'json_required'})

        # 2. Extract and Enforce Ingestion Size Limits
        try:
            length_str = env.get('CONTENT_LENGTH', '0')
            if not length_str.isdigit():
                raise ValueError('Invalid size header')
            length = int(length_str)
            if not 0 < length <= 262144:
                raise ValueError('Size boundaries out of range')

            raw_input = env['wsgi.input'].read(length)
            if len(raw_input) != length:
                raise ValueError('Short payload frame')

            event = strict_json(raw_input)
            payload_str = stream_signing_payload(event)
        except Exception as err:
            return respond('400 Bad Request', {'error': f'invalid_stream_event: {str(err)}'})

        # 3. Cryptographic Signature Authentication Block
        try:
            # FIX: Clean lookup context querying the factory-bound verifiers dictionary mapping
            verifier = verifiers.get(event['actor'])
            if verifier is None:
                return respond('401 Unauthorized', {'error': 'unregistered_actor_signature'})
                
            # Execute cryptographic verification checks safely over the payload footprint
            if not hasattr(verifier, 'verify') or verifier.verify(event['transaction_id'], payload_str, event['signature']) is not True:
                return respond('401 Unauthorized', {'error': 'invalid_stream_signature'})

            def committed_processor(transaction, namespaced_actor, database):
                # Ensure existing hooks retain execution capabilities
                return processor(transaction, namespaced_actor, database)

            # Commit the transaction safely through the persistent deduplication engine
            receipt = store.process(
                event['transaction'],
                stream_type='TRANSACTION_STREAM:' + event['actor'],
                callback=committed_processor
            )
            return respond('200 OK', {
                'transaction_id': event['transaction_id'],
                'status': 'COMMITTED',
                'receipt': receipt
            })
        except TransactionRejected as err:
            return respond('409 Conflict', {'error': f'stream_transaction_rejected: {str(err)}'})
        except Exception as err:
            return respond('503 Service Unavailable', {'error': f'stream_commit_failure: {str(err)}'})

    return app
