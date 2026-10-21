#!/bin/bash
# Owner-requested OL9 bootstrap, with staging/ACME/zone/readiness corrections.
# Default is read-only checking. --apply performs authorized host changes.
set -Eeuo pipefail

SDS_PROJECT_DIR=${SDS_PROJECT_DIR:-/opt/sanders-dash-seal}
SDS_COMPOSE_PROJECT=${SDS_COMPOSE_PROJECT:-sanders-dash-seal}
SDS_PUBLIC_IPV4=${SDS_PUBLIC_IPV4:-129.146.111.166}
SDS_RUNTIME_ENV_FILE=${SDS_RUNTIME_ENV_FILE:-/etc/sanders-dash-seal/runtime.env}
SDS_RELEASE_AUTHORIZER=${SDS_RELEASE_AUTHORIZER:-/etc/sanders-dash-seal/authorize-release}
SDS_STATE_DIR=${SDS_STATE_DIR:-/var/lib/sanders-dash-seal}
SDS_DOMAINS=(sandersdashandseal.com www.sandersdashandseal.com sanderslegalhelpersllc.com www.sanderslegalhelpersllc.com)

fail() { printf 'Deployment stopped: %s\n' "$*" >&2; return 1; }
compose() {
    docker compose -p "$SDS_COMPOSE_PROJECT" --project-directory "$SDS_PROJECT_DIR" \
        -f "$SDS_PROJECT_DIR/docker-compose.yml" -f "$SDS_PROJECT_DIR/deploy/compose.production.yml" "$@"
}

