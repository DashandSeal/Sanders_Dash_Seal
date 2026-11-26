"""Production runtime bindings for Sanders Dash & Seal.

The factory ``deploy.load_application`` / ``wsgi.create_native_application``
expects: ``create_production_bindings()`` returns a
``deploy.deployment.RuntimeBindings`` built from the repository's own
modules — the same modules the test fixture wires by hand
(``worker/test/python_fixture.py``), but against the production data
directory and the central Stripe connection, with a real session auth
instead of the fixture's stub authenticator.

What it wires:
- cases + appointments + quotes + the Stripe ledger share ONE SQLite file
  (``data/ledger.db`` — the same file the webhook ledger in ``wsgi.py``
  uses), because ``AppointmentPayments`` requires the ledger and the
  appointment store to resolve to the same file, and because a checkout
  registered here must be visible to the webhook path that settles it.
- the audit trail is ``GlassBoxAudit`` on ``data/audit.db``.
- sign-in is ``SessionAuth`` on ``data/accounts.db`` (no seeded accounts;
  the operator is created once through ``/auth/setup`` with the
  owner-held ``SDS_OWNER_SETUP_TOKEN``).
- the Stripe client is a real ``stripe.StripeClient`` built from the
  central connection (``core_platform.stripe_connection``). The module
  object that connection's ``stripe_client`` property returns has no
  ``.v1`` namespace in stripe 15.6.0 — only ``StripeClient`` instances
  do — and ``AppointmentPayments.checkout`` calls
  ``client.v1.checkout.sessions.create``; passing the module would
  409 every checkout. When no usable key is configured (or a live key
  is present without the verifier gate) the factory passes an adapter
  whose ``.v1`` raises ``PaymentDenied``, so checkout answers an
  honest 409 while sign-in, requests and quotes keep working.
- the release verifier is True once these bindings exist: this process
  has real bindings, so ``/readyz`` answers 200 and the customer API
  stops answering 503 ``appointments_unavailable``.
- the pipeline / stream bindings stay None: those routes keep their
  honest 503 until a transaction processor is supplied.
- the provider workspace is ``ProviderWorkflows`` on
  ``data/provider_requests.db``, bound to the same cases, operator
  verifier and audit trail. Its clients are built only for provider
  keys the owner has configured (``SIGNWELL_API_KEY`` /
  ``BLUENOTARY_API_KEY``, the names the provider-secret publisher
  uses), each bound to the provider's documented fixed endpoint, so
  an unconfigured provider answers its honest
  ``<provider>_credentials_not_configured`` status from the workflow
  layer instead of faking a connection. ``SIGNWELL_TEST_MODE`` is
  read with the same boolean convention as the Stripe live flags.
- the native track is wired alongside the provider workspace:
  ``NativeNotarySessions`` and the case-to-native-session bridge
  (``CaseNativeBridge``) share ``data/native_notary.db``; the bridge
  reads settlement from the same Stripe ledger, so a case whose
  payment has not settled opens no native session.
- the same ``GlassBoxAudit`` is exposed on the bindings as ``audit``
  so the deployment can wire it into the realtime media routes:
  every room/token issuance decision (granted or denied) is recorded
  on the chain (Phase A remediation, 2026-11-24 — finding F-11).
- the commercial meeting rooms control plane (MASTER Section 22) is
  ``RoomService`` on ``data/rooms.db``, bound to the same cases, the
  session auth's operator verifier and the same audit chain: room
  lifecycle, participant roles, invitations, recording consent and
  retention as governed records. It mints no media token and carries
  no notarial function; media issuance stays behind the
  ``voice_video_provider`` gate in the realtime module (Phase B,
  2026-11-24).
- the Uncle Nickey / Mao healthcare bridge (Three Originals
  Reconstruction Program) is ``UncleNickeyMaoBridge`` on
  ``data/uncle_nickey_mao.db``, bound to the session auth's operator
  verifier and the same audit chain: referrals routing opaque
  references between the six bridged healthcare industries behind a
  jurisdiction geofence and a HIPAA-by-design access guard. It is
  also bound to the Home Healthcare platform below (by-reference
  interoperation, owner-approved 2026-11-24): referrals open
  against Home Healthcare person identifiers against live
  activations, and the bridge serves referral state by subject
  reference — each platform keeps its own store and receipts.
- CareHive OS is ``CareHiveSidecar`` on ``data/carehive_os.db``,
  bound to the same operator verifier and audit chain: supervised
  subjects, hash-chained evidence, postconditions, supervision
  cycles, the evergreen version cycle and local interop envelope
  validation.
- Sanders Home Healthcare & Caregivers is ``HomeHealthcarePlatform``
  on ``data/home_healthcare.db``, bound to the same operator
  verifier, audit chain and the ``RoomService`` above (consultation
  rooms bind through it; the rooms service is not rebuilt):
  client intakes, caregiver assignments and consultation-room links
  across the six healthcare service lines. It is also bound to the
  Uncle Nickey / Mao bridge above: the unified person page shows
  the bridge's referral state for an identifier, and the platform
  serves the bridge a receipted activation-state surface.
- Grantwriter is ``GrantwriterPlatform`` on
  ``data/grantwriter_service.db``, bound to the existing Grantwriter
  base store (constructed by ``app/grantwriter_mother.py``'s
  ``database()`` factory, aimed at ``data/grantwriter.db`` through
  the ``SANDERS_GRANTWRITER_DB`` environment variable it reads), the
  same operator verifier and audit chain, and the established
  approval-gate checker (``core_platform.ai_platform_approval``'s
  ``is_approved``) as its ``approval_checker``: live draft generation
  stays behind the owner's ``grantwriter_purpose`` gate, which is
  UNAPPROVED, so live drafts refuse and offline drafts are labeled
  offline.
- PBDScriptValidationEngine is ``PBDValidationEngine`` on
  ``data/pbd_validation.db``, validating Dual-File Pairs against
  the deployed repository root (the MASTER §13 pre-execution
  validation gate), with the same operator verifier and audit
  chain. It assesses and records; it does not itself execute or
  block other code.
- PBDManifestGenerator is ``PBDManifestGenerator`` on
  ``data/pbd_manifest_generator.db``, generating paired
  ``.pbd.json`` manifests inside the deployed repository root
  (the MASTER §14 generation standard), operator-only, with the
  same audit chain. It never signs: generated manifests are
  UNSIGNED_SOURCE_MANIFEST.
- Vault is ``Vault`` on ``data/vault.db``: the MASTER §9/§20
  execution-lease lifecycle (issuance, expiration, revocation,
  destruction of temporary authority), operator-issued with the
  same audit chain. Only lease-token hashes are stored; the token
  itself is served once, at issuance.
- Global PBD Sentinel is ``PBDSentinel`` on
  ``data/pbd_sentinel.db``, scanning the deployed repository root
  in cycles (the MASTER §15 continuous deployed-state integrity
  monitoring): an accepted-state baseline per governed artifact,
  forensic findings driven through the Detect → Compare →
  Isolate → Alert → Preserve → Verify → Release or Rebuild
  chain, with the same operator verifier and audit chain. It
  records containment state; it does not move files.
- IT AI Manager is ``ITAIManager`` on ``data/it_ai_manager.db``:
  the MASTER §6/§7 operational authority and repair coordination
  platform — incident lifecycle, diagnosis records, Twin-Gate
  step-1 necessity evaluations, work orders bound to the 12
  registered IT agent designs (INTERFACE_ONLY; outcomes are
  reported records, never claimed executions), rollback and
  MINOTAUR-denied failover records, Quality-Agent-bound return
  verification, and reconciliation — with the same operator
  verifier and audit chain.
- TwinGate is ``TwinGateService`` on ``data/twin_gate.db``: the
  MASTER §8 Twin-Gate Authorization Chain as a durable state
  machine — requests bound to one agent/target/method/payload
  hash under the IT AI Manager's commanding authority, CLEARED
  only with both the Manager's sign-off and MINOTAUR clearance
  recorded, execution authorized only after exact re-validation
  with the Glass-Box receipt hash bound into the record,
  post-execution verification, receipt preservation, and
  revocation; MINOTAUR denials terminal (§10) and
  integrity-class failures quarantining the requester (§11) —
  with the same operator verifier and audit chain. The
  prototype ``core_platform/twin_gate.py`` remains untouched.

The factory never invents a boot mechanism: it is loaded only through
the existing ``deployment.load_application`` factory-reference mechanism,
named by the ``SANDERS_RUNTIME_FACTORY`` environment variable (set by
the systemd unit). It is not required for deployment — without the
variable ``wsgi.py`` keeps its diagnostic-only startup.
"""

