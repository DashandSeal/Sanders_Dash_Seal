"""
Module: core_platform.native_runtime
Architectural Layer: Core Platform Service Gateway
Description: Enterprise WSGI routing matrix for the Sanders Dash & Seal engine.
             Provides cryptographic request validation, secure session token mapping,
             zero-copy streaming, and microservice handoffs while eliminating syntactical bugs.
"""

import ast
import hashlib
import io
import json
import os
import pathlib
import re
import sqlite3
import sys
from datetime import datetime

# Import secure providers and state workflows
from provider_connections import import_write_provider_client
from provider_workflows import ImportProviderWorkflows, ProviderUnavailable, ProviderRequestConflict
from cases import import_case_denied
from accounts import import_account_store, auth_app
from appointments import import_appointment_store
from appointment_payments import import_appointment_payments
from native_notary import import_native_notary, NativeNotarySessions, NativeNotaryDenied
from native_evidence import import_native_evidence_index, EvidenceDenied
from native_documents import import_native_documents, DocumentDenied
from native_journal import import_native_journal, JournalDenied
from native_signatures import import_native_signatures, SignatureDenied
from native_ron_rooms import import_native_ron_rooms, RoomDenied
from native_authority import import_native_authority, AuthorityDenied
from native_seals import import_native_seals, SealDenied
from cases import import_case_registry
from deployment import RuntimeBindings, create_application, ORIGIN, _response
from glass_box_audit import import_glass_box_audit
from pipeline_api import import_transaction_store, TransactionRejected, create_pipeline_app
from stripe_payments import import_payment_ledger, PaymentDenied
from stripe_webhook_wsgi import import_make_app
from stream_api import import_strict_json
from upgrade_sidecar import import_core_laws
from operational_runtime import import_operational_runtime
from tech_team_dispatch import import_tech_team_dispatcher
from backend.auth_session import import_validate_worker_token_request, issue_webrtc_access_token

class UnconfiguredStripeClient:
    def __getattr__(self, name):
        raise PaymentDenied("Stripe credentials unavailable")

def read_settings(path):
    path_str = str(path)
    if not path.exists():
        return {}
    info = path.stat()
    if path.is_symlink() or info.st_uid != os.getuid() or (info.st_mode & 0o0077) != 0 or info.st_size > 16384:
        raise ValueError("Runtime secret configuration must be root-owned, private, and bounded")
    
    settings_data = json.loads(path.read_text())
    if not isinstance(settings_data, dict) or set(settings_data.keys()) - {
        'owner_setup_digest', 'owner_setup_expires', 'stripe_api_key', 'stripe_webhook_secret', 'stripe_livemode',
        'signwell_api_key', 'signwell_test_mode', 'bluenotary_api_key', 'bluenotary_test_mode'
    }:
        raise ValueError("Invalid runtime configuration fields detected")
    return settings_data

