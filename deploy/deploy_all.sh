# deploy_all.sh — the simultaneous master deploy for Sanders Dash & Seal.
# This script is the deploy: .github/workflows/deploy_all_simultaneous.yml
# only syncs the checkout at /opt/Sanders_Dash_Seal and runs this file, so
# deploy behavior is fixed here in the repository instead of by editing the
# workflow through the web UI. It runs on the Oracle instance as the deploy
# user (sudo where root is needed). Extracted from the workflow's former
# inline SSH script on 2026-11-23; behavior is unchanged except for the
# preflight (step 2b), the repo-owned nginx server config (step 4), and the
# extended failure diagnostics (step 7) added the same day, plus the
# automatic-recovery watchdog install (step 5c) added later that day, and
# the full self-repair layer — the env guard and repair playbook installs
# (step 5c) and the last-known-good snapshots (step 8) — added later that
# day as well. The certificate-coverage warning (step 7b) and the
# watchdog's cert-coverage guard were added later on 2026-11-23 (owner
# directive: correct certification by design, globally).
set -euo pipefail
REPO_DIR="/opt/Sanders_Dash_Seal"

# 0. Bootstrap git, Nginx, Python 3.12, and native C build tools on Oracle Linux 9
sudo dnf install -y git nginx cmake gcc-c++ make openssl-devel python3.12 python3.12-devel

# 1. Clone or sync entire DashandSeal/Sanders_Dash_Seal repository
if [ ! -d "$REPO_DIR/.git" ]; then
  sudo mkdir -p "$REPO_DIR"
  sudo chown -R "$USER:$USER" "$REPO_DIR"
  git clone https://github.com/DashandSeal/Sanders_Dash_Seal.git "$REPO_DIR"
fi
cd "$REPO_DIR"
# The checkout's .git directory must be writable by the deploy
# user: a past privileged git operation left root-owned objects
# behind, and `git fetch` fails with "insufficient permission
# for adding an object to repository database .git/objects"
# (deploy_all run #100, 2026-11-22). Re-assert ownership here
# so the deploy self-heals instead of failing.
sudo chown -R "$USER:$USER" "$REPO_DIR/.git"
git fetch origin main
git reset --hard origin/main

# 2. Ensure Python 3.12 virtual environment & install all repo + Legal Engine dependencies
if [ ! -d "$REPO_DIR/venv" ]; then
  python3.12 -m venv "$REPO_DIR/venv" || python3 -m venv "$REPO_DIR/venv"
fi
source "$REPO_DIR/venv/bin/activate"
pip install --upgrade pip
[ -f requirements.txt ] && pip install -r requirements.txt || true
[ -f requirements-server.txt ] && pip install -r requirements-server.txt || true
[ -f money_factory_legal_aid_v1_668/requirements.txt ] && pip install -r money_factory_legal_aid_v1_668/requirements.txt || true

# 2b. PREFLIGHT: the app environment must exist and carry a usable Stripe
# webhook secret BEFORE any service is restarted. wsgi.py raises
# WebhookConfigurationError at import when STRIPE_WEBHOOK_SECRET is unset,
# and the app unit reads it only from /etc/sanders-dash-seal/environment
# (installer template, empty by default) and
# /etc/sanders-dash-seal/runtime.env (written by
# deploy/refresh_provider_secrets.py from the OCI Vault). On 2026-11-23 the
# instance had NO runtime.env at all, so every deploy restarted the app
# into an exit-1 loop and took the site down (runs #101/#102/#103). This
# check fails the deploy here — before any restart — so a missing or
# malformed environment can never take the running site down again.
# Shape check only: the secret value is never printed.
RUNTIME_ENV="/etc/sanders-dash-seal/runtime.env"
if ! sudo test -f "$RUNTIME_ENV"; then
  echo "PREFLIGHT FAILED: $RUNTIME_ENV does not exist on this instance."
  echo "The app cannot start without it: wsgi.py refuses to import when STRIPE_WEBHOOK_SECRET is unset."
  echo "Owner step: populate it first (run the Vault refresh flow, deploy/refresh_provider_secrets.py, or create the file with the Stripe values), then re-run the deploy."
  echo "No service has been restarted; the running site is untouched."
  exit 1
