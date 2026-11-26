"""RTSA Minotaur — production build-out (RTSA Build Program Q9).

The recovered ``minotaur_sentinel.py`` at the repository root is the
foundation and is left untouched: ``MinotaurSentinel`` pins SHA-256
baselines over ``PROTECTED_TARGETS`` at construction and
``execute_patrol_cycle`` reports each target that is MISSING or whose
hash no longer matches its baseline. Its baselines live in process
memory — pinned from whatever the working directory held at import,
gone at exit — anomalies are returned as bare strings with no
lifecycle, and nothing is queryable after the fact.

This module is the production build-out the queue's Q9 completion
definition requires: the recovered patrol's semantics as durable,
receipted state on the shared RTSA foundation
(:mod:`core_platform.rtsa_foundation`) — operator-pinned durable
baselines over a workspace root (in place of the construction-time
in-memory pins), recorded patrol cycles, an anomaly lifecycle
(DETECTED, ACKNOWLEDGED, ESCALATED, CLEARED), and clearance
determinations for the Twin-Gate section 8 step 2: a subject is
SAFE_TO_EXECUTE only when every protected target is pinned, the
latest patrol cycle is clean, and no anomaly is open — otherwise the
determination is DENIED with the blocker named, per MASTER
section 10 (no token, no bypass).

MASTER section 5 and AGENTS.md are explicit: RTSA Minotaur and the
Sanders Labyrinth Shield are separate systems and are never merged.
The Minotaur patrols the integrity of the house's own files —
including, as one protected target among five, the Shield's
foundation file — it does not evaluate arriving traffic, and this
module contains no Shield code.

Like every platform on the foundation, the service refuses to exist
without a working Glass-Box audit adapter: no record, no action.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import ssl
import time
import uuid
from pathlib import Path

from minotaur_sentinel import PROTECTED_TARGETS, MinotaurSentinel

from .rtsa_foundation import (
    AccessGuard,
    FoundationDenied,
    FoundationForbidden,
    GeofencePolicy,
    PlatformIdentity,
    ensure_checkin_schema,
    validate_identity,
)
from .rtsa_foundation import (
    latest_check_in as _foundation_latest_check_in,
)
from .rtsa_foundation import (
    record_check_in as _foundation_record_check_in,
)


IDENTITY = validate_identity(PlatformIdentity(
    platform_id='minotaur_sentinel',
    name='RTSA Minotaur',
    legal_entities=(),
    naics_codes=(),
    authorized_regions=('US-CO', 'US-WI'),
    status='BUILT',
))

TARGETS = tuple(PROTECTED_TARGETS)
ANOMALY_KINDS = ('MISSING', 'ALTERED')
ANOMALY_STATUSES = ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED', 'CLEARED')
# The anomaly lifecycle: which transitions each action may take.
ANOMALY_TRANSITIONS = {
    'acknowledge': {'DETECTED': 'ACKNOWLEDGED'},
    'escalate': {'DETECTED': 'ESCALATED', 'ACKNOWLEDGED': 'ESCALATED'},
    'clear': {'DETECTED': 'CLEARED', 'ACKNOWLEDGED': 'CLEARED',
              'ESCALATED': 'CLEARED'},
}

# -- The three shields (founder's orders, 2026-11-26) --------------
#
# The shields the Minotaur patrols simultaneously, each under
# its own identity, with the core files that are that shield's
# own: the recovered foundation and production service of the
# Sanders Labyrinth Shield, the LABYRINTH service, and the
# Sovereign Shield V3 service. Patrol coverage is by reference
# to these files — the Minotaur reads hashes, he absorbs no
# shield code and no shield identity.
SHIELD_PATROL_TARGETS = (
    ('sanders_labyrinth_shield', 'Sanders Labyrinth Shield',
     ('labyrinth_shield.py',
      'core_platform/labyrinth_shield_service.py')),
    ('labyrinth', 'LABYRINTH',
     ('core_platform/labyrinth_service.py',)),
    ('sovereign_shield_v3', 'Sovereign Shield V3',
     ('core_platform/sovereign_shield_v3_service.py',)),
)
SHIELD_IDS = tuple(entry[0] for entry in SHIELD_PATROL_TARGETS)

# -- The Minotaur's own upgrade (founder's directive,
# 2026-11-26): quantum protection protocols and labyrinth
# behavior, built into the Minotaur himself.
#
# Quantum layer, at the honestly buildable native level of
# the Daedalus precedent: WOTS+ one-time signatures (SHA-256,
# w=16) under a SHA-256 Merkle tree — the hash-based
# post-quantum signature family of RFC 8391, as in XMSS /
# SLH-DSA (FIPS 205) — with SHA-3 digests and SHAKE-256 key
# derivation, pure Python standard library. His patrol
# attestations, integrity proofs, and baselines are signed
# with it and hash-chained with SHA3-256. ML-KEM key
# exchange is NOT in the Python standard library: it stands
# DECLARED below, not implemented and not claimed, and the
# repository's unattributed third-party PQC module is not
# wired here — that remains the founder's separate decision.
QUANTUM_SCHEME = (
    'WOTS+ one-time signatures (SHA-256, w=16) under a'
    ' SHA-256 Merkle tree — hash-based post-quantum family'
    ' (RFC 8391 construction, as in XMSS / SLH-DSA);'
    ' SHA3-256 attestation chain; SHAKE-256 key derivation')
QUANTUM_KEY_EXCHANGE = (
    'ML-KEM: declared, not implemented in this service'
    ' (not in the Python standard library; no third-party'
    ' PQC module is wired into this platform). The adopted'
    ' gap-closure route (founder amendment, 2026-11-26) is'
    ' the OpenSSL FIPS Provider 3.5.9 — FIPS 140-3'
    ' certificate #5586, whose approved algorithms include'
    ' ML-KEM, ML-DSA, and SLH-DSA — where the environment'
    ' provides it in approved mode; the environment check'
    ' of record states what this runtime actually'
    ' provides, and nothing beyond it is claimed.')
_WOTS_W = 16
_WOTS_LEN1 = 64
_WOTS_LEN2 = 3
_WOTS_LEN = _WOTS_LEN1 + _WOTS_LEN2
_TREE_HEIGHT = 5
_LEAVES = 1 << _TREE_HEIGHT
_SIGNING_SEED_ENV = 'MINOTAUR_SIGNING_SEED_HEX'
_ATTESTATION_GENESIS = '0' * 64

# -- Self-protection amendment (founder-adopted
# 2026-11-26) ----------------------------------------
#
# "The Minotaur — Comprehensive Self-Protection and
# Anti-Circumvention Amendment", adopted by the
# founder as an AMENDMENT to the Minotaur's original
# scope: it strengthens his original scope without
# superseding, replacing, repealing, diminishing or
# invalidating any existing Founder directive. The
# amendment's operative text is carried verbatim
# below; its fifteen enumerated protections stand as
# self-protection records/checks in his machinery,
# each protection's state derived from its checks of
# record and none represented beyond its evidence.
SELF_PROTECTION_TITLE = (
    'The Minotaur — Comprehensive Self-Protection and'
    ' Anti-Circumvention Amendment')
SELF_PROTECTION_ADOPTED = '2026-11-26'
SELF_PROTECTION_SCOPE_VERBATIM = (
    'The Minotaur shall possess comprehensive native'
    ' defensive capabilities to protect himself, his'
    ' original identity, governing directives,'
    ' intelligence, operational authority,'
    ' cryptographic infrastructure, communications,'
    ' credentials, defensive machinery and recovery'
    ' mechanisms against unauthorized access,'
    ' manipulation, compromise, circumvention and'
    ' attack.')
SELF_PROTECTION_EXTERNAL_AUTHORITY_VERBATIM = (
    'No external information source, software'
    ' dependency, communication channel, testing'
    ' mechanism, recovery mechanism, connected'
    ' platform or security update shall possess'
    ' unauthorized authority over the Minotaur\'s'
    ' governing intelligence or established'
    ' protective responsibilities.')
SELF_PROTECTION_DETECT_RESIST_VERBATIM = (
    'The Minotaur shall possess functional'
    ' capabilities to detect, resist, contain and'
    ' recover from attempted authentication bypass,'
    ' privilege escalation, platform impersonation,'
    ' forged Founder instructions, cryptographic'
    ' downgrade, malicious updates, compromised'
    ' dependencies, corrupted recovery baselines,'
    ' denial-of-service attacks, resource exhaustion'
    ' and unauthorized modifications.')
SELF_PROTECTION_DECEPTION_VERBATIM = (
    'His defensive deception environments shall'
    ' remain isolated from genuine production'
    ' infrastructure, confidential bloodline'
    ' information and functioning emergency'
    ' operations.')
SELF_PROTECTION_RECOVERY_VERBATIM = (
    'His recovery mechanisms shall preserve every'
    ' original Founder directive and every validly'
    ' adopted amendment.')
SELF_PROTECTION_ANTI_CIRCUMVENTION_VERBATIM = (
    'No unauthorized instruction shall disable,'
    ' diminish, circumvent or redirect his'
    ' established protective responsibilities.')
SELF_PROTECTION_NOT_A_CEILING_VERBATIM = (
    'The Minotaur\'s enumerated defensive'
    ' capabilities shall not constitute an exhaustive'
    ' limitation upon his original Founder-assigned'
    ' mission.')
SELF_PROTECTION_STRENGTHENS_VERBATIM = (
    'This amendment shall strengthen his original'
    ' scope without superseding, replacing,'
    ' repealing, diminishing or invalidating any'
    ' existing Founder directive.')
SELF_PROTECTION_ATTACK_CLASSES = (
    'AUTHENTICATION_BYPASS', 'PRIVILEGE_ESCALATION',
    'PLATFORM_IMPERSONATION',
    'FORGED_FOUNDER_INSTRUCTIONS',
    'CRYPTOGRAPHIC_DOWNGRADE', 'MALICIOUS_UPDATES',
    'COMPROMISED_DEPENDENCIES',
    'CORRUPTED_RECOVERY_BASELINES',
    'DENIAL_OF_SERVICE', 'RESOURCE_EXHAUSTION',
    'UNAUTHORIZED_MODIFICATIONS',
)
# The fifteen enumerated protections of the adopted
# amendment, verbatim, each with the native machinery
# of record that serves it. A mechanism statement is
# a statement about records and machinery that stand
# in this platform — never a claim of live effect
# beyond what the checks of record evidence.
SELF_PROTECTIONS = (
    {'protection': 'COMPROMISED_ADMINISTRATIVE_CREDENTIALS',
     'verbatim': 'Protection against compromised'
                 ' administrative credentials.',
     'mechanism': 'Every state-changing act requires'
                  ' the operator verifier; a'
                  ' credential that does not verify'
                  ' performs nothing, and every act'
                  ' is receipted to the Glass-Box'
                  ' record.'},
    {'protection': 'PRIVILEGE_ESCALATION',
     'verbatim': 'Protection against unauthorized'
                 ' privilege escalation.',
     'mechanism': 'Roles are fixed by the access'
                  ' guard (OPERATOR / AUDITOR scopes);'
                  ' guarded reads cannot write, and'
                  ' operator acts re-verify the actor'
                  ' on every call.'},
    {'protection': 'MALICIOUS_INTERNAL_PLATFORM_COMMUNICATIONS',
     'verbatim': 'Protection against malicious'
                 ' internal platform communications.',
     'mechanism': 'Platform-to-platform acts are'
                  ' records under the guard, never'
                  ' instructions: no inbound record'
                  ' can direct this platform, and the'
                  ' amendment\'s external-authority'
                  ' bar stands in the design of'
                  ' record.'},
    {'protection': 'COMPROMISED_RECOVERY_MECHANISMS',
     'verbatim': 'Protection against compromised'
                 ' recovery mechanisms.',
     'mechanism': 'Recovery is by reference to the'
                  ' guarded record set and the signed'
                  ' attestation chain; a recovery'
                  ' source whose hashes do not verify'
                  ' against the anchored chain head is'
                  ' evidence of compromise, not a'
                  ' restore path.'},
    {'protection': 'UNAUTHORIZED_CONFIGURATION_CHANGES',
     'verbatim': 'Protection against unauthorized'
                 ' configuration changes.',
     'mechanism': 'Configuration of record (baselines,'
                  ' pins, policies of his patrol)'
                  ' changes only through operator'
                  ' acts, each receipted; the'
                  ' self-integrity of his own modules'
                  ' is hash-pinned like every core he'
                  ' patrols.'},
    {'protection': 'DENIAL_OF_SERVICE',
     'verbatim': 'Protection against denial-of-service'
                 ' attacks.',
     'mechanism': 'His surfaces are governed record'
                  ' operations behind the access'
                  ' guard; availability attacks are'
                  ' recorded as checks of record'
                  ' against this protection. No live'
                  ' traffic function is claimed.'},
    {'protection': 'RESOURCE_EXHAUSTION',
     'verbatim': 'Protection against resource'
                 ' exhaustion.',
     'mechanism': 'His one-time signature pool is'
                  ' finite and fails closed at'
                  ' exhaustion rather than reusing a'
                  ' key; patrol and attestation work'
                  ' is bounded per recorded cycle.'},
    {'protection': 'SECURITY_LOG_TAMPERING',
     'verbatim': 'Protection against tampering with'
                 ' security logs.',
     'mechanism': 'His attestations are hash-chained'
                  ' (SHA3-256) and signed; any'
                  ' rewritten record breaks the chain'
                  ' verification, and the operator'
                  ' carries the signed head off the'
                  ' host as the anchor.'},
    {'protection': 'CLOCK_TIMESTAMP_MANIPULATION',
     'verbatim': 'Protection against manipulation of'
                 ' system clocks and timestamps.',
     'mechanism': 'The attestation chain is ordered'
                  ' by sequence and hash linkage, not'
                  ' by wall clock: a moved clock'
                  ' cannot reorder or rewrite chained'
                  ' history without breaking'
                  ' verification.'},
    {'protection': 'COMPROMISED_CRYPTOGRAPHIC_RANDOMNESS',
     'verbatim': 'Protection against compromised'
                 ' cryptographic randomness.',
     'mechanism': 'His signing keys derive'
                  ' deterministically from the seed'
                  ' by SHAKE-256 domain-separated'
                  ' derivation — no runtime randomness'
                  ' enters key material after the seed'
                  ' itself, whose source is recorded.'},
    {'protection': 'MALICIOUS_SOFTWARE_ROLLBACK',
     'verbatim': 'Protection against malicious'
                 ' software rollback.',
     'mechanism': 'His cores and the shields\' cores'
                  ' are hash-pinned; a rolled-back or'
                  ' substituted module reads MISMATCH'
                  ' against its pin and raises an'
                  ' anomaly rather than running'
                  ' silently.'},
    {'protection': 'UNAUTHORIZED_DISABLING_OF_DEFENSIVE_FUNCTIONS',
     'verbatim': 'Protection against unauthorized'
                 ' disabling of defensive functions.',
     'mechanism': 'No record operation in his'
                  ' contract disables a defensive'
                  ' function; the anti-circumvention'
                  ' bar of the amendment stands in'
                  ' the design of record, and any'
                  ' attempt is a check of record.'},
    {'protection': 'SINGLE_POINTS_OF_FAILURE',
     'verbatim': 'Protection against single points of'
                 ' failure.',
     'mechanism': 'His integrity evidence is held in'
                  ' three places by design: the'
                  ' patrol store, the Glass-Box'
                  ' receipts, and the operator-carried'
                  ' signed anchor — no single store\'s'
                  ' loss erases the evidence.'},
    {'protection': 'THREAT_DETECTION_INTELLIGENCE_COMPROMISE',
     'verbatim': 'Protection against compromise of'
                 ' his own threat-detection'
                 ' intelligence.',
     'mechanism': 'His detection records (baselines,'
                  ' anomaly lifecycle, decoy pins)'
                  ' are themselves receipted records;'
                  ' an altered detection record is a'
                  ' tamper finding under the same'
                  ' chain discipline as the cores he'
                  ' patrols.'},
    {'protection': 'GOVERNING_DIRECTIVES_MODIFICATION',
     'verbatim': 'Protection against unauthorized'
                 ' modification of his original'
                 ' governing directives.',
     'mechanism': 'His governing directives stand in'
                  ' the bloodline guarded record set,'
                  ' watched by Sanders Sentinel\'s'
                  ' verification cycle against their'
                  ' manifest hashes; amendment is the'
                  ' only path of change, never'
                  ' supersession.'},
)
SELF_PROTECTION_CHECK_OUTCOMES = (
    'EVIDENCED', 'FINDING', 'NOT_EVIDENCED', 'FUNCTIONING')
# The adopted quantum gap-closure route: the
# certificate covers exactly the OpenSSL FIPS
# Provider 3.5.9 operated in approved mode. The
# environment check of record states what a runtime
# actually provides; the claim follows the check,
# never the reverse.
CRYPTO_ROUTE = {
    'adopted_route': 'OPENSSL_FIPS_PROVIDER',
    'module': 'OpenSSL FIPS Provider 3.5.9',
    'validation': 'FIPS 140-3 certificate #5586'
                  ' (validated 2026-11-13)',
    'approved_algorithms': ['ML-KEM', 'ML-DSA',
                            'SLH-DSA'],
    'claim_rule': 'Validated-module operation is'
                  ' claimed only where the check of'
                  ' record proves the validated module'
                  ' present and operated in approved'
                  ' mode; where only a standard'
                  ' OpenSSL 3.5 provider with the PQC'
                  ' algorithms is reachable, the'
                  ' algorithms are claimed without the'
                  ' FIPS claim; where neither is'
                  ' reachable, the native hash-based'
                  ' construction stands and the gap is'
                  ' recorded as environment-blocked.',
    'substrate_note': 'OpenSSL is the platform\'s'
                      ' existing system substrate'
                      ' (its TLS already runs on it),'
                      ' used as the cryptographic'
                      ' module and labeled as such —'
                      ' never presented as the'
                      ' Minotaur\'s own invention.',
}
CRYPTO_DETERMINATIONS = (
    'VALIDATED_MODULE_APPROVED_MODE',
    'SYSTEM_PQC_ALGORITHMS_NO_FIPS_CLAIM',
    'NATIVE_HASH_BASED_STANDS_ENVIRONMENT_BLOCKED',
)

# -- The completed defensive relationship (founder
# directive, 2026-11-26 11:12 MST) ------------------
#
# The Minotaur stands as INDEPENDENT INTEGRITY
# VERIFICATION over the three shields — three
# INDEPENDENT protective identities — drawing
# authenticated integrity evidence (code,
# configuration, identity, runtime) into independent
# assessment and protection (Detect, Contain,
# Restore, Verify) with continuous watchdog
# recovery; the structure stands over the bloodline
# three under permanent bloodline protection. The
# relationship joins the shields; it merges
# nothing, and every shield keeps its own identity.
# "Watchdog recovery" names the Minotaur's
# continuous recovery function — not a platform.
DEFENSIVE_RELATIONSHIP = {
    'title': 'The completed defensive relationship',
    'given': '2026-11-26',
    'role': 'INDEPENDENT_INTEGRITY_VERIFICATION',
    'role_verbatim': 'Independent integrity'
                     ' verification',
    'subtitle_verbatim': 'Independent integrity and'
                         ' continuous defense',
    'shields': [
        {'shield_id': 'sanders_labyrinth_shield',
         'name': 'Sanders Labyrinth Shield'},
        {'shield_id': 'labyrinth', 'name': 'LABYRINTH',
         'descriptor': 'Independent shield'},
        {'shield_id': 'sovereign_shield_v3',
         'name': 'Sovereign Shield V3'},
    ],
    'shields_identities_verbatim':
        'Three independent protective identities',
    'shields_independent': True,
    'platforms_merged': False,
    'evidence_verbatim': 'Authenticated Integrity'
                         ' Evidence',
    'evidence_kinds': ['CODE', 'CONFIGURATION',
                       'IDENTITY', 'RUNTIME'],
    'assessment_verbatim': 'Independent Assessment'
                           ' and Protection',
    'assessment_functions': ['DETECT', 'CONTAIN',
                             'RESTORE', 'VERIFY'],
    'recovery_verbatim': 'CONTINUOUS WATCHDOG'
                         ' RECOVERY',
    'recovery_note': 'Watchdog recovery names the'
                     ' Minotaur\'s continuous'
                     ' recovery function — not a'
                     ' platform, and no platform is'
                     ' renamed for it.',
    'stands_over': [
        {'platform': 'sanders_sentinel',
         'name': 'Sentinel',
         'protection': 'Life protection'},
        {'platform': 'the_godfather',
         'name': 'Godfather',
         'protection': 'Human survival'},
        {'platform': 'sanders_patriot_saint',
         'name': 'Patriot Saint',
         'protection': 'Legal protection'},
    ],
    'under_verbatim': 'PERMANENT BLOODLINE'
                      ' PROTECTION',
}
# The thirteen additional anti-probing protections
# of the same directive, verbatim, in the same
# governed-records pattern as the amendment's
# fifteen: each stands on its mechanism of record,
# its state derived from its checks of record.
ANTI_PROBING_PROTECTIONS = (
    {'protection': 'UNAUTHORIZED_RECONNAISSANCE_AND_PROBING',
     'verbatim': 'Unauthorized reconnaissance and'
                 ' infrastructure probing.',
     'mechanism': 'His surfaces answer only through'
                  ' the access guard; probing meets'
                  ' the same governed surface as any'
                  ' other access, and his decoys give'
                  ' reconnaissance something watched'
                  ' to find instead of something'
                  ' real.'},
    {'protection': 'NETWORK_AND_SERVICE_ENUMERATION',
     'verbatim': 'Network and service enumeration.',
     'mechanism': 'Nothing in his contract lists his'
                  ' internals to an unguarded caller:'
                  ' boards and records stand behind'
                  ' the role guard, and enumeration'
                  ' attempts are checks of record.'},
    {'protection': 'API_DISCOVERY_AND_UNAUTHORIZED_ENDPOINT_ACCESS',
     'verbatim': 'API discovery and unauthorized'
                 ' endpoint access.',
     'mechanism': 'His route forms answer 401'
                  ' unauthenticated by the'
                  ' application\'s established gate;'
                  ' an undiscovered endpoint is not'
                  ' an open one, and a discovered one'
                  ' still requires the operator.'},
    {'protection': 'AUTHENTICATION_BYPASS_AND_SESSION_HIJACKING',
     'verbatim': 'Authentication bypass and session'
                 ' hijacking.',
     'mechanism': 'He holds no session of his own to'
                  ' hijack: every act re-verifies the'
                  ' actor through the operator'
                  ' verifier at the moment of the'
                  ' act.'},
    {'protection': 'CREDENTIAL_THEFT_AND_BRUTE_FORCE',
     'verbatim': 'Credential theft and brute-force'
                 ' attempts.',
     'mechanism': 'A stolen or guessed credential'
                  ' that does not verify performs'
                  ' nothing; failed verification'
                  ' changes no state and writes no'
                  ' record of action.'},
    {'protection': 'ERROR_MESSAGE_INFORMATION_LEAKAGE',
     'verbatim': 'Information leakage through error'
                 ' messages.',
     'mechanism': 'His refusals name the rule, never'
                  ' the internals: denial messages'
                  ' state what the contract requires'
                  ' without disclosing stores, paths,'
                  ' or records.'},
    {'protection': 'TIMING_AND_SIDE_CHANNEL_ATTACKS',
     'verbatim': 'Timing and cryptographic'
                 ' side-channel attacks.',
     'mechanism': 'His signature verification'
                  ' compares digests in fixed form'
                  ' over recorded values, and his'
                  ' one-time keys are never reused —'
                  ' there is no oracle of repeated'
                  ' signing under one key to measure.'},
    {'protection': 'FORGED_INTERNAL_PLATFORM_IDENTITIES',
     'verbatim': 'Forged internal platform'
                 ' identities.',
     'mechanism': 'Platform-to-platform acts are'
                  ' records under the guard, never'
                  ' instructions: a record claiming'
                  ' a platform identity directs'
                  ' nothing, and his patrol verifies'
                  ' cores by hash, not by claimed'
                  ' identity.'},
    {'protection': 'DEFENSIVE_PATROL_MANIPULATION',
     'verbatim': 'Manipulation of defensive patrols.',
     'mechanism': 'His patrol sequencing derives'
                  ' from the signed chain head, not'
                  ' from any presented input: a'
                  ' manipulated request cannot'
                  ' reorder, skip, or aim his walk'
                  ' over the shields\' cores.'},
    {'protection': 'DEFENSIVE_CONFIGURATION_DISCOVERY',
     'verbatim': 'Unauthorized discovery of defensive'
                 ' configurations.',
     'mechanism': 'His baselines, pins, and policies'
                  ' of record are guarded reads for'
                  ' named roles; configuration is'
                  ' evidence for the defense, not a'
                  ' public surface.'},
    {'protection': 'RECOVERY_INFRASTRUCTURE_COMPROMISE',
     'verbatim': 'Compromise of his recovery'
                 ' infrastructure.',
     'mechanism': 'Recovery evidence is held in'
                  ' three places by design (patrol'
                  ' store, Glass-Box receipts, the'
                  ' operator-carried signed anchor):'
                  ' compromising one store does not'
                  ' compromise recovery.'},
    {'protection': 'DISABLE_OWN_PROTECTIONS_ATTACKS',
     'verbatim': 'Attacks intended to make him'
                 ' disable his own protections.',
     'mechanism': 'No record operation in his'
                  ' contract disables a protection —'
                  ' the amendment\'s anti-circumvention'
                  ' bar stands: there is nothing for'
                  ' such an attack to invoke.'},
    {'protection': 'MACHINERY_TURNED_AGAINST_AUTHORIZED_OPERATIONS',
     'verbatim': 'Attempts to turn his defensive'
                 ' machinery against legitimate'
                 ' Founder-authorized operations.',
     'mechanism': 'His machinery acts only on the'
                  ' operator\'s verified acts and'
                  ' its own records: anomalies accuse'
                  ' tampered cores, never the'
                  ' founder\'s operations, and'
                  ' clearance denial is a'
                  ' determination for the operator —'
                  ' not a weapon another caller can'
                  ' aim.'},
)


def _wots_digits(digest: bytes) -> list[int]:
    digits: list[int] = []
    for byte in digest:
        digits.append(byte >> 4)
        digits.append(byte & 0x0F)
    checksum = sum((_WOTS_W - 1) - d for d in digits)
    for shift in (8, 4, 0):
        digits.append((checksum >> shift) & 0x0F)
    return digits


# -- Complete architecture: eight domains, the
# functioning-defense standard, and the completeness
# accounting (founder directive, 2026-11-26 11:16
# MST) ----------------------------------------------
#
# "One important distinction: a named defense of
# record must become an actual functioning defensive
# capability, not remain merely a recorded
# protection." The eight domains organize his whole
# defensive construction; the exercise evidence
# names, per protection, whether the defense is
# exercised in code (and by which labeled
# attack-simulation test) or stands as a record
# (and why code exercise is not its honest form).
# The accounting lists every omission and exposure
# the record identifies — the founder's counts of
# record are 30 omissions and 15 exposures; their
# source enumerations are not in hand, no list is
# fabricated to match the counts, and reconciliation
# by name awaits the founder's source lists.
FUNCTIONING_STANDARD_VERBATIM = (
    'a named defense of record must become an actual'
    ' functioning defensive capability, not remain'
    ' merely a recorded protection')
DEFENSIVE_DOMAINS = (
    {'domain': 'SELF_PROTECTION',
     'scope': 'His identity, intelligence, code,'
              ' memory and runtime.',
     'members': 'the amendment\'s fifteen enumerated'
                ' protections; his self-integrity'
                ' pins; the operator lockout'},
    {'domain': 'ANTI_PROBING',
     'scope': 'Unauthorized reconnaissance,'
              ' enumeration and infrastructure'
              ' fingerprinting.',
     'members': 'the thirteen anti-probing'
                ' protections; decoys; uniform'
                ' refusal behavior'},
    {'domain': 'ANTI_CIRCUMVENTION',
     'scope': 'Attempts to bypass, manipulate or'
              ' disable his defenses.',
     'members': 'the amendment\'s anti-circumvention'
                ' bars; no record operation disables'
                ' a protection; forged-instruction'
                ' refusal'},
    {'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'scope': 'Keys, signatures, integrity chains'
              ' and post-quantum communications.',
     'members': 'WOTS+ one-time signatures under a'
                ' Merkle tree; the SHA3-256'
                ' attestation chain; the crypto'
                ' environment check and claim rule;'
                ' ML-KEM declared, route adopted'},
    {'domain': 'INFRASTRUCTURE_PROTECTION',
     'scope': 'Operating systems, networks,'
              ' deployment environments and'
              ' dependencies.',
     'members': 'native standard library only; no'
                ' third-party component; the'
                ' foundation-import prohibition'
                ' (never import a module whose import'
                ' can stall boot)'},
    {'domain': 'RECOVERY_PROTECTION',
     'scope': 'Authenticated restoration,'
              ' redundancy, failover and Watchdog'
              ' interoperability.',
     'members': 'recovery by reference to the signed'
                ' chain and the guarded record set;'
                ' three-place evidence hold;'
                ' continuous watchdog recovery'},
    {'domain': 'DEFENSIVE_CONTINUITY',
     'scope': 'Continuous patrols and preservation'
              ' of legitimate protective operations.',
     'members': 'the simultaneous shield patrol;'
                ' the anomaly lifecycle; clearance'
                ' determinations that advise the'
                ' operator and never gate the'
                ' founder\'s operations'},
    {'domain': 'COUNTER_MANIPULATION',
     'scope': 'Protection against attempts to'
              ' weaponize his own defenses against'
              ' himself or your bloodline.',
     'members': 'patrol sequencing derived from the'
                ' signed chain head, never from'
                ' presented input; machinery acts'
                ' only on verified operator acts and'
                ' its own records'},
)
# Exercise evidence per protection: ('CODE', the
# labeled attack-simulation test that exercises the
# function) or ('RECORD', why the defense's honest
# form is a record with the check that does run).
EXERCISE_EVIDENCE = {
    'COMPROMISED_ADMINISTRATIVE_CREDENTIALS':
        ('CODE', 'simulation: unverified operator is'
                 ' refused and locked out at the'
                 ' threshold'),
    'PRIVILEGE_ESCALATION':
        ('CODE', 'simulation: guarded reads cannot'
                 ' write; operator acts re-verify'),
    'MALICIOUS_INTERNAL_PLATFORM_COMMUNICATIONS':
        ('RECORD', 'records are never executed as'
                   ' instructions — an architectural'
                   ' property; the check that runs is'
                   ' the patrol\'s hash verification'
                   ' of cores, not of claims'),
    'COMPROMISED_RECOVERY_MECHANISMS':
        ('CODE', 'simulation: a tampered attestation'
                 ' fails chain verification, so a'
                 ' compromised recovery source is'
                 ' detected, not restored from'),
    'UNAUTHORIZED_CONFIGURATION_CHANGES':
        ('CODE', 'simulation: configuration of'
                 ' record changes only through'
                 ' verified operator acts'),
    'DENIAL_OF_SERVICE':
        ('RECORD', 'availability is an infrastructure'
                   ' property of the host, not of'
                   ' this service\'s code; the check'
                   ' that runs is the platform health'
                   ' verification on deploy'),
    'RESOURCE_EXHAUSTION':
        ('CODE', 'simulation: the one-time signature'
                 ' pool fails closed at exhaustion'
                 ' rather than reusing a key'),
    'SECURITY_LOG_TAMPERING':
        ('CODE', 'simulation: a tampered attestation'
                 ' payload breaks chain verification'
                 ' at its sequence'),
    'CLOCK_TIMESTAMP_MANIPULATION':
        ('CODE', 'simulation: chain order is sequence'
                 ' and hash linkage; verification'
                 ' does not consult the wall clock'),
    'COMPROMISED_CRYPTOGRAPHIC_RANDOMNESS':
        ('CODE', 'simulation: key derivation is'
                 ' deterministic from the seed by'
                 ' SHAKE-256; the same seed rebuilds'
                 ' the same tree'),
    'MALICIOUS_SOFTWARE_ROLLBACK':
        ('CODE', 'simulation: an altered shield core'
                 ' reads MISMATCH against its pin and'
                 ' raises an anomaly on patrol'),
    'UNAUTHORIZED_DISABLING_OF_DEFENSIVE_FUNCTIONS':
        ('CODE', 'simulation: the contract exposes no'
                 ' operation that disables a'
                 ' protection; the surface is'
                 ' enumerated and asserted'),
    'SINGLE_POINTS_OF_FAILURE':
        ('RECORD', 'the three-place evidence hold is'
                   ' an architectural fact (patrol'
                   ' store, Glass-Box receipts,'
                   ' operator-carried anchor); the'
                   ' check that runs is anchor'
                   ' comparison against the chain'),
    'THREAT_DETECTION_INTELLIGENCE_COMPROMISE':
        ('RECORD', 'detection records are receipted'
                   ' records under the same chain'
                   ' discipline; the check that runs'
                   ' is Sentinel\'s guarded-record'
                   ' verification over the directives'
                   ' and this platform\'s receipts'),
    'GOVERNING_DIRECTIVES_MODIFICATION':
        ('RECORD', 'his directives stand in the'
                   ' bloodline guarded record set;'
                   ' the check that runs is Sanders'
                   ' Sentinel\'s verification cycle'
                   ' against their manifest hashes'),
    'UNAUTHORIZED_RECONNAISSANCE_AND_PROBING':
        ('CODE', 'simulation: probing meets the'
                 ' uniform guarded surface and the'
                 ' watched decoys'),
    'NETWORK_AND_SERVICE_ENUMERATION':
        ('CODE', 'simulation: invalid and unknown'
                 ' requests receive the identical'
                 ' refusal — no enumeration oracle'),
    'API_DISCOVERY_AND_UNAUTHORIZED_ENDPOINT_ACCESS':
        ('CODE', 'simulation: his route forms answer'
                 ' 401 unauthenticated (production'
                 ' probes of record)'),
    'AUTHENTICATION_BYPASS_AND_SESSION_HIJACKING':
        ('CODE', 'simulation: no session exists to'
                 ' hijack; every act re-verifies the'
                 ' actor at the moment of the act'),
    'CREDENTIAL_THEFT_AND_BRUTE_FORCE':
        ('CODE', 'simulation: failed verifications'
                 ' bucket per actor and lock out at'
                 ' the threshold'),
    'ERROR_MESSAGE_INFORMATION_LEAKAGE':
        ('CODE', 'simulation: refusals are uniform in'
                 ' type and text across unlike'
                 ' invalid requests'),
    'TIMING_AND_SIDE_CHANNEL_ATTACKS':
        ('CODE', 'simulation: chain and claim'
                 ' comparisons use constant-time'
                 ' digest comparison; one-time keys'
                 ' are never reused'),
    'FORGED_INTERNAL_PLATFORM_IDENTITIES':
        ('CODE', 'simulation: a forged patrol'
                 ' instruction from an unverified'
                 ' actor is refused before any state'
                 ' change'),
    'DEFENSIVE_PATROL_MANIPULATION':
        ('CODE', 'simulation: the patrol sequence'
                 ' derives from the signed chain'
                 ' head; presented input cannot'
                 ' reorder it'),
    'DEFENSIVE_CONFIGURATION_DISCOVERY':
        ('CODE', 'simulation: baselines and policies'
                 ' are guarded reads; unguarded'
                 ' callers receive the uniform'
                 ' refusal'),
    'RECOVERY_INFRASTRUCTURE_COMPROMISE':
        ('CODE', 'simulation: recovery evidence in'
                 ' any one store can be checked'
                 ' against the operator-carried'
                 ' anchor; a rewritten store fails'),
    'DISABLE_OWN_PROTECTIONS_ATTACKS':
        ('CODE', 'simulation: the contract exposes no'
                 ' disabling operation to invoke'),
    'MACHINERY_TURNED_AGAINST_AUTHORIZED_OPERATIONS':
        ('CODE', 'simulation: machinery acts only on'
                 ' verified operator acts; an'
                 ' unverified attempt to aim it is'
                 ' refused with no state change'),
}
# The completeness accounting: every omission and
# exposure the examined record identifies, marked
# ALREADY_PROTECTED (with its functioning evidence)
# or CONSTRUCTION_REQUIRED (with what construction).
# The founder's counts of record — 30 omissions,
# 15 exposures — stand as his; this accounting
# covers what the record in hand identifies, and
# name-by-name reconciliation awaits his source
# lists.
COMPLETENESS_ACCOUNTING = (
    {'item': 'Quantum-resistant key exchange'
             ' (ML-KEM) not reachable from the'
             ' platform runtime',
     'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'status': 'CONSTRUCTION_REQUIRED',
     'basis': 'the adopted route (OpenSSL FIPS'
              ' Provider 3.5.9, certificate #5586)'
              ' is not present in the build'
              ' environment; the environment check'
              ' of record states the gap as'
              ' environment-blocked. Construction:'
              ' provision the validated module on'
              ' the host, then record a new check'},
    {'item': 'ML-DSA / SLH-DSA signing via a'
             ' validated module',
     'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'status': 'CONSTRUCTION_REQUIRED',
     'basis': 'same environment gap; until then'
              ' his signatures are the native WOTS+'
              ' hash-based construction, honestly'
              ' labeled, never claimed as FIPS'
              ' 204/205'},
    {'item': 'Production-environment crypto check'
             ' not yet recorded by the operator',
     'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'status': 'CONSTRUCTION_REQUIRED',
     'basis': 'the check is a capability of his'
              ' platform; the founder-operator'
              ' records it on the production host'
              ' (POST /api/minotaur/crypto-'
              'environment/check) and its'
              ' determination becomes the production'
              ' evidence of record. Note: the'
              ' production host runs OpenSSL 3.5.9'
              ' (deploy journal of record), but the'
              ' probe\'s scope is the Python'
              ' ssl/hashlib surface, which reaches'
              ' no PQC algorithm — the claim follows'
              ' the probe, not the host banner'},
    {'item': 'Ed25519 deprecation clock (NIST IR'
             ' 8547: deprecated after 2030,'
             ' disallowed after 2035) for Bozly\'s'
             ' receipts',
     'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'status': 'CONSTRUCTION_REQUIRED',
     'basis': 'recorded as a design intention only'
              ' in this build, per instruction: no'
              ' cryptography is migrated here and'
              ' Bozly is untouched; the migration'
              ' decision is the founder\'s, ahead'
              ' of the 2030 clock'},
    {'item': 'A shield platform (LABYRINTH) whose'
             ' contract stands SPECIFIED, not'
             ' enabled',
     'domain': 'DEFENSIVE_CONTINUITY',
     'status': 'ALREADY_PROTECTED',
     'basis': 'his patrol covers LABYRINTH\'s core'
              ' as it stands; enabling the'
              ' intelligence is the founder\'s'
              ' named approval, not a gap in the'
              ' Minotaur\'s protection'},
    {'item': 'Decoy reads are not natively'
             ' observable (only alteration and'
             ' disappearance are)',
     'domain': 'ANTI_PROBING',
     'status': 'ALREADY_PROTECTED',
     'basis': 'recorded honestly in the research'
              ' application: a touch that alters'
              ' or removes a decoy is a patrol'
              ' finding; silent reads leave the'
              ' bait under watch, which is the'
              ' deception design'},
    {'item': 'SSRF fetch discipline has no fetch'
             ' path to govern yet',
     'domain': 'INFRASTRUCTURE_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'no platform performs outbound'
              ' fetches; the resolve-validate-pin'
              ' discipline stands recorded in the'
              ' Labyrinth Shield\'s posture for any'
              ' future founder-designated path'},
    {'item': 'Authorization-abuse classes beyond'
             ' mass assignment (BOLA/BFLA) are'
             ' behavioral, not payload-shaped',
     'domain': 'SELF_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'his surfaces bind every act to the'
              ' verified actor and the role guard;'
              ' object-level abuse has no unguarded'
              ' object to reach. Behavioral'
              ' monitoring of legitimate-actor'
              ' misuse remains a records discipline'},
    {'item': 'Denial-of-service and host-level'
             ' availability attacks',
     'domain': 'INFRASTRUCTURE_PROTECTION',
     'status': 'CONSTRUCTION_REQUIRED',
     'basis': 'availability is a property of the'
              ' host and network, not of his code;'
              ' construction belongs to the'
              ' infrastructure layer (the deploy'
              ' health verification and watchdog'
              ' already watch it). His part —'
              ' bounded work per recorded cycle —'
              ' stands'},
    {'item': 'Foundation modules whose optional'
             ' imports can stall application boot'
             ' (the liboqs build triggered by'
             ' importing the Sovereign Shield V3'
             ' foundation)',
     'domain': 'INFRASTRUCTURE_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'found and fixed in this build: the'
              ' V3 service verifies its foundation'
              ' from hash-pinned source and never'
              ' imports it; boot reproduced clean'
              ' under production conditions before'
              ' the fix landed'},
    {'item': 'Bindings contract drift (a service'
             ' constructed in bindings without a'
             ' field in RuntimeBindings crashed'
             ' boot, 2026-11-26)',
     'domain': 'INFRASTRUCTURE_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'fixed in this build (the'
              ' sovereign_shield_v3 field) and a'
              ' regression test now guards the'
              ' contract in the suite of record'},
    {'item': 'The thirteen anti-probing'
             ' protections read as the full extent'
             ' of his responsibilities',
     'domain': 'ANTI_PROBING',
     'status': 'ALREADY_PROTECTED',
     'basis': 'the directive itself rules they are'
              ' a floor, never the extent; the'
              ' amendment\'s not-a-ceiling clause'
              ' stands in his design of record'},
    {'item': 'Forged Founder instructions'
             ' arriving as records or messages',
     'domain': 'ANTI_CIRCUMVENTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'only the verified operator performs'
              ' acts; a forged instruction is an'
              ' unverified actor and is refused'
              ' before any state change'
              ' (attack-simulation tested)'},
    {'item': 'Cryptographic downgrade presented'
             ' as an upgrade',
     'domain': 'CRYPTOGRAPHIC_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'claim assertion is enforced in'
              ' code against the check of record;'
              ' a claim above the evidence is'
              ' refused (attack-simulation tested)'},
    {'item': 'Recovery from a fully compromised'
             ' patrol store',
     'domain': 'RECOVERY_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'the operator-carried signed anchor'
              ' and the Glass-Box receipts stand'
              ' outside the store; a rewritten'
              ' store fails anchor comparison'},
    {'item': 'His own governing directives'
             ' altered outside the amendment path',
     'domain': 'SELF_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'the directives stand in the guarded'
              ' record set under Sanders Sentinel\'s'
              ' manifest-hash verification;'
              ' amendment is the only path of'
              ' change'},
    {'item': 'A fourth shield or a renamed shield'
             ' entering his patrol silently',
     'domain': 'DEFENSIVE_CONTINUITY',
     'status': 'ALREADY_PROTECTED',
     'basis': 'his patrol targets are the three'
              ' shields of the founder\'s orders,'
              ' enumerated in code; any change is a'
              ' code change under the same guarded'
              ' landing discipline'},
    {'item': 'Watchdog interoperability with the'
             ' host\'s service watchdog',
     'domain': 'RECOVERY_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'the host watchdog (sds-watchdog)'
              ' already restarts unresponsive'
              ' services; his continuous watchdog'
              ' recovery is the integrity layer'
              ' above it — the two are named'
              ' distinctly and neither impersonates'
              ' the other'},
    {'item': 'Shield self-protection — Sanders'
             ' Labyrinth Shield (its own identity,'
             ' code, configuration, intelligence,'
             ' credentials, recovery mechanisms)',
     'domain': 'SELF_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'functioning in its own machinery:'
              ' the inherited lockout exercised by'
              ' simulation; its foundation self-hash'
              ' audit pinned and compared in its'
              ' integrity machinery; governed'
              ' self-protection checks of record in'
              ' its own store; the Minotaur patrols'
              ' its core as the independent'
              ' verification layer (founder'
              ' acceptance criterion, 2026-11-26)'},
    {'item': 'Shield self-protection — LABYRINTH'
             ' (its own identity, code,'
             ' configuration, intelligence,'
             ' credentials, recovery mechanisms)',
     'domain': 'SELF_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'functioning in its own machinery:'
              ' the inherited lockout exercised by'
              ' simulation; its own core integrity'
              ' pin (SHA-256 of its module, compared'
              ' in constant time — a tampered or'
              ' rolled-back core reads MISMATCH);'
              ' governed self-protection checks of'
              ' record in its own store; the'
              ' Minotaur patrols its core as the'
              ' independent verification layer'
              ' (founder acceptance criterion,'
              ' 2026-11-26)'},
    {'item': 'Shield self-protection — Sovereign'
             ' Shield V3 (its own identity, code,'
             ' configuration, intelligence,'
             ' credentials, recovery mechanisms)',
     'domain': 'SELF_PROTECTION',
     'status': 'ALREADY_PROTECTED',
     'basis': 'functioning in its own machinery:'
              ' the inherited lockout exercised by'
              ' simulation; its integrity pin over'
              ' foundation and service hashes,'
              ' compared in constant time; governed'
              ' self-protection checks of record in'
              ' its own store; the Minotaur patrols'
              ' its core as the independent'
              ' verification layer (founder'
              ' acceptance criterion, 2026-11-26)'},
)

# -- Global benchmark mapping (founder directive,
# 2026-11-26 11:36 MST) ------------------------------
#
# "Ensure they are the best, most secure globally,"
# executed as control-for-control hardening against
# the top-tier global standard: every control in the
# sets gathered in the shield-upgrade research is
# mapped here and marked FUNCTIONING (exercised by
# test), RECORDED_WITH_REASON,
# NOT_APPLICABLE_WITH_REASON, or ENVIRONMENT_LIMITED
# (the limit in plain words, plus the founder
# decision that would lift it). No control is
# silently skipped; no standing is overstated. The
# internal attack-simulation suites are the
# continuous proof mechanism.
FOUNDER_BENCHMARK_DIRECTIVE_VERBATIM = (
    "We've got to ensure that they are")
BENCHMARK_STANDINGS = (
    'FUNCTIONING', 'RECORDED_WITH_REASON',
    'NOT_APPLICABLE_WITH_REASON', 'ENVIRONMENT_LIMITED')
BENCHMARK_CONTROLS = (
    # OWASP Top 10:2025 (web)
    {'set': 'OWASP_TOP_10_2025', 'control': 'A01_BROKEN_ACCESS_CONTROL',
     'standing': 'FUNCTIONING',
     'basis': 'per-platform access guards with fixed role scopes; per-act operator verification; SSRF indicators stand in this family in the packet evaluator — exercised across the suites'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A02_SECURITY_MISCONFIGURATION',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'the edge posture checklist stands of record in the Labyrinth Shield posture view (fifteen items); live verification is by presented evidence — these platforms do not reconfigure their host'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A03_SOFTWARE_SUPPLY_CHAIN_FAILURES',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'native standard library only — no third-party component exists in these platforms to attack; the foundation-import prohibition is enforced in code; interpreter patch level stands as a host record, not exercised by these suites'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A04_CRYPTOGRAPHIC_FAILURES',
     'standing': 'FUNCTIONING',
     'basis': 'SHA-3/SHAKE constructions, hash-chained signed attestations, constant-time comparisons — exercised; claims above the environment check are refused in code (the validated-module standing is carried separately below)'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A05_INJECTION',
     'standing': 'FUNCTIONING',
     'basis': 'ten indicator classes in the packet evaluator — CRLF/desync, SSTI, traversal in all encodings, log injection, NoSQL operator shapes — exercised in the shield suites'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A06_INSECURE_DESIGN',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'fail-closed design is of record in every platform contract (refuse-to-exist without audit; prohibited operations refused by name); design discipline is a record, not a test'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A07_AUTHENTICATION_FAILURES',
     'standing': 'FUNCTIONING',
     'basis': 'per-actor lockout buckets, credential-stuffing scoring (account diversity + success source), per-act re-verification — exercised by the attack simulations'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A08_SOFTWARE_AND_DATA_INTEGRITY_FAILURES',
     'standing': 'FUNCTIONING',
     'basis': 'integrity patrol over known-good baselines, hash pins compared in constant time, signed chain verification — exercised, including tamper simulations that break verification on cue'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A09_LOGGING_AND_ALERTING_FAILURES',
     'standing': 'FUNCTIONING',
     'basis': 'every state change writes its Glass-Box receipt in the same transaction; integrity failures surface as anomaly records on the operator\u2019s boards — exercised; no external dispatch exists, by the native-only law'},
    {'set': 'OWASP_TOP_10_2025', 'control': 'A10_MISHANDLING_OF_EXCEPTIONAL_CONDITIONS',
     'standing': 'FUNCTIONING',
     'basis': 'uniform refusals that leak nothing; the signer fails closed at leaf exhaustion; the evaluator rejects rather than errors open — exercised'},
    # OWASP API Security Top 10 (2023)
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API1_BROKEN_OBJECT_LEVEL_AUTHORIZATION',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'sequential cross-owner identifier and mass-assignment indicator classes stand in the packet evaluator; behavioral BOLA detection across owners is adapted in part — no cross-owner object store stands in the shields\u2019 own surfaces for it to exercise against'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API2_BROKEN_AUTHENTICATION',
     'standing': 'FUNCTIONING',
     'basis': 'the A07 machinery, at the API surface: lockout, stuffing signals, per-act verification — exercised'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API3_BROKEN_OBJECT_PROPERTY_LEVEL_AUTHORIZATION',
     'standing': 'FUNCTIONING',
     'basis': 'mass-assignment probes (unexpected privileged fields in presented bodies) are indicator-classified — exercised; every route form in these platforms also refuses unexpected fields by name'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API4_UNRESTRICTED_RESOURCE_CONSUMPTION',
     'standing': 'FUNCTIONING',
     'basis': 'identity-keyed buckets and bounded governed records — exercised; volumetric absorption at network scale is the environment cap named in the completeness accounting (denial of service entry)'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API5_BROKEN_FUNCTION_LEVEL_AUTHORIZATION',
     'standing': 'FUNCTIONING',
     'basis': 'function-level acts are operator-only and re-verified per act; a forged instruction is refused before any state change — exercised by simulation'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API6_UNRESTRICTED_ACCESS_TO_SENSITIVE_BUSINESS_FLOWS',
     'standing': 'NOT_APPLICABLE_WITH_REASON',
     'basis': 'the shields and the Minotaur expose no public business flows — no booking, purchase, or signup endpoint stands in their surfaces; the flagship storefront\u2019s flows are outside this benchmark\u2019s platforms'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API7_SERVER_SIDE_REQUEST_FORGERY',
     'standing': 'FUNCTIONING',
     'basis': 'SSRF-shaped targets (internal, metadata, encoded forms) are classified and rejected by indicator without DNS or fetch — exercised; no component of these platforms fetches at all, and the resolve-classify-pin discipline stands of record for any future fetch'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API8_SECURITY_MISCONFIGURATION',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'as A02: the posture checklist of record, verified by presented evidence'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API9_IMPROPER_INVENTORY_MANAGEMENT',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'the platform registry and each shield\u2019s contract enumerate their own surfaces of record; inventory is a governed record in this ecosystem, not an exercised function'},
    {'set': 'OWASP_API_TOP_10_2023', 'control': 'API10_UNSAFE_CONSUMPTION_OF_APIS',
     'standing': 'NOT_APPLICABLE_WITH_REASON',
     'basis': 'these platforms consume no third-party APIs and make no outbound connections — there is no consumption surface to make unsafe'},
    # NIST SP 800-207 — the seven tenets
    {'set': 'NIST_SP_800_207', 'control': 'TENET_1_EVERY_RESOURCE_HAS_AN_ACCESS_DECISION',
     'standing': 'FUNCTIONING',
     'basis': 'every platform surface in this build answers through its own access guard with named role scopes — exercised'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_2_ALL_COMMUNICATION_SECURED_REGARDLESS_OF_LOCATION',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'platforms prove themselves by identity and records, never by loopback position — of record in the ecosystem law; transport security itself is the host TLS layer, recorded at the edge entries below, not exercised by these suites'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_3_ACCESS_GRANTED_PER_SESSION',
     'standing': 'FUNCTIONING',
     'basis': 'stronger than per-session in these platforms: the actor is verified at the moment of every act and no session stands to persist — exercised'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_4_DYNAMIC_POLICY_FROM_OBSERVABLE_STATE',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'LABYRINTH communication policies are governed records with observe-then-enforce discipline; device posture is not an input that exists in this environment, and no posture feed is represented'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_5_CONTINUOUS_MONITORING_OF_INTEGRITY_AND_POSTURE',
     'standing': 'FUNCTIONING',
     'basis': 'the simultaneous patrol, the posture views, and the anomaly lifecycle — exercised'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_6_AUTHENTICATION_AND_AUTHORIZATION_BEFORE_ACCESS',
     'standing': 'FUNCTIONING',
     'basis': 'guards evaluate before any record is read or written in these platforms — exercised, including the application gate answering 401 before dispatch'},
    {'set': 'NIST_SP_800_207', 'control': 'TENET_7_TELEMETRY_FED_BACK_INTO_POLICY',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'telemetry is receipted and surfaced to the operator; policy changes remain the operator\u2019s recorded acts — by design in this ecosystem, automation of policy is not claimed'},
    # NIST SP 800-53 controls as cited in the research
    {'set': 'NIST_SP_800_53', 'control': 'AU_9_PROTECTION_OF_AUDIT_INFORMATION',
     'standing': 'FUNCTIONING',
     'basis': 'receipts written in the same transaction as every act; alteration of patrolled records generates anomaly records on the operator\u2019s surfaces — exercised by tamper simulation'},
    {'set': 'NIST_SP_800_53', 'control': 'AU_9_3_CRYPTOGRAPHIC_PROTECTION_OF_AUDIT_INFORMATION',
     'standing': 'FUNCTIONING',
     'basis': 'the exercised form is hash-based: WOTS+ one-time signatures under a Merkle tree over a SHA3-256 chain, verified end-to-end in the suites; the validated-module asymmetric form is carried at the FIPS entry below'},
    {'set': 'NIST_SP_800_53', 'control': 'SI_7_SOFTWARE_FIRMWARE_AND_INFORMATION_INTEGRITY',
     'standing': 'FUNCTIONING',
     'basis': 'file-integrity patrol over known-good baselines with authorized re-baseline only; a tampered shield core raises an ALTERED anomaly — exercised (the research flags SI-7\u2019s enhancement text as not re-read at the primary source in its pass)'},
    {'set': 'NIST_SP_800_53', 'control': 'IA_13_TOKEN_AND_ASSERTION_PROTECTION',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'no bearer-token surface stands in the shields or the Minotaur — authority is the per-act operator verification, so token replay has no session to replay; the underlying IR 8587\u2019s exact release year stands flagged-unverified in the research of record'},
    # CISA practice
    {'set': 'CISA_PRACTICE', 'control': 'ZERO_TRUST_MATURITY_MODEL_V2_STAGED_ASSESSMENT',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'a yardstick is recorded, not exercised: of record, Identity and Applications stand advanced-ward by the functioning controls above; Devices and Data name no stage beyond what the records prove (the model itself is archived-content at CISA, cited as method)'},
    {'set': 'CISA_PRACTICE', 'control': 'MICROSEGMENTATION_OBSERVE_THEN_ENFORCE',
     'standing': 'FUNCTIONING',
     'basis': 'LABYRINTH communication policies: flows are OBSERVED violations until an ENFORCE policy of record refuses them — exercised end-to-end in the suites'},
    {'set': 'CISA_PRACTICE', 'control': 'DECOYS_AND_HONEYTOKENS_AS_DETECTION',
     'standing': 'FUNCTIONING',
     'basis': 'decoys planted under isolation rules; a touched decoy is an anomaly finding on patrol — exercised (the research read the CISA decoys guidance via a secondary summary, flagged there)'},
    # Edge / TLS (research Area 4)
    {'set': 'EDGE_AND_TLS', 'control': 'TLSREF_MOZILLA_INTERMEDIATE_TLS',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'the TLS checklist (1.2+1.3 only, AEAD suites, tickets off, HSTS 63072000) stands in the Labyrinth Shield posture checklist of record; the live proxy configuration is a host fact verified by presented evidence, outside these platforms\u2019 machinery'},
    {'set': 'EDGE_AND_TLS', 'control': 'OWASP_SECURITY_HEADERS_SET',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'the corrected header set (including X-XSS-Protection: 0 and no Server leak) stands in the same posture checklist of record; header emission is the application/proxy layer\u2019s standing behavior, verified by evidence'},
    {'set': 'EDGE_AND_TLS', 'control': 'HYBRID_PQ_KEY_EXCHANGE_X25519MLKEM768',
     'standing': 'ENVIRONMENT_LIMITED',
     'basis': 'the production host\u2019s OpenSSL is 3.5.9, which can offer the hybrid group — but the proxy\u2019s group list of record does not offer it first today',
     'limit': 'the hybrid post-quantum group is not enabled in the live proxy configuration, so recorded TLS traffic does not yet gain harvest-now-decrypt-later protection at the edge',
     'founder_decision': 'the founder\u2019s go to set X25519MLKEM768 first in the proxy\u2019s group list on his host — a configuration change, no purchase, no new component'},
    # Post-quantum route (research Areas 3.4, 5.1)
    {'set': 'POST_QUANTUM_ROUTE', 'control': 'FIPS_140_3_VALIDATED_PQC_OPERATION',
     'standing': 'ENVIRONMENT_LIMITED',
     'basis': 'the adopted route stands of record (OpenSSL FIPS Provider 3.5.9, FIPS 140-3 certificate #5586, ML-KEM/ML-DSA/SLH-DSA approved); the environment check of record proves the runtime reaches no PQC algorithm and no FIPS provider stands loaded, so validated operation is not claimed',
     'limit': 'post-quantum key establishment and validated-module signatures cannot run in the current runtime environment; the native hash-based construction stands in their place',
     'founder_decision': 'the founder\u2019s direction to provision the validated module in approved mode on the production host (and to record the production environment check), or to designate another runtime that reaches it'},
    {'set': 'POST_QUANTUM_ROUTE', 'control': 'NIST_IR_8547_ED25519_DEPRECATION_CLOCK',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'recorded as a design intention only, per the founder\u2019s boundary for this build: Ed25519 (Bozly receipts, platform credentials) is deprecated after 2030 and disallowed after 2035; no cryptography is migrated in this build and Bozly is untouched'},
    # PCI DSS floor as cited in the research
    {'set': 'PCI_DSS_FLOOR', 'control': 'REQ_10_3_4_LOG_ALTERATION_GENERATES_ALERTS',
     'standing': 'FUNCTIONING',
     'basis': 'alteration of a patrolled record generates an anomaly on the operator\u2019s surfaces — the mechanism-free property the requirement names, exercised by tamper simulation'},
    {'set': 'PCI_DSS_FLOOR', 'control': 'REQ_11_5_FILE_INTEGRITY_CHANGE_DETECTION',
     'standing': 'FUNCTIONING',
     'basis': 'the patrol itself: scheduled and on-event comparison against known-good baselines — exercised'},
    # Python stdlib discipline (research Area 5.3)
    {'set': 'RUNTIME_DISCIPLINE', 'control': 'STDLIB_CVE_AND_PARSER_SURFACE_DISCIPLINE',
     'standing': 'RECORDED_WITH_REASON',
     'basis': 'no untrusted archive extraction exists in these platforms; presented payloads are bounded governed records, which blunts the parser-DoS class; the interpreter patch level stands as a host record — the discipline is of record, not exercised by these suites'},
)


class _MinotaurHashSigner:
    """The Minotaur's own hash-based signature scheme.

    Keys are derived deterministically from one 32-byte seed:
    per-leaf secret elements and the public seed come from
    SHAKE-256 domain-separated derivation under the
    Minotaur's own domain strings, each public element is its
    secret element pushed through a masked Winternitz chain
    (RFC 8391 construction), each Merkle leaf is the SHA-256
    of one leaf's public elements, and the tree root is the
    public identity signatures verify against. One-time
    discipline is the caller's state to keep: a leaf that has
    signed once never signs again.
    """

    def __init__(self, seed: bytes) -> None:
        if not isinstance(seed, (bytes, bytearray)) \
                or len(seed) != 32:
            raise ValueError('Hash signature seed must be 32'
                             ' bytes')
        self._seed = bytes(seed)
        self._pub_seed = hashlib.shake_256(
            self._seed + b'|minotaur-wots-pubseed|').digest(32)
        self._leaf_hashes: list[bytes] = []
        self._leaf_pubkeys: list[list[bytes]] = []
        for leaf in range(_LEAVES):
            pubkey = [
                self._chain(self._secret(leaf, i), leaf, i, 0,
                            _WOTS_W - 1)
                for i in range(_WOTS_LEN)]
            self._leaf_pubkeys.append(pubkey)
            self._leaf_hashes.append(
                hashlib.sha256(b''.join(pubkey)).digest())
        self._tree: list[list[bytes]] = [self._leaf_hashes]
        while len(self._tree[-1]) > 1:
            level = self._tree[-1]
            self._tree.append([
                hashlib.sha256(level[i] + level[i + 1]).digest()
                for i in range(0, len(level), 2)
            ])
        self.root = self._tree[-1][0]

    def _secret(self, leaf: int, chain_index: int) -> bytes:
        return hashlib.shake_256(
            self._seed + b'|minotaur-wots-sk|'
            + leaf.to_bytes(4, 'big')
            + chain_index.to_bytes(2, 'big')).digest(32)

    def _chain(self, x: bytes, leaf: int, chain_index: int,
               start: int, steps: int) -> bytes:
        adrs = (leaf.to_bytes(4, 'big')
                + chain_index.to_bytes(4, 'big')
                + (0).to_bytes(4, 'big'))
        for step in range(start, start + steps):
            mask = hashlib.sha256(
                self._pub_seed + adrs
                + step.to_bytes(4, 'big')).digest()
            x = hashlib.sha256(
                bytes(a ^ b for a, b in zip(x, mask))).digest()
        return x

    def _auth_path(self, leaf: int) -> list[bytes]:
        path = []
        index = leaf
        for level in self._tree[:-1]:
            path.append(level[index ^ 1])
            index //= 2
        return path

    def sign(self, message: bytes, leaf_index: int) -> dict:
        if not 0 <= leaf_index < _LEAVES:
            raise ValueError('Leaf index out of range')
        digest = hashlib.sha256(message).digest()
        digits = _wots_digits(digest)
        elements = [
            self._chain(self._secret(leaf_index, i), leaf_index,
                        i, 0, digits[i])
            for i in range(_WOTS_LEN)]
        return {
            'scheme': 'WOTS+ (SHA-256, w=16) under SHA-256'
                      ' Merkle tree',
            'leaf_index': leaf_index,
            'pub_seed': self._pub_seed.hex(),
            'root': self.root.hex(),
            'elements': [e.hex() for e in elements],
            'auth_path': [p.hex() for p in self._auth_path(
                leaf_index)],
        }

    @staticmethod
    def verify(message: bytes, signature, trusted_root=None
               ) -> bool:
        try:
            leaf_index = int(signature['leaf_index'])
            pub_seed = bytes.fromhex(signature['pub_seed'])
            elements = [bytes.fromhex(e)
                        for e in signature['elements']]
            auth_path = [bytes.fromhex(p)
                         for p in signature['auth_path']]
            root_hex = str(signature['root'])
        except (KeyError, TypeError, ValueError):
            return False
        if len(elements) != _WOTS_LEN \
                or len(auth_path) != _TREE_HEIGHT:
            return False
        if trusted_root is not None and root_hex != trusted_root:
            return False

        def chain(x, chain_index, start, steps):
            adrs = (leaf_index.to_bytes(4, 'big')
                    + chain_index.to_bytes(4, 'big')
                    + (0).to_bytes(4, 'big'))
            for step in range(start, start + steps):
                mask = hashlib.sha256(
                    pub_seed + adrs
                    + step.to_bytes(4, 'big')).digest()
                x = hashlib.sha256(
                    bytes(a ^ b for a, b in zip(x, mask))).digest()
            return x

        digest = hashlib.sha256(message).digest()
        digits = _wots_digits(digest)
        pubkey = [
            chain(elements[i], i, digits[i],
                  (_WOTS_W - 1) - digits[i])
            for i in range(_WOTS_LEN)]
        node = hashlib.sha256(b''.join(pubkey)).digest()
        index = leaf_index
        for sibling in auth_path:
            if index % 2 == 0:
                node = hashlib.sha256(node + sibling).digest()
            else:
                node = hashlib.sha256(sibling + node).digest()
            index //= 2
        return node.hex() == root_hex


class MinotaurDenied(Exception):
    """The requested Minotaur operation is not allowed."""


class MinotaurForbidden(Exception):
    """The actor lacks authority for the requested operation."""


class MinotaurService:
    """Durable, receipted Minotaur patrol over the protected targets."""

    def __init__(self, database_path, workspace_root, operator_verifier,
                 audit, *, sentinel=None, signing_seed=None,
                 lockout_threshold=5, lockout_window_seconds=900,
                 clock=time.time):
        if audit is None or not callable(getattr(audit, 'preserve', None)):
            raise MinotaurDenied(
                'RTSA Minotaur requires a working Glass-Box audit adapter')
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._root = Path(workspace_root)
        self.operator_verifier = operator_verifier
        self._audit = audit
        self._lockout_threshold = lockout_threshold
        self._lockout_window = lockout_window_seconds
        self._sentinel = sentinel if sentinel is not None else MinotaurSentinel()
        self._clock = clock
        self.identity = IDENTITY
        self.geofence = GeofencePolicy(IDENTITY)
        self.guard = AccessGuard(audit, 'minotaur_sentinel', {
            'OPERATOR': {'PATROL'},
            'AUDITOR': {'PATROL'},
        })
        with self._connect() as db:
            ensure_checkin_schema(db)
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS minotaur_baselines (
                    target TEXT PRIMARY KEY,
                    pinned_hash TEXT NOT NULL,
                    pinned_by TEXT NOT NULL,
                    pinned_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_patrols (
                    patrol_id TEXT PRIMARY KEY,
                    patrolled_at REAL NOT NULL,
                    patrolled_by TEXT NOT NULL,
                    targets_checked INTEGER NOT NULL,
                    unpinned INTEGER NOT NULL,
                    anomalies_found INTEGER NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_anomalies (
                    anomaly_id TEXT PRIMARY KEY,
                    patrol_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS minotaur_anomalies_open_idx
                    ON minotaur_anomalies (target, kind, status);
                CREATE TABLE IF NOT EXISTS minotaur_clearances (
                    clearance_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    determination TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    patrol_id TEXT,
                    open_anomalies INTEGER NOT NULL,
                    issued_by TEXT NOT NULL,
                    issued_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_shield_baselines (
                    shield_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    pinned_hash TEXT NOT NULL,
                    pinned_by TEXT NOT NULL,
                    pinned_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL,
                    PRIMARY KEY (shield_id, target)
                );
                CREATE TABLE IF NOT EXISTS minotaur_shield_patrols (
                    patrol_id TEXT PRIMARY KEY,
                    patrolled_at REAL NOT NULL,
                    patrolled_by TEXT NOT NULL,
                    shields_covered INTEGER NOT NULL,
                    targets_checked INTEGER NOT NULL,
                    unpinned INTEGER NOT NULL,
                    anomalies_found INTEGER NOT NULL,
                    sequence TEXT NOT NULL,
                    attestation_seq INTEGER,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_decoys (
                    decoy_id TEXT PRIMARY KEY,
                    shield_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    note TEXT NOT NULL,
                    pinned_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    planted_by TEXT NOT NULL,
                    planted_at REAL NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_attestations (
                    seq INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    signature TEXT,
                    merkle_root TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_signing_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    seed_hex TEXT NOT NULL,
                    seed_source TEXT NOT NULL,
                    merkle_root TEXT NOT NULL,
                    used_leaves TEXT NOT NULL,
                    chain_head TEXT NOT NULL,
                    chain_length INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS
                minotaur_self_protection_checks (
                    check_id TEXT PRIMARY KEY,
                    protection_key TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_crypto_checks (
                    check_id TEXT PRIMARY KEY,
                    openssl_version TEXT NOT NULL,
                    openssl_version_info TEXT NOT NULL,
                    fips_provider_state TEXT NOT NULL,
                    pqc_reachable TEXT NOT NULL,
                    determination TEXT NOT NULL,
                    probe_scope TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    recorded_at REAL NOT NULL,
                    receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS minotaur_auth_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    failed_at REAL NOT NULL
                );
                """
            )
        self._init_signing(signing_seed)

    # -- the Minotaur's quantum layer (his upgrade, 2026-11-26) --------

    def _init_signing(self, signing_seed):
        """Resolve the hash-signature seed and open the signing
        state. A supplied or environment seed opens a new
        one-time epoch when it differs from the stored one
        (used leaves reset under the new root; the attestation
        chain carries over — it is content, not keys, and each
        attestation records the root it was signed under)."""
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM minotaur_signing_state WHERE id = 1',
            ).fetchone()
        supplied, source = None, None
        if signing_seed is not None:
            supplied, source = bytes(signing_seed), \
                'supplied_to_constructor'
        else:
            env_hex = os.environ.get(_SIGNING_SEED_ENV)
            if env_hex:
                try:
                    raw = bytes.fromhex(env_hex.strip())
                except ValueError:
                    raw = b''
                if len(raw) == 32:
                    supplied, source = raw, (
                        'environment:' + _SIGNING_SEED_ENV)
        if row is not None and (
                supplied is None
                or supplied.hex() == row['seed_hex']):
            self._signer = _MinotaurHashSigner(
                bytes.fromhex(row['seed_hex']))
            self._seed_source = row['seed_source']
            return
        if supplied is None:
            supplied = os.urandom(32)
            source = 'generated_into_patrol_store'
        self._signer = _MinotaurHashSigner(supplied)
        self._seed_source = source
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                if row is None:
                    db.execute(
                        'INSERT INTO minotaur_signing_state (id,'
                        ' seed_hex, seed_source, merkle_root,'
                        ' used_leaves, chain_head, chain_length)'
                        ' VALUES (1, ?, ?, ?, ?, ?, ?)',
                        (supplied.hex(), source,
                         self._signer.root.hex(), '[]',
                         _ATTESTATION_GENESIS, 0),
                    )
                else:
                    db.execute(
                        'UPDATE minotaur_signing_state SET'
                        ' seed_hex = ?, seed_source = ?,'
                        ' merkle_root = ?, used_leaves = ?'
                        ' WHERE id = 1',
                        (supplied.hex(), source,
                         self._signer.root.hex(), '[]'),
                    )
                db.commit()
            except Exception:
                db.rollback()
                raise

    def _signing_state(self, db):
        return db.execute(
            'SELECT * FROM minotaur_signing_state WHERE id = 1',
        ).fetchone()

    def _append_attestation(self, db, kind, payload, actor):
        """Append one signed, hash-chained attestation inside
        the caller's transaction. The chain hash is SHA3-256
        over the previous head and the canonical payload; the
        signature is the Minotaur's own WOTS+ over the chain
        hash, from the next unused one-time leaf — a leaf that
        has signed once never signs again, and exhaustion
        fails closed."""
        state = self._signing_state(db)
        used = json.loads(state['used_leaves'])
        leaf = next(
            (i for i in range(_LEAVES) if i not in used), None)
        if leaf is None:
            raise MinotaurDenied(
                'Hash-signature one-time key pool exhausted for'
                ' this seed epoch; refusing to reuse a one-time'
                ' key. The owner rotates the seed to open a new'
                ' epoch.')
        seq = int(state['chain_length'])
        prev = state['chain_head']
        now = self._now()
        body = {
            'seq': seq, 'kind': kind, 'at': now,
            'payload': payload,
        }
        canonical = json.dumps(
            body, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True).encode('utf-8')
        digest = hashlib.sha3_256(
            bytes.fromhex(prev) + canonical).hexdigest()
        signature = self._signer.sign(bytes.fromhex(digest),
                                      leaf)
        receipt_id = self._record(
            'MINOTAUR_ATTESTATION', actor=actor,
            attestation_seq=seq, kind=kind, hash=digest,
            merkle_root=self._signer.root.hex())
        db.execute(
            'INSERT INTO minotaur_attestations (seq, kind,'
            ' payload, prev_hash, hash, signature, merkle_root,'
            ' created_at, receipt_id) VALUES'
            ' (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (seq, kind, json.dumps(payload, sort_keys=True),
             prev, digest, json.dumps(signature),
             self._signer.root.hex(), now, receipt_id),
        )
        db.execute(
            'UPDATE minotaur_signing_state SET used_leaves = ?,'
            ' chain_head = ?, chain_length = ? WHERE id = 1',
            (json.dumps(sorted(used + [leaf])), digest, seq + 1),
        )
        return {
            'seq': seq, 'kind': kind, 'hash': digest,
            'prev_hash': prev,
            'merkle_root': self._signer.root.hex(),
            'signature': signature, 'receipt_id': receipt_id,
        }

    def verify_attestation_chain(self, actor, role, *,
                                 region=None):
        """Walk the attestation chain and verify every link
        and every signature. Returns the first break, by
        sequence, when the chain does not verify."""
        self._geo(region)
        self._guard_access(actor, role, 'attestations',
                           'attestation chain verification')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_attestations ORDER BY seq',
            ).fetchall()
        prev = _ATTESTATION_GENESIS
        for expected, row in enumerate(rows):
            payload = json.loads(row['payload'])
            body = {
                'seq': row['seq'], 'kind': row['kind'],
                'at': row['created_at'], 'payload': payload,
            }
            canonical = json.dumps(
                body, sort_keys=True, separators=(',', ':'),
                ensure_ascii=True).encode('utf-8')
            digest = hashlib.sha3_256(
                bytes.fromhex(prev) + canonical).hexdigest()
            if row['seq'] != expected or not hmac.compare_digest(
                    row['prev_hash'], prev):
                return {'valid': False, 'records': len(rows),
                        'broken_at': expected,
                        'reason': 'chain linkage broken'}
            if not hmac.compare_digest(digest, row['hash']):
                return {'valid': False, 'records': len(rows),
                        'broken_at': expected,
                        'reason': 'attestation content altered'}
            signature = json.loads(row['signature']) \
                if row['signature'] else None
            if signature is None or not _MinotaurHashSigner.verify(
                    bytes.fromhex(digest), signature,
                    trusted_root=row['merkle_root']):
                return {'valid': False, 'records': len(rows),
                        'broken_at': expected,
                        'reason': 'attestation signature does not'
                                ' verify'}
            prev = digest
        return {'valid': True, 'records': len(rows),
                'chain_head': prev, 'reason': None}

    def shield_anchor(self, actor, role, *, region=None):
        """The current signed chain head and Merkle root — the
        anchor copy the operator carries off the host, so a
        rewritten history must also rewrite the anchor
        (research Area 3.2)."""
        self._geo(region)
        self._guard_access(actor, role, 'anchor', 'anchor view')
        with self._connect() as db:
            state = self._signing_state(db)
            latest = db.execute(
                'SELECT seq, hash, merkle_root FROM'
                ' minotaur_attestations ORDER BY seq DESC'
                ' LIMIT 1').fetchone()
        return {
            'merkle_root': state['merkle_root'],
            'chain_head': state['chain_head'],
            'chain_length': state['chain_length'],
            'latest_attestation_seq':
                latest['seq'] if latest else None,
            'latest_attestation_hash':
                latest['hash'] if latest else None,
            'seed_source': state['seed_source'],
            'note': 'Carry this anchor off the host: an'
                    ' unsigned, self-held chain is evidence'
                    ' only against careless tampering; the'
                    ' signed head, anchored externally, is'
                    ' what makes a rewritten history'
                    ' detectable.',
        }

    def quantum_status(self) -> dict:
        with self._connect() as db:
            state = self._signing_state(db)
        used = json.loads(state['used_leaves'])
        return {
            'signatures': QUANTUM_SCHEME,
            'merkle_root': state['merkle_root'],
            'one_time_leaves_total': _LEAVES,
            'one_time_leaves_used': len(used),
            'seed_source': state['seed_source'],
            'attestation_chain_length': state['chain_length'],
            'attestation_chain_head': state['chain_head'],
            'key_exchange': QUANTUM_KEY_EXCHANGE,
        }

    # -- plumbing ---------------------------------------------------

    def _connect(self):
        db = sqlite3.connect(self._path, timeout=10,
                             isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def _now(self) -> float:
        return float(self._clock())

    def _check_actor(self, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise MinotaurForbidden('A non-empty actor is required')

    def _is_operator(self, actor):
        try:
            return self.operator_verifier(actor) is True
        except Exception:
            return False

    def _require_operator(self, actor):
        """Verify the operator before any state-changing
        act — with functioning brute-force resistance:
        failed verifications are bucketed per actor,
        and at the lockout threshold the actor is
        refused outright until the window clears, even
        if a later attempt would verify. A successful
        verification clears the actor's bucket. The
        refusal is uniform: it names the rule, never
        the internals."""
        self._check_actor(actor)
        now = self._now()
        with self._connect() as db:
            failures = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' minotaur_auth_failures WHERE actor = ?'
                ' AND failed_at > ?',
                (actor, now - self._lockout_window),
            ).fetchone()['n']
        if failures >= self._lockout_threshold:
            raise MinotaurForbidden(
                'Operator authority is required for this'
                ' operation')
        if self._is_operator(actor):
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE;')
                try:
                    db.execute(
                        'DELETE FROM minotaur_auth_failures'
                        ' WHERE actor = ?', (actor,))
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            return
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                db.execute(
                    'INSERT INTO minotaur_auth_failures'
                    ' (actor, failed_at) VALUES (?, ?)',
                    (actor, now))
                db.commit()
            except Exception:
                db.rollback()
                raise
        raise MinotaurForbidden(
            'Operator authority is required for this operation')

    def _record(self, event, **fields):
        return self._audit.preserve(event, **fields)

    def _geo(self, region):
        # The geofence binds a declared jurisdiction. Surfaces that
        # declare none (the session-bound HTTP family declares no
        # jurisdiction field) pass None; wherever a jurisdiction IS
        # declared, the foundation policy decides, fail-closed.
        if region is None:
            return
        decision = self.geofence.evaluate(region)
        if decision != 'ALLOW':
            raise MinotaurForbidden(
                f'Geofence {decision} for declared jurisdiction'
                f' {region!r}')

    def _guard_access(self, actor, role, record_ref, purpose):
        self._check_actor(actor)
        try:
            self.guard.access(actor, role, 'PATROL', record_ref,
                              purpose=purpose)
        except FoundationForbidden as exc:
            raise MinotaurForbidden(str(exc)) from exc
        except FoundationDenied as exc:
            raise MinotaurDenied(str(exc)) from exc

    def _current_hash(self, target: str) -> str:
        # The recovered sentinel's own hash engine, over the target
        # resolved against this service's workspace root.
        return self._sentinel.compute_target_hash(
            str(self._root / target))

    @staticmethod
    def _anomaly_view(row):
        return {
            'anomaly_id': row['anomaly_id'],
            'patrol_id': row['patrol_id'],
            'target': row['target'],
            'kind': row['kind'],
            'status': row['status'],
            'detected_at': row['detected_at'],
            'updated_by': row['updated_by'],
            'updated_at': row['updated_at'],
            'receipt_id': row['receipt_id'],
        }

    @staticmethod
    def _clearance_view(row):
        return {
            'clearance_id': row['clearance_id'],
            'subject': row['subject'],
            'determination': row['determination'],
            'reason': row['reason'],
            'patrol_id': row['patrol_id'],
            'open_anomalies': row['open_anomalies'],
            'issued_by': row['issued_by'],
            'issued_at': row['issued_at'],
            'receipt_id': row['receipt_id'],
        }

    # -- baselines ----------------------------------------------------

    def targets(self, actor, role, *, region=None):
        """Every protected target with its pin and live state."""
        self._geo(region)
        self._guard_access(actor, role, 'targets', 'targets view')
        with self._connect() as db:
            pins = {
                row['target']: row
                for row in db.execute('SELECT * FROM minotaur_baselines')
            }
        result = []
        for target in TARGETS:
            current = self._current_hash(target)
            pin = pins.get(target)
            if pin is None:
                state = 'UNPINNED'
                pinned_hash = None
            else:
                pinned_hash = pin['pinned_hash']
                if current == 'FILE_MISSING':
                    state = 'MISSING'
                elif current == pinned_hash:
                    state = 'MATCH'
                else:
                    state = 'MISMATCH'
            result.append({
                'target': target,
                'state': state,
                'pinned_hash': pinned_hash,
                'current_hash': current,
            })
        return result

    def pin_baseline(self, actor, target, *, region=None):
        """Pin one target's current hash as its baseline (operator)."""
        self._geo(region)
        self._require_operator(actor)
        if target not in TARGETS:
            raise MinotaurDenied(f'Not a protected target: {target!r}')
        current = self._current_hash(target)
        if current == 'FILE_MISSING':
            raise MinotaurDenied(
                f'Cannot pin a missing target: {target}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_BASELINE_PINNED', actor=actor, target=target,
                    pinned_hash=current)
                db.execute(
                    'INSERT INTO minotaur_baselines (target, pinned_hash,'
                    ' pinned_by, pinned_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?)'
                    ' ON CONFLICT(target) DO UPDATE SET'
                    ' pinned_hash = excluded.pinned_hash,'
                    ' pinned_by = excluded.pinned_by,'
                    ' pinned_at = excluded.pinned_at,'
                    ' receipt_id = excluded.receipt_id',
                    (target, current, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'target': target, 'pinned_hash': current,
                'pinned_by': actor, 'pinned_at': now}

    def pin_all_baselines(self, actor, *, region=None):
        """Pin every present protected target (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        pinned = []
        for target in TARGETS:
            if self._current_hash(target) != 'FILE_MISSING':
                pinned.append(self.pin_baseline(actor, target,
                                                region=region))
        return pinned

    # -- patrol ---------------------------------------------------------

    def patrol(self, actor, *, region=None):
        """Run one patrol cycle over the durable baselines (operator).

        The recovered cycle's semantics: a pinned target that is
        missing or whose hash differs from its pin is an anomaly.
        An unpinned target is reported as unpinned, never silently
        treated as patrolled. An anomaly already open for the same
        target and kind is carried, not duplicated.
        """
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        patrol_id = f'mn-patrol-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            pins = {
                row['target']: row['pinned_hash']
                for row in db.execute('SELECT * FROM minotaur_baselines')
            }
        findings = []
        unpinned = 0
        for target in TARGETS:
            pin = pins.get(target)
            if pin is None:
                unpinned += 1
                continue
            current = self._current_hash(target)
            if current == 'FILE_MISSING':
                findings.append((target, 'MISSING'))
            elif current != pin:
                findings.append((target, 'ALTERED'))
        anomalies = []
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_PATROL', actor=actor, patrol_id=patrol_id,
                    targets_checked=len(TARGETS) - unpinned,
                    anomalies_found=len(findings))
                db.execute(
                    'INSERT INTO minotaur_patrols (patrol_id, patrolled_at,'
                    ' patrolled_by, targets_checked, unpinned,'
                    ' anomalies_found, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (patrol_id, now, actor, len(TARGETS) - unpinned,
                     unpinned, len(findings), receipt_id),
                )
                for target, kind in findings:
                    open_row = db.execute(
                        "SELECT * FROM minotaur_anomalies"
                        " WHERE target = ? AND kind = ? AND status IN"
                        " ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED')"
                        ' ORDER BY detected_at LIMIT 1',
                        (target, kind),
                    ).fetchone()
                    if open_row is not None:
                        view = self._anomaly_view(open_row)
                        view['carried'] = True
                        anomalies.append(view)
                        continue
                    anomaly_id = f'mn-anom-{uuid.uuid4().hex[:16]}'
                    a_receipt = self._record(
                        'MINOTAUR_ANOMALY', actor=actor,
                        anomaly_id=anomaly_id, patrol_id=patrol_id,
                        target=target, kind=kind)
                    db.execute(
                        'INSERT INTO minotaur_anomalies (anomaly_id,'
                        ' patrol_id, target, kind, status, detected_at,'
                        ' updated_by, updated_at, receipt_id)'
                        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (anomaly_id, patrol_id, target, kind, 'DETECTED',
                         now, actor, now, a_receipt),
                    )
                    row = db.execute(
                        'SELECT * FROM minotaur_anomalies'
                        ' WHERE anomaly_id = ?',
                        (anomaly_id,),
                    ).fetchone()
                    view = self._anomaly_view(row)
                    view['carried'] = False
                    anomalies.append(view)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'patrol_id': patrol_id,
            'patrolled_at': now,
            'targets_checked': len(TARGETS) - unpinned,
            'unpinned': unpinned,
            'anomalies_found': len(findings),
            'anomalies': anomalies,
        }

    def anomalies_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'anomalies', 'anomalies view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_anomalies ORDER BY detected_at',
            ).fetchall()
        return [self._anomaly_view(row) for row in rows]

    def anomaly_view(self, actor, role, anomaly_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, anomaly_id, 'anomaly view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                (anomaly_id,),
            ).fetchone()
        if row is None:
            raise MinotaurDenied('Anomaly not found')
        return self._anomaly_view(row)

    def anomaly_action(self, actor, anomaly_id, action, *, region=None):
        """Advance one anomaly's lifecycle (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        transitions = ANOMALY_TRANSITIONS.get(action)
        if transitions is None:
            raise MinotaurDenied(f'Unknown anomaly action: {action!r}')
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                    (anomaly_id,),
                ).fetchone()
                if row is None:
                    raise MinotaurDenied('Anomaly not found')
                new_status = transitions.get(row['status'])
                if new_status is None:
                    raise MinotaurDenied(
                        f"Cannot {action} an anomaly in status"
                        f" {row['status']}")
                receipt_id = self._record(
                    'MINOTAUR_ANOMALY_ACTION', actor=actor,
                    anomaly_id=anomaly_id, action=action,
                    from_status=row['status'], to_status=new_status)
                db.execute(
                    'UPDATE minotaur_anomalies SET status = ?,'
                    ' updated_by = ?, updated_at = ?, receipt_id = ?'
                    ' WHERE anomaly_id = ?',
                    (new_status, actor, now, receipt_id, anomaly_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM minotaur_anomalies WHERE anomaly_id = ?',
                (anomaly_id,),
            ).fetchone()
        return self._anomaly_view(updated)

    # -- clearances -------------------------------------------------------

    def clearance_issue(self, actor, subject, *, region=None):
        """Issue a clearance determination for one subject (operator).

        SAFE_TO_EXECUTE only when every protected target is pinned,
        the latest patrol cycle is clean, and no anomaly is open;
        otherwise DENIED with the blocker named. The determination is
        recorded either way — a denial is a record, not an absence.
        The returned clearance_id is the reference the Twin-Gate
        section 8 chain records at its step 2.
        """
        self._geo(region)
        self._require_operator(actor)
        if not isinstance(subject, str) or not subject.strip():
            raise MinotaurDenied('A clearance subject is required')
        subject = subject.strip()
        now = self._now()
        with self._connect() as db:
            pinned = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_baselines',
            ).fetchone()['n']
            latest = db.execute(
                'SELECT * FROM minotaur_patrols'
                ' ORDER BY patrolled_at DESC, patrol_id DESC LIMIT 1',
            ).fetchone()
            open_anomalies = db.execute(
                "SELECT COUNT(*) AS n FROM minotaur_anomalies"
                " WHERE status IN ('DETECTED', 'ACKNOWLEDGED',"
                " 'ESCALATED')",
            ).fetchone()['n']
        if pinned < len(TARGETS):
            determination, reason = 'DENIED', 'unpinned_targets'
            patrol_id = latest['patrol_id'] if latest else None
        elif latest is None:
            determination, reason = 'DENIED', 'no_patrol_on_record'
            patrol_id = None
        elif open_anomalies > 0:
            determination, reason = 'DENIED', 'open_anomalies'
            patrol_id = latest['patrol_id']
        elif latest['anomalies_found'] > 0:
            determination, reason = 'DENIED', 'latest_patrol_found_anomalies'
            patrol_id = latest['patrol_id']
        else:
            determination, reason = 'SAFE_TO_EXECUTE', 'patrol_clean'
            patrol_id = latest['patrol_id']
        clearance_id = f'mn-clear-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_CLEARANCE', actor=actor,
                    clearance_id=clearance_id, subject=subject,
                    determination=determination, reason=reason)
                db.execute(
                    'INSERT INTO minotaur_clearances (clearance_id,'
                    ' subject, determination, reason, patrol_id,'
                    ' open_anomalies, issued_by, issued_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (clearance_id, subject, determination, reason,
                     patrol_id, open_anomalies, actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM minotaur_clearances WHERE clearance_id = ?',
                (clearance_id,),
            ).fetchone()
        return self._clearance_view(row)

    def clearance_view(self, actor, role, clearance_id, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, clearance_id, 'clearance view')
        with self._connect() as db:
            row = db.execute(
                'SELECT * FROM minotaur_clearances WHERE clearance_id = ?',
                (clearance_id,),
            ).fetchone()
        if row is None:
            raise MinotaurDenied('Clearance not found')
        return self._clearance_view(row)

    # -- shield patrol (founder's orders, 2026-11-26) -------------------
    #
    # The Minotaur patrols all three shields SIMULTANEOUSLY:
    # one patrol cycle covers every shield's core in a single
    # recorded run — never a rotation. The patrol's sequencing
    # is labyrinthine (his upgrade, below): the walk order over
    # the shields' cores is derived from the attestation chain
    # head, so the patrol never walks the same linear path
    # twice, and it walks out and back. Tamper findings surface
    # through the established anomaly lifecycle, and each
    # patrol closes with a signed, hash-chained attestation
    # whose payload carries the three shields' integrity
    # commitments in walk order — the shields' integrity
    # chained together, by reference, under his signature.

    @staticmethod
    def _labyrinth_sequence(chain_head, items):
        """The labyrinth walk: a deterministic-but-nonlinear
        order over ``items`` derived from the attestation
        chain head — start and stride from the head, every
        item visited exactly once, then the walk retraced in
        reverse. The sequence is recorded in the patrol
        record, so the path taken is itself evidence."""
        n = len(items)
        if n == 0:
            return []
        if n == 1:
            return [items[0], items[0]]
        start = int(chain_head[:8], 16) % n
        stride = 1 + (int(chain_head[8:16], 16) % (n - 1))
        order = None
        for candidate in range(stride, stride + n):
            step = candidate % n
            if step == 0:
                continue
            visited = []
            index = start
            for _ in range(n):
                if items[index] not in visited:
                    visited.append(items[index])
                index = (index + step) % n
            if len(visited) == n:
                order = visited
                break
        if order is None:
            order = list(items)
        return order + list(reversed(order))

    def _raise_anomaly(self, db, actor, patrol_id, target, kind,
                       now):
        open_row = db.execute(
            "SELECT * FROM minotaur_anomalies"
            " WHERE target = ? AND kind = ? AND status IN"
            " ('DETECTED', 'ACKNOWLEDGED', 'ESCALATED')"
            ' ORDER BY detected_at LIMIT 1',
            (target, kind),
        ).fetchone()
        if open_row is not None:
            view = self._anomaly_view(open_row)
            view['carried'] = True
            return view
        anomaly_id = f'mn-anom-{uuid.uuid4().hex[:16]}'
        a_receipt = self._record(
            'MINOTAUR_ANOMALY', actor=actor,
            anomaly_id=anomaly_id, patrol_id=patrol_id,
            target=target, kind=kind)
        db.execute(
            'INSERT INTO minotaur_anomalies (anomaly_id,'
            ' patrol_id, target, kind, status, detected_at,'
            ' updated_by, updated_at, receipt_id)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (anomaly_id, patrol_id, target, kind, 'DETECTED',
             now, actor, now, a_receipt),
        )
        row = db.execute(
            'SELECT * FROM minotaur_anomalies'
            ' WHERE anomaly_id = ?',
            (anomaly_id,),
        ).fetchone()
        view = self._anomaly_view(row)
        view['carried'] = False
        return view

    def shield_targets(self, actor, role, *, region=None):
        """Every shield's cores with pin and live state, all
        three shields at once."""
        self._geo(region)
        self._guard_access(actor, role, 'shield-targets',
                           'shield targets view')
        with self._connect() as db:
            pins = {
                (row['shield_id'], row['target']):
                    row['pinned_hash']
                for row in db.execute(
                    'SELECT * FROM minotaur_shield_baselines')
            }
        result = []
        for shield_id, shield_name, cores in SHIELD_PATROL_TARGETS:
            entries = []
            for target in cores:
                current = self._current_hash(target)
                pin = pins.get((shield_id, target))
                if pin is None:
                    state = 'UNPINNED'
                elif current == 'FILE_MISSING':
                    state = 'MISSING'
                elif current == pin:
                    state = 'MATCH'
                else:
                    state = 'MISMATCH'
                entries.append({
                    'target': target, 'state': state,
                    'pinned_hash': pin, 'current_hash': current,
                })
            result.append({
                'shield_id': shield_id, 'shield_name': shield_name,
                'cores': entries,
            })
        return result

    def pin_shield_baselines(self, actor, *, region=None):
        """Pin every present shield core across all three
        shields (operator only), and sign the baseline set as
        one attestation: the baselines are integrity proofs,
        and under his upgrade they carry his quantum-layer
        signature and chain link."""
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        pinned = []
        missing = []
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_SHIELD_BASELINES_PINNED', actor=actor,
                    shields=len(SHIELD_PATROL_TARGETS))
                for shield_id, _name, cores in \
                        SHIELD_PATROL_TARGETS:
                    for target in cores:
                        current = self._current_hash(target)
                        if current == 'FILE_MISSING':
                            missing.append(target)
                            continue
                        db.execute(
                            'INSERT INTO minotaur_shield_baselines'
                            ' (shield_id, target, pinned_hash,'
                            ' pinned_by, pinned_at, receipt_id)'
                            ' VALUES (?, ?, ?, ?, ?, ?)'
                            ' ON CONFLICT(shield_id, target)'
                            ' DO UPDATE SET pinned_hash ='
                            ' excluded.pinned_hash, pinned_by ='
                            ' excluded.pinned_by, pinned_at ='
                            ' excluded.pinned_at, receipt_id ='
                            ' excluded.receipt_id',
                            (shield_id, target, current, actor,
                             now, receipt_id),
                        )
                        pinned.append({
                            'shield_id': shield_id,
                            'target': target,
                            'pinned_hash': current,
                        })
                attestation = self._append_attestation(
                    db, 'SHIELD_BASELINES',
                    {'pinned': pinned, 'missing': missing},
                    actor)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'pinned': pinned, 'missing': missing,
                'attestation': {
                    'seq': attestation['seq'],
                    'hash': attestation['hash'],
                    'merkle_root': attestation['merkle_root'],
                }}

    def shield_patrol(self, actor, *, region=None):
        """Run ONE patrol cycle over all three shields
        simultaneously (operator only): every shield's cores,
        and every active decoy, walked in the labyrinth
        sequence in a single recorded run. A shield whose
        cores are unpinned is reported unpinned, never
        silently treated as patrolled. Findings enter the
        established anomaly lifecycle in the same transaction,
        and the patrol closes with a signed attestation."""
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        patrol_id = f'mn-shield-patrol-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            pins = {
                (row['shield_id'], row['target']):
                    row['pinned_hash']
                for row in db.execute(
                    'SELECT * FROM minotaur_shield_baselines')
            }
            decoys = db.execute(
                "SELECT * FROM minotaur_decoys WHERE status ="
                " 'ACTIVE'").fetchall()
            chain_head = self._signing_state(db)['chain_head']
        items = []
        for shield_id, _name, cores in SHIELD_PATROL_TARGETS:
            for target in cores:
                items.append(('core', shield_id, target))
        for decoy in decoys:
            items.append(('decoy', decoy['shield_id'],
                          decoy['target']))
        sequence = self._labyrinth_sequence(chain_head, items)
        per_shield = {
            shield_id: {'shield_id': shield_id,
                        'shield_name': name, 'checked': 0,
                        'unpinned': 0, 'anomalies': 0,
                        'decoys_checked': 0}
            for shield_id, name, _c in SHIELD_PATROL_TARGETS
        }
        findings = []
        unpinned = 0
        checked = 0
        seen_items = set()
        for kind, shield_id, target in sequence:
            # The walk visits each item twice (out and back);
            # the check counts once — the return visit is the
            # retrace, recorded in the sequence, not a second
            # check.
            key = (kind, shield_id, target)
            if key in seen_items:
                continue
            seen_items.add(key)
            current = self._current_hash(target)
            if kind == 'decoy':
                per_shield[shield_id]['decoys_checked'] += 1
                pin = next(
                    (d['pinned_hash'] for d in decoys
                     if d['target'] == target), None)
            else:
                pin = pins.get((shield_id, target))
                per_shield[shield_id]['checked'] += 1
                checked += 1
                if pin is None:
                    per_shield[shield_id]['unpinned'] += 1
                    unpinned += 1
                    continue
            if current == 'FILE_MISSING':
                findings.append((shield_id, target, 'MISSING'))
                per_shield[shield_id]['anomalies'] += 1
            elif pin is not None and current != pin:
                findings.append((shield_id, target, 'ALTERED'))
                per_shield[shield_id]['anomalies'] += 1
        found = findings
        anomalies = []
        sequence_view = [
            f'{kind}:{shield_id}:{target}'
            for kind, shield_id, target in sequence]
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_SHIELD_PATROL', actor=actor,
                    patrol_id=patrol_id,
                    shields_covered=len(SHIELD_PATROL_TARGETS),
                    targets_checked=checked,
                    anomalies_found=len(found))
                db.execute(
                    'INSERT INTO minotaur_shield_patrols'
                    ' (patrol_id, patrolled_at, patrolled_by,'
                    ' shields_covered, targets_checked, unpinned,'
                    ' anomalies_found, sequence, attestation_seq,'
                    ' receipt_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?,'
                    ' ?, ?)',
                    (patrol_id, now, actor,
                     len(SHIELD_PATROL_TARGETS), checked, unpinned,
                     len(found), json.dumps(sequence_view), None,
                     receipt_id),
                )
                for shield_id, target, kind in found:
                    anomalies.append(self._raise_anomaly(
                        db, actor, patrol_id, target, kind, now))
                attestation = self._append_attestation(
                    db, 'SHIELD_PATROL',
                    {'patrol_id': patrol_id,
                     'shields': [
                         per_shield[s] for s in SHIELD_IDS],
                     'sequence': sequence_view,
                     'anomalies_found': len(found)},
                    actor)
                db.execute(
                    'UPDATE minotaur_shield_patrols SET'
                    ' attestation_seq = ? WHERE patrol_id = ?',
                    (attestation['seq'], patrol_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {
            'patrol_id': patrol_id,
            'patrolled_at': now,
            'shields_covered': len(SHIELD_PATROL_TARGETS),
            'shields': [per_shield[s] for s in SHIELD_IDS],
            'targets_checked': checked,
            'unpinned': unpinned,
            'anomalies_found': len(found),
            'anomalies': anomalies,
            'sequence': sequence_view,
            'attestation': {
                'seq': attestation['seq'],
                'hash': attestation['hash'],
                'merkle_root': attestation['merkle_root'],
            },
        }

    def shield_patrols_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'shield-patrols',
                           'shield patrols view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_shield_patrols'
                ' ORDER BY patrolled_at').fetchall()
        return [{
            'patrol_id': row['patrol_id'],
            'patrolled_at': row['patrolled_at'],
            'patrolled_by': row['patrolled_by'],
            'shields_covered': row['shields_covered'],
            'targets_checked': row['targets_checked'],
            'unpinned': row['unpinned'],
            'anomalies_found': row['anomalies_found'],
            'sequence': json.loads(row['sequence']),
            'attestation_seq': row['attestation_seq'],
            'receipt_id': row['receipt_id'],
        } for row in rows]

    # -- decoys / honeytokens (his labyrinth behavior) ------------------
    #
    # Bait files on deceptive patrol paths (shield-upgrade
    # research Area 2.5, the CISA decoy discipline): a decoy
    # is a file nothing legitimate ever touches, planted under
    # a shield's patrol segment and pinned at planting. The
    # shield patrol walks the decoys with the cores; a decoy
    # altered or missing is a tamper finding in the same
    # anomaly lifecycle. A decoy is never a real core and
    # never a protected target — planting one over either is
    # refused by name.

    @staticmethod
    def _decoy_view(row):
        return {
            'decoy_id': row['decoy_id'],
            'shield_id': row['shield_id'],
            'target': row['target'],
            'note': row['note'],
            'pinned_hash': row['pinned_hash'],
            'status': row['status'],
            'planted_by': row['planted_by'],
            'planted_at': row['planted_at'],
            'receipt_id': row['receipt_id'],
        }

    def plant_decoy(self, actor, shield_id, target, note, *,
                    region=None):
        """Plant one honeytoken decoy (operator only): record
        the bait file's current hash as its pin. The operator
        places the bait file itself; this record is what makes
        any later touch a finding."""
        self._geo(region)
        self._require_operator(actor)
        if shield_id not in SHIELD_IDS:
            raise MinotaurDenied(
                f'Not one of the three shields: {shield_id!r}')
        if not isinstance(target, str) or not target.strip():
            raise MinotaurDenied('A decoy target is required')
        if not isinstance(note, str) or not note.strip():
            raise MinotaurDenied(
                'A decoy note is required (what legitimately'
                ' touches this path must be pre-inventoried)')
        target = target.strip()
        core_targets = {
            t for _s, _n, cores in SHIELD_PATROL_TARGETS
            for t in cores}
        if target in core_targets or target in TARGETS:
            raise MinotaurDenied(
                'A decoy is never planted over a real core or'
                ' a protected target')
        # Deception isolation, enforced in code (founder
        # directive 2026-11-26): decoys never stand on a
        # data store, a guarded document, a bloodline
        # store, or this service's own machinery — the
        # deception environment stays isolated from
        # production infrastructure, bloodline
        # information, and emergency operations.
        lowered = target.lower()
        if (lowered.endswith('.db')
                or lowered.endswith('.sqlite')
                or lowered.endswith('.sqlite3')
                or lowered.startswith('docs/')
                or 'bloodline' in lowered
                or target == self._path.name
                or lowered.endswith('_service.py')):
            raise MinotaurDenied(
                'A decoy is never planted on a data store,'
                ' a guarded document, a bloodline store, or'
                ' service machinery — deception stays'
                ' isolated')
        current = self._current_hash(target)
        if current == 'FILE_MISSING':
            raise MinotaurDenied(
                f'Cannot plant a decoy over a missing file:'
                f' {target}')
        now = self._now()
        decoy_id = f'mn-decoy-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_DECOY_PLANTED', actor=actor,
                    decoy_id=decoy_id, shield_id=shield_id,
                    target=target, pinned_hash=current)
                db.execute(
                    'INSERT INTO minotaur_decoys (decoy_id,'
                    ' shield_id, target, note, pinned_hash,'
                    ' status, planted_by, planted_at, updated_by,'
                    ' updated_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (decoy_id, shield_id, target, note.strip(),
                     current, 'ACTIVE', actor, now, actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM minotaur_decoys WHERE decoy_id = ?',
                (decoy_id,)).fetchone()
        return self._decoy_view(row)

    def retire_decoy(self, actor, decoy_id, *, region=None):
        """Retire one active decoy (operator only)."""
        self._geo(region)
        self._require_operator(actor)
        now = self._now()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                row = db.execute(
                    'SELECT * FROM minotaur_decoys'
                    ' WHERE decoy_id = ?',
                    (decoy_id,)).fetchone()
                if row is None:
                    raise MinotaurDenied('Decoy not found')
                if row['status'] != 'ACTIVE':
                    raise MinotaurDenied('Decoy is not active')
                receipt_id = self._record(
                    'MINOTAUR_DECOY_RETIRED', actor=actor,
                    decoy_id=decoy_id, target=row['target'])
                db.execute(
                    "UPDATE minotaur_decoys SET status ="
                    " 'RETIRED', updated_by = ?, updated_at = ?,"
                    ' receipt_id = ? WHERE decoy_id = ?',
                    (actor, now, receipt_id, decoy_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            updated = db.execute(
                'SELECT * FROM minotaur_decoys WHERE decoy_id = ?',
                (decoy_id,)).fetchone()
        return self._decoy_view(updated)

    def decoys_list(self, actor, role, *, region=None):
        self._geo(region)
        self._guard_access(actor, role, 'decoys', 'decoys view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_decoys'
                ' ORDER BY planted_at').fetchall()
        return [self._decoy_view(row) for row in rows]

    # -- self-protection (founder-adopted amendment,
    # 2026-11-26) ------------------------------------
    #
    # The Comprehensive Self-Protection and
    # Anti-Circumvention Amendment, in his machinery:
    # the fifteen enumerated protections stand as
    # governed checks of record, each protection's
    # state derived from its latest check — EVIDENCED,
    # FINDING, or NOT_EVIDENCED — and CONSTRUCTED on
    # its mechanism of record alone before any check
    # stands. Nothing here disables, diminishes,
    # circumvents, or redirects any protective
    # responsibility: there is no record operation in
    # this platform that turns a protection off.

    @staticmethod
    def _self_protection_entry(protection_key):
        for entry in (SELF_PROTECTIONS
                      + ANTI_PROBING_PROTECTIONS):
            if entry['protection'] == protection_key:
                return entry
        raise MinotaurDenied(
            'The protection must be one of the'
            ' amendment\'s fifteen enumerated'
            ' protections or the directive\'s'
            ' thirteen anti-probing protections')

    @staticmethod
    def self_protection_design_view() -> dict:
        return {
            'title': SELF_PROTECTION_TITLE,
            'adopted': SELF_PROTECTION_ADOPTED,
            'adoption_kind': 'AMENDMENT',
            'scope_verbatim':
                SELF_PROTECTION_SCOPE_VERBATIM,
            'external_authority_verbatim':
                SELF_PROTECTION_EXTERNAL_AUTHORITY_VERBATIM,
            'detect_resist_verbatim':
                SELF_PROTECTION_DETECT_RESIST_VERBATIM,
            'deception_isolation_verbatim':
                SELF_PROTECTION_DECEPTION_VERBATIM,
            'recovery_verbatim':
                SELF_PROTECTION_RECOVERY_VERBATIM,
            'anti_circumvention_verbatim':
                SELF_PROTECTION_ANTI_CIRCUMVENTION_VERBATIM,
            'not_a_ceiling_verbatim':
                SELF_PROTECTION_NOT_A_CEILING_VERBATIM,
            'strengthens_verbatim':
                SELF_PROTECTION_STRENGTHENS_VERBATIM,
            'attack_classes': list(
                SELF_PROTECTION_ATTACK_CLASSES),
            'crypto_route': dict(CRYPTO_ROUTE),
            'domains': [dict(d) for d in DEFENSIVE_DOMAINS],
            'functioning_standard':
                FUNCTIONING_STANDARD_VERBATIM,
            'scope_line': 'He defends himself, his'
                          ' defenses, the'
                          ' infrastructure sustaining'
                          ' him, and the three shields'
                          ' — simultaneously.',
            'accounting_counts_of_record': {
                'founder_omissions': 30,
                'founder_exposures': 15,
                'source_lists_in_hand': False,
                'reconciliation': 'name-by-name'
                                  ' reconciliation'
                                  ' awaits the'
                                  ' founder\'s source'
                                  ' lists',
            },
            'external_connections': 'NONE',
        }

    def self_protection_view(self, actor, role, *,
                             region=None):
        """The self-protection board (guarded read):
        the amendment's design of record and the
        fifteen protections, each with its mechanism
        and its state derived from its checks of
        record."""
        self._geo(region)
        self._guard_access(actor, role, 'self-protection',
                           'self protection view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' minotaur_self_protection_checks'
                ' ORDER BY recorded_at').fetchall()
            crypto_latest = db.execute(
                'SELECT * FROM minotaur_crypto_checks'
                ' ORDER BY recorded_at DESC LIMIT 1',
            ).fetchone()
        latest = {}
        for row in rows:
            latest[row['protection_key']] = row

        def protection_view(entry):
            row = latest.get(entry['protection'])
            if row is None:
                state = 'CONSTRUCTED'
                check = None
            else:
                state = row['outcome']
                check = {
                    'check_id': row['check_id'],
                    'outcome': row['outcome'],
                    'evidence_ref': row['evidence_ref'],
                    'recorded_at': row['recorded_at'],
                    'receipt_id': row['receipt_id'],
                }
            exercise = EXERCISE_EVIDENCE.get(
                entry['protection'], ('RECORD', ''))
            return {
                'protection': entry['protection'],
                'verbatim': entry['verbatim'],
                'mechanism': entry['mechanism'],
                'exercise_kind': exercise[0],
                'exercise_evidence': exercise[1],
                'state': state,
                'latest_check': check,
            }

        protections = [protection_view(entry)
                       for entry in SELF_PROTECTIONS]
        anti_probing = [protection_view(entry)
                        for entry in ANTI_PROBING_PROTECTIONS]
        return {
            'title': SELF_PROTECTION_TITLE,
            'design': type(self).self_protection_design_view(),
            'part': 'MINOTAUR_SELF_PROTECTION',
            'ladder_state': 'CONSTRUCTED',
            'protections': protections,
            'anti_probing_part':
                'MINOTAUR_ANTI_PROBING_PROTECTIONS',
            'anti_probing_ladder_state': 'CONSTRUCTED',
            'anti_probing_protections': anti_probing,
            'defensive_relationship': dict(
                DEFENSIVE_RELATIONSHIP),
            'checks_total': len(rows),
            'crypto_environment_latest': (
                self._crypto_check_view(crypto_latest)
                if crypto_latest else None),
            'external_connections': 'NONE',
        }

    @staticmethod
    def _sp_check_view(row):
        return {
            'check_id': row['check_id'],
            'protection': row['protection_key'],
            'outcome': row['outcome'],
            'evidence_ref': row['evidence_ref'],
            'detail': row['detail'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def record_self_protection_check(
            self, actor, protection_key, outcome,
            evidence_ref, detail, *, region=None):
        """Record one self-protection check against one
        of the fifteen enumerated protections
        (operator only): the evidence, by reference,
        and the outcome it supports — EVIDENCED,
        FINDING, or NOT_EVIDENCED. The protection's
        state derives from its latest check; a check
        records evidence, it neither grants nor
        removes the protection."""
        self._geo(region)
        self._require_operator(actor)
        self._self_protection_entry(protection_key)
        if outcome not in SELF_PROTECTION_CHECK_OUTCOMES:
            raise MinotaurDenied(
                'The check outcome must be one of: '
                + ', '.join(
                    SELF_PROTECTION_CHECK_OUTCOMES))
        for label, value in (
                ('evidence_ref', evidence_ref),
                ('detail', detail)):
            if (not isinstance(value, str)
                    or not value.strip()):
                raise MinotaurDenied(
                    f'A {label} is required')
        now = self._now()
        check_id = f'mn-spcheck-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_SELF_PROTECTION_CHECK',
                    actor=actor, check_id=check_id,
                    protection_key=protection_key,
                    outcome=outcome)
                db.execute(
                    'INSERT INTO'
                    ' minotaur_self_protection_checks'
                    ' (check_id, protection_key, outcome,'
                    ' evidence_ref, detail, recorded_by,'
                    ' recorded_at, receipt_id) VALUES'
                    ' (?, ?, ?, ?, ?, ?, ?, ?)',
                    (check_id, protection_key, outcome,
                     evidence_ref.strip(), detail.strip(),
                     actor, now, receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM'
                ' minotaur_self_protection_checks'
                ' WHERE check_id = ?',
                (check_id,)).fetchone()
        return self._sp_check_view(row)

    _CRYPTO_CLAIM_RANK = {
        'NATIVE_HASH_BASED_STANDS_ENVIRONMENT_BLOCKED': 0,
        'SYSTEM_PQC_ALGORITHMS_NO_FIPS_CLAIM': 1,
        'VALIDATED_MODULE_APPROVED_MODE': 2,
    }

    def assert_crypto_claim(self, actor, claimed, *,
                            region=None):
        """Assert a cryptographic claim against the
        latest environment check of record (operator
        only) — downgrade and overclaim refusal,
        enforced in code: a claim is allowed only at
        or below what the check of record proves. A
        claim above the evidence, or any claim with
        no check standing, is refused. This is the
        cryptographic-downgrade defense functioning:
        the platform cannot be made to present a
        weaker — or stronger — posture than its
        evidence."""
        self._geo(region)
        self._require_operator(actor)
        if claimed not in self._CRYPTO_CLAIM_RANK:
            raise MinotaurDenied(
                'The claimed determination must be one'
                ' of: ' + ', '.join(
                    self._CRYPTO_CLAIM_RANK))
        with self._connect() as db:
            latest = db.execute(
                'SELECT * FROM minotaur_crypto_checks'
                ' ORDER BY recorded_at DESC LIMIT 1',
            ).fetchone()
        if latest is None:
            raise MinotaurDenied(
                'No crypto environment check stands: no'
                ' claim may be asserted without evidence')
        proven = latest['determination']
        if (self._CRYPTO_CLAIM_RANK[claimed]
                > self._CRYPTO_CLAIM_RANK[proven]):
            raise MinotaurDenied(
                'Claim refused: the check of record'
                f' proves {proven}; claiming {claimed}'
                ' would misstate the cryptographic'
                ' posture (downgrade/overclaim refusal)')
        receipt_id = self._record(
            'MINOTAUR_CRYPTO_CLAIM_ASSERTED', actor=actor,
            claimed=claimed, proven=proven)
        return {
            'claimed': claimed,
            'proven_by_check': proven,
            'check_id': latest['check_id'],
            'allowed': True,
            'receipt_id': receipt_id,
        }

    def self_protection_checks(self, actor, role, *,
                               region=None):
        self._geo(region)
        self._guard_access(actor, role, 'self-protection',
                           'self protection checks view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM'
                ' minotaur_self_protection_checks'
                ' ORDER BY recorded_at').fetchall()
        views = [self._sp_check_view(row) for row in rows]
        return {'checks': views, 'total': len(views)}

    # -- the crypto environment check of record ------
    #
    # The adopted gap-closure route claims exactly
    # what the environment proves. This probe reads
    # the Python ssl/hashlib runtime surface of the
    # process this service runs in — the surface the
    # platform itself can reach. It cannot prove FIPS
    # approved mode from that surface, and it does
    # not pretend to: where the validated module is
    # not proven, the determination says so.

    @staticmethod
    def _probe_crypto_environment():
        version = ssl.OPENSSL_VERSION
        info = list(ssl.OPENSSL_VERSION_INFO)
        available = {a.lower().replace('-', '_')
                     for a in hashlib.algorithms_available}
        pqc = [name for name in ('ML-KEM', 'ML-DSA',
                                 'SLH-DSA')
               if name.lower().replace('-', '_')
               in available]
        fips_state = (
            'NOT_PROVABLE_FROM_PYTHON_SSL_SURFACE')
        if pqc:
            determination = \
                'SYSTEM_PQC_ALGORITHMS_NO_FIPS_CLAIM'
        else:
            determination = (
                'NATIVE_HASH_BASED_STANDS_'
                'ENVIRONMENT_BLOCKED')
        return {
            'openssl_version': version,
            'openssl_version_info': info,
            'fips_provider_state': fips_state,
            'pqc_reachable': pqc,
            'determination': determination,
            'probe_scope': 'Python ssl/hashlib runtime'
                           ' surface of the process this'
                           ' service runs in',
        }

    @staticmethod
    def _crypto_check_view(row):
        return {
            'check_id': row['check_id'],
            'openssl_version': row['openssl_version'],
            'openssl_version_info': json.loads(
                row['openssl_version_info']),
            'fips_provider_state':
                row['fips_provider_state'],
            'pqc_reachable': json.loads(
                row['pqc_reachable']),
            'determination': row['determination'],
            'probe_scope': row['probe_scope'],
            'recorded_by': row['recorded_by'],
            'recorded_at': row['recorded_at'],
            'receipt_id': row['receipt_id'],
        }

    def record_crypto_environment_check(self, actor, *,
                                        region=None):
        """Run the crypto environment probe in this
        service's own runtime and record its evidence
        (operator only). The recorded determination
        follows CRYPTO_ROUTE's claim rule exactly:
        nothing beyond the check is claimed, and a
        runtime that reaches neither the validated
        module nor the system PQC algorithms records
        the native construction standing, with the gap
        environment-blocked — not papered over."""
        self._geo(region)
        self._require_operator(actor)
        probe = self._probe_crypto_environment()
        now = self._now()
        check_id = f'mn-cryptocheck-{uuid.uuid4().hex[:16]}'
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                receipt_id = self._record(
                    'MINOTAUR_CRYPTO_ENVIRONMENT_CHECK',
                    actor=actor, check_id=check_id,
                    determination=probe['determination'],
                    openssl_version=probe['openssl_version'])
                db.execute(
                    'INSERT INTO minotaur_crypto_checks'
                    ' (check_id, openssl_version,'
                    ' openssl_version_info,'
                    ' fips_provider_state, pqc_reachable,'
                    ' determination, probe_scope,'
                    ' recorded_by, recorded_at, receipt_id)'
                    ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (check_id, probe['openssl_version'],
                     json.dumps(probe['openssl_version_info']),
                     probe['fips_provider_state'],
                     json.dumps(probe['pqc_reachable']),
                     probe['determination'],
                     probe['probe_scope'], actor, now,
                     receipt_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            row = db.execute(
                'SELECT * FROM minotaur_crypto_checks'
                ' WHERE check_id = ?',
                (check_id,)).fetchone()
        return self._crypto_check_view(row)

    def crypto_environment_checks(self, actor, role, *,
                                  region=None):
        self._geo(region)
        self._guard_access(actor, role, 'crypto-environment',
                           'crypto environment checks view')
        with self._connect() as db:
            rows = db.execute(
                'SELECT * FROM minotaur_crypto_checks'
                ' ORDER BY recorded_at').fetchall()
        views = [self._crypto_check_view(row) for row in rows]
        return {
            'route': dict(CRYPTO_ROUTE),
            'checks': views,
            'total': len(views),
            'latest': views[-1] if views else None,
        }

    def defensive_relationship_view(self, actor, role, *,
                                    region=None):
        """The completed defensive relationship
        (guarded read): the Minotaur as independent
        integrity verification over the three shields
        — three independent protective identities —
        drawing authenticated integrity evidence into
        independent assessment and protection, with
        continuous watchdog recovery, standing over
        the bloodline three under permanent bloodline
        protection. The relationship is stated in the
        founder's terms of record; it joins the
        shields and merges nothing."""
        self._geo(region)
        self._guard_access(actor, role,
                           'defensive-relationship',
                           'defensive relationship view')
        relationship = dict(DEFENSIVE_RELATIONSHIP)
        relationship['part'] = \
            'MINOTAUR_DEFENSIVE_RELATIONSHIP'
        relationship['ladder_state'] = 'CONSTRUCTED'
        relationship['patrol_machinery'] = (
            'shield baselines, simultaneous patrol,'
            ' signed attestation chain, decoys,'
            ' clearance determinations')
        return relationship

    def defensive_domains_view(self, actor, role, *,
                               region=None):
        """The eight domains of his complete
        architecture (guarded read), each with its
        scope in the founder's terms and the members
        of record that stand in it."""
        self._geo(region)
        self._guard_access(actor, role, 'defensive-domains',
                           'defensive domains view')
        return {
            'domains': [dict(d) for d in DEFENSIVE_DOMAINS],
            'total': len(DEFENSIVE_DOMAINS),
            'functioning_standard':
                FUNCTIONING_STANDARD_VERBATIM,
            'part': 'MINOTAUR_COMPLETE_ARCHITECTURE',
            'ladder_state': 'CONSTRUCTED',
        }

    def completeness_accounting_view(self, actor, role,
                                     *, region=None):
        """The completeness accounting (guarded read):
        every omission and exposure the examined
        record identifies, marked ALREADY_PROTECTED
        with its evidence or CONSTRUCTION_REQUIRED
        with its construction. The founder's counts
        of record (30 omissions, 15 exposures) stand
        as his; their source enumerations are not in
        hand, no list is fabricated to match the
        counts, and name-by-name reconciliation
        awaits his source lists."""
        self._geo(region)
        self._guard_access(actor, role,
                           'completeness-accounting',
                           'completeness accounting view')
        entries = [dict(e) for e in COMPLETENESS_ACCOUNTING]
        return {
            'accounting': entries,
            'total': len(entries),
            'already_protected': sum(
                1 for e in entries
                if e['status'] == 'ALREADY_PROTECTED'),
            'construction_required': sum(
                1 for e in entries
                if e['status'] == 'CONSTRUCTION_REQUIRED'),
            'founder_counts_of_record': {
                'omissions': 30, 'exposures': 15,
                'source_lists_in_hand': False,
            },
            'benchmark_total': len(BENCHMARK_CONTROLS),
            'benchmark_standings': {
                s: sum(1 for e in BENCHMARK_CONTROLS
                       if e['standing'] == s)
                for s in BENCHMARK_STANDINGS},
            'part': 'MINOTAUR_COMPLETENESS_ACCOUNTING',
            'ladder_state': 'CONSTRUCTED',
        }

    def benchmark_view(self, actor, role, *,
                       region=None):
        """The global benchmark mapping (guarded read):
        every control in the sets gathered in the
        shield-upgrade research, marked FUNCTIONING /
        RECORDED_WITH_REASON /
        NOT_APPLICABLE_WITH_REASON /
        ENVIRONMENT_LIMITED — the completeness
        accounting's benchmark section, under the
        founder's directive of 2026-11-26 11:36 MST.
        Standing is reported control-by-control,
        never as a blanket claim."""
        self._geo(region)
        self._guard_access(actor, role, 'benchmark',
                           'global benchmark view')
        entries = [dict(e) for e in BENCHMARK_CONTROLS]
        counts = {s: sum(1 for e in entries
                         if e['standing'] == s)
                  for s in BENCHMARK_STANDINGS}
        return {
            'directive_verbatim':
                FOUNDER_BENCHMARK_DIRECTIVE_VERBATIM,
            'benchmark': entries,
            'total': len(entries),
            'standings': counts,
            'proof_mechanism': (
                'the internal attack-simulation suites '
                'and the Minotaur\'s continuous patrol'),
            'part': 'GLOBAL_BENCHMARK_MAPPING',
            'ladder_state': 'CONSTRUCTED',
        }

    # -- status / check-in --------------------------------------------------

    def status(self) -> dict:
        with self._connect() as db:
            pinned = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_baselines',
            ).fetchone()['n']
            patrols = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_patrols',
            ).fetchone()['n']
            last_patrol = db.execute(
                'SELECT patrol_id, patrolled_at, anomalies_found'
                ' FROM minotaur_patrols'
                ' ORDER BY patrolled_at DESC, patrol_id DESC LIMIT 1',
            ).fetchone()
            by_status = {s: 0 for s in ANOMALY_STATUSES}
            for row in db.execute(
                    'SELECT status, COUNT(*) AS n FROM minotaur_anomalies'
                    ' GROUP BY status'):
                by_status[row['status']] = row['n']
            clearances = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_clearances',
            ).fetchone()['n']
            shield_patrols = db.execute(
                'SELECT COUNT(*) AS n FROM minotaur_shield_patrols',
            ).fetchone()['n']
            last_shield_patrol = db.execute(
                'SELECT patrol_id, patrolled_at, anomalies_found'
                ' FROM minotaur_shield_patrols'
                ' ORDER BY patrolled_at DESC, patrol_id DESC'
                ' LIMIT 1',
            ).fetchone()
            shield_pins = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' minotaur_shield_baselines',
            ).fetchone()['n']
            decoys_active = db.execute(
                "SELECT COUNT(*) AS n FROM minotaur_decoys"
                " WHERE status = 'ACTIVE'",
            ).fetchone()['n']
            sp_checks = db.execute(
                'SELECT COUNT(*) AS n FROM'
                ' minotaur_self_protection_checks',
            ).fetchone()['n']
            sp_findings = db.execute(
                "SELECT COUNT(*) AS n FROM"
                " minotaur_self_protection_checks"
                " WHERE outcome = 'FINDING'",
            ).fetchone()['n']
            crypto_latest = db.execute(
                'SELECT determination FROM'
                ' minotaur_crypto_checks ORDER BY'
                ' recorded_at DESC LIMIT 1',
            ).fetchone()
            latest = _foundation_latest_check_in(db, IDENTITY.platform_id)
        return {
            'identity': IDENTITY.to_dict(),
            'sentinel_id': self._sentinel.sentinel_id,
            'targets_total': len(TARGETS),
            'baselines_pinned': pinned,
            'patrols_total': patrols,
            'last_patrol': dict(last_patrol) if last_patrol else None,
            'anomalies_by_status': by_status,
            'clearances_issued': clearances,
            'shield_patrol': {
                'shields': [name for _id, name, _c
                            in SHIELD_PATROL_TARGETS],
                'shield_cores_pinned': shield_pins,
                'patrols_total': shield_patrols,
                'last_patrol': dict(last_shield_patrol)
                if last_shield_patrol else None,
                'decoys_active': decoys_active,
            },
            'quantum': self.quantum_status(),
            'self_protection': {
                'amendment': SELF_PROTECTION_TITLE,
                'adopted': SELF_PROTECTION_ADOPTED,
                'protections_total': len(SELF_PROTECTIONS),
                'anti_probing_total': len(
                    ANTI_PROBING_PROTECTIONS),
                'checks_total': sp_checks,
                'findings_total': sp_findings,
                'ladder_state': 'CONSTRUCTED',
            },
            'defensive_relationship': {
                'role': DEFENSIVE_RELATIONSHIP['role'],
                'shields': len(
                    DEFENSIVE_RELATIONSHIP['shields']),
                'shields_independent': True,
                'recovery': 'CONTINUOUS_WATCHDOG_RECOVERY',
                'ladder_state': 'CONSTRUCTED',
            },
            'complete_architecture': {
                'domains_total': len(DEFENSIVE_DOMAINS),
                'accounting_total': len(
                    COMPLETENESS_ACCOUNTING),
                'accounting_construction_required': sum(
                    1 for e in COMPLETENESS_ACCOUNTING
                    if e['status']
                    == 'CONSTRUCTION_REQUIRED'),
                'ladder_state': 'CONSTRUCTED',
            },
            'crypto_route': {
                'adopted_route': CRYPTO_ROUTE['adopted_route'],
                'module': CRYPTO_ROUTE['module'],
                'latest_determination': (
                    crypto_latest['determination']
                    if crypto_latest else 'NOT_CHECKED'),
            },
            'latest_check_in': latest,
        }

    def record_check_in(self, actor, deployment_location,
                        operational_status) -> dict:
        """Record a platform check-in (operator-only), bound to the
        platform identity's integrity digest via the shared
        foundation, with its receipt inside the transaction."""
        self._require_operator(actor)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE;')
            try:
                try:
                    record = _foundation_record_check_in(
                        db, IDENTITY, deployment_location,
                        operational_status)
                except FoundationDenied as exc:
                    raise MinotaurDenied(str(exc)) from exc
                self._record('MINOTAUR_CHECK_IN', actor=actor,
                             deployment_location=deployment_location,
                             operational_status=operational_status,
                             seq=record['seq'])
                db.commit()
            except Exception:
                db.rollback()
                raise
            return record
