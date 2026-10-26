"""
Module: core_platform.stripe_webhook_wsgi
Architectural Layer: Cryptographically Guarded Payment Webhook Transport
Description: Processes incoming raw Stripe webhook stream events.
             Validates cryptographic signatures via HMAC-SHA256 headers,
             enforces strict size limits, and registers verified sessions.
"""

import json
import logging
import stripe
from stripe.error import SignatureVerificationError

# Enterprise security limits: Webhook structures never require more than 64KB
MAX_WEBHOOK_BODY_BYTES = 65536

class WebhookConfigurationError(Exception):
    pass

def import_make_app(ledger_engine, webhook_secret, *, enabled=True, expected_livemode=True):
    """
    Factory builder initializing verified webhook receivers.
    Ensures absolute data protection and idempotent validation structures.
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

        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')

        if path != '/v1/payments/stripe/webhook':
            return respond(start_response, '404 Not Found', {'error': 'endpoint_not_found'})
            
        if method != 'POST':
            return respond(start_response, '405 Method Not Allowed', {'error': 'post_required'})

        # 1. Size Boundary Verification Guard
        try:
            content_length_str = environ.get('CONTENT_LENGTH', '0')
            if not content_length_str.isdigit():
                return respond(start_response, '400 Bad Request', {'error': 'invalid_content_length_header'})
                
            content_length = int(content_length_str)
            if not 0 < content_length <= MAX_WEBHOOK_BODY_BYTES:
                return respond(start_response, '413 Content Too Large', {'error': 'payload_exceeds_safe_boundaries'})
        except (ValueError, TypeError):
            return respond(start_response, '400 Bad Request', {'error': 'malformed_length_parameters'})

        # 2. Extract Raw Body Buffer Natively (Forbid prior parsing mutations)
        try:
            raw_body = environ['wsgi.input'].read(content_length)
            if len(raw_body) != content_length:
                return respond(start_response, '400 Bad Request', {'error': 'incomplete_data_frame'})
        except Exception as read_error:
            return respond(start_response, '500 Internal Server Error', {'error': f'stream_read_failure: {str(read_error)}'})

        # 3. Cryptographic Signature Validation Loop
        sig_header = environ.get('HTTP_STRIPE_SIGNATURE', '')
        if not sig_header:
            return respond(start_response, '401 Unauthorized', {'error': 'missing_stripe_signature_header'})

        try:
            # Force direct multi-hypothesis event reconstruction over unaltered bytes
            event = stripe.Webhook.construct_event(
                payload=raw_body,
                sig_header=sig_header,
                secret=webhook_secret
            )
        except (ValueError, SignatureVerificationError) as signature_error:
            logging.warning(f"⚠️ Cryptographic verification rejected payload handshake: {str(signature_error)}")
            return respond(start_response, '401 Unauthorized', {'error': 'invalid_cryptographic_signature'})

        # 4. Enforce Production Environment Security Bounds
        if event.get('livemode') != expected_livemode:
            return respond(start_response, '400 Bad Request', {'error': 'environment_livemode_mismatch'})

        # 5. Idempotent Ingestion & Ledger Handoff
        try:
            event_id = event.get('id')
            event_type = event.get('type')
            event_data_object = event.get('data', {}).get('object', {})

            if not event_id or not event_type:
                raise ValueError("Malformed event identity elements")

            # Route financial lifecycle metrics cleanly into your persistent accounting logs
            with ledger_engine.connect() as db:
                # Deduplicate by Event ID natively inside SQLite schema blocks to stop double-processing
                is_duplicate = db.execute("SELECT 1 FROM stripe_processed_events WHERE id = ?;", (event_id,)).fetchone()
                if is_duplicate:
                    return respond(start_response, '200 OK', {'status': 'SUCCESS_ALREADY_PROCESSED', 'event_id': event_id})

                if event_type == 'checkout.session.completed':
                    ledger_engine.fulfill_checkout(event_data_object, db)
                elif event_type == 'invoice.paid':
                    ledger_engine.record_subscription_renewal(event_data_object, db)
                elif event_type == 'charge.refunded':
                    ledger_engine.process_reversal(event_data_object, db)
                else:
                    # Gracefully acknowledge un-tracked events to stop retry cycles
                    db.execute("INSERT INTO stripe_processed_events (id, type, processed_at) VALUES (?, ?, ?);",
                               (event_id, event_type, int(time.time())))

            return respond(start_response, '200 OK', {'status': 'LEDGER_SETTLED', 'event_id': event_id})

        except Exception as processing_error:
            logging.error(f"❌ Internal accounting engine processing fault: {str(processing_error)}")
            return respond(start_response, '500 Internal Server Error', {'error': 'ledger_reconciliation_failed'})

    return application
