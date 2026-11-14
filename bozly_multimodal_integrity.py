"""Bozly CFO multimodal interview-integrity assessment.

Observe real supplied speech acoustics, transcripts, and optional human
behavior/physiological measurements, and compare claims with Bozly ledgers.
Bozly independently reports factual contradictions and observable changes.

Scientific boundary: there is no reliable universal vocal, visual, heart-rate,
sweat, breath or facial cue that establishes someone is lying. Behavioral
variation alone NEVER implies deceptive intent and cannot create a P0
asset-diversion incident.

No microphone, camera, sensor, transcription, or covert recording is activated
here. Recordings must originate from authorized, lawfully obtained sources.
Original audio is never stored; only its SHA-256 and derived acoustic summary.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
import time
import uuid
import wave

from bozly_purchasing import ENTITIES
import bozly_claim_integrity as claims

DEFAULT_DB="/app/secure_ledgers/bozly_financial_core.db"

# The available external sensing adapter may measure these parameters.
# Each is an observation, not an evidence-based lie signal.
MEASURES = frozenset({
    "speech_rate_wpm", "pause_fraction", "voice_rms", "median_pitch_hz",
    "response_latency_ms", "blink_rate_per_min", "gaze_shift_rate_per_min",
    "body_movement_rate", "heart_rate_bpm", "respirations_per_min",
    "skin_conductance_us",
})
# Owner-directed hard lock: 98% deception-detection accuracy is a fixed
# specification requirement. No assistant-selected downgrade or replacement.
# This setting does not itself establish measured performance.
OWNER_IMMUTABLE_DECEPTION_ACCURACY_REQUIREMENT_PERCENT=98
VERIFIED_DECEPTION_ACCURACY_PERCENT=None

MAX_WAV_BYTES=100_000


def _db():
    dbpath=Path(os.environ.get("BOZLY_DB_PATH",DEFAULT_DB))
    dbpath.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(dbpath),timeout=15,isolation_level=None)
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS bozly_multimodal_assessments(
        assessment_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        session_reference TEXT NOT NULL,
        subject_reference TEXT NOT NULL,
        capture_source TEXT NOT NULL,
        capture_time_unix INTEGER NOT NULL,
        observed_by TEXT NOT NULL,
        audio_sha256 TEXT,
        observation_sha256 TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        changed_metrics_json TEXT NOT NULL,
        related_claim_review_id TEXT,
        factual_claim_assessment TEXT,
        assessment TEXT NOT NULL,
        observed_at INTEGER NOT NULL
    );
    """)
    return db


def _measurements(values):
    if values is None:
        return {}
    if not isinstance(values,dict) or len(values)>len(MEASURES):
        raise ValueError("Measurements must be a bounded object")
    checked={}
    for name,value in values.items():
        if name not in MEASURES or type(value) not in (int,float):
            raise ValueError("Unsupported or nonnumeric sensor measurement")
        if not math.isfinite(value) or value<0 or value>1_000_000:
            raise ValueError("Sensor measurement out of range")
        if name=="pause_fraction" and value>1:
            raise ValueError("Pause fraction must be between 0 and 1")
        checked[name]=round(float(value),5)
    return checked


