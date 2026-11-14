"""Bozly authenticated global human collaboration and WebRTC signaling API.

Media is direct encrypted WebRTC media between browsers, not handled by
this WSGI signaling server. TURN/STUN, consent, permissions and global reach
depend on live infrastructure configuration.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

import jwt
from cryptography.fernet import Fernet, InvalidToken
import bozly_operations as ops
import bozly_purchasing as purchasing
import bozly_global_transactions as global_finance
import bozly_diversion_guard as diversion_guard
import bozly_legal_intelligence as legal_intelligence
import bozly_financial_ethics as ethics
import bozly_forensic_accounting as forensic
import bozly_claim_integrity as claims
import bozly_multimodal_integrity as multimodal
import bozly_native_cfo as native_cfo
import bozly_native_broker as native_broker
import bozly_native_investment_intelligence as investments
import bozly_wizardry_engine as wizardry
import bozly_market_ingestor as market_news
import bozly_onboarding as onboarding
import bozly_forensic_dashboard as forensic_dashboard
import bozly_native_backup as native_backup

ISSUER = os.getenv("BOZLY_OIDC_ISSUER", "")
AUDIENCE = os.getenv("BOZLY_OIDC_AUDIENCE", "")
JWKS_PEM_FILE = os.getenv("BOZLY_OIDC_PUBLIC_KEY_FILE", "")
FERNET_KEY = os.getenv("BOZLY_SIGNAL_FERNET_KEY", "")
MAX_BODY = 131072
READONLY_ROLE = "bozly:view"
OPERATOR_ROLE = "bozly:operate"
ADMIN_ROLE = "bozly:manage"


def identity(environ):
    if not (ISSUER and AUDIENCE and JWKS_PEM_FILE):
        raise PermissionError("OIDC identity not configured")
    token = environ.get("HTTP_AUTHORIZATION", "")
    if not token.startswith("Bearer "):
        raise PermissionError("Bearer identity token required")
    with open(JWKS_PEM_FILE, "rb") as f:
        key = f.read(65537)
    if len(key) > 65536:
        raise PermissionError("OIDC key invalid")
    claims = jwt.decode(token[7:], key=key, algorithms=["RS256"],
                        issuer=ISSUER, audience=AUDIENCE,
                        options={"require":["exp","iat","sub","iss","aud"]},
                        leeway=30)
    subject = claims["sub"]
    if not isinstance(subject,str) or len(subject)<1 or len(subject)>256:
        raise PermissionError("Invalid subject")
    # Role and authorized-entity assertions are signed by the configured issuer.
    roles = claims.get("bozly_roles", [])
    entities = claims.get("bozly_entities", [])
    if not isinstance(roles,list) or not isinstance(entities,list):
        raise PermissionError("Invalid identity grants")
    return {"sub":subject,"roles":frozenset(x for x in roles if isinstance(x,str)),
            "entities":frozenset(x for x in entities if isinstance(x,str))}


def require_access(actor, entity, needed):
    if not entity or entity not in actor["entities"]:
        raise PermissionError("No access to legal entity")
    if needed == "view":
        ok = bool(actor["roles"] & {READONLY_ROLE, OPERATOR_ROLE, ADMIN_ROLE})
    elif needed == "operate":
        ok = bool(actor["roles"] & {OPERATOR_ROLE, ADMIN_ROLE})
    else:
        ok = ADMIN_ROLE in actor["roles"]
    if not ok:
        raise PermissionError("Role does not permit this action")


def _db():
    path = Path(os.getenv("BOZLY_CONTROL_DB", "/app/secure_ledgers/bozly_controls.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS call_rooms(
      room_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,
      host_subject TEXT NOT NULL,guest_subject TEXT NOT NULL,
      created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS call_signals(
      signal_id INTEGER PRIMARY KEY AUTOINCREMENT,room_id TEXT NOT NULL,
      sender TEXT NOT NULL,recipient TEXT NOT NULL,
      payload_ciphertext BLOB NOT NULL,created_at INTEGER NOT NULL,
      FOREIGN KEY(room_id) REFERENCES call_rooms(room_id)
    );
    """)
    return db


