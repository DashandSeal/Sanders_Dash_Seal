"""Platform-services registry for Sanders Dash & Seal (Phase 2 linker).

One place that names every external platform the deployment touches,
what it needs, what is ready, and what is still missing -- in code, so
``/api/platform/status`` and the checklist doc
(``docs/platform-link-checklist-20261113.md``) can never drift apart
silently.

Platforms covered
-----------------
* **Stripe** -- Checkout + webhook.  Test-mode first: live payments are
  gated by :func:`stripe_live_gate` (``STRIPE_LIVEMODE`` in ``1``/``true``/
  ``yes`` AND ``STRIPE_LIVE_VERIFIED`` in ``1``/``true``/``yes`` -- one
  canonical truthiness, shared with ``wsgi.py`` and
  ``deploy/deployment.py`` since the P3 pass, 2026-11-13).  The webhook
  signing secret is never read, stored, or printed here; the webhook app
  (``core_platform.stripe_webhook_wsgi``) receives it from the caller.
  Ledger handlers in ``wsgi.py`` (``MockLedgerEngine.fulfill_checkout``
  etc.) are **real SQLite-backed methods since the P1 pass (2026-11-13)**:
  they delegate to ``core_platform.stripe_payments.PaymentLedger``.
  That is stated here and in the checklist; payment confirmation still
  does not authorize or execute a notarial act.
* **Oracle Cloud** -- the Always Free instance ``sanders-dash-seal``
  (``129.146.111.166``, ``us-phoenix-1``, tenancy
  ``rooseveltsanders381``).  Facts only; this module makes no OCI call.
  Deploy layout: ``/opt/sanders-dash-seal``, systemd units for gunicorn
  + nginx, env file ``0600``.  Backup policy:
  ``deploy/oracle/backup-policy.md``.
* **GoDaddy DNS** -- both apexes already resolve to the instance IP.
  The one missing record (``www.sanderslegalhelpersllc.com`` A) is
  produced as an exact record dict by :func:`dns_records_to_apply`;
  **this code never changes DNS** -- the owner applies the record in
  GoDaddy (or approves a separate DNS step).
* **GitHub CI / Gateway** -- push-gating + Shape A ``.pbd.json`` pairs.
  Proposed diff only (see the checklist doc); the workflow file
  ``.github/workflows/parallel-build-verification.yml`` is NOT edited
  here.
* **Google services** -- Gmail, Calendar, Docs, Sheets are connected at
  the Muse connector level (per the 2026-11-13 connection record).
  There is **no server-side Google integration in this repo**, and none
  is invented here.  :func:`google_service_links` lists only the three
  legitimate uses (notifications, scheduling, record-keeping) with
  status ``muse_connected_no_server_integration``.

No secrets: every function reports *presence* (set/unset), never values.
No network calls, no spend, no deploy, no merge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Verified facts (from the 2026-11-13 live checks; re-verify live before deploy)
# ---------------------------------------------------------------------------

ORACLE_INSTANCE = {
    "name": "sanders-dash-seal",
    "public_ip": "129.146.111.166",
    "private_ip": "10.0.0.175",
    "shape": "VM.Standard.A1.Flex",
    "ocpus": 1,
    "memory_gb": 6,
    "os": "Oracle Linux 9",
    "region": "us-phoenix-1",
    "tenancy": "rooseveltsanders381",
    "boot_volume": "sanders-dash-seal",
    "boot_volume_gb": 47,
    "cost_2026_11_01_to_13_usd": 0.00,
    "state": "Running",
    "code_deployed": False,  # instance serves nothing on HTTP/HTTPS (curl 000)
    "ssh": "blocked by egress proxy (this assistant); owner path: unblock SSH",
}

DNS_APEX_IP = "129.146.111.166"

DEPLOY_ROOT = "/opt/sanders-dash-seal"

LEDGER_STUB_WARNING = (
    "Ledger handlers are real since the P1 pass (2026-11-13): "
    "wsgi.MockLedgerEngine delegates fulfill_checkout / "
    "record_subscription_renewal / process_reversal to the SQLite-backed "
    "core_platform.stripe_payments.PaymentLedger (idempotent, durable). "
    "Payment confirmation still does not authorize or execute a notarial "
    "act. Test mode is the default; live requires STRIPE_LIVEMODE=1 AND "
    "STRIPE_LIVE_VERIFIED=1."
)


# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StripeLink:
    """Stripe link state, from environment presence only."""

    secret_key_set: bool
    webhook_secret_set: bool
    livemode_requested: bool
    live_verified: bool
    test_mode: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "StripeLink":
        src = os.environ if env is None else env
        # P3 (2026-11-13): canonical truthiness, shared with wsgi.py
        # (_env_truthy) and deploy/deployment.py: "1", "true" or "yes"
        # (case-insensitive, whitespace-tolerant). Previously this
        # reader accepted "true" only, so STRIPE_LIVEMODE=1 reported
        # test mode here while the webhook app ran live -- the two
        # readers disagreed about the same environment.
        livemode = (src.get("STRIPE_LIVEMODE") or "").strip().lower() in (
            "1", "true", "yes")
        live_verified = (src.get("STRIPE_LIVE_VERIFIED") or "").strip().lower() in (
            "1", "true", "yes")
        return cls(
            secret_key_set=bool((src.get("STRIPE_SECRET_KEY") or "").strip()),
            webhook_secret_set=bool((src.get("STRIPE_WEBHOOK_SECRET") or "").strip()),
            livemode_requested=livemode,
            live_verified=live_verified,
            test_mode=not livemode,
        )

    @property
    def configured_for_test(self) -> bool:
        """Test-mode Checkout/webhook can run when both secrets are set."""
        return self.secret_key_set and self.webhook_secret_set and self.test_mode

    def status(self) -> dict[str, Any]:
        return {
            "provider": "stripe",
            "test_mode": self.test_mode,
            "secret_key_set": self.secret_key_set,
            "webhook_secret_set": self.webhook_secret_set,
            "livemode_requested": self.livemode_requested,
            "live_verified": self.live_verified,
            "live_allowed": stripe_live_gate(self),
            "ledger_handlers": "real SQLite-backed PaymentLedger methods (P1 2026-11-13)",
            "note": (
                "Test-mode first. Webhook signing secret must come via the "
                "secure flow; it is never stored in code or in this status."
            ),
        }


def stripe_live_gate(link: StripeLink) -> bool:
    """True only when live mode is explicitly requested AND verifier-approved.

    Both ``STRIPE_LIVEMODE`` and ``STRIPE_LIVE_VERIFIED`` must be set
    to one of ``1``/``true``/``yes`` (canonical truthiness, P3
    2026-11-13, shared with ``wsgi.py``).  Anything else is test-mode.
    This gate does not move money itself; it is the check the webhook
    app / deploy step must consult before enabling live payments.
    """
    return bool(link.livemode_requested and link.live_verified)


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------


def oracle_status() -> dict[str, Any]:
    """Static Oracle facts + deploy layout.  Makes no OCI call."""
    return {
        "provider": "oracle",
        "instance": dict(ORACLE_INSTANCE),
        "deploy_root": DEPLOY_ROOT,
        "layout": {
            "app": DEPLOY_ROOT + "/src",
            "env_file": DEPLOY_ROOT + "/.env (0600, all keys UNSET until owner fills)",
            "systemd": ["sanders-dash-seal.service (gunicorn)", "nginx.service"],
            "web_server": "nginx 1.25-alpine pinned in compose.yaml / docker-compose.yml on this branch (1.25 EOL May 2024; SOTA branch moved to 1.30.6-alpine, unmerged)",
            "app_server": "gunicorn 27.0.1, 127.0.0.1:8000, timeout 75 (this branch; the simultaneous package used 90)",
        },
        "backup_policy": "deploy/oracle/backup-policy.md",
        "blocker": "SSH from this assistant is blocked by the egress proxy; no code deployed",
    }


# ---------------------------------------------------------------------------
# GoDaddy DNS (records to apply -- this code never applies them)
# ---------------------------------------------------------------------------


def dns_records_to_apply() -> list[dict[str, str]]:
    """Exact DNS records for the owner to apply in GoDaddy.

    The two apex A records already resolve (verified 2026-11-13 via DoH);
    they are listed so the desired end state is explicit.  The
    ``www.sanderslegalhelpersllc.com`` record is missing (NXDOMAIN) and
    is the only change needed.  No DNS mutation is performed by this
    code or any code in this branch.
    """
    return [
        {
            "host": "@",
            "domain": "sandersdashandseal.com",
            "type": "A",
            "value": DNS_APEX_IP,
            "ttl": "600",
            "state": "already_set_verified_2026_11_13",
        },
        {
            "host": "@",
            "domain": "sanderslegalhelpersllc.com",
            "type": "A",
            "value": DNS_APEX_IP,
            "ttl": "600",
            "state": "already_set_verified_2026_11_13",
        },
        {
            "host": "www",
            "domain": "sanderslegalhelpersllc.com",
            "type": "A",
            "value": DNS_APEX_IP,
            "ttl": "600",
            "state": "MISSING_NXDOMAIN_apply_in_godaddy",
        },
        {
            "host": "www",
            "domain": "sandersdashandseal.com",
            "type": "A",
            "value": DNS_APEX_IP,
            "ttl": "600",
            "state": "already_set_verified_2026_11_13",
        },
    ]


def dns_status() -> dict[str, Any]:
    missing = [r for r in dns_records_to_apply() if r["state"].startswith("MISSING")]
    return {
        "provider": "godaddy_dns",
        "apex_ip": DNS_APEX_IP,
        "records": dns_records_to_apply(),
        "missing_records": len(missing),
        "action_required": (
            "Add A record www -> %s on sanderslegalhelpersllc.com in GoDaddy DNS. "
            "This code does not change DNS." % DNS_APEX_IP
        ) if missing else "none",
    }


# ---------------------------------------------------------------------------
# GitHub CI / Gateway (proposed diff only -- workflow file NOT edited)
# ---------------------------------------------------------------------------


def gateway_status() -> dict[str, Any]:
    """Gateway state as known on 2026-11-13.  No workflow file is read or edited here."""
    return {
        "provider": "github_actions_gateway",
        "workflow": ".github/workflows/parallel-build-verification.yml",
        "failing_step": "Securely Push Verified Manifest Assets (exit 128)",
        "cause": (
            "Step pushes to main from PR runs and the sync step writes Shape B "
            "pairs (bare sha256, no payload_hash/signatures/status); canonical "
            "format is Shape A (payload_hash, signatures {}, "
            "status UNSIGNED_SOURCE_MANIFEST)."
        ),
        "fix": "PROPOSED DIFF ONLY -- see docs/platform-link-checklist-20261113.md § GitHub. "
               "Gate the push step to push events (if: github.event_name == 'push'), "
               "emit Shape A pairs, remove auto-push to main from PR runs.",
        "workflow_file_edited": False,
        "blocker": "Workflow-file read did not pass a safety check on 2026-11-13; "
                   "needs a clean read + fresh approval before any edit.",
        "pair_format": "Shape A / UNSIGNED_SOURCE_MANIFEST",
    }


# ---------------------------------------------------------------------------
# Google services (Muse-connected; no server-side integration invented)
# ---------------------------------------------------------------------------


def google_service_links() -> dict[str, Any]:
    """Legitimate Google uses only.  No server-side integration exists in-repo."""
    return {
        "provider": "google",
        "connection": "muse_connected_no_server_integration",
        "accounts_connected_2026_11_13": [
            "Gmail", "Google Calendar", "Google Docs", "Google Sheets",
        ],
        "uses": [
            {
                "service": "Gmail",
                "use": "Owner notifications (deploy results, payment alerts) via the connected Gmail account.",
                "server_integration": "none -- notification sending is a Muse-level action, not an app endpoint",
            },
            {
                "service": "Google Calendar",
                "use": "Scheduling notarial / appointment sessions created by the app.",
                "server_integration": "none -- no calendar write path exists in-repo",
            },
            {
                "service": "Google Docs / Sheets",
                "use": "Record-keeping: exportable reports and ledgers for the owner.",
                "server_integration": "none -- no Docs/Sheets write path exists in-repo",
            },
        ],
        "not_invented": "No Google OAuth flow, API client, or credential is added by this branch.",
    }


# ---------------------------------------------------------------------------
# Combined status (single source for /api/platform/status + checklist doc)
# ---------------------------------------------------------------------------


def platform_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Combined per-platform status.  Presence flags only; no secret values."""
    from .livekit_realtime import RealtimeConfig

    stripe = StripeLink.from_env(env)
    return {
        "platform": "Sanders Dash & Seal",
        "ledger_stub_warning": LEDGER_STUB_WARNING,
        "stripe": stripe.status(),
        "oracle": oracle_status(),
        "dns": dns_status(),
        "github_gateway": gateway_status(),
        "google": google_service_links(),
        "realtime": RealtimeConfig.from_env(env).status(),
        "deploy_blockers": [
            "SSH blocked by egress proxy (no code deployed to Oracle)",
            "Gateway workflow exit 128 (proposed fix only, not applied)",
            "Stripe ledger handlers are real SQLite-backed methods (P1); no code is deployed to Oracle yet",
            "www.sanderslegalhelpersllc.com DNS record missing (NXDOMAIN)",
            "No signalling server / SFU running (no live video call yet)",
        ],
    }
