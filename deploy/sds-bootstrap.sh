#!/bin/bash
# Once-per-instance cloud-init driver; secrets never belong in user_data.
set -Eeuo pipefail

SDS_BOOTSTRAP_REPOSITORY=https://github.com/DashandSeal/Sanders_Dash_Seal.git
SDS_SOURCE_DIR=${SDS_SOURCE_DIR:-/opt/sds-approved-source}
SDS_BOOTSTRAP_MODE=${SDS_BOOTSTRAP_MODE:-stage}
SDS_TUNE_KERNEL=${SDS_TUNE_KERNEL:-0}

bootstrap_fail() { printf 'Standardization stopped: %s\n' "$*" >&2; return 1; }
require_bootstrap_root() { [[ "$EUID" == 0 ]] || bootstrap_fail 'Cloud-init driver requires root.'; }

prepare_checkout() {
    [[ "${SDS_BOOTSTRAP_COMMIT:-}" =~ ^[0-9a-f]{40}$ ]] || bootstrap_fail 'Exact approved commit SHA required.'
    [[ "$SDS_SOURCE_DIR" == /opt/sds-approved-source ]] || bootstrap_fail 'Unexpected source checkout path.'
    [[ ! -L "$SDS_SOURCE_DIR" ]] || bootstrap_fail 'Source checkout cannot be a symlink.'
    export GIT_TERMINAL_PROMPT=0
    if [[ ! -d "$SDS_SOURCE_DIR/.git" ]]; then
        [[ ! -e "$SDS_SOURCE_DIR" ]] || bootstrap_fail 'Existing source directory needs review; refusing overwrite.'
        git clone --no-checkout "$SDS_BOOTSTRAP_REPOSITORY" "$SDS_SOURCE_DIR"
    else
        [[ "$(git -C "$SDS_SOURCE_DIR" remote get-url origin)" == "$SDS_BOOTSTRAP_REPOSITORY" ]] \
            || bootstrap_fail 'Unexpected repository origin.'
        [[ -z "$(git -C "$SDS_SOURCE_DIR" status --porcelain --untracked-files=all)" ]] \
            || bootstrap_fail 'Source checkout has drift.'
    fi
    if ! git -C "$SDS_SOURCE_DIR" cat-file -e "$SDS_BOOTSTRAP_COMMIT^{commit}"; then
        git -C "$SDS_SOURCE_DIR" fetch --no-tags origin "$SDS_BOOTSTRAP_COMMIT"
    fi
    git -C "$SDS_SOURCE_DIR" checkout --detach "$SDS_BOOTSTRAP_COMMIT"
    [[ "$(git -C "$SDS_SOURCE_DIR" rev-parse HEAD)" == "$SDS_BOOTSTRAP_COMMIT" ]] \
        || bootstrap_fail 'Checkout identity mismatch.'
}

apply_kernel_profile() {
    [[ "$SDS_TUNE_KERNEL" == 1 ]] || return 0
    # Explicit owner-selected profile, not a measured throughput guarantee.
    python3 "$SDS_SOURCE_DIR/deploy/kernel_profile.py" --apply
}

verify_bootstrap_source() {
    # Verify with independently provisioned code BEFORE sourcing repository code
    # as root. The deployment script repeats runtime/release checks afterward.
    local authorizer=/etc/sanders-dash-seal/authorize-release
    [[ -x "$authorizer" && ! -L "$authorizer" ]] \
        || bootstrap_fail 'Independent release authorizer required before loading source.'
    [[ "$(stat -c %u "$authorizer")" == 0 ]] || bootstrap_fail 'Authorizer must be root-owned.'
    (( (8#$(stat -c %a "$authorizer") & 0022) == 0 )) || bootstrap_fail 'Authorizer is group/world writable.'
    "$authorizer" "$SDS_SOURCE_DIR" "$SDS_BOOTSTRAP_COMMIT"
}

stage_node() {
    check_source "$SDS_SOURCE_DIR"
    check_host
    authorize_release "$SDS_SOURCE_DIR" "$SDS_BOOTSTRAP_COMMIT"
    local existing
    [[ "$SDS_PROJECT_DIR" == /opt/sanders-dash-seal && "$SDS_STATE_DIR" == /var/lib/sanders-dash-seal ]] \
        || bootstrap_fail 'Monitor templates require the standard project/state paths.'
    existing=$(docker ps -aq --filter label=com.docker.compose.project=sanders-dash-seal 2>/dev/null || true)
    [[ -z "$existing" ]] || bootstrap_fail 'Stage mode requires a fresh node without existing application containers.'
    [[ ! -e "$SDS_STATE_DIR/integrity.json" ]] \
        || bootstrap_fail 'Existing integrity baseline requires a reviewed update; refusing rebaseline.'
    install_engine
    configure_firewall
    stage_authorized_source "$SDS_SOURCE_DIR" "$SDS_BOOTSTRAP_COMMIT"
    export SDS_RUNTIME_ENV_FILE
    compose config --quiet
    compose build pipeline-worker wsgi-backend
    apply_kernel_profile
    install_integrity_monitor
    install_inventory_monitor
    printf 'STAGED: approved source, images and integrity monitoring prepared. Application services were not started.\n'
}

bootstrap_main() {
    require_bootstrap_root
    [[ "$SDS_BOOTSTRAP_MODE" == stage || "$SDS_BOOTSTRAP_MODE" == activate ]] \
        || bootstrap_fail 'Use stage or activate mode.'
    [[ "$SDS_TUNE_KERNEL" == 0 || "$SDS_TUNE_KERNEL" == 1 ]] || bootstrap_fail 'Invalid tuning selection.'
    if [[ "$SDS_BOOTSTRAP_MODE" == activate ]]; then
        # Never inherit the original host IP for a newly launched node.
        [[ -n "${SDS_PUBLIC_IPV4:-}" ]] || bootstrap_fail "Activate requires this node's verified public IPv4."
        python3 -c 'import ipaddress,sys; ipaddress.IPv4Address(sys.argv[1])' "$SDS_PUBLIC_IPV4"
    fi
    prepare_checkout
    verify_bootstrap_source
    # Reuse the same external authority, firewall and readiness controls.
    source "$SDS_SOURCE_DIR/deploy.sh"
    if [[ "$SDS_BOOTSTRAP_MODE" == stage ]]; then
        stage_node
    else
        main --apply
        apply_kernel_profile
        printf 'ACTIVATED: existing deployment readiness checks passed on this host.\n'
    fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then bootstrap_main "$@"; fi