from __future__ import annotations

import os
from pathlib import Path

from app import grantwriter_mother
from core_platform.ai_platform_approval import is_approved as _gate_is_approved
from core_platform.appointment_payments import AppointmentPayments
from core_platform.appointments import AppointmentStore
from core_platform.carehive_os import CareHiveSidecar
from core_platform.cases import CaseRegistry
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.grantwriter_service import GrantwriterPlatform
from core_platform.home_healthcare import HomeHealthcarePlatform
from core_platform.it_ai_manager import ITAIManager
from core_platform.native_case_bridge import CaseNativeBridge
from core_platform.twin_gate_service import TwinGateService
from core_platform.sharpshooter_service import SharpshooterService
from core_platform.labyrinth_shield_service import LabyrinthShieldService
from core_platform.minotaur_service import MinotaurService
from core_platform.glass_box_audit_service import GlassBoxAuditService
from core_platform.architect_service import ArchitectService
from core_platform.archimedes_service import ArchimedesService
from core_platform.promethean_service import PrometheanService
from core_platform.hydra_q_service import HydraQService
from core_platform.labyrinth_service import LabyrinthService
from core_platform.cerberus_service import CerberusService
from core_platform.chorus_service import ChorusService
from core_platform.cobol_synthetic_ai_service import CobolSyntheticAiService
from core_platform.juggernaut_service import JuggernautService
from core_platform.bozly_service import BozlyService
from core_platform.fraud_rtsa_service import FraudRtsaService
from core_platform.operations_rtsa_service import OperationsRtsaService
from core_platform.surn_service import SurnService
from core_platform.uptime_agent_service import UptimeAgentService
from core_platform.application_agent_service import ApplicationAgentService
from core_platform.database_agent_service import DatabaseAgentService
from core_platform.deployment_agent_service import DeploymentAgentService
from core_platform.infrastructure_agent_service import InfrastructureAgentService
from core_platform.integration_agent_service import IntegrationAgentService
from core_platform.performance_agent_service import PerformanceAgentService
from core_platform.backup_recovery_agent_service import BackupRecoveryAgentService
from core_platform.observability_agent_service import ObservabilityAgentService
from core_platform.quality_agent_service import QualityAgentService
from core_platform.configuration_agent_service import ConfigurationAgentService
from core_platform.it_support_agent_service import ITSupportAgentService
from core_platform.sanders_sentinel_service import SandersSentinelService
from core_platform.lil_mama_service import LilMamaService
from core_platform.baby_girl_service import BabyGirlService
from core_platform.sanders_omniconn_service import SandersOmniconnService
from core_platform.gia_mind_service import GiaMindService
from core_platform.ai_doctor_service import AIDoctorService
from core_platform.ai_medical.enforcement import AIMedicalEnforcement
from core_platform.sanders_ai_psychiatrist_service import SandersAIPsychiatristService
from core_platform.sanders_recon_service import SandersReconService
from core_platform.sanders_senior_living_service import SandersSeniorLivingService
from core_platform.sanders_legal_helpers_service import SandersLegalHelpersService
from core_platform.sanders_education_service import SandersEducationService
from core_platform.sanders_finance_service import SandersFinanceService
from core_platform.sanders_retail_service import SandersRetailService
from core_platform.sanders_logistics_service import SandersLogisticsService
from core_platform.sanders_security_service import SandersSecurityService
from core_platform.sanders_real_estate_service import SandersRealEstateService
from core_platform.sanders_energy_service import SandersEnergyService
from core_platform.sanders_transportation_service import SandersTransportationService
from core_platform.sanders_agriculture_service import SandersAgricultureService
from core_platform.sanders_manufacturing_service import SandersManufacturingService
from core_platform.sanders_consulting_service import SandersConsultingService
from core_platform.sanders_hospitality_service import SandersHospitalityService
from core_platform.sanders_entertainment_service import SandersEntertainmentService
from core_platform.sanders_sports_service import SandersSportsService
from core_platform.sanders_wellness_service import SandersWellnessService
from core_platform.sanders_steward_sentinel_service import SandersStewardSentinelService
from core_platform.sanders_patriot_saint_service import SandersPatriotSaintService
from core_platform.sanders_freedom_revolution_service import SandersFreedomRevolutionService
from core_platform.sanders_strategy_hub_service import SandersStrategyHubService
from core_platform.sanders_global_freedom_service import SandersGlobalFreedomService
from core_platform.sanders_coordinator_service import SandersCoordinatorService
from core_platform.sanders_intelligence_service import SandersIntelligenceService
from core_platform.sanders_ai_research_service import SandersAIResearchService
from core_platform.sanders_research_service import SandersResearchService
from core_platform.sanders_communications_service import SandersCommunicationsService
from core_platform.sanders_banking_hub_service import SandersBankingHubService
from core_platform.sanders_legal_services_service import SandersLegalServicesService
from core_platform.sanders_strategy_intel_service import SandersStrategyIntelService
from core_platform.sanders_analytics_service import SandersAnalyticsService
from core_platform.sanders_innovation_lab_service import SandersInnovationLabService
from core_platform.sanders_supply_chain_service import SandersSupplyChainService
from core_platform.sanders_logical_framework_service import SandersLogicalFrameworkService
from core_platform.sanders_infrastructure_service import SandersInfrastructureService
from core_platform.sanders_technology_service import SandersTechnologyService
from core_platform.sanders_cloud_services_service import SandersCloudServicesService
from core_platform.showtime_service import ShowtimeService
from core_platform.sanders_marketing_service import SandersMarketingService
from core_platform.sanders_sales_service import SandersSalesService
from core_platform.sanders_customer_support_service import SandersCustomerSupportService
from core_platform.sanders_human_resources_service import SandersHumanResourcesService
from core_platform.sanders_security_ops_service import SandersSecurityOpsService
from core_platform.sanders_global_relations_service import SandersGlobalRelationsService
from core_platform.sanders_healthcare_service import SandersHealthcareService
from core_platform.the_godfather_service import TheGodfatherService
from core_platform.sanders_ethics_impact_collective_service import SandersEthicsImpactCollectiveService
from core_platform.native_notary import NativeNotarySessions
from core_platform.pbd_manifest_generator import PBDManifestGenerator
from core_platform.pbd_sentinel import PBDSentinel
from core_platform.pbd_validation import PBDValidationEngine
from core_platform.provider_connections import WriteProviderClient
from core_platform.provider_workflows import ProviderWorkflows
from core_platform.rooms import RoomService
from core_platform.session_auth import SessionAuth
from core_platform.stripe_connection import StripeConnection
from core_platform.stripe_payments import PaymentDenied, PaymentLedger
from core_platform.uncle_nickey_mao import UncleNickeyMaoBridge
from core_platform.upgrade_sidecar import CORE_LAWS
from core_platform.vault import Vault
from deploy.deployment import ALIAS_HOSTS, ORIGIN, RuntimeBindings


