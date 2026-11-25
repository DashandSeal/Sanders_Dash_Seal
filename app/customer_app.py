"""
Customer interface over existing case, appointment and payment components.

Authentication is an injected independent session verifier, never a user header.
Production startup must be externally verified, default API behavior is denial.
The auth application owns OIDC/session cookies, login CSRF and logout behavior.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from core_platform.appointments import AppointmentDenied, IDENT
from core_platform.cases import CaseDenied
from core_platform.provider_workflows import (
    ProviderRequestConflict,
    ProviderUnavailable,
)
from core_platform.native_case_bridge import BridgeDenied
from core_platform.rooms import RoomDenied, RoomForbidden, RoomNotFound
from core_platform.stripe_payments import PaymentDenied
from core_platform.uncle_nickey_mao import BridgeDenied, BridgeForbidden
from core_platform.carehive_os import CareHiveDenied, CareHiveForbidden
from core_platform.home_healthcare import (
    HomeHealthcareDenied,
    HomeHealthcareForbidden,
)
from core_platform.grantwriter_service import (
    GrantwriterPlatformDenied,
    GrantwriterPlatformForbidden,
)
from core_platform.pbd_validation import (
    PBDValidationDenied,
    PBDValidationForbidden,
)
from core_platform.pbd_manifest_generator import (
    PBDGeneratorDenied,
    PBDGeneratorForbidden,
)
from core_platform.vault import VaultDenied, VaultForbidden
from core_platform.pbd_sentinel import PBDSentinelDenied, PBDSentinelForbidden
from core_platform.it_ai_manager import ITAIManagerDenied, ITAIManagerForbidden
from core_platform.rtsa_foundation import FoundationForbidden

ASSETS = {
    '/auth/login': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/register': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/setup': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/logout': ('auth.html', 'text/html; charset=utf-8'),
    # The .html spellings the pages themselves link to (auth.js redirects
    # to /auth/login.html and /operator.html; the portal links
    # /auth/login.html). Previously these 308-redirected on the canonical
    # host and 503d on alias hosts because they were not in this map.
    '/auth/login.html': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/register.html': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/setup.html': ('auth.html', 'text/html; charset=utf-8'),
    '/auth/logout.html': ('auth.html', 'text/html; charset=utf-8'),
    '/operator.html': ('operator.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    # '/resources.html' and '/resources.js' retired from public serving
    # 2026-11-23 (owner ruling: "No tiers are free" — the page was publicly
    # titled "Cloud Free Tier Status" and advertised zero-cost allowances).
    # The files remain in web/ but are deliberately unrouted: this map is
    # the only route that ever served them.
    '/assets/auth.js': ('auth.js', 'application/javascript; charset=utf-8'),
    '/landing': ('jade-landing.html', 'text/html; charset=utf-8'),
    '/assets/jade-landing.css': ('jade-landing.css', 'text/css; charset=utf-8'),
    '/assets/jade-landing.js': ('jade-landing.js', 'application/javascript; charset=utf-8'),
    '/assets/sds-founder.png': ('sds-founder.png', 'image/png'),
    '/assets/wall-of-valor-primary.jpg': ('IMG_20261024_141701319_HDR.jpg', 'image/jpeg'),
    '/assets/wall-of-valor-secondary.jpg': ('IMG_20261024_141659486_HDR.jpg', 'image/jpeg'),
    '/': ('jade-landing.html', 'text/html; charset=utf-8'),
    '/appointments': ('index.html', 'text/html; charset=utf-8'),
    '/operator': ('index.html', 'text/html; charset=utf-8'),
    '/assets/operator.js': ('operator.js', 'application/javascript; charset=utf-8'),
    '/assets/booking.css': ('booking.css', 'text/css; charset=utf-8'),
    '/assets/booking.js': ('booking.js', 'application/javascript; charset=utf-8'),
    '/assets/dash-seal-banner.png': ('dash-seal-banner.png', 'image/png'),
    '/assets/seal-corporate-hq.png': ('seal-corporate-hq.png', 'image/png'),
    '/assets/seal-home-healthcare.png': ('seal-home-healthcare.png', 'image/png'),
    '/assets/seal-senior-living.png': ('seal-senior-living.png', 'image/png'),
    '/assets/seal-legal-helpers.png': ('seal-legal-helpers.png', 'image/png'),
}

CASE_ROUTE = re.compile(r'^/api/appointments/([A-Za-z0-9_-]{1,128})/checkout$')
CASE_DETAIL_ROUTE = re.compile(r'^/api/appointments/([A-Za-z0-9_-]{1,128})$')
OPERATOR_ROUTE = re.compile(r'^/api/operator/appointments/([A-Za-z0-9_-]{1,128})/quote$')
PROVIDER_ROUTE = re.compile(r'^/api/operator/appointments/([A-Za-z0-9_-]{1,128})/provider$')
NATIVE_ROUTE = re.compile(r'^/api/operator/appointments/([A-Za-z0-9_-]{1,128})/native$')
ROOM_DETAIL_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})$')
ROOM_TRANSITION_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/transition$')
ROOM_PARTICIPANTS_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/participants$')
ROOM_PARTICIPANT_REMOVE_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/participants/([A-Za-z0-9_-]{1,128})/remove$')
ROOM_INVITES_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/invites$')
ROOM_INVITE_ACCEPT_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/invites/([A-Za-z0-9_-]{1,128})/accept$')
ROOM_INVITE_REVOKE_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/invites/([A-Za-z0-9_-]{1,128})/revoke$')
ROOM_CONSENT_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/consent$')
ROOM_RECORDING_ROUTE = re.compile(r'^/api/rooms/([A-Za-z0-9_-]{1,128})/recording$')
UNM_REFERRAL_ROUTE = re.compile(r'^/api/uncle-nickey-mao/referrals/([A-Za-z0-9_-]{1,128})$')
UNM_REFERRAL_TRANSITION_ROUTE = re.compile(r'^/api/uncle-nickey-mao/referrals/([A-Za-z0-9_-]{1,128})/transition$')
CH_SUBJECT_ROUTE = re.compile(r'^/api/carehive-os/subjects/([A-Za-z0-9_-]{1,128})$')
CH_SUBJECT_CLAIM_ROUTE = re.compile(r'^/api/carehive-os/subjects/([A-Za-z0-9_-]{1,128})/claim$')
CH_SUBJECT_EVIDENCE_ROUTE = re.compile(r'^/api/carehive-os/subjects/([A-Za-z0-9_-]{1,128})/evidence$')
CH_SUBJECT_POSTCONDITIONS_ROUTE = re.compile(r'^/api/carehive-os/subjects/([A-Za-z0-9_-]{1,128})/postconditions$')
CH_VERSION_PROMOTE_ROUTE = re.compile(r'^/api/carehive-os/versions/([A-Za-z0-9_-]{1,128})/promote$')
CH_INTEROP_ROUTE = re.compile(r'^/api/carehive-os/interop/([A-Za-z0-9_-]{1,128})/validate$')
HH_INTAKE_ROUTE = re.compile(r'^/api/home-healthcare/intakes/([A-Za-z0-9_-]{1,128})$')
HH_INTAKE_TRANSITION_ROUTE = re.compile(r'^/api/home-healthcare/intakes/([A-Za-z0-9_-]{1,128})/transition$')
HH_INTAKE_ROOM_ROUTE = re.compile(r'^/api/home-healthcare/intakes/([A-Za-z0-9_-]{1,128})/consultation-room$')
HH_ASSIGNMENT_ROUTE = re.compile(r'^/api/home-healthcare/assignments/([A-Za-z0-9_-]{1,128})$')
HH_ASSIGNMENT_TRANSITION_ROUTE = re.compile(r'^/api/home-healthcare/assignments/([A-Za-z0-9_-]{1,128})/transition$')
GW_APPLICATION_STAGE_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/stage$')
GW_APPLICATION_BUDGET_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/budget-lines$')
GW_APPLICATION_EVIDENCE_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/evidence$')
GW_APPLICATION_TRANSITIONS_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/transitions$')
GW_APPLICATION_SUBMISSION_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/submission$')
GW_APPLICATION_DRAFT_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/draft$')
GW_APPLICATION_COMPLIANCE_ROUTE = re.compile(r'^/api/grantwriter/applications/([A-Za-z0-9_-]{1,128})/compliance$')
PBD_VALIDATION_VIEW_ROUTE = re.compile(r'^/api/pbd-validation/validations/([A-Za-z0-9_-]{1,128})$')
PBD_GENERATOR_VIEW_ROUTE = re.compile(r'^/api/pbd-manifest-generator/generations/([A-Za-z0-9_-]{1,128})$')
VAULT_LEASE_ROUTE = re.compile(r'^/api/vault/leases/([A-Za-z0-9_-]{1,128})$')
VAULT_LEASE_REVOKE_ROUTE = re.compile(r'^/api/vault/leases/([A-Za-z0-9_-]{1,128})/revoke$')
VAULT_LEASE_BURN_ROUTE = re.compile(r'^/api/vault/leases/([A-Za-z0-9_-]{1,128})/burn$')
PBD_SENTINEL_FINDING_ROUTE = re.compile(r'^/api/pbd-sentinel/findings/([A-Za-z0-9_-]{1,128})$')
PBD_SENTINEL_FINDING_ACTION_ROUTE = re.compile(r'^/api/pbd-sentinel/findings/([A-Za-z0-9_-]{1,128})/(isolate|alert|preserve|verify|release|rebuild)$')
ITM_INCIDENT_ROUTE = re.compile(r'^/api/it-ai-manager/incidents/([A-Za-z0-9_-]{1,128})$')
ITM_INCIDENT_ACTION_ROUTE = re.compile(r'^/api/it-ai-manager/incidents/([A-Za-z0-9_-]{1,128})/(diagnose|dispatch|rollback|failover|verify|reconcile)$')
ITM_WORK_ORDER_ROUTE = re.compile(r'^/api/it-ai-manager/work-orders/([A-Za-z0-9_-]{1,128})$')
ITM_WORK_ORDER_OUTCOME_ROUTE = re.compile(r'^/api/it-ai-manager/work-orders/([A-Za-z0-9_-]{1,128})/outcome$')
ITM_EVALUATION_ROUTE = re.compile(r'^/api/it-ai-manager/evaluations/([A-Za-z0-9_-]{1,128})$')
ROOM_CREATE_FIELDS = {'room_type', 'purpose', 'case_id', 'jurisdiction', 'scheduled_start', 'scheduled_end', 'recording_policy', 'retention_days', 'consent_notice_version'}

def create_customer_app(appointments, authenticate, payments, auth_app, site_origin, *, release_verifier=lambda: False, allowed_origins=None, provider_workflows=None, provider_gate=None, native_bridge=None, native_gate=None, rooms=None, uncle_nickey_mao=None, carehive_os=None, home_healthcare=None, grantwriter=None, pbd_validation=None, pbd_manifest_generator=None, vault=None, pbd_sentinel=None, it_ai_manager=None):
    # allowed_origins: every origin a browser may POST from. The app serves
    # two domains from one process (canonical + aliases); the POST Origin
    # check previously compared against the canonical origin only, so every
    # POST from an alias host — sign-in, appointment request, quote, checkout
    # — answered 403 origin_denied. Defaults to the site origin alone.
    allowed_origins = frozenset(allowed_origins) if allowed_origins is not None else frozenset((site_origin,))
    origin = urlparse(site_origin)
    if (origin.scheme != 'https' or not origin.netloc or origin.path
        or origin.query or origin.fragment or origin.username
        or not all(callable(v) for v in (authenticate, auth_app, release_verifier))):
        raise ValueError('Trusted origin and independent authentication adapters required')
        
    root = Path(__file__).resolve().parent.parent / 'web'

    def respond(start_response, status, data, content_type='application/json'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        start_response(status, [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; "
                                        "connect-src 'self'; img-src 'self' data:; base-uri none; form-action 'self'; frame-ancestors 'none'"),
            ('X-Content-Type-Options', 'nosniff')
        ])
        return [body]

    def app(env, start):
        path, method = env.get('PATH_INFO', ''), env.get('REQUEST_METHOD', '')
        if method == 'GET' and path in ASSETS:
            filename, mime = ASSETS[path]
            return respond(start, '200 OK', (root / filename).read_bytes(), mime)
            
        try:
            if release_verifier() is not True:
                return respond(start, '503 Service Unavailable', {'error': 'appointments_unavailable'})
        except Exception:
            return respond(start, '503 Service Unavailable', {'error': 'appointments_unavailable'})

        if path.startswith('/auth/'):
            return auth_app(env, start)

        case_match = CASE_ROUTE.fullmatch(path)
        detail_match = CASE_DETAIL_ROUTE.fullmatch(path)
        operator_match = OPERATOR_ROUTE.fullmatch(path)
        provider_match = PROVIDER_ROUTE.fullmatch(path)
        native_match = NATIVE_ROUTE.fullmatch(path)
        room_detail_match = ROOM_DETAIL_ROUTE.fullmatch(path)
        room_transition_match = ROOM_TRANSITION_ROUTE.fullmatch(path)
        room_participants_match = ROOM_PARTICIPANTS_ROUTE.fullmatch(path)
        room_remove_match = ROOM_PARTICIPANT_REMOVE_ROUTE.fullmatch(path)
        room_invites_match = ROOM_INVITES_ROUTE.fullmatch(path)
        room_accept_match = ROOM_INVITE_ACCEPT_ROUTE.fullmatch(path)
        room_revoke_match = ROOM_INVITE_REVOKE_ROUTE.fullmatch(path)
        room_consent_match = ROOM_CONSENT_ROUTE.fullmatch(path)
        room_recording_match = ROOM_RECORDING_ROUTE.fullmatch(path)
        unm_referral_match = UNM_REFERRAL_ROUTE.fullmatch(path)
        unm_referral_transition_match = UNM_REFERRAL_TRANSITION_ROUTE.fullmatch(path)
        ch_subject_match = CH_SUBJECT_ROUTE.fullmatch(path)
        ch_subject_claim_match = CH_SUBJECT_CLAIM_ROUTE.fullmatch(path)
        ch_subject_evidence_match = CH_SUBJECT_EVIDENCE_ROUTE.fullmatch(path)
        ch_subject_postconditions_match = CH_SUBJECT_POSTCONDITIONS_ROUTE.fullmatch(path)
        ch_version_promote_match = CH_VERSION_PROMOTE_ROUTE.fullmatch(path)
        ch_interop_match = CH_INTEROP_ROUTE.fullmatch(path)
        hh_intake_match = HH_INTAKE_ROUTE.fullmatch(path)
        hh_intake_transition_match = HH_INTAKE_TRANSITION_ROUTE.fullmatch(path)
        hh_intake_room_match = HH_INTAKE_ROOM_ROUTE.fullmatch(path)
        hh_assignment_match = HH_ASSIGNMENT_ROUTE.fullmatch(path)
        hh_assignment_transition_match = HH_ASSIGNMENT_TRANSITION_ROUTE.fullmatch(path)
        gw_stage_match = GW_APPLICATION_STAGE_ROUTE.fullmatch(path)
        gw_budget_match = GW_APPLICATION_BUDGET_ROUTE.fullmatch(path)
        gw_evidence_match = GW_APPLICATION_EVIDENCE_ROUTE.fullmatch(path)
        gw_transitions_match = GW_APPLICATION_TRANSITIONS_ROUTE.fullmatch(path)
        gw_submission_match = GW_APPLICATION_SUBMISSION_ROUTE.fullmatch(path)
        gw_draft_match = GW_APPLICATION_DRAFT_ROUTE.fullmatch(path)
        gw_compliance_match = GW_APPLICATION_COMPLIANCE_ROUTE.fullmatch(path)
        pbd_validation_view_match = PBD_VALIDATION_VIEW_ROUTE.fullmatch(path)
        pbd_generator_view_match = PBD_GENERATOR_VIEW_ROUTE.fullmatch(path)
        vault_lease_match = VAULT_LEASE_ROUTE.fullmatch(path)
        vault_lease_revoke_match = VAULT_LEASE_REVOKE_ROUTE.fullmatch(path)
        vault_lease_burn_match = VAULT_LEASE_BURN_ROUTE.fullmatch(path)
        pbd_sentinel_finding_match = PBD_SENTINEL_FINDING_ROUTE.fullmatch(path)
        pbd_sentinel_action_match = PBD_SENTINEL_FINDING_ACTION_ROUTE.fullmatch(path)
        itm_incident_match = ITM_INCIDENT_ROUTE.fullmatch(path)
        itm_incident_action_match = ITM_INCIDENT_ACTION_ROUTE.fullmatch(path)
        itm_work_order_match = ITM_WORK_ORDER_ROUTE.fullmatch(path)
        itm_work_order_outcome_match = ITM_WORK_ORDER_OUTCOME_ROUTE.fullmatch(path)
        itm_evaluation_match = ITM_EVALUATION_ROUTE.fullmatch(path)
        is_unm_route = (path in ('/api/uncle-nickey-mao/status',
                                 '/api/uncle-nickey-mao/guardian-relay',
                                 '/api/uncle-nickey-mao/referrals',
                                 '/api/uncle-nickey-mao/check-in')
                        or unm_referral_match is not None
                        or unm_referral_transition_match is not None)
        is_carehive_route = (path in ('/api/carehive-os/status',
                                      '/api/carehive-os/subjects',
                                      '/api/carehive-os/cycles',
                                      '/api/carehive-os/versions',
                                      '/api/carehive-os/versions/rollback',
                                      '/api/carehive-os/check-in')
                             or ch_subject_match is not None
                             or ch_subject_claim_match is not None
                             or ch_subject_evidence_match is not None
                             or ch_subject_postconditions_match is not None
                             or ch_version_promote_match is not None
                             or ch_interop_match is not None)
        is_home_healthcare_route = (path in ('/api/home-healthcare/status',
                                             '/api/home-healthcare/intakes',
                                             '/api/home-healthcare/assignments',
                                             '/api/home-healthcare/check-in')
                                    or hh_intake_match is not None
                                    or hh_intake_transition_match is not None
                                    or hh_intake_room_match is not None
                                    or hh_assignment_match is not None
                                    or hh_assignment_transition_match is not None)
        is_grantwriter_route = (path in ('/api/grantwriter/status',
                                         '/api/grantwriter/opportunities',
                                         '/api/grantwriter/applications',
                                         '/api/grantwriter/portfolio',
                                         '/api/grantwriter/check-in')
                                or gw_stage_match is not None
                                or gw_budget_match is not None
                                or gw_evidence_match is not None
                                or gw_transitions_match is not None
                                or gw_submission_match is not None
                                or gw_draft_match is not None
                                or gw_compliance_match is not None)
        is_pbd_validation_route = (path in ('/api/pbd-validation/status',
                                            '/api/pbd-validation/validate',
                                            '/api/pbd-validation/scan',
                                            '/api/pbd-validation/check-in')
                                   or pbd_validation_view_match is not None)
        is_pbd_generator_route = (path in ('/api/pbd-manifest-generator/status',
                                           '/api/pbd-manifest-generator/generate',
                                           '/api/pbd-manifest-generator/check-in')
                                  or pbd_generator_view_match is not None)
        is_vault_route = (path in ('/api/vault/status',
                                   '/api/vault/leases',
                                   '/api/vault/verify',
                                   '/api/vault/consume',
                                   '/api/vault/sweep',
                                   '/api/vault/check-in')
                          or vault_lease_match is not None
                          or vault_lease_revoke_match is not None
                          or vault_lease_burn_match is not None)
        is_pbd_sentinel_route = (path in ('/api/pbd-sentinel/status',
                                          '/api/pbd-sentinel/scan',
                                          '/api/pbd-sentinel/check-in')
                                 or pbd_sentinel_finding_match is not None
                                 or pbd_sentinel_action_match is not None)
        is_itm_route = (path in ('/api/it-ai-manager/status',
                                 '/api/it-ai-manager/agents',
                                 '/api/it-ai-manager/incidents',
                                 '/api/it-ai-manager/evaluations',
                                 '/api/it-ai-manager/check-in')
                        or itm_incident_match is not None
                        or itm_incident_action_match is not None
                        or itm_work_order_match is not None
                        or itm_work_order_outcome_match is not None
                        or itm_evaluation_match is not None)
        is_platform_route = (is_unm_route or is_carehive_route
                             or is_home_healthcare_route
                             or is_grantwriter_route
                             or is_pbd_validation_route
                             or is_pbd_generator_route
                             or is_vault_route
                             or is_pbd_sentinel_route
                             or is_itm_route)
        is_rooms_route = (path == '/api/rooms'
                          or room_detail_match is not None
                          or room_transition_match is not None
                          or room_participants_match is not None
                          or room_remove_match is not None
                          or room_invites_match is not None
                          or room_accept_match is not None
                          or room_revoke_match is not None
                          or room_consent_match is not None
                          or room_recording_match is not None)
        is_operator_route = (path == '/api/operator/appointments'
                             or operator_match is not None
                             or provider_match is not None
                             or native_match is not None)

        if path not in ('/api/session', '/api/appointments') and not case_match and not detail_match and not is_operator_route and not is_rooms_route and not is_platform_route:
            return respond(start, '404 Not Found', {'error': 'not_found'})

        if is_platform_route:
            allowed = ('GET',) if (path in ('/api/uncle-nickey-mao/status',
                                            '/api/uncle-nickey-mao/guardian-relay',
                                            '/api/carehive-os/status',
                                            '/api/home-healthcare/status',
                                            '/api/grantwriter/status',
                                            '/api/grantwriter/portfolio',
                                            '/api/pbd-validation/status',
                                            '/api/pbd-manifest-generator/status',
                                            '/api/vault/status',
                                            '/api/pbd-sentinel/status',
                                            '/api/it-ai-manager/status',
                                            '/api/it-ai-manager/agents')
                                   or unm_referral_match is not None
                                   or hh_intake_match is not None
                                   or hh_assignment_match is not None
                                   or gw_stage_match is not None
                                   or gw_compliance_match is not None
                                   or pbd_validation_view_match is not None
                                   or pbd_generator_view_match is not None
                                   or vault_lease_match is not None
                                   or pbd_sentinel_finding_match is not None
                                   or itm_incident_match is not None
                                   or itm_work_order_match is not None
                                   or itm_evaluation_match is not None) else ('POST',)
        elif is_rooms_route:
            allowed = ('GET', 'POST') if path == '/api/rooms' else (
                ('GET',) if room_detail_match else ('POST',))
        else:
            allowed = ('GET', 'POST') if path == '/api/appointments' or provider_match or native_match else (
                ('POST',) if operator_match or case_match else ('GET',)
            )
        if method not in allowed:
            return respond(start, '405 Method Not Allowed', {'error': 'method_not_allowed'})

        try:
            identity = authenticate(env)
        except Exception:
            identity = None

        if not isinstance(identity, str) or not IDENT.fullmatch(identity):
            return respond(start, '401 Unauthorized', {'error': 'sign_in_required'})

        if is_operator_route:
            try:
                authorized = payments.operator_verifier(identity) is True
            except Exception:
                authorized = False
            if not authorized:
                return respond(start, '403 Forbidden', {'error': 'operator_required'})

        data = None
        if method == 'POST':
            if env.get('HTTP_ORIGIN') not in allowed_origins:
                return respond(start, '403 Forbidden', {'error': 'origin_denied'})
            if env.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
                return respond(start, '415 Unsupported Media Type', {'error': 'json_required'})
            try:
                length = env.get('CONTENT_LENGTH', '')
                if not isinstance(length, str) or not length.isdigit() or not 0 < int(length) <= 4096:
                    raise ValueError('length')
                row = env['wsgi.input'].read(int(length))
                if len(row) != int(length):
                    raise ValueError('short body')
                data = json.loads(row)
                if not isinstance(data, dict):
                    raise ValueError('object required')
            except (ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError):
                return respond(start, '400 Bad Request', {'error': 'invalid_request'})

        try:
            if path == '/api/operator/appointments':
                return respond(start, '200 OK', {'appointments': appointments.list_for_operator()})
            if provider_match:
                case_id = provider_match.group(1)
                if provider_workflows is None:
                    # No provider workspace backend is wired in this
                    # runtime; the operator UI renders an empty list as
                    # "No remote connection requests initialized yet."
                    return respond(start, '200 OK', {'requests': []})
                if method == 'GET':
                    return respond(start, '200 OK', {
                        'requests': provider_workflows.records(
                            case_id, identity)})
                if (set(data) != {'provider', 'request'}
                        or not isinstance(data.get('request'), dict)):
                    raise ValueError('unexpected fields')
                # A live provider call requires the owner's ron_notarial
                # approval gate, the same rule deploy/deployment.py
                # applies to every live provider route. The gate check
                # is injected; absent or unapproved fails closed.
                if provider_gate is None or provider_gate() is not True:
                    return respond(start, '503 Service Unavailable', {
                        'error': 'approval_required',
                        'gate': 'ron_notarial'})
                receipt = provider_workflows.submit(
                    case_id, identity, data['provider'], data['request'])
                return respond(start, '201 Created', {'request': receipt})
            if native_match:
                case_id = native_match.group(1)
                if native_bridge is None:
                    # No native bridge is wired in this runtime; the
                    # operator UI renders this as "no native session".
                    return respond(start, '200 OK', {'native_session': None})
                if method == 'GET':
                    return respond(start, '200 OK', {
                        'native_session': native_bridge.status_for_case(
                            case_id)})
                if set(data) != {'action'} or data.get('action') != 'open':
                    raise ValueError('unexpected fields')
                # Opening a native notarial session is a live notarial
                # operation: it requires the owner's ron_notarial
                # approval gate, the same rule the provider route and
                # deploy/deployment.py apply. Absent or unapproved
                # fails closed.
                if native_gate is None or native_gate() is not True:
                    return respond(start, '503 Service Unavailable', {
                        'error': 'approval_required',
                        'gate': 'ron_notarial'})
                record = native_bridge.open_session(case_id, identity)
                return respond(start, '201 Created', {'native_session': record})
            if is_rooms_route:
                # Commercial meeting rooms (MASTER Section 22 control
                # plane): governed room objects — lifecycle, roles,
                # invitations, consent, retention — with authority
                # enforced inside the rooms service itself. Rooms carry
                # no notarial function and mint no media token; media
                # issuance stays behind the voice_video_provider gate
                # in the realtime module.
                if rooms is None:
                    return respond(start, '503 Service Unavailable', {'error': 'rooms_unavailable'})
                if path == '/api/rooms':
                    if method == 'GET':
                        return respond(start, '200 OK', {'rooms': rooms.list_for_actor(identity)})
                    if set(data) - ROOM_CREATE_FIELDS or not {'room_type', 'purpose'} <= set(data):
                        raise ValueError('unexpected fields')
                    record = rooms.create_room(identity, **data)
                    return respond(start, '201 Created', {'room': record})
                room_match = (room_detail_match or room_transition_match
                              or room_participants_match or room_remove_match
                              or room_invites_match or room_accept_match
                              or room_revoke_match or room_consent_match
                              or room_recording_match)
                room_id = room_match.group(1)
                if room_detail_match:
                    return respond(start, '200 OK', {'room': rooms.get_room(room_id, identity)})
                if room_transition_match:
                    if set(data) - {'action', 'scheduled_start', 'scheduled_end'} or 'action' not in data:
                        raise ValueError('unexpected fields')
                    action = data.pop('action')
                    return respond(start, '200 OK', {'room': rooms.transition(room_id, identity, action, **data)})
                if room_participants_match:
                    if set(data) != {'identity', 'role'}:
                        raise ValueError('unexpected fields')
                    return respond(start, '200 OK', {'room': rooms.add_participant(room_id, identity, data['identity'], data['role'])})
                if room_remove_match:
                    if set(data) != set():
                        raise ValueError('unexpected fields')
                    return respond(start, '200 OK', {'room': rooms.remove_participant(room_id, identity, room_remove_match.group(2))})
                if room_invites_match:
                    if set(data) - {'invitee', 'role', 'ttl_seconds'} or not {'invitee', 'role'} <= set(data):
                        raise ValueError('unexpected fields')
                    invite = rooms.issue_invite(room_id, identity, **data)
                    return respond(start, '201 Created', {'invite': invite})
                if room_accept_match:
                    if set(data) != set():
                        raise ValueError('unexpected fields')
                    return respond(start, '200 OK', {'room': rooms.accept_invite(room_id, identity, room_accept_match.group(2))})
                if room_revoke_match:
                    if set(data) != set():
                        raise ValueError('unexpected fields')
                    invite = rooms.revoke_invite(room_id, identity, room_revoke_match.group(2))
                    return respond(start, '200 OK', {'invite': invite})
                if room_consent_match:
                    if set(data) != {'decision', 'notice_version'}:
                        raise ValueError('unexpected fields')
                    consent = rooms.record_consent(room_id, identity, **data)
                    return respond(start, '201 Created', {'consent': consent})
                if room_recording_match:
                    if set(data) != {'action'}:
                        raise ValueError('unexpected fields')
                    if data['action'] == 'authorize':
                        return respond(start, '200 OK', {'room': rooms.authorize_recording(room_id, identity)})
                    if data['action'] == 'revoke':
                        return respond(start, '200 OK', {'room': rooms.revoke_recording(room_id, identity)})
                    raise ValueError('unexpected fields')
            if is_platform_route:
                # The four reconstructed RTSA platforms (Three
                # Originals Reconstruction Program): governed service
                # objects in the rooms pattern — authority enforced
                # inside each service, the routes only bind the
                # session identity as actor and translate the service
                # exceptions into the family's error shapes. Operator
                # status uses the same determination the operator
                # routes use (payments.operator_verifier).
                def is_operator():
                    try:
                        return payments.operator_verifier(identity) is True
                    except Exception:
                        return False

                def check_in(service):
                    if set(data) != {'deployment_location', 'operational_status'}:
                        raise ValueError('unexpected fields')
                    return respond(start, '201 Created', {
                        'check_in': service.record_check_in(
                            identity, data['deployment_location'],
                            data['operational_status'])})

                if is_unm_route:
                    if uncle_nickey_mao is None:
                        return respond(start, '503 Service Unavailable', {'error': 'uncle_nickey_mao_unavailable'})
                    if path == '/api/uncle-nickey-mao/status':
                        return respond(start, '200 OK', {'status': uncle_nickey_mao.status()})
                    if path == '/api/uncle-nickey-mao/guardian-relay':
                        return respond(start, '200 OK', {'guardian_relay': uncle_nickey_mao.guardian_relay_status()})
                    if path == '/api/uncle-nickey-mao/referrals':
                        if set(data) != {'from_industry', 'to_industry', 'subject_ref', 'jurisdiction'}:
                            raise ValueError('unexpected fields')
                        record = uncle_nickey_mao.create_referral(identity, **data)
                        return respond(start, '201 Created', {'referral': record})
                    if unm_referral_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = uncle_nickey_mao.referral_view(identity, role, unm_referral_match.group(1))
                        return respond(start, '200 OK', {'referral': record})
                    if unm_referral_transition_match:
                        if set(data) != {'target'}:
                            raise ValueError('unexpected fields')
                        record = uncle_nickey_mao.transition_referral(identity, unm_referral_transition_match.group(1), data['target'])
                        return respond(start, '200 OK', {'referral': record})
                    return check_in(uncle_nickey_mao)
                if is_carehive_route:
                    if carehive_os is None:
                        return respond(start, '503 Service Unavailable', {'error': 'carehive_os_unavailable'})
                    if path == '/api/carehive-os/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': carehive_os.status()})
                    if path == '/api/carehive-os/subjects':
                        if set(data) != {'subject_id', 'kind', 'status_claim'}:
                            raise ValueError('unexpected fields')
                        record = carehive_os.register_subject(identity, **data)
                        return respond(start, '201 Created', {'subject': record})
                    if ch_subject_claim_match:
                        if set(data) != {'status_claim'}:
                            raise ValueError('unexpected fields')
                        record = carehive_os.update_claim(identity, ch_subject_claim_match.group(1), data['status_claim'])
                        return respond(start, '200 OK', {'subject': record})
                    if ch_subject_evidence_match:
                        if set(data) != {'kind', 'payload'}:
                            raise ValueError('unexpected fields')
                        record = carehive_os.append_evidence(identity, ch_subject_evidence_match.group(1), **data)
                        return respond(start, '201 Created', {'evidence': record})
                    if ch_subject_postconditions_match:
                        if set(data) != {'postcondition', 'observed_state'}:
                            raise ValueError('unexpected fields')
                        record = carehive_os.verify_postcondition(identity, ch_subject_postconditions_match.group(1), **data)
                        return respond(start, '201 Created', {'postcondition': record})
                    if path == '/api/carehive-os/cycles':
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        return respond(start, '201 Created', {'cycle': carehive_os.run_cycle(identity)})
                    if path == '/api/carehive-os/versions':
                        if set(data) != {'version_label'}:
                            raise ValueError('unexpected fields')
                        record = carehive_os.propose_version(identity, data['version_label'])
                        return respond(start, '201 Created', {'version': record})
                    if ch_version_promote_match:
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = carehive_os.promote_version(identity, ch_version_promote_match.group(1))
                        return respond(start, '200 OK', {'version': record})
                    if path == '/api/carehive-os/versions/rollback':
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        return respond(start, '200 OK', {'version': carehive_os.rollback_version(identity)})
                    if ch_interop_match:
                        if set(data) != {'payload'}:
                            raise ValueError('unexpected fields')
                        result = carehive_os.validate_envelope(ch_interop_match.group(1), data['payload'])
                        return respond(start, '200 OK', {'validation': result})
                    return check_in(carehive_os)
                if is_home_healthcare_route:
                    if home_healthcare is None:
                        return respond(start, '503 Service Unavailable', {'error': 'home_healthcare_unavailable'})
                    if path == '/api/home-healthcare/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': home_healthcare.status()})
                    if path == '/api/home-healthcare/intakes':
                        if set(data) != {'client_ref', 'service_line', 'jurisdiction'}:
                            raise ValueError('unexpected fields')
                        record = home_healthcare.create_intake(identity, **data)
                        return respond(start, '201 Created', {'intake': record})
                    if hh_intake_match:
                        role = 'OPERATOR' if is_operator() else 'CLIENT'
                        record = home_healthcare.intake_view(identity, role, hh_intake_match.group(1))
                        return respond(start, '200 OK', {'intake': record})
                    if hh_intake_transition_match:
                        if set(data) != {'target'}:
                            raise ValueError('unexpected fields')
                        record = home_healthcare.transition_intake(identity, hh_intake_transition_match.group(1), data['target'])
                        return respond(start, '200 OK', {'intake': record})
                    if hh_intake_room_match:
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = home_healthcare.create_consultation_room(identity, hh_intake_room_match.group(1))
                        return respond(start, '201 Created', {'room': record})
                    if path == '/api/home-healthcare/assignments':
                        if set(data) != {'intake_id', 'caregiver_ref', 'starts_at', 'ends_at'}:
                            raise ValueError('unexpected fields')
                        record = home_healthcare.create_assignment(identity, **data)
                        return respond(start, '201 Created', {'assignment': record})
                    if hh_assignment_match:
                        role = 'OPERATOR' if is_operator() else 'CAREGIVER'
                        record = home_healthcare.assignment_view(identity, role, hh_assignment_match.group(1))
                        return respond(start, '200 OK', {'assignment': record})
                    if hh_assignment_transition_match:
                        if set(data) != {'target'}:
                            raise ValueError('unexpected fields')
                        record = home_healthcare.transition_assignment(identity, hh_assignment_transition_match.group(1), data['target'])
                        return respond(start, '200 OK', {'assignment': record})
                    return check_in(home_healthcare)
                if is_grantwriter_route:
                    if grantwriter is None:
                        return respond(start, '503 Service Unavailable', {'error': 'grantwriter_unavailable'})
                    if path == '/api/grantwriter/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': grantwriter.status()})
                    if path == '/api/grantwriter/opportunities':
                        if 'jurisdiction' not in data:
                            raise ValueError('unexpected fields')
                        fields = dict(data)
                        jurisdiction = fields.pop('jurisdiction')
                        record = grantwriter.create_opportunity(identity, jurisdiction, **fields)
                        return respond(start, '201 Created', {'opportunity': record})
                    if path == '/api/grantwriter/applications':
                        if 'jurisdiction' not in data:
                            raise ValueError('unexpected fields')
                        fields = dict(data)
                        jurisdiction = fields.pop('jurisdiction')
                        record = grantwriter.create_application(identity, jurisdiction, **fields)
                        return respond(start, '201 Created', {'application': record})
                    if gw_stage_match:
                        record = grantwriter.workflow_for(gw_stage_match.group(1))
                        return respond(start, '200 OK', {'stage': record['stage'] if record else None, 'workflow': record})
                    if gw_budget_match:
                        record = grantwriter.add_budget_line(identity, gw_budget_match.group(1), **data)
                        return respond(start, '201 Created', {'budget_line': record})
                    if gw_evidence_match:
                        record = grantwriter.attach_evidence(identity, gw_evidence_match.group(1), **data)
                        return respond(start, '201 Created', {'evidence': record})
                    if gw_transitions_match:
                        if set(data) != {'target_stage'}:
                            raise ValueError('unexpected fields')
                        record = grantwriter.transition_stage(identity, gw_transitions_match.group(1), data['target_stage'])
                        return respond(start, '200 OK', {'workflow': record})
                    if gw_submission_match:
                        if set(data) != {'external_ref'}:
                            raise ValueError('unexpected fields')
                        record = grantwriter.record_submission(identity, gw_submission_match.group(1), data['external_ref'])
                        return respond(start, '200 OK', {'workflow': record})
                    if gw_draft_match:
                        if set(data) - {'mode'}:
                            raise ValueError('unexpected fields')
                        record = grantwriter.generate_draft(identity, gw_draft_match.group(1), mode=data.get('mode', 'offline'))
                        return respond(start, '200 OK', {'draft': record})
                    if path == '/api/grantwriter/portfolio':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'portfolio': grantwriter.portfolio_view(identity, 'OPERATOR')})
                    if gw_compliance_match:
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        result = grantwriter.compliance_evaluate(identity, 'OPERATOR', gw_compliance_match.group(1))
                        return respond(start, '200 OK', {'compliance': result})
                    return check_in(grantwriter)
                if is_pbd_validation_route:
                    if pbd_validation is None:
                        return respond(start, '503 Service Unavailable', {'error': 'pbd_validation_unavailable'})
                    if path == '/api/pbd-validation/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': pbd_validation.status()})
                    if path == '/api/pbd-validation/validate':
                        if set(data) != {'artifact'}:
                            raise ValueError('unexpected fields')
                        record = pbd_validation.validate_pair(identity, data['artifact'])
                        return respond(start, '201 Created', {'validation': record})
                    if path == '/api/pbd-validation/scan':
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = pbd_validation.scan(identity)
                        return respond(start, '201 Created', {'scan': record})
                    if pbd_validation_view_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = pbd_validation.validation_view(identity, role, pbd_validation_view_match.group(1))
                        return respond(start, '200 OK', {'validation': record})
                    return check_in(pbd_validation)
                if is_pbd_generator_route:
                    if pbd_manifest_generator is None:
                        return respond(start, '503 Service Unavailable', {'error': 'pbd_manifest_generator_unavailable'})
                    if path == '/api/pbd-manifest-generator/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': pbd_manifest_generator.status()})
                    if path == '/api/pbd-manifest-generator/generate':
                        if set(data) - {'artifact', 'scope', 'endpoint'} or 'artifact' not in data:
                            raise ValueError('unexpected fields')
                        record = pbd_manifest_generator.generate(identity, data['artifact'], scope=data.get('scope', 'source-manifest'), endpoint=data.get('endpoint'))
                        return respond(start, '201 Created', {'generation': record})
                    if pbd_generator_view_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = pbd_manifest_generator.generation_view(identity, role, pbd_generator_view_match.group(1))
                        return respond(start, '200 OK', {'generation': record})
                    return check_in(pbd_manifest_generator)
                if is_vault_route:
                    if vault is None:
                        return respond(start, '503 Service Unavailable', {'error': 'vault_unavailable'})
                    if path == '/api/vault/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': vault.status()})
                    if path == '/api/vault/leases':
                        if set(data) - {'requesting_agent', 'target_endpoint', 'allowed_verbs', 'ttl_seconds', 'max_executions', 'authorization_metadata'} or not {'requesting_agent', 'target_endpoint', 'allowed_verbs', 'ttl_seconds'} <= set(data):
                            raise ValueError('unexpected fields')
                        record = vault.issue_lease(identity, **data)
                        return respond(start, '201 Created', {'lease': record})
                    if path == '/api/vault/verify':
                        if set(data) - {'token', 'endpoint', 'verb'} or 'token' not in data:
                            raise ValueError('unexpected fields')
                        result = vault.verify_token(data['token'], endpoint=data.get('endpoint'), verb=data.get('verb'))
                        return respond(start, '200 OK', {'verification': result})
                    if path == '/api/vault/consume':
                        if set(data) != {'token', 'endpoint', 'verb'}:
                            raise ValueError('unexpected fields')
                        record = vault.consume_execution(identity, data['token'], data['endpoint'], data['verb'])
                        return respond(start, '200 OK', {'lease': record})
                    if path == '/api/vault/sweep':
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        result = vault.sweep_expired(identity)
                        return respond(start, '200 OK', {'sweep': result})
                    if vault_lease_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = vault.lease_view(identity, role, vault_lease_match.group(1))
                        return respond(start, '200 OK', {'lease': record})
                    if vault_lease_revoke_match:
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = vault.revoke_lease(identity, vault_lease_revoke_match.group(1))
                        return respond(start, '200 OK', {'lease': record})
                    if vault_lease_burn_match:
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = vault.burn_lease(identity, vault_lease_burn_match.group(1))
                        return respond(start, '200 OK', {'lease': record})
                    return check_in(vault)
                if is_pbd_sentinel_route:
                    if pbd_sentinel is None:
                        return respond(start, '503 Service Unavailable', {'error': 'pbd_sentinel_unavailable'})
                    if path == '/api/pbd-sentinel/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': pbd_sentinel.status()})
                    if path == '/api/pbd-sentinel/scan':
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = pbd_sentinel.run_scan(identity)
                        return respond(start, '201 Created', {'scan': record})
                    if pbd_sentinel_finding_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = pbd_sentinel.finding_view(identity, role, pbd_sentinel_finding_match.group(1))
                        return respond(start, '200 OK', {'finding': record})
                    if pbd_sentinel_action_match:
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        action = pbd_sentinel_action_match.group(2)
                        handler = {'isolate': pbd_sentinel.isolate,
                                   'alert': pbd_sentinel.alert,
                                   'preserve': pbd_sentinel.preserve,
                                   'verify': pbd_sentinel.verify,
                                   'release': pbd_sentinel.release,
                                   'rebuild': pbd_sentinel.mark_rebuild}[action]
                        record = handler(identity, pbd_sentinel_action_match.group(1))
                        return respond(start, '200 OK', {'finding': record})
                    return check_in(pbd_sentinel)
                if is_itm_route:
                    if it_ai_manager is None:
                        return respond(start, '503 Service Unavailable', {'error': 'it_ai_manager_unavailable'})
                    if path == '/api/it-ai-manager/status':
                        if not is_operator():
                            return respond(start, '403 Forbidden', {'error': 'operator_required'})
                        return respond(start, '200 OK', {'status': it_ai_manager.status()})
                    if path == '/api/it-ai-manager/agents':
                        return respond(start, '200 OK', {'agents': it_ai_manager.agent_matrix()})
                    if path == '/api/it-ai-manager/incidents':
                        if set(data) - {'component', 'symptom', 'evidence_ref'} or not {'component', 'symptom'} <= set(data):
                            raise ValueError('unexpected fields')
                        record = it_ai_manager.report_incident(identity, data['component'], data['symptom'], evidence_ref=data.get('evidence_ref', ''))
                        return respond(start, '201 Created', {'incident': record})
                    if itm_incident_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = it_ai_manager.incident_view(identity, role, itm_incident_match.group(1))
                        return respond(start, '200 OK', {'incident': record})
                    if itm_incident_action_match:
                        incident_id = itm_incident_action_match.group(1)
                        action = itm_incident_action_match.group(2)
                        if action == 'diagnose':
                            if set(data) != {'diagnosis'}:
                                raise ValueError('unexpected fields')
                            record = it_ai_manager.diagnose(identity, incident_id, data['diagnosis'])
                            return respond(start, '200 OK', {'incident': record})
                        if action == 'dispatch':
                            if set(data) - {'agent_name', 'task', 'target'} or not {'agent_name', 'task'} <= set(data):
                                raise ValueError('unexpected fields')
                            record = it_ai_manager.dispatch_work_order(identity, incident_id, data['agent_name'], data['task'], target=data.get('target', ''))
                            return respond(start, '201 Created', {'work_order': record})
                        if action == 'rollback':
                            if set(data) != {'reason'}:
                                raise ValueError('unexpected fields')
                            record = it_ai_manager.order_rollback(identity, incident_id, data['reason'])
                            return respond(start, '201 Created', {'work_order': record})
                        if action == 'failover':
                            if set(data) - {'minotaur_decision_ref', 'note'} or 'minotaur_decision_ref' not in data:
                                raise ValueError('unexpected fields')
                            record = it_ai_manager.record_failover(identity, incident_id, data['minotaur_decision_ref'], note=data.get('note', ''))
                            return respond(start, '201 Created', {'work_order': record})
                        if action == 'verify':
                            if set(data) - {'result', 'evidence_ref'} or 'result' not in data:
                                raise ValueError('unexpected fields')
                            record = it_ai_manager.verify_return(identity, incident_id, data['result'], evidence_ref=data.get('evidence_ref', ''))
                            return respond(start, '200 OK', {'incident': record})
                        if set(data) != set():
                            raise ValueError('unexpected fields')
                        record = it_ai_manager.reconcile(identity, incident_id)
                        return respond(start, '200 OK', {'incident': record})
                    if path == '/api/it-ai-manager/evaluations':
                        if set(data) != {'operation', 'target', 'requesting_agent', 'decision', 'rationale'}:
                            raise ValueError('unexpected fields')
                        record = it_ai_manager.evaluate_necessity(identity, **data)
                        return respond(start, '201 Created', {'evaluation': record})
                    if itm_evaluation_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = it_ai_manager.evaluation_view(identity, role, itm_evaluation_match.group(1))
                        return respond(start, '200 OK', {'evaluation': record})
                    if itm_work_order_outcome_match:
                        if set(data) - {'outcome', 'detail'} or 'outcome' not in data:
                            raise ValueError('unexpected fields')
                        record = it_ai_manager.record_outcome(identity, itm_work_order_outcome_match.group(1), data['outcome'], detail=data.get('detail', ''))
                        return respond(start, '200 OK', {'work_order': record})
                    if itm_work_order_match:
                        role = 'OPERATOR' if is_operator() else 'COORDINATOR'
                        record = it_ai_manager.work_order_view(identity, role, itm_work_order_match.group(1))
                        return respond(start, '200 OK', {'work_order': record})
                    return check_in(it_ai_manager)
            if operator_match:
                if set(data) != {'items', 'expires_at'}:
                    raise ValueError('unexpected fields')
                quote = payments.approve_quote(operator_match.group(1), identity, **data)
                return respond(start, '201 Created', {'quote': quote})
            if path == '/api/session':
                return respond(start, '200 OK', {'authenticated': True})
            if path == '/api/appointments':
                if method == 'GET':
                    return respond(start, '200 OK', {'appointments': appointments.list_owned(identity)})
                expected = {'request_id', 'jurisdiction', 'service', 'requested_start', 'meeting_area', 'consent'}
                if set(data) != expected:
                    raise ValueError('unexpected fields')
                record = appointments.request(identity, **data)
                return respond(start, '201 Created', {'appointment': record})

            case_id = case_match.group(1) if case_match is not None else detail_match.group(1)
            record = appointments.get(case_id, identity)
            
            if method == 'GET':
                return respond(start, '200 OK', {
                    'appointment': record,
                    'quote': payments.quote(case_id, identity),
                    'payment': payments.ledger.status(case_id)
                })

            if set(data) != {'quote_id', 'accept_quote'}:
                raise ValueError('unexpected fields')
            result = payments.checkout(case_id, identity, **data)
            return respond(start, '200 OK', result)

        except (BridgeForbidden, FoundationForbidden):
            return respond(start, '403 Forbidden', {'error': 'uncle_nickey_mao_forbidden'})
        except BridgeDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'uncle_nickey_mao_denied', 'detail': str(exc)})
        except CareHiveForbidden:
            return respond(start, '403 Forbidden', {'error': 'carehive_os_forbidden'})
        except CareHiveDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'carehive_os_denied', 'detail': str(exc)})
        except HomeHealthcareForbidden:
            return respond(start, '403 Forbidden', {'error': 'home_healthcare_forbidden'})
        except HomeHealthcareDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'home_healthcare_denied', 'detail': str(exc)})
        except GrantwriterPlatformForbidden:
            return respond(start, '403 Forbidden', {'error': 'grantwriter_forbidden'})
        except GrantwriterPlatformDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'grantwriter_denied', 'detail': str(exc)})
        except PBDValidationForbidden:
            return respond(start, '403 Forbidden', {'error': 'pbd_validation_forbidden'})
        except PBDValidationDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'pbd_validation_denied', 'detail': str(exc)})
        except PBDGeneratorForbidden:
            return respond(start, '403 Forbidden', {'error': 'pbd_manifest_generator_forbidden'})
        except PBDGeneratorDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'pbd_manifest_generator_denied', 'detail': str(exc)})
        except VaultForbidden:
            return respond(start, '403 Forbidden', {'error': 'vault_forbidden'})
        except VaultDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'vault_denied', 'detail': str(exc)})
        except PBDSentinelForbidden:
            return respond(start, '403 Forbidden', {'error': 'pbd_sentinel_forbidden'})
        except PBDSentinelDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'pbd_sentinel_denied', 'detail': str(exc)})
        except ITAIManagerForbidden:
            return respond(start, '403 Forbidden', {'error': 'it_ai_manager_forbidden'})
        except ITAIManagerDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'it_ai_manager_denied', 'detail': str(exc)})
        except RoomNotFound:
            return respond(start, '404 Not Found', {'error': 'not_found'})
        except RoomForbidden:
            return respond(start, '403 Forbidden', {'error': 'room_forbidden'})
        except RoomDenied as exc:
            return respond(start, '400 Bad Request', {'error': 'room_denied', 'detail': str(exc)})
        except BridgeDenied:
            return respond(start, '400 Bad Request', {'error': 'native_session_denied'})
        except AppointmentDenied:
            return respond(start, '400 Bad Request' if path == '/api/appointments' else '404 Not Found', {'error': 'appointment_unavailable'})
        except (ValueError, TypeError, KeyError, CaseDenied):
            return respond(start, '400 Bad Request', {'error': 'invalid_request'})
        except PaymentDenied:
            return respond(start, '409 Conflict', {'error': 'checkout_unavailable'})
        except ProviderUnavailable as exc:
            return respond(start, '503 Service Unavailable', {'error': 'provider_unavailable', 'detail': str(exc)})
        except ProviderRequestConflict:
            return respond(start, '409 Conflict', {'error': 'provider_request_conflict'})
        except PermissionError:
            return respond(start, '403 Forbidden', {'error': 'operator_required'})
        except Exception:
            return respond(start, '503 Service Unavailable', {'error': 'temporarily_unavailable'})

    return app
