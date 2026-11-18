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

systemctl --user daemon-reload
systemctl --user enable --now sanders-twostep.service sanders-judge.service
systemctl --user restart sanders-twostep.service sanders-judge.service
sleep 2

LOOPBACK="127.0.0.1"
curl -fsS "http://${LOOPBACK}:9400/healthz"
echo ""
curl -fsS "http://${LOOPBACK}:9405/healthz"
echo ""
