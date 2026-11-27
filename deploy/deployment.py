"""
WSGI deployment boundary for the existing Sanders Dash & Seal application.

Default startup serves existing assets and diagnostics only. Trusted production
adapters are supplied by the administrator, behind an external verified bootstrap.
Neither environment configuration nor an HTTP request grants production authority.
"""

from dataclasses import dataclass, replace
import importlib
import json
import os
import re
from pathlib import Path

from app.customer_app import ASSETS as CUSTOMER_ASSETS, create_customer_app
from core_platform.free_resources import catalog as free_resource_catalog
from core_platform.pipeline_api import create_pipeline_app, TransactionStore
from core_platform.stream_api import create_stream_app

CANONICAL_HOST = 'sandersdashandseal.com'
ALIAS_HOSTS = {'www.sandersdashandseal.com', 'sanderslegalhelpersllc.com', 'www.sanderslegalhelpersllc.com', 'sanderssixshield.com', 'www.sanderssixshield.com', 'sanderssecurestack.com', 'www.sanderssecurestack.com', 'sandersemergencyglobalcommunication.com', 'www.sandersemergencyglobalcommunication.com', 'sandersnexusshield.com', 'www.sandersnexusshield.com', 'sanderssixindustry.com', 'www.sanderssixindustry.com'}
ORIGIN = 'https://' + CANONICAL_HOST
# Every origin a browser may POST from: the canonical host plus every alias
# host. The customer app and the session auth both check POST Origins
# against this set; checking only the canonical origin 403d every POST
# from an alias host (sign-in, appointment request, quote, checkout).
SITE_ORIGINS = frozenset({ORIGIN} | {'https://' + host for host in ALIAS_HOSTS})
FACTORY = re.compile(r'([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))*(?::([A-Za-z_]\w*))?', re.ASCII)
WEB_ROOT = Path(__file__).resolve().parent.parent / 'web'

class DeploymentConfigurationError(ValueError):
    pass

@dataclass(frozen=True)
class RuntimeBindings:
    appointments: object = None
    payments: object = None
    authenticate: object = None
    auth_app: object = None
    release_verifier: object = None
    webhook_app: object = None
    transaction_processor: object = None
    transaction_store: object = None
    stream_verifier: object = None
    provider_workflows: object = None
    native_bridge: object = None
    audit: object = None
    rooms: object = None
    uncle_nickey_mao: object = None
    carehive_os: object = None
    home_healthcare: object = None
    grantwriter: object = None
    pbd_validation: object = None
    pbd_manifest_generator: object = None
    vault: object = None
    pbd_sentinel: object = None
    it_ai_manager: object = None
    twin_gate: object = None
    sharpshooter: object = None
    labyrinth_shield: object = None
    minotaur: object = None
    glass_box_audit: object = None
    architect: object = None
    archimedes: object = None
    promethean: object = None
    hydra_q: object = None
    labyrinth: object = None
    sovereign_shield_v3: object = None
    cerberus: object = None
    chorus: object = None
    cobol_synthetic_ai: object = None
    juggernaut: object = None
    bozly: object = None
    fraud_rtsa: object = None
    operations_rtsa: object = None
    surn: object = None
    portals: object = None
    ai_role_workers: object = None
    uptime_agent: object = None
    application_agent: object = None
    database_agent: object = None
    deployment_agent: object = None
    infrastructure_agent: object = None
    integration_agent: object = None
    performance_agent: object = None
    backup_recovery_agent: object = None
    observability_agent: object = None
    quality_agent: object = None
    configuration_agent: object = None
    it_support_agent: object = None
    sanders_sentinel: object = None
    lil_mama: object = None
    baby_girl: object = None
    sanders_omniconn: object = None
    gia_mind: object = None
    ai_doctor: object = None
    sanders_ai_psychiatrist: object = None
    sanders_recon: object = None
    sanders_senior_living: object = None
    sanders_legal_helpers: object = None
    sanders_education: object = None
    sanders_finance: object = None
    sanders_retail: object = None
    sanders_logistics: object = None
    sanders_security: object = None
    sanders_real_estate: object = None
    sanders_energy: object = None
    sanders_transportation: object = None
    sanders_agriculture: object = None
    sanders_manufacturing: object = None
    sanders_consulting: object = None
    sanders_hospitality: object = None
    sanders_entertainment: object = None
    sanders_sports: object = None
    sanders_wellness: object = None
    sanders_steward_sentinel: object = None
    bloodline_records: object = None
    sanders_patriot_saint: object = None
    sanders_freedom_revolution: object = None
    sanders_strategy_hub: object = None
    sanders_global_freedom: object = None
    sanders_coordinator: object = None
    sanders_intelligence: object = None
    sanders_ai_research: object = None
    sanders_research: object = None
    sanders_communications: object = None
    sanders_banking_hub: object = None
    sanders_legal_services: object = None
    sanders_strategy_intel: object = None
    sanders_analytics: object = None
    sanders_innovation_lab: object = None
    sanders_supply_chain: object = None
    sanders_logical_framework: object = None
    sanders_infrastructure: object = None
    sanders_technology: object = None
    sanders_cloud_services: object = None
    showtime: object = None
    sanders_marketing: object = None
    sanders_sales: object = None
    sanders_customer_support: object = None
    sanders_human_resources: object = None
    sanders_security_ops: object = None
    sanders_global_relations: object = None
    sanders_healthcare: object = None
    the_godfather: object = None
    sanders_ethics_impact_collective: object = None
    secretary: object = None
    money_factory_legal_aid: object = None

def _response(start, status, payload, extra=None):
    body = json.dumps(payload, separators=(',', ':')).encode()
    start(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-store'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Referrer-Policy', 'no-referrer'),
        *(extra or ())
    ])
    return [body]

def _unavailable(env, start):
    return _response(start, '503 Service Unavailable', {'error': 'service_unavailable'})

def _denied():
    return False

# ---------------------------------------------------------------------------
# P2 (2026-11-13): AI-platform / voice / realtime / global wiring.
# Every optional module is imported lazily inside a helper and guarded:
# a missing or broken optional module degrades its own routes to an
# honest 503 and can never break the core app (/, /healthz, webhook).
# No live provider call is made by any route below without (a) the
# provider key present in the environment and (b) the matching owner
# approval gate APPROVED (all 9 gates are UNAPPROVED until the owner
# approves a specific gate by name).
# Phase A remediation (2026-11-24): the voice/realtime apps are built
# per application instance inside create_application, wired with that
# application's session verifier, audit chain and gate check — see
# voice_apps()/realtime_app() there.
# ---------------------------------------------------------------------------


def _utcnow_iso():
    """UTC timestamp for responses (global_time; stdlib fallback)."""
    try:
        from core_platform.global_time import now_utc, serialize_utc
        return serialize_utc(now_utc())
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _negotiated_locale(env):
    """Best locale from Accept-Language (i18n; 'en' fallback)."""
    try:
        from core_platform.i18n import negotiate_locale
        return negotiate_locale(env.get("HTTP_ACCEPT_LANGUAGE"))
    except Exception:
        return "en"


def _is_approved(gate_id):
    """True only when the gate is APPROVED; any failure fails closed."""
    try:
        from core_platform.ai_platform_approval import is_approved
        return bool(is_approved(gate_id))
    except Exception:
        return False


def _approval_503(start, gate_id):
    try:
        from core_platform.ai_platform_approval import http_failure
        payload = http_failure(gate_id)
    except Exception:
        payload = {"status": 503, "error": "approval_required", "gate": gate_id}
    payload = {k: v for k, v in payload.items() if k != "status"}
    return _response(start, "503 Service Unavailable", payload)


class _OpenAIRealtimeTTSSynthesizer:
    """Minimal adapter for OpenAI Realtime TTS (mirrors the private
    adapter in core_platform.voice_api; that module remains the
    canonical provider-wiring module)."""

    name = "openai-realtime-tts"
    audio_format = "pcm"
    media_type = "audio/pcm"

    def __init__(self):
        from core_platform.openai_link import OpenAIRealtimeTTSSpeaker
        self._speaker = OpenAIRealtimeTTSSpeaker()

    def synthesize(self, text):
        return self._speaker.speak(text).audio