check_source() {
    local source_dir=$1
    [[ -f "$source_dir/docker-compose.yml" && -f "$source_dir/nginx.conf" \
       && -f "$source_dir/backend/platform-source.json" ]] || fail 'Complete source checkout required.'
    [[ -z "$(git -C "$source_dir" status --porcelain --untracked-files=all)" ]] \
        || fail 'Source checkout has uncommitted or untracked changes.'
    [[ "$SDS_PROJECT_DIR" == /opt/* && "$SDS_PROJECT_DIR" != *$'\n'* ]] || fail 'Project directory must be under /opt.'
    [[ "$SDS_COMPOSE_PROJECT" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || fail 'Invalid Compose project name.'
}

check_host() {
    local os_file=${SDS_OS_RELEASE_FILE:-/etc/os-release} tool
    # os-release is administrator-controlled OS metadata, not request content.
    grep -qx 'ID="\?ol"\?' "$os_file" || fail 'Oracle Linux required.'
    grep -Eq '^VERSION_ID="?9([."]|$)' "$os_file" || fail 'Oracle Linux 9 required.'
    case "$(uname -m)" in aarch64|x86_64) ;; *) fail 'Unsupported architecture.' ;; esac
    command -v python3 >/dev/null || fail 'Python 3 required for source/integrity checks.'
    for tool in git curl ip getent firewall-cmd flock tar; do
        command -v "$tool" >/dev/null || fail "Required host tool missing: $tool"
    done
    systemctl is-active --quiet firewalld || fail 'Inspect and activate firewalld with SSH access preserved before applying.'
}

authorize_release() {
    local source_dir=$1 approved_commit=${2:-}
    [[ -x "$SDS_RELEASE_AUTHORIZER" && ! -L "$SDS_RELEASE_AUTHORIZER" ]] \
        || fail 'Independent administrator-installed release authorizer required.'
    [[ "$(stat -c %u "$SDS_RELEASE_AUTHORIZER")" == 0 ]] || fail 'Authorizer must be root-owned.'
    (( (8#$(stat -c %a "$SDS_RELEASE_AUTHORIZER") & 0022) == 0 )) || fail 'Authorizer is group/world writable.'
    [[ -f "$SDS_RUNTIME_ENV_FILE" && ! -L "$SDS_RUNTIME_ENV_FILE" ]] || fail 'Protected runtime configuration required.'
    [[ "$(stat -c %u "$SDS_RUNTIME_ENV_FILE")" == 0 ]] || fail 'Runtime configuration must be root-owned.'
    (( (8#$(stat -c %a "$SDS_RUNTIME_ENV_FILE") & 0077) == 0 )) || fail 'Runtime configuration must be private to root.'
    grep -Eq '^SANDERS_RUNTIME_FACTORY=[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$' "$SDS_RUNTIME_ENV_FILE" \
        || fail 'Real runtime factory reference required.'
    # This file is deliberately not generated; it must verify independent source,
    # dependency and runtime authority, not echo a fabricated approval.
    [[ -n "$approved_commit" ]] || approved_commit=$(git -C "$source_dir" rev-parse HEAD)
    "$SDS_RELEASE_AUTHORIZER" "$source_dir" "$approved_commit"
}

configure_firewall() {
    local interface zone
    interface=$(ip -4 route show default | awk 'NR==1 {for(i=1;i<=NF;i++)if($i=="dev"){print $(i+1);exit}}')
    [[ -n "$interface" ]] || fail 'No default IPv4 interface found.'
    zone=$(firewall-cmd --get-zone-of-interface="$interface")
    [[ -n "$zone" && "$zone" != 'no zone' ]] || fail 'Active interface has no explicit zone; inspect it first.'
    firewall-cmd --get-zones | tr ' ' '\n' | grep -Fxq "$zone" || fail 'Unknown active zone.'
    # Add only HTTP/S in this interface's zone. No reload/flush or SSH rule removal.
    firewall-cmd --zone="$zone" --add-service=http
    firewall-cmd --zone="$zone" --add-service=https
    firewall-cmd --permanent --zone="$zone" --add-service=http
    firewall-cmd --permanent --zone="$zone" --add-service=https
}

install_engine() {
    if ! command -v docker >/dev/null 2>&1; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif ! docker compose version >/dev/null 2>&1; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
        dnf install -y docker-compose-plugin
    fi
    systemctl enable --now docker
    docker info >/dev/null
    docker compose version
}

check_dns() {
    local domain addresses
    for domain in "${SDS_DOMAINS[@]}"; do
        addresses=$(getent ahostsv4 "$domain" | awk '{print $1}' | sort -u)
        [[ "$addresses" == "$SDS_PUBLIC_IPV4" ]] || fail "DNS for $domain must resolve directly to $SDS_PUBLIC_IPV4 before HTTP-01 issuance."
    done
}

issue_certificate() {
    if compose run --rm --no-deps --entrypoint sh certbot -c \
        'test -s /etc/letsencrypt/live/sandersdashandseal.com/fullchain.pem'; then
        return
    fi
    check_dns
    compose up -d acme-bootstrap
    # Initial HTTP challenge service does not depend on nonexistent TLS files.
    if ! compose run --rm --no-deps certbot certonly --non-interactive --webroot \
        --webroot-path=/var/www/certbot --cert-name sandersdashandseal.com \
        -d "${SDS_DOMAINS[0]}" -d "${SDS_DOMAINS[1]}" -d "${SDS_DOMAINS[2]}" -d "${SDS_DOMAINS[3]}" \
        -m rooseveltsanders381@gmail.com --agree-tos --no-eff-email; then
        compose stop acme-bootstrap
        fail 'Certificate issuance failed; no TLS deployment was declared live.'
    fi
    compose stop acme-bootstrap
}

renew_certificates() {
    local before after
    before=$(compose exec -T reverse-proxy sha256sum /etc/letsencrypt/live/sandersdashandseal.com/fullchain.pem)
    compose run --rm --no-deps certbot renew --non-interactive --webroot --webroot-path=/var/www/certbot
    after=$(compose exec -T reverse-proxy sha256sum /etc/letsencrypt/live/sandersdashandseal.com/fullchain.pem)
    if [[ "$before" != "$after" ]]; then
        compose exec -T reverse-proxy nginx -t
        compose exec -T reverse-proxy nginx -s reload
    fi
}

validate_live() {
    local attempt domain
    for attempt in {1..30}; do
        if compose exec -T wsgi-backend python -c \
            "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/readyz',headers={'Host':'sandersdashandseal.com'}),timeout=3)"; then
            break
        fi
        (( attempt < 30 )) || fail 'Python authority/readiness remains unavailable.'
        sleep 2
    done
    compose exec -T reverse-proxy nginx -t
    curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
        --resolve "sandersdashandseal.com:443:$SDS_PUBLIC_IPV4" https://sandersdashandseal.com/readyz
    for domain in "${SDS_DOMAINS[@]:1}"; do
        curl --fail --silent --show-error --output /dev/null --connect-timeout 5 --max-time 10 \
            --resolve "$domain:443:$SDS_PUBLIC_IPV4" "https://$domain/"
    done
    printf '\nHTTPS/readiness checks passed from this host. External authenticated WebSocket validation remains a separate check.\n'
}

install_monitors() {
    install -d -m 0700 "$SDS_STATE_DIR"
    python3 "$SDS_PROJECT_DIR/deploy/host_integrity.py" baseline "$SDS_PROJECT_DIR" "$SDS_STATE_DIR/integrity.json"
    for unit in "$SDS_PROJECT_DIR"/deploy/systemd/*.service "$SDS_PROJECT_DIR"/deploy/systemd/*.timer; do
        install -m 0644 "$unit" /etc/systemd/system/
    done
    systemctl daemon-reload
    systemctl enable --now sanders-integrity.timer sanders-certbot-renew.timer
}

main() {
    local mode=${1:---check} source_dir stage existing_project approved_commit
    source_dir=${SDS_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
    [[ "$mode" == --check || "$mode" == --apply ]] || fail 'Use --check or --apply.'
    check_source "$source_dir"
    if [[ "$mode" == --check ]]; then
        printf 'Source checkout is clean. Apply requires OL9, active firewalld, real release authorization and protected runtime configuration. No host changes made.\n'
        return
    fi
    [[ "$EUID" == 0 ]] || fail '--apply requires root.'
    [[ "$SDS_PROJECT_DIR" == /opt/sanders-dash-seal && "$SDS_STATE_DIR" == /var/lib/sanders-dash-seal \
        && "$SDS_COMPOSE_PROJECT" == sanders-dash-seal ]] || fail 'Systemd templates currently require the default project/state paths and Compose project.'
    check_host
    approved_commit=$(git -C "$source_dir" rev-parse HEAD)
    authorize_release "$source_dir" "$approved_commit"
    install_engine
    existing_project=$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' sds_wsgi_backend 2>/dev/null || true)
    [[ -z "$existing_project" || "$existing_project" == "$SDS_COMPOSE_PROJECT" ]] || fail 'Existing container uses a different project/volume identity; review migration first.'
    configure_firewall
    [[ ! -L "$SDS_PROJECT_DIR" ]] || fail 'Project directory cannot be a symlink.'
    install -d -m 0755 "$SDS_PROJECT_DIR"
    stage=$(mktemp -d /opt/sds-stage.XXXXXX)
    git -C "$source_dir" archive "$approved_commit" | tar -x -C "$stage" --no-same-owner
    if ! python3 "$source_dir/deploy/host_integrity.py" validate-stage "$stage" "$SDS_PROJECT_DIR"; then
        rm -rf -- "$stage"
        fail 'Existing unrecognized source files require review before staging.'
    fi
    cp -a "$stage/." "$SDS_PROJECT_DIR/"
    rm -rf -- "$stage"
    export SDS_RUNTIME_ENV_FILE
    compose config --quiet
    compose build pipeline-worker wsgi-backend
    issue_certificate
    compose up -d pipeline-worker wsgi-backend reverse-proxy
    validate_live
    install_monitors
    printf 'Deployment validation completed; certificate and integrity timers installed.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
