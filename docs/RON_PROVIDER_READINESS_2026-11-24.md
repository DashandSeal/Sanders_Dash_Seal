# RON Technology Provider Readiness Map — Sanders Legal Helpers LLC

**Question:** What would it take for Sanders Legal Helpers LLC to be recognized as an approved RON
(remote online notarization) technology provider in Colorado and Wisconsin, and how does the
Sanders Dash & Seal native stack measure against those requirements today?

**Researched:** 2026-11-24. Requirements are stated only from official sources (Colorado Secretary
of State / Colorado Revised Statutes / 8 CCR 1505-11; Wisconsin DFI / Wis. Stat. ch. 140 /
ch. DFI-CCS 25), each with its source URL. Anything not verified from an official source is
marked **UNVERIFIED** rather than filled in. Stack positions are grounded in
`~/workspace/notarization-build/notarization-map.md`, the preserved repo record
(`docs/NOTARIZATION_ROLLOUT_RECORD_2026-11-24.md`), and the Stage 7 completion state
(native journal built, authority verifiers built, case→native-session bridge built, one audit
discrepancy found and corrected). Nothing in this map overstates the stack: where it lacks a
capability, the map says LACKS.

**Gap-action classes:** **BUILD** = engineering work · **FILING** = owner's application,
signature, or business act · **GATE** = owner approval decision.

---

## Part 1 — The requirements

### A. Colorado (Secretary of State, Notary Program)

**Does Colorado approve RON technology providers? Yes — affirmatively, before they may offer
services.** "Providers must be approved with the Secretary of State before offering remote notary
services in the state of Colorado," and the SOS publishes the current approved-provider list.
— https://www.coloradosos.gov/pubs/notary/FAQ/remote.html (Q4)
— Approved provider list: https://www.coloradosos.gov/notary/pages/remote/public/providerList.xhtml

**Process.** Apply through the SOS notary eFiling system. Published application requirements:
(1) a business registration in good standing with the Colorado Secretary of State; (2) contact
information (an individual's name and business email); (3) review of RULONA (C.R.S. Title 24,
Article 21, Part 5) and the Notary Program Rules; (4) review of the SOS Provider Protocols;
(5) answers to the required technology questions; (6) certification by the provider's authorized
agent that "the provider and its system comply with the requirements of section 24-21-514.5,
C.R.S., and the rules adopted under section 24-21-527, C.R.S."
— https://www.coloradosos.gov/notary/pages/remote/common/intro.xhtml
— Example application incl. all technology questions (Rev. 06/20/2024):
https://www.coloradosos.gov/pubs/notary/files/example-RemoteNotaryProviderApply.pdf
— Provider Protocols: https://coloradosos.gov/pubs/rule_making/files/2020/20201015ProviderProtocols.pdf
*(Caveat, stated honestly: the Protocols PDF as hosted is stamped "WORKING DRAFT ONLY." It is the
document the SOS application page directs applicants to review, and the current example
application's questions track its §1.5 criteria item for item — but the stamp is on the document,
and a filing should confirm the operative version with the SOS.)*

**Fees.** Remote notary provider application **$250**; provider renewal **$250** (online only).
Provider registrations must be **renewed annually** to maintain eligibility (SOS rule revision,
2023). — https://coloradosos.gov/pubs/info_center/fees/notary.html ·
https://www.sos.state.co.us/pubs/newsRoom/pressReleases/2023/PR20230630Notary.html
**Timeline:** no processing timeline is published in the sources read — **UNVERIFIED**.
**Demonstration:** the applicant must state whether it will provide a remote notarization
demonstration if the Secretary of State requests one (example application, p. 11).
**Who may apply:** any business entity meeting the requirements above — the applicant is the
provider company, not an individual notary. No requirement in the sources read that the provider
be a notary's employer. A CO SOS business registration in good standing is required, which for a
foreign (non-Colorado) entity would mean a foreign-entity registration — for Sanders Legal
Helpers LLC, a Colorado entity, this is a good-standing confirmation (**FILING**).

**Technology requirements (Provider Protocols §1.1–1.5, applied through the application):**

