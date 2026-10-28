"""
Module: core_platform.stream_api
Architectural Layer: Cryptographically Guarded Payment Webhook Transport
Design Standard: Platinum Blue Diamond Standard
Description: Processes incoming raw Stripe webhook stream events. Normalizes all
             reverse-proxy metadata, enforces strict size limits, ensures atomic
             SQLite deduplication, and routes events into the ledger engine.
             Optimized for zero unnecessary resource overhead and near-zero footprints.
"""

import json
import logging
import time
import stripe
from stripe.error import SignatureVerificationError

# Enterprise security boundaries: Webhook payloads never require more than 64KB
MAX_WEBHOOK_BODY_BYTES = 65536

class WebhookConfigurationError(Exception):
    pass


def import_make_app(ledger_engine, webhook_secret, *, enabled=True, expected_livemode=True):
    """
    Factory builder initializing verified webhook receivers.
    Configures SQLite environment execution states and hardens the WSGI gateway entry point.
    """
    if enabled and (not isinstance(webhook_secret, str) or not webhook_secret.startswith('whsec_')):
        raise WebhookConfigurationError("Invalid Stripe Webhook signature token configuration parameters")

    def respond(start_response, status_string, response_dict):
        body_bytes = json.dumps(response_dict, separators=(',', ':')).encode('utf-8')
        start_response(status_string, [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body_bytes))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff')
        ])
        return [body_bytes]

    def application(environ, start_response):
        if not enabled:
            return respond(start_response, '503 Service Unavailable', {'error': 'webhook_gateway_disabled'})

        # 1. Edge Proxy Normalization Layer
        path = environ.get('PATH_INFO', '').strip()
        method = environ.get('REQUEST_METHOD', '').strip().upper()

        if path != '/v1/payments/stripe/webhook':
            return respond(start_response, '404 Not Found', {'error': 'endpoint_not_found'})

        if method != 'POST':
            return respond(start_response, '405 Method Not Allowed', {'error': 'post_required'})

        # 2. Size Boundary Verification Guard
        try:
            content_length_str = environ.get('CONTENT_LENGTH', '0')
            if not content_length_str.isdigit():
                return respond(start_response, '400 Bad Request', {'error': 'invalid_content_length_header'})

            content_length = int(content_length_str)
            if not 0 < content_length <= MAX_WEBHOOK_BODY_BYTES:
                return respond(start_response, '413 Content Too Large', {'error': 'payload_exceeds_safe_boundaries'})
        except (ValueError, TypeError):
            return respond(start_response, '400 Bad Request', {'error': 'malformed_length_parameters'})

        # 3. Extract Raw Body Buffer Natively
        try:
            raw_body = environ['wsgi.input'].read(content_length)
            if len(raw_body) != content_length:
                return respond(start_response, '400 Bad Request', {'error': 'incomplete_data_frame'})
        except Exception as read_error:
            logging.error(f"❌ Webhook network stream read exception: {str(read_error)}")
            return respond(start_response, '500 Internal Server Error', {'error': 'stream_read_failure'})

        # 4. Cryptographic Signature Validation Loop
        sig_header = environ.get('HTTP_STRIPE_SIGNATURE', '')
        if not sig_header:
            return respond(start_response, '401 Unauthorized', {'error': 'missing_stripe_signature_header'})

        try:
            event = stripe.Webhook.construct_event(
                payload=raw_body,
                sig_header=sig_header,
                secret=webhook_secret
            )
        except (ValueError, SignatureVerificationError) as signature_error:
            logging.warning(f"⚠️ Cryptographic verification rejected payload handshake: {str(signature_error)}")
            return respond(start_response, '401 Unauthorized', {'error': 'invalid_cryptographic_signature'})

        # 5. Production Environment Security Bounds
        if event.get('livemode') != expected_livemode:
            return respond(start_response, '400 Bad Request', {'error': 'environment_livemode_mismatch'})

        # 6. Idempotent Inspection & Ledger Handoff
        try:
            event_id = event.get('id')
            event_type = event.get('type')
            event_data_object = event.get('data', {}).get('object', {})

            if not event_id or not event_type:
                raise ValueError("Malformed event identity elements")

            with ledger_engine.connect() as db:
                # Active WAL pragma setup to optimize performance and prevent database contention hanging
                db.execute('PRAGMA journal_mode=WAL;')
                db.execute('PRAGMA synchronous=NORMAL;')
                
                # Immediate exclusive write lock to completely isolate ledger processing requests
                db.execute('BEGIN IMMEDIATE')
                
                is_duplicate = db.execute(
                    'SELECT 1 FROM stripe_processed_events WHERE id = ?', 
                    (event_id,)
                ).fetchone()
                
                if is_duplicate:
                    # CRITICAL FIX: Explicitly release transaction state before returning
                    db.rollback()
                    return respond(start_response, '200 OK', {
                        'status': 'SUCCESS_ALREADY_PROCESSED', 
                        'event_id': event_id
                    })

                # Route to specific structural accounting logging handlers
                if event_type == 'checkout.session.completed':
                    ledger_engine.fulfill_checkout(event_data_object, db)
                elif event_type == 'invoice.paid':
                    ledger_engine.record_subscription_renewal(event_data_object, db)
                elif event_type == 'charge.refunded':
                    ledger_engine.process_reversal(event_data_object, db)
                
                # Register completed processing signature natively inside local tracking rows
                db.execute(
                    'INSERT INTO stripe_processed_events (id, type, processed_at) VALUES (?, ?, ?)',
                    (event_id, event_type, int(time.time()))
                )
                db.commit()

            return respond(start_response, '200 OK', {
                'status': 'LEDGER_SETTLED', 
                'event_id': event_id
            })

        except Exception as processing_error:
            logging.error(f"❌ Internal accounting engine processing fault: {str(processing_error)}")
            return respond(start_response, '500 Internal Server Error', {'error': 'ledger_reconciliation_failed'})

    return application