class NativeRuntime:
    def __init__(self, path, settings=None, stripe_client=None):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.umask(0o0077)
        os.chmod(self.path.parent, 0o0700)
        
        settings = settings if settings is not None else read_settings(self.path)
        self.accounts = import_account_store(path, setup_digest=settings.get('owner_setup_digest'), setup_expires=settings.get('owner_setup_expires', 0))
        self.audit = import_glass_box_audit(path) if hasattr(sys, 'sds_audit') else None
        self.operations = import_operational_runtime(path)
        self.technical_tasks = import_tech_team_dispatcher(path, core_laws=None, audit=self.audit)
        self.cases = import_case_registry(path, core_laws=None)
        self.native_sessions = import_native_notary_sessions(path)
        self.native_evidence = import_native_evidence_index(path)
        self.native_documents = import_native_documents(path, path.with_name('native_documents'))
        self.native_journal = import_native_journal(path)
        self.native_signatures = import_native_signatures(path, core_laws=None)
        self.native_ron_rooms = import_native_ron_rooms(path)
        self.native_authority = import_native_authority(path)
        self.native_seals = import_native_seals(path)
        self.appointments = import_appointment_store(self.cases, self.audit)
        self.ledger = import_payment_ledger(path)
        self.store = import_transaction_store(path)
        
        with self.store.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sds_ingestion_events (
                    actor TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    payload_text TEXT NOT NULL,
                    sha256_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY(actor, request_id)
                );
            """)
            
        livemode_settings = settings.get('stripe_livemode', True)
        if type(livemode_settings) is not bool:
            raise ValueError("Explicit Stripe livemode environment parameter must be a boolean flag")
        
        key = settings.get('stripe_api_key')
        secret = settings.get('stripe_webhook_secret')
        if key:
            prefix = 'rk_live_' if livemode_settings else 'rk_test_'
            if not isinstance(key, str) or not key.startswith(prefix):
                raise ValueError("Stripe API key format mismatch for target livemode boundary configuration")
            if secret and (not isinstance(secret, str) or not secret.startswith('whsec_')):
                raise ValueError("Invalid Stripe Webhook secret signature token configuration parameters")
                
            if key and stripe_client is None:
                import stripe
                stripe_client = stripe.StripeClient(key, stripe_version="2024-06-24.dahlia", max_network_retries=2)
                
        if type(settings.get('signwell_test_mode', False)) is not bool:
            raise ValueError("SignWell test mode flag configuration must be specified as a boolean parameter")
            
        clients = {}
        for provider in ('signwell', 'bluenotary'):
            if settings.get(f'{provider}_api_key'):
                clients[provider] = import_write_provider_client(provider, settings[f'{provider}_api_key'])
                
        self.providers = import_provider_workflows(path, self.cases, self.accounts, operator=self.audit, clients=clients,
                                                   signwell_test_mode=settings.get('signwell_test_mode', False))
                                                   
        self.self_payments_configured = bool(key and secret)
        
        # Deploy non-privileged dummy or functional stripe clients based on active configuration variables
        client = stripe_client if stripe_client is not None else UnconfiguredStripeClient()
        self.appointments = import_appointment_payments(self.appointments, self.ledger, client,
                                                         self.accounts, self.operations, self.technical_tasks,
                                                         expected_livemode=livemode_settings)
                                                         
        self.webhook = import_make_app(self.ledger, secret, enabled=bool(secret), expected_livemode=livemode_settings)
        self.bindings = RuntimeBindings(self.appointments, self.payments, self.accounts, self.operations,
                                        auth_app(self.accounts, ORIGIN), self.available, self.webhook, self.process_event, self.store)
        self.base = create_application(self.bindings)
        self.pipeline = create_pipeline_app(self.accounts, self.operations, self.technical_tasks, self.available, self.store)

    def available(self):
        try:
            self.audit.verify_audit()
            with self.store.connect() as db:
                return db.execute("PRAGMA quick_check;").fetchone()[0] == "ok"
        except Exception:
            return False

    def fee_review(self, case, actor, items):
        if not self.accounts.operator(actor):
            return False
        self.audit.preserve('stage', 'HUMAN_ITEMIZED_QUOTE_REVIEW', 'case_id', case['case_id'],
                           'actor', actor, 'items_sha256', hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest())
        return True

    def checkout(self, appointment, requester):
        self.appointments.get(appointment['case_id'], requester)
        with self.appointments.connect() as db:
            row = db.execute("SELECT 1 FROM appointment_quotes WHERE case_id=?;", (appointment['case_id'],)).fetchone()
        return bool(row)

    def process_event(self, transaction, actor, db):
        if not isinstance(transaction, dict) or not isinstance(transaction.get('payload'), dict):
            raise TransactionRejected("Only authenticated ingestion is available through this transport channel")
        raw_json = json.dumps(transaction['payload'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        if len(raw_json.encode()) >= 65536:
            raise TransactionRejected("Payload size limit exceeded for standard ledger injection")
            
        checksum = hashlib.sha256(raw_json.encode()).hexdigest()
        db.execute("INSERT INTO sds_ingestion_events VALUES (?, ?, ?, ?, ?);",
                   (actor, transaction['request_id'], raw_json, checksum, 'RECEIVED'))
        return {'status': 'RECEIVED', 'sha256_digest': checksum, 'notarial_action_executed': False}

    def status(self):
        return {
            'platform': 'Sanders Dash & Seal',
            'accounts': True,
            'appointment_intake': True,
            'operator_quotes': True,
            'durable_ingestion': True,
