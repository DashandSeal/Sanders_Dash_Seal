#!/usr/bin/env bash
# Sanders Dash & Seal — direct deploy to Oracle Always Free (NO Docker).
#
# Replaces deploy.sh, which is truncated (main() never closes, no invocation)
# and Docker/compose-based. Run ON the instance as root, with the extracted
# deploy package present:
#   tar xzf sanders-dash-seal-oracle-deploy-20261113.tar.gz
#   sudo bash sanders-dash-seal-oracle-deploy-20261113/deploy/install-oracle.sh \
#        sanders-dash-seal-oracle-deploy-20261113/src
#
# What it does: installs python3.12 + nginx + node, creates the sds user
# (uid 10001, matching deploy/gunicorn.conf.py), stages the app at
# /opt/sanders-dash-seal, builds a venv from requirements.txt, installs the
# Node worker deps, installs systemd units + the fixed nginx config, opens
# firewall ports 80/443, starts everything, and runs a local smoke test.
# What it does NOT do: no Stripe live charges, no secrets are created or
# stored (STRIPE_WEBHOOK_SECRET is an owner-filled placeholder only),
# no TLS certificate (needs DNS + certbot, see README), no Daedalus/Claude
# key, no spending.
set -euo pipefail

PKG_SRC="${1:-$(pwd)/src}"
SDS_DIR=/opt/sanders-dash-seal
SDS_USER=sds
SDS_UID=10001
ENV_FILE=/etc/sanders-dash-seal/env
SMOKE_LOG=/var/log/sds-install-smoke.log

fail() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "-- $*"; }

[[ "$EUID" == 0 ]] || fail "run as root (sudo)."
[[ -f "$PKG_SRC/wsgi.py" ]] || fail "package src not found at $PKG_SRC (expected wsgi.py there)."
grep -q 'ID="ol"' /etc/os-release 2>/dev/null || note "WARNING: not Oracle Linux (os-release ID != ol); continuing anyway."

# --- 1. Packages ------------------------------------------------------------
note "Installing system packages (python3.12, nginx, node, firewalld)..."
dnf install -y python3.12 python3.12-pip nginx firewalld policycoreutils-python-utils git nodejs 2>&1 | tail -2
command -v python3.12 >/dev/null || fail "python3.12 not available from AppStream; install a Python >= 3.9 first."
python3.12 --version

# Node worker requires >= 20. If the distro node is older, the worker is
# skipped (nginx /ws/ and telemetry will 502) and the rest still deploys.
WORKER_OK=1
if command -v node >/dev/null; then
    NODE_MAJOR=$(node --version | sed 's/^v//; s/\..*//')
    if [[ "$NODE_MAJOR" -lt 20 ]]; then
        note "WARNING: node $(node --version) < 20; sds-worker will NOT be started."
        WORKER_OK=0
    fi
else
    note "WARNING: node not installed; sds-worker will NOT be started."
    WORKER_OK=0
fi

# --- 2. Service user ---------------------------------------------------------
if ! id "$SDS_USER" >/dev/null 2>&1; then
    useradd --uid "$SDS_UID" --gid "$SDS_UID" --no-create-home --shell /sbin/nologin "$SDS_USER" 2>/dev/null \
        || { groupadd --gid "$SDS_UID" sds; useradd --uid "$SDS_UID" --gid "$SDS_UID" --no-create-home --shell /sbin/nologin "$SDS_USER"; }
fi

# --- 3. Stage the app --------------------------------------------------------
note "Staging app to $SDS_DIR ..."
mkdir -p "$SDS_DIR"
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
    --exclude 'data/ledger.db*' "$PKG_SRC/" "$SDS_DIR/"
mkdir -p "$SDS_DIR/data" /etc/sanders-dash-seal /srv/sds/status
chown -R "$SDS_USER:$SDS_USER" "$SDS_DIR"
chmod 0755 "$SDS_DIR"

# --- 4. Python venv ----------------------------------------------------------
note "Building venv and installing requirements.txt ..."
python3.12 -m venv "$SDS_DIR/.venv"
"$SDS_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SDS_DIR/.venv/bin/pip" install --quiet -r "$SDS_DIR/requirements.txt"
"$SDS_DIR/.venv/bin/pip" list 2>/dev/null | grep -i -E 'stripe|PyJWT|gunicorn|cryptography' || true