fi
if ! sudo grep -Eq '^[[:space:]]*STRIPE_WEBHOOK_SECRET=whsec_' "$RUNTIME_ENV"; then
  echo "PREFLIGHT FAILED: STRIPE_WEBHOOK_SECRET in $RUNTIME_ENV is missing or does not start with whsec_."
  echo "Owner step: set a real STRIPE_WEBHOOK_SECRET in $RUNTIME_ENV (Vault refresh flow: deploy/refresh_provider_secrets.py), then re-run the deploy."
  echo "No service has been restarted; the running site is untouched."
  exit 1
fi
echo "Preflight OK: $RUNTIME_ENV present and STRIPE_WEBHOOK_SECRET has the whsec_ shape."

# 3. Register liboqs shared libraries globally & allow Nginx localhost proxying under SELinux
printf "/usr/local/lib64\n/usr/local/lib\n" | sudo tee /etc/ld.so.conf.d/liboqs.conf >/dev/null
sudo ldconfig
if command -v setsebool >/dev/null 2>&1; then
  sudo setsebool -P httpd_can_network_connect 1 || true
fi

# 4. Install Money Factory Legal Aid v1.668 systemd & Nginx reverse proxy
if [ -f money_factory_legal_aid_v1_668/infra/oracle_linux_9/money-factory-legal.service ]; then
  sudo cp money_factory_legal_aid_v1_668/infra/oracle_linux_9/money-factory-legal.service /etc/systemd/system/
  sudo mkdir -p /etc/systemd/system/money-factory-legal.service.d
  sudo tee /etc/systemd/system/money-factory-legal.service.d/override.conf >/dev/null <<'OVERRIDE'
[Service]
Environment="LD_LIBRARY_PATH=/usr/local/lib64:/usr/local/lib"
OVERRIDE
fi

# 4b. Sync The Police Men RTSA status file only. The dashboard
# itself is NOT copied to the public web root: the public root
# on every domain is the Sanders Dash & Seal app. status.json
# stays for the /rtsa/status endpoint until the owner decides
# the dashboard's new home and access.
sudo mkdir -p /var/www/rtsa
if [ -d "$REPO_DIR/rtsa_police_men" ]; then
  sudo cp "$REPO_DIR/rtsa_police_men/status.json" /var/www/rtsa/status.json
  sudo chmod 644 /var/www/rtsa/status.json
  if command -v restorecon >/dev/null 2>&1; then
    sudo restorecon -Rv /var/www/rtsa || true
  fi
fi

sudo mkdir -p /etc/nginx/conf.d /etc/nginx/snippets
sudo sed -i 's/default_server//g' /etc/nginx/nginx.conf || true
sudo sed -i 's/server_name[[:space:]]\+_;$/server_name localhost;/g' /etc/nginx/nginx.conf || true

if [ -f money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal.conf ]; then
  sudo cp money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal.conf /etc/nginx/snippets/money_factory_legal.conf
  if ! grep -q "/rtsa/status" /etc/nginx/snippets/money_factory_legal.conf; then
    sudo tee -a /etc/nginx/snippets/money_factory_legal.conf >/dev/null <<'RTSA_LOC'

location = /rtsa/status {
    default_type application/json;
    alias /var/www/rtsa/status.json;
}
RTSA_LOC
  fi
fi

