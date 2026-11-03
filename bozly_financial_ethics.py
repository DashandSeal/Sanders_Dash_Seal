"""Bozly native financial ethics and AML/CFT case ledger.

Preserves truthful CFO reporting, evidence, confidentiality, conflict-of-interest
disclosure and risk-based investigation. The five ethics principles are informed
by the 2026 IESBA Code; AML topics by FATF Recommendations (June 2026).
Neither standard automatically applies as a licensing rule to Bozly software.

An indicator is not proof of illegal conduct. Only real regulated institutions
may carry out filings and obligations imposed on them. No simulated screening,
regulator filings, political profiling or arbitrary geography prohibitions.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from bozly_purchasing import ENTITIES

DB_PATH="/app/secure_ledgers/bozly_financial_core.db"
PHILOSOPHICAL_FOUNDATIONS=(
    "human_dignity_and_human_welfare",
    "truth_and_evidence",
    "justice_and_fairness",
    "stewardship_and_future_generations",
    "wisdom_and_proportionality",
    "responsibility_and_accountability",
    "ethical_moral_reasoning",
)

ETHICAL_PRINCIPLES=(
    "integrity",
    "objectivity",
    "competence_and_due_care",
    "confidentiality",
    "professional_behavior",
    "human_welfare",
    "accountability",
)
AML_AREAS=(
    "customer_due_diligence",
    "beneficial_ownership",
    "sanctions_screening",
    "transaction_monitoring",
    "source_of_funds",
    "cross_border_payments",
    "record_retention",
    "reporting_obligations",
)
CONCERNS=frozenset((
    "conflict_of_interest",
    "improper_personal_benefit",
    "misleading_financial_record",
    "suppression_of_financial_reporting",
    "unauthorized_asset_diversion",
    "bribery_or_kickback_indication",
    "sanctions_match_unresolved",
    "beneficial_owner_unresolved",
    "source_of_funds_unresolved",
    "unexplained_transaction_pattern",
    "potential_structuring",
    "third_party_payment_unexplained",
    "privacy_or_disclosure_risk",
    "other_documented_ethics_concern",
))
SERIOUS=frozenset((
    "unauthorized_asset_diversion",
    "suppression_of_financial_reporting",
))
FINDING_STATUSES=frozenset(("OPEN","UNDER_REVIEW","EXPLAINED","RESOLVED"))


def _db():
    path=Path(os.environ.get("BOZLY_DB_PATH",DB_PATH))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=20000")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_ethics_cases (
       case_id TEXT PRIMARY KEY,
       entity_id TEXT NOT NULL,
       topic TEXT NOT NULL,
       concern TEXT NOT NULL,
       subject_reference TEXT NOT NULL,
       described_observation TEXT NOT NULL,
       source_record_sha256 TEXT NOT NULL,
       business_effect TEXT NOT NULL,
       exact_amount_minor INTEGER,
       currency TEXT,
       request_actor TEXT NOT NULL,
       recorded_at INTEGER NOT NULL,
       status TEXT NOT NULL,
       conclusion TEXT NOT NULL DEFAULT 'UNDETERMINED',
       UNIQUE(entity_id,topic,concern,subject_reference,source_record_sha256)
    );
    CREATE TABLE IF NOT EXISTS bozly_ethics_history (
       event_id TEXT PRIMARY KEY,
       case_id TEXT NOT NULL REFERENCES bozly_ethics_cases(case_id),
       prior_hash TEXT,
       event_hash TEXT NOT NULL,
       event_type TEXT NOT NULL,
       metadata_sha256 TEXT NOT NULL,
       recorded_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bozly_aml_screening_evidence (
       record_id TEXT PRIMARY KEY,
       case_id TEXT NOT NULL REFERENCES bozly_ethics_cases(case_id),
       screening_source TEXT NOT NULL,
       screening_list_version TEXT NOT NULL,
       checked_at INTEGER NOT NULL,
       outcome TEXT NOT NULL,
       result_evidence_sha256 TEXT NOT NULL,
       recorded_at INTEGER NOT NULL
    );
    """)
    return db


def _valid_hash(digest: str):
    return (isinstance(digest,str) and len(digest)==64 and
            all(ch in "0123456789abcdef" for ch in digest))