| Area | Requirement (official source) |
|---|---|
| Credential analysis (§1.1) | Automated software assisting the notary to verify identity; credential must pass an authenticity test using sound commercial practices — integrity of visual/physical/cryptographic security features, fraud/modification detection, validation against issuing/authoritative sources where available, result delivered to the notary; notary must be able to visually compare credential photo/data against the live individual; capture must verify the individual possesses the credential at the time of the act, images unmanipulated and matching the credential in hand; resolution sufficient for analysis and visual inspection. |
| Dynamic KBA (§1.2) | Quiz of ≥5 questions from public/proprietary data sources, ≥5 answer choices each, ≥80% correct, all answered within 2 minutes; one retake within 24 hours with ≥40% new questions; second failure locks out retry with the same notary for 24 hours. |
| Public key certificate (§1.3) | Digital signatures accompanied by a digital certificate for document integrity; PKI based on X.509 standards. |
| Trusted third-party IDV (§1.4) | Permitted as an alternative, at accuracy ≥ KBA or PKI routes. The application requires a non-MISMO-certified applicant to answer YES to at least one of: credential analysis, dynamic KBA, public key certificate, or trusted third-party verification. |
| MISMO | The application asks whether the provider is MISMO RON certified or in process; non-certified applicants complete the full identity-proofing questions. Whether certification is mandatory is **not stated** in the sources read — the application's structure implies it is not, but that is an inference, marked **UNVERIFIED** as a legal conclusion. |
| Data security & storage (§1.5) | Firewall isolating internet connections from DMZ/internal networks; IDS/IPS; quarterly system hardening scans/audits; file-integrity monitoring; data (incl. backups) in secure locations; ≥256-bit encryption; full-disk or database encryption; cryptographic key-change/management process; data-leak protection; proper media destruction; offsite backups in a secure climate-controlled facility; current vendor patches; vulnerability identification process rated to an industry standard; monthly internal vulnerability scanning + remediation; quarterly internal/external network scans with results acted on. |
| Access control (§1.5.5) | Least-privilege access; **two-factor authentication for all internal and remote system access**; quarterly user-access audits; immediate deactivation of terminated users; disable inactive accounts >90 days. |
| Logging/audit (§1.5.6) | Automated audit trails for user access, administrator/root actions, invalid login attempts with date/time and success/failure; **logs retained ≥1 year**. |
| Security policy (§1.5.7) | Written security policy distributed to all personnel touching the systems, reviewed ≥ annually; background checks and qualification review for all personnel; adherence to Colorado cybersecurity law. |
| Incident response (§1.5.8) | Designated named person responsible for notifying affected customers and the Secretary of State of a data breach; incident response plan including digital forensics and log analysis by computer-forensics experts. |
| Continuity (§1.5.9) | A maintenance plan preserving authenticity/integrity of notarized records and AV recordings if the storage solution becomes obsolete or the provider ceases business, stating where/with whom items will be stored. |
| Privacy | Application asks whether any collected data will be sold to third parties and which affiliates/entities can access PII/non-PII data gathered in the process (example application, pp. 4, 11). |

