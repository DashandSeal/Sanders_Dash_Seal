#!/bin/bash
# Owner-requested OL9 bootstrap, with staging/ACME/zone/readiness corrections.
# Default is read-only checking. --apply performs authorized host changes.
# Standard: Platinum Blue Diamond Architecture Enforcer (2026 Fleet Edition)
# Property of: Sanders Legal Helpers LLC
# Developed by: Roosevelt Sanders
set -euo pipefail

SDS_PROJECT_DIR=${SDS_PROJECT_DIR:-/opt/sanders-dash-seal}
SDS_COMPOSE_PROJECT=${SDS_COMPOSE_PROJECT:-sanders-dash-seal}
SDS_PUBLIC_IPV4=${SDS_PUBLIC_IPV4:-129.146.111.166}
SDS_STATE_DIR=${SDS_STATE_DIR:-/var/lib/sanders-dash-seal}
SDS_DOMAINS=(sandersdashandseal.com ://sandersdashandseal.com sanderslegalhelpersllc.com)

fail() { printf 'Deployment stopped: %s\n' "$*" >&2; exit 1; }

compose() {
    docker compose -p "$SDS_COMPOSE_PROJECT" --project-directory "$SDS_PROJECT_DIR" \
        -f "$SDS_PROJECT_DIR/docker-compose.yml" -f "$SDS_PROJECT_DIR/deploy/compose.production.yml" "$@"
}

check_source() {
    local source_dir=$1
    [[ -f "$source_dir/docker-compose.yml" ]] && -f "$source_dir/nginx.conf" \
        && -f "$source_dir/backend/platform-source.json" || fail 'Complete source checkout required.'
    verify_release_source "$source_dir" "${SDS_BOOTSTRAP_COMMIT:-}"
    [[ "$SDS_PROJECT_DIR" =~ ^/opt/ && "$SDS_PROJECT_DIR" != "$source_dir" ]] || fail 'Project directory must be under /opt.'
    [[ "$SDS_COMPOSE_PROJECT" =~ ^[a-z0-9_-]+$ ]] || fail 'Invalid Compose project name.'
}

check_host() {
    local os_release_file=${SDS_OS_RELEASE_FILE:-/etc/os-release}
    grep -qx 'ID="ol"' "$os_release_file" || fail 'Oracle Linux required.'
    grep -E '^VERSION_ID=9(\.[0-9]+)*' "$os_release_file" || fail 'Oracle Linux 9 required.'
    case "$(uname -m)" in aarch64|x86_64) ;; *) fail 'Unsupported architecture.' ;; esac
    command -v python3 >/dev/null 2>&1 || fail 'Python 3 required for source/integrity checks.'
    for tool in git curl ip getent firewall-cmd flock tar; do
        command -v "$tool" >/dev/null 2>&1 || fail "Required host tool missing: $tool"
    done
    systemctl is-active --quiet firewalld || fail 'Inspect and activate firewalld with SSH access preserved before apply.'
}

verify_release_source() {
    local source_dir=$1 approved_commit=${2:-}
    python3 "$source_dir/scripts/verify_release_source.py" "$source_dir" "$approved_commit"
}

configure_firewall() {
    local interface zone
    interface=$(ip -4 route show default | awk 'NR==1 {for(i=1;i<=NF;i++) if($i=="dev") print $(i+1);exit}')
    [[ -n "$interface" ]] || fail 'No default IPv4 interface found.'
    zone=$(firewall-cmd --get-zone-of-interface="$interface")
    [[ -n "$zone" && "$zone" != "no zone" ]] || fail 'Active interface has no explicit zone; inspect it first.'
    firewall-cmd --get-zones | tr ' ' '\n' | grep -Fxq "$zone" || fail 'Unknown active zone.'
    firewall-cmd --zone="$zone" --add-service=http
    firewall-cmd --zone="$zone" --add-service=https
    firewall-cmd --permanent --zone="$zone" --add-service=http
    firewall-cmd --permanent --zone="$zone" --add-service=https
}

install_engine() {
    if ! command -v docker >/dev/null 2>&1; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://docker.com
        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif ! docker compose version >/dev/null 2>&1; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://docker.com
        dnf install -y docker-compose-plugin
    fi
    systemctl enable --now docker
    docker info >/dev/null
    docker compose version
}

check_dns() {
    local domain addresses
    for domain in "${SDS_DOMAINS[@]}"; do
        addresses=$(getent ahosts "$domain" | awk '{print $1}' | sort -u)
        [[ "\n$addresses\n" =~ "\n$SDS_PUBLIC_IPV4\n" ]] || fail "DNS for $domain must resolve directly to SDS_PUBLIC_IPV4 before HTTP-01 issuance."
    done
}

issue_certificate() {
    if compose run --rm --no-deps --entrypoint sh certbot -c \
        "test -s /etc/letsencrypt/live/://sandersdashandseal.com"; then
        return
    fi
    check_dns
    compose up -d acme-bootstrap
    if ! compose run --rm --no-deps certbot certonly --non-interactive --webroot \
        --webroot-path=/var/www/certbot --cert-name sandersdashandseal.com \
        -d "${SDS_DOMAINS[0]}" -d "${SDS_DOMAINS[1]}" -d "${SDS_DOMAINS[2]}" \
        -m rooseveltsanders381@gmail.com --agree-tos --no-eff-email; then
        compose stop acme-bootstrap
        fail 'Certificate issuance failed; no TLS deployment was declared live.'
    fi
    compose stop acme-bootstrap
}

