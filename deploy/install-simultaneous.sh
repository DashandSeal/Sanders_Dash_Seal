#!/usr/bin/env bash
# Sanders Dash & Seal — SIMULTANEOUS one-run install (2026-11-13).
#
# Run ON the Oracle instance as root, with this package extracted:
#   tar xzf sanders-dash-seal-simultaneous-20261113.tar.gz
#   sudo bash sanders-dash-seal-simultaneous-20261113/install-simultaneous.sh \
#        sanders-dash-seal-simultaneous-20261113
# (The first argument is the extracted package dir; it must contain
#  src/wsgi.py and deploy/nginx.conf. Defaults to the current directory.)
#
# What it does, in one run:
#   1. Creates user/group `sanders` uid/gid 10001.
#   2. Installs the app to /opt/sanders-dash-seal (rsync from src/).
#   3. Creates a python3.12 venv and pip installs requirements.txt.
#   4. Installs the Node worker deps with `npm ci` (only if node >= 20).
#   5. Places the env template at /etc/sanders-dash-seal/environment
#      (0600, root:sanders) ONLY if it does not already exist — ALL KEYS
#      UNSET (STRIPE_WEBHOOK_SECRET, ANTHROPIC_API_KEY,
#      DAEDALUS_CLAUDE_MODEL empty). No secret is created or stored.
#   6. Installs systemd units (sanders-dash-seal + sds-worker if node OK)
#      and deploy/nginx.conf, runs `nginx -t`, enables + starts everything.
#   7. Starts gunicorn on 127.0.0.1:8000 (via the systemd unit) and runs
#      a local smoke check through nginx on :80.
#
# What it does NOT do: no live Claude, no live Stripe, no TLS certificate
# (needs DNS + certbot; see deploy/nginx-443-snippet.conf), no domain
# setup, no spending, no secrets. The ONLY remaining step before this
# script can run is SSH access to the instance (see README.md).
set -euo pipefail

PKG="${1:-$(pwd)}"
# Allow running from inside the extracted dir (src/ is a sibling) or
# passing the dir that already IS the src tree.
if [[ ! -f "$PKG/src/wsgi.py" && -f "$PKG/wsgi.py" ]]; then
  PKG_SRC="$PKG"; PKG_DEPLOY="$PKG/deploy"
elif [[ -f "$PKG/src/wsgi.py" ]]; then
  PKG_SRC="$PKG/src"; PKG_DEPLOY="$PKG/deploy"
else
  echo "ERROR: package not found at $PKG (expected src/wsgi.py there)." >&2
  exit 1
fi
[[ -f "$PKG_DEPLOY/nginx.conf" ]] || { echo "ERROR: $PKG_DEPLOY/nginx.conf missing." >&2; exit 1; }

SDS_DIR=/opt/sanders-dash-seal
SDS_USER=sanders
SDS_UID=10001
ENV_FILE=/etc/sanders-dash-seal/environment
SMOKE_LOG=/var/log/sds-simultaneous-install.log

fail() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "-- $*"; }

[[ "$EUID" == 0 ]] || fail "run as root (sudo)."
grep -q 'ID="ol"' /etc/os-release 2>/dev/null || note "WARNING: not Oracle Linux (os-release ID != ol); continuing anyway."

# --- 1. System packages ------------------------------------------------------
note "Installing system packages (python3.12, nginx, node, firewalld)..."
dnf install -y python3.12 python3.12-pip nginx firewalld policycoreutils-python-utils git nodejs rsync 2>&1 | tail -2
command -v python3.12 >/dev/null || fail "python3.12 not available from AppStream; install a Python >= 3.9 first."
python3.12 --version

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

# --- 2. Service user/group ---------------------------------------------------
if ! getent group "$SDS_USER" >/dev/null; then
  groupadd --gid "$SDS_UID" "$SDS_USER"
fi
if ! id "$SDS_USER" >/dev/null 2>&1; then
  useradd --uid "$SDS_UID" --gid "$SDS_UID" --no-create-home --shell /sbin/nologin "$SDS_USER"
fi
id "$SDS_USER"

# --- 3. Stage the app --------------------------------------------------------
note "Staging app to $SDS_DIR ..."
mkdir -p "$SDS_DIR"
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
  --exclude 'data/ledger.db*' "$PKG_SRC/" "$SDS_DIR/"