# Install the nginx server config from the repo on EVERY run. The server
# config (port 80 + port 443 blocks for all ten site names) is repo source
# of truth in money_factory_legal_aid_v1_668/infra/oracle_linux_9/
# money_factory_legal_server.conf. It used to be written only when the TLS
# cert file was absent, and the 443 block existed only as a one-time append
# made by .github/workflows/restore-nginx-443-20261121.yml — so when the
# server file was later rewritten without that append, nginx came up with
# NO port 443 listener at all (found 2026-11-23: nginx listening on 80
# only, every https:// request reset). Installing it here on every run
# makes the deployed config always match the repo. The previous file is
# kept with a timestamped backup first, and step 5 runs `nginx -t` before
# any service restarts, so a bad config fails the deploy without touching
# the running nginx.
if [ -f money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal_server.conf ]; then
  if [ -f /etc/nginx/conf.d/money_factory_legal_server.conf ]; then
    sudo cp /etc/nginx/conf.d/money_factory_legal_server.conf "/tmp/money_factory_legal_server.conf.bak.$(date +%Y%m%d%H%M%S)"
  fi
  sudo cp money_factory_legal_aid_v1_668/infra/oracle_linux_9/money_factory_legal_server.conf /etc/nginx/conf.d/money_factory_legal_server.conf
fi

# 5. Open HTTP/HTTPS firewalld ports & explicitly enable/restart core services
if systemctl is-active --quiet firewalld; then
  sudo firewall-cmd --permanent --add-service=http || true
  sudo firewall-cmd --permanent --add-service=https || true
  sudo firewall-cmd --reload || true
fi
sudo systemctl daemon-reload
sudo nginx -t

sudo systemctl enable --now money-factory-legal.service
sudo systemctl restart money-factory-legal.service
sudo systemctl enable --now nginx.service
sudo systemctl restart nginx.service

for svc in sanders-dash-seal.service gunicorn.service; do
  if systemctl list-unit-files "$svc" | grep -q "$svc"; then
    sudo systemctl enable --now "$svc" || true
    sudo systemctl restart "$svc" || true
  fi
done

# 5b. Install the Sanders Dash & Seal app unit from the repo
# (deploy/sanders-dash-seal.service) so the restart above can
# actually restart the app, then restart it. The unit was
# missing from the repository, so deploys landed code without
# restarting the app and the running copy went stale (the
# overnight 421 host_denied regression on the three new
# domains). Pushed 2026-11-22 (commit 7c7ed46) via the web UI.
if [ -f deploy/sanders-dash-seal.service ]; then
  # The unit runs as the sanders service user (uid/gid 10001,
  # created by deploy/install-simultaneous.sh). Make sure it
  # exists first — without it the service cannot start.
  if ! getent group sanders >/dev/null; then
    sudo groupadd --gid 10001 sanders
  fi
  if ! id sanders >/dev/null 2>&1; then
    sudo useradd --uid 10001 --gid 10001 --no-create-home --shell /sbin/nologin sanders
  fi
  # The app creates <repo>/data at startup (wsgi.py
  # create_native_application: data_dir.mkdir) and writes its ledgers
  # there. Under systemd the whole process runs as sanders, which
  # cannot create that directory inside the opc-owned checkout — the
  # crash loop found 2026-11-23 once runtime.env was restored. Create
  # it here, owned by the runtime user, so startup never depends on
  # directory luck.
  sudo mkdir -p "$REPO_DIR/data"
  sudo chown sanders:sanders "$REPO_DIR/data"
  # Keep the previous unit file, if any, before overwriting it.
  if [ -f /etc/systemd/system/sanders-dash-seal.service ]; then
    sudo cp /etc/systemd/system/sanders-dash-seal.service "/tmp/sanders-dash-seal.service.bak.$(date +%Y%m%d%H%M%S)"
  fi
  sudo cp deploy/sanders-dash-seal.service /etc/systemd/system/sanders-dash-seal.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now sanders-dash-seal.service || true
  sudo systemctl restart sanders-dash-seal.service || true
fi