def _fee_verifier(case, actor, items):
    """An operator may quote only a case still awaiting human review."""
    return (isinstance(case, dict)
            and case.get('status') == 'AWAITING_HUMAN_REVIEW')


def _eligibility_verifier(cases):
    """A case may pay only while it is awaiting review or review-verified."""
    def verify(appointment, requester):
        try:
            case = cases.get(appointment['case_id'])
            return case.get('status') in ('AWAITING_HUMAN_REVIEW', 'REVIEW_VERIFIED')
        except Exception:
            return False
    return verify


class _UnavailableStripeClient:
    """Stand-in for the Stripe SDK client when no usable key is configured.

    ``AppointmentPayments.checkout`` accesses ``client.v1``; raising
    ``PaymentDenied`` here makes checkout answer its honest 409
    ``checkout_unavailable`` instead of crashing, while the rest of the
    application process keeps working.
    """

    @property
    def v1(self):
        raise PaymentDenied(
            'Stripe client unavailable: no usable Stripe key is configured')


def _stripe_client(connection):
    """A real ``StripeClient`` when the connection permits one.

    Test-mode-first: a live key without the verifier gate
    (``STRIPE_LIVEMODE`` + ``STRIPE_LIVE_VERIFIED``) must never create
    live sessions, so it gets the unavailable adapter too.
    """
    if not connection.secret_key_set:
        return _UnavailableStripeClient()
    if connection.mode not in ('test', 'live'):
        return _UnavailableStripeClient()
    if connection.mode == 'live' and not connection.live_allowed:
        return _UnavailableStripeClient()
    try:
        import stripe
    except ImportError:
        return _UnavailableStripeClient()
    return stripe.StripeClient(connection.secret_key)


SIGNWELL_CREATE_DOCUMENT_URL = (
    'https://www.signwell.com/api/v1/document_templates/documents/')
BLUENOTARY_CREATE_SESSION_URL = (
    'https://app.bluenotary.us/api/integrationsv2/sessions')


class _ProviderClient:
    """Adapt the repo's ``WriteProviderClient`` to the workflow shape.

    ``ProviderWorkflows`` calls ``client.create_request(payload)``; the
    repo client takes the endpoint explicitly, so each adapter binds
    exactly one documented fixed endpoint: SignWell's create-document-
    from-template and BlueNotary's create-notarization-session (API
    v2) — the provider references recorded in
    ``docs/SPEC_CONFORMANCE.md`` (October 22, 2026).
    """

    def __init__(self, provider, api_key, url):
        self._client = WriteProviderClient(provider, api_key)
        self._url = url

    def create_request(self, payload):
        return self._client.create_request(self._url, payload)


def _provider_clients():
    """Live provider clients for the keys the owner has configured.

    A provider whose key is absent (or unusable) is simply left out,
    so ``ProviderWorkflows`` answers its honest
    ``<provider>_credentials_not_configured`` status for it.
    """
    clients = {}
    for provider, env_name, url in (
            ('signwell', 'SIGNWELL_API_KEY', SIGNWELL_CREATE_DOCUMENT_URL),
            ('bluenotary', 'BLUENOTARY_API_KEY',
             BLUENOTARY_CREATE_SESSION_URL)):
        key = (os.environ.get(env_name) or '').strip()
        if not key:
            continue
        try:
            clients[provider] = _ProviderClient(provider, key, url)
        except ValueError:
            continue
    return clients


class LoopbackServiceBinding:
    """Wiring handle for a platform that runs as a standalone loopback
    service (its own host systemd unit + an nginx location in
    deploy/nginx.conf) rather than as an in-process service object:
    the loopback endpoint the served application routes to, and the
    service's own health path. The dispatcher's healthz answers 200
    when this handle is present in the bindings -- the same
    bindings-presence semantics as every in-process platform."""

    def __init__(self, endpoint: str, health_path: str):
        self.endpoint = endpoint
        self.health_path = health_path

    def __repr__(self):
        return (f'LoopbackServiceBinding(endpoint={self.endpoint!r}, '
                f'health_path={self.health_path!r})')


