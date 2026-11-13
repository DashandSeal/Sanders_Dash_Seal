"""
Module: core_platform.stream_api
Architectural Layer: Cryptographically Guarded Payment Webhook Transport
Design Standard: Platinum Blue Diamond Standard
Description: Real-time autonomous synthetic AI processing loop for incoming raw 
             Stripe webhook stream events. Automatically intercepts structural variations,
             performs high-resilience signature checks, and commits transactions 
             atomically with zero unnecessary resource overhead.
"""

import json
import logging
import time
import stripe
from stripe import SignatureVerificationError

from core_platform.global_payments import (
    CurrencyError,
    LivePaymentDenied,
    normalize_currency,
    validate_webhook_event,
)

# Enterprise security boundaries: Webhook payloads never require more than 64KB
MAX_WEBHOOK_BODY_BYTES = 65536

class WebhookConfigurationError(Exception):
    pass


def import_make_app(ledger_engine, webhook_secret, *, enabled=True, expected_livemode=False,
                    live_verified=False, bozly_recorder=None, bozly_db_path=None):
    """
    Factory builder initializing verified real-time webhook streaming receivers.
    Configures SQLite environment execution states and hardens the WSGI gateway entry point.

    Default is Stripe TEST mode (expected_livemode=False). Live mode requires
    BOTH expected_livemode=True AND live_verified=True: live acceptance is
    only possible after live eligibility and release controls have been
    explicitly confirmed by the owner. Requesting live mode without that
    verification raises WebhookConfigurationError at startup (fail closed),
    never silently in test mode and never live on a secret alone.

    Bozly (CFO) wiring: after an event passes Stripe signature verification
    here, it is handed to the Bozly CFO ledger as an observation via
    ``bozly_recorder`` (a ``core_platform.bozly_wiring.BozlyRecorder``).
    When none is supplied one is built lazily from the environment, but
    only if BOZLY_STRIPE_ROUTES_JSON is set; when Bozly is not configured
    the webhook settles exactly as before and the response reports
    ``bozly: {"status": "not_configured"}``. Bozly is an observation, not
    a gate: a Bozly failure never fails a verified webhook, and an
    unverified event never reaches Bozly (signature failure answers 401
    before this point).
    """
    if enabled and (not isinstance(webhook_secret, str) or not webhook_secret.startswith('whsec_')):
        raise WebhookConfigurationError("Invalid Stripe Webhook signature token configuration parameters")
    if expected_livemode and live_verified is not True:
        raise WebhookConfigurationError(
            "Live Stripe mode requires live_verified=True: live eligibility and "
            "release controls must be explicitly confirmed before live events "
            "are accepted; refusing to start in live mode unverified"
        )

    # Bozly (CFO) recorder: supplied by the caller (wsgi.py) or built
    # lazily from the environment. Construction never raises and never
    # touches the ledger when unconfigured; a missing recorder simply
    # means Bozly reports not_configured on verified events.
    if bozly_recorder is None:
        try:
            from core_platform.bozly_wiring import build_recorder_from_env
            bozly_recorder = build_recorder_from_env(db_path=bozly_db_path)
        except Exception:
            bozly_recorder = None

    def _record_bozly(event, raw_body):
        """Hand a verified event to Bozly. Best-effort, never raises."""
        if bozly_recorder is None:
            return None
        try:
            return bozly_recorder.record_verified_event(event, raw_body)
        except Exception:
            return {"available": False, "status": "ledger_unavailable"}

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

        # 2. Real-Time Size Boundary Verification Guard
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

        # stripe.Webhook.construct_event returns a stripe Event object, not a
        # dict: .get() raises AttributeError on it (stripe 15.6). Convert to
        # a plain dict once so the handlers below can use .get() throughout.
        # Found 2026-11-13 by tests/test_p1_wsgi.py: every valid signed event
        # previously crashed here and answered 500.
        if hasattr(event, "to_dict"):
            event = event.to_dict()

        # 5. Production Environment Security Bounds
        if event.get('livemode') != expected_livemode:
            return respond(start_response, '400 Bad Request', {'error': 'environment_livemode_mismatch'})

        # 6. Idempotent Ledger Synchronization Lock
        try:
            event_id = event.get('id')
            event_type = event.get('type')
            event_data_object = event.get('data', {}).get('object', {})

            if not event_id or not event_type:
                raise ValueError("Malformed event identity elements")

            with ledger_engine.connect() as db:
                # Active WAL pragma setup to optimize performance and prevent process hanging
                db.execute('PRAGMA journal_mode=WAL;')
                db.execute('PRAGMA synchronous=NORMAL;')
                
                # Immediate exclusive write lock to completely isolate ledger processing requests
                db.execute('BEGIN IMMEDIATE')

                # The processed-events table is created here, not by the
                # installer: a fresh ledger.db has no tables, and without
                # this the SELECT below fails with "no such table" and every
                # first signed webhook 500s (found 2026-11-13 by the live
                # gunicorn smoke test). Same DDL as the test helper
                # make_event_table in tests/test_p1_wsgi.py.
                db.execute(
                    'CREATE TABLE IF NOT EXISTS stripe_processed_events '
                    '(id TEXT PRIMARY KEY, type TEXT, processed_at INTEGER)'
                )

                is_duplicate = db.execute(
                    'SELECT 1 FROM stripe_processed_events WHERE id = ?', 
                    (event_id,)
                ).fetchone()
                
                if is_duplicate:
                    db.rollback()
                    # Already settled by the platform ledger; Bozly
                    # dedups itself, so a replay is offered to it too
                    # (backfills events settled before Bozly was wired).
                    # Best-effort only; the response is unchanged.
                    _record_bozly(event, raw_body)
                    return respond(start_response, '200 OK', {
                        'status': 'SUCCESS_ALREADY_PROCESSED', 
                        'event_id': event_id
                    })

                # 6a. Per-event currency validation (P3, 2026-11-13).
                # The event's own currency/amount are validated with
                # global_payments.validate_webhook_event BEFORE any ledger
                # method runs, so a currency/amount mismatch can never
                # settle silently. It applies only where the event carries
                # money fields: checkout.session.completed,
                # payment_intent.succeeded and invoice.paid carry
                # amount_total/amount_received/amount_paid + currency and
                # get the full check; charge.refunded carries
                # amount_refunded (not covered by that validator), so only
                # its currency is checked. Events with no amount and no
                # currency field (e.g. the legacy/test shape {"id": ...})
                # have nothing to validate and proceed as before; other
                # event types are recorded only and are not validated.
                # A replay (duplicate, above) keeps its earlier verdict.
                validated_currency = None
                if event_type in ('checkout.session.completed',
                                  'payment_intent.succeeded',
                                  'invoice.paid'):
                    _money_keys = ('amount_total', 'amount_paid',
                                   'amount_received', 'currency')
                    if isinstance(event_data_object, dict) and any(
                            k in event_data_object for k in _money_keys):
                        try:
                            _checked = validate_webhook_event(
                                event, expected_livemode=expected_livemode)
                            validated_currency = _checked['currency']
                        except (CurrencyError, LivePaymentDenied) as exc:
                            db.rollback()
                            logging.warning(
                                "Webhook currency/amount mismatch for %s: %s",
                                event_type, exc)
                            return respond(start_response, '400 Bad Request', {
                                'error': 'webhook_currency_or_amount_mismatch',
                                'event_type': event_type,
                            })
                elif event_type == 'charge.refunded':
                    if isinstance(event_data_object, dict) and \
                            event_data_object.get('currency') is not None:
                        try:
                            validated_currency = normalize_currency(
                                event_data_object.get('currency'))
                        except CurrencyError:
                            db.rollback()
                            return respond(start_response, '400 Bad Request', {
                                'error': 'webhook_currency_or_amount_mismatch',
                                'event_type': event_type,
                            })

                # Route to specific structural accounting logging handlers.
                # The ledger engine must provide the method for the event type;
                # since P1 (2026-11-13) PaymentLedger
                # (core_platform/stripe_payments.py) implements all three
                # as real SQLite-backed methods. If the supplied engine
                # does not provide the method, fail closed with 503: the
                # event is rejected, not silently dropped and not recorded
                # as settled.
                _dispatch = {
                    'checkout.session.completed': 'fulfill_checkout',
                    'invoice.paid': 'record_subscription_renewal',
                    'charge.refunded': 'process_reversal',
                }
                _method_name = _dispatch.get(event_type)
                if _method_name is not None:
                    _method = getattr(ledger_engine, _method_name, None)
                    if not callable(_method):
                        db.rollback()
                        return respond(start_response, '503 Service Unavailable', {
                            'error': 'ledger_method_unavailable',
                            'event_type': event_type,
                            'method': _method_name,
                        })
                    _method(event_data_object, db)
                
                # Settle transaction record globally across tracking tables
                db.execute(
                    'INSERT INTO stripe_processed_events (id, type, processed_at) VALUES (?, ?, ?)',
                    (event_id, event_type, int(time.time()))
                )
                db.commit()

            # Bozly (CFO): only now, after the platform ledger settled
            # this signature-verified event, is it handed to Bozly as an
            # observation. Bozly failures never fail the webhook.
            bozly_result = _record_bozly(event, raw_body)

            response = {
                'status': 'LEDGER_SETTLED',
                'event_id': event_id,
                'currency': validated_currency,
            }
            if bozly_result is not None:
                response['bozly'] = {'status': bozly_result.get('status')}
            return respond(start_response, '200 OK', response)

        except Exception as processing_error:
            logging.error(f"❌ Internal accounting engine processing fault: {str(processing_error)}")
            return respond(start_response, '500 Internal Server Error', {'error': 'ledger_reconciliation_failed'})

    return application