# 5c. Install the automatic-recovery watchdog (deploy/sds_watchdog.sh,
# deploy/sds-watchdog.service, deploy/sds-watchdog.timer) and enable its
# timer. The watchdog health-checks every platform service every 2
# minutes and restarts one that has stopped answering (2 consecutive
# failed checks, at most one restart per service per 5 minutes); see the
# watchdog script header and docs/SPEC_CONFORMANCE.md (November 23, 2026,
# automatic-recovery entry). It runs from /usr/local/sbin — installed
# fresh from the repo on every deploy — so it never depends on the
# checkout's state. Linger for opc is enabled here too, guarded: the
# Secretary, TwoStep and Judge services are systemd --user services
# owned by opc, and without linger the opc user manager stops at logout
# and does not start at boot. Both of those platforms' own deploy
# scripts already enable it; repeating it here means a fresh instance
# gets it from the main deploy as well.
# The full self-repair layer's two scripts are installed alongside
# the watchdog (owner decision, 2026-11-23: playbook repairs run
# autonomously; secrets, gates, and money are never automated):
# sds_repair.sh is the diagnose-and-repair playbook the watchdog
# escalates to when a plain restart did not recover a service, and
# sds_env_guard.sh is the conditional environment repair the app
# unit runs at every start (ExecStartPre in
# deploy/sanders-dash-seal.service) to regenerate runtime.env from
# the OCI Vault when it is missing or malformed.
if [ -f deploy/sds_watchdog.sh ]; then
  sudo install -m 0755 deploy/sds_watchdog.sh /usr/local/sbin/sds_watchdog.sh
fi
if [ -f deploy/sds_repair.sh ]; then
  sudo install -m 0755 deploy/sds_repair.sh /usr/local/sbin/sds_repair.sh
fi
if [ -f deploy/sds_env_guard.sh ]; then
  sudo install -m 0755 deploy/sds_env_guard.sh /usr/local/sbin/sds_env_guard.sh
fi
if [ -f deploy/sds-watchdog.service ]; then
  sudo cp deploy/sds-watchdog.service /etc/systemd/system/sds-watchdog.service
fi
if [ -f deploy/sds-watchdog.timer ]; then
  sudo cp deploy/sds-watchdog.timer /etc/systemd/system/sds-watchdog.timer
  sudo systemctl daemon-reload
  sudo systemctl enable --now sds-watchdog.timer || true
fi
sudo loginctl enable-linger opc || true

# 6. Bring up Docker Compose stacks if Docker is installed
if command -v docker >/dev/null 2>&1 && [ -f compose.yaml ]; then
  docker compose up -d --build || true
fi

# 7. Automated End-to-End Health, RTSA & ML-DSA-65 Smoke Test on OCI
# Extended 2026-11-22 (pushed, commit 7c7ed46): the old check verified only nginx +
# Money Factory, never the Dash & Seal app itself. The new
# checks also require /healthz on gunicorn (8000), both home
# pages through nginx, and an unauthenticated GET /api/session
# on the app answering 401 — 401 proves production bindings
# are live (the customer API reached authentication); 503
# proves diagnostic-only, and a failed connection proves the
# app never restarted.
HEALTH_OK=0
for i in 1 2 3 4 5; do
  if curl -fsS -H "Host: sandersdashandseal.com" http://127.0.0.1/legal-aid/health && \
     curl -fsS -H "Host: sandersdashandseal.com" http://127.0.0.1/rtsa/status >/dev/null && \
     curl -fsS -H "Host: sandersdashandseal.com" http://127.0.0.1:8000/healthz >/dev/null && \
     curl -fsS -H "Host: sandersdashandseal.com" http://127.0.0.1/ >/dev/null && \
     curl -fsS -H "Host: sanderslegalhelpersllc.com" http://127.0.0.1/ >/dev/null && \
     [ "$(curl -s -o /dev/null -w '%{http_code}' -H "Host: sandersdashandseal.com" http://127.0.0.1:8000/api/session)" = "401" ]; then
    HEALTH_OK=1
    break
  fi
  sleep 2
done

