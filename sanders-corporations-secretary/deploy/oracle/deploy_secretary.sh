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
SVC_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$SVC_DIR/$UNIT_NAME"

mkdir -p "$APP_HOME" "$DB_DIR" "$CONF_DIR" "$SVC_DIR"
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

# Syntax-check the app with the venv interpreter before the service starts,
# so a broken file fails the deploy with its real error instead of a service
# that never answers.
echo "Syntax-checking Secretary app..."
"$VENV/bin/python" -m compileall -q "$PROJECT/app" || {
    echo "Syntax check failed for the Secretary app; see above." >&2
    exit 1
}

# Create the actual owner token on the Oracle VM if one is not already configured.
# Never print it or commit it to GitHub.
if [[ ! -f "$CONF_DIR/runtime.env" ]]; then
    umask 077
    token="$($VENV/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
    printf 'SCS_API_TOKEN=%s\n' "$token" > "$CONF_DIR/runtime.env"
    unset token
fi
chmod 0600 "$CONF_DIR/runtime.env"

# Retire the old system service first: under SELinux (Enforcing) it cannot
# execute the venv under $HOME (203/EXEC, "Permission denied") and keeps
# restarting in a loop. The user service below replaces it on the same port.
if [[ -f "/etc/systemd/system/$UNIT_NAME" ]]; then
    sudo -n systemctl disable --now "$UNIT_NAME" 2>/dev/null || true
    sudo -n rm -f "/etc/systemd/system/$UNIT_NAME"
    sudo -n systemctl daemon-reload 2>/dev/null || true
fi
# This unit is a systemd USER service (like TwoStep/Judge), not a system
# service: the user manager runs unconfined, so it can execute the venv.
# It binds only to loopback; public TLS routing is configured independently.
cat > "$UNIT_FILE" <<UNIT
[Unit]
Description=Sanders Corporations Secretary (Oracle Always Free)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT
EnvironmentFile=$CONF_DIR/runtime.env
Environment=SCS_DB_PATH=$DB_DIR/secretary.sqlite3
ExecStart=$VENV/bin/uvicorn app.main:app --host 127.0.0.1 --port 8791
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
UNIT
# Keep the opc user manager alive after the SSH session that deployed this
# ends; without this, systemd stops user units at logout. Ignore failure if
# the privilege is unavailable in this session.
loginctl enable-linger opc 2>/dev/null || loginctl enable-linger 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"

# Capture the real startup output: run the entrypoint briefly on a test
# loopback port (8792, never the service port) with the unit's own
# environment, so an import/startup crash shows its actual error instead
# of silence. The timeout kill is expected.
echo "Probing Secretary entrypoint briefly to capture startup output..."
( set -a; . "$CONF_DIR/runtime.env"; set +a
  cd "$PROJECT"
  SCS_DB_PATH="$DB_DIR/secretary.sqlite3" timeout 8 "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8792 > /tmp/scs-startup.log 2>&1
) || true

systemctl --user restart "$UNIT_NAME"
printf 'Oracle deployment command completed for commit %s; service %s, loopback port 8791.\n' "$COMMIT_SHA" "$UNIT_NAME"
printf 'This step does not establish public DNS, TLS or production hardening; see docs/ORACLE_ALWAYS_FREE_DEPLOYMENT.md.\n'

# Loopback check: something must answer on 8791. No route is assumed, so any
# HTTP response counts; only a refused connection fails the deploy.
# curl prints 000 itself on a refused connection, so no fallback is needed:
# an `|| echo 000` fallback would append a second 000, making "000000" and
# silently defeating the check below. Retry briefly: a single immediate curl
# can miss startup.
code="000"
for attempt in 1 2 3 4 5; do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8791/" || true)"
    if [[ "$code" != "000" ]]; then
        break
    fi
    sleep 2
done
if [[ "$code" == "000" ]]; then
    echo "Secretary loopback check failed on port 8791; service status and startup output:" >&2
    systemctl --user status "$UNIT_NAME" --no-pager >&2 || true
    if [[ -f /tmp/scs-startup.log ]]; then
        echo "--- startup output (/tmp/scs-startup.log) ---" >&2
        tail -n 80 /tmp/scs-startup.log >&2 || true
    fi
    journalctl --user -u "$UNIT_NAME" -n 50 --no-pager >&2 || true
    exit 1
fi
printf 'Secretary loopback responded HTTP %s on port 8791.\n' "$code"
