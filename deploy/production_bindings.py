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
  jurisdiction geofence and a HIPAA-by-design access guard.
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
  across the six healthcare service lines.
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
    )