if [ "$HEALTH_OK" -ne 1 ]; then
  echo "=== DIAGNOSTICS: Nginx & money-factory-legal.service ==="
  curl -i -sS -H "Host: sandersdashandseal.com" http://127.0.0.1/rtsa/status | head -n 20 || true
  sudo systemctl status money-factory-legal.service --no-pager -l || true
  echo "=== DIAGNOSTICS: Sanders Dash & Seal app (8000) ==="
  curl -i -sS -H "Host: sandersdashandseal.com" http://127.0.0.1:8000/healthz | head -n 20 || true
  curl -s -o /dev/null -w 'GET /api/session (unauthenticated) -> %{http_code}\n' -H "Host: sandersdashandseal.com" http://127.0.0.1:8000/api/session || true
  sudo systemctl status sanders-dash-seal.service --no-pager -l || true
  # The app service journal and the listener table are part of the failure
  # diagnostics on purpose (added 2026-11-23): during the Nov 22–23 outage
  # the diagnostics printed only `systemctl status`, which never shows the
  # app's actual startup error, so three failed runs in a row (#101/#102/
  # #103) left the real cause invisible in the run log. The journal carries
  # the gunicorn traceback; the listener table shows at a glance whether
  # 8000 (app), 8668 (Money Factory), 80 and 443 (nginx) are bound.
  echo "=== DIAGNOSTICS: Sanders Dash & Seal app journal (last 60) ==="
  sudo journalctl -u sanders-dash-seal.service -n 60 --no-pager || true
  echo "=== DIAGNOSTICS: listeners (80/443/8000/8668) ==="
  sudo ss -ltnp | grep -E ':(80|443|8000|8668)' || true
  exit 1
fi

# 7b. Certificate coverage warning (owner directive 2026-11-23:
# correct certification by design, globally). Every name the installed
# server config serves must be on the certificate nginx serves — the
# 2026-11-23 www.sanderslegalhelpersllc.com gap (a name live in DNS
# with no certificate coverage, found by the owner on his phone) is
# the incident this exists to catch at deploy time. A gap is a LOUD
# WARNING here, never a deploy failure (the deployment law: nothing
# stops deployment). The watchdog's cert-coverage guard
# (deploy/sds_watchdog.sh) checks the same thing every 2 minutes and
# escalates until it is fixed. Issuing or expanding a certificate is
# an owner-approved action; this step only reports.
CERT_SERVED="$(grep -h '^[[:space:]]*server_name' /etc/nginx/conf.d/money_factory_legal_server.conf 2>/dev/null | tr ';' ' ' | awk '{for (i=2; i<=NF; i++) print $i}' | grep -v '^_$' | grep -vE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | sort -u || true)"
CERT_ON="$(echo | openssl s_client -connect 127.0.0.1:443 -servername sandersdashandseal.com 2>/dev/null | openssl x509 -noout -ext subjectAltName 2>/dev/null | grep -o 'DNS:[^,]*' | sed 's/^DNS://' | sort -u || true)"
CERT_MISSING=""
for n in $CERT_SERVED; do
  printf '%s\n' "$CERT_ON" | grep -qx "$n" || CERT_MISSING="${CERT_MISSING} $n"
done
if [ -n "$CERT_MISSING" ]; then
  echo "CERT COVERAGE WARNING: served name(s) NOT on the certificate:${CERT_MISSING} — visitors to those names will get a certificate warning. Owner step: approve expanding the certificate to add them."
elif [ -z "$CERT_SERVED" ] || [ -z "$CERT_ON" ]; then
  echo "CERT COVERAGE WARNING: could not read the served names or the served certificate to compare them."
else
  echo "CERT COVERAGE: OK — every served name is on the certificate."
fi

# 7c. Public-face warning (owner standing rule 2026-11-23: "Everything
# that has its own domain name should always be the public facing RTSA
# platform"). Every served name must return the public Dash & Seal
# storefront at / — the marker is the storefront banner
# ("dash-seal-banner" in the response body, verified live on all 10
# served names 2026-11-23) — never a backend, a placeholder, or a dead
# page. A wrong face is a LOUD WARNING here, never a deploy failure.
# The watchdog's public-face guard (deploy/sds_watchdog.sh) checks the
# same thing every 2 minutes and escalates until it is fixed; neither
# this step nor the watchdog changes what a name serves.
FACE_BAD=""
for n in $CERT_SERVED; do
  FACE_BODY="$(curl -sk --max-time 15 --resolve "${n}:443:127.0.0.1" "https://${n}/" 2>/dev/null || true)"
  case "$FACE_BODY" in
    *dash-seal-banner*) : ;;
    *) FACE_BAD="${FACE_BAD} $n" ;;
  esac
