#!/usr/bin/env bash
# sds_env_guard.sh — conditional environment repair for the Sanders
# Dash & Seal app, run at every app service start.
#
# Owner decision (2026-11-23): the full self-repair layer's playbook
# repairs run autonomously; secrets, gates, and money are NEVER
# automated. This guard is the environment entry of that playbook
# (class P1 in deploy/sds_repair.sh). Its one job: make sure
# /etc/sanders-dash-seal/runtime.env exists and carries a
# shape-valid STRIPE_WEBHOOK_SECRET before gunicorn starts, because
# wsgi.py raises WebhookConfigurationError at import when the secret
# is unset — the missing-file failure that took the site down on
# 2026-11-23 (deploy_all runs #101/#102/#103).
#
# Behavior:
#   * If runtime.env exists AND a line matches the whsec_ shape (the
#     same shape pattern the deploy preflight uses), exit 0 and do
#     nothing. This is the normal path: the guard costs one grep.
#   * Otherwise, regenerate runtime.env from the owner's OCI Vault
#     secret (sds-runtime-provider-config) by running the repo's own
#     refresh path, deploy/refresh_provider_secrets.py, exactly as
#     that script requires: as root, no arguments except that
#     --restart is deliberately NOT passed (its restart path drives
#     docker compose, which is not how this instance runs the app;
#     systemd restarts the unit itself). The refresh script reads the
#     compartment id from /etc/sanders-dash-seal/release.json, pulls
#     the CURRENT secret bundle with instance_principal auth, and
#     writes ONLY STRIPE_WEBHOOK_SECRET into runtime.env (root:root,
#     0600, atomic) — and only when the vault config actually carries
#     a webhook secret; otherwise it leaves any existing file
#     untouched.
#   * After the refresh attempt, re-check the shape. Exit 0 only if a
#     shape-valid file now exists; exit 1 otherwise.
#
# HARD BOUNDARIES (owner's words, 2026-11-23 — secrets, gates, and
# money always stay the owner's):
#   * This guard NEVER creates, rotates, or guesses a secret value.
#     The only source it will ever use is the owner's existing OCI
#     Vault secret, re-fetched unchanged. If the vault yields nothing
#     shape-valid, any existing runtime.env is left untouched and the
#     guard fails loudly (logger -t sds-env-guard + exit 1).
#   * The secret value is never printed, logged, or copied anywhere.
#     Every check below is shape-only (grep -q / exit codes).
#   * It never approves a gate, never touches Stripe settings,
#     payments, or money, and never edits the repository.
#
# Why the exit code is not trusted on its own: refresh_provider_
# secrets.py exits 0 with PROVIDER_SECRET_NOT_CONFIGURED when the
# vault holds no matching secret, and can exit 1 (settings-file step)
# AFTER it has already written a valid runtime.env. The only
# trustworthy signal is the file's shape afterwards, so that is what
# this guard checks. The refresh script's own status token
# (PROVIDER_SECRET_REFRESHED / _UNCHANGED / _NOT_CONFIGURED /
# _REFRESH_FAILED) carries no secret material by that script's
# design and is logged for diagnosis.
#
# Wiring: deploy/sanders-dash-seal.service runs this as
#   ExecStartPre=-+/usr/local/sbin/sds_env_guard.sh
# The "-" prefix means a guard failure never blocks the start
# attempt — the app and the deploy preflight surface the real state.
# The "+" prefix runs it as root even though the unit's user is
# sanders: the refresh requires euid 0 and runtime.env is root-owned.
# It is placed BEFORE the unit's stale-gunicorn pkill ExecStartPre so
# the port-clearing step stays immediately before ExecStart (the
# vault refresh can take some seconds when the network is slow; the
# kill should be the last thing that happens before gunicorn binds).
# Installed by deploy/deploy_all.sh (step 5c) to
# /usr/local/sbin/sds_env_guard.sh; the repo copy is
# deploy/sds_env_guard.sh.
set -u

RUNTIME_ENV="/etc/sanders-dash-seal/runtime.env"
REPO_DIR="${SDS_REPO_DIR:-/opt/Sanders_Dash_Seal}"
REFRESH_SCRIPT="$REPO_DIR/deploy/refresh_provider_secrets.py"
# Same shape pattern as the deploy preflight (deploy_all.sh step 2b):
# a STRIPE_WEBHOOK_SECRET line whose value starts with whsec_.
SHAPE_RE='^[[:space:]]*STRIPE_WEBHOOK_SECRET=whsec_'

log_msg() {
  local msg="$1"
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') sds-env-guard: $msg"
  logger -t sds-env-guard -- "$msg" 2>/dev/null || true
}

env_shape_ok() {
  [ -f "$RUNTIME_ENV" ] && grep -Eq "$SHAPE_RE" "$RUNTIME_ENV" 2>/dev/null
}

main() {
  if env_shape_ok; then
    log_msg "OK: $RUNTIME_ENV present and STRIPE_WEBHOOK_SECRET has the whsec_ shape; nothing to do"
    exit 0
  fi

  if [ "$(id -u)" != "0" ]; then
    log_msg "ERROR: $RUNTIME_ENV is missing or shape-invalid and the Vault refresh requires root; run as root (the app unit runs this guard with the systemd '+' prefix)"
    exit 1
  fi
  if [ ! -f "$REFRESH_SCRIPT" ]; then
    log_msg "ERROR: $RUNTIME_ENV is missing or shape-invalid and the refresh script $REFRESH_SCRIPT is not present in the checkout; cannot regenerate from the Vault"
    exit 1
  fi
  local python3_bin=""
  python3_bin="$(command -v python3 || true)"
  if [ -z "$python3_bin" ] && [ -x /usr/bin/python3 ]; then
    python3_bin="/usr/bin/python3"
  fi
  if [ -z "$python3_bin" ]; then
    log_msg "ERROR: python3 not found; cannot run the Vault refresh for $RUNTIME_ENV"
    exit 1
  fi

  log_msg "runtime.env missing or STRIPE_WEBHOOK_SECRET not whsec_-shaped; regenerating from the OCI Vault via $REFRESH_SCRIPT (re-fetch only — no secret is created, rotated, or guessed)"
  local token=""
  token="$("$python3_bin" "$REFRESH_SCRIPT" 2>/dev/null || true)"
  case "$token" in
    PROVIDER_SECRET_*) log_msg "Vault refresh reported: $token" ;;
    *) log_msg "Vault refresh produced no status token (script error or missing /etc/sanders-dash-seal/release.json)" ;;
  esac

  if env_shape_ok; then
    log_msg "OK: $RUNTIME_ENV now carries a whsec_-shaped STRIPE_WEBHOOK_SECRET after the Vault refresh"
    exit 0
  fi
  log_msg "ERROR: $RUNTIME_ENV is still missing or shape-invalid after the Vault refresh; leaving any existing file untouched. Owner step: confirm the Vault secret sds-runtime-provider-config holds the current provider config (including stripe_webhook_secret) and that /etc/sanders-dash-seal/release.json names its compartment"
  exit 1
}

main "$@"