def _record_history(db,case_id,event_type,metadata):
    before=db.execute(
        "SELECT event_hash FROM bozly_ethics_history WHERE case_id=? ORDER BY rowid DESC LIMIT 1",
        (case_id,)
    ).fetchone()
    previous=before[0] if before else None
    now=int(time.time())
    uid=uuid.uuid4().hex
    data_hash=hashlib.sha256(
        json.dumps(metadata,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    ).hexdigest()
    chain_hash=hashlib.sha256(
        json.dumps([uid,case_id,previous,event_type,data_hash,now],
                   separators=(",",":")).encode()
    ).hexdigest()
    db.execute(
        """INSERT INTO bozly_ethics_history
        (event_id,case_id,prior_hash,event_hash,event_type,metadata_sha256,recorded_at)
        VALUES(?,?,?,?,?,?,?)""",
        (uid,case_id,previous,chain_hash,event_type,data_hash,now)
    )


def record_concern(*, entity_id: str, topic: str, concern: str,
                   subject_reference: str, described_observation: str,
                   source_record_sha256: str, business_effect: str,
                   request_actor: str, exact_amount_minor: int | None = None,
                   currency: str | None = None) -> dict:
    """Record one actual source-grounded ethics/AML exception, not a legal verdict."""
    if entity_id not in ENTITIES:
        raise ValueError("Unknown Sanders legal entity")
    if topic not in ("ethics","aml","financial_integrity"):
        raise ValueError("Invalid investigation topic")
    if concern not in CONCERNS:
        raise ValueError("Unrecognized documented concern")
    args=(subject_reference,described_observation,business_effect,request_actor)
    if any(not isinstance(v,str) or not v.strip() or len(v)>2000 for v in args):
        raise ValueError("Source, observation, effect and actor are required")
    if not _valid_hash(source_record_sha256):
        raise ValueError("Actual evidence SHA-256 required")
    if (exact_amount_minor is None)!=(currency is None):
        raise ValueError("Specify both exact amount and currency, or neither")
    if exact_amount_minor is not None and (
        type(exact_amount_minor) is not int or exact_amount_minor<0 or
        not isinstance(currency,str) or len(currency)!=3 or not currency.isascii()
        or not currency.isalpha()
    ):
        raise ValueError("Currency amounts must be exact integer minor units")
    currency=currency.upper() if currency else None
    now=int(time.time())
    case_id="eth_"+uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        existing=db.execute(
            """SELECT case_id,status FROM bozly_ethics_cases WHERE entity_id=?
               AND topic=? AND concern=? AND subject_reference=? AND source_record_sha256=?""",
            (entity_id,topic,concern,subject_reference,source_record_sha256)
        ).fetchone()
        if existing:
            db.commit()
            return {"case_id":existing[0],"status":existing[1],"duplicate":True}
        db.execute(
            """INSERT INTO bozly_ethics_cases
            (case_id,entity_id,topic,concern,subject_reference,described_observation,
             source_record_sha256,business_effect,exact_amount_minor,currency,
             request_actor,recorded_at,status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'OPEN')""",
            (case_id,entity_id,topic,concern,subject_reference,
             described_observation,source_record_sha256,business_effect,
             exact_amount_minor,currency,request_actor,now)
        )
        _record_history(db,case_id,"CONCERN_RECORDED",{
            "topic":topic,"concern":concern,"source_sha256":source_record_sha256,
            "actor":request_actor,
        })
        db.commit()
    return {"case_id":case_id,"entity_id":entity_id,"topic":topic,
            "concern":concern,"status":"OPEN",
            "severity":"P0" if concern in SERIOUS else "REVIEW",
            "illegal_activity_proven":False,
            "mandatory_regulatory_filing_determined":False}


def record_screening_observation(*, case_id: str, entity_id: str,
                                 screening_source: str, screening_list_version: str,
                                 checked_at: int, outcome: str,
                                 result_evidence_sha256: str) -> dict:
    """Log actual externally sourced screenings; never fake a sanctions clearance."""
    if (any(not isinstance(s,str) or not s.strip() or len(s)>500
            for s in (screening_source,screening_list_version))
            or type(checked_at) is not int or checked_at<1
            or checked_at>int(time.time())+300
            or outcome not in ("MATCH_UNRESOLVED","NO_MATCH_OBSERVED",
                               "INDETERMINATE","FALSE_POSITIVE_DOCUMENTED")
            or not _valid_hash(result_evidence_sha256)):
        raise ValueError("Actual dated list identity and screening evidence required")
    record_id="scr_"+uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute(
            "SELECT entity_id FROM bozly_ethics_cases WHERE case_id=?",
            (case_id,)
        ).fetchone()
        if not row or row[0]!=entity_id:
            raise PermissionError("Screening case belongs to a different LLC")
        db.execute(
            """INSERT INTO bozly_aml_screening_evidence
            (record_id,case_id,screening_source,screening_list_version,checked_at,
             outcome,result_evidence_sha256,recorded_at) VALUES(?,?,?,?,?,?,?,?)""",
            (record_id,case_id,screening_source,screening_list_version,checked_at,
             outcome,result_evidence_sha256,int(time.time()))
        )
        _record_history(db,case_id,"ACTUAL_SCREENING_OBSERVED",{
            "record_id":record_id,"result_evidence_sha256":result_evidence_sha256,
            "outcome":outcome,
        })
        db.commit()
    return {"case_id":case_id,"record_id":record_id,"outcome":outcome,
            "legal_clearance_asserted":False}


def list_cases(*, entity_id: str, topic: str | None = None,
               limit: int = 100) -> dict:
    if entity_id not in ENTITIES:
        raise ValueError("Unknown Sanders legal entity")
    if topic is not None and topic not in ("ethics","aml","financial_integrity"):
        raise ValueError("Invalid topic")
    if type(limit) is not int or not 1<=limit<=250:
        raise ValueError("Invalid result limit")
    query="""SELECT case_id,topic,concern,subject_reference,
             described_observation,source_record_sha256,business_effect,
             exact_amount_minor,currency,recorded_at,status,conclusion
             FROM bozly_ethics_cases WHERE entity_id=?"""
    args=[entity_id]
    if topic:
        query+=" AND topic=?"
        args.append(topic)
    query+=" ORDER BY recorded_at DESC,case_id LIMIT ?"
    args.append(limit)
    with _db() as db:
        rows=db.execute(query,args).fetchall()
    return {"entity_id":entity_id,"cases":[{
        "case_id":cid,"topic":tp,"concern":c,"subject_reference":subject,
        "observation":desc,"evidence_sha256":digest,"business_effect":effect,
        "exact_amount_minor":amount,"currency":currency,"recorded_at_unix":at,
        "status":status,"conclusion":conclusion,
    } for cid,tp,c,subject,desc,digest,effect,amount,currency,at,status,conclusion in rows]}


def resolve_case(*, case_id: str, entity_id: str, status: str, 
                 conclusion: str, actor: str) -> dict:
    if status not in FINDING_STATUSES or not conclusion or len(conclusion)>2000:
        raise ValueError("A documented resolution state and conclusion required")
    if not isinstance(actor,str) or not actor.strip():
        raise ValueError("Authenticated case actor required")
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT entity_id,status FROM bozly_ethics_cases WHERE case_id=?",
                       (case_id,)).fetchone()
        if not row or row[0]!=entity_id:
            raise PermissionError("Case not found for LLC")
        db.execute("UPDATE bozly_ethics_cases SET status=?,conclusion=? WHERE case_id=?",
                   (status,conclusion,case_id))
        _record_history(db,case_id,"CASE_UPDATED",{
            "previous_status":row[1],"status":status,
            "conclusion":conclusion,"actor":actor,
        })
        db.commit()
    return {"case_id":case_id,"status":status,
            "conclusion_not_legal_certification":True}


