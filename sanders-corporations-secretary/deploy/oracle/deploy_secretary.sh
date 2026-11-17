#!/usr/bin/env bash
# Independently deploy only Sanders Corporations Secretary on the existing Oracle Always Free VM.
# The Dash & Seal deployment, database, services and network configuration remain untouched.
set -euo pipefail

COMMIT_SHA="${1:?Pass the GitHub commit SHA}"
[[ "$COMMIT_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected a full Git commit SHA' >&2; exit 2; }

APP_HOME="$HOME/.local/share/sanders-corporations-secretary"
CHECKOUT="$APP_HOME/public-source"
PROJECT="$CHECKOUT/sanders-corporations-secretary"
VENV="$APP_HOME/venv"
DB_DIR="$APP_HOME/state"
CONF_DIR="$HOME/.config/sanders-corporations-secretary"
UNIT_NAME="sanders-corporations-secretary.service"
UNIT_FILE="/etc/systemd/system/$UNIT_NAME"

mkdir -p "$APP_HOME" "$DB_DIR" "$CONF_DIR"
chmod 0700 "$DB_DIR" "$CONF_DIR"

if [[ ! -d "$CHECKOUT/.git" ]]; then
    git clone --no-checkout --filter=blob:none https://github.com/DashandSeal/Sanders_Dash_Seal.git "$CHECKOUT"
fi
# Isolated working copy; never modifies the existing Sanders Dash & Seal checkout.
git -C "$CHECKOUT" fetch --depth 1 origin "$COMMIT_SHA"
git -C "$CHECKOUT" checkout --force --detach "$COMMIT_SHA"

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3,11))'; then
        PYTHON="$candidate"; break
    fi
done
[[ -n "$PYTHON" ]] || { echo 'Python 3.11 or newer must be available on the Oracle VM' >&2; exit 1; }
if [[ ! -x "$VENV/bin/python" ]]; then "$PYTHON" -m venv "$VENV"; fi
"$VENV/bin/python" -m pip install --disable-pip-version-check --quiet -r "$PROJECT/requirements.txt"

# Create the actual owner token on the Oracle VM if one is not already configured.
# Never print it or commit it to GitHub.
if [[ ! -f "$CONF_DIR/runtime.env" ]]; then
    umask 077
    token="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(48))')"
    printf 'SCS_API_TOKEN=%s\n' "$token" > "$CONF_DIR/runtime.env"
    unset token
fi
chmod 0600 "$CONF_DIR/runtime.env"

RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"
# Oracle Linux default SSH users have passwordless sudo. This unit is separate
# and binds only to loopback; public TLS routing is configured independently.
sudo -n tee "$UNIT_FILE" >/dev/null <<UNIT
[Unit]
Description=Sanders Corporations Secretary (Oracle Always Free)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT
EnvironmentFile=$CONF_DIR/runtime.env
Environment=SCS_DB_PATH=$DB_DIR/secretary.sqlite3
ExecStart=$VENV/bin/uvicorn app.main:app --host 127.0.0.1 --port 8791
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
sudo -n systemctl daemon-reload
sudo -n systemctl enable --now "$UNIT_NAME"
sudo -n systemctl restart "$UNIT_NAME"
printf 'Oracle deployment command completed for commit %s; service %s, loopback port 8791.\n' "$COMMIT_SHA" "$UNIT_NAME"
printf 'This step does not establish public DNS, TLS or production hardening; see docs/ORACLE_ALWAYS_FREE_DEPLOYMENT.md.\n'