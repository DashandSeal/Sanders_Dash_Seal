"""Fail-closed Stripe webhook ingress for Sanders Dash & Seal.

Verifies signed Stripe events before recording payment state.
Payment confirmation does not authorize or execute a notarial act.
"""
import os
from core_platform.stripe_payments import PaymentDenied, PaymentLedger, verify_stripe_webhook

MAX_BODY = 65536

def make_app(ledger, signing_secret, *, enabled=False, expected_livemode=None):
    """Return a narrow WSGI endpoint; caller must supply protected secret and ledger."""
    def app(environ, start_response):
        def respond(code, message):
            data = message.encode('ascii')
            start_response(code, [('Content-Type', 'text/plain; charset=us-ascii'),
                                  ('Content-Length', str(len(data))),
                                  ('Cache-Control', 'no-store')])
            return [data]
        if not enabled:
            return respond('503 Service Unavailable', 'Payment webhook is not configured')
        if environ.get('PATH_INFO') != '/stripe/webhook':
            return respond('404 Not Found', 'Not found')
        if environ.get('REQUEST_METHOD') != 'POST':
            return respond('405 Method Not Allowed', 'Method not allowed')
        if environ.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
            return respond('415 Unsupported Media Type', 'JSON required')
        try:
            n = int(environ.get('CONTENT_LENGTH', '-1'))
        except (ValueError, TypeError):
            return respond('400 Bad Request', 'Invalid length')
        if not 0 < n <= MAX_BODY:
            return respond('413 Content Too Large', 'Invalid body size')
        body = environ['wsgi.input'].read(n)
        if len(body) != n:
            return respond('400 Bad Request', 'Incomplete body')
        try:
            event = verify_stripe_webhook(body, environ.get('HTTP_STRIPE_SIGNATURE'),
                                          signing_secret)
            if expected_livemode is not None and event.get("livemode") is not expected_livemode:
                raise PaymentDenied("Payment environment mismatch")
            ledger.record_event(event)
        except PaymentDenied:
            return respond('400 Bad Request', 'Rejected')
        except Exception:
            # Storage or infrastructure failure: Stripe retries; never acknowledge.
            return respond('503 Service Unavailable', 'Processing unavailable')
        return respond('200 OK', 'Accepted')
    return app

def application(environ, start_response):
    """Deployment default is DENY, even when environment secrets exist."""
    return make_app(None, None, enabled=False)(environ, start_response)