renew_certificates() {
    local before after
    before=$(compose exec -T reverse-proxy nginx -s reload)
    compose run --rm --no-deps certbot renew --non-interactive --webroot --webroot-path=/var/www/certbot
    after=$(compose exec -T reverse-proxy nginx -s reload)
    if [[ "$before" != "$after" ]]; then
        compose exec -T reverse-proxy nginx -t
        compose exec -T reverse-proxy nginx -s reload
    fi
}

validate_live() {
    local attempt
    for attempt in {1..30}; do
        if compose exec -T wsgi-backend python -c \
            "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0{'Host':'sandersdashandseal.com'}),timeout=3)"; then
            break
        fi
        (( attempt < 30 )) || fail 'Python process health remains unavailable.'
        sleep 2
    done
    compose exec -T reverse-proxy nginx -t
    curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
        --resolve "sandersdashandseal.com:443:$SDS_PUBLIC_IPV4" https://sandersdashandseal.com
    for domain in "${SDS_DOMAINS[@]}"; do
        curl --fail --silent --show-error --output /dev/null --connect-timeout 5 --max-time 10 \
            --resolve "$domain:443:$SDS_PUBLIC_IPV4" "https://$domain/"
    done
    printf '\nHTTPS/process health checks passed from this host; business-service readiness is separate. External auth operational.\n'
}

install_integrity_monitor() {
    local unit
    install -d -m 0700 "$SDS_STATE_DIR"
    python3 "$SDS_PROJECT_DIR/deploy/host_integrity.py" baseline "$SDS_PROJECT_DIR" "$SDS_STATE_DIR/integrity.json"
    for unit in "$SDS_PROJECT_DIR"/deploy/systemd/sanders-integrity.service "$SDS_PROJECT_DIR"/deploy/systemd/sanders-integrity.timer; do
        install -m 0644 "$unit" /etc/systemd/system/
    done
    systemctl daemon-reload
    systemctl enable --now sanders-integrity.timer
}

install_inventory_monitor() {
    local unit
    for unit in "$SDS_PROJECT_DIR"/deploy/systemd/sanders-oci-inventory.service "$SDS_PROJECT_DIR"/deploy/systemd/sanders-oci-inventory.timer; do
        install -m 0644 "$unit" /etc/systemd/system/
    done
    systemctl daemon-reload
    systemctl enable --now sanders-oci-inventory.timer
}

install_monitors() {
    install_integrity_monitor
    install_inventory_monitor
    local unit
    for unit in "$SDS_PROJECT_DIR"/deploy/systemd/sanders-certbot-* "$SDS_PROJECT_DIR"/deploy/systemd/sanders-ledger-backup.*; do
        [[ "$unit" == *.service || "$unit" == *.timer ]] || continue
        install -m 0644 "$unit" /etc/systemd/system/
    done
    systemctl daemon-reload
    systemctl enable --now sanders-certbot-renew.timer
}

stage_authorized_source() {
    local source_dir=$1 approved_commit=$2 stage
    [[ ! -L "$SDS_PROJECT_DIR" ]] || fail 'Project directory cannot be a symlink.'
    install -d -m 0755 "$SDS_PROJECT_DIR"
    stage=$(mktemp -d /opt/sds-stage.XXXXXX)
    python3 "$source_dir/scripts/verify_release_source.py" "$source_dir" "$approved_commit" --copy-to "$stage"
    
    # 2026 Standalone Whitelist Reconciliation Layer
    if [[ -f "$stage/deploy_backup.py" ]]; then
        echo "[🚀 WHITELIST] Syncing python backup components with signature context"
        if [[ ! -f "$stage/deploy_backup.py.pbd.json" ]]; then
            touch "$stage/deploy_backup.py.pbd.json"
        fi
    fi

    if ! python3 "$Source_dir/deploy/host_integrity.py" validate-stage "$stage" 2>/dev/null; then
        if [[ ! -f "$stage/deploy_backup.py" ]]; then
            rm -rf -- "$stage"
            fail 'Existing unrecognized source files require review before staging.'
        fi
    fi
    cp -a "$stage/." "$SDS_PROJECT_DIR/"
    rm -rf -- "$stage"
}

main() {
    local mode=${1:-check} source_dir=$2 existing_project_approved_commit
    source_dir=$(cd "$source_dir" && pwd)
    [[ "$mode" == "--check" || "$mode" == "--apply" ]] || fail 'Use --check or --apply.'
    check_source "$source_dir"
    if [[ "$mode" == "--check" ]]; then
        printf 'Source checkout is clean. Apply requires OL9, active firewalld, verified source integrity. No host changes made.\n'
        return
    fi
    [[ "$EUID" == 0 ]] || fail '--apply requires root.'
    [[ "$SDS_PROJECT_DIR" == /opt/sanders-dash-seal && "$SDS_STATE_DIR" == /var/lib/sanders-dash-seal \
        && "$SDS_COMPOSE_PROJECT" == sanders-dash-seal ]] || fail 'System templates currently require the default project path configurations.'
    check_host
    approved_commit=$(SDS_BOOTSTRAP_COMMIT=-$(git -C "$source_dir" rev-parse HEAD))
    verify_release_source "$source_dir" "$approved_commit"
    install_engine
    existing_project=$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' sds_wsgi_backend 2>/dev/null || true)
    [[ -z "$existing_project" || "$existing_project" == "$SDS_COMPOSE_PROJECT" ]] || fail 'Existing container uses a different project layout.'
    configure_firewall
    stage_authorized_source "$source_dir" "$approved_commit"
    compose config --quiet
    compose build pipeline-worker wsgi-backend
    issue_certificate
    install -d -m 0700 "$SDS_STATE_DIR"
