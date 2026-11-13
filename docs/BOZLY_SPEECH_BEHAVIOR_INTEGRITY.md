# Bozly CFO — Speech, Behavior and Financial Integrity

The owner requires Bozly to make his own assessments of possible lies or deception, including evidence beyond documents. The system must consider genuine speech observations, behavior, bodily responses (when actually measured by authorized instruments) and corroborated business records.

## Observations and evidence

The native `bozly_multimodal_integrity.py` module accepts genuine evidence from an authenticated operator:
- Short real PCM-16 audio excerpts (up to 4 seconds), and optional accompanying transcripts.
- Quantitative changes in speech timing, pauses, vocal intensity, pitch, response latency, gaze/blink rate, body motion, pulse, breathing and skin conductance, when **actually captured** by authorized microphones, cameras or sensors.
- Same-person baselines for reporting changes, not a diagnosis of motives.
- A referenced factual financial claim that Bozly can independently compare with an actual LLC-specific purchase or global-payment ledger record.

Bozly analyzes the supplied real audio for energy and low-energy frame fractions; it does not currently extract pitch, detect a speaker, identify speech, operate a camera or connect to wearables. It does not invent such readings or treat absent readings as normal. A transcript supplied by a caller is not independently authenticated by the module.

## Immutable owner-directed accuracy requirement

**Hard-locked specification: Bozly must achieve 98% deception-detection accuracy.** This is an owner-established, immutable design requirement, not a discretionary target that the assistant may reduce, redefine or remove. Only an explicit new instruction from the founder can amend the governing requirement. It is not an observed or verified performance statistic. Currently there is no measured deception-classification accuracy for Bozly's live speech, camera or physiological sensor integrations; those sources are not connected in production. The module must never present the 98% target as achieved accuracy or a 98% probability that any individual is lying.

Bozly independently evaluates source-grounded factual claims and genuine recorded observations. Stress-related behavior and physiological changes alone cannot establish intentional dishonesty. This fixed requirement does not change existing ethics, privacy, non-weaponization or human-in-the-loop diversion notifications. No tests or verification requirements are added.

## Bozly's autonomous assessment

Bozly classifies supported, contradicted and insufficient financial assertions by its own ledger comparisons. It reports observed physiological or nonverbal changes separately, with their measurements and available baselines. These cues are not reliable proof of deception and must never be assigned a fabricated lie probability, clinical diagnosis, or criminal finding.

There is no scientifically established universal pattern of voice stress, eye contact, blinking, body language, pulse, sweating or breathing that reliably identifies lying in a particular person. Bozly must distinguish **observable behavior, factual contradictions, uncertainty and intent**. It makes an autonomous evidence-based assessment; neither the owner nor the assistant supplies a preordained verdict.

## Runtime API

`POST /bozly/v1/multimodal-integrity` on the existing authenticated entity-scoped human API accepts real supplied observations, a session reference, subject reference, capture source, UTC capture timestamp, optional short WAV bytes, transcript, baselines, and a referenced financial claim. It stores observation data, original-audio SHA-256, assessment and related claim review ID. The original audio is not retained by this module.

Any collection of voice, video or physiological data must comply with applicable recording, privacy, biometric and employment laws. The module does not activate covert monitoring or record audio automatically. Live sensors, phone/video streams, lawful capture mechanisms, access and privacy controls, real-time streaming, full evidence archiving and production deployment are not yet connected.

An observed behavior change alone cannot trigger a financial-diversion P0 incident. Actual documented unauthorized asset redirection uses the separate existing executive alert mechanism. Private conversations discussing Bozly are not themselves diversion incidents.

## Implementation

- `bozly_multimodal_integrity.py` — independent observable-signal assessment and evidence trace.
- `bozly_claim_integrity.py` — original ledger-grounded factual claim classification.
- `bozly_human_api.py` — authenticated endpoint.
- `bozly_identity_and_conduct.py` — native professional/ethical conduct.
- `Dockerfile.bozly` — runtime packaging.

**No tests created or run. No live sensor connection or production lie-detection capability claimed.**