# --- 5. Node worker ----------------------------------------------------------
if [[ "$WORKER_OK" == 1 ]]; then
    note "Installing Node worker deps (npm ci) ..."
    (cd "$SDS_DIR/worker" && npm ci --omit=dev 2>&1 | tail -2)
    chown -R "$SDS_USER:$SDS_USER" "$SDS_DIR/worker"
else
    note "Skipping Node worker install (node < 20 or missing)."
fi

# --- 6. Env file (placeholder only, never a real secret) ---------------------
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<'EOF'
# Sanders Dash & Seal runtime environment (owner fills in real values).
# STRIPE_WEBHOOK_SECRET is required for real Stripe webhooks; without it the
# webhook app runs with its built-in test placeholder and rejects live events.
# STRIPE_WEBHOOK_SECRET=whsec_...
EOF
    chmod 0600 "$ENV_FILE"
    chown root:root "$ENV_FILE"
fi

# --- 7. systemd units --------------------------------------------------------
note "Installing systemd units ..."
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
install -m 0644 "$SCRIPT_DIR/sds-webhook.service" /etc/systemd/system/sds-webhook.service
install -m 0644 "$SCRIPT_DIR/sds-api.service" /etc/systemd/system/sds-api.service
if [[ "$WORKER_OK" == 1 ]]; then
    install -m 0644 "$SCRIPT_DIR/sds-worker.service" /etc/systemd/system/sds-worker.service
fi
systemctl daemon-reload
systemctl enable --now sds-webhook.service sds-api.service
if [[ "$WORKER_OK" == 1 ]]; then
    systemctl enable --now sds-worker.service
fi

# --- 8. nginx + firewall -----------------------------------------------------
note "Installing fixed nginx config ..."
cp -a /etc/nginx/nginx.conf "/etc/nginx/nginx.conf.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
cp "$SCRIPT_DIR/nginx.oracle.conf" /etc/nginx/nginx.conf
nginx -t
systemctl enable --now nginx
# SELinux: allow nginx to proxy to loopback upstreams.
setsebool -P httpd_can_network_connect 1 2>/dev/null || note "WARNING: setsebool failed (SELinux may block proxying; check audit log)."
systemctl enable --now firewalld 2>/dev/null || true
firewall-cmd --permanent --add-service=http --add-service=https 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true
# OCI security list / NSG must also allow 80/443 — check in the OCI console.

# --- 9. Smoke test (local, no Stripe, no secrets) ---------------------------
note "Smoke test (results in $SMOKE_LOG) ..."
sleep 3
{
    echo "== $(date -u +%FT%TZ) sds install smoke test =="
    echo "-- systemctl --"
    systemctl is-active sds-webhook.service sds-api.service nginx || true
    [[ "$WORKER_OK" == 1 ]] && systemctl is-active sds-worker.service || echo "sds-worker: skipped (node < 20)"
    echo "-- HTTP via nginx :80 --"
    echo -n "GET  /healthz: "; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/healthz
    echo -n "GET  /v1/payments/stripe/webhook: "; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/v1/payments/stripe/webhook
    echo -n "POST /v1/payments/stripe/webhook (no sig): "; curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1/v1/payments/stripe/webhook
    echo -n "POST /api/auth/verify: "; curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1/api/auth/verify
    echo -n "POST /api/stream/transactions (public IP, expect 403): "; curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1/api/stream/transactions
    echo -n "GET  /landing: "; curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: sandersdashandseal.com' -H 'X-Forwarded-Proto: https' http://127.0.0.1/landing
} | tee "$SMOKE_LOG"

echo
echo "DONE. Expected: healthz 200, webhook GET 405, webhook POST 401,"
echo "api/auth/verify 503 (diagnostic mode), stream/transactions 403 (private route),"
echo "landing 200. Anything else: check 'systemctl status sds-*' and 'journalctl -u sds-webhook -n 50'."
echo "NEXT: set STRIPE_WEBHOOK_SECRET in $ENV_FILE, point DNS at this instance,"
echo "then run certbot and append nginx.oracle-443-snippet.conf (see README)."