def _voice_backends():
    """Free-first voice backends (transcriber faster-whisper -> Deepgram
    -> OpenAI gpt-transcribe; synthesizer system TTS -> Google ->
    ElevenLabs -> OpenAI Realtime). Provider adapters are constructed
    ONLY when the voice_video_provider approval gate is APPROVED;
    otherwise only local/offline backends are attempted. A backend
    whose key or package is missing is skipped; nothing here makes a
    live call. FasterWhisperTranscriber constructs its model eagerly
    (one ~75 MB download on first use when faster-whisper is installed
    but the model is not cached), so backends are built lazily on the
    first /api/voice request, never at startup."""
    from core_platform.daedalus_voice import (
        DeepgramTranscriber,
        ElevenLabsSynthesizer,
        FasterWhisperTranscriber,
        GoogleTTSSynthesizer,
        OpenAITranscriber,
        SystemTTSSynthesizer,
    )
    approved = _is_approved("voice_video_provider")
    transcriber = None
    builds = [lambda: FasterWhisperTranscriber("tiny")]
    if approved:
        builds += [DeepgramTranscriber, OpenAITranscriber]
    for build in builds:
        try:
            transcriber = build()
            break
        except Exception:
            continue
    synthesizer = None
    builds = [SystemTTSSynthesizer]
    if approved:
        builds += [GoogleTTSSynthesizer, ElevenLabsSynthesizer,
                   _OpenAIRealtimeTTSSynthesizer]
    for build in builds:
        try:
            synthesizer = build()
            break
        except Exception:
            continue
    return transcriber, synthesizer