def _cipher():
    if not FERNET_KEY:
        raise RuntimeError("Encrypted signaling key not provisioned")
    return Fernet(FERNET_KEY.encode("ascii"))


def _room_access(db, room, actor, entity):
    row = db.execute(
        """SELECT host_subject,guest_subject,expires_at FROM call_rooms
           WHERE room_id=? AND entity_id=?""",(room,entity)).fetchone()
    if not row or row[2]<int(time.time()) or actor["sub"] not in row[:2]:
        raise PermissionError("Unknown, expired or unauthorized call room")
    return row


def _respond(start, code, obj):
    codes={200:"200 OK",201:"201 Created",400:"400 Bad Request",
           401:"401 Unauthorized",403:"403 Forbidden",404:"404 Not Found",
           413:"413 Content Too Large",503:"503 Service Unavailable"}
    data=json.dumps(obj,separators=(",",":")).encode()
    start(codes[code],[
        ("Content-Type","application/json"),
        ("Content-Length",str(len(data))),
        ("Cache-Control","no-store"),
        ("X-Content-Type-Options","nosniff"),
        ("Access-Control-Allow-Origin","null"),
    ])
    return [data]


def application(environ,start_response):
    try:
        actor=identity(environ)
    except (PermissionError,jwt.PyJWTError,OSError,ValueError):
        return _respond(start_response,401,{"error":"IDENTITY_UNAVAILABLE"})
    if environ.get("CONTENT_TYPE","").split(";")[0].strip() not in (
        "application/json","") and environ.get("REQUEST_METHOD")=="POST":
        return _respond(start_response,400,{"error":"JSON_REQUIRED"})
    method=environ.get("REQUEST_METHOD","")
    path=environ.get("PATH_INFO","")
    if not path.startswith("/bozly/v1/"):
        return _respond(start_response,404,{"error":"UNKNOWN_PATH"})
    if method not in {"POST","GET"}:
        return _respond(start_response,404,{"error":"UNSUPPORTED_METHOD"})
    length=int(environ.get("CONTENT_LENGTH","0") or "0")
    if length<0 or length>MAX_BODY:
        return _respond(start_response,413,{"error":"INVALID_SIZE"})
    if method=="POST" and not (0 < length <= MAX_BODY):
        return _respond(start_response,400,{"error":"BODY_REQUIRED"})
    try:
        data=json.loads(environ["wsgi.input"].read(length)) if method=="POST" else {}
        if not isinstance(data,dict):
            raise ValueError()
        entity=data.get("entity_id") if method=="POST" else environ.get("QUERY_STRING","").removeprefix("entity_id=")
        if not isinstance(entity,str) or len(entity)>180:
            raise ValueError()
        action=path.removeprefix("/bozly/v1/")
        # Owner-native CFO accounting, planning and investment books.
        # Existing entity-scoped authentication applies; no new approval chain.
        if method=="POST" and action=="cfo-account-register":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_cfo.register_account(
                entity_id=entity,currency=data["currency"],code=data["code"],
                name=data["name"],kind=data["kind"]))
        if method=="POST" and action=="cfo-journal-post":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_cfo.post_journal(
                entity_id=entity,currency=data["currency"],
                journal_id=data["journal_id"],posting_date=data["posting_date"],
                source_reference=data["source_reference"],
                source_sha256=data["source_sha256"],
                explanation=data["explanation"],actor=actor["sub"],
                lines=data["lines"]))
        if method=="POST" and action=="cfo-trial-balance":
            require_access(actor,entity,"view")
            return _respond(start_response,200,native_cfo.trial_balance(
                entity_id=entity,currency=data["currency"],
                through_date=data.get("through_date")))
        if method=="POST" and action=="cfo-statements":
            require_access(actor,entity,"view")
            return _respond(start_response,200,native_cfo.financial_statements(
                entity_id=entity,currency=data["currency"],
                through_date=data.get("through_date")))
        if method=="POST" and action=="cfo-budget-set":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_cfo.set_budget(
                entity_id=entity,currency=data["currency"],month=data["month"],
                code=data["code"],planned_net_minor=data["planned_net_minor"],
                source_reference=data["source_reference"],actor=actor["sub"]))
        if method=="POST" and action=="cfo-budget-variance":
            require_access(actor,entity,"view")
            return _respond(start_response,200,native_cfo.budget_variance(
                entity_id=entity,currency=data["currency"],month=data["month"]))
        if method=="POST" and action=="cfo-cash-plan-set":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_cfo.set_cash_plan(
                entity_id=entity,currency=data["currency"],month=data["month"],
                opening_cash_minor=data["opening_cash_minor"],
                projected_inflows_minor=data["projected_inflows_minor"],
                projected_outflows_minor=data["projected_outflows_minor"],
                source_reference=data["source_reference"],actor=actor["sub"]))
        if method=="POST" and action=="cfo-cash-plan":
            require_access(actor,entity,"view")
            return _respond(start_response,200,native_cfo.cash_plan(
                entity_id=entity,currency=data["currency"],month=data["month"]))
        if method=="POST" and action=="broker-account-register":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_broker.register_account(
                account_id=data["account_id"],entity_id=entity,
                currency=data["currency"],
                account_reference=data["account_reference"]))
        if method=="POST" and action=="broker-market-quote":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_broker.record_market_price(
                quote_id=data["quote_id"],venue_mic=data["venue_mic"],
                symbol=data["symbol"],currency=data["currency"],
                price_minor=data["price_minor"],
                observed_unix=data["observed_unix"],
                source_reference=data["source_reference"],
                source_sha256=data["source_sha256"]))
        if method=="POST" and action=="broker-cash-record":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_broker.record_cash_movement(
                entity_id=entity,account_id=data["account_id"],
                event_id=data["event_id"],direction=data["direction"],
                amount_minor=data["amount_minor"],
                source_reference=data["source_reference"],
                source_sha256=data["source_sha256"],
                event_kind=data["event_kind"],actor=actor["sub"]))
        if method=="POST" and action=="broker-limit-order":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_broker.create_limit_order(
                entity_id=entity,account_id=data["account_id"],
                order_id=data["order_id"],venue_mic=data["venue_mic"],
                symbol=data["symbol"],side=data["side"],
                quantity_micro=data["quantity_micro"],
                limit_price_minor=data["limit_price_minor"],
                trade_reason=data["trade_reason"],actor=actor["sub"]))
        if method=="POST" and action=="broker-record-execution":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,native_broker.record_execution(
                entity_id=entity,order_id=data["order_id"],
                execution_id=data["execution_id"],
                venue_mic=data["venue_mic"],
                executed_micro=data["executed_micro"],
                executed_price_minor=data["executed_price_minor"],
                fee_minor=data["fee_minor"],
                executed_at_unix=data["executed_at_unix"],
                source_sha256=data["source_sha256"]))
        if method=="POST" and action=="broker-cancel-request":
            require_access(actor,entity,"operate")
            return _respond(start_response,200,native_broker.request_cancel(
                entity_id=entity,order_id=data["order_id"],actor=actor["sub"]))
        if method=="POST" and action=="broker-confirm-cancel":
            require_access(actor,entity,"operate")
            return _respond(start_response,200,native_broker.confirm_cancel(
                entity_id=entity,order_id=data["order_id"],
                source_sha256=data["source_sha256"]))
        if method=="POST" and action=="broker-portfolio":
            require_access(actor,entity,"view")
            return _respond(start_response,200,native_broker.portfolio(
                entity_id=entity,account_id=data["account_id"]))
        if method=="POST" and action=="investment-policy-set":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,investments.set_policy(
                entity_id=entity,account_id=data["account_id"],
                currency=data["currency"],
                minimum_liquidity_minor=data["minimum_liquidity_minor"],
                maximum_single_holding_bps=data["maximum_single_holding_bps"],
                maximum_equity_exposure_bps=data["maximum_equity_exposure_bps"],
                rebalance_threshold_bps=data["rebalance_threshold_bps"],
                thesis=data["thesis"],actor=actor["sub"]))
        if method=="POST" and action=="investment-portfolio-analyze":
            require_access(actor,entity,"view")
            return _respond(start_response,200,investments.portfolio_analysis(
                entity_id=entity,account_id=data["account_id"]))
        if method=="POST" and action=="investment-scenario-project":
            require_access(actor,entity,"view")
            return _respond(start_response,200,investments.compound_projection(
                starting_minor=data["starting_minor"],
                monthly_contribution_minor=data["monthly_contribution_minor"],
                months=data["months"],
                annual_return_percent=data["annual_return_percent"]))
        if method=="POST" and action=="wizard-allocation":
            require_access(actor,entity,"view")
            model=wizardry.BozlyWizardryEngine(
                global_benchmark_yields=data.get("benchmark_yields"),
                aggressive_allocations=data.get("aggressive_allocations"))
            return _respond(start_response,200,model.model_global_equity_allocation(
                data["capital_pool_usd"],data["profile_key"]))
        if method=="POST" and action=="wizard-accumulation":
            require_access(actor,entity,"view")
            return _respond(start_response,200,wizardry.BozlyWizardryEngine(
                ).model_capital_accumulation(
                    data["initial_usd"],data["monthly_addition_usd"],
                    data["years"],data["annual_rate"]))
        if method=="POST" and action=="wizard-debt-retirement":
            require_access(actor,entity,"view")
            return _respond(start_response,200,wizardry.BozlyWizardryEngine(
                ).model_debt_acceleration(
                    data["principal_usd"],data["annual_interest_rate"],
                    data["monthly_payment_usd"],
                    data.get("extra_payment_usd","0")))
        if method=="POST" and action=="market-news-ingest":
            require_access(actor,entity,"operate")
            return _respond(start_response,200,market_news.BozlyMarketIngestor(
                ).fetch_and_analyze_feed(data["feed_name"],entity))
        if method=="POST" and action=="client-license-create":
            require_access(actor,entity,"manage")
            return _respond(start_response,201,onboarding.BozlyOnboardingEngine(
                ).provision_new_client(
                    entity_id=entity,
                    contact_reference=data["contact_reference"],
                    license_name=data["license_name"],actor=actor["sub"],
                    expires_at=data.get("expires_at")))
        if method=="POST" and action=="client-license-revoke":
            require_access(actor,entity,"manage")
            return _respond(start_response,200,onboarding.BozlyOnboardingEngine(
                ).revoke(entity_id=entity,client_id=data["client_id"],
                         actor=actor["sub"]))
        if method=="POST" and action=="forensic-dashboard":
            require_access(actor,entity,"view")
            return _respond(start_response,200,forensic_dashboard.forensic_snapshot(
                entity_id=entity,limit=data.get("limit",100)))
        if method=="POST" and action=="cfo-online-backup":
            require_access(actor,entity,"manage")
            # Multi-LLC physical backup cannot be safely scoped to one entity;
            # no backup is exposed through an entity-scoped HTTP endpoint.
            return _respond(start_response,403,{
                "error":"BACKUP_REQUIRES_LOCAL_OPERATOR_CONTEXT",
                "detail":"Use the native local Bozly backup service on the host"})
        if method=="POST" and action=="multimodal-integrity":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,multimodal.assess_interaction(
                entity_id=entity,
                session_reference=data["session_reference"],
                subject_reference=data["subject_reference"],
                capture_source=data["capture_source"],
                capture_time_unix=data["capture_time_unix"],
                observed_by=actor["sub"],
                measurement_values=data.get("measurement_values"),
                baseline_values=data.get("baseline_values"),
                wav_pcm16_base64=data.get("wav_pcm16_base64"),
                transcript=data.get("transcript"),
                financial_claim=data.get("financial_claim"),
            ))
        if method=="POST" and action=="claim-integrity":
            require_access(actor,entity,"operate")
            result=claims.assess_documented_claim(
                entity_id=entity,record_type=data["record_type"],
                record_id=data["record_id"],claimed_field=data["claimed_field"],
                claimed_value=data["claimed_value"],requested_by=actor["sub"])
            return _respond(start_response,200,result)
        if method=="POST" and action=="forensic-open-case":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,forensic.open_case(
                entity_id=entity,title=data["title"],scope=data["scope"],
                opened_by=actor["sub"],case_id=data.get("case_id"),
            ))
        if method=="POST" and action=="forensic-attach-evidence":
            require_access(actor,entity,"operate")
            with forensic._db() as fdb:
                if forensic._entity(fdb,data["case_id"])!=entity:
                    raise PermissionError("Case is outside authenticated LLC")
            return _respond(start_response,201,forensic.attach_evidence(
                case_id=data["case_id"],evidence_id=data["evidence_id"],
                evidence_type=data["evidence_type"],
                source_reference=data["source_reference"],
                source_sha256=data["source_sha256"],
                collected_by=actor["sub"],
            ))
        if method=="POST" and action=="forensic-investigate":
            require_access(actor,entity,"operate")
            return _respond(start_response,200,forensic.investigate(
                case_id=data["case_id"],entity_id=entity,
            ))
        if method=="POST" and action=="ethics-principles":
            require_access(actor,entity,"view")
            return _respond(start_response,200,ethics.ethical_operating_principles())
        if method=="POST" and action=="ethics-cases":
            require_access(actor,entity,"view")
            return _respond(start_response,200,ethics.list_cases(
                entity_id=entity,topic=data.get("topic"),limit=data.get("limit",100)
            ))
        if method=="POST" and action=="ethics-record-concern":
            require_access(actor,entity,"operate")
            result=ethics.record_concern(
                entity_id=entity,topic=data["topic"],concern=data["concern"],
                subject_reference=data["subject_reference"],
                described_observation=data["described_observation"],
                source_record_sha256=data["source_record_sha256"],
                business_effect=data["business_effect"],
                request_actor=actor["sub"],
                exact_amount_minor=data.get("exact_amount_minor"),
                currency=data.get("currency"),
            )
            # Only authenticated, evidence-grounded financial diversion or
            # concealment incidents reach the established executive P0 path.
            if data["concern"] in ethics.SERIOUS:
                category=(
                    "unauthorized_money_diversion"
                    if data["concern"]=="unauthorized_asset_diversion"
                    else "suppressed_financial_notification"
                )
                incident=diversion_guard.report_diversion_attempt(
                    entity_id=entity,category=category,
                    subject_id=data["subject_reference"],
                    request_actor=actor["sub"],
                    evidence_sha256=data["source_record_sha256"],
                    incident_id="ethics_"+result["case_id"],
                )
                result["diversion_incident"]=incident
            return _respond(start_response,201,result)
        if method=="POST" and action=="ethics-record-screening":
            require_access(actor,entity,"operate")
            return _respond(start_response,201,ethics.record_screening_observation(
                case_id=data["case_id"],entity_id=entity,
                screening_source=data["screening_source"],
                screening_list_version=data["screening_list_version"],
                checked_at=data["checked_at"],outcome=data["outcome"],
                result_evidence_sha256=data["result_evidence_sha256"],
            ))
        if method=="POST" and action=="ethics-update-case":
            require_access(actor,entity,"operate")
            return _respond(start_response,200,ethics.resolve_case(
                case_id=data["case_id"],entity_id=entity,
                status=data["status"],conclusion=data["conclusion"],
                actor=actor["sub"],
            ))
        if method=="POST" and action=="legal-sources":
            require_access(actor,entity,"view")
            legal_intelligence.seed_authorities()
            return _respond(start_response,200,{
                "entity_id":entity,
                "sources":legal_intelligence.source_status(
                    jurisdiction=data.get("jurisdiction"),
                    topic=data.get("topic")
                ),
                "disclaimer":"Source dates and digests do not prove legal completeness or applicability."
            })
        if method=="POST" and action=="legal-source-refresh":
            require_access(actor,entity,"operate")
            legal_intelligence.seed_authorities()
            source_id=data["source_id"]
            if not isinstance(source_id,str) or len(source_id)>180:
                raise ValueError("Invalid official source ID")
            return _respond(start_response,200,
                legal_intelligence.refresh_source(source_id))
        if method=="POST" and action=="diversion-incident":
            require_access(actor,entity,"operate")
            result=diversion_guard.report_diversion_attempt(
                entity_id=entity,
                category=data["category"],
                subject_id=data["subject_id"],
                request_actor=actor["sub"],
                evidence_sha256=data["evidence_sha256"],
                incident_id=data.get("incident_id"),
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="diversion-notification-status":
            require_access(actor,entity,"view")
            incident_id=data["incident_id"]
            with ops._db() as db:
                diversion_guard._setup(db)
                incident=db.execute(
                    "SELECT entity_id FROM bozly_diversion_incidents WHERE incident_id=?",
                    (incident_id,)
                ).fetchone()
                if not incident or incident[0]!=entity:
                    raise PermissionError("Incident belongs to another entity")
                deliveries=db.execute(
                    """SELECT role,recipient_id,status,attempts,last_attempt_at,
                    delivered_at FROM bozly_diversion_deliveries WHERE incident_id=?
                    ORDER BY role,recipient_id""",(incident_id,)
                ).fetchall()
            return _respond(start_response,200,{
                "incident_id":incident_id,
                "delivery_status":[{
                    "role":role,"recipient_id":rid,"status":status,
                    "attempts":attempts,"last_attempt_at":last_at,
                    "delivered_at":delivered,
                } for role,rid,status,attempts,last_at,delivered in deliveries],
            })
        if method=="POST" and action=="global-transaction-quote":
            require_access(actor,entity,"operate")
            if data.get("paying_entity")!=entity:
                raise PermissionError("Paying LLC must match authorized entity")
            result=global_finance.prepare_global_transaction(
                transaction_id=data["transaction_id"],
                paying_entity=entity,
                recipient_reference=data["recipient_reference"],
                recipient_country=data["recipient_country"],
                purpose=data["purpose"],
                necessity_evidence=data["necessity_evidence"],
                source_currency=data["source_currency"],
                source_minor=data["source_minor"],
                source_exponent=data["source_exponent"],
                destination_currency=data["destination_currency"],
                destination_minor=data["destination_minor"],
                destination_exponent=data["destination_exponent"],
                fx_rate_decimal=data["fx_rate_decimal"],
                fx_quote_reference=data["fx_quote_reference"],
                fx_provider_reference=data["fx_provider_reference"],
                quote_expires_utc=data["quote_expires_utc"],
                quoted_fees_source_minor=data["quoted_fees_source_minor"],
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="global-transaction-authorize":
            require_access(actor,entity,"manage")
            ceo=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo or actor["sub"]!=ceo:
                raise PermissionError("CEO authorization required")
            with global_finance._open() as financial_db:
                found=financial_db.execute(
                    "SELECT paying_entity FROM bozly_global_transactions WHERE transaction_id=?",
                    (data["transaction_id"],)
                ).fetchone()
            if not found or found[0]!=entity:
                raise PermissionError("Global transaction belongs to another entity")
            result=global_finance.authorize_global_transaction(
                transaction_id=data["transaction_id"],
                ceo_subject=actor["sub"],
                transaction_digest=data["transaction_digest"],
            )
            return _respond(start_response,200,result)
        if method=="POST" and action=="global-transaction-submit":
            require_access(actor,entity,"manage")
            ceo=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo or actor["sub"]!=ceo:
                raise PermissionError("Actual CEO identity required for transfer initiation")
            with global_finance._open() as financial_db:
                found=financial_db.execute(
                    "SELECT paying_entity FROM bozly_global_transactions WHERE transaction_id=?",
                    (data["transaction_id"],)
                ).fetchone()
            if not found or found[0]!=entity:
                raise PermissionError("Transaction belongs to another LLC")
            result=global_finance.submit_global_transaction(data["transaction_id"])
            return _respond(start_response,200,result)
        if method=="POST" and action=="global-transaction-summary":
            require_access(actor,entity,"view")
            return _respond(start_response,200,{
                "entity_id":entity,
                "transactions":global_finance.global_transaction_summary(entity),
                "status":"recorded_transactions_only_not_live_bank_settlement",
            })
        if method=="POST" and action=="purchase":
            require_access(actor,entity,"operate")
            if data.get("paying_entity")!=entity:
                raise PermissionError("Paying entity must match authenticated entity scope")
            result=purchasing.create_purchase(
                order_id=data["order_id"],
                paying_entity=entity,
                merchant_id=data["merchant_id"],
                merchant_invoice=data["merchant_invoice"],
                description=data["description"],
                category=data["category"],
                necessity_reason=data["necessity_reason"],
                evidence_reference=data["evidence_reference"],
                amount_minor=data["amount_minor"],
                currency=data["currency"],
                destination_token=data["destination_token"],
                line_items=data["line_items"],
                beneficiary_allocations_minor=data["beneficiary_allocations_minor"],
                creator_subject=actor["sub"],
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="purchase-ceo-authorize":
            require_access(actor,entity,"manage")
            ceo_id=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo_id or actor["sub"]!=ceo_id:
                raise PermissionError("CEO identity required for purchasing authorization")
            order_id=data["order_id"]
            with purchasing._db() as order_db:
                existing=purchasing._order_row(order_db,order_id)
            if existing[0]!=entity:
                raise PermissionError("Purchase belongs to another legal entity")
            result=purchasing.ceo_authorize_purchase(
                order_id=order_id,ceo_subject=actor["sub"],
                authorized_purchase_digest=data["authorized_purchase_digest"],
            )
            return _respond(start_response,200,result)
        if method=="POST" and action=="purchase-submit":
            require_access(actor,entity,"manage")
            ceo_id=os.environ.get("BOZLY_CEO_SUBJECT","")
            if not ceo_id or actor["sub"]!=ceo_id:
                raise PermissionError("CEO identity required for purchase submission")
            order_id=data["order_id"]
            with purchasing._db() as order_db:
                existing=purchasing._order_row(order_db,order_id)
            if existing[0]!=entity:
                raise PermissionError("Purchase belongs to another legal entity")
            result=purchasing.submit_authorized_purchase(order_id)
            return _respond(start_response,200,result)
        if method=="POST" and action=="purchase-monthly-review":
            require_access(actor,entity,"view")
            return _respond(start_response,200,
                purchasing.monthly_purchases(paying_entity=entity,month=data["month"]))
        if method=="POST" and action=="workflows":
            require_access(actor,entity,"operate")
            result=ops.new_workflow(entity,data["title"],data["category"],actor["sub"])
            return _respond(start_response,201,result)
        if method=="POST" and action=="workflow-transition":
            require_access(actor,entity,"operate")
            result=ops.advance_workflow(entity,data["workflow_id"],data["state"],
                                        actor["sub"],int(data["revision"]))
            return _respond(start_response,200,result)
        if method=="POST" and action=="alert":
            require_access(actor,entity,"operate")
            result=ops.priority_alert(entity,data["priority"],data["category"],
                                      data["description"],data["dedupe_key"])
            return _respond(start_response,201,result)
        if method=="POST" and action=="alert-ack":
            require_access(actor,entity,"operate")
            done=ops.acknowledge_alert(entity,data["alert_id"],actor["sub"])
            return _respond(start_response,200,{"acknowledged":done})
        if method=="POST" and action=="fraud-signal":
            require_access(actor,entity,"operate")
            result=ops.record_risk_signal(
                entity,data["source_id"],data["signal_type"],data["evidence_digest"]
            )
            return _respond(start_response,201,result)
        if method=="POST" and action=="learning-feedback":
            require_access(actor,entity,"operate")
            result=ops.record_learning_feedback(entity,data["signal_id"],
                        data["disposition"],actor["sub"],data.get("model_version"))
            return _respond(start_response,201,{"feedback_id":result})
        if method=="POST" and action=="call-rooms":
            require_access(actor,entity,"operate")
            guest=data["guest_subject"]
            if not isinstance(guest,str) or not guest or guest==actor["sub"] or len(guest)>256:
                raise ValueError()
            rid="room_"+uuid.uuid4().hex
            now=int(time.time())
            with _db() as db:
                db.execute("INSERT INTO call_rooms VALUES(?,?,?,?,?,?)",
                           (rid,entity,actor["sub"],guest,now,now+3600))
            return _respond(start_response,201,{"room_id":rid,"expires_at":now+3600})
        if method=="POST" and action=="call-signals":
            require_access(actor,entity,"view")
            room=data["room_id"]
            kind=data["kind"]
            if kind not in {"offer","answer","ice-candidate","hangup"}:
                raise ValueError()
            payload=data["payload"]
            if not isinstance(payload,dict):
                raise ValueError()
            encoded=json.dumps({"kind":kind,"payload":payload},separators=(",",":")).encode()
            if len(encoded)>64000:
                raise ValueError()
            with _db() as db:
                host,guest,_=_room_access(db,room,actor,entity)
                recipient=guest if actor["sub"]==host else host
                cipher=_cipher().encrypt(encoded)
                cursor=db.execute("""INSERT INTO call_signals
                  (room_id,sender,recipient,payload_ciphertext,created_at)
                  VALUES(?,?,?,?,?)""",(room,actor["sub"],recipient,cipher,int(time.time())))
            return _respond(start_response,201,{"signal_id":cursor.lastrowid})
        if method=="POST" and action=="call-inbox":
            require_access(actor,entity,"view")
            room=data["room_id"]
            after=max(0,int(data.get("after",0)))
            with _db() as db:
                _room_access(db,room,actor,entity)
                rows=db.execute("""SELECT signal_id,sender,payload_ciphertext FROM call_signals
                   WHERE room_id=? AND recipient=? AND signal_id>? ORDER BY signal_id LIMIT 100""",
                   (room,actor["sub"],after)).fetchall()
            out=[]
            for ident,sender,ciphertext in rows:
                out.append({"id":ident,"sender":sender,
                            **json.loads(_cipher().decrypt(ciphertext))})
            return _respond(start_response,200,{"signals":out})
        return _respond(start_response,404,{"error":"UNKNOWN_ACTION"})
    except PermissionError:
        return _respond(start_response,403,{"error":"ACCESS_DENIED"})
    except (KeyError,ValueError,TypeError,OverflowError,InvalidToken):
        return _respond(start_response,400,{"error":"INVALID_REQUEST"})
    except Exception:
        return _respond(start_response,503,{"error":"SERVICE_UNAVAILABLE"})
