#!/usr/bin/env bash
set -euo pipefail

COMMIT_SHA="${1:-}"
if [[ ! "$COMMIT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: Valid 40-character GitHub commit SHA required." >&2
  exit 1
fi

APP_DIR="$HOME/.local/share/sanders-twostep-v2"
REPO_DIR="$HOME/.local/src/Sanders_Dash_Seal"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/sanders-twostep.service"

mkdir -p "$APP_DIR/assets" "$REPO_DIR" "$SERVICE_DIR"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone --depth 1 https://github.com "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch origin main --depth 1
git checkout -f "$COMMIT_SHA"

install -m 0750 "$REPO_DIR/sanders-twostep/sanders_twostep_v2.py" "$APP_DIR/sanders_twostep_v2.py"
if [[ -d "$REPO_DIR/sanders-twostep/assets" ]]; then
  cp -f "$REPO_DIR/sanders-twostep/assets/"*.png "$APP_DIR/assets/" 2>/dev/null || true
fi
sha256sum "$APP_DIR/sanders_twostep_v2.py" > "$APP_DIR/sanders_twostep_v2.py.sha256"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=The Sanders TwoStep v2 - Sovereign Uplink & Self-Healing Control Plane
After=network-online.target
Wants=network-online.target

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

systemctl --user daemon-reload
systemctl --user enable --now sanders-twostep.service
systemctl --user restart sanders-twostep.service

sleep 2
curl -fsS http://127.0.0.1:9400/healthz
echo ""
echo "The Sanders TwoStep v2 deployed and verified at commit $COMMIT_SHA"