def create_production_bindings():
    """Build the production ``RuntimeBindings`` from the repo's own modules."""
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    shared_db = data_dir / 'ledger.db'

    cases = CaseRegistry(shared_db, CORE_LAWS)
    audit = GlassBoxAudit(data_dir / 'audit.db')
    appointments = AppointmentStore(cases, audit)
    ledger = PaymentLedger(shared_db)

    connection = StripeConnection.from_env()
    stripe_client = _stripe_client(connection)

    site_origins = frozenset(
        {ORIGIN} | {'https://' + host for host in ALIAS_HOSTS})
    auth = SessionAuth(
        data_dir / 'accounts.db', ORIGIN,
        setup_token=os.environ.get('SDS_OWNER_SETUP_TOKEN') or None,
        allowed_origins=site_origins)

    payments = AppointmentPayments(
        appointments, ledger, stripe_client,
        auth.operator_verifier, _fee_verifier,
        _eligibility_verifier(cases), audit, ORIGIN,
        expected_livemode=bool(
            connection.live_allowed and connection.mode == 'live'))

    signwell_test_mode = (os.environ.get('SIGNWELL_TEST_MODE') or ''
                          ).strip().lower() in ('1', 'true', 'yes')
    provider_workflows = ProviderWorkflows(
        data_dir / 'provider_requests.db', cases, auth.operator_verifier,
        audit, _provider_clients(), signwell_test_mode=signwell_test_mode)

    native_sessions = NativeNotarySessions(data_dir / 'native_notary.db')
    native_bridge = CaseNativeBridge(
        data_dir / 'native_notary.db', cases, ledger, native_sessions,
        auth.operator_verifier, audit)

    rooms = RoomService(
        data_dir / 'rooms.db', cases, auth.operator_verifier, audit)

    uncle_nickey_mao = UncleNickeyMaoBridge(
        data_dir / 'uncle_nickey_mao.db', auth.operator_verifier, audit)
    carehive_os = CareHiveSidecar(
        data_dir / 'carehive_os.db', auth.operator_verifier, audit)
    home_healthcare = HomeHealthcarePlatform(
        data_dir / 'home_healthcare.db', auth.operator_verifier, audit,
        rooms=rooms)

    # The Uncle Nickey / Mao <-> Home Healthcare connection
    # (owner-approved 2026-11-24): by-reference interoperation
    # between the two sibling platforms — each binds the other's
    # service surface; neither shares a store and nothing merges.
    uncle_nickey_mao.bind_home_healthcare(home_healthcare)
    home_healthcare.bind_bridge(uncle_nickey_mao)

    # Grantwriter's base store comes from the existing data layer's
    # own database() factory, which reads the SANDERS_GRANTWRITER_DB
    # environment variable for its path: point it at the production
    # data directory for this process before calling the factory.
    os.environ['SANDERS_GRANTWRITER_DB'] = str(data_dir / 'grantwriter.db')
    grantwriter_base = grantwriter_mother.database()
    grantwriter = GrantwriterPlatform(
        data_dir / 'grantwriter_service.db', grantwriter_base,
        auth.operator_verifier, audit,
        approval_checker=_gate_is_approved)

    # PBDScriptValidationEngine (RTSA Build Program): the MASTER
    # §13 Dual-File Pair validation gate over the deployed
    # repository root, on its own store.
    pbd_validation = PBDValidationEngine(
        data_dir / 'pbd_validation.db', repo_root,
        operator_verifier=auth.operator_verifier, audit=audit)

    # PBDManifestGenerator (RTSA Build Program): the MASTER §14
    # manifest generation standard over the deployed repository
    # root, on its own store. Operator-only; never signs.
    pbd_manifest_generator = PBDManifestGenerator(
        data_dir / 'pbd_manifest_generator.db', repo_root,
        operator_verifier=auth.operator_verifier, audit=audit)

    # Vault (RTSA Build Program): the MASTER §9/§20 execution
    # lease lifecycle, on its own store.
    vault = Vault(
        data_dir / 'vault.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Global PBD Sentinel (RTSA Build Program): the MASTER §15
    # continuous deployed-state integrity monitoring over the
    # deployed repository root, on its own store.
    pbd_sentinel = PBDSentinel(
        data_dir / 'pbd_sentinel.db', repo_root,
        operator_verifier=auth.operator_verifier, audit=audit)

    # IT AI Manager (RTSA Build Program): the MASTER §6/§7
    # operational authority and repair coordination platform, on
    # its own store. It binds the 12 agent designs from
    # core_platform.agent_registry; it executes nothing itself.
    it_ai_manager = ITAIManager(
        data_dir / 'it_ai_manager.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # TwinGate (RTSA Build Program): the MASTER §8 authorization
    # chain as a durable state machine, on its own store.
    # Sign-offs and clearances are recorded attestation
    # references; the signers' own platforms record their acts.
    twin_gate = TwinGateService(
        data_dir / 'twin_gate.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Sharpshooter (RTSA Build Program): the production build-out
    # of the sharpshooter/ foundation — durable event store,
    # provider adapter registry with environment credential
    # acquisition, and the API service, on its own store. Its
    # diagnoser is the recovered sharpshooter.core.diagnose.
    sharpshooter = SharpshooterService(
        data_dir / 'sharpshooter.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Sanders Labyrinth Shield (RTSA Build Program): the production
    # build-out of the recovered labyrinth_shield.py foundation —
    # durable evaluation ledger (payload hashes only), durable
    # blocklist, rate limiting, isolation, and the self-integrity
    # pin, on its own store.
    labyrinth_shield = LabyrinthShieldService(
        data_dir / 'labyrinth_shield.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # RTSA Minotaur (RTSA Build Program): the production build-out
    # of the recovered minotaur_sentinel.py foundation — durable
    # operator-pinned baselines over the repository root, recorded
    # patrol cycles, the anomaly lifecycle, and clearance
    # determinations for the Twin-Gate section 8 chain, on its
    # own store.
    minotaur = MinotaurService(
        data_dir / 'minotaur.db',
        Path(__file__).resolve().parent.parent,
        operator_verifier=auth.operator_verifier, audit=audit)

    # Glass-Box Audit (RTSA Build Program): the designed
    # strengthening of the GlassBoxAudit substrate — completeness
    # verification over the audit chain (data/audit.db) and the
    # native notary journal (data/native_notary.db), anchor
    # bundles, witness records, the evidence key registry,
    # snapshot manifests, and restore-drill records, on its own
    # store. The evidence stores are opened read-only; the
    # irreversible retention lock (design decision D4) is not
    # applied and no signing key is provisioned.
    glass_box_audit = GlassBoxAuditService(
        data_dir / 'glass_box_audit.db',
        data_dir / 'audit.db',
        data_dir / 'native_notary.db',
        (data_dir / 'audit.db', data_dir / 'native_notary.db',
         data_dir / 'glass_box_audit.db'),
        operator_verifier=auth.operator_verifier, audit=audit)

    # ARCHITECT (RTSA Build Program): the architecture/design role
    # contract built as its own platform — governed design records,
    # reviews, and recorded human decisions under the contract's
    # discipline (prohibited operations refused by name; the
    # contract stays SPECIFIED and enabled: False), on its own
    # store.
    architect = ArchitectService(
        data_dir / 'architect.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # ARCHIMEDES #43 (RTSA Build Program): the build-engineering
    # role contract built as its own platform — governed build,
    # test, and deployment-record jobs under the contract's
    # discipline (it performs no build, test, or deployment;
    # production deployment is prohibited by its own contract),
    # on its own store.
    archimedes = ArchimedesService(
        data_dir / 'archimedes_43.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # PROMETHEAN (RTSA Build Program): the adversarial-reasoning
    # and red-team role contract built as its own platform —
    # governed evaluation records and evidence-bound findings
    # under the contract's discipline (it performs no attack,
    # probe, or execution; production deployment is prohibited
    # by its own contract), on its own store.
    promethean = PrometheanService(
        data_dir / 'promethean.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # HYDRA-Q (RTSA Build Program): the quantum-resistant
    # cryptographic security role contract built as its own
    # platform — the post-quantum readiness register (assets by
    # reference, family classification, evidence-bound migration
    # determinations) under the contract's discipline (it holds
    # no key material and performs no cryptography), on its own
    # store.
    hydra_q = HydraQService(
        data_dir / 'hydra_q.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # LABYRINTH (RTSA Build Program): the zero-trust and
    # attack-path role contract built as its own platform —
    # governed attack-path analysis records over declared models
    # under the contract's discipline (it performs no scan,
    # probe, or enforcement), on its own store. Separate from
    # Sanders Labyrinth Shield and from RTSA Minotaur — never
    # merged.
    labyrinth = LabyrinthService(
        data_dir / 'labyrinth.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # CERBERUS (RTSA Build Program): the evidence, provenance,
    # and audit role contract built as its own platform —
    # governed evidence-chain assessment and determination
    # records over chains presented by reference, under the
    # contract's discipline (it opens no store, recomputes no
    # chain, and anchors nothing), on its own store. Separate
    # from Glass-Box Audit per MASTER section 20 — never merged.
    cerberus = CerberusService(
        data_dir / 'cerberus.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # CHORUS (RTSA Build Program): the multimodal synthesis and
    # orchestration role contract built as its own platform —
    # governed composition records under the contract's modality
    # discipline (it performs no synthesis and no live
    # orchestration), on its own store.
    chorus = ChorusService(
        data_dir / 'chorus.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # COBOL Synthetic AI (RTSA Build Program): the legacy
    # systems and modernization role contract built as its own
    # platform — governed modernization assessment records
    # under the contract's discipline (it reads, parses,
    # converts, and executes no legacy code, and records no
    # migration approval), on its own store. Daedalus's COBOL
    # Bridge is a Daedalus component, not this platform.
    cobol_synthetic_ai = CobolSyntheticAiService(
        data_dir / 'cobol_synthetic_ai.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # JUGGERNAUT (RTSA Build Program): the execution integrity
    # and verification role contract built as its own platform —
    # governed execution-integrity verification records under
    # the contract's discipline (it performs no execution of
    # any kind; an execution presented without its receipt
    # digest stands EXECUTION_RECEIPT_MISSING, and a presented
    # digest still leaves receipt signature verification
    # required), on its own store. JUGGERNAUT is its own
    # platform — not Hades, not MICHAEL ANGELO — and carries no
    # NAICS codes (owner ruling, 2026-11-24).
    juggernaut = JuggernautService(
        data_dir / 'juggernaut.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Bozly (Bozly Full-Operation Build): the corporate CFO and
    # integrity witness on the live path — machine-event receipts,
    # officer action-integrity receipts through the recovered
    # BozlyAuthGate against owner-configured officer public keys,
    # and claim integrity through the recovered claim engine,
    # on its own store. Its claim assessments run against the
    # production Bozly ledger — the same database the verified
    # Stripe-event recorder writes (wsgi.py: BOZLY_DB_PATH or
    # data/bozly_ledger.db) — so align the environment the claim
    # module reads, the same way the Grantwriter base store is
    # aligned above. Bozly witnesses; it moves no money.
    bozly_ledger_db = Path(
        os.environ.get('BOZLY_DB_PATH')
        or str(data_dir / 'bozly_ledger.db'))
    os.environ['BOZLY_DB_PATH'] = str(bozly_ledger_db)
    bozly = BozlyService(
        data_dir / 'bozly.db', ledger_db_path=bozly_ledger_db,
        operator_verifier=auth.operator_verifier, audit=audit)

    # Fraud RTSA (RTSA Build Program): the fraud intelligence
    # role contract built as its own platform — governed
    # fraud-intelligence case records under the contract's
    # discipline (subjects and signal sets by reference only;
    # a case with no signals stands NO_SIGNALS_SUBMITTED and
    # cannot be determined FRAUD_SUBSTANTIATED; it freezes,
    # holds, reverses, and transfers nothing), on its own
    # store.
    fraud_rtsa = FraudRtsaService(
        data_dir / 'fraud_rtsa.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Operations RTSA (RTSA Build Program): the operational
    # reasoning and incident response role contract built as
    # its own platform — governed operational incident records
    # under the contract's discipline (subjects and incidents
    # by reference only; a record with no active incidents
    # stands NO_INCIDENTS_SUBMITTED and cannot be recorded
    # RESOLVED; it executes nothing, deploys nothing, and
    # dispatches no one), on its own store.
    operations_rtsa = OperationsRtsaService(
        data_dir / 'operations_rtsa.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # SURN (RTSA Build Program Q131, Band 4): the disaster and
    # emergency intelligence role contract built as its own
    # platform — governed emergency-preparedness assessment
    # records under the contract's discipline (subjects, plans,
    # and scopes by reference only; an assessment with no
    # recovery plan stands EMERGENCY_PLAN_MISSING and cannot be
    # determined DRILL_VERIFIED; it dispatches no responders,
    # issues no alerts, and contacts no agency), on its own
    # store.
    surn = SurnService(
        data_dir / 'surn.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Uptime Agent (RTSA Build Program): the first agent of the
    # MASTER §7 IT AI agent matrix built as its own platform —
    # governed uptime records under the agent design's
    # INTERFACE_ONLY discipline (services and observations by
    # reference only; a record with no observations stands
    # NO_OBSERVATIONS_SUBMITTED and no determination can be
    # recorded on it; it probes nothing, restarts nothing, and
    # executes nothing), on its own store.
    uptime_agent = UptimeAgentService(
        data_dir / 'uptime_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Application Agent (RTSA Build Program): the second agent
    # of the MASTER §7 IT AI agent matrix built as its own
    # platform — governed application-health assessment records
    # under the agent design's INTERFACE_ONLY discipline
    # (applications and checks by reference only; an assessment
    # with no checks stands NO_CHECKS_SUBMITTED and no
    # determination can be recorded on it; it repairs nothing,
    # restarts nothing, and executes nothing), on its own
    # store.
    application_agent = ApplicationAgentService(
        data_dir / 'application_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Database Agent (RTSA Build Program): the third agent of
    # the MASTER §7 IT AI agent matrix built as its own
    # platform — governed database-health assessment records
    # under the agent design's INTERFACE_ONLY discipline
    # (databases and checks by reference only; an assessment
    # with no checks stands NO_CHECKS_SUBMITTED and no
    # determination can be recorded on it; it repairs nothing,
    # restores nothing, opens no database, and executes
    # nothing), on its own store.
    database_agent = DatabaseAgentService(
        data_dir / 'database_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Deployment Agent (RTSA Build Program): the fourth agent
    # of the MASTER §7 IT AI agent matrix built as its own
    # platform — governed deployment records under the agent
    # design's INTERFACE_ONLY discipline (deployments and
    # changes by reference only; a record with no changes
    # stands NO_CHANGES_SUBMITTED and no determination can be
    # recorded on it; the MASTER §10 MINOTAUR-denial failover
    # sequence is carried as a governed record flow — a denial
    # enters by reference, refuses the cleared determination,
    # and the failover outcome requires all eight designed
    # steps recorded in order; it deploys nothing, rolls back
    # nothing, bypasses nothing, and executes nothing), on its
    # own store.
    deployment_agent = DeploymentAgentService(
        data_dir / 'deployment_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Infrastructure Agent (RTSA Build Program): the fifth
    # agent of the MASTER §7 IT AI agent matrix built as its
    # own platform — governed infrastructure-health assessment
    # records under the agent design's INTERFACE_ONLY
    # discipline (infrastructure and checks by reference only;
    # an assessment with no checks stands NO_CHECKS_SUBMITTED
    # and no determination can be recorded on it; it restores
    # nothing, repairs nothing, provisions nothing, and
    # executes nothing), on its own store.
    infrastructure_agent = InfrastructureAgentService(
        data_dir / 'infrastructure_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Integration Agent (RTSA Build Program): the sixth agent
    # of the MASTER §7 IT AI agent matrix built as its own
    # platform — governed integration records under the agent
    # design's INTERFACE_ONLY discipline (integrations and
    # bounded operations by reference only; a record with no
    # operations stands NO_OPERATIONS_SUBMITTED and a record
    # with no Vault lease reference stands NO_LEASE_BOUND,
    # and the bounded-execution determination is refused on
    # both; the lease binding is to the Q3 Vault by reference
    # only — this platform never issues, verifies, or
    # consumes a lease; it executes nothing externally and
    # calls no external system), on its own store.
    integration_agent = IntegrationAgentService(
        data_dir / 'integration_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Performance Agent (RTSA Build Program): the seventh
    # agent of the MASTER §7 IT AI agent matrix built as its
    # own platform — governed performance records under the
    # agent design's INTERFACE_ONLY discipline (subjects and
    # measurements by reference only; a record with no
    # measurements stands NO_MEASUREMENTS_SUBMITTED and no
    # determination can be recorded on it; it remediates
    # nothing, tunes nothing, scales nothing, takes no live
    # measurement, and executes nothing), on its own store.
    performance_agent = PerformanceAgentService(
        data_dir / 'performance_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Backup & Recovery Agent platform (Q43, RTSA Build
    # Program tranche 10): governed backup records over its
    # own store, built under its design's INTERFACE_ONLY
    # discipline — it runs no backup, restores nothing, and
    # executes nothing.
    backup_recovery_agent = BackupRecoveryAgentService(
        data_dir / 'backup_recovery_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Observability Agent platform (Q44, RTSA Build Program
    # tranche 10): governed observation records over its own
    # store, built under its design's INTERFACE_ONLY
    # discipline — it collects no telemetry, queries no live
    # system, and observes nothing live.
    observability_agent = ObservabilityAgentService(
        data_dir / 'observability_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Quality Agent platform (Q45, RTSA Build Program
    # tranche 11): governed verification records over its
    # own store, built under its design's INTERFACE_ONLY
    # discipline — it runs no functional test, verifies no
    # live system, and modifies no state.
    quality_agent = QualityAgentService(
        data_dir / 'quality_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Configuration Agent platform (Q46, RTSA Build Program
    # tranche 11): governed configuration records over its
    # own store, built under its design's INTERFACE_ONLY
    # discipline — it applies no configuration, modifies
    # no configuration, and reconciles no live system.
    configuration_agent = ConfigurationAgentService(
        data_dir / 'configuration_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # IT Support Agent platform (Q47, RTSA Build Program
    # tranche 11): governed support records over its own
    # store, built under its design's INTERFACE_ONLY
    # discipline — it resolves no case itself, contacts no
    # requester, and accesses no remote system.
    it_support_agent = ITSupportAgentService(
        data_dir / 'it_support_agent.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Sentinel platform (Q48, RTSA Build Program
    # tranche 12): governed global-watch records over its
    # own store, under the watchdog law — it detects and
    # escalates only, holds no decision authority, and
    # takes no action against any subject. Bound to the
    # repository root for its bloodline governance coverage
    # (founder's ruling, 2026-11-25): the governed watch
    # over the bloodline governance records in docs/.
    sanders_sentinel = SandersSentinelService(
        data_dir / 'sanders_sentinel.db',
        operator_verifier=auth.operator_verifier, audit=audit,
        repo_root=repo_root)
    # Lil Mama platform (Q49, RTSA Build Program tranche
    # 12): governed human-oversight records over its own
    # store, under the watchdog law — she detects and
    # escalates only, holds no decision authority, and
    # takes no action against any subject. Her public
    # business face is served at /lil-mama.
    lil_mama = LilMamaService(
        data_dir / 'lil_mama.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Baby Girl platform (Q50, RTSA Build Program tranche
    # 12): governed redundant-monitoring records and
    # forensic custody records over her own store, under
    # the watchdog law — she detects and escalates only,
    # holds no decision authority, alters no evidence,
    # and takes no action against any subject. Her public
    # business face is served at /baby-girl.
    baby_girl = BabyGirlService(
        data_dir / 'baby_girl.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Omniconn platform (Q51, RTSA Build Program
    # tranche 13): governed oversight and AI-coordination
    # records over its own store — oversight and
    # coordination by record only; it directs, commands,
    # overrides, and surveils nothing.
    sanders_omniconn = SandersOmniconnService(
        data_dir / 'sanders_omniconn.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Gia Mind platform (Q52, RTSA Build Program tranche
    # 13): governed ethics and system-balance review
    # records over her own store — she reviews and
    # records only; she overrides no decision and
    # rebalances no live system. No persona (D-N2 unruled).
    gia_mind = GiaMindService(
        data_dir / 'gia_mind.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Constitutional Execution Stack (AI Medical fix build):
    # the enforcement layer over AI Doctor and Sanders AI
    # Psychiatrist. Constructed from the environment; when
    # the owner-provisioned bundle/keys are absent it stands
    # NOT_PROVISIONED with the named missing state and the
    # two services refuse outcome commits through it — fail
    # closed, never waved through, no keys invented here.
    ai_medical_enforcement = AIMedicalEnforcement.from_environment(
        data_dir, glass_box_audit=audit)
    # AI Doctor platform (Q53, RTSA Build Program tranche
    # 13): governed AI-system health case records over
    # his own store — AI-to-AI only, never humans;
    # human subjects are refused by construction and
    # determinations are records, never acts.
    ai_doctor = AIDoctorService(
        data_dir / 'ai_doctor.db',
        operator_verifier=auth.operator_verifier, audit=audit,
        enforcement=ai_medical_enforcement)
    # Sanders AI Psychiatrist platform (Q54, RTSA Build
    # Program tranche 14): governed AI-system psychiatric
    # assessment records over her own store — AI-to-AI
    # only, never humans; human subjects are refused by
    # construction and determinations are records, never
    # acts. No persona (unruled).
    sanders_ai_psychiatrist = SandersAIPsychiatristService(
        data_dir / 'sanders_ai_psychiatrist.db',
        operator_verifier=auth.operator_verifier, audit=audit,
        enforcement=ai_medical_enforcement)
    # Sanders Recon platform (Q55, RTSA Build Program
    # tranche 14): governed security-intelligence records
    # over his own store — records only; he collects
    # nothing, intercepts nothing, and accesses no
    # external system. Name per owner ruling D-N4.
    sanders_recon = SandersReconService(
        data_dir / 'sanders_recon.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Senior Living platform (Q56, RTSA Build
    # Program tranche 14): governed care-coordination
    # records over its own store — the platform, distinct
    # from Sanders Senior Living LLC; it operates no
    # residence and provides no care itself.
    sanders_senior_living = SandersSeniorLivingService(
        data_dir / 'sanders_senior_living.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Legal Helpers platform (Q57, RTSA Build
    # Program tranche 15): governed legal-support records
    # over its own store — the platform, distinct from
    # Sanders Legal Helpers LLC; it renders no legal advice,
    # represents no client, and practices no law.
    sanders_legal_helpers = SandersLegalHelpersService(
        data_dir / 'sanders_legal_helpers.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Education platform (Q58, RTSA Build Program
    # tranche 15): governed education-program records over
    # its own store — the record platform for its designed
    # education purpose; it delivers no instruction, assesses
    # no learner, and certifies no one.
    sanders_education = SandersEducationService(
        data_dir / 'sanders_education.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Finance platform (Q59, RTSA Build Program
    # tranche 15): governed finance records over its own
    # store — records only; it holds no funds, moves no
    # money, and pays no one. Bozly remains the HQ CFO.
    sanders_finance = SandersFinanceService(
        data_dir / 'sanders_finance.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Retail platform (Q60, RTSA Build Program
    # tranche 16): governed retail-operations records over
    # its own store — it sells nothing, fulfills no
    # order, and processes no payment itself.
    sanders_retail = SandersRetailService(
        data_dir / 'sanders_retail.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Logistics platform (Q61, RTSA Build Program
    # tranche 16): governed supply-chain records over its
    # own store — it ships nothing, dispatches no
    # fleet, and procures nothing itself.
    sanders_logistics = SandersLogisticsService(
        data_dir / 'sanders_logistics.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Security platform (Q62, RTSA Build Program
    # tranche 16): governed security-services records
    # over its own store — it enforces nothing, hunts
    # no threat, and accesses no system itself.
    sanders_security = SandersSecurityService(
        data_dir / 'sanders_security.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Real Estate platform (Q63, RTSA Build
    # Program tranche 17): governed real-estate records
    # over its own store — it sells no property,
    # leases no property, and closes no transaction
    # itself.
    sanders_real_estate = SandersRealEstateService(
        data_dir / 'sanders_real_estate.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Energy platform (Q64, RTSA Build Program
    # tranche 17): governed energy records over its own
    # store — it supplies no energy, operates no
    # grid, and dispatches no power itself.
    sanders_energy = SandersEnergyService(
        data_dir / 'sanders_energy.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Transportation platform (Q65, RTSA Build
    # Program tranche 17): governed transportation-
    # coordination records over its own store — it
    # transports no passenger, dispatches no vehicle,
    # and operates no route itself.
    sanders_transportation = SandersTransportationService(
        data_dir / 'sanders_transportation.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Agriculture platform (Q66, RTSA Build
    # Program tranche 18): governed agriculture
    # records over its own store — it grows no
    # crops, raises no livestock, and processes
    # no food itself.
    sanders_agriculture = SandersAgricultureService(
        data_dir / 'sanders_agriculture.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Manufacturing platform (Q67, RTSA Build
    # Program tranche 18): governed manufacturing
    # records over its own store — it manufactures
    # no goods, operates no plant, and assembles
    # no product itself.
    sanders_manufacturing = SandersManufacturingService(
        data_dir / 'sanders_manufacturing.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Consulting platform (Q68, RTSA Build
    # Program tranche 18): governed consulting
    # records over its own store — it advises no
    # client, delivers no consulting, and bills
    # no client itself.
    sanders_consulting = SandersConsultingService(
        data_dir / 'sanders_consulting.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Hospitality platform (Q69, RTSA Build
    # Program tranche 19): governed hospitality
    # records over its own store — it books no
    # stay, hosts no guest, and operates no
    # property itself.
    sanders_hospitality = SandersHospitalityService(
        data_dir / 'sanders_hospitality.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Entertainment platform (Q70, RTSA Build
    # Program tranche 19): governed entertainment
    # records over its own store — it produces
    # no content, broadcasts nothing, and
    # distributes nothing itself. Distinct from
    # Showtime (D-N10).
    sanders_entertainment = SandersEntertainmentService(
        data_dir / 'sanders_entertainment.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Sports platform (Q71, RTSA Build
    # Program tranche 19): governed sports
    # records over its own store — it stages
    # no event, sells no ticket, and manages
    # no team itself.
    sanders_sports = SandersSportsService(
        data_dir / 'sanders_sports.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Wellness platform (Q72, RTSA Build
    # Program tranche 20): governed wellness
    # records over its own store — it delivers
    # no care, provides no treatment, and
    # prescribes nothing itself. Distinct from
    # the healthcare identities (catalog 64/96/132).
    sanders_wellness = SandersWellnessService(
        data_dir / 'sanders_wellness.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Steward Sentinel platform (Q73,
    # RTSA Build Program tranche 20): governed
    # platform-defense records over its own
    # store — it integrates no agency, runs no
    # counterintelligence, and enforces no defense
    # itself. No persona (D-N15 unruled).
    sanders_steward_sentinel = SandersStewardSentinelService(
        data_dir / 'sanders_steward_sentinel.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Patriot Saint platform (Q74, RTSA
    # Build Program tranche 20): governed
    # governance records over its own store — it
    # issues no directive, exercises no authority,
    # and delivers no briefing itself. Separate
    # from The Godfather (owner correction).
    sanders_patriot_saint = SandersPatriotSaintService(
        data_dir / 'sanders_patriot_saint.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Freedom Revolution platform (Q75,
    # RTSA Build Program tranche 21): governed
    # democracy-framework records over its own
    # store — it integrates no agency, supports
    # no regime change, and enforces no rights
    # itself. Persona Uncle Freedom (owner-ruled).
    sanders_freedom_revolution = SandersFreedomRevolutionService(
        data_dir / 'sanders_freedom_revolution.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Strategy Hub platform (Q76, RTSA
    # Build Program tranche 21): governed
    # strategic planning records over its own
    # store — it executes no strategy, conducts
    # no war game, and directs no operations
    # itself. Radar is a display name only (D-N14).
    sanders_strategy_hub = SandersStrategyHubService(
        data_dir / 'sanders_strategy_hub.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Global Freedom platform (Q77,
    # RTSA Build Program tranche 21): governed
    # global-operations records over its own
    # store — it conducts no operations,
    # operates across no border, and directs
    # no partners itself. Distinct from Sanders
    # Freedom Revolution (catalog 86).
    sanders_global_freedom = SandersGlobalFreedomService(
        data_dir / 'sanders_global_freedom.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Coordinator platform (Q78,
    # RTSA Build Program tranche 22): governed
    # platform-coordination records over its
    # own store — it coordinates no platform,
    # integrates no platform, and automates
    # no workflow itself. Persona Butterscotch
    # (owner-ruled).
    sanders_coordinator = SandersCoordinatorService(
        data_dir / 'sanders_coordinator.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Intelligence platform (Q79,
    # RTSA Build Program tranche 22): governed
    # intelligence-analysis records over its
    # own store — it runs no covert operation,
    # collects no intelligence, and accesses
    # no classified system itself. Name per
    # owner ruling D-N5.
    sanders_intelligence = SandersIntelligenceService(
        data_dir / 'sanders_intelligence.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders AI Research platform (Q80,
    # RTSA Build Program tranche 22): governed
    # AI-research records over its own store
    # — it conducts no research, develops no
    # algorithm, and trains no model itself.
    # Separate from Sanders Research (D-N11).
    sanders_ai_research = SandersAIResearchService(
        data_dir / 'sanders_ai_research.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Research platform (Q81,
    # RTSA Build Program tranche 23): governed
    # medical-research records over its own
    # store — it runs no clinical trial,
    # conducts no research, and enrolls no
    # subjects itself. Separate from Sanders
    # AI Research (D-N11).
    sanders_research = SandersResearchService(
        data_dir / 'sanders_research.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Communications platform (Q82,
    # RTSA Build Program tranche 23): governed
    # communications records over its own
    # store — it transmits no message,
    # operates no network, and encrypts no
    # traffic itself.
    sanders_communications = SandersCommunicationsService(
        data_dir / 'sanders_communications.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Banking Hub platform (Q83,
    # RTSA Build Program tranche 23): governed
    # banking-operations records over its own
    # store — it opens no account, moves no
    # funds, and disburses no grants itself.
    sanders_banking_hub = SandersBankingHubService(
        data_dir / 'sanders_banking_hub.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Legal Services platform (Q84,
    # RTSA Build Program tranche 24): governed
    # legal-services records over its own
    # store — it provides no legal advice,
    # represents no client, and files no
    # court action itself. Separate from
    # Sanders Legal Helpers (catalog #66).
    sanders_legal_services = SandersLegalServicesService(
        data_dir / 'sanders_legal_services.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Strategy Intel platform (Q85,
    # RTSA Build Program tranche 24): governed
    # strategic-intelligence records over its
    # own store — it collects no intelligence,
    # conducts no surveillance, and runs no
    # operation itself. Radar is a display
    # name only (D-N14), never an identifier.
    sanders_strategy_intel = SandersStrategyIntelService(
        data_dir / 'sanders_strategy_intel.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Analytics platform (Q86,
    # RTSA Build Program tranche 24): governed
    # analytics records over its own store
    # — it runs no analysis, trains no
    # model, and accesses no live data itself.
    sanders_analytics = SandersAnalyticsService(
        data_dir / 'sanders_analytics.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Innovation Lab platform (Q87,
    # RTSA Build Program tranche 25): governed
    # innovation records over its own store
    # — it conducts no experiment, files no
    # patent, and develops no product itself.
    sanders_innovation_lab = SandersInnovationLabService(
        data_dir / 'sanders_innovation_lab.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Supply Chain platform (Q88,
    # RTSA Build Program tranche 25): governed
    # supply-chain records over its own store
    # — it ships no goods, procures no
    # materials, and dispatches no shipment
    # itself. Distinct from Sanders Logistics
    # (catalog #70); the Flow nickname conflict
    # is recorded, never harmonized.
    sanders_supply_chain = SandersSupplyChainService(
        data_dir / 'sanders_supply_chain.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Logical Framework platform (Q89,
    # RTSA Build Program tranche 25): governed
    # operations-framework records over its own
    # store — it enforces no SOP, modifies no
    # process, and directs no operation itself.
    sanders_logical_framework = SandersLogicalFrameworkService(
        data_dir / 'sanders_logical_framework.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Infrastructure platform (Q90,
    # RTSA Build Program tranche 26): governed
    # infrastructure-operations records over its
    # own store — it operates no infrastructure,
    # provisions no capacity, and repairs nothing
    # itself. Distinct from the Infrastructure
    # Agent (catalog #46).
    sanders_infrastructure = SandersInfrastructureService(
        data_dir / 'sanders_infrastructure.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Technology platform (Q91, RTSA
    # Build Program tranche 26): governed
    # technology records over its own store
    # — it develops no software, deploys no
    # software, and runs no pipeline itself.
    sanders_technology = SandersTechnologyService(
        data_dir / 'sanders_technology.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Cloud Services platform (Q92,
    # RTSA Build Program tranche 26): governed
    # cloud-services records over its own store
    # — it provisions no cloud, deploys to no
    # cloud, and migrates no workload itself.
    # Core Law 10: Oracle Always Free remains
    # the permanent home.
    sanders_cloud_services = SandersCloudServicesService(
        data_dir / 'sanders_cloud_services.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Showtime platform (Q93, RTSA Build
    # Program tranche 27): the owner's D-N10
    # unification of Sanders Media and Sanders
    # Media Hub — governed media records over
    # its own store — it produces no media,
    # broadcasts nothing, and distributes no
    # content itself.
    showtime = ShowtimeService(
        data_dir / 'showtime.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Marketing platform (Q94, RTSA
    # Build Program tranche 27): governed
    # marketing records over its own store
    # — it launches no campaign, purchases no
    # advertising, and publishes nothing itself.
    sanders_marketing = SandersMarketingService(
        data_dir / 'sanders_marketing.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Sales platform (Q95, RTSA
    # Build Program tranche 27): governed
    # sales records over its own store — it
    # closes no sale, processes no order, and
    # charges no customer itself; payments
    # remain the flagship's central Stripe
    # connection.
    sanders_sales = SandersSalesService(
        data_dir / 'sanders_sales.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Customer Support platform (Q96,
    # RTSA Build Program tranche 28): governed
    # customer support records over its own store
    # — it sends no message, contacts no
    # customer, and dispatches no agent itself.
    sanders_customer_support = SandersCustomerSupportService(
        data_dir / 'sanders_customer_support.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Human Resources platform (Q97,
    # RTSA Build Program tranche 28): governed
    # human resources records over its own store
    # — it hires no candidate, terminates no
    # employee, and runs no payroll itself.
    sanders_human_resources = SandersHumanResourcesService(
        data_dir / 'sanders_human_resources.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Security Ops platform (Q98, RTSA
    # Build Program tranche 28): governed
    # security operations records over its own
    # store — it runs no surveillance, operates
    # no access control, and dispatches no
    # patrol itself.
    sanders_security_ops = SandersSecurityOpsService(
        data_dir / 'sanders_security_ops.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Global Relations platform (Q99,
    # RTSA Build Program tranche 29): governed
    # global relations records over its own store
    # — it conducts no diplomacy, negotiates no
    # treaty, and forms no alliance itself.
    sanders_global_relations = SandersGlobalRelationsService(
        data_dir / 'sanders_global_relations.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Healthcare platform (Q100, RTSA
    # Build Program tranche 29): governed
    # healthcare management records over its own
    # store — it treats no patient, accesses no
    # patient record, and holds no PHI at all.
    sanders_healthcare = SandersHealthcareService(
        data_dir / 'sanders_healthcare.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # The Godfather platform (Q101, RTSA Build
    # Program tranche 29): governed matter
    # records over its own store — it provides
    # no protection, transacts no business, and
    # issues no directive itself.
    the_godfather = TheGodfatherService(
        data_dir / 'the_godfather.db',
        operator_verifier=auth.operator_verifier, audit=audit)
    # Sanders Ethics & Impact Collective (SEIC)
    # platform (owner-directed, 2026-11-25):
    # governed engagement records over its own
    # store — it practices no law, administers
    # no grant, and disburses no funds itself.
    sanders_ethics_impact_collective = SandersEthicsImpactCollectiveService(
        data_dir / 'sanders_ethics_impact_collective.db',
        operator_verifier=auth.operator_verifier, audit=audit)

    # Loopback sidecar platforms (Secretary, Money Factory Legal Aid):
    # standalone FastAPI apps running as host systemd services on
    # loopback -- Secretary (uvicorn 127.0.0.1:8791, unit installed by
    # sanders-corporations-secretary/deploy/oracle/deploy_secretary.sh)
    # and Money Factory Legal Aid (uvicorn 127.0.0.1:8668, unit in
    # money_factory_legal_aid_v1_668/infra/oracle_linux_9/) -- reached
    # publicly through the nginx locations in deploy/nginx.conf. The
    # handle below is the wiring the dispatcher's healthz checks for
    # presence, exactly as for the in-process platforms.
    secretary = LoopbackServiceBinding(
        endpoint='http://127.0.0.1:8791', health_path='/api/health')
    money_factory_legal_aid = LoopbackServiceBinding(
        endpoint='http://127.0.0.1:8668', health_path='/health')

    return RuntimeBindings(
        appointments=appointments,
        payments=payments,
        authenticate=auth.authenticate,
        auth_app=auth.auth_app,
        release_verifier=lambda: True,
        provider_workflows=provider_workflows,
        native_bridge=native_bridge,
        audit=audit,
        rooms=rooms,
        uncle_nickey_mao=uncle_nickey_mao,
        carehive_os=carehive_os,
        home_healthcare=home_healthcare,
        grantwriter=grantwriter,
        pbd_validation=pbd_validation,
        pbd_manifest_generator=pbd_manifest_generator,
        vault=vault,
        pbd_sentinel=pbd_sentinel,
        it_ai_manager=it_ai_manager,
        twin_gate=twin_gate,
        sharpshooter=sharpshooter,
        labyrinth_shield=labyrinth_shield,
        minotaur=minotaur,
        glass_box_audit=glass_box_audit,
        architect=architect,
        archimedes=archimedes,
        promethean=promethean,
        hydra_q=hydra_q,
        labyrinth=labyrinth,
        cerberus=cerberus,
        chorus=chorus,
        cobol_synthetic_ai=cobol_synthetic_ai,
        juggernaut=juggernaut,
        bozly=bozly,
        fraud_rtsa=fraud_rtsa,
        operations_rtsa=operations_rtsa,
        surn=surn,
        uptime_agent=uptime_agent,
        application_agent=application_agent,
        database_agent=database_agent,
        deployment_agent=deployment_agent,
        infrastructure_agent=infrastructure_agent,
        integration_agent=integration_agent,
        performance_agent=performance_agent,
        backup_recovery_agent=backup_recovery_agent,
        observability_agent=observability_agent,
        quality_agent=quality_agent,
        configuration_agent=configuration_agent,
        it_support_agent=it_support_agent,
        sanders_sentinel=sanders_sentinel,
        lil_mama=lil_mama,
        baby_girl=baby_girl,
        sanders_omniconn=sanders_omniconn,
        gia_mind=gia_mind,
        ai_doctor=ai_doctor,
        sanders_ai_psychiatrist=sanders_ai_psychiatrist,
        sanders_recon=sanders_recon,
        sanders_senior_living=sanders_senior_living,
        sanders_legal_helpers=sanders_legal_helpers,
        sanders_education=sanders_education,
        sanders_finance=sanders_finance,
        sanders_retail=sanders_retail,
        sanders_logistics=sanders_logistics,
        sanders_security=sanders_security,
        sanders_real_estate=sanders_real_estate,
        sanders_energy=sanders_energy,
        sanders_transportation=sanders_transportation,
        sanders_agriculture=sanders_agriculture,
        sanders_manufacturing=sanders_manufacturing,
        sanders_consulting=sanders_consulting,
        sanders_hospitality=sanders_hospitality,
        sanders_entertainment=sanders_entertainment,
        sanders_sports=sanders_sports,
        sanders_wellness=sanders_wellness,
        sanders_steward_sentinel=sanders_steward_sentinel,
        sanders_patriot_saint=sanders_patriot_saint,
        sanders_freedom_revolution=sanders_freedom_revolution,
        sanders_strategy_hub=sanders_strategy_hub,
        sanders_global_freedom=sanders_global_freedom,
        sanders_coordinator=sanders_coordinator,
        sanders_intelligence=sanders_intelligence,
        sanders_ai_research=sanders_ai_research,
        sanders_research=sanders_research,
        sanders_communications=sanders_communications,
        sanders_banking_hub=sanders_banking_hub,
        sanders_legal_services=sanders_legal_services,
        sanders_strategy_intel=sanders_strategy_intel,
        sanders_analytics=sanders_analytics,
        sanders_innovation_lab=sanders_innovation_lab,
        sanders_supply_chain=sanders_supply_chain,
        sanders_logical_framework=sanders_logical_framework,
        sanders_infrastructure=sanders_infrastructure,
        sanders_technology=sanders_technology,
        sanders_cloud_services=sanders_cloud_services,
        showtime=showtime,
        sanders_marketing=sanders_marketing,
        sanders_sales=sanders_sales,
        sanders_customer_support=sanders_customer_support,
        sanders_human_resources=sanders_human_resources,
        sanders_security_ops=sanders_security_ops,
        sanders_global_relations=sanders_global_relations,
        sanders_healthcare=sanders_healthcare,
        the_godfather=the_godfather,
        sanders_ethics_impact_collective=sanders_ethics_impact_collective,
        secretary=secretary,
        money_factory_legal_aid=money_factory_legal_aid,
    )
