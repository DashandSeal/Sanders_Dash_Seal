#!/usr/bin/env bash
set -euo pipefail

COMMIT_SHA="${1:-main}"
GH_HOST="github.com"
GH_REPO="DashandSeal/Sanders_Dash_Seal.git"
REPO_DIR="$HOME/.local/src/Sanders_Dash_Seal"
APP_DIR="$HOME/.local/share/sanders-twostep-v2"
SVC_DIR="$HOME/.config/systemd/user"

mkdir -p "$APP_DIR/assets" "$HOME/.local/src" "$SVC_DIR"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone --depth 1 "https://${GH_HOST}/${GH_REPO}" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch origin main --depth 1
  git -C "$REPO_DIR" reset --hard origin/main
fi

install -m 0750 "$REPO_DIR/sanders-twostep/sanders_twostep_v2.py" "$APP_DIR/sanders_twostep_v2.py"
install -m 0750 "$REPO_DIR/sanders-twostep/the_judge.py" "$APP_DIR/the_judge.py"
cp -f "$REPO_DIR/sanders-twostep/"*.png "$APP_DIR/assets/" 2>/dev/null || true
cp -f "$REPO_DIR/sanders-twostep/assets/"*.png "$APP_DIR/assets/" 2>/dev/null || true

# The Judge crashed at startup in run #20 even though its file parses, and
# the user journal on this host is empty, so a crash leaves no trace. Check
# both entrypoints parse with the same interpreter the units will use, and
# capture each one's real startup output to a log file before the services
# start, so a failure can show its actual error instead of silence.
echo "Syntax-checking installed entrypoints..."
/usr/bin/python3 -m py_compile "$APP_DIR/sanders_twostep_v2.py" "$APP_DIR/the_judge.py" || {
    echo "Syntax check failed for a TwoStep/Judge entrypoint; see above." >&2
    exit 1
}
echo "Probing entrypoints briefly to capture startup output (the timeout kill is expected)..."
( cd "$APP_DIR" && timeout 5 /usr/bin/python3 "$APP_DIR/sanders_twostep_v2.py" > /tmp/twostep-startup.log 2>&1 ) || true
( cd "$APP_DIR" && timeout 5 /usr/bin/python3 "$APP_DIR/the_judge.py" > /tmp/judge-startup.log 2>&1 ) || true

cat > "$SVC_DIR/sanders-twostep.service" <<EOF
[Unit]
Description=The Sanders TwoStep v2 (127.0.0.1:9400)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/sanders_twostep_v2.py
Restart=always
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

cat > "$SVC_DIR/sanders-judge.service" <<EOF
[Unit]
Description=The Judge - RTSA Constitutional Adjudicator (127.0.0.1:9405)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/the_judge.py
Restart=always
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

# Keep the opc user services alive after the SSH session that deployed them
# ends; without this, systemd stops user units at logout. Ignore failure if
# the privilege is unavailable in this session.
loginctl enable-linger opc 2>/dev/null || loginctl enable-linger 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable --now sanders-twostep.service sanders-judge.service
systemctl --user restart sanders-twostep.service sanders-judge.service

# Health checks that tell the truth: retry each loopback check, accept only
# a real HTTP response, and on failure print the service status plus the
# captured startup output. The user journal on this host is empty, so it is
# only a last resort, never the sole diagnostic.
LOOPBACK="127.0.0.1"
check_health() {
    local port="$1" unit="$2" log="$3"
    local attempt
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        if curl -fsS "http://${LOOPBACK}:${port}/healthz" 2>/dev/null; then
            echo ""
            return 0
        fi
        sleep 2
    done
    echo "Health check failed for ${unit} on port ${port} after 10 attempts; service status and startup output:" >&2
    systemctl --user status "$unit" --no-pager >&2 || true
    if [[ -f "$log" ]]; then
        echo "--- startup output ($log) ---" >&2
        tail -n 80 "$log" >&2 || true
    fi
    echo "--- user journal (may be empty on this host) ---" >&2
    journalctl --user -u "$unit" -n 50 --no-pager >&2 || true
    return 1
}
check_health 9400 sanders-twostep.service /tmp/twostep-startup.log
check_health 9405 sanders-judge.service /tmp/judge-startup.log