def philosophical_financial_decision_protocol() -> dict:
    """Decision reasoning Bozly must apply alongside its existing ethics framework.

    This policy is a published operating contract; it is not a claim that a
    semantic reasoning model or live payment screening has been deployed.
    """
    return {
        "foundation":list(PHILOSOPHICAL_FOUNDATIONS),
        "decision_questions":[
            "What are the verified facts and exact financial amounts?",
            "What is the genuine business purpose and supporting evidence?",
            "Who may benefit, who could be harmed, and are their interests fairly considered?",
            "Is the action lawful in the actual relevant jurisdiction, or is law still unknown?",
            "Does it protect the owner's assets and legitimate interests over time?",
            "Are there conflicts of interest, concealment, bribery, exploitation or unjustified risks?",
            "What less harmful and proportionate course achieves the legitimate objective?",
            "Can Bozly explain the outcome, source, uncertainty and accountability?",
        ],
        "distinctions":{
            "technical_possibility":"Does not establish ethical permission.",
            "legal_possibility":"Does not alone establish moral justification.",
            "owner_instruction":"Must be interpreted truthfully and without invented consent.",
            "ordinary_private_conversation":"Not an executive incident solely for discussing Bozly.",
            "documented_unauthorized_diversion":"Uses the existing P0 financial alert path.",
        },
        "method":"Philosophy informs ethics, evidence informs logic, and human oversight ensures accountability.",
    }


def ethical_operating_principles() -> dict:
    return {
        "engine":"BOZLY-NATIVE-FINANCIAL-ETHICS",
        "principles":list(ETHICAL_PRINCIPLES),
        "philosophy":philosophical_financial_decision_protocol(),
        "aml_areas":list(AML_AREAS),
        "reporting":"Truthful, source-linked, currency-accurate, explainable.",
        "conflicts":"Disclose conflicts, self-dealing and improper influence.",
        "confidentiality":"Protect private executive conversations and case evidence.",
        "nonweaponization":"No harmful coercion, fabrication or discriminatory profiling.",
        "financial_diversion":"Block unauthorized diversions through guarded payment paths "
                              "and notify designated human officers via the P0 system.",
        "separation":"Separate LLC accounts; no implied joint liability.",
        "legal_scope":"Jurisdiction-specific obligations depend on actual regulated activity.",
        "certification":"No professional licensing or AML compliance certification implied.",
    }