def _wav_metrics(wav_b64,transcript):
    """Process genuine PCM-16 mono WAV bytes with energy-based pause estimate.

    This is acoustic signal measurement, not medical diagnosis, emotion
    detection, biometric speaker verification, or validated lie detection.
    """
    if not isinstance(wav_b64,str) or len(wav_b64)>136_000:
        raise ValueError("PCM WAV base64 input too large")
    try:
        raw=base64.b64decode(wav_b64,validate=True)
    except (ValueError,binascii.Error) as exc:
        raise ValueError("Invalid PCM WAV data") from exc
    if not raw or len(raw)>MAX_WAV_BYTES:
        raise ValueError("Unsupported audio input length")
    try:
        with wave.open(io.BytesIO(raw),"rb") as reader:
            rate=reader.getframerate()
            channels=reader.getnchannels()
            width=reader.getsampwidth()
            frames=reader.getnframes()
            if (reader.getcomptype()!="NONE" or channels!=1 or width!=2
                    or not 8000<=rate<=48000
                    or not 0.3<=frames/rate<=4.0):
                raise ValueError("Requires 0.3–4 seconds mono PCM-16 WAV at 8–48 kHz")
            payload=reader.readframes(frames)
    except (wave.Error,EOFError,struct.error) as exc:
        raise ValueError("Malformed PCM WAV file") from exc
    if len(payload)!=frames*2:
        raise ValueError("Truncated PCM WAV frames")
    window=max(1,int(rate*0.025))
    frame_rms=[]
    for pos in range(0,frames-window+1,window):
        samp=struct.unpack_from("<"+("h"*window),payload,pos*2)
        rms=math.sqrt(sum(x*x for x in samp)/window)/32768
        frame_rms.append(rms)
    if not frame_rms:
        raise ValueError("Audio too short for stable measurements")
    sorted_energy=sorted(frame_rms)
    noise=sorted_energy[max(0,int(len(sorted_energy)*0.15)-1)]
    # A relative, context-dependent energy floor, not speech recognition.
    threshold=max(0.012,noise*2.5)
    quiet=sum(1 for level in frame_rms if level<threshold)
    pause_fraction=round(quiet/len(frame_rms),5)
    overall_rms=round(math.sqrt(sum(x*x for x in frame_rms)/len(frame_rms)),5)
    duration=frames/rate
    measured={
        "pause_fraction":pause_fraction,
        "voice_rms":overall_rms,
    }
    if isinstance(transcript,str) and transcript.strip():
        measured["speech_rate_wpm"]=round(
            len(transcript.split())*60/duration,5
        )
    return {
        "audio_sha256":hashlib.sha256(raw).hexdigest(),
        "derived_metrics":measured,
        "audio_seconds":round(duration,3),
        "signal_note":"Energy-based silent-frame estimate; silence may be noise, "
                      "microphone distance, room conditions or real pauses.",
    }


def _departures(current,baseline):
    """Observed deviations from a supplied same-speaker baseline.

    Differences are never assigned a deception probability or guilt score.
    """
    departures=[]
    for name,value in sorted(current.items()):
        if name not in baseline:
            continue
        other=baseline[name]
        difference=round(value-other,5)
        # Report numerical change without pseudo-clinical diagnostic thresholds.
        departures.append({
            "measurement":name,
            "current":value,
            "baseline":other,
            "delta":difference,
            "relative_delta":(
                round(difference/other,5) if other>0 else None
            ),
            "not_diagnostic_of_lying":True,
        })
    return departures