def _serve_web_file(start, filename, media_type):
    """Serve one file from web/; returns None when it does not exist."""
    try:
        body = (WEB_ROOT / filename).read_bytes()
    except OSError:
        return None
    start("200 OK", [
        ("Content-Type", media_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    ])
    return [body]


# Per-platform healthz routes of the WSGI dispatcher (see the
# healthz branch in create_application): path -> (bindings field,
# platform id, unavailable error). Hoisted to module level so the
# status board (core_platform.ai_platform_links) checks every
# platform against the same map the dispatcher itself serves.
PLATFORM_HEALTHZ_PATHS = (
    '/api/uncle-nickey-mao/healthz',
    '/api/carehive-os/healthz',
    '/api/home-healthcare/healthz',
    '/api/grantwriter/healthz',
    '/api/pbd-validation/healthz',
    '/api/pbd-manifest-generator/healthz',
    '/api/vault/healthz',
    '/api/pbd-sentinel/healthz',
    '/api/it-ai-manager/healthz',
    '/api/twin-gate/healthz',
    '/api/sharpshooter/healthz',
    '/api/labyrinth-shield/healthz',
    '/api/minotaur/healthz',
    '/api/glass-box-audit/healthz',
    '/api/architect/healthz',
    '/api/archimedes-43/healthz',
    '/api/promethean/healthz',
    '/api/hydra-q/healthz',
    '/api/labyrinth/healthz',
    '/api/cerberus/healthz',
    '/api/chorus/healthz',
    '/api/cobol-synthetic-ai/healthz',
    '/api/juggernaut/healthz',
    '/api/bozly/healthz',
    '/api/fraud-rtsa/healthz',
    '/api/operations-rtsa/healthz',
    '/api/surn/healthz',
    '/api/ai-role-workers/healthz',
    '/api/uptime-agent/healthz',
    '/api/application-agent/healthz',
    '/api/database-agent/healthz',
    '/api/deployment-agent/healthz',
    '/api/infrastructure-agent/healthz',
    '/api/integration-agent/healthz',
    '/api/performance-agent/healthz',
    '/api/backup-recovery-agent/healthz',
    '/api/observability-agent/healthz',
    '/api/quality-agent/healthz',
    '/api/configuration-agent/healthz',
    '/api/it-support-agent/healthz',
    '/api/sanders-sentinel/healthz',
    '/api/lil-mama/healthz',
    '/api/baby-girl/healthz',
    '/api/sanders-omniconn/healthz',
    '/api/gia-mind/healthz',
    '/api/ai-doctor/healthz',
    '/api/ai-psychiatrist/healthz',
    '/api/sanders-recon/healthz',
    '/api/sanders-senior-living/healthz',
    '/api/sanders-legal-helpers/healthz',
    '/api/sanders-education/healthz',
    '/api/sanders-finance/healthz',
    '/api/sanders-retail/healthz',
    '/api/sanders-logistics/healthz',
    '/api/sanders-security/healthz',
    '/api/sanders-real-estate/healthz',
    '/api/sanders-energy/healthz',
    '/api/sanders-transportation/healthz',
    '/api/sanders-agriculture/healthz',
    '/api/sanders-manufacturing/healthz',
    '/api/sanders-consulting/healthz',
    '/api/sanders-hospitality/healthz',
    '/api/sanders-entertainment/healthz',
    '/api/sanders-sports/healthz',
    '/api/sanders-wellness/healthz',
    '/api/sanders-steward-sentinel/healthz',
    '/api/sanders-patriot-saint/healthz',
    '/api/sanders-freedom-revolution/healthz',
    '/api/sanders-strategy-hub/healthz',
    '/api/sanders-global-freedom/healthz',
    '/api/sanders-coordinator/healthz',
    '/api/sanders-intelligence/healthz',
    '/api/sanders-ai-research/healthz',
    '/api/sanders-research/healthz',
    '/api/sanders-communications/healthz',
    '/api/sanders-banking-hub/healthz',
    '/api/sanders-legal-services/healthz',
    '/api/sanders-strategy-intel/healthz',
    '/api/sanders-analytics/healthz',
    '/api/sanders-innovation-lab/healthz',
    '/api/sanders-supply-chain/healthz',
    '/api/sanders-logical-framework/healthz',
    '/api/sanders-infrastructure/healthz',
    '/api/sanders-technology/healthz',
    '/api/sanders-cloud-services/healthz',
    '/api/showtime/healthz',
    '/api/sanders-marketing/healthz',
    '/api/sanders-sales/healthz',
    '/api/sanders-customer-support/healthz',
    '/api/sanders-human-resources/healthz',
    '/api/sanders-security-ops/healthz',
    '/api/sanders-global-relations/healthz',
    '/api/sanders-healthcare/healthz',
    '/api/the-godfather/healthz',
    '/api/sanders-ethics-impact-collective/healthz',
    '/api/secretary/healthz',
    '/api/money-factory-legal-aid/healthz',
)

PLATFORM_HEALTH = {
    '/api/uncle-nickey-mao/healthz': ('uncle_nickey_mao', 'uncle_nickey_mao', 'uncle_nickey_mao_unavailable'),
    '/api/carehive-os/healthz': ('carehive_os', 'carehive_os', 'carehive_os_unavailable'),
    '/api/home-healthcare/healthz': ('home_healthcare', 'sanders_home_healthcare', 'home_healthcare_unavailable'),
    '/api/grantwriter/healthz': ('grantwriter', 'grantwriter', 'grantwriter_unavailable'),
    '/api/pbd-validation/healthz': ('pbd_validation', 'pbd_validation', 'pbd_validation_unavailable'),
    '/api/pbd-manifest-generator/healthz': ('pbd_manifest_generator', 'pbd_manifest_generator', 'pbd_manifest_generator_unavailable'),
    '/api/vault/healthz': ('vault', 'vault', 'vault_unavailable'),
    '/api/pbd-sentinel/healthz': ('pbd_sentinel', 'pbd_sentinel', 'pbd_sentinel_unavailable'),
    '/api/it-ai-manager/healthz': ('it_ai_manager', 'it_ai_manager', 'it_ai_manager_unavailable'),
    '/api/twin-gate/healthz': ('twin_gate', 'twin_gate', 'twin_gate_unavailable'),
    '/api/sharpshooter/healthz': ('sharpshooter', 'sharpshooter', 'sharpshooter_unavailable'),
    '/api/labyrinth-shield/healthz': ('labyrinth_shield', 'sanders_labyrinth_shield', 'labyrinth_shield_unavailable'),
    '/api/minotaur/healthz': ('minotaur', 'minotaur_sentinel', 'minotaur_unavailable'),
    '/api/glass-box-audit/healthz': ('glass_box_audit', 'glass_box_audit', 'glass_box_audit_unavailable'),
    '/api/architect/healthz': ('architect', 'architect', 'architect_unavailable'),
    '/api/archimedes-43/healthz': ('archimedes', 'archimedes_43', 'archimedes_unavailable'),
    '/api/promethean/healthz': ('promethean', 'promethean', 'promethean_unavailable'),
    '/api/hydra-q/healthz': ('hydra_q', 'hydra_q', 'hydra_q_unavailable'),
    '/api/labyrinth/healthz': ('labyrinth', 'labyrinth', 'labyrinth_unavailable'),
    '/api/cerberus/healthz': ('cerberus', 'cerberus', 'cerberus_unavailable'),
    '/api/chorus/healthz': ('chorus', 'chorus', 'chorus_unavailable'),
    '/api/cobol-synthetic-ai/healthz': ('cobol_synthetic_ai', 'cobol_synthetic_ai', 'cobol_synthetic_ai_unavailable'),
    '/api/juggernaut/healthz': ('juggernaut', 'juggernaut', 'juggernaut_unavailable'),
    '/api/bozly/healthz': ('bozly', 'bozly', 'bozly_unavailable'),
    '/api/fraud-rtsa/healthz': ('fraud_rtsa', 'fraud_rtsa', 'fraud_rtsa_unavailable'),
    '/api/operations-rtsa/healthz': ('operations_rtsa', 'operations_rtsa', 'operations_rtsa_unavailable'),
    '/api/surn/healthz': ('surn', 'surn', 'surn_unavailable'),
    '/api/ai-role-workers/healthz': ('ai_role_workers', 'ai_role_workers', 'ai_role_workers_unavailable'),
    '/api/uptime-agent/healthz': ('uptime_agent', 'uptime_agent', 'uptime_agent_unavailable'),
    '/api/application-agent/healthz': ('application_agent', 'application_agent', 'application_agent_unavailable'),
    '/api/database-agent/healthz': ('database_agent', 'database_agent', 'database_agent_unavailable'),
    '/api/deployment-agent/healthz': ('deployment_agent', 'deployment_agent', 'deployment_agent_unavailable'),
    '/api/infrastructure-agent/healthz': ('infrastructure_agent', 'infrastructure_agent', 'infrastructure_agent_unavailable'),
    '/api/integration-agent/healthz': ('integration_agent', 'integration_agent', 'integration_agent_unavailable'),
    '/api/performance-agent/healthz': ('performance_agent', 'performance_agent', 'performance_agent_unavailable'),
    '/api/backup-recovery-agent/healthz': ('backup_recovery_agent', 'backup_recovery_agent', 'backup_recovery_agent_unavailable'),
    '/api/observability-agent/healthz': ('observability_agent', 'observability_agent', 'observability_agent_unavailable'),
    '/api/quality-agent/healthz': ('quality_agent', 'quality_agent', 'quality_agent_unavailable'),
    '/api/configuration-agent/healthz': ('configuration_agent', 'configuration_agent', 'configuration_agent_unavailable'),
    '/api/it-support-agent/healthz': ('it_support_agent', 'it_support_agent', 'it_support_agent_unavailable'),
    '/api/sanders-sentinel/healthz': ('sanders_sentinel', 'sanders_sentinel', 'sanders_sentinel_unavailable'),
    '/api/lil-mama/healthz': ('lil_mama', 'lil_mama', 'lil_mama_unavailable'),
    '/api/baby-girl/healthz': ('baby_girl', 'baby_girl', 'baby_girl_unavailable'),
    '/api/sanders-omniconn/healthz': ('sanders_omniconn', 'sanders_omniconn', 'sanders_omniconn_unavailable'),
    '/api/gia-mind/healthz': ('gia_mind', 'gia_mind', 'gia_mind_unavailable'),
    '/api/ai-doctor/healthz': ('ai_doctor', 'ai_doctor', 'ai_doctor_unavailable'),
    '/api/ai-psychiatrist/healthz': ('sanders_ai_psychiatrist', 'sanders_ai_psychiatrist', 'sanders_ai_psychiatrist_unavailable'),
    '/api/sanders-recon/healthz': ('sanders_recon', 'sanders_recon', 'sanders_recon_unavailable'),
    '/api/sanders-senior-living/healthz': ('sanders_senior_living', 'sanders_senior_living', 'sanders_senior_living_unavailable'),
    '/api/sanders-legal-helpers/healthz': ('sanders_legal_helpers', 'sanders_legal_helpers', 'sanders_legal_helpers_unavailable'),
    '/api/sanders-education/healthz': ('sanders_education', 'sanders_education', 'sanders_education_unavailable'),
    '/api/sanders-finance/healthz': ('sanders_finance', 'sanders_finance', 'sanders_finance_unavailable'),
    '/api/sanders-retail/healthz': ('sanders_retail', 'sanders_retail', 'sanders_retail_unavailable'),
    '/api/sanders-logistics/healthz': ('sanders_logistics', 'sanders_logistics', 'sanders_logistics_unavailable'),
    '/api/sanders-security/healthz': ('sanders_security', 'sanders_security', 'sanders_security_unavailable'),
    '/api/sanders-real-estate/healthz': ('sanders_real_estate', 'sanders_real_estate', 'sanders_real_estate_unavailable'),
    '/api/sanders-energy/healthz': ('sanders_energy', 'sanders_energy', 'sanders_energy_unavailable'),
    '/api/sanders-transportation/healthz': ('sanders_transportation', 'sanders_transportation', 'sanders_transportation_unavailable'),
    '/api/sanders-agriculture/healthz': ('sanders_agriculture', 'sanders_agriculture', 'sanders_agriculture_unavailable'),
    '/api/sanders-manufacturing/healthz': ('sanders_manufacturing', 'sanders_manufacturing', 'sanders_manufacturing_unavailable'),
    '/api/sanders-consulting/healthz': ('sanders_consulting', 'sanders_consulting', 'sanders_consulting_unavailable'),
    '/api/sanders-hospitality/healthz': ('sanders_hospitality', 'sanders_hospitality', 'sanders_hospitality_unavailable'),
    '/api/sanders-entertainment/healthz': ('sanders_entertainment', 'sanders_entertainment', 'sanders_entertainment_unavailable'),
    '/api/sanders-sports/healthz': ('sanders_sports', 'sanders_sports', 'sanders_sports_unavailable'),
    '/api/sanders-wellness/healthz': ('sanders_wellness', 'sanders_wellness', 'sanders_wellness_unavailable'),
    '/api/sanders-steward-sentinel/healthz': ('sanders_steward_sentinel', 'sanders_steward_sentinel', 'sanders_steward_sentinel_unavailable'),
    '/api/sanders-patriot-saint/healthz': ('sanders_patriot_saint', 'sanders_patriot_saint', 'sanders_patriot_saint_unavailable'),
    '/api/sanders-freedom-revolution/healthz': ('sanders_freedom_revolution', 'sanders_freedom_revolution', 'sanders_freedom_revolution_unavailable'),
    '/api/sanders-strategy-hub/healthz': ('sanders_strategy_hub', 'sanders_strategy_hub', 'sanders_strategy_hub_unavailable'),
    '/api/sanders-global-freedom/healthz': ('sanders_global_freedom', 'sanders_global_freedom', 'sanders_global_freedom_unavailable'),
    '/api/sanders-coordinator/healthz': ('sanders_coordinator', 'sanders_coordinator', 'sanders_coordinator_unavailable'),
    '/api/sanders-intelligence/healthz': ('sanders_intelligence', 'sanders_intelligence', 'sanders_intelligence_unavailable'),
    '/api/sanders-ai-research/healthz': ('sanders_ai_research', 'sanders_ai_research', 'sanders_ai_research_unavailable'),
    '/api/sanders-research/healthz': ('sanders_research', 'sanders_research', 'sanders_research_unavailable'),
    '/api/sanders-communications/healthz': ('sanders_communications', 'sanders_communications', 'sanders_communications_unavailable'),
    '/api/sanders-banking-hub/healthz': ('sanders_banking_hub', 'sanders_banking_hub', 'sanders_banking_hub_unavailable'),
    '/api/sanders-legal-services/healthz': ('sanders_legal_services', 'sanders_legal_services', 'sanders_legal_services_unavailable'),
    '/api/sanders-strategy-intel/healthz': ('sanders_strategy_intel', 'sanders_strategy_intel', 'sanders_strategy_intel_unavailable'),
    '/api/sanders-analytics/healthz': ('sanders_analytics', 'sanders_analytics', 'sanders_analytics_unavailable'),
    '/api/sanders-innovation-lab/healthz': ('sanders_innovation_lab', 'sanders_innovation_lab', 'sanders_innovation_lab_unavailable'),
    '/api/sanders-supply-chain/healthz': ('sanders_supply_chain', 'sanders_supply_chain', 'sanders_supply_chain_unavailable'),
    '/api/sanders-logical-framework/healthz': ('sanders_logical_framework', 'sanders_logical_framework', 'sanders_logical_framework_unavailable'),
    '/api/sanders-infrastructure/healthz': ('sanders_infrastructure', 'sanders_infrastructure', 'sanders_infrastructure_unavailable'),
    '/api/sanders-technology/healthz': ('sanders_technology', 'sanders_technology', 'sanders_technology_unavailable'),
    '/api/sanders-cloud-services/healthz': ('sanders_cloud_services', 'sanders_cloud_services', 'sanders_cloud_services_unavailable'),
    '/api/showtime/healthz': ('showtime', 'showtime', 'showtime_unavailable'),
    '/api/sanders-marketing/healthz': ('sanders_marketing', 'sanders_marketing', 'sanders_marketing_unavailable'),
    '/api/sanders-sales/healthz': ('sanders_sales', 'sanders_sales', 'sanders_sales_unavailable'),
    '/api/sanders-customer-support/healthz': ('sanders_customer_support', 'sanders_customer_support', 'sanders_customer_support_unavailable'),
    '/api/sanders-human-resources/healthz': ('sanders_human_resources', 'sanders_human_resources', 'sanders_human_resources_unavailable'),
    '/api/sanders-security-ops/healthz': ('sanders_security_ops', 'sanders_security_ops', 'sanders_security_ops_unavailable'),
    '/api/sanders-global-relations/healthz': ('sanders_global_relations', 'sanders_global_relations', 'sanders_global_relations_unavailable'),
    '/api/sanders-healthcare/healthz': ('sanders_healthcare', 'sanders_healthcare', 'sanders_healthcare_unavailable'),
    '/api/the-godfather/healthz': ('the_godfather', 'the_godfather', 'the_godfather_unavailable'),
    '/api/sanders-ethics-impact-collective/healthz': ('sanders_ethics_impact_collective', 'sanders_ethics_impact_collective', 'sanders_ethics_impact_collective_unavailable'),
    '/api/secretary/healthz': ('secretary', 'secretary', 'secretary_unavailable'),
    '/api/money-factory-legal-aid/healthz': ('money_factory_legal_aid', 'money_factory_legal_aid', 'money_factory_legal_aid_unavailable'),
}


def _combined_platform_status(env, bindings=None):
    """Combined per-platform status: link registry + approval gates +
    service links + platform services + global (region/locale/currency)
    + voice backends + free-first ordering. Read-only; no live call,
    no secret value is ever returned. Each section is guarded so one
    broken module degrades its own section instead of the endpoint."""
    locale = _negotiated_locale(env)
    payload = {
        "platform": "Sanders Dash & Seal",
        "generated_at_utc": _utcnow_iso(),
        "locale": locale,
    }
    try:
        from core_platform.i18n import text_direction, translate
        payload["text_direction"] = text_direction(locale)
        payload["title"] = translate("app.title", locale)
    except Exception as exc:
        payload["title_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.ai_platform_links import (
            check_all,
            check_providers,
            summarize,
        )
        results = check_all(bindings=bindings)
        payload["platform_links"] = {
            pid: status.to_dict() for pid, status in results.items()}
        payload["platform_link_summary"] = summarize(results)
        payload["providers"] = check_providers()
    except Exception as exc:
        payload["platform_links_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.ai_platform_approval import approval_checklist
        payload["approvals"] = approval_checklist()
    except Exception as exc:
        payload["approvals_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.service_linking import linking_table
        rows = linking_table()
        payload["service_links"] = {
            "rows": len(rows),
            "by_live_status": {
                s: sum(1 for r in rows if r.get("live_status") == s)
                for s in sorted({r.get("live_status") for r in rows})},
        }
    except Exception as exc:
        payload["service_links_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.platform_services import platform_status
        payload["services"] = platform_status()
    except Exception as exc:
        payload["services_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.global_regions import GlobalRegionsConfig
        payload["regions"] = GlobalRegionsConfig.from_env().summary()
    except Exception as exc:
        payload["regions_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # P3 (2026-11-13): global_connectivity now has a real caller.
        # Policy table only (no live calls, no network): per-platform
        # timeout/retry/offline-fallback for the primary region ("us",
        # us-phoenix-1). eu/apac policies are declared only -- no
        # deployment exists there.
        from core_platform.global_connectivity import all_policies
        payload["connectivity"] = {
            "region": "us",
            "policies": {
                p.platform: {
                    "timeout_seconds": p.timeout_seconds,
                    "max_retries": p.max_retries,
                    "offline_fallback": p.offline_fallback,
                }
                for p in all_policies()
                if p.region == "us"
            },
            "note": ("Policy table only, not measured latency. "
                     "eu/apac policies are declared only; no deployment there."),
        }
    except Exception as exc:
        payload["connectivity_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # P3 (2026-11-13): global_compliance now has a real caller.
        # RON gate state, read-only: the owner-approved set is EMPTY by
        # default and gating is fail-closed, so no jurisdiction is
        # approved until the owner approves one by name.
        from core_platform.global_compliance import APPROVED_RON_JURISDICTIONS
        payload["ron"] = {
            "gate": "fail_closed",
            "approved_jurisdictions": sorted(APPROVED_RON_JURISDICTIONS),
            "check": "GET /api/compliance/ron?jurisdiction=XX",
        }
    except Exception as exc:
        payload["ron_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.global_payments import live_gate, resolve_currency
        livemode = (os.environ.get("STRIPE_LIVEMODE") or "").strip().lower() in (
            "1", "true", "yes")
        live_verified = (os.environ.get("STRIPE_LIVE_VERIFIED") or "").strip().lower() in (
            "1", "true", "yes")
        payments = {"live_gate": live_gate(
            livemode=livemode, live_verified=live_verified)}
        try:
            currency, source = resolve_currency(
                accept_language=env.get("HTTP_ACCEPT_LANGUAGE"))
            payments["currency"] = currency
            payments["currency_source"] = source
        except Exception as exc:
            payments["currency"] = None
            payments["currency_source"] = None
            payments["currency_note"] = (
                f"unresolvable from request: {type(exc).__name__}; "
                "pass an explicit currency")
        payload["payments"] = payments
    except Exception as exc:
        payload["payments_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.voice_api import describe_voice_backends
        payload["voice_backends"] = describe_voice_backends()
    except Exception as exc:
        payload["voice_backends_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from core_platform.free_first import free_first_status
        payload["free_first"] = free_first_status()
    except Exception as exc:
        payload["free_first_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # PQC (2026-11-13): post-quantum cryptography status, read-only.
        # Reports honestly whether this runtime can perform ML-KEM-768 /
        # ML-DSA-65. No keys are ever returned. If the runtime cannot do
        # PQC, "available" is False and nothing claims otherwise.
        from core_platform.pqc import status as pqc_status
        payload["pqc"] = pqc_status()
    except Exception as exc:
        payload["pqc_error"] = f"{type(exc).__name__}: {exc}"
    try:
        # Bozly CFO (2026-11-13): wired into the live webhook path.
        # Read-only and honest: reports whether Bozly is configured
        # (BOZLY_STRIPE_ROUTES_JSON set with a usable route), whether
        # its ledger file exists, and whether it is live. No secret
        # values, no file paths, no traceback internals are returned.
        # When unconfigured Bozly reports not_configured and the rest
        # of the app keeps working.
        from core_platform.bozly_wiring import bozly_status
        payload["bozly"] = bozly_status()
    except Exception as exc:
        payload["bozly_error"] = f"{type(exc).__name__}: {exc}"
    return payload

def create_application(bindings=None):
    """Expose existing components; no bindings means diagnostic-only startup."""
    if bindings is not None:
        if not isinstance(bindings, RuntimeBindings) or bindings.appointments is None or bindings.payments is None or getattr(bindings.payments, 'origin', None) is not ORIGIN or not all(callable(v) for v in (bindings.authenticate, bindings.auth_app, bindings.release_verifier)) or (bindings.webhook_app is not None and not callable(bindings.webhook_app)):
            raise DeploymentConfigurationError('Independent runtime bindings required')
        verifier = bindings.release_verifier
        if bindings.transaction_processor is not None and not callable(bindings.transaction_processor):
            raise DeploymentConfigurationError('Trusted transaction processor required')
        customer = create_customer_app(
            bindings.appointments, bindings.authenticate,
            bindings.payments, bindings.auth_app, ORIGIN, release_verifier=verifier,
            allowed_origins=SITE_ORIGINS,
            provider_workflows=bindings.provider_workflows,
            provider_gate=lambda: _is_approved('ron_notarial'),
            native_bridge=bindings.native_bridge,
            native_gate=lambda: _is_approved('ron_notarial'),
            rooms=bindings.rooms,
            uncle_nickey_mao=getattr(bindings, 'uncle_nickey_mao', None),
            carehive_os=getattr(bindings, 'carehive_os', None),
            home_healthcare=getattr(bindings, 'home_healthcare', None),
            grantwriter=getattr(bindings, 'grantwriter', None),
            pbd_validation=getattr(bindings, 'pbd_validation', None),
            pbd_manifest_generator=getattr(bindings, 'pbd_manifest_generator', None),
            vault=getattr(bindings, 'vault', None),
            pbd_sentinel=getattr(bindings, 'pbd_sentinel', None),
            it_ai_manager=getattr(bindings, 'it_ai_manager', None),
            twin_gate=getattr(bindings, 'twin_gate', None),
            sharpshooter=getattr(bindings, 'sharpshooter', None),
            labyrinth_shield=getattr(bindings, 'labyrinth_shield', None),
            minotaur=getattr(bindings, 'minotaur', None),
            glass_box_audit=getattr(bindings, 'glass_box_audit', None),
            architect=getattr(bindings, 'architect', None),
            archimedes=getattr(bindings, 'archimedes', None),
            promethean=getattr(bindings, 'promethean', None),
            hydra_q=getattr(bindings, 'hydra_q', None),
            labyrinth=getattr(bindings, 'labyrinth', None),
            cerberus=getattr(bindings, 'cerberus', None),
            chorus=getattr(bindings, 'chorus', None),
            cobol_synthetic_ai=getattr(bindings, 'cobol_synthetic_ai', None),
            juggernaut=getattr(bindings, 'juggernaut', None),
            bozly=getattr(bindings, 'bozly', None),
            fraud_rtsa=getattr(bindings, 'fraud_rtsa', None),
            operations_rtsa=getattr(bindings, 'operations_rtsa', None),
            surn=getattr(bindings, 'surn', None),
            uptime_agent=getattr(bindings, 'uptime_agent', None),
            application_agent=getattr(bindings, 'application_agent', None),
            database_agent=getattr(bindings, 'database_agent', None),
            deployment_agent=getattr(bindings, 'deployment_agent', None),
            infrastructure_agent=getattr(bindings, 'infrastructure_agent', None),
            integration_agent=getattr(bindings, 'integration_agent', None),
            performance_agent=getattr(bindings, 'performance_agent', None),
            backup_recovery_agent=getattr(bindings, 'backup_recovery_agent', None),
            observability_agent=getattr(bindings, 'observability_agent', None),
            quality_agent=getattr(bindings, 'quality_agent', None),
            configuration_agent=getattr(bindings, 'configuration_agent', None),
            it_support_agent=getattr(bindings, 'it_support_agent', None),
            sanders_sentinel=getattr(bindings, 'sanders_sentinel', None),
            lil_mama=getattr(bindings, 'lil_mama', None),
            baby_girl=getattr(bindings, 'baby_girl', None),
            sanders_omniconn=getattr(bindings, 'sanders_omniconn', None),
            gia_mind=getattr(bindings, 'gia_mind', None),
            ai_doctor=getattr(bindings, 'ai_doctor', None),
            sanders_ai_psychiatrist=getattr(bindings, 'sanders_ai_psychiatrist', None),
            sanders_recon=getattr(bindings, 'sanders_recon', None),
            sanders_senior_living=getattr(bindings, 'sanders_senior_living', None),
            sanders_legal_helpers=getattr(bindings, 'sanders_legal_helpers', None),
            sanders_education=getattr(bindings, 'sanders_education', None),
            sanders_finance=getattr(bindings, 'sanders_finance', None),
            sanders_retail=getattr(bindings, 'sanders_retail', None),
            sanders_logistics=getattr(bindings, 'sanders_logistics', None),
            sanders_security=getattr(bindings, 'sanders_security', None),
            sanders_real_estate=getattr(bindings, 'sanders_real_estate', None),
            sanders_energy=getattr(bindings, 'sanders_energy', None),
            sanders_transportation=getattr(bindings, 'sanders_transportation', None),
            sanders_agriculture=getattr(bindings, 'sanders_agriculture', None),
            sanders_manufacturing=getattr(bindings, 'sanders_manufacturing', None),
            sanders_consulting=getattr(bindings, 'sanders_consulting', None),
            sanders_hospitality=getattr(bindings, 'sanders_hospitality', None),
            sanders_entertainment=getattr(bindings, 'sanders_entertainment', None),
            sanders_sports=getattr(bindings, 'sanders_sports', None),
            sanders_wellness=getattr(bindings, 'sanders_wellness', None),
            sanders_steward_sentinel=getattr(bindings, 'sanders_steward_sentinel', None),
            sanders_patriot_saint=getattr(bindings, 'sanders_patriot_saint', None),
            sanders_freedom_revolution=getattr(bindings, 'sanders_freedom_revolution', None),
            sanders_strategy_hub=getattr(bindings, 'sanders_strategy_hub', None),
            sanders_global_freedom=getattr(bindings, 'sanders_global_freedom', None),
            sanders_coordinator=getattr(bindings, 'sanders_coordinator', None),
            sanders_intelligence=getattr(bindings, 'sanders_intelligence', None),
            sanders_ai_research=getattr(bindings, 'sanders_ai_research', None),
            sanders_research=getattr(bindings, 'sanders_research', None),
            sanders_communications=getattr(bindings, 'sanders_communications', None),
            sanders_banking_hub=getattr(bindings, 'sanders_banking_hub', None),
            sanders_legal_services=getattr(bindings, 'sanders_legal_services', None),
            sanders_strategy_intel=getattr(bindings, 'sanders_strategy_intel', None),
            sanders_analytics=getattr(bindings, 'sanders_analytics', None),
            sanders_innovation_lab=getattr(bindings, 'sanders_innovation_lab', None),
            sanders_supply_chain=getattr(bindings, 'sanders_supply_chain', None),
            sanders_logical_framework=getattr(bindings, 'sanders_logical_framework', None),
            sanders_infrastructure=getattr(bindings, 'sanders_infrastructure', None),
            sanders_technology=getattr(bindings, 'sanders_technology', None),
            sanders_cloud_services=getattr(bindings, 'sanders_cloud_services', None),
            showtime=getattr(bindings, 'showtime', None),
            sanders_marketing=getattr(bindings, 'sanders_marketing', None),
            sanders_sales=getattr(bindings, 'sanders_sales', None),
            sanders_customer_support=getattr(bindings, 'sanders_customer_support', None),
            sanders_human_resources=getattr(bindings, 'sanders_human_resources', None),
            sanders_security_ops=getattr(bindings, 'sanders_security_ops', None),
            sanders_global_relations=getattr(bindings, 'sanders_global_relations', None),
            sanders_healthcare=getattr(bindings, 'sanders_healthcare', None),
            the_godfather=getattr(bindings, 'the_godfather', None),
            sanders_ethics_impact_collective=getattr(bindings, 'sanders_ethics_impact_collective', None)
        )
    else:
        verifier = _denied
        customer = create_customer_app(
            None, lambda env: None,
            _unavailable, _unavailable, ORIGIN, release_verifier=verifier,
            allowed_origins=SITE_ORIGINS
        )

    pipeline = create_pipeline_app(
        authenticate=bindings.authenticate if bindings else None,
        processor=bindings.transaction_processor if bindings else None,
        release_verifier=verifier,
        store=bindings.transaction_store if bindings else None)

    stream = create_stream_app(
        processor=bindings.transaction_processor if bindings else None,
        release_verifier=verifier,
        store=bindings.transaction_store if bindings else None,
        stream_verifier=bindings.stream_verifier if bindings else None)

    # Media apps (voice + realtime), built lazily per application
    # instance — never at startup (the voice backends load models on
    # first use) and never shared across instances, because each is
    # wired with THIS application's session verifier and audit chain
    # (Phase A remediation, 2026-11-24 — findings F-1/F-2/F-5/F-11).
    # With no bindings (diagnostic startup) the authenticator is None
    # and the media apps fail closed: issuance and voice work refuse.
    media_apps = {}

    def voice_apps():
        """(plain voice app, Daedalus voice-turn app) for this instance.
        The turn app has runtime=None: no Daedalus signing key, durable
        evidence store, or daedalus_live approval is wired in this pass,
        so POST /api/voice/turn honestly answers 503
        daedalus_runtime_not_configured."""
        if "voice" not in media_apps:
            from core_platform.voice_api import (
                create_daedalus_voice_app,
                create_voice_app,
            )
            transcriber, synthesizer = _voice_backends()
            media_apps["voice"] = create_voice_app(
                transcriber, synthesizer,
                authenticate=bindings.authenticate if bindings else None,
                allowed_origins=SITE_ORIGINS)
            media_apps["daedalus"] = create_daedalus_voice_app(
                runtime=None, transcriber=transcriber, synthesizer=synthesizer)
        return media_apps["voice"], media_apps["daedalus"]

    def realtime_app():
        """Realtime/video app for this instance (env-wired LiveKit/Daily
        clients, no transport: room/token answer honest 503s until a
        provider is configured). The gate check, session verifier,
        audit chain and origin set are injected here; enforcement runs
        inside the realtime module itself."""
        if "realtime" not in media_apps:
            from core_platform.realtime_api import create_realtime_app
            media_apps["realtime"] = create_realtime_app(
                authenticate=bindings.authenticate if bindings else None,
                audit=bindings.audit if bindings else None,
                gate_approved=lambda: _is_approved("voice_video_provider"),
                allowed_origins=SITE_ORIGINS)
        return media_apps["realtime"]

    def portals_app():
        """Portals app for this instance (founder portals band,
        2026-11-25), built lazily like the media apps and wired with
        THIS application's session verifier. With no service bound
        (diagnostic startup) the app answers an honest 503 on every
        route; enforcement — consent, the review queue, operator
        authority — runs inside the portals module itself."""
        if "portals" not in media_apps:
            from core_platform.portals_api import create_portals_app
            media_apps["portals"] = create_portals_app(
                bindings.portals if bindings else None,
                authenticate=bindings.authenticate if bindings else None,
                allowed_origins=SITE_ORIGINS)
        return media_apps["portals"]

    def ready():
        try:
            return verifier() is True
        except Exception:
            return False

    # Hosts that reach this process without going through the public proxy:
    # the legacy internal name, the compose service name the worker calls
    # (worker/src/index.js uses http://wsgi-backend:8000), and loopback,
    # which the installer health checks and the worker test fixture use.
    # These hosts may only reach diagnostics and the authenticated API
    # routes, never the customer pages; the API routes still enforce their
    # own authentication / release-verifier gates.
    INTERNAL_HOSTS = ('magi-backend:8000', 'wsgi-backend:8000')
    LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')

    def _is_internal(hostname):
        if hostname in INTERNAL_HOSTS:
            return True
        return hostname.split(':')[0] in LOOPBACK_HOSTS

    def _api_route(env, start):
        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if path == '/':
            # Storefront home. Since the 2026-11-23 relaunch (owner
            # directive: "relaunch the real Dash and Seal" — the Imperial
            # Jade storefront is the public face on its own domain too),
            # the canonical host serves web/jade-landing.html at '/',
            # exactly as alias hosts do through the customer app. The
            # appointment portal (web/index.html) lives at /appointments
            # on every host. Before the relaunch the canonical host
            # served the portal at '/' (and, earlier still, 308-redirected
            # '/' to itself).
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            host = env.get('HTTP_HOST', '')
            if not isinstance(host, str):
                return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
            host = host.lower()
            if host.endswith(':443'):
                host = host[:-4]
            if host in ALIAS_HOSTS:
                return None
            try:
                body = (WEB_ROOT / 'jade-landing.html').read_bytes()
            except OSError:
                return _response(start, '503 Service Unavailable', {'error': 'home_unavailable'})
            start('200 OK', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(body))),
                ('Cache-Control', 'no-store'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Referrer-Policy', 'no-referrer'),
                ('Content-Language', _negotiated_locale(env)),
            ])
            return [body]
        if path in ('/voice.html', '/video.html',
                    '/daedalus_voice.js', '/video.js'):
            # Voice/video pages + their scripts, served from web/.
            # /voice.html needs camera/mic for getUserMedia; nginx only
            # relaxes Permissions-Policy for that one path (see nginx.conf).
            media_type = ('text/html; charset=utf-8' if path.endswith('.html')
                          else 'text/javascript; charset=utf-8')
            served = _serve_web_file(start, path.lstrip('/'), media_type)
            if served is not None:
                return served
            if path == '/voice.html':
                return _response(start, '503 Service Unavailable',
                                 {'error': 'voice_unavailable',
                                  'reason': 'web/voice.html is missing from this checkout'})
            return _response(start, '404 Not Found', {'error': 'not_found'})
        if path in ('/assets/booking.css', '/assets/booking.js',
                    '/assets/dash-seal-banner.png',
                    '/assets/seal-corporate-hq.png',
                    '/assets/seal-home-healthcare.png',
                    '/assets/seal-senior-living.png',
                    '/assets/seal-legal-helpers.png'):
            # Canonical home page assets. web/index.html links both, and
            # the canonical host 308-redirects every path _api_route does
            # not serve, so without this the portal home on
            # sandersdashandseal.com loads with no CSS and no booking
            # script. Served from web/ like the voice/video pages.
            # Alias hosts return None here so they keep serving these
            # files from the customer app, with its own headers.
            # The four seal images joined this list 2026-11-23 with the
            # portal presentation repair (web/index.html displays them).
            host = env.get('HTTP_HOST', '')
            if not isinstance(host, str):
                return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
            host = host.lower()
            if host.endswith(':443'):
                host = host[:-4]
            if host in ALIAS_HOSTS:
                return None
            media_type = ('text/css; charset=utf-8' if path.endswith('.css')
                          else 'image/png' if path.endswith('.png')
                          else 'application/javascript; charset=utf-8')
            served = _serve_web_file(start, path.rsplit('/', 1)[-1], media_type)
            if served is not None:
                return served
            return _response(start, '404 Not Found', {'error': 'not_found'})
        if path == '/api/voice' or path.startswith('/api/voice/'):
            # Real voice adapters (free-first, approval-gated for live
            # providers). No backends are configured when no key/package
            # is present, so transcribe/speak answer honest 503s; the
            # turn route answers 503 daedalus_runtime_not_configured
            # until a Daedalus runtime is wired (signing key + durable
            # evidence store + daedalus_live approval).
            try:
                voice_app, daedalus_app = voice_apps()
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'voice_unavailable',
                                  'reason': f'voice module failed to load: {type(exc).__name__}: {exc}'})
            if path in ('/api/voice/turn', '/api/voice/daedalus/status'):
                return daedalus_app(env, start)
            return voice_app(env, start)
        if path == '/api/portals' or path.startswith('/api/portals/'):
            # The Portals (founder portals band, 2026-11-25): public
            # submissions land as cases AWAITING_HUMAN_REVIEW and
            # publish nothing; public reads carry only what the
            # operator's recorded decision made public; contractor
            # and operator surfaces enforce the session and operator
            # authority inside the portals module itself.
            return portals_app()(env, start)
        if path == '/api/daedalus/describe':
            # Real Daedalus capability report (pure, no key, no live call).
            # fully_active is false until a live engine is built.
            try:
                from core_platform.daedalus_engine import describe as daedalus_describe
                payload = daedalus_describe()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'daedalus_unavailable',
                                  'reason': f'Daedalus engine failed to load: {type(exc).__name__}: {exc}'})
        if path == '/api/realtime/status' or path == '/api/video/status' or path.startswith('/api/realtime/'):
            # LiveKit/Daily realtime + video signalling (env-wired, no
            # transport). Room/token issuance is enforced inside the
            # realtime app itself (Phase A remediation, 2026-11-24 —
            # findings F-1/F-2/F-11): the voice_video_provider gate,
            # session authentication, session-bound identity and a
            # Glass-Box receipt are all evaluated by the module that
            # mints, so no router path can bypass them and every
            # denial is recorded on the audit chain. This router
            # previously evaluated the gate here via
            # RealtimeConfig.from_env().provider() — calling a
            # @property as a method; the TypeError was swallowed by
            # the surrounding except, the provider read as 'none',
            # and the gate check never ran (F-1).
            try:
                return realtime_app()(env, start)
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'realtime_unavailable',
                                  'reason': f'realtime module failed to load: {type(exc).__name__}: {exc}'})
        if path == '/api/compliance/ron':
            # P3 (2026-11-13): RON / notarial gating on a live route.
            # Fail-closed via global_compliance.gate_ron: the approved
            # set is EMPTY by default, so every jurisdiction is denied
            # with NOT_APPROVED_IN_JURISDICTION until the owner approves
            # one by name. The request cannot supply its own approved
            # list; only an owner code change to
            # APPROVED_RON_JURISDICTIONS can approve a jurisdiction.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from urllib.parse import parse_qs
                from core_platform.global_compliance import (
                    APPROVED_RON_JURISDICTIONS,
                    NotApprovedInJurisdiction,
                    gate_ron,
                )
                query = parse_qs(env.get('QUERY_STRING') or '')
                jurisdiction = (query.get('jurisdiction') or [None])[0]
                try:
                    result = gate_ron(jurisdiction)
                except NotApprovedInJurisdiction as exc:
                    return _response(start, '403 Forbidden', {
                        'error': 'NOT_APPROVED_IN_JURISDICTION',
                        'jurisdiction': jurisdiction,
                        'approved_jurisdictions': sorted(APPROVED_RON_JURISDICTIONS),
                        'detail': str(exc)})
                return _response(start, '200 OK', {
                    'ok': True, 'jurisdiction': result['jurisdiction'],
                    'generated_at_utc': _utcnow_iso()})
            except Exception as exc:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'ron_gate_unavailable',
                                  'reason': f'{type(exc).__name__}: {exc}'})
        if path == '/api/platform/status':
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            return _response(start, '200 OK', _combined_platform_status(env, bindings))
        if path == '/api/payments/currency':
            # Read-only currency resolution for payments (global_payments):
            # explicit ?currency= takes priority, then Accept-Language,
            # then nothing is silently assumed (USD is never a default).
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from urllib.parse import parse_qs
                from core_platform.global_payments import CurrencyError, resolve_currency
                query = parse_qs(env.get('QUERY_STRING') or '')
                explicit = (query.get('currency') or [None])[0]
                currency, source = resolve_currency(
                    explicit, accept_language=env.get('HTTP_ACCEPT_LANGUAGE'))
                return _response(start, '200 OK', {
                    'currency': currency, 'source': source,
                    'generated_at_utc': _utcnow_iso()})
            except Exception as exc:
                status = ('400 Bad Request' if exc.__class__.__name__ == 'CurrencyError'
                          else '503 Service Unavailable')
                error = ('currency_unresolvable' if exc.__class__.__name__ == 'CurrencyError'
                         else 'currency_service_unavailable')
                return _response(start, status, {'error': error, 'detail': str(exc)})
        if path == '/api/platform/free-resources':
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                payload = free_resource_catalog()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'resource_catalog_unavailable'})
        if path == '/api/pqc/status':
            # Post-quantum cryptography status (ML-KEM-768 / ML-DSA-65),
            # read-only and key-free. Reports honestly whether this
            # runtime can perform PQC; 200 with available:false when it
            # cannot — never a fake claim of quantum safety.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from core_platform.pqc import status as pqc_status
                payload = pqc_status()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'pqc_status_unavailable'})
        if path == '/api/bozly/status':
            # Bozly CFO status, read-only and key-free. Reports honestly
            # whether Bozly is wired and configured; 200 with
            # configured:false when BOZLY_STRIPE_ROUTES_JSON is not set —
            # never a fake claim of live CFO operation. No secret values,
            # no file paths, no traceback internals are returned.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'read_only'}, [('Allow', 'GET')])
            try:
                from core_platform.bozly_wiring import bozly_status
                payload = bozly_status()
                payload['generated_at_utc'] = _utcnow_iso()
                return _response(start, '200 OK', payload)
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'bozly_status_unavailable'})
        if path == '/internal/grantwriter-surn':
            # INTERNAL ONLY — Grantwriter + SURN architecture
            # dashboard (HL37 air-gapped confidentiality / HL40 zero
            # knowledge public footprint). Served only on internal /
            # loopback hosts; on every public host this branch
            # returns None so the path follows the ordinary
            # unknown-path flow and is indistinguishable from any
            # other nonexistent path. It is in no public navigation,
            # no customer-app asset map, and no public route family.
            host = env.get('HTTP_HOST', '')
            if not isinstance(host, str):
                return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
            host = host.lower()
            if host.endswith(':443'):
                host = host[:-4]
            if not _is_internal(host):
                return None
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            try:
                from core_platform.grantwriter_surn_architecture import (
                    dashboard_snapshot, render_dashboard)
                gw = getattr(bindings, 'grantwriter', None) \
                    if bindings is not None else None
                body = render_dashboard(
                    dashboard_snapshot(gw)).encode('utf-8')
            except Exception:
                return _response(start, '503 Service Unavailable',
                                 {'error': 'internal_dashboard_unavailable'})
            start('200 OK', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(body))),
                ('Cache-Control', 'no-store'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Referrer-Policy', 'no-referrer'),
            ])
            return [body]
        if path in PLATFORM_HEALTHZ_PATHS:
            # Per-platform liveness for the four reconstructed RTSA
            # platforms (Three Originals Reconstruction Program) and
            # the RTSA Build Program platforms as they land: no
            # auth, liveness only, like /healthz — answerable from
            # loopback so the watchdog can probe each in-process
            # surface of this service. 200 only when the platform's
            # bindings field is present; otherwise its honest 503.
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            field, platform_id, unavailable = PLATFORM_HEALTH[path]
            if bindings is None or getattr(bindings, field, None) is None:
                return _response(start, '503 Service Unavailable', {'error': unavailable})
            return _response(start, '200 OK', {'platform': platform_id, 'ok': True})
        if path in ('/healthz', '/readyz'):
            if method != 'GET':
                return _response(start, '405 Method Not Allowed', {'error': 'method_not_allowed'}, [('Allow', 'GET')])
            if path == '/healthz':
                return _response(start, '200 OK',
                                 {'platform': 'Sanders Dash & Seal', 'process_alive': True,
                                  'generated_at_utc': _utcnow_iso()})
            available = ready()
            return _response(start, '200 OK' if available else '503 Service Unavailable',
                             {'service_ready': available,
                              'generated_at_utc': _utcnow_iso()})
        if path == '/stripe/webhook':
            if bindings is None or bindings.webhook_app is None or not ready():
                return _unavailable(env, start)
            return bindings.webhook_app(env, start)
        if path in ('/api/auth/verify', '/api/transactions/process'):
            return pipeline(env, start)
        if path == '/api/stream/transactions':
            return stream(env, start)
        return None

    def _is_customer_api(path):
        # Paths served by app/customer_app.py (session + appointment APIs).
        # They were reachable only on alias hosts: on the canonical host
        # the 308 below swallowed them (GET /api/session 308-redirected
        # with no JSON body), so the worker's session check -- which always
        # sends Host: sandersdashandseal.com -- could never succeed, and
        # the worker python-integration test failed at WebSocket upgrade
        # with 503. Only these API paths are delegated; customer static
        # pages stay alias-only. customer() itself still enforces the
        # release verifier (503) and authentication (401).
        return (path == '/api/session'
                or path == '/api/appointments'
                or path.startswith('/api/appointments/')
                or path == '/api/operator/appointments'
                or path.startswith('/api/operator/appointments/')
                or path == '/api/rooms'
                or path.startswith('/api/rooms/')
                or path == '/api/uncle-nickey-mao'
                or path.startswith('/api/uncle-nickey-mao/')
                or path == '/api/carehive-os'
                or path.startswith('/api/carehive-os/')
                or path == '/api/home-healthcare'
                or path.startswith('/api/home-healthcare/')
                or path == '/api/grantwriter'
                or path.startswith('/api/grantwriter/')
                or path == '/api/pbd-validation'
                or path.startswith('/api/pbd-validation/')
                or path == '/api/pbd-manifest-generator'
                or path.startswith('/api/pbd-manifest-generator/')
                or path == '/api/vault'
                or path.startswith('/api/vault/')
                or path == '/api/pbd-sentinel'
                or path.startswith('/api/pbd-sentinel/')
                or path == '/api/it-ai-manager'
                or path.startswith('/api/it-ai-manager/')
                or path == '/api/twin-gate'
                or path.startswith('/api/twin-gate/')
                or path == '/api/sharpshooter'
                or path.startswith('/api/sharpshooter/')
                or path == '/api/labyrinth-shield'
                or path.startswith('/api/labyrinth-shield/')
                or path == '/api/minotaur'
                or path.startswith('/api/minotaur/')
                or path == '/api/glass-box-audit'
                or path.startswith('/api/glass-box-audit/')
                or path == '/api/architect'
                or path.startswith('/api/architect/')
                or path == '/api/archimedes-43'
                or path.startswith('/api/archimedes-43/')
                or path == '/api/promethean'
                or path.startswith('/api/promethean/')
                or path == '/api/hydra-q'
                or path.startswith('/api/hydra-q/')
                or path == '/api/labyrinth'
                or path.startswith('/api/labyrinth/')
                or path == '/api/cerberus'
                or path.startswith('/api/cerberus/')
                or path == '/api/chorus'
                or path.startswith('/api/chorus/')
                or path == '/api/cobol-synthetic-ai'
                or path.startswith('/api/cobol-synthetic-ai/')
                or path == '/api/juggernaut'
                or path.startswith('/api/juggernaut/')
                or path == '/api/bozly-cfo'
                or path.startswith('/api/bozly-cfo/')
                or path == '/api/fraud-rtsa'
                or path.startswith('/api/fraud-rtsa/')
                or path == '/api/operations-rtsa'
                or path.startswith('/api/operations-rtsa/')
                or path == '/api/surn'
                or path.startswith('/api/surn/')
                or path == '/api/uptime-agent'
                or path.startswith('/api/uptime-agent/')
                or path == '/api/application-agent'
                or path.startswith('/api/application-agent/')
                or path == '/api/database-agent'
                or path.startswith('/api/database-agent/')
                or path == '/api/deployment-agent'
                or path.startswith('/api/deployment-agent/')
                or path == '/api/infrastructure-agent'
                or path.startswith('/api/infrastructure-agent/')
                or path == '/api/integration-agent'
                or path.startswith('/api/integration-agent/')
                or path == '/api/performance-agent'
                or path.startswith('/api/performance-agent/')
                or path == '/api/backup-recovery-agent'
                or path.startswith('/api/backup-recovery-agent/')
                or path == '/api/observability-agent'
                or path.startswith('/api/observability-agent/')
                or path == '/api/quality-agent'
                or path.startswith('/api/quality-agent/')
                or path == '/api/configuration-agent'
                or path.startswith('/api/configuration-agent/')
                or path == '/api/it-support-agent'
                or path.startswith('/api/it-support-agent/')
                or path == '/api/sanders-sentinel'
                or path.startswith('/api/sanders-sentinel/')
                or path == '/api/lil-mama'
                or path.startswith('/api/lil-mama/')
                or path == '/api/baby-girl'
                or path.startswith('/api/baby-girl/')
                or path == '/api/sanders-omniconn'
                or path.startswith('/api/sanders-omniconn/')
                or path == '/api/gia-mind'
                or path.startswith('/api/gia-mind/')
                or path == '/api/ai-doctor'
                or path.startswith('/api/ai-doctor/')
                or path == '/api/ai-psychiatrist'
                or path.startswith('/api/ai-psychiatrist/')
                or path == '/api/sanders-recon'
                or path.startswith('/api/sanders-recon/')
                or path == '/api/sanders-senior-living'
                or path.startswith('/api/sanders-senior-living/')
                or path == '/api/sanders-legal-helpers'
                or path.startswith('/api/sanders-legal-helpers/')
                or path == '/api/sanders-education'
                or path.startswith('/api/sanders-education/')
                or path == '/api/sanders-finance'
                or path.startswith('/api/sanders-finance/')
                or path == '/api/sanders-retail'
                or path.startswith('/api/sanders-retail/')
                or path == '/api/sanders-logistics'
                or path.startswith('/api/sanders-logistics/')
                or path == '/api/sanders-security'
                or path.startswith('/api/sanders-security/')
                or path == '/api/sanders-real-estate'
                or path.startswith('/api/sanders-real-estate/')
                or path == '/api/sanders-energy'
                or path.startswith('/api/sanders-energy/')
                or path == '/api/sanders-transportation'
                or path.startswith('/api/sanders-transportation/')
                or path == '/api/sanders-agriculture'
                or path.startswith('/api/sanders-agriculture/')
                or path == '/api/sanders-manufacturing'
                or path.startswith('/api/sanders-manufacturing/')
                or path == '/api/sanders-consulting'
                or path.startswith('/api/sanders-consulting/')
                or path == '/api/sanders-hospitality'
                or path.startswith('/api/sanders-hospitality/')
                or path == '/api/sanders-entertainment'
                or path.startswith('/api/sanders-entertainment/')
                or path == '/api/sanders-sports'
                or path.startswith('/api/sanders-sports/')
                or path == '/api/sanders-wellness'
                or path.startswith('/api/sanders-wellness/')
                or path == '/api/sanders-steward-sentinel'
                or path.startswith('/api/sanders-steward-sentinel/')
                or path == '/api/sanders-patriot-saint'
                or path.startswith('/api/sanders-patriot-saint/')
                or path == '/api/sanders-freedom-revolution'
                or path.startswith('/api/sanders-freedom-revolution/')
                or path == '/api/sanders-strategy-hub'
                or path.startswith('/api/sanders-strategy-hub/')
                or path == '/api/sanders-global-freedom'
                or path.startswith('/api/sanders-global-freedom/')
                or path == '/api/sanders-coordinator'
                or path.startswith('/api/sanders-coordinator/')
                or path == '/api/sanders-intelligence'
                or path.startswith('/api/sanders-intelligence/')
                or path == '/api/sanders-ai-research'
                or path.startswith('/api/sanders-ai-research/')
                or path == '/api/sanders-research'
                or path.startswith('/api/sanders-research/')
                or path == '/api/sanders-communications'
                or path.startswith('/api/sanders-communications/')
                or path == '/api/sanders-banking-hub'
                or path.startswith('/api/sanders-banking-hub/')
                or path == '/api/sanders-legal-services'
                or path.startswith('/api/sanders-legal-services/')
                or path == '/api/sanders-strategy-intel'
                or path.startswith('/api/sanders-strategy-intel/')
                or path == '/api/sanders-analytics'
                or path.startswith('/api/sanders-analytics/')
                or path == '/api/sanders-innovation-lab'
                or path.startswith('/api/sanders-innovation-lab/')
                or path == '/api/sanders-supply-chain'
                or path.startswith('/api/sanders-supply-chain/')
                or path == '/api/sanders-logical-framework'
                or path.startswith('/api/sanders-logical-framework/')
                or path == '/api/sanders-infrastructure'
                or path.startswith('/api/sanders-infrastructure/')
                or path == '/api/sanders-technology'
                or path.startswith('/api/sanders-technology/')
                or path == '/api/sanders-cloud-services'
                or path.startswith('/api/sanders-cloud-services/')
                or path == '/api/showtime'
                or path.startswith('/api/showtime/')
                or path == '/api/sanders-marketing'
                or path.startswith('/api/sanders-marketing/')
                or path == '/api/sanders-sales'
                or path.startswith('/api/sanders-sales/')
                or path == '/api/sanders-customer-support'
                or path.startswith('/api/sanders-customer-support/')
                or path == '/api/sanders-human-resources'
                or path.startswith('/api/sanders-human-resources/')
                or path == '/api/sanders-security-ops'
                or path.startswith('/api/sanders-security-ops/')
                or path == '/api/sanders-global-relations'
                or path.startswith('/api/sanders-global-relations/')
                or path == '/api/sanders-healthcare'
                or path.startswith('/api/sanders-healthcare/')
                or path == '/api/the-godfather'
                or path.startswith('/api/the-godfather/')
                or path == '/api/sanders-ethics-impact-collective'
                or path.startswith('/api/sanders-ethics-impact-collective/'))

    def application(env, start):
        host = env.get('HTTP_HOST', '')
        if not isinstance(host, str):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})
        host = host.lower()
        if host.endswith(':443'):
            host = host[:-4]

        # Internal / loopback hosts: diagnostics and API only. The API
        # routes were previously unreachable here (only 'magi-backend:8000'
        # was recognised, while the worker calls 'wsgi-backend:8000' and
        # the fixture calls 127.0.0.1), and the canonical redirect below
        # used to swallow /healthz and every API call on the public host.
        if _is_internal(host):
            routed = _api_route(env, start)
            if routed is not None:
                return routed
            if _is_customer_api(env.get('PATH_INFO', '')):
                return customer(env, start)
            return _response(start, '404 Not Found', {'error': 'not_found'})

        if host not in (CANONICAL_HOST, *ALIAS_HOSTS):
            return _response(start, '421 Misdirected Request', {'error': 'host_denied'})

        # Public hosts: serve diagnostics and API routes before the
        # canonical-host redirect, so /healthz, /readyz and the /api/
        # routes are reachable through nginx instead of 308-redirecting
        # (and, for POSTs, 421-ing) every one of them.
        routed = _api_route(env, start)
        if routed is not None:
            return routed

        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if host == CANONICAL_HOST:
            if _is_customer_api(path):
                return customer(env, start)
            # Customer static pages and the auth routes are served by the
            # customer app on the canonical host too. Previously only the
            # API paths were delegated, so /auth/login, /auth/login.html
            # and /operator.html 308-redirected to '/' (and a POST there
            # 405d), while the alias host served them. '/' itself is
            # excluded: _api_route already served the portal at '/' above.
            if path.startswith('/auth/') or (path in CUSTOMER_ASSETS and path != '/'):
                return customer(env, start)
            if method not in ('GET', 'HEAD'):
                return _response(start, '421 Misdirected Request',
                                 {'error': 'canonical_origin_required'})
            start('308 Permanent Redirect', [('Location', ORIGIN + '/'),
                                               ('Content-Length', '0'), ('Cache-Control', 'no-store')])
            return [b'']

        return customer(env, start)

    return application

def load_application(factory_reference=None, *, transaction_db=None):
    """Load a trusted, administrator-installed adapter factory, not HTTP input."""
    if factory_reference is None:
        return create_application()
    if not isinstance(factory_reference, str) or not FACTORY.fullmatch(factory_reference):
        raise DeploymentConfigurationError('Expected trusted module:factory')
    module, name = factory_reference.split(':')
    factory = getattr(importlib.import_module(module), name)
    if not callable(factory):
        raise DeploymentConfigurationError('Runtime factory must be callable')
    bindings = factory()
    if not isinstance(bindings, RuntimeBindings):
        raise DeploymentConfigurationError('Configured factory must return runtime bindings')
    if (transaction_db is not None and bindings.transaction_processor is not None
        and bindings.transaction_store is None):
        bindings = replace(bindings, transaction_store=TransactionStore(transaction_db))
    return create_application(bindings)