done
if [ -n "$FACE_BAD" ]; then
  echo "PUBLIC FACE WARNING: served name(s) NOT returning the public Dash & Seal storefront at /:${FACE_BAD} — every domain must serve its public-facing RTSA platform, never a backend or placeholder. Fix through the normal content/config deploy path."
elif [ -z "$CERT_SERVED" ]; then
  echo "PUBLIC FACE WARNING: could not read the served names to check their public faces."
else
  echo "PUBLIC FACE: OK — every served name returns the public storefront."
fi

# 8. Last-known-good (LKG) snapshot. Reaching this step means the
# health check above PASSED, so the configuration installed right
# now is verified working. Snapshot it to
# /var/lib/sds-lkg/<timestamp>/ on the instance so the repair
# playbook (deploy/sds_repair.sh, entry point `restore-lkg`) can
# restore a known-working state without a redeploy: the installed
# nginx server conf + snippet, the installed app unit, and the
# watchdog / repair / env-guard scripts as installed. MANIFEST.txt
# carries the sha256 of every snapshotted file in sha256sum format
# (the repair script verifies hashes before restoring), and
# DEPLOYED_COMMIT records the git commit this deploy put live.
# At most the 3 newest snapshots are kept.
# runtime.env is snapshotted too — deliberately, and ONLY here:
# the snapshot directory is root-only (0700) on the instance and
# the copy is 0600 root:root. It is the owner's own secret file,
# copied byte-for-byte from /etc on the same instance and NEVER
# into the repository, so `sds_repair.sh restore-lkg env` can put
# back the exact file a passing deploy verified. If the health
# check failed, the deploy already exited above and no snapshot is
# taken. Snapshot problems are loud warnings, never a deploy
# failure — the deploy itself has already passed.
LKG_BASE="/var/lib/sds-lkg"
LKG_DIR="$LKG_BASE/$(date +%Y%m%d%H%M%S)"
sudo install -d -m 0755 "$LKG_BASE" || true
if sudo install -d -m 0700 "$LKG_DIR"; then
  for pair in \
    "/etc/nginx/conf.d/money_factory_legal_server.conf money_factory_legal_server.conf" \
    "/etc/nginx/snippets/money_factory_legal.conf money_factory_legal.conf" \
    "/etc/systemd/system/sanders-dash-seal.service sanders-dash-seal.service" \
    "/usr/local/sbin/sds_watchdog.sh sds_watchdog.sh" \
    "/usr/local/sbin/sds_repair.sh sds_repair.sh" \
    "/usr/local/sbin/sds_env_guard.sh sds_env_guard.sh" \
    "/etc/sanders-dash-seal/runtime.env runtime.env"; do
    src="${pair%% *}"; dst="${pair##* }"
    if sudo test -f "$src"; then
      sudo cp "$src" "$LKG_DIR/$dst" || echo "LKG WARNING: could not snapshot $src"
    else
      echo "LKG NOTE: $src not present on this instance; not snapshotted"
    fi
  done
  sudo chmod 0600 "$LKG_DIR/runtime.env" 2>/dev/null || true
  git rev-parse HEAD 2>/dev/null | sudo tee "$LKG_DIR/DEPLOYED_COMMIT" >/dev/null || true
  sudo sh -c "cd '$LKG_DIR' && sha256sum money_factory_legal_server.conf money_factory_legal.conf sanders-dash-seal.service sds_watchdog.sh sds_repair.sh sds_env_guard.sh runtime.env > MANIFEST.txt" 2>/dev/null \
    || echo "LKG WARNING: MANIFEST.txt could not be completed (a snapshotted file was missing)"
  # Keep at most the 3 newest snapshots.
  ls -1dt "$LKG_BASE"/*/ 2>/dev/null | tail -n +4 | while read -r old; do
    sudo rm -rf "$old" || true
  done || true
  echo "LKG snapshot written: $LKG_DIR"
else
  echo "LKG WARNING: could not create $LKG_DIR; no snapshot taken"
fi

echo ""
echo "SIMULTANEOUS DEPLOY COMPLETE: The Police Men RTSA & Sanders_Dash_Seal active."