**Notary-side duties the technology must support** (C.R.S. §24-21-514.5; 8 CCR 1505-11 Rule 5;
SOS Remote Notarization FAQ — https://www.coloradosos.gov/pubs/notary/FAQ/remote.html):
real-time audio-video (parties see/hear each other substantially simultaneously, without
interruption); the **entire interaction recorded**; before recording, the notary must disclose
the recording and its storage details (where, how long) and obtain the individual's **express
consent** to recording and storage; the recording must contain the notary's spoken statement of
name, date/time, document descriptions, the individual's name, any credible witness, and the
identification method used; identity established by personal knowledge, credible witness, or
**at least two different types of identity proofing** (remote presentation + credential analysis
of a government ID bearing signature and photo, plus dynamic KBA, a valid public key certificate,
or another rule-compliant method); notary and individual must be viewing the **same record**,
with all signatures, changes, and attachments made **in real time**; the act recorded in the
notary's **tamper-evident electronic journal** (including the provider used), subject to the
§24-21-519(10)(c) exception; the recording **securely stored for 10 years**; certificate must
indicate the act used audio-video technology; the notary must be **physically located in
Colorado** (the individual may be anywhere; outside-the-U.S. acts carry subject-matter limits);
excluded: records relating to the electoral process, and wills except under the Colorado Uniform
Electronic Wills Act; remote-notary fee cap **$25** per act (§24-21-529(2)). Notary-side
prerequisites the platform will be used by: an active CO commission, SOS remote-notary training
and exam, and an approved remote-notary registration naming at least one provider on record.

### B. Wisconsin (Department of Financial Institutions; Wis. Stat. ch. 140; ch. DFI-CCS 25)

**Does Wisconsin approve RON technology providers? Yes — approval is required before the
platform may be used, and it is granted by the Department on the review of the Remote Notary
Council.** "A provider of communication technology… shall obtain approval… before allowing its
platform to be used by a notary public of this state." Approved providers are added to a **public
list**. — https://docs.legis.wisconsin.gov/document/administrativecode/DFI-CCS%2025.03
(DFI-CCS 25.04(1), (3)(d)); DFI's announcement of the same process:
https://dfi.wi.gov/Pages/About/NewsEvents/NewsReleases/20230524RemoteOnlineNotarizationRules.aspx

**Process (DFI-CCS 25.04(2)–(3)).** The provider submits documentation/evidence to DFI, in the
form and manner DFI accepts, explaining items (a)–(o) (below). Once DFI is satisfied the
application is complete, it is scheduled for a forthcoming **Remote Notary Council meeting**; a
representative of the applicant **with knowledge of its processes and authority to make binding
representations** must be available to participate (by phone/remote means unless the Council
specifies otherwise). The Council may **approve, approve with conditions/limitations, deny,
table, or require supplementation**. Representations made are **binding** on the provider; the
provider must **promptly notify DFI of material changes** to any statement and of **Wisconsin
notaries newly authorized** to use its technology. Approval may be restricted, suspended, or
terminated for violations, false statements, discipline in another jurisdiction, or loss of
confidence (25.04(4)–(5)).
**Fees:** no provider fee is stated anywhere in ch. DFI-CCS 25 — **UNVERIFIED** whether DFI
charges one. **Timeline:** tied to Council meetings; no published processing period —
**UNVERIFIED**. **Who may apply:** "a provider of communication technology" — no requirement in
the rule that the provider be a notary, a notary's employer, or a Wisconsin entity —
**UNVERIFIED** whether any separate Wisconsin business-registration duty applies to an out-of-state
LLC acting as a provider (the rule is silent).

**What the application must explain (DFI-CCS 25.04(2)(a)–(o))** — these are the technology
requirements, stated as demonstrations:
(a) how the provider ensures acts on its platform comply with ss. 140.145 and 140.20 and ch.
DFI-CCS 25; (b) the proposed method of performing a remote act on the technology; (c) how its
**identity proofing** ensures compliance with **s. 140.07** (personal knowledge, or satisfactory
evidence via passport/driver's license/government ID current or expired ≤3 years, or credible
witness — https://docs.legis.wisconsin.gov/statutes/statutes/140/07); (d) whether the technology
and identity proofing meet the **most current MISMO standards**; (e) means ensuring acts are
**accurate, authentic, resistant to tampering, and tamper-evident**; (f) means ensuring **all
parties view the same record** and all signatures, changes, and attachments are made **in real
time**; (g) means ensuring the technology is **secure from hacking or interception**; (h) means
ensuring the act is **recorded and adequately preserved for at least 7 years** after the
recording is made; (i) means ensuring a notary is **properly instructed and competent** on the
technology; (j) **all jurisdictions** where the technology has been approved or disapproved;
(k) the provider's **experience**; (l) warning letters, complaints, or discipline in any
jurisdiction; (m) pending/adjudicated lawsuits relating to notarial acts on the technology;
(n) whether the provider **has and will maintain insurance or other security for errors and
omissions**; (o) anything else DFI or the Council requests.

**Statutory floor the technology must support** (s. 140.145 —
https://docs.legis.wisconsin.gov/statutes/statutes/140/145): communication technology must let
notary and individual communicate **simultaneously by sight and sound** and, when necessary and
consistent with other law, facilitate communication with an individual with a vision, hearing, or
speech impairment; identity via personal knowledge, credible witness, or **at least 2 different
types of identity proofing**; the notary must reasonably confirm the record before them is the
**same record** the individual signed/stated on; the notary (or a person acting on the notary's
behalf) must **create an audio-visual recording** of the act; the recording must be **retained at
least 7 years** (s. 140.145(6)); the certificate must indicate communication technology was used;
before a first remote act the notary must **notify DFI and identify the technologies** to be
used (s. 140.145(7); s. 140.20(2) — https://docs.legis.wisconsin.gov/statutes/statutes/140/20);
the notary's location is determinative (notary located in Wisconsin); excluded transactions:
wills/codicils/testamentary trusts, personal living trusts, most powers of attorney, marital
property agreements, health-care POAs/living wills (s. 140.145(10)). A notary may only use a
provider that has **authorized the notary** to use its technology and is DFI-approved, must have
reviewed s. 140.145 and DFI guidance, and must be competent with the technology (DFI-CCS 25.03).
Wisconsin journal specifics for remote acts were **not verified** from official sources in this
pass — marked **UNVERIFIED**, not assumed.

---

## Part 2 — The native stack, mapped requirement by requirement

Stack evidence key: **[Map]** = notarization-map.md (head 4a415068 + Stages 1–4) ·
**[S7]** = Stage 7 completions (journal, verifiers, bridge; audited, one discrepancy corrected) ·
**[Rec]** = preserved rollout record. Live state reminder: everything below is built and, for
Stages 1–4 + 7, deployed to the instance 2026-11-24 — but every live gate remains the owner's
(0 of 9 approved; `APPROVED_RON_JURISDICTIONS` empty; no operator account; no provider keys).

### Colorado table

| # | Requirement | Stack position | Evidence | Gap action |
|---|---|---|---|---|
| C1 | SOS provider approval + annual renewal; $250/$250; certification of compliance by authorized agent | **LACKS** (not applied) | No filing exists; approval is external by nature | **FILING** (owner signs certification) + **GATE** (decision to seek provider status) |
| C2 | CO SOS business registration in good standing for the applicant entity | **PARTIAL** | Sanders Legal Helpers LLC is the intended CO applicant; current good standing not evidenced in the repo record | **FILING** (confirm/renew good standing) |
| C3 | Real-time two-way AV; entire interaction recorded | **PARTIAL** | LiveKit transport layer exists (`livekit_realtime.py`, `livekit_video.py`, `realtime_api.py`) but is gated by the unapproved `voice_video_provider` gate, unconfigured, answering honest 503s; no LiveKit deployment demonstrated; the designed RON act today runs on BlueNotary's session, not the native layer [Map §3 #19] | **BUILD** (configure/deploy transport, session recording wired end-to-end) + **GATE** (`voice_video_provider`) |
| C4 | Disclosure of recording + storage details and express consent before recording | **PARTIAL** | Native RON rooms implement a consent lifecycle (AWAITING_CONSENT → CONSENT_RECORDED → RECORDING_INDEXED) [Map §3 #13]; the spoken disclosure script (storage where/how-long, statement contents per FAQ A14) is a session-procedure layer not evidenced as built | **BUILD** (consent/disclosure flow + recording-content checklist in the room flow) |
| C5 | Recording securely stored **10 years** | **PARTIAL** | Recording manifests compute 10-year retention in code and bind the recording by digest [Map §3 #14]; but actual AV storage is external and the manifest honestly reports `storage_upload_verified: False`, `continuity_verified: False` [Map §4] — retention is computed, not yet proven against a durable repository | **BUILD** (durable recording repository + verified upload/continuity) |
| C6 | Credential analysis per Protocols §1.1 (automated authenticity test, possession check, visual comparison support) | **LACKS** | No credential-analysis engine exists in the stack. Stage 7 authority verifiers verify the *operator's* identity/commission/provider configuration — not a signer's government credential [S7; Map §3 #4, #18] | **BUILD** (credential-analysis capability, in-house or via a §1.4-compliant third-party IDV integration — an architecture decision for the owner) |
| C7 | Dynamic KBA per §1.2 (5×5, 80%, 2 min, retake rules) **or** PKI route **or** trusted third-party IDV (≥1 required for non-MISMO applicants) | **LACKS** | No KBA exists (it requires public/proprietary data sources the stack does not have); no third-party IDV integration exists | **BUILD** (integrate a KBA/IDV source) + **GATE** (owner chooses the identity-proofing route) |
| C8 | Public key certificate: X.509 PKI digital certificates accompanying signatures (§1.3) | **PARTIAL → LACKS for the X.509 element** | Native signatures are Ed25519 verified against the stored document digest, and the seal honestly reports `commission_verified: False` [Map §3 #16] — sound tamper-evidence, but not X.509 PKI certificates as §1.3 specifies | **BUILD** (X.509 certificate issuance/binding for notary + signer signatures, or rely on the C7 alternative route and document why) |
| C9 | Tamper-evident system; same record viewed by all; signatures/changes in real time | **PARTIAL** | Document custody is hash-addressed with integrity re-reads; manifests digest-bind recordings; GlassBox chain is append-only [Map §3 #15, #20]. A real-time shared-record signing session (all parties on the same record, changes in real time) is not demonstrated — it depends on C3 | **BUILD** (real-time co-signing on the native session) |
| C10 | Tamper-evident **electronic journal** incl. provider used (notary's journal duty) | **PARTIAL** | Stage 7 built the native journal: append-only, hash-chained, written inside the completion transaction, indexed as JOURNAL evidence [S7]. Gap: it is the platform's journal substrate — per-notary journal presentation, the CO-required fields (incl. provider identification on the provider track), and the §24-21-519 field set are not yet mapped field-by-field | **BUILD** (field mapping + per-notary journal view/export) |
| C11 | Data-security program per §1.5 (firewall/IDS, quarterly hardening audits, FIM, 256-bit + full-disk/db encryption, key management, DLP, media destruction, offsite climate-controlled backups, patching, monthly vuln scans) | **LACKS as demonstrated evidence** | The stack has real pieces — fail-closed gates, GlassBox audit trails, watchdog/cert guards, hash-manifest file integrity across the repo [Map §3 #20–22] — but the §1.5 program is operational evidence (network architecture, scan cadences, backup facility, destruction procedure) that does not exist in documented form, and the single-instance deployment cannot truthfully claim several items (e.g., offsite climate-controlled media backups) today | **BUILD** (operational security program + the infrastructure to make each answer true) + **FILING** (the technology-question answers themselves) |
| C12 | Access control: 2FA for all internal/remote access; quarterly access audits; deactivation rules | **PARTIAL** | Platform sign-in is scrypt-based SessionAuth with an owner-held setup token; operator-only routes are enforced [Map §3 #3]. 2FA, quarterly access-audit process, and inactive-account rules are not evidenced | **BUILD** |
| C13 | Logging/audit trails retained ≥1 year; incident-response plan with named breach notifier + forensics | **PARTIAL** | GlassBox provides immutable in-platform audit receipts and provider workflows preserve stages into it [Map §3 #20]; retention period, off-platform log custody, and a written incident-response plan with a designated notifier are not evidenced | **BUILD** (log retention/custody) + **FILING** (name the incident-response designee; adopt the plan) |
| C14 | Continuity/maintenance plan if solution obsolete or provider ceases business (§1.5.9) | **LACKS** | No such plan is documented | **FILING** (owner adopts + files the plan; engineering supports the export path — **BUILD** assist) |
| C15 | Demonstration to SOS on request | **LACKS** (cannot be given truthfully today) | Depends on C3–C9 working end-to-end in the native track | **BUILD** (prerequisite chain) + **FILING** (owner/representative presents) |
| C16 | MISMO RON certification status (asked; mandatory status UNVERIFIED) | **LACKS** | Not MISMO certified; not in process per any record | **GATE** (owner decides whether to pursue MISMO certification in parallel) |

### Wisconsin table

| # | Requirement | Stack position | Evidence | Gap action |
|---|---|---|---|---|
| W1 | DFI/Remote Notary Council approval before platform use; binding representative at a Council meeting; public listing | **LACKS** (not applied) | No filing exists | **FILING** (owner or authorized representative appears) + **GATE** (decision to seek provider status) |
| W2 | Application (a): how platform ensures compliance with ss. 140.145/140.20 + ch. DFI-CCS 25 | **PARTIAL** | The jurisdiction framework records WI with RON status and the gate denies until the owner approves [Map §3 #8–9] — internal compliance machinery exists; the compliance narrative mapped to each statutory element does not | **FILING** (application drafting, engineering-supported) |
| W3 | Application (b): proposed method of performing a remote act | **PARTIAL** | Two designed methods exist (provider track; native track) with a full session/authority/evidence chain [Map §1, §3 #11–17; S7 bridge] — describable today, demonstrable only when W5/C3 works natively | **FILING** + **BUILD** (native session completion) |
| W4 | Application (c): identity proofing per s. 140.07 | **LACKS** | Same gap as C6/C7: no signer credential analysis, no KBA, no IDV integration; s. 140.145(3)(a)3 requires **two different types** of identity proofing (absent personal knowledge/credible witness) and the stack has zero signer-facing types today | **BUILD** + **GATE** (route choice — shared with C7) |
| W5 | Communication technology: simultaneous sight+sound; accessibility facilitation for vision/hearing/speech impairment | **PARTIAL** | LiveKit layer exists, gated/unconfigured (as C3). Accessibility facilitation (owner's own standing direction: real-time language, sign-language, Braille support in the Signal design) is designed intent, not a built RON-session capability | **BUILD** + **GATE** (`voice_video_provider`) |
| W6 | Application (d): MISMO standards conformance statement | **LACKS** | As C16 | **GATE**/**FILING** |
| W7 | Application (e): accurate, authentic, tamper-resistant, tamper-evident | **HAS (design-level), PARTIAL (session-level)** | Strongest native suit: hash-addressed document custody with integrity re-reads, digest-bound recording manifests, Ed25519 signature verification, append-only hash-chained journal + GlassBox chain, fail-closed completion gate requiring the full authority/evidence set [Map §3 #11–17, #20; S7]. Session-level proof waits on W5 | **BUILD** (bind the evidence chain to the live AV session) |
| W8 | Application (f): same record for all parties; signatures/changes/attachments in real time | **PARTIAL** | As C9 | **BUILD** |
| W9 | Application (g): secure from hacking or interception | **PARTIAL** | Fail-closed gates, operator-only routes, encrypted transport by design of the AV layer; no penetration/security evidence package exists (shared with C11) | **BUILD** |
| W10 | Application (h): recording preserved **≥7 years** | **PARTIAL** | The manifest's computed retention is 10 years — which *exceeds* Wisconsin's 7 on paper — against the same unverified external storage as C5 (`storage_upload_verified: False`) | **BUILD** (shared with C5) |
| W11 | Application (i): means of ensuring notaries are instructed and competent on the technology | **LACKS** | No provider-side notary training/onboarding program exists in the stack or records | **BUILD** (training + competency attestation flow) + **FILING** |
| W12 | Application (j)–(m): jurisdictions approved/disapproved; experience; complaints/discipline; lawsuits | **HAS (truthfully answerable)** | The honest answers are short: no other-jurisdiction approvals yet (this filing is the first), no complaints/discipline/lawsuits on record — but they must be the owner's sworn answers, not engineering's | **FILING** (owner attests) |
| W13 | Application (n): E&O insurance or other security, maintained | **LACKS** | No E&O coverage for the provider entity is evidenced | **FILING**/**GATE** (owner procures coverage) |
| W14 | Ongoing duties: notify DFI of material changes + newly authorized WI notaries; representations binding | **LACKS (process)** | No compliance-notification process exists; the platform does track operator authorization internally (SessionAuth operators), which the process can be built on | **BUILD** (notification workflow) + **FILING** |
| W15 | Notary-side supports: notary notifies DFI + identifies technology before first act (s. 140.145(7)/140.20(2)); provider authorizes the notary | **PARTIAL** | Operator account creation exists (owner-held setup token, one-time /auth/setup) [Map §3 #3] — the provider-authorization record for a WI notary can ride on it; the DFI notification itself is the notary's filing | **FILING** (notary-side) + **BUILD** (authorization record) |

---

## Ordered path to recognition

### Colorado
1. **GATE — Owner decides** to seek SOS provider recognition for Sanders Legal Helpers LLC
   (and, in parallel, whether to pursue MISMO RON certification — C16).
2. **FILING — Confirm** the LLC's Colorado SOS business registration stands in good standing (C2).
3. **BUILD — Identity proofing**: credential analysis (C6) + at least one of dynamic KBA / X.509
   PKI / trusted third-party IDV (C7, C8). This is the longest pole; nothing else can be
   demonstrated without it.
4. **BUILD — Native session end-to-end**: configure the AV transport behind the owner's
   `voice_video_provider` gate approval (C3), wire recording capture to a durable repository so
   upload/continuity verify true against the 10-year manifest (C5, C10), real-time same-record
   signing (C9), disclosure/consent flow (C4).
5. **BUILD — Security evidence program** (C11–C13): make each §1.5 answer true and document it —
   network architecture, scan cadences, 2FA, log retention, incident-response plan.
6. **FILING — Adopt the continuity plan** (C14) and complete the technology questions truthfully.
7. **FILING — Owner (authorized agent) signs the certification and files** via SOS eFiling with
   the $250 fee; stand ready to give the SOS a live demonstration (C15).
8. **GATE — Only after listing**: owner approves the internal `ron_notarial` gate and names
   Colorado in `APPROVED_RON_JURISDICTIONS`; commissioned notaries then register as remote
   notaries naming this provider.

### Wisconsin
1. **GATE — Owner decides** to seek DFI/Remote Notary Council approval (and the MISMO posture —
   W6 — since item (d) asks directly).
2. **BUILD — Shared prerequisites with Colorado**: identity proofing with **two** different
   types (W4), native AV session (W5), same-record real-time signing (W8), durable recording
   preservation — the manifest's 10-year computation already exceeds WI's 7-year floor once
   storage verifies (W10), evidence chain bound to the session (W7), security package (W9).
3. **BUILD — Notary instruction/competency program** (W11) and the DFI notification workflow
   (W14, W15).
4. **FILING — Procure/confirm E&O coverage** for the provider entity (W13); owner attests the
   (j)–(m) answers (W12).
5. **FILING — Submit the (a)–(o) documentation to DFI**; owner or a representative with binding
   authority appears before the Remote Notary Council (W1).
6. **GATE — Only after listing**: internal gate + jurisdiction approvals as in Colorado step 8;
   each Wisconsin notary then files their own DFI notification identifying this technology
   before their first remote act.

**Sequencing truth:** the two states share ~80% of the build (identity proofing, live session,
durable recordings, security evidence). Colorado is the natural first filing — its criteria are
published as a checklist an applicant can engineer against, its applicant entity is the home-state
LLC, and its approval then becomes a truthful entry on Wisconsin's item (j) (jurisdictions where
the technology has been approved).

## Decisions that are the owner's alone
- Whether Sanders Legal Helpers LLC seeks provider recognition at all, and in which state first.
- The identity-proofing route: build credential analysis natively, integrate a third-party IDV/KBA
  source, pursue the X.509 PKI route — or a combination (Wisconsin needs two types regardless).
- Whether to pursue MISMO RON certification.
- Every signature: the Colorado certification of compliance, the Wisconsin application and
  (j)–(m) attestations, the binding representations to the Remote Notary Council.
- E&O insurance procurement; naming the incident-response designee; adopting the continuity plan.
- All internal gates, in order: `voice_video_provider` (to build/demonstrate), and — only after a
  state listing exists — `ron_notarial` and the per-state `APPROVED_RON_JURISDICTIONS` entries.
- His own commission posture: provider recognition does not commission any notary; the notaries
  who would sign on the platform need their own commissions + remote registrations (CO) /
  DFI notifications (WI).

## What could NOT be verified from official sources
- **Colorado processing timeline** for provider applications — not published in the sources read.
- **Whether MISMO RON certification is mandatory in Colorado** — the application asks for status
  and routes non-certified applicants to full identity-proofing questions; no official source read
  states a mandate. Treated as UNVERIFIED, not as "not required."
- **The "WORKING DRAFT ONLY" stamp** on the SOS-hosted Provider Protocols PDF — it is the
  document the SOS application page links as the protocols to review, and the 2024 example
  application mirrors it; the stamp is flagged rather than explained away.
- **Wisconsin provider application fee** — none is stated in ch. DFI-CCS 25; whether DFI charges
  one by another route is UNVERIFIED.
- **Wisconsin processing timeline** — approval turns on Remote Notary Council meetings; no
  published period was found.
- **Wisconsin journal specifics for remote acts** — the recording-retention duty (7 years) is
  verified (s. 140.145(6); DFI-CCS 25.04(2)(h)); journal field/format duties for WI remote acts
  were not verified from official sources in this pass.
- **Whether Wisconsin requires any separate business registration** for an out-of-state provider
  entity — ch. DFI-CCS 25 is silent; UNVERIFIED.
- **Current SOS/DFI list membership and any post-2024 rule amendments** beyond the sources read
  on 2026-11-24 — lists change as providers are added; re-check at filing time.
