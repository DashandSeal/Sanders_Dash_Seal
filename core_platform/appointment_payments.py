"""Human-approved itemized quotes and idempotent Stripe Checkout handoff.

Development composition, not production authority. A deployment supplies an
instantiated StripeClient, independent operator/fee/case verification and audit.
Quote approval is internal only; customers cannot set prices or review authority.
"""
import json
import secrets
import string
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from .appointments import AppointmentDenied
from .stripe_payments import PaymentDenied, checkout_parameters


class AppointmentPayments:
    def __init__(self, appointments, ledger, client, operator_verifier,
                 fee_verifier, eligibility_verifier, audit, site_origin, *, clock=time.time,
                 expected_livemode=False):
        origin = urlsplit(site_origin)
        if (origin.scheme != 'https' or not origin.netloc or origin.path
                or origin.query or origin.fragment or origin.username
                or type(expected_livemode) is not bool
                or not all(callable(v) for v in
                           (operator_verifier, fee_verifier, eligibility_verifier))
                or Path(ledger.path).resolve() != Path(appointments.path).resolve()):
            raise PaymentDenied('Independent adapters and shared protected storage required')
        self.appointments, self.ledger, self.client = appointments, ledger, client
        self.operator_verifier, self.fee_verifier = operator_verifier, fee_verifier
        self.eligibility_verifier, self.audit = eligibility_verifier, audit
        self.origin, self.clock = site_origin, clock
        self.expected_livemode = expected_livemode
        with appointments.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS appointment_quotes (
                case_id TEXT PRIMARY KEY REFERENCES cases(case_id),
                quote_id TEXT NOT NULL UNIQUE, items TEXT NOT NULL,
                expires_at INTEGER NOT NULL, idempotency_key TEXT NOT NULL,
                integration_tag TEXT NOT NULL, params TEXT, attempted_at INTEGER,
                session_id TEXT, checkout_url TEXT)''')

    def approve_quote(self, case_id, actor, items, expires_at):
        """Called only by a trusted operator adapter; immutable once approved."""
        if (not isinstance(items, dict) or set(items) !=
                {'Notarial acts', 'Travel', 'Document support'}
                or any(type(v) is not int or v < 0 for v in items.values())
                or not 0 < sum(items.values()) <= 99_999_999
                or type(expires_at) is not int
                or not self.clock() < expires_at <= self.clock() + 7 * 86400):
            raise PaymentDenied('Invalid quote')
        case = self.appointments.cases.get(case_id)
        self.appointments.get(case_id, case['requester'])
        if (self.operator_verifier(actor) is not True
                or self.fee_verifier(case, actor, dict(items)) is not True):
            raise PaymentDenied('Quote approval denied')
        quote_id = 'quote-' + uuid.uuid4().hex
        # Intent evidence is distinct from a committed quote or a completed act.
        self.audit.preserve({'stage': 'QUOTE_APPROVAL_INTENT', 'case_id': case_id,
                             'quote_id': quote_id, 'actor': actor})
        with self.appointments.connect() as db:
            try:
                db.execute('INSERT INTO appointment_quotes '
                    '(case_id,quote_id,items,expires_at,idempotency_key,integration_tag) '
                    'VALUES (?,?,?,?,?,?)', (case_id, quote_id, json.dumps(items), expires_at,
                    'dash-seal-' + uuid.uuid4().hex,
                    'sanders_dash_seal_' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(8))))
            except Exception as exc:
                raise PaymentDenied('Quote not committed') from exc
        return self.quote(case_id, case['requester'])

    def quote(self, case_id, requester):
        self.appointments.get(case_id, requester)
        with self.appointments.connect() as db:
            row = db.execute('SELECT quote_id,items,expires_at FROM appointment_quotes '
                             'WHERE case_id=?', (case_id,)).fetchone()
        if not row:
            return None
        return dict(quote_id=row['quote_id'], items=json.loads(row['items']),
                    total_cents=sum(json.loads(row['items']).values()), currency='usd',
                    expires_at=row['expires_at'], expired=row['expires_at'] <= self.clock())

    def checkout(self, case_id, requester, quote_id, accept_quote):
        appointment = self.appointments.get(case_id, requester)
        if accept_quote is not True:
            raise PaymentDenied('Quote acceptance required')
        if self.eligibility_verifier(appointment, requester) is not True:
            raise PaymentDenied('Independent case eligibility required')
        with self.appointments.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM appointment_quotes WHERE case_id=?', (case_id,)).fetchone()
            if not row or row['quote_id'] != quote_id:
                raise PaymentDenied('Unknown approved quote')
            if self.ledger.status(case_id) == 'PAID':
                raise PaymentDenied('Already paid')
            if row['expires_at'] <= self.clock():
                raise PaymentDenied('Quote expired')
            if row['session_id']:
                if json.loads(row['params'])['expires_at'] <= self.clock():
                    raise PaymentDenied('Checkout expired; operator reconciliation required')
                return {'url': row['checkout_url']}
            if row['attempted_at'] is not None and self.clock() - row['attempted_at'] >= 23 * 3600:
                raise PaymentDenied('Checkout requires provider reconciliation before retry')
            items = json.loads(row['items'])
            if row['params']:
                params = json.loads(row['params'])
            else:
                params = checkout_parameters(case_id, sum(items.values()), 'usd',
                    'Sanders Dash & Seal approved service', self.origin + '/appointments',
                    self.origin + '/appointments')
                params['line_items'] = [{'price_data': {'currency': 'usd',
                    'product_data': {'name': label}, 'unit_amount': cents}, 'quantity': 1}
                    for label, cents in items.items() if cents]
                params['integration_identifier'] = row['integration_tag']
                params['metadata']['quote_id'] = quote_id
                # Session can never outlast this quote. Stripe requires >=30 minutes.
                if row['expires_at'] < self.clock() + 1800:
                    raise PaymentDenied('Quote requires renewal before Checkout')
                params['expires_at'] = min(row['expires_at'], int(self.clock()) + 86400)
                db.execute('UPDATE appointment_quotes SET params=?,attempted_at=? WHERE case_id=?',
                           (json.dumps(params), int(self.clock()), case_id))
            idempotency_key = row['idempotency_key']
        # Persist exact params and retry key before the network call. Do not hold a DB lock.
        self.audit.preserve({'stage': 'CHECKOUT_INTENT', 'case_id': case_id, 'quote_id': quote_id})
        try:
            session = self.client.v1.checkout.sessions.create(params,
                options={'idempotency_key': idempotency_key})
            sid, url = session['id'], session['url']
            parsed = urlsplit(url)
            if (not isinstance(sid, str) or not sid.startswith('cs_')
                    or parsed.scheme != 'https' or parsed.netloc != 'checkout.stripe.com'
                    or session['client_reference_id'] != case_id
                    or session.get('livemode') is not self.expected_livemode
                    or type(session['amount_total']) is not int
                    or session['amount_total'] != sum(items.values())
                    or session['currency'] != 'usd' or session['mode'] != 'payment'):
                raise PaymentDenied('Checkout response mismatch')
        except Exception as exc:
            raise PaymentDenied('Checkout unavailable; retry preserves the same request') from exc
        with self.appointments.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT session_id,checkout_url FROM appointment_quotes WHERE case_id=?',
                                 (case_id,)).fetchone()
            if current['session_id']:
                if current['session_id'] != sid:
                    raise PaymentDenied('Provider idempotency mismatch')
                return {'url': current['checkout_url']}
            self.ledger.register_checkout(case_id, sid, sum(items.values()), 'usd', connection=db)
            db.execute('UPDATE appointment_quotes SET session_id=?,checkout_url=? WHERE case_id=?',
                       (sid, url, case_id))
        return {'url': url}
