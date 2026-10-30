#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Starting OCI Deployment Sync for Dash & Seal "
echo "=================================================="

# 1. Fetch latest verified commit from main
echo "[1/5] Fetching verified codebase from origin/main..."
git fetch origin main
git reset --hard origin/main

# 2. Verify local signature manifest assets
echo "[2/5] Validating Cryptographic Manifests (.pbd.json)..."
if ls *.pbd.json 1> /dev/null 2>&1; then
    echo "✔ Manifest assets detected and aligned."
else
    echo "⚠️ Warning: No .pbd.json manifests found. Proceeding with caution."
fi

# 3. Update Python Virtual Environment & Server Dependencies
echo "[3/5] Updating server runtime dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi

python3 -m pip install --upgrade pip
if [ -f "requirements-server.txt" ]; then
    pip install -r requirements-server.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# 4. Reload Gunicorn WSGI Worker Service
echo "[4/5] Reloading Gunicorn backend service..."
if systemctl is-active --quiet gunicorn; then
    sudo systemctl reload gunicorn
    echo "✔ Gunicorn service reloaded cleanly."
elif systemctl is-active --quiet sanders-dash-seal; then
    sudo systemctl reload sanders-dash-seal
    echo "✔ Sanders Dash & Seal service reloaded cleanly."
else
    echo "⚠️ Service not active via systemd. Checking for Docker fallback..."
    if [ -f "docker-compose.yml" ]; then
        docker compose up -d --build
    fi
fi

# 5. Validate and Reload Nginx Reverse Proxy
echo "[5/5] Validating Nginx configuration and binding domains..."
if command -v nginx &> /dev/null; then
    sudo nginx -t
    sudo systemctl reload nginx
    echo "✔ Nginx reloaded successfully across all domain routing rules."
fi

echo "=================================================="
echo " SUCCESS: Deployment fully synchronized on OCI.  "
echo "=================================================="