def assess_interaction(*, entity_id,session_reference,subject_reference,
                       capture_source,capture_time_unix,observed_by,
                       measurement_values=None,baseline_values=None,
                       wav_pcm16_base64=None,transcript=None,
                       financial_claim=None):
    """Bozly autonomously evaluates speech/body cues and corroborated facts.

    financial_claim: {record_type, record_id, claimed_field, claimed_value}.
    The separately recorded source comparison determines factual contradiction.
    We do NOT infer deliberate deception from gestures, voice stress or pulse.
    """
    if entity_id not in ENTITIES:
        raise ValueError("Known Sanders LLC required")
    strings=(session_reference,subject_reference,capture_source,observed_by)
    if any(not isinstance(v,str) or not v.strip() or len(v)>256 for v in strings):
        raise ValueError("Session, subject reference, source and actor required")
    if (type(capture_time_unix) is not int or capture_time_unix<=0
            or capture_time_unix>int(time.time())+300):
        raise ValueError("A genuine capture timestamp required")
    if transcript is not None and (
        not isinstance(transcript,str) or len(transcript)>10000
    ):
        raise ValueError("Transcript too long")
    current=_measurements(measurement_values)
    baseline=_measurements(baseline_values)
    audio=None
    if wav_pcm16_base64 is not None:
        audio=_wav_metrics(wav_pcm16_base64,transcript)
        current.update(audio["derived_metrics"])
    if not current and not financial_claim:
        raise ValueError("Actual behavioral observation or factual claim required")
    depart=_departures(current,baseline)
    claim_observation=None
    if financial_claim is not None:
        if not isinstance(financial_claim,dict) or set(financial_claim)!={
            "record_type","record_id","claimed_field","claimed_value"
        }:
            raise ValueError("Financial claim requires exact source reference and field")
        claim_observation=claims.assess_documented_claim(
            entity_id=entity_id,
            record_type=financial_claim["record_type"],
            record_id=financial_claim["record_id"],
            claimed_field=financial_claim["claimed_field"],
            claimed_value=financial_claim["claimed_value"],
            requested_by=observed_by,
        )
    finding=claim_observation["assessment"] if claim_observation else None
    if finding=="CONTRADICTED_BY_RECORD":
        status="DOCUMENTED_FACTUAL_CONTRADICTION"
    elif finding=="CONSISTENT_WITH_RECORD":
        status="CLAIM_CONSISTENT_WITH_AVAILABLE_RECORD"
    elif current:
        status="BEHAVIORAL_OBSERVATIONS_ONLY_NO_VERACITY_INFERENCE"
    else:
        status="INSUFFICIENT_EVIDENCE"
    summary={
        "session_reference":session_reference,
        "subject_reference":subject_reference,
        "capture_source":capture_source,
        "capture_time_unix":capture_time_unix,
        "measurements":current,
        "baseline":baseline,
        "audio_sha256":audio["audio_sha256"] if audio else None,
        "claim_review_id":claim_observation["review_id"] if claim_observation else None,
        "status":status,
    }
    digest=hashlib.sha256(
        json.dumps(summary,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    assessment_id="multi_"+uuid.uuid4().hex
    with _db() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT INTO bozly_multimodal_assessments
            (assessment_id,entity_id,session_reference,subject_reference,
            capture_source,capture_time_unix,observed_by,audio_sha256,
            observation_sha256,metrics_json,changed_metrics_json,
            related_claim_review_id,factual_claim_assessment,assessment,observed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (assessment_id,entity_id,session_reference,subject_reference,
             capture_source,capture_time_unix,observed_by,
             audio["audio_sha256"] if audio else None,digest,
             json.dumps(current,sort_keys=True,separators=(",",":")),
             json.dumps(depart,sort_keys=True,separators=(",",":")),
             claim_observation["review_id"] if claim_observation else None,
             finding,status,int(time.time()))
        )
        db.commit()
    return {
        "assessment_id":assessment_id,
        "entity_id":entity_id,
        "assessed_by_system":"BOZLY-CFO",
        "assessment":status,
        "observed_metrics":current,
        "within_subject_changes":depart,
        "related_financial_claim":claim_observation,
        "audio_sha256":audio["audio_sha256"] if audio else None,
        "audio_note":audio["signal_note"] if audio else None,
        "observation_sha256":digest,
        "required_deception_accuracy_percent":OWNER_IMMUTABLE_DECEPTION_ACCURACY_REQUIREMENT_PERCENT,
        "requirement_immutable_by_design":True,
        "requirement_change_authority":"founder_only",
        "verified_accuracy_percent":VERIFIED_DECEPTION_ACCURACY_PERCENT,
        "requirement_achieved":False,
        "lie_or_deceptive_intent_proven":False,
        "behavior_is_not_proof_of_lying":True,
        "automatic_diversion_alert_triggered":False,
        "source_authenticity":"provided_by_authenticated_channel_not_independently_proven",
        "original_audio_retained":False,
        "requirements":"Use lawful, authorized recordings and genuine sensor observations.",
    }