# The systemd unit runs gunicorn with --config deploy/gunicorn.conf.py from
# $SDS_DIR, so the authoritative packaged copy (timeout 90, above nginx's
# 75s max gunicorn-route read timeout) must win over the older copy that
# ships inside src/deploy/ (which had timeout 30 and caused 502s).
cp "$PKG_DEPLOY/gunicorn.conf.py" "$SDS_DIR/deploy/gunicorn.conf.py"
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
if [[ "$WORKER_OK" == 1 && -f "$SDS_DIR/worker/package.json" ]]; then
  note "Installing Node worker deps (npm ci) ..."
  (cd "$SDS_DIR/worker" && npm ci --omit=dev 2>&1 | tail -2)
  chown -R "$SDS_USER:$SDS_USER" "$SDS_DIR/worker"
else
  note "Skipping Node worker install (node < 20, missing, or no worker/package.json)."
  WORKER_OK=0
fi

# --- 6. Env file (template only, all keys UNSET, never a real secret) --------
if [[ ! -f "$ENV_FILE" ]]; then
  install -d -m 0750 -o root -g "$SDS_USER" /etc/sanders-dash-seal
  install -m 0600 -o root -g "$SDS_USER" "$PKG_DEPLOY/environment.example" "$ENV_FILE"
  note "Env template installed at $ENV_FILE (0600, all keys UNSET — owner fills in real values)."
else
  note "Env file already exists at $ENV_FILE — left untouched."
  chmod 0600 "$ENV_FILE" || true
fi

# --- 7. systemd units --------------------------------------------------------
note "Installing systemd units ..."
install -m 0644 "$PKG_DEPLOY/sanders-dash-seal.service" /etc/systemd/system/sanders-dash-seal.service
if [[ "$WORKER_OK" == 1 ]]; then
  install -m 0644 "$PKG_DEPLOY/sds-worker.service" /etc/systemd/system/sds-worker.service
fi
systemctl daemon-reload
systemctl enable --now sanders-dash-seal.service
if [[ "$WORKER_OK" == 1 ]]; then
  systemctl enable --now sds-worker.service
fi

# --- 8. nginx + firewall -----------------------------------------------------
note "Installing nginx config ..."
cp -a /etc/nginx/nginx.conf "/etc/nginx/nginx.conf.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
cp "$PKG_DEPLOY/nginx.conf" /etc/nginx/nginx.conf
nginx -t
systemctl enable --now nginx
setsebool -P httpd_can_network_connect 1 2>/dev/null || note "WARNING: setsebool failed (SELinux may block proxying; check audit log)."
systemctl enable --now firewalld 2>/dev/null || true
firewall-cmd --permanent --add-service=http --add-service=https 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true
# OCI security list / NSG must also allow 80/443 — check in the OCI console.

# --- 9. Smoke test (local, no Stripe, no secrets) ----------------------------
note "Smoke test (results in $SMOKE_LOG) ..."
sleep 3
{
  echo "== $(date -u +%FT%TZ) simultaneous install smoke test =="
  echo "-- systemctl --"
  systemctl is-active sanders-dash-seal.service nginx || true
  [[ "$WORKER_OK" == 1 ]] && systemctl is-active sds-worker.service || echo "sds-worker: skipped (node < 20 or no worker)"
  echo "-- HTTP via nginx :80 --"
  echo -n "GET  /: "; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
  echo -n "GET  /healthz: "; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/healthz
  echo -n "GET  /api/voice/status: "; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/api/voice/status
  echo -n "POST /v1/payments/stripe/webhook (no sig, no secret set -> 503 disabled): "
  curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1/v1/payments/stripe/webhook
} | tee "$SMOKE_LOG"

echo
echo "DONE. Expected: homepage 200, /healthz 200, /api/voice/status 200,"
echo "webhook POST with no secret set 503 webhook_gateway_disabled."
echo "(With a test STRIPE_WEBHOOK_SECRET set, unsigned webhook POST is 401 —"
echo " see smoke-test-simultaneous.sh, which tests exactly that locally.)"
echo "NEXT: set real values in $ENV_FILE, point DNS at this instance,"
echo "then run certbot and append deploy/nginx-443-snippet.conf (see README)."