# Maximum stream-event body: matches pipeline_api (1 MiB) and the serverless
# caller's MAX_BODY. The serverless caller (serverless/sds-transaction-
# validator-fn/integrated.py) POSTs one signed event per request and requires
# a 200 response of {"status": "COMMITTED", "transaction_id": ...,
# "receipt": {"request_id": <transaction_id>, ...}}.
MAX_STREAM_BODY_BYTES = 1048576


def _stream_strict_json(raw):
    """Parse JSON rejecting duplicate keys and non-finite constants."""

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


def create_stream_app(processor=None, release_verifier=None, store=None,
                      stream_verifier=None):
    """WSGI app for POST /api/stream/transactions.

    Accepts the signed-event envelope the serverless caller sends:
    {"actor", "transaction_id", "transaction", "signature"}, where
    transaction["request_id"] == transaction_id. The transaction is committed
    idempotently through the supplied TransactionStore and processor, and the
    store receipt is returned wrapped as COMMITTED so the caller can match it
    to the event. Without a release verifier that returns True, or without a
    processor/store, the endpoint fails closed with 503, mirroring
    pipeline_api.create_pipeline_app. If a stream_verifier callable is
    supplied it must return True for the event or the request is rejected.
    """

    def respond(start_response, status_string, response_dict):
        body_bytes = json.dumps(response_dict, separators=(',', ':')).encode('utf-8')
        start_response(status_string, [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body_bytes))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff')
        ])
        return [body_bytes]

    def app(environ, start_response):
        try:
            ready = (callable(release_verifier) and release_verifier() is True)
        except Exception:
            ready = False
        if not ready:
            return respond(start_response, '503 Service Unavailable',
                           {'error': 'authority_unavailable'})
        if environ.get('PATH_INFO', '') != '/api/stream/transactions':
            return respond(start_response, '404 Not Found', {'error': 'not_found'})
        if environ.get('REQUEST_METHOD', '') != 'POST':
            return respond(start_response, '405 Method Not Allowed',
                           {'error': 'post_required'})
        if processor is None or store is None:
            return respond(start_response, '503 Service Unavailable',
                           {'error': 'processor_unavailable'})
        if environ.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
            return respond(start_response, '415 Unsupported Media Type',
                           {'error': 'json_required'})
        try:
            length = int(environ.get('CONTENT_LENGTH', '0'))
            if not 0 < length <= MAX_STREAM_BODY_BYTES:
                raise ValueError('length')
            raw = environ['wsgi.input'].read(length)
            if len(raw) != length:
                raise ValueError('short body')
            event = _stream_strict_json(raw)
            if (not isinstance(event, dict)
                    or set(event) != {'actor', 'transaction_id', 'transaction', 'signature'}
                    or not isinstance(event['actor'], str)
                    or not isinstance(event['transaction_id'], str)
                    or not isinstance(event['transaction'], dict)
                    or event['transaction'].get('request_id') != event['transaction_id']):
                raise ValueError('envelope')
        except (ValueError, TypeError, KeyError, UnicodeError):
            return respond(start_response, '400 Bad Request',
                           {'error': 'invalid_request'})
        if stream_verifier is not None:
            try:
                verified = stream_verifier(event)
            except Exception:
                verified = False
            if verified is not True:
                return respond(start_response, '401 Unauthorized',
                               {'error': 'stream_signature_unverified'})
        try:
            from .pipeline_api import TransactionRejected
            receipt = store.process(event['transaction'], event['actor'], processor)
        except TransactionRejected:
            return respond(start_response, '422 Unprocessable Entity',
                           {'error': 'transaction_rejected'})
        except Exception:
            return respond(start_response, '503 Service Unavailable',
                           {'error': 'transaction_unavailable'})
        return respond(start_response, '200 OK', {
            'status': 'COMMITTED',
            'transaction_id': event['transaction_id'],
            'receipt': receipt,
        })

    return app
